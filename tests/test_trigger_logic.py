"""Test trigger logic checks."""

from __future__ import annotations

import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input import evdevraw as ev
from voice_input import trigger as trigger_mod
from voice_input.trigger import TriggerWatcher


class FakePad:
    """Fake evdev device controlled directly by the test."""

    def __init__(self):
        self.path = "/dev/input/eventFAKE"
        self.name = "Fake Pad"
        self.r, self.w = os.pipe()
        os.set_blocking(self.r, False)
        self.fd = self.r
        self.abs = {ev.ABS_Z}
        self.abs_ranges = {ev.ABS_Z: (0, 255)}
        self.keys = set()
        self.value = 0

    def read(self):
        try:
            data = os.read(self.fd, ev.INPUT_EVENT_SIZE * 64)
        except (BlockingIOError, InterruptedError):
            return []
        out = []
        for off in range(0, len(data) - ev.INPUT_EVENT_SIZE + 1, ev.INPUT_EVENT_SIZE):
            _s, _us, t, c, v = ev.INPUT_EVENT.unpack_from(data, off)
            out.append((t, c, v))
        return out

    def close(self):
        os.close(self.r)
        os.close(self.w)


fails = 0


def check(label, cond):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


pad = FakePad()

trigger_mod.ev.abs_info = lambda fd, code: (pad.value, 0, 255, 0)

w = TriggerWatcher(press_threshold=0.30, release_threshold=0.12, release_grace=0.05)
w.devices = [pad]

check("Initially released", w.poll(0.01) == [] and not w.pressed)

pad.value = 20
check("Light touch does not trigger", w.poll(0.01) == [] and not w.pressed)

pad.value = 200
edges = w.poll(0.01)
check(f"Press produces a press edge {edges}", edges == ["press"])
check("Repeated pressed values do not retrigger", w.poll(0.01) == [])

pad.value = 120
check("Middle values keep the button pressed", w.poll(0.01) == [] and w.pressed)

pad.value = 10
check("Release remains inside grace period", w.poll(0.01) == [] and w.pressed)
time.sleep(0.07)
check("Release edge after grace period", w.poll(0.01) == ["release"] and not w.pressed)

pad.value = 255
check("Full press can retrigger", w.poll(0.01) == ["press"])


pad.value = 0
w.poll(0.01)
pad.value = 255
time.sleep(0.02)
check("Bounce does not cause a release", w.poll(0.01) == [] and w.pressed)

pad.close()
print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
