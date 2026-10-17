from PySide6.QtCore import QRect

from whiskaz.overlay import HEIGHT, MARGIN, WIDTH, overlay_position

AREA = QRect(0, 0, 1920, 1080)


def test_anchor_left_center_right():
    assert overlay_position("left", None, AREA) == (MARGIN, MARGIN)
    assert overlay_position("center", None, AREA) == (AREA.center().x() - WIDTH // 2, MARGIN)
    assert overlay_position("right", None, AREA) == (AREA.right() - WIDTH - MARGIN, MARGIN)


def test_saved_position_wins_over_anchor():
    assert overlay_position("left", [300, 400], AREA) == (300, 400)


def test_saved_position_is_clamped_onto_screen():
    assert overlay_position("center", [-500, -500], AREA) == (0, 0)
    x, y = overlay_position("center", [5000, 5000], AREA)
    assert x == AREA.right() - WIDTH + 1
    assert y == AREA.bottom() - HEIGHT + 1


def test_offset_area_is_respected():
    area = QRect(100, 50, 1000, 800)
    x, y = overlay_position("left", None, area)
    assert (x, y) == (100 + MARGIN, 50 + MARGIN)
