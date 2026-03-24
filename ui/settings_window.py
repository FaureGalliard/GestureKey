from __future__ import annotations
import threading
import cv2
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QPushButton, QWidget, QFrame,
)
from config import AppConfig

try:
    from ui.theme import TEXT_HIGH, TEXT_LOW, BASE_STYLE
except ImportError:
    TEXT_HIGH  = "rgba(255,255,255,0.90)"
    TEXT_LOW   = "rgba(255,255,255,0.35)"
    BASE_STYLE = ""


# ── One-time camera scan at app startup ───────────────────────────────────────

class CameraScanner(QThread):
    """
    Run once at startup (before the main worker opens the camera).
    Probes indices 0-7 in parallel and emits the result as a dict.
    """
    scan_done = pyqtSignal(dict)   # {index: name}

    def run(self) -> None:
        friendly: list[str] = []
        try:
            from pygrabber.dshow_graph import FilterGraph
            friendly = FilterGraph().get_input_devices()
        except Exception:
            pass

        found: dict[int, str] = {}
        lock = threading.Lock()

        def probe(i: int) -> None:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            ok  = cap.isOpened()
            cap.release()
            if ok:
                name = friendly[i] if i < len(friendly) else f"Camera {i}"
                with lock:
                    found[i] = name

        threads = [threading.Thread(target=probe, args=(i,), daemon=True)
                   for i in range(8)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=3.0)

        self.scan_done.emit(found)


# ── helpers ───────────────────────────────────────────────────────────────────

def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("background:rgba(255,255,255,0.07);border:none;max-height:1px;")
    return f


# ── Settings window ───────────────────────────────────────────────────────────

class SettingsWindow(QDialog):
    """
    Opens instantly — camera list is pre-populated before this window exists.
    Shows a live preview of whichever camera is highlighted.
    On Save: persists to config, emits camera_selected, closes.
    """
    camera_selected  = pyqtSignal(int)
    preview_released = pyqtSignal()

    def __init__(self, config: AppConfig, cameras: dict[int, str], parent=None) -> None:
        super().__init__(parent)
        self._config   = config
        self._cameras  = cameras          # pre-populated at startup
        self._current  = config.camera_device
        self._selected = config.camera_device
        self._cam_cap: cv2.VideoCapture | None    = None
        self._cam_buttons: dict[int, QPushButton] = {}
        self._expanded = False

        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)

        self.setWindowTitle("Settings — GestureKey")
        self.setFixedWidth(340)
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet((BASE_STYLE or "") + """
            QDialog { background:#141414; color:rgba(255,255,255,0.80); }
        """)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel("CAMERA")
        lbl.setStyleSheet(
            f"color:{TEXT_LOW};font-size:9px;font-weight:600;letter-spacing:2px;"
        )
        lay.addWidget(lbl)

        # Live preview
        self._preview_lbl = QLabel()
        self._preview_lbl.setFixedHeight(170)
        self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_lbl.setStyleSheet(
            "background:#000;border-radius:8px;"
            "color:rgba(255,255,255,0.30);font-size:10px;"
        )
        lay.addWidget(self._preview_lbl)

        # Trigger button — shows current camera, click to expand list
        current_name = self._cameras.get(self._current, f"Camera {self._current}")
        self._trigger_btn = QPushButton(current_name + " ▼")
        self._trigger_btn.setStyleSheet(self._trigger_style())
        self._trigger_btn.clicked.connect(self._toggle_expand)
        lay.addWidget(self._trigger_btn)

        # Collapsable camera list
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background:transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        for idx, name in sorted(self._cameras.items()):
            btn = QPushButton(name)
            btn.setStyleSheet(self._cam_btn_style(idx == self._selected))
            btn.clicked.connect(lambda _, i=idx: self._highlight_camera(i))
            self._list_layout.addWidget(btn)
            self._cam_buttons[idx] = btn
        self._list_widget.hide()
        lay.addWidget(self._list_widget)

        lay.addWidget(_sep())

        # Save button
        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(self._save_btn_style(False))
        self._save_btn.clicked.connect(self._save)
        lay.addWidget(self._save_btn)

    # ── styles ────────────────────────────────────────────────────────────────

    def _trigger_style(self) -> str:
        return """
            QPushButton {
                background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.70);
                border:none; border-radius:8px;
                padding:8px 12px; text-align:left; font-size:10px;
            }
            QPushButton:hover { background:rgba(255,255,255,0.09); }
        """

    def _cam_btn_style(self, active: bool) -> str:
        bg    = "rgba(255,255,255,0.10)" if active else "transparent"
        color = TEXT_HIGH if active else TEXT_LOW
        return f"""
            QPushButton {{
                background:{bg}; color:{color};
                border:none; border-radius:6px;
                padding:7px 12px; text-align:left; font-size:10px;
            }}
            QPushButton:hover {{ background:rgba(255,255,255,0.08); color:{TEXT_HIGH}; }}
        """

    def _save_btn_style(self, saved: bool) -> str:
        if saved:
            return """
                QPushButton {
                    background:rgba(52,211,153,0.15); color:#34d399;
                    border:1px solid rgba(52,211,153,0.20);
                    border-radius:8px; padding:8px;
                    font-size:10px; font-weight:500;
                }
            """
        return """
            QPushButton {
                background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.50);
                border:1px solid rgba(255,255,255,0.05);
                border-radius:8px; padding:8px;
                font-size:10px; font-weight:500;
            }
            QPushButton:hover {
                background:rgba(255,255,255,0.10); color:rgba(255,255,255,0.70);
            }
        """

    # ── interactions ──────────────────────────────────────────────────────────

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._list_widget.setVisible(self._expanded)
        name = self._cameras.get(self._selected, f"Camera {self._selected}")
        self._trigger_btn.setText(name + (" ▲" if self._expanded else " ▼"))
        self.adjustSize()

    def _highlight_camera(self, index: int) -> None:
        """User clicked a camera in the list — preview it, don't save yet."""
        self._selected = index
        name = self._cameras.get(index, f"Camera {index}")

        # Collapse list
        self._expanded = False
        self._list_widget.hide()
        self._trigger_btn.setText(name + " ▼")
        self.adjustSize()

        # Update highlights
        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == index))

        # Preview selected camera
        self._start_preview(index)

    def _save(self) -> None:
        """Persist selection, emit signal, show brief confirmation, close."""
        import re, pathlib
        config_path = pathlib.Path(__file__).parent.parent / "config.py"
        try:
            text = config_path.read_text(encoding="utf-8")
            text = re.sub(
                r"(camera_device\s*:\s*int\s*=\s*)\d+",
                lambda m: f"{m.group(1)}{self._selected}",
                text,
            )
            config_path.write_text(text, encoding="utf-8")
        except Exception as e:
            print(f"[Settings] Error saving: {e}")
            return

        self._config.camera_device = self._selected
        self.camera_selected.emit(self._selected)

        self._save_btn.setText("✓ Saved")
        self._save_btn.setStyleSheet(self._save_btn_style(True))
        QTimer.singleShot(500, self.close)

    # ── show / close ──────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Reset selection to current saved camera each time window opens
        self._selected = self._config.camera_device
        self._current  = self._config.camera_device
        name = self._cameras.get(self._selected, f"Camera {self._selected}")
        self._trigger_btn.setText(name + " ▼")
        self._save_btn.setText("Save")
        self._save_btn.setStyleSheet(self._save_btn_style(False))
        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == self._selected))
        self._start_preview(self._selected)

    def closeEvent(self, event) -> None:
        self._stop_preview()
        self.preview_released.emit()
        super().closeEvent(event)

    # ── preview ───────────────────────────────────────────────────────────────

    def _start_preview(self, index: int) -> None:
        self._stop_preview()
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            self._cam_cap = cap
            self._preview_timer.start(33)
        else:
            cap.release()
            self._preview_lbl.setText(f"Cannot open camera {index}")

    def _stop_preview(self) -> None:
        self._preview_timer.stop()
        if self._cam_cap is not None:
            self._cam_cap.release()
            self._cam_cap = None

    def _update_preview(self) -> None:
        if self._cam_cap is None:
            return
        ret, frame = self._cam_cap.read()
        if not ret:
            return
        import cv2 as _cv2
        import numpy as _np
        frame    = _cv2.flip(frame, 1)
        rgb      = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._preview_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_lbl.setPixmap(pix)