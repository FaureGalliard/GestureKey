# PyInstaller spec for the engine sidecar (onedir: fast start, no temp extraction).
# Built by `pnpm build:engine` from app/, output lands in app/src-tauri/engine/.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "gesturekey" / "__main__.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "gesturekey" / "models"), "models"),
        *collect_data_files("mediapipe", includes=["**/*.tflite", "**/*.binarypb", "**/*.txt"]),
    ],
    hiddenimports=["sklearn.ensemble._forest", "sklearn.tree._tree", "pycaw.pycaw", "comtypes.stream"],
    # matplotlib stays: mediapipe.solutions imports it through drawing_utils
    excludes=["tkinter", "PyQt6", "PyQt5", "pandas", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gesturekey-engine",
    console=True,           # Tauri spawns it with CREATE_NO_WINDOW; stdout stays readable
    icon=str(ROOT.parent / "app" / "src-tauri" / "icons" / "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="gesturekey-engine")
