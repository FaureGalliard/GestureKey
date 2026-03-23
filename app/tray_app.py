from __future__ import annotations
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction

from app.config import AppConfig, default_config
from app.camera_worker import CameraWorker
from app.tray_icon import make_tray_icon
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow


class TrayApp:
    def __init__(self, config: AppConfig = default_config) -> None:
        self._config  = config
        self._running = False

        self._window   = MainWindow()
        self._settings = SettingsWindow(config)
        self._worker   = CameraWorker(config)

        self._connect_worker()
        self._connect_ui()

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(make_tray_icon(active=False))
        self._tray.setToolTip("GestureKey")
        self._build_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def start(self) -> None:
        self._worker.start()
        self._running = True
        self._tray.setIcon(make_tray_icon(active=True))

    def _restart_worker(self) -> None:
        if self._running:
            self._worker = CameraWorker(self._config)
            self._connect_worker()
            self._worker.start()

    def stop(self) -> None:
        if self._running:
            self._worker.stop()
            self._running = False
        self._tray.hide()
        QApplication.quit()

    def _connect_worker(self) -> None:
        self._worker.frame_ready.connect(self._window.on_frame)
        self._worker.state_changed.connect(self._window.on_state_changed)
        self._worker.event_fired.connect(self._window.on_event)

    def _connect_ui(self) -> None:
        self._window.request_settings.connect(self._open_settings)
        self._settings.camera_selected.connect(self._on_camera_changed)
        # Cuando settings cierra, reinicia el worker con la cámara correcta
        self._settings.preview_released.connect(self._restart_worker)

    def _open_settings(self) -> None:
        # Pausa el worker ANTES de abrir settings para liberar la cámara
        if self._running:
            self._worker.stop()
 
        if self._settings.isVisible():
            self._settings.raise_()
        else:
            geo = self._window.geometry()
            self._settings.move(geo.right() + 12, geo.top())
            self._settings.show()

    def _on_camera_changed(self, index: int) -> None:
        self._config.camera_device = index

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1a1a1a;
                color: rgba(255,255,255,0.80);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                font-size: 12px;
                padding: 4px 0;
            }
            QMenu::item { padding: 7px 20px; border-radius: 3px; }
            QMenu::item:selected { background: rgba(255,255,255,0.08); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.05); margin: 4px 0; }
        """)

        self._act_show = QAction("Show window", menu)
        self._act_show.triggered.connect(self._toggle_window)
        menu.addAction(self._act_show)

        act_settings = QAction("Settings", menu)
        act_settings.triggered.connect(self._open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()
        self._worker.hands_changed.connect(self._window.on_hands_changed)
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