"""Model catalog, download, extraction, and verification. Download into temporary files and validate known hashes; fetch large models only when selected."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
import urllib.error
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(PROJECT_ROOT, "models.json")
DEFAULT_MODEL = "sensevoice"

MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


def load_catalog() -> dict:
    with open(CATALOG_PATH) as fh:
        return json.load(fh)


def models() -> dict[str, dict]:
    return load_catalog().get("models", {})


def selectable_models() -> dict[str, dict]:
    return {name: spec for name, spec in models().items() if not spec.get("hidden")}


def cloud_presets() -> dict[str, dict]:
    return load_catalog().get("cloud_presets", {})


def get(name: str) -> dict:
    catalog = models()
    if name not in catalog:
        raise KeyError(f"Unknown model: {name}(choose from: {', '.join(catalog)})")
    return catalog[name]


def model_dir(name: str) -> str:
    return os.path.join(MODELS_DIR, get(name)["dir"])


def is_installed(name: str) -> bool:
    path = model_dir(name)
    if not os.path.isdir(path):
        return False
    spec = get(name)
    required = spec.get("files") or {}
    if required:
        return all(os.path.exists(os.path.join(path, f)) for f in required)

    return any(f.endswith(".onnx") for f in os.listdir(path))


def installed_models() -> list[str]:
    return [name for name in models() if is_installed(name)]


def sha256(path: str, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify(name: str, *, path: str | None = None) -> list[str]:
    """Return validation problems; an empty list means verification passed."""
    spec = get(name)
    path = path or model_dir(name)
    problems: list[str] = []
    if not os.path.isdir(path):
        return [f"Directory does not exist: {path}"]
    from .backends.local_sherpa import find_model_files
    try:
        files = find_model_files(path)
        if spec.get("streaming") and not files.get("joiner"):
            problems.append("Missing streaming model joiner")
    except FileNotFoundError as exc:
        problems.append(str(exc))
    for filename, expected in (spec.get("files") or {}).items():
        target = os.path.join(path, filename)
        if not os.path.exists(target):
            problems.append(f"Missing {filename}")
            continue
        actual = sha256(target)
        if actual != expected:
            problems.append(f"{filename} sha256 mismatch (expected {expected[:12]}..., got {actual[:12]}…)")
    return problems


def remove(name: str) -> bool:
    path = model_dir(name)
    if not os.path.isdir(path):
        return False
    shutil.rmtree(path)
    return True


def open_download(url, on_phase):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(url, timeout=60)
        except urllib.error.URLError as exc:
            if attempt == 2 or (isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429):
                raise
            on_phase("retrying")
            time.sleep(attempt + 1)


def install(name: str, on_progress=None, on_phase=None) -> str:
    """Download and extract a model; report progress as completed and total bytes."""
    spec = get(name)
    phase = on_phase or (lambda _name: None)
    phase("checking")
    os.makedirs(MODELS_DIR, exist_ok=True)
    target_dir = model_dir(name)
    if is_installed(name) and not verify(name):
        return target_dir

    phase("connecting")
    fd, archive = tempfile.mkstemp(suffix=".tar.bz2", dir=MODELS_DIR)
    os.close(fd)
    part = archive + ".part"
    try:
        with open_download(spec["url"], phase) as resp, \
                open(part, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                block = resp.read(1 << 16)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if on_progress:
                    on_progress(done, total)
        os.replace(part, archive)

        phase("extracting")
        with tarfile.open(archive, "r:bz2") as tar:
            tmpdir = tempfile.mkdtemp(dir=MODELS_DIR)
            try:
                tar.extractall(tmpdir, filter="data")
                inner = os.path.join(tmpdir, spec["dir"])
                source = inner if os.path.isdir(inner) else tmpdir
                phase("verifying")
                problems = verify(name, path=source)
                if problems:
                    raise RuntimeError("Model verification failed: " + "; ".join(problems))
                # Publish only a complete model; retain the prior copy on error.
                backup = tempfile.mkdtemp(prefix="backup-", dir=MODELS_DIR)
                previous = os.path.join(backup, "model")
                try:
                    if os.path.isdir(target_dir):
                        os.replace(target_dir, previous)
                    try:
                        os.replace(source, target_dir)
                    except BaseException:
                        if os.path.isdir(previous):
                            os.replace(previous, target_dir)
                        raise
                finally:
                    shutil.rmtree(backup, ignore_errors=True)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
    finally:
        for path in (part, archive):
            if os.path.exists(path):
                os.unlink(path)

    phase("verifying")
    problems = verify(name)
    if problems:
        raise RuntimeError("Model verification failed: " + "; ".join(problems))
    return target_dir
