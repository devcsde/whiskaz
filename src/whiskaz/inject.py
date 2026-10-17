"""Text an die Cursorposition bringen: ins Clipboard legen, einfügen, altes Clipboard wiederherstellen.

Muss im Qt-Hauptthread laufen, weil das Clipboard dort lebt."""

import sys

from PySide6.QtCore import QTimer
from pynput.keyboard import Controller, Key

PASTE_DELAY_MS = 120
RESTORE_DELAY_MS = 500


class Paster:
    def __init__(self, clipboard, terminal: bool = False):
        self._clipboard = clipboard
        self._terminal = terminal
        self._keyboard = Controller()

    def paste(self, text: str) -> None:
        previous = self._clipboard.text()
        self._clipboard.setText(text)
        QTimer.singleShot(PASTE_DELAY_MS, lambda: self._send_paste(text, previous))

    def _send_paste(self, text: str, previous: str) -> None:
        modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
        with self._keyboard.pressed(modifier):
            if self._terminal:
                with self._keyboard.pressed(Key.shift):
                    self._keyboard.tap("v")
            else:
                self._keyboard.tap("v")
        QTimer.singleShot(RESTORE_DELAY_MS, lambda: self._restore(text, previous))

    def _restore(self, pasted: str, previous: str) -> None:
        # Nur zurücksetzen, wenn in der Zwischenzeit niemand etwas anderes kopiert hat.
        if self._clipboard.text() == pasted:
            self._clipboard.setText(previous)
