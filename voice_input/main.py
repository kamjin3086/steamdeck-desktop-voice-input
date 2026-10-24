"""Hold-to-talk CLI. Capture audio while the trigger is held, finalize segments during pauses, and inject text into the focused input."""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time

from . import evdevraw as ev
from . import models_registry as registry
from .asr import read_wav, transcribe_file
from .audio_stream import SAMPLE_RATE, AudioStream, pcm_stats, write_wav
from .autostop import SilenceStopper
from .backends import create_backend
from .bind import describe, interactive_bind
from .feedback import Beep
from .hidraw import load_config, save_config
from .hud import PartialLog, RecorderHUD
from .inject import Injector
from .sources import make_source
from .trigger import TriggerWatcher

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_WAV = os.path.join(PROJECT_ROOT, ".last.wav")

MIN_DURATION = 0.35
MAX_DURATION = 60.0
MIN_PEAK = 0.02

DEFAULT_AUTO_STOP = {"enabled": True, "silence_ms": 600, "threshold": 0.02}
DEFAULT_ASR = {"backend": "local", "model": registry.DEFAULT_MODEL, "num_threads": 2,
               "language": "auto"}


def say(msg: str) -> None:
    print(msg, flush=True)


def effective_config(args) -> dict:
    """Merge persisted configuration with CLI overrides."""
    cfg = load_config()
    asr = dict(DEFAULT_ASR)
    asr.update(cfg.get("asr") or {})
    for key, value in (("backend", args.backend), ("model", args.model),
                       ("preset", args.preset), ("base_url", args.base_url),
                       ("api_key", args.api_key), ("language", args.language)):
        if value:
            asr[key] = value
    if args.cloud_model:
        asr["model"] = args.cloud_model
    if args.threads:
        asr["num_threads"] = args.threads
    cfg["asr"] = asr
    auto = dict(DEFAULT_AUTO_STOP)
    auto.update(cfg.get("auto_stop") or {})
    cfg["auto_stop"] = auto
    return cfg


def resolve_trigger(args, cfg: dict) -> dict:
    if args.trigger_key:
        return {"source": "evdev-key", "code": args.trigger_key}
    if args.trigger_abs:
        return {"source": "evdev-abs", "code": args.trigger_abs}
    trigger = cfg.get("trigger")
    if not trigger:
        raise SystemExit("No activation button configured. Run ./run.sh bind first.")
    return trigger


# ---------------------------------------------------------------- run
def cmd_run(args) -> int:
    cfg = effective_config(args)
    trigger = resolve_trigger(args, cfg)
    auto = cfg["auto_stop"]
    show_partial = not args.no_partial

    say(f"[trigger] {describe({'trigger': trigger})}")
    say(f"[asr] {cfg['asr']}")
    t0 = time.monotonic()
    backend = create_backend(cfg["asr"], debug=args.debug)
    say(f"[asr] {backend.describe()} ready ({time.monotonic() - t0:.1f}s)"
        f"  partial={'supported' if backend.supports_partial else 'unsupported'}")
    if auto["enabled"]:
        say(f"[auto-stop] Silence {auto['silence_ms']}ms finalizes a segment; keep holding to continue")

    injector = Injector(restore_clipboard=not args.no_restore_clipboard,
                        debug=args.debug)
    beep = Beep(enabled=args.beep and not args.no_beep)
    hud = RecorderHUD(meter=args.meter, partial=show_partial)
    plog = PartialLog(args.partial_log)
    session = None
    try:
        with AudioStream(device=args.mic, debug=args.debug) as stream, \
                make_source(trigger, args.press_threshold,
                            args.release_threshold) as source:
            say("== Ready: hold to dictate, pauses finalize segments, release to stop (Ctrl+C exits) ==")
            session = None
            cursor = 0
            recording = False
            peak = 0.0
            started_at = 0.0
            stopper = SilenceStopper(silence_ms=auto["silence_ms"],
                                     speech_peak=float(auto["threshold"]))
            should_stop = False
            partial_text = ""

            def on_partial(text: str) -> None:
                nonlocal partial_text
                partial_text = text
                plog.write("partial", text)

            while True:
                for edge in source.poll(timeout=0.02):
                    if edge == "press" and not recording:
                        session = backend.open_session(on_partial=on_partial)
                        beep.start()
                        # Capture only audio after activation, excluding the
                        # optional cue and all pre-activation buffer contents.
                        cursor = stream.position()
                        recording = True
                        started_at = time.monotonic()
                        peak = 0.0
                        stopper.reset()
                        partial_text = ""
                        plog.write("start")
                        say("● Recording...")
                    elif edge == "release" and recording:
                        recording = False
                        hud.done()
                        session, text = finish_session(
                            session, stream, cursor, peak, started_at, args,
                            plog)
                        session = None
                        beep.stop()
                        if text:
                            inject(injector, text, args)

                if not recording:
                    continue

                pcm, cursor = stream.read_since(cursor)
                should_stop = False
                if pcm:
                    session.accept(pcm)
                    chunk_peak, _chunk_rms = pcm_stats(pcm)
                    peak = max(peak, chunk_peak)
                    should_stop = stopper.feed(chunk_peak, time.monotonic())

                now = time.monotonic()
                elapsed = now - started_at

                hud.draw(stream.level(), elapsed, partial_text)

                stop_reason = None
                if auto["enabled"] and should_stop:
                    stop_reason = "Silence segment"
                elif elapsed > MAX_DURATION:
                    stop_reason = f"Exceeded {MAX_DURATION:.0f}s"

                if stop_reason:
                    # Keep the physical hold armed. Freeze this boundary before
                    # finalizing so audio captured during decoding/injection is
                    # consumed by the next session, without gaps or duplication.
                    say(f"○ {stop_reason}, continue listening")
                    session, text = finish_session(
                        session, stream, cursor, peak, started_at, args,
                        plog, drain=False)
                    session = backend.open_session(on_partial=on_partial)
                    started_at = now
                    peak = 0.0
                    stopper.reset()
                    partial_text = ""
                    plog.write("start")
                    if text:
                        inject(injector, text, args)
    except KeyboardInterrupt:
        say("\nExiting.")
    finally:
        if session is not None:
            session.cancel()
        hud.done()
        beep.close()
        injector.close()
    return 0


def finish_session(session, stream, cursor, peak, started_at, args, plog, *, drain=True):
    """Drain pending audio, finalize recognition, and reject short or silent segments."""
    if session is None:
        return None, ""
    if drain:
        pcm, _ = stream.read_since(cursor)
        if pcm:
            session.accept(pcm)
            peak = max(peak, pcm_stats(pcm)[0])
    duration = time.monotonic() - started_at
    if duration < MIN_DURATION:
        session.cancel()
        say(f"○ {duration:.2f}s; too short, ignored")
        return None, ""
    if peak < MIN_PEAK:
        session.cancel()
        say(f"○ No speech detected (peak={peak:.3f}); ignored. Check the microphone and Steam input device")
        return None, ""
    t0 = time.monotonic()
    try:
        text = (session.finish() or "").strip()
    except Exception as exc:
        say(f"  -> Recognition failed: {exc}")
        return None, ""
    elapsed = time.monotonic() - t0
    tag = "final" if elapsed > 0.05 else "finalize"
    plog.write("final", f"{text}\t{elapsed:.3f}s")
    say(f"○ {duration:.2f}s audio -> {tag} {elapsed:.2f}s  「{text}」")
    return None, text


def inject(injector: Injector, text: str, args) -> None:
    try:
        mode = injector.type_or_paste(text)
        if args.debug:
            say(f"  -> Inserted ({mode})")
    except Exception as exc:  # noqa: BLE001
        say(f"  -> Injection failed: {exc}")


# --------------------------------------------------------------- models
def cmd_models(args) -> int:
    action = args.action or "list"
    catalog = registry.models()
    if action == "list":
        installed = registry.installed_models()
        for name, spec in registry.selectable_models().items():
            mark = "✓" if name in installed else " "
            stream = "streaming" if spec.get("streaming") else "offline"
            langs = ",".join(spec.get("languages") or [])
            print(f" [{mark}] {name:14} {spec['name']:28} {stream} "
                  f"{spec.get('rt_factor', '?'):>3}x  {langs:8} "
                  f"{'(benchmarked locally)' if spec.get('verified') else '(not benchmarked)'}")
            print(f"       {spec.get('note', '')}")
        print("\nCloud presets:")
        for name, spec in registry.cloud_presets().items():
            print(f"  {name:12} {spec['model']:32} {spec['base_url']}")
        return 0

    names = args.names or ([] if action == "list" else [registry.DEFAULT_MODEL])
    if action == "verify":
        names = names if args.names else list(registry.selectable_models())
        bad = 0
        for name in names:
            problems = registry.verify(name)
            if problems:
                bad += 1
                print(f"[FAIL] {name}: {'; '.join(problems)}")
            else:
                print(f"[OK]   {name}")
        return 1 if bad else 0

    if action == "remove":
        for name in names:
            print(f"{'Removed' if registry.remove(name) else 'not installed'}: {name}")
        return 0

    if action == "install":
        for name in names:
            print(f"Installing {name} ...")
            last = [0.0]

            def progress(done: int, total: int) -> None:
                now = time.monotonic()
                if now - last[0] < 0.5 and done != total:
                    return
                last[0] = now
                if total:
                    pct = done * 100 / total
                    print(f"\r  {done / 1048576:6.1f} / {total / 1048576:.1f} MB "
                          f"({pct:5.1f}%)", end="", flush=True)
                else:
                    print(f"\r  {done / 1048576:6.1f} MB", end="", flush=True)

            path = registry.install(name, on_progress=progress)
            print(f"\n  ✓ {path}")
        return 0

    print(f"Unknown action: {action}")
    return 2


# ---------------------------------------------------------------- bind
def cmd_bind(args) -> int:
    trigger = interactive_bind(args.seconds)
    if not trigger:
        return 1
    say(f"Current binding: {describe({'trigger': trigger})}")
    say("\nVerify: press the same button again within 5 seconds...")
    deadline = time.monotonic() + 5
    with make_source(trigger) as source:
        while time.monotonic() < deadline:
            if "press" in source.poll(timeout=0.05):
                say("Verified. Start with: ./run.sh --meter")
                return 0
    say("No press detected in 5 seconds. Retry ./run.sh bind")
    return 1


# ---------------------------------------------------------- calibrate
def cmd_calibrate(args) -> int:
    cfg = load_config()
    trigger = resolve_trigger(args, cfg)
    say(f"Trigger source: {describe({'trigger': trigger})}    Press Ctrl+C to stop")
    with make_source(trigger, args.press_threshold,
                     args.release_threshold) as source:
        last_print = 0.0
        try:
            while True:
                for edge in source.poll(timeout=0.02):
                    print(f"\n  >>> {edge.upper()}", flush=True)
                    last_print = 0.0
                if time.monotonic() - last_print < 0.2:
                    continue
                last_print = time.monotonic()
                value = getattr(source, "value", None)
                if value is None:
                    state = bool(getattr(source, "pressed", False))
                    if state != getattr(cmd_calibrate, "_last", None):
                        cmd_calibrate._last = state
                        print(f"{'PRESSED' if state else 'released'}", flush=True)
                else:
                    bar = "#" * int(value * 40)
                    print(f"\rvalue={value:.2f} |{bar:<40}| "
                          f"{'PRESSED' if source.pressed else '       '}",
                          end="", flush=True)
        except KeyboardInterrupt:
            print()
    return 0


# --------------------------------------------------------- test-inject
def cmd_test_inject(args) -> int:
    say(f"Injecting in 3 seconds: {args.text!r}  (focus an input field)")
    time.sleep(3)
    injector = Injector(restore_clipboard=not args.no_restore_clipboard,
                        debug=True)
    try:
        say(f"Injection complete; method = {injector.type_or_paste(args.text)}")
    finally:
        injector.close()
    return 0


# ------------------------------------------------------------ test-asr
def cmd_test_asr(args) -> int:
    cfg = effective_config(args)
    backend = create_backend(cfg["asr"], debug=args.debug)
    say(f"[asr] {backend.describe()}  partial="
        f"{'supported' if backend.supports_partial else 'unsupported'}")
    target = args.wav or os.path.join(registry.model_dir(cfg['asr']['model']), "test_wavs")
    paths = ([target] if os.path.isfile(target)
             else sorted(glob.glob(os.path.join(target, "*.wav"))))
    if not paths:
        say("No WAV files found")
        return 1
    for path in paths:
        try:
            samples = read_wav(path)
        except ValueError as exc:
            print(f"{os.path.basename(path):28} skipped: {exc}")
            continue
        duration = len(samples) / SAMPLE_RATE
        duration_t = time.monotonic()
        text = transcribe_file(path, backend)
        elapsed = time.monotonic() - duration_t
        print(f"{os.path.basename(path):28} {duration:5.2f}s recognition {elapsed:5.2f}s "
              f"({duration / elapsed:4.1f}x)  「{text}」")
    return 0


# ---------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="voice-input")
    p.add_argument("--threads", type=int, default=None,
                   help="Local model threads (default: 2)")
    p.add_argument("--backend", choices=["local", "cloud"], default=None)
    p.add_argument("--language", default=None, help="Recognition language hint, e.g. en or zh")
    p.add_argument("--model", default=None, help="Local model name, e.g. sensevoice")
    p.add_argument("--preset", default=None, help="Cloud preset, e.g. lan/groq")
    p.add_argument("--base-url", default=None, help="Cloud or LAN service URL")
    p.add_argument("--cloud-model", default=None, help="Cloud model name")
    p.add_argument("--api-key", default=None)
    p.add_argument("--press-threshold", type=float, default=0.30)
    p.add_argument("--release-threshold", type=float, default=0.12)
    p.add_argument("--mic", default=None, help="pw-record --target")
    p.add_argument("--meter", action="store_true", help="Show recording levels")
    p.add_argument("--no-partial", action="store_true", help="Hide partial transcripts")
    p.add_argument("--partial-log", default=None,
                   help="Write timestamped partial/final results to a log")
    p.add_argument("--beep", action="store_true", help="Enable optional tones outside recording (off by default)")
    p.add_argument("--no-beep", action="store_true", help="Disable feedback tones")
    p.add_argument("--config", action="store_true", help="Print effective configuration and exit")
    p.add_argument("--trigger-key", type=lambda v: int(v, 0), default=None,
                   help="Use a key, e.g. 0x138 = BTN_TL2 / 0x44 = F10")
    p.add_argument("--trigger-abs", type=lambda v: int(v, 0), default=None,
                   help="Use an axis, e.g. 0x2 = ABS_Z")
    p.add_argument("--no-restore-clipboard", action="store_true")
    p.add_argument("--debug", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("run")
    sub.add_parser("calibrate")
    sub.add_parser("devices")

    b = sub.add_parser("bind")
    b.add_argument("--seconds", type=float, default=6.0)

    m = sub.add_parser("models")
    m.add_argument("action", nargs="?", default="list",
                   choices=["list", "install", "remove", "verify"])
    m.add_argument("names", nargs="*")

    ti = sub.add_parser("test-inject")
    ti.add_argument("text", nargs="?", default="\u4f60\u597d, \u8fd9\u662f voice-input \u6ce8\u5165\u6d4b\u8bd5 hello")

    ta = sub.add_parser("test-asr")
    ta.add_argument("wav", nargs="?", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cmd = args.cmd or "run"
    if args.config:
        import json
        print(json.dumps(effective_config(args), indent=2, ensure_ascii=False))
        return 0
    if cmd == "devices":
        for dev in ev.list_devices():
            print(f"{dev.path:22} {dev.name!r} "
                  f"abs={sorted(hex(a) for a in dev.abs)}")
        return 0
    if cmd == "models":
        return cmd_models(args)
    if cmd == "bind":
        return cmd_bind(args)
    if cmd == "calibrate":
        return cmd_calibrate(args)
    if cmd == "test-inject":
        return cmd_test_inject(args)
    if cmd == "test-asr":
        return cmd_test_asr(args)
    from .runtime import worker_lock
    import signal
    def stop_signal(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_signal)
    with worker_lock():
        return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
