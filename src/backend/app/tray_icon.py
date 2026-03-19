from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen


def make_tray_icon(active: bool = True) -> QIcon:
    size = 64
    pix  = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QBrush(QColor("#1a1a1a")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    hand_color = QColor("#ffffff") if active else QColor("#3a3a3a")
    accent     = QColor("#bbbbbb") if active else QColor("#2a2a2a")

    pen = QPen(hand_color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(QBrush(hand_color))

    p.drawRoundedRect(20, 34, 24, 18, 5, 5)

    finger_xs = [22, 27, 32, 37, 42]
    heights   = [20, 14, 12, 14, 18]
    for x, dh in zip(finger_xs, heights):
        p.drawLine(x, 34, x, 34 - dh)
        p.drawEllipse(x - 2, 34 - dh - 4, 4, 4)

    p.setBrush(QBrush(accent))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(28, 50, 8, 8)

    p.end()
    return QIcon(pix)