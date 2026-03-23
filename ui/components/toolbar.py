from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QRectF, QPoint
from PyQt6.QtGui import QCursor, QPainter, QColor, QFontMetrics
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy,
)
# ── SVG templates ─────────────────────────────────────────────────────────────
_SVG_MENU = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
    fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round">
  <line x1="4" y1="6" x2="20" y2="6"/>
  <line x1="4" y1="12" x2="20" y2="12"/>
  <line x1="4" y1="18" x2="20" y2="18"/>
</svg>"""
_SVG_CLOSE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
    fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round">
  <line x1="4" y1="4" x2="20" y2="20"/>
  <line x1="20" y1="4" x2="4" y2="20"/>
</svg>"""
_SVG_GESTURES = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
    fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2"/>
  <path d="M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v2"/>
  <path d="M10 10.5a2 2 0 0 0-2-2 2 2 0 0 0-2 2v1.5"/>
  <path d="M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8 2 2 0 1 1 4 0"/>
</svg>"""
_SVG_CONSOLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
    fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 17 10 11 4 5"/>
  <line x1="12" y1="19" x2="20" y2="19"/>
</svg>"""
_SVG_SETTINGS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
    fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06
           a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09
           A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83
           l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09
           A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83
           l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09
           a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83
           l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09
           a1.65 1.65 0 0 0-1.51 1z"/>
</svg>"""
_SVG_PAUSE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{c}">
  <rect x="6" y="4" width="4" height="16" rx="1"/>
  <rect x="14" y="4" width="4" height="16" rx="1"/>
</svg>"""
_SVG_RESUME = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{c}">
  <polygon points="5,3 19,12 5,21"/>
</svg>"""
_S = 36    # button size
_I = 16    # icon size
_O = (_S - _I) // 2  # icon offset = 10
# ── SVG button ────────────────────────────────────────────────────────────────
class _SvgButton(QPushButton):
    NORMAL = "n"
    ACTIVE = "a"
    PAUSE  = "p"
    def __init__(self, tpl: str, parent=None) -> None:
        super().__init__(parent)
        self._tpl     = tpl
        self._state   = self.NORMAL
        self._hovered = False
        self.setFixedSize(_S, _S)
        self.setFlat(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("background:transparent;border:none;")
    def set_svg(self, t: str)   -> None: self._tpl = t;   self.update()
    def set_state(self, s: str) -> None: self._state = s; self.update()
    def _bg(self) -> QColor:
        if self._state == self.ACTIVE: return QColor(255, 255, 255)
        if self._state == self.PAUSE:
            return QColor(239, 68, 68, 77 if self._hovered else 51)
        return QColor(42, 42, 42) if self._hovered else QColor(26, 26, 26)
    def _ic(self) -> str:
        if self._state == self.ACTIVE: return "#111111"
        if self._state == self.PAUSE:  return "#f87171"
        return "#ffffff" if self._hovered else "#b3b3b3"
    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._bg())
        p.drawEllipse(0, 0, _S, _S)
        QSvgRenderer(QByteArray(
            self._tpl.format(c=self._ic()).encode()
        )).render(p, QRectF(_O, _O, _I, _I))
        p.end()
    def enterEvent(self, e) -> None:
        self._hovered = True;  self.update(); super().enterEvent(e)
    def leaveEvent(self, e) -> None:
        self._hovered = False; self.update(); super().leaveEvent(e)
# ── row: label is painted as overlay, never affects layout ───────────────────
class _BtnRow(QWidget):
    """
    Always fixed at _S × _S.  The hover label is drawn by paintEvent as an
    overlay to the LEFT of the button — it never touches the layout, so the
    button position is 100% stable regardless of window size or hover state.
    """
    def __init__(self, btn: _SvgButton, label: str, parent=None) -> None:
        super().__init__(parent)
        self._label   = label
        self._hovered = False
        self.setFixedSize(_S, _S)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(btn)
    def set_label(self, text: str) -> None:
        self._label = text
        if self._hovered:
            self.update()
    def enterEvent(self, e) -> None:
        self._hovered = True;  self.update(); super().enterEvent(e)
    def leaveEvent(self, e) -> None:
        self._hovered = False; self.update(); super().leaveEvent(e)
    def paintEvent(self, e) -> None:
        super().paintEvent(e)
        if not self._hovered or not self._label:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = p.font()
        font.setPointSize(7)
        font.setWeight(600)
        p.setFont(font)
        fm   = QFontMetrics(font)
        text = self._label
        tw   = fm.horizontalAdvance(text)
        gap  = 8
        p.setPen(QColor(255, 255, 255, 102))
        p.drawText(-(tw + gap), (_S + fm.ascent() - fm.descent()) // 2, text)
        p.end()
# ── Toolbar ───────────────────────────────────────────────────────────────────
class Toolbar(QWidget):
    toggle_console   = pyqtSignal()
    toggle_active    = pyqtSignal()
    open_settings    = pyqtSignal()
    open_gestures    = pyqtSignal()
    geometry_changed = pyqtSignal()
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._open       = False
        self._console_on = False
        self._active     = True
        self.setStyleSheet("background:transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._build_ui()
        self.adjustSize()
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self._main_btn = _SvgButton(_SVG_MENU)
        self._main_btn.clicked.connect(self._toggle_menu)
        lay.addWidget(self._main_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self._dropdown = QWidget()
        self._dropdown.setStyleSheet("background:transparent;")
        drop = QVBoxLayout(self._dropdown)
        drop.setContentsMargins(0, 0, 0, 0)
        drop.setSpacing(6)
        drop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._btn_gestures = _SvgButton(_SVG_GESTURES)
        self._btn_gestures.clicked.connect(self.open_gestures.emit)
        drop.addWidget(_BtnRow(self._btn_gestures, "GESTURES"),
                       alignment=Qt.AlignmentFlag.AlignRight)
        self._btn_console = _SvgButton(_SVG_CONSOLE)
        self._btn_console.clicked.connect(self._on_console)
        drop.addWidget(_BtnRow(self._btn_console, "CONSOLE"),
                       alignment=Qt.AlignmentFlag.AlignRight)
        self._btn_settings = _SvgButton(_SVG_SETTINGS)
        self._btn_settings.clicked.connect(self.open_settings.emit)
        drop.addWidget(_BtnRow(self._btn_settings, "SETTINGS"),
                       alignment=Qt.AlignmentFlag.AlignRight)
        sep = QFrame()
        sep.setFixedSize(1, 12)
        sep.setStyleSheet("background:rgba(255,255,255,0.10);border:none;")
        drop.addWidget(sep, alignment=Qt.AlignmentFlag.AlignRight)
        self._btn_pause = _SvgButton(_SVG_PAUSE)
        self._btn_pause.clicked.connect(self._on_pause)
        self._pause_row = _BtnRow(self._btn_pause, "PAUSE")
        drop.addWidget(self._pause_row, alignment=Qt.AlignmentFlag.AlignRight)
        self._dropdown.hide()
        lay.addWidget(self._dropdown, alignment=Qt.AlignmentFlag.AlignRight)
    def _toggle_menu(self) -> None:
        self._open = not self._open
        self._main_btn.set_svg(_SVG_CLOSE if self._open else _SVG_MENU)
        self._dropdown.setVisible(self._open)
        self.adjustSize()
        self.geometry_changed.emit()
    def _on_console(self) -> None:
        self._console_on = not self._console_on
        self._btn_console.set_state(
            _SvgButton.ACTIVE if self._console_on else _SvgButton.NORMAL)
        self.toggle_console.emit()
    def _on_pause(self) -> None:
        self._active = not self._active
        if self._active:
            self._btn_pause.set_svg(_SVG_PAUSE)
            self._btn_pause.set_state(_SvgButton.NORMAL)
            self._pause_row.set_label("PAUSE")
        else:
            self._btn_pause.set_svg(_SVG_RESUME)
            self._btn_pause.set_state(_SvgButton.PAUSE)
            self._pause_row.set_label("RESUME")
        self.toggle_active.emit()
    def set_console_state(self, on: bool) -> None:
        self._console_on = on
        self._btn_console.set_state(
            _SvgButton.ACTIVE if on else _SvgButton.NORMAL)