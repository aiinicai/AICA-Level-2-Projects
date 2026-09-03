"""
ECL Stage Migration Matrix & Commentary Narrator — Desktop GUI
------------------------------------------------------------------
AICA Level 2 Capstone Project
Author : Hitesh Bhadada (Financial Controller)

WHAT THIS FILE IS (AND ISN'T)
------------------------------
This is a Tkinter front-end bolted onto ecl_migration_matrix.py. It adds
NO new calculation logic of its own - every number in the output workbook
is produced by functions that already exist in the engine file, called
through the single shared entry point `run_pipeline()`. This file only
decides WHAT to run (which data folder, which two periods, whether to
also draft the optional AI commentary) - never HOW the numbers are
computed. That keeps the audited arithmetic and regulatory logic in
exactly one place, so a reviewer only has to check the calculations once,
regardless of whether they run the tool via this window or via the
command line.

The command-line tool keeps working exactly as before:
    python ecl_migration_matrix.py --data-dir ./data --compare Q1FY26:Q2FY26

This window exists purely so that someone reviewing the capstone project -
who was not involved in building it - can run the tool without knowing any
command-line flags: point it at a folder, see the periods it found, tick
two, click Run, and watch the same messages the command-line version
prints, then open the workbook it produces.

HOW TO RUN
----------
    python ecl_gui.py

HOW TO PACKAGE (see ecl_migration_matrix.py's own header for --ai extras)
--------------------------------------------------------------------------
    pip install pandas openpyxl pyinstaller
    pyinstaller --onefile --windowed ecl_gui.py
PyInstaller auto-detects the local "import ecl_migration_matrix" below and
bundles that file into the same .exe, provided both files sit in the same
folder when you run the pyinstaller command - no extra flag is needed for
that. Use --windowed (not --console) here, since this GUI has no need of
a console window; all progress is shown inside the window's own log pane.
"""

import os
import sys
import queue
import shutil
import threading
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import ecl_migration_matrix as engine


# --------------------------------------------------------------------------
# Redirects print() output (from the engine's existing print statements)
# into a thread-safe queue that the GUI polls on the main thread. Tkinter
# widgets may only be touched from the main thread, but the engine runs on
# a background thread so the window itself never freezes during a run.
# --------------------------------------------------------------------------
class QueueWriter:
    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(s)

    def flush(self):
        pass


ABOUT_TEXT = """ECL STAGE MIGRATION MATRIX & COMMENTARY NARRATOR
AICA Level 2 Capstone Project — Hitesh Bhadada, Financial Controller

WHAT THIS TOOL DOES
--------------------
Given loan-level data for two (or more) period-ends, it builds:

  1. A From-Stage x To-Stage MIGRATION MATRIX (Ind AS 109 stages) showing
     exactly which loans moved between Stage 1/2/3, with click-through to
     the underlying customer list in the workbook.
  2. A DPD (days-past-due) ageing bucket migration matrix, on the same
     loan-level basis.
  3. The Ind AS 107 para 35H loss-allowance reconciliation (opening to
     closing ECL provision, split by movement type).
  4. The RBI IRACP vs Ind AS 109 provisioning comparison required for
     NBFCs under the RBI (NBFC - IRACP) Directions, 2025, and the
     resulting Impairment Reserve requirement, if any.
  5. A deterministic, rule-based commentary paragraph summarising the
     above in Board/Audit-Committee language - optionally followed by an
     AI-polished version of the SAME aggregate figures (no customer names
     or loan IDs are ever sent to the AI service; see the "Include AI
     commentary" option in the Run tab).

REGULATORY SCOPE
-----------------
IRACP thresholds and provisioning rates are those applicable to an NBFC
classified in the MIDDLE LAYER under the RBI (NBFC - IRACP) Directions,
2025. Base Layer and Upper Layer rates are NOT implemented. If the entity
is reclassified into another layer, the engine file's constants must be
revisited before relying on this output.

WHAT THIS TOOL DOES NOT DO
----------------------------
It never computes ECL provisioning itself - Provision_Cr is taken as
given from the source data, governed by Ind AS 109 and RBI norms in your
source systems. The optional AI step only drafts prose from numbers
already computed; it never alters a stage, a provision, or an IRACP
classification.

DATA REQUIRED
--------------
One file per period-end (CSV or Excel) in the data folder, each with at
minimum:
    Period, LoanID, CustomerName, Stage, Outstanding_Cr, Provision_Cr

Add a DPD column to also get the RBI IRACP disclosure (auto-computed per
loan - no pre-computed provision figure required). Secured_Value_Cr and
Loss_Flag are optional refinements; see the engine file's own header
comment for the full specification, including write-off file handling and
the Product/Branch summary sheets.

WHERE THE OUTPUT GOES
------------------------
Every run creates a timestamped folder under output/, next to your data
folder (or wherever you point the "Output base folder" field), containing
the Excel workbook, a plain-text copy of the commentary, and a run log
recording exactly which source files (with SHA-256 hashes) fed that run -
so any workbook can be traced back to the precise data behind it.

AUDIT NOTE
-----------
This tool drafts the computation and layout. It does not substitute
professional or regulatory judgement, and every run's commentary ends
with a line to that effect. Always verify against the latest RBI/ICAI
notifications before relying on this for an actual filing or Board paper.
"""


class ECLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECL Stage Migration Matrix & Commentary Narrator — AICA Capstone")
        self.geometry("1000x760")
        self.minsize(880, 640)

        # State populated by _scan_folder()
        self.periods_index = {}
        self.frames = {}
        self.writeoff_frames = {}
        self.ordered_periods = []

        self.log_queue: queue.Queue = queue.Queue()
        self.last_output_dir = None
        self.run_thread = None

        self._build_ui()
        self.after(150, self._poll_log_queue)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        tab_run = ttk.Frame(nb)
        tab_about = ttk.Frame(nb)
        nb.add(tab_run, text="Run Analysis")
        nb.add(tab_about, text="About / Methodology")

        self._build_run_tab(tab_run)
        self._build_about_tab(tab_about)

    def _build_run_tab(self, root):
        default_dir = os.path.join(engine.SCRIPT_DIR, "data")

        # ---- Step 1: data folder ----
        frm_data = ttk.LabelFrame(root, text="1.  Period-end data folder")
        frm_data.pack(fill="x", padx=4, pady=4)

        self.data_dir_var = tk.StringVar(value=default_dir)
        ttk.Entry(frm_data, textvariable=self.data_dir_var, width=68).pack(
            side="left", padx=6, pady=6, fill="x", expand=True)
        ttk.Button(frm_data, text="Browse...", command=self._browse_data_dir).pack(side="left", padx=4)
        ttk.Button(frm_data, text="Scan Folder", command=self._scan_folder).pack(side="left", padx=(4, 6))

        # ---- Step 2: periods table + pair selection ----
        frm_periods = ttk.LabelFrame(root, text="2.  Periods found — choose FROM and TO")
        frm_periods.pack(fill="x", padx=4, pady=4)

        cols = ("period", "loans", "outstanding", "source")
        self.tree = ttk.Treeview(frm_periods, columns=cols, show="headings", height=6)
        headers = [("period", 100, "Period"), ("loans", 70, "Loans"),
                   ("outstanding", 170, "Outstanding (Rs. Cr)"), ("source", 380, "Source file")]
        for key, width, label in headers:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.pack(fill="x", padx=6, pady=(6, 4))

        sel_row = ttk.Frame(frm_periods)
        sel_row.pack(fill="x", padx=6, pady=(0, 8))

        ttk.Label(sel_row, text="Compare FROM:").pack(side="left")
        self.from_var = tk.StringVar()
        self.from_combo = ttk.Combobox(sel_row, textvariable=self.from_var, state="readonly", width=13)
        self.from_combo.pack(side="left", padx=(4, 14))

        ttk.Label(sel_row, text="TO:").pack(side="left")
        self.to_var = tk.StringVar()
        self.to_combo = ttk.Combobox(sel_row, textvariable=self.to_var, state="readonly", width=13)
        self.to_combo.pack(side="left", padx=4)

        self.all_pairs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sel_row, text="Run ALL consecutive period pairs instead of one",
                        variable=self.all_pairs_var,
                        command=self._toggle_pair_controls).pack(side="left", padx=20)

        # ---- Step 3: options ----
        frm_opts = ttk.LabelFrame(root, text="3.  Options")
        frm_opts.pack(fill="x", padx=4, pady=4)

        ttk.Label(frm_opts, text="IRACP disclosure as at:").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        self.iracp_var = tk.StringVar()
        self.iracp_combo = ttk.Combobox(frm_opts, textvariable=self.iracp_var, state="readonly", width=13)
        self.iracp_combo.grid(row=0, column=1, sticky="w", padx=4, pady=5)
        ttk.Label(frm_opts, text="(default: latest period selected; only runs if a DPD column is present)").grid(
            row=0, column=2, columnspan=2, sticky="w", padx=6)

        self.ai_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_opts, text="Also draft AI-polished commentary (aggregated figures only)",
                        variable=self.ai_var, command=self._toggle_ai_key).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=6, pady=5)

        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(frm_opts, textvariable=self.api_key_var, width=34, show="*", state="disabled")
        self.api_key_entry.grid(row=1, column=2, sticky="w", padx=6)
        ttk.Label(frm_opts, text="ANTHROPIC_API_KEY — used for this run only, never saved to disk").grid(
            row=1, column=3, sticky="w", padx=4)

        ttk.Label(frm_opts, text="Output base folder:").grid(row=2, column=0, sticky="w", padx=6, pady=5)
        self.out_dir_var = tk.StringVar(value=os.path.dirname(default_dir) or engine.SCRIPT_DIR)
        ttk.Entry(frm_opts, textvariable=self.out_dir_var, width=46).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=4)
        ttk.Button(frm_opts, text="Browse...", command=self._browse_out_dir).grid(row=2, column=3, sticky="w", padx=4)

        for col in range(4):
            frm_opts.columnconfigure(col, weight=0)

        # ---- Run controls ----
        frm_run = ttk.Frame(root)
        frm_run.pack(fill="x", padx=4, pady=8)
        self.run_btn = ttk.Button(frm_run, text="▶  Run Analysis", command=self._run_clicked)
        self.run_btn.pack(side="left", padx=4)
        self.open_folder_btn = ttk.Button(frm_run, text="Open Output Folder",
                                          command=self._open_output_folder, state="disabled")
        self.open_folder_btn.pack(side="left", padx=4)
        self.progress = ttk.Progressbar(frm_run, mode="indeterminate", length=220)
        self.progress.pack(side="left", padx=18)
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frm_run, textvariable=self.status_var).pack(side="left", padx=6)

        # ---- Log pane ----
        frm_log = ttk.LabelFrame(root, text="4.  Run log — the same messages the command-line tool prints")
        frm_log.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_box = scrolledtext.ScrolledText(frm_log, height=16, state="disabled", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_about_tab(self, root):
        txt = scrolledtext.ScrolledText(root, wrap="word", font=("Segoe UI", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", ABOUT_TEXT)
        txt.configure(state="disabled")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _browse_data_dir(self):
        d = filedialog.askdirectory(title="Select period-end data folder")
        if d:
            self.data_dir_var.set(d)

    def _browse_out_dir(self):
        d = filedialog.askdirectory(title="Select output base folder")
        if d:
            self.out_dir_var.set(d)

    def _toggle_ai_key(self):
        self.api_key_entry.configure(state="normal" if self.ai_var.get() else "disabled")

    def _toggle_pair_controls(self):
        state = "disabled" if self.all_pairs_var.get() else "readonly"
        self.from_combo.configure(state=state)
        self.to_combo.configure(state=state)

    def _scan_folder(self):
        repo_dir = self.data_dir_var.get().strip()
        try:
            periods_index, frames, writeoff_frames = engine.scan_period_repository(repo_dir)
        except ValueError as e:
            messagebox.showerror("Scan folder", str(e))
            return
        except Exception:
            messagebox.showerror("Scan folder", f"Unexpected error while scanning:\n\n{traceback.format_exc()}")
            return

        self.periods_index = periods_index
        self.frames = frames
        self.writeoff_frames = writeoff_frames
        self.ordered_periods = list(periods_index.keys())

        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.ordered_periods:
            fdf = frames[p]
            self.tree.insert("", "end", values=(
                p,
                fdf["LoanID"].nunique(),
                f"{fdf['Outstanding_Cr'].sum():,.2f}",
                os.path.basename(periods_index[p]),
            ))

        self.from_combo["values"] = self.ordered_periods
        self.to_combo["values"] = self.ordered_periods
        self.iracp_combo["values"] = self.ordered_periods
        if len(self.ordered_periods) >= 2:
            self.from_var.set(self.ordered_periods[-2])
            self.to_var.set(self.ordered_periods[-1])
            self.iracp_var.set(self.ordered_periods[-1])

        self._log(f"Scanned '{repo_dir}': found {len(self.ordered_periods)} period(s): "
                   f"{', '.join(self.ordered_periods)}\n\n")
        self.status_var.set(f"{len(self.ordered_periods)} period(s) found.")

    def _run_clicked(self):
        if self.run_thread and self.run_thread.is_alive():
            return
        if not self.ordered_periods:
            messagebox.showwarning("Run Analysis", "Scan the data folder first.")
            return

        if self.all_pairs_var.get():
            pairs = list(zip(self.ordered_periods[:-1], self.ordered_periods[1:]))
        else:
            a, b = self.from_var.get(), self.to_var.get()
            if not a or not b:
                messagebox.showwarning("Run Analysis",
                                       "Choose a FROM and TO period, or tick 'Run ALL pairs'.")
                return
            if a == b:
                messagebox.showwarning("Run Analysis", "FROM and TO must be different periods.")
                return
            ia, ib = self.ordered_periods.index(a), self.ordered_periods.index(b)
            pairs = [(a, b) if ia < ib else (b, a)]

        iracp_period = self.iracp_var.get() or None
        use_ai = self.ai_var.get()
        api_key = self.api_key_var.get().strip()
        out_dir = self.out_dir_var.get().strip() or None
        data_dir = self.data_dir_var.get().strip()

        if use_ai:
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif not os.environ.get("ANTHROPIC_API_KEY"):
                proceed = messagebox.askyesno(
                    "No API key entered",
                    "You ticked 'Also draft AI-polished commentary' but no API key was entered "
                    "(and none is set in the environment). The run will still complete with the "
                    "deterministic commentary only, and will note that the AI step was skipped.\n\n"
                    "Continue anyway?")
                if not proceed:
                    return

        self.run_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("Running...")
        self._clear_log()

        self.run_thread = threading.Thread(
            target=self._run_worker,
            args=(data_dir, pairs, iracp_period, use_ai, out_dir),
            daemon=True,
        )
        self.run_thread.start()

    def _run_worker(self, data_dir, pairs, iracp_period, use_ai, out_dir):
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_queue)
        try:
            # Re-scan fresh inside the worker thread so the run reflects
            # exactly what is on disk at the moment Run was clicked, even
            # if the folder changed since the last "Scan Folder" click.
            periods_index, frames, writeoff_frames = engine.scan_period_repository(data_dir)
            periods = list(periods_index.keys())
            source_desc = os.path.abspath(data_dir)

            output_run_dir = engine.run_pipeline(
                periods_index=periods_index,
                frames=frames,
                writeoff_frames=writeoff_frames,
                periods=periods,
                pairs=pairs,
                source_desc=source_desc,
                iracp_period=iracp_period,
                use_ai=use_ai,
                output_dir=out_dir,
                input_file=None,
                data_dir=data_dir,
            )
            self.last_output_dir = output_run_dir
            self.log_queue.put(f"\n[DONE] Output folder:\n{output_run_dir}\n")
        except ValueError as e:
            self.log_queue.put(f"\n[COULD NOT COMPLETE THE RUN]\n{e}\n")
        except Exception:
            self.log_queue.put("\n[UNEXPECTED ERROR]\n")
            self.log_queue.put(traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            self.log_queue.put("__RUN_FINISHED__")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__RUN_FINISHED__":
                    self.progress.stop()
                    self.run_btn.configure(state="normal")
                    if self.last_output_dir:
                        self.open_folder_btn.configure(state="normal")
                        self.status_var.set("Run complete.")
                    else:
                        self.status_var.set("Run failed — see log.")
                    continue
                self._log(msg)
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _open_output_folder(self):
        if not self.last_output_dir:
            return
        path = self.last_output_dir
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: this branch only runs on Windows
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            messagebox.showerror("Open folder", str(e))


def main():
    app = ECLApp()
    app.mainloop()


if __name__ == "__main__":
    main()
