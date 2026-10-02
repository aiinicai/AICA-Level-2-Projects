"""
AICA SOP TOOL - Interaction Capture Agent v5
=============================================

Fixes the folder-path capture failure present in v4.

The v4 defect
-------------
v4 initialised COM and created the Shell.Application object on the main
Tkinter thread. However, folder lookups are triggered from two OTHER
threads:

    - the keyboard library's low-level hook thread (shortcuts)
    - the pynput listener thread (mouse clicks)

COM is apartment-threaded. An object created in one apartment cannot be
used from a thread that has not itself called CoInitialize. Every lookup
therefore raised an exception, which was silently swallowed by a bare
except clause. The dashboard still showed "Enabled" because the main-thread
initialisation had succeeded, so the failure was invisible.

The v5 fix
----------
1. COM is initialised PER THREAD using thread-local storage. The first
   lookup on any thread creates its own Shell object in its own apartment.
2. Failures are counted and the last error is shown on the dashboard, so a
   silent failure can no longer occur.
3. A SELF-TEST button resolves the path of any open Explorer window on
   demand, letting you confirm the capability works before recording.
4. Folder paths are also resolved for non-Explorer windows where a path is
   present in the window title, which helps for terminal sessions.

Output
------
    sessions/INTERACTION_YYYYMMDD_HHMMSS/
        interaction_log.csv
        screenshots/evt_001.png ...

Install
-------
    python -m pip install keyboard pynput pillow psutil pygetwindow pywin32

Run (Administrator recommended)
-------------------------------
    python interaction_capture_v5.py

Build EXE
---------
    pyinstaller --onefile --noconsole --clean --name AICA_Interaction_v5 interaction_capture_v5.py
"""

import csv
import os
import re
import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

import keyboard
from pynput import mouse
from PIL import ImageGrab

try:
    import psutil
    import pygetwindow as gw
    import win32process
    WINDOW_CONTEXT = True
except Exception:
    WINDOW_CONTEXT = False

try:
    import pythoncom
    import win32com.client
    SHELL_PATHS = True
except Exception:
    SHELL_PATHS = False


APP_TITLE = "AICA SOP Tool - Interaction Capture v5"
TOOL_NAME = "AICA SOP Tool"
BRAND = "#6B001B"
SUCCESS = "#1F7A1F"
WARN = "#9A6700"
ERROR = "#C00000"

SHORTCUTS = {
    "ctrl+c": "Ctrl+C - Copy",
    "ctrl+v": "Ctrl+V - Paste",
    "ctrl+s": "Ctrl+S - Save",
    "ctrl+x": "Ctrl+X - Cut",
    "ctrl+z": "Ctrl+Z - Undo",
    "ctrl+y": "Ctrl+Y - Redo",
    "ctrl+p": "Ctrl+P - Print",
    "ctrl+a": "Ctrl+A - Select All",
    "ctrl+f": "Ctrl+F - Find",
    "ctrl+n": "Ctrl+N - New",
    "ctrl+o": "Ctrl+O - Open",
    "ctrl+w": "Ctrl+W - Close",
    "alt+tab": "Alt+Tab - Switch Application",
    "f5": "F5 - Refresh",
    "f9": "F9 - Calculate",
    "f12": "F12 - Save As",
}

APP_NAMES = {
    "excel.exe": "Microsoft Excel",
    "winword.exe": "Microsoft Word",
    "powerpnt.exe": "Microsoft PowerPoint",
    "outlook.exe": "Microsoft Outlook",
    "onenote.exe": "Microsoft OneNote",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "pbidesktop.exe": "Power BI Desktop",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "explorer.exe": "Windows File Explorer",
    "notepad.exe": "Notepad",
    "code.exe": "Visual Studio Code",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "Windows PowerShell",
    "windowsterminal.exe": "Windows Terminal",
    "acrobat.exe": "Adobe Acrobat",
    "acrord32.exe": "Adobe Acrobat Reader",
    "saplogon.exe": "SAP Logon",
    "tally.exe": "Tally",
    "m365copilot.exe": "Microsoft 365 Copilot",
}

SELF_TITLES = ("aica sop tool", "interaction capture", "sop genius ai")

# A Windows path appearing inside a window title, e.g. a terminal caption.
TITLE_PATH = re.compile(r"[A-Za-z]:\\[^\r\n\"'<>|*?]{3,160}")


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def friendly_app(executable):
    if not executable:
        return "Unknown Application"
    return APP_NAMES.get(executable.lower(), executable.replace(".exe", ""))


# =========================================================
# Per-thread COM folder resolution
# =========================================================

# --- AICA scrollable window helper ---
def attach_scroll(window, bg="white"):
    """
    Return a frame that scrolls vertically inside the given window.

    Every widget placed in the returned frame can be reached by scrolling,
    so content below the fold stays accessible on a smaller display. The
    window itself keeps its own title, geometry and protocol handlers.
    """
    import tkinter as _tk
    from tkinter import ttk as _ttk

    outer = _tk.Frame(window, bg=bg)
    outer.pack(fill="both", expand=True)

    canvas = _tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    bar = _ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)

    canvas.pack(side="left", fill="both", expand=True)
    body = _tk.Frame(canvas, bg=bg)
    holder = canvas.create_window((0, 0), window=body, anchor="nw")

    def _content_changed(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        needed = body.winfo_reqheight() > canvas.winfo_height()
        if needed and not bar.winfo_ismapped():
            bar.pack(side="right", fill="y")
        elif not needed and bar.winfo_ismapped():
            bar.pack_forget()

    def _width_changed(event):
        canvas.itemconfigure(holder, width=event.width)
        _content_changed()

    body.bind("<Configure>", _content_changed)
    canvas.bind("<Configure>", _width_changed)

    def _wheel(event):
        if body.winfo_reqheight() <= canvas.winfo_height():
            return
        step = -1 if getattr(event, "delta", 0) > 0 else 1
        canvas.yview_scroll(step, "units")

    def _wheel_on(_event=None):
        canvas.bind_all("<MouseWheel>", _wheel)

    def _wheel_off(_event=None):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _wheel_on)
    canvas.bind("<Leave>", _wheel_off)

    def _key(event):
        if event.keysym == "Prior":
            canvas.yview_scroll(-1, "pages")
        elif event.keysym == "Next":
            canvas.yview_scroll(1, "pages")
        elif event.keysym == "Home":
            canvas.yview_moveto(0)
        elif event.keysym == "End":
            canvas.yview_moveto(1)

    for key in ("<Prior>", "<Next>", "<Home>", "<End>"):
        window.bind(key, _key)

    return body
# --- end helper ---


class FolderResolver:
    """
    Resolves Explorer folder paths safely from any thread.

    Each thread that performs a lookup initialises its own COM apartment
    and holds its own Shell object in thread-local storage.
    """

    def __init__(self):
        self._local = threading.local()
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.last_error = ""
        self._lock = threading.Lock()

    # ------------------------------------------------------
    def _shell(self):
        """Return a Shell object valid on the CALLING thread."""
        if not SHELL_PATHS:
            return None

        shell = getattr(self._local, "shell", None)
        if shell is not None:
            return shell

        if getattr(self._local, "broken", False):
            return None

        try:
            # Initialise COM for THIS thread. This is the v4 fix.
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("Shell.Application")
            self._local.shell = shell
            return shell
        except Exception as error:
            self._local.broken = True
            with self._lock:
                self.last_error = "COM init on thread {}: {}".format(
                    threading.current_thread().name, error)
            return None

    # ------------------------------------------------------
    def resolve(self, hwnd, application, window_title=""):
        """Return the folder path for the given window, or an empty string."""
        path = ""

        if application == "Windows File Explorer" and hwnd:
            with self._lock:
                self.attempts += 1

            shell = self._shell()
            if shell is not None:
                try:
                    for window in shell.Windows():
                        try:
                            if int(window.HWND) != int(hwnd):
                                continue
                            folder = window.Document.Folder
                            path = folder.Self.Path or ""
                            break
                        except Exception:
                            continue
                except Exception as error:
                    with self._lock:
                        self.last_error = "Shell.Windows(): {}".format(error)

            with self._lock:
                if path:
                    self.successes += 1
                else:
                    self.failures += 1

        # Fall back to a path visible in the window title, which covers
        # terminal sessions and some dialog captions.
        if not path and window_title:
            match = TITLE_PATH.search(window_title)
            if match:
                candidate = match.group(0).strip()
                candidate = re.sub(r"\s{2,}.*$", "", candidate).strip()
                if len(candidate) > 6:
                    path = candidate

        return path

    # ------------------------------------------------------
    def self_test(self):
        """Resolve every open Explorer window. Used by the dashboard."""
        if not SHELL_PATHS:
            return [], "pywin32 is not installed."

        shell = self._shell()
        if shell is None:
            return [], self.last_error or "Shell object could not be created."

        found = []
        try:
            for window in shell.Windows():
                try:
                    path = window.Document.Folder.Self.Path
                    if path:
                        found.append(path)
                except Exception:
                    continue
        except Exception as error:
            return [], str(error)

        return found, ""


class WindowContext:
    """Resolves the active application and window title."""

    @staticmethod
    def active():
        if not WINDOW_CONTEXT:
            return "Unknown Application", "", 0
        try:
            window = gw.getActiveWindow()
            if window is None:
                return "Unknown Application", "", 0
            title = window.title or ""
            hwnd = window._hWnd
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return friendly_app(process.name()), title, hwnd
        except Exception:
            return "Unknown Application", "", 0


# =========================================================
# Capture engine
# =========================================================

class InteractionCapture:

    def __init__(self):
        self.running = False
        self.stopping = False

        self.event_count = 0
        self.keyboard_count = 0
        self.mouse_count = 0
        self.shot_count = 0
        self.path_count = 0

        self.capture_images = True
        self.capture_mouse = True

        self.mouse_listener = None
        self.write_lock = threading.Lock()
        self.shot_lock = threading.Lock()

        self.last_event = {}
        self.last_click_time = 0.0
        self.last_click_button = None

        self.last_application = "-"
        self.last_window = "-"
        self.last_path = "-"

        self.resolver = FolderResolver()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = "INTERACTION_" + stamp
        self.session_dir = os.path.join(
            base_dir(), "sessions", self.session_name)
        self.shot_dir = os.path.join(self.session_dir, "screenshots")
        os.makedirs(self.shot_dir, exist_ok=True)

        self.log_file = os.path.join(self.session_dir, "interaction_log.csv")
        self._create_log()

    # ------------------------------------------------------
    def _create_log(self):
        with open(self.log_file, "w", newline="",
                  encoding="utf-8-sig") as handle:
            csv.writer(handle).writerow([
                "Timestamp", "EventType", "Action", "Application",
                "WindowTitle", "FolderPath", "MouseX", "MouseY", "Screenshot",
            ])

    # ------------------------------------------------------
    def _duplicate(self, key, interval=0.30):
        now = time.monotonic()
        previous = self.last_event.get(key, 0.0)
        self.last_event[key] = now
        return (now - previous) < interval

    # ------------------------------------------------------
    def take_shot(self):
        if not self.capture_images:
            return ""
        try:
            with self.shot_lock:
                self.shot_count += 1
                filename = "evt_{:03d}.png".format(self.shot_count)
                path = os.path.join(self.shot_dir, filename)
            ImageGrab.grab().save(path, "PNG")
            return filename
        except Exception:
            return ""

    # ------------------------------------------------------
    def record(self, event_type, action, mouse_x="", mouse_y=""):
        if not self.running:
            return
        if self._duplicate("{}:{}".format(event_type, action)):
            return

        application, title, hwnd = WindowContext.active()

        if title and any(token in title.lower() for token in SELF_TITLES):
            return

        folder = self.resolver.resolve(hwnd, application, title)

        time.sleep(0.12)
        screenshot = self.take_shot()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        with self.write_lock:
            with open(self.log_file, "a", newline="",
                      encoding="utf-8-sig") as handle:
                csv.writer(handle).writerow([
                    timestamp, event_type, action, application,
                    title, folder, mouse_x, mouse_y, screenshot,
                ])

            self.event_count += 1
            if event_type == "Keyboard Shortcut":
                self.keyboard_count += 1
            elif event_type == "Mouse":
                self.mouse_count += 1
            if folder:
                self.path_count += 1

            self.last_application = application or "-"
            self.last_window = (title or "-")[:70]
            self.last_path = folder or "-"

    # ------------------------------------------------------
    def on_shortcut(self, action):
        self.record("Keyboard Shortcut", action)

    def on_click(self, x, y, button, pressed):
        if not self.running or not pressed or not self.capture_mouse:
            return
        now = time.monotonic()
        double = (
            button == mouse.Button.left
            and self.last_click_button == button
            and (now - self.last_click_time) <= 0.45
        )
        if double:
            action = "Double Left Click"
            self.last_event.pop("Mouse:{}".format(action), None)
        elif button == mouse.Button.left:
            action = "Left Click"
        elif button == mouse.Button.right:
            action = "Right Click"
        elif button == mouse.Button.middle:
            action = "Middle Click"
        else:
            action = "{} Click".format(
                str(button).replace("Button.", "").title())

        self.last_click_time = now
        self.last_click_button = button
        self.record("Mouse", action, int(x), int(y))

    # ------------------------------------------------------
    def start(self):
        if self.running:
            return
        self.running = True
        self.stopping = False
        try:
            for combination, action in SHORTCUTS.items():
                keyboard.add_hotkey(
                    combination,
                    lambda chosen=action: self.on_shortcut(chosen),
                    suppress=False, trigger_on_release=False)
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.mouse_listener.start()
        except Exception:
            self.running = False
            self._release()
            raise

    def _release(self):
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
        except Exception:
            pass
        self.mouse_listener = None

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        self.running = False
        self._release()


# =========================================================
# Dashboard
# =========================================================

class CaptureWindow:

    def __init__(self, root):
        self.root = root
        self.capture = InteractionCapture()

        root.title(APP_TITLE)
        root.geometry("720x620")
        root.resizable(True, True)
        root.configure(bg="white")
        root.attributes("-topmost", True)
        root.after(1200, lambda: root.attributes("-topmost", False))
        # Scrollable body. Widgets are placed here so content
        # below the fold can be reached by scrolling.
        self._body = attach_scroll(root)


        tk.Label(self._body, text=TOOL_NAME.upper(),
                 font=("Segoe UI", 20, "bold"),
                 bg="white", fg=BRAND).pack(pady=(14, 2))
        tk.Label(self._body, text="Interaction Capture Agent | Version 5",
                 font=("Segoe UI", 9), bg="white", fg="gray").pack()

        self.status = tk.Label(self._body, text="STARTING...",
                               font=("Segoe UI", 12, "bold"),
                               bg="white", fg=WARN)
        self.status.pack(pady=6)

        # ---- capability panel ----
        caps = tk.LabelFrame(self._body, text=" Capabilities ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        caps.pack(fill="x", padx=22, pady=4)

        self._cap(caps, "Event-level screenshots", "Enabled", SUCCESS)
        self._cap(caps, "Window context per event",
                  "Enabled" if WINDOW_CONTEXT else
                  "Unavailable - install pywin32, psutil, pygetwindow",
                  SUCCESS if WINDOW_CONTEXT else ERROR)
        self._cap(caps, "Explorer folder paths",
                  "Library present - run the self-test to confirm"
                  if SHELL_PATHS else "Unavailable - install pywin32",
                  WARN if SHELL_PATHS else ERROR)

        test_row = tk.Frame(caps, bg="white")
        test_row.pack(fill="x", padx=12, pady=(2, 8))
        tk.Button(test_row, text="RUN FOLDER PATH SELF-TEST",
                  command=self.self_test, bg="#1F3864", fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  width=30).pack(side="left")
        self.test_label = tk.Label(test_row, text="Not tested",
                                   bg="white", fg="gray",
                                   font=("Segoe UI", 9), anchor="w",
                                   wraplength=330, justify="left")
        self.test_label.pack(side="left", padx=10)

        # ---- counters ----
        counters = tk.Frame(self._body, bg="white")
        counters.pack(fill="x", padx=22, pady=4)
        self.total_label = self._counter(counters, "Total events: 0", True)
        self.keyboard_label = self._counter(counters, "Keyboard shortcuts: 0")
        self.mouse_label = self._counter(counters, "Mouse actions: 0")
        self.shot_label = self._counter(counters, "Screenshots captured: 0")
        self.path_label = self._counter(counters, "Folder paths captured: 0")
        self.diag_label = tk.Label(
            counters, text="Path lookups: 0 attempted, 0 resolved",
            bg="white", fg="gray", font=("Segoe UI", 8))
        self.diag_label.pack(anchor="w", pady=1)

        # ---- live context ----
        live = tk.LabelFrame(self._body, text=" Last captured context ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        live.pack(fill="x", padx=22, pady=6)
        self.app_label = tk.Label(live, text="Application: -", bg="white",
                                  font=("Segoe UI", 9), anchor="w",
                                  wraplength=650, justify="left")
        self.app_label.pack(fill="x", padx=12, pady=(6, 1))
        self.window_label = tk.Label(live, text="Window: -", bg="white",
                                     font=("Segoe UI", 9), anchor="w",
                                     wraplength=650, justify="left")
        self.window_label.pack(fill="x", padx=12, pady=1)
        self.path_live = tk.Label(live, text="Folder path: -", bg="white",
                                  font=("Consolas", 8), fg="#1F3864",
                                  anchor="w", wraplength=650, justify="left")
        self.path_live.pack(fill="x", padx=12, pady=(1, 7))

        # ---- toggles ----
        toggles = tk.Frame(self._body, bg="white")
        toggles.pack(fill="x", padx=22, pady=2)
        self.image_var = tk.BooleanVar(value=True)
        self.mouse_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles, text="Capture screenshots",
                       variable=self.image_var, command=self.toggle_images,
                       bg="white", activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left")
        tk.Checkbutton(toggles, text="Capture mouse clicks",
                       variable=self.mouse_var, command=self.toggle_mouse,
                       bg="white", activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left", padx=16)

        tk.Label(self._body, text="Session: " + self.capture.session_name,
                 font=("Segoe UI", 8), bg="white", fg="gray").pack(pady=3)

        self.stop_button = tk.Button(self._body, text="STOP CAPTURE", command=self.stop,
            font=("Segoe UI", 11, "bold"), bg="#C00000", fg="white",
            activebackground="#8B0000", activeforeground="white",
            width=22, relief="flat", cursor="hand2")
        self.stop_button.pack(pady=8)

        tk.Label(self._body,
                 text="Typed text and clipboard contents are never captured  "
                      "|  Use only with informed consent",
                 font=("Segoe UI", 8), bg="white", fg="gray").pack(
            side="bottom", pady=6)

        root.protocol("WM_DELETE_WINDOW", self.stop)
        root.bind("<Escape>", self.stop)

        try:
            self.capture.start()
            self.status.config(text="RECORDING", fg=SUCCESS)
        except Exception as error:
            self.status.config(text="FAILED TO START", fg=ERROR)
            messagebox.showerror(
                APP_TITLE,
                "Could not install keyboard or mouse hooks.\n\n"
                "Try running Command Prompt as Administrator.\n\n"
                "{}".format(error), parent=root)

        self.refresh()

    # ------------------------------------------------------
    def _cap(self, parent, label, value, colour):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=12, pady=2)
        tk.Label(row, text=label + ":", width=26, anchor="w", bg="white",
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row, text=value, bg="white", fg=colour,
                 font=("Segoe UI", 9), anchor="w", wraplength=400,
                 justify="left").pack(side="left")

    def _counter(self, parent, text, bold=False):
        label = tk.Label(parent, text=text, bg="white",
                         font=("Segoe UI", 10 if bold else 9,
                               "bold" if bold else "normal"))
        label.pack(anchor="w", pady=1)
        return label

    def toggle_images(self):
        self.capture.capture_images = self.image_var.get()

    def toggle_mouse(self):
        self.capture.capture_mouse = self.mouse_var.get()

    # ------------------------------------------------------
    def self_test(self):
        """Prove folder-path capture works before recording begins."""
        found, error = self.capture.resolver.self_test()
        if error:
            self.test_label.config(
                text="FAILED - " + error[:160], fg=ERROR)
            messagebox.showerror(
                APP_TITLE,
                "Folder path capture is not working.\n\n{}\n\n"
                "Confirm pywin32 is installed:\n"
                "    python -m pip install pywin32\n\n"
                "Then open at least one File Explorer window and test "
                "again.".format(error), parent=self.root)
            return

        if not found:
            self.test_label.config(
                text="No Explorer windows are open. Open one and test again.",
                fg=WARN)
            return

        self.test_label.config(
            text="Working - resolved {} path(s). First: {}".format(
                len(found), found[0][:70]),
            fg=SUCCESS)
        messagebox.showinfo(
            APP_TITLE,
            "Folder path capture is working.\n\n"
            "Resolved {} open Explorer window(s):\n\n{}".format(
                len(found), "\n".join(found[:6])), parent=self.root)

    # ------------------------------------------------------
    def refresh(self):
        c = self.capture
        r = c.resolver
        self.total_label.config(text="Total events: {}".format(c.event_count))
        self.keyboard_label.config(
            text="Keyboard shortcuts: {}".format(c.keyboard_count))
        self.mouse_label.config(
            text="Mouse actions: {}".format(c.mouse_count))
        self.shot_label.config(
            text="Screenshots captured: {}".format(c.shot_count))
        self.path_label.config(
            text="Folder paths captured: {}".format(c.path_count),
            fg=SUCCESS if c.path_count else "black")

        diag = "Path lookups: {} attempted, {} resolved".format(
            r.attempts, r.successes)
        if r.last_error:
            diag += "  |  last error: " + r.last_error[:60]
        self.diag_label.config(
            text=diag, fg=ERROR if r.last_error else "gray")

        self.app_label.config(text="Application: " + c.last_application)
        self.window_label.config(text="Window: " + c.last_window)
        self.path_live.config(text="Folder path: " + c.last_path)

        if c.running:
            self.root.after(500, self.refresh)

    # ------------------------------------------------------
    def stop(self, event=None):
        if self.capture.stopping:
            return
        self.capture.stop()
        self.status.config(text="STOPPED", fg=ERROR)
        self.stop_button.config(state="disabled", text="STOPPED")
        self.root.update_idletasks()

        r = self.capture.resolver
        summary = (
            "Capture stopped.\n\n"
            "Total events: {0}\n"
            "Keyboard shortcuts: {1}\n"
            "Mouse actions: {2}\n"
            "Screenshots captured: {3}\n"
            "Folder paths captured: {4}\n\n"
            "Path lookups attempted: {5}\n"
            "Path lookups resolved: {6}\n\n"
            "Session folder:\n{7}\n\n"
            "Next: run Process Analyzer and select\n"
            "interaction_log.csv from this folder."
        ).format(
            self.capture.event_count, self.capture.keyboard_count,
            self.capture.mouse_count, self.capture.shot_count,
            self.capture.path_count, r.attempts, r.successes,
            self.capture.session_dir)

        if r.last_error:
            summary += "\n\nLast path error:\n" + r.last_error

        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, summary, parent=self.root)

        try:
            os.startfile(self.capture.session_dir)
        except Exception:
            pass

        self.root.destroy()
        os._exit(0)


if __name__ == "__main__":
    main_root = tk.Tk()
    CaptureWindow(main_root)
    main_root.mainloop()
