"""Inject ASCII with uinput; paste Unicode using KDE Klipper or wl-copy, optionally restoring the clipboard."""

from __future__ import annotations

import shutil
import subprocess
import time

from .uinput_kbd import VirtualKeyboard


def _run(cmd: list[str], timeout: float = 3.0) -> tuple[bool, str]:
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return out.returncode == 0, out.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False, ""


class Injector:
    def __init__(self, restore_clipboard: bool = True, debug: bool = False):
        self.kbd = VirtualKeyboard()
        self.restore_clipboard = restore_clipboard
        self.debug = debug
        self._qdbus = shutil.which("qdbus") or shutil.which("qdbus6") or "qdbus"
        self._klipper = self._klipper_available()
        if self.debug:
            print(f"[inject] klipper={bool(self._klipper)}", flush=True)

    def _klipper_available(self) -> bool:
        ok, out = _run([self._qdbus, "org.kde.klipper", "/klipper",
                        "org.kde.klipper.klipper.getClipboardContents"])
        return ok


    def _get_clipboard(self) -> str | None:
        ok, out = _run([self._qdbus, "org.kde.klipper", "/klipper",
                        "org.kde.klipper.klipper.getClipboardContents"])
        return out.rstrip("\n") if ok else None

    def _set_clipboard(self, text: str) -> bool:
        if self._klipper:
            ok, _ = _run([self._qdbus, "org.kde.klipper", "/klipper",
                          "org.kde.klipper.klipper.setClipboardContents", text])
            return ok
        if shutil.which("wl-copy"):
            try:
                subprocess.run(["wl-copy", text], timeout=3, check=True)
                return True
            except (OSError, subprocess.SubprocessError):
                return False
        return False


    @staticmethod
    def is_ascii(text: str) -> bool:
        return all(ord(ch) < 128 for ch in text)

    def type_or_paste(self, text: str) -> str:
        """Inject text and return 'type', 'paste', or 'none'."""
        if not text:
            return "none"
        if self.is_ascii(text):
            self.kbd.type_text(text)
            return "type"

        previous = self._get_clipboard() if self.restore_clipboard else None
        if not self._set_clipboard(text):
            raise RuntimeError("No usable clipboard service (Klipper and wl-copy unavailable)")
        time.sleep(0.15)
        self.kbd.paste()
        time.sleep(0.35)
        if self.restore_clipboard and previous is not None:
            self._set_clipboard(previous)
        return "paste"

    def close(self) -> None:
        self.kbd.close()
