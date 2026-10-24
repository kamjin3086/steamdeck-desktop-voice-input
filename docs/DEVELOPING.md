# Development

English | [简体中文](zh-CN/DEVELOPING.md)

Python 3.10+ on Linux; SteamOS Desktop Mode is the target. Runtime dependencies are sherpa-onnx and PySide6-Essentials; input IO, HTTP, model management, and process ownership use the standard library. Install binary wheels; a compiler is not required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
```

## Architecture

- `desktop.py`: Qt window, binding confirmation dialog, worker subprocess, single-instance IPC.
- `main.py`: CLI, audio/trigger loop, silence segmentation, transcript injection.
- `audio_stream.py`: persistent pw-record child and bounded PCM buffer.
- `hidraw.py`, `evdevraw.py`, `trigger.py`, `sources.py`: device access and button state.
- `binding_capture.py`: non-blocking GUI candidate detection; never persists configuration.
- `bind.py`: HID candidate scoring, CLI two-capture learning, button labels.
- `backends/`: shared session interface, local sherpa-onnx, cloud/LAN WAV requests.
- `models_registry.py`, `models.json`: download, required-file checks, optional SHA-256 validation.
- `inject.py`, `uinput_kbd.py`: keyboard injection and Unicode clipboard paste.
- `model_dialog.py`, `model_manager.py`: three language groups, cancelable preparation subprocess, visible progress, and commit-on-success selection.
- `setup.py`, `runtime.py`: installation, shortcuts, per-checkout process ownership and stopping.

A physical hold may contain many recognition sessions. Silence or a 60-second limit finishes the current session while retaining the physical hold. Preserve the audio cursor at segment boundaries so finalization/injection does not duplicate or skip buffered audio. Release finishes the last session. The model stays loaded in the worker across holds.

The GUI pauses the worker before binding capture, stores only a candidate, saves on explicit confirmation, and resumes the previous run state after either result. Cancellation and window close must not write configuration. IPC and worker ownership are scoped to the checkout, not broad process names.

## Automated tests without physical input

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_model_switching.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_desktop_regressions.py
.venv/bin/python -m unittest discover -s tests -p test_audio_boundaries.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_hold_to_talk.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_binding_dialog.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_desktop_lifecycle.py
.venv/bin/python -m unittest discover -s tests -p test_installation.py
.venv/bin/python tests/test_autostop.py
.venv/bin/python tests/test_bind_detect.py
.venv/bin/python tests/test_trigger_logic.py
.venv/bin/python tests/test_hud.py
.venv/bin/python tests/test_cloud_backend.py
```

Several older test scripts execute at import and some require real devices, so unrestricted `unittest discover` is not the supported test entry point. The CI workflow runs an explicit hardware-free selection.

`test_streaming.py` needs the downloaded zh14m model and its bundled WAV sample. `smoke.py`, `e2e_inject.py`, `e2e_loop.py`, and `spike_qt.py` are manual device/desktop integration checks; injection tests can type into the live desktop. Run them only in a disposable local desktop session. Offscreen tests validate lifecycle logic, not actual taskbar behavior, microphone quality, or L5 accessibility.

## Changes and contributions

Keep UI labels, errors, code comments, and test descriptions in English. Maintain English and Simplified Chinese companion documentation with reciprocal language links. Represent multilingual ASR/Unicode fixtures with Unicode escapes; preserving those samples is necessary for testing non-ASCII injection and recognition. Keep focused tests for behavior changes. Model files, recordings, local credentials, and transcript logs must remain untracked.

To add a model, extend models.json with its upstream URL, directory, language/streaming metadata, and file hashes where known. The current local adapter supports transducer models with encoder/decoder/joiner files and Whisper with encoder/decoder/tokens. Load and decode a real sample before describing a new model as verified.

MIT applies to application contributions. Model weights and dependencies retain their own upstream licenses; maintain THIRD_PARTY_NOTICES.md when adding dependencies or redistributing assets.

Current GUI backends are SenseVoice, Qwen3-ASR, and Omnilingual CTC; legacy transducer/Whisper models remain compatible. Qwen3 requires conv_frontend, encoder, decoder and tokenizer files. Single-file models select the matching constructor from catalog metadata. Extraction and verification happen in staging before replacing an installation. Window close and desktop-session shutdown stop an isolated process group; bounded escalation also cleans up its recording subprocess.
