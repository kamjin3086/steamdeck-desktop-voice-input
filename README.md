# Steam Deck Desktop Voice Input

Hold a button, speak, and insert the transcript into the focused text field on your Steam Deck.

Built for **SteamOS Desktop Mode** with KDE Plasma and PipeWire. Use it in chat boxes, browser forms, editors, and terminal prompts, including the prompt of a locally installed coding agent. **Gaming Mode is not supported.** Other Linux desktops are experimental.

The application runs locally, stays available in the taskbar, and uses **L5 (the left rear button)** by default. Hold to dictate; release to deactivate. Pauses finalize and insert a segment while you keep holding, so you can continue speaking without pressing L5 again. Releasing ends capture and finalizes remaining speech; it does not undo text already inserted.

## Features

- Local speech recognition using sherpa-onnx, with downloadable model choices.
- Continuous hold-to-talk, silence segmentation, and a rolling audio pre-buffer.
- Native Qt window, taskbar icon, optional system tray, and single-instance startup.
- Rebind the activation button in a dialog with **Confirm** and **Cancel**.
- Repeatable installer that checks dependencies, verifies/loads the selected model, and repairs missing components.
- Desktop shortcut and a separate stop script.
- Optional OpenAI-compatible cloud or LAN transcription.

## Requirements

- Steam Deck running **SteamOS Desktop Mode**, with a working microphone.
- Python 3.10+ with `venv` support, Bash, and Git (or a downloaded source ZIP).
- PipeWire's `pw-record` (`pw-play` is used for optional tones).
- Read access to controller/input devices and write access to `/dev/uinput`.
- KDE Klipper with `qdbus`/`qdbus6`, or `wl-copy`, for Unicode paste.
- Internet access for the initial Python dependencies and selected model.

The installer uses the checkout's `.venv/` and `models/`, plus your user configuration and desktop directories. It does not use sudo, install system packages, or unlock the SteamOS root filesystem. Input-device permissions vary by SteamOS release and session; installation checks them and reports unmet requirements instead of claiming success.

## Install manually

Switch to Desktop Mode and open Konsole:

```bash
mkdir -p ~/Applications
cd ~/Applications
git clone https://github.com/kamjin3086/steamdeck-desktop-voice-input.git
cd steamdeck-desktop-voice-input
./init.sh
```

Choose a model when prompted. The installer creates **Steam Deck Voice Input** on your desktop and in the application menu, then launches it when device checks pass.

Alternatively, open the checkout in Dolphin and double-click **Init.desktop**, or right-click it and choose to execute it. KDE may ask you to mark it trusted before running. Keep `Init.desktop` beside `init.sh`; it locates the installer relative to itself. If a ZIP download has lost executable permissions, run `bash init.sh` from a terminal.

### Choose a model

| Model | Languages | Recognition | Approximate download |
| --- | --- | --- | --- |
| `zh14m` | Chinese | Streaming; lightweight default | 74 MB |
| `bilingual` | Chinese and English | Streaming | 200 MB (estimate) |
| `whisper-small` | Multilingual | Offline per segment | 640 MB |

The English UI does not change the model's language: **the default `zh14m` model recognizes Chinese, not English**. For English dictation, choose `bilingual`, or use Whisper with an English language setting:

```bash
./init.sh --model whisper-small --language en
```

Downloads are on demand. Models and dependencies have their own licenses; this repository's MIT license covers the application code. See [third-party notices](THIRD_PARTY_NOTICES.md).

## Let an agent install it

Give an agent running **on your Steam Deck** this prompt:

> Install https://github.com/kamjin3086/steamdeck-desktop-voice-input on this Steam Deck in Desktop Mode. Read AGENTS.md and docs/AGENT_INSTALL.md first. Use the documented installer, preserve existing bindings, and verify the desktop shortcut, model loading, and device permissions. Use whisper-small with language en for English dictation. Report anything that needs my physical input; do not claim the microphone or L5 works without a live check.

The [agent installation guide](docs/AGENT_INSTALL.md) includes unattended commands, repair steps, and explicit completion checks. Agents can also choose `zh14m` for Chinese or `bilingual` for mixed Chinese/English.

## Everyday use

1. Double-click **Steam Deck Voice Input** and wait for **Ready**.
2. Focus the text field where you want the transcript to appear.
3. Hold **L5**, speak, and release to stop. Keep holding through pauses to continue dictating; each finalized segment is inserted into the focused field.
4. Minimize the window to keep it running. Click its taskbar icon to reopen it. Closing the window minimizes it; **Quit application** exits it.

**Rebind button:** click the button in the app, press your desired keyboard/controller button (hold a rear button for about half a second, then release), inspect the detected candidate, and click **Confirm**. **Cancel** or closing the dialog keeps the old binding. Recognition pauses during capture and resumes afterward if it was running before.

```bash
./desktop.sh                        # Open or reveal the desktop application
./stop.sh                           # Stop this checkout's app and recognition worker
./init.sh                           # Repair/reconfigure; select another model
./init.sh --model zh14m --no-launch   # Install/check without starting the app
./run.sh --meter                     # CLI recognition with a terminal meter
./run.sh --help                      # CLI options
```

The desktop shortcut points to the checkout. After moving the folder, rerun `init.sh` to refresh it. Repeated installation preserves custom button bindings. Repeated startup reveals the existing window; repeated stopping is safe.

## Dictate instructions to an agent

For a useful hands-on setup, install a local coding agent such as [Pi](https://github.com/earendil-works/pi), following its own installation and authentication instructions. Open the agent in a terminal in Desktop Mode, focus its prompt, and dictate your request with L5. Review the inserted text and submit it yourself.

For example, ask an agent to organize project files, edit a script, or investigate an error. What it can do depends on its available tools and permissions; controlling desktop applications requires an agent with suitable desktop automation tools. Voice Input supplies text input and does not itself execute commands or install an agent.

## Configuration, privacy, and limitations

Configuration lives in `~/.config/voice-input/config.json`. Local models work offline after installation. Cloud/LAN backends send audio to the endpoint you configure; local mode does not send it there. The GUI log shows transcripts; optional diagnostic logs may also contain them.

Text injection uses uinput for ASCII and clipboard paste for Unicode. Unicode insertion briefly uses the clipboard and restores it by default. Most editable areas work, but applications that block synthetic input/paste, privileged windows, and some secure fields may reject it. Keep focus in the intended field while dictating; this is not an input-method framework integration. Partial recognition appears in the UI/log; finalized segments are what get inserted.

Rear-button exposure and device permissions can change with firmware, Steam Input, or SteamOS updates. The default L5 mapping is based on a tested Deck layout; use the rebinding dialog if your layout differs. A 60-second segment cap bounds recognition memory and automatically begins the next segment while held. Very slow decoding can exceed the rolling audio buffer; avoid backends slower than real time for long dictation.

This initial open-source release includes automated lifecycle and binding tests, plus real local-model decoding checks. Current release work was validated on a Linux Wayland host without Deck hardware; L5, microphone, taskbar interaction, and insertion still need verification on your Deck. Historical Deck observations are not a compatibility guarantee for every SteamOS version.

## More documentation

- [Agent installation and verification](docs/AGENT_INSTALL.md)
- [Configuration](docs/CONFIG.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Cloud and LAN transcription](docs/CLOUD_ASR.md)
- [Development and tests](docs/DEVELOPING.md)
- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE). Copyright (c) 2026 kamjin3086.
