"""
GURU - GST Returns Downloader & Compliance Dashboard  (v2)
Mogalapalli & Co., Chartered Accountants

Run:  python main.py      (first time: setup.bat)
"""
import os
import queue
import subprocess
import sys
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd

import compliance as comp
from portal_config import MONTHS

BLUE = "#1F4E79"
ITEMS = [  # key, label, default
    ("status", "Filing status & compliance dashboard", True),
    ("notices", "Notices & orders (received / pending)", True),
    ("gstr3b", "GSTR-3B (Excel: table-wise, month-wise)", True),
    ("gstr1", "GSTR-1 summary (Excel: section-wise)", True),
    ("gstr2b", "GSTR-2B invoices & ITC (Excel)", True),
    ("cert", "Registration Certificate REG-06 (PDF)", True),
    ("gstr9", "GSTR-9 data (Excel)", False),
    ("pdf3b", "GSTR-3B PDF exactly as portal prints (slower)", False),
    ("gstr2a", "GSTR-2A files (request, collect after ~20 min)", False),
    ("gstr1json", "GSTR-1 full JSON (request, collect after ~20 min)", False),
]
STATE_COLORS = {"Filed on time": "#C6EFCE", "Filed late": "#FFEB9C", "Not filed - overdue": "#FFC7CE",
                "Not yet due": "#EDEDED"}


def fy_list():
    t = date.today()
    cur = t.year if t.month >= 4 else t.year - 1
    return [f"{y}-{str(y + 1)[2:]}" for y in range(cur, 2016, -1)]


def open_path(p):
    p = str(p)
    if sys.platform.startswith("win"):
        os.startfile(p)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GURU - GST Returns Downloader & Compliance Dashboard")
        self.geometry("1180x900")
        self.minsize(1000, 700)
        self.q = queue.Queue()
        self.worker = None
        self.logged_in = False
        self.gstin = tk.StringVar()
        self.out_dir = tk.StringVar(value=str(Path.home() / "Documents" / "GST_Downloads"))
        self.status_df = None
        self.recon_df = None
        self._cap_img = None
        self._style()
        self._header()
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)
        self.login_frame = self._build_login()
        self.login_frame.pack(fill="both", expand=True)
        self.main_frame = None
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(150, self.poll)

    # ------------------------------------------------------------ look
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Accent.TButton", foreground="white", background=BLUE, padding=7)
        s.map("Accent.TButton", background=[("active", "#2E75B6"), ("disabled", "#9DB3C9")])
        s.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        s.configure("CardT.TLabel", background="white", foreground="#555")
        s.configure("CardV.TLabel", background="white", foreground=BLUE, font=("Segoe UI", 18, "bold"))
        s.configure("H.TLabel", font=("Segoe UI", 11, "bold"), foreground=BLUE)
        s.configure("Treeview", rowheight=23)

    def _header(self):
        h = tk.Frame(self, bg=BLUE, height=48)
        h.pack(fill="x")
        tk.Label(h, text="GURU", bg=BLUE, fg="#9DC3E6", font=("Segoe UI", 18, "bold")).pack(side="left", padx=(14, 6))
        tk.Label(h, text="GST Returns Downloader & Compliance Dashboard", bg=BLUE, fg="white",
                 font=("Segoe UI", 12)).pack(side="left")
        self.hdr = tk.Label(h, text="", bg=BLUE, fg="white", font=("Segoe UI", 10, "bold"))
        self.hdr.pack(side="right", padx=14)

    # ------------------------------------------------------------ LOGIN SCREEN
    def _build_login(self):
        f = ttk.Frame(self.body, padding=20)
        box = ttk.LabelFrame(f, text="  Step 1 - Login to GST portal  ", padding=18)
        box.place(relx=0.5, rely=0.46, anchor="center")
        ttk.Label(box, text="GST Username").grid(row=0, column=0, sticky="w", pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.user_var, width=34).grid(row=0, column=1, columnspan=2, sticky="we")
        ttk.Label(box, text="Password").grid(row=1, column=0, sticky="w", pady=5)
        self.pwd_var = tk.StringVar()
        self.pwd_entry = ttk.Entry(box, textvariable=self.pwd_var, show="*", width=34)
        self.pwd_entry.grid(row=1, column=1, columnspan=2, sticky="we")
        self.show_pwd = tk.BooleanVar()
        ttk.Checkbutton(box, text="Show", variable=self.show_pwd,
                        command=lambda: self.pwd_entry.config(show="" if self.show_pwd.get() else "*")).grid(row=1, column=3)
        ttk.Button(box, text="1. Open portal & show captcha", style="Accent.TButton",
                   command=self.get_captcha).grid(row=2, column=1, columnspan=2, sticky="we", pady=(10, 4))
        ttk.Separator(box).grid(row=3, column=0, columnspan=4, sticky="we", pady=8)
        ttk.Label(box, text="Captcha").grid(row=4, column=0, sticky="nw")
        self.cap_label = tk.Label(box, text="(captcha appears here)", bg="#F2F2F2", width=30, height=4, relief="groove")
        self.cap_label.grid(row=4, column=1, columnspan=2, sticky="we")
        ttk.Button(box, text="New captcha", command=lambda: self.worker and self.worker.submit("refresh_captcha")
                   ).grid(row=4, column=3, sticky="n", padx=6)
        ttk.Label(box, text="Type captcha (digits)").grid(row=5, column=0, sticky="w", pady=6)
        self.cap_var = tk.StringVar()
        e = ttk.Entry(box, textvariable=self.cap_var, width=14, font=("Consolas", 14))
        e.grid(row=5, column=1, sticky="w")
        e.bind("<Return>", lambda _: self.do_login())
        ttk.Button(box, text="2. LOGIN", style="Accent.TButton", command=self.do_login).grid(
            row=6, column=1, columnspan=2, sticky="we", pady=(8, 4))
        ttk.Button(box, text="I have logged in in the browser (continue)", command=self.confirm_login).grid(
            row=7, column=1, columnspan=2, sticky="we")
        self.login_msg = ttk.Label(box, text="", foreground="#C00000", wraplength=440)
        self.login_msg.grid(row=8, column=0, columnspan=4, pady=(8, 0))
        ttk.Separator(box).grid(row=9, column=0, columnspan=4, sticky="we", pady=10)
        ttk.Button(box, text="Open dashboard offline (from a saved Compliance workbook)",
                   command=self.go_offline).grid(row=10, column=1, columnspan=2, sticky="we")
        ttk.Label(box, foreground="#555", wraplength=460, justify="left", text=(
            "A browser window opens next to this app. The captcha is shown here for you to read and type; "
            "you can also type it in the browser. If the portal asks for an OTP, enter it in the browser. "
            "Your password is not saved anywhere.")).grid(row=11, column=0, columnspan=4, pady=(10, 0))
        return f

    def ensure_worker(self):
        if self.worker is None or not self.worker.is_alive():
            try:
                from portal import PortalWorker
            except ImportError as e:
                messagebox.showerror("Setup needed", f"A required package is missing ({e}).\nRun setup.bat first.")
                return False
            self.worker = PortalWorker(self.q)
            self.worker.start()
        return True

    def get_captcha(self):
        if not self.user_var.get().strip():
            return self.login_msg.config(text="Enter the GST username first.")
        if self.ensure_worker():
            self.login_msg.config(text="Opening portal... (first start can take 10-20 seconds)", foreground="#555")
            self.worker.submit("open_login", self.user_var.get().strip())

    def do_login(self):
        if not self.worker:
            return self.get_captcha()
        if not self.pwd_var.get():
            return self.login_msg.config(text="Enter the password.", foreground="#C00000")
        self.login_msg.config(text="Logging in...", foreground="#555")
        self.worker.submit("login", self.pwd_var.get(), self.cap_var.get().strip())

    def confirm_login(self):
        if self.ensure_worker():
            self.worker.submit("confirm_logged_in")

    def show_captcha(self, png, error):
        if png:
            img = tk.PhotoImage(data=png)
            if img.width() < 220:
                img = img.zoom(2, 2)
            self._cap_img = img
            self.cap_label.config(image=img, text="", width=img.width(), height=img.height())
        self.cap_var.set("")
        self.login_msg.config(text=error or "Type the captcha and press LOGIN (or Enter).",
                              foreground="#C00000" if error else "#2E7D32")

    def go_offline(self):
        self.open_main()
        self.nb.select(self.tab_dash)
        self.load_workbook()

    # ------------------------------------------------------------ MAIN SCREEN
    def open_main(self):
        self.login_frame.pack_forget()
        if self.main_frame:
            return self.main_frame.pack(fill="both", expand=True)
        self.main_frame = ttk.Frame(self.body)
        self.main_frame.pack(fill="both", expand=True)
        self.nb = ttk.Notebook(self.main_frame)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_dl = ttk.Frame(self.nb, padding=10)
        self.tab_dash = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_dl, text="  Step 2 - Download  ")
        self.nb.add(self.tab_dash, text="  Compliance dashboard  ")
        self._build_downloads()
        self._build_dashboard()

    def _build_downloads(self):
        t = self.tab_dl
        left = ttk.Frame(t)
        left.pack(side="left", fill="y", padx=(0, 10))
        right = ttk.Frame(t)
        right.pack(side="left", fill="both", expand=True)

        # action buttons pinned at the bottom of the left column - always visible,
        # whatever the laptop's screen height (so START is never clipped off-screen)
        actions = ttk.Frame(left)
        actions.pack(side="bottom", fill="x")
        self.btn_start = ttk.Button(actions, text="START", style="Accent.TButton", command=self.start_jobs)
        self.btn_start.pack(fill="x", pady=(8, 4))
        ttk.Button(actions, text="Stop after current step", command=self.stop_jobs).pack(fill="x")
        ttk.Button(actions, text="Open download folder", command=self.open_out).pack(fill="x", pady=4)

        # the controls above the buttons scroll if the window is short
        _cv = tk.Canvas(left, width=372, highlightthickness=0, borderwidth=0)
        _vsb = ttk.Scrollbar(left, orient="vertical", command=_cv.yview)
        _cv.configure(yscrollcommand=_vsb.set)
        _vsb.pack(side="right", fill="y")
        _cv.pack(side="left", fill="both", expand=True)
        lc = ttk.Frame(_cv)
        _win = _cv.create_window((0, 0), window=lc, anchor="nw")
        lc.bind("<Configure>", lambda e: _cv.configure(scrollregion=_cv.bbox("all")))
        _cv.bind("<Configure>", lambda e: _cv.itemconfigure(_win, width=e.width))

        def _wheel(e):
            w = self.winfo_containing(e.x_root, e.y_root)
            while w is not None:
                if w is _cv:
                    _cv.yview_scroll(int(-(e.delta or 0) / 120), "units")
                    return
                w = getattr(w, "master", None)
        _cv.bind_all("<MouseWheel>", _wheel)

        f0 = ttk.LabelFrame(lc, text=" Financial years (select one or more) ", padding=8)
        f0.pack(fill="x")
        fy_box = ttk.Frame(f0)
        fy_box.pack(fill="x")
        self.fy_list = tk.Listbox(fy_box, selectmode="extended", height=6, exportselection=False,
                                  activestyle="none")
        fys = fy_list()
        for f in fys:
            self.fy_list.insert("end", f)
        self.fy_list.selection_set(0)       # current FY selected by default
        sb = ttk.Scrollbar(fy_box, command=self.fy_list.yview)
        self.fy_list.config(yscrollcommand=sb.set)
        self.fy_list.pack(side="left", fill="x", expand=True)
        sb.pack(side="left", fill="y")
        ttk.Label(f0, text="Ctrl/Shift-click to pick several years.", foreground="#777").pack(anchor="w")

        f1 = ttk.LabelFrame(lc, text=" Months (applied to every selected year) ", padding=8)
        f1.pack(fill="x", pady=(8, 0))
        self.month_vars = {}
        for i, m in enumerate(MONTHS):
            v = tk.BooleanVar(value=True)
            self.month_vars[m] = v
            ttk.Checkbutton(f1, text=m[:3], variable=v).grid(row=i // 4, column=i % 4, sticky="w", padx=2)
        bf = ttk.Frame(f1)
        bf.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Button(bf, text="All", width=6, command=lambda: [v.set(True) for v in self.month_vars.values()]).pack(side="left")
        ttk.Button(bf, text="None", width=6, command=lambda: [v.set(False) for v in self.month_vars.values()]).pack(side="left", padx=4)
        ttk.Label(f1, text="Months not yet open on the portal are skipped.", foreground="#777").grid(row=4, column=0, columnspan=4, sticky="w")

        f2 = ttk.LabelFrame(lc, text=" What to download ", padding=8)
        f2.pack(fill="x", pady=8)
        self.item_vars = {}
        for k, label, d in ITEMS:
            v = tk.BooleanVar(value=d)
            self.item_vars[k] = v
            ttk.Checkbutton(f2, text=label, variable=v).pack(anchor="w")

        fe = ttk.LabelFrame(lc, text=" E-way bills (optional) ", padding=8)
        fe.pack(fill="x", pady=(0, 8))
        self.ewb_files = []
        self.ewb_lbl = ttk.Label(fe, text="No e-way bill export added.", foreground="#777")
        self.ewb_lbl.pack(anchor="w")
        be = ttk.Frame(fe)
        be.pack(fill="x", pady=(4, 0))
        ttk.Button(be, text="1. Open e-way bill portal", command=self.open_ewb_portal).pack(side="left")
        ttk.Button(be, text="Add export file(s)", command=self.add_ewb_files).pack(side="left", padx=4)

        # automated complete download across 5-day windows
        de = ttk.Frame(fe)
        de.pack(fill="x", pady=(6, 0))
        ttk.Label(de, text="From").pack(side="left")
        self.ewb_from = tk.StringVar(value="01/04/2025")
        ttk.Entry(de, textvariable=self.ewb_from, width=11).pack(side="left", padx=(2, 8))
        ttk.Label(de, text="To").pack(side="left")
        self.ewb_to = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        ttk.Entry(de, textvariable=self.ewb_to, width=11).pack(side="left", padx=2)
        self.ewb_inward = tk.BooleanVar(value=False)
        ttk.Checkbutton(de, text="also inward", variable=self.ewb_inward).pack(side="left", padx=6)
        self.btn_ewb_dl = ttk.Button(fe, text="2. Download complete EWB records",
                                     command=self.download_ewb_range)
        self.btn_ewb_dl.pack(fill="x", pady=(6, 0))
        ttk.Label(fe, text="Dates are dd/mm/yyyy. After you log in to the portal (step 1), the app pulls\n"
                          "every record itself in 5-day windows (the portal's limit) and combines them.\n"
                          "Or use 'Add export file(s)' for a report you downloaded by hand.",
                  foreground="#777", justify="left").pack(anchor="w")

        f3 = ttk.LabelFrame(lc, text=" Save to folder ", padding=8)
        f3.pack(fill="x", pady=(0, 4))
        ttk.Entry(f3, textvariable=self.out_dir, width=34).pack(side="left", fill="x", expand=True)
        ttk.Button(f3, text="...", width=3, command=self.pick_folder).pack(side="left", padx=4)

        ttk.Label(right, text="Progress", style="H.TLabel").pack(anchor="w")
        self.prog = ttk.Progressbar(right, mode="indeterminate")
        self.prog.pack(fill="x", pady=4)
        self.prog_lbl = ttk.Label(right, text="Ready.")
        self.prog_lbl.pack(anchor="w")
        cols = ("item", "period", "status", "file")
        self.res_tree = ttk.Treeview(right, columns=cols, show="headings", height=11)
        for c, w in zip(cols, (170, 110, 300, 330)):
            self.res_tree.heading(c, text=c.title())
            self.res_tree.column(c, width=w, anchor="w")
        self.res_tree.tag_configure("ok", background="#C6EFCE")
        self.res_tree.tag_configure("warn", background="#FFEB9C")
        self.res_tree.tag_configure("bad", background="#FFC7CE")
        self.res_tree.bind("<Double-1>", self._open_result)
        self.res_tree.pack(fill="x", pady=6)
        ttk.Label(right, text="Double-click a row to open its file.", foreground="#777").pack(anchor="w")
        ttk.Label(right, text="Activity log", style="H.TLabel").pack(anchor="w", pady=(6, 0))
        lf = ttk.Frame(right)
        lf.pack(fill="both", expand=True)
        self.log_txt = tk.Text(lf, height=10, font=("Consolas", 9), wrap="word", bg="#FAFAFA")
        sb = ttk.Scrollbar(lf, command=self.log_txt.yview)
        self.log_txt.config(yscrollcommand=sb.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.out_dir.get())
        if d:
            self.out_dir.set(d)

    def add_ewb_files(self):
        fs = filedialog.askopenfilenames(title="Select e-way bill export file(s)",
                                         filetypes=[("Excel / CSV", "*.xlsx *.xls *.csv"), ("All", "*.*")])
        if fs:
            self.ewb_files = list(fs)
            self.ewb_lbl.config(text=f"{len(self.ewb_files)} e-way bill file(s) selected.", foreground="#2E7D32")

    def open_ewb_portal(self):
        if not self.ensure_worker():
            return
        self.log("Opening e-way bill portal...")
        self.worker.submit("open_ewb", self.out_dir.get())

    def download_ewb_range(self):
        if not self.ensure_worker():
            return
        frm, to = self.ewb_from.get().strip(), self.ewb_to.get().strip()
        for s in (frm, to):
            try:
                datetime.strptime(s, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Dates", "Enter dates as dd/mm/yyyy, e.g. 01/04/2025.")
                return
        self.prog.start(12)
        self.prog_lbl.config(text="Downloading e-way bill records...")
        self.log(f"Downloading complete e-way bill records {frm} to {to} "
                 f"(5-day windows){' + inward' if self.ewb_inward.get() else ''}...")
        self.worker.submit("download_ewb_range", self.out_dir.get(), frm, to, bool(self.ewb_inward.get()))

    def open_out(self):
        p = Path(self.out_dir.get())
        if self.gstin.get() and (p / self.gstin.get()).exists():
            p = p / self.gstin.get()
        p.mkdir(parents=True, exist_ok=True)
        open_path(p)

    def _open_result(self, _):
        sel = self.res_tree.selection()
        if sel:
            f = self.res_tree.item(sel[0])["values"][3]
            if f and Path(str(f)).exists():
                open_path(f)

    def open_portfolio(self):
        if self.portfolio_path and Path(self.portfolio_path).exists():
            return open_path(self.portfolio_path)
        root = Path(self.out_dir.get())
        try:
            import dashboard as dash
            out = dash.generate_portfolio(root)
            if not out:
                return messagebox.showinfo("No clients yet", "Download at least one GSTIN first - the firm "
                                           "portfolio is built from every GSTIN folder under your save folder.")
            self.portfolio_path = str(out)
            open_path(self.portfolio_path)
        except Exception as e:
            messagebox.showerror("Could not build portfolio", str(e))

    def open_html_dashboard(self):
        # already built this session?
        if self.html_path and Path(self.html_path).exists():
            return open_path(self.html_path)
        # else (re)build from the folder of the loaded/last workbook
        base = Path(self.dash_path).parent if self.dash_path else None
        if not base or not (base / "json").exists():
            return messagebox.showinfo("No data yet", "Run a download first, or load a saved Compliance "
                                       "workbook from a folder that still has its 'json' subfolder.")
        try:
            import dashboard as dash
            root = base.parent      # GSTIN root
            out = dash.generate_overview(root) if any(root.glob("*/json")) else None
            self.html_path = str(out or dash.generate(base))
            open_path(self.html_path)
        except Exception as e:
            messagebox.showerror("Could not build dashboard", str(e))

    def start_jobs(self):
        if not self.logged_in:
            return messagebox.showwarning("Not logged in", "Log in to the GST portal first.")
        fys = [self.fy_list.get(i) for i in self.fy_list.curselection()]
        months = [m for m, v in self.month_vars.items() if v.get()]
        items = [k for k, v in self.item_vars.items() if v.get()]
        if not fys:
            return messagebox.showwarning("No year", "Select at least one financial year.")
        if not items or not months:
            return messagebox.showwarning("Nothing selected", "Tick at least one month and one item.")
        self.res_tree.delete(*self.res_tree.get_children())
        self.btn_start.config(state="disabled")
        self.prog.start(12)
        Path(self.out_dir.get()).mkdir(parents=True, exist_ok=True)
        self.html_path = None
        self.portfolio_path = None
        self.worker.stop_flag = False
        self.worker.submit("run_jobs", {"fys": fys, "months": months, "items": items,
                                        "out_dir": self.out_dir.get(), "ewb_files": self.ewb_files})

    def stop_jobs(self):
        if self.worker:
            self.worker.stop_flag = True
            self.log("Stop requested...")

    def log(self, msg):
        if self.main_frame:
            self.log_txt.insert("end", msg + "\n")
            self.log_txt.see("end")

    # ------------------------------------------------------------ DASHBOARD
    def _build_dashboard(self):
        t = self.tab_dash
        bar = ttk.Frame(t)
        bar.pack(fill="x")
        self.dash_title = ttk.Label(bar, text="No data yet - run a download with 'Filing status' ticked, "
                                              "or load a saved Compliance workbook.", style="H.TLabel")
        self.dash_title.pack(side="left")
        ttk.Button(bar, text="Load saved workbook", command=self.load_workbook).pack(side="right")
        ttk.Button(bar, text="Open workbook", command=lambda: self.dash_path and open_path(self.dash_path)).pack(side="right", padx=4)
        ttk.Button(bar, text="Open HTML dashboard", style="Accent.TButton",
                   command=self.open_html_dashboard).pack(side="right", padx=4)
        ttk.Button(bar, text="Firm portfolio (all clients)",
                   command=self.open_portfolio).pack(side="right", padx=4)
        self.dash_path = None
        self.html_path = None
        self.portfolio_path = None

        cards = ttk.Frame(t)
        cards.pack(fill="x", pady=8)
        self.cards = {}
        for k, title in (("due", "Returns due"), ("on_time", "Filed on time"), ("late", "Filed late"),
                         ("pending", "Overdue / not filed"), ("score", "Compliance score"), ("late_fee", "Est. late fee (Rs)")):
            c = ttk.Frame(cards, style="Card.TFrame", padding=(12, 8))
            c.pack(side="left", fill="x", expand=True, padx=4)
            ttk.Label(c, text=title, style="CardT.TLabel").pack(anchor="w")
            v = ttk.Label(c, text="-", style="CardV.TLabel")
            v.pack(anchor="w")
            self.cards[k] = v

        inner = ttk.Notebook(t)
        inner.pack(fill="both", expand=True)
        self.tv_status = self._tree(inner, "Return-wise status")
        self.tv_grid = self._tree(inner, "Month grid")
        self.tv_recon = self._tree(inner, "Reconciliation (GSTR-1 vs 3B, 2B vs 3B)")
        for st, col in STATE_COLORS.items():
            self.tv_status.tag_configure(st, background=col)
        self.tv_recon.tag_configure("flag", background="#FFC7CE")
        ttk.Label(t, foreground="#777", wraplength=1100, text=(
            "Due dates and filing status come from the portal (Returns Dashboard and View e-Filed Returns). "
            "Late fee is an estimate: GSTR-1/3B Rs 50/day (nil Rs 20/day, max Rs 500), capped by your aggregate "
            "turnover read from the portal; GSTR-9 as per Notification 07/2023-CT. Interest u/s 50 not computed.")
                  ).pack(anchor="w", pady=(4, 0))

    def _tree(self, nb, title):
        f = ttk.Frame(nb)
        nb.add(f, text=f"  {title}  ")
        tv = ttk.Treeview(f, show="headings")
        ys = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        xs = ttk.Scrollbar(f, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tv.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        return tv

    @staticmethod
    def _fill(tv, df, tag_col=None, tag_fn=None):
        tv.delete(*tv.get_children())
        if df is None or df.empty:
            tv["columns"] = ()
            return
        cols = [str(c) for c in df.columns]
        tv["columns"] = cols
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=max(80, min(220, len(c) * 9)), anchor="center")
        for _, r in df.iterrows():
            vals = []
            for v in r.values:
                if v is None or v is pd.NaT or (not isinstance(v, (str, list, dict)) and pd.isna(v)):
                    vals.append("")
                elif isinstance(v, float):
                    vals.append("" if pd.isna(v) else f"{v:,.2f}")
                elif hasattr(v, "strftime"):
                    vals.append(v.strftime("%d-%m-%Y"))
                else:
                    vals.append("" if v is None or (not isinstance(v, str) and pd.isna(v)) else v)
            tags = ()
            if tag_col and tag_col in df:
                tags = (r[tag_col],)
            if tag_fn:
                tags = tag_fn(r)
            tv.insert("", "end", values=vals, tags=tags)

    def show_dashboard(self, fy, gstin, status, recon, path=""):
        self.status_df, self.recon_df, self.dash_path = status, recon, path or None
        self.dash_title.config(text=f"{gstin}  |  FY {fy}")
        s = comp.summary(status)
        for k, v in s.items():
            self.cards[k].config(text=f"{v}%" if k == "score" else (f"{v:,.0f}" if k == "late_fee" else str(v)))
        self.cards["score"].config(foreground="#2E7D32" if s["score"] >= 90 else ("#BF9000" if s["score"] >= 70 else "#C00000"))
        self._fill(self.tv_status, status, tag_col="Status")
        self._fill(self.tv_grid, comp.month_grid(status))
        self._fill(self.tv_recon, recon, tag_fn=lambda r: ("flag",) if r.get("Flag", "OK") != "OK" else ())

    def load_workbook(self):
        p = filedialog.askopenfilename(title="Select <GSTIN>_Compliance_<FY>.xlsx", initialdir=self.out_dir.get(),
                                       filetypes=[("Excel", "*.xlsx")])
        if not p:
            return
        try:
            st = pd.read_excel(p, sheet_name="Return status", header=2)
            for c in ("Due date", "Filed on"):
                st[c] = pd.to_datetime(st[c], errors="coerce").dt.date
            st["Days late"] = st["Days late"].fillna(0).astype(int)
            try:
                rc = pd.read_excel(p, sheet_name="Reconciliation", header=2)
            except Exception:
                rc = None
            name = Path(p).stem.split("_")
            self.show_dashboard(name[-1] if name else "", name[0] if name else "", st, rc, p)
            self.nb.select(self.tab_dash)
        except Exception as e:
            messagebox.showerror("Could not read workbook", str(e))

    # ------------------------------------------------------------ worker messages
    def poll(self):
        try:
            while True:
                kind, kw = self.q.get_nowait()
                self.handle(kind, kw)
        except queue.Empty:
            pass
        self.after(150, self.poll)

    def handle(self, kind, kw):
        if kind == "log":
            self.log(kw["msg"])
        elif kind == "captcha":
            self.show_captcha(kw.get("png"), kw.get("error", ""))
        elif kind == "otp":
            self.login_msg.config(text=kw["msg"], foreground="#BF9000")
        elif kind == "logged_in":
            self.logged_in = True
            self.pwd_var.set("")
            self.gstin.set(kw["gstin"])
            self.hdr.config(text=f"Logged in  |  GSTIN {kw['gstin']}")
            self.open_main()
            self.log(f"Logged in. GSTIN {kw['gstin']}")
        elif kind == "progress":
            self.prog_lbl.config(text=kw["text"])
        elif kind == "result":
            st = str(kw["status"])
            tag = "ok" if st.startswith(("saved", "downloaded")) or "found" in st else \
                ("bad" if st.startswith(("error", "could not")) else "warn")
            self.res_tree.insert("", "end", values=(kw["item"], kw["period"], st, kw["file"]), tags=(tag,))
        elif kind == "status_data":
            self.show_dashboard(kw["fy"], kw["gstin"], kw["status"], kw["recon"], kw.get("path", ""))
        elif kind == "notices_data":
            n = kw.get("summary", {})
            self.log(f"Notices & orders: {n.get('total', 0)} found, {n.get('pending', 0)} pending, "
                     f"{n.get('orders', 0)} order(s).")
        elif kind == "dashboard_ready":
            self.html_path = kw["path"]
        elif kind == "portfolio_ready":
            self.portfolio_path = kw["path"]
        elif kind == "ewb_opened":
            self.log(f"E-way bill portal opened. Log in there (captcha / OTP), then set From/To "
                     f"and click 'Download complete EWB records'. Files are saved in "
                     f"{kw.get('folder','the ewb folder')}.")
        elif kind == "ewb_downloaded":
            self.log(f"E-way bill report saved: {kw['path']}")
            self.ewb_lbl.config(text="E-way bill records downloaded - they're included automatically on START.",
                                foreground="#2E7D32")
        elif kind == "ewb_progress":
            self.prog_lbl.config(text=f"E-way bills: {kw.get('done', 0)} window(s) done, "
                                      f"{kw.get('saved', 0)} file(s) saved...")
        elif kind == "ewb_range_done":
            self.prog.stop()
            n, empty = len(kw.get("files", [])), kw.get("empty", 0)
            self.prog_lbl.config(text=f"E-way bill download finished - {n} file(s) saved.")
            self.log(f"E-way bill download finished: {n} file(s) in {kw.get('folder','')} "
                     f"({empty} empty window(s) skipped). They're combined automatically on START.")
            self.ewb_lbl.config(text=f"{n} e-way bill file(s) downloaded - included automatically on START.",
                                foreground="#2E7D32")
        elif kind == "jobs_done":
            self.prog.stop()
            if self.main_frame:
                self.btn_start.config(state="normal")
                self.prog_lbl.config(text=f"Finished. {len(kw['results'])} item(s) - see table below.")
                if self.html_path:
                    try:
                        open_path(self.html_path)
                    except Exception:
                        pass
        elif kind == "session_lost":
            self.prog.stop()
            self.logged_in = False
            if self.main_frame:
                self.btn_start.config(state="normal")
                self.main_frame.pack_forget()
            self.login_frame.pack(fill="both", expand=True)
            self.login_msg.config(text=f"{kw['msg']}\nClick 'Open portal & show captcha' to log in again.", foreground="#C00000")
        elif kind == "error":
            self.prog.stop()
            if self.main_frame and self.logged_in:
                self.btn_start.config(state="normal")
                self.prog_lbl.config(text=f"Error: {kw['msg']}")
            else:
                self.login_msg.config(text=f"Error: {kw['msg']}", foreground="#C00000")
        elif kind == "fatal":
            messagebox.showerror("Browser problem", kw["msg"])

    def on_close(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop_flag = True
            self.worker.submit("quit")
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
