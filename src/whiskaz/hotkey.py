"""Globale Push-to-talk-Taste. Läuft in einem pynput-Thread, gibt Qt-Signals an die UI weiter.

Zwei Modi:
- "hold": gedrückt halten startet, Loslassen stoppt. Andere Taste während des Haltens bricht ab.
- "toggle": jeder Tastendruck schaltet um. Loslassen wird ignoriert."""

import threading

from PySide6.QtCore import QObject, Signal
from pynput import keyboard

# Autorepeat sendet unter X11 Release+Press in schneller Folge. Ein Release wird
# deshalb kurz verzögert, und ein sofort folgendes Press hebt es auf.
RELEASE_DEBOUNCE_S = 0.06


def resolve_key(name: str):
    name = name.strip()
    if hasattr(keyboard.Key, name):
        return getattr(keyboard.Key, name)
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unbekannte Taste: {name}")


class HotkeyListener(QObject):
    pressed = Signal()  # hold: Start; toggle: jeder Tastendruck
    released = Signal()  # nur Modus "hold"
    interrupted = Signal()  # nur Modus "hold": andere Taste während des Haltens

    def __init__(self, key_name: str, mode: str = "hold"):
        super().__init__()
        self._target = resolve_key(key_name)
        self._mode = mode
        self._down = False
        self._active = False
        self._release_timer: threading.Timer | None = None
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._release_timer is not None:
            self._release_timer.cancel()
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key):
        if key == self._target:
            if self._release_timer is not None:
                # Autorepeat: Release und sofortiges Press, kein neuer Tastendruck
                self._release_timer.cancel()
                self._release_timer = None
                return
            if self._down:
                return
            self._down = True
            if self._mode == "hold":
                self._active = True
            self.pressed.emit()
        elif self._mode == "hold" and self._active:
            self._active = False
            self.interrupted.emit()

    def _on_release(self, key):
        if key != self._target or not self._down:
            return
        self._down = False
        self._release_timer = threading.Timer(RELEASE_DEBOUNCE_S, self._emit_released)
        self._release_timer.daemon = True
        self._release_timer.start()

    def _emit_released(self):
        self._release_timer = None
        if self._mode == "hold" and self._active:
            self._active = False
            self.released.emit()
