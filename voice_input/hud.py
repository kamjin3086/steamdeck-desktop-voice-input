"""Render recording levels and partial transcripts through a single terminal writer."""

from __future__ import annotations

import sys

CLEAR_LINE = "\r\033[K"


def meter_bar(level: float, width: int = 12) -> str:
    n = min(width, int(level * width * 4))
    return "▏" + "█" * n + "·" * (width - n)


class RecorderHUD:
    def __init__(self, meter: bool = True, partial: bool = True,
                 stream=None, width: int = 0):
        self.meter = meter
        self.partial = partial
        self.stream = stream or sys.stdout
        self.tty = getattr(self.stream, "isatty", lambda: False)()
        self.width = width
        self._last = ""
        self._drawn = False

    def _compose(self, level: float, elapsed: float, partial: str) -> str:
        parts = []
        if self.meter:
            parts.append(f"{meter_bar(level)} {elapsed:5.1f}s")
        if self.partial and partial:
            text = partial
            if self.width and len(text) > self.width:

                parts.append("…" + text[-(self.width - 1):])
            else:
                parts.append(f"… {text}")
        return "  ".join(parts)

    def draw(self, level: float, elapsed: float, partial: str = "") -> None:
        line = self._compose(level, elapsed, partial)
        if line == self._last:
            return
        self._last = line
        if not line:
            return
        if self.tty:
            self.stream.write(CLEAR_LINE + line)
        else:
            self.stream.write(line + "\n")
        self.stream.flush()
        self._drawn = True

    def done(self) -> None:
        """Clear the terminal HUD after recording."""
        if self.tty and self._drawn:
            self.stream.write(CLEAR_LINE)
            self.stream.flush()
        self._last = ""
        self._drawn = False


class PartialLog:
    """Write timestamped partial and final results to a diagnostic log."""

    def __init__(self, path: str | None):
        self.fh = open(path, "a", buffering=1) if path else None

    def write(self, event: str, text: str = "") -> None:
        if not self.fh:
            return
        import time
        stamp = time.strftime("%H:%M:%S")
        self.fh.write(f"{stamp}\t{event}\t{text}\n")

    def close(self) -> None:
        if self.fh:
            self.fh.close()
            self.fh = None
