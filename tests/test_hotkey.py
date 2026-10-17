import time

import pytest

pytest.importorskip("pynput.keyboard")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from pynput.keyboard import Key, KeyCode  # noqa: E402

from whiskaz.hotkey import HotkeyListener  # noqa: E402

app = QCoreApplication.instance() or QCoreApplication([])


def collect(listener):
    events = {"pressed": 0, "released": 0, "interrupted": 0}
    listener.pressed.connect(lambda: events.__setitem__("pressed", events["pressed"] + 1))
    listener.released.connect(lambda: events.__setitem__("released", events["released"] + 1))
    listener.interrupted.connect(lambda: events.__setitem__("interrupted", events["interrupted"] + 1))
    return events


def wait_debounce():
    # Signale aus dem Timer-Thread landen in der Warteschlange des Hauptthreads
    time.sleep(0.15)
    app.processEvents()


def test_hold_mode_press_and_release():
    listener = HotkeyListener("ctrl_r", "hold")
    events = collect(listener)
    listener._on_press(Key.ctrl_r)
    listener._on_press(Key.ctrl_r)  # Wiederholung ohne Loslassen
    listener._on_release(Key.ctrl_r)
    wait_debounce()
    assert events == {"pressed": 1, "released": 1, "interrupted": 0}


def test_hold_mode_other_key_interrupts():
    listener = HotkeyListener("ctrl_r", "hold")
    events = collect(listener)
    listener._on_press(Key.ctrl_r)
    listener._on_press(KeyCode.from_char("c"))  # Strg+C
    listener._on_release(Key.ctrl_r)
    wait_debounce()
    assert events == {"pressed": 1, "released": 0, "interrupted": 1}


def test_toggle_mode_each_press_is_a_toggle_and_release_is_ignored():
    listener = HotkeyListener("ctrl_r", "toggle")
    events = collect(listener)
    for _ in range(3):
        listener._on_press(Key.ctrl_r)
        listener._on_release(Key.ctrl_r)
        wait_debounce()
    assert events == {"pressed": 3, "released": 0, "interrupted": 0}


def test_toggle_mode_other_key_does_not_interrupt():
    listener = HotkeyListener("ctrl_r", "toggle")
    events = collect(listener)
    listener._on_press(Key.ctrl_r)
    listener._on_release(Key.ctrl_r)
    listener._on_press(KeyCode.from_char("c"))
    wait_debounce()
    assert events == {"pressed": 1, "released": 0, "interrupted": 0}


def test_autorepeat_release_and_immediate_press_counts_once_in_toggle_mode():
    listener = HotkeyListener("ctrl_r", "toggle")
    events = collect(listener)
    listener._on_press(Key.ctrl_r)
    listener._on_release(Key.ctrl_r)
    listener._on_press(Key.ctrl_r)  # Autorepeat innerhalb der Debounce-Zeit
    wait_debounce()
    assert events["pressed"] == 1
