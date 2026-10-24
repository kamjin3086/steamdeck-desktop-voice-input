"""WAV utilities and one-shot transcription through the shared backend interface."""

from __future__ import annotations

import wave
from array import array

from .backends import create_backend

SAMPLE_RATE = 16000


def read_wav(path: str) -> array:
    """Read mono, 16 kHz, 16-bit PCM WAV samples into array('h')."""
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1:
            raise ValueError(f"Expected mono audio, got {w.getnchannels()}")
        if w.getsampwidth() != 2:
            raise ValueError(f"Expected 16-bit samples, got {w.getsampwidth() * 8}bit")
        rate = w.getframerate()
        data = w.readframes(w.getnframes())
    if rate != SAMPLE_RATE:
        raise ValueError(f"Expected {SAMPLE_RATE}Hz, got {rate}Hz")
    samples = array("h")
    samples.frombytes(data)
    return samples


def transcribe_file(path: str, backend, chunk: int = 3200) -> str:
    """Feed a WAV file in 100 ms chunks and return the final transcript."""
    samples = read_wav(path)
    pcm = samples.tobytes()
    session = backend.open_session()
    for off in range(0, len(pcm), chunk * 2):
        session.accept(pcm[off: off + chunk * 2])
    return session.finish()


def backend_from_config(cfg: dict | None = None, debug: bool = False):
    return create_backend(cfg, debug=debug)
