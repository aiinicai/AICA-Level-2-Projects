"""Tkinter GUI for fifo_fixed_income.run_fifo."""
import json
import numbers
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

import pandas as pd

import fifo_report as fr
from fifo_fixed_income import run_fifo

def _app_dir():
    """Folder of the .exe when packaged, otherwise of this script (never PyInstaller's temp dir)."""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


SETTINGS_FILE = _app_dir() / "fifo_settings.json"


def _load_pos_dir():
    try:
        d = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("positions_dir")
        if d:
            return Path(d)
    except Exception:
        pass
    return _app_dir() / "positions"


POS_DIR = _load_pos_dir()   # month-end snapshots live here (changeable with "Positions folder")
REQUIRED = ["trade_date", "security_id", "side", "quantity", "price", "coupon_rate"]


FRACTIONS = {"⅛": .125, "¼": .25, "⅜": .375, "½": .5, "⅝": .625, "¾": .75, "⅞": .875}
COUPON_RE = re.compile(r"^\S+\s+(\d+(?:\.\d+)?)(?:\s*(\d+)\s*/\s*(\d+)|\s*([⅛¼⅜½⅝¾⅞]))?(?=\s|$)")


def read_raw(path):
    """Read a CSV / Excel file without a header row. If Windows or OneDrive refuses access
    (file open in Excel, sync in progress), read a temporary copy made with the Windows copy API."""
    def read(p):
        if str(p).lower().endswith(".csv"):
            return pd.read_csv(p, sep=None, engine="python", encoding="utf-8-sig", header=None)
        return pd.read_excel(p, header=None)

    try:
        return read(path)
    except PermissionError:
        import ctypes
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = str(Path(d) / Path(path).name)
            ok = sys.platform == "win32" and ctypes.windll.kernel32.CopyFileW(str(path), tmp, False)
            if not ok:
                raise PermissionError(
                    f"Cannot open '{Path(path).name}'. Close it in Excel (and let OneDrive finish "
                    "syncing), or save a copy to your desktop and load that.") from None
            return read(tmp)


def parse_coupon(name):
    """'DAMACR 6 1/8 08/05/29' -> 6.125, 'ALDAR 5 ⅞ ...' -> 5.875, 'KFHKK 4.563 ...' -> 4.563."""
    m = COUPON_RE.match(str(name).strip())
    if not m:
        return float("nan")
    c = float(m.group(1))
    if m.group(2):
        c += int(m.group(2)) / int(m.group(3))
    elif m.group(4):
        c += FRACTIONS[m.group(4)]
    return c


PRICE_ID = ["isin", "security_id", "security id", "cusip", "security", "instrument", "bond", "symbol"]
PRICE_PX = ["closing price", "close price", "close", "closing", "market price", "price (dec)",
            "price", "px", "mid price", "mid", "clean price"]
PRICE_DT = ["price date", "as of", "as of date", "date", "valuation date"]
COUPON_DT = ["coupon date", "coupon payment date", "coupon received date", "payment date",
             "pay date", "paydate", "date received", "received date", "date", "value date",
             "pmt date"]
# opening positions file: ISIN, name, quantity, market price, market value (+ optional columns)
OPEN_ID = ["isin", "security_id", "security id", "cusip"]
OPEN_NAME = ["name", "bond name", "security name", "security description", "description",
             "security", "bond", "instrument"]
OPEN_QTY = ["quantity", "qty", "face value", "face", "nominal", "amount", "units", "position",
            "closing quantity", "closing face"]
OPEN_PX = ["market price", "mkt price", "closing price", "close price", "price", "px",
           "price (dec)", "month-end price"]
OPEN_MV = ["market value", "mkt value", "mv", "market value (usd)", "closing market value", "value"]
OPEN_COST = ["cost price", "avg cost", "average cost", "purchase price", "cost"]
OPEN_CPN = ["coupon", "coupon rate", "coupon %"]
OPEN_DT = ["date", "as of", "as of date", "as at", "position date", "valuation date"]


BUY_WORDS = {"B", "BUY", "BOUGHT", "PURCHASE", "PURCHASED"}
SELL_WORDS = {"S", "SELL", "SOLD", "SALE"}


def normalize_side(series):
    """B, [B], buy -> BUY; S, [S], sell -> SELL. Brackets, spaces and case are ignored.
    Any other value raises an error, so a trade is never silently read as the wrong side."""
    def one(x):
        s = re.sub(r"[^A-Z]", "", str(x).upper())
        if s in BUY_WORDS:
            return "BUY"
        if s in SELL_WORDS:
            return "SELL"
        return None
    out = series.map(one)
    bad = sorted(set(series[out.isna()].astype(str)))
    if bad:
        raise ValueError("Unrecognised side value(s): " + ", ".join(repr(b) for b in bad)
                         + ".\nUse B / [B] / BUY for purchases and S / [S] / SELL for sales.")
    return out


def parse_any_date(v):
    """Excel dates pass through; text dates are read as MM/DD/YY(YY) or ISO / 14-Jan-2026."""
    if v is None or (isinstance(v, float) and v != v):
        return pd.NaT
    if isinstance(v, str):
        s = v.strip()
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d %b %Y"):
            try:
                return pd.Timestamp(pd.to_datetime(s, format=fmt))
            except (ValueError, TypeError):
                continue
        return pd.NaT
    return pd.Timestamp(v) if not pd.isna(v) else pd.NaT


def norm_entity(x):
    """'QMM LTD', 'QMM LTD\' -> 'LTD'; 'Q MARKET MAKER LLC' -> 'LLC'; anything else -> cleaned text."""
    s = re.sub(r"[^A-Z0-9 ]", "", str(x).upper()).strip()
    if not s or s == "NAN":
        return "UNKNOWN"
    if "LTD" in s.split():
        return "LTD"
    if "LLC" in s.split():
        return "LLC"
    return re.sub(r"\s+", "_", s)


def parse_settle(df, trade_col, settle_col):
    """Settlement dates: text is MM/DD/YY; real datetimes may have day/month swapped by Excel.
    Keep a date that falls 0-30 days after the trade date, else try the swapped one."""
    def fix(row):
        t = row[trade_col]
        v = row[settle_col]
        if isinstance(v, str):
            v = pd.to_datetime(v, format="%m/%d/%y", errors="coerce")
        if pd.isna(v):
            return pd.NaT
        v = pd.Timestamp(v)
        ok = lambda x: pd.notna(t) and 0 <= (x - t).days <= 30
        if ok(v) or v.day > 12:
            return v
        swapped = pd.Timestamp(v.year, v.day, v.month)
        return swapped if ok(swapped) else v
    return df.apply(fix, axis=1)


def with_detected_header(raw, known=None, min_hits=3):
    """Find the header row (skipping blank/title rows) and return a DataFrame."""
    known = known or set(REQUIRED) | {a for v in ALIASES.values() for a in v}
    for i in range(min(30, len(raw))):
        cells = [str(x).strip().lower() for x in raw.iloc[i] if pd.notna(x)]
        if sum(c in known for c in cells) >= min_hits:
            df = raw.iloc[i + 1:].copy()
            df.columns = [str(c).strip() if pd.notna(c) else f"unnamed_{j}"
                          for j, c in enumerate(raw.iloc[i])]
            return df.dropna(how="all").reset_index(drop=True)
    df = raw.copy()
    df.columns = [str(c) for c in df.iloc[0]]
    return df.iloc[1:].reset_index(drop=True)


def fix_swapped_dates(df, col, settle_col):
    """Text dates are MM/DD/YY; Excel auto-converted some to datetimes with day/month swapped.
    Swap them back when real datetimes fall after the settlement date (or settlement is absent)."""
    def fix(row):
        v = row[col]
        if isinstance(v, str):
            return pd.to_datetime(v, format="%m/%d/%y", errors="coerce")
        if pd.isna(v):
            return pd.NaT
        v = pd.Timestamp(v)
        if v.day > 12:
            return v
        swapped = pd.Timestamp(v.year, v.day, v.month)
        s = pd.to_datetime(row[settle_col], errors="coerce") if settle_col else pd.NaT
        return swapped if pd.isna(s) or v > s else v
    df = df.copy()
    df[col] = df.apply(fix, axis=1)
    return df


ALIASES = {
    "trade_date": ["trade dt", "trade date", "date", "tradedate", "deal date"],
    "security_id": ["isin", "cusip", "security id", "instrument", "bond", "symbol", "security"],
    "side": ["side", "buy/sell", "type", "transaction type", "trade type", "direction", "b/s"],
    "quantity": ["quantity", "qty", "qty (m)", "qty in m", "face value", "face", "nominal", "amount", "units"],
    "price": ["price (dec)", "price", "clean price", "trade price", "rate", "px"],
    "coupon_rate": ["coupon", "coupon rate", "coupon %", "rate %"],
}


P = dict(bg="#F4F6F9", card="#FFFFFF", border="#E2E8F0", navy="#14213D", accent="#2563EB",
         accent_dark="#1D4ED8", text="#1F2937", muted="#6B7280", pos="#047857", neg="#B91C1C",
         zebra="#F6F8FB", head="#E8EDF4", select="#DBEAFE")
FONT = "Segoe UI"

HEADINGS = {
    "security_id": "ISIN", "direction": "Direction", "quantity": "Face value",
    "closing_quantity": "Closing face", "open_date": "Trade date", "settle_date": "Settlement",
    "open_settle": "Open settlement", "close_date": "Close date", "close_settle": "Close settlement",
    "open_price": "Open price", "close_price": "Close price", "cost_price": "Cost price",
    "market_price": "Market price", "market_value": "Market value",
    "coupon_rate": "Coupon %", "days": "Days",
    "realized_pl": "Realized P&L", "unrealized_pl": "Unrealized P&L",
    "unrealized_pl_period": "Unrealized P&L (period)",
    "interest_income": "Interest since purchase", "interest_period": "Interest (period)",
    "interest_since_coupon": "Accrued since last coupon",
    "interest_since_coupon_sold": "Since coupon - sold",
    "interest_since_coupon_closing": "Accrued since coupon - closing",
    "realized_pl_sold": "Realized P&L", "interest_income_sold": "Interest - sold",
    "interest_period_sold": "Interest (period) - sold",
    "interest_income_closing": "Interest - closing",
    "interest_period_closing": "Interest (period) - closing",
}
SUM_COLS = {"quantity", "closing_quantity", "market_value", "realized_pl", "unrealized_pl", "unrealized_pl_period", "interest_income",
            "interest_period", "interest_since_coupon", "interest_since_coupon_sold",
            "interest_since_coupon_closing", "realized_pl_sold", "interest_income_sold",
            "interest_period_sold", "interest_income_closing", "interest_period_closing"}
TEXT_COLS = {"security_id", "direction"}
DATE_COLS = {"open_date", "settle_date", "close_date", "open_settle", "close_settle"}
PL_COLS = ("unrealized_pl", "realized_pl", "realized_pl_sold")
KPIS = [("unreal", "Unrealized P&L", "USD, closing positions"),
        ("real", "Realized P&L", "USD, positions sold"),
        ("int_close", "Interest since purchase", "USD, positions held"),
        ("acc", "Accrued since last coupon", "USD, positions held"),
        ("int_sold", "Interest - sold", "USD, positions sold"),
        ("face", "Closing face value", ""),
        ("mv", "Closing market value", "USD, at closing prices")]


class App(tk.Tk):
    def __init__(self):
        try:  # crisp text on high-DPI Windows screens
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        super().__init__()
        self.title("FIFO Fixed Income P&L")
        w = min(1280, self.winfo_screenwidth() - 40)
        h = min(780, self.winfo_screenheight() - 80)
        self.geometry(f"{w}x{h}")
        self.minsize(980, 560)
        self.configure(bg=P["bg"])
        self.all_trades = None       # every entity in the file
        self.trades = None           # trades of the selected entity
        self.entity = tk.StringVar()
        self.opening = None          # previous month-end lots (DataFrame) or None
        self.opening_date = None     # date of that snapshot
        self.price_vars = {}
        self.results = {}
        self._style()
        self._build()

    # ---------- look and feel ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        k = self.winfo_fpixels("1i") / 96
        s.configure(".", font=(FONT, 10), background=P["bg"], foreground=P["text"])
        s.configure("TFrame", background=P["bg"])
        s.configure("Card.TFrame", background=P["card"], bordercolor=P["border"],
                    relief="solid", borderwidth=1)
        s.configure("Plain.TFrame", background=P["card"], borderwidth=0)
        s.configure("TLabel", background=P["bg"])
        s.configure("Card.TLabel", background=P["card"])
        s.configure("Muted.TLabel", background=P["card"], foreground=P["muted"], font=(FONT, 9))
        s.configure("CardTitle.TLabel", background=P["card"], font=(FONT, 11, "bold"))
        s.configure("TButton", padding=(12, 6), background=P["card"], bordercolor=P["border"],
                    focuscolor=P["card"])
        s.map("TButton", background=[("active", "#EEF2F7")])
        s.configure("Primary.TButton", background=P["accent"], foreground="#FFFFFF",
                    bordercolor=P["accent"], font=(FONT, 10, "bold"), padding=(22, 6))
        s.map("Primary.TButton", background=[("active", P["accent_dark"])],
              foreground=[("active", "#FFFFFF")])
        s.configure("TEntry", padding=4, fieldbackground="#FFFFFF", bordercolor=P["border"])
        s.configure("TCombobox", padding=4, fieldbackground="#FFFFFF", bordercolor=P["border"],
                    arrowsize=14)
        s.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")],
              background=[("readonly", "#FFFFFF")], foreground=[("readonly", P["text"])])
        s.configure("TCheckbutton", background=P["card"])
        s.configure("TNotebook", background=P["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", padding=(18, 8), font=(FONT, 10), background=P["head"])
        s.map("TNotebook.Tab", background=[("selected", P["card"])],
              foreground=[("selected", P["accent"])])
        s.configure("Treeview", background=P["card"], fieldbackground=P["card"], borderwidth=0,
                    rowheight=int(28 * k), font=(FONT, 10))
        s.configure("Treeview.Heading", background=P["head"], font=(FONT, 10, "bold"),
                    padding=(6, 7), relief="flat")
        s.map("Treeview", background=[("selected", P["select"])],
              foreground=[("selected", P["text"])])
        s.map("Treeview.Heading", background=[("active", "#DCE3EE")])
        s.configure("TPanedwindow", background=P["bg"])

    def _build(self):
        # --- header band ---
        head = tk.Frame(self, bg=P["navy"])
        head.pack(fill="x")
        tk.Label(head, text="FIFO Fixed Income P&L", bg=P["navy"], fg="#FFFFFF",
                 font=(FONT, 15, "bold")).pack(side="left", padx=(20, 14), pady=8)
        self.file_lbl = tk.Label(head, text="No file loaded", bg=P["navy"], fg="#B8C4DA",
                                 font=(FONT, 10))
        self.file_lbl.pack(side="left")

        # --- status bar (packed early so it keeps its place at the bottom) ---
        sb = tk.Frame(self, bg=P["head"])
        sb.pack(fill="x", side="bottom")
        self.run_lbl = tk.Label(sb, text="Ready. Load a trades file to begin.", bg=P["head"],
                                fg=P["muted"], font=(FONT, 9), anchor="w")
        self.run_lbl.pack(fill="x", padx=16, pady=5)

        # --- actions ---
        bar = ttk.Frame(self, padding=(16, 12, 16, 4))
        bar.pack(fill="x")
        ttk.Button(bar, text="Load trades", command=self.load).pack(side="left")
        ttk.Button(bar, text="Load closing prices",
                   command=self.load_prices).pack(side="left", padx=8)
        ttk.Button(bar, text="Period report", command=self.open_report).pack(side="left")
        ttk.Button(bar, text="Export to Excel", command=self.export).pack(side="right")
        ttk.Button(bar, text="Run", style="Primary.TButton", command=self.run
                   ).pack(side="right", padx=10)

        # --- settings card ---
        card = ttk.Frame(self, style="Card.TFrame", padding=(14, 10))
        card.pack(fill="x", padx=16, pady=6)
        r1 = ttk.Frame(card, style="Plain.TFrame")
        r1.pack(fill="x")
        ttk.Label(r1, text="Valuation date", style="Card.TLabel").pack(side="left")
        self.val_date = tk.StringVar(value=pd.Timestamp.today().strftime("%Y-%m-%d"))
        ttk.Entry(r1, textvariable=self.val_date, width=12).pack(side="left", padx=(6, 18))
        ttk.Label(r1, text="Interest on", style="Card.TLabel").pack(side="left")
        self.base_var = tk.StringVar(value="Face value")
        ttk.Combobox(r1, textvariable=self.base_var, state="readonly", width=13,
                     values=["Face value", "Market value"]).pack(side="left", padx=(6, 18))
        ttk.Label(r1, text="Day count", style="Card.TLabel").pack(side="left")
        self.dc_var = tk.StringVar(value="30E/360")
        ttk.Combobox(r1, textvariable=self.dc_var, state="readonly", width=11,
                     values=["30E/360", "30/360 US", "Actual"]).pack(side="left", padx=(6, 18))
        ttk.Label(r1, text="Entity", style="Card.TLabel").pack(side="left")
        self.ent_box = ttk.Combobox(r1, textvariable=self.entity, width=8)
        self.ent_box.pack(side="left", padx=6)
        self.ent_box.bind("<<ComboboxSelected>>", lambda e: self.apply_entity())

        r2 = ttk.Frame(card, style="Plain.TFrame")
        r2.pack(fill="x", pady=(10, 0))
        self.open_lbl = ttk.Label(r2, text="Opening positions: none (start from zero)",
                                  style="Card.TLabel")
        self.open_lbl.pack(side="left")
        ttk.Button(r2, text="Upload opening positions file", style="Primary.TButton",
                   command=self.upload_opening).pack(side="left", padx=10)
        ttk.Button(r2, text="Use saved position",
                   command=self.choose_opening).pack(side="left")
        ttk.Button(r2, text="Start from zero",
                   command=lambda: (self.clear_opening(), self.build_price_panel())
                   ).pack(side="left")
        self.save_pos = tk.BooleanVar(value=True)
        ttk.Checkbutton(r2, text="Save positions and data after Run",
                        variable=self.save_pos).pack(side="right")
        r3 = ttk.Frame(card, style="Plain.TFrame")
        r3.pack(fill="x", pady=(8, 0))
        ttk.Button(r3, text="Positions folder", command=self.choose_pos_dir).pack(side="left")
        self.pos_lbl = ttk.Label(r3, text=f"Saved positions: {POS_DIR}", style="Muted.TLabel")
        self.pos_lbl.pack(side="left", padx=10)
        r4 = ttk.Frame(card, style="Plain.TFrame")
        r4.pack(fill="x", pady=(8, 0))
        ttk.Button(r4, text="Load coupons received", command=self.load_coupons).pack(side="left")
        ttk.Button(r4, text="Clear coupons", command=self.clear_coupons).pack(side="left", padx=8)
        self.coupon_lbl = ttk.Label(r4, text="", style="Muted.TLabel")
        self.coupon_lbl.pack(side="left", padx=6)
        self.read_coupons()

        # --- KPI cards ---
        kp = ttk.Frame(self)
        kp.pack(fill="x", padx=16, pady=(2, 6))
        self.kpi = {}
        for i, (key, title, sub) in enumerate(KPIS):
            c = tk.Frame(kp, bg=P["card"], highlightbackground=P["border"], highlightthickness=1)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            kp.columnconfigure(i, weight=1, uniform="kpi")
            tk.Label(c, text=title, bg=P["card"], fg=P["muted"], font=(FONT, 9)
                     ).pack(anchor="w", padx=14, pady=(6, 0))
            v = tk.Label(c, text="-", bg=P["card"], fg=P["text"], font=(FONT, 15, "bold"))
            v.pack(anchor="w", padx=14)
            s = tk.Label(c, text=sub, bg=P["card"], fg=P["muted"], font=(FONT, 8))
            s.pack(anchor="w", padx=14, pady=(0, 6))
            self.kpi[key] = (v, s, sub)

        # --- body: price panel + result tables ---
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        left = ttk.Frame(body, style="Card.TFrame", padding=10)
        ttk.Label(left, text="Closing prices", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(left, text="Per 100 face, for bonds still held",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        holder = ttk.Frame(left, style="Plain.TFrame")
        holder.pack(fill="both", expand=True)
        cv = tk.Canvas(holder, bg=P["card"], highlightthickness=0, width=250)
        sc = ttk.Scrollbar(holder, orient="vertical", command=cv.yview)
        self.price_frame = ttk.Frame(cv, style="Plain.TFrame")
        cv.create_window((0, 0), window=self.price_frame, anchor="nw")
        self.price_frame.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.configure(yscrollcommand=sc.set)
        cv.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")
        cv.bind("<Enter>", lambda e: cv.bind_all(
            "<MouseWheel>", lambda ev: cv.yview_scroll(int(-ev.delta / 120), "units")))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        body.add(left, weight=1)

        self.nb = ttk.Notebook(body)
        self.trees = {}
        for key, title in [("summary", "Summary"), ("closing", "Closing positions"),
                           ("closed", "Closed matches")]:
            frame = ttk.Frame(self.nb, style="Plain.TFrame")
            tree = ttk.Treeview(frame, show="headings")
            sy = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
            sy.pack(side="right", fill="y")
            sx.pack(side="bottom", fill="x")
            tree.pack(fill="both", expand=True)
            tree.tag_configure("odd", background=P["zebra"])
            tree.tag_configure("neg", foreground=P["neg"])
            tree.tag_configure("total", background=P["head"], font=(FONT, 10, "bold"))
            self.nb.add(frame, text=title)
            self.trees[key] = tree
        body.add(self.nb, weight=5)
        k = self.winfo_fpixels("1i") / 96

        def place_sash():  # wait until the window has its real size, then fit the price boxes
            if body.winfo_width() < 200:
                self.after(100, place_sash)
            else:
                body.sashpos(0, int(250 * k))
        self.after(100, place_sash)
        self.update_kpis()

    def update_kpis(self):
        """Headline numbers above the tables; green for gains, red for losses."""
        closing, closed = self.results.get("closing"), self.results.get("closed")

        def total(df, col):
            if df is None or df.empty or col not in df:
                return None
            return float(df[col].sum())

        vals = {"unreal": total(closing, "unrealized_pl"), "real": total(closed, "realized_pl"),
                "int_close": total(closing, "interest_income"),
                "acc": total(closing, "interest_since_coupon"),
                "int_sold": total(closed, "interest_income"),
                "face": total(closing, "quantity"), "mv": total(closing, "market_value")}
        for key, (lbl, sub, default_sub) in self.kpi.items():
            v = vals[key]
            if not self.results:
                lbl.config(text="-", fg=P["text"])
                sub.config(text=default_sub)
            elif v is None:
                lbl.config(text="0" if key == "face" else "0.00", fg=P["muted"])
                sub.config(text=default_sub)
            else:
                text = f"{v:,.0f}" if key == "face" else f"{v:,.2f}"
                color = P["text"] if key in ("face", "mv") else (
                    P["pos"] if v > 0 else P["neg"] if v < 0 else P["text"])
                lbl.config(text=text, fg=color)
                sub_text = default_sub
                if key == "face" and closing is not None:
                    sub_text = f"{len(closing)} lots"
                elif key == "unreal" and total(closing, "unrealized_pl_period") is not None:
                    sub_text = f"This period: {total(closing, 'unrealized_pl_period'):,.2f}"
                sub.config(text=sub_text)


    def load(self):
        path = filedialog.askopenfilename(
            filetypes=[("Trades", "*.csv *.xlsx *.xls"), ("All files", "*.*")])
        if not path:
            return
        try:
            raw = read_raw(path)
            df = with_detected_header(raw)
            lower = {c.lower(): c for c in df.columns}
            if "coupon_rate" not in lower and not any(a in lower for a in ALIASES["coupon_rate"]):
                src = next((lower[c] for c in ("security", "description", "security_id")
                            if c in lower), None)
                if src:  # derive coupon from names like "DAMACR 6 1/8 08/05/29"
                    df["coupon_rate"] = df[src].map(parse_coupon)
                    lower["coupon_rate"] = "coupon_rate"
            df["_swap"] = False
            if "trade dt" in lower or "trade_date" in lower:
                df = fix_swapped_dates(df, lower.get("trade dt") or lower["trade_date"],
                                       lower.get("setdt"))
            if "status" in lower:
                df = df[df[lower["status"]].astype(str).str.lower().isin(["accepted", "nan"])]
            tcol = lower.get("trade dt") or lower.get("trade_date")
            scol = lower.get("setdt") or lower.get("settle_date") or lower.get("settlement date")
            df["settle_date"] = parse_settle(df, tcol, scol) if tcol and scol else pd.NaT
            mapping = {r: lower.get(r) for r in REQUIRED}
            for r in REQUIRED:  # guess from aliases
                if mapping[r] is None:
                    mapping[r] = next((lower[a] for a in ALIASES[r] if a in lower), None)
            if any(v is None for v in mapping.values()):
                mapping = self.ask_mapping(list(df.columns), mapping)
                if mapping is None:
                    return
            df = df.rename(columns={v: k for k, v in mapping.items()})[REQUIRED + ["settle_date"]]
            df = df.dropna(subset=["trade_date", "security_id", "side", "quantity", "price"])
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df["settle_date"] = pd.to_datetime(df["settle_date"]).fillna(df["trade_date"])
            for c in ("quantity", "price", "coupon_rate"):
                df[c] = pd.to_numeric(df[c])
            if df["coupon_rate"].isna().any():
                bad = df.loc[df["coupon_rate"].isna(), "security_id"].unique()
                raise ValueError(f"Could not determine coupon for: {', '.join(map(str, bad))}")
            df["side"] = normalize_side(df["side"])
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return
        self.all_trades = df
        self.file_name = Path(path).name
        # The whole file belongs to one book; the entity is only a label (from the file name)
        # that keeps each book's saved positions separate. The Customer column is ignored.
        words = re.sub(r"[^A-Z0-9]+", " ", self.file_name.upper()).split()
        self.ent_box["values"] = ["LTD", "LLC"]
        self.entity.set(next((w for w in ("LTD", "LLC") if w in words), "LTD"))
        self.apply_entity()

    def apply_entity(self):
        """Restrict to the selected entity, rebuild the price panel and pick its opening position."""
        ent = self.entity.get()
        df = self.all_trades
        self.trades = df
        self.results = {}
        for t in self.trees.values():
            t.delete(*t.get_children())
        self.update_kpis()
        self.file_lbl.config(text=f"{self.file_name}  |  {len(df)} trades")
        self.run_lbl.config(text="Enter closing prices, check the settings, then click Run.")
        self.val_date.set((self.trades["trade_date"].max() + pd.offsets.MonthEnd(0))
                          .strftime("%Y-%m-%d"))  # default: month-end of the latest trade
        self.price_vars = {}
        self.auto_opening()
        self.build_price_panel()

    def build_price_panel(self):
        """One price box per bond still held at the end: opening quantity + buys - sells != 0.
        Fully sold bonds need no closing price."""
        net = self.trades.assign(q=self.trades["quantity"].where(
            self.trades["side"] == "BUY", -self.trades["quantity"])).groupby("security_id")["q"].sum()
        if self.opening is not None:
            net = net.add(self.opening.groupby("security_id")["quantity"].sum(), fill_value=0)
        held = sorted(net[net.abs() > 1e-9].index)
        old = {s: v.get() for s, v in self.price_vars.items()}  # keep prices already typed
        for w in self.price_frame.winfo_children():
            w.destroy()
        for i, sec in enumerate(held):
            ttk.Label(self.price_frame, text=sec, style="Card.TLabel").grid(
                row=i, column=0, sticky="w", pady=3, padx=(0, 10))
            default_px = old.get(sec, "")
            if not default_px:
                sec_trades = self.trades[self.trades["security_id"] == sec]
                if not sec_trades.empty:
                    last_px = sec_trades.sort_values("trade_date").iloc[-1]["price"]
                    if pd.notna(last_px) and float(last_px) > 0:
                        default_px = f"{float(last_px):g}"
                elif self.opening is not None:
                    sec_open = self.opening[self.opening["security_id"] == sec]
                    if not sec_open.empty:
                        last_px = sec_open.iloc[-1]["cost_price"]
                        if pd.notna(last_px) and float(last_px) > 0:
                            default_px = f"{float(last_px):g}"
            v = tk.StringVar(value=default_px)
            ttk.Entry(self.price_frame, textvariable=v, width=10).grid(row=i, column=1, padx=4)
            self.price_vars[sec] = v

    # ---------- opening positions (carry-forward) ----------
    def set_opening(self, path):
        df = pd.read_csv(path)
        need = ["security_id", "quantity", "open_date", "cost_price", "coupon_rate"]
        if any(c not in df.columns for c in need):
            raise ValueError(f"Not a positions file; needs columns: {', '.join(need)}")
        self.opening = df[need + [c for c in ("settle_date", "mark_price") if c in df.columns]]
        self.opening_date = pd.Timestamp(Path(path).stem.split("_")[-1])
        self.open_lbl.config(text=f"Opening positions: {Path(path).name} "
                                  f"({len(df)} lots, as of {self.opening_date.date()})")

    def clear_opening(self):
        self.opening = self.opening_date = None
        self.open_lbl.config(text="Opening positions: none (start from zero)")

    def auto_opening(self):
        """Pick the latest saved snapshot dated before the first trade in the loaded file."""
        self.clear_opening()
        first = self.trades["trade_date"].min()
        snaps = sorted((p for p in POS_DIR.glob(f"positions_{self.entity.get()}_*.csv")
                        if pd.Timestamp(p.stem.split("_")[-1]) < first),
                       key=lambda p: p.stem.split("_")[-1])
        if snaps:
            try:
                self.set_opening(snaps[-1])
            except Exception as e:
                messagebox.showerror("Opening positions", str(e))

    # ---------- coupons received ----------
    def read_coupons(self):
        """Coupon payment dates saved in the positions folder (coupons.csv), per bond."""
        self.coupons = {}
        try:
            df = pd.read_csv(POS_DIR / "coupons.csv", parse_dates=["coupon_date"])
            for s, g in df.groupby("security_id"):
                self.coupons[s] = sorted(g["coupon_date"].dt.date.unique())
        except Exception:
            pass
        n = sum(len(v) for v in self.coupons.values())
        self.coupon_lbl.config(
            text=(f"Coupons received: {n} date(s) for {len(self.coupons)} bond(s) "
                  "- interest since last coupon is shown separately") if n
            else "Coupons received: none (interest since last coupon = since purchase)")

    def load_coupons(self):
        """Add coupon payment dates from a file (ISIN + date received) to the saved list."""
        path = filedialog.askopenfilename(
            title="File with coupon payment dates (ISIN + date received)",
            filetypes=[("Coupons", "*.csv *.xlsx *.xls"), ("All files", "*.*")])
        if not path:
            return
        try:
            raw = read_raw(path)
            df = with_detected_header(raw, known=set(PRICE_ID) | set(COUPON_DT), min_hits=2)
            lower = {c.lower(): c for c in df.columns}
            id_col = next((lower[a] for a in PRICE_ID if a in lower), None)
            dt_col = next((lower[a] for a in COUPON_DT if a in lower), None)
            if id_col is None or dt_col is None:
                m = self.ask_mapping(list(df.columns), {"security_id": id_col, "coupon_date": dt_col},
                                     fields=["security_id", "coupon_date"])
                if m is None:
                    return
                id_col, dt_col = m["security_id"], m["coupon_date"]
            new = pd.DataFrame({"security_id": df[id_col].astype(str).str.strip(),
                                "coupon_date": df[dt_col].map(parse_any_date)})
            new["coupon_date"] = pd.to_datetime(new["coupon_date"])
            bad = int(new["coupon_date"].isna().sum())
            new = new.dropna().drop_duplicates()
            if new.empty:
                raise ValueError("No valid (ISIN, date) rows found. Check the date column.")
            old = []
            if self.coupons:
                old = [(s, pd.Timestamp(d)) for s, v in self.coupons.items() for d in v]
            old = pd.DataFrame(old, columns=["security_id", "coupon_date"])
            allc = pd.concat([old, new], ignore_index=True)
            allc["coupon_date"] = pd.to_datetime(allc["coupon_date"])
            allc = allc.drop_duplicates()
            POS_DIR.mkdir(parents=True, exist_ok=True)
            allc = allc.sort_values(["security_id", "coupon_date"])
            allc.assign(coupon_date=allc["coupon_date"].dt.strftime("%Y-%m-%d")).to_csv(
                POS_DIR / "coupons.csv", index=False)
        except Exception as e:
            messagebox.showerror("Load coupons failed", str(e))
            return
        before = sum(len(v) for v in self.coupons.values())
        self.read_coupons()
        added = sum(len(v) for v in self.coupons.values()) - before
        lines = [f"{added} new coupon date(s) added; {len(new) - added} already known."]
        if bad:
            lines.append(f"{bad} row(s) skipped: the date could not be read.")
        lines += [f"{s}: " + ", ".join(str(d) for d in sorted(g["coupon_date"].dt.date))
                  for s, g in new.groupby("security_id")]
        lines.append("\nPlease check the dates above were read correctly "
                     "(text dates are read as MM/DD/YY).")
        messagebox.showinfo("Coupons received", "\n".join(lines))

    def clear_coupons(self):
        if not self.coupons:
            return
        if messagebox.askyesno("Clear coupons", "Remove all saved coupon dates?"):
            try:
                (POS_DIR / "coupons.csv").unlink()
            except FileNotFoundError:
                pass
            self.read_coupons()

    def choose_pos_dir(self):
        """Pick the folder holding the saved month-end positions (e.g. a shared OneDrive folder)."""
        global POS_DIR
        d = filedialog.askdirectory(title="Folder for saved positions", initialdir=POS_DIR.parent
                                    if POS_DIR.parent.exists() else None)
        if not d:
            return
        POS_DIR = Path(d)
        try:
            SETTINGS_FILE.write_text(json.dumps({"positions_dir": str(POS_DIR)}), encoding="utf-8")
        except Exception as e:
            messagebox.showwarning("Not remembered", f"Could not save the setting: {e}")
        self.pos_lbl.config(text=f"Saved positions: {POS_DIR}")
        self.read_coupons()
        if self.trades is not None:  # pick the opening position from the new folder
            self.auto_opening()
            self.build_price_panel()

    def upload_opening(self):
        """Opening position from a file: ISIN, name, quantity, market price, market value.
        The file has no cost, so each bond starts at its opening market price (that price is its
        cost from the positions date). The coupon is read from the bond name (or a coupon
        column). The position is saved for this entity and used by the next trades file."""
        ent = self.entity.get() or "LTD"
        path = filedialog.askopenfilename(
            title=f"Opening positions file for {ent} (ISIN, name, quantity, market price, market value)",
            filetypes=[("Opening positions", "*.xlsx *.xls *.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            raw = read_raw(path)
            known = set(OPEN_ID + OPEN_NAME + OPEN_QTY + OPEN_PX + OPEN_MV + OPEN_COST
                        + OPEN_CPN + OPEN_DT)
            df = with_detected_header(raw, known=known, min_hits=3)
            lower = {str(c).strip().lower(): c for c in df.columns}

            def pick(names):
                return next((lower[a] for a in names if a in lower), None)

            cols = {"security_id": pick(OPEN_ID), "quantity": pick(OPEN_QTY),
                    "market_price": pick(OPEN_PX)}
            if any(v is None for v in cols.values()):
                cols = self.ask_mapping(list(df.columns), cols, fields=list(cols))
                if cols is None:
                    return
            name_c, mv_c, cost_c = pick(OPEN_NAME), pick(OPEN_MV), pick(OPEN_COST)
            cpn_c, dt_c = pick(OPEN_CPN), pick(OPEN_DT)

            def num(series):
                return pd.to_numeric(series.astype(str).str.replace(r"[,\s]", "", regex=True),
                                     errors="coerce")

            out = pd.DataFrame({
                "security_id": df[cols["security_id"]].astype(str).str.strip(),
                "name": df[name_c].astype(str).str.strip() if name_c else "",
                "quantity": num(df[cols["quantity"]]), "price": num(df[cols["market_price"]])})
            if mv_c:
                out["mv"] = num(df[mv_c])
            low = out["security_id"].str.lower()
            out = out[~(low.isin(["", "nan", "none"]) | low.str.startswith("total"))
                      & out["quantity"].notna() & (out["quantity"] != 0)]
            if out.empty:
                raise ValueError("No positions found. The file needs ISIN, quantity and "
                                 "market price columns.")
            if out["price"].isna().any():
                raise ValueError("No market price for: "
                                 + ", ".join(out.loc[out["price"].isna(), "security_id"]))
            out["coupon_rate"] = num(df.loc[out.index, cpn_c]) if cpn_c else float("nan")
            out["coupon_rate"] = out["coupon_rate"].fillna(out["name"].map(parse_coupon))
            if out["coupon_rate"].isna().any():
                raise ValueError(
                    "Could not read the coupon for: "
                    + ", ".join(out.loc[out["coupon_rate"].isna(), "security_id"])
                    + ".\nPut it in the name (e.g. 'DAMACR 6 1/8 08/05/29') or add a Coupon column.")
            out["cost_price"] = (num(df.loc[out.index, cost_c]).fillna(out["price"])
                                 if cost_c else out["price"])
            warn = []
            if mv_c:
                diff = (out["quantity"] * out["price"] / 100 - out["mv"]).abs()
                bad = out[diff > (0.001 * out["mv"].abs()).clip(lower=1.0)]
                warn = [f"{r.security_id}: file says {r.mv:,.2f}, quantity x price = "
                        f"{r.quantity * r.price / 100:,.2f}" for r in bad.itertuples()]
            asof = None
            if dt_c:
                ds = df.loc[out.index, dt_c].map(parse_any_date).dropna().unique()
                if len(ds) == 1:
                    asof = pd.Timestamp(ds[0])
            if asof is None:
                default = ""
                if self.trades is not None:
                    default = (self.trades["trade_date"].min().replace(day=1)
                               - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                s = simpledialog.askstring(
                    "Opening positions date",
                    "These positions are as of (YYYY-MM-DD).\nUsually the last day of the month "
                    "before your first trade:", initialvalue=default, parent=self)
                if not s:
                    return
                asof = pd.Timestamp(s.strip())
            snap = POS_DIR / f"positions_{ent}_{asof.date()}.csv"
            if snap.exists() and not messagebox.askyesno(
                    "Replace?", f"{snap.name} already exists. Replace it with this file?"):
                return
            lots = pd.DataFrame({
                "security_id": out["security_id"], "quantity": out["quantity"],
                "open_date": asof.strftime("%Y-%m-%d"), "settle_date": asof.strftime("%Y-%m-%d"),
                "cost_price": out["cost_price"], "coupon_rate": out["coupon_rate"],
                "mark_price": out["price"]})
            POS_DIR.mkdir(parents=True, exist_ok=True)
            lots.to_csv(snap, index=False)
            fr.save_opening(POS_DIR, ent, lots, asof)   # period reports start from it too
            self.set_opening(snap)
            if self.trades is not None:
                self.build_price_panel()
        except Exception as e:
            messagebox.showerror("Opening positions", str(e))
            return
        lines = [f"Opening positions for {ent} as of {asof.date()}: {len(out)} position(s), "
                 f"face {out['quantity'].sum():,.0f}, market value "
                 f"{(out['quantity'] * out['price'] / 100).sum():,.2f}.",
                 f"Saved as {snap.name}. Each bond starts at its opening market price, which "
                 "is its cost from this date.",
                 "The next trades file continues FIFO from these positions."]
        if warn:
            lines += ["", "Check - market value differs from quantity x price for:"] + warn[:10]
        messagebox.showinfo("Opening positions loaded", "\n".join(lines))

    def choose_opening(self):
        POS_DIR.mkdir(exist_ok=True)
        path = filedialog.askopenfilename(initialdir=POS_DIR, filetypes=[("Positions", "positions_*.csv")])
        if path:
            owner = "_".join(Path(path).stem.split("_")[1:-1])
            if owner != self.entity.get() and not messagebox.askyesno(
                    "Different entity?",
                    f"This file belongs to '{owner}', but the selected entity is "
                    f"'{self.entity.get()}'. Use it anyway?"):
                return
            try:
                self.set_opening(path)
                self.build_price_panel()
            except Exception as e:
                messagebox.showerror("Opening positions", str(e))

    def save_closing(self, closing, vd):
        POS_DIR.mkdir(exist_ok=True)
        path = POS_DIR / f"positions_{self.entity.get()}_{vd.date()}.csv"
        if path.exists() and not messagebox.askyesno(
                "Overwrite?", f"{path.name} already exists. Overwrite it?"):
            return
        cols = ["security_id", "quantity", "open_date", "settle_date", "cost_price", "coupon_rate"]
        # mark_price = this month-end closing price; next month measures its period P&L from it
        out = (closing[cols].assign(mark_price=closing["market_price"]) if len(closing)
               else pd.DataFrame(columns=cols + ["mark_price"]))
        out.to_csv(path, index=False)
        messagebox.showinfo("Positions saved", f"Closing positions saved to\n{path}")

    def load_prices(self):
        """Fill the market price boxes from a file with a security id column and a price column."""
        if self.trades is None:
            messagebox.showwarning("No trades", "Load the trades file first.")
            return
        path = filedialog.askopenfilename(
            filetypes=[("Prices", "*.csv *.xlsx *.xls"), ("All files", "*.*")])
        if not path:
            return
        try:
            raw = read_raw(path)
            df = with_detected_header(raw, known=set(PRICE_ID) | set(PRICE_PX) | set(PRICE_DT),
                                      min_hits=2)
            lower = {c.lower(): c for c in df.columns}
            id_col = next((lower[a] for a in PRICE_ID if a in lower), None)
            px_col = next((lower[a] for a in PRICE_PX if a in lower), None)
            if id_col is None or px_col is None:
                guess = {"security_id": id_col, "price": px_col}
                m = self.ask_mapping(list(df.columns), guess, fields=["security_id", "price"])
                if m is None:
                    return
                id_col, px_col = m["security_id"], m["price"]
            dt_col = next((lower[a] for a in PRICE_DT if a in lower), None)
            if dt_col is not None:  # a single price date in the file becomes the valuation date
                dates = pd.to_datetime(df[dt_col], errors="coerce").dropna().unique()
                if len(dates) == 1:
                    self.val_date.set(pd.Timestamp(dates[0]).strftime("%Y-%m-%d"))
            df = df[[id_col, px_col]].dropna()
            df[id_col] = df[id_col].astype(str).str.strip()
            df[px_col] = pd.to_numeric(df[px_col], errors="coerce")
            prices = df.dropna().drop_duplicates(id_col, keep="last").set_index(id_col)[px_col]
        except Exception as e:
            messagebox.showerror("Load prices failed", str(e))
            return
        matched = [s for s in self.price_vars if s in prices.index]
        for s in matched:
            self.price_vars[s].set(f"{prices[s]:g}")
        missing = [s for s in self.price_vars if s not in prices.index]
        msg = f"Loaded prices for {len(matched)} of {len(self.price_vars)} securities."
        if missing:
            msg += "\nNo price found for: " + ", ".join(missing)
        messagebox.showinfo("Closing prices", msg)

    def ask_mapping(self, columns, guess, fields=None):
        """Modal dialog: map each required field to a column in the file."""
        win = tk.Toplevel(self)
        win.title("Map columns")
        win.transient(self)
        win.grab_set()
        ttk.Label(win, text="Select which column in your file holds each field:",
                  padding=8).grid(row=0, column=0, columnspan=2)
        fields = fields or REQUIRED
        vars_ = {}
        for i, r in enumerate(fields, start=1):
            ttk.Label(win, text=r, padding=4).grid(row=i, column=0, sticky="w")
            v = tk.StringVar(value=guess.get(r) or "")
            ttk.Combobox(win, textvariable=v, values=columns, state="readonly",
                         width=28).grid(row=i, column=1, padx=8, pady=2)
            vars_[r] = v
        result = {}

        def ok():
            chosen = {r: v.get() for r, v in vars_.items()}
            if not all(chosen.values()):
                messagebox.showerror("Map columns", "Map every field.", parent=win)
                return
            result.update(chosen)
            win.destroy()

        ttk.Button(win, text="OK", command=ok).grid(row=len(fields) + 1, column=0,
                                                    columnspan=2, pady=8)
        self.wait_window(win)
        return result or None

    def run(self):
        if self.trades is None:
            messagebox.showwarning("No data", "Load a trades file first.")
            return
        try:
            prices = {s: float(v.get()) for s, v in self.price_vars.items() if v.get().strip()}
            vd = pd.Timestamp(self.val_date.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Check market prices and valuation date.")
            return
        missing = [s for s in self.price_vars if s not in prices]
        if missing:
            # Auto-populate missing market prices from latest trade or cost so Unrealized P&L is calculated
            for s in missing:
                sec_trades = self.trades[self.trades["security_id"] == s]
                if not sec_trades.empty:
                    last_px = float(sec_trades.sort_values("trade_date").iloc[-1]["price"])
                    prices[s] = last_px
                    self.price_vars[s].set(f"{last_px:g}")
                elif self.opening is not None:
                    sec_open = self.opening[self.opening["security_id"] == s]
                    if not sec_open.empty:
                        last_px = float(sec_open.iloc[-1]["cost_price"])
                        prices[s] = last_px
                        self.price_vars[s].set(f"{last_px:g}")
        last_trade = self.trades["trade_date"].max()
        if vd < last_trade:
            messagebox.showerror(
                "Valuation date too early",
                f"The file has trades up to {last_trade.date()}, after the valuation date "
                f"{vd.date()}. Set the valuation date on or after {last_trade.date()} "
                "(normally the month-end).")
            return
        if self.opening_date is not None and vd <= self.opening_date:
            messagebox.showerror(
                "Valuation date too early",
                f"The valuation date must be after the opening positions date "
                f"({self.opening_date.date()}). This also stops a saved position being overwritten.")
            return
        if self.opening is not None and self.trades["trade_date"].min() <= self.opening_date:
            if not messagebox.askyesno(
                    "Possible double count",
                    f"Trades start on {self.trades['trade_date'].min().date()}, which is on or "
                    f"before the opening positions date ({self.opening_date.date()}).\n"
                    "Those trades may already be in the opening positions. Continue?"):
                return
        closed, closing, summary = run_fifo(self.trades, vd, prices,
                                            opening_lots=self.opening,
                                            period_start=self.opening_date,
                                            day_count={"30E/360": "30e/360", "30/360 US": "30/360",
                                                       "Actual": "actual"}[self.dc_var.get()],
                                            interest_base="market" if self.base_var.get().startswith("Market") else "face",
                                            coupon_dates=self.coupons)
        self.results = {"closed": closed, "closing": closing, "summary": summary}
        for key, df in self.results.items():
            self.show(self.trees[key], df)
        self.update_kpis()
        self.run_lbl.config(text=f"Last run: interest on {self.base_var.get().lower()}, "
                                 f"{self.dc_var.get()} days, valued {vd.date()}")
        shorts = closing[closing["quantity"] < 0] if len(closing) else closing
        if len(shorts):
            names = ", ".join(sorted(shorts["security_id"].unique()))
            messagebox.showwarning(
                "Short positions found",
                f"Sold more than held for: {names}.\nThis usually means an earlier month's "
                "position or purchase is missing (wrong or missing opening positions, or a "
                "trade file with sells but no matching buys).")
            if self.save_pos.get() and not messagebox.askyesno(
                    "Save anyway?", "Closing positions contain shorts. Save them anyway?"):
                return
        if self.save_pos.get():
            self.save_closing(closing, vd)
            self.save_run_data(vd, prices)

    # ---------- stored data and period reports ----------
    def save_run_data(self, vd, prices):
        """Keep this month's trades and closing prices so period reports need no upload."""
        ent = self.entity.get() or "LTD"
        try:
            others = fr.overlaps(POS_DIR, ent, self.trades)
            if others and not messagebox.askyesno(
                    "Overlapping trade dates",
                    "The trades in this file overlap the dates already stored for: "
                    f"{', '.join(others)}.\nSaving them may double count trades in period "
                    "reports. Save anyway?"):
                return
            label = fr.save_run(POS_DIR, ent, self.trades, getattr(self, "file_name", ""), vd,
                                prices, {"day_count": self.dc_var.get(),
                                         "interest_base": self.base_var.get()})
            self.run_lbl.config(text=self.run_lbl.cget("text")
                                + f"   |   stored as {label} for period reports")
        except Exception as e:
            messagebox.showerror("Saving data", str(e))

    def open_report(self):
        """Pick a From and To month and rebuild the report from stored data (no upload)."""
        ent = self.entity.get() or "LTD"
        runs = fr.list_runs(POS_DIR, ent)
        if not runs:
            messagebox.showinfo(
                "Period report",
                "Nothing is stored yet. Run a month with 'Save positions and data after Run' "
                "ticked. After that you can report on any period without uploading trades.")
            return
        labels = [r["label"] for r in runs]
        win = tk.Toplevel(self)
        win.title("Period report")
        win.transient(self)
        win.configure(bg=P["bg"])
        box = ttk.Frame(win, padding=16)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text=f"Period report - {ent}", font=(FONT, 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="Built from the months stored on this computer; no upload needed.",
                  foreground=P["muted"]).grid(row=1, column=0, columnspan=2, sticky="w",
                                              pady=(0, 10))
        f_var, t_var = tk.StringVar(value=labels[0]), tk.StringVar(value=labels[-1])
        ttk.Label(box, text="From month").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(box, textvariable=f_var, values=labels, state="readonly",
                     width=12).grid(row=2, column=1, padx=8)
        ttk.Label(box, text="To month").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(box, textvariable=t_var, values=labels, state="readonly",
                     width=12).grid(row=3, column=1, padx=8)
        stored = "\n".join(f"{r['label']}   valued {r['valuation_date']}   {r['n_trades']} trades"
                           for r in runs)
        ttk.Label(box, text="Stored months:\n" + stored, foreground=P["muted"]).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))

        def generate():
            self.show_report(win, f_var.get(), t_var.get())

        ttk.Button(box, text="Generate report", style="Primary.TButton",
                   command=generate).grid(row=5, column=0, columnspan=2, pady=(12, 0))

    def show_report(self, win, from_label, to_label):
        ent = self.entity.get() or "LTD"
        try:
            closed, closing, summary, info = fr.build_report(
                POS_DIR, ent, from_label, to_label,
                day_count={"30E/360": "30e/360", "30/360 US": "30/360",
                           "Actual": "actual"}[self.dc_var.get()],
                interest_base="market" if self.base_var.get().startswith("Market") else "face",
                coupon_dates=self.coupons)
        except Exception as e:
            messagebox.showerror("Period report", str(e), parent=win)
            return
        if info["gaps"] and not messagebox.askyesno(
                "Months missing",
                f"No stored data for: {', '.join(info['gaps'])}.\nPositions may be wrong if "
                "those months had trades. Continue anyway?", parent=win):
            return
        self.results = {"closed": closed, "closing": closing, "summary": summary}
        for key, df in self.results.items():
            self.show(self.trees[key], df)
        self.update_kpis()
        self.nb.select(0)
        self.run_lbl.config(
            text=f"Period report {from_label} to {to_label}: "
                 f"{info['period_start'].date()} to {info['period_end'].date()}, "
                 f"{info['trades_in_period']} trades, interest on {self.base_var.get().lower()}, "
                 f"{self.dc_var.get()} days. Click Export to Excel to download it.")
        win.destroy()

    @staticmethod
    def _fmt(col, x):
        """Display text for one cell."""
        if x is None or (isinstance(x, float) and x != x):
            return "-"
        if hasattr(x, "isoformat"):
            return str(x)[:10]
        if isinstance(x, numbers.Number):
            if col == "days":
                return f"{int(x)}"
            if "quantity" in col:
                return f"{x:,.0f}"
            if "price" in col or col == "coupon_rate":
                return f"{x:,.3f}"
            return f"{x:,.2f}"
        return str(x)

    def show(self, tree, df):
        """Fill a table: friendly headings, aligned numbers, zebra rows, red loss rows, totals."""
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            tree["columns"] = ("msg",)
            tree.heading("msg", text="")
            tree.column("msg", width=600, anchor="w", stretch=True)
            tree.insert("", "end", values=("No data for this period.",))
            return
        cols = list(df.columns)
        tree["columns"] = cols
        rows = [[self._fmt(c, x) for c, x in zip(cols, r)] for r in df.itertuples(index=False)]
        neg = [any(c in PL_COLS and isinstance(x, numbers.Number) and x == x and x < 0
                   for c, x in zip(cols, r)) for r in df.itertuples(index=False)]
        sums = [c for c in cols if c in SUM_COLS]
        if sums:
            tot = [""] * len(cols)
            tot[0] = "TOTAL"
            for c in sums:
                tot[cols.index(c)] = self._fmt(c, float(df[c].sum()))
            rows.append(tot)
            neg.append(False)
        font = tkfont.Font(font=(FONT, 10))
        for j, c in enumerate(cols):
            head = HEADINGS.get(c, c.replace("_", " ").title())
            anchor = "w" if c in TEXT_COLS else "center" if c in DATE_COLS else "e"
            width = max([font.measure(head)] + [font.measure(r[j]) for r in rows]) + 34
            tree.heading(c, text=head, anchor=anchor)
            tree.column(c, width=min(max(width, 90), 280), anchor=anchor, stretch=False)
        for i, (r, is_neg) in enumerate(zip(rows, neg)):
            tags = ["total"] if sums and i == len(rows) - 1 else []
            if i % 2 and not tags:
                tags.append("odd")
            if is_neg:
                tags.append("neg")
            tree.insert("", "end", values=r, tags=tags)

    @staticmethod
    def _with_total(df):
        """Copy of df with a TOTAL row at the end (face, P&L and interest columns summed)."""
        sums = [c for c in df.columns if c in SUM_COLS]
        if not sums:
            return df
        tot = {c: None for c in df.columns}
        tot[df.columns[0]] = "TOTAL"
        for c in sums:
            tot[c] = float(df[c].sum())
        return pd.concat([df, pd.DataFrame([tot])], ignore_index=True)

    @staticmethod
    def _style_sheets(xw):
        """Header colour, column widths, number formats and frozen header row in the export."""
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
        for ws in xw.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="14213D")
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.freeze_panes = "A2"
            for i, col in enumerate(ws.columns, 1):
                head = str(col[0].value or "")
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[get_column_letter(i)].width = min(max(width + 3, 12), 60)
                for c in col[1:]:
                    if isinstance(c.value, (int, float)):
                        if "quantity" in head:
                            c.number_format = "#,##0"
                        elif "price" in head or head == "coupon_rate":
                            c.number_format = "0.000"
                        elif head != "days":
                            c.number_format = "#,##0.00;[Red]-#,##0.00"
            last = ws.max_row  # highlight the TOTAL row at the bottom
            if last > 1 and str(ws.cell(last, 1).value) == "TOTAL":
                for c in ws[last]:
                    c.font = Font(bold=True)
                    c.fill = PatternFill("solid", fgColor="DDEBF7")
                    c.border = Border(top=Side(style="medium", color="14213D"))

    def export(self):
        if not self.results:
            messagebox.showwarning("Nothing to export", "Run the calculation first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as xw:
                order = [("summary", "Summary"), ("closing", "Closing Positions"), ("closed", "Closed Matches (Sales)")]
                for k, title in order:
                    df = self.results.get(k)
                    if df is not None and not df.empty:
                        self._with_total(df).to_excel(xw, sheet_name=title, index=False)
                    elif k == "closed":
                        pd.DataFrame([{"Status": "No positions were sold in this period. All transactions were acquisitions / inventory additions."}]).to_excel(xw, sheet_name=title, index=False)
                    else:
                        pd.DataFrame([{"Status": "No data"}]).to_excel(xw, sheet_name=title, index=False)
                self._style_sheets(xw)
        except ImportError:
            messagebox.showerror(
                "Excel export needs openpyxl",
                "openpyxl is not installed for the Python running this program.\n\n"
                "Open a terminal and run:\n"
                f'"{sys.executable}" -m pip install openpyxl\n\n'
                "Then restart the program and export again.")
            return
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return
        messagebox.showinfo("Exported", f"Saved to {path}")


def _selftest(out_path):
    """Used to verify the packaged .exe: runs a calculation, an Excel write and opens the window."""
    import openpyxl  # noqa: F401  (must be bundled)
    lines = []
    try:
        t = pd.DataFrame([("2026-01-05", "X1", "[B]", 1_000_000, 99.0, 5.0),
                          ("2026-01-20", "X1", "[S]", 400_000, 100.0, 5.0)],
                         columns=["trade_date", "security_id", "side", "quantity", "price",
                                  "coupon_rate"])
        closed, closing, _ = run_fifo(t, "2026-01-31", {"X1": 100.0}, day_count="30e/360")
        lines.append(f"realized={closed.realized_pl.sum():.2f} unrealized={closing.unrealized_pl.sum():.2f}")
        xlsx = Path(out_path).with_suffix(".xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
            closing.to_excel(xw, sheet_name="t", index=False)
        lines.append(f"excel_ok={xlsx.exists()}")
        a = App()
        a.update()
        a.destroy()
        lines.append(f"window_ok=True positions_dir={POS_DIR}")
        lines.append("RESULT=OK")
    except Exception as e:  # report instead of crashing silently in a windowed exe
        lines.append(f"RESULT=FAIL {type(e).__name__}: {e}")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest(sys.argv[sys.argv.index("--selftest") + 1])
    else:
        App().mainloop()






