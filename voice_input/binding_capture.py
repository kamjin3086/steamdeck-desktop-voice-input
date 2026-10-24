"""Non-blocking candidate capture. This module never writes configuration."""
import time

from . import evdevraw as ev
from .bind import detect_binding
from .hidraw import HidrawReader, find_deck_hidraws


class BindingCapture:
    def __init__(self):
        self.reader = None
        self.devices = []
        self.samples = {}
        try:
            paths = find_deck_hidraws()
            if paths:
                self.reader = HidrawReader(paths)
            self.devices = ev.list_devices()
            # Discard input queued before the dialog began listening.
            for device in self.devices:
                device.read()
            if not self.reader and not self.devices:
                raise RuntimeError('No readable input devices. Connect a controller, check /dev/input and /dev/hidraw access, then reopen this dialog.')
        except Exception:
            self.close()
            raise

    def poll(self):
        now = time.monotonic()
        if self.reader:
            changed = set()
            for path, data in self.reader.poll(0):
                if not data or data[0] != 1:
                    continue
                samples = self.samples.setdefault(path, [])
                samples.append((now, data))
                # Preserve enough history for a normal hold, bounding memory.
                if len(samples) > 2000:
                    del samples[:500]
                changed.add(path)
            for path in changed:
                candidates = detect_binding(self.samples[path])
                if candidates:
                    top = candidates[0]
                    return {'source': 'hidraw', 'report_id': 1,
                            'byte': top['byte'], 'bit': top['bit']}
        for device in self.devices:
            for kind, code, value in device.read():
                # Mouse clicks must remain available for Confirm and Cancel.
                if kind == ev.EV_KEY and value == 1 and not 0x110 <= code <= 0x117:
                    return {'source': 'evdev-key', 'code': code}
        return None

    def close(self):
        if self.reader:
            self.reader.__exit__()
            self.reader = None
        for device in self.devices:
            device.close()
        self.devices = []
