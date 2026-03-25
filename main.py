from __future__ import annotations
import sys
import ctypes
from pathlib import Path

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()
# --------------------------------

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PyQt6.QtWidgets import QApplication

from config import AppConfig
from app import TrayApp


def main() -> None:
    QApplication.setQuitOnLastWindowClosed(False)

    app = QApplication(sys.argv)
    app.setApplicationName("GestureKey")
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