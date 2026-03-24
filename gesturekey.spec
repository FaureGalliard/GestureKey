# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = os.path.abspath(".")

# --- RECOLECCIÓN AUTOMÁTICA ---
# Esto extrae todo lo necesario de las librerías problemáticas
m_datas, m_binaries, m_hidden = collect_all("mediapipe")
s_datas, s_binaries, s_hidden = collect_all("sklearn")
c_datas, c_binaries, c_hidden = collect_all("cv2")

analysis = Analysis(
    ["main.py"],
    pathex=[project_root],
    # Combinamos los binarios encontrados automáticamente
    binaries=m_binaries + s_binaries + c_binaries,
    datas=[
        # Tus carpetas locales (se pondrán en _internal por seguridad de compilación)
        ("models/hand_state_rf.pkl", "models"),
        ("gestures/", "gestures"),
        *m_datas,
        *s_datas,
        *c_datas,
    ],
    hiddenimports=[
        "config",
        "pipeline",
        "pipeline.camera",
        "pipeline.tracker",
        "pipeline.classifier",
        "pipeline.stabilizer",
        "pipeline.gesture_manager",
        "pipeline.cooldown",
        "utils.enums",
        "utils.models",
        "joblib",
        "pandas",
        *m_hidden,
        *s_hidden,
        *c_hidden,
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["torch", "tensorflow", "mediapipe.model_maker"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="GestureKey",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # IMPORTANTE: Mantener en True para ver el log de errores
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestureKey",
)