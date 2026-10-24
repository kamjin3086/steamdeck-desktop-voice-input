"""Read Linux input devices using standard-library ioctl calls and non-blocking input_event parsing."""

from __future__ import annotations

import fcntl
import os
import struct

EV_SYN, EV_KEY, EV_REL, EV_ABS, EV_MSC = 0, 1, 2, 3, 4


INPUT_EVENT = struct.Struct("llHHi")
INPUT_EVENT_SIZE = INPUT_EVENT.size


BTN_TL, BTN_TR = 0x136, 0x137
BTN_TL2, BTN_TR2 = 0x138, 0x139
ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
ABS_BRAKE, ABS_GAS = 0x0A, 0x09


def _IOC(direction: int, type_: str, nr: int, size: int) -> int:
    return (direction << 30) | (size << 16) | (ord(type_) << 8) | nr


def _ioc_read(type_: str, nr: int, size: int) -> int:
    return _IOC(2, type_, nr, size)


def device_name(fd: int, size: int = 256) -> str:
    buf = bytearray(size)
    try:
        fcntl.ioctl(fd, _ioc_read("E", 0x06, size), buf, True)
    except OSError:
        return ""
    return buf.split(b"\0")[0].decode(errors="replace")


def _bits(fd: int, ev_type: int, nbytes: int = 96) -> set[int]:
    buf = bytearray(nbytes)
    try:
        fcntl.ioctl(fd, _ioc_read("E", 0x20 + ev_type, nbytes), buf, True)
    except OSError:
        return set()
    out = set()
    for byte_i, byte in enumerate(buf):
        if not byte:
            continue
        for bit in range(8):
            if byte >> bit & 1:
                out.add(byte_i * 8 + bit)
    return out


def abs_info(fd: int, code: int) -> tuple[int, int, int, int]:
    """Return value, minimum, maximum, and fuzz from EVIOCGABS."""
    buf = bytearray(24)  # struct input_absinfo = 6 * __s32
    try:
        fcntl.ioctl(fd, _ioc_read("E", 0x40 + code, 24), buf, True)
    except OSError:
        return (0, 0, 0, 0)
    value, minimum, maximum, fuzz, _flat, _res = struct.unpack("6i", buf)
    return value, minimum, maximum, fuzz


class Device:
    """A non-blocking /dev/input/event device."""

    def __init__(self, path: str):
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.name = device_name(self.fd)
        self.keys = _bits(self.fd, EV_KEY)
        self.abs = _bits(self.fd, EV_ABS)
        self.abs_ranges = {code: abs_info(self.fd, code)[1:3] for code in self.abs}

    def __repr__(self) -> str:
        return f"<Device {self.path} {self.name!r}>"

    @property
    def is_gamepad(self) -> bool:
        return bool(self.abs & {ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ})

    def trigger_axes(self) -> list[int]:
        """Return axis codes that could represent analog triggers."""
        return sorted(self.abs & {ABS_Z, ABS_RZ, ABS_BRAKE, ABS_GAS})

    def read(self) -> list[tuple[int, int, int]]:
        try:
            data = os.read(self.fd, INPUT_EVENT_SIZE * 128)
        except (BlockingIOError, InterruptedError):
            return []
        except OSError:
            return []
        events = []
        for off in range(0, len(data) - INPUT_EVENT_SIZE + 1, INPUT_EVENT_SIZE):
            _s, _us, etype, code, value = INPUT_EVENT.unpack_from(data, off)
            events.append((etype, code, value))
        return events

    def close(self) -> None:
        try:
            os.close(self.fd)
        except OSError:
            pass


def list_devices() -> list[Device]:
    """Enumerate readable evdev nodes, excluding our virtual input devices."""
    devices = []
    base = "/dev/input"
    if not os.path.isdir(base):
        return devices
    for entry in sorted(os.listdir(base)):
        if not entry.startswith("event"):
            continue
        try:
            dev = Device(os.path.join(base, entry))
        except OSError:
            continue
        if dev.name.startswith("voice-input"):
            dev.close()
            continue
        devices.append(dev)
    return devices
