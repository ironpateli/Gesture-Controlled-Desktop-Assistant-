"""Shared filesystem locations for development and packaged builds."""

import os
import sys

APP_NAME = "Gesture Assistant"
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "GestureAssistant",
    )
else:
    RESOURCE_DIR = SOURCE_DIR
    DATA_DIR = SOURCE_DIR


def ensure_data_dir() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return DATA_DIR


def resource_path(filename: str) -> str:
    return os.path.join(RESOURCE_DIR, filename)


def data_path(filename: str) -> str:
    ensure_data_dir()
    return os.path.join(DATA_DIR, filename)
