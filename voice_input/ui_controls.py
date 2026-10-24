"""Explicit UI commands unaffected by controller keyboard mappings."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class CommandButton(QPushButton):
    """Hardware trigger mappings must never activate a focused UI command."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAutoDefault(False)

    def keyPressEvent(self, event):
        event.accept()

    def keyReleaseEvent(self, event):
        event.accept()
