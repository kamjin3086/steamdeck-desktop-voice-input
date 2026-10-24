"""Linux uinput keyboard and absolute pointer, implemented using the Python standard library."""

from __future__ import annotations

import fcntl
import os
import struct
import time

from .evdevraw import EV_KEY, EV_SYN

UI_DEV_SETUP = (1 << 30) | (92 << 16) | (ord("U") << 8) | 3
UI_DEV_CREATE = (0 << 30) | (0 << 16) | (ord("U") << 8) | 1
UI_DEV_DESTROY = (0 << 30) | (0 << 16) | (ord("U") << 8) | 2
UI_SET_EVBIT = (1 << 30) | (4 << 16) | (ord("U") << 8) | 100
UI_SET_KEYBIT = (1 << 30) | (4 << 16) | (ord("U") << 8) | 101

# linux/input-event-codes.h
KEY = {
    "esc": 1, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9,
    "9": 10, "0": 11, "minus": 12, "equal": 13, "backspace": 14, "tab": 15,
    "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23,
    "o": 24, "p": 25, "leftbrace": 26, "rightbrace": 27, "enter": 28,
    "leftctrl": 29, "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35,
    "j": 36, "k": 37, "l": 38, "semicolon": 39, "apostrophe": 40, "grave": 41,
    "leftshift": 42, "backslash": 43, "z": 44, "x": 45, "c": 46, "v": 47,
    "b": 48, "n": 49, "m": 50, "comma": 51, "dot": 52, "slash": 53,
    "rightshift": 54, "kpasterisk": 55, "leftalt": 56, "space": 57,
    "capslock": 58, "f1": 59, "home": 102, "up": 103, "pageup": 104,
    "left": 105, "right": 106, "end": 107, "down": 108, "pagedown": 109,
    "insert": 110, "delete": 111, "rightctrl": 97, "rightalt": 100,
    "leftmeta": 125,
}


_CHARS: dict[str, tuple[int, bool]] = {}
for _c in "1234567890":
    _CHARS[_c] = (KEY[_c], False)
for _c, _s in zip("!@#$%^&*()", "1234567890"):
    _CHARS[_c] = (KEY[_s], True)
for _c in "abcdefghijklmnopqrstuvwxyz":
    _CHARS[_c] = (KEY[_c], False)
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _CHARS[_c] = (KEY[_c.lower()], True)
_CHARS.update({
    " ": (KEY["space"], False), "\n": (KEY["enter"], False),
    "\t": (KEY["tab"], False), "-": (KEY["minus"], False),
    "_": (KEY["minus"], True), "=": (KEY["equal"], False),
    "+": (KEY["equal"], True), "[": (KEY["leftbrace"], False),
    "{": (KEY["leftbrace"], True), "]": (KEY["rightbrace"], False),
    "}": (KEY["rightbrace"], True), ";": (KEY["semicolon"], False),
    ":": (KEY["semicolon"], True), "'": (KEY["apostrophe"], False),
    '"': (KEY["apostrophe"], True), "`": (KEY["grave"], False),
    "~": (KEY["grave"], True), "\\": (KEY["backslash"], False),
    "|": (KEY["backslash"], True), ",": (KEY["comma"], False),
    "<": (KEY["comma"], True), ".": (KEY["dot"], False),
    ">": (KEY["dot"], True), "/": (KEY["slash"], False),
    "?": (KEY["slash"], True), "!": (KEY["1"], True),
})


class VirtualKeyboard:
    def __init__(self, name: str = "voice-input virtual keyboard"):
        self.fd = os.open("/dev/uinput", os.O_RDWR | os.O_NONBLOCK)
        for ev in (EV_SYN, EV_KEY):
            fcntl.ioctl(self.fd, UI_SET_EVBIT, ev)
        for code in set(KEY.values()):
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, code)
        # struct uinput_setup { input_id(8) name[80] ff_effects_max(4) }
        setup = struct.pack(
            "HHHH80sI", 0x03, 0x1209, 0x0001, 1, name.encode()[:79], 0
        )
        fcntl.ioctl(self.fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(0.15)


    def _emit(self, etype: int, code: int, value: int) -> None:
        os.write(self.fd, struct.pack("llHHi", 0, 0, etype, code, value))

    def _syn(self) -> None:
        self._emit(EV_SYN, 0, 0)

    def tap(self, code: int, modifiers: tuple[int, ...] = (), delay: float = 0.008) -> None:
        for m in modifiers:
            self._emit(EV_KEY, m, 1)
        self._emit(EV_KEY, code, 1)
        self._syn()
        time.sleep(delay)
        self._emit(EV_KEY, code, 0)
        for m in reversed(modifiers):
            self._emit(EV_KEY, m, 0)
        self._syn()
        time.sleep(delay)


    def type_text(self, text: str, delay: float = 0.008) -> None:
        """Type supported ASCII characters; raise ValueError for unsupported input."""
        shift = KEY["leftshift"]
        for ch in text:
            if ch not in _CHARS:
                raise ValueError(f"uinput cannot type character {ch!r}(use clipboard paste for non-ASCII text)")
            code, need_shift = _CHARS[ch]
            self.tap(code, (shift,) if need_shift else (), delay)

    def paste(self, delay: float = 0.02) -> None:
        """Ctrl+V"""
        self.tap(KEY["v"], (KEY["leftctrl"],), delay)

    def close(self) -> None:
        try:
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        finally:
            os.close(self.fd)



UI_SET_ABSBIT = (1 << 30) | (4 << 16) | (ord("U") << 8) | 103
UI_ABS_SETUP = (1 << 30) | (28 << 16) | (ord("U") << 8) | 4
ABS_X, ABS_Y = 0x00, 0x01
BTN_LEFT = 0x110


class VirtualPointer:
    """Absolute uinput pointer for explicit desktop interaction tests."""

    def __init__(self, width: int = 1280, height: int = 800,
                 name: str = "voice-input virtual pointer"):
        self.width, self.height = width, height
        self.fd = os.open("/dev/uinput", os.O_RDWR | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_SYN)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, 3)  # EV_ABS
        fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_LEFT)
        for code, maximum in ((ABS_X, width - 1), (ABS_Y, height - 1)):
            fcntl.ioctl(self.fd, UI_SET_ABSBIT, code)
            # struct uinput_abs_setup { __u16 code; pad; input_absinfo(6*i) }
            fcntl.ioctl(self.fd, UI_ABS_SETUP,
                        struct.pack("<Hxx6i", code, 0, 0, maximum, 0, 0, 0))
        setup = struct.pack("HHHH80sI", 0x03, 0x1209, 0x0002, 1,
                            name.encode()[:79], 0)
        fcntl.ioctl(self.fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(0.4)

    def move(self, x: int, y: int) -> None:
        self._emit(3, ABS_X, int(x))
        self._emit(3, ABS_Y, int(y))
        self._emit(EV_SYN, 0, 0)
        time.sleep(0.03)

    def click(self) -> None:
        self._emit(EV_KEY, BTN_LEFT, 1)
        self._emit(EV_SYN, 0, 0)
        time.sleep(0.05)
        self._emit(EV_KEY, BTN_LEFT, 0)
        self._emit(EV_SYN, 0, 0)
        time.sleep(0.08)

    def click_center(self) -> None:
        self.move(self.width // 2, self.height // 2)
        self.click()

    def _emit(self, etype: int, code: int, value: int) -> None:
        os.write(self.fd, struct.pack("llHHi", 0, 0, etype, code, value))

    def close(self) -> None:
        try:
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        finally:
            os.close(self.fd)
