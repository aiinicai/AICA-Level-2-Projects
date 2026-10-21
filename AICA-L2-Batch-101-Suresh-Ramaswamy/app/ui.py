"""Tkinter desktop UI for CA GST Filing Assistant Pro.

Tabs:  1 Home | 2 Clients | 3 Return | 4 Master Template (download blank / upload filled - all GSTR-1 tables)
5 Invoices (Excel/PDF extraction) | 6 Invoice Review | 7 Classification | 8 Validation | 9 Documents (Table 13)
10 CSV Preview (every table) | 11 GSTR-1 Summary + reconciliation | 12 Export | 13 History | 14 Settings & Backup
The Excel Column Mapping screen opens automatically as a dialog when a sheet is not recognised.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
import webbrowser
from decimal import Decimal
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from . import config, gstr1, annual
from . import recon, returns as filed_returns, yearimport
from . import autofill
from . import hsn as hsn_mod
from .classifier import classify_all, is_implemented, reason_for
from .config import (STATE_CODES, REG_TYPES, RETURN_TYPES, INVOICE_TYPES, SECTIONS, APP_NAME, DOC_NATURES)
from .db import Database
from .exporters import (build_docs, derive_docs, read_docs_template, register_table13, write_docs_template, export_documents_only,
                        export_exception_report, export_issue_report, export_project, project_dir, summary_frame)
from .extractors.excel_reader import FIELD_LABELS, auto_map
from .gstin import validate_gstin
from .models import (Line, DocSeries, group_invoices, invoice_value, STATUS_APPROVED, STATUS_PENDING,
                     STATUS_REJECTED, STATUS_DUP)
from .schema import load_schema, save_schema, reset_schema, headers_status
from .services import (learn_hsn, remove_template_rows, register_file, extract_file, merge_lines, review_count, dashboard, file_type,
                      import_master_template, merge_docs, is_master_template)
from .utils import D, q2, ZERO as ZERO_D, parse_date, pos_label, fin_year, state_from_text
from .validation import validate_all, blocking_errors

log = logging.getLogger(__name__)

try:  # optional drag & drop
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _Base = TkinterDnD.Tk
    HAS_DND = True
except Exception:  # noqa
    _Base = tk.Tk
    HAS_DND = False

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]


# ------------------------------------------------------------------ widgets
def _sort_key(v):
    try:
        return (0, float(str(v).replace(",", "")))
    except ValueError:
        return (1, str(v).lower())


def sort_tree(tree, col, reverse=False):
    data = [(tree.set(i, col), i) for i in tree.get_children("")]
    data.sort(key=lambda t: _sort_key(t[0]), reverse=reverse)
    for n, (_, i) in enumerate(data):
        tree.move(i, "", n)
    tree.heading(col, command=lambda: sort_tree(tree, col, not reverse))


def make_tree(parent, cols, height=12):
    """cols = [(key, title, width)]. Returns (frame, tree)."""
    fr = ttk.Frame(parent)
    tree = ttk.Treeview(fr, columns=[c[0] for c in cols], show="headings", height=height, selectmode="extended")
    for key, title, w in cols:
        tree.heading(key, text=title, command=lambda k=key: sort_tree(tree, k))
        tree.column(key, width=w, anchor="w", stretch=True)
    ys = ttk.Scrollbar(fr, orient="vertical", command=tree.yview)
    xs = ttk.Scrollbar(fr, orient="horizontal", command=tree.xview)
    tree.configure(yscroll=ys.set, xscroll=xs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    ys.grid(row=0, column=1, sticky="ns")
    xs.grid(row=1, column=0, sticky="ew")
    fr.rowconfigure(0, weight=1)
    fr.columnconfigure(0, weight=1)
    def select_all(_e=None):
        tree.selection_set(tree.get_children(""))
        return "break"
    for seq in ("<Control-a>", "<Control-A>"):
        tree.bind(seq, select_all)
    tree.tag_configure("error", background="#ffd6d6")
    tree.tag_configure("warning", background="#fff3c4")
    tree.tag_configure("approved", background="#dff5df")
    tree.tag_configure("rejected", foreground="#888888")
    tree.tag_configure("dup", background="#ffe0b8")
    return fr, tree


def clear(tree):
    tree.delete(*tree.get_children())


def open_folder(path):
    path = str(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:  # noqa
        messagebox.showerror(APP_NAME, f"Cannot open folder:\n{e}")


class FormDialog(tk.Toplevel):
    """Generic modal form. fields = [(key, label, kind, choices)] kind: entry|combo|check."""

    def __init__(self, parent, title, fields, values, columns=2, extra_buttons=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.result = None
        self.vars = {}
        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)
        for n, (key, label, kind, choices) in enumerate(fields):
            r, c = divmod(n, columns)
            ttk.Label(body, text=label).grid(row=r, column=c * 2, sticky="e", padx=4, pady=3)
            if kind == "check":
                v = tk.BooleanVar(value=bool(values.get(key)))
                w = ttk.Checkbutton(body, variable=v)
            else:
                v = tk.StringVar(value=str(values.get(key, "")))
                w = (ttk.Combobox(body, textvariable=v, values=choices, width=30) if kind == "combo"
                     else ttk.Entry(body, textvariable=v, width=32))
            w.grid(row=r, column=c * 2 + 1, sticky="w", padx=4, pady=3)
            self.vars[key] = v
        bar = ttk.Frame(self, padding=(10, 0, 10, 10))
        bar.pack(fill="x")
        # extra_buttons = [(text, callback)]; the callback gets the current (unsaved) values of the form
        for text, cb in (extra_buttons or []):
            ttk.Button(bar, text=text, command=lambda cb=cb: cb({k: v.get() for k, v in self.vars.items()})
                       ).pack(side="left", padx=4)
        ttk.Button(bar, text="Save", command=self._ok).pack(side="right", padx=4)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.grab_set()
        self.wait_window(self)

    def _ok(self):
        self.result = {k: v.get() for k, v in self.vars.items()}
        self.destroy()


class MappingDialog(tk.Toplevel):
    """Excel Column Mapping screen: which column holds each item, plus values that are the same for every row."""

    FIXED = [
        ("invoice_type", "Invoice type", ["Regular", "SEZ supplies with payment", "SEZ supplies without payment",
                                          "Deemed Exp", "Intra-State supplies attracting IGST",
                                          "Export - with payment of tax", "Export - without payment of tax"]),
        ("rate", "GST rate % (whole file)", ["0", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40"]),
        ("note_type", "Credit / Debit note", ["Credit note", "Debit note"]),
        ("reverse_charge", "Reverse charge", ["No", "Yes"]),
        ("nil_kind", "Nil / Exempt / Non-GST", ["Nil Rated", "Exempted", "Non-GST"]),
        ("pos", "Place of supply", [f"{c}-{n}" for c, n in STATE_CODES.items()]),
    ]

    def __init__(self, parent, filename, entry):
        super().__init__(parent)
        self.title(f"Excel Column Mapping - {filename} / {entry['sheet']}")
        self.transient(parent)
        self.result = None
        cols = [""] + entry["columns"]
        self.TAG = "[All rows] "
        valued = {k: ch for k, _l, ch in self.FIXED if k in ("invoice_type", "reverse_charge", "note_type", "nil_kind")}
        guess = entry.get("mapping") or auto_map(entry["columns"])
        intro = ("Check which column of your file holds each item (the lists show YOUR column headings). Invoice number "
                 "and Taxable value are mandatory." if entry.get("mapping") else
                 "This sheet was not recognised automatically. Choose which column holds each item. Invoice number "
                 "and Taxable value are mandatory; map the rest where available.")
        ttk.Label(self, wraplength=900, padding=10, text=intro).pack()
        self.preview = entry.get("preview") or []
        self.hdr0 = entry.get("header_row", 0)
        self.hdr_var = tk.IntVar(value=self.hdr0 + 1)
        self.combos = []
        if self.preview:
            pf = ttk.LabelFrame(self, text="First rows of your sheet (so you can see what each column holds)", padding=4)
            pf.pack(fill="x", padx=10)
            self.ptext = tk.Text(pf, height=7, width=130, wrap="none", font=("Consolas", 9))
            self.ptext.pack(fill="x")
            self.ptext.configure(state="disabled")
            hb = ttk.Frame(pf)
            hb.pack(fill="x", pady=3)
            ttk.Label(hb, text="The column headings are on row:").pack(side="left")
            ttk.Spinbox(hb, from_=1, to=len(self.preview), width=4, textvariable=self.hdr_var,
                        command=self._hdr_changed).pack(side="left", padx=4)
            ttk.Label(hb, text="(change it if the headings are on a different row)").pack(side="left")
            self._draw_preview()
        body = ttk.Frame(self, padding=10)
        body.pack()
        self.vars = {}
        for n, (k, label) in enumerate(FIELD_LABELS.items()):
            v = tk.StringVar(value=guess.get(k, ""))
            star = " *" if k in ("invoice_no", "taxable") else ""
            ttk.Label(body, text=label + star).grid(row=n // 2, column=(n % 2) * 2, sticky="e", padx=4, pady=2)
            opts = ([""] + [self.TAG + c for c in valued[k]] + cols[1:]) if k in valued else cols
            cb = ttk.Combobox(body, textvariable=v, values=opts, width=26, state="readonly")
            cb.grid(row=n // 2, column=(n % 2) * 2 + 1, padx=4, pady=2)
            self.combos.append((k, cb))
            self.vars[k] = v
        box = ttk.LabelFrame(self, text="Same value for EVERY ROW - use it when your file has no such column "
                                        "(a column chosen above is used first; this fills the blanks)", padding=8)
        box.pack(fill="x", padx=10, pady=4)
        self.fixed = {}
        for n, (k, label, choices) in enumerate([x for x in self.FIXED if x[0] in ("rate", "pos")]):
            v = tk.StringVar(value="")
            ttk.Label(box, text=label).grid(row=n // 2, column=(n % 2) * 2, sticky="e", padx=4, pady=3)
            ttk.Combobox(box, textvariable=v, values=[""] + choices, width=34,
                         state="normal" if k == "rate" else "readonly").grid(row=n // 2, column=(n % 2) * 2 + 1, padx=4)
            self.fixed[k] = v
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Use this mapping", command=self._ok).pack(side="right", padx=4)
        ttk.Button(bar, text="Skip file", command=self.destroy).pack(side="right")
        self.grab_set()
        self.wait_window(self)

    def _draw_preview(self):
        from .extractors.excel_reader import col_letter
        w = max((len(r) for r in self.preview), default=0)
        lines = ["     " + " | ".join(f"{col_letter(i):<12}" for i in range(w))]
        for n, r in enumerate(self.preview, 1):
            mark = ">" if n == self.hdr_var.get() else " "
            lines.append(f"{mark}{n:>3} " + " | ".join(f"{(r[i] if i < len(r) else '')[:12]:<12}" for i in range(w)))
        self.ptext.configure(state="normal")
        self.ptext.delete("1.0", "end")
        self.ptext.insert("1.0", "\n".join(lines))
        self.ptext.configure(state="disabled")

    def _hdr_changed(self):
        """New heading row: rebuild every column list from that row."""
        from .extractors.excel_reader import make_headers
        try:
            row = self.preview[int(self.hdr_var.get()) - 1]
        except (ValueError, IndexError, tk.TclError):
            return
        self.cols = [""] + make_headers(row)
        for k, cb in self.combos:
            pre = [x for x in cb.cget("values") if str(x).startswith(self.TAG)]
            cb.configure(values=[""] + pre + self.cols[1:])
        for v in self.vars.values():
            if not v.get().startswith(self.TAG):
                v.set("")
        self._draw_preview()

    def _ok(self):
        m = {k: v.get() for k, v in self.vars.items() if v.get() and not v.get().startswith(self.TAG)}
        picked = {k: v.get()[len(self.TAG):] for k, v in self.vars.items() if v.get().startswith(self.TAG)}
        if "invoice_no" not in m or "taxable" not in m:
            messagebox.showwarning(APP_NAME, "Invoice number and Taxable value must be mapped.", parent=self)
            return
        fx = {k: v.get().strip() for k, v in self.fixed.items() if v.get().strip()}
        fx.update(picked)
        if "rate" in fx and D(fx["rate"], None) is None:
            messagebox.showwarning(APP_NAME, "GST rate must be a number such as 18.", parent=self)
            return
        if fx:
            m["__fixed"] = fx
        if self.preview and self.hdr_var.get() - 1 != self.hdr0:
            m["__header_row"] = int(self.hdr_var.get()) - 1
        self.result = m
        self.destroy()


# ------------------------------------------------------------------ main app
class YearImportDialog(tk.Toplevel):
    """Preview of a whole-year upload: what each file is and which month it goes to. Nothing is imported until
    Import is clicked; files can be left out and the month can be changed."""

    def __init__(self, parent, fy, entries, client):
        super().__init__(parent)
        self.title(f"Upload whole year - FY {fy} - {client['name']}")
        self.transient(parent)
        self.result = None
        self.entries = entries
        self.fy = fy
        s = int(fy[:4])
        self.month_choices = [yearimport.month_label(m, s if m >= 4 else s + 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]
        ttk.Label(self, padding=(10, 8), wraplength=1000, text=(
            "Check the list: each file goes to the month shown (a register covering several months is split by invoice "
            "date). Missing month returns are created. Select rows and use the buttons to leave a file out or change "
            "its month. Filed GSTR-1 / 3B / 9 PDFs go to the reconciliation.")).pack(anchor="w")
        fr, self.tree = make_tree(self, [("inc", "Import", 60), ("file", "File", 330), ("kind", "Type", 170),
                                         ("mon", "Month(s)", 200), ("note", "Note", 420)], height=18)
        fr.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", lambda e: self.set_month())
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Include / leave out selected", command=self.toggle).pack(side="left", padx=3)
        ttk.Label(bar, text="Month for selected:").pack(side="left", padx=(12, 3))
        self.mvar = tk.StringVar(value=self.month_choices[0])
        ttk.Combobox(bar, textvariable=self.mvar, values=self.month_choices, width=10, state="readonly").pack(side="left")
        ttk.Button(bar, text="Set month", command=self.set_month).pack(side="left", padx=3)
        self.approve = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Approve lines without errors after import", variable=self.approve).pack(side="left", padx=12)
        ttk.Button(bar, text="Import", command=self._ok).pack(side="right", padx=4)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.info = tk.StringVar()
        ttk.Label(self, textvariable=self.info, padding=(10, 0, 10, 8), foreground="#1F3864").pack(anchor="w")
        self.fill()
        self.grab_set()
        self.wait_window(self)

    def fill(self):
        clear(self.tree)
        for i, e in enumerate(self.entries):
            mon = ", ".join(yearimport.month_label(*m) for m in e["months"])
            if e["kind"] == "GSTR9" and e.get("doc"):
                mon = f"FY {e['doc'].get('fy') or self.fy}"
            tag = ("approved",) if e["include"] else ("rejected",)
            if e["include"] and e["note"]:
                tag = ("warning",)
            self.tree.insert("", "end", iid=str(i), tags=tag, values=(
                "Yes" if e["include"] else "No", e["name"], yearimport.KIND_LABEL.get(e["kind"], e["kind"]), mon, e["note"]))
        n = sum(1 for e in self.entries if e["include"])
        self.info.set(f"{len(self.entries)} file(s) found, {n} will be imported.")

    def toggle(self):
        for iid in self.tree.selection():
            e = self.entries[int(iid)]
            if e["kind"] == "skip":
                continue
            e["include"] = not e["include"] and bool(e["months"])
        self.fill()

    def set_month(self):
        mm = yearimport.parse_month_label(self.mvar.get())
        if not mm:
            return
        for iid in self.tree.selection():
            e = self.entries[int(iid)]
            if e["kind"] == "skip":
                continue
            e["months"] = [mm]
            e["include"] = True
            e["note"] = "Month set by you"
        self.fill()

    def _ok(self):
        self.result = [e for e in self.entries if e["include"] and e["months"]]
        self.approve_clean = bool(self.approve.get())
        self.destroy()


class App(_Base):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Pro  -  GSTR-1 utility")
        self.geometry("1280x760")
        self.minsize(1000, 640)
        self.db = Database()
        self.settings = self.db.get_settings()
        self.schema = load_schema()
        self.client = None
        self.project = None
        self.lines = []
        self.docs = []
        self.sets = []
        self.force_map = set()
        self.docs_lock = False       # True after staff deleted series: do not rebuild them silently
        self.last_upload_issues = []
        self.issues = []
        self.issue_by_line = {}
        self.last_export = None
        ttk.Style(self).theme_use("clam")
        ttk.Style(self).configure("Head.TLabel", font=("Segoe UI", 13, "bold"))
        ttk.Style(self).configure("Warn.TLabel", foreground="#b00020")
        # compact tab strip so all 15 tab names fit on one row
        ttk.Style(self).configure("TNotebook.Tab", padding=(5, 3), font=("Segoe UI", 8))

        self.banner = tk.StringVar(value="No return open - create a client, then a return (tabs 2 and 3).")
        ttk.Label(self, textvariable=self.banner, anchor="w", padding=(10, 6), background="#1f3a5f",
                  foreground="white", font=("Segoe UI", 10, "bold")).pack(fill="x")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.status = tk.StringVar(value="Ready. All processing is local on this computer.")
        ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken", padding=3).pack(fill="x")

        self._tab_home()
        self._tab_clients()
        self._tab_project()
        self._tab_master()
        self._tab_upload()
        self._tab_review()
        self._tab_classification()
        self._tab_validation()
        self._tab_documents()
        self._tab_previews()
        self._tab_summary()
        self._tab_export()
        self._tab_history()
        self._tab_settings()
        self._tab_annual()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_current())
        self.refresh_clients()
        self._schema_label()

    # ---------------------------------------------------------- helpers
    TAB_HELP = {
        "1 Home": "Overview of the open return: counts, status and what to do next.",
        "2 Clients": "Create, save or delete clients. Select a client, then click 'Use for Return'.",
        "3 Return": "Create a return for one month - or for the whole financial year in one click - and open it.",
        "4 Master Template": "One Excel file for every GSTR-1 table: download the blank template, upload it when the client has filled it.",
        "5 Invoices (Excel/PDF)": "Upload the client's Excel registers, summary reports, PDF or scanned invoices and click Extract Data.",
        "6 Invoice Review": "WORK on the extracted invoice lines: search, correct, then Approve or Reject. Only approved lines go into GSTR-1.",
        "7 Classification": "See which GSTR-1 table each invoice goes to (B2B, B2CL, B2CS, notes ...) and change it if needed.",
        "8 Validation": "CHECK the whole return: every error and warning, plus the reconciliation. Double-click a problem to go to its line.",
        "9 Documents": "Document series for Table 13 (invoices, notes issued, cancelled) - check gaps and numbers.",
        "10 CSV Preview": "Exactly what will be written to each CSV file for the GST Offline Tool.",
        "11 GSTR-1 Summary": "Totals by table and the reconciliation - compare with the Offline Tool summary before filing.",
        "12 Export": "Generate the CSV files for the Offline Tool, and the reports.",
        "13 History": "Audit trail: what was done on this return, and when.",
        "14 Settings": "Preferences, GST rate slabs, backup and restore, and the Offline Tool header comparison.",
        "15 YTD & Annual": "Upload a whole year, then compare books, GSTR-1, GSTR-3B, GSTR-9 and GSTR-9C. Double-click a row for the reason and the remedy.",
    }

    def tab(self, title):
        outer = ttk.Frame(self.nb)
        self.nb.add(outer, text=title)
        help_text = self.TAB_HELP.get(title, "")
        if help_text:
            ttk.Label(outer, text="What this tab is for:  " + help_text, foreground="#1F3864", background="#E8EEF7",
                      padding=(8, 4), wraplength=1500, justify="left").pack(fill="x", padx=8, pady=(6, 0))
        f = ttk.Frame(outer, padding=8)
        f.pack(fill="both", expand=True)
        return f

    def goto(self, name):
        """Select a tab by its name (the part after the number)."""
        for i, t in enumerate(self.nb.tabs()):
            if self.nb.tab(t, "text").split(" ", 1)[-1].startswith(name):
                self.nb.select(i)
                return

    def need_project(self) -> bool:
        if not self.project:
            messagebox.showinfo(APP_NAME, "Open or create a return first (tabs 2 and 3).")
            return False
        return True

    def set_status(self, msg):
        self.status.set(msg)
        self.update_idletasks()

    def persist(self):
        if self.project:
            self.db.save_lines(self.project["id"], self.lines)
            self.db.save_docs(self.project["id"], self.docs)

    def run_checks(self, save=True):
        if not self.project:
            return
        classify_all(self.lines, self.settings)
        if hasattr(self, "doc_gaps") and not self.docs_lock and not any(
                d.origin in ("register", "manual", "verified") for d in self.docs):
            self._auto_series()                      # suggested series follow the invoices, even before the Documents tab is opened
        period = (self.project["month"], self.project["year"])
        self.issues = validate_all(self.lines, self.client, self.docs, self.settings, period)
        ctx = gstr1.make_ctx(self.client, self.project, self.settings, self.schema)
        self.issues += gstr1.validate_sets(self.sets, self.lines, ctx)
        self.issue_by_line = {}
        for i in self.issues:
            if i.line_id:
                self.issue_by_line.setdefault(i.line_id, []).append(i)
        if save:
            self.persist()

    def refresh_current(self):
        name = self.nb.tab(self.nb.select(), "text").split(" ", 1)[-1]
        fn = {"Home": self.refresh_home, "Master Template": self.refresh_master, "Invoices (Excel/PDF)": self.refresh_files,
              "Invoice Review": self.refresh_review, "Classification": self.refresh_class,
              "Validation": self.refresh_validation, "Documents": self.refresh_documents,
              "CSV Preview": self.refresh_previews, "GSTR-1 Summary": self.refresh_summary,
              "History": self.refresh_history,
              "YTD & Annual": self.refresh_annual}.get(name)
        if fn:
            fn()

    # ---------------------------------------------------------- 1 Home
    def _tab_home(self):
        f = self.tab("1 Home")
        ttk.Label(f, text="Home Dashboard", style="Head.TLabel").pack(anchor="w")
        nb = ttk.Frame(f)
        nb.pack(fill="x", pady=(6, 0))
        self.next_var = tk.StringVar(value="")
        self.next_tab = "Clients"
        ttk.Label(nb, text="NEXT STEP:", font=("Segoe UI", 10, "bold"), foreground="#0b5394").pack(side="left")
        ttk.Label(nb, textvariable=self.next_var, foreground="#0b5394", wraplength=900).pack(side="left", padx=6)
        ttk.Button(nb, text="Go there", command=lambda: self.goto(self.next_tab)).pack(side="left", padx=6)
        self.home_vars = {}
        grid = ttk.Frame(f)
        grid.pack(anchor="w", pady=10)
        items = [("client", "Client"), ("gstin", "GSTIN"), ("period", "Return period"), ("files", "Source files"),
                 ("invoices", "Invoices extracted"), ("approved", "Invoices approved"),
                 ("to_review", "Invoices needing review"), ("taxable", "Total taxable value"),
                 ("igst", "IGST"), ("cgst", "CGST"), ("sgst", "SGST/UTGST"), ("cess", "Cess"),
                 ("b2b", "B2B invoices / value"), ("errors", "Errors"), ("warnings", "Warnings"),
                 ("tpl", "Master template rows imported"), ("csv", "CSV generation status")]
        for n, (k, label) in enumerate(items):
            r, c = divmod(n, 2)
            ttk.Label(grid, text=label + ":", font=("Segoe UI", 10, "bold")).grid(row=r, column=c * 2, sticky="e",
                                                                                    padx=8, pady=3)
            v = tk.StringVar(value="-")
            ttk.Label(grid, textvariable=v, width=34).grid(row=r, column=c * 2 + 1, sticky="w")
            self.home_vars[k] = v
        # the button row is packed first (at the bottom) so it always keeps its space; the table takes what is left
        bar = ttk.Frame(f)
        bar.pack(side="bottom", anchor="w", pady=8)
        ttk.Button(bar, text="New Client", command=lambda: self.goto("Clients")).pack(side="left", padx=3)
        ttk.Button(bar, text="New Return", command=lambda: self.goto("Return")).pack(side="left", padx=3)
        ttk.Button(bar, text="Review Errors", command=self.review_errors).pack(side="left", padx=3)
        ttk.Button(bar, text="Refresh", command=self.refresh_home).pack(side="left", padx=3)
        ttk.Label(f, text="GSTR-1 tables prepared so far (approved invoice lines + Master Template)", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        fr, self.home_sections = make_tree(f, [("s", "GSTR-1 table", 360), ("n", "Rows", 80), ("d", "Documents", 90),
                                               ("v", "Taxable value", 140), ("t", "Total incl. tax", 140)], height=5)
        fr.pack(fill="both", expand=True)

    def next_step(self):
        """(what to do next, tab to open) from the state of the open return."""
        if not self.client:
            return "Create the client (name and GSTIN).", "Clients"
        if not self.project:
            return "Create or open the GSTR-1 return for the month.", "Return"
        files = self.db.files(self.project["id"])
        if not self.sets and not self.lines and not files:
            return "Upload the client's filled Master Template or the invoice / sales register files.", "Master Template"
        if any(f["status"] == "Queued" for f in files):
            return "Click 'Extract Data' to read the uploaded invoice files.", "Invoices"
        pend = [l for l in self.lines if l.review_status in (STATUS_PENDING, STATUS_DUP)]
        if pend:
            return (f"Review the invoice lines ({len(pend)} pending): set the GST rate / HSN, fix errors, then "
                    "'Approve all without errors'."), "Invoice Review"
        errs = [i for i in self.issues if i.severity == "Error"]
        if errs:
            return f"Fix the {len(errs)} error(s) - or delete the rows that are wrong.", "Validation"
        if not self.docs:
            return "Prepare the document series (Table 13) - 'Build series from invoices'.", "Documents"
        return "Everything is ready: generate the CSV files and import them in the GST Offline Tool.", "Export"

    def refresh_home(self):
        v = self.home_vars
        clear(self.home_sections)
        self.next_var.set(self.next_step()[0])
        self.next_tab = self.next_step()[1]
        if not self.project:
            for k in v:
                v[k].set("-")
            return
        files = self.db.files(self.project["id"])
        d = dashboard(self.lines, self.issues, files, self.project)
        v["client"].set(self.client["name"])
        v["gstin"].set(self.client["gstin"])
        v["period"].set(f"{MONTH_NAMES[self.project['month'] - 1]} {self.project['year']} (FY {self.project['fy']})")
        v["files"].set(d["files"])
        v["invoices"].set(d["invoices"])
        v["approved"].set(d["approved"])
        v["to_review"].set(d["to_review"])
        for k in ("taxable", "igst", "cgst", "sgst", "cess"):
            v[k].set(f"{q2(d[k]):,}")
        v["b2b"].set(f"{d['b2b_count']}  /  {q2(d['b2b_value']):,}")
        v["errors"].set(d["errors"])
        v["warnings"].set(d["warnings"])
        v["csv"].set(d["csv_status"])
        v["tpl"].set(sum(len(rows) for ds in self.sets for rows in ds["tables"].values()))
        out = self.compute_outputs()
        for sm in out["summary"]:
            self.home_sections.insert("", "end", values=(sm["title"], sm["rows"], sm["docs"], f"{sm['taxable']:,.2f}",
                                                         f"{sm['total']:,.2f}"))

    def review_errors(self):
        if not self.need_project():
            return
        self.f_sev.set("Error")
        self.goto("Invoice Review")
        self.refresh_review()

    # ---------------------------------------------------------- 2 Clients
    def _tab_clients(self):
        f = self.tab("2 Clients")
        ttk.Label(f, text="Client Master", style="Head.TLabel").pack(anchor="w")
        top = ttk.Frame(f)
        top.pack(fill="both", expand=True)
        left = ttk.Frame(top)
        left.pack(side="left", fill="both", expand=True)
        fr, self.client_tree = make_tree(left, [("name", "Client", 220), ("gstin", "GSTIN", 150),
                                                ("state", "State", 130), ("reg", "Registration", 90)], height=14)
        fr.pack(fill="both", expand=True)
        self.client_tree.bind("<<TreeviewSelect>>", lambda e: self.load_client_form())
        right = ttk.LabelFrame(top, text="Client details", padding=10)
        right.pack(side="left", fill="y", padx=10)
        self.cv = {k: tk.StringVar() for k in ("id", "name", "gstin", "legal_name", "trade_name", "state_code",
                                              "reg_type", "return_type")}
        rows = [("name", "Client name *"), ("gstin", "GSTIN *"), ("legal_name", "Legal name"),
                ("trade_name", "Trade name"), ("state_code", "Registered state"), ("reg_type", "Registration type"),
                ("return_type", "Return type")]
        for n, (k, label) in enumerate(rows):
            ttk.Label(right, text=label).grid(row=n, column=0, sticky="e", pady=3, padx=4)
            if k == "state_code":
                w = ttk.Combobox(right, textvariable=self.cv[k], width=34, state="readonly",
                                 values=[f"{c}-{n_}" for c, n_ in STATE_CODES.items()])
            elif k == "reg_type":
                w = ttk.Combobox(right, textvariable=self.cv[k], width=34, state="readonly", values=REG_TYPES)
            elif k == "return_type":
                w = ttk.Combobox(right, textvariable=self.cv[k], width=34, state="readonly", values=RETURN_TYPES)
            else:
                w = ttk.Entry(right, textvariable=self.cv[k], width=37)
            w.grid(row=n, column=1, pady=3)
        self.gstin_msg = tk.StringVar()
        ttk.Label(right, textvariable=self.gstin_msg, wraplength=300, foreground="#444").grid(
            row=len(rows), column=0, columnspan=2, pady=4)
        ttk.Label(right, wraplength=300, foreground="#666",
                  text="GSTIN validation checks structure, state code and check digit only. It does not prove "
                       "that the registration is active.").grid(row=len(rows) + 1, column=0, columnspan=2)
        bar = ttk.Frame(right)
        bar.grid(row=len(rows) + 2, column=0, columnspan=2, pady=8)
        ttk.Button(bar, text="New Client", command=self.new_client).pack(side="left", padx=3)
        ttk.Button(bar, text="Save Client", command=self.save_client).pack(side="left", padx=3)
        ttk.Button(bar, text="Use for Return >", command=lambda: self.goto("Return")).pack(side="left", padx=3)
        ttk.Button(right, text="Delete client and all its data", command=self.delete_client).grid(
            row=len(rows) + 3, column=0, columnspan=2)

    def refresh_clients(self):
        clear(self.client_tree)
        self.client_rows = self.db.clients()
        for c in self.client_rows:
            self.client_tree.insert("", "end", iid=str(c["id"]), values=(
                c["name"], c["gstin"], STATE_CODES.get(c["state_code"], c["state_code"]), c["reg_type"]))
        if hasattr(self, "proj_client"):
            self.proj_client["values"] = [f"{c['name']} ({c['gstin']})" for c in self.client_rows]

    def new_client(self):
        for k, v in self.cv.items():
            v.set("")
        self.cv["reg_type"].set(REG_TYPES[0])
        self.cv["return_type"].set(RETURN_TYPES[0])
        self.gstin_msg.set("")

    def load_client_form(self):
        sel = self.client_tree.selection()
        if not sel:
            return
        c = next(x for x in self.client_rows if str(x["id"]) == sel[0])
        for k in self.cv:
            self.cv[k].set(c.get(k) if k != "state_code" else
                           f"{c['state_code']}-{STATE_CODES.get(c['state_code'], '')}")
        self.gstin_msg.set(validate_gstin(c["gstin"])[1])

    def save_client(self):
        g = self.cv["gstin"].get().strip().upper()
        name = self.cv["name"].get().strip()
        if not name:
            messagebox.showwarning(APP_NAME, "Client name is required.")
            return
        lvl, msg = validate_gstin(g)
        self.gstin_msg.set(msg)
        if lvl == "error":
            messagebox.showerror(APP_NAME, f"GSTIN problem: {msg}")
            return
        if lvl == "warn" and not messagebox.askyesno(APP_NAME, f"{msg}\n\nSave anyway?"):
            return
        data = {k: v.get().strip() for k, v in self.cv.items()}
        data["gstin"] = g
        data["state_code"] = g[:2]
        data["id"] = int(data["id"]) if data["id"] else None
        try:
            cid = self.db.save_client(data)
        except Exception as e:  # noqa
            messagebox.showerror(APP_NAME, f"Could not save client (duplicate GSTIN?):\n{e}")
            return
        self.cv["id"].set(str(cid))
        self.refresh_clients()
        self.client_tree.selection_set(str(cid))
        self.set_status(f"Client saved: {name}")

    def delete_client(self):
        cid = self.cv["id"].get()
        if not cid:
            return
        if not messagebox.askyesno(APP_NAME, "Permanently delete this client, all returns, extracted data, "
                                   "audit trail and stored source files from this computer?\n\n"
                                   "Generated output in other folders is not touched.", icon="warning"):
            return
        gstin = self.cv["gstin"].get()
        self.db.delete_client_data(int(cid))
        shutil.rmtree(config.CLIENTS_DIR / gstin, ignore_errors=True)
        if self.client and self.client["id"] == int(cid):
            self.client = self.project = None
            self.lines, self.docs, self.issues, self.sets = [], [], [], []
            self.banner.set("No return open.")
        self.new_client()
        self.refresh_clients()

    # ---------------------------------------------------------- 3 Project
    def _tab_project(self):
        f = self.tab("3 Return")
        ttk.Label(f, text="Create / Open GST Return Project (GSTR-1)", style="Head.TLabel").pack(anchor="w")
        form = ttk.Frame(f)
        form.pack(anchor="w", pady=10)
        self.proj_client = ttk.Combobox(form, width=50, state="readonly")
        self.proj_client.grid(row=0, column=1, pady=4)
        ttk.Label(form, text="Client").grid(row=0, column=0, sticky="e", padx=4)
        import datetime as dt
        today = dt.date.today()
        prev = today.replace(day=1) - dt.timedelta(days=1)
        self.pm = tk.StringVar(value=MONTH_NAMES[prev.month - 1])
        self.py = tk.StringVar(value=str(prev.year))
        self.pf = tk.StringVar(value=RETURN_TYPES[0])
        ttk.Label(form, text="Month").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Combobox(form, textvariable=self.pm, values=MONTH_NAMES, state="readonly", width=20).grid(
            row=1, column=1, sticky="w", pady=4)
        ttk.Label(form, text="Year").grid(row=2, column=0, sticky="e", padx=4)
        ttk.Spinbox(form, textvariable=self.py, from_=2017, to=2100, width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="Filing frequency").grid(row=3, column=0, sticky="e", padx=4)
        ttk.Combobox(form, textvariable=self.pf, values=RETURN_TYPES, state="readonly", width=20).grid(
            row=3, column=1, sticky="w", pady=4)
        ttk.Label(form, text="Financial year").grid(row=4, column=0, sticky="e", padx=4)
        self.pfy = tk.StringVar(value=fin_year(prev.month, prev.year))
        ttk.Entry(form, textvariable=self.pfy, width=10).grid(row=4, column=1, sticky="w", pady=4)
        bar = ttk.Frame(f)
        bar.pack(anchor="w")
        ttk.Button(bar, text="New Return", command=self.new_return).pack(side="left", padx=3)
        ttk.Button(bar, text="Create ALL returns of the financial year (Apr-Mar)", command=self.new_fy_returns).pack(
            side="left", padx=3)
        ttk.Button(bar, text="Open selected return", command=self.open_selected_return).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete selected return(s)", command=self.delete_selected_returns).pack(side="left", padx=3)
        ttk.Label(f, text="Existing returns for the selected client").pack(anchor="w", pady=(14, 2))
        fr, self.proj_tree = make_tree(f, [("period", "Period", 160), ("fy", "Financial year", 120),
                                           ("status", "CSV status", 220), ("created", "Created", 160)], height=8)
        fr.pack(fill="x")
        self.proj_tree.bind("<Double-1>", lambda e: self.open_selected_return())
        self.proj_client.bind("<<ComboboxSelected>>", lambda e: self.refresh_projects())

    def _selected_client(self):
        i = self.proj_client.current()
        return self.client_rows[i] if i >= 0 else None

    def refresh_projects(self):
        clear(self.proj_tree)
        c = self._selected_client()
        if not c:
            return
        for p in self.db.projects(c["id"]):
            self.proj_tree.insert("", "end", iid=str(p["id"]), values=(
                f"{MONTH_NAMES[p['month'] - 1]} {p['year']}", p["fy"], p["csv_status"], p["created"]))

    def new_return(self):
        c = self._selected_client()
        if not c:
            sel = self.client_tree.selection()
            if sel:
                self.proj_client.current([str(x["id"]) for x in self.client_rows].index(sel[0]))
                c = self._selected_client()
        if not c:
            messagebox.showinfo(APP_NAME, "Select a client first (create one in tab 2).")
            return
        month = MONTH_NAMES.index(self.pm.get()) + 1
        year = int(self.py.get())
        pid = self.db.create_project(c["id"], fin_year(month, year), month, year, self.pf.get(),
                                     load_schema()["schema_version"])
        self.refresh_projects()
        self.open_project(c, pid)

    def new_fy_returns(self):
        """One click: create every return of a financial year (12 months, or the 4 quarter-end months for QRMP)."""
        c = self._selected_client()
        if not c:
            sel = self.client_tree.selection()
            if sel:
                self.proj_client.current([str(x["id"]) for x in self.client_rows].index(sel[0]))
                c = self._selected_client()
        if not c:
            messagebox.showinfo(APP_NAME, "Select a client first (create one in tab 2).")
            return
        fy = self.pfy.get().strip()
        m = re.fullmatch(r"(20\d\d)-(\d\d)", fy)
        if not m or int(m.group(2)) != (int(m.group(1)) + 1) % 100:
            messagebox.showwarning(APP_NAME, "Type the financial year like 2025-26.")
            return
        start = int(m.group(1))
        months = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
        if self.pf.get().lower().startswith("quarterly"):
            months = [6, 9, 12, 3]
        have = {(p["month"], p["year"]) for p in self.db.projects(c["id"])}
        made = 0
        ver = load_schema()["schema_version"]
        for mo in months:
            yr = start if mo >= 4 else start + 1
            if (mo, yr) not in have:
                self.db.create_project(c["id"], fy, mo, yr, self.pf.get(), ver)
                made += 1
        self.refresh_projects()
        self.set_status(f"FY {fy}: {made} return(s) created, {len(months) - made} already existed. Open each month from the list "
                        "below and upload its files; tab 15 shows the whole year.")
        messagebox.showinfo(APP_NAME, f"FY {fy}: {made} new return(s) created for {c['name']} "
                                      f"({len(months) - made} already existed).")

    def open_selected_return(self):
        c = self._selected_client()
        sel = self.proj_tree.selection()
        if not c or not sel:
            messagebox.showinfo(APP_NAME, "Select a client and a return from the list.")
            return
        self.open_project(c, int(sel[0]))

    def delete_selected_returns(self):
        """Delete one or more returns of the selected client with everything uploaded to them (invoice files, template
        data, extracted lines, document register, audit trail). Files already generated in the output folder stay."""
        c = self._selected_client()
        sel = [int(x) for x in self.proj_tree.selection()]
        if not c or not sel:
            messagebox.showinfo(APP_NAME, "Select the return(s) to delete in the list (Ctrl+A selects all).")
            return
        names = []
        for pid in sel:
            p = self.db.get_project(pid)
            names.append(f"{MONTH_NAMES[p['month'] - 1]} {p['year']}")
        if not messagebox.askyesno(APP_NAME, f"Permanently delete {len(sel)} return(s) of {c['name']}?\n\n"
                                   f"{', '.join(names)}\n\nThis removes the uploaded invoice files and templates, extracted "
                                   "lines, document register and history of those returns. CSV files already generated in "
                                   "your output folder are NOT deleted.", icon="warning"):
            return
        for pid in sel:
            p = self.db.get_project(pid)
            root = project_dir(c, p)
            for sub in ("source_files", "extracted_data", "review_reports"):
                shutil.rmtree(root / sub, ignore_errors=True)
            self.db.delete_project_data(pid, keep_project=False)
            if self.project and self.project["id"] == pid:
                self.project, self.lines, self.docs, self.sets, self.issues = None, [], [], [], []
                self.last_upload_issues = []
                self.banner.set("No return open.")
        self.refresh_projects()
        self.set_status(f"{len(sel)} return(s) deleted.")

    def open_project(self, client, pid):
        self.client = client
        self.project = self.db.get_project(pid)
        self.lines = self.db.load_lines(pid)
        self.docs = self.db.load_docs(pid)
        self.sets = self.db.datasets(pid)
        self.last_upload_issues = []
        self.banner.set(f"{client['name']}   |   {client['gstin']}   |   GSTR-1 "
                        f"{MONTH_NAMES[self.project['month'] - 1]} {self.project['year']}   "
                        f"(FY {self.project['fy']})")
        self.run_checks(save=False)
        self.db.audit(pid, "Return opened", "")
        self.goto("Master Template")
        self.set_status("Return opened. Next: download the Master Template, or upload Excel/PDF invoice files.")

    # ---------------------------------------------------------- 4 Upload
    def _tab_upload(self):
        f = self.tab("5 Invoices (Excel/PDF)")
        ttk.Label(f, text="Invoice files (Excel sales registers / PDF invoices) - upload and extraction results", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(anchor="w", pady=6)
        ttk.Button(bar, text="Upload Files", command=self.browse_files).pack(side="left", padx=3)
        ttk.Button(bar, text="Extract Data", command=self.extract_data).pack(side="left", padx=3)
        ttk.Button(bar, text="Re-extract selected", command=self.reextract_selected).pack(side="left", padx=3)
        ttk.Button(bar, text="Map columns / same value for all rows...", command=self.map_selected).pack(side="left", padx=3)
        ttk.Button(bar, text="Remove selected file", command=self.remove_selected_file).pack(side="left", padx=3)
        ttk.Label(bar, text=("   Drag & drop files onto the table is enabled." if HAS_DND else
                             "   (Install 'tkinterdnd2' to enable drag & drop.)")).pack(side="left")
        fr, self.file_tree = make_tree(f, [("file", "File", 260), ("type", "Type", 70), ("status", "Status", 150),
                                           ("rec", "Records", 70), ("rev", "Need review", 90),
                                           ("msg", "Messages / errors", 560)], height=16)
        fr.pack(fill="both", expand=True)
        self.file_tree.bind("<Control-a>", lambda e: (self.file_tree.selection_set(self.file_tree.get_children()), "break")[1])
        self.file_tree.bind("<Delete>", lambda e: self.remove_selected_file())
        self.progress = ttk.Progressbar(f, mode="determinate")
        self.progress.pack(fill="x", pady=4)
        if HAS_DND:
            self.file_tree.drop_target_register(DND_FILES)
            self.file_tree.dnd_bind("<<Drop>>", lambda e: self.add_files(list(self.tk.splitlist(e.data))))

    def refresh_files(self):
        clear(self.file_tree)
        if not self.project:
            return
        for r in self.db.files(self.project["id"]):
            self.file_tree.insert("", "end", iid=str(r["id"]), values=(
                r["filename"], r["ftype"], r["status"], r["records"], r["review_count"], r["message"] or ""))

    def browse_files(self):
        if not self.need_project():
            return
        paths = filedialog.askopenfilenames(title="Select sales invoices / registers", filetypes=[
            ("Excel, CSV and PDF", "*.xlsx *.xlsm *.xls *.csv *.pdf"), ("All files", "*.*")])
        if paths:
            self.add_files(list(paths))

    def add_files(self, paths):
        if not self.need_project():
            return
        msgs = []
        for p in paths:
            if is_master_template(Path(p)):
                msgs.append(f"{Path(p).name}: this is a GSTR-1 Master Template - upload it in the 'Master Template' tab.")
                continue
            fid, msg = register_file(self.db, self.client, self.project, Path(p))
            if not fid:
                msgs.append(msg)
        self.refresh_files()
        if msgs:
            messagebox.showinfo(APP_NAME, "\n".join(msgs))
        self.set_status("Files added. Click 'Extract Data'.")

    def extract_data(self, only_ids=None):
        if not self.need_project():
            return
        files = [f for f in self.db.files(self.project["id"])
                 if (f["id"] in only_ids if only_ids else f["status"] == "Queued")]
        if not files:
            messagebox.showinfo(APP_NAME, "No queued files. Upload files first.")
            return
        self.progress["maximum"] = len(files)
        self.progress["value"] = 0
        self._extract_step(files, 0)

    def _extract_step(self, files, i):
        if i >= len(files):
            self.run_checks()
            self.refresh_files()
            self.set_status(f"Extraction finished for {len(files)} file(s). Review the data in the Invoice Review tab.")
            self.goto("Invoice Review")
            return
        f = files[i]
        self.set_status(f"Extracting {f['filename']} ({i + 1}/{len(files)}) ... scanned files can take a minute each")
        self.update_idletasks()
        try:
            res = extract_file(self.db, self.client, self.project, f["id"], self.settings)
            entry = res.needs_mapping[0] if res.needs_mapping else (
                res.sheets[0] if f["id"] in self.force_map and res.sheets else None)
            self.force_map.discard(f["id"])
            if entry:
                dlg = MappingDialog(self, f["filename"], entry)
                if dlg.result:
                    res = extract_file(self.db, self.client, self.project, f["id"], self.settings, dlg.result)
            self.lines = [l for l in self.lines if l.source_file != f["filename"]]
            if res.tables or res.docs:                      # summary report (HSN report / output register)
                self.sets = self.db.datasets(self.project["id"])
                self.docs = [d for d in self.docs if d.source_file != f["filename"]]
                if res.docs:
                    self.docs = merge_docs(self.docs, res.docs, "add")
            flagged = merge_lines(self.lines, res.lines)
            msg = "; ".join(res.messages)
            if flagged:
                msg += f"; {flagged} possible duplicate line(s) flagged"
            t13 = register_table13(Path(f["stored_path"]), self.schema)
            if t13 and t13[0] and not t13[1]:
                series, _ = t13
                for d in series:
                    d.source_file = f["filename"]
                self.docs = [d for d in self.docs if not (d.origin == "register" and d.source_file == f["filename"])]
                self.docs = merge_docs(self.docs, series, "add")
                msg += f"; {len(series)} document series (Table 13) read from the Documents sheet"
            self.db.update_file(f["id"], review_count=review_count(res.lines), message=msg[:500])
            self.db.audit(self.project["id"], "Extracted", f"{f['filename']}: {len(res.lines)} records")
        except Exception as e:  # noqa
            log.exception("Extraction failed for file id %s", f["id"])
            self.db.update_file(f["id"], status="Failed", message=f"Error: {e}"[:500])
        self.progress["value"] = i + 1
        self.refresh_files()
        self.after(20, lambda: self._extract_step(files, i + 1))

    def map_selected(self):
        """Open the column-mapping screen for the selected Excel file even if it was recognised automatically."""
        ids = [int(x) for x in self.file_tree.selection()]
        if not ids:
            messagebox.showinfo(APP_NAME, "Select an Excel file in the list first.")
            return
        self.force_map = set(ids)
        self.extract_data(only_ids=set(ids))

    def reextract_selected(self):
        ids = [int(x) for x in self.file_tree.selection()]
        if ids:
            self.extract_data(only_ids=set(ids))

    def remove_selected_file(self):
        ids = [int(i) for i in self.file_tree.selection()]
        if not ids:
            messagebox.showinfo(APP_NAME, "Select the file(s) to remove first.")
            return
        recs = []
        for i in ids:
            r = self.db.q("SELECT * FROM files WHERE id=?", (i,))
            if r:
                recs.append(r[0])
        if len(recs) == 1:
            ask = f"Remove '{recs[0]['filename']}' and the records extracted from it?"
        else:
            ask = f"Remove these {len(recs)} files and the records extracted from them?\n\n" + \
                  "\n".join("  " + r["filename"] for r in recs[:10]) + \
                  (f"\n  ... and {len(recs) - 10} more" if len(recs) > 10 else "")
        if not messagebox.askyesno(APP_NAME, ask):
            return
        names = {r["filename"] for r in recs}
        self.lines = [l for l in self.lines if l.source_file not in names]
        for rec in recs:
            for d in self.db.datasets(self.project["id"]):
                if d["filename"] == rec["filename"]:
                    self.db.delete_dataset(d["id"])
            self.docs = [d for d in self.docs if d.source_file != rec["filename"]]
            Path(rec["stored_path"]).unlink(missing_ok=True)
            self.db.x("DELETE FROM files WHERE id=?", (rec["id"],))
            self.db.audit(self.project["id"], "File removed", rec["filename"])
        self.sets = self.db.datasets(self.project["id"])
        self.run_checks()
        self.refresh_files()
        self.set_status(f"{len(recs)} file(s) removed.")

    # ---------------------------------------------------------- 5 Review
    def _tab_review(self):
        f = self.tab("6 Invoice Review")
        ttk.Label(f, text="Invoice Review and Correction", style="Head.TLabel").pack(anchor="w")
        flt = ttk.Frame(f)
        flt.pack(fill="x", pady=4)
        self.f_search = tk.StringVar()
        self.f_date = tk.StringVar()
        self.f_sec = tk.StringVar(value="All")
        self.f_status = tk.StringVar(value="All")
        self.f_sev = tk.StringVar(value="Any")
        self.f_file = tk.StringVar(value="All")
        self.f_rate = tk.StringVar()
        def lab(t):
            ttk.Label(flt, text=t).pack(side="left", padx=(8, 2))
        lab("Search (invoice/name/GSTIN)")
        ttk.Entry(flt, textvariable=self.f_search, width=18).pack(side="left")
        lab("Date")
        ttk.Entry(flt, textvariable=self.f_date, width=10).pack(side="left")
        lab("Rate")
        ttk.Entry(flt, textvariable=self.f_rate, width=5).pack(side="left")
        lab("Section")
        ttk.Combobox(flt, textvariable=self.f_sec, values=["All"] + list(SECTIONS), width=7, state="readonly").pack(side="left")
        lab("Status")
        ttk.Combobox(flt, textvariable=self.f_status, width=10, state="readonly",
                     values=["All", STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_DUP]).pack(side="left")
        lab("Severity")
        ttk.Combobox(flt, textvariable=self.f_sev, width=11, state="readonly",
                     values=["Any", "Error", "Warning", "Information", "None"]).pack(side="left")
        lab("File")
        self.f_file_cb = ttk.Combobox(flt, textvariable=self.f_file, width=18, state="readonly", values=["All"])
        self.f_file_cb.pack(side="left")
        ttk.Button(flt, text="Apply", command=self.refresh_review).pack(side="left", padx=6)
        ttk.Button(flt, text="Clear", command=self.clear_filters).pack(side="left")
        cols = [("id", "ID", 40), ("file", "Source file", 130), ("ref", "Source ref", 90), ("inv", "Invoice no", 90),
                ("date", "Date", 80), ("name", "Recipient", 130), ("gstin", "Recipient GSTIN", 130),
                ("hsn", "HSN", 60), ("rate", "Rate", 40), ("taxable", "Taxable", 85), ("igst", "IGST", 70),
                ("cgst", "CGST", 70), ("sgst", "SGST", 70), ("total", "Line total", 85), ("sec", "Section", 55),
                ("status", "Status", 75), ("iss", "Issues", 60)]
        fr, self.rev_tree = make_tree(f, cols, height=16)
        fr.pack(fill="both", expand=True)
        self.rev_tree.bind("<Double-1>", lambda e: self.edit_line())
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        for text, cmd in [("Edit / Correct selected", self.edit_line), ("Approve Transactions (selected)", self.approve_selected),
                          ("Approve all without errors", self.approve_clean), ("Reject selected", self.reject_selected),
                          ("Set to Pending", self.pending_selected), ("Add line", self.add_line),
                          ("Delete selected (Del)", self.delete_lines), ("Re-validate", self.revalidate)]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3)
        bar2 = ttk.Frame(f)
        bar2.pack(fill="x", pady=2)
        for text, cmd in [("Select all (Ctrl+A)", self.select_all_lines), ("Select lines with errors", self.select_error_lines),
                          ("Delete ALL lines with errors", self.delete_error_lines),
                          ("Auto-fill place of supply & tax", self.autofill_selected),
                          ("Place of supply = GSTIN state (selected)", self.pos_from_gstin_selected),
                          ("Set GST rate / HSN for many rows...", self.set_rate_hsn),
                          ("Mark as Nil / Exempt / Non-GST...", self.set_nil_kind)]:
            ttk.Button(bar2, text=text, command=cmd).pack(side="left", padx=3)
        # third row, so the online checks stay visible on laptop screens
        bar3 = ttk.Frame(f)
        bar3.pack(fill="x", pady=2)
        for text, cmd in [("Check GSTIN on GST portal", self.check_gstin_online),
                          ("Look up HSN online", self.lookup_hsn_online)]:
            ttk.Button(bar3, text=text, command=cmd).pack(side="left", padx=3)
        ttk.Label(bar3, foreground="#555", text=(
            "Select a line first. The GSTIN / HSN is copied and the GST portal opens: paste it (Ctrl+V), "
            "type the captcha and search.")).pack(side="left", padx=8)
        self.rev_tree.bind("<Delete>", lambda e: self.delete_lines())
        self.rev_info = tk.StringVar()
        ttk.Label(f, textvariable=self.rev_info, foreground="#555").pack(anchor="w")
        ttk.Label(f, text="Selected line - validation messages:", foreground="#555").pack(anchor="w")
        self.rev_msgs = tk.Text(f, height=5, wrap="word", state="disabled", background="#fafafa")
        self.rev_msgs.pack(fill="x")
        self.rev_tree.bind("<<TreeviewSelect>>", lambda e: self.show_line_issues())

    def clear_filters(self):
        self.f_search.set("")
        self.f_date.set("")
        self.f_rate.set("")
        for v, d in ((self.f_sec, "All"), (self.f_status, "All"), (self.f_sev, "Any"), (self.f_file, "All")):
            v.set(d)
        self.refresh_review()

    def filtered_lines(self):
        s = self.f_search.get().strip().lower()
        dsub = self.f_date.get().strip()
        rate = self.f_rate.get().strip()
        out = []
        for l in self.lines:
            if s and s not in f"{l.invoice_no} {l.recipient_name} {l.recipient_gstin}".lower():
                continue
            if dsub:
                from .utils import fmt_date
                if dsub not in l.invoice_date and dsub not in fmt_date(l.invoice_date, "DD/MM/YYYY"):
                    continue
            if rate and D(rate, None) is not None and l.rate != D(rate):
                continue
            if self.f_sec.get() != "All" and l.section != self.f_sec.get():
                continue
            if self.f_status.get() != "All" and l.review_status != self.f_status.get():
                continue
            if self.f_file.get() != "All" and l.source_file != self.f_file.get():
                continue
            sev = self.f_sev.get()
            iss = self.issue_by_line.get(l.id, [])
            if sev == "None" and iss:
                continue
            if sev in ("Error", "Warning", "Information") and not any(i.severity == sev for i in iss):
                continue
            out.append(l)
        return out

    def refresh_review(self):
        clear(self.rev_tree)
        files = sorted({l.source_file for l in self.lines})
        self.f_file_cb["values"] = ["All"] + files
        rows = self.filtered_lines()
        for l in rows:
            iss = self.issue_by_line.get(l.id, [])
            e = sum(1 for i in iss if i.severity == "Error")
            w = sum(1 for i in iss if i.severity == "Warning")
            tags = []
            if l.review_status == STATUS_REJECTED:
                tags.append("rejected")
            elif e:
                tags.append("error")
            elif l.review_status == STATUS_DUP:
                tags.append("dup")
            elif w:
                tags.append("warning")
            elif l.review_status == STATUS_APPROVED:
                tags.append("approved")
            self.rev_tree.insert("", "end", iid=str(l.id), tags=tags, values=(
                l.id, l.source_file, l.source_ref, l.invoice_no, l.invoice_date, l.recipient_name,
                l.recipient_gstin, l.hsn, l.rate, l.taxable, l.igst, l.cgst, l.sgst, q2(l.line_total),
                l.section, l.review_status, f"{e}E {w}W" if (e or w) else ""))
        self.rev_info.set(f"{len(rows)} of {len(self.lines)} lines shown.  Red = errors, yellow = warnings, "
                          f"orange = possible duplicate, green = approved.")
        if not self.lines and self.sets:
            self.rev_info.set("No invoice lines: the uploaded file(s) are summary reports or Master Template data, so "
                              "there is nothing to review line by line. Their totals are in tabs 4, 7, 10 and 11.")

    def _open_portal(self, url, text, what):
        """Copy the value to the clipboard and open the official GST portal page (needs internet; a captcha is
        entered on the portal, so the lookup cannot be automatic)."""
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
        try:
            webbrowser.open(url)
            self.set_status(f"GST portal opened" + (f" - {what} '{text}' is copied: paste it in the search box there."
                                                    if text else "."))
        except Exception:  # noqa
            messagebox.showinfo(APP_NAME, "Open https://services.gst.gov.in in your browser and use the search there.")

    def check_gstin_online(self, gstin=None):
        if gstin is None:
            sel = self._sel_lines()
            gstin = sel[0].recipient_gstin if sel else ""
        g = str(gstin or "").strip().upper()
        if not g:
            messagebox.showinfo(APP_NAME, "This line has no recipient GSTIN (unregistered customer). "
                                          "The portal search page will open without a number.")
        self._open_portal("https://services.gst.gov.in/services/searchtp", g, "GSTIN")

    def lookup_hsn_online(self, hsn=None):
        if hsn is None:
            sel = self._sel_lines()
            hsn = (sel[0].hsn or sel[0].description) if sel else ""
        self._open_portal("https://services.gst.gov.in/services/searchhsnsac", str(hsn or "").strip(), "HSN")

    def _sel_lines(self):
        ids = {int(i) for i in self.rev_tree.selection()}
        return [l for l in self.lines if l.id in ids]

    def show_line_issues(self):
        sel = self._sel_lines()
        self.rev_msgs.configure(state="normal")
        self.rev_msgs.delete("1.0", "end")
        if len(sel) == 1:
            l = sel[0]
            if l.note:
                self.rev_msgs.insert("end", f"Note: {l.note}\n")
            for i in self.issue_by_line.get(l.id, []):
                self.rev_msgs.insert("end", f"[{i.severity}] {i.message}  ->  {i.action}\n")
            self.rev_msgs.insert("end", f"Classification reason: {reason_for(l, self.lines, self.settings)}")
        elif len(sel) > 1:
            from collections import Counter, OrderedDict
            cnt, ex = Counter(), OrderedDict()
            for l in sel:
                for i in self.issue_by_line.get(l.id, []):
                    k = (0 if i.severity == "Error" else 1 if i.severity == "Warning" else 2, i.severity, i.code)
                    cnt[k] += 1
                    ex.setdefault(k, i)
            self.rev_msgs.insert("end", f"{len(sel)} lines selected. What is wrong (click ONE line to see its own details):\n")
            for k in sorted(cnt, key=lambda x: (x[0], -cnt[x])):
                i = ex[k]
                self.rev_msgs.insert("end", f"[{i.severity}] {cnt[k]} line(s): {i.message}  ->  {i.action}\n")
            if not cnt:
                self.rev_msgs.insert("end", "No messages for the selected lines.")
        self.rev_msgs.configure(state="disabled")

    def _set_status(self, lines, status):
        for l in lines:
            if l.review_status != status:
                l.review_status = status
        self.db.audit(self.project["id"], "Status change", f"{len(lines)} line(s) -> {status}")
        if status == STATUS_APPROVED:
            learn_hsn(self.db, self.client["id"], lines)
        self.run_checks()
        self.refresh_review()

    def approve_selected(self):
        sel = self._sel_lines()
        if not sel:
            return
        bad = [l for l in sel if any(i.severity == "Error" for i in self.issue_by_line.get(l.id, []))]
        if bad and not messagebox.askyesno(APP_NAME, f"{len(bad)} selected line(s) still have errors. They will "
                                           "block CSV generation until resolved or overridden.\n\nApprove anyway?"):
            return
        self._set_status(sel, STATUS_APPROVED)

    def approve_clean(self):
        if not self.need_project():
            return
        ok = [l for l in self.lines if l.review_status in (STATUS_PENDING,) and not any(
            i.severity == "Error" for i in self.issue_by_line.get(l.id, []))]
        if ok and messagebox.askyesno(APP_NAME, f"Approve {len(ok)} pending line(s) that have no errors? "
                                      "Warnings will remain visible in the reports."):
            self._set_status(ok, STATUS_APPROVED)

    def reject_selected(self):
        sel = self._sel_lines()
        if sel:
            self._set_status(sel, STATUS_REJECTED)

    def pending_selected(self):
        sel = self._sel_lines()
        if sel:
            self._set_status(sel, STATUS_PENDING)

    def revalidate(self):
        self.run_checks()
        self.refresh_review()
        self.set_status(f"Validation complete: {sum(1 for i in self.issues if i.severity == 'Error')} error(s), "
                        f"{sum(1 for i in self.issues if i.severity == 'Warning')} warning(s).")

    def delete_lines(self):
        sel = self._sel_lines()
        if sel and messagebox.askyesno(APP_NAME, f"Delete {len(sel)} line(s) permanently? (Use Reject to keep them "
                                       "for the audit trail.)"):
            self._delete_line_objs(sel)

    def select_all_lines(self):
        self.rev_tree.selection_set(self.rev_tree.get_children(""))

    def _error_lines(self, shown_only=True):
        src = self.filtered_lines() if shown_only else self.lines
        return [l for l in src if l.review_status != STATUS_REJECTED
                and any(i.severity == "Error" for i in self.issue_by_line.get(l.id, []))]

    def select_error_lines(self):
        bad = self._error_lines()
        self.rev_tree.selection_set([str(l.id) for l in bad])
        if bad:
            self.rev_tree.see(str(bad[0].id))
        self.set_status(f"{len(bad)} line(s) with errors selected. Press Delete (or 'Delete selected') to remove them.")

    def _delete_line_objs(self, sel, what="line(s)"):
        ids = {l.id for l in sel}
        self.lines = [l for l in self.lines if l.id not in ids]
        self.db.audit(self.project["id"], "Lines deleted", f"{len(ids)} {what}")
        self.run_checks()
        self.refresh_review()
        self.set_status(f"{len(ids)} line(s) deleted.")

    def delete_error_lines(self):
        if not self.need_project():
            return
        bad = self._error_lines(shown_only=False)
        if not bad:
            messagebox.showinfo(APP_NAME, "There are no lines with errors.")
            return
        invs = sorted({l.invoice_no or "(no number)" for l in bad})
        if messagebox.askyesno(APP_NAME, f"Delete {len(bad)} line(s) with errors, from {len(invs)} invoice(s)?\n\n"
                               f"{', '.join(invs[:12])}{' ...' if len(invs) > 12 else ''}\n\n"
                               "Other lines of those invoices stay and may then show a total mismatch. "
                               "(Use Reject instead to keep them for the audit trail.)"):
            self._delete_line_objs(bad, "line(s) with errors")

    def autofill_selected(self):
        if not self.need_project():
            return
        sel = self._sel_lines()
        target = sel or [l for l in self.lines if l.review_status != STATUS_REJECTED]
        n = autofill.autofill_lines(target, self.client["gstin"][:2], self.settings)
        self.db.audit(self.project["id"], "Auto-fill", f"{n} of {len(target)} line(s): place of supply / tax")
        self.run_checks()
        self.refresh_review()
        self.set_status(f"Place of supply and tax completed on {n} of {len(target)} line(s) "
                        f"({'selected' if sel else 'all'}). Tax = taxable value x rate.")

    def set_nil_kind(self):
        """Mark many lines at once as Nil rated / Exempted / Non-GST (Table 8): kind, rate 0 and no tax."""
        if not self.need_project():
            return
        files = sorted({l.source_file for l in self.lines})
        sel = self._sel_lines()
        fields = [("kind", "These supplies are", "combo", ["Exempted", "Nil Rated", "Non-GST"]),
                  ("scope", "Apply to", "combo", ["All lines", "Selected lines"]),
                  ("file", "Only lines from file", "combo", ["All files"] + files),
                  ("clear", "Clear it again (make them normal taxable lines)", "combo", ["No", "Yes"])]
        dlg = FormDialog(self, "Mark rows as Nil / Exempt / Non-GST", fields,
                         {"kind": "Exempted", "scope": "Selected lines" if sel else "All lines",
                          "file": files[-1] if files and not sel else "All files", "clear": "No"}, columns=1)
        if not dlg.result:
            return
        r = dlg.result
        base = [l for l in self.lines if l.review_status != STATUS_REJECTED]
        if r["scope"] == "Selected lines":
            base = [l for l in base if l in sel]
        if r["file"] != "All files":
            base = [l for l in base if l.source_file == r["file"]]
        if not base:
            messagebox.showinfo(APP_NAME, "No lines match - nothing changed.")
            return
        for l in base:
            if r["clear"] == "Yes":
                l.nil_kind = ""
            else:
                l.nil_kind = r["kind"]
                l.rate = Decimal(0)
                l.igst = l.cgst = l.sgst = l.cess = Decimal(0)
        self.db.audit(self.project["id"], "Bulk nil/exempt", f"{r['kind']} on {len(base)} line(s) clear={r['clear']}")
        self.run_checks()
        self.refresh_review()
        self.set_status(f"{len(base)} line(s) " + ("cleared." if r["clear"] == "Yes" else f"marked {r['kind']} (rate 0, no tax)."))

    def set_rate_hsn(self):
        """One dialog: 'what is the GST rate (and HSN) for these rows?'. Applies it, then recalculates IGST / CGST / SGST
        from taxable value x rate using the place of supply that follows from each recipient GSTIN."""
        if not self.need_project():
            return
        files = sorted({l.source_file for l in self.lines})
        sel = self._sel_lines()
        scopes = ["All lines", "Selected lines", "Only lines with no rate", "Only lines with no HSN"]
        fields = [("rate", "GST rate % (blank = leave as is)", "combo",
                   ["", "0", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40"]),
                  ("hsn", "HSN / SAC (blank = leave as is)", "entry", None),
                  ("description", "HSN description (blank = automatic)", "entry", None),
                  ("uqc", "Unit (UQC)", "combo", ["", "NOS", "KGS", "PCS", "LTR", "MTR", "BOX", "SET", "UNT", "OTH"]),
                  ("scope", "Apply to", "combo", scopes), ("file", "Only lines from file", "combo", ["All files"] + files)]
        dlg = FormDialog(self, "Set GST rate / HSN for many rows", fields,
                         {"scope": "Selected lines" if sel else "All lines", "file": "All files"}, columns=1)
        if not dlg.result:
            return
        r = dlg.result
        rate = D(r["rate"], None) if r["rate"].strip() else None
        hsn = re.sub(r"\s+", "", r["hsn"])
        if (r["rate"].strip() and (rate is None or rate < 0 or rate > 100)) or (hsn and not hsn.isdigit()):
            messagebox.showerror(APP_NAME, "GST rate must be a number (such as 18) and HSN/SAC must be digits only.")
            return
        if rate is None and not hsn:
            messagebox.showinfo(APP_NAME, "Enter a GST rate and/or an HSN/SAC.")
            return
        base = [l for l in self.lines if l.review_status != STATUS_REJECTED]
        if r["scope"] == "Selected lines":
            base = [l for l in base if l in sel]
        elif r["scope"] == "Only lines with no rate":
            base = [l for l in base if not l.rate]
        elif r["scope"] == "Only lines with no HSN":
            base = [l for l in base if not l.hsn]
        if r["file"] != "All files":
            base = [l for l in base if l.source_file == r["file"]]
        master = self.db.hsn_master(self.client["id"])
        forced = dict(self.settings, auto_tax="1")
        own = self.client["gstin"][:2]
        n_rate = n_igst = n_split = n_hsn = 0
        for l in base:
            if hsn:
                l.hsn = hsn
                l.description = r["description"].strip() or hsn_mod.describe(hsn, master) or l.description
                l.uqc = r["uqc"].strip() or l.uqc or master.get(hsn, {}).get("uqc", "")
                n_hsn += 1
            if rate is not None and not l.nil_kind:
                l.rate = rate
                l.igst = l.cgst = l.sgst = Decimal(0)
                autofill.autofill_line(l, own, forced)
                n_rate += 1
                if l.igst:
                    n_igst += 1
                elif l.cgst:
                    n_split += 1
        self.db.audit(self.project["id"], "Bulk rate/HSN",
                      f"rate={r['rate'] or '-'} hsn={hsn or '-'} on {len(base)} line(s) [{r['scope']}]")
        self.run_checks()
        self.refresh_review()
        msg = []
        if rate is not None:
            msg.append(f"GST rate {r['rate']}% set on {n_rate} line(s): {n_igst} with IGST, {n_split} with CGST+SGST")
        if hsn:
            msg.append(f"HSN {hsn} set on {n_hsn} line(s)")
        self.set_status("; ".join(msg) + ".")
        messagebox.showinfo(APP_NAME, "\n".join(msg) + "\n\nLines marked Nil / Exempt / Non-GST keep their rate.")

    def pos_from_gstin_selected(self):
        sel = self._sel_lines()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select the lines first (Ctrl+A selects all).")
            return
        n = 0
        for l in sel:
            p = autofill.pos_from_gstin(l.recipient_gstin)
            if p and p != l.pos:
                l.pos, n = p, n + 1
                l.igst = l.cgst = l.sgst = Decimal(0)
                autofill.autofill_line(l, self.client["gstin"][:2], self.settings)
        self.db.audit(self.project["id"], "Place of supply from GSTIN", f"{n} line(s) changed")
        self.run_checks()
        self.refresh_review()
        self.set_status(f"Place of supply set from the recipient GSTIN on {n} line(s); tax recalculated.")

    LINE_FIELDS = [("invoice_no", "Invoice no", "entry", None), ("invoice_date", "Invoice date (DD/MM/YYYY)", "entry", None),
                   ("recipient_gstin", "Recipient GSTIN", "entry", None), ("recipient_name", "Recipient name", "entry", None),
                   ("invoice_type", "Invoice type", "combo", INVOICE_TYPES + ["Advance", "Advance adjustment"]),
                   ("note_type", "Note type ('' / C / D)", "combo", ["", "C", "D"]),
                   ("orig_invoice_no", "Original invoice no", "entry", None),
                   ("orig_invoice_date", "Original invoice date", "entry", None),
                   ("pos", "Place of supply", "combo", [f"{c}-{n}" for c, n in STATE_CODES.items()]),
                   ("reverse_charge", "Reverse charge (Y/N)", "combo", ["N", "Y"]),
                   ("ecom_gstin", "E-commerce GSTIN", "entry", None), ("hsn", "HSN/SAC", "entry", None),
                   ("description", "Description", "entry", None), ("uqc", "UQC", "entry", None),
                   ("qty", "Quantity", "entry", None), ("rate", "GST rate %", "entry", None),
                   ("taxable", "Taxable value", "entry", None), ("igst", "IGST", "entry", None),
                   ("cgst", "CGST", "entry", None), ("sgst", "SGST/UTGST", "entry", None),
                   ("cess", "Cess", "entry", None), ("invoice_total", "Invoice total", "entry", None),
                   ("nil_kind", "Nil / Exempt / Non-GST kind", "combo", ["", "Nil Rated", "Exempted", "Non-GST"]),
                   ("export_type", "Export type", "combo", ["", "WPAY", "WOPAY"]),
                   ("port_code", "Port code", "entry", None), ("ship_bill_no", "Shipping bill no", "entry", None),
                   ("ship_bill_date", "Shipping bill date", "entry", None),
                   ("section", "GSTR-1 section", "combo", [k for k in SECTIONS if is_implemented(k)]),
                   ("section_locked", "Keep this section (lock)", "check", None),
                   ("review_status", "Review status", "combo", [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_DUP])]
    HEADER_FIELDS = ("invoice_no", "invoice_date", "recipient_gstin", "recipient_name", "invoice_type",
                     "note_type", "pos", "reverse_charge", "invoice_total")

    def _line_values(self, l):
        v = {k: getattr(l, k) for k, *_ in self.LINE_FIELDS}
        v["pos"] = pos_label(l.pos)
        return v

    def edit_line(self):
        sel = self._sel_lines()
        if len(sel) != 1:
            messagebox.showinfo(APP_NAME, "Select one line to edit.")
            return
        l = sel[0]
        dlg = FormDialog(self, f"Edit line {l.id} - {l.source_file} {l.source_ref}", self.LINE_FIELDS,
                         self._line_values(l), columns=2,
                         extra_buttons=[("Check GSTIN on GST portal",
                                         lambda v: self.check_gstin_online(v.get("recipient_gstin", ""))),
                                        ("Look up HSN online",
                                         lambda v: self.lookup_hsn_online(v.get("hsn") or v.get("description", "")))])
        if not dlg.result:
            return
        r = dlg.result
        old_key = l.key()
        changes = []
        new = {}
        for k, _, kind, _c in self.LINE_FIELDS:
            val = r[k]
            if k in ("invoice_date", "orig_invoice_date", "ship_bill_date"):
                val = parse_date(val) or ("" if not str(val).strip() else l.__dict__[k])
            elif k == "pos":
                val = state_from_text(val)
            elif k in ("qty", "rate", "taxable", "igst", "cgst", "sgst", "cess", "invoice_total"):
                val = D(val)
            elif k in ("recipient_gstin", "ecom_gstin"):
                val = str(val).strip().upper()
            elif k == "section_locked":
                val = bool(val)
            elif isinstance(val, str):
                val = val.strip()
            new[k] = val
        if new["section"] != l.section:
            new["section_locked"] = True
        for k, val in new.items():
            if getattr(l, k) != val:
                changes.append(f"{k}: {getattr(l, k)} -> {val}")
                setattr(l, k, val)
        # ---- automatic completion: place of supply from the GSTIN, tax = taxable x rate
        user_tax = any(c.split(":")[0] in ("igst", "cgst", "sgst") for c in changes)
        if any(c.startswith("recipient_gstin") for c in changes) and not any(c.startswith("pos") for c in changes) \
                and autofill.flag(self.settings, "auto_pos"):
            p = autofill.pos_from_gstin(l.recipient_gstin)
            if p and p != l.pos:
                changes.append(f"pos: {l.pos} -> {p} (from GSTIN)")
                l.pos = p
        if not l.pos:
            autofill.autofill_line(l, self.client["gstin"][:2], self.settings, tax=False)
        if not user_tax:
            for c in autofill.autofill_line(l, self.client["gstin"][:2], self.settings):
                changes.append("auto: " + c)
        if changes:
            # invoice-level fields apply to every line of the same invoice
            for o in self.lines:
                if o is not l and o.key() == old_key:
                    for k in self.HEADER_FIELDS:
                        setattr(o, k, getattr(l, k))
                    autofill.autofill_line(o, self.client["gstin"][:2], self.settings)
            l.confidence = max(l.confidence, 0.9)
            self.db.audit(self.project["id"], "Correction",
                          f"line {l.id} ({l.source_file} {l.source_ref}): " + "; ".join(changes))
        self.run_checks()
        self.refresh_review()

    def add_line(self):
        if not self.need_project():
            return
        l = Line(id=max((x.id for x in self.lines), default=0) + 1, source_file="Manual entry", source_ref="manual",
                 supplier_gstin=self.client["gstin"], supplier_name=self.client["name"], confidence=1.0)
        dlg = FormDialog(self, "Add manual line", self.LINE_FIELDS, self._line_values(l))
        if not dlg.result:
            return
        self.lines.append(l)
        r = dlg.result
        for k, _, kind, _c in self.LINE_FIELDS:
            val = r[k]
            if k in ("invoice_date", "orig_invoice_date", "ship_bill_date"):
                val = parse_date(val)
            elif k == "pos":
                val = state_from_text(val)
            elif k in ("qty", "rate", "taxable", "igst", "cgst", "sgst", "cess", "invoice_total"):
                val = D(val)
            elif k == "section_locked":
                val = bool(val)
            elif isinstance(val, str):
                val = val.strip().upper() if k in ("recipient_gstin", "ecom_gstin") else val.strip()
            setattr(l, k, val)
        autofill.autofill_line(l, self.client["gstin"][:2], self.settings, tax=not any(
            getattr(l, k) for k in ("igst", "cgst", "sgst")))
        self.db.audit(self.project["id"], "Line added", f"manual line {l.id}")
        self.run_checks()
        self.refresh_review()

    # ---------------------------------------------------------- 6 Classification
    def _tab_classification(self):
        f = self.tab("7 Classification")
        ttk.Label(f, text="GST Classification Review", style="Head.TLabel").pack(anchor="w")
        ttk.Label(f, wraplength=1100, foreground="#a00000",
                  text="Invoice lines from Excel/PDF are classified into B2B, B2CL, B2CS, Exports, Credit/Debit notes, "
                       "Nil/Exempt/Non-GST and Advances. Amendments cannot be derived from a single invoice - enter them in "
                       "the Master Template (amendment sheets). Override a classification below where needed.").pack(anchor="w", pady=4)
        fr, self.cls_sum = make_tree(f, [("s", "Section", 330), ("impl", "Generated?", 150), ("n", "Invoices", 80),
                                         ("v", "Taxable value", 140)], height=6)
        fr.pack(fill="x")
        fr, self.cls_tree = make_tree(f, [("inv", "Invoice", 110), ("date", "Date", 90), ("name", "Recipient", 200),
                                          ("gstin", "GSTIN", 140), ("sec", "Section", 70), ("lock", "Manual", 60),
                                          ("val", "Invoice value", 110), ("why", "Reason", 380)], height=12)
        fr.pack(fill="both", expand=True, pady=6)
        bar = ttk.Frame(f)
        bar.pack(anchor="w")
        self.cls_set = tk.StringVar(value="B2B")
        ttk.Label(bar, text="Change selected invoices to section:").pack(side="left")
        ttk.Combobox(bar, textvariable=self.cls_set, values=[k for k in SECTIONS if is_implemented(k)], width=8, state="readonly").pack(side="left", padx=4)
        ttk.Button(bar, text="Apply (locks classification)", command=self.apply_section).pack(side="left", padx=3)
        ttk.Button(bar, text="Unlock selected (re-classify automatically)", command=self.unlock_section).pack(side="left", padx=3)

    def refresh_class(self):
        clear(self.cls_sum)
        clear(self.cls_tree)
        if not self.project:
            return
        d = dashboard(self.lines, self.issues, [], self.project)
        for s, (n, v) in sorted(d["sections"].items()):
            self.cls_sum.insert("", "end", values=(f"{s} - {SECTIONS.get(s, ('?',))[0]}",
                                                   "Yes" if is_implemented(s) else "NO - manual", n, f"{q2(v):,}"))
        if self.sets:                       # summary reports / Master Template rows are not invoice lines - show them here
            try:
                _pre, fin = gstr1.build_tables([], self.sets, self.client, self.settings, self.schema)
                for r in gstr1.summarize(fin, self.client["gstin"][:2], self.schema):
                    self.cls_sum.insert("", "end", tags=("approved",), values=(
                        f"{r['title']}  (from uploaded summary / template data)", "Yes", r["docs"], f"{q2(r['taxable']):,}"))
            except Exception as ex:   # noqa
                log.warning("classification summary of uploaded datasets failed: %s", ex)
        for key, grp in group_invoices([l for l in self.lines if l.review_status != STATUS_REJECTED]).items():
            l = grp[0]
            self.cls_tree.insert("", "end", iid="|".join(key), values=(
                l.invoice_no, l.invoice_date, l.recipient_name, l.recipient_gstin,
                "/".join(sorted({x.section for x in grp})), "Yes" if any(x.section_locked for x in grp) else "",
                q2(invoice_value(grp)), reason_for(l, self.lines, self.settings)))

    def _sel_invoice_lines(self):
        keys = set(self.cls_tree.selection())
        return [l for l in self.lines if "|".join(l.key()) in keys]

    def apply_section(self):
        for l in self._sel_invoice_lines():
            l.section, l.section_locked = self.cls_set.get(), True
        self.db.audit(self.project["id"], "Classification override", self.cls_set.get())
        self.run_checks()
        self.refresh_class()

    def unlock_section(self):
        for l in self._sel_invoice_lines():
            l.section_locked = False
        self.run_checks()
        self.refresh_class()

    # ---------------------------------------------------------- 7 Validation
    def _tab_validation(self):
        f = self.tab("8 Validation")
        ttk.Label(f, text="Validation and Reconciliation", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        self.v_sev = tk.StringVar(value="All")
        ttk.Label(bar, text="Severity").pack(side="left")
        ttk.Combobox(bar, textvariable=self.v_sev, values=["All", "Error", "Warning", "Information"], width=12,
                     state="readonly").pack(side="left", padx=4)
        ttk.Button(bar, text="Run Validation", command=lambda: (self.run_checks(), self.refresh_validation())).pack(side="left", padx=3)
        ttk.Button(bar, text="Export Exception Report", command=self.export_exceptions).pack(side="left", padx=3)
        ttk.Button(bar, text="Select all (Ctrl+A)", command=lambda: self.val_tree.selection_set(
            self.val_tree.get_children(""))).pack(side="left", padx=3)
        ttk.Button(bar, text="Select all errors", command=self.select_error_issues).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete rows of selected issues", command=self.delete_issue_rows).pack(side="left", padx=3)
        self.v_sev.trace_add("write", lambda *a: self.refresh_validation())
        fr, self.val_tree = make_tree(f, [("sev", "Severity", 80), ("code", "Code", 130), ("inv", "Invoice / note", 90),
                                          ("file", "Source file", 130), ("ref", "Sheet / row", 110),
                                          ("msg", "Explanation", 400), ("act", "Suggested action", 320)], height=12)
        fr.pack(fill="both", expand=True)
        self.val_tree.bind("<Double-1>", self.goto_issue)
        ttk.Label(f, text="Reconciliation (based on currently approved records)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        fr, self.rec_tree = make_tree(f, [("c", "Check", 520), ("s", "Source", 100), ("p", "Processed", 100),
                                          ("d", "Difference", 90), ("st", "Status", 90), ("n", "Note", 300)], height=7)
        fr.pack(fill="x")

    def refresh_validation(self):
        clear(self.val_tree)
        clear(self.rec_tree)
        if not self.project:
            return
        sev = self.v_sev.get()
        for n, i in enumerate(self.issues):
            if sev != "All" and i.severity != sev:
                continue
            self.val_tree.insert("", "end", iid=str(n), tags=("error" if i.severity == "Error" else
                                                              "warning" if i.severity == "Warning" else ""),
                                 values=(i.severity, i.code, i.invoice_no, i.source_file, i.ref, i.message, i.action))
        out = self.compute_outputs()
        self._fill_recon(self.rec_tree, out["recon"])

    def select_error_issues(self):
        self.v_sev.set("Error")
        self.refresh_validation()
        self.val_tree.selection_set(self.val_tree.get_children(""))

    def delete_issue_rows(self):
        """Delete the invoice lines and the Master Template rows that the selected issues point to."""
        if not self.need_project():
            return
        picked = [self.issues[int(i)] for i in self.val_tree.selection()]
        line_ids = {i.line_id for i in picked if i.line_id}
        targets = {(i.source_file, i.ref) for i in picked if not i.line_id and i.ref and " row " in i.ref}
        sel = [l for l in self.lines if l.id in line_ids]
        if not sel and not targets:
            messagebox.showinfo(APP_NAME, "Select issues that point to an invoice line or to a template row. "
                                "(Register-level and duplicate-across-files issues have no single row to delete.)")
            return
        if not messagebox.askyesno(APP_NAME, f"Delete {len(sel)} invoice line(s) and {len(targets)} Master Template "
                                   "row(s) (with all rows of the same invoice/note) that the selected issues point to?"):
            return
        if sel:
            self.lines = [l for l in self.lines if l.id not in line_ids]
        n = remove_template_rows(self.db, self.sets, targets) if targets else 0
        if n:
            self.sets = self.db.datasets(self.project["id"])
        self.db.audit(self.project["id"], "Rows deleted from issue list", f"{len(sel)} line(s), {n} template row(s)")
        self.run_checks()
        self.refresh_validation()
        self.set_status(f"Deleted {len(sel)} invoice line(s) and {n} template row(s).")

    def goto_issue(self, _e=None):
        sel = self.val_tree.selection()
        if not sel:
            return
        i = self.issues[int(sel[0])]
        if i.line_id and i.invoice_no:
            self.clear_filters()
            self.f_search.set(i.invoice_no)
            self.goto("Invoice Review")
            self.refresh_review()
        elif i.ref:
            messagebox.showinfo(APP_NAME, f"This problem is in the uploaded template ({i.ref}).\n\nCorrect it in the Excel "
                                "file and upload it again (remove the old upload in the Master Template tab first).")
        elif "DOC" in i.code:
            self.goto("Documents")

    def export_exceptions(self):
        if not self.need_project():
            return
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                         initialfile=f"exception_report_{self.client['gstin']}_{self.project['year']}_{self.project['month']:02d}.xlsx")
        if p:
            if Path(p).exists() and not messagebox.askyesno(APP_NAME, "File exists. Overwrite?"):
                return
            export_exception_report(Path(p), self.issues, self.lines)
            self.db.audit(self.project["id"], "Exception report exported", Path(p).name)
            self.set_status(f"Exception report saved: {p}")

    # ---------------------------------------------------------- computed outputs
    def compute_outputs(self):
        """Tables, tax summary and reconciliation from approved invoice lines + uploaded template data."""
        if not self.project:
            return None
        pre, final = gstr1.build_tables(self.lines, self.sets, self.client, self.settings, self.schema)
        summary = gstr1.summarize(final, self.client["gstin"][:2], self.schema)
        recon = gstr1.reconcile(self.lines, pre, final, self.docs, summary, self.settings)
        final["docs"] = build_docs(self.docs)
        return {"pre": pre, "final": final, "summary": summary, "recon": recon}

    # ---------------------------------------------------------- 4 Master Template
    def _tab_master(self):
        f = self.tab("4 Master Template")
        ttk.Label(f, text="GSTR-1 Master Template - one Excel file for every table", style="Head.TLabel").pack(anchor="w")
        ttk.Label(f, wraplength=1150, foreground="#444", text=(
            "1) Download the blank template (one sheet each for B2B, B2CL, B2CS, Exports, Credit/Debit notes, Exempt-Nil-NonGST, "
            "Advances, HSN, Documents and all Amendment tables).  2) The client fills the sheets that apply.  "
            "3) Upload the filled file here.  The whole file is checked; if anything is wrong NOTHING is imported and every "
            "problem is listed with its sheet and row.  4) Generate the CSV files from the Export tab.  "
            "Use the sample template only to see how a filled file looks - it is refused on upload.")).pack(anchor="w", pady=4)
        bar = ttk.Frame(f)
        bar.pack(anchor="w", pady=4)
        for text, cmd in [("Download Blank Template", lambda: self.master_download(False)),
                          ("Download Sample Template (demo data)", lambda: self.master_download(True)),
                          ("Upload Filled Template", self.master_upload),
                          ("Remove selected upload", self.master_remove),
                          ("Export Upload Issues", self.master_export_issues)]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3)
        self.skip_err = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, variable=self.skip_err, text=(
            "On upload, skip the invoices/rows that have errors and import the rest (skipped rows are listed below as "
            "warnings - send them back to the client)")).pack(anchor="w")
        ttk.Label(f, text="Template files uploaded for this return", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        fr, self.tpl_tree = make_tree(f, [("f", "File", 260), ("when", "Uploaded", 140), ("rows", "Rows per table", 740)], height=5)
        fr.pack(fill="x")
        ttk.Label(f, text="Result of the last upload (errors block the import; warnings are imported and kept for review)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        fr, self.tpl_issues = make_tree(f, [("sev", "Severity", 80), ("ref", "Sheet / row", 130), ("code", "Code", 120),
                                            ("msg", "Problem", 470), ("act", "What to do", 330)], height=13)
        fr.pack(fill="both", expand=True)

    def refresh_master(self):
        clear(self.tpl_tree)
        clear(self.tpl_issues)
        if not self.project:
            return
        for ds in self.sets:
            rows = ", ".join(f"{k.upper()} {len(v)}" for k, v in ds["tables"].items() if v)
            self.tpl_tree.insert("", "end", iid=str(ds["id"]), values=(ds["filename"], ds["uploaded"], rows or "-"))
        for i in self.last_upload_issues:
            self.tpl_issues.insert("", "end", tags=("error" if i.severity == "Error" else
                                                    "warning" if i.severity == "Warning" else "",),
                                   values=(i.severity, i.ref, i.code, i.message, i.action))

    def master_download(self, sample):
        if not self.need_project():
            return
        p = filedialog.asksaveasfilename(
            title="Save the GSTR-1 Master Template" + (" (SAMPLE with demo data)" if sample else ""),
            defaultextension=".xlsx", initialdir=self.settings.get("last_template_dir") or str(Path.home()),
            initialfile=f"GSTR1_master_template_{'SAMPLE_' if sample else ''}{self.client['gstin']}_"
                        f"{self.project['year']}_{self.project['month']:02d}.xlsx",
            filetypes=[("Excel workbook", "*.xlsx")])
        if not p:
            return
        try:
            gstr1.write_master_template(Path(p), self.schema, self.client, self.project, sample=sample)
        except Exception as e:  # noqa
            log.exception("Template download failed")
            messagebox.showerror(APP_NAME, f"Could not save the template:\n{e}")
            return
        self.db.set_setting("last_template_dir", str(Path(p).parent))
        self.settings = self.db.get_settings()
        self.db.audit(self.project["id"], "Master template downloaded", Path(p).name + (" (sample)" if sample else ""))
        self.set_status(f"Template saved: {p}")
        if messagebox.askyesno(APP_NAME, f"Template saved:\n{p}\n\nOpen the folder now?"):
            open_folder(Path(p).parent)

    def master_upload(self):
        if not self.need_project():
            return
        p = filedialog.askopenfilename(
            title="Select the filled GSTR-1 Master Template",
            initialdir=self.settings.get("last_template_dir") or str(Path.home()),
            filetypes=[("Excel workbook", "*.xlsx *.xlsm"), ("All files", "*.*")])
        if not p:
            return
        self.set_status("Reading and checking the template ...")
        try:
            res, ds_id, msg = import_master_template(self.db, self.client, self.project, Path(p), self.settings,
                                                     self.schema, skip_errors=self.skip_err.get())
        except Exception as e:  # noqa
            log.exception("Template import failed")
            messagebox.showerror(APP_NAME, f"The template could not be processed:\n{e}")
            return
        self.last_upload_issues = res.issues
        self.refresh_master()
        if ds_id is None:
            if res.errors:
                messagebox.showwarning(APP_NAME, f"The file was NOT imported - {len(res.errors)} error(s).\n\nEvery problem "
                                       "is listed below with its sheet and row. Correct the file and upload it again.")
            else:
                messagebox.showinfo(APP_NAME, msg)
            return
        if res.docs:
            mode = "replace"
            if any(d.origin != "derived" for d in self.docs):
                ans = messagebox.askyesnocancel(
                    APP_NAME, f"The Documents sheet has {len(res.docs)} series and a document register already exists.\n\n"
                              "Yes = REPLACE the existing register\nNo = ADD to the existing register\n"
                              "Cancel = keep the existing register unchanged")
                mode = None if ans is None else ("replace" if ans else "add")
            if mode:
                self.docs = merge_docs(self.docs, res.docs, mode)
        self.sets = self.db.datasets(self.project["id"])
        self.db.set_setting("last_template_dir", str(Path(p).parent))
        self.settings = self.db.get_settings()
        self.run_checks()
        self.refresh_master()
        counts = ", ".join(f"{k.upper()}: {v}" for k, v in sorted(res.counts.items()))
        skipped = f"\n\n{res.skipped} row(s) with errors were SKIPPED - see the warnings below." if res.skipped else ""
        messagebox.showinfo(APP_NAME, f"Imported {res.total_rows} rows.\n{counts}{skipped}\n\nWarnings: {len(res.warnings)} (listed below).\n"
                                      "Next: check the Validation tab, then CSV Preview, GSTR-1 Summary and Export.")
        self.set_status(f"Template imported: {Path(p).name}")

    def master_remove(self):
        sel = self.tpl_tree.selection()
        if not sel or not self.need_project():
            return
        ds = next((d for d in self.sets if str(d["id"]) == sel[0]), None)
        if ds and messagebox.askyesno(APP_NAME, f"Remove the data imported from '{ds['filename']}'?\n(The Documents register is "
                                      "not changed - edit it in the Documents tab.)"):
            self.db.delete_dataset(ds["id"])
            self.db.audit(self.project["id"], "Template upload removed", ds["filename"])
            self.sets = self.db.datasets(self.project["id"])
            self.run_checks()
            self.refresh_master()

    def master_export_issues(self):
        if not self.last_upload_issues:
            messagebox.showinfo(APP_NAME, "No upload issues to export.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                         initialfile="template_upload_issues.xlsx")
        if p:
            export_issue_report(Path(p), self.last_upload_issues)
            self.set_status(f"Issue list saved: {p}")

    # ---------------------------------------------------------- 9 Documents
    DOC_FIELDS = [("nature", "Nature of document", "combo", DOC_NATURES),
        ("from_no", "Sr. No. from", "entry", None), ("to_no", "Sr. No. to", "entry", None),
        ("total", "Total issued", "entry", None), ("cancelled", "Cancelled", "entry", None)]

    def _tab_documents(self):
        f = self.tab("9 Documents")
        ttk.Label(f, text="Documents issued (Table 13) - document series register", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        for text, cmd in [("Download Sample Template", self.doc_template),
                          ("Upload Filled Documents File", self.doc_upload),
                          ("Generate documents.csv", self.doc_generate),
                          ("Add series", self.doc_add), ("Edit selected", self.doc_edit),
                          ("Delete selected", self.doc_delete), ("Delete ALL", self.doc_delete_all),
                          ("Build series from invoices (gap-wise)", self.doc_suggest),
                          ("Mark selected as VERIFIED", self.doc_verify),
                          ("Refresh", self.doc_refresh)]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3, pady=3)
        ttk.Label(bar, text="Series by:").pack(side="left", padx=(10, 2))
        self.doc_mode = tk.StringVar(value="Auto")
        ttk.Combobox(bar, textvariable=self.doc_mode, state="readonly", width=16,
                     values=["Auto", "Prefix / running number", "Customer"]).pack(side="left")
        ttk.Label(f, foreground="#a00000", wraplength=1150,
                  text="The Documents sheet of the Master Template is also read automatically. Alternatively download this "
                       "stand-alone Documents template, fill it from the client's invoice register (issued and cancelled "
                       "counts) and upload it. The file is checked row by row; nothing is imported if any row has a "
                       "problem. 'Suggest' only reads the invoices uploaded here and is flagged as unverified.").pack(anchor="w")
        fr, self.doc_tree = make_tree(f, [("n", "Nature of Document", 330), ("a", "Sr. No. From", 120), ("b", "Sr. No. To", 120),
                                          ("t", "Total Number", 100), ("c", "Cancelled", 90), ("net", "Net issued", 90),
                                          ("o", "Source", 220)], height=18)
        fr.pack(fill="both", expand=True)
        self.doc_tree.bind("<Double-1>", lambda e: self.doc_edit())
        self.doc_gaps = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.doc_gaps, foreground="#8a4b00", wraplength=1150, justify="left").pack(anchor="w", pady=4)

    def _auto_series(self):
        """Keep the suggested series in step with the invoices (gap-wise); never touches typed / uploaded series."""
        from .series import entries_from_lines, entries_from_sets, build_runs, runs_to_docs, gap_report, auto_mode
        entries = entries_from_lines(self.lines) + entries_from_sets(self.sets)
        keep = [d for d in self.docs if d.origin not in ("derived", "verified")]
        if not entries:
            self.docs = keep
            self.doc_gaps.set("")
            return
        pick = {"Auto": "auto", "Prefix / running number": "prefix", "Customer": "customer"}[self.doc_mode.get()]
        mode = auto_mode(entries) if pick == "auto" else pick
        runs = build_runs(entries, mode)
        self.docs = keep + runs_to_docs(runs, mode)
        gaps = gap_report(runs, keep)
        uniq = len({(n, c, nat) if mode == "customer" else (n, nat) for n, c, nat in entries})
        covered = sum(r["total"] for r in runs)
        head = (f"Check: {uniq} different invoice/note numbers in the files; the series below cover {covered} documents "
                f"in {len(runs)} series.\n")
        if gaps:
            body = ("Numbers missing between the series (add them as cancelled in a series if they were issued and "
                    "cancelled):\n  " + "\n  ".join(gaps[:12]) + (f"\n  ... and {len(gaps) - 12} more" if len(gaps) > 12 else ""))
        else:
            body = "No gaps found in the numbering."
        self.doc_gaps.set(head + body)

    def _gap_text_only(self):
        """Typed / verified / uploaded series exist: only refresh the note about missing numbers, so it does not
        keep showing numbers those series already account for as cancelled."""
        from .series import entries_from_lines, entries_from_sets, build_runs, gap_report
        entries = entries_from_lines(self.lines) + entries_from_sets(self.sets)
        if not entries:
            self.doc_gaps.set("")
            return
        gaps = gap_report(build_runs(entries, "auto"), [d for d in self.docs if d.origin != "derived"])
        if gaps:
            self.doc_gaps.set("Numbers missing in the invoices and not yet accounted for as cancelled:\n  "
                              + "\n  ".join(gaps[:12]))
        else:
            self.doc_gaps.set("Every gap in the invoice numbers is accounted for in the series above.")

    def doc_refresh(self):
        """Re-read the invoices, rebuild the suggested series and clear old messages."""
        self.doc_gaps.set("")
        self.docs_lock = False
        if self.project and not any(d.origin in ("register", "manual", "verified") for d in self.docs):
            self._auto_series()
        self.refresh_documents()
        self.set_status("Documents refreshed.")

    def refresh_documents(self):
        if not self.project or not (self.lines or self.sets or self.docs):
            self.doc_gaps.set("")
        if self.project and not self.docs_lock and not any(
                d.origin in ("register", "manual", "verified") for d in self.docs):
            self._auto_series()
        elif self.project and self.docs:
            self._gap_text_only()
        clear(self.doc_tree)
        for d in self.docs:
            src = {"derived": "Built from invoices - verify" + (f" ({d.source_file})" if d.source_file else ""), "register": d.source_file or "uploaded file",
                   "manual": "Entered manually", "verified": "Verified by staff"}.get(d.origin, d.origin)
            self.doc_tree.insert("", "end", tags=("warning",) if d.origin == "derived" else (),
                                 values=(d.nature, d.from_no, d.to_no, d.total, d.cancelled, d.net, src))

    def _doc_apply(self, d, r):
        d.nature, d.from_no, d.to_no = r["nature"], r["from_no"].strip(), r["to_no"].strip()
        d.total, d.cancelled = int(D(r["total"])), int(D(r["cancelled"]))
        d.origin = "manual"

    def doc_add(self):
        if not self.need_project():
            return
        dlg = FormDialog(self, "Add document series", self.DOC_FIELDS, {"nature": "Invoices for outward supply"}, columns=1)
        if dlg.result:
            d = DocSeries()
            self._doc_apply(d, dlg.result)
            self.docs.append(d)
            self._docs_changed()

    def _doc_sel(self):
        sel = self.doc_tree.selection()
        if not sel:
            return None
        return self.docs[self.doc_tree.index(sel[0])]

    def doc_edit(self):
        d = self._doc_sel()
        if d:
            dlg = FormDialog(self, "Edit document series", self.DOC_FIELDS, d.to_dict(), columns=1)
            if dlg.result:
                self._doc_apply(d, dlg.result)
                self._docs_changed()

    def doc_delete(self):
        sel = [self.docs[self.doc_tree.index(i)] for i in self.doc_tree.selection()]
        if not sel:
            return
        if len(sel) > 1 and not messagebox.askyesno(APP_NAME, f"Delete {len(sel)} selected series?"):
            return
        for d in sel:
            self.docs.remove(d)
        self.docs_lock = True
        self._docs_changed()
        self.set_status(f"{len(sel)} series deleted. Click 'Build series from invoices' to build them afresh.")

    def doc_delete_all(self):
        if not self.need_project() or not self.docs:
            return
        if not messagebox.askyesno(APP_NAME, f"Delete ALL {len(self.docs)} document series of this return?\n\nThen click "
                                   "'Build series from invoices' to build them afresh."):
            return
        self.docs = []
        self.docs_lock = True
        self.doc_gaps.set("")
        self._docs_changed()
        self.set_status("All document series deleted. Click 'Build series from invoices (gap-wise)' to start afresh.")

    def doc_template(self):
        """Save a blank Documents template (Offline Tool Table-13 layout) to a folder chosen by the user."""
        p = filedialog.asksaveasfilename(
            title="Save the Documents sample template", defaultextension=".xlsx",
            initialdir=self.settings.get("last_template_dir") or str(Path.home()),
            initialfile="documents_template.xlsx",
            filetypes=[("Excel template (with drop-down and instructions)", "*.xlsx"),
                       ("CSV template (headings only)", "*.csv")])
        if not p:
            return
        try:
            write_docs_template(Path(p), self.schema)
        except Exception as e:  # noqa
            messagebox.showerror(APP_NAME, f"Could not save the template:\n{e}")
            return
        self.db.set_setting("last_template_dir", str(Path(p).parent))
        self.settings = self.db.get_settings()
        self.set_status(f"Template saved: {p}")
        if messagebox.askyesno(APP_NAME, f"Template saved:\n{p}\n\nOpen the folder now?"):
            open_folder(Path(p).parent)

    def doc_upload(self):
        """Upload a filled Documents file (template layout). Strict validation - all or nothing."""
        if not self.need_project():
            return
        p = filedialog.askopenfilename(
            title="Select the filled Documents file",
            initialdir=self.settings.get("last_template_dir") or str(Path.home()),
            filetypes=[("Documents file (Excel or CSV)", "*.xlsx *.xlsm *.xls *.csv"), ("All files", "*.*")])
        if not p:
            return
        try:
            series, problems = read_docs_template(Path(p), self.schema)
        except ValueError as e:
            messagebox.showerror(APP_NAME, str(e))
            return
        if problems:
            shown = "\n".join(problems[:25]) + (f"\n... and {len(problems) - 25} more" if len(problems) > 25 else "")
            messagebox.showwarning(APP_NAME, "The file was NOT imported. Fix these rows in the file and upload again:\n\n"
                                   + shown)
            return
        mode = "replace"
        if any(d.origin != "derived" for d in self.docs):
            ans = messagebox.askyesnocancel(
                APP_NAME, f"{len(series)} series found in the file.\n\nYes = REPLACE the existing document register\n"
                          "No = ADD to the existing register\nCancel = do nothing")
            if ans is None:
                return
            mode = "replace" if ans else "add"
        self.docs = merge_docs(self.docs, series, mode)
        self.db.set_setting("last_template_dir", str(Path(p).parent))
        self.settings = self.db.get_settings()
        self.db.audit(self.project["id"], "Documents file uploaded", f"{Path(p).name}: {len(series)} series")
        self._docs_changed()
        self.set_status(f"{len(series)} document series imported from {Path(p).name}.")

    def doc_generate(self):
        """Create documents.csv from the document register alone; the user chooses the folder."""
        if not self.need_project():
            return
        if not self.docs:
            messagebox.showinfo(APP_NAME, "The document register is empty. Upload the Master Template (Documents sheet) "
                                          "or the stand-alone Documents file first.")
            return
        derived = [d for d in self.docs if d.origin == "derived"]
        if derived and not messagebox.askyesno(
                APP_NAME, f"{len(derived)} series were only suggested from the received invoices and are unverified.\n\n"
                          "Generate documents.csv anyway?", icon="warning"):
            return
        chosen = filedialog.askdirectory(
            title="Select the folder where documents.csv should be saved", mustexist=True,
            initialdir=self.settings.get("last_output_dir") or str(Path.home()))
        if not chosen:
            self.set_status("Cancelled - no folder was selected.")
            return
        self.db.set_setting("last_output_dir", chosen)
        self.settings = self.db.get_settings()

        def confirm(names):
            return messagebox.askyesno(APP_NAME, f"{names[0]} already exists. Overwrite?", icon="warning")
        try:
            r = export_documents_only(self.client, self.project, self.docs, Path(chosen), confirm)
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e))
            return
        except Exception as e:  # noqa
            log.exception("documents.csv export failed")
            messagebox.showerror(APP_NAME, f"Could not create documents.csv: {e}")
            return
        self.last_export = r["file"].parent
        self.db.audit(self.project["id"], "documents.csv generated",
                      f"rows={r['rows']} schema={r['schema_version']} sha256={r['sha256'][:16]}")
        messagebox.showinfo(APP_NAME, f"documents.csv saved ({r['rows']} series):\n{r['file']}")
        self.set_status(f"documents.csv saved: {r['file']}")

    def doc_suggest(self):
        """One series per unbroken run of numbers: 1001-1009 and 1014-1023 become two rows."""
        if not self.need_project():
            return
        from .series import entries_from_lines, entries_from_sets, build_runs, runs_to_docs, gap_report, auto_mode
        entries = entries_from_lines(self.lines) + entries_from_sets(self.sets)
        if not entries:
            messagebox.showinfo(APP_NAME, "There are no invoices or notes yet - upload invoice files or the Master "
                                "Template first.")
            return
        if any(d.origin == "verified" for d in self.docs) and not messagebox.askyesno(
                APP_NAME, "Series you marked as VERIFIED will be replaced by the freshly built ones (typed and uploaded "
                          "series are kept).\n\nContinue?"):
            return
        self.docs_lock = False
        self._auto_series()
        n = sum(1 for d in self.docs if d.origin == "derived")
        mode = "customer" if any(d.source_file.startswith("customer ") for d in self.docs if d.origin == "derived") else "prefix"
        runs = [None] * n
        self._docs_changed()
        self.set_status(f"{len(runs)} document series built ({'by customer' if mode == 'customer' else 'by prefix'}); "
                        "check the cancelled counts against the client's register.")

    def doc_verify(self):
        """Staff confirmation: the selected suggested series (all of them when none is selected) are correct."""
        if not self.need_project():
            return
        sel = [self.docs[self.doc_tree.index(i)] for i in self.doc_tree.selection()]
        todo = [d for d in (sel or self.docs) if d.origin == "derived"]
        if not todo:
            messagebox.showinfo(APP_NAME, "Nothing to verify - no suggested series is selected.")
            return
        if not messagebox.askyesno(APP_NAME, f"Confirm {len(todo)} series as correct?\n\nYou have checked the cancelled "
                                   "counts and the missing numbers against the client's invoice register."):
            return
        for d in todo:
            d.origin = "verified"
        self._docs_changed()
        self.set_status(f"{len(todo)} series marked as verified.")

    def _docs_changed(self):
        self.db.audit(self.project["id"], "Document register changed", f"{len(self.docs)} series")
        self.run_checks()
        self.refresh_documents()

    # ---------------------------------------------------------- 10 CSV Preview
    def _tab_previews(self):
        f = self.tab("10 CSV Preview")
        ttk.Label(f, text="CSV Preview - exactly what will be written for the Offline Tool", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        ttk.Label(bar, text="Table:").pack(side="left")
        self.prev_pick = ttk.Combobox(bar, state="readonly", width=95)
        self.prev_pick.pack(side="left", padx=4)
        self.prev_pick.bind("<<ComboboxSelected>>", lambda e: self._show_preview())
        ttk.Button(bar, text="Refresh", command=self.refresh_previews).pack(side="left", padx=3)
        ttk.Label(f, text="Contains approved invoice lines (Excel/PDF) and all uploaded Master Template rows, "
                          "aggregated as the Offline Tool expects.", foreground="#555").pack(anchor="w")
        fr, self.prev_tree = make_tree(f, [("c0", "-", 100)], height=22)
        fr.pack(fill="both", expand=True)
        self.prev_note = tk.StringVar()
        ttk.Label(f, textvariable=self.prev_note, style="Warn.TLabel", wraplength=1150).pack(anchor="w")
        self.prev_final = {}

    def refresh_previews(self):
        out = self.compute_outputs() if self.project else None
        self.prev_final = out["final"] if out else {}
        keys = list(self.schema["tables"])
        labels = [f"{self.schema['tables'][k]['title']}   [{self.schema['tables'][k]['filename']}]   -   "
                  f"{len(self.prev_final.get(k, []))} row(s)" for k in keys]
        cur = self.prev_pick.current()
        self.prev_pick["values"] = labels
        if labels:
            self.prev_pick.current(cur if cur >= 0 else 0)
        self.prev_note.set(headers_status(self.schema)[2] if self.schema else "")
        self._show_preview()

    def _show_preview(self):
        t = self.prev_tree
        clear(t)
        i = self.prev_pick.current()
        keys = list(self.schema["tables"])
        if i < 0 or i >= len(keys):
            return
        key = keys[i]
        cols = self.schema["tables"][key]["columns"]
        ids = [f"c{n}" for n in range(len(cols))]
        t.configure(columns=ids)
        for cid, c in zip(ids, cols):
            t.heading(cid, text=c["header"], command=lambda x=cid: sort_tree(t, x))
            t.column(cid, width=max(70, min(220, len(c["header"]) * 9)), anchor="w", stretch=True)
        for r in self.prev_final.get(key, []):
            t.insert("", "end", values=[gstr1.format_cell(c, r.get(c["source"], ""), self.schema) for c in cols])

    # ---------------------------------------------------------- 11 GSTR-1 Summary
    def _tab_summary(self):
        f = self.tab("11 GSTR-1 Summary")
        ttk.Label(f, text="GSTR-1 Summary and Reconciliation", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="Refresh", command=self.refresh_summary).pack(side="left", padx=3)
        ttk.Button(bar, text="Export Summary to Excel", command=self.export_summary).pack(side="left", padx=3)
        ttk.Label(f, foreground="#555", wraplength=1150,
                  text="Tax is calculated as taxable value x rate (credit notes negative). Review this summary against the "
                       "client's books and against the Offline Tool summary before filing.").pack(anchor="w")
        fr, self.sum_tree = make_tree(f, [("t", "Table", 330), ("r", "Rows", 50), ("d", "Docs", 60), ("tx", "Taxable value", 110),
                                          ("i", "IGST", 100), ("c", "CGST", 100), ("s", "SGST/UTGST", 100), ("ce", "Cess", 80),
                                          ("tot", "Total", 110), ("n", "Note", 330)], height=14)
        fr.pack(fill="both", expand=True)
        ttk.Label(f, text="Reconciliation", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        fr, self.sum_rec = make_tree(f, [("c", "Check", 560), ("s", "Source", 100), ("p", "Processed", 100),
                                         ("d", "Difference", 90), ("st", "Status", 90), ("n", "Note", 300)], height=7)
        fr.pack(fill="x")

    @staticmethod
    def _money(v):
        return f"{v:,.2f}" if isinstance(v, Decimal) else ("" if v is None else str(v))

    def refresh_summary(self):
        clear(self.sum_tree)
        clear(self.sum_rec)
        out = self.compute_outputs() if self.project else None
        if not out:
            return
        for r in summary_frame(out["summary"]).to_dict("records"):
            total = str(r["Table"]).startswith("TOTAL")
            self.sum_tree.insert("", "end", tags=("approved",) if total else (), values=(
                r["Table"], r["Rows"], r["Documents"], self._money(r["Taxable value"]), self._money(r["IGST"]),
                self._money(r["CGST"]), self._money(r["SGST/UTGST"]), self._money(r["Cess"]), self._money(r["Total"]),
                r["Note"]))
        self._fill_recon(self.sum_rec, out["recon"])

    @staticmethod
    def _fill_recon(tree, rows):
        for r in rows:
            tag = {"DIFFERENCE": "error", "INFO": "warning"}.get(r["status"], "approved")
            tree.insert("", "end", tags=(tag,), values=(r["check"], r["source"], r["processed"], r["difference"],
                                                        r["status"], r["note"]))

    def export_summary(self):
        if not self.need_project():
            return
        out = self.compute_outputs()
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=f"gstr1_summary_{self.client['gstin']}_{self.project['year']}_{self.project['month']:02d}.xlsx")
        if p:
            summary_frame(out["summary"]).to_excel(p, sheet_name="Summary", index=False)
            self.set_status(f"Summary saved: {p}")

    # ---------------------------------------------------------- 9 Export
    def _tab_export(self):
        f = self.tab("12 Export")
        ttk.Label(f, text="Export - generate every GSTR-1 CSV file", style="Head.TLabel").pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=4)
        self.out_var = tk.StringVar(value="")
        ttk.Label(row, text="Last export folder:").pack(side="left")
        ttk.Entry(row, textvariable=self.out_var, width=80, state="readonly").pack(side="left", padx=4)
        ttk.Label(f, foreground="#555", wraplength=1150,
                  text="When you click 'Generate CSV Files' the application asks you to select the folder where the "
                       "output is saved (on any drive). Files are written to  <selected folder>/clients/<GSTIN>/"
                       "FY_xxxx_xx/GSTR1_<year>_<month>/output").pack(anchor="w")
        ov = ttk.LabelFrame(f, text="Unresolved errors", padding=6)
        ov.pack(fill="x", pady=6)
        self.ov_var = tk.BooleanVar()
        self.ov_reason = tk.StringVar()
        ttk.Checkbutton(ov, variable=self.ov_var, text="Override remaining errors on approved records. Reason (mandatory, recorded in audit trail):").pack(side="left")
        ttk.Entry(ov, textvariable=self.ov_reason, width=50).pack(side="left", padx=4)
        bar = ttk.Frame(f)
        bar.pack(anchor="w", pady=4)
        ttk.Button(bar, text="Generate CSV Files", command=self.generate).pack(side="left", padx=3)
        ttk.Button(bar, text="Open Output Folder", command=self.open_output).pack(side="left", padx=3)
        ttk.Button(bar, text="Export Exception Report", command=self.export_exceptions).pack(side="left", padx=3)
        self.sch_lbl = tk.StringVar()
        ttk.Label(f, textvariable=self.sch_lbl, style="Warn.TLabel", wraplength=1150).pack(anchor="w", pady=2)
        self.exp_text = tk.Text(f, wrap="word", height=22, background="#fafafa")
        self.exp_text.pack(fill="both", expand=True)
        self._write_guide()

    def _schema_label(self):
        n, tot, text = headers_status(self.schema)
        self.sch_lbl.set(f"Export schema {self.schema['schema_version']}: {text}. "
                         + ("" if n == tot else "Use Settings > 'Compare with official Offline Tool samples' and do a test "
                            "import of every file."))

    GUIDE = (
        "HOW TO USE THE GENERATED FILES WITH THE OFFICIAL GST OFFLINE TOOL\n"
        "1. Download the current GSTR-1 Offline Tool and its sample CSV templates from the GST Portal "
        "(Downloads > Offline Tools). Install it.\n"
        "2. In this application: Settings > 'Compare with official Offline Tool samples' - select the folder with the "
        "official sample CSV files; matching headings are adopted automatically, differences are listed.\n"
        "3. In the Offline Tool, import each generated CSV (b2b, b2cl, b2cs, exp, cdnr, cdnur, exemp, at, atadj, hsn, "
        "documents and the amendment files b2ba, b2cla, b2csa, expa, cdnra, cdnura, ata, atadja) into its section as "
        "described in the tool's own instructions. Fix any import error it reports here, regenerate and re-import.\n"
        "4. Compare the Offline Tool's summary with the 'GSTR-1 Summary' tab. Enter manually anything listed in the "
        "exception report under 'Manual reporting required'.\n"
        "5. Use the tool to validate and generate the GSTR-1 JSON file.\n"
        "6. The authorised taxpayer/professional uploads the JSON on the GST Portal, reviews the summary, and files "
        "with their own authentication (DSC/EVC). This application never logs in to or submits to the portal.\n"
        "7. Keep the output folder (source files, reports, manifest.json) as your working papers; keep secure backups.\n")

    def _write_guide(self, extra=""):
        self.exp_text.configure(state="normal")
        self.exp_text.delete("1.0", "end")
        self.exp_text.insert("end", extra + self.GUIDE)
        self.exp_text.configure(state="disabled")

    def generate(self):
        if not self.need_project():
            return
        self.run_checks()
        chosen = filedialog.askdirectory(
            title="Select the folder where the GSTR-1 output files should be saved", mustexist=True,
            initialdir=self.settings.get("last_output_dir") or str(Path.home()))
        if not chosen:
            self.set_status("Export cancelled - no folder was selected.")
            return
        base = Path(chosen)
        self.db.set_setting("last_output_dir", str(base))
        self.settings = self.db.get_settings()

        def confirm(names):
            return messagebox.askyesno(APP_NAME, "These files already exist and will be overwritten:\n\n  " +
                                       "\n  ".join(names) + "\n\nOverwrite?", icon="warning")
        try:
            r = export_project(self.client, self.project, self.lines, self.sets, self.docs, self.issues,
                               self.settings, base, override=self.ov_var.get(), override_reason=self.ov_reason.get(),
                               confirm_overwrite=confirm)
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e))
            return
        except Exception as e:  # noqa
            log.exception("Export failed")
            messagebox.showerror(APP_NAME, f"Export failed: {e}")
            return
        status = "Generated - PROVISIONAL schema" if not r["verified"] else "Generated"
        self.db.set_csv_status(self.project["id"], status)
        self.project["csv_status"] = status
        self.last_export = r["folder"]
        self.out_var.set(str(base))
        rows = r["rows"]
        detail = (f"schema={r['schema_version']}; rows={rows}; files={r['files']}; override={r['overrode']} "
                  f"reason={self.ov_reason.get()}")
        self.db.audit(self.project["id"], "CSV generated", detail)
        warn = sum(1 for i in self.issues if i.severity == "Warning")
        diff = sum(1 for x in r["recon"] if x["status"] == "DIFFERENCE")
        text = (f"DONE. Files saved in:\n{r['folder']}\n\n  CSV files written:\n" +
                "".join(f"    {self.schema['tables'][k]['filename']:14} {n} row(s)\n" for k, n in rows.items()) +
                f"\n  Also written: gstr1_summary.xlsx, validation_report.xlsx ({warn} warning(s)), "
                f"reconciliation_report.xlsx ({diff} difference(s)), manifest.json\n")
        missing = [self.schema["tables"][k]["filename"] for k in ("hsn", "docs") if k not in rows]
        if missing:
            text += (f"\n  NOTE: {', '.join(missing)} not written - no data. HSN (Table 12) and Documents (Table 13) "
                     "are mandatory in GSTR-1: fill them in the Master Template (or the Documents tab).\n")
        if not r["verified"]:
            text += f"\n  NOTE: {r['header_status']}. Verify against the official Offline Tool before use.\n"
        self._write_guide(text + "\n")
        self.set_status("CSV files generated.")

    def open_output(self):
        if not self.need_project():
            return
        if not self.last_export or not Path(self.last_export).exists():
            last = self.settings.get("last_output_dir")
            guess = project_dir(self.client, self.project, Path(last)) / "output" if last else None
            if not guess or not guess.exists():
                messagebox.showinfo(APP_NAME, "No output folder yet. Click 'Generate CSV Files' and choose a folder first.")
                return
            self.last_export = guess
        open_folder(Path(self.last_export))

    # ---------------------------------------------------------- 10 History
    def _tab_history(self):
        f = self.tab("13 History")
        ttk.Label(f, text="Processing History (files, hashes, corrections, exports)", style="Head.TLabel").pack(anchor="w")
        fr, self.hist_files = make_tree(f, [("f", "File", 220), ("sha", "SHA-256 (first 16)", 160), ("st", "Status", 120),
                                            ("n", "Records", 70), ("when", "Processed", 150)], height=6)
        fr.pack(fill="x")
        fr, self.hist_tree = make_tree(f, [("ts", "Time", 140), ("op", "Operator", 100), ("a", "Action", 170),
                                           ("d", "Detail", 800)], height=14)
        fr.pack(fill="both", expand=True, pady=6)

    def refresh_history(self):
        clear(self.hist_files)
        clear(self.hist_tree)
        if not self.project:
            return
        for r in self.db.files(self.project["id"]):
            self.hist_files.insert("", "end", values=(r["filename"], (r["sha256"] or "")[:16], r["status"],
                                                      r["records"], r["processed_at"] or ""))
        for r in self.db.audit_log(self.project["id"]):
            self.hist_tree.insert("", "end", values=(r["ts"], r["operator"], r["action"], r["detail"]))

    # ---------------------------------------------------------- 11 Settings
    # ---------------------------------------------------------- 15 YTD & Annual
    def _tab_annual(self):
        f = self.tab("15 YTD & Annual")
        ttk.Label(f, text="Year-to-date view and annual reconciliation (GSTR-9 preparation)", style="Head.TLabel").pack(anchor="w")
        ttk.Label(f, foreground="#555", wraplength=1150, text=(
            "Shows every return of the opened client for one financial year side by side. Upload the whole year at once "
            "(a folder or a zip with the month files - Master Templates, registers, invoices and the filed GSTR-1 / 3B / 9 "
            "PDFs), or build each month in tabs 4/5. The Reconciliation table compares books, GSTR-1, GSTR-3B and "
            "GSTR-9; the GSTR-9 worksheet arranges the year totals like GSTR-9 Tables 4 and 5.")).pack(anchor="w", pady=2)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        ttk.Label(bar, text="Financial year").pack(side="left")
        self.an_fy = tk.StringVar()
        self.an_fy_cb = ttk.Combobox(bar, textvariable=self.an_fy, width=10, state="readonly")
        self.an_fy_cb.pack(side="left", padx=4)
        self.an_fy_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_annual())
        ttk.Button(bar, text="Refresh", command=self.refresh_annual).pack(side="left", padx=3)
        ttk.Button(bar, text="Enter GSTR-3B / books figures for selected month...", command=self.annual_entry).pack(side="left", padx=3)
        ttk.Button(bar, text="Export to Excel", command=self.annual_export).pack(side="left", padx=3)
        bar2 = ttk.Frame(f)
        bar2.pack(fill="x", pady=2)
        ttk.Button(bar2, text="Upload whole year: folder...", command=lambda: self.year_upload("folder")).pack(side="left", padx=3)
        ttk.Button(bar2, text="Upload whole year: zip file...", command=lambda: self.year_upload("zip")).pack(side="left", padx=3)
        ttk.Button(bar2, text="Upload filed GSTR-1 / 3B / 9 (PDF)...", command=lambda: self.year_upload("returns")
                   ).pack(side="left", padx=3)
        ttk.Button(bar2, text="Remove selected filed return", command=self.remove_filed_return).pack(side="left", padx=3)
        ttk.Button(bar2, text="Open month of selected row", command=self.annual_open_month).pack(side="left", padx=3)
        ttk.Button(bar2, text="Enter GSTR-9C figures...", command=self.ninec_entry).pack(side="left", padx=3)
        self.an_info = tk.StringVar()
        ttk.Label(f, textvariable=self.an_info, foreground="#1F3864").pack(anchor="w")
        nb = ttk.Notebook(f)
        nb.pack(fill="both", expand=True)
        a = ttk.Frame(nb, padding=4)
        b = ttk.Frame(nb, padding=4)
        c = ttk.Frame(nb, padding=4)
        nb.add(a, text="Year to date")
        nb.add(b, text="Books vs GSTR-3B")
        nb.add(c, text="GSTR-9 worksheet")
        d = ttk.Frame(nb, padding=4)
        e = ttk.Frame(nb, padding=4)
        nb.add(d, text="Reconciliation (books / GSTR-1 / 3B / 9)")
        nb.add(e, text="Filed returns uploaded")
        self.an_nb, self.an_rc_tab = nb, d
        ttk.Label(d, foreground="#555", wraplength=1150, text=(
            "One table for each comparison. Red = difference above Rs 1, yellow = missing / information, green = "
            "matches. Difference = first source - second source. Double-click a row for the reason and the remedy. "
            "GSTR-1 vs GSTR-3B follows the portal's auto-fill of Table 3.1 from GSTR-1 (amendments and credit / debit "
            "notes included; reverse-charge supplies carry no tax for the supplier).")).pack(anchor="w")
        self.an_rc_nb = ttk.Notebook(d)
        self.an_rc_nb.pack(fill="both", expand=True, pady=3)
        self.an_rc_trees = []
        for name, areas, s1, s2 in recon.RECON_TABLES:
            fr0 = ttk.Frame(self.an_rc_nb, padding=2)
            self.an_rc_nb.add(fr0, text=name)
            if s1:
                cols = [("st", "Status", 70), ("per", "Period", 80), ("chk", "Check", 280),
                        ("av", f"{s1} value", 120), ("at", f"{s1} tax", 100), ("bv", f"{s2} value", 120),
                        ("bt", f"{s2} tax", 100), ("dv", f"Difference value ({s1} - {s2})", 170),
                        ("dtx", f"Difference tax ({s1} - {s2})", 160), ("why", "Likely reason / action", 420),
                        ("src", "Figures compared", 320)]
            else:
                cols = [("st", "Status", 80), ("per", "Period", 90), ("chk", "Check", 260), ("src", "Detail", 320),
                        ("why", "Action", 600)]
            fr, tree = make_tree(fr0, cols, height=15)
            fr.pack(fill="both", expand=True)
            tree.bind("<Double-1>", lambda e_, t=tree: self.recon_row_detail(t))
            self.an_rc_trees.append((name, areas, bool(s1), tree))
        self.an_rc = self.an_rc_trees[0][3]
        cols = [("form", "Return", 70), ("per", "Period", 80), ("file", "File", 260), ("arn", "ARN date", 80),
                ("fig", "Key figures", 520), ("note", "Notes", 300)]
        fr, self.an_filed = make_tree(e, cols, height=16)
        fr.pack(fill="both", expand=True)
        cols = [("m", "Month", 80), ("b2b", "B2B", 95), ("b2cl", "B2CL", 80), ("b2cs", "B2CS", 95), ("ex", "Exports", 80),
                ("cdn", "Notes (net)", 80), ("tx", "Total taxable", 105), ("nil", "Nil/Exempt", 85), ("i", "IGST", 85),
                ("c", "CGST", 85), ("s", "SGST", 85), ("ce", "Cess", 60), ("tt", "Total tax", 95), ("d", "Invoices", 65),
                ("st", "Status / flags", 420)]
        fr, self.an_tree = make_tree(a, cols, height=16)
        fr.pack(fill="both", expand=True)
        cols = [("m", "Month", 80), ("g1", "Books (app) taxable", 120), ("g1n", "Books (app) nil/exempt", 130), ("g1t", "Books (app) tax", 110),
                ("bv", "3B outward value", 110), ("bt", "3B tax", 95), ("bk", "Books taxable", 105),
                ("dv", "Diff value (Books taxable + nil - 3B)", 210), ("dt", "Diff tax (Books - 3B)", 125), ("dk", "Diff (app - books of account)", 170)]
        fr, self.an_rec = make_tree(b, cols, height=16)
        fr.pack(fill="both", expand=True)
        self.an_rec.bind("<Double-1>", lambda e: self.annual_entry())
        self.an_tree.bind("<Double-1>", lambda e: self.annual_entry())
        cols = [("t", "Table", 60), ("d", "Description", 520), ("tx", "Taxable value", 120), ("c", "Central tax", 110),
                ("s", "State/UT tax", 110), ("i", "Integrated tax", 110), ("ce", "Cess", 80)]
        fr, self.an_g9 = make_tree(c, cols, height=16)
        fr.pack(fill="both", expand=True)
        self._an_year = None

    def _an_client(self):
        if not self.client:
            messagebox.showinfo(APP_NAME, "Open a return of the client first (tabs 2 and 3); the year view is built from "
                                          "all returns of that client.")
            return None
        return self.client

    def refresh_annual(self):
        for t in (self.an_tree, self.an_rec, self.an_g9, self.an_filed) + tuple(x[3] for x in self.an_rc_trees):
            clear(t)
        if not self.client:
            self.an_info.set("Open a return of the client first.")
            return
        fys = sorted({p["fy"] for p in self.db.projects(self.client["id"]) if p.get("fy")}, reverse=True)
        cur = self.project["fy"] if self.project else (fys[0] if fys else fin_year(8, 2026))
        for extra in (cur, annual.previous_fy(cur)):
            if extra not in fys:
                fys.append(extra)
        fys = sorted(set(fys), reverse=True)
        self.an_fy_cb["values"] = fys
        if self.an_fy.get() not in fys:
            self.an_fy.set(cur)
        fy = self.an_fy.get()
        y = annual.build_year(self.db, self.client, fy, self.settings, self.schema)
        self._an_year = y
        m = self._money
        have = 0
        for r in y["months"]:
            c = annual.month_columns(r)
            t = c["total"]
            mm = r["m"] if r["has_data"] else None
            have += 1 if r["has_data"] else 0
            if r["has_data"]:
                st = "; ".join(r["flags"]) if r["flags"] else "OK"
            else:
                st = ("; ".join(r["flags"]) if r["flags"] else "No return / no data")
            tag = () if r["has_data"] and not r["flags"] else (("warning",) if r["flags"] or r["has_data"] else ("rejected",))
            self.an_tree.insert("", "end", iid=r["label"], tags=tag, values=(
                r["label"], m(c["b2b"]["taxable"]), m(c["b2cl"]["taxable"]), m(c["b2cs"]["taxable"]), m(c["exp"]["taxable"]),
                m(c["cdn"]["taxable"]), m(t["taxable"]), m(c["nilex"]["taxable"]), m(t["igst"]), m(t["cgst"]), m(t["sgst"]),
                m(t["cess"]), m(t["igst"] + t["cgst"] + t["sgst"] + t["cess"]), mm["docs_total"] if mm else "", st))
        T, tot = y["tot"], y["totals"]
        tt = T["total"]
        self.an_tree.insert("", "end", tags=("approved",), values=(
            "TOTAL", m(T["b2b"]["taxable"]), m(T["b2cl"]["taxable"]), m(T["b2cs"]["taxable"]), m(T["exp"]["taxable"]),
            m(T["cdn"]["taxable"]), m(tt["taxable"]), m(T["nilex"]["taxable"]), m(tt["igst"]), m(tt["cgst"]), m(tt["sgst"]),
            m(tt["cess"]), m(tt["igst"] + tt["cgst"] + tt["sgst"] + tt["cess"]), tot["docs_total"], f"{have} of 12 months have data"))
        dr, dt = annual.diff_rows(y)
        for r, d in zip(y["months"], dr):
            tag = ()
            if d["entered"] and (abs(d["d_3b_taxable"]) > 1 or abs(d["d_3b_tax"]) > 1):
                tag = ("error",)
            self.an_rec.insert("", "end", iid="r" + r["label"], tags=tag, values=(
                d["label"], m(d["g1_taxable"]), m(d["g1_nil"]), m(d["g1_tax"]), m(d["tb_taxable"]) if d["entered"] else "",
                m(d["tb_tax"]) if d["entered"] else "", m(d["bk_taxable"]) if d["bk_taxable"] else "",
                m(d["d_3b_taxable"]) if d["entered"] else "", m(d["d_3b_tax"]) if d["entered"] else "",
                m(d["d_bk_taxable"]) if d["bk_taxable"] else ""))
        nil = sum((d["g1_nil"] for d in dr), ZERO_D)
        self.an_rec.insert("", "end", tags=("approved",), values=(
            "TOTAL", m(dt["g1_taxable"] - nil), m(nil), m(dt["g1_tax"]), m(dt["tb_taxable"]), m(dt["tb_tax"]), m(dt["bk_taxable"]),
            m(dt["g1_taxable"] - dt["tb_taxable"]), m(dt["g1_tax"] - dt["tb_tax"]), m(dt["g1_taxable"] - dt["bk_taxable"])))
        for code, label in annual.G9_ROWS:
            v = y["g9"][code]
            self.an_g9.insert("", "end", values=(code, label, m(v["taxable"]), m(v["cgst"]), m(v["sgst"]), m(v["igst"]),
                                                 m(v["cess"])))
        clear(self.an_filed)
        rows = recon.build(self.db, self.client, fy, y)
        self._an_recon = rows
        self.fill_recon_table()
        self._an_filed = recon.filed_list(self.db, self.client["id"], fy)
        for i, r in enumerate(self._an_filed):
            self.an_filed.insert("", "end", iid=f"fr{i}", values=(r["form"], r["period"], r["file"], r["arn"],
                                                                   r["figures"], r["notes"]))
        cnt = recon.summary_counts(rows)
        self.an_info.set(f"{self.client['name']}  |  FY {fy}  |  {have} of 12 months have data"
                         + ("  |  quarterly (QRMP) client" if y["qrmp"] else "")
                         + f"  |  filed returns: {len(self._an_filed)}  |  reconciliation: {cnt['DIFF']} difference(s), "
                           f"{cnt['MISSING']} missing, {cnt['OK']} matching")

    def ninec_entry(self):
        """GSTR-9C turnover figures typed from the certified reconciliation statement (kept per client and FY)."""
        if not self._an_client():
            return
        fy = self.an_fy.get()
        if not fy:
            messagebox.showinfo(APP_NAME, "Choose the financial year first.")
            return
        entries = annual.load_entries(self.db, self.client["id"], fy)
        cur = entries.get(annual.ANNUAL_KEY, {})
        win = tk.Toplevel(self)
        win.title(f"GSTR-9C figures - FY {fy}")
        win.transient(self)
        ttk.Label(win, text=f"{self.client['name']}  FY {fy}: type the figures from GSTR-9C Part II Table 5",
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=8)
        vars_ = {}
        for i, (k, label) in enumerate(annual.NINEC_FIELDS, 1):
            ttk.Label(win, text=label, wraplength=520, justify="left").grid(row=i, column=0, sticky="w", padx=10, pady=4)
            vars_[k] = tk.StringVar(value=str(cur.get(k, "")))
            ttk.Entry(win, textvariable=vars_[k], width=18, justify="right").grid(row=i, column=1, padx=10)

        def ok():
            ann = dict(entries.get(annual.ANNUAL_KEY, {}))
            for k, v in vars_.items():
                t = v.get().strip().replace(",", "")
                if t:
                    ann[k] = t
                else:
                    ann.pop(k, None)
            entries[annual.ANNUAL_KEY] = ann
            annual.save_entries(self.db, self.client["id"], fy, entries)
            win.destroy()
            self.refresh_annual()
        ttk.Button(win, text="Save", command=ok).grid(row=len(vars_) + 1, column=0, columnspan=2, pady=10)

    def fill_recon_table(self):
        """Fill the table of each comparison; the tab names show how many differences each has."""
        tagmap = {recon.DIFF: ("error",), recon.MISSING: ("warning",), recon.INFO: ("warning",), recon.OK: ("approved",)}
        m = self._money
        mm = lambda v: "" if v is None else m(v)   # noqa: E731
        rows = getattr(self, "_an_recon", [])
        total = 0
        for k, (name, areas, full, tree) in enumerate(self.an_rc_trees):
            clear(tree)
            n_bad = 0
            for i, r in enumerate(rows):
                if r["area"] not in areas:
                    continue
                total += 1
                n_bad += r["status"] in (recon.DIFF, recon.MISSING)
                if full:
                    vals = (r["status"], r["period"], r["check"], mm(r["a_value"]), mm(r["a_tax"]), mm(r["b_value"]),
                            mm(r["b_tax"]), mm(r["d_value"]), mm(r["d_tax"]), r["reason"],
                            f"{r['a_name']}  vs  {r['b_name']}")
                else:
                    vals = (r["status"], r["period"], r["check"], r["a_name"], r["reason"])
                tree.insert("", "end", iid=f"rc{i}", tags=tagmap.get(r["status"], ()), values=vals)
            try:
                self.an_rc_nb.tab(k, text=f"{name}  ({n_bad})" if n_bad else name)
            except Exception:  # noqa
                pass
        return total

    # ---- whole-year upload and filed returns
    def year_upload(self, mode):
        if not self._an_client():
            return
        fy = self.an_fy.get() or (self.project["fy"] if self.project else "")
        if not fy:
            messagebox.showinfo(APP_NAME, "Choose the financial year first.")
            return
        if mode == "folder":
            src = filedialog.askdirectory(title=f"Folder with the files of FY {fy} (sub-folders and zips are read too)")
        elif mode == "zip":
            src = filedialog.askopenfilename(title=f"Zip file with the files of FY {fy}",
                                             filetypes=[("Zip file", "*.zip"), ("All files", "*.*")])
        else:
            src = filedialog.askopenfilenames(title="Filed GSTR-1 / GSTR-3B / GSTR-9 returns (PDF from the GST portal)",
                                              filetypes=[("PDF", "*.pdf"), ("All files", "*.*")])
            src = list(src)
        if not src:
            return
        self.set_status("Reading the files ... (PDF returns and scanned files can take a while)")

        def prog(i, n, name):
            self.set_status(f"Reading {i + 1} of {n}: {name}")
        try:
            entries, tmp = yearimport.scan(src, fy, self.settings, progress=prog)
        except Exception as ex:  # noqa
            log.exception("Year scan failed")
            messagebox.showerror(APP_NAME, f"The files could not be read:\n{ex}")
            return
        if not entries:
            messagebox.showinfo(APP_NAME, "No files found.")
            return
        dlg = YearImportDialog(self, fy, entries, self.client)
        if not dlg.result:
            self.set_status("Year upload cancelled.")
            return
        log_rows = yearimport.import_entries(self.db, self.client, dlg.result, self.settings, self.schema, progress=prog,
                                             approve_clean=getattr(dlg, "approve_clean", False))
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        if self.project:                                   # reload the open month: it may have received data
            self.open_project(self.client, self.project["id"])
            self.goto("YTD")
        self.refresh_annual()
        bad = [r for r in log_rows if not r[3]]
        text = "\n".join(f"{'OK   ' if r[3] else 'CHECK'}  {r[1]:>9}  {r[0]}: {r[2]}" for r in log_rows[:25])
        more = f"\n... and {len(log_rows) - 25} more" if len(log_rows) > 25 else ""
        if messagebox.askyesno(APP_NAME, f"{len(log_rows)} file(s) processed, {len(bad)} need checking.\n\n{text}{more}"
                                         "\n\nSave this list as an Excel file?"):
            p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                             initialfile=f"Year_upload_{self.client['gstin']}_FY{fy}.xlsx")
            if p:
                yearimport.write_log(p, self.client, fy, log_rows)
        self.set_status(f"Year upload finished: {len(log_rows)} file(s), {len(bad)} to check. See the Reconciliation table.")

    def remove_filed_return(self):
        if not self._an_client():
            return
        sel = [s_ for s_ in self.an_filed.selection() if s_.startswith("fr")]
        if not sel:
            messagebox.showinfo(APP_NAME, "Select the return(s) in the 'Filed returns uploaded' table first.")
            return
        rows = [self._an_filed[int(s_[2:])] for s_ in sel]
        if not messagebox.askyesno(APP_NAME, "Remove these filed returns from the reconciliation?\n\n" +
                                   "\n".join(f"{r['form']} {r['period']}  ({r['file']})" for r in rows)):
            return
        fy = self.an_fy.get()
        for r in rows:
            filed_returns.remove_return(self.db, self.client["id"], fy, r["form"], r["key"])
        self.refresh_annual()

    def recon_row_detail(self, tree=None):
        """Double-click on a reconciliation row: what the row means and how to put it right."""
        tree = tree or self.an_rc
        self.an_rc = tree
        sel = tree.selection()
        rows = getattr(self, "_an_recon", [])
        if not sel or not sel[0].startswith("rc") or int(sel[0][2:]) >= len(rows):
            return
        r = rows[int(sel[0][2:])]
        m = lambda v: "-" if v is None else self._money(v)   # noqa: E731
        fix = recon.how_to_fix(r)
        is_month = r["period"] in {x["label"] for x in (self._an_year or {}).get("months", [])}
        text = (f"{r['check']}  ({r['period']})\n\n"
                f"{r['a_name'] or 'Source 1'}:  value {m(r['a_value'])}   tax {m(r['a_tax'])}\n"
                f"{r['b_name'] or 'Source 2'}:  value {m(r['b_value'])}   tax {m(r['b_tax'])}\n"
                f"Difference ({r['a_name'] or '1'} - {r['b_name'] or '2'}):  value {m(r['d_value'])}   "
                f"tax {m(r['d_tax'])}\n\n"
                f"Status: {r['status']}\n{r['reason']}\n\nHow to put it right:\n{fix}")
        target = "Invoice Review" if r["area"] == "Books vs GSTR-1" else "GSTR-1 Summary"
        if is_month and messagebox.askyesno(APP_NAME, text + f"\n\nOpen the {r['period']} return now "
                                            f"(tab: {target})?"):
            self.annual_open_month(target)
        elif not is_month:
            messagebox.showinfo(APP_NAME, text)

    def annual_open_month(self, target=None):
        """Open the month return of the selected row (YTD, 3B or reconciliation table) at a tab that shows its
        figures: Invoice Review when the month has invoice lines, otherwise the GSTR-1 Summary (months built from
        summary reports or a Master Template have no invoice lines)."""
        if not self._an_client() or not self._an_year:
            return
        label = None
        rc = [x[3] for x in self.an_rc_trees]
        for tree in [self.an_rc] + rc + [self.an_tree, self.an_rec]:
            sel = tree.selection()
            if sel:
                label = tree.set(sel[0], "per") if tree in rc else tree.set(sel[0], "m")
                break
        row = next((r for r in self._an_year["months"] if r["label"] == label), None)
        if not row or not row.get("pid"):
            messagebox.showinfo(APP_NAME, "Select a month row that has a return (yearly rows have no month).")
            return
        self.open_project(self.client, row["pid"])
        if target == "Invoice Review" and not self.lines:
            target = "GSTR-1 Summary"
        target = target or ("Invoice Review" if self.lines else "GSTR-1 Summary")
        self.goto(target)
        self.set_status(f"{row['label']} opened in '{target}'. Tab 15 has the reconciliation of the year.")

    def annual_entry(self):
        if not self._an_client() or not self._an_year:
            return
        sel = self.an_tree.selection() or self.an_rec.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select a month first.")
            return
        label = sel[0][1:] if sel[0].startswith("r") and sel[0][1:] in {r["label"] for r in self._an_year["months"]} else sel[0]
        row = next((r for r in self._an_year["months"] if r["label"] == label), None)
        if not row:
            return
        key = f"{row['year']}-{row['month']:02d}"
        fy = self.an_fy.get()
        entries = annual.load_entries(self.db, self.client["id"], fy)
        cur = entries.get(key, {})
        win = tk.Toplevel(self)
        win.title(f"GSTR-3B and books figures - {label}")
        win.transient(self)
        vars_ = {}
        ttk.Label(win, text=f"{label}: type the figures as filed / as per books (leave blank if not available)",
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=8)
        for i, k in enumerate(annual.ENTRY_KEYS, 1):
            ttk.Label(win, text=annual.ENTRY_LABELS[k]).grid(row=i, column=0, sticky="w", padx=10, pady=3)
            vars_[k] = tk.StringVar(value=str(cur.get(k, "")))
            ttk.Entry(win, textvariable=vars_[k], width=18, justify="right").grid(row=i, column=1, padx=10)

        def ok():
            vals = {k: v.get().strip() for k, v in vars_.items() if v.get().strip()}
            entries[key] = vals
            annual.save_entries(self.db, self.client["id"], fy, entries)
            win.destroy()
            self.refresh_annual()
        ttk.Button(win, text="Save", command=ok).grid(row=len(vars_) + 1, column=0, columnspan=2, pady=10)

    def annual_export(self):
        if not self._an_client() or not self._an_year:
            return
        fy = self.an_fy.get()
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                         initialfile=f"YTD_Annual_{self.client['gstin']}_FY{fy}.xlsx")
        if p:
            annual.export_year(p, self.client, self._an_year)
            recon.export_sheets(p, self.client, fy, getattr(self, "_an_recon", []), getattr(self, "_an_filed", []))
            self.set_status(f"YTD / annual workbook saved: {p}")

    def _tab_settings(self):
        f = self.tab("14 Settings")
        ttk.Label(f, text="Settings and Backup", style="Head.TLabel").pack(anchor="w")
        form = ttk.Frame(f)
        form.pack(anchor="w", pady=8)
        self.sv = {}
        rows = [("operator", "Operator name (for audit trail)"), ("rounding_tolerance", "Rounding tolerance (Rs.)"),
                ("b2cl_threshold", "B2C Large invoice value threshold (Rs.)"),
                ("hsn_min_digits", "Minimum HSN digits (4 up to Rs 5 crore turnover, 6 above)"),
                ("valid_rates", "Valid GST rates (comma separated)"),
                ("tesseract_path", "Tesseract.exe path (optional, for OCR)")]
        for n, (k, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=n, column=0, sticky="e", padx=4, pady=3)
            v = tk.StringVar(value=self.settings.get(k, ""))
            ttk.Entry(form, textvariable=v, width=60).grid(row=n, column=1, pady=3)
            self.sv[k] = v
        self.ocr_var = tk.BooleanVar(value=self.settings.get("ocr_enabled") == "1")
        ttk.Checkbutton(form, text="Enable OCR for scanned PDFs (needs Tesseract installed)", variable=self.ocr_var).grid(
            row=len(rows), column=1, sticky="w")
        self.auto_tax_var = tk.BooleanVar(value=self.settings.get("auto_tax", "1") == "1")
        self.auto_pos_var = tk.BooleanVar(value=self.settings.get("auto_pos", "1") == "1")
        ttk.Checkbutton(form, text="Calculate IGST / CGST / SGST automatically = taxable value x rate",
                        variable=self.auto_tax_var).grid(row=len(rows) + 1, column=1, sticky="w")
        ttk.Checkbutton(form, text="Fill blank place of supply from the recipient GSTIN (state code)",
                        variable=self.auto_pos_var).grid(row=len(rows) + 2, column=1, sticky="w")
        ttk.Button(f, text="Save Settings", command=self.save_settings).pack(anchor="w", pady=4)
        ttk.Separator(f).pack(fill="x", pady=8)
        ttk.Label(f, text="Official Offline Tool template check", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ob = ttk.Frame(f)
        ob.pack(anchor="w", pady=4)
        ttk.Button(ob, text="Compare with official Offline Tool samples...", command=self.official_check).pack(side="left", padx=3)
        ttk.Button(ob, text="Reset headings to built-in", command=self.schema_reset).pack(side="left", padx=3)
        self.schema_status = tk.StringVar(value=headers_status(self.schema)[2])
        ttk.Label(ob, textvariable=self.schema_status, foreground="#a00000").pack(side="left", padx=8)
        ttk.Separator(f).pack(fill="x", pady=8)
        bar = ttk.Frame(f)
        bar.pack(anchor="w")
        ttk.Button(bar, text="Backup Data", command=self.backup).pack(side="left", padx=3)
        ttk.Button(bar, text="Restore Data", command=self.restore).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete this return's extracted data & source copies", command=self.delete_return_data).pack(side="left", padx=3)
        ttk.Button(bar, text="Open data folder", command=lambda: open_folder(config.DATA_ROOT)).pack(side="left", padx=3)
        ttk.Label(f, wraplength=1100, foreground="#444", justify="left", text=(
            "\nSECURITY & CONFIDENTIALITY\n"
            f"- All documents and data stay on this computer in: {config.DATA_ROOT}\n"
            "- No client data is sent over the internet. OCR runs locally and does not write temporary image files.\n"
            "- GST Portal passwords and OTPs are never requested or stored.\n"
            "- The log file records events and counts only, not invoice details.\n"
            "- Keep regular backups on an encrypted drive and restrict access to the data folder (Windows folder "
            "permissions / BitLocker).\n")).pack(anchor="w")

    def official_check(self):
        """Compare our CSV headings with the official sample CSV files and optionally adopt them."""
        folder = filedialog.askdirectory(title="Select the folder with the official GSTR-1 Offline Tool sample CSV files",
                                         mustexist=True)
        if not folder:
            return
        comp = gstr1.compare_headers(folder, self.schema)
        win = tk.Toplevel(self)
        win.title("Official template check")
        win.geometry("1020x600")
        win.transient(self)
        ttk.Label(win, wraplength=980, padding=8, text=(
            "Match = identical headings.  Adoptable = same columns with different spelling/order (can be adopted "
            "automatically).  Different = columns differ: the schema file must be edited by hand.  Not found = no sample "
            "file for that table in the folder.  Headings are only one part of compatibility - always do a test import "
            "of every generated file into the Offline Tool.")).pack()
        fr, tree = make_tree(win, [("t", "Table", 170), ("f", "Official file", 170), ("s", "Result", 90), ("d", "Detail", 520)], height=14)
        fr.pack(fill="both", expand=True, padx=8)
        for c in comp:
            tag = {"match": "approved", "adoptable": "warning", "different": "error"}.get(c["status"], "")
            tree.insert("", "end", iid=c["key"], tags=(tag,) if tag else (), values=(
                self.schema["tables"][c["key"]]["title"], c["file"], c["status"], c["detail"]))
        txt = tk.Text(win, height=7, wrap="word")
        txt.pack(fill="x", padx=8, pady=4)

        def show(_e=None):
            sel = tree.selection()
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            if sel:
                c = next(x for x in comp if x["key"] == sel[0])
                txt.insert("end", f"Official headings : {c['official']}\nOur headings      : {c['mine']}\n"
                                  f"Only in official  : {c['missing']}\nOnly in ours      : {c['extra']}")
            txt.configure(state="disabled")
        tree.bind("<<TreeviewSelect>>", show)

        def adopt():
            n = gstr1.adopt_headers(self.schema, comp)
            save_schema(self.schema)
            self.schema = load_schema()
            self.schema_status.set(headers_status(self.schema)[2])
            self._schema_label()
            self.db.audit(self.project["id"] if self.project else 0, "Official headings adopted", f"{n} table(s)")
            messagebox.showinfo(APP_NAME, f"{n} table(s) now use the official headings and are marked as verified.\n"
                                "Tables marked 'different' or 'not found' still need attention.", parent=win)
            win.destroy()
        bb = ttk.Frame(win, padding=8)
        bb.pack(fill="x")
        ttk.Button(bb, text="Adopt official headings (Match / Adoptable tables)", command=adopt).pack(side="left")
        ttk.Button(bb, text="Close", command=win.destroy).pack(side="right")

    def schema_reset(self):
        if messagebox.askyesno(APP_NAME, "Go back to the built-in (provisional) headings? Adopted headings are discarded."):
            reset_schema()
            self.schema = load_schema()
            self.schema_status.set(headers_status(self.schema)[2])
            self._schema_label()

    def save_settings(self):
        try:
            D(self.sv["rounding_tolerance"].get())
            D(self.sv["b2cl_threshold"].get())
            if int(D(self.sv["hsn_min_digits"].get())) not in (2, 4, 6, 8):
                raise ValueError("HSN digits")
        except Exception:  # noqa
            messagebox.showerror(APP_NAME, "Invalid number in settings (HSN digits must be 4, 6 or 8).")
            return
        for k, v in self.sv.items():
            self.db.set_setting(k, v.get().strip())
        self.db.set_setting("ocr_enabled", "1" if self.ocr_var.get() else "0")
        self.db.set_setting("auto_tax", "1" if self.auto_tax_var.get() else "0")
        self.db.set_setting("auto_pos", "1" if self.auto_pos_var.get() else "0")
        self.settings = self.db.get_settings()
        self.run_checks(save=False)
        self.set_status("Settings saved.")

    def backup(self):
        p = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Backup", "*.zip")],
                                         initialfile=f"CA_GST_backup_{__import__('datetime').date.today()}.zip")
        if p:
            self.persist()
            self.db.backup(Path(p))
            messagebox.showinfo(APP_NAME, f"Backup saved:\n{p}\n\nStore it securely - it contains client data.")

    def restore(self):
        p = filedialog.askopenfilename(filetypes=[("Backup", "*.zip")])
        if p and messagebox.askyesno(APP_NAME, "Restoring replaces current application data with the backup. "
                                     "The application will close afterwards. Continue?", icon="warning"):
            try:
                self.db.restore(Path(p))
            except Exception as e:  # noqa
                messagebox.showerror(APP_NAME, f"Restore failed: {e}")
                return
            messagebox.showinfo(APP_NAME, "Restore complete. Please start the application again.")
            self.destroy()

    def delete_return_data(self):
        if not self.need_project():
            return
        if messagebox.askyesno(APP_NAME, "Delete extracted data, uploaded-file records, document register and "
                               "stored copies of source files for this return? Generated output files are kept.",
                               icon="warning"):
            root = project_dir(self.client, self.project)
            for sub in ("source_files", "extracted_data", "review_reports"):
                shutil.rmtree(root / sub, ignore_errors=True)
                (root / sub).mkdir(parents=True, exist_ok=True)
            self.db.delete_project_data(self.project["id"])
            self.db.audit(self.project["id"], "Return data deleted", "")
            self.lines, self.docs, self.sets = [], [], []
            self.last_upload_issues = []
            self.run_checks(save=False)
            self.refresh_current()
