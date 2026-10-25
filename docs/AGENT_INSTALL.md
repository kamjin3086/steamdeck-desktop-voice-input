# Install or repair with an agent

English | [简体中文](zh-CN/AGENT_INSTALL.md)

Use this procedure when a user gives you the repository URL and asks you to install it. The intended host is the user's Steam Deck in **Desktop Mode**. A remote agent may prepare files, but final GUI/audio checks must run in the user's graphical session. Gaming Mode is unsupported.

## 1. Inspect the target

Check the OS, architecture, Python, desktop session, and existing checkout:

```bash
uname -m
cat /etc/os-release
python3 --version
printf 'Desktop: %s; session: %s\n' "${XDG_CURRENT_DESKTOP:-unknown}" "${XDG_SESSION_TYPE:-unknown}"
command -v pw-record
```

Use `~/.local/share/steamdeck-desktop-voice-input` as the default writable checkout. Avoid `~/Applications` so this source installation stays outside the directory the user reserves for AppImage integration. If it already exists, inspect its origin and working tree before updating it. Preserve local edits. Reuse an existing installation rather than creating an accidental second copy. The process lock is per checkout; two distinct checkouts can each run an instance.

If an existing checkout is under `~/Applications`, stop it at the old path before moving, check the destination for conflicts, preserve its models and local changes, and rerun the installer at the new path to refresh shortcuts. Disable any explicitly installed legacy systemd service before moving; regenerate its unit afterward only if the user still wants that startup method. Do not silently relocate another working installation.

Completion: the target host/session and checkout are identified. If you are on another machine or a non-graphical SSH session, state that limitation before reporting device readiness.

## 2. Install the default language group

A fresh installation automatically uses SenseVoice for Mandarin, English, Cantonese, Japanese, and Korean. Do not prompt the user to pick a model during installation. The GUI provides three language groups afterward: Common languages (SenseVoice), Global languages (Qwen3-ASR), and More languages (Omnilingual ASR).

For a new checkout:

```bash
mkdir -p ~/.local/share
cd ~/.local/share
git clone https://github.com/kamjin3086/steamdeck-desktop-voice-input.git
cd steamdeck-desktop-voice-input
VOICE_INPUT_NO_PAUSE=1 bash init.sh --no-launch
```

Repeat installation preserves a previously selected local model. `--model sensevoice` can explicitly restore the default if requested; other model overrides are advanced CLI options, not a required installation decision. Language detection is automatic for the three GUI groups.

The installer checks/repairs `.venv`, installs binary Python packages, verifies/downloads the model, loads it, preserves an existing trigger binding, creates or repairs the desktop/application-menu shortcut, and checks runtime prerequisites. Existing valid model files are reused. Downloads can be large; do not download every model just to install one.

If PyPI connectivity is a problem, use a user-approved `PIP_INDEX_URL`. A download failure is not a successful installation; resolve it and rerun the same command. The script intentionally returns nonzero when device requirements remain unmet, even if software and models have installed successfully.

Completion: the installer exits zero, or you record the exact remaining blocker and distinguish software installation from device readiness.

## 3. Verify software and desktop integration

```bash
.venv/bin/python -m pip check
./run.sh models verify sensevoice
./run.sh --config
./run.sh --model sensevoice --language auto test-asr /path/to/user-approved-16khz-mono-pcm16.wav
```

Substitute the selected model. Only run the audio-file check if a suitable file is available; do not invent a passing result. `models verify` checks known hashes where supplied and required model files otherwise. The installer additionally loads the recognizer; it does not certify every possible transcript.

Use `xdg-user-dir DESKTOP` to locate the actual desktop directory, including localized paths. Verify that its `voice-input.desktop` exists, is executable, and points to this checkout. `desktop-file-validate` is useful if available. Do not require the user to install that optional validation utility.

`./run.sh --config` can contain cloud credentials if the user configured them inline. Inspect it locally; redact credentials from any report. Prefer the environment variables documented in docs/CLOUD_ASR.md.

Completion: dependency validation, selected model verification/loading, persisted configuration, and shortcut existence are all checked.

## 4. Verify in the graphical session

Launch `./desktop.sh`. Confirm that the window opens, a taskbar entry is available, minimizing keeps it alive, and a second launch reveals the existing window.

Ask the user to focus a disposable text field and hold L5 while saying two phrases with a pause between them. They should keep holding through the pause, then release. Check that the phrases are inserted once, capture continues across the pause, and release ends recording. Confirm that changing the foreground input field changes the destination of subsequent injected text.

Verify **Change model / languages** displays three groups and language descriptions, then visible download/progress states when selecting a missing model. Cancellation/failure must retain the previous selection, success must persist it, and switching back should reuse cached files. Close the window using X and confirm the application exits; minimizing should keep it running.

To test rebinding, use **Rebind button**. Verify the candidate label, then test **Cancel** first: the old binding must remain. If the user wants a replacement, repeat and choose **Confirm**, then verify the new button with a live recording. Custom bindings must survive rerunning the installer.

Physical button presses, microphone quality, desktop focus, and real insertion cannot be proven by a headless/offscreen test. Request only the live steps your tools cannot perform.

Completion: either the live checks pass, or your handoff explicitly lists them as pending.

## 5. Stop or hand off

```bash
./stop.sh
./stop.sh
```

Both calls should succeed after the checkout's processes exit. Restart `./desktop.sh` if the user wants it left running. If an older systemd user service was explicitly installed, follow docs/TROUBLESHOOTING.md for its removal before switching to GUI startup.

Report the installation path, selected model/language, current activation button, shortcut location, checks performed, pending physical checks, and how to stop the app. The default binding is **L5: hold to use, release to deactivate**. Releasing finalizes captured speech; it does not undo text already inserted.
