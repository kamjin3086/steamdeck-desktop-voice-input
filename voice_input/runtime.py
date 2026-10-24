"""Per-checkout process ownership; no broad process-name matching."""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import socket
import time

ROOT = Path(__file__).resolve().parent.parent
KEY = hashlib.sha256(os.fsencode(ROOT)).hexdigest()[:16]
STATE = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/voice-input-{os.getuid()}')) / f'voice-input-{KEY}'


def state_dir():
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE.stat().st_uid != os.getuid() or STATE.is_symlink():
        raise RuntimeError(f'Unsafe runtime directory: {STATE}')
    STATE.chmod(0o700)
    return STATE


def socket_path():
    return str(state_dir() / 'desktop.sock')


def desktop_command(command):
    try:
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(2)
            client.connect(socket_path())
            client.sendall((command + '\n').encode())
            return client.recv(32) == b'OK\n'
    except OSError:
        return False


@contextmanager
def worker_lock():
    with (state_dir() / 'worker.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('This checkout is already running. Open its window or run ./stop.sh first.')
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()
        try:
            yield
        finally:
            lock.seek(0)
            lock.truncate()


def stop_worker(timeout=8):
    path = state_dir() / 'worker.lock'
    with path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            lock.seek(0)
            value = lock.read().strip()
            if not value.isdigit():
                return False
            pid = int(value)
        # pidfd pins process identity, preventing PID-reuse races.
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            return True
        try:
            if Path(f'/proc/{pid}/cwd').resolve() != ROOT:
                return False
            cmd = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
            if b'voice_input.main' not in cmd:
                return False
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    time.sleep(.1)
            return False
        except ProcessLookupError:
            return True
        finally:
            os.close(fd)


def stop_desktop(timeout=10):
    if not desktop_command('stop'):
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # Do not send another command: just observe server shutdown.
        try:
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(.2)
                client.connect(socket_path())
        except OSError:
            return True
        time.sleep(.1)
    return False


def stop():
    desktop_stopped = stop_desktop()
    if not stop_worker() or not desktop_stopped:
        print('The application has not exited. Check its log and try again.')
        return 1
    print('This checkout is stopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(stop())
