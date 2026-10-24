"""Local sherpa-onnx backend. Transducer models decode incrementally with throttling; Whisper models buffer audio for offline decoding."""

from __future__ import annotations

import glob
import os
import re
import time

from .base import SAMPLE_RATE, Backend, Session, pcm16_to_float


def _pick(pattern: str) -> str | None:
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def find_model_files(model_dir: str) -> dict[str, str]:
    """Find encoder, decoder, optional joiner, and tokens; prefer int8 weights."""
    frontend = _pick(os.path.join(model_dir, "conv_frontend*.onnx"))
    if frontend:
        files = {"conv_frontend": frontend,
                 "encoder": _pick(os.path.join(model_dir, "encoder.int8.onnx")),
                 "decoder": _pick(os.path.join(model_dir, "decoder.int8.onnx")),
                 "tokenizer": os.path.join(model_dir, "tokenizer")}
        missing = [k for k, v in files.items() if not v or not os.path.exists(v)]
        missing += [f"tokenizer/{f}" for f in ("vocab.json", "merges.txt", "tokenizer_config.json")
                    if not os.path.isfile(os.path.join(model_dir, "tokenizer", f))]
        if missing:
            raise FileNotFoundError(f"{model_dir} missing model files: {missing}")
        return files
    tokens = _pick(os.path.join(model_dir, "*tokens.txt"))
    single = _pick(os.path.join(model_dir, "model.int8.onnx")) or _pick(os.path.join(model_dir, "model.onnx"))
    if single and tokens:
        return {"model": single, "tokens": tokens}
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
                 throttle: float = 0.12, debug: bool = False, clean_tags: bool = False):
        self.rec = recognizer
        self.streaming = streaming
        self.on_partial = on_partial
        self.throttle = throttle
        self.debug = debug
        self.clean_tags = clean_tags
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
        if self.streaming:
            self.stream.accept_waveform(SAMPLE_RATE, [0.0] * int(0.4 * SAMPLE_RATE))
            self.stream.input_finished()
            self._decode()
            return (self.rec.get_result(self.stream) or "").strip()
        self.stream.accept_waveform(SAMPLE_RATE, self._buffered)
        self.rec.decode_stream(self.stream)
        self._buffered.clear()
        text = self.stream.result.text or ""
        # SenseVoice event/language/emotion markers are metadata, not dictation.
        return (re.sub(r"<\|[^|]*\|>", "", text) if self.clean_tags else text).strip()

    def cancel(self) -> None:
        self._buffered.clear()


class LocalSherpaBackend(Backend):
    name = "local"

    def __init__(self, model_dir: str, num_threads: int = 2,
                 language: str = "auto", provider: str = "cpu",
                 debug: bool = False, model_type: str | None = None):
        import sherpa_onnx

        self.sherpa = sherpa_onnx
        self.model_dir = model_dir
        self.language = language
        self.debug = debug
        files = find_model_files(model_dir)
        self.streaming = bool(files.get("joiner"))
        self.kind = "online-transducer" if self.streaming else "offline"

        self.sensevoice = "model" in files and model_type != "omnilingual"
        if "conv_frontend" in files:
            self.rec = sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
                conv_frontend=files["conv_frontend"], encoder=files["encoder"],
                decoder=files["decoder"], tokenizer=files["tokenizer"], max_new_tokens=256,
                num_threads=num_threads, provider=provider, debug=debug,
            )
        elif model_type == "omnilingual":
            self.rec = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
                model=files["model"], tokens=files["tokens"],
                num_threads=num_threads, provider=provider, debug=debug,
            )
        elif self.sensevoice:
            self.rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=files["model"], tokens=files["tokens"],
                num_threads=num_threads, language=language or "auto",
                use_itn=True, provider=provider, debug=debug,
            )
        elif self.streaming:
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
                language="" if language == "auto" else language,
                task="transcribe",
                provider=provider,
                debug=debug,
            )

    @property
    def supports_partial(self) -> bool:
        return self.streaming

    def open_session(self, on_partial=None) -> SherpaSession:
        return SherpaSession(self.rec, self.streaming, on_partial,
                             debug=self.debug, clean_tags=self.sensevoice)

    def describe(self) -> str:
        mode = "streaming" if self.streaming else "offline"
        return f"local:{os.path.basename(self.model_dir)}({mode})"
