# Configuration

English | [简体中文](zh-CN/CONFIG.md)

Path: `~/.config/voice-input/config.json`. Precedence is command-line options over saved settings over defaults. Run `./run.sh --help` for current CLI flags, or `./run.sh --config` to inspect effective settings. Redact API keys before sharing configuration output.

```json
{
  "trigger": {"source": "hidraw", "report_id": 1, "byte": 9, "bit": 7},
  "asr": {"backend": "local", "model": "sensevoice", "num_threads": 2, "language": "auto"},
  "auto_stop": {"enabled": true, "silence_ms": 600, "threshold": 0.02}
}
```

## Activation button

The installer sets L5 only if no binding exists. The GUI rebinding dialog saves a replacement only after Confirm. Cancel preserves the old binding.

| Source | Settings | Purpose |
| --- | --- | --- |
| `hidraw` | `report_id`, `byte`, `bit` | Raw Deck buttons, including rear buttons |
| `evdev-key` | Linux input `code` | Keyboard/controller key |
| `evdev-abs` | Linux axis `code` | Analog trigger with press/release thresholds |

Observed mappings on the original tested Deck layout: L5 = report 1, byte 9, bit 7; L4 = report 1, byte 13, bit 1. Firmware and Steam Input may expose different layouts. Use the dialog rather than guessing. The CLI `./run.sh bind` is a separate two-capture HID-learning workflow requiring terminal input.

Examples: `./run.sh --trigger-key 0x44` uses F10; `./run.sh calibrate` prints trigger state. Evdev uses Linux input codes, not Qt key values or X11 keycodes.

## Local recognition

| Setting | Default | Meaning |
| --- | --- | --- |
| `backend` | `local` | Use sherpa-onnx |
| `model` | `sensevoice` | Entry in models.json |
| `num_threads` | `2` | CPU decoding threads |
| `language` | `auto` | Automatic language detection; legacy Whisper/cloud may use explicit hints |
| `provider` | `cpu` | sherpa-onnx execution provider |

Installation uses SenseVoice without a model prompt. **Change model / languages** in the GUI offers three groups, visible progress, cancellation, and persistence only after a successful load. Repeat installation keeps the selected model. `--model` and `--language` remain advanced CLI overrides.

## Silence and segment limits

`auto_stop.enabled=true` enables silence segmentation after speech. `silence_ms=600` controls pause duration and `threshold=0.02` is the normalized peak threshold. Increase silence_ms to 1000–1500 for longer pauses, or increase threshold in a noisy room.

Silence segmentation finalizes and inserts text, then starts a new session while the button stays held. Disabling it waits for release or the 60-second segment cap. The cap still rotates sessions while held to bound memory. The minimum segment duration is 0.35 seconds. New holds start after activation without pre-activation audio; input polling and model decoding determine practical latency.

## Cloud and LAN

See [CLOUD_ASR.md](CLOUD_ASR.md). Backend settings include `preset`, `base_url`, `model`, `language`, `timeout` (default 30 seconds), `response_format` (`json` or `text`), and optional `endpoint`. Prefer a preset's API-key environment variable to an inline `api_key`.

## Files

| Location | Contents |
| --- | --- |
| Checkout `.venv/` | Python runtime dependencies |
| Checkout `models/` | Downloaded models |
| `~/.config/voice-input/config.json` | User configuration |
| Desktop and user application directory `voice-input.desktop` | GUI shortcut |
| User runtime directory `voice-input-<checkout hash>/` | Per-checkout lock and IPC socket |
| Explicit `--partial-log PATH` | Optional transcript log |

The GUI retains a bounded log in memory. Diagnostic logs and any recordings you create may contain private speech.

## Feedback and closing

Tones are off by default. Optional `--beep` plays cues outside the capture boundaries; the release tone follows finalization. Window X exits the app; minimize it to keep it running.
