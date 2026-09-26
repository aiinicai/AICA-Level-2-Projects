"""
AICA SOP TOOL - Vision Extractor v1
====================================

Computer Vision module for the AICA SOP Tool pipeline.

Purpose
-------
Every captured screenshot contains business detail that the Windows APIs
cannot see: workbook file names, worksheet tab names, selected cell
references, dialog titles, toolbar labels and ribbon commands. Without
reading the image, the AI has to mark these as "Business validation
required".

This module applies Optical Character Recognition to each screenshot,
extracts the meaningful on-screen text, and writes a context file that the
AI prompt can use. The result is a materially more specific SOP.

Pipeline position
-----------------
    activity_recorder_phase2   ->  activity_log.csv
    interaction_capture_v4     ->  interaction_log.csv + screenshots
    process_analyzer_v6        ->  process_steps.csv
    vision_extractor_v1        ->  ocr_context.csv          <-- this module
                                   ocr_context.txt
    ChatGPT                    ->  sop_text.txt
    sop_builder_v10            ->  SOP.docx / SOP.pdf

What it extracts
----------------
    File names          Revenue_Report.xlsx, Opening.xlsx
    Worksheet tabs      Sheet1, Summary, Working
    Cell references     A1, B12, A1:D45
    Dialog titles       Save As, Open, Print
    Ribbon commands     Refresh All, PivotTable, Save
    Window captions     visible application headings

What it deliberately ignores
----------------------------
    Body text, email content, numeric cell values, personal names,
    anything under three characters, and repeated interface noise.

Privacy note
------------
OCR reads whatever is visible in the screenshot. Review the generated
ocr_context.csv before pasting anything into an external AI tool, and
delete rows containing confidential values. The Review tab in the window
is provided for exactly this purpose.

Requirements
------------
    python -m pip install pytesseract pillow

Tesseract OCR engine must also be installed separately on Windows:
    https://github.com/UB-Mannheim/tesseract/wiki
Default install location:
    C:\\Program Files\\Tesseract-OCR\\tesseract.exe

Run
---
    python vision_extractor_v1.py

Build EXE
---------
    pyinstaller --onefile --noconsole --clean --name AICA_Vision_v1 vision_extractor_v1.py
"""

import csv
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps

try:
    import pytesseract
    HAVE_PYTESSERACT = True
except Exception:
    pytesseract = None
    HAVE_PYTESSERACT = False


APP_TITLE = "AICA SOP Tool - Vision Extractor v1"
TOOL_NAME = "AICA SOP Tool"
BRAND = "#6B001B"
SUCCESS = "#1F7A1F"
WARN = "#9A6700"
ERROR = "#C00000"

# Common Windows install locations for the Tesseract engine.
TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
)

# ---------------------------------------------------------------------
# Extraction patterns
# ---------------------------------------------------------------------

FILE_PATTERN = re.compile(
    r"\b[\w\-. ]{2,60}\.(xlsx|xlsm|xls|csv|docx|doc|pptx|ppt|pdf|txt|msg)\b",
    re.IGNORECASE,
)

CELL_PATTERN = re.compile(r"\b[A-Z]{1,3}\d{1,6}(?::[A-Z]{1,3}\d{1,6})?\b")

# OCR commonly misreads the digit 1 as lowercase l or capital I, and the
# digit 0 as capital O. This catches cell ranges that were distorted that way.
CELL_OCR_PATTERN = re.compile(
    r"\b[A-Za-z]{1,3}[0-9lIoO]{1,6}:[A-Za-z]{1,3}[0-9lIoO]{1,6}\b"
)

# Windows folder paths may contain spaces, so allow them but stop at
# punctuation that cannot appear in a path.
PATH_PATTERN = re.compile(r"\b[A-Za-z]:\\[^\r\n\"'<>|*?]{3,140}")

# Interface commands worth recording when they appear on screen.
COMMANDS = (
    "refresh all", "refresh", "save as", "save", "open", "print",
    "pivottable", "pivot table", "insert", "formulas", "data", "review",
    "home", "file", "page layout", "view", "sort", "filter", "find",
    "replace", "paste special", "paste", "copy", "cut", "undo", "redo",
    "get data", "from text", "from file", "close", "export", "publish",
    "send", "new email", "reply", "forward", "attach", "download",
    "upload", "sign in", "log in", "ok", "cancel", "apply", "next",
    "finish", "browse", "properties", "connections", "queries",
    "workbook connections", "name box", "autosum", "freeze panes",
)

# Words that appear on almost every screen and add no business value.
NOISE_TOKENS = {
    "file", "edit", "view", "help", "window", "tools", "search",
    "type here to search", "start", "taskbar", "notification",
    "minimize", "maximize", "restore", "close", "back", "forward",
    "refresh page", "address", "bookmarks", "tab", "new tab",
    "aica sop tool", "sop genius ai", "interaction capture",
}

# Worksheet-tab style names.
SHEET_PATTERN = re.compile(
    r"\b(sheet\s?\d+|summary|working|data|input|output|master|detail|"
    r"pivot|dashboard|report|raw|trial\s?balance|tb|gl|ledger|"
    r"revenue|cost|budget|actual|variance|jan|feb|mar|apr|may|jun|"
    r"jul|aug|sep|oct|nov|dec)\b",
    re.IGNORECASE,
)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def locate_tesseract():
    """Find the Tesseract engine and configure pytesseract."""
    if not HAVE_PYTESSERACT:
        return "", "The pytesseract package is not installed."

    # Already on PATH?
    try:
        version = str(pytesseract.get_tesseract_version())
        return "PATH", "Tesseract {} found on the system PATH.".format(version)
    except Exception:
        pass

    for candidate in TESSERACT_CANDIDATES:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            try:
                version = str(pytesseract.get_tesseract_version())
                return candidate, "Tesseract {} found.".format(version)
            except Exception:
                continue

    return "", ("Tesseract engine was not found. Install it from "
                "https://github.com/UB-Mannheim/tesseract/wiki")


# ---------------------------------------------------------------------
# Image preparation
# ---------------------------------------------------------------------

def prepare(image, upscale=True):
    """
    Improve OCR accuracy on screenshots.

    Screen text is small and anti-aliased. Converting to greyscale,
    increasing contrast and upscaling materially improves recognition.
    """
    work = image.convert("L")
    work = ImageOps.autocontrast(work)
    if upscale:
        width, height = work.size
        if width < 2600:
            factor = min(2.0, 2600.0 / float(width))
            work = work.resize(
                (int(width * factor), int(height * factor)),
                Image.LANCZOS,
            )
    return work


def read_text(path, upscale=True):
    """Return raw OCR text for one screenshot."""
    try:
        with Image.open(path) as image:
            prepared = prepare(image, upscale)
            return pytesseract.image_to_string(prepared, lang="eng")
    except Exception as error:
        return "__ERROR__" + str(error)


# ---------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------

def clean_token(value):
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" \t|:;,.-_\u2014\u2013")
    return value


def repair_cell_reference(token):
    """
    Repair a cell range distorted by OCR.

    Tesseract frequently reads the digit 1 as lowercase l or capital I, and
    the digit 0 as capital O. A1:D45 therefore arrives as Al:D45. The column
    letters are restored to upper case and the row characters are mapped back
    to digits.
    """
    parts = token.split(":")
    if len(parts) != 2:
        return ""

    rebuilt = []
    for part in parts:
        match = re.match(r"^([A-Za-z]{1,3})([0-9lIoO]{1,6})$", part)
        if not match:
            return ""
        column = match.group(1).upper()
        rows = match.group(2)
        rows = rows.replace("l", "1").replace("I", "1")
        rows = rows.replace("O", "0").replace("o", "0")
        if not rows.isdigit() or rows.startswith("0"):
            return ""
        rebuilt.append(column + rows)

    return ":".join(rebuilt)


def plausible(value):
    """Reject OCR garbage."""
    if len(value) < 3 or len(value) > 90:
        return False
    letters = sum(1 for ch in value if ch.isalnum())
    if letters < max(2, int(len(value) * 0.45)):
        return False
    if value.lower() in NOISE_TOKENS:
        return False
    return True


def extract(text):
    """Pull structured, business-relevant items out of raw OCR text."""
    found = {
        "files": [],
        "paths": [],
        "cells": [],
        "sheets": [],
        "commands": [],
        "headings": [],
    }

    if not text or text.startswith("__ERROR__"):
        return found

    lowered = text.lower()

    # --- file names ---
    for match in FILE_PATTERN.finditer(text):
        token = clean_token(match.group(0))
        if plausible(token) and token not in found["files"]:
            found["files"].append(token)

    # --- full paths ---
    for match in PATH_PATTERN.finditer(text):
        token = clean_token(match.group(0))
        # Trim a trailing word that is clearly a separate UI label.
        token = re.sub(r"\s{2,}.*$", "", token).strip()
        if len(token) > 6 and token not in found["paths"]:
            found["paths"].append(token)

    # --- cell references ---
    for match in CELL_PATTERN.finditer(text):
        token = match.group(0)
        # A single letter plus digits is ambiguous; keep ranges and
        # references that look deliberate.
        if ":" in token or len(token) >= 3:
            if token not in found["cells"]:
                found["cells"].append(token)

    # --- cell ranges distorted by OCR (Al:D45 -> A1:D45) ---
    for match in CELL_OCR_PATTERN.finditer(text):
        token = match.group(0)
        corrected = repair_cell_reference(token)
        if corrected and corrected not in found["cells"]:
            found["cells"].append(corrected)

    # --- worksheet tabs ---
    for match in SHEET_PATTERN.finditer(text):
        token = clean_token(match.group(0)).title()
        if token not in found["sheets"]:
            found["sheets"].append(token)

    # --- interface commands ---
    for command in COMMANDS:
        if command in lowered:
            pretty = command.title()
            if pretty not in found["commands"]:
                found["commands"].append(pretty)

    # --- candidate headings: short standalone lines ---
    for line in text.split("\n"):
        token = clean_token(line)
        if not plausible(token):
            continue
        if len(token) > 55:
            continue
        words = token.split()
        if len(words) > 7:
            continue
        # Skip lines already captured as a file or path.
        if any(token in item for item in found["files"] + found["paths"]):
            continue
        if token.lower() in NOISE_TOKENS:
            continue
        # Require at least one capitalised word to favour UI captions.
        if not any(word[:1].isupper() for word in words):
            continue
        if token not in found["headings"]:
            found["headings"].append(token)

    # Keep the lists short so the AI prompt stays focused.
    found["cells"] = found["cells"][:8]
    found["sheets"] = found["sheets"][:8]
    found["commands"] = found["commands"][:10]
    found["headings"] = found["headings"][:6]
    found["files"] = found["files"][:8]
    found["paths"] = found["paths"][:4]

    return found


def summarise(found):
    """Build a single readable context line for one screenshot."""
    parts = []
    if found["files"]:
        parts.append("Files: " + ", ".join(found["files"]))
    if found["paths"]:
        parts.append("Paths: " + ", ".join(found["paths"]))
    if found["sheets"]:
        parts.append("Sheets/Tabs: " + ", ".join(found["sheets"]))
    if found["cells"]:
        parts.append("Cell refs: " + ", ".join(found["cells"]))
    if found["commands"]:
        parts.append("Commands visible: " + ", ".join(found["commands"]))
    if found["headings"]:
        parts.append("On-screen labels: " + "; ".join(found["headings"]))
    return " | ".join(parts)


# ---------------------------------------------------------------------
# Session processing
# ---------------------------------------------------------------------

def read_steps(session):
    """Map screenshot filename -> list of step numbers and descriptions."""
    path = os.path.join(session, "process_steps.csv")
    mapping = {}
    order = []
    if not os.path.exists(path):
        return mapping, order

    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            shot = (row.get("Screenshot") or "").strip()
            if not shot:
                continue
            try:
                number = int(float(row.get("StepNo") or 0))
            except ValueError:
                continue
            description = (row.get("StepDescription") or "").strip()
            mapping.setdefault(shot, []).append((number, description))
            if shot not in order:
                order.append(shot)
    return mapping, order


def list_screenshots(session):
    folder = os.path.join(session, "screenshots")
    if not os.path.isdir(folder):
        return []
    names = [
        name for name in os.listdir(folder)
        if name.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    names.sort()
    return names


def process_session(session, upscale, progress=None, stop_flag=None):
    """OCR every screenshot and return per-image results."""
    mapping, ordered = read_steps(session)
    available = list_screenshots(session)

    # Prefer the order steps reference them; append any extras.
    targets = [name for name in ordered if name in available]
    targets += [name for name in available if name not in targets]

    folder = os.path.join(session, "screenshots")
    results = []

    for index, name in enumerate(targets, start=1):
        if stop_flag and stop_flag():
            break
        if progress:
            progress(index, len(targets), name)

        path = os.path.join(folder, name)
        raw = read_text(path, upscale)
        error = raw[9:] if raw.startswith("__ERROR__") else ""
        found = extract(raw)
        steps = mapping.get(name, [])

        results.append({
            "screenshot": name,
            "steps": steps,
            "found": found,
            "summary": summarise(found),
            "characters": 0 if error else len(raw.strip()),
            "error": error,
        })

    return results


# ---------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------

def write_csv(results, path):
    fields = [
        "Screenshot", "StepNumbers", "StepDescriptions",
        "FileNames", "FolderPaths", "WorksheetTabs", "CellReferences",
        "CommandsVisible", "OnScreenLabels", "OcrCharacters", "Error",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in results:
            found = item["found"]
            writer.writerow({
                "Screenshot": item["screenshot"],
                "StepNumbers": ", ".join(
                    str(number) for number, _ in item["steps"]),
                "StepDescriptions": " / ".join(
                    text for _, text in item["steps"]),
                "FileNames": ", ".join(found["files"]),
                "FolderPaths": ", ".join(found["paths"]),
                "WorksheetTabs": ", ".join(found["sheets"]),
                "CellReferences": ", ".join(found["cells"]),
                "CommandsVisible": ", ".join(found["commands"]),
                "OnScreenLabels": "; ".join(found["headings"]),
                "OcrCharacters": item["characters"],
                "Error": item["error"],
            })


def write_context(results, path):
    """
    Build the block that is appended to the AI prompt.

    It is organised by step number so the AI can tie visual evidence to the
    correct instruction.
    """
    by_step = []
    for item in results:
        if not item["summary"]:
            continue
        if item["steps"]:
            for number, description in item["steps"]:
                by_step.append((number, description, item["summary"]))
        else:
            by_step.append((9999, item["screenshot"], item["summary"]))
    by_step.sort(key=lambda row: row[0])

    lines = [
        "SCREEN EVIDENCE EXTRACTED BY OPTICAL CHARACTER RECOGNITION",
        "=" * 72,
        "",
        "The following detail was read directly from the captured screens.",
        "Use it to make the instructions specific. Where this evidence names",
        "a file, worksheet, cell range, folder or command, state it exactly",
        "and do not mark it as requiring validation.",
        "",
    ]

    for number, description, summary in by_step:
        label = ("Step {}".format(number) if number != 9999
                 else "Unmatched screen")
        lines.append("{} - {}".format(label, description))
        lines.append("    {}".format(summary))
        lines.append("")

    lines.append("=" * 72)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return len(by_step)


def merge_into_prompt(session, context_path):
    """Append the OCR block to ai_prompt.txt, replacing any earlier block."""
    prompt_path = os.path.join(session, "ai_prompt.txt")
    if not os.path.exists(prompt_path):
        return False, "ai_prompt.txt was not found in this session."

    try:
        with open(prompt_path, "r", encoding="utf-8") as handle:
            prompt = handle.read()
        with open(context_path, "r", encoding="utf-8") as handle:
            block = handle.read()
    except Exception as error:
        return False, str(error)

    marker = "SCREEN EVIDENCE EXTRACTED BY OPTICAL CHARACTER RECOGNITION"
    if marker in prompt:
        prompt = prompt.split(marker)[0].rstrip()
        prompt = prompt.rstrip("=").rstrip()

    merged = prompt.rstrip() + "\n\n" + block + "\n"

    try:
        with open(prompt_path, "w", encoding="utf-8") as handle:
            handle.write(merged)
    except Exception as error:
        return False, str(error)

    return True, "ai_prompt.txt updated with the screen evidence block."


# ---------------------------------------------------------------------
# GUI
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


class App:

    def __init__(self, root):
        self.root = root
        self.session = ""
        self.results = []
        self.worker = None
        self.cancelled = False

        root.title(APP_TITLE)
        root.geometry("1010x780")
        root.configure(bg="white")
        # Scrollable body. Widgets are placed here so content
        # below the fold can be reached by scrolling.
        self._body = attach_scroll(root)


        tk.Label(self._body, text=TOOL_NAME.upper(),
                 font=("Segoe UI", 20, "bold"),
                 bg="white", fg=BRAND).pack(pady=(12, 0))
        tk.Label(self._body, text="Vision Extractor | Computer Vision Module",
                 font=("Segoe UI", 9), bg="white", fg="gray").pack()

        # ---- engine status ----
        engine = tk.LabelFrame(self._body, text=" OCR engine ", bg="white",
                               fg=BRAND, font=("Segoe UI", 9, "bold"))
        engine.pack(fill="x", padx=22, pady=8)
        self.engine_label = tk.Label(
            engine, text="Checking...", bg="white", fg="gray",
            font=("Segoe UI", 9), anchor="w", wraplength=940,
            justify="left")
        self.engine_label.pack(fill="x", padx=12, pady=8)

        self.tesseract_path, message = locate_tesseract()
        if self.tesseract_path:
            self.engine_label.config(text=message, fg=SUCCESS)
            self.ready = True
        else:
            self.engine_label.config(text=message, fg=ERROR)
            self.ready = False

        # ---- session ----
        top = tk.Frame(self._body, bg="white")
        top.pack(fill="x", padx=22, pady=6)
        tk.Button(top, text="SELECT SESSION FOLDER", command=self.select,
                  bg=BRAND, fg="white", relief="flat", width=24,
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        self.folder_label = tk.Label(top, text="No folder selected",
                                     bg="white", fg="gray")
        self.folder_label.pack(side="left", padx=12)

        # ---- options ----
        opts = tk.Frame(self._body, bg="white")
        opts.pack(fill="x", padx=22, pady=4)
        self.upscale_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts,
                       text="Enhance images before reading (slower, more accurate)",
                       variable=self.upscale_var, bg="white",
                       activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left")
        self.merge_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="Append evidence to ai_prompt.txt",
                       variable=self.merge_var, bg="white",
                       activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left", padx=16)

        # ---- action ----
        actions = tk.Frame(self._body, bg="white")
        actions.pack(pady=10)
        self.run_button = tk.Button(
            actions, text="READ SCREENS", command=self.start,
            bg=SUCCESS, fg="white", relief="flat",
            font=("Segoe UI", 12, "bold"), width=22)
        self.run_button.pack(side="left", padx=5)
        self.cancel_button = tk.Button(
            actions, text="CANCEL", command=self.cancel,
            bg="#888888", fg="white", relief="flat",
            font=("Segoe UI", 11, "bold"), width=12, state="disabled")
        self.cancel_button.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self._body, orient="horizontal",
                                        length=600, mode="determinate")
        self.progress.pack(pady=4)
        self.progress_label = tk.Label(self._body, text="", bg="white", fg="gray",
                                       font=("Segoe UI", 9))
        self.progress_label.pack()

        # ---- results ----
        table = tk.Frame(self._body, bg="white")
        table.pack(fill="both", expand=True, padx=22, pady=8)
        columns = ("Screenshot", "Steps", "Files", "Tabs",
                   "Cells", "Commands")
        self.tree = ttk.Treeview(table, columns=columns,
                                 show="headings", height=13)
        widths = {"Screenshot": 115, "Steps": 70, "Files": 210,
                  "Tabs": 130, "Cells": 120, "Commands": 280}
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=widths[column], anchor="w")
        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        bottom = tk.Frame(self._body, bg="white")
        bottom.pack(fill="x", padx=22, pady=8)
        self.export_button = tk.Button(
            bottom, text="EXPORT OCR CONTEXT", command=self.export,
            bg=BRAND, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), width=26, state="disabled")
        self.export_button.pack(side="left")
        self.status = tk.Label(bottom, text="", bg="white", fg="gray",
                               wraplength=620, justify="left")
        self.status.pack(side="left", padx=14)

        tk.Label(self._body,
                 text="Review the extracted text before sharing it with an "
                      "external AI tool.",
                 font=("Segoe UI", 8), bg="white", fg="gray").pack(
            side="bottom", pady=6)

    # ------------------------------------------------------
    def initial(self):
        sessions = os.path.join(app_dir(), "sessions")
        return sessions if os.path.isdir(sessions) else app_dir()

    def select(self):
        path = filedialog.askdirectory(title="Select session folder",
                                       initialdir=self.initial())
        if not path:
            return
        self.session = path
        self.folder_label.config(text=os.path.basename(path), fg="black")

        shots = list_screenshots(path)
        steps_present = os.path.exists(
            os.path.join(path, "process_steps.csv"))
        prompt_present = os.path.exists(os.path.join(path, "ai_prompt.txt"))

        self.status.config(
            text="{} screenshot(s) found | process_steps.csv: {} | "
                 "ai_prompt.txt: {}".format(
                     len(shots),
                     "yes" if steps_present else "no",
                     "yes" if prompt_present else "no"),
            fg=SUCCESS if shots else ERROR)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.export_button.config(state="disabled")

    # ------------------------------------------------------
    def start(self):
        if not self.ready:
            messagebox.showerror(
                APP_TITLE,
                "The OCR engine is not available.\n\n"
                "Install the Python package:\n"
                "    python -m pip install pytesseract pillow\n\n"
                "Then install the Tesseract engine from:\n"
                "    https://github.com/UB-Mannheim/tesseract/wiki")
            return
        if not self.session:
            messagebox.showwarning(APP_TITLE,
                                   "Select a session folder first.")
            return
        if not list_screenshots(self.session):
            messagebox.showwarning(
                APP_TITLE,
                "No screenshots were found in this session folder.")
            return

        self.cancelled = False
        self.run_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.export_button.config(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.worker = threading.Thread(target=self.work, daemon=True)
        self.worker.start()

    def cancel(self):
        self.cancelled = True
        self.progress_label.config(text="Cancelling...")

    def work(self):
        def progress(index, total, name):
            self.root.after(
                0, self.update_progress, index, total, name)

        try:
            results = process_session(
                self.session,
                self.upscale_var.get(),
                progress,
                lambda: self.cancelled,
            )
        except Exception as error:
            self.root.after(0, self.failed, str(error))
            return
        self.root.after(0, self.finished, results)

    def update_progress(self, index, total, name):
        self.progress["maximum"] = total
        self.progress["value"] = index
        self.progress_label.config(
            text="Reading {} of {}  -  {}".format(index, total, name))

    def failed(self, message):
        self.run_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.progress_label.config(text="")
        self.status.config(text=message, fg=ERROR)
        messagebox.showerror(APP_TITLE, message)

    def finished(self, results):
        self.results = results
        self.run_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.progress_label.config(text="")

        for item in results:
            found = item["found"]
            steps = ", ".join(str(number) for number, _ in item["steps"])
            self.tree.insert("", "end", values=(
                item["screenshot"],
                steps,
                ", ".join(found["files"]),
                ", ".join(found["sheets"]),
                ", ".join(found["cells"]),
                ", ".join(found["commands"]),
            ))

        useful = sum(1 for item in results if item["summary"])
        files = sum(len(item["found"]["files"]) for item in results)
        cells = sum(len(item["found"]["cells"]) for item in results)

        self.status.config(
            text="{} screen(s) read | {} produced usable evidence | "
                 "{} file name(s) | {} cell reference(s)".format(
                     len(results), useful, files, cells),
            fg=SUCCESS if useful else WARN)

        if results:
            self.export_button.config(state="normal")

    # ------------------------------------------------------
    def export(self):
        if not self.results:
            return
        csv_path = os.path.join(self.session, "ocr_context.csv")
        txt_path = os.path.join(self.session, "ocr_context.txt")

        try:
            write_csv(self.results, csv_path)
            entries = write_context(self.results, txt_path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return

        merged_message = ""
        if self.merge_var.get():
            ok, note = merge_into_prompt(self.session, txt_path)
            merged_message = "\n\n" + note

        messagebox.showinfo(
            APP_TITLE,
            "Export completed.\n\n"
            "Created:\n"
            "- ocr_context.csv\n"
            "- ocr_context.txt\n\n"
            "Step entries with evidence: {}\n\n"
            "Saved in:\n{}{}\n\n"
            "Review ocr_context.csv and remove any confidential values "
            "before pasting the prompt into an external AI tool.".format(
                entries, self.session, merged_message))

        self.status.config(text="Exported to " + self.session, fg=SUCCESS)
        try:
            os.startfile(self.session)
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
