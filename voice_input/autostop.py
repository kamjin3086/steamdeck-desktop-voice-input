"""Detect silence after speech using an explicit clock; the caller decides how to segment recording."""

from __future__ import annotations


class SilenceStopper:
    def __init__(self, silence_ms: float = 600, speech_peak: float = 0.02):
        self.silence_ms = silence_ms
        self.speech_peak = speech_peak
        self.speech_seen = False
        self.silent_since: float | None = None

    def reset(self) -> None:
        self.speech_seen = False
        self.silent_since = None

    def feed(self, peak: float, now: float) -> bool:
        """Return whether silence after speech has exceeded the configured duration."""
        if peak >= self.speech_peak:
            self.speech_seen = True
            self.silent_since = None
            return False
        if not self.speech_seen:
            return False
        if self.silent_since is None:
            self.silent_since = now
            return False
        return (now - self.silent_since) * 1000.0 >= self.silence_ms
