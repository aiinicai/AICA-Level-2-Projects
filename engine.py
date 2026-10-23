import calendar
import csv
import datetime as dt
import random
import subprocess
import sys
import time
from pathlib import Path

from .config import DATA, DEFAULTS, USER, load_json, save_json
from .screen_time import ScreenTimeMonitor

WIN = sys.platform.startswith("win")
MAC = sys.platform == "darwin"


# ------------------------------------------------------------ system helpers
def idle_seconds():
    """Seconds since last keyboard/mouse input across Windows, macOS, and Linux."""
    if WIN:
        try:
            import ctypes

            class LII(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            i = LII()
            i.cbSize = ctypes.sizeof(LII)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(i))
            return (ctypes.windll.kernel32.GetTickCount() - i.dwTime) / 1000.0
        except Exception:
            return 0
    elif MAC:
        try:
            out = subprocess.check_output(
                ["ioreg", "-c", "IOHIDSystem"], stderr=subprocess.DEVNULL, timeout=1
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if "HIDIdleTime" in line:
                    ns = int(line.split("=")[-1].strip())
                    return ns / 1_000_000_000.0
        except Exception:
            return 0
    else:
        try:
            out = subprocess.check_output(
                ["xprintidle"], stderr=subprocess.DEVNULL, timeout=1
            ).decode("utf-8", errors="ignore")
            return int(out.strip()) / 1000.0
        except Exception:
            return 0
    return 0


def beep(root):
    try:
        if WIN:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            root.bell()
    except Exception:
        pass


def speak(text):
    text = "".join(ch for ch in text if ch not in "\"'`$;&|<>")
    try:
        if WIN:
            ps = ("Add-Type -AssemblyName System.Speech; "
                  f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')")
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
        elif MAC:
            subprocess.Popen(["say", text])
        else:
            subprocess.Popen(["espeak", text])
    except Exception:
        pass


def occurrence(d, today):
    """Next date (>= today) of a deadline dict, or None."""
    try:
        if d.get("date"):
            dd = dt.date.fromisoformat(d["date"])
            return dd if dd >= today else None
        day = int(d.get("monthly_day", 0))
        if not 1 <= day <= 31:
            return None
        y, m = today.year, today.month
        for _ in range(2):
            cand = dt.date(y, m, min(day, calendar.monthrange(y, m)[1]))
            if cand >= today:
                return cand
            m += 1
            if m > 12:
                m, y = 1, y + 1
    except Exception:
        return None
    return None


EMPTY_DAY = {
    "screen_sec": 0,
    "focus_sec": 0,
    "pomo_count": 0,
    "breaks": 0,
    "skipped": 0,
    "water": 0,
    "posture_checks": 0,
    "points": 0,
    "moods": [],
    "acts": {},
    "hours": {}
}

RANK_TITLES = [
    (1, "Junior Wellness Associate"),
    (3, "Ergonomic Executive"),
    (5, "Senior Balance Analyst"),
    (8, "Wellness Audit Manager"),
    (12, "Director of Focus & Flow"),
    (16, "Managing Partner of Zen"),
    (25, "Grandmaster of Longevity"),
]


# ------------------------------------------------------------ engine
class Engine:
    def __init__(self):
        self.s = {**DEFAULTS, **load_json(USER / "settings.json", {})}
        self.chars = load_json(DATA / "characters.json", {"characters": []})["characters"]
        self.acts = load_json(DATA / "activities.json", {"activities": []})["activities"]
        dl = load_json(USER / "deadlines.json", None) or load_json(DATA / "deadlines.json", {})
        self.deadlines = dl.get("deadlines", [])
        self.tasks = load_json(USER / "tasks.json", {"tasks": []}).get("tasks", [])
        self.all = load_json(USER / "stats.json", {})
        self.today = dt.date.today().isoformat()
        self.since_break = 0.0
        self.since_water = 0.0
        self.since_posture = 0.0
        self.since_eye20 = 0.0
        self.session = 0.0
        self.fired_meals = set()
        self.dnd_until = 0.0
        self.rot = 0
        self.ticks = 0
        self.monitor = ScreenTimeMonitor(self.s)

        # Pomodoro state
        self.pomo_active = False
        self.pomo_left = int(self.s["pomo_work_min"]) * 60
        self.pomo_total = int(self.s["pomo_work_min"]) * 60
        self.pomo_task = "Deep Work / Audit Review"

    # ---- persistence
    def save_settings(self):
        save_json(USER / "settings.json", self.s)

    def save_stats(self):
        save_json(USER / "stats.json", self.all)

    def save_deadlines(self):
        save_json(USER / "deadlines.json", {"deadlines": self.deadlines})

    def save_tasks(self):
        save_json(USER / "tasks.json", {"tasks": self.tasks})

    def save_chars(self):
        save_json(DATA / "characters.json", {"characters": self.chars})

    def save_acts(self):
        save_json(DATA / "activities.json", {"activities": self.acts})

    # ---- day / ticking
    def day(self, iso=None):
        iso = iso or dt.date.today().isoformat()
        if iso != self.today and iso == dt.date.today().isoformat():
            self.today = iso
            self.since_break = self.session = 0.0
            self.fired_meals = set()
        d = self.all.setdefault(iso, {})
        for k, v in EMPTY_DAY.items():
            d.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)
        return d

    def tick(self):
        self.ticks += 1
        d = self.day()
        idle = idle_seconds()
        self.monitor.sample(idle)
        hr_key = str(dt.datetime.now().hour)
        if idle < self.s["idle_limit_sec"]:
            d["screen_sec"] += 1
            d["hours"][hr_key] = d["hours"].get(hr_key, 0) + 1
            self.since_break += 1
            self.since_water += 1
            self.since_posture += 1
            self.since_eye20 += 1
            self.session += 1
        elif idle > 300:
            self.since_break = 0
            self.since_eye20 = 0

        if self.pomo_active:
            self.pomo_left = max(0, self.pomo_left - 1)
            d["focus_sec"] = d.get("focus_sec", 0) + 1

        if self.ticks % 30 == 0:
            self.save_stats()

    # ---- intervals / season
    def next_deadlines(self, n=5):
        today = dt.date.today()
        out = []
        for d in self.deadlines:
            occ = occurrence(d, today)
            if occ:
                out.append(((occ - today).days, d["name"], occ, d.get("category", "General")))
        return sorted(out)[:n]

    def in_season(self):
        if self.s["season_manual"]:
            return True
        nd = self.next_deadlines(1)
        return bool(nd and nd[0][0] <= int(self.s["auto_season_days"]))

    def interval_sec(self):
        m = self.s["season_interval_min"] if self.in_season() else self.s["interval_min"]
        return max(1, int(m)) * 60

    def in_work_hours(self):
        now = dt.datetime.now().strftime("%H:%M")
        return self.s["work_start"] <= now <= self.s["work_end"]

    # ---- selection
    def enabled_acts(self):
        ok = [a for a in self.acts if a["name"] not in self.s["disabled_activities"]]
        return ok or self.acts

    def pick_char(self, name="Random"):
        for c in self.chars:
            if c["name"] == name:
                return c
        if self.chars:
            return random.choice(self.chars)
        return {"name": "BreakBuddy", "avatar": "🙂", "break_lines": ["Time for a break!"]}

    def pick_act(self, name="Auto rotate"):
        for a in self.acts:
            if a["name"] == name:
                return a
        pool = self.enabled_acts()
        a = pool[self.rot % len(pool)]
        self.rot += 1
        return a

    def line(self, ch, kind, act=None):
        pool = ch.get(kind) or ch.get("break_lines") or ["Time for a break!"]
        if kind == "break_lines" and self.session >= 7200 and ch.get("long_work_lines") and random.random() < 0.5:
            pool = ch["long_work_lines"]
        text = random.choice(pool)
        return (text.replace("{hours}", f"{self.session / 3600:.1f}")
                    .replace("{activity}", act["name"] if act else ""))

    # ---- recording
    def record_break(self, act, mood=None):
        d = self.day()
        d["breaks"] += 1
        d["points"] += 15
        d["acts"][act["name"]] = d["acts"].get(act["name"], 0) + 1
        if mood:
            d["moods"].append(mood)
        self.since_break = 0
        self.since_eye20 = 0
        self.save_stats()

    def record_skip(self):
        self.day()["skipped"] += 1
        self.since_break = 0
        self.save_stats()

    def record_water(self):
        d = self.day()
        d["water"] += 1
        d["points"] += 3
        self.since_water = 0
        self.save_stats()

    def record_posture(self):
        d = self.day()
        d["posture_checks"] = d.get("posture_checks", 0) + 1
        d["points"] += 2
        self.since_posture = 0
        self.save_stats()

    def record_pomo(self):
        d = self.day()
        d["pomo_count"] = d.get("pomo_count", 0) + 1
        d["points"] += 25
        for t in self.tasks:
            if t.get("title") == self.pomo_task and not t.get("done"):
                t["pomos"] = t.get("pomos", 0) + 1
                self.save_tasks()
                break
        self.save_stats()

    # ---- ergonomics & health index
    def wellness_score(self, iso=None):
        """Calculates a 0-100 Daily Ergonomic & Wellness Score."""
        d = self.day(iso)
        bg = max(1, int(self.s["break_goal"]))
        wg = max(1, int(self.s["water_goal"]))
        b_score = min(40.0, 40.0 * (d.get("breaks", 0) / bg))
        w_score = min(30.0, 30.0 * (d.get("water", 0) / wg))
        skips = d.get("skipped", 0)
        total_b = d.get("breaks", 0) + skips
        discipline = 20.0 * (d.get("breaks", 0) / total_b) if total_b > 0 else 15.0
        posture_bonus = min(10.0, d.get("posture_checks", 0) * 2.5 + d.get("pomo_count", 0) * 3.0)
        overtime_penalty = max(0.0, (d.get("screen_sec", 0) / 3600.0 - 9.5) * 4.0)
        return int(max(0, min(100, round(b_score + w_score + discipline + posture_bonus - overtime_penalty))))

    # ---- gamification
    def total_points(self):
        return sum(v.get("points", 0) for v in self.all.values())

    def level(self):
        return self.total_points() // 100 + 1

    def rank_title(self):
        lvl = self.level()
        title = RANK_TITLES[0][1]
        for req, t in RANK_TITLES:
            if lvl >= req:
                title = t
        return title

    def _goal_days(self):
        g = int(self.s["break_goal"])
        return sorted(k for k, v in self.all.items() if v.get("breaks", 0) >= g)

    def streak(self):
        g = int(self.s["break_goal"])
        d = dt.date.today()
        if self.all.get(d.isoformat(), {}).get("breaks", 0) < g:
            d -= dt.timedelta(days=1)
        n = 0
        while self.all.get(d.isoformat(), {}).get("breaks", 0) >= g:
            n += 1
            d -= dt.timedelta(days=1)
        return n

    def best_streak(self):
        best = cur = 0
        prev = None
        for k in self._goal_days():
            day = dt.date.fromisoformat(k)
            cur = cur + 1 if prev and (day - prev).days == 1 else 1
            best, prev = max(best, cur), day
        return best

    def badges(self):
        tb = sum(v.get("breaks", 0) for v in self.all.values())
        eye = sum(v.get("acts", {}).get("20-20-20 Eye Rest", 0) for v in self.all.values())
        pomo = sum(v.get("pomo_count", 0) for v in self.all.values())
        post = sum(v.get("posture_checks", 0) for v in self.all.values())
        wg = int(self.s["water_goal"])
        return [
            ("🌱", "First Break", "Complete your first break", tb >= 1),
            ("🔟", "Ten Breaks", "Complete 10 breaks", tb >= 10),
            ("💯", "Century Club", "Complete 100 breaks", tb >= 100),
            ("💧", "Hydration Hero", "Reach your daily water goal", any(v.get("water", 0) >= wg for v in self.all.values())),
            ("🔥", "3-Day Streak", "Hit the break goal 3 days in a row", self.best_streak() >= 3),
            ("🏆", "Week Warrior", "Hit the break goal 7 days in a row", self.best_streak() >= 7),
            ("👁️", "Eye Guardian", "Complete 10 eye rest sessions", eye >= 10),
            ("⚖️", "Balanced Audit", "6h+ screen time AND break goal met",
             any(v.get("screen_sec", 0) >= 21600 and v.get("breaks", 0) >= int(self.s["break_goal"]) for v in self.all.values())),
            ("🍅", "Deep Work Master", "Complete 5 Focus Pomodoro sprints", pomo >= 5),
            ("🪑", "Spine Protector", "Complete 10 posture check-ins", post >= 10),
            ("💎", "Peak Wellness", "Achieve a 90+ Wellness Score today", self.wellness_score() >= 90),
            ("🦸", "Due-Date Survivor", "Hit break goal during Due-Date Season",
             self.in_season() and self.day().get("breaks", 0) >= int(self.s["break_goal"])),
        ]

    def earned_names(self):
        return {b[1] for b in self.badges() if b[3]}

    def export_csv(self, filepath):
        rows = []
        for iso in sorted(self.all.keys()):
            d = self.all[iso]
            moods = d.get("moods", [])
            avg_mood = f"{sum(moods)/len(moods):.2f}" if moods else ""
            rows.append({
                "Date": iso,
                "Screen_Hours": f"{d.get('screen_sec', 0)/3600:.2f}",
                "Focus_Hours": f"{d.get('focus_sec', 0)/3600:.2f}",
                "Pomodoros": d.get("pomo_count", 0),
                "Breaks_Taken": d.get("breaks", 0),
                "Breaks_Skipped": d.get("skipped", 0),
                "Water_Glasses": d.get("water", 0),
                "Posture_Checks": d.get("posture_checks", 0),
                "Points_Earned": d.get("points", 0),
                "Avg_Energy_Mood": avg_mood,
                "Wellness_Score": self.wellness_score(iso),
            })
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Date", "Screen_Hours", "Focus_Hours", "Pomodoros", "Breaks_Taken",
                "Breaks_Skipped", "Water_Glasses", "Posture_Checks", "Points_Earned",
                "Avg_Energy_Mood", "Wellness_Score"
            ])
            writer.writeheader()
            writer.writerows(rows)
