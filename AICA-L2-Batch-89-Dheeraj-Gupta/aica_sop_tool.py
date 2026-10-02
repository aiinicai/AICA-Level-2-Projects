"""
AICA SOP TOOL - Launcher v4
============================

A single entry point for the SOP generation pipeline.

Design
------
This launcher is an ORCHESTRATOR, not a merged application. Each stage
remains its own script and is started as a separate process. That keeps
every module independently testable, avoids multiple Tkinter roots
competing in one process, and prevents COM threading conflicts between
the capture agents and Word automation.

Change in v4
------------
Stage 6 now runs sop_builder_v14.py, which removes three kinds of
statement the capture cannot support:

    - sentences whose only content is that a detail needs validation
    - claims about visible cell references, which are usually data values
    - claims about displayed worksheet tabs, which frequently disagree
      with the screenshot beneath them

Retained from v3
----------------
    - stage 1 runs activity_recorder_v3.py, which resolves Explorer
      folder paths
    - folder path readiness is reported for the selected session
    - packages are checked in the interpreter that will run the stages,
      which is what makes the check correct when packaged
    - Graphviz and Tesseract are located on the PATH or in their usual
      install folders
    - each stage is enabled only once its inputs exist

Pipeline
--------
    1  Activity Recorder        activity_recorder_v3.py
    2  Interaction Capture      interaction_capture_v5.py
    3  Process Analyzer         process_analyzer_v7.py
    4  Vision Extractor         vision_extractor_v1.py
    5  Flowchart Builder        flowchart_builder_v2.py
    6  SOP Builder              sop_builder_v14.py

Run
---
    python aica_sop_tool.py

Package
-------
    pyinstaller --onefile --noconsole --clean --name AICA_SOP_Tool aica_sop_tool.py
"""

import csv
import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

APP_TITLE = "AICA SOP Tool"
VERSION = "4.0"

BRAND = "#6B001B"
BRAND_DARK = "#4A0013"
SUCCESS = "#1F7A1F"
WARN = "#9A6700"
ERROR = "#C00000"
INK = "#202020"
MUTED = "#6B6B6B"
PANEL = "#F7F3F4"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ---------------------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------------------

STAGES = [
    {
        "key": "record",
        "number": "1",
        "title": "Start Activity Recorder",
        "script": "activity_recorder_v3.py",
        "detail": "Captures the active application, window title, duration "
                  "and Explorer folder paths. Run the folder path self-test "
                  "before recording.",
        "needs": [],
    },
    {
        "key": "interact",
        "number": "2",
        "title": "Start Interaction Capture",
        "script": "interaction_capture_v5.py",
        "detail": "Captures approved shortcuts and one screenshot per event. "
                  "Run its folder path self-test as well.",
        "needs": [],
    },
    {
        "key": "analyze",
        "number": "3",
        "title": "Analyze Logs",
        "script": "process_analyzer_v7.py",
        "detail": "Merges both logs into process_steps.csv, ai_prompt.txt and "
                  "the first flowchart.",
        "needs": ["activity_log"],
    },
    {
        "key": "vision",
        "number": "4",
        "title": "Extract Screen Text",
        "script": "vision_extractor_v1.py",
        "detail": "Reads file names, folder paths and ribbon commands from "
                  "the captured screens. Untick the prompt-append option.",
        "needs": ["process_steps"],
    },
    {
        "key": "rebuild",
        "number": "5",
        "title": "Rebuild Flowchart",
        "script": "flowchart_builder_v2.py",
        "detail": "Redraws the flow in columns so it fits one readable page.",
        "needs": ["process_steps"],
    },
    {
        "key": "build",
        "number": "6",
        "title": "Build SOP Document",
        "script": "sop_builder_v14.py",
        "detail": "Produces the final Word and PDF document and removes "
                  "statements the capture cannot support.",
        "needs": ["process_steps", "sop_text"],
    },
]

# (import name, pip name, purpose)
REQUIRED_PACKAGES = [
    ("keyboard", "keyboard", "Shortcut capture"),
    ("pynput", "pynput", "Mouse capture"),
    ("PIL", "pillow", "Screenshots and images"),
    ("psutil", "psutil", "Application detection"),
    ("pygetwindow", "pygetwindow", "Active window detection"),
    ("win32com", "pywin32", "Folder paths and PDF export"),
    ("graphviz", "graphviz", "Flowchart generation"),
    ("docx", "python-docx", "Word document creation"),
    ("pytesseract", "pytesseract", "Optical character recognition"),
]

TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
)

GRAPHVIZ_CANDIDATES = (
    r"C:\Program Files\Graphviz\bin\dot.exe",
    r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
)


# ---------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def python_command():
    """
    Locate the interpreter that will actually run the module scripts.

    When the launcher is packaged, sys.executable points at the launcher
    itself, so a system Python must be found instead.
    """
    if not is_frozen():
        return sys.executable

    for candidate in ("python", "python3", "py"):
        found = shutil.which(candidate)
        if found:
            return found

    local = os.path.expanduser(r"~\AppData\Local\Programs\Python")
    if os.path.isdir(local):
        for name in sorted(os.listdir(local), reverse=True):
            candidate = os.path.join(local, name, "python.exe")
            if os.path.exists(candidate):
                return candidate
    return ""


PROBE = (
    "import importlib,json,sys\n"
    "names=json.loads(sys.argv[1])\n"
    "out={}\n"
    "for n in names:\n"
    "    try:\n"
    "        importlib.import_module(n)\n"
    "        out[n]=True\n"
    "    except Exception:\n"
    "        out[n]=False\n"
    "print(json.dumps(out))\n"
)


def check_packages():
    """Probe the interpreter that will run the stages, not this process."""
    interpreter = python_command()

    if not interpreter:
        return [], [(p, d) for _, p, d in REQUIRED_PACKAGES], (
            "No system Python interpreter was found on the PATH.")

    names = [module for module, _, _ in REQUIRED_PACKAGES]

    try:
        completed = subprocess.run(
            [interpreter, "-c", PROBE, json.dumps(names)],
            capture_output=True, text=True, timeout=30,
            creationflags=CREATE_NO_WINDOW,
        )
        result = json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception as error:
        return [], [(p, d) for _, p, d in REQUIRED_PACKAGES], (
            "Could not query {}: {}".format(interpreter, error))

    available, missing = [], []
    for module, package, purpose in REQUIRED_PACKAGES:
        if result.get(module):
            available.append((package, purpose))
        else:
            missing.append((package, purpose))

    return available, missing, "Checked against {}".format(interpreter)


def locate_tool(command, candidates):
    found = shutil.which(command)
    if found:
        return found, "PATH"
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate, "installed"
    return "", ""


def check_tools():
    graphviz_path, graphviz_where = locate_tool("dot", GRAPHVIZ_CANDIDATES)
    tesseract_path, tesseract_where = locate_tool(
        "tesseract", TESSERACT_CANDIDATES)
    return [
        ("Graphviz", bool(graphviz_path), graphviz_path, graphviz_where,
         "Required to draw the process flow"),
        ("Tesseract OCR", bool(tesseract_path), tesseract_path,
         tesseract_where, "Required to read text from screenshots"),
    ]


def find_scripts():
    base = app_dir()
    found = {}
    for stage in STAGES:
        path = os.path.join(base, stage["script"])
        found[stage["key"]] = path if os.path.exists(path) else ""
    return found


# ---------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------

def sessions_root():
    return os.path.join(app_dir(), "sessions")


def list_sessions():
    root = sessions_root()
    if not os.path.isdir(root):
        return []
    entries = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if not name.upper().startswith("SESSION"):
            continue
        try:
            stamp = os.path.getmtime(path)
        except Exception:
            stamp = 0
        entries.append((stamp, path))
    entries.sort(reverse=True)
    return [path for _, path in entries]


def activity_has_paths(session):
    """Report whether the activity log carries a FolderPath column."""
    path = os.path.join(session, "activity_log.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            fields = set(csv.DictReader(handle).fieldnames or [])
        return "FolderPath" in fields
    except Exception:
        return None


def count_step_paths(session):
    """Count distinct folder paths carried in process_steps.csv."""
    path = os.path.join(session, "process_steps.csv")
    if not os.path.exists(path):
        return None
    try:
        values = set()
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                value = (row.get("FolderPath") or "").strip()
                if value:
                    values.add(value)
        return len(values)
    except Exception:
        return None


def inspect(session):
    if not session or not os.path.isdir(session):
        return {
            "activity_log": False, "process_steps": False,
            "ai_prompt": False, "ocr_context": False,
            "sop_text": False, "flowchart": False,
            "screenshots": 0, "documents": 0,
        }

    shots = 0
    shot_dir = os.path.join(session, "screenshots")
    if os.path.isdir(shot_dir):
        shots = len([f for f in os.listdir(shot_dir)
                     if f.lower().endswith((".png", ".jpg", ".jpeg"))])

    documents = len([f for f in os.listdir(session)
                     if f.lower().startswith("sop_")
                     and f.lower().endswith((".docx", ".pdf"))])

    def has(name):
        return os.path.exists(os.path.join(session, name))

    return {
        "activity_log": has("activity_log.csv"),
        "process_steps": has("process_steps.csv"),
        "ai_prompt": has("ai_prompt.txt"),
        "ocr_context": has("ocr_context.csv"),
        "sop_text": has("sop_text.txt"),
        "flowchart": has("process_flow.png"),
        "screenshots": shots,
        "documents": documents,
    }


# ---------------------------------------------------------------------
# Launcher window
# ---------------------------------------------------------------------

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


class Launcher:

    def __init__(self, root):
        self.root = root
        self.session = ""
        self.scripts = find_scripts()
        self.buttons = {}

        self.packages_available = []
        self.packages_missing = []
        self.packages_note = ""
        self.tools = []

        root.title("{} v{}".format(APP_TITLE, VERSION))
        root.geometry("880x830")
        root.minsize(860, 400)
        root.configure(bg="white")
        # Scrollable body. Widgets are placed here so content
        # below the fold can be reached by scrolling.
        self._body = attach_scroll(root)


        self.build_header()
        self.build_footer()
        self.build_environment()
        self.build_session()
        self.build_stages()

        self.autoselect()
        threading.Thread(target=self.scan_environment, daemon=True).start()

    # -----------------------------------------------------------------
    def build_header(self):
        header = tk.Frame(self._body, bg=BRAND, height=76)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=APP_TITLE.upper(),
                 font=("Segoe UI", 19, "bold"),
                 bg=BRAND, fg="white").pack(pady=(14, 0))
        tk.Label(header,
                 text="Automated Standard Operating Procedure generation",
                 font=("Segoe UI", 9), bg=BRAND, fg="#E8D5DA").pack()

    # -----------------------------------------------------------------
    def build_footer(self):
        """Anchored before the stage list so it cannot be displaced."""
        footer = tk.Frame(self._body, bg="white")
        footer.pack(side="bottom", fill="x", padx=18, pady=(4, 10))
        self.status = tk.Label(footer, text="Ready.", bg="white", fg=MUTED,
                               font=("Segoe UI", 9), anchor="w",
                               wraplength=680, justify="left")
        self.status.pack(side="left")
        tk.Button(footer, text="Refresh", command=self.refresh,
                  bg=PANEL, fg=INK, relief="flat", width=10,
                  font=("Segoe UI", 9), cursor="hand2").pack(side="right")

    # -----------------------------------------------------------------
    def build_environment(self):
        frame = tk.LabelFrame(self._body, text=" Environment ", bg="white",
                              fg=BRAND, font=("Segoe UI", 9, "bold"))
        frame.pack(fill="x", padx=18, pady=(12, 6))

        row = tk.Frame(frame, bg="white")
        row.pack(fill="x", padx=12, pady=(8, 2))

        self.package_label = tk.Label(
            row, text="Python packages: checking...", bg="white",
            fg=MUTED, font=("Segoe UI", 9))
        self.package_label.pack(side="left")

        self.tool_label = tk.Label(row, text="", bg="white",
                                   fg=MUTED, font=("Segoe UI", 9))
        self.tool_label.pack(side="left")

        note_row = tk.Frame(frame, bg="white")
        note_row.pack(fill="x", padx=12, pady=(0, 4))
        self.env_note = tk.Label(note_row, text="", bg="white", fg=MUTED,
                                 font=("Segoe UI", 8), anchor="w",
                                 wraplength=700, justify="left")
        self.env_note.pack(side="left")

        script_row = tk.Frame(frame, bg="white")
        script_row.pack(fill="x", padx=12, pady=(0, 8))
        missing_scripts = [s["script"] for s in STAGES
                           if not self.scripts.get(s["key"])]
        if missing_scripts:
            tk.Label(script_row,
                     text="Missing module files: " + ", ".join(missing_scripts),
                     bg="white", fg=ERROR, font=("Segoe UI", 9),
                     wraplength=620, justify="left").pack(side="left")
        else:
            tk.Label(script_row,
                     text="All six module files found beside the launcher.",
                     bg="white", fg=SUCCESS,
                     font=("Segoe UI", 9)).pack(side="left")

        tk.Button(script_row, text="Details", command=self.show_environment,
                  bg=PANEL, fg=INK, relief="flat",
                  font=("Segoe UI", 8), cursor="hand2").pack(side="right")
        tk.Button(script_row, text="Re-check",
                  command=lambda: threading.Thread(
                      target=self.scan_environment, daemon=True).start(),
                  bg=PANEL, fg=INK, relief="flat",
                  font=("Segoe UI", 8),
                  cursor="hand2").pack(side="right", padx=6)

    # -----------------------------------------------------------------
    def build_session(self):
        frame = tk.LabelFrame(self._body, text=" Capture session ", bg="white",
                              fg=BRAND, font=("Segoe UI", 9, "bold"))
        frame.pack(fill="x", padx=18, pady=6)

        row = tk.Frame(frame, bg="white")
        row.pack(fill="x", padx=12, pady=(8, 4))

        tk.Button(row, text="SELECT SESSION", command=self.choose,
                  bg=BRAND, fg="white", relief="flat", width=16,
                  font=("Segoe UI", 9, "bold"),
                  cursor="hand2").pack(side="left")
        tk.Button(row, text="Use newest", command=self.autoselect,
                  bg=PANEL, fg=INK, relief="flat", width=12,
                  font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left", padx=6)
        tk.Button(row, text="Open folder", command=self.open_session,
                  bg=PANEL, fg=INK, relief="flat", width=12,
                  font=("Segoe UI", 9), cursor="hand2").pack(side="left")

        self.session_label = tk.Label(row, text="No session selected",
                                      bg="white", fg=MUTED,
                                      font=("Segoe UI", 9), anchor="w")
        self.session_label.pack(side="left", padx=12)

        self.artefact_label = tk.Label(frame, text="", bg="white", fg=MUTED,
                                       font=("Segoe UI", 9), anchor="w",
                                       wraplength=820, justify="left")
        self.artefact_label.pack(fill="x", padx=12, pady=(0, 2))

        self.path_label = tk.Label(frame, text="", bg="white", fg=MUTED,
                                   font=("Segoe UI", 9, "bold"), anchor="w",
                                   wraplength=820, justify="left")
        self.path_label.pack(fill="x", padx=12, pady=(0, 8))

    # -----------------------------------------------------------------
    def build_stages(self):
        frame = tk.LabelFrame(self._body, text=" Pipeline ", bg="white",
                              fg=BRAND, font=("Segoe UI", 9, "bold"))
        frame.pack(fill="both", expand=True, padx=18, pady=6)
        for stage in STAGES:
            self.add_stage(frame, stage)
            if stage["key"] == "rebuild":
                self.add_handoff(frame)

    def add_stage(self, parent, stage):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=12, pady=3)

        tk.Label(row, text=stage["number"], width=2,
                 font=("Segoe UI", 12, "bold"),
                 bg="white", fg=BRAND).pack(side="left")

        button = tk.Button(
            row, text=stage["title"],
            command=lambda s=stage: self.run(s),
            bg=BRAND, fg="white", relief="flat", width=26,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
            anchor="w", padx=10)
        button.pack(side="left", padx=(4, 10))
        self.buttons[stage["key"]] = button

        tk.Label(row, text=stage["detail"], bg="white", fg=MUTED,
                 font=("Segoe UI", 8), anchor="w", justify="left",
                 wraplength=520).pack(side="left", fill="x", expand=True)

    def add_handoff(self, parent):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=12, pady=6)
        inner = tk.Frame(row, bg=PANEL)
        inner.pack(fill="x", padx=10, pady=8)

        tk.Label(inner, text="!", width=2, font=("Segoe UI", 12, "bold"),
                 bg=PANEL, fg=WARN).pack(side="left")
        tk.Button(inner, text="Open ai_prompt.txt",
                  command=self.open_prompt,
                  bg=BRAND_DARK, fg="white", relief="flat", width=26,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  anchor="w", padx=10).pack(side="left", padx=(4, 10))
        tk.Label(inner,
                 text="Manual step: copy the prompt into ChatGPT, then save "
                      "the reply as sop_text.txt in the session folder "
                      "(All Files, UTF-8).",
                 bg=PANEL, fg=INK, font=("Segoe UI", 8),
                 anchor="w", justify="left",
                 wraplength=520).pack(side="left", fill="x", expand=True)

    # -----------------------------------------------------------------
    # Environment scanning
    # -----------------------------------------------------------------

    def scan_environment(self):
        available, missing, note = check_packages()
        tools = check_tools()
        self.root.after(0, self.apply_environment,
                        available, missing, note, tools)

    def apply_environment(self, available, missing, note, tools):
        self.packages_available = available
        self.packages_missing = missing
        self.packages_note = note
        self.tools = tools

        if missing:
            self.package_label.config(
                text="Python packages: {} missing".format(len(missing)),
                fg=ERROR)
        else:
            self.package_label.config(
                text="Python packages: all {} present".format(len(available)),
                fg=SUCCESS)

        parts = []
        for name, present, path, where, _ in tools:
            parts.append("{}: {}".format(
                name, "found" if present else "not found"))
        self.tool_label.config(
            text="   |   " + "   |   ".join(parts),
            fg=SUCCESS if all(t[1] for t in tools) else WARN)

        interpreter = python_command()
        if is_frozen():
            detail = ("Running as an executable. Stages are started with "
                      "{}, so packages are checked there.".format(
                          interpreter or "no interpreter found"))
        else:
            detail = "Running from source with {}.".format(interpreter)
        self.env_note.config(text=detail)

    # -----------------------------------------------------------------
    def show_environment(self):
        lines = []

        lines.append("Interpreter used to run the stages")
        lines.append("-" * 52)
        lines.append("  " + (python_command() or "NOT FOUND"))
        lines.append("  launcher mode: {}".format(
            "packaged executable" if is_frozen() else "source"))
        if self.packages_note:
            lines.append("  " + self.packages_note)

        lines.extend(["", "Python packages", "-" * 52])
        for package, purpose in self.packages_available:
            lines.append("  present   {:<16} {}".format(package, purpose))
        for package, purpose in self.packages_missing:
            lines.append("  MISSING   {:<16} {}".format(package, purpose))

        lines.extend(["", "External programs", "-" * 52])
        for name, present, path, where, purpose in self.tools:
            if present:
                lines.append("  found     {:<16} {}".format(name, path))
            else:
                lines.append("  MISSING   {:<16} {}".format(name, purpose))

        lines.extend(["", "Module files", "-" * 52])
        for stage in STAGES:
            path = self.scripts.get(stage["key"])
            lines.append("  {}   {}".format(
                "found  " if path else "MISSING", stage["script"]))

        if self.packages_missing:
            lines.extend(["", "Install the missing packages with:",
                          "  python -m pip install "
                          + " ".join(p for p, _ in self.packages_missing)])

        if not all(t[1] for t in self.tools):
            lines.append("")
            for name, present, _, _, _ in self.tools:
                if present:
                    continue
                if name.startswith("Graphviz"):
                    lines.append("Install Graphviz from "
                                 "https://graphviz.org/download/")
                else:
                    lines.append("Install Tesseract from https://github.com/"
                                 "UB-Mannheim/tesseract/wiki")

        messagebox.showinfo(APP_TITLE, "\n".join(lines), parent=self.root)

    # -----------------------------------------------------------------
    # Session actions
    # -----------------------------------------------------------------

    def choose(self):
        root = sessions_root()
        start = root if os.path.isdir(root) else app_dir()
        path = filedialog.askdirectory(title="Select a capture session",
                                       initialdir=start)
        if path:
            self.session = path
            self.refresh()

    def autoselect(self):
        sessions = list_sessions()
        if sessions:
            self.session = sessions[0]
            self.status.config(
                text="Selected the newest session automatically.", fg=MUTED)
        else:
            self.session = ""
            self.status.config(
                text="No capture session found yet. Start with stage 1.",
                fg=MUTED)
        self.refresh()

    def open_session(self):
        if not self.session:
            messagebox.showwarning(APP_TITLE, "No session is selected.",
                                   parent=self.root)
            return
        try:
            os.startfile(self.session)
        except Exception:
            messagebox.showinfo(APP_TITLE, self.session, parent=self.root)

    def open_prompt(self):
        if not self.session:
            messagebox.showwarning(APP_TITLE, "Select a session first.",
                                   parent=self.root)
            return
        path = os.path.join(self.session, "ai_prompt.txt")
        if not os.path.exists(path):
            messagebox.showwarning(
                APP_TITLE,
                "ai_prompt.txt does not exist yet.\n\n"
                "Run stage 3, and stage 4 if you want screen evidence "
                "included.", parent=self.root)
            return
        try:
            os.startfile(path)
            self.status.config(
                text="Opened ai_prompt.txt. Copy it into ChatGPT, then save "
                     "the reply as sop_text.txt in the session folder.",
                fg=INK)
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error), parent=self.root)

    # -----------------------------------------------------------------
    def run(self, stage):
        script = self.scripts.get(stage["key"])
        if not script:
            messagebox.showerror(
                APP_TITLE,
                "{} was not found beside the launcher.\n\n"
                "Place all six module files in the same folder as this "
                "launcher.".format(stage["script"]), parent=self.root)
            return

        interpreter = python_command()
        if not interpreter:
            messagebox.showerror(
                APP_TITLE,
                "A Python interpreter could not be located.\n\n"
                "Install Python and tick 'Add Python to PATH' during "
                "installation, then press Re-check.", parent=self.root)
            return

        try:
            subprocess.Popen([interpreter, script], cwd=app_dir())
            self.status.config(
                text="Started {}. Complete it, then return here and press "
                     "Refresh.".format(stage["script"]), fg=SUCCESS)
        except Exception as error:
            messagebox.showerror(
                APP_TITLE,
                "Could not start {}.\n\n{}".format(stage["script"], error),
                parent=self.root)

    # -----------------------------------------------------------------
    def refresh(self):
        state = inspect(self.session)

        if self.session:
            self.session_label.config(
                text=os.path.basename(self.session), fg=INK)
            parts = [
                "activity log: " + ("yes" if state["activity_log"] else "no"),
                "steps: " + ("yes" if state["process_steps"] else "no"),
                "prompt: " + ("yes" if state["ai_prompt"] else "no"),
                "OCR: " + ("yes" if state["ocr_context"] else "no"),
                "narrative: " + ("yes" if state["sop_text"] else "no"),
                "flowchart: " + ("yes" if state["flowchart"] else "no"),
                "screens: {}".format(state["screenshots"]),
                "documents: {}".format(state["documents"]),
            ]
            self.artefact_label.config(text="   |   ".join(parts))
            self.report_paths()
        else:
            self.session_label.config(text="No session selected", fg=MUTED)
            self.artefact_label.config(text="")
            self.path_label.config(text="")

        for stage in STAGES:
            button = self.buttons[stage["key"]]
            script_present = bool(self.scripts.get(stage["key"]))
            inputs_ready = all(state.get(need) for need in stage["needs"])
            if script_present and inputs_ready:
                button.config(state="normal", bg=BRAND)
            else:
                button.config(state="disabled", bg="#B9A5AB")

    # -----------------------------------------------------------------
    def report_paths(self):
        """
        Report folder path readiness.

        A session recorded with the older recorder has no FolderPath column,
        which is the reason Explorer navigation produced no paths.
        """
        has_column = activity_has_paths(self.session)
        step_paths = count_step_paths(self.session)

        if has_column is None:
            self.path_label.config(
                text="Folder paths: no activity log in this session yet.",
                fg=MUTED)
            return

        if not has_column:
            self.path_label.config(
                text="Folder paths: this session was recorded without a "
                     "FolderPath column. Re-record with "
                     "activity_recorder_v3.py to capture Explorer "
                     "navigation paths.",
                fg=WARN)
            return

        if step_paths is None:
            self.path_label.config(
                text="Folder paths: the activity log supports them. Run "
                     "stage 3 to carry them into the process steps.",
                fg=SUCCESS)
            return

        if step_paths == 0:
            self.path_label.config(
                text="Folder paths: supported, but none were resolved. "
                     "Confirm the recorder's folder path self-test passes "
                     "and that File Explorer was used during the recording.",
                fg=WARN)
            return

        self.path_label.config(
            text="Folder paths: {} distinct path(s) carried into the "
                 "process steps.".format(step_paths),
            fg=SUCCESS)


def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
