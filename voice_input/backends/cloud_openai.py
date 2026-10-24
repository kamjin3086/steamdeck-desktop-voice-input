"""Buffer PCM and send WAV audio to an OpenAI-compatible transcription endpoint. Supports hosted and LAN services."""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
import uuid
import wave

from .base import SAMPLE_RATE, Backend, Session

DEFAULT_TIMEOUT = 30.0


def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _multipart(fields: dict[str, str], file_field: str, filename: str,
               file_bytes: bytes) -> tuple[bytes, str]:
    boundary = "----voice-input-" + uuid.uuid4().hex
    out = io.BytesIO()
    for key, value in fields.items():
        if value is None:
            continue
        out.write(f"--{boundary}\r\n".encode())
        out.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        out.write(str(value).encode())
        out.write(b"\r\n")
    out.write(f"--{boundary}\r\n".encode())
    out.write(
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'.encode()
    )
    out.write(b"Content-Type: audio/wav\r\n\r\n")
    out.write(file_bytes)
    out.write(f"\r\n--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


class CloudSession(Session):
    supports_partial = False

    def __init__(self, backend: "CloudBackend"):
        self.backend = backend
        self._pcm = bytearray()
        self._cancelled = False

    def accept(self, pcm: bytes) -> None:
        self._pcm += pcm

    def cancel(self) -> None:
        self._cancelled = True
        self._pcm.clear()

    def finish(self) -> str:
        if self._cancelled or not self._pcm:
            return ""
        return self.backend.transcribe_pcm(bytes(self._pcm))


class CloudBackend(Backend):
    name = "cloud"

    def __init__(self, base_url: str, api_key: str = "", model: str = "whisper-1",
                 language: str | None = "zh", timeout: float = DEFAULT_TIMEOUT,
                 response_format: str = "json", debug: bool = False,
                 extra_fields: dict | None = None, endpoint: str | None = None):
        self.base_url = base_url.rstrip("/")

        self._endpoint = endpoint
        self.api_key = api_key or ""
        self.model = model
        self.language = language
        self.timeout = timeout
        self.response_format = response_format
        self.debug = debug
        self.extra_fields = extra_fields or {}
        self.last_error: str | None = None

    @property
    def endpoint(self) -> str:
        if self._endpoint:
            return self._endpoint
        if self.base_url.endswith("/audio/transcriptions"):
            return self.base_url
        return f"{self.base_url}/audio/transcriptions"

    def open_session(self, on_partial=None) -> CloudSession:
        return CloudSession(self)

    def describe(self) -> str:
        return f"cloud:{self.model} @ {self.base_url}"


    def transcribe_pcm(self, pcm: bytes) -> str:
        started = time.monotonic()
        fields = {
            "model": self.model,
            "language": self.language,
            "response_format": self.response_format,
        }
        fields.update(self.extra_fields)
        body, content_type = _multipart(
            fields, "file", "speech.wav", pcm_to_wav_bytes(pcm)
        )
        headers = {"Content-Type": content_type, "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_exc: Exception | None = None
        for attempt in range(2):
            req = urllib.request.Request(
                self.endpoint, data=body, headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode(errors="replace")
                text = self._parse(raw)
                if self.debug:
                    print(f"[cloud] {time.monotonic() - started:.2f}s -> {text!r}",
                          flush=True)
                self.last_error = None
                return text
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                self.last_error = f"HTTP {exc.code}: {detail}"
                if exc.code in (401, 403):
                    break
                last_exc = exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self.last_error = f"Cannot connect to {self.endpoint}: {exc}"
                last_exc = exc
            if attempt == 0:
                time.sleep(0.4)

        if self.last_error:
            raise RuntimeError(self.last_error) from last_exc
        raise RuntimeError("Cloud transcription failed (unknown cause)")

    @staticmethod
    def _parse(raw: str) -> str:
        raw = raw.strip()
        if not raw:
            return ""
        try:
            data = json.loads(raw)
        except ValueError:
            return raw
        if isinstance(data, dict):
            return str(data.get("text", "")).strip()
        return raw
