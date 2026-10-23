import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
USER = BASE / "userdata"
IMAGES = BASE / "images"
USER.mkdir(exist_ok=True)

DEFAULTS = {
    "interval_min": 45,
    "season_interval_min": 30,
    "auto_season_days": 3,
    "season_manual": False,
    "water_every_min": 60,
    "water_goal": 8,
    "break_goal": 6,
    "posture_every_min": 25,
    "posture_on": True,
    "eye_20_every_min": 20,
    "eye_20_on": False,
    "pomo_work_min": 25,
    "pomo_break_min": 5,
    "sound": True,
    "voice": False,
    "theme": "dark",
    "app_monitor_on": True,
    "monitor_window_titles": False,
    "news_auto_refresh": True,
    "work_start": "09:00",
    "work_end": "21:00",
    "enforce_work_hours": False,
    "meals_on": True,
    "meals": {"Lunch": "13:30", "Dinner": "20:30"},
    "idle_limit_sec": 120,
    "character": "Random",
    "activity": "Auto rotate",
    "use_tray": True,
    "disabled_activities": [],
}

THEMES = {
    "dark": dict(
        name="Midnight Slate",
        bg="#0f172a",
        sidebar="#090e1a",
        card="#1e293b",
        card_alt="#263349",
        fg="#f8fafc",
        sub="#94a3b8",
        accent="#3b82f6",
        accent2="#8b5cf6",
        good="#10b981",
        warn="#f43f5e",
        gold="#f59e0b",
        bar="#334155",
        pop="#1e293b",
        border="#334155"
    ),
    "light": dict(
        name="Nordic Daylight",
        bg="#f1f5f9",
        sidebar="#0f172a",
        card="#ffffff",
        card_alt="#f8fafc",
        fg="#0f172a",
        sub="#64748b",
        accent="#2563eb",
        accent2="#7c3aed",
        good="#059669",
        warn="#e11d48",
        gold="#d97706",
        bar="#e2e8f0",
        pop="#ffffff",
        border="#cbd5e1"
    ),
    "cyber": dict(
        name="Cyber Neon",
        bg="#09090b",
        sidebar="#050507",
        card="#18181b",
        card_alt="#27272a",
        fg="#fafafa",
        sub="#a1a1aa",
        accent="#06b6d4",
        accent2="#ec4899",
        good="#22c55e",
        warn="#ef4444",
        gold="#eab308",
        bar="#27272a",
        pop="#18181b",
        border="#3f3f46"
    ),
    "emerald": dict(
        name="Emerald Executive",
        bg="#061914",
        sidebar="#03110d",
        card="#0d2922",
        card_alt="#133930",
        fg="#ecfdf5",
        sub="#6ee7b7",
        accent="#10b981",
        accent2="#34d399",
        good="#22c55e",
        warn="#fb7185",
        gold="#fbbf24",
        bar="#1f493d",
        pop="#0d2922",
        border="#1f493d"
    ),
    "warm": dict(
        name="Warm Latte",
        bg="#faf6f0",
        sidebar="#29221e",
        card="#ffffff",
        card_alt="#f3ede2",
        fg="#29221e",
        sub="#786b5e",
        accent="#d97706",
        accent2="#b45309",
        good="#15803d",
        warn="#dc2626",
        gold="#ca8a04",
        bar="#e6dec8",
        pop="#fffdf9",
        border="#dcd2be"
    ),
}


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    """Atomic local save: interruptions won't leave a half-written JSON file."""
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)
    except Exception as ex:
        print("save failed:", path, ex)
        try:
            temp.unlink(missing_ok=True)
        except Exception:
            pass
