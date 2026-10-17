import pytest

pytest.importorskip("pynput.keyboard")

from pynput.keyboard import Key  # noqa: E402

from whiskaz.inject import auto_send_keys  # noqa: E402


def test_auto_send_off_sends_nothing():
    assert auto_send_keys("off") is None
    assert auto_send_keys("unbekannt") is None


def test_auto_send_enter():
    assert auto_send_keys("enter") == (None, Key.enter)


def test_auto_send_ctrl_enter():
    assert auto_send_keys("ctrl_enter") == (Key.ctrl, Key.enter)
