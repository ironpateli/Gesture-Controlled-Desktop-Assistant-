"""Create Windows launch shortcuts and configure per-user auto-start."""

import argparse
import ctypes
import os
import subprocess

import win32com.client
from PIL import Image, ImageDraw

from windows_integration import launch_parts, set_start_with_windows

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(BASE_DIR, "gesture_assistant.ico")
TRAY_PNG_FALLBACK = os.path.join(BASE_DIR, "tray_icon_inactive.png")
SHORTCUT_NAME = "Gesture Assistant.lnk"


def _draw_fallback_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, size - 2, size - 2), fill="#2d3142")
    draw.rounded_rectangle(
        (size * 0.32, size * 0.42, size * 0.68, size * 0.78),
        radius=6,
        fill="white",
    )
    for i in range(3):
        x0 = size * 0.30 + i * size * 0.14
        draw.rounded_rectangle(
            (x0, size * 0.14, x0 + size * 0.09, size * 0.45),
            radius=4,
            fill="white",
        )
    return img


def _ensure_ico() -> str:
    if os.path.exists(ICO_PATH):
        return ICO_PATH

    if os.path.exists(TRAY_PNG_FALLBACK):
        img = Image.open(TRAY_PNG_FALLBACK).convert("RGBA")
    else:
        img = _draw_fallback_icon()
    img.save(ICO_PATH, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"[setup] Created icon: {ICO_PATH}")
    return ICO_PATH


def _create_shortcut(shortcut_path: str, description: str) -> str:
    parts = launch_parts()
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = parts[0]
    shortcut.Arguments = subprocess.list2cmdline(parts[1:])
    shortcut.WorkingDirectory = BASE_DIR
    shortcut.IconLocation = _ensure_ico()
    shortcut.Description = description
    shortcut.Save()
    print(f"[setup] Created shortcut: {shortcut_path}")
    return shortcut_path


def _desktop_dir() -> str:
    path = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, path)
    if result != 0:
        raise OSError(f"Windows could not resolve the Desktop folder: {result}")
    return path.value


def _start_menu_dir() -> str:
    return os.path.join(
        os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
    )


def create_desktop_shortcut() -> str:
    return _create_shortcut(
        os.path.join(_desktop_dir(), SHORTCUT_NAME),
        "Launch Gesture Assistant",
    )


def create_start_menu_shortcut() -> str:
    return _create_shortcut(
        os.path.join(_start_menu_dir(), SHORTCUT_NAME),
        "Launch Gesture Assistant",
    )


def enable_startup() -> None:
    set_start_with_windows(True)
    print("[setup] Enabled Start with Windows.")


def disable_startup() -> None:
    set_start_with_windows(False)
    print("[setup] Disabled Start with Windows.")


def main():
    parser = argparse.ArgumentParser(description="Set up Gesture Assistant launchers.")
    parser.add_argument(
        "--desktop-only",
        action="store_true",
        help="Create only the Desktop shortcut",
    )
    parser.add_argument(
        "--startup-only",
        action="store_true",
        help="Enable only Start with Windows",
    )
    parser.add_argument(
        "--remove-startup",
        action="store_true",
        help="Disable Start with Windows",
    )
    args = parser.parse_args()

    if args.remove_startup:
        disable_startup()
        return

    if args.startup_only:
        enable_startup()
        return

    create_desktop_shortcut()
    if not args.desktop_only:
        create_start_menu_shortcut()
        enable_startup()

    print("[setup] Gesture Assistant launchers are ready.")


if __name__ == "__main__":
    main()
