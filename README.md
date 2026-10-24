# Steam Deck Desktop Voice Input

English | [简体中文](README.zh-CN.md)

Hold a button, speak, and insert the transcript into the focused text field on your Steam Deck.

Built for **SteamOS Desktop Mode** with KDE Plasma and PipeWire. Use it in chat boxes, browser forms, editors, and terminal prompts, including the prompt of a locally installed coding agent. **Gaming Mode is not supported.** Other Linux desktops are experimental.

The application runs locally, stays available in the taskbar, and uses **L5 (the left rear button)** by default. Hold to dictate; release to deactivate. Pauses finalize and insert a segment while you keep holding, so you can continue speaking without pressing L5 again. Releasing ends capture and finalizes remaining speech; it does not undo text already inserted.

## Features

- Local speech recognition using sherpa-onnx, with downloadable model choices.
- Continuous hold-to-talk and silence segmentation; capture starts after activation.
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

SenseVoice is installed automatically; there is no model-choice prompt. The installer creates **Steam Deck Voice Input** on your desktop and in the application menu, then launches it when device checks pass.

Alternatively, open the checkout in Dolphin and double-click **Init.desktop**, or right-click it and choose to execute it. KDE may ask you to mark it trusted before running. Keep `Init.desktop` beside `init.sh`; it locates the installer relative to itself. If a ZIP download has lost executable permissions, run `bash init.sh` from a terminal.

### Speech recognition languages

Install once with `./init.sh`. Fresh installations use **Common languages / SenseVoice** automatically. Open **Change model / languages** in the GUI whenever you want a different language group:

| Language group | Coverage | Engine | Approximate download |
| --- | --- | --- | --- |
| Common languages (default) | Mandarin, English, Cantonese, Japanese, Korean | SenseVoice Small INT8 | 163 MB |
| Global languages | 30 major languages, including Chinese, English, French, German, Spanish, Russian and Thai | Qwen3-ASR 0.6B INT8 | 879 MB |
| More languages | 1600+ languages, including many low-resource languages | Omnilingual ASR 300M INT8 | 293 MB |

Select a group to see its full language summary, characteristics, engine, upstream documentation, installation state, and estimated download size. Click **Download and switch** or **Use this model**. The dialog shows received bytes/percentage and extraction, verification, and loading phases. The selection is saved only after loading succeeds. Failure or Cancel keeps the previous selection. Downloaded models remain cached, so you can switch back without downloading again.

Your selected model is reused on later launches and repeat installations; custom button bindings also remain intact. The three groups describe language coverage, not accuracy tiers. Chinese/English mixed speech should be tested with your own recordings for each applicable group. Wider language coverage does not imply better Chinese/English accuracy or faster performance on a Deck.

Legacy Zipformer/Whisper installations remain usable for compatibility but are not additional GUI choices. New installations and the GUI use the three language groups above. Model language coverage is documented upstream: [SenseVoice](https://k2-fsa.github.io/sherpa/onnx/sense-voice/pretrained.html), [Qwen3-ASR](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html), [Omnilingual](https://k2-fsa.github.io/sherpa/onnx/omnilingual-asr/models.html).

Downloads are on demand. Models and dependencies have their own licenses; this repository's MIT license covers the application code. See [third-party notices](THIRD_PARTY_NOTICES.md).

## Let an agent install it

Give an agent running **on your Steam Deck** this prompt:

> Install https://github.com/kamjin3086/steamdeck-desktop-voice-input on this Steam Deck in Desktop Mode. Read AGENTS.md and docs/AGENT_INSTALL.md first. Use the documented installer, preserve existing bindings, and verify the desktop shortcut, model loading, and device permissions. Use the default SenseVoice model; I can change language groups in the GUI later. Report anything that needs my physical input; do not claim the microphone or L5 works without a live check.

The [agent installation guide](docs/AGENT_INSTALL.md) includes unattended commands, repair steps, and explicit completion checks. The installer defaults to SenseVoice without prompting; no model choice is needed to get started.

## Everyday use

1. Double-click **Steam Deck Voice Input** and wait for **Ready**.
2. Focus the text field where you want the transcript to appear.
3. Hold **L5**, speak, and release to stop. Keep holding through pauses to continue dictating; each finalized segment is inserted into the focused field.
4. Minimize the window to keep it running. Click its taskbar icon to reopen it. The window **X** and **Quit application** both stop the app; minimizing keeps it running. This permits Desktop Mode logout or switching back to Gaming Mode.

**Rebind button:** click the button in the app, press your desired keyboard/controller button (hold a rear button for about half a second, then release), inspect the detected candidate, and click **Confirm**. **Cancel** or closing the dialog keeps the old binding. Recognition pauses during capture and resumes afterward if it was running before.

```bash
./desktop.sh                        # Open or reveal the desktop application
./stop.sh                           # Stop this checkout's app and recognition worker
./init.sh                           # Repair while preserving the selected model
./init.sh --no-launch                 # Install/check without starting the app
./run.sh --meter                     # CLI recognition with a terminal meter
./run.sh --help                      # CLI options
```

The desktop shortcut points to the checkout. After moving the folder, rerun `init.sh` to refresh it. Repeated installation preserves custom button bindings. Repeated startup reveals the existing window; repeated stopping is safe.

## Dictate instructions to an agent

For a useful hands-on setup, install a local coding agent such as [Pi](https://github.com/earendil-works/pi), following its own installation and authentication instructions. Open the agent in a terminal in Desktop Mode, focus its prompt, and dictate your request with L5. Review the inserted text and submit it yourself.

For example, ask an agent to organize project files, edit a script, or investigate an error. What it can do depends on its available tools and permissions; controlling desktop applications requires an agent with suitable desktop automation tools. Voice Input supplies text input and does not itself execute commands or install an agent.

## Configuration, privacy, and limitations

Configuration lives in `~/.config/voice-input/config.json`. Local models work offline after installation. Cloud/LAN backends send audio to the endpoint you configure; local mode does not send it there. The GUI log shows transcripts; optional diagnostic logs may also contain them.

Text injection uses uinput for ASCII and clipboard paste for Unicode. Unicode insertion briefly uses the clipboard and restores it by default. Most editable areas work, but applications that block synthetic input/paste, privileged windows, and some secure fields may reject it. Keep focus in the intended field while dictating; this is not an input-method framework integration. The current three language groups recognize finalized segments at pauses or release; legacy streaming models may also show partial transcripts. Only finalized text is inserted. Activation/release tones are off by default to avoid transcribing speaker sounds. Optional CLI `--beep` plays the activation tone before the capture boundary and the release tone after finalization. There is no pre-activation audio in a new hold.

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
