# PyInstaller definition for the distributable Windows application.

from PyInstaller.utils.hooks import collect_data_files

mediapipe_datas = collect_data_files(
    "mediapipe",
    includes=[
        "modules/hand_landmark/**",
        "modules/palm_detection/**",
    ],
)

a = Analysis(
    ["tray.py"],
    pathex=[],
    binaries=[],
    datas=mediapipe_datas
    + [
        ("gesture_model_runtime.npz", "."),
        ("tray_icon_active.png", "."),
        ("tray_icon_inactive.png", "."),
    ],
    hiddenimports=["win32timezone"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "jax",
        "jaxlib",
        "onnxruntime",
        "pandas",
        "scipy",
        "sklearn",
        "sounddevice",
        "torch",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GestureAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["gesture_assistant.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestureAssistant",
)
