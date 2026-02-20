"""
main.py — Entry point de Gesture Control como aplicación de system tray.

Uso:
    python app/main.py

La aplicación:
  1. Arranca sin ventana visible.
  2. Muestra ícono en la bandeja del sistema.
  3. Corre el pipeline de visión en un hilo de fondo.
  4. Al hacer click en el ícono → muestra/oculta la ventana de cámara.
  5. Click derecho en el ícono → menú de control.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PyQt6.QtWidgets import QApplication

from app.config import AppConfig
from app.tray_app import TrayApp


def main() -> None:
    # Necesario para que QSystemTrayIcon funcione sin ventana principal
    QApplication.setQuitOnLastWindowClosed(False)

    app = QApplication(sys.argv)
    app.setApplicationName("Gesture Control")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("GestureProject")
    app.setStyle("Fusion")

    config = AppConfig(
        model_path=_ROOT / "models" / "hand_state_rf.pkl",
        fps_limit=30,
        min_confidence=0.60,
        state_window=4,
        state_consensus=2,
        cooldown=0.6,
    )

    tray = TrayApp(config)
    tray.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()