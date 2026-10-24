# Troubleshooting

English | [简体中文](zh-CN/TROUBLESHOOTING.md)

Use **SteamOS Desktop Mode**. Gaming Mode is unsupported.

## Installation or startup fails

Rerun `./init.sh --no-launch`. It repairs missing Python dependencies, verifies and loads the selected model, and refreshes desktop shortcuts. Keep the terminal output when reporting a failure, with credentials and private transcripts removed.

- **Python/venv unavailable:** check `python3 --version` and `python3 -m venv --help`. Installation requires Python 3.10+ with venv support.
- **Download fails:** check connectivity to PyPI and the public sherpa-onnx GitHub release URLs. You may supply `PIP_INDEX_URL` for an approved package mirror. Rerunning reuses completed models, but an interrupted archive download restarts.
- **No matching binary wheel:** dependencies must have wheels for your Python/architecture. Use the Steam Deck's supported Python rather than attempting a source build on read-only SteamOS.
- **Qt plugin error:** launch from the local graphical session and retain Qt's error output. Check `WAYLAND_DISPLAY`/`DISPLAY`. `QT_QPA_PLATFORM=offscreen` is for tests only and does not verify a visible window.
- **Shortcut does nothing after moving the folder:** rerun the installer at the new location. `Init.desktop` must remain next to `init.sh`. If executable bits were lost in a ZIP download, run `bash init.sh`.

## Button does not activate

Check the current button in the app, and use **Rebind button**. For a rear button, hold it for about half a second and release. Confirm saves; Cancel preserves the old binding. `./run.sh calibrate` can distinguish a trigger problem from an ASR problem.

Steam Input may consume or remap a control. Rear buttons use raw HID reports; ordinary keys use evdev. Readable `/dev/hidraw*` and `/dev/input/event*` nodes depend on desktop-session permissions. Run in the logged-in user's graphical session. If permission checks fail, inspect the relevant session/device ACLs; the installer does not change system-wide device permissions.

A non-Deck development host will normally report no Deck controller. That is an unmet hardware requirement rather than a model-installation failure.

## No speech, poor recognition, or incorrect language

Check the microphone selection and gain in Plasma audio settings. Avoid clipping. Use `./run.sh --meter --debug` and, if necessary, `--mic <PipeWire-node>` to select a source. Unplugged or switched microphones may require restarting the app.

The default SenseVoice group supports Mandarin, English, Cantonese, Japanese and Korean. Use the GUI Global languages group for Qwen3-ASR or More languages for Omnilingual ASR. Broader coverage does not guarantee higher accuracy; mixed Chinese/English needs real recording checks.

A pause normally inserts the completed segment and continues capture while held. If speech is split too early, increase `auto_stop.silence_ms`. If capture stops unexpectedly, inspect the log for a crashed process or device failure.

## Transcript appears in the log but not the intended field

Keep the destination field focused while speaking. ASCII uses uinput; Unicode uses clipboard paste. Check writable `/dev/uinput` and working Klipper (`qdbus` or `qdbus6`) or `wl-copy`. Some applications, secure fields, or privileged windows reject synthetic input or paste. Try a disposable editor field before testing a terminal prompt.

Clipboard restoration is enabled by default and briefly replaces the clipboard during Unicode insertion. `--no-restore-clipboard` is available for diagnosing clipboard synchronization issues.

## Duplicate input or an older background service

The application prevents duplicates within one checkout. Different checkouts or an older service can still compete for input. Stop this checkout with `./stop.sh`.

If you previously chose the optional legacy systemd user service, disable it before using GUI startup:

```bash
systemctl --user disable --now voice-input.service
```

That service is an optional CLI-only login service and does not create the native GUI. The standard installer does not enable it. To remove the unit after disabling it, remove `~/.config/systemd/user/voice-input.service` and run `systemctl --user daemon-reload`.

## Report a bug

Include SteamOS/desktop version, Python version, selected model/language, activation source, how to reproduce, and redacted log output. State whether a disposable text field works. Include the installer exit code if installation failed. Never post API keys, raw recordings, or transcripts you do not intend to share.

## L5 reopens a dialog or a tone is transcribed

Update to the current version: UI commands no longer respond to Space/Enter controller mappings, tones default to off, and new holds exclude pre-activation audio. Optional tones run outside recording boundaries. Window X now exits; minimizing keeps recognition available.
