"""Build local or OpenAI-compatible transcription backends from ASR configuration."""

from __future__ import annotations

import os

from .. import models_registry as registry
from .base import Backend, Session
from .cloud_openai import CloudBackend
from .local_sherpa import LocalSherpaBackend


def create_backend(cfg: dict | None, debug: bool = False) -> Backend:
    cfg = dict(cfg or {})
    kind = cfg.get("backend", "local")

    if kind == "local":
        name = cfg.get("model", "zh14m")
        if not registry.is_installed(name):
            raise RuntimeError(
                f"Model {name} is not installed: ./run.sh models install {name}"
            )
        return LocalSherpaBackend(
            registry.model_dir(name),
            num_threads=int(cfg.get("num_threads", 2)),
            language=cfg.get("language", "zh"),
            provider=cfg.get("provider", "cpu"),
            debug=debug,
        )

    if kind == "cloud":
        preset_name = cfg.get("preset")
        preset = registry.cloud_presets().get(preset_name, {}) if preset_name else {}
        base_url = cfg.get("base_url") or preset.get("base_url")
        if not base_url:
            raise RuntimeError("Cloud backend requires base_url or a preset")
        api_key = cfg.get("api_key") or ""
        env_name = preset.get("api_key_env") or ""
        if not api_key and env_name:
            api_key = os.environ.get(env_name, "")
        return CloudBackend(
            base_url=base_url,
            api_key=api_key,
            model=cfg.get("model") or preset.get("model") or "whisper-1",
            language=cfg.get("language", "zh"),
            timeout=float(cfg.get("timeout", 30)),
            response_format=cfg.get("response_format", "json"),
            endpoint=cfg.get("endpoint"),
            debug=debug,
        )

    raise RuntimeError(f"Unknown ASR backend: {kind}(local / cloud)")
