"""E2e loop checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input import models_registry as registry         # noqa: E402
from voice_input.asr import read_wav, transcribe_file      # noqa: E402
from voice_input.inject import Injector                     # noqa: E402
from voice_input.backends import create_backend             # noqa: E402
from voice_input.uinput_kbd import (                        # noqa: E402
    KEY, VirtualKeyboard, VirtualPointer,
)


def screen_size() -> tuple[int, int]:
    try:
        out = subprocess.run(["kscreen-doctor", "--json"], capture_output=True,
                             text=True, timeout=5).stdout
        for output in json.loads(out)["outputs"]:
            if output.get("enabled", True):
                return output["size"]["width"], output["size"]["height"]
    except Exception:  # noqa: BLE001
        pass
    return 1280, 800


wav = os.path.join(registry.model_dir("zh14m"), "test_wavs", "1.wav")
samples = read_wav(wav)
duration = len(samples) / 16000

print("[1/4] Loading model...")
backend = create_backend({"backend": "local", "model": "zh14m"})
print(f"[2/4] Recognizing {os.path.basename(wav)} ({duration:.2f}s) ...")
started = time.monotonic()
text = transcribe_file(wav, backend)
elapsed = time.monotonic() - started
print(f"      「{text}」  {elapsed:.2f}s ({duration / elapsed:.1f}x real time)")
if not text:
    print("FAIL: empty transcript")
    sys.exit(1)

print("[3/4] Opening dialog and injecting...")
width, height = screen_size()
fd, out_path = tempfile.mkstemp(suffix=".txt")
os.close(fd)
proc = subprocess.Popen(
    ["kdialog", "--title", "voice-input-loop", "--inputbox", "voice-input loop", ""],
    stdout=open(out_path, "w"), stderr=subprocess.DEVNULL, start_new_session=True,
)
try:
    time.sleep(1.5)
    pointer = VirtualPointer(width, height)
    kbd = VirtualKeyboard()
    inj = Injector(restore_clipboard=True)
    try:
        time.sleep(0.4)
        pointer.click_center()
        time.sleep(0.4)
        mode = inj.type_or_paste(text)
        print(f"      Injection method = {mode}")
        time.sleep(0.2)
        kbd.tap(KEY["enter"])
    finally:
        inj.close()
        kbd.close()
        pointer.close()
    for _ in range(50):
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    else:
        proc.terminate()
    got = open(out_path).read().strip()
finally:
    if proc.poll() is None:
        proc.kill()
    os.unlink(out_path)

print(f"[4/4] Expected: {text}\n      Actual: {got}」")
ok = got == text
print("Results:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
