"""Read raw Steam Deck HID reports. Rear buttons are available through hidraw rather than ordinary evdev button events. Device access depends on the desktop session ACLs."""

from __future__ import annotations

import json
import os
import select
import struct
import time

CONFIG_DIR = os.path.expanduser("~/.config/voice-input")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

VALVE_VID, DECK_PID = 0x28DE, 0x1205


def _hid_id(path: str) -> str:
    node = os.path.basename(path)
    uevent = f"/sys/class/hidraw/{node}/device/uevent"
    try:
        for line in open(uevent):
            if line.startswith("HID_ID="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _hid_name(path: str) -> str:
    node = os.path.basename(path)
    try:
        return open(f"/sys/class/hidraw/{node}/device/uevent").read()
    except OSError:
        return ""


def find_deck_hidraws() -> list[str]:
    """Find Valve Steam Deck hidraw nodes by vendor/product ID."""
    found = []
    for entry in sorted(os.listdir("/dev")):
        if not entry.startswith("hidraw"):
            continue
        path = os.path.join("/dev", entry)
        hid_id = _hid_id(path).lower()
        # HID_ID=0003:000028DE:00001205
        if "28de" in hid_id and "1205" in hid_id:
            found.append(path)
    return found


class HidrawReader:
    """Poll raw HID reports without blocking."""

    def __init__(self, paths: list[str] | None = None):
        self.paths = paths or find_deck_hidraws()
        self.fds: dict[int, str] = {}
        for path in self.paths:
            self.fds[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path

    def __enter__(self) -> "HidrawReader":
        return self

    def __exit__(self, *exc) -> None:
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self.fds.clear()

    def poll(self, timeout: float = 0.05) -> list[tuple[str, bytes]]:
        if not self.fds:
            time.sleep(timeout)
            return []
        try:
            readable, _, _ = select.select(list(self.fds), [], [], timeout)
        except InterruptedError:
            return []
        reports = []
        for fd in readable:
            try:
                data = os.read(fd, 64)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError:
                continue
            if data:
                reports.append((self.fds[fd], data))
        return reports



def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


class HidrawButton:
    """Convert a report byte and bit into debounced press/release edges. Offsets include the report ID byte."""

    def __init__(self, byte_index: int, bit: int, report_id: int | None = None,
                 debounce: float = 0.03):
        self.byte_index = byte_index
        self.bit = bit
        self.report_id = report_id
        self.debounce = debounce
        self.pressed = False
        self._raw = False
        self._changed_at = 0.0
        self._reader = HidrawReader()

    def __enter__(self) -> "HidrawButton":
        return self

    def __exit__(self, *exc) -> None:
        self._reader.__exit__(*exc)

    def poll(self, timeout: float = 0.05) -> list[str]:
        edges: list[str] = []
        mask = 1 << self.bit
        for _path, data in self._reader.poll(timeout):
            if self.report_id is not None and data[0] != self.report_id:
                continue
            if self.byte_index >= len(data):
                continue
            down = bool(data[self.byte_index] & mask)
            if down != self._raw:
                self._raw = down
                self._changed_at = time.monotonic()

        if self._raw != self.pressed and \
                time.monotonic() - self._changed_at >= self.debounce:
            self.pressed = self._raw
            edges.append("press" if self.pressed else "release")
        return edges



def learn(duration: float, out_path: str) -> int:
    """Record changing HID bytes as timestamped TSV for diagnostics."""
    paths = find_deck_hidraws()
    if not paths:
        print("No Valve Steam Deck hidraw nodes found")
        return 1
    print(f"Watching {paths}")
    prev: dict[str, bytes] = {}
    t0 = time.monotonic()
    with HidrawReader(paths) as reader, open(out_path, "w") as out:
        out.write("# path\treport_id\tlen\thex\n")
        first_seen = set()
        while time.monotonic() - t0 < duration:
            for path, data in reader.poll(0.02):
                if path not in first_seen:
                    first_seen.add(path)
                    out.write(f"# {path}\treport_id={data[0]}\tlen={len(data)}\t"
                              f"{data.hex()}\n")
                old = prev.get(path)
                prev[path] = data
                if not old or len(old) != len(data):
                    continue
                ts = time.monotonic() - t0
                for i, (a, b) in enumerate(zip(old, data)):
                    if a != b:
                        out.write(f"{ts:.3f}\t{data[0]}\t{i}\t{a:#04x}\t{b:#04x}\n")
    print(f"Written to {out_path}")
    return 0
