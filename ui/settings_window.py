from __future__ import annotations
import threading
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
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


class CameraScanner(QThread):
    scan_done = pyqtSignal(dict)

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
            # Try to open the device. If it fails (e.g. worker already owns it),
            # still record it if it has a friendly name — the worker's device
            # is always valid even if we can't open a second handle to it.
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            ok  = cap.isOpened()
            cap.release()
            if ok or i < len(friendly):
                name = friendly[i] if i < len(friendly) else f"Camera {i}"
                with lock:
                    found[i] = name

        threads = [threading.Thread(target=probe, args=(i,), daemon=True)
                   for i in range(8)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=3.0)
        self.scan_done.emit(found)


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("background:rgba(255,255,255,0.07);border:none;max-height:1px;")
    return f


class SettingsWindow(QDialog):
    camera_selected  = pyqtSignal(int)
    preview_released = pyqtSignal()

    def __init__(self, config: AppConfig, cameras: dict[int, str], parent=None) -> None:
        super().__init__(parent)
        self._config   = config
        self._cameras  = cameras
        self._current  = config.camera_device
        self._selected = config.camera_device
        self._cam_buttons: dict[int, QPushButton] = {}
        self._expanded = False

        self._use_worker_preview: bool = True
        self._preview_cap: cv2.VideoCapture | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(33)
        self._preview_timer.timeout.connect(self._tick_preview)

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

    # ── public API ────────────────────────────────────────────────────────────

    def update_preview_frame(self, frame: np.ndarray) -> None:
        if not self.isVisible() or not self._use_worker_preview:
            return
        self._display(frame)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        hdr = QLabel("CAMERA")
        hdr.setStyleSheet(
            f"color:{TEXT_LOW};font-size:9px;font-weight:600;letter-spacing:2px;"
        )
        lay.addWidget(hdr)

        self._preview_lbl = QLabel("Connecting…")
        self._preview_lbl.setFixedHeight(170)
        self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_lbl.setStyleSheet(
            "background:#000;border-radius:8px;"
            "color:rgba(255,255,255,0.30);font-size:10px;"
        )
        lay.addWidget(self._preview_lbl)

        current_name = self._cameras.get(self._current, f"Camera {self._current}")
        self._trigger_btn = QPushButton(current_name + " ▼")
        self._trigger_btn.setStyleSheet(self._trigger_style())
        self._trigger_btn.clicked.connect(self._toggle_expand)
        lay.addWidget(self._trigger_btn)

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

        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(self._save_btn_style(False))
        self._save_btn.clicked.connect(self._save)
        lay.addWidget(self._save_btn)

    # ── expand / collapse ─────────────────────────────────────────────────────

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._list_widget.setVisible(self._expanded)
        name = self._cameras.get(self._selected, f"Camera {self._selected}")
        self._trigger_btn.setText(name + (" ▲" if self._expanded else " ▼"))
        self.adjustSize()

    # ── camera selection ──────────────────────────────────────────────────────

    def _highlight_camera(self, index: int) -> None:
        self._selected = index
        name = self._cameras.get(index, f"Camera {index}")

        self._expanded = False
        self._list_widget.hide()
        self._trigger_btn.setText(name + " ▼")
        self.adjustSize()

        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == index))

        self._save_btn.setText("Save")
        self._save_btn.setStyleSheet(self._save_btn_style(False))

        if index == self._current:
            self._use_worker_preview = True
            self._stop_preview()
        else:
            self._use_worker_preview = False
            self._start_preview(index)

    # ── local preview (MODE B) ────────────────────────────────────────────────

    def _start_preview(self, index: int) -> None:
        self._stop_preview()
        self._preview_lbl.setText("Opening…")
        self._preview_lbl.setPixmap(QPixmap())
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            self._preview_cap = cap
            self._preview_timer.start()
        else:
            cap.release()
            self._preview_lbl.setText(f"Cannot open camera {index}")

    def _stop_preview(self) -> None:
        self._preview_timer.stop()
        if self._preview_cap is not None:
            self._preview_cap.release()
            self._preview_cap = None

    def _tick_preview(self) -> None:
        if self._preview_cap is None:
            return
        ret, frame = self._preview_cap.read()
        if ret:
            self._display(frame)

    def _display(self, frame: np.ndarray) -> None:
        rgb      = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._preview_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_lbl.setPixmap(pix)

    # ── save ──────────────────────────────────────────────────────────────────

    def _save(self) -> None:
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
            print(f"[Settings] Error saving config: {e}")
            return

        self._config.camera_device = self._selected

        if self._selected != self._current:
            self._stop_preview()
            self.camera_selected.emit(self._selected)

        self._save_btn.setText("✓ Saved")
        self._save_btn.setStyleSheet(self._save_btn_style(True))
        QTimer.singleShot(500, self.close)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Clean up any stale preview state from a previous session.
        self._stop_preview()
        self._use_worker_preview = True
        # Sync to current saved device.
        self._current  = self._config.camera_device
        self._selected = self._current
        name = self._cameras.get(self._selected, f"Camera {self._selected}")
        self._trigger_btn.setText(name + " ▼")
        self._expanded = False
        self._list_widget.hide()
        self._save_btn.setText("Save")
        self._save_btn.setStyleSheet(self._save_btn_style(False))
        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == self._selected))
        self._preview_lbl.setText("Connecting…")
        self._preview_lbl.setPixmap(QPixmap())

    def closeEvent(self, event) -> None:
        self._stop_preview()
        self.preview_released.emit()
        super().closeEvent(event)

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