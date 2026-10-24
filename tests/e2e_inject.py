"""E2e inject checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input.inject import Injector                          # noqa: E402
from voice_input.uinput_kbd import (                             # noqa: E402
    KEY, VirtualKeyboard, VirtualPointer,
)

TITLE = "voice-input-e2e"


def screen_size() -> tuple[int, int]:
    try:
        out = subprocess.run(["kscreen-doctor", "--json"], capture_output=True,
                             text=True, timeout=5).stdout
        data = json.loads(out)
        for output in data["outputs"]:
            if output.get("enabled", True):
                size = output["size"]
                return size["width"], size["height"]
    except Exception:  # noqa: BLE001
        pass
    return 1280, 800


def run_case(text: str, mode: str) -> bool:
    """Exercise ASCII typing or Unicode clipboard paste."""
    width, height = screen_size()
    out_fd, out_path = tempfile.mkstemp(suffix=".txt")
    os.close(out_fd)
    proc = subprocess.Popen(
        ["kdialog", "--title", TITLE, "--inputbox", "voice-input e2e", ""],
        stdout=open(out_path, "w"), stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        time.sleep(1.5)
        pointer = VirtualPointer(width, height)
        kbd = VirtualKeyboard()
        try:
            time.sleep(0.4)
            pointer.click_center()
            time.sleep(0.4)
            if mode == "type":
                kbd.type_text(text)
            else:
                inject = Injector()
                try:
                    inject._set_clipboard(text)
                    time.sleep(0.2)
                    kbd.paste()
                finally:
                    inject.close()
            time.sleep(0.2)
            kbd.tap(KEY["enter"])
        finally:
            kbd.close()
            pointer.close()
        for _ in range(50):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        else:
            proc.terminate()
        got = open(out_path).read().strip()
        print(f"    Expected: {text!r}\n    Actual: {got!r}")
        return got == text
    finally:
        if proc.poll() is None:
            proc.kill()
        os.unlink(out_path)


print("=== 1) ASCII typing ===")
r1 = run_case("hello world 123", "type")
print(("PASS" if r1 else "FAIL") + "\n")

print("=== 2) Unicode clipboard paste ===")
r2 = run_case("\u4f60\u597d, \u8fd9\u662f\u4e00\u6b21\u6ce8\u5165\u6d4b\u8bd5.", "paste")
print(("PASS" if r2 else "FAIL") + "\n")

print("Results:", "All passed" if (r1 and r2) else "Some checks failed")
sys.exit(0 if (r1 and r2) else 1)
