# Changelog

English | [简体中文](CHANGELOG.zh-CN.md)

## Unreleased

- Recommend `~/.local/share/steamdeck-desktop-voice-input` instead of the AppImage-oriented `~/Applications` directory, with migration instructions.

## 0.2.0 - 2026-10-24

- Install SenseVoice automatically; offer three language groups in the GUI: Common languages, Global languages (Qwen3-ASR), and More languages (Omnilingual ASR).
- Show download byte/percentage progress and preparation phases; preserve the previous model on cancellation or failure and reuse cached models.
- Prevent controller keyboard mappings from activating focused UI commands or reopening rebinding.
- Default feedback tones to off; exclude pre-activation audio and finalize before optional release tones.
- Make window X exit cleanly and bound worker shutdown for desktop-session switching.
- Add Simplified Chinese README, installation/agent guides, configuration, troubleshooting, development, cloud, roadmap, changelog, and third-party notices with reciprocal language links.

## 0.1.0 - 2026-10-24

Initial English-language open-source release under MIT.

- Native Qt desktop window, taskbar/tray integration, and per-checkout single-instance behavior.
- Repeatable install/repair script, on-demand model selection, desktop shortcut, and stop script.
- Hold-to-talk continuation across silence and 60-second segment boundaries.
- Activation-button dialog with explicit confirmation, cancellation, and worker-state restoration.
- Local streaming transducer and offline Whisper recognition; optional compatible cloud/LAN endpoints.
- Manual and agent-oriented installation guides with separate software and physical-device verification.
- Automated binding, recording-loop, installer, cloud adapter, and desktop-lifecycle checks.

The initial release incorporates earlier private development. Physical Deck observations informed the input design; the release integration checks were run on a Linux Wayland development host without Deck hardware.
