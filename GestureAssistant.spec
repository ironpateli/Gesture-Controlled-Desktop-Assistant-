# PyInstaller definition for the distributable Windows application.

from PyInstaller.utils.hooks import collect_all

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["tray.py"],
    pathex=[],
    binaries=mediapipe_binaries,
    datas=mediapipe_datas
    + [
        ("gesture_model.pth", "."),
        ("tray_icon_active.png", "."),
        ("tray_icon_inactive.png", "."),
    ],
    hiddenimports=mediapipe_hiddenimports + ["win32timezone"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "sklearn"],
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
