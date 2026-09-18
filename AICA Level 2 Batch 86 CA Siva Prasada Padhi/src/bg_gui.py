#!/usr/bin/env python3
"""
BANK GUARANTEE MONITORING — desktop window

A simple graphical front-end for bg_monitor_exe.py.  Keep both files in the
same folder along with key.json.

    python bg_gui.py

Build as a windowed application:

    python -m PyInstaller --onefile --windowed --name BG_Monitor_App bg_gui.py
"""

import io
import os
import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext

# In a --windowed build there is no console, so sys.stdout can be None.
# Anything that prints before we redirect would then crash.
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import bg_monitor_exe as engine

APP_TITLE = "Bank Guarantee Monitoring System"
ORG_NAME = "Your Organisation"        # shown in the window header
PASSWORD_ENV = "BG_GMAIL_APP_PASSWORD"

BG_DARK = "#1f2933"
BG_PANEL = "#f4f6f8"
ACCENT = "#1a73e8"
WARN = "#c62828"
OK = "#1b7a3d"


class TextRedirector(io.TextIOBase):
    """Sends anything the engine prints into the on-screen log box."""

    def __init__(self, widget, tag=None):
        self.widget = widget
        self.tag = tag

    def write(self, text):
        if text:
            self.widget.after(0, self._append, text)
        return len(text)

    def _append(self, text):
        self.widget.configure(state="normal")
        self.widget.insert("end", text, self.tag)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class BGApp:
    def __init__(self, root):
        self.root = root
        self.running = False

        root.title(APP_TITLE)
        root.geometry("1100x700")
        root.minsize(820, 540)
        root.configure(bg=BG_PANEL)

        # Open maximised. "zoomed" works on Windows; the fallbacks cover
        # Linux and macOS so the file still runs everywhere.
        try:
            root.state("zoomed")
        except tk.TclError:
            try:
                root.attributes("-zoomed", True)
            except tk.TclError:
                root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")

        root.bind("<F11>", lambda e: root.attributes(
            "-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

        # ── Header ────────────────────────────────────────────────────────
        header = tk.Frame(root, bg=BG_DARK, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text=APP_TITLE, bg=BG_DARK, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=20)
        tk.Label(header, text=ORG_NAME, bg=BG_DARK, fg="#9aa5b1",
                 font=("Segoe UI", 10)).pack(side="right", padx=20)

        # ── Password row ──────────────────────────────────────────────────
        pw_frame = tk.Frame(root, bg=BG_PANEL)
        pw_frame.pack(fill="x", padx=20, pady=(18, 4))

        tk.Label(pw_frame, text="Gmail App Password", bg=BG_PANEL,
                 font=("Segoe UI", 10)).pack(side="left")

        self.pw_var = tk.StringVar(value=os.environ.get(PASSWORD_ENV, ""))
        self.pw_entry = tk.Entry(pw_frame, textvariable=self.pw_var, show="\u2022",
                                 width=26, font=("Consolas", 11), relief="solid", bd=1)
        self.pw_entry.pack(side="left", padx=10)

        self.show_pw = tk.IntVar(value=0)
        tk.Checkbutton(pw_frame, text="show", variable=self.show_pw,
                       command=self._toggle_pw, bg=BG_PANEL).pack(side="left")

        tk.Label(pw_frame, text="(16 characters, no spaces — needed only for sending)",
                 bg=BG_PANEL, fg="#616e7c", font=("Segoe UI", 9)).pack(side="left", padx=8)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=BG_PANEL)
        btn_frame.pack(fill="x", padx=20, pady=12)

        self.btn_preview = self._button(
            btn_frame, "Preview what is due", ACCENT, self.on_preview)
        self.btn_test = self._button(
            btn_frame, "Send test mail to myself", OK, self.on_test)
        self.btn_send = self._button(
            btn_frame, "Run and send reminders", WARN, self.on_send)
        self.btn_dash = self._button(
            btn_frame, "Open dashboard", "#4c3f91", self.on_dashboard)

        tk.Button(btn_frame, text="Clear", command=self.clear_log,
                  font=("Segoe UI", 10), bg="#e4e7eb", relief="flat",
                  padx=14, pady=8, cursor="hand2").pack(side="right")

        # ── Log box ───────────────────────────────────────────────────────
        tk.Label(root, text="Output", bg=BG_PANEL, fg="#3e4c59",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)

        self.log = scrolledtext.ScrolledText(
            root, wrap="word", font=("Consolas", 10), bg="#111820", fg="#e5e9f0",
            insertbackground="white", relief="flat", padx=12, pady=10)
        self.log.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        self.log.configure(state="disabled")
        self.log.tag_configure("error", foreground="#ff8f8f")
        self.log.tag_configure("note", foreground="#7dd3a0")

        # ── Status bar ────────────────────────────────────────────────────
        self.status = tk.Label(root, text="Ready    ·    F11 full screen, Esc to exit full screen", bg="#e4e7eb", fg="#3e4c59",
                               anchor="w", font=("Segoe UI", 9), padx=14, pady=6)
        self.status.pack(fill="x", side="bottom")

        self.write("Preview and Dashboard are always safe — they send nothing and\n"
                   "write nothing. Whether the other two buttons reach vendors or only\n"
                   "you depends on SYSTEM_MODE in the Config tab of the spreadsheet.\n\n",
                   "note")

    # ── small helpers ─────────────────────────────────────────────────────

    def _button(self, parent, text, colour, command):
        b = tk.Button(parent, text=text, command=command, bg=colour, fg="white",
                      font=("Segoe UI", 10, "bold"), relief="flat",
                      padx=16, pady=9, cursor="hand2", activebackground=colour)
        b.pack(side="left", padx=(0, 10))
        return b

    def _toggle_pw(self):
        self.pw_entry.configure(show="" if self.show_pw.get() else "\u2022")

    def write(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_busy(self, busy, message="Ready"):
        self.running = busy
        state = "disabled" if busy else "normal"
        for b in (self.btn_preview, self.btn_test, self.btn_send, self.btn_dash):
            b.configure(state=state)
        self.status.configure(text=message)

    # ── button actions ────────────────────────────────────────────────────

    def on_preview(self):
        self.run_engine(["--preview"], "Reading the sheet...")

    def on_test(self):
        if not self.require_password():
            return
        self.run_engine(["--test"], "Sending test mail...")

    def on_send(self):
        if not self.require_password():
            return
        confirm = messagebox.askyesno(
            "Confirm",
            "This runs the monitor for real.\n\n"
            "If SYSTEM_MODE in the Config tab is set to PRODUCTION, notices — "
            "including 10-day invocation warnings — will go to the vendor "
            "addresses in the sheet.\n\n"
            "Have you previewed the list first?",
            icon="warning")
        if confirm:
            self.run_engine([], "Processing and sending...")

    def on_dashboard(self):
        # The import is deferred into the worker thread so that a missing or
        # broken bg_dashboard module reports itself in the output panel. In a
        # --windowed build there is no console for a traceback to land in.
        self.run_engine([], "Building the dashboard...", func=self._build_dashboard)

    def _build_dashboard(self):
        import bg_dashboard
        bg_dashboard.main()
        print("\nIf the dashboard did not open by itself, look for "
              "BG_Dashboard.html in this application's folder and open it "
              "in your browser.")

    def require_password(self):
        pw = self.pw_var.get().strip()
        if not pw:
            messagebox.showwarning(
                "App password needed",
                "Enter your 16-character Gmail App Password before sending.\n\n"
                "This is not your normal Gmail password. Generate one at "
                "myaccount.google.com under Security.")
            self.pw_entry.focus_set()
            return False
        os.environ[PASSWORD_ENV] = pw
        return True

    # ── engine runner ─────────────────────────────────────────────────────

    def run_engine(self, argv, busy_text, func=None):
        if self.running:
            return
        self.set_busy(True, busy_text)
        self.write(f"\n{'─' * 62}\n", "note")

        thread = threading.Thread(target=self._worker, args=(argv, func), daemon=True)
        thread.start()

    def _worker(self, argv, func=None):
        old_out, old_err, old_argv = sys.stdout, sys.stderr, sys.argv
        sys.stdout = TextRedirector(self.log)
        sys.stderr = TextRedirector(self.log, "error")
        sys.argv = ["bg_monitor"] + argv
        message = "Finished"
        try:
            (func or engine.main)()
        except SystemExit as stop:
            # engine.main() calls sys.exit() with a message on setup problems
            if str(stop) not in ("0", "None"):
                print(f"\n{stop}\n", file=sys.stderr)
                message = "Stopped — see output"
        except Exception:
            traceback.print_exc(file=sys.stderr)
            message = "Error — see output"
        finally:
            sys.stdout, sys.stderr, sys.argv = old_out, old_err, old_argv
            self.root.after(0, self.set_busy, False, message)


def main():
    root = tk.Tk()
    BGApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
