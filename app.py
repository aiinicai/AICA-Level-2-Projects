import datetime as dt
import os
import queue
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import BASE, THEMES
from .engine import WIN, Engine
from .tray import Tray
from .widgets import GuidedBreak, MiniHUD, Toast
from .screen_page import ScreenTimePage
from .wellness_lab import WellnessLab
from .news_service import IndiaNewsManager
from .news_page import IndiaNewsPage


# ---------------------------------------------------------------- autostart (Windows)
def _startup_file():
    return Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/BreakBuddy.bat"


def autostart_enabled():
    return WIN and _startup_file().exists()


def set_autostart(on):
    if not WIN:
        return
    p = _startup_file()
    if on:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f'@echo off\ncd /d "{BASE}"\nstart "" pythonw main.py\n')
    elif p.exists():
        p.unlink()


def fmt_h(sec):
    sec = int(sec)
    return f"{sec // 3600}h {(sec % 3600) // 60:02d}m"


# ---------------------------------------------------------------- app
class App:
    def __init__(self):
        self.e = Engine()
        self.root = tk.Tk()
        self.root.title("BreakBuddy Pro v4.0 — Wellness, Focus & India Finance News")
        self.root.geometry("1110x760")
        self.root.minsize(1000, 700)
        self.q = queue.Queue()
        self.popup = None
        self.hud = None
        self.snooze_until = 0.0
        self.cur_page = 0
        self._shutting_down = False
        self._tick_job = None
        self.news = IndiaNewsManager()
        self.tray = Tray(self.q)
        self.t = THEMES.get(self.e.s["theme"], THEMES["dark"])
        self.tray_ok = bool(self.e.s["use_tray"] and self.tray.start())
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-b>", lambda ev: self.show_break(manual=True))
        self.root.bind("<Control-m>", lambda ev: self.toggle_hud())
        self.root.bind("<Control-p>", lambda ev: self.toggle_pomo())
        self.root.bind("<Control-l>", lambda ev: self.toggle_day_night())
        self.root.bind("<Control-r>", lambda ev: self.open_scratchpad())
        self.root.bind("<Control-q>", lambda ev: self.quit())
        self._tick_job = self.root.after(1000, self.tick)

    # ------------------------------------------------------------ theme + layout shell
    def apply_theme(self):
        t = self.t
        st = ttk.Style()
        st.theme_use("clam")
        self.root.configure(bg=t["bg"])
        st.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["card"], font=("Segoe UI", 10))
        st.configure("TFrame", background=t["bg"])
        st.configure("Card.TFrame", background=t["card"], relief="flat")
        st.configure("Alt.TFrame", background=t["card_alt"], relief="flat")
        st.configure("TLabel", background=t["bg"], foreground=t["fg"])
        st.configure("Card.TLabel", background=t["card"], foreground=t["fg"])
        st.configure("Alt.TLabel", background=t["card_alt"], foreground=t["fg"])
        st.configure("Sub.TLabel", background=t["card"], foreground=t["sub"], font=("Segoe UI", 9))
        st.configure("Big.TLabel", background=t["card"], foreground=t["fg"], font=("Segoe UI", 22, "bold"))
        st.configure("H.TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 13, "bold"))
        st.configure("TButton", padding=(10, 6), background=t["card_alt"], foreground=t["fg"], borderwidth=0)
        st.map("TButton", background=[("active", t["bar"])])
        st.configure("Accent.TButton", background=t["accent"], foreground="white", padding=(12, 7), font=("Segoe UI", 10, "bold"))
        st.map("Accent.TButton", background=[("active", t["good"])])
        st.configure("Good.TButton", background=t["good"], foreground="white", padding=(10, 6), font=("Segoe UI", 9, "bold"))
        st.map("Good.TButton", background=[("active", t["accent"])])
        st.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        st.configure("TRadiobutton", background=t["bg"], foreground=t["fg"])
        st.configure("Treeview", background=t["card"], fieldbackground=t["card"], foreground=t["fg"], rowheight=28, borderwidth=0)
        st.configure("Treeview.Heading", background=t["card_alt"], foreground=t["fg"], font=("Segoe UI", 10, "bold"))
        st.map("Treeview", background=[("selected", t["accent"])], foreground=[("selected", "white")])
        st.configure("Horizontal.TProgressbar", background=t["accent"], troughcolor=t["bar"], thickness=8)
        st.configure("TNotebook", background=t["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=t["card_alt"], foreground=t["fg"], padding=(12, 10))
        st.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", "white")])

    def build(self):
        # Persist scratchpad before palette changes reconstruct the widgets.
        old_lab = getattr(self, "lab", None)
        if old_lab:
            old_lab.flush()
        for w in self.root.winfo_children():
            w.destroy()
        self.apply_theme()
        t = self.t

        # Top Menu
        m = tk.Menu(self.root)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Take a Break Now   (Ctrl+B)", command=lambda: self.show_break(manual=True))
        fm.add_command(label="Toggle Floating HUD   (Ctrl+M)", command=self.toggle_hud)
        fm.add_command(label="Start/Pause Pomodoro   (Ctrl+P)", command=self.toggle_pomo)
        fm.add_command(label="Log Water (+1 Glass)", command=self.drink)
        fm.add_command(label="Where I Left Off   (Ctrl+R)", command=self.open_scratchpad)
        fm.add_command(label="Switch Day / Night   (Ctrl+L)", command=self.toggle_day_night)
        fm.add_command(label="App Usage Monitor", command=lambda: self.select_page(7))
        fm.add_command(label="Meditation", command=self.open_meditation)
        fm.add_command(label="Live India Tax & Finance News", command=lambda: self.select_page(9))
        fm.add_separator()
        fm.add_command(label="Export Wellness CSV Report...", command=self.export_csv_dialog)
        fm.add_separator()
        fm.add_command(label="STOP & EXIT BreakBuddy Pro (Ctrl+Q)", command=self.quit)
        m.add_cascade(label="Actions", menu=fm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label="About BreakBuddy Pro v4.0", command=lambda: messagebox.showinfo(
            "BreakBuddy Pro v4.0",
            "Executive Wellness, Ergonomics & Deep Work Companion.\n"
            "Built for high-focus professionals & due-date seasons.\n\n"
            "Shortcuts:\n• Ctrl+B: Instant Guided Break\n• Ctrl+M: Floating Mini-HUD\n• Ctrl+P: Start/Pause Pomodoro"
        ))
        m.add_cascade(label="Help", menu=hm)
        self.root.config(menu=m)

        # Main Shell: Left Sidebar + Right Content Area
        shell = tk.Frame(self.root, bg=t["bg"])
        shell.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(shell, bg=t["sidebar"], width=215)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand Header in Sidebar
        brand = tk.Frame(self.sidebar, bg=t["sidebar"], pady=18, padx=16)
        brand.pack(fill="x")
        tk.Label(brand, text="🩺 BreakBuddy", font=("Segoe UI", 15, "bold"), bg=t["sidebar"], fg="white", anchor="w").pack(fill="x")
        tk.Label(brand, text="PRO v4.0 • WORK SUITE", font=("Segoe UI", 8, "bold"), bg=t["sidebar"], fg=t["accent"], anchor="w").pack(fill="x", pady=(2, 0))

        theme_text = "☀  Day Mode" if self.e.s["theme"] != "light" else "🌙  Night Mode"
        self.day_btn = tk.Button(brand, text=theme_text, command=self.toggle_day_night,
                                 bg=t["card_alt"], fg=t["fg"], activebackground=t["accent"],
                                 activeforeground="white", borderwidth=0, cursor="hand2", pady=6)
        self.day_btn.pack(fill="x", pady=(10, 0))

        self.nav_btns = []
        nav_items = [
            ("🏠  Dashboard", 0),
            ("🍅  Focus & Tasks", 1),
            ("🧘  Routines", 2),
            ("📅  Deadlines", 3),
            ("📊  Analytics", 4),
            ("🎭  Characters", 5),
            ("⚙️  Settings", 6),
            ("💻  App Screen Time", 7),
            ("🧠  Wellness Lab", 8),
            ("📰  India Tax & Finance", 9),
        ]
        for label, idx in nav_items:
            b = tk.Label(self.sidebar, text=label, font=("Segoe UI", 11), bg=t["sidebar"], fg="#94a3b8",
                         anchor="w", padx=20, pady=9, cursor="hand2")
            b.pack(fill="x", pady=1)
            b.bind("<Button-1>", lambda ev, i=idx: self.select_page(i))
            self.nav_btns.append(b)

        # Sidebar Footer Quick Actions
        foot = tk.Frame(self.sidebar, bg=t["sidebar"], padx=14, pady=14)
        foot.pack(side="bottom", fill="x")
        hud_btn = tk.Label(foot, text="⚡ Toggle Mini-HUD (Ctrl+M)", font=("Segoe UI", 9, "bold"),
                           bg="#1e293b", fg="#60a5fa", pady=7, cursor="hand2")
        hud_btn.pack(fill="x", pady=(0, 6))
        hud_btn.bind("<Button-1>", lambda e: self.toggle_hud())
        resume_btn = tk.Label(foot, text="📝 Where I Left Off (Ctrl+R)", font=("Segoe UI", 9, "bold"),
                              bg=t["card_alt"], fg=t["fg"], pady=7, cursor="hand2")
        resume_btn.pack(fill="x", pady=(0, 7))
        stop_btn = tk.Button(foot, text="⏹  STOP & EXIT APP", font=("Segoe UI", 10, "bold"),
                             bg="#b91c1c", fg="white", activebackground="#991b1b",
                             activeforeground="white", relief="flat", borderwidth=0,
                             command=self.quit, cursor="hand2", pady=9)
        stop_btn.pack(fill="x", pady=(0, 6))
        resume_btn.bind("<Button-1>", lambda ev: self.open_scratchpad())
        self.lbl_side_rank = tk.Label(foot, text="", font=("Segoe UI", 8), bg=t["sidebar"], fg="#64748b", wraplength=185, justify="left")
        self.lbl_side_rank.pack(anchor="w")

        # Pages Container
        self.content = tk.Frame(shell, bg=t["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        self.pages = []
        builders = [
            self.build_dashboard,
            self.build_focus,
            self.build_routines,
            self.build_deadlines,
            self.build_progress,
            self.build_characters,
            self.build_settings,
            self.build_screen_time,
            self.build_wellness_lab,
            self.build_india_news,
        ]
        for fn in builders:
            p = ttk.Frame(self.content)
            self.pages.append(p)
            fn(p)

        self.select_page(self.cur_page)

    def select_page(self, idx):
        self.cur_page = idx
        for i, p in enumerate(self.pages):
            if i == idx:
                p.pack(fill="both", expand=True)
            else:
                p.pack_forget()
        for i, b in enumerate(self.nav_btns):
            if i == idx:
                b.config(bg=self.t["accent"], fg="white", font=("Segoe UI", 11, "bold"))
            else:
                b.config(bg=self.t["sidebar"], fg="#94a3b8", font=("Segoe UI", 11))
        self.refresh_all()
        if idx == 9:
            self.news_page.enter()

    def card(self, parent, **pack):
        f = tk.Frame(parent, bg=self.t["card"], highlightthickness=1, highlightbackground=self.t["border"])
        f.pack(**pack)
        return f

    # ------------------------------------------------------------ PAGE 0: DASHBOARD
    def build_dashboard(self, f):
        t = self.t
        # Top KPI Hero Row
        kpi_row = tk.Frame(f, bg=t["bg"])
        kpi_row.pack(fill="x", pady=(0, 10))
        self.kpi_labels = {}
        kpis = [
            ("screen", "💻 SCREEN TIME", "0h 00m", "Active session today"),
            ("wellness", "🛡️ WELLNESS SCORE", "100 / 100", "Ergonomic health index"),
            ("streak", "🔥 ACTIVE STREAK", "0 Days", "Break goal consistency"),
            ("xp", "⭐ LEVEL & XP", "Lvl 1 (0 XP)", "Junior Wellness Associate"),
        ]
        for key, title, val, sub in kpis:
            c = tk.Frame(kpi_row, bg=t["card"], highlightthickness=1, highlightbackground=t["border"], padx=14, pady=10)
            c.pack(side="left", fill="both", expand=True, padx=(0, 8) if key != "xp" else 0)
            tk.Label(c, text=title, font=("Segoe UI", 8, "bold"), bg=t["card"], fg=t["accent"]).pack(anchor="w")
            v_lbl = tk.Label(c, text=val, font=("Segoe UI", 17, "bold"), bg=t["card"], fg=t["fg"])
            v_lbl.pack(anchor="w", pady=(2, 0))
            s_lbl = tk.Label(c, text=sub, font=("Segoe UI", 8), bg=t["card"], fg=t["sub"])
            s_lbl.pack(anchor="w")
            self.kpi_labels[key] = (v_lbl, s_lbl)

        # Middle Section: Dual Ring Canvas + Progress & Interactive Water Tracker
        mid = tk.Frame(f, bg=t["bg"])
        mid.pack(fill="x", pady=(0, 10))

        left = self.card(mid, side="left", padx=(0, 10))
        self.ring = tk.Canvas(left, width=240, height=240, bg=t["card"], highlightthickness=0)
        self.ring.pack(padx=12, pady=10)

        right = self.card(mid, side="left", fill="both", expand=True)
        r_in = tk.Frame(right, bg=t["card"], padx=16, pady=12)
        r_in.pack(fill="both", expand=True)

        tk.Label(r_in, text="Daily Goals & Interactive Hydration", font=("Segoe UI", 12, "bold"), bg=t["card"], fg=t["fg"]).pack(anchor="w")

        self.lbl_breaks = tk.Label(r_in, text="", font=("Segoe UI", 10), bg=t["card"], fg=t["fg"])
        self.lbl_breaks.pack(anchor="w", pady=(8, 2))
        self.bar_breaks = ttk.Progressbar(r_in, maximum=100)
        self.bar_breaks.pack(fill="x", pady=(0, 8))

        self.lbl_water = tk.Label(r_in, text="", font=("Segoe UI", 10), bg=t["card"], fg=t["fg"])
        self.lbl_water.pack(anchor="w", pady=(4, 2))

        # Interactive Water Cups Canvas
        self.water_canvas = tk.Canvas(r_in, width=440, height=42, bg=t["card"], highlightthickness=0, cursor="hand2")
        self.water_canvas.pack(anchor="w", pady=4)
        self.water_canvas.bind("<Button-1>", lambda e: self.drink())

        act_row = tk.Frame(r_in, bg=t["card"])
        act_row.pack(fill="x", pady=(6, 0))
        ttk.Button(act_row, text="🥤 +1 Glass of Water", style="Good.TButton", command=self.drink).pack(side="left", padx=(0, 6))
        ttk.Button(act_row, text="🪑 Log Posture Check (+2 XP)", command=self.manual_posture).pack(side="left", padx=6)
        ttk.Button(act_row, text="👁️ Quick 20s Eye Rest", command=self.quick_eye_rest).pack(side="left", padx=6)

        # Quick Launch & Focus Controls Card
        do = self.card(f, fill="x", pady=(0, 10))
        do_in = tk.Frame(do, bg=t["card"], padx=16, pady=10)
        do_in.pack(fill="x")
        tk.Label(do_in, text="Instant Break Launcher & Focus Mode", font=("Segoe UI", 11, "bold"), bg=t["card"], fg=t["fg"]).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))

        tk.Label(do_in, text="Routine:", bg=t["card"], fg=t["sub"]).grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.cb_act = ttk.Combobox(do_in, state="readonly", width=25,
                                   values=["Auto rotate"] + [a["name"] for a in self.e.acts])
        self.cb_act.set(self.e.s["activity"] if self.e.s["activity"] in self.cb_act["values"] else "Auto rotate")
        self.cb_act.grid(row=1, column=1, padx=4, pady=4)

        tk.Label(do_in, text="Companion:", bg=t["card"], fg=t["sub"]).grid(row=1, column=2, sticky="w", padx=(12, 6))
        self.cb_char = ttk.Combobox(do_in, state="readonly", width=22,
                                    values=["Random"] + [c["name"] for c in self.e.chars])
        self.cb_char.set(self.e.s["character"] if self.e.s["character"] in self.cb_char["values"] else "Random")
        self.cb_char.grid(row=1, column=3, padx=4, pady=4)

        for cb in (self.cb_act, self.cb_char):
            cb.bind("<<ComboboxSelected>>", lambda ev: self.save_choice())

        ttk.Button(do_in, text="▶ Start Break Now", style="Accent.TButton", command=self.start_selected).grid(
            row=1, column=4, padx=(14, 6))

        fm = tk.Frame(do_in, bg=t["card"])
        fm.grid(row=1, column=5, padx=(8, 0))
        self.cb_dnd = ttk.Combobox(fm, state="readonly", width=9, values=["15 min", "30 min", "60 min", "Off"])
        self.cb_dnd.set("30 min")
        self.cb_dnd.pack(side="left")
        ttk.Button(fm, text="DND", command=self.set_dnd).pack(side="left", padx=4)

        # Upcoming Statutory & Filing Deadlines Card
        dl = self.card(f, fill="both", expand=True)
        dl_in = tk.Frame(dl, bg=t["card"], padx=16, pady=10)
        dl_in.pack(fill="both", expand=True)
        hdr_dl = tk.Frame(dl_in, bg=t["card"])
        hdr_dl.pack(fill="x")
        tk.Label(hdr_dl, text="📅 Upcoming Compliance & Filing Deadlines", font=("Segoe UI", 11, "bold"), bg=t["card"], fg=t["fg"]).pack(side="left")
        self.lbl_status = tk.Label(hdr_dl, text="", font=("Segoe UI", 9), bg=t["card"], fg=t["sub"])
        self.lbl_status.pack(side="right")

        self.lbl_dead = tk.Label(dl_in, text="", font=("Segoe UI", 10), bg=t["card"], fg=t["fg"], justify="left")
        self.lbl_dead.pack(anchor="w", pady=(6, 2))

    def draw_ring(self):
        c, t, e = self.ring, self.t, self.e
        c.delete("all")
        total = e.interval_sec()
        left = max(0, total - e.since_break)
        frac = left / total

        # Outer Ring: Next Break Countdown
        c.create_oval(20, 20, 220, 220, outline=t["bar"], width=14)
        col = t["warn"] if frac < 0.2 else t["accent"]
        if frac > 0.003:
            c.create_arc(20, 20, 220, 220, start=90, extent=-359.9 * frac, style="arc", outline=col, width=14)

        # Inner Ring: Daily Break Goal or Pomodoro Progress
        d = e.day()
        bg = max(1, int(e.s["break_goal"]))
        b_frac = min(1.0, d["breaks"] / bg)
        c.create_oval(40, 40, 200, 200, outline=t["card_alt"], width=6)
        if b_frac > 0.003:
            c.create_arc(40, 40, 200, 200, start=90, extent=-359.9 * b_frac, style="arc", outline=t["good"], width=6)

        c.create_text(120, 98, text=f"{int(left) // 60:02d}:{int(left) % 60:02d}", fill=t["fg"],
                      font=("Segoe UI", 28, "bold"))
        c.create_text(120, 130, text="until next break", fill=t["sub"], font=("Segoe UI", 9))

        if e.pomo_active:
            pm, ps = int(e.pomo_left) // 60, int(e.pomo_left) % 60
            c.create_text(120, 154, text=f"🍅 Pomo {pm:02d}:{ps:02d}", fill=t["gold"], font=("Segoe UI", 10, "bold"))
        elif e.in_season():
            c.create_text(120, 154, text="🔥 Due-Date Season", fill=t["warn"], font=("Segoe UI", 9, "bold"))

        if time.time() < e.dnd_until:
            c.create_text(120, 174, text=f"🔕 DND until {dt.datetime.fromtimestamp(e.dnd_until):%H:%M}",
                          fill=t["good"], font=("Segoe UI", 8, "bold"))

    def draw_water_cups(self, count, goal):
        c, t = self.water_canvas, self.t
        c.delete("all")
        n = max(goal, count, 8)
        n = min(n, 14)
        for i in range(n):
            x = i * 31 + 4
            filled = i < count
            fill_col = t["accent"] if filled else t["card_alt"]
            out_col = t["accent"] if filled else t["border"]
            # Cup trapezoid / rectangle
            c.create_polygon(x + 2, 6, x + 24, 6, x + 21, 34, x + 5, 34, fill=fill_col, outline=out_col, width=2)
            if filled:
                c.create_line(x + 6, 12, x + 20, 12, fill="white", width=1)

    def refresh_dashboard(self):
        e = self.e
        d = e.day()
        self.draw_ring()
        w_score = e.wellness_score()

        # KPI Cards
        self.kpi_labels["screen"][0].config(text=fmt_h(d["screen_sec"]))
        self.kpi_labels["screen"][1].config(text=f"Continuous: {fmt_h(e.session)}")

        self.kpi_labels["wellness"][0].config(text=f"{w_score} / 100",
                                              fg=self.t["good"] if w_score >= 75 else (self.t["gold"] if w_score >= 50 else self.t["warn"]))
        self.kpi_labels["wellness"][1].config(text=f"Posture checks: {d.get('posture_checks', 0)} today")

        self.kpi_labels["streak"][0].config(text=f"{e.streak()} Days")
        self.kpi_labels["streak"][1].config(text=f"Best record: {e.best_streak()} days")

        self.kpi_labels["xp"][0].config(text=f"Lvl {e.level()} ({e.total_points()} XP)")
        self.kpi_labels["xp"][1].config(text=e.rank_title())
        self.lbl_side_rank.config(text=f"🎖️ {e.rank_title()}\nLevel {e.level()} • {e.total_points()} XP")

        bg = int(e.s["break_goal"])
        self.lbl_breaks.config(text=f"Guided Breaks: {d['breaks']} / {bg} completed   •   Skipped: {d['skipped']}   •   Pomodoros: {d.get('pomo_count', 0)}")
        self.bar_breaks["value"] = min(100, 100 * d["breaks"] / max(1, bg))

        wg = int(e.s["water_goal"])
        self.lbl_water.config(text=f"Hydration Tracker: {d['water']} / {wg} glasses ({d['water'] * 250} ml) — Click cups to log water!")
        self.draw_water_cups(d["water"], wg)

        nd = e.next_deadlines(4)
        if nd:
            lines = []
            for days, name, occ, cat in nd:
                when = "DUE TODAY!" if days == 0 else ("Tomorrow" if days == 1 else f"in {days} days")
                icon = "🚨" if days <= 3 else "📌"
                lines.append(f"{icon}  [{cat}] {name} — {occ:%d %b %Y} ({when})")
            self.lbl_dead.config(text="\n".join(lines))
        else:
            self.lbl_dead.config(text="No upcoming deadlines. Add statutory or client filing dates in the Deadlines tab.")

        hrs = e.session / 3600
        if hrs >= 3.5:
            self.lbl_status.config(text=f"⚠️ {hrs:.1f}h continuous session! Take a break now.", fg=self.t["warn"])
        else:
            self.lbl_status.config(text="Shortcuts: Ctrl+B Break • Ctrl+M Mini-HUD • Ctrl+P Pomodoro", fg=self.t["sub"])

    # ------------------------------------------------------------ PAGE 1: FOCUS & TASKS (POMODORO)
    def build_focus(self, f):
        t = self.t
        top = tk.Frame(f, bg=t["bg"])
        top.pack(fill="both", expand=True)

        # Left Card: Pomodoro Timer
        left = self.card(top, side="left", fill="y", padx=(0, 12))
        l_in = tk.Frame(left, bg=t["card"], padx=20, pady=16)
        l_in.pack(fill="both", expand=True)

        tk.Label(l_in, text="🍅 Deep Work Pomodoro", font=("Segoe UI", 14, "bold"), bg=t["card"], fg=t["fg"]).pack()
        self.lbl_pomo_task = tk.Label(l_in, text=f"Active Task: {self.e.pomo_task}", font=("Segoe UI", 9, "italic"),
                                      bg=t["card"], fg=t["accent"], wraplength=260)
        self.lbl_pomo_task.pack(pady=(2, 8))

        self.pomo_canvas = tk.Canvas(l_in, width=220, height=220, bg=t["card"], highlightthickness=0)
        self.pomo_canvas.pack(pady=6)

        btn_row = tk.Frame(l_in, bg=t["card"])
        btn_row.pack(pady=8)
        self.btn_pomo_toggle = ttk.Button(btn_row, text="▶ Start Sprint", style="Accent.TButton", command=self.toggle_pomo)
        self.btn_pomo_toggle.pack(side="left", padx=4)
        ttk.Button(btn_row, text="↺ Reset", command=self.reset_pomo).pack(side="left", padx=4)

        preset_row = tk.Frame(l_in, bg=t["card"])
        preset_row.pack(pady=6)
        for mins, lbl in ((15, "15m Quick"), (25, "25m Classic"), (45, "45m Deep"), (60, "60m Audit")):
            ttk.Button(preset_row, text=lbl, command=lambda m=mins: self.set_pomo_duration(m)).pack(side="left", padx=2)

        self.lbl_pomo_stats = tk.Label(l_in, text="", font=("Segoe UI", 9), bg=t["card"], fg=t["sub"])
        self.lbl_pomo_stats.pack(pady=(10, 0))

        # Right Card: Task & Client Deliverable Planner
        right = self.card(top, side="left", fill="both", expand=True)
        r_in = tk.Frame(right, bg=t["card"], padx=16, pady=16)
        r_in.pack(fill="both", expand=True)

        tk.Label(r_in, text="📋 Priority Tasks & Audit Deliverables", font=("Segoe UI", 13, "bold"), bg=t["card"], fg=t["fg"]).pack(anchor="w")
        tk.Label(r_in, text="Select a task and click 'Set Active for Pomodoro' to track focused sprints against it.",
                 font=("Segoe UI", 9), bg=t["card"], fg=t["sub"]).pack(anchor="w", pady=(0, 8))

        add_bar = tk.Frame(r_in, bg=t["card"])
        add_bar.pack(fill="x", pady=(0, 8))
        self.var_new_task = tk.StringVar()
        ent = ttk.Entry(add_bar, textvariable=self.var_new_task, width=38)
        ent.pack(side="left", padx=(0, 6))
        ent.bind("<Return>", lambda e: self.add_task())
        ttk.Button(add_bar, text="➕ Add Task", style="Accent.TButton", command=self.add_task).pack(side="left")

        self.tv_tasks = ttk.Treeview(r_in, columns=("status", "title", "pomos"), show="headings", height=11)
        self.tv_tasks.heading("status", text="Status")
        self.tv_tasks.column("status", width=80, anchor="center")
        self.tv_tasks.heading("title", text="Deliverable / Task Description")
        self.tv_tasks.column("title", width=290)
        self.tv_tasks.heading("pomos", text="🍅 Sprints")
        self.tv_tasks.column("pomos", width=80, anchor="center")
        self.tv_tasks.pack(fill="both", expand=True)

        t_btns = tk.Frame(r_in, bg=t["card"])
        t_btns.pack(fill="x", pady=(10, 0))
        ttk.Button(t_btns, text="🎯 Set Active for Pomodoro", command=self.activate_task).pack(side="left", padx=(0, 6))
        ttk.Button(t_btns, text="✔ Toggle Done", style="Good.TButton", command=self.toggle_task_done).pack(side="left", padx=6)
        ttk.Button(t_btns, text="🗑 Delete", command=self.delete_task).pack(side="right")

    def draw_pomo(self):
        c, t, e = self.pomo_canvas, self.t, self.e
        c.delete("all")
        frac = e.pomo_left / max(1, e.pomo_total)
        c.create_oval(16, 16, 204, 204, outline=t["bar"], width=12)
        col = t["gold"] if e.pomo_active else t["accent"]
        if frac > 0.003:
            c.create_arc(16, 16, 204, 204, start=90, extent=-359.9 * frac, style="arc", outline=col, width=12)
        m, s = int(e.pomo_left) // 60, int(e.pomo_left) % 60
        c.create_text(110, 98, text=f"{m:02d}:{s:02d}", fill=t["fg"], font=("Segoe UI", 30, "bold"))
        status = "FOCUSING..." if e.pomo_active else "READY"
        c.create_text(110, 134, text=status, fill=col, font=("Segoe UI", 9, "bold"))

    def refresh_focus(self):
        self.draw_pomo()
        e = self.e
        d = e.day()
        self.btn_pomo_toggle.config(text="⏸ Pause Sprint" if e.pomo_active else "▶ Start Sprint")
        self.lbl_pomo_task.config(text=f"Active Task: {e.pomo_task}")
        self.lbl_pomo_stats.config(
            text=f"Today: {d.get('pomo_count', 0)} Pomodoros completed  •  {fmt_h(d.get('focus_sec', 0))} deep focus"
        )
        self.tv_tasks.delete(*self.tv_tasks.get_children())
        if not e.tasks:
            e.tasks = [
                {"title": "Client VAT & Corporate Tax Reconciliation", "done": False, "pomos": 1},
                {"title": "Review Financial Statements (IFRS 18 Disclosures)", "done": False, "pomos": 0},
                {"title": "Zoho Books / Tally Ledger Audit & Finalization", "done": False, "pomos": 0},
            ]
            e.save_tasks()
        for idx, task in enumerate(e.tasks):
            st_txt = "✔ Done" if task.get("done") else "⏳ Open"
            self.tv_tasks.insert("", "end", iid=str(idx), values=(st_txt, task["title"], f"🍅 {task.get('pomos', 0)}"))

    def set_pomo_duration(self, mins):
        self.e.pomo_active = False
        self.e.pomo_total = mins * 60
        self.e.pomo_left = mins * 60
        self.refresh_focus()

    def toggle_pomo(self):
        self.e.pomo_active = not self.e.pomo_active
        self.refresh_focus()
        self.refresh_dashboard()

    def reset_pomo(self):
        self.e.pomo_active = False
        self.e.pomo_left = self.e.pomo_total
        self.refresh_focus()

    def add_task(self):
        txt = self.var_new_task.get().strip()
        if txt:
            self.e.tasks.insert(0, {"title": txt, "done": False, "pomos": 0})
            self.e.save_tasks()
            self.var_new_task.set("")
            self.refresh_focus()

    def activate_task(self):
        sel = self.tv_tasks.selection()
        if sel:
            idx = int(sel[0])
            self.e.pomo_task = self.e.tasks[idx]["title"]
            self.refresh_focus()

    def toggle_task_done(self):
        sel = self.tv_tasks.selection()
        if sel:
            idx = int(sel[0])
            self.e.tasks[idx]["done"] = not self.e.tasks[idx].get("done", False)
            self.e.save_tasks()
            self.refresh_focus()

    def delete_task(self):
        sel = self.tv_tasks.selection()
        if sel:
            del self.e.tasks[int(sel[0])]
            self.e.save_tasks()
            self.refresh_focus()

    # ------------------------------------------------------------ PAGE 2: ROUTINES & CUSTOM BUILDER
    def build_routines(self, f):
        t = self.t
        hdr = tk.Frame(f, bg=t["bg"])
        hdr.pack(fill="x", pady=(0, 8))
        ttk.Label(hdr, text="🧘 Exercise & Ergonomic Routine Library", style="H.TLabel").pack(side="left")
        ttk.Button(hdr, text="➕ Create Custom Routine", style="Accent.TButton", command=self.new_routine_dialog).pack(side="right")

        body = tk.Frame(f, bg=t["bg"])
        body.pack(fill="both", expand=True)
        self.lb_act = tk.Listbox(body, width=34, height=16, font=("Segoe UI", 11), bg=t["card"], fg=t["fg"],
                                 selectbackground=t["accent"], selectforeground="white",
                                 highlightthickness=1, highlightbackground=t["border"], exportselection=False)
        self.lb_act.pack(side="left", fill="y")
        self.lb_act.bind("<<ListboxSelect>>", lambda ev: self.show_act_detail())

        right = self.card(body, side="left", fill="both", expand=True, padx=(12, 0))
        r_in = tk.Frame(right, bg=t["card"], padx=18, pady=16)
        r_in.pack(fill="both", expand=True)

        self.act_title = tk.Label(r_in, font=("Segoe UI", 15, "bold"), bg=t["card"], fg=t["fg"])
        self.act_title.pack(anchor="w")
        self.act_why = tk.Label(r_in, font=("Segoe UI", 10), bg=t["card"], fg=t["accent"], wraplength=520, justify="left")
        self.act_why.pack(anchor="w", pady=(2, 10))
        self.act_steps = tk.Label(r_in, font=("Segoe UI", 10), bg=t["card"], fg=t["fg"], justify="left", wraplength=520)
        self.act_steps.pack(anchor="w", pady=6)

        row = tk.Frame(r_in, bg=t["card"])
        row.pack(anchor="w", pady=14)
        ttk.Button(row, text="▶ Start This Routine Now", style="Accent.TButton", command=self.start_listed).pack(side="left")
        ttk.Button(row, text="✔/✘ Toggle Auto-Rotation", command=self.toggle_act).pack(side="left", padx=8)
        self.fill_acts()

    def fill_acts(self, keep=0):
        self.lb_act.delete(0, "end")
        for a in self.e.acts:
            on = a["name"] not in self.e.s["disabled_activities"]
            cat = a.get("category", "General")
            self.lb_act.insert("end", f"{'✔' if on else '✘'}  [{cat}] {a['name']}")
        if self.e.acts:
            self.lb_act.selection_set(min(keep, len(self.e.acts) - 1))
            self.show_act_detail()

    def sel_act(self):
        s = self.lb_act.curselection()
        return self.e.acts[s[0]] if s else None

    def show_act_detail(self):
        a = self.sel_act()
        if not a:
            return
        total = sum(s["sec"] for s in a["steps"])
        self.act_title.config(text=f"{a['name']}  ({total // 60}m {total % 60:02d}s)")
        self.act_why.config(text=f"Why it helps: {a.get('why', 'Restores circulation and posture.')}")
        lines = []
        for i, s in enumerate(a["steps"]):
            anim_tag = s.get("anim", "ring").upper()
            lines.append(f"  Step {i + 1}:  {s['t']}   •   {s['sec']}s  [{anim_tag}]")
        self.act_steps.config(text="\n\n".join(lines))

    def start_listed(self):
        a = self.sel_act()
        if a:
            self.show_break(manual=True, activity=a)

    def toggle_act(self):
        a = self.sel_act()
        if not a:
            return
        dis = self.e.s["disabled_activities"]
        if a["name"] in dis:
            dis.remove(a["name"])
        else:
            dis.append(a["name"])
        self.e.save_settings()
        self.fill_acts(self.lb_act.curselection()[0])

    def new_routine_dialog(self):
        w = tk.Toplevel(self.root)
        w.title("Create Custom Exercise Routine")
        w.configure(bg=self.t["bg"])
        w.geometry("500x440")
        w.transient(self.root)
        w.grab_set()

        name_v = tk.StringVar()
        cat_v = tk.StringVar(value="Strength")
        why_v = tk.StringVar(value="Custom desk mobility & strength routine.")

        frm = ttk.Frame(w, padding=14)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Routine Name (e.g. Afternoon Pushup & Core Set):").pack(anchor="w")
        ttk.Entry(frm, textvariable=name_v, width=54).pack(anchor="w", pady=(2, 8))

        ttk.Label(frm, text="Category:").pack(anchor="w")
        ttk.Combobox(frm, textvariable=cat_v, values=["Eyes", "Stretch", "Posture", "Breathing", "Strength", "Hydration"], width=20).pack(anchor="w", pady=(2, 8))

        ttk.Label(frm, text="Health Benefit / Why:").pack(anchor="w")
        ttk.Entry(frm, textvariable=why_v, width=54).pack(anchor="w", pady=(2, 8))

        ttk.Label(frm, text="Steps (one per line, format: Step description | seconds | anim):\nAnimations: ring, breathe, box_breathe, figure8, far, posture, rep_counter").pack(anchor="w")
        txt = tk.Text(frm, height=7, width=54, font=("Segoe UI", 9))
        txt.insert("1.0", "15 Desk Pushups | 35 | rep_counter\nShoulder & Chest Stretch | 20 | posture\nDeep Recovery Breathing | 30 | breathe")
        txt.pack(pady=6)

        def save_custom():
            n = name_v.get().strip()
            if not n:
                return messagebox.showwarning("Missing", "Enter a routine name.", parent=w)
            steps = []
            for line in txt.get("1.0", "end").splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split("|")]
                t_str = parts[0]
                sec_val = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
                anim_val = parts[2] if len(parts) > 2 else "ring"
                steps.append({"t": t_str, "sec": max(5, sec_val), "anim": anim_val})
            if not steps:
                return
            self.e.acts.append({"name": n, "category": cat_v.get().strip() or "Custom", "why": why_v.get().strip(), "steps": steps})
            self.e.save_acts()
            w.destroy()
            self.build()
            self.select_page(2)

        ttk.Button(frm, text="💾 Save Routine", style="Accent.TButton", command=save_custom).pack(anchor="e", pady=6)

    # ------------------------------------------------------------ PAGE 3: DEADLINES
    def build_deadlines(self, f):
        ttk.Label(f, text="📅 Statutory & Client Filing Calendar (Auto-Activates Due-Date Season)",
                  style="H.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, text="When any deadline is within your threshold days, BreakBuddy automatically switches to shorter, high-care break intervals.",
                  foreground=self.t["sub"]).pack(anchor="w", pady=(0, 8))

        self.tv = ttk.Treeview(f, columns=("cat", "name", "date", "left", "kind"), show="headings", height=13)
        for col, w, txt in (
            ("cat", 120, "Category"),
            ("name", 310, "Compliance / Deliverable"),
            ("date", 120, "Next Due Date"),
            ("left", 100, "Status"),
            ("kind", 140, "Frequency")
        ):
            self.tv.heading(col, text=txt)
            self.tv.column(col, width=w)
        self.tv.pack(fill="both", expand=True)

        row = ttk.Frame(f)
        row.pack(fill="x", pady=10)
        ttk.Button(row, text="➕ Add Custom Deadline", style="Accent.TButton", command=self.add_deadline).pack(side="left")
        ttk.Button(row, text="🇦🇪 Add UAE VAT/CT Pack", command=self.add_uae_pack).pack(side="left", padx=8)
        ttk.Button(row, text="🇮🇳 Add India GST/TDS Pack", command=self.add_india_pack).pack(side="left", padx=4)
        ttk.Button(row, text="🗑 Delete Selected", command=self.del_deadline).pack(side="right")

    def fill_deadlines(self):
        from .engine import occurrence
        self.tv.delete(*self.tv.get_children())
        today = dt.date.today()
        for i, d in enumerate(self.e.deadlines):
            occ = occurrence(d, today)
            kind = f"Monthly (Day {d['monthly_day']})" if d.get("monthly_day") else "One-time"
            days = (occ - today).days if occ else -1
            st_txt = f"{days} days left" if days > 0 else ("DUE TODAY!" if days == 0 else "Passed")
            self.tv.insert("", "end", iid=str(i), values=(
                d.get("category", "General"),
                d["name"],
                f"{occ:%d %b %Y}" if occ else "Passed",
                st_txt,
                kind
            ))

    def add_uae_pack(self):
        presets = [
            {"name": "UAE VAT Return Filing (FTA)", "monthly_day": 28, "category": "UAE VAT"},
            {"name": "WPS Payroll & Salary Transfer", "monthly_day": 28, "category": "UAE Compliance"},
            {"name": "Monthly Client Book Close & MIS", "monthly_day": 5, "category": "Accounting"},
        ]
        existing = {d["name"] for d in self.e.deadlines}
        for p in presets:
            if p["name"] not in existing:
                self.e.deadlines.append(p)
        self.e.save_deadlines()
        self.fill_deadlines()

    def add_india_pack(self):
        presets = [
            {"name": "TDS / TCS Deposit", "monthly_day": 7, "category": "India Tax"},
            {"name": "GSTR-1 Monthly Return", "monthly_day": 11, "category": "India GST"},
            {"name": "PF & ESI Statutory Payment", "monthly_day": 15, "category": "Payroll"},
            {"name": "GSTR-3B Monthly Return", "monthly_day": 20, "category": "India GST"},
        ]
        existing = {d["name"] for d in self.e.deadlines}
        for p in presets:
            if p["name"] not in existing:
                self.e.deadlines.append(p)
        self.e.save_deadlines()
        self.fill_deadlines()

    def add_deadline(self):
        w = tk.Toplevel(self.root)
        w.title("Add Compliance or Filing Deadline")
        w.configure(bg=self.t["bg"])
        w.transient(self.root)
        w.grab_set()
        name, cat, kind, val = tk.StringVar(), tk.StringVar(value="Tax / Audit"), tk.StringVar(value="monthly"), tk.StringVar()
        ttk.Label(w, text="Deliverable / Filing Name:").grid(row=0, column=0, padx=12, pady=(12, 2), sticky="w")
        ttk.Entry(w, textvariable=name, width=42).grid(row=1, column=0, padx=12, columnspan=2, sticky="w")
        ttk.Label(w, text="Category (e.g. UAE VAT, India GST, Audit):").grid(row=2, column=0, padx=12, pady=(8, 2), sticky="w")
        ttk.Entry(w, textvariable=cat, width=25).grid(row=3, column=0, padx=12, sticky="w")
        ttk.Radiobutton(w, text="Monthly recurring day (1-31)", variable=kind, value="monthly").grid(row=4, column=0, sticky="w", padx=12, pady=(8, 0))
        ttk.Radiobutton(w, text="Specific date (YYYY-MM-DD)", variable=kind, value="date").grid(row=5, column=0, sticky="w", padx=12)
        ttk.Entry(w, textvariable=val, width=20).grid(row=6, column=0, sticky="w", padx=12, pady=6)

        def ok():
            n, v, c_str = name.get().strip(), val.get().strip(), cat.get().strip() or "General"
            if not n:
                return messagebox.showwarning("Missing", "Please enter a name.", parent=w)
            try:
                if kind.get() == "monthly":
                    day = int(v)
                    assert 1 <= day <= 31
                    item = {"name": n, "monthly_day": day, "category": c_str}
                else:
                    dt.date.fromisoformat(v)
                    item = {"name": n, "date": v, "category": c_str}
            except Exception:
                return messagebox.showwarning("Invalid", "Enter a day 1-31, or a date like 2026-11-30.", parent=w)
            self.e.deadlines.append(item)
            self.e.save_deadlines()
            self.fill_deadlines()
            w.destroy()

        ttk.Button(w, text="💾 Save Deadline", style="Accent.TButton", command=ok).grid(row=7, column=0, padx=12, pady=12, sticky="w")

    def del_deadline(self):
        sel = self.tv.selection()
        if sel:
            del self.e.deadlines[int(sel[0])]
            self.e.save_deadlines()
            self.fill_deadlines()

    # ------------------------------------------------------------ PAGE 4: ANALYTICS & PROGRESS
    def build_progress(self, f):
        t = self.t
        hdr = tk.Frame(f, bg=t["bg"])
        hdr.pack(fill="x", pady=(0, 6))
        ttk.Label(hdr, text="📊 7-Day Screen Time, Wellness Score & Activity Heatmap", style="H.TLabel").pack(side="left")
        ttk.Button(hdr, text="📥 Export CSV Report", style="Accent.TButton", command=self.export_csv_dialog).pack(side="right")

        self.chart = tk.Canvas(f, width=760, height=220, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        self.chart.pack(fill="x", pady=(0, 10))

        mid = tk.Frame(f, bg=t["bg"])
        mid.pack(fill="x", pady=(0, 8))
        self.lbl_mood = ttk.Label(mid, style="H.TLabel")
        self.lbl_mood.pack(side="left")
        self.lbl_heat_info = ttk.Label(mid, text="28-Day Consistency Heatmap (Darker = More Breaks)", foreground=t["sub"])
        self.lbl_heat_info.pack(side="right")

        # 28-Day Heatmap Canvas
        self.heat_canvas = tk.Canvas(f, width=760, height=54, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        self.heat_canvas.pack(fill="x", pady=(0, 10))

        ttk.Label(f, text="🏅 Achievements & Ergonomic Badges (12 Total)", style="H.TLabel").pack(anchor="w", pady=(2, 6))
        self.badge_frame = tk.Frame(f, bg=t["bg"])
        self.badge_frame.pack(fill="both", expand=True)

    def draw_chart(self):
        c, t, e = self.chart, self.t, self.e
        c.delete("all")
        today = dt.date.today()
        days = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
        data = [e.all.get(d.isoformat(), {}) for d in days]
        vals = [x.get("screen_sec", 0) / 3600 for x in data]
        mx = max(max(vals), 1)
        base, bw, gap, x0 = 165, 64, 38, 42
        c.create_line(x0 - 10, base, x0 + 7 * (bw + gap), base, fill=t["bar"], width=2)
        for i, (d, v, x) in enumerate(zip(days, vals, data)):
            xx = x0 + i * (bw + gap)
            h = (base - 36) * v / mx
            col = t["warn"] if v >= 9.5 else t["accent"]
            c.create_rectangle(xx, base - h, xx + bw, base, fill=col, outline="")
            c.create_text(xx + bw / 2, base - h - 11, text=f"{v:.1f}h", fill=t["fg"], font=("Segoe UI", 9, "bold"))
            c.create_text(xx + bw / 2, base + 14, text=d.strftime("%a %d"), fill=t["sub"], font=("Segoe UI", 9))
            c.create_text(xx + bw / 2, base + 32,
                          text=f"☕{x.get('breaks', 0)}  🥤{x.get('water', 0)}  🍅{x.get('pomo_count', 0)}",
                          fill=t["good"], font=("Segoe UI", 8, "bold"))

    def draw_heatmap(self):
        c, t, e = self.heat_canvas, self.t, self.e
        c.delete("all")
        today = dt.date.today()
        g = max(1, int(e.s["break_goal"]))
        for i in range(28):
            d = today - dt.timedelta(days=27 - i)
            brks = e.all.get(d.isoformat(), {}).get("breaks", 0)
            if brks == 0:
                col = t["card_alt"]
            elif brks < g // 2:
                col = "#1d4ed8"
            elif brks < g:
                col = t["accent"]
            else:
                col = t["good"]
            x = 16 + i * 26
            c.create_rectangle(x, 8, x + 20, 28, fill=col, outline=t["border"])
            c.create_text(x + 10, 40, text=d.strftime("%d"), fill=t["sub"], font=("Segoe UI", 7))

    def refresh_progress(self):
        self.draw_chart()
        self.draw_heatmap()
        d = self.e.day()
        if d["moods"]:
            avg = sum(d["moods"]) / len(d["moods"])
            emo = ["😫", "😐", "🙂", "😄"][min(3, max(0, round(avg) - 1))]
            self.lbl_mood.config(text=f"Post-Break Energy Today: {emo} ({avg:.1f} / 4.0)  •  Wellness Score: {self.e.wellness_score()}/100")
        else:
            self.lbl_mood.config(text=f"Wellness Score Today: {self.e.wellness_score()}/100  •  Complete a break to log energy mood")

        for w in self.badge_frame.winfo_children():
            w.destroy()
        for i, (emo, name, desc, ok) in enumerate(self.e.badges()):
            fr = tk.Frame(self.badge_frame, bg=self.t["card"] if ok else self.t["card_alt"],
                          highlightthickness=1, highlightbackground=self.t["good"] if ok else self.t["border"], padx=6, pady=4)
            fr.grid(row=i // 6, column=i % 6, padx=4, pady=4, sticky="nsew")
            tk.Label(fr, text=emo if ok else "🔒", bg=fr["bg"], fg=self.t["fg"], font=("Segoe UI Emoji", 18)).pack(pady=(2, 0))
            tk.Label(fr, text=name, bg=fr["bg"], fg=self.t["fg"] if ok else self.t["sub"], font=("Segoe UI", 8, "bold")).pack()
            tk.Label(fr, text=desc, bg=fr["bg"], fg=self.t["sub"], font=("Segoe UI", 7), wraplength=110, justify="center").pack(pady=(0, 2))

    def export_csv_dialog(self):
        fp = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Wellness & Productivity Report",
            defaultextension=".csv",
            initialfile=f"BreakBuddy_Wellness_Report_{dt.date.today().isoformat()}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if fp:
            self.e.export_csv(fp)
            messagebox.showinfo("Export Complete", f"Wellness & Focus report exported to:\n{fp}")

    # ------------------------------------------------------------ PAGE 5: CHARACTERS
    def build_characters(self, f):
        t = self.t
        body = tk.Frame(f, bg=t["bg"])
        body.pack(fill="both", expand=True)
        self.lb_char = tk.Listbox(body, width=28, height=16, font=("Segoe UI", 11), bg=t["card"], fg=t["fg"],
                                  selectbackground=t["accent"], selectforeground="white",
                                  highlightthickness=1, highlightbackground=t["border"], exportselection=False)
        self.lb_char.pack(side="left", fill="y")
        self.lb_char.bind("<<ListboxSelect>>", lambda ev: self.show_char())

        right = self.card(body, side="left", fill="both", expand=True, padx=(12, 0))
        r_in = tk.Frame(right, bg=t["card"], padx=18, pady=16)
        r_in.pack(fill="both", expand=True)

        self.ch_av = tk.Label(r_in, font=("Segoe UI Emoji", 44), bg=t["card"], fg=t["fg"])
        self.ch_av.pack(pady=(4, 0))
        self.ch_name = tk.Label(r_in, font=("Segoe UI", 15, "bold"), bg=t["card"], fg=t["fg"])
        self.ch_name.pack()
        self.ch_line = tk.Label(r_in, wraplength=460, font=("Segoe UI", 11, "italic"), justify="center", bg=t["card"], fg=t["accent"])
        self.ch_line.pack(padx=12, pady=10)

        row = tk.Frame(r_in, bg=t["card"])
        row.pack()
        ttk.Button(row, text="🔀 Another Quote", command=self.show_char).pack(side="left", padx=4)
        ttk.Button(row, text="▶ Preview Break with Character", style="Accent.TButton", command=self.preview_char).pack(side="left", padx=4)

        tk.Label(r_in, text="Add your own custom reminder line (English, Manglish, Tanglish):", bg=t["card"], fg=t["sub"]).pack(anchor="w", pady=(18, 4))
        self.new_line = tk.StringVar()
        ttk.Entry(r_in, textvariable=self.new_line, width=54).pack(anchor="w")
        b_row = tk.Frame(r_in, bg=t["card"])
        b_row.pack(anchor="w", pady=8)
        ttk.Button(b_row, text="➕ Save Line to Character", command=self.add_line).pack(side="left", padx=(0, 8))
        ttk.Button(b_row, text="🆕 Create New Character", command=self.new_character).pack(side="left")
        self.fill_chars()

    def fill_chars(self, keep=0):
        self.lb_char.delete(0, "end")
        for c in self.e.chars:
            self.lb_char.insert("end", f"{c.get('avatar', '🙂')}  {c['name']}")
        if self.e.chars:
            self.lb_char.selection_set(min(keep, len(self.e.chars) - 1))
            self.show_char()

    def sel_char(self):
        s = self.lb_char.curselection()
        return self.e.chars[s[0]] if s else None

    def show_char(self):
        c = self.sel_char()
        if c:
            self.ch_av.config(text=c.get("avatar", "🙂"))
            self.ch_name.config(text=c["name"])
            self.ch_line.config(text=f"“{self.e.line(c, 'break_lines')}”")

    def preview_char(self):
        c = self.sel_char()
        if c:
            self.show_break(manual=True, char=c)

    def add_line(self):
        c, txt = self.sel_char(), self.new_line.get().strip()
        if c and txt:
            c.setdefault("break_lines", []).append(txt)
            self.e.save_chars()
            self.new_line.set("")
            self.ch_line.config(text=f"“{txt}”   ✔ Saved!")

    def new_character(self):
        w = tk.Toplevel(self.root)
        w.title("Create New Companion Character")
        w.configure(bg=self.t["bg"])
        w.transient(self.root)
        w.grab_set()
        n, a, l = tk.StringVar(), tk.StringVar(value="😎"), tk.StringVar()
        for r, (lab, var) in enumerate((("Character Name:", n), ("Emoji Avatar:", a), ("Opening Break Line:", l))):
            ttk.Label(w, text=lab).grid(row=r, column=0, padx=12, pady=8, sticky="w")
            ttk.Entry(w, textvariable=var, width=40).grid(row=r, column=1, padx=12)

        def ok():
            if not n.get().strip() or not l.get().strip():
                return
            self.e.chars.append({
                "name": n.get().strip(), "avatar": a.get().strip() or "😎", "image": "",
                "break_lines": [l.get().strip()], "water_lines": [l.get().strip()],
                "meal_lines": [l.get().strip()], "posture_lines": ["Sit tall and relax your shoulders!"],
                "done_lines": ["Great job! Back to work."]
            })
            self.e.save_chars()
            w.destroy()
            self.build()
            self.select_page(5)

        ttk.Button(w, text="Create Character", style="Accent.TButton", command=ok).grid(row=3, column=1, pady=12, sticky="e", padx=12)

    # ------------------------------------------------------------ PAGE 6: SETTINGS
    def build_settings(self, f):
        s = self.e.s
        self.vars = {}
        card = self.card(f, fill="both", expand=True)
        g = tk.Frame(card, bg=self.t["card"], padx=20, pady=16)
        g.pack(fill="both", expand=True)

        spin = [
            ("Standard break interval (min)", "interval_min", 1, 240),
            ("Due-Date Season interval (min)", "season_interval_min", 1, 240),
            ("Auto-Season trigger (days before due date)", "auto_season_days", 0, 30),
            ("Water reminder every (min)", "water_every_min", 10, 240),
            ("Posture radar check every (min)", "posture_every_min", 10, 180),
            ("Daily water goal (glasses)", "water_goal", 1, 20),
            ("Daily guided break goal", "break_goal", 1, 30),
            ("Count as idle after (sec)", "idle_limit_sec", 30, 900),
        ]
        r = 0
        for lab, key, lo, hi in spin:
            tk.Label(g, text=lab, bg=self.t["card"], fg=self.t["fg"]).grid(row=r, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=str(s[key]))
            ttk.Spinbox(g, from_=lo, to=hi, width=8, textvariable=v).grid(row=r, column=1, padx=12, sticky="w")
            self.vars[key] = ("int", v)
            r += 1

        txt = [("Work day starts (HH:MM)", "work_start"), ("Work day ends (HH:MM)", "work_end")]
        for lab, key in txt:
            tk.Label(g, text=lab, bg=self.t["card"], fg=self.t["fg"]).grid(row=r, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=s[key])
            ttk.Entry(g, width=10, textvariable=v).grid(row=r, column=1, padx=12, sticky="w")
            self.vars[key] = ("time", v)
            r += 1

        for meal, hhmm in s["meals"].items():
            tk.Label(g, text=f"{meal} reminder (HH:MM)", bg=self.t["card"], fg=self.t["fg"]).grid(row=r, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=hhmm)
            ttk.Entry(g, width=10, textvariable=v).grid(row=r, column=1, padx=12, sticky="w")
            self.vars["meal:" + meal] = ("time", v)
            r += 1

        tk.Label(g, text="Visual Theme Palette", bg=self.t["card"], fg=self.t["fg"]).grid(row=r, column=0, sticky="w", pady=4)
        tv = tk.StringVar(value=s["theme"])
        ttk.Combobox(g, state="readonly", width=14, values=list(THEMES.keys()), textvariable=tv).grid(row=r, column=1, padx=12, sticky="w")
        self.vars["theme"] = ("str", tv)

        c = tk.Frame(g, bg=self.t["card"])
        c.grid(row=0, column=2, rowspan=15, padx=36, sticky="n")
        checks = [
            ("Force Due-Date Season mode (always on)", "season_manual"),
            ("Enable Posture & Spine Radar checks", "posture_on"),
            ("Enable 20-20-20 Eye Micro-Notifications", "eye_20_on"),
            ("Play notification chimes", "sound"),
            ("Read reminders aloud (TTS voice)", "voice"),
            ("Only remind during work hours", "enforce_work_hours"),
            ("Meal time reminders (Lunch/Dinner)", "meals_on"),
            ("Keep running in system tray on close", "use_tray"),
        ]
        for lab, key in checks:
            v = tk.BooleanVar(value=bool(s[key]))
            ttk.Checkbutton(c, text=lab, variable=v).pack(anchor="w", pady=4)
            self.vars[key] = ("bool", v)

        self.var_auto = tk.BooleanVar(value=autostart_enabled())
        cb = ttk.Checkbutton(c, text="Launch automatically with Windows", variable=self.var_auto)
        cb.pack(anchor="w", pady=4)
        if not WIN:
            cb.state(["disabled"])

        ttk.Button(c, text="💾 Save & Apply Settings", style="Accent.TButton", command=self.save_settings).pack(anchor="w", pady=(16, 6))
        self.lbl_saved = tk.Label(c, text="", bg=self.t["card"], fg=self.t["good"], font=("Segoe UI", 9, "bold"))
        self.lbl_saved.pack(anchor="w")

    def save_settings(self):
        s = self.e.s
        old_theme = s["theme"]
        try:
            for key, (kind, v) in self.vars.items():
                val = v.get()
                if kind == "int":
                    s[key] = max(0, int(float(val)))
                elif kind == "time":
                    dt.datetime.strptime(val.strip(), "%H:%M")
                    if key.startswith("meal:"):
                        s["meals"][key[5:]] = val.strip()
                    else:
                        s[key] = val.strip()
                else:
                    s[key] = val
            set_autostart(self.var_auto.get())
        except Exception:
            return messagebox.showwarning("Check values", "Please enter valid numbers and HH:MM times (e.g. 13:30).")
        self.e.save_settings()
        if s["theme"] != old_theme:
            self.t = THEMES.get(s["theme"], THEMES["dark"])
            self.build()
            self.select_page(6)
        else:
            self.lbl_saved.config(text="✔ Settings Saved!")
            self.refresh_all()

    # ------------------------------------------------------------ NEW: App usage / Wellness Lab
    def build_screen_time(self, f):
        self.screen_page = ScreenTimePage(self, f)

    def build_wellness_lab(self, f):
        self.lab = WellnessLab(self, f)

    def build_india_news(self, f):
        self.news_page = IndiaNewsPage(self, f)

    def toggle_day_night(self):
        self.e.s["theme"] = "light" if self.e.s.get("theme") != "light" else "dark"
        self.e.save_settings()
        self.t = THEMES[self.e.s["theme"]]
        # Close the HUD to avoid leaving a mismatched floating theme behind.
        if self.hud and self.hud.winfo_exists():
            self.hud.destroy()
            self.hud = None
        self.build()

    def open_scratchpad(self):
        self.select_page(8)
        self.lab.notebook.select(0)
        self.lab.next_text.focus_set()

    def open_meditation(self):
        self.select_page(8)
        self.lab.notebook.select(2)

    # ------------------------------------------------------------ actions & triggers
    def toggle_hud(self):
        if self.hud and self.hud.winfo_exists():
            self.hud.destroy()
            self.hud = None
        else:
            self.hud = MiniHUD(self)
            self.hud.update_hud()

    def save_choice(self):
        self.e.s["activity"] = self.cb_act.get()
        self.e.s["character"] = self.cb_char.get()
        self.e.save_settings()

    def start_selected(self):
        self.save_choice()
        self.show_break(manual=True, activity=self.e.pick_act(self.cb_act.get()))

    def set_dnd(self):
        v = self.cb_dnd.get()
        self.e.dnd_until = 0 if v == "Off" else time.time() + int(v.split()[0]) * 60
        self.refresh_dashboard()

    def drink(self):
        before = self.e.earned_names()
        self.e.record_water()
        new = self.e.earned_names() - before
        if new:
            Toast(self, "New Badge Unlocked!", ", ".join(sorted(new)), avatar="🏅", timeout=8)
        self.refresh_all()

    def manual_posture(self):
        self.e.record_posture()
        Toast(self, "Posture Checked! +2 XP", "Shoulders relaxed, spine aligned, jaw unclenched.", avatar="🪑", timeout=6)
        self.refresh_all()

    def quick_eye_rest(self):
        act = self.e.pick_act("20-20-20 Eye Rest")
        self.show_break(manual=True, activity=act)

    def show_break(self, manual=False, activity=None, char=None):
        if self.popup:
            self.popup.lift()
            return
        e = self.e
        ch = char or e.pick_char(e.s["character"])
        act = activity or e.pick_act(e.s["activity"])
        self.popup = GuidedBreak(self, ch, act, e.line(ch, "break_lines", act), manual)

    def on_break_done(self, act, mood):
        before = self.e.earned_names()
        self.e.record_break(act, mood)
        if act.get("water"):
            self.e.record_water()
        new = self.e.earned_names() - before
        if new:
            Toast(self, "New Badge Unlocked!", ", ".join(sorted(new)), avatar="🏅", timeout=8)
        self.refresh_all()

    def on_break_snooze(self):
        self.snooze_until = time.time() + 300

    def on_break_skip(self):
        self.e.record_skip()
        self.refresh_all()

    def toast_water(self):
        e = self.e
        ch = e.pick_char(e.s["character"])
        e.since_water = 0

        def later():
            e.since_water = max(0, int(e.s["water_every_min"]) * 60 - 600)

        Toast(self, "Hydration Check 💧", e.line(ch, "water_lines"),
              buttons=[("🥤 I Drank (+3 XP)", self.drink), ("Snooze 10m", later)], avatar=ch.get("avatar", "🙂"))

    def toast_posture(self):
        e = self.e
        ch = e.pick_char(e.s["character"])
        e.since_posture = 0
        Toast(self, "Posture Radar 🪑", e.line(ch, "posture_lines"),
              buttons=[("✔ Fixed Posture (+2 XP)", self.manual_posture)], avatar=ch.get("avatar", "🪑"), timeout=18)

    def toast_eye20(self):
        e = self.e
        e.since_eye20 = 0
        Toast(self, "20-20-20 Eye Care 👁️", "Look 20 feet away for 20 seconds and blink slowly 10 times.",
              buttons=[("▶ Start Guided Eye Rest", self.quick_eye_rest)], avatar="👁️", timeout=18)

    def toast_meal(self, name):
        ch = self.e.pick_char(self.e.s["character"])
        Toast(self, f"{name} Time 🍽️", self.e.line(ch, "meal_lines"), buttons=[("On my way!", lambda: None)],
              avatar=ch.get("avatar", "🙂"), timeout=40)

    # ------------------------------------------------------------ main loop
    def check_triggers(self):
        e = self.e
        if e.pomo_active and e.pomo_left <= 0:
            e.pomo_active = False
            e.pomo_left = e.pomo_total
            e.record_pomo()
            Toast(self, "🍅 Pomodoro Complete! +25 XP",
                  f"Great sprint on '{e.pomo_task}'! Ready for a 5-minute restorative break?",
                  buttons=[("▶ Start Break", lambda: self.show_break(manual=True))], avatar="🍅", timeout=30)
            self.refresh_all()
            return

        if self.popup or time.time() < e.dnd_until:
            return
        if e.s["enforce_work_hours"] and not e.in_work_hours():
            return
        if e.s["meals_on"]:
            now = dt.datetime.now().strftime("%H:%M")
            for name, hhmm in e.s["meals"].items():
                if hhmm == now and name not in e.fired_meals:
                    e.fired_meals.add(name)
                    return self.toast_meal(name)
        if e.since_break >= e.interval_sec() and time.time() >= self.snooze_until:
            return self.show_break()
        if e.since_water >= int(e.s["water_every_min"]) * 60:
            return self.toast_water()
        if e.s.get("posture_on", True) and e.since_posture >= int(e.s.get("posture_every_min", 25)) * 60:
            return self.toast_posture()
        if e.s.get("eye_20_on", False) and e.since_eye20 >= int(e.s.get("eye_20_every_min", 20)) * 60:
            return self.toast_eye20()

    def process_queue(self):
        while True:
            try:
                cmd = self.q.get_nowait()
            except queue.Empty:
                return
            if cmd == "open":
                self.root.deiconify()
                self.root.lift()
            elif cmd == "hud":
                self.toggle_hud()
            elif cmd == "break":
                self.show_break(manual=True)
            elif cmd == "pomo":
                self.e.pomo_active = True
                self.refresh_all()
            elif cmd == "water":
                self.drink()
            elif cmd == "dnd30":
                self.e.dnd_until = time.time() + 1800
            elif cmd == "quit":
                return self.quit()

    def refresh_all(self):
        try:
            self.refresh_dashboard()
            self.refresh_focus()
            self.fill_deadlines()
            self.refresh_progress()
            if self.hud and self.hud.winfo_exists():
                self.hud.update_hud()
        except Exception:
            traceback.print_exc()

    def tick(self):
        if self._shutting_down:
            return
        try:
            self.process_queue()
            if self._shutting_down:
                return
            self.e.tick()
            self.check_triggers()
            self.refresh_dashboard()
            if self.cur_page == 1:
                self.draw_pomo()
            if self.hud and self.hud.winfo_exists():
                self.hud.update_hud()
            if self.e.ticks % 30 == 0:
                self.refresh_progress()
            if self.cur_page == 7 and self.e.ticks % 3 == 0:
                self.screen_page.refresh()
            if self.cur_page == 9 and self.e.ticks % 3 == 0:
                self.news_page.tick()
            self.lab.tick()
        except Exception:
            traceback.print_exc()
        finally:
            if not self._shutting_down:
                self._tick_job = self.root.after(1000, self.tick)

    def on_close(self):
        if self._shutting_down:
            return
        if self.tray.ok:
            self.root.withdraw()
        else:
            self.root.iconify()

    def quit(self):
        """Explicit Stop & Exit always terminates, even with tray mode enabled."""
        if self._shutting_down:
            return
        self._shutting_down = True
        if self._tick_job is not None:
            try:
                self.root.after_cancel(self._tick_job)
            except tk.TclError:
                pass
            self._tick_job = None
        self.news.stop()
        try:
            if getattr(self, "lab", None):
                self.lab.flush()
            self.e.monitor.save()
            self.e.save_stats()
            self.e.save_settings()
        finally:
            self.tray.stop()
            self.root.destroy()

    def run(self):
        self.root.mainloop()
