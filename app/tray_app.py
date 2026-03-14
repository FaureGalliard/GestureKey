"""
TrayApp — aplicación de system tray que orquesta el worker y la ventana.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction

from app.config import AppConfig, default_config
from app.camera_worker import CameraWorker
from app.camera_window import CameraWindow
from app.tray_icon import make_tray_icon
from domain.enums import HandState


class TrayApp:
    def __init__(self, config: AppConfig = default_config) -> None:
        self._config  = config
        self._running = False

        self._window = CameraWindow()
        self._worker = CameraWorker(config)
        self._connect_worker()

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(make_tray_icon(active=False))
        self._tray.setToolTip("Gesture Control")

        self._build_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def start(self) -> None:
        self._worker.start()
        self._running = True
        self._tray.setIcon(make_tray_icon(active=True))

    def stop(self) -> None:
        if self._running:
            self._worker.stop()
            self._running = False
        self._tray.hide()
        QApplication.quit()

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #1a1a1a;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 3px;
            }
            QMenu::item:selected { background-color: #f0f0f0; }
            QMenu::separator { height: 1px; background: #e0e0e0; margin: 4px 0; }
        """)

        self._act_show = QAction("Mostrar cámara", menu)
        self._act_show.triggered.connect(self._toggle_window)
        menu.addAction(self._act_show)

        menu.addSeparator()

        act_quit = QAction("Salir", menu)
        act_quit.triggered.connect(self.stop)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)

    def _connect_worker(self) -> None:
        self._worker.frame_ready.connect(self._window.on_frame)
        self._worker.state_changed.connect(self._window.on_state_changed)
        self._worker.event_fired.connect(self._window.on_event)
        self._worker.status_msg.connect(self._window.on_status)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_window()

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
            self._act_show.setText("Mostrar cámara")
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
            self._act_show.setText("Ocultar cámara")