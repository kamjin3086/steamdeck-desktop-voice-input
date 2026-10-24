"""Shared recognition backend and session interfaces."""

from __future__ import annotations

from array import array

SAMPLE_RATE = 16000


def pcm16_to_float(pcm: bytes) -> list[float]:
    """Convert little-endian PCM16 to normalized floating-point samples."""
    if len(pcm) < 2:
        return []
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    return [s / 32768.0 for s in samples]


class Session:
    """One recognition segment within a physical button hold."""

    supports_partial = False

    def accept(self, pcm: bytes) -> None:
        raise NotImplementedError

    def finish(self) -> str:
        raise NotImplementedError

    def cancel(self) -> None:
        """Discard unfinished recognition; the default implementation does nothing."""


class Backend:
    name = "base"
    supports_partial = False

    def open_session(self, on_partial=None) -> Session:
        """Create a session; on_partial receives updated partial transcripts."""
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError
