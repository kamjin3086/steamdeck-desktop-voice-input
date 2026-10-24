"""Prepare a model in a subprocess and report newline-delimited JSON progress.

Configuration is committed by the GUI only after this subprocess exits cleanly.
"""
import argparse
import json
import signal
import time

from . import models_registry as registry
from .backends import create_backend


def emit(**event):
    print(json.dumps(event), flush=True)


def prepare(name):
    last = [0.0]
    def progress(done, total):
        now = time.monotonic()
        if now - last[0] >= .1 or done == total:
            last[0] = now
            emit(phase='downloading', done=done, total=total)
    registry.install(name, on_progress=progress, on_phase=lambda phase: emit(phase=phase))
    emit(phase='loading')
    backend = create_backend({'backend': 'local', 'model': name,
                              'language': registry.get(name).get('default_language', 'auto'),
                              'num_threads': 2})
    del backend
    emit(phase='ready', model=name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', choices=list(registry.selectable_models()))
    args = parser.parse_args()
    def interrupted(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        prepare(args.model)
    except KeyboardInterrupt:
        emit(phase='canceled')
        return 130
    except Exception as exc:
        emit(phase='error', message=str(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
