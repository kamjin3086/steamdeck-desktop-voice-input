"""Spike qt checks."""

from __future__ import annotations

import sys

try:
    from PySide6.QtCore import QTimer, Qt, qVersion
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import (
        QApplication, QLabel, QSystemTrayIcon, QVBoxLayout, QWidget,
    )
except ImportError as exc:  # noqa: BLE001
    print(f"PySide6 is not installed: {exc}")
    sys.exit(2)


app = QApplication(sys.argv)
print(f"Qt version: {qVersion()}")
print(f"Platform plugin: {QGuiApplication.platformName()}")
screen = app.primaryScreen()
print(f"Screen: {screen.geometry().width()}x{screen.geometry().height()} "
      f"dpr={screen.devicePixelRatio()}")

tray_ok = QSystemTrayIcon.isSystemTrayAvailable()
print(f"System tray available: {tray_ok}")

win = QWidget()
win.setWindowTitle("voice-input Qt spike")
layout = QVBoxLayout(win)
layout.addWidget(QLabel("Unicode rendering: hold to speak, recognize, insert text"))
layout.addWidget(QLabel(f"platform = {QGuiApplication.platformName()}"))
win.resize(420, 140)
win.show()

tray = None
if tray_ok:
    tray = QSystemTrayIcon(win)
    tray.setToolTip("voice-input spike")
    tray.show()

timer = QTimer()
timer.timeout.connect(app.quit)
timer.start(2500)
app.exec()
print("OK: Qt window works" + ("(with system tray)" if tray_ok else "(no system tray)"))
