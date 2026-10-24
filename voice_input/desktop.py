"""Native desktop window owning a single recognition subprocess."""
import signal
import sys

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QGuiApplication
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMainWindow,
                              QMenu, QPlainTextEdit, QPushButton, QSystemTrayIcon,
                              QVBoxLayout, QWidget)

from .bind import binding_label
from .binding_capture import BindingCapture
from .hidraw import load_config, save_config
from .runtime import ROOT, desktop_command, socket_path


class BindingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Change voice activation button')
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(440)
        self.candidate = None
        self.capture = None
        self.listening = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.current = QLabel('Current button: ' + binding_label(load_config().get('trigger')))
        layout.addWidget(self.current)
        self.message = QLabel('Pausing recognition; please wait...')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.detected = QLabel('New button: waiting for input')
        layout.addWidget(self.detected)
        self.buttons = QDialogButtonBox()
        self.confirm = self.buttons.addButton('Confirm', QDialogButtonBox.AcceptRole)
        self.cancel = self.buttons.addButton('Cancel', QDialogButtonBox.RejectRole)
        for button in (self.confirm, self.cancel):
            button.setMinimumHeight(38)
            button.setAutoDefault(False)
            button.setFocusPolicy(Qt.NoFocus)
        self.confirm.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.poll)

    def listen(self):
        if self.listening or self.candidate is not None:
            return
        self.listening = True
        try:
            self.capture = BindingCapture()
        except Exception as exc:
            self.message.setText(f'Cannot listen for buttons: {exc}')
            return
        self.message.setText('Press the button you want to bind. Hold a rear button for about half a second, then release.\nClick Confirm to save, or Cancel to keep the current binding.')
        self.timer.start()

    def poll(self):
        try:
            candidate = self.capture.poll()
        except Exception as exc:
            self.stop_capture()
            self.message.setText(f'Input capture failed: {exc}. Cancel and try again.')
            return
        if candidate is not None:
            self.candidate = candidate
            self.stop_capture()
            self.detected.setText('New button: ' + binding_label(candidate))
            self.message.setText('Button detected. Click Confirm to save or Cancel to keep the current binding.')
            self.confirm.setEnabled(True)
            self.confirm.setFocusPolicy(Qt.StrongFocus)
            self.cancel.setFocusPolicy(Qt.StrongFocus)

    def stop_capture(self):
        self.timer.stop()
        if self.capture:
            self.capture.close()
            self.capture = None

    def accept(self):
        if self.candidate is None:
            return
        try:
            cfg = load_config()
            cfg['trigger'] = dict(self.candidate)
            save_config(cfg)
        except Exception as exc:
            self.message.setText(f'Save failed: {exc}. Retry or cancel this change.')
            return
        super().accept()

    def done(self, result):
        self.stop_capture()
        super().done(result)

    def keyPressEvent(self, event):
        # Physical keys, including Enter/Escape, are candidates; only explicit
        # button clicks/window close should confirm or cancel this operation.
        event.accept()


class Window(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.exiting = False
        self.setWindowTitle('Voice Input')
        self.setWindowIcon(QIcon(str(ROOT / 'packaging/voice-input.svg')))
        self.resize(660, 460)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.status = QLabel('Starting...')
        font = self.status.font()
        font.setPointSize(18)
        self.status.setFont(font)
        layout.addWidget(self.status)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.refresh_binding()
        self.model = QLabel()
        self.model.setWordWrap(True)
        layout.addWidget(self.model)
        row = QHBoxLayout()
        self.start_button = QPushButton('Start recognition')
        self.stop_button = QPushButton('Stop recognition')
        self.bind_button = QPushButton('Rebind button')
        for button in (self.start_button, self.stop_button, self.bind_button):
            button.setMinimumHeight(42)
            row.addWidget(button)
        layout.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText('Startup details, transcripts, and errors appear here.')
        self.log.document().setMaximumBlockCount(500)
        layout.addWidget(self.log, 1)
        self.exit_button = QPushButton('Quit application')
        self.exit_button.setMinimumHeight(38)
        self.exit_button.clicked.connect(self.shutdown)
        layout.addWidget(self.exit_button)
        self.worker = QProcess(self)
        self.worker.setWorkingDirectory(str(ROOT))
        self.worker.setProcessChannelMode(QProcess.MergedChannels)
        self.worker.readyReadStandardOutput.connect(self.read_output)
        self.worker.finished.connect(self.finished)
        self.worker.errorOccurred.connect(self.process_error)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.bind_button.clicked.connect(self.bind)
        self.binding_dialog = None
        self.resume_after_binding = False
        self.restart_after_stop = False
        self.pending = b''
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.windowIcon(), self)
            self.tray.setToolTip('Voice Input')
            menu = QMenu(self)
            show_action = QAction('Open Voice Input', self)
            show_action.triggered.connect(self.reveal)
            menu.addAction(show_action)
            quit_action = QAction('Quit application', self)
            quit_action.triggered.connect(self.shutdown)
            menu.addAction(quit_action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda _reason: self.reveal())
            self.tray.show()
        QTimer.singleShot(0, self.start)

    def reveal(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def launch(self, args):
        self.pending = b''
        self.start_button.setEnabled(False)
        self.bind_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.worker.start(sys.executable, ['-u', '-m', 'voice_input.main', *args])

    def start(self):
        if self.worker.state() != QProcess.NotRunning:
            return
        if self.binding_dialog is not None:
            return
        self.restart_after_stop = False
        self.refresh_binding()
        cfg = load_config()
        self.model.setText(f"Current model: {cfg.get('asr', {}).get('model', 'zh14m')} - Run init.sh to change models")
        self.status.setText('Loading model...')
        self.launch(['run'])

    def refresh_binding(self):
        label = binding_label(load_config().get('trigger'))
        self.hint.setText(f'Current activation button: {label}\nHold to dictate; release to deactivate. Pauses finalize text segments.')

    def bind(self):
        if self.binding_dialog is not None:
            self.binding_dialog.raise_()
            return
        self.restart_after_stop = False
        self.resume_after_binding = self.worker.state() != QProcess.NotRunning
        dialog = BindingDialog(self)
        self.binding_dialog = dialog
        dialog.finished.connect(self.binding_done)
        dialog.open()
        if self.resume_after_binding:
            self.stop()
        else:
            dialog.listen()

    def binding_done(self, result):
        dialog = self.binding_dialog
        self.binding_dialog = None
        self.refresh_binding()
        if result == QDialog.Accepted:
            self.log.appendPlainText('Activation button changed: ' + binding_label(dialog.candidate))
        else:
            self.log.appendPlainText('Binding change canceled; the previous button is unchanged.')
        dialog.deleteLater()
        if self.resume_after_binding and not self.exiting:
            if self.worker.state() == QProcess.NotRunning:
                self.start()
            else:
                self.restart_after_stop = True
        self.resume_after_binding = False

    def stop(self):
        if self.worker.state() != QProcess.NotRunning:
            self.status.setText('Stopping...')
            self.stop_button.setEnabled(False)
            self.worker.terminate()

    def process_error(self, error):
        self.log.appendPlainText(f'Process error: {self.worker.errorString()}')
        if error == QProcess.FailedToStart:
            self.finished(1, QProcess.CrashExit)

    def read_output(self):
        self.pending += bytes(self.worker.readAllStandardOutput())
        while b'\n' in self.pending:
            line, self.pending = self.pending.split(b'\n', 1)
            text = line.decode('utf-8', errors='replace')
            self.log.appendPlainText(text)
            if '== Ready' in text:
                self.status.setText('Ready - hold your activation button')
            elif text.startswith('●'):
                self.status.setText('Listening - release to stop')
            elif text.startswith('○') and 'continue listening' not in text:
                self.status.setText('Ready - hold your activation button')

    def finished(self, code, _status):
        self.read_output()
        if self.pending:
            self.log.appendPlainText(self.pending.decode('utf-8', errors='replace'))
            self.pending = b''
        self.start_button.setEnabled(True)
        self.bind_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status.setText('Stopped' if code == 0 else 'Startup or recognition failed - see the log')
        if self.exiting:
            self.app.quit()
        elif self.binding_dialog is not None:
            self.binding_dialog.listen()
        elif self.restart_after_stop:
            self.restart_after_stop = False
            self.start()

    def shutdown(self):
        self.exiting = True
        if self.binding_dialog is not None:
            self.binding_dialog.reject()
        if self.worker.state() == QProcess.NotRunning:
            self.app.quit()
        else:
            self.stop()

    def closeEvent(self, event):
        # A taskbar entry remains available even on desktops without a tray.
        if not self.exiting:
            event.ignore()
            self.showMinimized()
        else:
            event.accept()


def main():
    # Hold a lock while checking/removing stale sockets and starting the server.
    # Concurrent desktop launches cannot delete each other's live endpoint.
    import fcntl
    from .runtime import state_dir
    if '--check' in sys.argv:
        app = QApplication(['voice-input-check'])
        print(f'Qt available: {QGuiApplication.platformName()}')
        return 0
    with (state_dir() / 'desktop.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if desktop_command('show'):
            return 0
        app = QApplication(sys.argv)
        app.setApplicationName('voice-input')
        app.setQuitOnLastWindowClosed(False)
        QGuiApplication.setDesktopFileName('voice-input')
        server = QLocalServer()
        QLocalServer.removeServer(socket_path())
        if not server.listen(socket_path()):
            raise RuntimeError(server.errorString())
    window = Window(app)
    connections = set()

    def connected():
        while server.hasPendingConnections():
            client = server.nextPendingConnection()
            connections.add(client)
            buffer = bytearray()

            def receive(client=client, buffer=buffer):
                buffer.extend(bytes(client.readAll()))
                if b'\n' not in buffer:
                    return
                command = bytes(buffer).split(b'\n', 1)[0]
                client.write(b'OK\n')
                client.flush()
                client.disconnectFromServer()
                if command == b'stop':
                    window.shutdown()
                else:
                    window.reveal()

            client.readyRead.connect(receive)
            client.disconnected.connect(lambda client=client: (connections.discard(client), client.deleteLater()))
            if client.bytesAvailable():
                receive()
    server.newConnection.connect(connected)
    signal.signal(signal.SIGTERM, lambda *_: window.shutdown())
    signal.signal(signal.SIGINT, lambda *_: window.shutdown())
    tick = QTimer()
    tick.timeout.connect(lambda: None)
    tick.start(250)
    window.show()
    result = app.exec()
    server.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
