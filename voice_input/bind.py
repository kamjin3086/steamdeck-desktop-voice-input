"""Learn HID button bits from clean press/release cycles. Ignore rapidly changing analog bytes and require a minimum hold. CLI binding uses two matching captures before saving."""

from __future__ import annotations

from collections import Counter, defaultdict

from .hidraw import HidrawReader, find_deck_hidraws, load_config, save_config

MIN_HOLD = 0.15
MAX_BYTE_CHANGES = 25


def detect_binding(
    samples: list[tuple[float, bytes]],
    min_hold: float = MIN_HOLD,
    max_byte_changes: int = MAX_BYTE_CHANGES,
) -> list[dict]:
    """Rank HID bits with complete press/release cycles by byte stability and repeated holds."""
    byte_changes: Counter[int] = Counter()
    down_at: dict[tuple[int, int], float] = {}
    cycles: defaultdict[tuple[int, int], list[float]] = defaultdict(list)

    prev: bytes | None = None
    for ts, data in samples:
        if prev is None or len(prev) != len(data):
            prev = data
            continue
        for idx, (a, b) in enumerate(zip(prev, data)):
            if a == b:
                continue
            byte_changes[idx] += 1
            diff = a ^ b
            for bit in range(8):
                if not (diff >> bit) & 1:
                    continue
                key = (idx, bit)
                if (b >> bit) & 1:
                    down_at[key] = ts
                else:
                    started = down_at.pop(key, None)
                    if started is not None and ts - started >= min_hold:
                        cycles[key].append(ts - started)
        prev = data

    results = []
    for (idx, bit), holds in cycles.items():
        if byte_changes[idx] > max_byte_changes:
            continue
        results.append({
            "byte": idx,
            "bit": bit,
            "byte_changes": byte_changes[idx],
            "holds": [round(h, 2) for h in holds],
        })
    results.sort(key=lambda r: (r["byte_changes"], -len(r["holds"])))
    return results


def capture(seconds: float = 6.0, report_id: int | None = 1) -> list[tuple[float, bytes]]:
    import time

    paths = find_deck_hidraws()
    if not paths:
        raise RuntimeError("No Valve Steam Deck hidraw nodes found")
    samples: list[tuple[float, bytes]] = []
    t0 = time.monotonic()
    with HidrawReader(paths) as reader:
        while time.monotonic() - t0 < seconds:
            for _path, data in reader.poll(0.02):
                if report_id is not None and data[0] != report_id:
                    continue
                samples.append((time.monotonic() - t0, data))
    return samples


def interactive_bind(seconds: float = 6.0) -> dict | None:
    """Capture twice, require matching candidates, then save the binding."""
    print(f"Step 1: within the next {seconds:.0f} seconds, hold the desired button for about 1 second, then release.")
    input("Press Enter to begin...")
    first = detect_binding(capture(seconds))
    if not first:
        print("No button detected. Check the controller connection and Steam Input mapping.")
        return None
    top = first[0]
    print(f"  Candidate: byte {top['byte']} bit {top['bit']}(held for {top['holds']} seconds)")
    if len(first) > 1:
        print(f"  There are {len(first) - 1} other candidate bits; a second capture will disambiguate them.")

    print(f"\nStep 2: press the same button again (within {seconds:.0f} seconds).")
    input("Press Enter to begin...")
    second = detect_binding(capture(seconds))
    matched = [r for r in second
               if r["byte"] == top["byte"] and r["bit"] == top["bit"]]
    if not matched:
        print("The captures did not match; nothing was saved. Run bind again.")
        print("Second capture candidates: ", second[:3])
        return None

    cfg = load_config()
    cfg["trigger"] = {"source": "hidraw", "report_id": 1,
                      "byte": top["byte"], "bit": top["bit"]}
    cfg["note"] = f"Learned binding, byte {top['byte']} bit {top['bit']}"
    save_config(cfg)
    print(f"\nSaved to ~/.config/voice-input/config.json: "
          f"byte {top['byte']} bit {top['bit']}")
    return cfg["trigger"]


def describe(cfg: dict) -> str:
    t = cfg.get("trigger") or {}
    if t.get("source") == "hidraw":
        return f"hidraw report{t.get('report_id', 1)} byte{t['byte']} bit{t['bit']}"
    if t.get("source") in ("evdev-abs", "evdev-key"):
        return f"{t['source']} code {hex(t['code'])}"
    return "Unbound"


def binding_label(trigger: dict | None) -> str:
    """Human label shared by the desktop and installer."""
    trigger = trigger or {}
    if trigger.get("source") == "hidraw" and trigger.get("report_id", 1) == 1:
        known = {(9, 7): "L5 (left rear button)", (13, 1): "L4 (left rear button)"}
        name = known.get((trigger.get("byte"), trigger.get("bit")))
        if name:
            return name
    if trigger.get("source") == "evdev-key":
        code = trigger["code"]
        names = {1: "Esc", 28: "Enter", 57: "Space", 87: "F11", 88: "F12"}
        names.update({59 + index: f"F{index + 1}" for index in range(10)})
        return names.get(code, f"Keyboard/controller key {hex(code)}")
    return describe({"trigger": trigger})
