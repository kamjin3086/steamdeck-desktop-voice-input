"""Construct a pollable trigger source from hidraw, evdev key, or evdev axis configuration."""

from __future__ import annotations

from .hidraw import HidrawButton
from .trigger import TriggerWatcher


def make_source(trigger: dict, press_threshold: float = 0.30,
                release_threshold: float = 0.12):
    source = (trigger or {}).get("source")
    if source == "hidraw":
        return HidrawButton(
            byte_index=int(trigger["byte"]),
            bit=int(trigger["bit"]),
            report_id=int(trigger.get("report_id", 1)),
        )
    if source == "evdev-abs":
        return TriggerWatcher(
            abs_codes=(int(trigger["code"]),),
            press_threshold=press_threshold,
            release_threshold=release_threshold,
        )
    if source == "evdev-key":
        return TriggerWatcher(
            key_codes=(int(trigger["code"]),),
            press_threshold=press_threshold,
            release_threshold=release_threshold,
        )
    raise ValueError(f"Unknown trigger source in config: {trigger!r}(run bind first)")
