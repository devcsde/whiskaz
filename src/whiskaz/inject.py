"""Text an die Cursorposition bringen: ins Clipboard legen, einfügen, altes Clipboard wiederherstellen.

Optional danach Enter oder Strg+Enter senden. Muss im Qt-Hauptthread laufen, weil das Clipboard dort lebt."""

import sys

from PySide6.QtCore import QTimer
from pynput.keyboard import Controller, Key

PASTE_DELAY_MS = 120
AUTO_SEND_DELAY_MS = 250  # damit die Zielapp das Einfügen verarbeitet hat, bevor Enter kommt
RESTORE_DELAY_MS = 500


def auto_send_keys(mode: str):
    """Gibt (Modifier, Taste) zurück, oder None, wenn nichts gesendet werden soll."""
    if mode == "enter":
        return None, Key.enter
    if mode == "ctrl_enter":
        return Key.ctrl, Key.enter
    return None


class Paster:
    def __init__(self, clipboard, terminal: bool = False, auto_send: str = "off"):
        self._clipboard = clipboard
        self._terminal = terminal
        self._auto_send = auto_send_keys(auto_send)
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
        if self._auto_send is not None:
            QTimer.singleShot(AUTO_SEND_DELAY_MS, self._send_auto_send)
        QTimer.singleShot(RESTORE_DELAY_MS, lambda: self._restore(text, previous))

    def _send_auto_send(self) -> None:
        modifier, key = self._auto_send
        if modifier is None:
            self._keyboard.tap(key)
            return
        with self._keyboard.pressed(modifier):
            self._keyboard.tap(key)

    def _restore(self, pasted: str, previous: str) -> None:
        # Nur zurücksetzen, wenn in der Zwischenzeit niemand etwas anderes kopiert hat.
        if self._clipboard.text() == pasted:
            self._clipboard.setText(previous)
