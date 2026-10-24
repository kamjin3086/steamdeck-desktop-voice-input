"""Smoke checks."""

from __future__ import annotations

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input import evdevraw as ev                     # noqa: E402
from voice_input.inject import Injector                    # noqa: E402
from voice_input.uinput_kbd import KEY, VirtualKeyboard    # noqa: E402

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    ok = ok and cond
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")


def find_node(name_prefix: str) -> str | None:
    txt = open("/proc/bus/input/devices").read()
    for block in txt.strip().split("\n\n"):
        if f'Name="{name_prefix}' in block:
            for line in block.splitlines():
                if line.startswith("H: Handlers="):
                    for token in line.split("=", 1)[1].split():
                        if token.startswith("event"):
                            return "/dev/input/" + token
    return None


print("1) Trigger devices")
triggers = [d for d in ev.list_devices() if d.trigger_axes()]
check("Finds trigger-capable devices", bool(triggers), ", ".join(
    f"{d.path}({d.name}) {[hex(t) for t in d.trigger_axes()]}" for d in triggers))
for d in triggers:
    d.close()

print("\n2) uinput virtual keyboard")
kbd = VirtualKeyboard()
try:
    time.sleep(0.4)
    node = find_node("voice-input")
    check("Virtual keyboard appears in the kernel", node is not None, str(node))
    if node:
        try:
            reader = ev.Device(node)
        except PermissionError:
            print("[SKIP] Cannot read the virtual device (session ACL unavailable). "
                  "Run tests/e2e_inject.py to verify desktop injection.")
            reader = None
    if node and reader:


        reader.read()
        kbd.tap(KEY["a"])
        time.sleep(0.2)
        events = [(t, c, v) for (t, c, v) in reader.read() if t == ev.EV_KEY]
        check("Injected key events can be read back", (ev.EV_KEY, KEY["a"], 1) in events
              and (ev.EV_KEY, KEY["a"], 0) in events, str(events))
        reader.close()
finally:
    kbd.close()

print("\n3) Clipboard (Klipper D-Bus)")
inj = Injector(restore_clipboard=True, debug=True)
try:
    check("Klipper is available", bool(inj._klipper))
    sentinel = "voice-input-\u526a\u8d34\u677f-\u6d4b\u8bd5-42"
    before = inj._get_clipboard()
    inj._set_clipboard(sentinel)
    time.sleep(0.3)
    check("Clipboard read matches write", inj._get_clipboard() == sentinel)
    if before is not None:
        inj._set_clipboard(before)
    check("Non-ASCII detection", not Injector.is_ascii("\u4f60\u597dabc"))
    check("ASCII detection", Injector.is_ascii("hello world!"))
finally:
    inj.close()

print("\n4) Input method processes (informational)")
out = subprocess.run(["pgrep", "-a", "fcitx5|ibus-daemon"], capture_output=True,
                     text=True).stdout.strip()
print("   ", out or "None (clipboard injection does not require an input method)")

print("\nResults:", "All passed" if ok else "Some checks failed")
sys.exit(0 if ok else 1)
