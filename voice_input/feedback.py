"""Generate short start/stop tones and play them with pw-play."""

from __future__ import annotations

import math
import os
import struct
import subprocess
import tempfile
import shutil
import time
import wave
from array import array


def _tone(path: str, freq: float, seconds: float = 0.07,
          rate: int = 16000, volume: float = 0.25) -> None:
    n = int(rate * seconds)
    fade = max(1, n // 6)
    samples = array("h")
    for i in range(n):
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = (n - i) / fade
        samples.append(
            int(volume * env * 32767 * math.sin(2 * math.pi * freq * i / rate))
        )
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


class Beep:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and bool(os.environ.get("PIPEWIRE_REMOTE", "1"))
        self._start = None
        self._stop = None
        self._directory = None
        if not self.enabled:
            return
        d = self._directory = tempfile.mkdtemp(prefix="voice-input-beep-")
        self._start = os.path.join(d, "start.wav")
        self._stop = os.path.join(d, "stop.wav")
        try:
            _tone(self._start, 880)
            _tone(self._stop, 520)
        except OSError:
            self.enabled = False

    def _play(self, path: str | None) -> None:
        if not self.enabled or not path:
            return
        try:
            subprocess.run(["pw-play", path], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=2, check=True)
            # Let speaker echo and queued microphone frames settle before the
            # caller establishes the next audio boundary.
            time.sleep(0.20)
        except (OSError, subprocess.SubprocessError):
            self.enabled = False

    def start(self) -> None:
        self._play(self._start)

    def stop(self) -> None:
        self._play(self._stop)

    def close(self):
        if self._directory:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = None
