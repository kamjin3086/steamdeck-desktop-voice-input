"""Test autostop checks."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input.autostop import SilenceStopper      # noqa: E402

fails = 0


def check(label, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + str(detail)) if detail else ''}")


QUIET, LOUD = 0.001, 0.10


def run(seq, silence_ms=600, speech_peak=0.02):
    """Return whether and when the synthetic peak/time sequence crosses the silence limit."""
    stopper = SilenceStopper(silence_ms=silence_ms, speech_peak=speech_peak)
    for peak, ts in seq:
        if stopper.feed(peak, ts):
            return True, ts
    return False, None



stopped, _ = run([(QUIET, t / 10) for t in range(50)])
check("Continuous silence does not trigger a stop", not stopped)


seq = [(LOUD, t / 10) for t in range(10)] + [(QUIET, 1.0 + t / 10) for t in range(20)]
stopped, ts = run(seq)
check("Silence after speech triggers a stop", stopped)
check("Stops around 1.6 seconds", ts is not None and 1.55 <= ts <= 1.75, ts)


seq = ([(LOUD, t / 10) for t in range(10)]
       + [(QUIET, 1.0 + t / 10) for t in range(3)]
       + [(LOUD, 1.3 + t / 10) for t in range(10)])
stopped, _ = run(seq)
check("300 ms breathing pause does not stop recording", not stopped)


seq = [(LOUD, t / 10) for t in range(10)] + [(QUIET, 1.0 + t / 10) for t in range(20)]
stopped, ts = run(seq, silence_ms=200)
check("Configurable 200 ms threshold", stopped and ts is not None and ts <= 1.35, ts)


seq = [(0.03, t / 10) for t in range(5)] + [(QUIET, 0.5 + t / 10) for t in range(20)]
stopped, _ = run(seq)
check("Silence after noise can still stop recording", stopped)


stopper = SilenceStopper(silence_ms=600)
for t in range(10):
    stopper.feed(LOUD, t / 10)
stopper.reset()
check("reset clears state", not stopper.speech_seen and stopper.silent_since is None)

print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
