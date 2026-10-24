"""Interactive, repeatable installation and desktop integration."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import models_registry as registry
from .backends import create_backend
from .bind import binding_label
from .hidraw import find_deck_hidraws, load_config, save_config
from .runtime import ROOT


def desktop_quote(value):
    # Desktop Entry string escaping followed by Exec argument escaping.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\') + '"'


def desktop_dir():
    if shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True)
        value = result.stdout.strip()
        if result.returncode == 0 and value and Path(value).is_absolute():
            return Path(value)
    return Path.home() / 'Desktop'


def install_shortcut():
    applications = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications'
    entry = '\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Name=Steam Deck Voice Input',
        'Comment=Hold the configured button to dictate; release to stop',
        f'Exec={desktop_quote(ROOT / "desktop.sh")}',
        f'Icon={ROOT / "packaging/voice-input.svg"}',
        'Terminal=false', 'Categories=Utility;Accessibility;',
        'StartupNotify=true', 'StartupWMClass=voice-input', '',
    ])
    for directory in (applications, desktop_dir()):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / 'voice-input.desktop'
        # Rewrite stale paths when a checkout has moved; stable on repeat runs.
        if not path.exists() or path.read_text() != entry:
            path.write_text(entry)
        path.chmod(0o755)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(applications)], check=False)
    print(f'Desktop shortcut: {desktop_dir() / "voice-input.desktop"}')


def choose_model(cfg):
    catalog = registry.models()
    current = cfg.get('asr', {}).get('model', 'zh14m')
    if current not in catalog:
        current = 'zh14m'
    names = list(catalog)
    for index, name in enumerate(names, 1):
        spec = catalog[name]
        state = 'installed' if registry.is_installed(name) else 'not installed'
        print(f'{index}. {name}: {spec["name"]} / approximately {spec.get("archive_bytes", 0) / 1e6:.0f} MB / {state}')
    while True:
        choice = input(f'Select model number or name (Enter keeps {current}): ').strip()
        if not choice:
            return current
        if choice in catalog:
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        print('Enter a listed number or model name.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=list(registry.models()))
    parser.add_argument('--language', help='Recognition language hint, e.g. en or zh')
    parser.add_argument('--no-launch', action='store_true')
    args = parser.parse_args(argv)
    subprocess.run([sys.executable, '-m', 'voice_input.desktop', '--check'],
                   cwd=ROOT, check=True, timeout=30)
    cfg = load_config()
    name = args.model or choose_model(cfg)
    print(f'Checking model {name}…', flush=True)
    registry.install(name, on_progress=lambda done, total: print(
        f'\rDownload: {done / 1e6:.1f} / {total / 1e6:.1f} MB', end='', flush=True))
    print('\nChecking that the model loads...', flush=True)
    model_cfg = dict(cfg.get('asr') or {})
    model_cfg.update(backend='local', model=name)
    if args.language:
        model_cfg['language'] = args.language
    try:
        backend = create_backend(model_cfg)
    except Exception:
        print('Model loading failed; downloading a fresh copy once...', flush=True)
        registry.remove(name)
        registry.install(name)
        backend = create_backend(model_cfg)
    print(backend.describe())
    del backend
    cfg['asr'] = model_cfg
    cfg.setdefault('trigger', {'source': 'hidraw', 'report_id': 1, 'byte': 9, 'bit': 7})
    save_config(cfg)
    install_shortcut()
    problems = []
    if not shutil.which('pw-record'):
        problems.append('pw-record is missing; a PipeWire Linux desktop is required.')
    if not os.access('/dev/uinput', os.W_OK):
        problems.append('Cannot write /dev/uinput. Check device access in the Deck desktop session.')
    if cfg['trigger'].get('source') == 'hidraw':
        paths = find_deck_hidraws()
        if not any(os.access(path, os.R_OK) for path in paths):
            problems.append('No readable Steam Deck controller. Run on a Deck, or bind another button with ./run.sh bind.')
    if not (shutil.which('qdbus') or shutil.which('qdbus6') or shutil.which('wl-copy')):
        problems.append('qdbus, qdbus6, or wl-copy is required for Unicode clipboard paste.')
    if problems:
        print('\nSoftware and models installed; resolve these device requirements:\n- ' + '\n- '.join(problems))
        return 1
    print('Installation complete. The default voice activation button is L5 (left rear button).')
    print(f"Current activation button: {binding_label(cfg['trigger'])}. Hold to use; release to deactivate (end recording).")
    print('Use Rebind button in the app to change it; use ./stop.sh to stop the app.')
    if not args.no_launch:
        # Restart so a newly selected model takes effect in an existing window.
        from .runtime import stop_desktop, stop_worker
        if not stop_desktop() or not stop_worker():
            raise RuntimeError('The previous instance has not stopped. Run ./stop.sh before restarting.')
        subprocess.Popen([str(ROOT / 'desktop.sh')], cwd=ROOT, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
