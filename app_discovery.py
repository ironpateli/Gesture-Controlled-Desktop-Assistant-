"""
app_discovery.py

Scans the Windows Start Menu for installed apps by resolving .lnk
shortcuts to their real target .exe. Used by config_gui.py to populate
the "pick an app" dropdown without you having to hunt for install paths.

Two Start Menu locations are scanned:
  - Per-user:  %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
  - All users: %PROGRAMDATA%\\Microsoft\\Windows\\Start Menu\\Programs

Results are cached to app_cache.json (next to this file) so repeat scans
are instant. Delete that file (or call discover_apps(force_refresh=True))
if you install/uninstall something and want the list updated.

Requires pywin32 (already a project dependency) for shortcut resolution.
"""

import os
import json
import time

from app_paths import data_path

CACHE_PATH = data_path("app_cache.json")
CACHE_MAX_AGE_SECONDS = 60 * 60 * 24  # 1 day

try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False
    print("[app_discovery] pywin32 (win32com) not found — app discovery unavailable.")

# Shortcuts we never want to surface (uninstallers, help links, readmes, etc.)
_SKIP_NAME_SUBSTRINGS = (
    "uninstall", "unins000", "read me", "readme", "help",
    "license", "documentation", "website", "changelog",
)


def _start_menu_dirs():
    dirs = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        dirs.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        dirs.append(os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    return [d for d in dirs if os.path.isdir(d)]


def _resolve_shortcut(lnk_path: str):
    """Resolve a .lnk file to its target path. Returns None if it can't
    be resolved or doesn't point at a real executable."""
    if not WIN32COM_AVAILABLE:
        return None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target = shortcut.Targetpath
        if target and os.path.isfile(target):
            return target
    except Exception:
        # Some shortcuts are malformed, point at UWP apps (no real target),
        # or fail to resolve for other reasons — just skip them.
        return None
    return None


def _should_skip(name: str) -> bool:
    lowered = name.lower()
    return any(bad in lowered for bad in _SKIP_NAME_SUBSTRINGS)


def _scan_start_menu():
    """Walk both Start Menu folders, resolve every .lnk, and return a
    deduped, sorted list of {"name": ..., "path": ...} dicts."""
    apps = {}
    for root_dir in _start_menu_dirs():
        for dirpath, _subdirs, filenames in os.walk(root_dir):
            for filename in filenames:
                if not filename.lower().endswith(".lnk"):
                    continue
                name = os.path.splitext(filename)[0]
                if _should_skip(name):
                    continue
                target = _resolve_shortcut(os.path.join(dirpath, filename))
                if not target:
                    continue
                # Prefer the first match found (user Start Menu is scanned first)
                apps.setdefault(name, target)

    return sorted(
        ({"name": name, "path": path} for name, path in apps.items()),
        key=lambda a: a["name"].lower()
    )


def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r") as f:
            cache = json.load(f)
        if time.time() - cache.get("scanned_at", 0) > CACHE_MAX_AGE_SECONDS:
            return None
        return cache.get("apps")
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(apps):
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump({"scanned_at": time.time(), "apps": apps}, f, indent=2)
    except OSError as e:
        print(f"[app_discovery] Failed to write cache: {e}")


def discover_apps(force_refresh: bool = False):
    """Return a sorted list of {"name": ..., "path": ...} dicts for every
    resolvable Start Menu app. Uses a cache unless force_refresh=True."""
    if not WIN32COM_AVAILABLE:
        return []

    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            return cached

    apps = _scan_start_menu()
    _save_cache(apps)
    return apps


if __name__ == "__main__":
    found = discover_apps(force_refresh=True)
    print(f"Found {len(found)} apps:\n")
    for app in found:
        print(f"  {app['name']:<40} {app['path']}")
