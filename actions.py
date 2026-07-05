"""
actions.py

Decoupled action-dispatch layer: gesture name -> OS-level action.
Keeping this separate from gesture_detector.py means you can change
gestures or add new ones without touching action logic, and vice versa.
"""

import pyautogui

pyautogui.FAILSAFE = True  # move mouse to a screen corner to abort, safety net


def do_thumbs_up():
    print("[ACTION] Volume up")
    pyautogui.press("volumeup")


def do_thumbs_down():
    print("[ACTION] Volume down")
    pyautogui.press("volumedown")


def do_peace():
    print("[ACTION] Play/Pause media")
    pyautogui.press("playpause")


def do_point():
    print("[ACTION] Next slide / next track")
    pyautogui.press("right")


def do_rock():
    print("[ACTION] Screenshot")
    pyautogui.screenshot("gesture_screenshot.png")


GESTURE_ACTION_MAP = {
    "thumbs_up": do_thumbs_up,
    "thumbs_down": do_thumbs_down,
    "peace": do_peace,
    "point": do_point,
    "rock": do_rock,
}


def dispatch(gesture_name: str):
    action = GESTURE_ACTION_MAP.get(gesture_name)
    if action:
        action()
