"""
actions.py

Decoupled action-dispatch layer: gesture name -> OS-level action.
Updated for Phase 2 gesture set:
  Static:  thumbs_up, thumbs_down, fist, peace
  Motion:  swipe_left, swipe_right, swipe_up, swipe_down

Focus problem: OpenCV window steals focus from the browser, so
window-dependent actions (Ctrl+Tab, scroll) need focus management.

ACTIVE:    Option 3 — always-on-top non-focusing window (pywin32).
COMMENTED: Option 2 — alt+tab before each action (simpler, no install needed).

To use Option 2 instead:
  pip uninstall pywin32
  Uncomment Option 2 blocks below, comment out Option 3 blocks.
"""

import time
import pyautogui

pyautogui.FAILSAFE = True  # move mouse to screen corner to abort

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


# --- Static gestures (OS-level keys, no focus needed) ---

def do_thumbs_up():
    """Volume up — global OS key, always works regardless of focus."""
    print("[ACTION] Volume up")
    pyautogui.press("volumeup")


def do_thumbs_down():
    """Volume down — global OS key, always works regardless of focus."""
    print("[ACTION] Volume down")
    pyautogui.press("volumedown")


def do_fist():
    """Mute / unmute — global OS key, always works regardless of focus."""
    print("[ACTION] Mute toggle")
    pyautogui.press("volumemute")


def do_peace():
    """Play / pause — global OS media key, always works regardless of focus."""
    print("[ACTION] Play/Pause")
    pyautogui.press("playpause")


# --- Motion gestures (window-dependent — need focus management) ---

def do_swipe_left():
    """Previous browser tab.
    Option 3: works if always-on-top is set (browser retains focus).
    Option 2: uncomment _focus_last_window() line below instead."""
    print("[ACTION] Swipe left → previous tab")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.hotkey("ctrl", "shift", "tab")


def do_swipe_right():
    """Next browser tab.
    Option 3: works if always-on-top is set (browser retains focus).
    Option 2: uncomment _focus_last_window() line below instead."""
    print("[ACTION] Swipe right → next tab")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.hotkey("ctrl", "tab")


def do_swipe_up():
    """Scroll up.
    Option 3: works if always-on-top is set (browser retains focus).
    Option 2: uncomment _focus_last_window() line below instead."""
    print("[ACTION] Swipe up → scroll up")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.scroll(5)


def do_swipe_down():
    """Scroll down.
    Option 3: works if always-on-top is set (browser retains focus).
    Option 2: uncomment _focus_last_window() line below instead."""
    print("[ACTION] Swipe down → scroll down")
    # _focus_last_window()  # Option 2: uncomment this line
    pyautogui.scroll(-5)


GESTURE_ACTION_MAP = {
    "thumbs_up":   do_thumbs_up,
    "thumbs_down": do_thumbs_down,
    "fist":        do_fist,
    "peace":       do_peace,
    "swipe_left":  do_swipe_left,
    "swipe_right": do_swipe_right,
    "swipe_up":    do_swipe_up,
    "swipe_down":  do_swipe_down,
}


def dispatch(gesture_name: str):
    action = GESTURE_ACTION_MAP.get(gesture_name)
    if action:
        action()
    else:
        print(f"[dispatch] No action mapped for gesture: '{gesture_name}'")