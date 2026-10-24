"""Language-oriented model selection with visible, cancelable preparation."""
import json
import sys

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                              QProgressBar, QPushButton, QVBoxLayout)
from .ui_controls import CommandButton
from . import models_registry as registry
from .hidraw import load_config, save_config
from .runtime import ROOT


class ModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Speech recognition languages')
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(540)
        self.resize(570, 440)
        self.allowed = False
        self.canceling = False
        self.ready_model = None
        self.target = None
        self.pending = b''
        self.failure = ''
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_progress)
        self.process.finished.connect(self.prepared)
        self.process.errorOccurred.connect(self.process_error)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        title = QLabel('Which languages do you use?')
        font = title.font()
        font.setPointSize(17)
        title.setFont(font)
        layout.addWidget(title)
        self.choices = QComboBox()
        self.choices.setMinimumHeight(40)
        for name, spec in registry.selectable_models().items():
            self.choices.addItem(spec['name'], name)
        layout.addWidget(self.choices)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.PlainText)
        layout.addWidget(self.details)
        self.source = QLabel()
        self.source.setOpenExternalLinks(True)
        layout.addWidget(self.source)
        self.status = QLabel('Pausing recognition; please wait...')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.change = CommandButton('Download and switch')
        self.cancel = CommandButton('Cancel')
        for button in (self.change, self.cancel):
            button.setFocusPolicy(Qt.NoFocus)
            button.setAutoDefault(False)
            button.setMinimumHeight(40)
            row.addWidget(button)
        layout.addLayout(row)
        self.change.clicked.connect(self.switch)
        self.cancel.clicked.connect(self.reject)
        self.choices.currentIndexChanged.connect(self.selection_changed)
        current = load_config().get('asr', {}).get('model', registry.DEFAULT_MODEL)
        index = self.choices.findData(current)
        self.choices.setCurrentIndex(max(index, 0))
        self.selection_changed()

    def allow_switch(self):
        self.allowed = True
        self.status.setText('Select a language group. Other models download only when selected.')
        self.selection_changed()

    def selection_changed(self):
        name = self.choices.currentData()
        spec = registry.get(name)
        installed = registry.is_installed(name)
        size = spec.get('archive_bytes', 0) / 1e6
        self.details.setText('Languages: ' + ', '.join(spec.get('language_names', spec['languages']))
                             + '\n\n' + spec['note']
                             + f"\n\nEngine: {spec.get('engine', spec['name'])}"
                             + f"\n{'Installed; reusable without downloading.' if installed else f'Not installed; estimated download {size:.0f} MB.'}")
        url = spec.get('source_url', '')
        self.source.setText(f'<a href="{url}">Language coverage and model documentation</a>' if url else '')
        self.change.setText('Use this model' if installed else 'Download and switch')
        self.change.setEnabled(self.allowed and self.process.state() == QProcess.NotRunning)
        self.details.setMinimumHeight(self.details.heightForWidth(max(200, self.width() - 48)))
        self.resize(self.width(), max(self.height(), self.minimumSizeHint().height()))

    def switch(self):
        if not self.allowed or self.process.state() != QProcess.NotRunning:
            return
        self.target = self.choices.currentData()
        self.ready_model = None
        self.canceling = False
        self.failure = ''
        self.pending = b''
        self.choices.setEnabled(False)
        self.change.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText('Checking cached model and connecting if needed...')
        self.process.start(sys.executable, ['-u', '-m', 'voice_input.model_manager', self.target])

    def read_progress(self):
        self.pending += bytes(self.process.readAllStandardOutput())
        while b'\n' in self.pending:
            line, self.pending = self.pending.split(b'\n', 1)
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError):
                continue  # Upstream libraries may print non-protocol diagnostics.
            if not isinstance(event, dict):
                continue
            phase = event.get('phase')
            if phase == 'downloading':
                done, total = event.get('done', 0), event.get('total', 0)
                if total:
                    self.progress.setRange(0, 1000)
                    self.progress.setValue(min(1000, int(done * 1000 / total)))
                    self.status.setText(f'Downloading: {done / 1e6:.1f} / {total / 1e6:.1f} MB')
                else:
                    self.progress.setRange(0, 0)
                    self.status.setText(f'Downloading: {done / 1e6:.1f} MB (total size unavailable)')
            elif phase == 'ready':
                self.ready_model = event.get('model')
            elif phase == 'error':
                self.failure = event.get('message', 'Model preparation failed.')
            elif not self.canceling:
                self.progress.setRange(0, 0)
                self.status.setText({'checking': 'Checking installed files...',
                                     'connecting': 'Connecting to the model download...',
                                     'retrying': 'Connection interrupted; retrying...',
                                     'extracting': 'Extracting downloaded model...',
                                     'verifying': 'Verifying model files...',
                                     'loading': 'Loading model to verify compatibility...'
                                     }.get(phase, phase or 'Preparing model...'))

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.failure = self.process.errorString()
            self.prepared(1, QProcess.CrashExit)

    def prepared(self, code, _status):
        self.read_progress()
        if self.canceling:
            super().reject()
            return
        self.choices.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        if code != 0 or self.ready_model != self.target:
            self.status.setText('Model unchanged. ' + (self.failure or 'Preparation failed; retry or cancel.'))
            self.selection_changed()
            return
        try:
            cfg = load_config()
            cfg.setdefault('asr', {}).update(backend='local', model=self.target,
                language=registry.get(self.target).get('default_language', 'auto'))
            save_config(cfg)
        except Exception as exc:
            self.status.setText(f'Model unchanged. Could not save selection: {exc}')
            self.selection_changed()
            return
        self.progress.setValue(100)
        self.status.setText('Model ready and selected.')
        super().accept()

    def reject(self):
        if self.process.state() != QProcess.NotRunning:
            self.canceling = True
            self.cancel.setEnabled(False)
            self.status.setText('Canceling preparation; keeping the previous model...')
            self.process.terminate()
            QTimer.singleShot(3000, self.force_stop)
        else:
            super().reject()

    def force_stop(self):
        if self.canceling and self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def closeEvent(self, event):
        if self.process.state() != QProcess.NotRunning:
            self.reject()
            event.ignore()
        else:
            event.accept()
            self.reject()

    def keyPressEvent(self, event):
        event.accept()
