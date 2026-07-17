"""
actions.py

Decoupled action-dispatch layer: gesture name -> OS-level action.

Actions are no longer hardcoded — they're read from gestures_config.json
(same folder as this file). Each gesture maps to an entry like:

    "swipe_right": {"type": "uri", "target": "spotify:", "label": "Spotify"}

Supported "type" values:
    builtin  - one of the actions in BUILTIN_ACTIONS below
               (volume_up, volume_down, mute, play_pause,
                scroll_up, scroll_down, prev_tab, next_tab)
    uri      - a Windows URI protocol handler, e.g. "spotify:", "ms-settings:"
    path     - a direct path to an .exe (or any executable)
    script   - a path to a .py / .bat / .cmd / .ps1 file to run
    hotkey   - a list of keys to send together, e.g. ["ctrl", "shift", "s"]

If gestures_config.json is missing, a default one (matching the original
behavior) is created automatically on first run. A future config GUI will
read/write this same file — no code changes needed to remap a gesture.

Focus problem: OpenCV window steals focus from the browser, so
window-dependent actions (Ctrl+Tab, scroll) need focus management.

ACTIVE:    Option 3 — always-on-top non-focusing window (pywin32).
COMMENTED: Option 2 — alt+tab before each action (simpler, no install needed).

To use Option 2 instead:
  pip uninstall pywin32
  Uncomment Option 2 blocks below, comment out Option 3 blocks.
"""

import os
import sys
import json
import time
import subprocess
import pyautogui

from app_paths import data_path

pyautogui.FAILSAFE = True  # move mouse to screen corner to abort

CONFIG_PATH = data_path("gestures_config.json")
SCRIPTS_DIR = data_path("scripts")

DEFAULT_CONFIG = {
    "thumbs_up":   {"type": "builtin", "target": "volume_up",   "label": "Volume Up"},
    "thumbs_down": {"type": "builtin", "target": "volume_down", "label": "Volume Down"},
    "fist":        {"type": "builtin", "target": "mute",        "label": "Mute Toggle"},
    "peace":       {"type": "builtin", "target": "play_pause",  "label": "Play/Pause"},
    "swipe_left":  {"type": "builtin", "target": "prev_tab",    "label": "Previous Tab"},
    "swipe_right": {"type": "uri",     "target": "spotify:",    "label": "Spotify"},
    "swipe_up":    {"type": "uri",     "target": "ms-settings:","label": "Settings"},
    "swipe_down":  {"type": "builtin", "target": "scroll_down", "label": "Scroll Down"},
}

# The fixed set of gestures the model recognizes. config_gui.py builds its
# rows from this rather than hardcoding the list a second time.
GESTURE_NAMES = list(DEFAULT_CONFIG.keys())

# ============================================================
# OPTION 3 — Always-on-top window (active)
# pip install pywin32
# Call setup_always_on_top() once after cv2.imshow() in main.py
# ============================================================
try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[actions] pywin32 not found — Option 3 unavailable, falling back to Option 2 behavior.")


def setup_always_on_top(window_title: str):
    """Call this ONCE from main.py after the first cv2.imshow().
    Makes the OpenCV window float on top without stealing focus —
    so your browser stays focused while the webcam overlay stays visible.

    Usage in main.py (after first cv2.imshow call):
        from actions import setup_always_on_top
        setup_always_on_top('Gesture Assistant (Phase 2 - PyTorch LSTM)')
    """
    if not WIN32_AVAILABLE:
        print("[actions] pywin32 not installed — skipping always-on-top setup.")
        return
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,  # always on top
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE  # don't move or resize
            )
            print(f"[actions] Window '{window_title}' set to always-on-top.")
        else:
            print(f"[actions] Could not find window '{window_title}' for always-on-top.")
    except Exception as e:
        print(f"[actions] always-on-top setup failed: {e}")


# ============================================================
# OPTION 2 — Alt+Tab before window-dependent actions (commented)
# No extra install needed. Uncomment if you don't want pywin32.
# ============================================================
# def _focus_last_window():
#     """Switch focus away from OpenCV back to last used window."""
#     pyautogui.hotkey("alt", "tab")
#     time.sleep(0.15)


# ============================================================
# BUILT-IN ACTIONS — the "type": "builtin" targets
# ============================================================

def _volume_up():
    print("[ACTION] Volume up")
    pyautogui.press("volumeup")


def _volume_down():
    print("[ACTION] Volume down")
    pyautogui.press("volumedown")


def _mute():
    print("[ACTION] Mute toggle")
    pyautogui.press("volumemute")


def _play_pause():
    print("[ACTION] Play/Pause")
    pyautogui.press("playpause")


def _prev_tab():
    print("[ACTION] Previous tab")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.hotkey("ctrl", "shift", "tab")


def _next_tab():
    print("[ACTION] Next tab")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.hotkey("ctrl", "tab")


def _scroll_up():
    print("[ACTION] Scroll up")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.scroll(200)


def _scroll_down():
    print("[ACTION] Scroll down")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.scroll(-200)


# Registry the config GUI will offer as dropdown choices later.
BUILTIN_ACTIONS = {
    "volume_up":   _volume_up,
    "volume_down": _volume_down,
    "mute":        _mute,
    "play_pause":  _play_pause,
    "prev_tab":    _prev_tab,
    "next_tab":    _next_tab,
    "scroll_up":   _scroll_up,
    "scroll_down": _scroll_down,
}


# ============================================================
# ACTION RUNNERS — one per config "type"
# ============================================================

def _run_builtin(target: str):
    fn = BUILTIN_ACTIONS.get(target)
    if not fn:
        print(f"[actions] Unknown builtin action '{target}'. "
              f"Valid options: {list(BUILTIN_ACTIONS.keys())}")
        return
    fn()


def _run_uri(target: str):
    print(f"[ACTION] Open URI: {target}")
    try:
        os.startfile(target)
    except OSError as e:
        print(f"[actions] Failed to open URI '{target}': {e}")


def _run_path(target: str):
    print(f"[ACTION] Launch: {target}")
    if not os.path.exists(target):
        print(f"[actions] Path not found: {target}")
        return
    try:
        subprocess.Popen([target])
    except OSError as e:
        print(f"[actions] Failed to launch '{target}': {e}")


def _run_script(target: str):
    print(f"[ACTION] Run script: {target}")
    if not os.path.exists(target):
        print(f"[actions] Script not found: {target}")
        return
    ext = os.path.splitext(target)[1].lower()
    try:
        if ext == ".py":
            subprocess.Popen([sys.executable, target])
        elif ext == ".ps1":
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", target])
        elif ext in (".bat", ".cmd"):
            subprocess.Popen([target], shell=True)
        else:
            # Fall back to letting Windows figure out the file association.
            os.startfile(target)
    except OSError as e:
        print(f"[actions] Failed to run script '{target}': {e}")


def _run_hotkey(target):
    if isinstance(target, str):
        target = [target]
    print(f"[ACTION] Hotkey: {'+'.join(target)}")
    try:
        pyautogui.hotkey(*target)
    except Exception as e:
        print(f"[actions] Failed to send hotkey {target}: {e}")


ACTION_RUNNERS = {
    "builtin": _run_builtin,
    "uri":     _run_uri,
    "path":    _run_path,
    "script":  _run_script,
    "hotkey":  _run_hotkey,
}


# ============================================================
# CONFIG LOADING
# ============================================================

def _write_default_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"[actions] Created default config at {CONFIG_PATH}")


def load_config() -> dict:
    """Load gestures_config.json, creating it with defaults if missing
    or unreadable. Called fresh on every dispatch so external edits
    (e.g. from a future config GUI) are picked up without a restart."""
    if not os.path.exists(CONFIG_PATH):
        _write_default_config()
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[actions] Failed to read {CONFIG_PATH} ({e}) — using defaults.")
        return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """Write the full gesture->action config to disk. Writes to a temp
    file first and replaces atomically so a crash mid-write (or main.py
    reading concurrently) can't leave a corrupted/half-written file."""
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp_path, CONFIG_PATH)


# ============================================================
# DISPATCH
# ============================================================

def dispatch(gesture_name: str):
    config = load_config()
    entry = config.get(gesture_name)

    if not entry:
        print(f"[dispatch] No action configured for gesture: '{gesture_name}'")
        return

    action_type = entry.get("type")
    target = entry.get("target")
    runner = ACTION_RUNNERS.get(action_type)

    if not runner:
        print(f"[dispatch] Unknown action type '{action_type}' for gesture '{gesture_name}'")
        return
    if target is None:
        print(f"[dispatch] No target set for gesture '{gesture_name}'")
        return

    runner(target)
