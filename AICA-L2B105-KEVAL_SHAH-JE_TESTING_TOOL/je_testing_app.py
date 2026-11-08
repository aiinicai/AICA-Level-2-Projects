"""
============================================================================
 JOURNAL ENTRY TESTING  --  Desktop App
----------------------------------------------------------------------------
 A clickable window around the JE Testing engine in je_testing.py:

   1. Browse to the GL extract (Excel / CSV / SAP export)
   2. (Optional) check the auto-detected column mapping
   3. Click  Run JE Testing
   4. Open the Excel workpaper

 Run:  python je_testing_app.py      (or double-click once packaged as .exe)
============================================================================
"""

import os
import sys
import json
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import je_testing as core

NAVY  = "#1a2744"; NAVY2 = "#2a3a5a"; BG = "#f8f9fc"; MUTED = "#5a6a8a"
GREEN = "#1b6b3a"; RED = "#c0392b"; AMBER = "#b9770e"; WHITE = "#ffffff"


class JEApp:
    def __init__(self, root):
        self.root = root
        root.title("Journal Entry Testing")
        root.configure(bg=BG)
        root.geometry("760x640"); root.minsize(700, 580)

        self.gl_path = tk.StringVar(value=str(core.find_gl() or ""))
        self.out_dir = tk.StringVar(value=str(core.OUTPUT_DIR))
        self.mapping = None
        self.last_excel = None

        self._build_header(); self._build_body(); self._build_footer()

    # ---- UI ----
    def _build_header(self):
        h = tk.Frame(self.root, bg=NAVY); h.pack(fill="x")
        tk.Label(h, text="Journal Entry Testing", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(h, text="Risk-based JE analysis  -  SA 240  -  100% offline",
                 bg=NAVY, fg="#8fa8d4", font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(2, 18))

    def _build_body(self):
        b = tk.Frame(self.root, bg=BG); b.pack(fill="both", expand=True, padx=24, pady=16)
        self._row(b, "GL extract (Excel / CSV)", self.gl_path, self._browse_gl)
        self._row(b, "Output folder", self.out_dir, self._browse_out)

        mp = tk.Frame(b, bg=BG); mp.pack(fill="x", pady=(6, 2))
        tk.Button(mp, text="Check column mapping", command=self._check_mapping,
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(mp, text="⚙ Settings", command=lambda: ConfigEditor(self.root),
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))

        act = tk.Frame(b, bg=BG); act.pack(fill="x", pady=(8, 6))
        tk.Button(act, text="Create sample GL", command=self._make_samples,
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                  padx=12, pady=6, cursor="hand2").pack(side="left")
        self.run_btn = tk.Button(act, text="▶  Run JE Testing", command=self._on_run,
                                 bg=NAVY, fg=WHITE, relief="flat",
                                 font=("Segoe UI", 11, "bold"), padx=22, pady=8,
                                 cursor="hand2", activebackground=NAVY2,
                                 activeforeground=WHITE)
        self.run_btn.pack(side="right")

        rf = tk.Frame(b, bg=BG); rf.pack(fill="both", expand=True, pady=(8, 0))
        tk.Label(rf, text="Result", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.results = tk.Text(rf, height=15, wrap="word", bg=WHITE, fg=NAVY,
                               relief="solid", bd=1, font=("Consolas", 10),
                               padx=12, pady=10, state="disabled")
        self.results.pack(fill="both", expand=True, pady=(4, 0))
        for tag, col in (("ok", GREEN), ("warn", RED), ("amber", AMBER), ("head", NAVY)):
            self.results.tag_config(tag, foreground=col, font=("Consolas", 10, "bold"))

    def _build_footer(self):
        f = tk.Frame(self.root, bg=BG); f.pack(fill="x", padx=24, pady=(0, 16))
        self.open_report_btn = tk.Button(f, text="Open Workpaper", command=self._open_report,
            state="disabled", bg=WHITE, fg=NAVY, relief="solid", bd=1,
            font=("Segoe UI", 10), padx=14, pady=6, cursor="hand2")
        self.open_report_btn.pack(side="left")
        self.open_folder_btn = tk.Button(f, text="Open Output Folder", command=self._open_folder,
            state="disabled", bg=WHITE, fg=NAVY, relief="solid", bd=1,
            font=("Segoe UI", 10), padx=14, pady=6, cursor="hand2")
        self.open_folder_btn.pack(side="left", padx=(10, 0))
        self.status = tk.Label(f, text="Ready", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.status.pack(side="right")

    def _row(self, parent, label, var, cmd):
        r = tk.Frame(parent, bg=BG); r.pack(fill="x", pady=6)
        tk.Label(r, text=label, bg=BG, fg=NAVY, width=24, anchor="w",
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(r, textvariable=var, font=("Segoe UI", 9), relief="solid",
                 bd=1).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(r, text="Browse…", command=cmd, bg=WHITE, fg=NAVY, relief="solid",
                  bd=1, font=("Segoe UI", 9), padx=10, cursor="hand2").pack(side="right")

    # ---- handlers ----
    def _browse_gl(self):
        p = filedialog.askopenfilename(
            title="Select the GL extract",
            filetypes=[("GL exports", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if p:
            self.gl_path.set(p); self.mapping = None

    def _browse_out(self):
        d = filedialog.askdirectory(title="Select the output folder")
        if d:
            self.out_dir.set(d)

    def _check_mapping(self):
        gl = self.gl_path.get().strip()
        if not gl or not os.path.isfile(gl):
            messagebox.showwarning("Missing file", "Choose a valid GL file first.")
            return
        self._set_status("Reading header…")
        try:
            self.mapping = core.build_mapping(core.load_raw(gl))
            lines = [("  COLUMN MAPPING", "head"), ("", None)]
            for field in core.COLUMN_ALIASES:
                actual = self.mapping.get(field)
                tag = "ok" if actual else ("warn" if field in core.ESSENTIAL_FIELDS else "amber")
                lines.append((f"   {field:14} <- {actual or '(not found)'}", tag))
            miss = [f for f in core.ESSENTIAL_FIELDS if f not in self.mapping]
            lines += [("", None),
                      ("  Essential fields OK" if not miss
                       else f"  MISSING essential: {', '.join(miss)}",
                       "ok" if not miss else "warn")]
            self._set_results(lines); self._set_status("Mapping checked.")
        except Exception as e:
            messagebox.showerror("Could not read file", str(e))
            self._set_status("Failed.")

    def _make_samples(self):
        try:
            path = core.make_samples()
            self.gl_path.set(str(path)); self.mapping = None
            messagebox.showinfo("Sample created",
                f"A sample GL was written to:\n{path}\n\nClick Run JE Testing to try it.")
            self._set_status("Sample created.")
        except Exception as e:
            messagebox.showerror("Could not create sample", str(e))

    def _on_run(self):
        gl = self.gl_path.get().strip()
        out = self.out_dir.get().strip() or str(core.OUTPUT_DIR)
        if not gl or not os.path.isfile(gl):
            messagebox.showwarning("Missing file", "Choose a valid GL file.")
            return
        self.run_btn.config(state="disabled")
        self.open_report_btn.config(state="disabled")
        self.open_folder_btn.config(state="disabled")
        self._set_results([("Working — this can take a minute on a large GL…", "head")])
        self._holder = {}
        t = threading.Thread(target=self._worker, args=(gl, out), daemon=True)
        t.start(); self.root.after(200, self._poll, t)

    def _worker(self, gl, out):
        try:
            self._holder["ok"] = core.analyze_file(
                gl, out, core.load_config(), mapping=self.mapping,
                progress=lambda m: self.root.after(0, self._set_status, m))
        except Exception as e:
            self._holder["error"] = "".join(
                traceback.format_exception_only(type(e), e)).strip()

    def _poll(self, t):
        if t.is_alive():
            self.root.after(200, self._poll, t); return
        self.run_btn.config(state="normal")
        if "error" in self._holder:
            msg = self._holder["error"]
            self._set_results([("JE Testing failed:", "warn"), ("", None), (msg, None)])
            self._set_status("Failed."); messagebox.showerror("JE Testing failed", msg)
            return
        results, xlsx = self._holder["ok"]
        self.last_excel = Path(xlsx)
        je = results["je"]; ig = results["integrity"]
        vc = je["risk_category"].value_counts()
        tot = len(je)
        cat_tag = {"Critical": "warn", "High": "amber", "Medium": None, "Low": "ok"}
        lines = [("  JE TESTING COMPLETE", "head"), ("", None),
                 (f"   Line items      : {len(results['df']):,}", None),
                 (f"   Journal entries : {tot:,}", None),
                 (f"   Balance (Dr-Cr) : {ig['total_debit'] - ig['total_credit']:,.0f}  "
                  + ("BALANCED" if ig["balanced"] else "DOES NOT TIE OUT"),
                  "ok" if ig["balanced"] else "warn"),
                 ("", None), ("  RISK CATEGORY", "head")]
        for c in ("Critical", "High", "Medium", "Low"):
            n = int(vc.get(c, 0))
            lines.append((f"     {c:9}: {n:,}  ({100 * n / max(tot, 1):.1f}%)", cat_tag[c]))
        hi = int(vc.get("Critical", 0) + vc.get("High", 0))
        lines += [("", None),
                  (f"   Test population (High+Critical): {hi:,}", "amber"),
                  (f"   Samples selected               : {len(results['samples']):,}", None),
                  ("", None), ("  Workpaper:", None), (f"  {xlsx}", None)]
        self._set_results(lines); self._set_status("Done.")
        self.open_report_btn.config(state="normal")
        self.open_folder_btn.config(state="normal")

    # ---- helpers ----
    def _set_status(self, m):
        self.status.config(text=m)

    def _set_results(self, lines):
        self.results.config(state="normal"); self.results.delete("1.0", "end")
        for text, tag in lines:
            self.results.insert("end", text + "\n", tag or "")
        self.results.config(state="disabled")

    def _open_report(self):
        if self.last_excel and self.last_excel.exists():
            try: os.startfile(str(self.last_excel))
            except AttributeError: messagebox.showinfo("Workpaper", str(self.last_excel))

    def _open_folder(self):
        d = self.out_dir.get().strip() or str(core.OUTPUT_DIR)
        if os.path.isdir(d):
            try: os.startfile(d)
            except AttributeError: messagebox.showinfo("Folder", d)


# ===========================================================================
#  SETTINGS  --  edit je_config.json from inside the tool
# ===========================================================================
class ConfigEditor(tk.Toplevel):
    """A tabbed form over je_config.json. Lists are one item per line."""

    THRESHOLDS = [
        (("non_working_days",), "Non-working days (comma, e.g. Sunday)", "csv"),
        (("period_end_days",), "Month-end window (last N days)", "int"),
        (("back_dated_lag_days",), "Back-dated lag (days)", "int"),
        (("round_base",), "Round-sum base (Rs.)", "float"),
        (("large_amount",), "Large amount (Rs.)", "float"),
        (("narration_min_len",), "Min narration length", "int"),
        (("category_bands", "critical"), "Band: Critical score ≥", "int"),
        (("category_bands", "high"), "Band: High score ≥", "int"),
        (("category_bands", "medium"), "Band: Medium score ≥", "int"),
        (("risk_sample_size",), "Risk-based sample size", "int"),
        (("random_sample_size",), "Random sample size", "int"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("JE Testing — Settings")
        self.configure(bg=BG)
        self.geometry("720x620"); self.minsize(640, 520)
        self.transient(parent)
        self.cfg = core.load_config()
        self.fields = []                  # (path, kind, widget)

        head = tk.Frame(self, bg=NAVY); head.pack(fill="x")
        tk.Label(head, text="Settings", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(14, 0))
        tk.Label(head, text="Saved to je_config.json beside the program  ·  lists are one item per line",
                 bg=NAVY, fg="#8fa8d4", font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(2, 14))

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=12, pady=10)
        self._tab_people(nb)
        self._tab_thresholds(nb)
        self._tab_keywords(nb)
        self._tab_weights(nb)

        bar = tk.Frame(self, bg=BG); bar.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(bar, text="Reset to defaults", command=self._reset, bg=WHITE,
                  fg=RED, relief="solid", bd=1, font=("Segoe UI", 9), padx=10,
                  pady=6, cursor="hand2").pack(side="left")
        tk.Button(bar, text="Save & Close", command=self._save_close, bg=NAVY,
                  fg=WHITE, relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=18, pady=7, cursor="hand2", activebackground=NAVY2,
                  activeforeground=WHITE).pack(side="right")
        tk.Button(bar, text="Cancel", command=self.destroy, bg=WHITE, fg=MUTED,
                  relief="solid", bd=1, font=("Segoe UI", 10), padx=14, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 8))

        self._populate(self.cfg)

    def _scroll_body(self, nb, title):
        outer = tk.Frame(nb, bg=BG); nb.add(outer, text=title)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def _multiline(self, parent, label, path, help_=""):
        tk.Label(parent, text=label, bg=BG, fg=NAVY,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        if help_:
            tk.Label(parent, text=help_, bg=BG, fg=MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w", padx=14)
        t = tk.Text(parent, height=4, wrap="word", bg=WHITE, fg=NAVY,
                    relief="solid", bd=1, font=("Consolas", 9))
        t.pack(fill="x", padx=14, pady=(3, 0))
        self.fields.append((path, "list", t))

    def _entry(self, parent, label, path, kind):
        r = tk.Frame(parent, bg=BG); r.pack(fill="x", padx=14, pady=4)
        tk.Label(r, text=label, bg=BG, fg=NAVY, width=36, anchor="w",
                 font=("Segoe UI", 10)).pack(side="left")
        e = tk.Entry(r, font=("Segoe UI", 10), relief="solid", bd=1)
        e.pack(side="left", fill="x", expand=True)
        self.fields.append((path, kind, e))

    def _tab_people(self, nb):
        f = self._scroll_body(nb, "Users")
        self._multiline(f, "Privileged / IT users", ("privileged_users",),
                        "SAP user IDs with admin / elevated access")
        self._multiline(f, "Super users", ("super_users",),
                        "senior users (e.g. CFO) who can post anywhere")
        self._entry(f, "Manual document types (comma)", ("manual_doc_types",), "csv")

    def _tab_thresholds(self, nb):
        f = self._scroll_body(nb, "Thresholds")
        for path, label, kind in self.THRESHOLDS:
            self._entry(f, label, path, kind)

    def _tab_keywords(self, nb):
        f = self._scroll_body(nb, "Keywords & Holidays")
        self._multiline(f, "Generic narrations", ("generic_descriptions",),
                        "vague narrations to flag")
        self._multiline(f, "Red-flag keywords", ("fraud_keywords",))
        self._multiline(f, "Public holidays (YYYY-MM-DD)", ("public_holidays",),
                        "one date per line, for the year under audit")

    def _tab_weights(self, nb):
        f = self._scroll_body(nb, "Risk Weights")
        tk.Label(f, text="Points each rule adds to a journal entry's risk score",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 2))
        for k in core.RULE_KEYS:
            self._entry(f, core.RULES[k][0], ("risk_weights", k), "int")

    @staticmethod
    def _get_in(cfg, path):
        cur = cfg
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    @staticmethod
    def _set_in(cfg, path, value):
        cur = cfg
        for p in path[:-1]:
            cur = cur.setdefault(p, {})
        cur[path[-1]] = value

    def _populate(self, cfg):
        for path, kind, w in self.fields:
            val = self._get_in(cfg, path)
            if val is None:
                val = [] if kind in ("list", "csv") else 0
            if kind == "list":
                w.delete("1.0", "end"); w.insert("1.0", "\n".join(str(x) for x in val))
            elif kind == "csv":
                w.delete(0, "end"); w.insert(0, ", ".join(str(x) for x in val))
            else:
                w.delete(0, "end"); w.insert(0, str(val))

    def _collect(self):
        for path, kind, w in self.fields:
            if kind == "list":
                items = [ln.strip() for ln in w.get("1.0", "end").splitlines() if ln.strip()]
                self._set_in(self.cfg, path, items)
            elif kind == "csv":
                self._set_in(self.cfg, path, [p.strip() for p in w.get().split(",") if p.strip()])
            elif kind == "int":
                self._set_in(self.cfg, path, int(round(self._num(w.get()))))
            elif kind == "float":
                self._set_in(self.cfg, path, self._num(w.get()))

    @staticmethod
    def _num(s):
        try:
            return float(str(s).replace(",", "").strip())
        except ValueError:
            return 0.0

    def _save_close(self):
        try:
            self._collect()
            core.save_config(self.cfg)
            messagebox.showinfo("Saved", f"Settings saved to:\n{core.CONFIG_PATH}\n\n"
                                "They apply to the next run.", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Could not save", str(e), parent=self)

    def _reset(self):
        if messagebox.askyesno("Reset to defaults",
                               "Replace all settings with the built-in defaults?", parent=self):
            self.cfg = json.loads(json.dumps(core.DEFAULT_CONFIG))
            self._populate(self.cfg)


def main():
    root = tk.Tk(); JEApp(root); root.mainloop()


if __name__ == "__main__":
    main()
