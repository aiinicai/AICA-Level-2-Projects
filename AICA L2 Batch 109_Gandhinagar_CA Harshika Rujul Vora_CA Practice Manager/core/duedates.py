"""Statutory due-date engine.

* Rules (GSTR-3B monthly on the 20th, etc.) live in the `due_date_rules` table.
* One-off extensions (e.g. GSTR-3B for Oct-2026 extended to 25 Nov) live in `due_date_overrides`.
* Both come from `due_dates.json`. The firm keeps its own copy of that file on GitHub; the
  "Check for updates" button downloads it and moves every pending task to the new date.
"""
import calendar
import json
import re
import urllib.request
from datetime import date

from . import clock, config, db
from .constants import QRMP_24


# ------------------------------------------------------------------ financial year helpers
def current_fy_start(today: date | None = None) -> int:
    today = today or clock.today()
    return today.year if today.month >= 4 else today.year - 1


def fy_label(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


# ------------------------------------------------------------------ which rules apply to a client
def applies(rule_applies: str, c: dict) -> bool:
    gst = c.get("gst_freq") or "None"
    quarterly_b = (c.get("state") or "") in QRMP_24
    is_company = c.get("entity_type") == "Company"
    return {
        "gst_monthly": gst == "Monthly",
        "gst_quarterly": gst == "Quarterly",
        "gst_quarterly_a": gst == "Quarterly" and not quarterly_b,
        "gst_quarterly_b": gst == "Quarterly" and quarterly_b,
        "gst_any": gst in ("Monthly", "Quarterly"),
        "tds": bool(c.get("has_tds")),
        "itr": bool(c.get("needs_itr")),
        "audit": bool(c.get("needs_audit")),
        "itr_nonaudit": bool(c.get("needs_itr")) and not c.get("needs_audit") and not is_company,
        "itr_audit": bool(c.get("needs_itr")) and (bool(c.get("needs_audit")) or is_company),
    }.get(rule_applies, False)


# ------------------------------------------------------------------ schedule expansion
def expand(rule: dict, fy: int):
    """Yield (period_label, due_date) for one rule in one financial year."""
    sched = str(rule["schedule"]).strip()
    if rule["frequency"] == "Monthly":
        day, exceptions = sched, {}
        if "|" in sched:  # e.g. "7|3=30" -> 7th, but March period due on 30th
            day, rest = sched.split("|", 1)
            for part in rest.split(","):
                m, d = part.split("=")
                exceptions[int(m)] = int(d)
        for i in range(12):  # return periods Apr(fy) .. Mar(fy+1)
            m = (3 + i) % 12 + 1
            y = fy if m >= 4 else fy + 1
            dm, dy = (1, y + 1) if m == 12 else (m + 1, y)
            dd = min(exceptions.get(m, int(day)), calendar.monthrange(dy, dm)[1])
            yield f"{calendar.month_abbr[m]}-{y}", date(dy, dm, dd)
    else:
        for part in sched.split(","):
            md, label = part.strip().split(":", 1)
            mmdd, off = md.split("@")
            mm, dd = map(int, mmdd.split("-"))
            yield f"{label.strip()} FY {fy_label(fy)}", date(fy + int(off), mm, dd)


def validate_schedule(frequency: str, schedule: str) -> str | None:
    try:
        list(expand({"frequency": frequency, "schedule": schedule}, 2026))
        return None
    except Exception:
        return ("Monthly: a day like 20 (or 7|3=30). Others: MM-DD@N:Label entries separated by commas, "
                "e.g. 07-31@0:Q1,01-31@1:Q3")


def rules(active_only=True):
    return db.query("SELECT * FROM due_date_rules" + (" WHERE active=1" if active_only else "") + " ORDER BY id")


def overrides_map() -> dict:
    return {(o["rule_code"], o["period"]): o["due_date"] for o in db.query("SELECT * FROM due_date_overrides")}


def periods_for(rule_code: str, fy: int) -> list[str]:
    r = db.one("SELECT * FROM due_date_rules WHERE code=:c", c=rule_code)
    return [p for p, _ in expand(r, fy)] if r else []


# ------------------------------------------------------------------ task generation
def generate_for_client(client: dict, fy: int) -> int:
    ov = overrides_map()
    created = 0
    for r in rules():
        if not applies(r["applies_to"], client):
            continue
        for period, due in expand(r, fy):
            due_iso = ov.get((r["code"], period), due.isoformat())
            created += db.execute(
                "INSERT INTO tasks(client_id,rule_code,title,category,period,due_date,updated_on) "
                "VALUES (:c,:code,:t,:cat,:p,:d,:u) ON CONFLICT DO NOTHING",
                c=client["id"], code=r["code"], t=r["title"], cat=r["category"], p=period, d=due_iso, u=db.now())
    if created and client.get("manager_id"):
        # new statutory work goes to the client's manager by default
        db.execute("UPDATE tasks SET assigned_to=:m WHERE client_id=:c AND assigned_to IS NULL AND rule_code IS NOT NULL",
                   m=client["manager_id"], c=client["id"])
    return created


def generate_for_all(fy: int) -> int:
    return sum(generate_for_client(c, fy) for c in db.query("SELECT * FROM clients WHERE active=1"))


def sync_client(client: dict, fy: int) -> tuple[int, int]:
    """After a client's services change: add newly applicable tasks, drop untouched tasks that no longer apply."""
    removed = 0
    for r in rules(active_only=False):
        if not applies(r["applies_to"], client) or not r["active"]:
            removed += db.execute("DELETE FROM tasks WHERE client_id=:c AND rule_code=:r AND status='To Do'",
                                  c=client["id"], r=r["code"])
    return generate_for_client(client, fy), removed


# ------------------------------------------------------------------ rescheduling
def reschedule_pending(user_id=None) -> int:
    """Move every not-yet-done statutory task to the date given by the current rules + overrides."""
    fy0 = current_fy_start()
    expected = {}
    for r in rules(active_only=False):
        for fy in range(fy0 - 3, fy0 + 3):
            for period, due in expand(r, fy):
                expected[(r["code"], period)] = due.isoformat()
    expected.update(overrides_map())
    moved = 0
    for t in db.query("SELECT id, rule_code, period, due_date FROM tasks "
                      "WHERE rule_code IS NOT NULL AND status <> 'Done'"):
        new = expected.get((t["rule_code"], t["period"]))
        if new and new != t["due_date"]:
            db.execute("UPDATE tasks SET due_date=:d, updated_on=:u WHERE id=:i", d=new, u=db.now(), i=t["id"])
            db.log(t["id"], user_id, "Due date changed", f"{t['due_date']} → {new}")
            moved += 1
    return moved


def add_override(rule_code: str, period: str, due_iso: str, note: str, user_id=None) -> int:
    db.execute("INSERT INTO due_date_overrides(rule_code,period,due_date,note) VALUES (:r,:p,:d,:n) "
               "ON CONFLICT (rule_code, period) DO UPDATE SET due_date=excluded.due_date, note=excluded.note",
               r=rule_code, p=period, d=due_iso, n=note)
    return reschedule_pending(user_id)


# ------------------------------------------------------------------ due_dates.json import / updates
def load_bundled() -> dict:
    return json.loads(config.BUNDLED_DUE_DATES.read_text(encoding="utf-8"))


def to_raw_url(url: str) -> str:
    """Accept a normal GitHub link and turn it into the raw-file link."""
    url = (url or "").strip()
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/(.+)", url)
    return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else url


def fetch(url: str) -> dict:
    req = urllib.request.Request(to_raw_url(url), headers={"User-Agent": "CA-Practice-Manager",
                                                            "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def validate_payload(data: dict) -> list[str]:
    errs = []
    if not isinstance(data, dict) or "rules" not in data:
        return ["File has no 'rules' list."]
    for r in data["rules"]:
        missing = {"code", "title", "category", "frequency", "schedule", "applies_to"} - set(r)
        if missing:
            errs.append(f"Rule {r.get('code', '?')} is missing {', '.join(sorted(missing))}")
        elif validate_schedule(r["frequency"], r["schedule"]):
            errs.append(f"Rule {r['code']}: schedule '{r['schedule']}' is not valid")
    for o in data.get("overrides", []):
        try:
            date.fromisoformat(o["due_date"])
            o["code"], o["period"]
        except (KeyError, ValueError):
            errs.append(f"Override {o} needs code, period and due_date (YYYY-MM-DD)")
    return errs


def apply_payload(data: dict, user_id=None) -> dict:
    errs = validate_payload(data)
    if errs:
        raise ValueError("; ".join(errs))
    added = changed = 0
    current = {r["code"]: r for r in rules(active_only=False)}
    for r in data["rules"]:
        old = current.get(r["code"])
        active = int(r.get("active", 1))
        if old is None:
            db.execute("INSERT INTO due_date_rules(code,title,category,frequency,schedule,applies_to,active) "
                       "VALUES (:code,:title,:category,:frequency,:schedule,:applies_to,:active)", **{**r, "active": active})
            added += 1
        elif any(str(old[k]) != str(v) for k, v in {**r, "active": active}.items() if k in old):
            db.execute("UPDATE due_date_rules SET title=:title, category=:category, frequency=:frequency, "
                       "schedule=:schedule, applies_to=:applies_to, active=:active WHERE code=:code",
                       **{k: r[k] for k in ("title", "category", "frequency", "schedule", "applies_to", "code")},
                       active=active)
            changed += 1
    n_ov = 0
    for o in data.get("overrides", []):
        n_ov += db.execute(
            "INSERT INTO due_date_overrides(rule_code,period,due_date,note) VALUES (:r,:p,:d,:n) "
            "ON CONFLICT (rule_code, period) DO UPDATE SET due_date=excluded.due_date, note=excluded.note",
            r=o["code"], p=o["period"], d=o["due_date"], n=o.get("note", ""))
    moved = reschedule_pending(user_id)
    db.set_setting("due_dates_version", data.get("version", ""))
    db.set_setting("due_dates_checked", db.now())
    return {"version": data.get("version", ""), "rules_added": added, "rules_changed": changed,
            "overrides": n_ov, "tasks_moved": moved, "note": data.get("note", "")}


def seed_rules():
    if db.scalar("SELECT COUNT(*) FROM due_date_rules") == 0:
        apply_payload(load_bundled())


def check_for_updates(user_id=None, force=False) -> tuple[str, dict | None]:
    url = db.get_setting("due_dates_url")
    if not url:
        return "no_url", None
    data = fetch(url)
    if not force and str(data.get("version")) == str(db.get_setting("due_dates_version")):
        db.set_setting("due_dates_checked", db.now())
        return "up_to_date", {"version": data.get("version")}
    return "updated", apply_payload(data, user_id)


def export_current() -> dict:
    """Current rules + overrides in due_dates.json format (to paste into GitHub)."""
    return {
        "version": clock.today().strftime("%Y.%m.%d"),
        "updated_on": clock.today().isoformat(),
        "note": "Exported from CA Practice Manager",
        "rules": [{k: r[k] for k in ("code", "title", "category", "frequency", "schedule", "applies_to", "active")}
                  for r in rules(active_only=False)],
        "overrides": [{"code": o["rule_code"], "period": o["period"], "due_date": o["due_date"], "note": o["note"] or ""}
                      for o in db.query("SELECT * FROM due_date_overrides ORDER BY due_date")],
    }
