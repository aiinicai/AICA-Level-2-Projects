"""
AICA SOP TOOL - Activity Recorder v3
=====================================

Records the active application, window title, duration, a screenshot, and
- new in v3 - the Windows File Explorer folder path.

Why this version exists
-----------------------
Folder paths were still reported as zero even after Interaction Capture v5
fixed its COM threading. The reason is that the two agents capture different
kinds of event:

    Interaction Capture   fires on a shortcut or mouse click
    Activity Recorder     fires when the active window changes

Navigating in File Explorer changes the active window but does not press a
shortcut. In a typical session every interaction event occurs inside Excel,
so the interaction agent's folder resolver is never invoked while Explorer is
in focus. The capability was present but had no opportunity to run.

Explorer navigation is recorded by THIS agent, so the folder path must be
resolved here.

What v3 adds
------------
1. A FolderPath column in activity_log.csv.
2. Thread-local COM initialisation, matching the approach proven in
   Interaction Capture v5, so the resolver works from the monitoring thread.
3. A self-test button that resolves every open Explorer window on demand, so
   the capability can be confirmed before recording rather than discovered
   afterwards.
4. Live counters showing how many lookups were attempted and resolved, so a
   silent failure cannot recur.

Output
------
    sessions/SESSION_YYYYMMDD_HHMMSS/
        activity_log.csv
        screenshots/step_001.png ...

CSV columns
-----------
    Timestamp, Application, WindowTitle, FolderPath,
    DurationSeconds, Screenshot

Install
-------
    python -m pip install pygetwindow pywin32 psutil pillow

Run
---
    python activity_recorder_v3.py

Build EXE
---------
    pyinstaller --onefile --noconsole --clean --name AICA_Recorder_v3 activity_recorder_v3.py
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


APP_TITLE = "AICA SOP Tool - Activity Recorder v3"
TOOL_NAME = "AICA SOP Tool"
BRAND = "#6B001B"
SUCCESS = "#1F7A1F"
WARN = "#9A6700"
ERROR = "#C00000"

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

SELF_TITLES = ("aica sop tool", "activity recorder",
               "interaction capture", "sop genius ai")

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
# Folder resolution, safe from any thread
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
    Resolves Explorer folder paths.

    COM is apartment-threaded, so each thread performing a lookup creates
    and holds its own Shell object in thread-local storage. This is the
    same approach proven in Interaction Capture v5.
    """

    def __init__(self):
        self._local = threading.local()
        self.attempts = 0
        self.successes = 0
        self.last_error = ""
        self._lock = threading.Lock()

    def _shell(self):
        if not SHELL_PATHS:
            return None
        shell = getattr(self._local, "shell", None)
        if shell is not None:
            return shell
        if getattr(self._local, "broken", False):
            return None
        try:
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("Shell.Application")
            self._local.shell = shell
            return shell
        except Exception as error:
            self._local.broken = True
            with self._lock:
                self.last_error = "COM init on {}: {}".format(
                    threading.current_thread().name, error)
            return None

    def resolve(self, hwnd, application, window_title=""):
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
                            path = window.Document.Folder.Self.Path or ""
                            break
                        except Exception:
                            continue
                except Exception as error:
                    with self._lock:
                        self.last_error = "Shell.Windows(): {}".format(error)
            if path:
                with self._lock:
                    self.successes += 1

        # A path shown in the window title covers terminal sessions.
        if not path and window_title:
            match = TITLE_PATH.search(window_title)
            if match:
                candidate = re.sub(r"\s{2,}.*$", "",
                                   match.group(0).strip()).strip()
                if len(candidate) > 6:
                    path = candidate

        return path

    def self_test(self):
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


# =========================================================
# Recorder
# =========================================================

class ActivityRecorder:

    def __init__(self):
        self.running = True
        self.stopped = False

        self.activity_count = 0
        self.shot_count = 0
        self.path_count = 0

        self.capture_images = True

        self.previous_window = None
        self.previous_app = None
        self.previous_path = ""
        self.pending_shot = ""

        self.current_app = "Waiting..."
        self.current_window = "Waiting..."
        self.current_path = "-"

        self.start_time = datetime.now()
        self.window_start_time = datetime.now()

        self.resolver = FolderResolver()
        self.write_lock = threading.Lock()

        stamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.session_name = "SESSION_" + stamp
        self.session_dir = os.path.join(base_dir(), "sessions",
                                        self.session_name)
        self.shot_dir = os.path.join(self.session_dir, "screenshots")
        os.makedirs(self.shot_dir, exist_ok=True)

        self.log_file = os.path.join(self.session_dir, "activity_log.csv")
        self._create_log()

    # ------------------------------------------------------
    def _create_log(self):
        with open(self.log_file, "w", newline="",
                  encoding="utf-8-sig") as handle:
            csv.writer(handle).writerow([
                "Timestamp", "Application", "WindowTitle", "FolderPath",
                "DurationSeconds", "Screenshot",
            ])

    # ------------------------------------------------------
    def write_log(self, application, window_title, folder,
                  duration, screenshot):
        try:
            with self.write_lock:
                with open(self.log_file, "a", newline="",
                          encoding="utf-8-sig") as handle:
                    csv.writer(handle).writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        application, window_title, folder,
                        duration, screenshot,
                    ])
                if folder:
                    self.path_count += 1
        except Exception:
            pass

    # ------------------------------------------------------
    def take_shot(self):
        if not self.capture_images:
            return ""
        try:
            self.shot_count += 1
            filename = "step_{:03d}.png".format(self.shot_count)
            ImageGrab.grab().save(
                os.path.join(self.shot_dir, filename), "PNG")
            return filename
        except Exception:
            return ""

    # ------------------------------------------------------
    def active(self):
        if not WINDOW_CONTEXT:
            return None, None, 0
        try:
            window = gw.getActiveWindow()
            if window is None:
                return None, None, 0
            title = window.title
            if not title:
                return None, None, 0
            hwnd = window._hWnd
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return friendly_app(process.name()), title, hwnd
        except Exception:
            return None, None, 0

    # ------------------------------------------------------
    def loop(self):
        while self.running:
            application, title, hwnd = self.active()

            if application and title:
                if any(token in title.lower() for token in SELF_TITLES):
                    self._sleep()
                    continue

                folder = self.resolver.resolve(hwnd, application, title)

                self.current_app = application
                self.current_window = title
                self.current_path = folder or "-"

                if self.previous_window is None:
                    self.previous_window = title
                    self.previous_app = application
                    self.previous_path = folder
                    self.window_start_time = datetime.now()
                    self.pending_shot = self.take_shot()

                elif title != self.previous_window:
                    now = datetime.now()
                    duration = int(
                        (now - self.window_start_time).total_seconds())

                    self.write_log(self.previous_app, self.previous_window,
                                   self.previous_path, duration,
                                   self.pending_shot)
                    self.activity_count += 1

                    self.previous_window = title
                    self.previous_app = application
                    self.previous_path = folder
                    self.window_start_time = now

                    time.sleep(0.35)
                    self.pending_shot = self.take_shot()

                elif folder and not self.previous_path:
                    # The path became resolvable after the window settled.
                    self.previous_path = folder

            self._sleep()

    def _sleep(self):
        for _ in range(4):
            if not self.running:
                return
            time.sleep(0.5)

    # ------------------------------------------------------
    def finalise(self):
        try:
            if self.previous_window:
                duration = int(
                    (datetime.now() - self.window_start_time).total_seconds())
                self.write_log(self.previous_app, self.previous_window,
                               self.previous_path, duration,
                               self.pending_shot)
                self.activity_count += 1
        except Exception:
            pass

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        self.running = False
        self.finalise()


# =========================================================
# Dashboard
# =========================================================

class RecorderWindow:

    def __init__(self, root):
        self.root = root
        self.recorder = ActivityRecorder()

        root.title(APP_TITLE)
        root.geometry("700x600")
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
        tk.Label(self._body, text="Activity Recorder | Version 3",
                 font=("Segoe UI", 9), bg="white", fg="gray").pack()

        self.status = tk.Label(self._body, text="RECORDING",
                               font=("Segoe UI", 12, "bold"),
                               bg="white", fg=SUCCESS)
        self.status.pack(pady=6)

        # ---- capability panel ----
        caps = tk.LabelFrame(self._body, text=" Capabilities ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        caps.pack(fill="x", padx=22, pady=4)

        self._cap(caps, "Window and duration capture",
                  "Enabled" if WINDOW_CONTEXT else
                  "Unavailable - install pywin32, psutil, pygetwindow",
                  SUCCESS if WINDOW_CONTEXT else ERROR)
        self._cap(caps, "Screenshots", "Enabled", SUCCESS)
        self._cap(caps, "Explorer folder paths",
                  "Library present - run the self-test to confirm"
                  if SHELL_PATHS else "Unavailable - install pywin32",
                  WARN if SHELL_PATHS else ERROR)

        test_row = tk.Frame(caps, bg="white")
        test_row.pack(fill="x", padx=12, pady=(2, 8))
        tk.Button(test_row, text="RUN FOLDER PATH SELF-TEST",
                  command=self.self_test, bg="#1F3864", fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  width=30, cursor="hand2").pack(side="left")
        self.test_label = tk.Label(test_row, text="Not tested", bg="white",
                                   fg="gray", font=("Segoe UI", 9),
                                   anchor="w", wraplength=320,
                                   justify="left")
        self.test_label.pack(side="left", padx=10)

        # ---- counters ----
        counters = tk.Frame(self._body, bg="white")
        counters.pack(fill="x", padx=22, pady=4)
        self.activity_label = self._counter(counters,
                                            "Activities recorded: 0", True)
        self.shot_label = self._counter(counters, "Screenshots captured: 0")
        self.path_label = self._counter(counters, "Folder paths captured: 0")
        self.duration_label = self._counter(counters,
                                            "Session duration: 00:00:00")
        self.diag_label = tk.Label(
            counters, text="Path lookups: 0 attempted, 0 resolved",
            bg="white", fg="gray", font=("Segoe UI", 8))
        self.diag_label.pack(anchor="w", pady=1)

        # ---- live context ----
        live = tk.LabelFrame(self._body, text=" Current window ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        live.pack(fill="x", padx=22, pady=6)
        self.app_label = tk.Label(live, text="Application: -", bg="white",
                                  font=("Segoe UI", 9), anchor="w",
                                  wraplength=630, justify="left")
        self.app_label.pack(fill="x", padx=12, pady=(6, 1))
        self.window_label = tk.Label(live, text="Window: -", bg="white",
                                     font=("Segoe UI", 9), anchor="w",
                                     wraplength=630, justify="left")
        self.window_label.pack(fill="x", padx=12, pady=1)
        self.path_live = tk.Label(live, text="Folder path: -", bg="white",
                                  font=("Consolas", 8), fg="#1F3864",
                                  anchor="w", wraplength=630, justify="left")
        self.path_live.pack(fill="x", padx=12, pady=(1, 7))

        toggles = tk.Frame(self._body, bg="white")
        toggles.pack(fill="x", padx=22, pady=2)
        self.image_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles, text="Capture screenshots",
                       variable=self.image_var, command=self.toggle_images,
                       bg="white", activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left")

        tk.Label(self._body, text="Session: " + self.recorder.session_name,
                 font=("Segoe UI", 8), bg="white", fg="gray").pack(pady=3)

        self.stop_button = tk.Button(self._body, text="STOP RECORDING", command=self.stop,
            font=("Segoe UI", 11, "bold"), bg="#C00000", fg="white",
            activebackground="#8B0000", activeforeground="white",
            width=22, relief="flat", cursor="hand2")
        self.stop_button.pack(pady=8)

        tk.Label(self._body,
                 text="Keyboard input is not captured  |  Use only with "
                      "informed consent",
                 font=("Segoe UI", 8), bg="white", fg="gray").pack(
            side="bottom", pady=6)

        root.protocol("WM_DELETE_WINDOW", self.stop)
        root.bind("<Escape>", self.stop)

        threading.Thread(target=self.recorder.loop, daemon=True).start()
        self.refresh()

    # ------------------------------------------------------
    def _cap(self, parent, label, value, colour):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=12, pady=2)
        tk.Label(row, text=label + ":", width=26, anchor="w", bg="white",
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row, text=value, bg="white", fg=colour,
                 font=("Segoe UI", 9), anchor="w", wraplength=380,
                 justify="left").pack(side="left")

    def _counter(self, parent, text, bold=False):
        label = tk.Label(parent, text=text, bg="white",
                         font=("Segoe UI", 10 if bold else 9,
                               "bold" if bold else "normal"))
        label.pack(anchor="w", pady=1)
        return label

    def toggle_images(self):
        self.recorder.capture_images = self.image_var.get()

    # ------------------------------------------------------
    def self_test(self):
        found, error = self.recorder.resolver.self_test()
        if error:
            self.test_label.config(text="FAILED - " + error[:150], fg=ERROR)
            messagebox.showerror(
                APP_TITLE,
                "Folder path capture is not working.\n\n{}\n\n"
                "Install pywin32:\n    python -m pip install pywin32\n\n"
                "Then open a File Explorer window and test again.".format(
                    error), parent=self.root)
            return
        if not found:
            self.test_label.config(
                text="No Explorer windows are open. Open one and test again.",
                fg=WARN)
            return
        self.test_label.config(
            text="Working - resolved {} path(s). First: {}".format(
                len(found), found[0][:60]), fg=SUCCESS)
        messagebox.showinfo(
            APP_TITLE,
            "Folder path capture is working.\n\n"
            "Resolved {} open Explorer window(s):\n\n{}".format(
                len(found), "\n".join(found[:6])), parent=self.root)

    # ------------------------------------------------------
    def refresh(self):
        r = self.recorder
        res = r.resolver
        elapsed = datetime.now() - r.start_time

        self.activity_label.config(
            text="Activities recorded: {}".format(r.activity_count))
        self.shot_label.config(
            text="Screenshots captured: {}".format(r.shot_count))
        self.path_label.config(
            text="Folder paths captured: {}".format(r.path_count),
            fg=SUCCESS if r.path_count else "black")
        self.duration_label.config(
            text="Session duration: " + str(elapsed).split(".")[0])

        diag = "Path lookups: {} attempted, {} resolved".format(
            res.attempts, res.successes)
        if res.last_error:
            diag += "  |  last error: " + res.last_error[:55]
        self.diag_label.config(
            text=diag, fg=ERROR if res.last_error else "gray")

        self.app_label.config(text="Application: " + r.current_app)
        self.window_label.config(text="Window: " + r.current_window[:90])
        self.path_live.config(text="Folder path: " + r.current_path)

        if r.running:
            self.root.after(1000, self.refresh)

    # ------------------------------------------------------
    def stop(self, event=None):
        if self.recorder.stopped:
            return
        self.recorder.stop()
        self.status.config(text="STOPPED", fg=ERROR)
        self.stop_button.config(state="disabled", text="STOPPED")
        self.root.update_idletasks()

        res = self.recorder.resolver
        summary = (
            "Recording stopped.\n\n"
            "Activities recorded: {0}\n"
            "Screenshots captured: {1}\n"
            "Folder paths captured: {2}\n\n"
            "Path lookups attempted: {3}\n"
            "Path lookups resolved: {4}\n\n"
            "Session folder:\n{5}\n\n"
            "Next: run Process Analyzer and select\n"
            "activity_log.csv from this folder."
        ).format(self.recorder.activity_count, self.recorder.shot_count,
                 self.recorder.path_count, res.attempts, res.successes,
                 self.recorder.session_dir)

        if res.last_error:
            summary += "\n\nLast path error:\n" + res.last_error

        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, summary, parent=self.root)

        try:
            os.startfile(self.recorder.session_dir)
        except Exception:
            pass

        self.root.destroy()
        os._exit(0)


if __name__ == "__main__":
    main_root = tk.Tk()
    RecorderWindow(main_root)
    main_root.mainloop()
