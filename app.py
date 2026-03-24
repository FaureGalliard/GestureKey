from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from config import AppConfig, default_config
from pipeline.worker import CameraWorker
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow, CameraScanner


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


class TrayApp:
    """
    Camera ownership
    ────────────────
    CameraWorker owns the active VideoCapture at ALL times and NEVER restarts.
    SettingsWindow uses worker frames for the current camera (MODE A) and its
    own VideoCapture only when previewing a different device (MODE B).

    Overlay lifecycle
    ─────────────────
    open settings  → on_camera_stopped()   freeze + "Selecting camera…"
    save new cam   → on_camera_loading()   freeze + "Loading camera…" (animated)
    settings close → on_camera_resumed()   unfreeze — next frame clears overlay
    switch done    → (no extra call needed, unfreeze already happened)
    """

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
        self._worker.start()
        self._tray.setIcon(make_tray_icon(active=True))

    def stop(self) -> None:
        self._worker.stop()
        self._tray.hide()
        QApplication.quit()

    # ── worker wiring ─────────────────────────────────────────────────────────

    def _connect_worker(self) -> None:
        self._worker.frame_ready.connect(self._window.on_frame)
        self._worker.state_changed.connect(self._window.on_state_changed)
        self._worker.event_fired.connect(self._window.on_event)
        self._worker.hands_changed.connect(self._window.on_hands_changed)
        self._worker.status_msg.connect(print)
        self._worker.camera_switched.connect(self._on_camera_switched)

    # ── settings flow ─────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        if self._settings is not None and self._settings.isVisible():
            self._settings.raise_()
            return

        # Freeze main view immediately — worker keeps running normally.
        self._window.on_camera_stopped()

        # Scan cameras while worker continues capturing.
        self._scanner = CameraScanner()
        self._scanner.scan_done.connect(self._on_scan_done)
        self._scanner.start()

    def _on_scan_done(self, cameras: dict) -> None:
        if self._settings is not None:
            try:
                self._settings.camera_selected.disconnect()
                self._settings.preview_released.disconnect()
            except RuntimeError:
                pass
            self._settings.deleteLater()

        self._settings = SettingsWindow(self._config, cameras=cameras)
        self._settings.camera_selected.connect(self._on_camera_selected)
        self._settings.preview_released.connect(self._on_preview_released)

        # Wire worker live feed → settings preview (MODE A).
        self._worker.frame_ready.connect(self._settings.update_preview_frame)

        geo = self._window.geometry()
        self._settings.move(geo.right() + 12, geo.top())
        self._settings.show()

    def _on_camera_selected(self, index: int) -> None:
        """User saved a new device — switch without restarting the worker."""
        # Loading overlay (still frozen from on_camera_stopped).
        self._window.on_camera_loading()
        self._worker.switch_camera(index)

    def _on_preview_released(self) -> None:
        """Settings is closing — disconnect feed and unfreeze main view."""
        if self._settings is not None:
            try:
                self._worker.frame_ready.disconnect(self._settings.update_preview_frame)
            except RuntimeError:
                pass
        # Unfreeze: the next frame_ready → on_frame → update_frame() will
        # clear the overlay automatically.
        self._window.on_camera_resumed()

    def _on_camera_switched(self, device: int) -> None:
        """Worker finished a switch attempt."""
        if device == -1:
            # Switch failed — stay frozen with an error-ish overlay.
            self._window.on_camera_stopped()
            print("[APP] Camera switch failed")
        # On success the unfreeze already happened in _on_preview_released,
        # so the next frame from the new device will clear the overlay.

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