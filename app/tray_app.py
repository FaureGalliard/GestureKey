"""
TrayApp — aplicación de system tray que orquesta el worker y la ventana.

Comportamiento:
  • Al arrancar: ícono en la bandeja, pipeline corriendo en background.
  • Click en ícono / "Mostrar cámara"  → abre/muestra CameraWindow.
  • Click derecho → menú contextual con controles.
  • "Salir" → detiene el worker y cierra todo limpiamente.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
)
from PyQt6.QtGui import QAction

from app.config import AppConfig, default_config
from app.camera_worker import CameraWorker
from app.camera_window import CameraWindow
from app.tray_icon import make_tray_icon, make_status_icon
from domain.enums import HandState


class TrayApp:
    """
    Controlador de la aplicación de bandeja.

    Conecta CameraWorker (hilo) ↔ CameraWindow (UI) a través de señales Qt.
    """

    def __init__(self, config: AppConfig = default_config) -> None:
        self._config  = config
        self._running = False

        # ---- Ventana de cámara (oculta al inicio) --------------------
        self._window = CameraWindow()

        # ---- Worker en hilo separado ---------------------------------
        self._worker = CameraWorker(config)
        self._connect_worker()

        # ---- System tray --------------------------------------------
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(make_tray_icon(active=False))
        self._tray.setToolTip("Gesture Control — iniciando…")

        self._build_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ------------------------------------------------------------------
    # Inicio / parada
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._worker.start()
        self._running = True
        self._tray.setIcon(make_tray_icon(active=True))
        self._tray.setToolTip("Gesture Control — activo")
        self._tray.showMessage(
            "Gesture Control",
            "Pipeline activo. Click en el ícono para ver la cámara.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def stop(self) -> None:
        if self._running:
            self._worker.stop()
            self._running = False
        self._tray.hide()
        QApplication.quit()

    # ------------------------------------------------------------------
    # Construcción del menú contextual
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #334;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 4px;
            }
            QMenu::item:selected { background-color: #0f3460; }
            QMenu::separator { height: 1px; background: #334; margin: 4px 0; }
        """)

        self._act_show = QAction("Mostrar cámara", menu)
        self._act_show.triggered.connect(self._show_window)
        menu.addAction(self._act_show)

        menu.addSeparator()

        self._act_status = QAction("Estado: sin manos", menu)
        self._act_status.setEnabled(False)
        menu.addAction(self._act_status)

        menu.addSeparator()

        act_restart = QAction("Reiniciar pipeline", menu)
        act_restart.triggered.connect(self._restart_pipeline)
        menu.addAction(act_restart)

        menu.addSeparator()

        act_quit = QAction("Salir", menu)
        act_quit.triggered.connect(self.stop)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)

    # ------------------------------------------------------------------
    # Conexión de señales worker → UI
    # ------------------------------------------------------------------
    def _connect_worker(self) -> None:
        self._worker.frame_ready.connect(self._window.on_frame)
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.event_fired.connect(self._window.on_event)
        self._worker.status_msg.connect(self._window.on_status)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Click simple o doble en el ícono → toggle de ventana."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_window()

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
            self._act_show.setText("📷  Mostrar cámara")
        else:
            self._show_window()

    def _show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        self._act_show.setText(" Ocultar cámara")

    def _on_state_changed(
        self, stable: HandState, raw: HandState, confidence: float
    ) -> None:
        """Actualiza tooltip y menú con el estado actual."""
        self._window.on_state_changed(stable, raw, confidence)

        state_str = stable.value
        self._tray.setToolTip(
            f"Gesture Control — {state_str}  ({confidence*100:.0f}%)"
        )
        self._tray.setIcon(make_status_icon(state_str))
        self._act_status.setText(f" Estado: {state_str}  ({confidence*100:.0f}%)")

    def _restart_pipeline(self) -> None:
        self._worker.stop()
        self._worker = CameraWorker(self._config)
        self._connect_worker()
        self._worker.start()
        self._tray.showMessage(
            "Gesture Control",
            "Pipeline reiniciado.",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )