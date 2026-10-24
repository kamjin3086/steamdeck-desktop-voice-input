"""Watch Linux keys and trigger axes with hysteresis and release debounce. Steam Input mappings determine which events are exposed."""

from __future__ import annotations

import select
import time

from . import evdevraw as ev


DEFAULT_ABS_CODES = (ev.ABS_Z,)
DEFAULT_KEY_CODES = ()


class TriggerWatcher:
    """Discover devices and emit trigger edges using thresholds and release grace."""

    def __init__(
        self,
        abs_codes: tuple[int, ...] = DEFAULT_ABS_CODES,
        key_codes: tuple[int, ...] = DEFAULT_KEY_CODES,
        press_threshold: float = 0.35,
        release_threshold: float = 0.15,
        release_grace: float = 0.05,
        device_paths: list[str] | None = None,
        verbose: bool = False,
    ):
        self.abs_codes = abs_codes
        self.key_codes = key_codes
        self.press_threshold = press_threshold
        self.release_threshold = release_threshold
        self.release_grace = release_grace
        self.verbose = verbose
        self.devices: list[ev.Device] = []
        self._paths = device_paths
        self.pressed = False
        self.value = 0.0
        self._below_since: float | None = None
        self._key_down: set[tuple[str, int]] = set()


    def _discover(self) -> None:
        for dev in ev.list_devices():
            abs_hit = bool(set(self.abs_codes) & dev.abs)
            key_hit = bool(set(self.key_codes) & dev.keys)
            if not (abs_hit or key_hit):
                dev.close()
                continue
            if self._paths and dev.path not in self._paths:
                dev.close()
                continue
            self.devices.append(dev)
            if self.verbose:
                print(f"[trigger] Watching {dev.path} {dev.name!r}", flush=True)

    def __enter__(self) -> "TriggerWatcher":
        self._discover()
        if not self.devices:
            raise RuntimeError(
                "No suitable trigger device. Check the controller connection and Steam Input mapping."
            )
        return self

    def __exit__(self, *exc) -> None:
        for dev in self.devices:
            dev.close()
        self.devices.clear()


    def _norm(self, dev: ev.Device, code: int, raw: int) -> float:
        lo, hi = dev.abs_ranges.get(code, (0, 255))
        span = (hi - lo) or 1
        return max(0.0, min(1.0, (raw - lo) / span))

    def poll(self, timeout: float = 0.1) -> list[str]:
        """Return press/release edges observed during this polling interval."""
        edges: list[str] = []
        if not self.devices:
            time.sleep(timeout)
            return edges
        fds = [d.fd for d in self.devices]
        try:
            readable, _, _ = select.select(fds, [], [], timeout)
        except InterruptedError:
            return edges

        best = 0.0
        for dev in self.devices:
            if dev.fd in readable:
                for etype, code, value in dev.read():
                    if etype == ev.EV_KEY and code in self.key_codes:
                        if value == 1:
                            self._key_down.add((dev.path, code))
                        elif value == 0:
                            self._key_down.discard((dev.path, code))


            for code in self.abs_codes:
                if code not in dev.abs:
                    continue
                val, _lo, _hi, _fuzz = ev.abs_info(dev.fd, code)
                best = max(best, self._norm(dev, code, val))
        self.value = best
        if self._key_down:
            self.value = max(self.value, 1.0)

        now = time.monotonic()
        if not self.pressed:
            if self.value >= self.press_threshold:
                self.pressed = True
                self._below_since = None
                edges.append("press")
        else:
            if self.value <= self.release_threshold:
                if self._below_since is None:
                    self._below_since = now
                elif now - self._below_since >= self.release_grace:
                    self.pressed = False
                    self._below_since = None
                    edges.append("release")
            else:
                self._below_since = None
        return edges
