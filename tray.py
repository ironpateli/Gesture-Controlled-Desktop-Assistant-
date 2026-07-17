"""
tray.py

The app's entry point. Run this instead of main.py:

    python tray.py

A permanent system tray icon appears. Clicking it (or its "Start/Stop
Gesture Engine" menu item) toggles the camera + gesture recognition
loop on and off — the camera is NOT running until you turn it on.
The tray icon itself changes color to show whether the engine is
currently active.

Menu:
  - Start/Stop Gesture Engine  (also the default action on click)
  - Show Camera Preview        (recognition continues when hidden)
  - Configure Gestures         (opens config_gui.py's window)
  - Exit                       (stops the engine and tray process)

Icon files:
  tray_icon_inactive.png / tray_icon_active.png are generated once next
  to this file the first time you run it, then reused on every future
  run — no regeneration, no network calls. Replace either PNG with your
  own image any time; your version is used as-is as long as it exists.
"""

import os
import sys
import threading

from app_paths import data_path, resource_path
from windows_integration import (
    acquire_single_instance,
    is_start_with_windows_enabled,
    set_start_with_windows,
    set_windows_app_identity,
)

set_windows_app_identity()
if not acquire_single_instance():
    print("[tray] Gesture Assistant is already running.")
    sys.exit(0)

import pystray
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_INACTIVE_RESOURCE = resource_path("tray_icon_inactive.png")
ICON_ACTIVE_RESOURCE = resource_path("tray_icon_active.png")
ICON_INACTIVE_PATH = data_path("tray_icon_inactive.png")
ICON_ACTIVE_PATH = data_path("tray_icon_active.png")

COLOR_INACTIVE = "#2d3142"  # dark navy — engine off
COLOR_ACTIVE = "#2a9d8f"    # green — engine on

_gui_lock = threading.Lock()
_gui_open = False

_engine_lock = threading.Lock()
_engine_thread = None
_engine_stop_event = None
_preview_enabled = threading.Event()
_preview_enabled.set()


# ============================================================
# Icon image — generated once, then persisted to disk
# ============================================================

def _generate_icon(color: str, size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, size - 2, size - 2), fill=color)
    # Palm
    draw.rounded_rectangle(
        (size * 0.32, size * 0.42, size * 0.68, size * 0.78), radius=6, fill="white"
    )
    # Three "fingers"
    for i in range(3):
        x0 = size * 0.30 + i * size * 0.14
        draw.rounded_rectangle(
            (x0, size * 0.14, x0 + size * 0.09, size * 0.45), radius=4, fill="white"
        )
    return img


def _get_icon_image(active: bool) -> Image.Image:
    """Load the saved icon PNG for the given state, generating and
    saving it first if this is the very first run. Once a PNG exists
    on disk, it's loaded as-is and never regenerated — so replacing it
    with your own image sticks permanently."""
    path = ICON_ACTIVE_PATH if active else ICON_INACTIVE_PATH
    if os.path.exists(path):
        return Image.open(path)

    resource = ICON_ACTIVE_RESOURCE if active else ICON_INACTIVE_RESOURCE
    if os.path.exists(resource):
        return Image.open(resource)

    img = _generate_icon(COLOR_ACTIVE if active else COLOR_INACTIVE)
    try:
        img.save(path)
        print(f"[tray] Saved generated icon to {path} — replace this file any time to customize it.")
    except OSError as e:
        print(f"[tray] Could not save icon to {path}: {e}")
    return img


# ============================================================
# Gesture engine start/stop
# ============================================================

def _engine_running() -> bool:
    return _engine_thread is not None and _engine_thread.is_alive()


def _start_engine(icon):
    global _engine_thread, _engine_stop_event

    with _engine_lock:
        if _engine_running():
            return
        _engine_stop_event = threading.Event()
        stop_event = _engine_stop_event

        def runner():
            try:
                import main as gesture_main

                gesture_main.run_gesture_engine(stop_event, _preview_enabled)
            except Exception as e:
                print(f"[tray] Gesture engine stopped with an error: {e}")
            finally:
                icon.icon = _get_icon_image(active=False)
                icon.title = "Gesture Assistant (stopped)"
                icon.update_menu()

        _engine_thread = threading.Thread(target=runner, daemon=True, name="gesture-engine")
        icon.icon = _get_icon_image(active=True)
        icon.title = "Gesture Assistant (running)"
        _engine_thread.start()

    print("[tray] Gesture engine started.")
    if _engine_running():
        icon.update_menu()


def _stop_engine(icon, wait: bool = True):
    global _engine_thread

    with _engine_lock:
        if not _engine_running():
            return
        _engine_stop_event.set()
        thread = _engine_thread

    if wait:
        thread.join(timeout=5)

    print("[tray] Gesture engine stopped.")
    icon.icon = _get_icon_image(active=False)
    icon.title = "Gesture Assistant (stopped)"
    icon.update_menu()


def _toggle_engine(icon, item):
    if _engine_running():
        _stop_engine(icon)
    else:
        _start_engine(icon)


def _engine_menu_text(item) -> str:
    return "Stop Gesture Engine" if _engine_running() else "Start Gesture Engine"


def _toggle_preview(icon, item):
    if _preview_enabled.is_set():
        _preview_enabled.clear()
        print("[tray] Camera preview hidden; recognition is still running.")
    else:
        _preview_enabled.set()
        print("[tray] Camera preview enabled.")
    icon.update_menu()


def _preview_checked(item) -> bool:
    return _preview_enabled.is_set()


def _toggle_start_with_windows(icon, item):
    enabled = not is_start_with_windows_enabled()
    try:
        set_start_with_windows(enabled)
    except OSError as exc:
        print(f"[tray] Could not update Start with Windows: {exc}")
        return
    state = "enabled" if enabled else "disabled"
    print(f"[tray] Start with Windows {state}.")
    icon.update_menu()


def _startup_checked(item) -> bool:
    return is_start_with_windows_enabled()


# ============================================================
# Configure Gestures window (unchanged behavior, guarded against duplicates)
# ============================================================

def _open_config_window():
    global _gui_open

    with _gui_lock:
        if _gui_open:
            print("[tray] Configure window is already open.")
            return
        _gui_open = True

    def runner():
        global _gui_open
        try:
            import config_gui

            config_gui.open_config_window()
        except Exception as e:
            print(f"[tray] Config window closed with an error: {e}")
        finally:
            with _gui_lock:
                _gui_open = False

    threading.Thread(target=runner, daemon=True, name="config-gui").start()


def _on_configure(icon, item):
    _open_config_window()


def _exit_app(icon, item):
    _stop_engine(icon)
    print("[tray] Exiting Gesture Assistant.")
    icon.stop()


# ============================================================
# Tray icon
# ============================================================
#
def run_tray():
    """Build and run the tray icon until Exit is selected. This is meant
    to be called from the main thread."""
    menu = pystray.Menu(
        pystray.MenuItem(_engine_menu_text, _toggle_engine, default=True),
        pystray.MenuItem("Show Camera Preview", _toggle_preview, checked=_preview_checked),
        pystray.MenuItem("Configure Gestures", _on_configure),
        pystray.MenuItem(
            "Start with Windows",
            _toggle_start_with_windows,
            checked=_startup_checked,
        ),
        pystray.MenuItem("Exit", _exit_app),
    )
    icon = pystray.Icon(
        "gesture_assistant",
        icon=_get_icon_image(active=False),
        title="Gesture Assistant (stopped)",
        menu=menu,
    )
    print("[tray] Gesture Assistant is running in the system tray.")
    icon.run()


if __name__ == "__main__":
    run_tray()
