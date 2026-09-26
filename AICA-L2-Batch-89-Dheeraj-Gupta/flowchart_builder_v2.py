"""
AICA SOP TOOL - Flowchart Builder v2
=====================================

Regenerates process_flow.png / .pdf from an existing process_steps.csv.

Why this exists
---------------
A fifteen-step process drawn as a single vertical chain produces a diagram
roughly six times taller than it is wide. To fit the page it must either be
shrunk until the text is unreadable, or sliced across pages, which can cut
through a node box.

v2 lays the same sequence out in COLUMNS. Fifteen steps in three columns of
five produce a diagram close to square, which fits one page at full width
with readable text and no slicing.

What it fixes
-------------
1. Node boxes split across page breaks - removed, because the diagram now
   fits a single page.
2. Unreadable node text - the diagram is rendered at higher resolution and
   is no longer shrunk to fit.
3. Repeated step labels - where the same activity description appears more
   than once, the later occurrence is annotated as a revisit so the reader
   can see it is a genuine return to an earlier application, not a
   duplication error.

What it deliberately does NOT do
--------------------------------
It does not reorder steps. The sequence is the recorded order of events.
Rearranging it to match an expected order would misrepresent what was
actually captured. If the recorded order is wrong, re-record the process.

Requirements
------------
    python -m pip install graphviz
Graphviz desktop software must also be installed. Verify with:
    dot -V

Run
---
    python flowchart_builder_v2.py

Build EXE
---------
    pyinstaller --onefile --noconsole --clean --name AICA_Flowchart_v2 flowchart_builder_v2.py
"""

import csv
import math
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from graphviz import Digraph
    GRAPHVIZ = True
except Exception:
    Digraph = None
    GRAPHVIZ = False


APP_TITLE = "AICA SOP Tool - Flowchart Builder v2"
TOOL_NAME = "AICA SOP Tool"
BRAND = "#6B001B"
SUCCESS = "#1F7A1F"
WARN = "#9A6700"
ERROR = "#C00000"

ACTIVITY_FILL = "#D9EAF7"
INTERACTION_FILL = "#FFF2CC"
REVISIT_FILL = "#EDE3F2"
START_FILL = "#D9EAD3"
END_FILL = "#F4CCCC"


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# =========================================================
# Input
# =========================================================

def read_steps(session):
    """Read process_steps.csv produced by the Process Analyzer."""
    path = os.path.join(session, "process_steps.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            "process_steps.csv was not found in the selected folder."
        )

    steps = []
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if not {"StepNo", "StepDescription"}.issubset(fields):
            raise ValueError(
                "process_steps.csv requires StepNo and StepDescription columns."
            )
        for row in reader:
            try:
                number = int(float(row.get("StepNo") or 0))
            except ValueError:
                continue
            if number <= 0:
                continue
            steps.append({
                "number": number,
                "description": (row.get("StepDescription") or "").strip(),
                "record_type": (row.get("RecordType") or "Activity").strip(),
                "application": (row.get("Application") or "").strip(),
                "detail": (row.get("Detail") or "").strip(),
            })

    steps.sort(key=lambda item: item["number"])
    if not steps:
        raise ValueError("No usable steps were found.")
    return steps


def mark_revisits(steps):
    """
    Identify steps whose description has appeared before.

    A repeated description is not an error. It means the user genuinely
    returned to an application already used earlier in the process. The
    diagram states this explicitly so the reader is not left wondering
    whether the step was duplicated by mistake.
    """
    seen = {}
    revisits = 0
    for step in steps:
        key = step["description"].strip().lower()
        if key and key in seen:
            step["revisit_of"] = seen[key]
            revisits += 1
        else:
            step["revisit_of"] = 0
            if key:
                seen[key] = step["number"]
    return revisits


# =========================================================
# Layout
# =========================================================

def suggest_columns(count):
    """
    Choose a column count that produces a near-square diagram.

    A node is roughly three times wider than it is tall, so aiming for
    rows ~= columns * 3 keeps the overall shape close to a page.
    """
    if count <= 4:
        return 1
    columns = max(1, int(round(math.sqrt(count / 1.8))))
    return max(1, min(columns, 5))


def build_columns(steps, per_column):
    """Split the sequence into vertical columns, preserving order."""
    columns = []
    for index in range(0, len(steps), per_column):
        columns.append(steps[index:index + per_column])
    return columns


def wrap(text, limit=30):
    """Wrap a label so nodes stay a consistent width."""
    words = (text or "").split()
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
    return "\\n".join(lines)


def node_label(step, annotate_revisits):
    label = "{}. {}".format(step["number"], wrap(step["description"]))
    if annotate_revisits and step.get("revisit_of"):
        label += "\\n(returns to step {})".format(step["revisit_of"])
    return label


# =========================================================
# Render
# =========================================================

def build_flowchart(session, steps, per_column, annotate_revisits,
                    resolution, process_name):
    """Produce process_flow.png and process_flow.pdf in column layout."""
    if not GRAPHVIZ:
        return False, "The Python graphviz package is not installed.", 0

    columns = build_columns(steps, per_column)

    dot = Digraph(name="process_flow", comment=process_name)
    dot.attr(
        rankdir="TB",
        bgcolor="white",
        pad="0.35",
        nodesep="0.30",
        ranksep="0.42",
        splines="ortho",
        newrank="true",
        dpi=str(resolution),
    )
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Segoe UI",
        fontsize="11",
        color=BRAND,
        penwidth="1.3",
        margin="0.16,0.10",
        width="2.5",
        fixedsize="false",
    )
    dot.attr("edge", color="#666666", arrowhead="vee", penwidth="1.2")

    # ---- nodes, column by column ----
    dot.node("START", "START", shape="oval", fillcolor=START_FILL,
             fontsize="12", width="1.4")

    for c_index, column in enumerate(columns):
        for step in column:
            node_id = "S{}".format(step["number"])
            if step.get("revisit_of") and annotate_revisits:
                fill = REVISIT_FILL
            elif step["record_type"] == "Interaction":
                fill = INTERACTION_FILL
            else:
                fill = ACTIVITY_FILL
            dot.node(node_id, node_label(step, annotate_revisits),
                     fillcolor=fill)

    dot.node("END", "END", shape="oval", fillcolor=END_FILL,
             fontsize="12", width="1.4")

    # ---- vertical chain inside each column ----
    for c_index, column in enumerate(columns):
        previous = "START" if c_index == 0 else None
        for step in column:
            node_id = "S{}".format(step["number"])
            if previous:
                dot.edge(previous, node_id)
            previous = node_id

    # ---- carry the sequence from one column to the next ----
    # constraint=false keeps these edges from distorting the vertical ranks.
    for c_index in range(len(columns) - 1):
        last = "S{}".format(columns[c_index][-1]["number"])
        first = "S{}".format(columns[c_index + 1][0]["number"])
        dot.edge(last, first, constraint="false", style="dashed",
                 color="#9A6700", penwidth="1.4")

    # ---- close the final column ----
    if columns:
        dot.edge("S{}".format(columns[-1][-1]["number"]), "END")

    # ---- align the head of each column on the same rank ----
    if len(columns) > 1:
        heads = ["S{}".format(column[0]["number"]) for column in columns]
        with dot.subgraph() as same:
            same.attr(rank="same")
            for head in heads:
                same.node(head)
        # Invisible edges fix the left-to-right order of the columns.
        for index in range(len(heads) - 1):
            dot.edge(heads[index], heads[index + 1],
                     style="invis", constraint="false", weight="10")

    target = os.path.join(session, "process_flow")
    try:
        dot.render(target, format="png", cleanup=True)
        dot.render(target, format="pdf", cleanup=True)
    except Exception as error:
        return False, str(error), len(columns)

    return True, "Flowchart created.", len(columns)


def describe_shape(session):
    """Report the dimensions of the rendered PNG, if Pillow is available."""
    path = os.path.join(session, "process_flow.png")
    if not os.path.exists(path):
        return ""
    try:
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
        ratio = height / float(width) if width else 0
        verdict = ("fits one page" if ratio <= 1.9
                   else "still tall; increase steps per column")
        return "{} x {} pixels, height/width {:.2f} - {}".format(
            width, height, ratio, verdict)
    except Exception:
        return ""


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


class App:

    def __init__(self, root):
        self.root = root
        self.session = ""
        self.steps = []

        root.title(APP_TITLE)
        root.geometry("900x700")
        root.configure(bg="white")
        # Scrollable body. Widgets are placed here so content
        # below the fold can be reached by scrolling.
        self._body = attach_scroll(root)


        tk.Label(self._body, text=TOOL_NAME.upper(),
                 font=("Segoe UI", 20, "bold"),
                 bg="white", fg=BRAND).pack(pady=(12, 0))
        tk.Label(self._body, text="Flowchart Builder | Version 2 - column layout",
                 font=("Segoe UI", 9), bg="white", fg="gray").pack()

        if not GRAPHVIZ:
            tk.Label(self._body,
                     text="The Python graphviz package is not installed. "
                          "Run: python -m pip install graphviz",
                     bg="white", fg=ERROR,
                     font=("Segoe UI", 9, "bold")).pack(pady=4)

        top = tk.Frame(self._body, bg="white")
        top.pack(fill="x", padx=22, pady=10)
        tk.Button(top, text="SELECT SESSION FOLDER", command=self.select,
                  bg=BRAND, fg="white", relief="flat", width=24,
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        self.folder = tk.Label(top, text="No folder selected",
                               bg="white", fg="gray")
        self.folder.pack(side="left", padx=12)

        info = tk.LabelFrame(self._body, text=" Sequence ", bg="white", fg=BRAND,
                             font=("Segoe UI", 9, "bold"))
        info.pack(fill="x", padx=22, pady=4)
        self.info_label = tk.Label(
            info, text="Select a session folder to begin.",
            bg="white", fg="gray", anchor="w", justify="left",
            wraplength=830, font=("Segoe UI", 9))
        self.info_label.pack(fill="x", padx=12, pady=8)

        opts = tk.LabelFrame(self._body, text=" Layout options ", bg="white",
                             fg=BRAND, font=("Segoe UI", 9, "bold"))
        opts.pack(fill="x", padx=22, pady=6)

        row1 = tk.Frame(opts, bg="white")
        row1.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(row1, text="Steps per column:", bg="white").pack(side="left")
        self.per_column = tk.Spinbox(row1, from_=3, to=30, width=5)
        self.per_column.pack(side="left", padx=(6, 22))
        self.per_column.delete(0, "end")
        self.per_column.insert(0, "5")
        tk.Label(row1, text="Resolution (dpi):", bg="white").pack(side="left")
        self.dpi = tk.Spinbox(row1, from_=96, to=300, increment=25, width=6)
        self.dpi.pack(side="left", padx=(6, 0))
        self.dpi.delete(0, "end")
        self.dpi.insert(0, "150")

        row2 = tk.Frame(opts, bg="white")
        row2.pack(fill="x", padx=12, pady=(2, 8))
        self.revisit_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row2,
                       text="Mark repeated activities as a return to the "
                            "earlier step",
                       variable=self.revisit_var, bg="white",
                       activebackground="white",
                       font=("Segoe UI", 9)).pack(side="left")

        tk.Button(self._body, text="REBUILD FLOWCHART", command=self.run,
                  bg=SUCCESS, fg="white", relief="flat",
                  font=("Segoe UI", 12, "bold"), width=28).pack(pady=12)

        table = tk.Frame(self._body, bg="white")
        table.pack(fill="both", expand=True, padx=22, pady=4)
        columns = ("Step", "Type", "Application", "Description", "Note")
        self.tree = ttk.Treeview(table, columns=columns,
                                 show="headings", height=12)
        widths = {"Step": 50, "Type": 85, "Application": 145,
                  "Description": 330, "Note": 190}
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=widths[column], anchor="w")
        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.status = tk.Label(self._body, text="", bg="white", fg="gray",
                               wraplength=840, justify="left")
        self.status.pack(pady=8)

    def initial(self):
        sessions = os.path.join(base_dir(), "sessions")
        return sessions if os.path.isdir(sessions) else base_dir()

    def select(self):
        path = filedialog.askdirectory(title="Select session folder",
                                       initialdir=self.initial())
        if not path:
            return
        self.session = path
        self.folder.config(text=os.path.basename(path), fg="black")

        try:
            self.steps = read_steps(path)
        except Exception as error:
            self.info_label.config(text=str(error), fg=ERROR)
            self.steps = []
            return

        revisits = mark_revisits(self.steps)
        suggested = suggest_columns(len(self.steps))
        per_column = max(3, math.ceil(len(self.steps) / suggested))
        self.per_column.delete(0, "end")
        self.per_column.insert(0, str(per_column))

        for item in self.tree.get_children():
            self.tree.delete(item)
        for step in self.steps:
            note = ""
            if step.get("revisit_of"):
                note = "Returns to step {}".format(step["revisit_of"])
            self.tree.insert("", "end", values=(
                step["number"], step["record_type"], step["application"],
                step["description"], note))

        self.info_label.config(
            text="{} step(s) found. {} repeat an earlier activity. "
                 "Suggested layout: {} column(s) of {} steps, which should "
                 "fit a single page.".format(
                     len(self.steps), revisits, suggested, per_column),
            fg=SUCCESS)

    def run(self):
        if not self.session or not self.steps:
            messagebox.showwarning(APP_TITLE,
                                   "Select a session folder first.")
            return
        if not GRAPHVIZ:
            messagebox.showerror(
                APP_TITLE,
                "The Python graphviz package is not installed.\n\n"
                "Run: python -m pip install graphviz\n\n"
                "The Graphviz desktop software is also required.")
            return

        try:
            per_column = max(2, int(self.per_column.get()))
        except ValueError:
            per_column = 5
        try:
            resolution = max(96, int(self.dpi.get()))
        except ValueError:
            resolution = 150

        ok, message, column_count = build_flowchart(
            self.session, self.steps, per_column,
            self.revisit_var.get(), resolution,
            os.path.basename(self.session))

        if not ok:
            self.status.config(text=message, fg=ERROR)
            messagebox.showerror(
                APP_TITLE,
                "The flowchart could not be created.\n\n{}\n\n"
                "Confirm the Graphviz desktop software is installed and "
                "that 'dot -V' works in Command Prompt.".format(message))
            return

        shape = describe_shape(self.session)

        summary = (
            "Flowchart rebuilt.\n\n"
            "Steps: {}\n"
            "Columns: {} of up to {} steps\n"
            "Resolution: {} dpi\n"
        ).format(len(self.steps), column_count, per_column, resolution)
        if shape:
            summary += "Image: {}\n".format(shape)
        summary += (
            "\nUpdated:\n- process_flow.png\n- process_flow.pdf\n\n"
            "Saved in:\n{}\n\n"
            "Next: rebuild the SOP so the new diagram is embedded.".format(
                self.session)
        )

        messagebox.showinfo(APP_TITLE, summary)
        self.status.config(
            text="Rebuilt in {} column(s). {}".format(column_count, shape),
            fg=SUCCESS)
        try:
            os.startfile(self.session)
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
