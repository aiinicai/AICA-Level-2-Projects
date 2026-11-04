"""
E-Proceedings Consolidator  (modern UI)
Input : Excel with columns  name | pan | password
Output: merged E-Proceedings (For Your Action + For Your Information) for all clients,
        plus a separate window listing clients whose password/PAN failed.
"""
import os
import re
import csv
import queue
import shutil
import time
import tempfile
import threading
import tkinter as tk
from io import StringIO
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import customtkinter as ctk
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

LOGIN_URL = "https://eportal.incometax.gov.in/iec/foservices/#/login"
TABS = ["For Your Action", "For Your Information"]
TIMEOUT = 45_000

PAN_ERR = re.compile(r"invalid pan|pan does not exist|not registered|does not exist|"
                     r"not valid|no records|enter valid pan", re.I)
LOCK_ERR = re.compile(r"locked|blocked|attempts exceeded|too many", re.I)
PWD_ERR = re.compile(r"invalid password|incorrect password|wrong password|invalid credentials|"
                     r"enter valid password|password.{0,40}(invalid|incorrect|wrong|not match)|"
                     r"(invalid|incorrect|wrong).{0,40}password", re.I)
NOT_AUTH = re.compile(r"not authenticated|request is not", re.I)

ACCENT, GREEN, RED, AMBER = "#5b7cfa", "#2ecc71", "#ff5c6c", "#f5b942"
BG, CARD, ROW1, ROW2 = "#12141c", "#1c2030", "#1e2230", "#242a3c"


class LoginError(Exception):
    def __init__(self, kind, text):
        super().__init__(text)
        self.kind, self.text = kind, text


# ------------------------------------------------------------- data helpers
def read_clients(path):
    df = pd.read_excel(path, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = {"name", "pan", "password"} - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing column(s): {', '.join(sorted(missing))}")
    df = df.dropna(subset=["pan", "password"])
    df["pan"] = df["pan"].str.strip().str.upper()
    df["name"] = df["name"].fillna("").str.strip()
    return df[["name", "pan", "password"]].to_dict("records")


def _load_any(path):
    with open(path, "rb") as f:
        head = f.read(2048)
    if head[:2] == b"PK":
        return pd.read_excel(path, header=None, dtype=str, engine="openpyxl")
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return pd.read_excel(path, header=None, dtype=str, engine="xlrd")
    text = None
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            break
        except Exception:
            continue
    if text is None:
        raise ValueError("Unreadable file")
    low = text.lower()
    if "<table" in low or "<html" in low:
        tables = pd.read_html(StringIO(text), header=None)
        return max(tables, key=lambda t: t.shape[0] * t.shape[1]).astype(str).replace("nan", pd.NA)
    try:
        delim = csv.Sniffer().sniff(text[:4000], delimiters=",;\t|").delimiter
    except Exception:
        delim = ","
    rows = list(csv.reader(StringIO(text), delimiter=delim))
    width = max((len(r) for r in rows), default=0)
    rows = [r + [None] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows).replace("", pd.NA)


def read_downloaded(path):
    raw = _load_any(path).dropna(how="all")
    if raw.empty:
        return pd.DataFrame()
    counts = raw.notna().sum(axis=1)
    hdr = counts[counts >= counts.max() * 0.6].index[0]
    pos = raw.index.get_loc(hdr)
    df = raw.iloc[pos + 1:].copy()
    cols, seen = [], {}
    for c in raw.iloc[pos]:
        c = str(c).strip() if pd.notna(c) else "Column"
        seen[c] = seen.get(c, 0) + 1
        cols.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    df.columns = cols
    return df.dropna(how="all").reset_index(drop=True)


# ------------------------------------------------------------ portal robot
def _continue_btn(page):
    return page.get_by_role("button", name=re.compile(r"^\s*continue\s*$", re.I))


def _visible_text(page, rx):
    loc = page.get_by_text(rx)
    try:
        for i in range(min(loc.count(), 5)):
            if loc.nth(i).is_visible():
                return loc.nth(i).inner_text()[:150].replace("\n", " ")
    except Exception:
        pass
    return None


def login(page, pan, password):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    pwd = page.locator("#loginPasswordField")

    def type_pan():
        box = page.locator("#panAdhaarUserId")
        box.wait_for(timeout=TIMEOUT)
        box.fill("")
        box.press_sequentially(pan, delay=60)

    # ---- Step 1: PAN, then Continue. The portal often answers the first click(s) with
    #      "Request is not authenticated". Keep clicking Continue until the password
    #      box appears (2, 3, 4 ... times - however many it takes).
    popup_ok = page.locator("button:has-text('OK'), button:has-text('Ok'), button:has-text('Close')")
    type_pan()
    page.wait_for_timeout(1000)
    deadline, clicks, moved = time.time() + 120, 0, False
    while time.time() < deadline and not moved:
        clicks += 1
        # dismiss any error pop-up that could block the button
        try:
            if popup_ok.count() and popup_ok.first.is_visible():
                popup_ok.first.click(timeout=1500)
                page.wait_for_timeout(500)
        except Exception:
            pass
        # make sure the PAN is still in the box
        try:
            box = page.locator("#panAdhaarUserId")
            if box.count() and box.is_visible() and not (box.input_value() or "").strip():
                type_pan()
                page.wait_for_timeout(800)
        except Exception:
            pass
        if clicks % 12 == 0:                   # very stubborn -> reload and restart
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            type_pan()
            page.wait_for_timeout(1500)
        try:
            _continue_btn(page).first.click(timeout=5000)
        except Exception:
            page.keyboard.press("Enter")
        # watch for the result of this click (up to ~8s)
        for _ in range(32):
            if pwd.is_visible():
                moved = True
                break
            err = _visible_text(page, NOT_AUTH)
            if err:
                break                          # error shown -> click Continue again
            bad = _visible_text(page, PAN_ERR)
            if bad:
                raise LoginError("INVALID_PAN", bad)
            page.wait_for_timeout(250)
        if not moved:
            page.wait_for_timeout(800)
    if not moved:
        raise LoginError("FAILED", f"Request is not authenticated (tried {clicks} clicks)")
    pwd.wait_for(state="visible", timeout=10000)

    # ---- Step 2: password + tick-box, then Continue. Same story as step 1: the portal
    #      may answer with "Request is not authenticated" - keep clicking Continue
    #      (2, 3, 4 ... times) until it moves forward.
    def fill_password():
        if not (pwd.input_value() or "").strip():
            pwd.fill("")
            pwd.press_sequentially(password, delay=40)
        cb = page.locator("input[type=checkbox]").first
        if cb.count() and not cb.is_checked():
            cb.check(force=True)

    login_here = page.locator("button:has-text('Login Here'), a:has-text('Login Here')")
    dashboard = page.get_by_text(re.compile("pending actions", re.I)).first
    pwd.fill("")
    pwd.press_sequentially(password, delay=40)
    fill_password()
    page.wait_for_timeout(800)

    deadline, clicks = time.time() + 150, 0
    while time.time() < deadline:
        if dashboard.is_visible():
            return
        if login_here.count() and login_here.first.is_visible():
            login_here.first.click()          # dual login -> continue here
            dashboard.wait_for(state="visible", timeout=40000)
            return
        clicks += 1
        try:
            if popup_ok.count() and popup_ok.first.is_visible():
                popup_ok.first.click(timeout=1500)
                page.wait_for_timeout(500)
        except Exception:
            pass
        try:
            fill_password()
        except Exception:
            pass
        try:
            _continue_btn(page).last.click(timeout=5000)
        except Exception:
            page.keyboard.press("Enter")
        for _ in range(32):                    # watch this click's result (~8 s)
            if dashboard.is_visible() or (login_here.count() and login_here.first.is_visible()):
                break
            msg = _visible_text(page, LOCK_ERR)
            if msg:
                raise LoginError("LOCKED", msg)
            if _visible_text(page, NOT_AUTH):
                break                          # click Continue again
            msg = _visible_text(page, PWD_ERR)
            if msg:
                raise LoginError("WRONG_PASSWORD", msg)
            page.wait_for_timeout(250)
        else:
            page.wait_for_timeout(800)
    raise LoginError("FAILED", f"Request is not authenticated (password step, tried {clicks} clicks)")


def open_eproceedings(page):
    page.get_by_text(re.compile("pending actions", re.I)).first.click()
    page.get_by_text(re.compile(r"^\s*e-?proceedings\s*$", re.I)).first.click()
    page.wait_for_load_state("networkidle")


def download_tab_excel(page, tab_text, save_to):
    tab = page.get_by_role("tab", name=re.compile(tab_text, re.I))
    if tab.count() == 0:
        tab = page.get_by_text(re.compile(tab_text, re.I))
    tab.first.click()
    page.wait_for_timeout(2500)
    btn = page.get_by_role("button", name=re.compile("excel", re.I))
    if btn.count() == 0:
        btn = page.get_by_text(re.compile("excel", re.I))
    with page.expect_download(timeout=TIMEOUT) as dl:
        btn.first.click()
    ext = os.path.splitext(dl.value.suggested_filename or "")[1] or ".xlsx"
    final = os.path.splitext(save_to)[0] + ext
    dl.value.save_as(final)
    return final


def logout(page):
    try:
        page.goto("https://eportal.incometax.gov.in/iec/foservices/#/dashboard")
        page.locator("text=/log\\s*out/i").first.click(timeout=5000)
    except Exception:
        pass


def run_all(clients, out_q, headless, stop_evt):
    base = os.path.join(os.path.expanduser("~"), "EProceedingsDownloads")
    os.makedirs(base, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="eproc_", dir=base)
    frames, had_error = [], False
    with sync_playwright() as pw:
        opts = dict(headless=headless,
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                    ignore_default_args=["--enable-automation"])
        try:
            browser = pw.chromium.launch(channel="chrome", **opts)
        except Exception:
            browser = pw.chromium.launch(**opts)
        total = len(clients)
        for i, c in enumerate(clients, 1):
            if stop_evt.is_set():
                break
            name, pan = c["name"], c["pan"]
            out_q.put(("progress", i - 1, total))
            out_q.put(("status", f"[{i}/{total}] {name} ({pan}) - logging in..."))
            res = {"name": name, "pan": pan, "status": "OK", "reason": ""}
            ctx = browser.new_context(accept_downloads=True, no_viewport=True,
                                      locale="en-IN", timezone_id="Asia/Kolkata")
            ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
            page = ctx.new_page()
            page.set_default_timeout(TIMEOUT)
            try:
                login(page, pan, c["password"])
                open_eproceedings(page)
                for label in TABS:
                    out_q.put(("status", f"[{i}/{total}] {name} - {label}: downloading..."))
                    f = os.path.join(tmp, f"{pan}_{label.replace(' ', '')}.csv")
                    try:
                        f = download_tab_excel(page, label, f)
                        df = read_downloaded(f)
                        if not df.empty:
                            existing = {str(x).strip().lower(): x for x in df.columns}
                            for key in ("client name", "source tab"):
                                if key in existing:
                                    df = df.rename(columns={existing[key]: f"{existing[key]} (portal)"})
                            df.insert(0, "Source Tab", label)
                            if "pan" not in existing:
                                df.insert(0, "PAN", pan)
                            df.insert(0, "Client Name", name)
                            frames.append(df)
                        else:
                            out_q.put(("log", f"{name} / {label}: no records"))
                    except Exception as e:
                        had_error = True
                        out_q.put(("log", f"{name} / {label}: failed ({str(e)[:150]})"))
                logout(page)
            except LoginError as e:
                had_error = True
                res.update(status=e.kind, reason=e.text)
                out_q.put(("log", f"{name} ({pan}): {e.kind} - {e.text}"))
            except Exception as e:
                had_error = True
                res.update(status="FAILED", reason=str(e)[:150])
                out_q.put(("log", f"{name} ({pan}): FAILED - {str(e)[:150]}"))
            finally:
                ctx.close()
            out_q.put(("result", res))
        out_q.put(("progress", total, total))
        browser.close()
    merged = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    if frames and not had_error:
        shutil.rmtree(tmp, ignore_errors=True)
    out_q.put(("done", merged))


# ---------------------------------------------------------------------- UI
ISSUE_TEXT = {"WRONG_PASSWORD": "Wrong password", "LOCKED": "Account locked",
              "INVALID_PAN": "Invalid PAN", "FAILED": "Login failed"}


def style_tree():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview", background=ROW1, fieldbackground=ROW1, foreground="#e6e9f0",
                rowheight=30, borderwidth=0, font=("Segoe UI", 10))
    s.configure("Treeview.Heading", background="#2b3150", foreground="white",
                relief="flat", font=("Segoe UI", 10, "bold"), padding=6)
    s.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
    s.map("Treeview.Heading", background=[("active", "#38406a")])
    s.configure("Vertical.TScrollbar", background="#2b3150", troughcolor=ROW1, borderwidth=0)
    s.configure("Horizontal.TScrollbar", background="#2b3150", troughcolor=ROW1, borderwidth=0)


def make_table(parent, columns):
    wrap = ctk.CTkFrame(parent, fg_color=ROW1, corner_radius=12)
    tree = ttk.Treeview(wrap, columns=columns, show="headings")
    ys = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    xs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
    ys.grid(row=0, column=1, sticky="ns", pady=(6, 0))
    xs.grid(row=1, column=0, sticky="ew", padx=(6, 0))
    wrap.rowconfigure(0, weight=1)
    wrap.columnconfigure(0, weight=1)
    tree.tag_configure("odd", background=ROW2)
    return wrap, tree


class IssuesWindow(ctk.CTkToplevel):
    def __init__(self, master, issues):
        super().__init__(master)
        self.title("Wrong Password / Login Issues")
        self.geometry("820x520")
        self.configure(fg_color=BG)
        self.issues = issues
        self.after(150, self.lift)
        ctk.CTkLabel(self, text="Clients that could not log in", font=("Segoe UI", 22, "bold"),
                     text_color="white").pack(anchor="w", padx=22, pady=(18, 0))
        ctk.CTkLabel(self, text=f"{len(issues)} client(s) need attention - fix the password in your "
                                "Excel file and run them again.", text_color="#9aa3bd"
                     ).pack(anchor="w", padx=22, pady=(0, 10))
        wrap, tree = make_table(self, ("#", "Client Name", "PAN", "Issue", "Portal message"))
        wrap.pack(fill="both", expand=True, padx=20, pady=6)
        for col, w in (("#", 50), ("Client Name", 220), ("PAN", 120), ("Issue", 140), ("Portal message", 380)):
            tree.heading(col, text=col)
            tree.column(col, width=w, minwidth=40)
        for n, r in enumerate(issues, 1):
            tree.insert("", "end", tags=("odd",) if n % 2 == 0 else (),
                        values=(n, r["name"], r["pan"], ISSUE_TEXT.get(r["status"], r["status"]), r["reason"]))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=14)
        ctk.CTkButton(bar, text="Export list to Excel", fg_color=ACCENT, command=self.export
                      ).pack(side="left")
        ctk.CTkButton(bar, text="Copy PANs", fg_color="#2b3150", command=self.copy_pans
                      ).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Close", fg_color="#2b3150", command=self.destroy).pack(side="right")

    def export(self):
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                         initialfile="wrong_password_list.xlsx")
        if p:
            pd.DataFrame([{"Client Name": r["name"], "PAN": r["pan"],
                           "Issue": ISSUE_TEXT.get(r["status"], r["status"]),
                           "Portal message": r["reason"]} for r in self.issues]).to_excel(p, index=False)
            messagebox.showinfo("Saved", p, parent=self)

    def copy_pans(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(r["pan"] for r in self.issues))
        messagebox.showinfo("Copied", "PANs copied to clipboard.", parent=self)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("E-Proceedings Consolidator")
        self.geometry("1380x820")
        self.minsize(1100, 680)
        self.configure(fg_color=BG)
        style_tree()
        self.q = queue.Queue()
        self.stop_evt = threading.Event()
        self.merged = pd.DataFrame()
        self.issues, self.total, self.done_n = [], 0, 0
        self.path = tk.StringVar()
        self.headless = tk.BooleanVar(value=False)
        self.win = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.build_sidebar()
        self.build_main()
        self.after(200, self.poll)

    # ---- layout
    def build_sidebar(self):
        sb = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color=CARD)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text="⚖  E-Proceedings", font=("Segoe UI", 22, "bold"),
                     text_color="white").pack(anchor="w", padx=22, pady=(26, 0))
        ctk.CTkLabel(sb, text="Income Tax portal consolidator", text_color="#8b94b3"
                     ).pack(anchor="w", padx=22, pady=(0, 22))

        ctk.CTkLabel(sb, text="1  CLIENT FILE", text_color=ACCENT, font=("Segoe UI", 11, "bold")
                     ).pack(anchor="w", padx=22)
        ctk.CTkButton(sb, text="📂  Choose Excel (name, pan, password)", height=40, fg_color="#2b3150",
                      hover_color="#38406a", command=self.browse).pack(fill="x", padx=22, pady=(6, 2))
        self.file_lbl = ctk.CTkLabel(sb, text="No file selected", text_color="#8b94b3",
                                     wraplength=220, justify="left")
        self.file_lbl.pack(anchor="w", padx=22, pady=(0, 14))

        ctk.CTkLabel(sb, text="2  RUN", text_color=ACCENT, font=("Segoe UI", 11, "bold")
                     ).pack(anchor="w", padx=22)
        self.start_btn = ctk.CTkButton(sb, text="▶  Start", height=46, fg_color=ACCENT, hover_color="#4766e0",
                                       font=("Segoe UI", 15, "bold"), command=self.start)
        self.start_btn.pack(fill="x", padx=22, pady=(6, 6))
        ctk.CTkButton(sb, text="■  Stop", height=36, fg_color="#3a2630", hover_color="#57323f",
                      command=self.stop_evt.set).pack(fill="x", padx=22)
        ctk.CTkSwitch(sb, text="Hide browser window", variable=self.headless,
                      progress_color=ACCENT).pack(anchor="w", padx=22, pady=14)

        ctk.CTkLabel(sb, text="3  RESULTS", text_color=ACCENT, font=("Segoe UI", 11, "bold")
                     ).pack(anchor="w", padx=22)
        self.issue_btn = ctk.CTkButton(sb, text="🔑  Wrong passwords (0)", height=38, fg_color="#3a2630",
                                       hover_color="#57323f", command=self.show_issues)
        self.issue_btn.pack(fill="x", padx=22, pady=(6, 6))
        ctk.CTkButton(sb, text="💾  Export merged Excel", height=38, fg_color=GREEN, text_color="#08210f",
                      hover_color="#27b862", command=self.export).pack(fill="x", padx=22)

    def build_main(self):
        m = ctk.CTkFrame(self, fg_color="transparent")
        m.grid(row=0, column=1, sticky="nsew", padx=22, pady=18)
        m.columnconfigure(0, weight=1)
        m.rowconfigure(3, weight=1)

        cards = ctk.CTkFrame(m, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew")
        self.stat = {}
        for i, (key, title, color) in enumerate((("clients", "CLIENTS", "white"),
                                                 ("done", "PROCESSED", ACCENT),
                                                 ("rows", "ROWS FETCHED", GREEN),
                                                 ("bad", "LOGIN ISSUES", RED))):
            cards.columnconfigure(i, weight=1)
            f = ctk.CTkFrame(cards, fg_color=CARD, corner_radius=14)
            f.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            ctk.CTkLabel(f, text=title, text_color="#8b94b3", font=("Segoe UI", 11, "bold")
                         ).pack(anchor="w", padx=16, pady=(12, 0))
            lbl = ctk.CTkLabel(f, text="0", text_color=color, font=("Segoe UI", 30, "bold"))
            lbl.pack(anchor="w", padx=16, pady=(0, 10))
            self.stat[key] = lbl

        self.progress = ctk.CTkProgressBar(m, height=10, progress_color=ACCENT, fg_color=CARD)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(16, 4))
        self.status = ctk.CTkLabel(m, text="Ready - choose your client file and press Start",
                                   text_color="#9aa3bd", anchor="w")
        self.status.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        tabs = ctk.CTkTabview(m, fg_color=CARD, segmented_button_selected_color=ACCENT, corner_radius=14)
        tabs.grid(row=3, column=0, sticky="nsew")
        t1, t2 = tabs.add("Merged data"), tabs.add("Activity log")

        bar = ctk.CTkFrame(t1, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        self.search = ctk.CTkEntry(bar, placeholder_text="🔍  Search any text...", width=320, height=34)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.seg = ctk.CTkSegmentedButton(bar, values=["All", "For Your Action", "For Your Information"],
                                          selected_color=ACCENT, command=lambda v: self.refresh())
        self.seg.set("All")
        self.seg.pack(side="left", padx=12)
        self.count_lbl = ctk.CTkLabel(bar, text="", text_color="#9aa3bd")
        self.count_lbl.pack(side="right")
        wrap, self.tree = make_table(t1, ())
        wrap.pack(fill="both", expand=True)

        self.log = ctk.CTkTextbox(t2, fg_color=ROW1, text_color="#cfd5e8", font=("Consolas", 12))
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    # ---- actions
    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if p:
            self.path.set(p)
            self.file_lbl.configure(text=os.path.basename(p), text_color="white")

    def write_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self):
        try:
            clients = read_clients(self.path.get())
        except Exception as e:
            messagebox.showerror("Input error", str(e))
            return
        if not clients:
            messagebox.showwarning("Empty", "No clients found in the file.")
            return
        self.stop_evt.clear()
        self.issues, self.done_n, self.total = [], 0, len(clients)
        self.merged = pd.DataFrame()
        self.refresh()
        self.stat["clients"].configure(text=str(self.total))
        self.stat["done"].configure(text="0")
        self.stat["rows"].configure(text="0")
        self.stat["bad"].configure(text="0")
        self.issue_btn.configure(text="🔑  Wrong passwords (0)")
        self.progress.set(0)
        self.start_btn.configure(state="disabled", text="⏳  Running...")
        threading.Thread(target=run_all, daemon=True,
                         args=(clients, self.q, self.headless.get(), self.stop_evt)).start()

    def poll(self):
        try:
            while True:
                kind, *val = self.q.get_nowait()
                if kind == "status":
                    self.status.configure(text=val[0])
                    self.write_log(val[0])
                elif kind == "log":
                    self.write_log(val[0])
                elif kind == "progress":
                    self.progress.set(val[0] / max(val[1], 1))
                elif kind == "result":
                    r = val[0]
                    self.done_n += 1
                    self.stat["done"].configure(text=str(self.done_n))
                    if r["status"] != "OK":
                        self.issues.append(r)
                        self.stat["bad"].configure(text=str(len(self.issues)))
                        self.issue_btn.configure(text=f"🔑  Wrong passwords ({len(self.issues)})")
                elif kind == "done":
                    self.merged = val[0]
                    self.stat["rows"].configure(text=str(len(self.merged)))
                    self.refresh()
                    self.start_btn.configure(state="normal", text="▶  Start")
                    self.status.configure(text=f"Finished - {len(self.merged)} rows, "
                                               f"{len(self.issues)} login issue(s)")
                    if self.issues:
                        self.show_issues()
        except queue.Empty:
            pass
        self.after(200, self.poll)

    def refresh(self):
        df = self.merged
        self.tree.delete(*self.tree.get_children())
        if df.empty:
            self.tree["columns"] = ()
            self.count_lbl.configure(text="")
            return
        tab = self.seg.get()
        if tab != "All":
            df = df[df["Source Tab"] == tab]
        q = self.search.get().strip()
        if q:
            mask = df.astype(str).apply(lambda c: c.str.contains(q, case=False, na=False, regex=False)).any(axis=1)
            df = df[mask]
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=230 if c == "Client Name" else 140, minwidth=80)
        for n, row in enumerate(df.fillna("").itertuples(index=False)):
            self.tree.insert("", "end", values=list(row), tags=("odd",) if n % 2 else ())
        self.count_lbl.configure(text=f"{len(df)} of {len(self.merged)} rows")

    def show_issues(self):
        if not self.issues:
            messagebox.showinfo("All good", "No wrong-password / login issues so far.")
            return
        if self.win is not None and self.win.winfo_exists():
            self.win.destroy()
        self.win = IssuesWindow(self, list(self.issues))

    def export(self):
        if self.merged.empty:
            messagebox.showinfo("Nothing to export", "Run the tool first.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if p:
            self.merged.to_excel(p, index=False)
            messagebox.showinfo("Saved", p)


if __name__ == "__main__":
    App().mainloop()
