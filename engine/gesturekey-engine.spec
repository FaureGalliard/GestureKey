# PyInstaller spec for the engine sidecar (onedir: fast start, no temp extraction).
# Built by `pnpm build:engine` from app/, output lands in app/src-tauri/engine/.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "gesturekey" / "__main__.py")],
    pathex=[str(ROOT)],
    # MediaPipe Tasks runs on a native library loaded at runtime (tasks/c/libmediapipe.dll)
    binaries=collect_dynamic_libs("mediapipe"),
    datas=[
        # only what the engine loads (the v2 model stays in the repo, not in the installer)
        (str(ROOT / "gesturekey" / "models" / "hand_state_rf.pkl"), "models"),
        (str(ROOT / "gesturekey" / "models" / "hand_landmarker.task"), "models"),
        *collect_data_files("mediapipe", includes=["**/*.tflite", "**/*.binarypb", "**/*.txt", "**/*.task"]),
    ],
    hiddenimports=["sklearn.ensemble._forest", "sklearn.tree._tree", "pycaw.pycaw", "comtypes.stream"],
    # matplotlib stays: mediapipe.tasks imports it
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
