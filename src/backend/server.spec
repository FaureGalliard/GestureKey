# src/backend/server.spec
from PyInstaller.utils.hooks import collect_all

block_cipher = None

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")
mpl_datas, mpl_binaries, mpl_hiddenimports = collect_all("matplotlib")
sklearn_datas, sklearn_binaries, sklearn_hiddenimports = collect_all("sklearn")

a = Analysis(
    ["server.py"],
    pathex=["."],
    binaries=cv2_binaries + mediapipe_binaries + mpl_binaries + sklearn_binaries,
    datas=[
        ("models/hand_state_rf.pkl", "models"),
        *mediapipe_datas,
        *cv2_datas,
        *mpl_datas,
        *sklearn_datas,
    ],
    hiddenimports=[
        "gestures",
        "gestures.base",
        "gestures.scroll",
        "gestures.volume",
        "gestures.zoom",
        "gestures.screenshot",
        "gestures.close_window",
        "gestures.pause",
        "gestures.mute",
        "gestures.task_view",
        "vision",
        "vision.camera",
        "vision.hand_tracker",
        "vision.state_classifier",
        "pipeline",
        "pipeline.cooldown_manager",
        "pipeline.gesture_manager",
        "pipeline.state_stabilizer",
        "utils",
        "utils.geometry",
        "joblib",
        "pandas",
        "pynput",
        "pynput.keyboard",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        "matplotlib",
        "matplotlib.pyplot",
        "matplotlib.backends.backend_agg",
        *mediapipe_hiddenimports,
        *cv2_hiddenimports,
        *mpl_hiddenimports,
        *sklearn_hiddenimports,
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter", "tk", "tcl","mediapipe.model_maker","matplotlib.tests","matplotlib.testing","sklearn.externals.array_api_compat.torch",
    "torch"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="server",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="server",
)