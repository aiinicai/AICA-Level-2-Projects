"""
AICA SOP TOOL - Process Analyzer v7
====================================

Merges the two capture streams and prepares everything the SOP Builder needs.

Inputs
------
    activity_log.csv        Activity Recorder v3 (or earlier)
    interaction_log.csv     Interaction Capture v5 (or earlier)
    ocr_context.csv         Vision Extractor, optional

Outputs, written beside the activity log
----------------------------------------
    process_steps.csv
    ai_prompt.txt
    process_flow.png
    process_flow.pdf

Folder path handling
--------------------
Folder paths can arrive from either agent:

    Activity Recorder v3    resolves the path when Explorer becomes active,
                            which is what happens during navigation
    Interaction Capture v5  resolves the path when a shortcut fires while
                            Explorer is in focus

Earlier analyzer builds read the path only from the interaction log. In a
typical session every shortcut is pressed inside Excel, so no path was ever
found. This version reads the FolderPath column from BOTH logs.

Prompt reliability rules
------------------------
The generated prompt now tells the AI which parts of the screen evidence are
dependable and which are not. Optical character recognition matches sheet
names anywhere in the screen text, including column headers and cell
contents, and matches any letter-plus-digit token as a cell reference. Both
produce claims that disagree with the screenshot. The prompt therefore
forbids stating worksheet tabs and cell references, while permitting file
names, folder paths and ribbon commands, which are read from stable
interface regions.

The prompt also forbids sentences whose only content is that a detail
requires validation, because such a sentence carries no instruction.

Window layout
-------------
The action bar is anchored to the bottom of the window before the results
table is allowed to expand, so the export button cannot be pushed off the
screen on a smaller display.

Install
-------
    python -m pip install graphviz

Graphviz desktop software is also required. Verify with:
    dot -V

Run
---
    python process_analyzer_v7.py

Build EXE
---------
    pyinstaller --onefile --noconsole --clean --name AICA_Analyzer_v7 process_analyzer_v7.py
"""

import csv
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from graphviz import Digraph
    GRAPHVIZ = True
except Exception:
    Digraph = None
    GRAPHVIZ = False


APP_TITLE = "AICA SOP Tool - Process Analyzer v7"
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

SHORTCUT_TEXT = {
    "ctrl+c": "Copy the selected content",
    "ctrl+v": "Paste the copied content",
    "ctrl+s": "Save the current work",
    "ctrl+x": "Cut the selected content",
    "ctrl+z": "Undo the previous action",
    "ctrl+y": "Redo the previous action",
    "ctrl+p": "Open the print command",
    "ctrl+a": "Select all visible content",
    "ctrl+f": "Open the find command",
    "ctrl+n": "Create a new item",
    "ctrl+o": "Open an existing file",
    "ctrl+w": "Close the current item",
    "alt+tab": "Switch to another application",
    "f5": "Refresh the data",
    "f9": "Recalculate the workbook",
    "f12": "Open the Save As dialog",
}

NOISE = (
    "aica sop tool", "sop genius ai", "interaction capture",
    "activity recorder", "task switching", "program manager",
    "windows default lock screen",
)


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_time(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def friendly_app(value):
    value = (value or "").strip()
    if not value:
        return "Unknown Application"
    low = value.lower()
    if low in APP_NAMES:
        return APP_NAMES[low]
    if low.endswith(".exe"):
        return value.replace(".exe", "")
    return value


def clean_title(title):
    value = (title or "").strip()
    value = re.sub(r"^\(\d+\)\s*", "", value)
    value = re.sub(
        r"\s*[-\u2013\u2014]\s*(Microsoft\s+)?"
        r"(Excel|Word|PowerPoint|Outlook|Edge|Google Chrome|Chrome|"
        r"Firefox|Power BI Desktop|Teams|File Explorer)\s*$",
        "", value, flags=re.I)
    value = re.sub(r"\.(xlsx|xlsm|xls|csv|docx|doc|pptx|ppt|pdf|txt)\b",
                   "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" -\u2013\u2014")


def is_noise(title):
    low = (title or "").lower()
    return any(token in low for token in NOISE)


def shortcut_phrase(action):
    key = (action or "").strip().lower().split(" - ")[0].strip()
    if key in SHORTCUT_TEXT:
        return SHORTCUT_TEXT[key]
    low = (action or "").lower()
    if "double" in low and "click" in low:
        return "Double-click the required item"
    if "right" in low and "click" in low:
        return "Right-click the required item"
    if "middle" in low and "click" in low:
        return "Use the middle mouse button"
    if "click" in low:
        return "Select the required on-screen option"
    return "Perform the {} action".format(action)


def activity_phrase(application, detail):
    if application == "Microsoft Excel":
        return ("Open the {} workbook in Microsoft Excel".format(detail)
                if detail else "Open Microsoft Excel")
    if application == "Microsoft Word":
        return ("Open the {} document in Microsoft Word".format(detail)
                if detail else "Open Microsoft Word")
    if application == "Microsoft PowerPoint":
        return ("Open the {} presentation in Microsoft PowerPoint".format(detail)
                if detail else "Open Microsoft PowerPoint")
    if application == "Microsoft Outlook":
        if "inbox" in detail.lower():
            return "Review the Outlook inbox"
        return ("Open Microsoft Outlook and navigate to {}".format(detail)
                if detail else "Open Microsoft Outlook")
    if application == "Power BI Desktop":
        return ("Open the {} report in Power BI Desktop".format(detail)
                if detail else "Open Power BI Desktop")
    if application in ("Google Chrome", "Microsoft Edge", "Mozilla Firefox"):
        return ("Open {} in {}".format(detail, application)
                if detail else "Open {}".format(application))
    if application == "Windows File Explorer":
        return ("Navigate to {} in Windows File Explorer".format(detail)
                if detail else "Open Windows File Explorer")
    if detail:
        return "Work in {} on {}".format(application, detail)
    return "Open {}".format(application)


# =========================================================
# Log readers
# =========================================================

def read_activity(path, minimum):
    """
    Read the activity log.

    Activity Recorder v3 supplies a FolderPath column. Earlier recorders do
    not, in which case the field is absent and resolves to an empty string.
    """
    rows = []
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if not {"Timestamp", "Application", "WindowTitle"}.issubset(fields):
            raise ValueError(
                "Activity log requires Timestamp, Application and "
                "WindowTitle columns.")

        for row in reader:
            stamp = parse_time(row.get("Timestamp"))
            title = (row.get("WindowTitle") or "").strip()
            if stamp is None or not title or is_noise(title):
                continue
            try:
                duration = int(float(row.get("DurationSeconds") or 0))
            except ValueError:
                duration = 0
            if duration < minimum:
                continue

            rows.append({
                "timestamp": stamp,
                "end": stamp + timedelta(seconds=max(duration, 1)),
                "application": friendly_app(row.get("Application")),
                "detail": clean_title(title),
                "duration": duration,
                "screenshot": (row.get("Screenshot") or "").strip(),
                "shot_source": "activity",
                "folder": (row.get("FolderPath") or "").strip(),
                "raw": title,
            })

    rows.sort(key=lambda item: item["timestamp"])
    return rows


def activity_has_paths(path):
    """Report whether the activity log carries a FolderPath column."""
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            fields = set(csv.DictReader(handle).fieldnames or [])
        return "FolderPath" in fields
    except Exception:
        return False


def read_interactions(path):
    rows = []
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if not {"Timestamp", "Action"}.issubset(fields):
            raise ValueError(
                "Interaction log requires Timestamp and Action columns.")
        rich = "Screenshot" in fields or "FolderPath" in fields
        for row in reader:
            stamp = parse_time(row.get("Timestamp"))
            action = (row.get("Action") or "").strip()
            if stamp is None or not action:
                continue
            title = (row.get("WindowTitle") or "").strip()
            if title and is_noise(title):
                continue
            rows.append({
                "timestamp": stamp,
                "event_type": (row.get("EventType") or "Interaction").strip(),
                "action": action,
                "application": friendly_app(row.get("Application")),
                "title": title,
                "folder": (row.get("FolderPath") or "").strip(),
                "screenshot": (row.get("Screenshot") or "").strip(),
            })
    rows.sort(key=lambda item: item["timestamp"])
    return rows, rich


def context_for(activities, stamp):
    candidate = None
    for item in activities:
        if item["timestamp"] <= stamp <= item["end"]:
            return item
        if item["timestamp"] <= stamp:
            candidate = item
        else:
            break
    if candidate and abs((stamp - candidate["end"]).total_seconds()) <= 10:
        return candidate
    return None


# =========================================================
# OCR evidence
# =========================================================

def read_ocr(session):
    path = os.path.join(session, "ocr_context.csv")
    if not os.path.exists(path):
        return {}, False

    evidence = {}
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                shot = (row.get("Screenshot") or "").strip()
                if not shot:
                    continue
                record = {
                    "files": (row.get("FileNames") or "").strip(),
                    "paths": (row.get("FolderPaths") or "").strip(),
                    "sheets": (row.get("WorksheetTabs") or "").strip(),
                    "cells": (row.get("CellReferences") or "").strip(),
                    "commands": (row.get("CommandsVisible") or "").strip(),
                }
                parts = []
                if record["files"]:
                    parts.append("Files: " + record["files"])
                if record["paths"]:
                    parts.append("Paths: " + record["paths"])
                if record["sheets"]:
                    parts.append("Sheets/Tabs: " + record["sheets"])
                if record["cells"]:
                    parts.append("Cell refs: " + record["cells"])
                if record["commands"]:
                    parts.append("Commands: " + record["commands"])
                record["summary"] = " | ".join(parts)
                evidence[shot] = record
    except Exception:
        return {}, False

    return evidence, True


def attach_ocr(steps, evidence):
    attached = 0
    for row in steps:
        shot = row.get("screenshot") or ""
        record = evidence.get(shot)
        if record and record["summary"]:
            row["ocr"] = record["summary"]
            attached += 1
        else:
            row["ocr"] = ""
    return attached


# =========================================================
# Merge
# =========================================================

def merge(activities, interactions, rich, include_mouse, merge_repeats):
    timeline = []

    for item in activities:
        timeline.append({
            "timestamp": item["timestamp"],
            "record_type": "Activity",
            "application": item["application"],
            "detail": item["detail"],
            "folder": item.get("folder", ""),
            "description": activity_phrase(item["application"], item["detail"]),
            "duration": item["duration"],
            "screenshot": item["screenshot"],
            "shot_source": "activity",
            "source_event": item["raw"],
            "ocr": "",
        })

    for item in interactions:
        low = item["action"].lower()
        is_mouse = "click" in low or item["event_type"].lower() == "mouse"
        if is_mouse and not include_mouse:
            continue

        if rich and item["application"] != "Unknown Application":
            application = item["application"]
            detail = clean_title(item["title"])
            folder = item["folder"]
        else:
            ctx = context_for(activities, item["timestamp"])
            application = ctx["application"] if ctx else "Unknown Application"
            detail = ctx["detail"] if ctx else ""
            folder = ctx.get("folder", "") if ctx else ""

        if rich and item["screenshot"]:
            screenshot = item["screenshot"]
            source = "interaction"
        else:
            ctx = context_for(activities, item["timestamp"])
            screenshot = ctx["screenshot"] if ctx else ""
            source = "activity"

        phrase = shortcut_phrase(item["action"])
        if application and application != "Unknown Application":
            phrase = "{} in {}".format(phrase, application)

        timeline.append({
            "timestamp": item["timestamp"],
            "record_type": "Interaction",
            "application": application,
            "detail": detail,
            "folder": folder,
            "description": phrase,
            "duration": 0,
            "screenshot": screenshot,
            "shot_source": source,
            "source_event": item["action"],
            "ocr": "",
        })

    timeline.sort(key=lambda r: (r["timestamp"],
                                0 if r["record_type"] == "Activity" else 1))

    cleaned = []
    for row in timeline:
        if cleaned:
            previous = cleaned[-1]
            same = previous["description"] == row["description"]
            close = abs((row["timestamp"] -
                         previous["timestamp"]).total_seconds()) <= 2
            if same and close:
                continue
        cleaned.append(row)

    if merge_repeats:
        merged = []
        for row in cleaned:
            if (row["record_type"] == "Activity" and merged
                    and merged[-1]["record_type"] == "Activity"
                    and merged[-1]["application"] == row["application"]
                    and merged[-1]["detail"] == row["detail"]):
                merged[-1]["duration"] += row["duration"]
                if not merged[-1]["screenshot"] and row["screenshot"]:
                    merged[-1]["screenshot"] = row["screenshot"]
                if not merged[-1]["folder"] and row["folder"]:
                    merged[-1]["folder"] = row["folder"]
                continue
            merged.append(row)
        cleaned = merged

    # An Explorer step with no resolved path inherits the nearest known one.
    last_folder = ""
    for row in cleaned:
        if row["folder"]:
            last_folder = row["folder"]
        elif row["application"] == "Windows File Explorer" and last_folder:
            row["folder"] = last_folder

    for index, row in enumerate(cleaned, start=1):
        row["step_no"] = index
    return cleaned


def copy_screens(steps, activity_dir, interaction_dir):
    target = os.path.join(activity_dir, "screenshots")
    os.makedirs(target, exist_ok=True)
    copied = 0
    for row in steps:
        if row["shot_source"] != "interaction" or not row["screenshot"]:
            continue
        source = os.path.join(interaction_dir, "screenshots", row["screenshot"])
        if not os.path.exists(source):
            row["screenshot"] = ""
            continue
        destination = os.path.join(target, row["screenshot"])
        if not os.path.exists(destination):
            try:
                shutil.copy2(source, destination)
                copied += 1
            except Exception:
                row["screenshot"] = ""
    return copied


# =========================================================
# Writers
# =========================================================

STEP_FIELDS = [
    "StepNo", "Timestamp", "RecordType", "Application", "Detail",
    "FolderPath", "StepDescription", "DurationSeconds",
    "Screenshot", "OcrEvidence", "SourceEvent",
]


def write_steps(steps, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=STEP_FIELDS)
        writer.writeheader()
        for row in steps:
            stamp = row["timestamp"]
            if hasattr(stamp, "strftime"):
                stamp = stamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            writer.writerow({
                "StepNo": row["step_no"],
                "Timestamp": stamp,
                "RecordType": row["record_type"],
                "Application": row["application"],
                "Detail": row["detail"],
                "FolderPath": row["folder"],
                "StepDescription": row["description"],
                "DurationSeconds": row["duration"],
                "Screenshot": row["screenshot"],
                "OcrEvidence": row.get("ocr", ""),
                "SourceEvent": row["source_event"],
            })


def load_steps(path):
    """Read process_steps.csv back in for a prompt rebuild."""
    steps = []
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                number = int(float(row.get("StepNo") or 0))
            except ValueError:
                continue
            if number <= 0:
                continue
            steps.append({
                "step_no": number,
                "timestamp": (row.get("Timestamp") or "").strip(),
                "record_type": (row.get("RecordType") or "Activity").strip(),
                "application": (row.get("Application") or "").strip(),
                "detail": (row.get("Detail") or "").strip(),
                "folder": (row.get("FolderPath") or "").strip(),
                "description": (row.get("StepDescription") or "").strip(),
                "duration": (row.get("DurationSeconds") or "0").strip(),
                "screenshot": (row.get("Screenshot") or "").strip(),
                "ocr": (row.get("OcrEvidence") or "").strip(),
                "source_event": (row.get("SourceEvent") or "").strip(),
                "shot_source": "activity",
            })
    steps.sort(key=lambda item: item["step_no"])
    return steps


def write_prompt(steps, path, meta, ocr_present):
    paths = sorted({row["folder"] for row in steps if row["folder"]})
    with_evidence = sum(1 for row in steps if row.get("ocr"))

    lines = [
        "Act as a Process Excellence Consultant and SOP author.",
        "",
        "Create a professional Standard Operating Procedure using only the",
        "captured desktop activities, interaction events and screen evidence",
        "below.",
        "",
        "PROCESS METADATA PROVIDED BY THE USER",
        "=" * 72,
        "Process Name: {}".format(meta["process_name"] or "Unnamed Process"),
        "Process Owner: {}".format(
            meta["process_owner"] or "Business validation required"),
        "Process Performer: {}".format(
            meta["process_performer"] or meta["process_owner"]
            or "Business validation required"),
        "Department: {}".format(
            meta["department"] or "Business validation required"),
        "Frequency: {}".format(
            meta["frequency"] or "Business validation required"),
        "Reviewer / Approver: {}".format(
            meta["approver"] or "Business validation required"),
        "Total Captured Steps: {}".format(len(steps)),
        "=" * 72,
        "",
    ]

    if paths:
        lines.append("CAPTURED FOLDER PATHS")
        lines.append("=" * 72)
        lines.extend(paths)
        lines.append("=" * 72)
        lines.append("")
        lines.append("These folder paths were captured directly from Windows")
        lines.append("File Explorer. State them exactly. Do not mark them as")
        lines.append("requiring validation.")
        lines.append("")

    if ocr_present:
        lines.extend([
            "HOW TO READ THE SEQUENCE BELOW",
            "=" * 72,
            "Each step may be followed by a 'Screen evidence' line. That line",
            "was read from the actual screenshot by Optical Character",
            "Recognition and lists the file names, worksheet tabs, cell",
            "ranges, folder paths and interface commands that were visible.",
            "",
            "Use this evidence to write specific instructions. Where the",
            "evidence names a file, folder or command, state it exactly and",
            "do not mark it as requiring validation. Ignore any evidence item",
            "that is clearly unrelated to the step.",
            "=" * 72,
            "",
        ])

    lines.append("CAPTURED PROCESS SEQUENCE")
    lines.append("=" * 72)

    for row in steps:
        extra = ""
        if row["detail"]:
            extra += " [Context: {}]".format(row["detail"])
        if row["folder"]:
            extra += " [Path: {}]".format(row["folder"])
        lines.append("Step {0}: {1}{2}".format(
            row["step_no"], row["description"], extra))
        if row.get("ocr"):
            lines.append("    Screen evidence: {}".format(row["ocr"]))

    lines.extend([
        "=" * 72,
        "",
        "MANDATORY OUTPUT STRUCTURE",
        "1. Purpose",
        "2. Scope",
        "3. Process Owner and Frequency",
        "4. Prerequisites and System Access",
        "5. Inputs",
        "6. Detailed Process Steps",
        "7. Outputs and Deliverables",
        "8. Key Controls and Validation Checks",
        "9. Risks and Common Errors",
        "10. Escalation Contacts",
        "",
        "DETAILED PROCESS STEPS FORMAT",
        "Under section 6, provide a Markdown table with exactly these columns:",
        "| Step | Activity | Detailed User Instruction |",
        "Include one row for every captured step number, in the same sequence.",
        "Do not renumber, omit, combine, or invent captured steps.",
        "",
        "SCREEN EVIDENCE RELIABILITY",
        "The screen evidence was produced by optical character recognition",
        "and is not reliable for the following, which must never be stated:",
        "- Do not list which worksheet tabs were displayed. Sheet names are",
        "  matched anywhere in the screen text, including column headers and",
        "  cell contents, so the list frequently disagrees with the screen.",
        "- Do not state visible cell references. Tokens such as LTO7, PT053",
        "  and PLO002827 are data values and reference numbers, not cell",
        "  addresses.",
        "- File names, folder paths and ribbon commands may be stated,",
        "  because those are read from stable interface regions.",
        "",
        "SENTENCES THAT STATE NOTHING",
        "Do not write a sentence whose only purpose is to say a detail",
        "requires validation. If a detail is not evidenced, omit it and write",
        "the instruction using what is known. Use 'Business validation",
        "required' only inside a table cell that must carry a value.",
        "",
        "PLACEHOLDER AND VALIDATION RULES - STRICT",
        "- Never write '[Process owner to confirm]'.",
        "- Never replace missing technical detail with the process owner's name.",
        "- Use the supplied metadata values consistently.",
        "- Where a folder path is supplied, state the actual path.",
        "- Where screen evidence names a file or command, state it exactly",
        "  rather than marking it for validation.",
        "- Attach 'Business validation required' only to the unknown field,",
        "  never to a person.",
        "- Do not invent facts, systems, controls, owners or deadlines.",
        "",
        "SECTION SEPARATORS",
        "Do not insert horizontal rules such as --- between sections. Use the",
        "section headings alone.",
        "",
        "WRITING RULES",
        "- Use clear professional business English.",
        "- Preserve the exact captured sequence.",
        "- Convert shortcuts into practical user instructions.",
        "- Do not reproduce these instructions in the final SOP.",
    ])

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return with_evidence


def wrap(text, limit=38):
    words = text.split()
    lines, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > limit:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def make_flow(steps, directory, name):
    if not GRAPHVIZ:
        return False, "Python graphviz package is not installed."
    try:
        dot = Digraph(name="process_flow", comment=name)
        dot.attr(rankdir="TB", bgcolor="white", pad="0.3",
                 nodesep="0.35", ranksep="0.48", splines="ortho")
        dot.attr("node", fontname="Arial", fontsize="10",
                 color="#6B001B", penwidth="1.2")
        dot.attr("edge", color="#666666", arrowhead="vee", penwidth="1.1")
        dot.node("START", "START", shape="oval", style="filled",
                 fillcolor="#D9EAD3")
        previous = "START"
        for row in steps:
            node = "STEP_{}".format(row["step_no"])
            label = "{0}. {1}".format(row["step_no"], wrap(row["description"]))
            fill = ("#FFF2CC" if row["record_type"] == "Interaction"
                    else "#D9EAF7")
            dot.node(node, label, shape="box", style="rounded,filled",
                     fillcolor=fill, margin="0.14,0.08")
            dot.edge(previous, node)
            previous = node
        dot.node("END", "END", shape="oval", style="filled",
                 fillcolor="#F4CCCC")
        dot.edge(previous, "END")
        target = os.path.join(directory, "process_flow")
        dot.render(target, format="png", cleanup=True)
        dot.render(target, format="pdf", cleanup=True)
        return True, "Flowchart created."
    except Exception as error:
        return False, str(error)


# =========================================================
# GUI
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


class Window:

    def __init__(self, root):
        self.root = root
        self.activity_path = ""
        self.interaction_path = ""
        self.output_dir = ""
        self.steps = []
        self.rich = False

        root.title(APP_TITLE)
        root.geometry("1060x860")
        root.minsize(1000, 700)
        root.configure(bg="white")
        # Scrollable body. Widgets are placed here so content
        # below the fold can be reached by scrolling.
        self._body = attach_scroll(root)


        # -------------------------------------------------------------
        # The action bar is packed to the bottom FIRST, before the table
        # is allowed to expand. Tkinter honours packing order, so the
        # export button can never be displaced off the window.
        # -------------------------------------------------------------
        bottom = tk.Frame(self._body, bg="white")
        bottom.pack(side="bottom", fill="x", padx=22, pady=(6, 12))

        self.export_button = tk.Button(
            bottom, text="EXPORT STEPS + PROMPT + FLOWCHART",
            command=self.export, bg=BRAND, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), width=38, state="disabled",
            cursor="hand2")
        self.export_button.pack(side="left")

        self.status = tk.Label(bottom, text="", bg="white", fg="gray",
                               wraplength=520, justify="left", anchor="w")
        self.status.pack(side="left", padx=14)

        tk.Label(self._body, text=TOOL_NAME.upper(),
                 font=("Segoe UI", 20, "bold"),
                 bg="white", fg=BRAND).pack(pady=(12, 0))
        tk.Label(self._body, text="Process Analyzer | Version 7",
                 font=("Segoe UI", 9), bg="white", fg="gray").pack()

        # ---- input logs ----
        files = tk.LabelFrame(self._body, text=" Input logs ", bg="white",
                              fg=BRAND, font=("Segoe UI", 9, "bold"))
        files.pack(fill="x", padx=22, pady=8)
        self.activity_label = self._row(
            files, "SELECT ACTIVITY LOG", self.pick_activity,
            "No activity log selected")
        self.interaction_label = self._row(
            files, "SELECT INTERACTION LOG", self.pick_interaction,
            "No interaction log selected")

        self.mode_label = tk.Label(
            files, text="Log format: not detected", bg="white",
            fg="gray", font=("Segoe UI", 9, "bold"), anchor="w",
            wraplength=990, justify="left")
        self.mode_label.pack(fill="x", padx=12, pady=(0, 2))

        self.path_label = tk.Label(
            files, text="Folder paths: not checked", bg="white",
            fg="gray", font=("Segoe UI", 9, "bold"), anchor="w",
            wraplength=990, justify="left")
        self.path_label.pack(fill="x", padx=12, pady=(0, 2))

        self.ocr_label = tk.Label(
            files, text="OCR evidence: not checked", bg="white",
            fg="gray", font=("Segoe UI", 9, "bold"), anchor="w",
            wraplength=990, justify="left")
        self.ocr_label.pack(fill="x", padx=12, pady=(0, 8))

        # ---- metadata ----
        meta = tk.LabelFrame(self._body, text=" Process metadata sent to AI ",
                             bg="white", fg=BRAND,
                             font=("Segoe UI", 9, "bold"))
        meta.pack(fill="x", padx=22, pady=4)
        grid = tk.Frame(meta, bg="white")
        grid.pack(fill="x", padx=10, pady=8)
        self.entries = {}
        fields = [
            ("process_name", "Process name", "Monthly Revenue Report"),
            ("process_owner", "Process owner", "Dheeraj Gupta"),
            ("process_performer", "Process performer", "Dheeraj Gupta"),
            ("department", "Department", "Finance"),
            ("frequency", "Frequency", "Monthly"),
            ("approver", "Reviewer / approver", "Anand Gupta"),
        ]
        for index, (key, label, default) in enumerate(fields):
            r, c = index // 2, (index % 2) * 2
            tk.Label(grid, text=label + ":", bg="white").grid(
                row=r, column=c, sticky="w", padx=(0, 6), pady=4)
            entry = tk.Entry(grid, width=34)
            entry.grid(row=r, column=c + 1, sticky="w", padx=(0, 25), pady=4)
            entry.insert(0, default)
            self.entries[key] = entry

        # ---- options ----
        opts = tk.LabelFrame(self._body, text=" Analysis options ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        opts.pack(fill="x", padx=22, pady=4)
        row = tk.Frame(opts, bg="white")
        row.pack(fill="x", padx=10, pady=8)
        tk.Label(row, text="Minimum activity duration:",
                 bg="white").pack(side="left")
        self.duration = tk.Spinbox(row, from_=0, to=120, width=5)
        self.duration.pack(side="left", padx=(6, 20))
        self.duration.delete(0, "end")
        self.duration.insert(0, "2")

        # Generic mouse clicks add many uninformative steps, so this is
        # unticked by default.
        self.mouse_var = tk.BooleanVar(value=False)
        self.merge_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row, text="Include generic mouse clicks",
                       variable=self.mouse_var, bg="white",
                       activebackground="white").pack(side="left")
        tk.Checkbutton(row, text="Merge repeated activity rows",
                       variable=self.merge_var, bg="white",
                       activebackground="white").pack(side="left", padx=18)

        # ---- actions ----
        actions = tk.Frame(self._body, bg="white")
        actions.pack(pady=10)
        tk.Button(actions, text="ANALYZE AND PREVIEW", command=self.analyze,
                  bg=SUCCESS, fg="white", relief="flat",
                  font=("Segoe UI", 11, "bold"), width=26,
                  cursor="hand2").pack(side="left", padx=5)
        tk.Button(actions, text="REBUILD PROMPT WITH OCR",
                  command=self.rebuild, bg="#1F3864", fg="white",
                  relief="flat", font=("Segoe UI", 11, "bold"),
                  width=26, cursor="hand2").pack(side="left", padx=5)

        # ---- results table, expands into whatever space remains ----
        table = tk.Frame(self._body, bg="white")
        table.pack(fill="both", expand=True, padx=22, pady=(4, 0))

        columns = ("StepNo", "Type", "Application", "Step",
                   "FolderPath", "Screenshot", "Evidence")
        self.tree = ttk.Treeview(table, columns=columns,
                                 show="headings", height=10)
        widths = {"StepNo": 45, "Type": 75, "Application": 125,
                  "Step": 280, "FolderPath": 185, "Screenshot": 95,
                  "Evidence": 230}
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=widths[column], anchor="w")

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # -----------------------------------------------------------------
    def _row(self, parent, text, command, default):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=10, pady=4)
        tk.Button(row, text=text, command=command, bg=BRAND, fg="white",
                  relief="flat", width=24, cursor="hand2").pack(side="left")
        label = tk.Label(row, text=default, bg="white", fg="gray", anchor="w")
        label.pack(side="left", padx=12)
        return label

    def initial(self):
        sessions = os.path.join(base_dir(), "sessions")
        return sessions if os.path.isdir(sessions) else base_dir()

    def check_ocr(self):
        if not self.output_dir:
            return
        evidence, present = read_ocr(self.output_dir)
        if present:
            useful = sum(1 for item in evidence.values() if item["summary"])
            self.ocr_label.config(
                text="OCR evidence: ocr_context.csv found - {} screen(s), "
                     "{} with usable detail.".format(len(evidence), useful),
                fg=SUCCESS)
        else:
            self.ocr_label.config(
                text="OCR evidence: not found. Run the Vision Extractor, "
                     "then use REBUILD PROMPT WITH OCR.",
                fg=WARN)

    def pick_activity(self):
        path = filedialog.askopenfilename(
            title="Select activity_log.csv", initialdir=self.initial(),
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        self.activity_path = path
        self.output_dir = os.path.dirname(path)
        self.activity_label.config(text=path, fg="black")

        if activity_has_paths(path):
            self.path_label.config(
                text="Folder paths: the activity log carries a FolderPath "
                     "column, so Explorer navigation will be captured.",
                fg=SUCCESS)
        else:
            self.path_label.config(
                text="Folder paths: this activity log has no FolderPath "
                     "column. Re-record with activity_recorder_v3.py to "
                     "capture Explorer navigation paths.",
                fg=WARN)
        self.check_ocr()

    def pick_interaction(self):
        path = filedialog.askopenfilename(
            title="Select interaction_log.csv", initialdir=self.initial(),
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        self.interaction_path = path
        self.interaction_label.config(text=path, fg="black")
        try:
            with open(path, "r", newline="", encoding="utf-8-sig") as handle:
                fields = set(csv.DictReader(handle).fieldnames or [])
            rich = "Screenshot" in fields and "FolderPath" in fields
            self.mode_label.config(
                text=("Log format: Version 4 or later - event screenshots "
                      "available") if rich else
                     ("Log format: Version 3 - no event screenshots; screens "
                      "will be inherited from the activity log"),
                fg=SUCCESS if rich else WARN)
        except Exception:
            self.mode_label.config(text="Log format: could not be read",
                                   fg=ERROR)

    def metadata(self):
        return {key: entry.get().strip()
                for key, entry in self.entries.items()}

    def fill_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.steps:
            self.tree.insert("", "end", values=(
                row["step_no"], row["record_type"], row["application"],
                row["description"], row["folder"], row["screenshot"],
                row.get("ocr", "")[:120]))

    def analyze(self):
        if not self.activity_path or not self.interaction_path:
            messagebox.showwarning(
                APP_TITLE, "Select both the activity and interaction logs.")
            return
        try:
            minimum = int(self.duration.get())
        except ValueError:
            minimum = 0
        try:
            activities = read_activity(self.activity_path, minimum)
            interactions, rich = read_interactions(self.interaction_path)
            self.rich = rich
            self.steps = merge(activities, interactions, rich,
                               self.mouse_var.get(), self.merge_var.get())
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return

        if not self.steps:
            messagebox.showwarning(
                APP_TITLE,
                "No steps remained after filtering. Reduce the minimum "
                "activity duration and try again.")
            return

        evidence, present = read_ocr(self.output_dir)
        attached = attach_ocr(self.steps, evidence) if present else 0

        self.fill_table()
        distinct = len({r["screenshot"] for r in self.steps if r["screenshot"]})
        paths = len({r["folder"] for r in self.steps if r["folder"]})
        self.status.config(
            text="{} steps | {} distinct screens | {} folder path(s) | "
                 "{} with OCR evidence".format(
                     len(self.steps), distinct, paths, attached),
            fg=SUCCESS if paths else WARN)
        self.export_button.config(state="normal")
        self.check_ocr()

    def rebuild(self):
        directory = self.output_dir
        if not directory:
            directory = filedialog.askdirectory(
                title="Select the session folder", initialdir=self.initial())
            if not directory:
                return
            self.output_dir = directory

        steps_path = os.path.join(directory, "process_steps.csv")
        if not os.path.exists(steps_path):
            messagebox.showwarning(
                APP_TITLE,
                "process_steps.csv was not found in this folder. Run "
                "ANALYZE AND PREVIEW and export first.")
            return

        try:
            steps = load_steps(steps_path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return

        evidence, present = read_ocr(directory)
        if not present:
            messagebox.showwarning(
                APP_TITLE,
                "ocr_context.csv was not found in this folder.\n\n"
                "Run the Vision Extractor on this session first, then use "
                "this button again.")
            return

        attached = attach_ocr(steps, evidence)

        try:
            write_steps(steps, steps_path)
            written = write_prompt(
                steps, os.path.join(directory, "ai_prompt.txt"),
                self.metadata(), True)
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return

        self.steps = steps
        self.fill_table()
        self.export_button.config(state="normal")
        self.check_ocr()

        messagebox.showinfo(
            APP_TITLE,
            "Prompt rebuilt with screen evidence.\n\n"
            "Steps read: {}\n"
            "Steps carrying OCR evidence: {}\n\n"
            "Updated:\n- process_steps.csv\n- ai_prompt.txt\n\n"
            "Saved in:\n{}\n\n"
            "Next: paste ai_prompt.txt into ChatGPT and save the reply as "
            "sop_text.txt.".format(len(steps), written, directory))

        self.status.config(
            text="Prompt rebuilt - {} step(s) carry screen evidence".format(
                attached), fg=SUCCESS)

    def export(self):
        if not self.steps:
            return
        directory = self.output_dir or os.path.dirname(self.activity_path)
        os.makedirs(directory, exist_ok=True)

        copied = 0
        if self.rich and self.interaction_path:
            copied = copy_screens(
                self.steps, directory,
                os.path.dirname(self.interaction_path))

        evidence, present = read_ocr(directory)
        if present:
            attach_ocr(self.steps, evidence)

        try:
            write_steps(self.steps,
                        os.path.join(directory, "process_steps.csv"))
            written = write_prompt(
                self.steps, os.path.join(directory, "ai_prompt.txt"),
                self.metadata(), present)
            flow_ok, flow_message = make_flow(
                self.steps, directory,
                self.metadata()["process_name"] or "Business Process")
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return

        created = ["process_steps.csv", "ai_prompt.txt"]
        if flow_ok:
            created.extend(["process_flow.png", "process_flow.pdf"])

        paths = len({r["folder"] for r in self.steps if r["folder"]})

        message = ("Export completed.\n\nCreated:\n- " + "\n- ".join(created)
                   + "\n\nScreenshots copied: {}".format(copied)
                   + "\nFolder paths captured: {}".format(paths)
                   + "\nSteps with screen evidence: {}".format(written)
                   + "\n\nSaved in:\n" + directory)
        if not flow_ok:
            message += "\n\nFlowchart not created: " + flow_message
        if paths == 0:
            message += ("\n\nNo folder paths were captured. Re-record with "
                        "activity_recorder_v3.py and run its folder path "
                        "self-test before recording.")
        if not present:
            message += ("\n\nNo OCR evidence found. Run the Vision Extractor, "
                        "then use REBUILD PROMPT WITH OCR.")
        else:
            message += ("\n\nNext: paste ai_prompt.txt into ChatGPT and save "
                        "the reply as sop_text.txt.")

        messagebox.showinfo(APP_TITLE, message)
        self.status.config(text="Exported to " + directory, fg=SUCCESS)
        self.fill_table()


if __name__ == "__main__":
    root = tk.Tk()
    Window(root)
    root.mainloop()
