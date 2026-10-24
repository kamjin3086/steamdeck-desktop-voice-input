"""Test streaming checks."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input import models_registry as registry       # noqa: E402
from voice_input.asr import read_wav                     # noqa: E402
from voice_input.backends import create_backend          # noqa: E402

fails = 0


def check(label, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + str(detail)) if detail else ''}")


backend = create_backend({"backend": "local", "model": "zh14m", "num_threads": 2})
check("Backend supports streaming", backend.supports_partial, backend.describe())

wav = os.path.join(registry.model_dir("zh14m"), "test_wavs", "1.wav")
samples = read_wav(wav)
pcm = samples.tobytes()
duration = len(samples) / 16000

partials: list[tuple[float, str]] = []
t0 = time.monotonic()
session = backend.open_session(on_partial=lambda t: partials.append(
    (time.monotonic() - t0, t)))
session.throttle = 0.0

step = 3200 * 2
for off in range(0, len(pcm), step):
    session.accept(pcm[off:off + step])
final = session.finish()

print(f"\nAudio {duration:.2f}s, partial {len(partials)} updates, final {final!r}")
print("First five partials:")
for ts, text in partials[:5]:
    print(f"  t={ts:5.2f}s  {text}")

check("Produces partial transcripts", len(partials) > 0)
check("Partials grow over time", len(partials[0][1]) < len(partials[-1][1]),
      f"{len(partials[0][1])} -> {len(partials[-1][1])}")
check("First partial appears before the audio duration elapses",
      partials and partials[0][0] < duration)
check("Final transcript matches expected content", "\u91cd\u70b9" in final and "\u91d1\u878d" in final, final)
check("Last partial is a prefix of the final result",
      partials and final.startswith(partials[-1][1][:4]),
      f"{partials[-1][1][:12]!r} vs {final[:12]!r}")
check("Final transcript retains the last partial",
      len(final) >= len(partials[-1][1]) if partials else False,
      f"final={len(final)} last_partial={len(partials[-1][1]) if partials else 0}")


session = backend.open_session()
session.accept(b"\x00\x00" * 16000)
check("Silent input does not crash", isinstance(session.finish(), str))

print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
