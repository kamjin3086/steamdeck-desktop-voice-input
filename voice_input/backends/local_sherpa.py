"""Local sherpa-onnx backend. Transducer models decode incrementally with throttling; Whisper models buffer audio for offline decoding."""

from __future__ import annotations

import glob
import os
import time

from .base import SAMPLE_RATE, Backend, Session, pcm16_to_float


def _pick(pattern: str) -> str | None:
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def find_model_files(model_dir: str) -> dict[str, str]:
    """Find encoder, decoder, optional joiner, and tokens; prefer int8 weights."""
    files = {
        "tokens": _pick(os.path.join(model_dir, "*tokens.txt")),
        "encoder": _pick(os.path.join(model_dir, "*encoder*.int8.onnx"))
        or _pick(os.path.join(model_dir, "*encoder*.onnx")),
        "decoder": _pick(os.path.join(model_dir, "*decoder*.int8.onnx"))
        or _pick(os.path.join(model_dir, "*decoder*.onnx")),
        "joiner": _pick(os.path.join(model_dir, "*joiner*.int8.onnx"))
        or _pick(os.path.join(model_dir, "*joiner*.onnx")),
    }
    missing = [k for k, v in files.items() if k != "joiner" and (not v or not os.path.exists(v))]
    if missing:
        raise FileNotFoundError(
            f"{model_dir} missing model files: {missing}"
        )
    return files


class SherpaSession(Session):
    def __init__(self, recognizer, streaming: bool, on_partial=None,
                 throttle: float = 0.12, debug: bool = False):
        self.rec = recognizer
        self.streaming = streaming
        self.on_partial = on_partial
        self.throttle = throttle
        self.debug = debug
        self.stream = recognizer.create_stream()
        self._last_decode = 0.0
        self._buffered: list[float] = []
        self._last_partial = ""

    def _decode(self) -> None:
        while self.rec.is_ready(self.stream):
            self.rec.decode_stream(self.stream)


    def accept(self, pcm: bytes) -> None:
        samples = pcm16_to_float(pcm)
        if not samples:
            return
        if not self.streaming:
            self._buffered.extend(samples)
            return
        self.stream.accept_waveform(SAMPLE_RATE, samples)
        now = time.monotonic()
        if now - self._last_decode >= self.throttle:
            self._last_decode = now
            self._decode()
            text = (self.rec.get_result(self.stream) or "").strip()
            if text and text != self._last_partial:
                self._last_partial = text
                if self.on_partial:
                    self.on_partial(text)

    def finish(self) -> str:
        if not self.streaming:
            self.stream.accept_waveform(SAMPLE_RATE, self._buffered)

        self.stream.accept_waveform(SAMPLE_RATE, [0.0] * int(0.4 * SAMPLE_RATE))
        if self.streaming:
            self.stream.input_finished()
            self._decode()
            return (self.rec.get_result(self.stream) or "").strip()
        self.rec.decode_stream(self.stream)
        self._buffered.clear()
        return (self.stream.result.text or "").strip()

    def cancel(self) -> None:
        self._buffered.clear()


class LocalSherpaBackend(Backend):
    name = "local"

    def __init__(self, model_dir: str, num_threads: int = 2,
                 language: str = "zh", provider: str = "cpu",
                 debug: bool = False):
        import sherpa_onnx

        self.sherpa = sherpa_onnx
        self.model_dir = model_dir
        self.language = language
        self.debug = debug
        files = find_model_files(model_dir)
        self.streaming = bool(files.get("joiner"))
        self.kind = "online-transducer" if self.streaming else "offline"

        if self.streaming:
            self.rec = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=files["tokens"],
                encoder=files["encoder"],
                decoder=files["decoder"],
                joiner=files["joiner"],
                num_threads=num_threads,
                sample_rate=SAMPLE_RATE,
                feature_dim=80,
                decoding_method="greedy_search",
                provider=provider,
                enable_endpoint_detection=False,
            )
        else:
            self.rec = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=files["encoder"],
                decoder=files["decoder"],
                tokens=files["tokens"],
                num_threads=num_threads,
                decoding_method="greedy_search",
                language=language,
                task="transcribe",
                provider=provider,
                debug=debug,
            )

    @property
    def supports_partial(self) -> bool:
        return self.streaming

    def open_session(self, on_partial=None) -> SherpaSession:
        return SherpaSession(self.rec, self.streaming, on_partial,
                             debug=self.debug)

    def describe(self) -> str:
        mode = "streaming" if self.streaming else "offline"
        return f"local:{os.path.basename(self.model_dir)}({mode})"
