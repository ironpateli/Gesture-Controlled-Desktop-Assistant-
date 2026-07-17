"""
config_gui.py

Tkinter window for assigning what each gesture does. Reads/writes
gestures_config.json via actions.load_config() / actions.save_config(),
so main.py picks up changes on the very next gesture — no restart needed.

Run standalone to test:
    python config_gui.py

In the full app, tray.py opens this same window from the tray icon menu.
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import actions
import app_discovery

SCRIPT_EXTENSIONS = [
    ("Scripts", "*.py *.bat *.cmd *.ps1"),
    ("All files", "*.*"),
]

ACTION_TYPES = [
    ("builtin", "Built-in action"),
    ("path", "Launch an app"),
    ("uri", "Open a URI"),
    ("script", "Run a script"),
    ("hotkey", "Keyboard shortcut"),
]

# Friendly names for the built-in action dropdown
BUILTIN_LABELS = {
    "volume_up": "Volume Up",
    "volume_down": "Volume Down",
    "mute": "Mute Toggle",
    "play_pause": "Play/Pause",
    "prev_tab": "Previous Tab",
    "next_tab": "Next Tab",
    "scroll_up": "Scroll Up",
    "scroll_down": "Scroll Down",
}

GESTURE_LABELS = {
    "thumbs_up": "Thumbs Up",
    "thumbs_down": "Thumbs Down",
    "fist": "Fist",
    "peace": "Peace",
    "swipe_left": "Swipe Left",
    "swipe_right": "Swipe Right",
    "swipe_up": "Swipe Up",
    "swipe_down": "Swipe Down",
}

# ---- Shared color palette ----
COLOR_BG = "#f4f5f7"          # window background
COLOR_HEADER_BG = "#2d3142"   # dark header bar
COLOR_HEADER_TEXT = "#ffffff"
COLOR_ROW_BG = "#ffffff"      # each gesture row
COLOR_ROW_BORDER = "#c9cdd4"
COLOR_TEXT = "#22223b"
COLOR_TEXT_MUTED = "#6c757d"
COLOR_ACCENT_BLUE = "#4361ee"    # Edit button
COLOR_ACCENT_GREEN = "#2a9d8f"   # Save button
COLOR_CANCEL = "#9aa1ab"         # Cancel/secondary button


# ============================================================
# Pure helper functions (no Tkinter) — kept separate so they're testable
# without a display.
# ============================================================

def copy_script_to_scripts_dir(source_path: str) -> str:
    """Copy an uploaded script into actions.SCRIPTS_DIR and return the
    new path. Overwrites if a script with the same name already exists."""
    os.makedirs(actions.SCRIPTS_DIR, exist_ok=True)
    filename = os.path.basename(source_path)
    dest_path = os.path.join(actions.SCRIPTS_DIR, filename)
    shutil.copy2(source_path, dest_path)
    return dest_path


def parse_hotkey_event(keysym: str, state: int):
    """Turn a Tkinter key event into a pyautogui-style key list, e.g.
    Ctrl+Shift+S -> ["ctrl", "shift", "s"]. Returns None for a bare
    modifier press (nothing to record yet)."""
    modifier_keysyms = {
        "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
        "Win_L", "Win_R", "Super_L", "Super_R",
    }
    if keysym in modifier_keysyms:
        return None

    keys = []
    # Tkinter state bitmask: 0x4 = Control, 0x1 = Shift, 0x20000/0x8 = Alt
    if state & 0x4:
        keys.append("ctrl")
    if state & 0x1:
        keys.append("shift")
    if state & 0x20000 or state & 0x8:
        keys.append("alt")

    key = keysym.lower()
    # Normalize a few common keysym names to pyautogui's expected names
    key = {"return": "enter", "prior": "pageup", "next": "pagedown"}.get(key, key)
    keys.append(key)
    return keys


def describe_entry(entry: dict) -> str:
    """Human-readable one-line summary of a gesture's current action,
    shown in the main window's list."""
    if not entry:
        return "(unassigned)"
    action_type = entry.get("type")
    label = entry.get("label")
    if label:
        return f"{label}  [{action_type}]"
    return f"{entry.get('target', '?')}  [{action_type}]"


# ============================================================
# GUI
# ============================================================

class EditGestureDialog(tk.Toplevel):
    """Modal dialog for configuring a single gesture's action."""

    def __init__(self, parent, gesture_name: str, current_entry: dict, on_save):
        super().__init__(parent)
        self.title(f"Configure: {GESTURE_LABELS.get(gesture_name, gesture_name)}")
        self.geometry("440x390")
        self.minsize(400, 340)
        self.configure(bg=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self.gesture_name = gesture_name
        self.on_save = on_save
        self.selected_app_path = current_entry.get("target") if current_entry.get("type") == "path" else None
        self.selected_script_path = current_entry.get("target") if current_entry.get("type") == "script" else None
        self.hotkey_keys = current_entry.get("target") if current_entry.get("type") == "hotkey" else None

        self._build_widgets(current_entry)

    def _build_widgets(self, current_entry: dict):
        pad = {"padx": 10, "pady": 6}

        # Pack the button bar FIRST with side="bottom" so it reserves its
        # space at the bottom of the window no matter how tall the body
        # content above it grows. (Packing it last, after an expand=True
        # body frame, is what was pushing it off-screen before.)
        btn_frame = tk.Frame(self, bg=COLOR_BG)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="Save", command=self._save, width=10,
                  bg=COLOR_ACCENT_GREEN, fg="white", relief="flat",
                  activebackground="#238a7f", cursor="hand2").pack(side="right")
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10,
                  bg=COLOR_CANCEL, fg="white", relief="flat",
                  activebackground="#8a929c", cursor="hand2").pack(side="right", padx=6)

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg=COLOR_TEXT_MUTED, bg=COLOR_BG,
                 wraplength=380, justify="left").pack(side="bottom", anchor="w", padx=10)

        tk.Label(self, text="Action type:", font=("Segoe UI", 10, "bold"),
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w", **pad)

        self.type_var = tk.StringVar(value=current_entry.get("type", "builtin"))
        type_frame = tk.Frame(self, bg=COLOR_BG)
        type_frame.pack(anchor="w", padx=10)
        for value, label in ACTION_TYPES:
            tk.Radiobutton(
                type_frame, text=label, variable=self.type_var, value=value,
                command=self._refresh_body, bg=COLOR_BG, fg=COLOR_TEXT,
                selectcolor=COLOR_ROW_BG, activebackground=COLOR_BG,
            ).pack(anchor="w")

        self.body_frame = tk.Frame(self, bg=COLOR_BG)
        self.body_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self._current_entry = current_entry
        self._refresh_body()

    def _clear_body(self):
        for widget in self.body_frame.winfo_children():
            widget.destroy()

    def _refresh_body(self):
        self._clear_body()
        action_type = self.type_var.get()
        if action_type == "builtin":
            self._build_builtin_body()
        elif action_type == "path":
            self._build_app_body()
        elif action_type == "uri":
            self._build_uri_body()
        elif action_type == "script":
            self._build_script_body()
        elif action_type == "hotkey":
            self._build_hotkey_body()

    def _build_builtin_body(self):
        tk.Label(self.body_frame, text="Choose a built-in action:", bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        current_target = self._current_entry.get("target") if self._current_entry.get("type") == "builtin" else None
        display_values = list(BUILTIN_LABELS.values())
        self.builtin_var = tk.StringVar(
            value=BUILTIN_LABELS.get(current_target, display_values[0])
        )
        combo = ttk.Combobox(self.body_frame, textvariable=self.builtin_var, values=display_values, state="readonly")
        combo.pack(fill="x", pady=6)

    def _build_app_body(self):
        tk.Label(self.body_frame, text="Pick an installed app, or browse for one:",
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")

        apps = app_discovery.discover_apps()
        app_names = [a["name"] for a in apps]
        self._apps_by_name = {a["name"]: a["path"] for a in apps}

        current_label = self._current_entry.get("label", "")
        self.app_var = tk.StringVar(value=current_label if current_label in app_names else "")

        combo = ttk.Combobox(self.body_frame, textvariable=self.app_var, values=app_names, state="readonly")
        combo.pack(fill="x", pady=6)
        if not apps:
            tk.Label(self.body_frame, text="(No Start Menu apps found — use Browse instead)",
                     bg=COLOR_BG, fg=COLOR_TEXT_MUTED).pack(anchor="w")

        tk.Button(self.body_frame, text="Browse for .exe...", command=self._browse_app,
                  bg=COLOR_ACCENT_BLUE, fg="white", relief="flat",
                  activebackground="#3651c9", cursor="hand2").pack(anchor="w", pady=4)

        if self._current_entry.get("type") == "path" and current_label not in app_names:
            self.status_var.set(f"Currently: {self._current_entry.get('target', '')}")

    def _build_uri_body(self):
        tk.Label(
            self.body_frame,
            text="Enter a Windows or application URI (for example, spotify:):",
            bg=COLOR_BG,
            fg=COLOR_TEXT,
        ).pack(anchor="w")
        current_target = self._current_entry.get("target", "") if self._current_entry.get("type") == "uri" else ""
        self.uri_var = tk.StringVar(value=current_target)
        tk.Entry(self.body_frame, textvariable=self.uri_var).pack(fill="x", pady=6)

    def _browse_app(self):
        path = filedialog.askopenfilename(title="Choose an application", filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if path:
            self.selected_app_path = path
            self.app_var.set(os.path.splitext(os.path.basename(path))[0])
            self.status_var.set(f"Selected: {path}")

    def _build_script_body(self):
        tk.Label(self.body_frame, text="Upload a script to run (.py, .bat, .cmd, .ps1):",
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        tk.Button(self.body_frame, text="Upload...", command=self._browse_script,
                  bg=COLOR_ACCENT_BLUE, fg="white", relief="flat",
                  activebackground="#3651c9", cursor="hand2").pack(anchor="w", pady=6)
        if self.selected_script_path:
            self.status_var.set(f"Current: {os.path.basename(self.selected_script_path)}")

    def _browse_script(self):
        path = filedialog.askopenfilename(title="Choose a script", filetypes=SCRIPT_EXTENSIONS)
        if path:
            self.status_var.set(f"Selected: {os.path.basename(path)} (will be copied into scripts/)")
            self._pending_script_source = path

    def _build_hotkey_body(self):
        tk.Label(self.body_frame, text="Click below, then press your key combo:",
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        self.hotkey_display = tk.StringVar(
            value="+".join(self.hotkey_keys) if self.hotkey_keys else "(none set)"
        )
        entry = tk.Entry(self.body_frame, textvariable=self.hotkey_display, state="readonly", justify="center",
                          font=("Segoe UI", 12))
        entry.pack(fill="x", pady=6)
        entry.bind("<KeyPress>", self._on_hotkey_press)
        entry.bind("<Button-1>", lambda e: entry.focus_set())
        tk.Label(self.body_frame, text="(Focus the box above, then press e.g. Ctrl+Shift+S)",
                 bg=COLOR_BG, fg=COLOR_TEXT_MUTED).pack(anchor="w")

    def _on_hotkey_press(self, event):
        keys = parse_hotkey_event(event.keysym, event.state)
        if keys is None:
            return  # bare modifier press, wait for the real key
        self.hotkey_keys = keys
        self.hotkey_display.set("+".join(keys))

    def _save(self):
        action_type = self.type_var.get()
        entry = None

        if action_type == "builtin":
            label = self.builtin_var.get()
            target = next((k for k, v in BUILTIN_LABELS.items() if v == label), None)
            if not target:
                messagebox.showerror("Error", "Pick a built-in action.")
                return
            entry = {"type": "builtin", "target": target, "label": label}

        elif action_type == "path":
            chosen_name = self.app_var.get()
            if chosen_name in getattr(self, "_apps_by_name", {}):
                path = self._apps_by_name[chosen_name]
                label = chosen_name
            elif self.selected_app_path:
                path = self.selected_app_path
                label = os.path.splitext(os.path.basename(path))[0]
            else:
                messagebox.showerror("Error", "Pick an app or browse for one.")
                return
            entry = {"type": "path", "target": path, "label": label}

        elif action_type == "uri":
            target = self.uri_var.get().strip()
            if not target:
                messagebox.showerror("Error", "Enter a URI first.")
                return
            current_label = self._current_entry.get("label")
            current_target = self._current_entry.get("target")
            label = current_label if current_label and target == current_target else target
            entry = {"type": "uri", "target": target, "label": label}

        elif action_type == "script":
            source = getattr(self, "_pending_script_source", None) or self.selected_script_path
            if not source:
                messagebox.showerror("Error", "Upload a script first.")
                return
            if source != self.selected_script_path:
                # newly uploaded — copy into scripts/
                dest = copy_script_to_scripts_dir(source)
            else:
                dest = source
            entry = {"type": "script", "target": dest, "label": os.path.basename(dest)}

        elif action_type == "hotkey":
            if not self.hotkey_keys:
                messagebox.showerror("Error", "Press a key combo first.")
                return
            entry = {"type": "hotkey", "target": self.hotkey_keys, "label": "+".join(self.hotkey_keys)}

        self.on_save(self.gesture_name, entry)
        self.destroy()


class ConfigGUI(tk.Tk):
    """Main window listing all 8 gestures with their current action.
    Click a row's Edit button to reassign it."""

    def __init__(self):
        super().__init__()
        self.title("Gesture Assistant — Configure Actions")
        self.geometry("520x480")
        self.minsize(420, 320)
        self.configure(bg=COLOR_BG)

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG)
        header.pack(fill="x")
        tk.Label(header, text="Gesture -> Action", font=("Segoe UI", 15, "bold"),
                 bg=COLOR_HEADER_BG, fg=COLOR_HEADER_TEXT).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(header, text="Click Edit to change what a gesture does.",
                 bg=COLOR_HEADER_BG, fg="#c7cad1").pack(anchor="w", padx=16, pady=(0, 14))

        # --- Scrollable row area ---
        # A fixed-size Frame won't grow with the window or scroll when its
        # content is taller than the visible area, so the row list lives
        # inside a Canvas (which CAN scroll) with a Scrollbar next to it.
        scroll_container = tk.Frame(self, bg=COLOR_BG)
        scroll_container.pack(fill="both", expand=True, padx=12, pady=12)

        self.canvas = tk.Canvas(scroll_container, bg=COLOR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas, bg=COLOR_BG)

        self.rows_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._rows_window = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        # Keep the inner frame's width matched to the canvas so rows stretch full-width
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._rows_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling (Windows sends <MouseWheel> with event.delta)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- Footer ---
        footer = tk.Frame(self, bg=COLOR_BG)
        footer.pack(fill="x", pady=(0, 12))
        tk.Button(footer, text="Refresh App List", command=self._refresh_apps,
                  bg=COLOR_ACCENT_BLUE, fg="white", relief="flat",
                  activebackground="#3651c9", cursor="hand2", padx=10, pady=4
                  ).pack()

        self._row_labels = {}
        self._build_rows()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_rows(self):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        config = actions.load_config()

        for gesture_name in actions.GESTURE_NAMES:
            # A bordered "card" per gesture so rows are visually distinct
            # from the page background instead of blending together.
            row = tk.Frame(self.rows_frame, bg=COLOR_ROW_BG, highlightbackground=COLOR_ROW_BORDER,
                            highlightthickness=1, bd=0)
            row.pack(fill="x", pady=5, padx=2)

            tk.Label(row, text=GESTURE_LABELS.get(gesture_name, gesture_name), width=14, anchor="w",
                     bg=COLOR_ROW_BG, fg=COLOR_TEXT, font=("Segoe UI", 10, "bold")
                     ).pack(side="left", padx=(10, 4), pady=10)

            desc_var = tk.StringVar(value=describe_entry(config.get(gesture_name)))
            self._row_labels[gesture_name] = desc_var
            tk.Label(row, textvariable=desc_var, anchor="w", bg=COLOR_ROW_BG, fg=COLOR_TEXT_MUTED
                     ).pack(side="left", fill="x", expand=True, pady=10)

            tk.Button(row, text="Edit", command=lambda g=gesture_name: self._edit(g),
                      bg=COLOR_ACCENT_BLUE, fg="white", relief="flat",
                      activebackground="#3651c9", cursor="hand2", padx=10
                      ).pack(side="right", padx=10, pady=10)

    def _edit(self, gesture_name):
        config = actions.load_config()
        current_entry = config.get(gesture_name, {})
        EditGestureDialog(self, gesture_name, current_entry, self._on_gesture_saved)

    def _on_gesture_saved(self, gesture_name, entry):
        config = actions.load_config()
        config[gesture_name] = entry
        actions.save_config(config)
        self._row_labels[gesture_name].set(describe_entry(entry))

    def _refresh_apps(self):
        app_discovery.discover_apps(force_refresh=True)
        messagebox.showinfo("Done", "App list refreshed from Start Menu.")


def open_config_window():
    """Entry point called from tray.py (or run directly for testing)."""
    app = ConfigGUI()
    app.mainloop()


if __name__ == "__main__":
    open_config_window()
