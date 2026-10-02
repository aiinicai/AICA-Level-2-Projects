"""Shared paths, logging and small helpers for the LookThrough data bridge."""
import calendar
import json
import logging
import os
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = DATA / "config"
CACHE = DATA / "cache"
LIVE = DATA / "live"
PORTFOLIO_DIR = DATA / "amc_portfolios"
LOGS = ROOT / "logs"
APP_SRC = ROOT / "app_src"
APP_OUT = ROOT / "app" / "LookThrough.html"
VERSION = "3.0"

SNAPSHOT = DATA / "snapshot" / "dataset.json"
SEED_CACHE = DATA / "seed_cache"

for p in (CACHE, LIVE, PORTFOLIO_DIR, LOGS):
    p.mkdir(parents=True, exist_ok=True)
# A fresh clone has no data/live (rebuilt from the internet, never committed): start from the committed 31-Aug-2026
# snapshot, so the app, the MCP server and the checks run offline on the documented figures. A refresh replaces it.
if not (LIVE / "dataset.json").exists() and SNAPSHOT.exists():
    shutil.copyfile(SNAPSHOT, LIVE / "dataset.json")
# ...and from the seed cache (tools/make_seed_cache.py), so an offline rebuild reproduces that snapshot. A seed file is
# copied only when missing and back-dated, so an online session replaces it with a full download at first use.
if SEED_CACHE.is_dir():
    for f in SEED_CACHE.iterdir():
        if f.is_file() and not (CACHE / f.name).exists():
            shutil.copyfile(f, CACHE / f.name)
            os.utime(CACHE / f.name, (946684800, 946684800))  # 1-Jan-2000: stale, so a fetch refreshes it

log = logging.getLogger("lookthrough")
if not log.handlers:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOGS / "bridge.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj, indent=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, default=str, separators=None if indent else (",", ":")), encoding="utf-8")
    tmp.replace(path)


def config(name):
    return load_json(CONFIG / f"{name}.json")


def month_end(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def valuation_date(today=None):
    """Last completed month-end strictly before today."""
    today = today or date.today()
    prev = today.replace(day=1) - timedelta(days=1)
    return month_end(prev)


def month_ends(as_on, n=37):
    out = []
    y, m = as_on.year, as_on.month
    for _ in range(n):
        out.append(month_end(date(y, m, 1)))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def fy_label(d):
    """Fiscal-year label for a period-end date (Indian FY ends March)."""
    if isinstance(d, str):
        d = datetime.fromisoformat(d[:10]).date()
    if d.month <= 3:
        return f"FY{d.year - 1}-{str(d.year)[2:]}"
    return f"FY{d.year}-{str(d.year + 1)[2:]}"


def isin_check_digit_ok(s):
    s = (s or "").strip().upper()
    if len(s) != 12 or not s[:2].isalpha() or not s[-1].isdigit():
        return False
    digits = "".join(str(int(ch, 36)) for ch in s[:11])
    tot = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        tot += n
    return (10 - tot % 10) % 10 == int(s[-1])


def is_equity_isin(isin):
    """Indian equity shares carry security-type code 01 in positions 8-9 (INE…01…); IN9 = partly paid / DVR equity."""
    return (isin.startswith("INE") and isin[7:9] == "01") or isin.startswith("IN9")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")
