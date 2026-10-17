"""Kleines Aufnahme-Overlay: zeigt während der Aufnahme Lampe und Pegel, lässt sich mit der Maus verschieben."""

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from whiskaz import theme

WIDTH = 220
HEIGHT = 44
MARGIN = 16
SEGMENTS = 16


def overlay_position(anchor: str, saved, area: QRect, width: int = WIDTH, height: int = HEIGHT) -> tuple[int, int]:
    """Gespeicherte Position hat Vorrang, sonst die Startposition oben links, Mitte oder rechts.
    Das Ergebnis wird so begrenzt, dass das Overlay auf dem Bildschirm bleibt."""
    if saved is not None:
        x, y = saved
    else:
        x = {
            "left": area.left() + MARGIN,
            "center": area.center().x() - width // 2,
            "right": area.right() - width - MARGIN,
        }.get(anchor, area.center().x() - width // 2)
        y = area.top() + MARGIN
    x = min(max(x, area.left()), area.right() - width + 1)
    y = min(max(y, area.top()), area.bottom() - height + 1)
    return x, y


class RecordingOverlay(QWidget):
    moved = Signal(int, int)  # nach dem Verschieben mit der Maus

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        # Der Fokus bleibt beim Fenster, in das später eingefügt wird.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)
        self._level = 0  # 0 bis 100
        self._drag_offset = None

    def set_level(self, level: int) -> None:
        self._level = level
        self.update()

    def show_at(self, x: int, y: int) -> None:
        self.move(x, y)
        self.show()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(theme.OVERLAY_BORDER), 1))
        painter.setBrush(QColor(theme.OVERLAY_BG))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), theme.OVERLAY_RADIUS, theme.OVERLAY_RADIUS)

        # Aufnahmelampe
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.REC_RED))
        painter.drawEllipse(QPointF(20, self.height() / 2), 6, 6)

        # Beschriftung
        font = QFont(painter.font())
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(theme.OVERLAY_TEXT))
        painter.drawText(QRect(32, 0, 40, self.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "REC")

        # Pegelanzeige aus Segmenten, die obersten drei zeigen Rot
        left, right, gap = 84, self.width() - 14, 2
        seg_w = (right - left - gap * (SEGMENTS - 1)) / SEGMENTS
        lit = round(self._level / 100 * SEGMENTS)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(SEGMENTS):
            if i < lit:
                color = theme.REC_RED if i >= SEGMENTS - 3 else theme.COLOR_LEVEL
            else:
                color = theme.OVERLAY_SEGMENT_OFF
            painter.setBrush(QColor(color))
            x = left + i * (seg_w + gap)
            painter.drawRect(QRectF(x, self.height() / 2 - 6, seg_w, 12))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None:
            self._drag_offset = None
            self.moved.emit(self.x(), self.y())
