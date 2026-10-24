"""Run the real Qt event loop and IPC without controller/audio hardware."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from voice_input import runtime


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'requires desktop dependencies')
class DesktopLifecycleTest(unittest.TestCase):
    def test_reopen_and_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / f'voice-input-{runtime.KEY}'
            env = dict(os.environ, XDG_RUNTIME_DIR=temp, QT_QPA_PLATFORM='offscreen')
            code = ("from voice_input import desktop\n"
                    "desktop.Window.start = lambda self: self.status.setText('Test ready')\n"
                    "raise SystemExit(desktop.main())\n")
            proc = subprocess.Popen([sys.executable, '-c', code], cwd=runtime.ROOT,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                with patch.object(runtime, 'STATE', state):
                    for _ in range(100):
                        if Path(runtime.socket_path()).exists():
                            break
                        self.assertIsNone(proc.poll())
                        time.sleep(.05)
                    self.assertTrue(runtime.desktop_command('show'))
                    reopened = subprocess.run([sys.executable, '-m', 'voice_input.desktop'],
                                              cwd=runtime.ROOT, env=env, timeout=5)
                    self.assertEqual(reopened.returncode, 0)
                    self.assertIsNone(proc.poll())
                    self.assertTrue(runtime.stop_desktop())
                    self.assertEqual(proc.wait(timeout=5), 0)
                    self.assertTrue(runtime.stop_worker())
                    self.assertTrue(runtime.stop_worker())
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                proc.communicate()


if __name__ == '__main__':
    unittest.main()
