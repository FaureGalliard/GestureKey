from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from config import AppConfig, default_config
from pipeline.worker import CameraWorker
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow, CameraScanner


# ── tray icon ─────────────────────────────────────────────────────────────────

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
    for x, dh in zip([22, 27, 32, 37, 42], [20, 14, 12, 14, 18]):
        p.drawLine(x, 34, x, 34 - dh)
        p.drawEllipse(x - 2, 34 - dh - 4, 4, 4)
    p.setBrush(QBrush(accent))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(28, 50, 8, 8)
    p.end()
    return QIcon(pix)


# ── TrayApp ───────────────────────────────────────────────────────────────────

class TrayApp:
    def __init__(self, config: AppConfig = default_config) -> None:
        self._config   = config
        self._worker   = CameraWorker(config)
        self._window   = MainWindow()
        self._settings: SettingsWindow | None = None
        self._scanner:  CameraScanner  | None = None

        self._connect_worker()
        self._window.request_settings.connect(self._open_settings)

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(make_tray_icon(active=False))
        self._tray.setToolTip("GestureKey")
        self._build_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def start(self) -> None:
        self._window.show()
        self._worker.start()           # start pipeline immediately, no scan yet
        self._tray.setIcon(make_tray_icon(active=True))

    def stop(self) -> None:
        self._worker._running = False  # non-blocking
        self._tray.hide()
        QApplication.quit()

    # ── connections ───────────────────────────────────────────────────────────

    def _connect_worker(self) -> None:
        self._worker.frame_ready.connect(self._window.on_frame)
        self._worker.state_changed.connect(self._window.on_state_changed)
        self._worker.event_fired.connect(self._window.on_event)
        self._worker.hands_changed.connect(self._window.on_hands_changed)
        self._worker.status_msg.connect(print)
        self._worker.finished.connect(lambda: print('[WORKER] thread finished'))

    # ── settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        # If settings already visible, just bring it forward
        if self._settings is not None and self._settings.isVisible():
            self._settings.raise_()
            return

        # Disconnect frame signal FIRST so no more frames reach the UI
        try:
            self._worker.frame_ready.disconnect(self._window.on_frame)
        except RuntimeError:
            pass
        # Paint overlay — event loop is free, renders immediately
        self._window.on_camera_stopped()
        # Signal worker to stop non-blocking
        self._worker._running = False

        # Scan cameras now (worker is stopped, device is free)
        self._scanner = CameraScanner()
        self._scanner.scan_done.connect(self._on_scan_done)
        self._scanner.start()

    def _on_scan_done(self, cameras: dict) -> None:
        # Build/rebuild settings with fresh camera list
        self._settings = SettingsWindow(self._config, cameras=cameras)
        self._settings.camera_selected.connect(self._on_camera_changed)
        self._settings.preview_released.connect(self._on_settings_closed)

        geo = self._window.geometry()
        self._settings.move(geo.right() + 12, geo.top())
        self._settings.show()

    def _on_camera_changed(self, index: int) -> None:
        self._config.camera_device = index

    def _on_settings_closed(self) -> None:
        # Show animated loading state while the new pipeline initialises
        self._window.on_camera_loading()
        # Restart pipeline with the newly selected device
        self._worker = CameraWorker(self._config)
        self._connect_worker()
        self._worker.start()

    # ── tray menu ─────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background:#1a1a1a; color:rgba(255,255,255,0.80);
                border:1px solid rgba(255,255,255,0.08);
                border-radius:6px; font-size:12px; padding:4px 0;
            }
            QMenu::item { padding:7px 20px; border-radius:3px; }
            QMenu::item:selected { background:rgba(255,255,255,0.08); }
            QMenu::separator { height:1px; background:rgba(255,255,255,0.05); margin:4px 0; }
        """)
        self._act_show = QAction("Show window", menu)
        self._act_show.triggered.connect(self._toggle_window)
        menu.addAction(self._act_show)
        act_settings = QAction("Settings", menu)
        act_settings.triggered.connect(self._open_settings)
        menu.addAction(act_settings)
        menu.addSeparator()
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.stop)
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_window()

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
            self._act_show.setText("Show window")
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
            self._act_show.setText("Hide window")