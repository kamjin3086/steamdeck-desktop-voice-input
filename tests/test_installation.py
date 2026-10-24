"""Installer filesystem behavior and safe process ownership."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from voice_input import models_registry, runtime, setup
from voice_input.backends.local_sherpa import SherpaSession, find_model_files


class InstallationTest(unittest.TestCase):
    def test_shortcuts_repeat_and_repair_without_touching_config(self):
        with tempfile.TemporaryDirectory(prefix='voice input ') as temp:
            root = Path(temp)
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(root / 'data')}), \
                 patch.object(setup, 'desktop_dir', return_value=root / 'Desktop'), \
                 patch.object(setup, 'ROOT', root / 'project $with "quotes" %value'), \
                 patch.object(setup.subprocess, 'run'):
                setup.install_shortcut()
                desktop = root / 'Desktop/voice-input.desktop'
                expected = desktop.read_text()
                setup.install_shortcut()
                self.assertEqual(desktop.read_text(), expected)
                desktop.unlink()
                setup.install_shortcut()
                self.assertEqual(desktop.read_text(), expected)
                self.assertTrue(os.access(desktop, os.X_OK))
                self.assertIn('Terminal=false', expected)
                self.assertIn('%%value', expected)
                subprocess.run(['/usr/bin/desktop-file-validate', str(desktop)], check=True)

    def test_installer_explains_default_and_preserves_custom_binding(self):
        import contextlib
        import io
        from unittest.mock import MagicMock
        cfg = {'trigger': {'source': 'evdev-key', 'code': 68}}
        output = io.StringIO()
        with patch.object(setup, 'load_config', return_value=cfg), \
             patch.object(setup, 'save_config') as save, \
             patch.object(setup, 'install_shortcut'), \
             patch.object(setup.registry, 'install'), \
             patch.object(setup, 'create_backend', return_value=MagicMock()), \
             patch.object(setup.subprocess, 'run'), \
             patch.object(setup.shutil, 'which', return_value='/usr/bin/tool'), \
             patch.object(setup.os, 'access', return_value=True), \
             contextlib.redirect_stdout(output):
            self.assertEqual(setup.main(['--model', 'whisper-small', '--language', 'en', '--no-launch']), 0)
        self.assertEqual(save.call_args.args[0]['asr']['language'], 'en')
        self.assertIn('The default voice activation button is L5', output.getvalue())
        self.assertIn('Current activation button: F10. Hold to use; release to deactivate', output.getvalue())
        self.assertEqual(save.call_args.args[0]['trigger'], {'source': 'evdev-key', 'code': 68})

    def test_partial_model_directory_fails_verification(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(models_registry, 'MODELS_DIR', temp):
            path = Path(models_registry.model_dir('bilingual'))
            path.mkdir()
            (path / 'encoder.onnx').touch()
            self.assertTrue(models_registry.verify('bilingual'))

    def test_whisper_does_not_require_joiner(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('small-encoder.int8.onnx', 'small-decoder.int8.onnx', 'small-tokens.txt'):
                (Path(temp) / name).touch()
            self.assertIsNone(find_model_files(temp)['joiner'])

    def test_offline_uses_offline_decode_api(self):
        from unittest.mock import MagicMock
        recognizer = MagicMock()
        recognizer.create_stream.return_value.result.text = '\u4f60\u597d'
        session = SherpaSession(recognizer, streaming=False)
        session.accept(b'\0\0' * 1600)
        self.assertEqual(session.finish(), '\u4f60\u597d')
        recognizer.decode_stream.assert_called_once()
        recognizer.is_ready.assert_not_called()
        recognizer.create_stream.return_value.input_finished.assert_not_called()

    def test_worker_single_instance_and_safe_repeat_stop(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(runtime, 'STATE', Path(temp)):
            script = '''import sys, time
from pathlib import Path
from voice_input import runtime
runtime.STATE = Path(sys.argv[1])
with runtime.worker_lock():
 print('ready', flush=True)
 time.sleep(30)
'''
            proc = subprocess.Popen([sys.executable, '-c', script, temp], cwd=runtime.ROOT,
                                    stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(), 'ready')
                with self.assertRaises(SystemExit):
                    with runtime.worker_lock():
                        pass
                # An unrelated Python process must not be killed by stop.sh.
                self.assertFalse(runtime.stop_worker(timeout=.1))
                self.assertIsNone(proc.poll())
            finally:
                proc.terminate()
                proc.wait(timeout=3)
                proc.stdout.close()
            self.assertTrue(runtime.stop_worker())
            self.assertTrue(runtime.stop_worker())


if __name__ == '__main__':
    unittest.main()
