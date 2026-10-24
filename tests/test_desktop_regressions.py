"""Regression checks for hardware-button focus and desktop shutdown."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from voice_input import desktop


class DesktopRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mapped_space_does_not_reopen_binding_dialog(self):
        with patch.object(desktop.Window, 'start'), patch.object(desktop.Window, 'bind') as bind:
            window = desktop.Window(self.app)
            window.show()
            self.app.processEvents()
            # Steam Input may send Space after mouse interaction with a button.
            window.bind_button.setFocus()
            QTest.keyClick(window.bind_button, Qt.Key_Space)
            self.assertEqual(bind.call_count, 0)
            window.exiting = True
            window.close()

    def test_window_close_exits_instead_of_minimizing(self):
        with patch.object(desktop.Window, 'start'):
            window = desktop.Window(self.app)
            window.show()
            self.app.processEvents()
            window.close()
            self.assertTrue(window.exiting)
            self.assertFalse(window.isVisible())

    def test_close_forces_a_stuck_decoder_and_its_child_to_exit(self):
        import sys
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as temp, patch.object(desktop.Window, 'start'):
            window = desktop.Window(self.app)
            window.show()
            self.app.processEvents()
            pidfile = str(Path(temp) / 'child.pid')
            code = ("import signal, subprocess, sys, time; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                    "open(sys.argv[1],'w').write(str(child.pid)); time.sleep(60)")
            window.worker.start(sys.executable, ['-c', code, pidfile])
            try:
                self.assertTrue(window.worker.waitForStarted(2000))
                for _ in range(40):
                    if Path(pidfile).exists(): break
                    QTest.qWait(25)
                child = int(Path(pidfile).read_text())
                self.assertEqual(os.getpgid(window.worker.processId()), window.worker.processId())
                window.close()
                QTest.qWait(2800)
                self.assertEqual(window.worker.state(), QProcess.NotRunning)
                stat = Path(f'/proc/{child}/stat')
                self.assertTrue(not stat.exists() or stat.read_text().split()[2] == 'Z')
            finally:
                if window.worker.state() != QProcess.NotRunning:
                    os.killpg(window.worker.processId(), 9)
                    window.worker.waitForFinished(2000)



if __name__ == '__main__':
    unittest.main()
