"""Test bind detect checks."""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input.bind import detect_binding      # noqa: E402

RATE = 250.0
DURATION = 8.0
ANALOG = [4, 5, 6, 20, 48, 52, 55]
COUNTER = [61, 62]


def make_reports() -> list[tuple[float, bytes]]:
    random.seed(7)
    reports = []
    n = int(RATE * DURATION)
    for i in range(n):
        ts = i / RATE
        data = bytearray(64)
        data[0] = 0x01                     # report id
        for idx in ANALOG:
            data[idx] = random.randrange(256)
        for idx in COUNTER:
            data[idx] = (i * 7) & 0xFF

        if 1.0 <= ts < 2.0 or 3.0 <= ts < 4.0:
            data[9] |= 0x80

        if 5.0 <= ts < 5.7:
            data[13] |= 0x02

        if 6.5 <= ts < 6.52:
            data[17] |= 0x01
        reports.append((ts, bytes(data)))
    return reports


fails = 0


def check(label, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")


found = detect_binding(make_reports())
print("Detected candidates:")
for r in found:
    print(f"  byte {r['byte']:2d} bit {r['bit']} held for {r['holds']} "
          f"(byte changes {r['byte_changes']} times)")

keys = [(r["byte"], r["bit"]) for r in found]
check("Finds L5 at byte9 bit7", (9, 7) in keys)
check("Finds L4 at byte13 bit1", (13, 1) in keys)
check("L5 has two press cycles", any((r["byte"], r["bit"]) == (9, 7)
                              and len(r["holds"]) == 2 for r in found))
check("20 ms bounce is ignored", all((r["byte"], r["bit"]) != (17, 0) for r in found))
check("Analog bytes are not treated as buttons",
      all(r["byte"] not in ANALOG + COUNTER for r in found))
check("Most stable byte ranks first", found[0]["byte_changes"] <= found[-1]["byte_changes"])

print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
