"""
============================================================================
 JOURNAL ENTRY TESTING  --  Desktop App
----------------------------------------------------------------------------
 A clickable window around the JE Testing engine in je_testing.py:

   1. Browse to the GL extract (Excel / CSV / SAP export)
      and, optionally, the Trial Balance to link it to
   2. (Optional) check the auto-detected column mapping
   3. Click  Run JE Testing
   4. Open the Excel workpaper

 Before the main window opens, the user signs in (je_access.py):
   admin  - run testing, change Settings, manage users
   user   - run testing and open the workpaper only
 and each login ID must carry a valid licence key from the vendor.

 Run:  python je_testing_app.py      (or double-click once packaged as .exe)
============================================================================
"""

import os
import sys
import json
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import je_testing as core
import je_access as access

NAVY  = "#1a2744"; NAVY2 = "#2a3a5a"; BG = "#f8f9fc"; MUTED = "#5a6a8a"
GREEN = "#1b6b3a"; RED = "#c0392b"; AMBER = "#b9770e"; WHITE = "#ffffff"

# Friendly names for the column-mapping check
FIELD_LABELS = {
    "je_id": "Document number", "company": "Company code", "account": "G/L account",
    "account_name": "Account name", "user": "User name", "doc_type": "Document type",
    "entry_date": "Entry date", "posting_date": "Posting date", "doc_date": "Document date",
    "period": "Period", "amount": "Amount (local currency)", "narration": "Narration / text",
    "offset_acct": "Offsetting account", "offset_name": "Offsetting account name",
    "opening": "Opening balance", "closing": "Closing balance",
}


def datetime_text(iso):
    """'2027-11-08' -> '08-11-2027' (Indian date style)."""
    y, m, d = str(iso).split("-")
    return f"{d}-{m}-{y}"


def friendly_error(e):
    """Message for the user: our own messages as they are; anything unexpected
    with a short technical note for support."""
    if isinstance(e, (ValueError, FileNotFoundError, PermissionError)):
        return str(e)
    return f"An unexpected problem occurred ({type(e).__name__}: {e}).\nPlease contact support."


class JEApp:
    def __init__(self, root, session):
        self.root = root
        self.session = session              # {"username", "role", "licence", "store"}
        self.is_admin = session["role"] == "admin"
        root.title("Journal Entry Testing")
        root.configure(bg=BG)
        root.geometry("760x720"); root.minsize(700, 660)

        self.gl_path = tk.StringVar(value="")
        self.tb_path = tk.StringVar(value="")
        self.out_dir = tk.StringVar(value=os.path.normpath(str(core.OUTPUT_DIR)))
        self.mapping = None
        self.last_excel = None

        self._build_header(); self._build_body(); self._build_footer()

    # ---- UI ----
    def _build_header(self):
        h = tk.Frame(self.root, bg=NAVY); h.pack(fill="x")
        tk.Label(h, text="Journal Entry Testing", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(h, text="Risk-based JE analysis  -  SA 240  -  100% offline",
                 bg=NAVY, fg="#8fa8d4", font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(2, 6))
        lic = self.session["licence"]
        tk.Label(h, text=(f"Signed in: {self.session['username']} "
                          f"({'Administrator' if self.is_admin else 'User'})"),
                 bg=NAVY, fg="#F0A35E", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=24)
        tk.Label(h, text=(f"Licensed to {lic['licensee']}   ·   Licence {lic['licence_no']}"
                          f"   ·   valid until {datetime_text(lic['expires'])}"),
                 bg=NAVY, fg="#C9D4EA", font=("Segoe UI", 9), wraplength=700,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 14))

    def _build_body(self):
        b = tk.Frame(self.root, bg=BG); b.pack(fill="both", expand=True, padx=24, pady=16)
        self._row(b, "GL extract (Excel / CSV)", self.gl_path, self._browse_gl)
        self._row(b, "Trial Balance (optional)", self.tb_path, self._browse_tb)
        self._row(b, "Output folder", self.out_dir, self._browse_out)

        mp = tk.Frame(b, bg=BG); mp.pack(fill="x", pady=(6, 2))
        tk.Button(mp, text="Check column mapping", command=self._check_mapping,
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(mp, text="⚙ Settings" if self.is_admin else "🔒 Settings (admin only)",
                  command=lambda: ConfigEditor(self.root),
                  state="normal" if self.is_admin else "disabled",
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))
        if self.is_admin:
            tk.Button(mp, text="👥 Users", command=lambda: UserAdmin(self.root, self.session),
                      bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 9),
                      padx=10, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))

        act = tk.Frame(b, bg=BG); act.pack(fill="x", pady=(8, 6))
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
            self.gl_path.set(os.path.normpath(p)); self.mapping = None

    def _browse_tb(self):
        p = filedialog.askopenfilename(
            title="Select the Trial Balance (optional)",
            filetypes=[("Trial Balance", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if p:
            self.tb_path.set(os.path.normpath(p))

    def _browse_out(self):
        d = filedialog.askdirectory(title="Select the output folder")
        if d:
            self.out_dir.set(os.path.normpath(d))

    def _check_mapping(self):
        gl = self.gl_path.get().strip()
        if not gl or not os.path.isfile(gl):
            messagebox.showwarning("Missing file", "Choose a valid GL file first.")
            return
        self._set_status("Reading header…")
        try:
            self.mapping = core.build_mapping(core.load_raw(gl))
            lines = [("  GL COLUMNS FOUND IN YOUR FILE", "head"), ("", None)]
            for field in core.COLUMN_ALIASES:
                actual = self.mapping.get(field)
                tag = "ok" if actual else ("warn" if field in core.ESSENTIAL_FIELDS else "amber")
                lines.append((f"   {FIELD_LABELS.get(field, field):26} <- "
                              f"{actual or '(not found)'}", tag))
            miss = [FIELD_LABELS[f] for f in core.ESSENTIAL_FIELDS if f not in self.mapping]
            lines += [("", None),
                      ("  All required GL columns found" if not miss
                       else f"  MISSING required column(s): {', '.join(miss)}",
                       "ok" if not miss else "warn")]
            tb = self.tb_path.get().strip()
            if tb and os.path.isfile(tb):
                _, tb_map = core.load_tb(tb)
                lines += [("", None), ("  TRIAL BALANCE COLUMNS FOUND", "head"), ("", None)]
                for field in core.TB_ALIASES:
                    actual = tb_map.get(field)
                    tag = "ok" if actual else ("warn" if field in core.TB_ESSENTIAL_FIELDS else "amber")
                    lines.append((f"   {FIELD_LABELS.get(field, field):26} <- "
                                  f"{actual or '(not found)'}", tag))
            self._set_results(lines); self._set_status("Columns checked.")
        except Exception as e:      # shown to the user, never silently ignored
            self.mapping = None
            messagebox.showerror("Could not read file", friendly_error(e))
            self._set_status("Failed.")

    def _on_run(self):
        gl = self.gl_path.get().strip()
        tb = self.tb_path.get().strip() or None
        out = self.out_dir.get().strip() or str(core.OUTPUT_DIR)
        if not gl or not os.path.isfile(gl):
            messagebox.showwarning("Missing file", "Choose a valid GL file.")
            return
        if tb and not os.path.isfile(tb):
            messagebox.showwarning("Missing file", "The Trial Balance file was not found. "
                                   "Choose a valid file or clear the box.")
            return
        self.run_btn.config(state="disabled")
        self.open_report_btn.config(state="disabled")
        self.open_folder_btn.config(state="disabled")
        self._set_results([("Working — this can take a minute on a large GL…", "head")])
        self._holder = {}
        t = threading.Thread(target=self._worker, args=(gl, out, tb), daemon=True)
        t.start(); self.root.after(200, self._poll, t)

    def _worker(self, gl, out, tb):
        try:
            lic = self.session["licence"]
            self._holder["ok"] = core.analyze_file(
                gl, out, core.load_config(), mapping=self.mapping,
                progress=lambda m: self.root.after(0, self._set_status, m),
                tb_path=tb,
                prepared_by=(f"{self.session['username']} ({self.session['role']}) - "
                             f"licence {lic['licence_no']}, {lic['licensee']}"))
        except Exception as e:      # reported to the user in _poll
            self._holder["error"] = friendly_error(e)

    def _poll(self, t):
        if t.is_alive():
            self.root.after(200, self._poll, t); return
        self.run_btn.config(state="normal")
        if "error" in self._holder:
            msg = self._holder["error"]
            self._set_results([("  THE FILE COULD NOT BE PROCESSED", "warn"), ("", None),
                               (msg, None)])
            self._set_status("Failed."); messagebox.showerror("JE Testing - file rejected", msg)
            return
        results, xlsx = self._holder["ok"]
        self.last_excel = Path(xlsx)
        je = results["je"]; ig = results["integrity"]
        vc = je["risk_category"].value_counts()
        tot = len(je)
        cat_tag = {"Critical": "warn", "High": "amber", "Medium": None, "Low": "ok"}
        n_err, n_iss = results["n_errors"], results["n_issues"]
        lines = [("  JE TESTING COMPLETE", "head"), ("", None),
                 (f"   Line items      : {len(results['df']):,}", None),
                 (f"   Journal entries : {tot:,}", None),
                 (("   Data quality    : CLEAN - no issues found", "ok") if not n_iss else
                  (f"   Data quality    : {n_iss} ISSUE(S) FOUND"
                   + (" - data has errors, see 'Data Quality' sheet" if n_err
                      else " - review 'Data Quality' sheet"), "warn" if n_err else "amber")),
                 (f"   Balance (Dr-Cr) : {ig['total_debit'] - ig['total_credit']:,.0f}  "
                  + ("BALANCED" if ig["balanced"] else "DOES NOT TIE OUT"),
                  "ok" if ig["balanced"] else "warn")]
        tbs = results.get("tb_summary")
        if tbs:
            lines.append((f"   GL vs TB        : {tbs['agreed']} of {tbs['accounts_tb']} accounts agree"
                          + (f", {tbs['differences']} DIFFERENCE(S)" if tbs["differences"] else ""),
                          "warn" if tbs["differences"] else "ok"))
        else:
            lines.append(("   GL vs TB        : TB not provided (completeness not confirmed)", "amber"))
        lines += [("", None), ("  RISK CATEGORY", "head")]
        for c in ("Critical", "High", "Medium", "Low"):
            n = int(vc.get(c, 0))
            lines.append((f"     {c:9}: {n:,}  ({100 * n / max(tot, 1):.1f}%)", cat_tag[c]))
        hi = int(vc.get("Critical", 0) + vc.get("High", 0))
        lines += [("", None),
                  (f"   Test population (High+Critical): {hi:,}", "amber"),
                  (f"   Samples selected               : {len(results['samples']):,}"
                   f"  (random seed {results['seed']})", None),
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

    # os.startfile only opens the workpaper this run created / the chosen
    # output folder (no shell, no user-typed command), so Bandit B606 is accepted.
    def _open_report(self):
        if self.last_excel and self.last_excel.exists():
            try: os.startfile(str(self.last_excel))  # nosec B606
            except AttributeError: messagebox.showinfo("Workpaper", str(self.last_excel))

    def _open_folder(self):
        d = self.out_dir.get().strip() or str(core.OUTPUT_DIR)
        if os.path.isdir(d):
            try: os.startfile(d)  # nosec B606
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
        (("random_seed",), "Random seed (blank = new each run)", "str"),
        (("tb_tolerance",), "GL vs TB tolerance (Rs.)", "float"),
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
            elif kind == "str":
                self._set_in(self.cfg, path, w.get().strip())

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


# ===========================================================================
#  SIGN-IN  +  LICENCE ACTIVATION
# ===========================================================================
class LoginScreen:
    """Shown before the main window.  Calls on_success(session) once the
    password is correct AND the login ID has a valid licence."""

    def __init__(self, root, store, on_success):
        self.root, self.store, self.on_success = root, store, on_success
        self.attempts = 0
        root.title("Journal Entry Testing - Sign in")
        root.configure(bg=BG); root.geometry("520x470"); root.minsize(480, 440)
        self.frame = tk.Frame(root, bg=BG); self.frame.pack(fill="both", expand=True)
        self._login_view()

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def _header(self, title, sub):
        h = tk.Frame(self.frame, bg=NAVY); h.pack(fill="x")
        tk.Label(h, text=title, bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(h, text=sub, bg=NAVY, fg="#8fa8d4",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(2, 16))

    def _login_view(self):
        self._clear()
        self._header("Journal Entry Testing", "Sign in to continue")
        b = tk.Frame(self.frame, bg=BG); b.pack(fill="both", expand=True, padx=40, pady=24)
        tk.Label(b, text="Login ID", bg=BG, fg=NAVY, font=("Segoe UI", 10)).pack(anchor="w")
        self.user_e = tk.Entry(b, font=("Segoe UI", 11), relief="solid", bd=1)
        self.user_e.pack(fill="x", pady=(2, 12))
        tk.Label(b, text="Password", bg=BG, fg=NAVY, font=("Segoe UI", 10)).pack(anchor="w")
        self.pw_e = tk.Entry(b, font=("Segoe UI", 11), relief="solid", bd=1, show="•")
        self.pw_e.pack(fill="x", pady=(2, 12))
        self.msg = tk.Label(b, text="", bg=BG, fg=RED, font=("Segoe UI", 9), wraplength=420,
                            justify="left")
        self.msg.pack(anchor="w")
        tk.Button(b, text="Sign in", command=self._sign_in, bg=NAVY, fg=WHITE, relief="flat",
                  font=("Segoe UI", 11, "bold"), padx=22, pady=8, cursor="hand2",
                  activebackground=NAVY2, activeforeground=WHITE).pack(anchor="e", pady=(10, 0))
        self.user_e.focus_set()
        self.root.bind("<Return>", lambda e: self._sign_in())

    def _sign_in(self):
        username = self.user_e.get().strip().lower()
        rec = access.authenticate(username, self.pw_e.get(), self.store)
        if rec is None:
            self.attempts += 1
            left = access.MAX_LOGIN_ATTEMPTS - self.attempts
            if left <= 0:
                messagebox.showerror("Locked", "Too many failed sign-in attempts. "
                                     "The program will now close.")
                self.root.destroy(); return
            self.msg.config(text=f"Login ID or password is incorrect. {left} attempt(s) left.")
            self.pw_e.delete(0, "end"); return
        self.username = username
        lic, reason = access.licence_status(rec, username)
        if lic:
            self._finish(lic)
        else:
            self._activation_view(reason)

    def _activation_view(self, reason):
        self.root.unbind("<Return>")
        self._clear()
        self._header("Activate your licence", f"Login ID: {self.username}")
        b = tk.Frame(self.frame, bg=BG); b.pack(fill="both", expand=True, padx=32, pady=18)
        tk.Label(b, text=reason, bg=BG, fg=AMBER, font=("Segoe UI", 10, "bold"),
                 wraplength=440, justify="left").pack(anchor="w")
        tk.Label(b, text="Paste the licence key you received from the vendor:",
                 bg=BG, fg=NAVY, font=("Segoe UI", 10)).pack(anchor="w", pady=(12, 4))
        self.key_t = tk.Text(b, height=6, wrap="char", font=("Consolas", 9),
                             relief="solid", bd=1)
        self.key_t.pack(fill="x")
        self.msg = tk.Label(b, text="", bg=BG, fg=RED, font=("Segoe UI", 9), wraplength=440,
                            justify="left")
        self.msg.pack(anchor="w", pady=(6, 0))
        bar = tk.Frame(b, bg=BG); bar.pack(fill="x", pady=(10, 0))
        tk.Button(bar, text="Back", command=self._login_view, bg=WHITE, fg=MUTED,
                  relief="solid", bd=1, font=("Segoe UI", 10), padx=14, pady=6).pack(side="left")
        tk.Button(bar, text="Activate", command=self._activate, bg=NAVY, fg=WHITE,
                  relief="flat", font=("Segoe UI", 11, "bold"), padx=22, pady=7,
                  cursor="hand2", activebackground=NAVY2,
                  activeforeground=WHITE).pack(side="right")
        self.key_t.focus_set()

    def _activate(self):
        key = self.key_t.get("1.0", "end").strip()
        try:
            lic = access.verify_licence(key, self.username)
        except ValueError as e:
            self.msg.config(text=str(e)); return
        self.store["users"][self.username]["licence_key"] = "".join(key.split())
        try:
            access.save_users(self.store)
        except OSError as e:
            self.msg.config(text=f"Licence is valid but could not be saved: {e}"); return
        messagebox.showinfo("Licence activated",
                            f"Licence {lic['licence_no']} activated for {lic['licensee']}.\n"
                            f"Valid until {datetime_text(lic['expires'])}.")
        self._finish(lic)

    def _finish(self, lic):
        self.root.unbind("<Return>")
        self.frame.destroy()
        # the role comes from the SIGNED licence, not from the editable users file
        self.on_success({"username": self.username, "role": lic["role"],
                         "licence": lic, "store": self.store})


# ===========================================================================
#  USERS  (admin only)  --  view licences, reset a password
# ===========================================================================
class UserAdmin(tk.Toplevel):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session, self.store = session, session["store"]
        self.title("JE Testing — Users & Licences")
        self.configure(bg=BG); self.geometry("720x380"); self.transient(parent)
        head = tk.Frame(self, bg=NAVY); head.pack(fill="x")
        tk.Label(head, text="Users & Licences", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=14)
        cols = ("login", "role", "licence", "licensee", "expires", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=6)
        for c, w in zip(cols, (90, 70, 110, 200, 90, 130)):
            self.tree.heading(c, text=c.title()); self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=14, pady=10)
        bar = tk.Frame(self, bg=BG); bar.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(bar, text="Reset password of selected user", command=self._reset_pw,
                  bg=WHITE, fg=NAVY, relief="solid", bd=1, font=("Segoe UI", 10),
                  padx=12, pady=6).pack(side="left")
        tk.Button(bar, text="Close", command=self.destroy, bg=WHITE, fg=MUTED,
                  relief="solid", bd=1, font=("Segoe UI", 10), padx=14, pady=6).pack(side="right")
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for name, rec in sorted(self.store["users"].items()):
            lic, reason = access.licence_status(rec, name)
            self.tree.insert("", "end", iid=name, values=(
                name, lic["role"] if lic else rec.get("role", ""),
                lic["licence_no"] if lic else "-", lic["licensee"] if lic else "-",
                datetime_text(lic["expires"]) if lic else "-",
                "Active" if lic else ("Not activated" if not rec.get("licence_key")
                                      else "INVALID / EXPIRED")))

    def _reset_pw(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Users", "Select a user first.", parent=self); return
        name = sel[0]
        from tkinter import simpledialog
        pw = simpledialog.askstring("Reset password", f"New password for '{name}' "
                                    "(min 8 characters):", show="•", parent=self)
        if not pw:
            return
        try:
            access.set_password(self.store, name, pw)
            access.save_users(self.store)
            messagebox.showinfo("Users", f"Password for '{name}' changed.", parent=self)
        except (ValueError, OSError) as e:
            messagebox.showerror("Users", str(e), parent=self)


def _set_window_icon(root):
    """JE icon on every window's title bar (bundled inside the .exe)."""
    here = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon = here / "icon.ico"
    if icon.exists():
        try:
            root.iconbitmap(default=str(icon))
        except tk.TclError as e:    # cosmetic only: keep the default icon
            print(f"  (Window icon not set: {e})")


def main():
    root = tk.Tk()
    _set_window_icon(root)
    try:
        store = access.load_users()
    except (FileNotFoundError, ValueError) as e:
        root.withdraw(); messagebox.showerror("Journal Entry Testing", str(e))
        root.destroy(); return
    LoginScreen(root, store, lambda session: JEApp(root, session))
    root.mainloop()


if __name__ == "__main__":
    main()
