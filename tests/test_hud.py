"""Test hud checks."""

from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input.hud import PartialLog, RecorderHUD      # noqa: E402

fails = 0


def check(label, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + str(detail)) if detail else ''}")


class TTY(io.StringIO):
    def isatty(self) -> bool:
        return True



buf = TTY()
hud = RecorderHUD(meter=True, partial=True, stream=buf)
hud.draw(0.1, 0.3, "\u91cd\u70b9")
hud.draw(0.2, 0.6, "\u91cd\u70b9\u5462\u60f3")
out = buf.getvalue()
check("Every frame clears the line", out.count("\r\033[K") == 2, out.count("\r\033[K"))
check("Includes level meter and partial transcript", "… \u91cd\u70b9\u5462\u60f3" in out and "0.6s" in out)
check("Frames overwrite the same line", "\n" not in out)


buf2 = TTY()
hud2 = RecorderHUD(meter=False, partial=True, stream=buf2)
hud2.draw(0.0, 1.0, "same text")
before = len(buf2.getvalue())
hud2.draw(0.0, 1.0, "same text")
check("Identical content is not rewritten", len(buf2.getvalue()) == before)


buf3 = TTY()
hud3 = RecorderHUD(meter=True, partial=True, stream=buf3)
hud3.draw(0.5, 1.2, "abc")
buf3.seek(0)
buf3.truncate()
hud3.done()
check("done clears the line once", buf3.getvalue() == "\r\033[K", repr(buf3.getvalue()))


buf4 = TTY()
hud4 = RecorderHUD(meter=False, partial=True, stream=buf4, width=10)
hud4.draw(0.0, 1.0, "\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u5341\u4e00\u5341\u4e8c")
line = buf4.getvalue().split("\r\033[K")[-1]
check("Long text is truncated on the left", line.startswith("…") and "… …" not in line
      and len(line) <= 14, repr(line))


pipe = io.StringIO()
hud5 = RecorderHUD(meter=True, partial=True, stream=pipe)
hud5.draw(0.1, 0.2, "\u91cd\u70b9")
hud5.draw(0.9, 0.4, "\u91cd\u70b9\u5462")
out5 = pipe.getvalue()
check("Non-TTY output contains no ANSI sequences", "\033" not in out5, repr(out5[:40]))
check("Non-TTY frames use separate lines", out5.count("\n") == 2)


path = "/tmp/voice-input-test-plog.tsv"
if os.path.exists(path):
    os.unlink(path)
log = PartialLog(path)
log.write("partial", "\u91cd\u70b9")
log.write("final", "\u91cd\u70b9\u5462\u60f3\t0.02s")
log.close()
rows = open(path).read().strip().splitlines()
check("Log contains two lines", len(rows) == 2, rows)
check("Log includes timestamps and event names", rows[0].split("\t")[1] == "partial", rows[0])
os.unlink(path)

print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
