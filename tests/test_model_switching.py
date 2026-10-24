"""Model download state, persistence, cancellation, and language grouping."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QDialog
from voice_input import models_registry as registry, model_dialog, setup
from voice_input.backends.local_sherpa import SherpaSession, find_model_files


class ModelSwitchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cfg = {'trigger': {'source': 'evdev-key', 'code': 68},
                    'asr': {'model': 'sensevoice', 'backend': 'local'}}
        self.saves = []
        self.patchers = [patch.object(model_dialog, 'load_config', side_effect=lambda: copy.deepcopy(self.cfg)),
                         patch.object(model_dialog, 'save_config', side_effect=self.save)]
        for p in self.patchers: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patchers)])

    def save(self, cfg):
        self.cfg = cfg
        self.saves.append(copy.deepcopy(cfg))

    def make_dialog(self):
        dialog = model_dialog.ModelDialog()
        dialog.allow_switch()
        proc = MagicMock()
        proc.state.return_value = QProcess.NotRunning
        proc.readAllStandardOutput.return_value = b''
        dialog.process = proc
        return dialog, proc

    def test_exactly_three_language_groups(self):
        self.assertEqual(list(registry.selectable_models()), ['sensevoice', 'qwen3', 'omnilingual'])
        self.assertEqual(registry.DEFAULT_MODEL, 'sensevoice')
        dialog, _ = self.make_dialog()
        self.assertEqual(dialog.choices.count(), 3)
        self.assertIn('Cantonese', dialog.details.text())
        dialog.reject()

    def test_success_saves_only_after_loading_and_reuses_an_installed_model(self):
        dialog, proc = self.make_dialog()
        dialog.choices.setCurrentIndex(dialog.choices.findData('qwen3'))
        dialog.switch()
        self.assertEqual(self.saves, [])
        self.assertIn('qwen3', proc.start.call_args.args[1])
        # A real successful child sends ready only after backend loading.
        proc.readAllStandardOutput.return_value = b'{"phase":"ready","model":"qwen3"}\n'
        dialog.prepared(0, QProcess.NormalExit)
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(self.cfg['asr']['model'], 'qwen3')
        self.assertEqual(self.cfg['trigger']['code'], 68)

    def test_error_keeps_old_model_and_shows_retry_state(self):
        dialog, proc = self.make_dialog()
        dialog.target = 'qwen3'
        proc.readAllStandardOutput.return_value = b'{"phase":"error","message":"download interrupted"}\n'
        dialog.prepared(1, QProcess.NormalExit)
        self.assertEqual(self.saves, [])
        self.assertIn('download interrupted', dialog.status.text())
        self.assertTrue(dialog.change.isEnabled())
        dialog.reject()

    def test_visible_byte_progress_and_extraction_state(self):
        dialog, proc = self.make_dialog()
        proc.readAllStandardOutput.return_value = b'{"phase":"downloading","done":25,"total":100}\n'
        dialog.read_progress()
        self.assertEqual(dialog.progress.value(), 250)
        self.assertIn('Downloading:', dialog.status.text())
        proc.readAllStandardOutput.return_value = b'{"phase":"extracting"}\n'
        dialog.read_progress()
        self.assertIn('Extracting', dialog.status.text())
        dialog.reject()

    def test_cancel_during_download_never_persists(self):
        dialog, proc = self.make_dialog()
        proc.state.return_value = QProcess.Running
        dialog.reject()
        proc.terminate.assert_called_once()
        proc.state.return_value = QProcess.NotRunning
        dialog.ready_model = dialog.target = 'qwen3'
        dialog.prepared(0, QProcess.NormalExit)
        self.assertEqual(self.saves, [])
        self.assertEqual(self.cfg['asr']['model'], 'sensevoice')

    def test_save_error_does_not_change_selected_model(self):
        dialog, proc = self.make_dialog()
        dialog.target = 'qwen3'
        dialog.ready_model = 'qwen3'
        with patch.object(model_dialog, 'save_config', side_effect=OSError('read-only')):
            dialog.prepared(0, QProcess.NormalExit)
        self.assertIn('Could not save', dialog.status.text())
        self.assertEqual(self.cfg['asr']['model'], 'sensevoice')
        dialog.reject()

    def test_sensevoice_metadata_is_not_dictated(self):
        rec = MagicMock()
        rec.create_stream.return_value.result.text = '<|en|><|NEUTRAL|><|Speech|>hello<|withitn|>'
        session = SherpaSession(rec, streaming=False, clean_tags=True)
        session.accept(b'\0\0' * 100)
        self.assertEqual(session.finish(), 'hello')
        rec.create_stream.return_value.accept_waveform.assert_called_once()

    def test_qwen_missing_tokenizer_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ['conv_frontend.onnx', 'encoder.int8.onnx', 'decoder.int8.onnx']:
                (root / name).touch()
            with self.assertRaises(FileNotFoundError):
                find_model_files(temp)

class RegistryTransactionTest(unittest.TestCase):
    def test_bad_download_preserves_old_directory_and_cleans_temporary_files(self):
        import io
        import tarfile
        blob = io.BytesIO()
        with tarfile.open(fileobj=blob, mode='w:bz2') as archive:
            info = tarfile.TarInfo('fake/encoder.onnx')
            info.size = 3
            archive.addfile(info, io.BytesIO(b'bad'))
        response = io.BytesIO(blob.getvalue())
        response.headers = {'Content-Length': str(len(blob.getvalue()))}
        spec = {'dir': 'fake', 'url': 'https://example.invalid/model', 'streaming': False, 'files': {}}
        with tempfile.TemporaryDirectory() as temp, patch.object(registry, 'MODELS_DIR', temp), \
             patch.object(registry, 'get', return_value=spec), \
             patch.object(registry.urllib.request, 'urlopen', return_value=response):
            target = Path(temp) / 'fake'
            target.mkdir()
            (target / 'previous').write_text('keep')
            with self.assertRaises(RuntimeError):
                registry.install('fake')
            self.assertEqual((target / 'previous').read_text(), 'keep')
            self.assertEqual(list(Path(temp).iterdir()), [target])

    def test_valid_cached_model_never_downloads_again(self):
        spec = {'dir': 'fake', 'url': 'https://example.invalid/model', 'streaming': False, 'files': {}}
        with tempfile.TemporaryDirectory() as temp, patch.object(registry, 'MODELS_DIR', temp), \
             patch.object(registry, 'get', return_value=spec), \
             patch.object(registry.urllib.request, 'urlopen') as download:
            target = Path(temp) / 'fake'
            target.mkdir()
            (target / 'model.int8.onnx').write_bytes(b'model')
            (target / 'tokens.txt').write_text('tokens')
            self.assertEqual(registry.install('fake'), str(target))
            download.assert_not_called()



if __name__ == '__main__':
    unittest.main()
