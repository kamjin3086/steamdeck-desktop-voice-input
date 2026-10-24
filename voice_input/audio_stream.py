"""Persistent PipeWire PCM capture with a rolling buffer and pre-roll to preserve initial syllables."""

from __future__ import annotations

import os
import struct
import subprocess
import threading
import time
import wave
from array import array

SAMPLE_RATE = 16000


class AudioStream:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        preroll: float = 0.4,
        max_seconds: float = 70.0,
        device: str | None = None,
        debug: bool = False,
    ):
        self.sample_rate = sample_rate
        self.preroll = preroll
        self.max_bytes = int(max_seconds * sample_rate * 2)
        self.device = device
        self.debug = debug
        self._buf = bytearray()
        self._dropped = 0
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._running = False


    def start(self) -> None:
        cmd = [
            "pw-record",
            "--rate", str(self.sample_rate),
            "--channels", "1",
            "--format", "s16",
            "--latency", "40ms",
            "--container", "raw",
        ]
        if self.device:
            cmd += ["--target", self.device]
        cmd.append("-")
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, args=(self._proc,),
                                        daemon=True)
        self._reader.start()

    def _read_loop(self, proc: subprocess.Popen) -> None:
        out = proc.stdout
        assert out is not None
        while self._running:
            chunk = out.read(4096)
            if not chunk:
                break
            with self._lock:
                self._buf += chunk
                overflow = len(self._buf) - self.max_bytes
                if overflow > 0:
                    del self._buf[:overflow]
                    self._dropped += overflow
        if self._running and self.debug:
            print("[audio] Capture stopped (device changed?); restart the application", flush=True)

    def stop(self) -> None:
        self._running = False
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def __enter__(self) -> "AudioStream":
        self.start()

        deadline = time.monotonic() + 3
        while self.position() == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


    def position(self) -> int:
        with self._lock:
            return self._dropped + len(self._buf)

    def _absolute_view(self) -> tuple[int, bytearray]:
        with self._lock:
            return self._dropped, bytearray(self._buf)

    def slice_from(self, pos: int) -> bytes:
        """Read PCM from an absolute position, including pre-roll."""
        start = max(0, pos - int(self.preroll * self.sample_rate * 2))
        dropped, buf = self._absolute_view()
        offset = max(0, start - dropped)
        return bytes(buf[offset:])

    def read_since(self, pos: int) -> tuple[bytes, int]:
        """Return incremental PCM and its new absolute cursor."""
        dropped, buf = self._absolute_view()
        start = max(0, pos - dropped)
        return bytes(buf[start:]), dropped + len(buf)

    def bytes_since(self, pos: int) -> int:
        return self.position() - pos

    def level(self, window: float = 0.1) -> float:
        """Return RMS over the most recent window."""
        dropped, buf = self._absolute_view()
        nbytes = int(window * self.sample_rate * 2)
        tail = bytes(buf[-nbytes:]) if buf else b""
        if len(tail) < 2:
            return 0.0
        samples = array("h")
        samples.frombytes(tail[: len(tail) // 2 * 2])
        if not samples:
            return 0.0
        total = sum(s * s for s in samples) / len(samples)
        return (total ** 0.5) / 32768.0


def pcm_stats(pcm: bytes) -> tuple[float, float]:
    """Return normalized peak and RMS for PCM16 audio."""
    if len(pcm) < 2:
        return 0.0, 0.0
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return 0.0, 0.0
    peak = max(abs(s) for s in samples) / 32768.0
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5 / 32768.0
    return peak, rms


def write_wav(path: str, pcm: bytes, sample_rate: int = SAMPLE_RATE) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
