"""Complete GST Suite - one-file launcher for the web app (new design).

Built with PyInstaller --onefile. The exe carries node.exe and the built web app
inside it, so nothing has to be installed. MODE is "local" or "server" and is set
by build_exes.ps1 (it writes _mode.py next to this file before building).
"""
import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from ctypes import wintypes
from tkinter import messagebox

try:
    from _mode import MODE
except ImportError:
    MODE = "local"

APP = "Complete GST Suite"
NAVY, BG, SLATE, GREEN, RED = "#1F3864", "#F6F8FB", "#475569", "#15803D", "#B91C1C"
BASE_PORT = int(os.environ.get("PORT", "8080"))
HOST = "0.0.0.0" if MODE == "server" else "127.0.0.1"
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CompleteGSTSuite")


def res(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


# ---------------------------------------------------------------- job object
# Ensures node.exe is killed if this launcher closes or crashes.
def make_kill_on_close_job():
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                        ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class EXTENDED(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32.CreateJobObjectW.restype = wintypes.HANDLE
        job = k32.CreateJobObjectW(None, None)
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
        return k32, job
    except Exception:
        return None, None


def assign_to_job(k32, job, proc):
    if not job:
        return
    try:
        k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(proc._handle)))
    except Exception:
        pass


# ---------------------------------------------------------------- helpers
def is_gst_suite(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1.5) as r:
            return b"GST" in r.read(200000)
    except Exception:
        return False


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((HOST, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def lan_addresses():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127.") and not ip.startswith("169.254."))


# ---------------------------------------------------------------- window
class Launcher:
    def __init__(self):
        self.proc = None
        self.port = None
        self.k32, self.job = make_kill_on_close_job()
        self.root = tk.Tk()
        self.root.title(APP + (" - Office Server" if MODE == "server" else ""))
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        try:
            self.root.iconbitmap(res("app.ico"))
        except Exception:
            pass
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.build_ui()
        self.root.after(100, self.start)

    def build_ui(self):
        head = tk.Frame(self.root, bg=NAVY, padx=22, pady=16)
        head.pack(fill="x")
        tk.Label(head, text=APP, bg=NAVY, fg="white", font=("Segoe UI Semibold", 16)).pack(anchor="w")
        sub = ("Office server - other computers on your network can open it"
               if MODE == "server" else "Running on this computer only")
        tk.Label(head, text=sub, bg=NAVY, fg="#C7D2E5", font=("Segoe UI", 10)).pack(anchor="w")

        body = tk.Frame(self.root, bg=BG, padx=22, pady=16)
        body.pack(fill="both")
        self.status = tk.Label(body, text="Starting...", bg=BG, fg=SLATE, font=("Segoe UI Semibold", 11))
        self.status.pack(anchor="w")
        self.links = tk.Frame(body, bg=BG)
        self.links.pack(anchor="w", fill="x", pady=(8, 4))
        self.note = tk.Label(body, bg=BG, fg=SLATE, font=("Segoe UI", 9), justify="left", wraplength=430,
                             text="Keep this window open while you use the app. Closing it stops the suite.")
        self.note.pack(anchor="w", pady=(6, 0))

        bar = tk.Frame(self.root, bg=BG, padx=22, pady=(0))
        bar.pack(fill="x", pady=(0, 18))
        self.open_btn = tk.Button(bar, text="Open in browser", command=self.open_browser, state="disabled",
                                  bg=NAVY, fg="white", activebackground="#2B4A80", activeforeground="white",
                                  relief="flat", font=("Segoe UI Semibold", 10), padx=16, pady=6, cursor="hand2")
        self.open_btn.pack(side="left")
        tk.Button(bar, text="Stop and exit", command=self.quit, bg="white", fg=NAVY, relief="solid", bd=1,
                  font=("Segoe UI", 10), padx=16, pady=5, cursor="hand2").pack(side="left", padx=10)
        self.root.minsize(480, 0)

    def link(self, url):
        lbl = tk.Label(self.links, text=url, bg=BG, fg="#1D4ED8", cursor="hand2",
                       font=("Segoe UI", 11, "underline"))
        lbl.pack(anchor="w")
        lbl.bind("<Button-1>", lambda _e: webbrowser.open(url))

    def set_status(self, text, color=SLATE):
        self.status.config(text=text, fg=color)

    # ------------------------------------------------------------ server
    def start(self):
        # Already running (e.g. exe opened twice)? Just open the browser.
        if MODE == "local" and is_gst_suite(BASE_PORT):
            webbrowser.open(f"http://localhost:{BASE_PORT}")
            messagebox.showinfo(APP, f"{APP} is already running.\nIt has been opened in your browser.")
            self.root.destroy()
            return
        port = next((p for p in range(BASE_PORT, BASE_PORT + 20) if port_free(p)), None)
        if port is None:
            self.set_status("No free port found (8080-8099 are in use).", RED)
            return
        self.port = port
        node, entry = res("node", "node.exe"), res("app", "server", "index.mjs")
        if not (os.path.isfile(node) and os.path.isfile(entry)):
            self.set_status("The app files are missing from this exe. Please rebuild it.", RED)
            return
        os.makedirs(LOG_DIR, exist_ok=True)
        log = open(os.path.join(LOG_DIR, f"web-{MODE}.log"), "w", encoding="utf-8", errors="replace")
        env = dict(os.environ, NITRO_HOST=HOST, NITRO_PORT=str(port), HOST=HOST, PORT=str(port),
                   NODE_ENV="production")
        self.proc = subprocess.Popen([node, entry], cwd=res("app"), env=env, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=0x08000000)  # CREATE_NO_WINDOW
        assign_to_job(self.k32, self.job, self.proc)
        threading.Thread(target=self.wait_ready, daemon=True).start()

    def wait_ready(self):
        for _ in range(120):
            if self.proc.poll() is not None:
                self.root.after(0, lambda: self.set_status(
                    f"The suite stopped unexpectedly. Details: {os.path.join(LOG_DIR, f'web-{MODE}.log')}", RED))
                return
            if is_gst_suite(self.port):
                self.root.after(0, self.ready)
                return
            time.sleep(0.25)
        self.root.after(0, lambda: self.set_status("The suite is taking too long to start.", RED))

    def ready(self):
        self.set_status("Running", GREEN)
        self.link(f"http://localhost:{self.port}")
        if MODE == "server":
            tk.Label(self.links, text="Other computers in the office open:", bg=BG, fg=SLATE,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 0))
            ips = lan_addresses()
            for ip in ips:
                self.link(f"http://{ip}:{self.port}")
            if not ips:
                tk.Label(self.links, text="(no network connection found)", bg=BG, fg=RED).pack(anchor="w")
            self.note.config(text="If Windows Firewall asks, click \"Allow access\" for private networks.\n"
                                  "Keep this window open while people use the app. Closing it stops the suite.\n"
                                  "Each person's clients and runs are saved in their own browser.")
        elif self.port != BASE_PORT:
            self.note.config(text=f"Port {BASE_PORT} was busy, so port {self.port} is used. Data saved under "
                                  f"port {BASE_PORT} will show again next time that port is free.\n"
                                  "Keep this window open while you use the app.")
        self.open_btn.config(state="normal")
        self.open_browser()

    def open_browser(self):
        if self.port:
            webbrowser.open(f"http://localhost:{self.port}")

    def quit(self):
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "stop requested from window")
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except Exception:
                self.proc.kill()
        self.root.destroy()


if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    if sys.stderr is None or getattr(sys, "frozen", False):
        # windowed exe has no console: send errors to a file instead of crashing on print
        sys.stderr = sys.stdout = open(os.path.join(LOG_DIR, f"launcher-{MODE}.log"), "a",
                                      encoding="utf-8", errors="replace", buffering=1)
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "launcher start")
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    Launcher().root.mainloop()
