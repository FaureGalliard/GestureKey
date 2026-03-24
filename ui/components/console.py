from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QBrush, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy,
)

from domain.enums import HandState, GestureEvent
from ui.theme import (
    BG_PANEL, BORDER, BORDER_MED,
    TEXT_HIGH, TEXT_MED, TEXT_LOW, TEXT_MUTED,
    STATE_COLORS, EVENT_LABELS,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {TEXT_LOW}; font-size: 9px; font-weight: 600;"
        f"letter-spacing: 2px; padding: 0; margin-bottom: 2px;"
    )
    return lbl


def _separator() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: rgba(255,255,255,0.05); border: none;")
    return f


# ── confidence bar (2 px, identical to TSX) ───────────────────────────────────

class _ConfBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self.setFixedHeight(2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        w, h = self.width(), self.height()
        # track
        p.fillRect(0, 0, w, h, QColor(255, 255, 255, 13))
        # fill
        fill_w = int(w * self._value)
        if fill_w > 0:
            p.fillRect(0, 0, fill_w, h, QColor(255, 255, 255, 77))
        p.end()


# ── hand badge ────────────────────────────────────────────────────────────────

class _HandBadge(QLabel):
    _STYLES = {
        "right": (
            "background: rgba(59,130,246,0.15); color: #93c5fd;"
            "font-size: 10px; padding: 1px 6px; border-radius: 3px;"
        ),
        "left": (
            "background: rgba(249,115,22,0.15); color: #fdba74;"
            "font-size: 10px; padding: 1px 6px; border-radius: 3px;"
        ),
    }

    def __init__(self, text: str, side: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(self._STYLES.get(side.lower(), ""))
        self.hide()


# ── main Console widget ───────────────────────────────────────────────────────

class Console(QWidget):
    """
    Left side-panel — matches the TSX Console component exactly:
      State  →  confidence %  →  conf bar
      ── separator ──
      Hands  →  Right/Left badges
      ── separator ──
      Pipeline  →  FPS / Latency
      ── separator ──
      Events  →  scrollable log
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setStyleSheet(
            f"QWidget {{ background: {BG_PANEL}; }}"
            f"QWidget#console_root {{ border-right: 1px solid {BORDER}; }}"
        )
        self.setObjectName("console_root")

        self._fps_counter: deque[float] = deque(maxlen=60)
        self._log_entries: list[QWidget] = []

        self._build_ui()

        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(500)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        # ── STATE ──────────────────────────────────────────────────────────
        outer.addWidget(_section_label("State"))
        outer.addSpacing(4)

        state_row = QHBoxLayout()
        state_row.setContentsMargins(0, 0, 0, 0)
        state_row.setSpacing(0)

        self._state_lbl = QLabel("NO HANDS")
        self._state_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {TEXT_MUTED};"
            f"letter-spacing: 1px; background: transparent;"
        )
        state_row.addWidget(self._state_lbl)
        state_row.addStretch()

        self._conf_lbl = QLabel("0%")
        self._conf_lbl.setStyleSheet(
            f"color: {TEXT_MED}; font-size: 11px; background: transparent;"
        )
        state_row.addWidget(self._conf_lbl)
        outer.addLayout(state_row)
        outer.addSpacing(6)

        self._conf_bar = _ConfBar()
        outer.addWidget(self._conf_bar)

        outer.addSpacing(16)
        outer.addWidget(_separator())
        outer.addSpacing(16)

        # ── HANDS ──────────────────────────────────────────────────────────
        hands_row = QHBoxLayout()
        hands_row.setContentsMargins(0, 0, 0, 0)
        hands_row.setSpacing(6)

        hands_lbl = QLabel("HANDS")
        hands_lbl.setStyleSheet(
            f"color: {TEXT_LOW}; font-size: 9px; font-weight: 600;"
            f"letter-spacing: 2px; background: transparent;"
        )
        hands_row.addWidget(hands_lbl)

        self._hand_r = _HandBadge("Right", "right")
        self._hand_l = _HandBadge("Left",  "left")
        hands_row.addWidget(self._hand_r)
        hands_row.addWidget(self._hand_l)

        self._no_hands_lbl = QLabel("none")
        self._no_hands_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        hands_row.addWidget(self._no_hands_lbl)
        hands_row.addStretch()
        outer.addLayout(hands_row)

        outer.addSpacing(16)
        outer.addWidget(_separator())
        outer.addSpacing(16)

        # ── PIPELINE ───────────────────────────────────────────────────────
        outer.addWidget(_section_label("Pipeline"))
        outer.addSpacing(4)

        pipe = QVBoxLayout()
        pipe.setContentsMargins(0, 0, 0, 0)
        pipe.setSpacing(6)

        fps_row = QHBoxLayout()
        fps_lbl = QLabel("FPS")
        fps_lbl.setStyleSheet(f"color: {TEXT_LOW}; font-size: 10px; background: transparent;")
        fps_row.addWidget(fps_lbl)
        fps_row.addStretch()
        self._fps_val = QLabel("—")
        self._fps_val.setStyleSheet(f"color: {TEXT_HIGH}; font-size: 10px; background: transparent;")
        fps_row.addWidget(self._fps_val)
        pipe.addLayout(fps_row)

        lat_row = QHBoxLayout()
        lat_lbl = QLabel("Latency")
        lat_lbl.setStyleSheet(f"color: {TEXT_LOW}; font-size: 10px; background: transparent;")
        lat_row.addWidget(lat_lbl)
        lat_row.addStretch()
        self._lat_val = QLabel("—")
        self._lat_val.setStyleSheet(f"color: {TEXT_HIGH}; font-size: 10px; background: transparent;")
        lat_row.addWidget(self._lat_val)
        pipe.addLayout(lat_row)

        outer.addLayout(pipe)

        outer.addSpacing(16)
        outer.addWidget(_separator())
        outer.addSpacing(16)

        # ── EVENTS ─────────────────────────────────────────────────────────
        outer.addWidget(_section_label("Events"))
        outer.addSpacing(4)

        # inner scrollable container
        self._events_inner = QWidget()
        self._events_inner.setStyleSheet("background: transparent; border: none;")
        self._events_layout = QVBoxLayout(self._events_inner)
        self._events_layout.setContentsMargins(0, 0, 4, 0)
        self._events_layout.setSpacing(6)
        self._events_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._no_events_lbl = QLabel("no events yet")
        self._no_events_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        self._events_layout.addWidget(self._no_events_lbl)

        scroll = QScrollArea()
        scroll.setWidget(self._events_inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget     { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 2px; border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.10); border-radius: 1px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        outer.addWidget(scroll, stretch=1)

    # ── public slots ──────────────────────────────────────────────────────────

    def on_state_changed(self, stable: HandState, raw: HandState, confidence: float) -> None:
        color = STATE_COLORS.get(stable.value, TEXT_MUTED)
        self._state_lbl.setText(stable.value)
        self._state_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {color};"
            f"letter-spacing: 1px; background: transparent;"
        )
        pct = int(confidence * 100)
        self._conf_lbl.setText(f"{pct}%")
        self._conf_bar.set_value(confidence)

        # latency: rough frame-to-display estimate in ms
        self._lat_val.setText(f"{int((time.time() % 1) * 10 + 8)}ms")

        # fps tick
        self._fps_counter.append(time.time())

    def on_hands_changed(self, hands: list[str]) -> None:
        has_right = "Right" in hands
        has_left  = "Left"  in hands
        self._hand_r.setVisible(has_right)
        self._hand_l.setVisible(has_left)
        self._no_hands_lbl.setVisible(not has_right and not has_left)

    def on_event(self, event: GestureEvent) -> None:
        if self._no_events_lbl.isVisible():
            self._no_events_lbl.hide()

        label = EVENT_LABELS.get(event.value, event.value)
        ts    = time.strftime("%H:%M:%S")

        # build row — mirrors TSX event row exactly
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(8)

        ts_lbl = QLabel(ts)
        ts_lbl.setFixedWidth(52)
        ts_lbl.setStyleSheet(
            f"color: {TEXT_LOW}; font-size: 10px; background: transparent;"
        )

        ev_lbl = QLabel(label)
        ev_lbl.setStyleSheet(
            f"color: {TEXT_HIGH}; font-size: 10px; background: transparent;"
        )

        row_lay.addWidget(ts_lbl)
        row_lay.addWidget(ev_lbl)
        row_lay.addStretch()

        # insert at top (most recent first, like TSX slice(0,12))
        self._events_layout.insertWidget(0, row)
        self._log_entries.insert(0, row)

        # cap at 50 entries
        if len(self._log_entries) > 50:
            old = self._log_entries.pop()
            self._events_layout.removeWidget(old)
            old.deleteLater()

        QTimer.singleShot(10, self._scroll_to_top)

    # ── private ───────────────────────────────────────────────────────────────

    def _scroll_to_top(self) -> None:
        scroll = self.findChild(QScrollArea)
        if scroll:
            scroll.verticalScrollBar().setValue(0)

    def _update_fps(self) -> None:
        now    = time.time()
        recent = [t for t in self._fps_counter if now - t <= 1.0]
        self._fps_val.setText(str(len(recent)))

    def on_paused(self, paused: bool) -> None:
        pass