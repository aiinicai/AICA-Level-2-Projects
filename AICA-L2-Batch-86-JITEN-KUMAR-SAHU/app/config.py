"""
=============================================================
  ClientLedger India — Configuration & First-Run Setup
=============================================================
Responsible for:
  1. Locating (or creating) config.json, which stores ONE thing:
     the path to the user's chosen "Base Data Folder".
  2. Deriving every working path (SQLite DB, GSTR1/2A/2B/3B,
     TDS/TCS download folders, browser profiles, logs, etc.)
     from that single base folder, using fixed sub-folder names.
  3. Showing a one-time graphical setup wizard (Tkinter — ships
     with Python, no extra install) the very first time the app
     runs, so the accountant picks where their data should live
     (e.g. a folder on drive D:, a NAS mount, a synced Dropbox folder).

config.json itself is NOT stored inside the data folder — it is
stored in the normal per-OS "app config" location, so the app
can always find the data folder on next launch even before it
has opened that folder:

    Windows:  %APPDATA%/ClientLedgerIndia/config.json
    macOS:    ~/Library/Application Support/ClientLedgerIndia/config.json
    Linux:    ~/.config/ClientLedgerIndia/config.json
=============================================================
"""

import os
import sys
import json
import platform

APP_NAME = "ClientLedgerIndia"

# Fixed sub-folder names created inside the base data folder.
# These are the names referenced in the product spec:
#   Database, GSTR1, GSTR2A, GSTR2B, GSTR3B, TDS_TCS
SUBFOLDERS = {
    "database": "Database",
    "gstr1": "GSTR1",
    "gstr2a": "GSTR2A",
    "gstr2b": "GSTR2B",
    "gstr3b": "GSTR3B",
    "tdstcs": "TDS_TCS",
    # Internal-use folders (not part of the user-facing spec, but need
    # a home too): browser automation profiles, logs, gstin name cache.
    "system": "System",
}


def _app_config_dir():
    """Per-OS location for the small config.json pointer file."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(base, APP_NAME)
    elif system == "Darwin":
        return os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, APP_NAME)


CONFIG_DIR = _app_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Allow overriding entirely via env var — useful for dev/testing and
# for silent/unattended installs (installer can write this before
# first launch instead of relying on the GUI wizard).
_ENV_OVERRIDE = os.environ.get("CLIENTLEDGER_DATA_DIR")


def _read_config():
    if not os.path.isfile(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_config(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


def get_data_dir(create=True):
    """
    Return the base data folder path, running the first-run wizard
    if none has been configured yet. Always returns an absolute path.
    """
    if _ENV_OVERRIDE:
        path = os.path.abspath(_ENV_OVERRIDE)
        if create:
            ensure_folder_structure(path)
        return path

    cfg = _read_config()
    path = cfg.get("data_dir")

    if not path or not os.path.isdir(path):
        path = run_setup_wizard(suggested=path)
        cfg["data_dir"] = path
        _write_config(cfg)

    if create:
        ensure_folder_structure(path)
    return path


def set_data_dir(path):
    """Explicitly set/change the base data folder (e.g. from an in-app
    'Change data location' settings option)."""
    path = os.path.abspath(path)
    ensure_folder_structure(path)
    cfg = _read_config()
    cfg["data_dir"] = path
    _write_config(cfg)
    return path


def ensure_folder_structure(base):
    os.makedirs(base, exist_ok=True)
    for name in SUBFOLDERS.values():
        os.makedirs(os.path.join(base, name), exist_ok=True)
    # A couple of internal sub-sub-folders under System/
    for name in ("profiles", "logs", "gstin_names", "cache"):
        os.makedirs(os.path.join(base, SUBFOLDERS["system"], name), exist_ok=True)


def run_setup_wizard(suggested=None):
    """
    One-time GUI folder picker. Falls back to a console prompt if
    Tkinter isn't available (e.g. headless server use) or if the
    CLIENTLEDGER_HEADLESS env var is set.
    """
    default_dir = suggested or os.path.join(
        os.path.expanduser("~"),
        "Documents" if platform.system() != "Linux" else "",
        "ClientLedger India Data",
    )
    default_dir = os.path.normpath(default_dir)

    if os.environ.get("CLIENTLEDGER_HEADLESS"):
        ensure_folder_structure(default_dir)
        return default_dir

    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox

        root = tk.Tk()
        root.title("ClientLedger India — First-Time Setup")
        root.geometry("560x300")
        root.resizable(False, False)

        chosen = {"path": default_dir}

        tk.Label(
            root,
            text="Welcome to ClientLedger India",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(18, 4))

        tk.Label(
            root,
            text=(
                "Choose the folder where all your data will be stored:\n"
                "the client database, and separate folders for\n"
                "GSTR-1, GSTR-2A, GSTR-2B, GSTR-3B and TDS/TCS files.\n\n"
                "Pick a location you back up regularly (a local drive,\n"
                "an external drive, or a synced folder)."
            ),
            justify="center",
        ).pack(pady=(0, 14))

        path_var = tk.StringVar(value=default_dir)
        entry_frame = tk.Frame(root)
        entry_frame.pack(fill="x", padx=24)
        entry = tk.Entry(entry_frame, textvariable=path_var, width=52)
        entry.pack(side="left", fill="x", expand=True)

        def browse():
            d = filedialog.askdirectory(
                title="Choose ClientLedger India data folder",
                initialdir=path_var.get() or os.path.expanduser("~"),
            )
            if d:
                path_var.set(d)

        tk.Button(entry_frame, text="Browse…", command=browse).pack(side="left", padx=(6, 0))

        def confirm():
            p = path_var.get().strip()
            if not p:
                messagebox.showerror("ClientLedger India", "Please choose a folder.")
                return
            try:
                ensure_folder_structure(p)
            except Exception as e:
                messagebox.showerror("ClientLedger India", f"Could not create folders here:\n{e}")
                return
            chosen["path"] = os.path.abspath(p)
            root.destroy()

        tk.Button(
            root, text="Continue", command=confirm, width=18, height=2,
            bg="#1a73e8", fg="white",
        ).pack(pady=22)

        tk.Label(
            root,
            text="You can change this later from Settings.",
            fg="#666666",
        ).pack()

        root.protocol("WM_DELETE_WINDOW", confirm)
        root.mainloop()
        return chosen["path"]

    except Exception:
        # No display / Tkinter unavailable — fall back to console.
        print("=" * 56)
        print("  ClientLedger India — First-time setup")
        print("=" * 56)
        print(f"  Press Enter to use the default data folder:\n  {default_dir}")
        print("  ...or type a full path to use instead.")
        try:
            typed = input("  Data folder: ").strip()
        except Exception:
            typed = ""
        path = typed or default_dir
        ensure_folder_structure(path)
        return os.path.abspath(path)


# ── Convenience path accessors — call get_data_dir() once per process
#    and derive everything else from it. ────────────────────────────

class Paths:
    """Resolved, ready-to-use paths. Build once at process start via
    `Paths.load()`."""

    def __init__(self, base):
        self.base = base
        self.database_dir = os.path.join(base, SUBFOLDERS["database"])
        self.db_file = os.path.join(self.database_dir, "clientledger.db")

        self.gstr1_dir = os.path.join(base, SUBFOLDERS["gstr1"])
        self.gstr2a_dir = os.path.join(base, SUBFOLDERS["gstr2a"])
        self.gstr2b_dir = os.path.join(base, SUBFOLDERS["gstr2b"])
        self.gstr3b_dir = os.path.join(base, SUBFOLDERS["gstr3b"])
        self.tdstcs_dir = os.path.join(base, SUBFOLDERS["tdstcs"])

        system_dir = os.path.join(base, SUBFOLDERS["system"])
        self.system_dir = system_dir
        self.profiles_dir = os.path.join(system_dir, "profiles")
        self.logs_dir = os.path.join(system_dir, "logs")
        self.gstin_names_dir = os.path.join(system_dir, "gstin_names")
        self.cache_dir = os.path.join(system_dir, "cache")

        self.log_file = os.path.join(self.logs_dir, "gst_rpa_activity.log")
        self.gst_cache_file = os.path.join(self.cache_dir, "gst_cache.json")
        self.clients_backup_file = os.path.join(self.database_dir, "clients_backup.json")
        self.fy_config_file = os.path.join(self.cache_dir, "fy_config.json")

    @classmethod
    def load(cls):
        base = get_data_dir(create=True)
        return cls(base)
