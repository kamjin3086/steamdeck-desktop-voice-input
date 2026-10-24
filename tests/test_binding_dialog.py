"""Confirmation/cancellation and live worker transitions for rebinding."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import copy
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QProcess, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from voice_input import desktop
from voice_input.binding_capture import BindingCapture
from voice_input import evdevraw as ev

OLD = {'source': 'hidraw', 'report_id': 1, 'byte': 9, 'bit': 7}
NEW = {'source': 'evdev-key', 'code': 68}


class BindingDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cfg = {'trigger': OLD, 'asr': {'model': 'zh14m'}}
        self.saved = []
        self.capture = MagicMock()
        self.capture.poll.return_value = NEW
        self.patches = [patch.object(desktop, 'load_config', side_effect=lambda: copy.deepcopy(self.cfg)),
                        patch.object(desktop, 'save_config', side_effect=self.save),
                        patch.object(desktop, 'BindingCapture', return_value=self.capture)]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def save(self, cfg):
        self.saved.append(copy.deepcopy(cfg))
        self.cfg = cfg

    def dialog(self):
        dialog = desktop.BindingDialog()
        dialog.show()
        dialog.listen()
        return dialog

    def test_candidate_is_displayed_but_only_confirm_saves(self):
        dialog = self.dialog()
        self.assertFalse(dialog.confirm.isEnabled())
        dialog.poll()
        self.assertIn('F10', dialog.detected.text())
        self.assertEqual(self.saved, [])
        self.capture.close.assert_called_once()
        QTest.mouseClick(dialog.confirm, Qt.LeftButton)
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(self.cfg['trigger'], NEW)
        self.assertEqual(self.cfg['asr'], {'model': 'zh14m'})

    def test_cancel_after_detection_keeps_old_binding(self):
        dialog = self.dialog()
        dialog.poll()
        QTest.mouseClick(dialog.cancel, Qt.LeftButton)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.cfg['trigger'], OLD)

    def test_close_before_input_keeps_old_binding_and_closes_devices(self):
        dialog = self.dialog()
        dialog.close()
        self.assertEqual(self.saved, [])
        self.assertFalse(dialog.timer.isActive())
        self.capture.close.assert_called_once()

    def test_enter_is_not_an_implicit_confirmation(self):
        dialog = self.dialog()
        dialog.poll()
        QTest.keyClick(dialog, Qt.Key_Return)
        self.assertEqual(self.saved, [])
        dialog.reject()

    def test_save_failure_keeps_dialog_open_and_can_cancel(self):
        dialog = self.dialog()
        dialog.poll()
        with patch.object(desktop, 'save_config', side_effect=OSError('read-only')):
            dialog.accept()
        self.assertTrue(dialog.isVisible())
        self.assertIn('Save failed', dialog.message.text())
        self.assertEqual(self.cfg['trigger'], OLD)
        dialog.reject()

    def test_running_worker_pauses_and_resumes_on_cancel(self):
        with patch.object(desktop.Window, 'start') as start:
            window = desktop.Window(self.app)
            self.app.processEvents()  # consume initial scheduled start
            start.reset_mock()
            worker = MagicMock()
            worker.state.return_value = QProcess.Running
            window.worker = worker
            window.bind()
            worker.terminate.assert_called_once()
            self.assertIsNotNone(window.binding_dialog)
            self.capture.poll.assert_not_called()
            # Cancel while the worker is still stopping.
            window.binding_dialog.reject()
            self.assertTrue(window.restart_after_stop)
            worker.state.return_value = QProcess.NotRunning
            worker.readAllStandardOutput.return_value = b''
            window.finished(0, QProcess.NormalExit)
            start.assert_called_once()
            self.assertEqual(self.saved, [])
            window.exiting = True
            window.close()


    def test_stopped_worker_stays_stopped_after_confirmation(self):
        with patch.object(desktop.Window, 'start') as start:
            window = desktop.Window(self.app)
            self.app.processEvents()
            start.reset_mock()
            window.bind()
            dialog = window.binding_dialog
            dialog.poll()
            dialog.accept()
            self.assertEqual(self.cfg['trigger'], NEW)
            self.assertIn('F10', window.hint.text())
            start.assert_not_called()
            window.exiting = True
            window.close()

    def test_running_worker_resumes_with_confirmed_binding(self):
        with patch.object(desktop.Window, 'start') as start:
            window = desktop.Window(self.app)
            self.app.processEvents()
            start.reset_mock()
            worker = MagicMock()
            worker.state.return_value = QProcess.Running
            worker.readAllStandardOutput.return_value = b''
            window.worker = worker
            window.bind()
            worker.state.return_value = QProcess.NotRunning
            window.finished(0, QProcess.NormalExit)
            window.binding_dialog.poll()
            window.binding_dialog.accept()
            self.assertEqual(self.cfg['trigger'], NEW)
            start.assert_called_once()
            window.exiting = True
            window.close()


class CaptureTest(unittest.TestCase):
    def test_hid_reports_capture_l5_without_saving(self):
        raw = MagicMock()
        base = bytes(64)
        down = bytearray(base)
        down[0] = 1
        down[9] = 128
        base = bytes([1]) + bytes(63)
        raw.poll.side_effect = [[('deck', base)], [('deck', bytes(down))], [('deck', base)]]
        with patch('voice_input.binding_capture.find_deck_hidraws', return_value=['deck']), \
             patch('voice_input.binding_capture.HidrawReader', return_value=raw), \
             patch('voice_input.binding_capture.ev.list_devices', return_value=[]), \
             patch('voice_input.binding_capture.time.monotonic', side_effect=[0, .1, .6]):
            capture = BindingCapture()
            self.assertIsNone(capture.poll())
            self.assertIsNone(capture.poll())
            self.assertEqual(capture.poll(), OLD)
            capture.close()
            raw.__exit__.assert_called_once()

    def test_mouse_clicks_ignored_keyboard_detected(self):
        device = MagicMock()
        device.read.side_effect = [[], [(ev.EV_KEY, 0x110, 1)], [(ev.EV_KEY, 68, 1)]]
        with patch('voice_input.binding_capture.find_deck_hidraws', return_value=[]), \
             patch('voice_input.binding_capture.ev.list_devices', return_value=[device]):
            capture = BindingCapture()
            self.assertIsNone(capture.poll())
            self.assertEqual(capture.poll(), NEW)
            capture.close()
            device.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
