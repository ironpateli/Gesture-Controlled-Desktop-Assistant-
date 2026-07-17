"""Windows lifecycle integration for startup, identity, and single instance."""

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import winreg

from app_paths import IS_FROZEN, SOURCE_DIR

APP_ID = "GestureAssistant.Desktop"
RUN_VALUE_NAME = "GestureAssistant"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
MUTEX_NAME = r"Local\GestureAssistant.Singleton"
LEGACY_STARTUP_SHORTCUT = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs",
    "Startup",
    "Gesture Assistant.lnk",
)

_mutex_handle = None

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_create_mutex = _kernel32.CreateMutexW
_create_mutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_create_mutex.restype = wintypes.HANDLE
_close_handle = _kernel32.CloseHandle
_close_handle.argtypes = [wintypes.HANDLE]
_close_handle.restype = wintypes.BOOL


def set_windows_app_identity() -> None:
    """Give Windows a stable shell identity for notifications and grouping."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        pass


def acquire_single_instance() -> bool:
    """Return False when another Gesture Assistant process already owns the mutex."""
    global _mutex_handle
    ctypes.set_last_error(0)
    handle = _create_mutex(None, False, MUTEX_NAME)
    if not handle:
        return True
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        _close_handle(handle)
        return False
    _mutex_handle = handle
    return True


def release_single_instance() -> None:
    global _mutex_handle
    if _mutex_handle:
        _close_handle(_mutex_handle)
        _mutex_handle = None


def packaged_executable_path() -> str | None:
    if IS_FROZEN:
        return sys.executable
    candidate = os.path.join(
        SOURCE_DIR, "dist", "GestureAssistant", "GestureAssistant.exe"
    )
    return candidate if os.path.exists(candidate) else None


def launch_parts() -> list[str]:
    """Return the preferred silent launch command for this installation."""
    packaged = packaged_executable_path()
    if packaged:
        return [packaged]

    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    interpreter = pythonw if os.path.exists(pythonw) else sys.executable
    return [interpreter, os.path.join(SOURCE_DIR, "tray.py")]


def launch_command() -> str:
    return subprocess.list2cmdline(launch_parts())


def is_start_with_windows_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except FileNotFoundError:
        return bool(LEGACY_STARTUP_SHORTCUT and os.path.exists(LEGACY_STARTUP_SHORTCUT))


def set_start_with_windows(enabled: bool) -> None:
    """Enable or disable per-user startup without requiring administrator access."""
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            winreg.SetValueEx(
                key,
                RUN_VALUE_NAME,
                0,
                winreg.REG_SZ,
                launch_command(),
            )
        if LEGACY_STARTUP_SHORTCUT and os.path.exists(LEGACY_STARTUP_SHORTCUT):
            os.remove(LEGACY_STARTUP_SHORTCUT)
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        pass

    if LEGACY_STARTUP_SHORTCUT and os.path.exists(LEGACY_STARTUP_SHORTCUT):
        os.remove(LEGACY_STARTUP_SHORTCUT)
