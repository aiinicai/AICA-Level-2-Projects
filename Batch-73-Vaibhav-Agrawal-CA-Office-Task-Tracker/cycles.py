"""
cycles.py - The "brain" of the Task Tracker: due dates and status of tasks.

A CA office has work that repeats - GSTR-3B every month, TDS returns every
quarter, ROC forms every year. Instead of creating a new task each time, a
repeating task is stored ONCE and this module works out, for today's date:

  * which cycle the task is currently in      (e.g. "Sep 2026", "Jul-Sep 2026")
  * the due date of that cycle                (e.g. 20 Sep 2026)
  * whether the task is done for that cycle
  * its status: done / overdue / soon / later / open

When a new cycle begins (next month, next quarter ...) the task automatically
shows as open again, because its "done for" marker belongs to the old cycle.

Quarters and years follow the Indian financial year (April to March).

A task is a dictionary with these keys (all optional except title):
  frequency   : 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly' | 'Annual' | 'One-time'
  dueDate     : 'YYYY-MM-DD'   (One-time: the due date, Annual: day and month)
  dueDay      : 1-31           (Monthly / Quarterly: due by this day)
  dueFrom     : 1-31           (Monthly: work opens from this day)
  dueRule     : '2nd-sat'      (Monthly: due on the second Saturday)
  dueWeekday  : 1-7            (Weekly: 1 = Monday ... 7 = Sunday)
  dueQOffset  : 0 or 1         (Quarterly: 0 = last month of the quarter,
                                           1 = month after the quarter)
  status      : 'open' | 'done'   (One-time tasks)
  doneFor     : cycle key         (repeating tasks: the cycle it was done for)
  checkedOn   : 'YYYY-MM-DD'      (looked at today, hide until tomorrow)
  later       : True = "do when free"
"""

import calendar
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FREQUENCIES = ["Daily", "Weekly", "Monthly", "Quarterly", "Annual", "One-time"]
RECURRING = FREQUENCIES[:-1]


# --------------------------------------------------------------------------
# Small date helpers
# --------------------------------------------------------------------------
def parse_iso(text):
    """'2026-09-21' -> date(2026, 9, 21). Returns None for blank / bad input."""
    try:
        return date.fromisoformat(text) if text else None
    except (TypeError, ValueError):
        return None


def clamp_day(year, month, day):
    """Date for the given day, pulled back to month-end if the month is shorter
    (day 31 in a 30-day month becomes the 30th)."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def second_saturday(year, month):
    first = date(year, month, 1)
    first_saturday = 1 + (5 - first.weekday()) % 7      # Monday=0 ... Saturday=5
    return date(year, month, first_saturday + 7)


def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 23 -> '23rd'."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def fmt(d, today, with_year=False):
    """'21 Sep' - the year is added only when it differs from the current year."""
    if d is None:
        return ""
    text = f"{d.day} {MONTHS[d.month - 1]}"
    return f"{text} {d.year}" if with_year or d.year != today.year else text


# --------------------------------------------------------------------------
# Financial year and quarters (April - March)
# --------------------------------------------------------------------------
def fy_start(d):
    """Starting calendar year of the financial year containing d."""
    return d.year if d.month >= 4 else d.year - 1


def fy_label(fy):
    return f"FY {fy}-{(fy + 1) % 100:02d}"


def quarter_of(d):
    """0 = Apr-Jun, 1 = Jul-Sep, 2 = Oct-Dec, 3 = Jan-Mar."""
    return (d.month - 4) // 3 if d.month >= 4 else 3


def quarter_label(fy, q):
    first = (3 + q * 3) % 12                    # month index, 0 = January
    last = (first + 2) % 12
    return f"{MONTHS[first]}–{MONTHS[last]} {fy + 1 if first < 3 else fy}"


def quarter_deadline(fy, q, task):
    due_day = task.get("dueDay")
    if not due_day:
        return None
    end_month = (3 + q * 3 + 2) % 12            # 0 = January
    year = fy + (1 if end_month < 3 else 0)
    month = end_month + (1 if task.get("dueQOffset") else 0)
    if month > 11:
        month, year = 0, year + 1
    return clamp_day(year, month + 1, due_day)


def is_recurring(task):
    return task.get("frequency") in RECURRING


# --------------------------------------------------------------------------
# The current cycle of a task
# --------------------------------------------------------------------------
def cycle(task, today=None):
    """
    Work out the cycle a task is in today.

    Returns a dict:  key      - unique id of the cycle (None for one-time tasks)
                     label    - text shown to the user
                     deadline - due date of this cycle (may be None)
                     start    - date from which the work opens (may be None)
    """
    today = today or date.today()
    frequency = task.get("frequency")
    due_day, due_from = task.get("dueDay"), task.get("dueFrom")

    if frequency == "Monthly":
        year, month = today.year, today.month
        # A window such as "21st to 7th" runs across two months. Until the 7th
        # we are still in the cycle that opened on the 21st of LAST month.
        crosses_month = bool(due_from and due_day and due_from > due_day)
        if crosses_month and today.day <= due_day:
            year, month = (year - 1, 12) if month == 1 else (year, month - 1)

        deadline = start = None
        if task.get("dueRule") == "2nd-sat":
            deadline = second_saturday(year, month)
        elif due_day:
            if crosses_month:
                next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
                deadline = clamp_day(next_year, next_month, due_day)
                start = clamp_day(year, month, due_from)
            else:
                deadline = clamp_day(year, month, due_day)
                if due_from:
                    start = clamp_day(year, month, due_from)
        return {"key": f"{year}-{month:02d}", "label": f"{MONTHS[month - 1]} {year}",
                "deadline": deadline, "start": start}

    if frequency == "Daily":
        return {"key": today.isoformat(), "label": "today", "deadline": today, "start": None}

    if frequency == "Weekly":
        monday = today - timedelta(days=today.weekday())
        weekday = task.get("dueWeekday")
        deadline = monday + timedelta(days=weekday - 1) if weekday and 1 <= weekday <= 7 else None
        return {"key": "W" + monday.isoformat(), "label": "this week",
                "deadline": deadline, "start": None}

    if frequency == "Quarterly":
        fy, q = fy_start(today), quarter_of(today)
        # A return for Apr-Jun may be due on 31 July. Until that date passes,
        # the task still belongs to the PREVIOUS quarter.
        prev_fy, prev_q = (fy - 1, 3) if q == 0 else (fy, q - 1)
        prev_deadline = quarter_deadline(prev_fy, prev_q, task)
        if prev_deadline and today <= prev_deadline:
            fy, q = prev_fy, prev_q
        return {"key": f"Q{fy}-{q}", "label": quarter_label(fy, q),
                "deadline": quarter_deadline(fy, q, task), "start": None}

    if frequency == "Annual":
        fy = fy_start(today)
        deadline = None
        due = parse_iso(task.get("dueDate"))
        if due:
            deadline = clamp_day(fy if due.month >= 4 else fy + 1, due.month, due.day)
        return {"key": f"FY{fy}", "label": fy_label(fy), "deadline": deadline, "start": None}

    # One-time task
    return {"key": None, "label": None, "deadline": parse_iso(task.get("dueDate")), "start": None}


def cycle_key_label(key):
    """Readable name of a stored cycle key, used in the 'Completed' history."""
    try:
        if key.startswith("FY"):
            return fy_label(int(key[2:]))
        if key.startswith("Q"):
            fy, q = key[1:].split("-")
            return quarter_label(int(fy), int(q))
        if key.startswith("W"):
            d = date.fromisoformat(key[1:])
            return f"Week of {d.day} {MONTHS[d.month - 1]} {d.year}"
        if len(key) == 7:
            return f"{MONTHS[int(key[5:]) - 1]} {key[:4]}"
        d = date.fromisoformat(key)
        return f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    except (ValueError, IndexError, AttributeError):
        return str(key)


# --------------------------------------------------------------------------
# Status of a task
# --------------------------------------------------------------------------
def info(task, today=None):
    """
    Full status of a task for today.

      state   : 'done' | 'overdue' | 'soon' (due within 3 days) |
                'later' (window not open yet) | 'open'
      days    : days left to the deadline (negative = overdue, None = no deadline)
      free    : marked "do when free" and not urgent
      checked : looked at today, so hidden until tomorrow
    """
    today = today or date.today()
    c = cycle(task, today)

    if is_recurring(task):
        done = task.get("doneFor") == c["key"]
    else:
        done = task.get("status") == "done"

    days = (c["deadline"] - today).days if c["deadline"] else None
    if done:
        state = "done"
    elif days is not None and days < 0:
        state = "overdue"
    elif days is not None and days <= 3:
        state = "soon"
    elif c["start"] and today < c["start"]:
        state = "later"
    else:
        state = "open"

    free = bool(task.get("later")) and not done and state not in ("overdue", "soon")
    checked = not done and task.get("checkedOn") == today.isoformat()
    return {"c": c, "done": done, "state": state, "days": days, "free": free, "checked": checked}


def due_text(task, today=None):
    """Short description of the due rule, shown in the 'Due' column."""
    today = today or date.today()
    frequency, due_day = task.get("frequency"), task.get("dueDay")
    if frequency == "Daily":
        return "Every day"
    if frequency == "Weekly":
        weekday = task.get("dueWeekday")
        return f"Every {WEEKDAYS[weekday - 1]}" if weekday and 1 <= weekday <= 7 else ""
    if frequency == "Quarterly":
        if not due_day:
            return ""
        return ordinal(due_day) + (" after qtr" if task.get("dueQOffset") else " of qtr end")
    if frequency == "Monthly":
        if task.get("dueRule") == "2nd-sat":
            return "2nd Saturday"
        if task.get("dueFrom") and due_day:
            return f"{ordinal(task['dueFrom'])}–{ordinal(due_day)}"
        return ordinal(due_day) if due_day else ""
    due = parse_iso(task.get("dueDate"))
    if frequency == "Annual":
        return f"{due.day} {MONTHS[due.month - 1]}" if due else ""
    return fmt(due, today)


def pill_text(task, i, today=None):
    """Text of the coloured status pill, e.g. '3d overdue' or 'Due tomorrow'."""
    today = today or date.today()
    if i["done"]:
        return f"Done · {i['c']['label']}" if is_recurring(task) else "Done"
    if i["state"] == "overdue":
        return f"{-i['days']}d overdue"
    if i["state"] == "soon":
        return {0: "Due today", 1: "Due tomorrow"}.get(i["days"], f"Due in {i['days']}d")
    if i["state"] == "later":
        return "Opens " + fmt(i["c"]["start"], today)
    if i["checked"]:
        return "Checked today"
    if i["free"]:
        return "When free"
    if i["c"]["deadline"]:
        return "Due " + fmt(i["c"]["deadline"], today)
    return ""


def due_preview(task, today=None):
    """One-line HTML hint shown in the task form while the user sets the due rule."""
    today = today or date.today()
    frequency = task.get("frequency") or "One-time"

    if frequency == "One-time":
        due = parse_iso(task.get("dueDate"))
        if not due:
            return ""
        days = (due - today).days
        if days < 0:
            return f"<b>{-days} day{'' if days == -1 else 's'} overdue</b>"
        if days == 0:
            return "Due <b>today</b>"
        if days == 1:
            return "Due <b>tomorrow</b>"
        return f"Due in <b>{days} days</b>"

    c = cycle(task, today)
    if not c["deadline"]:
        return {"Monthly": "Set a day so it shows as due each month.",
                "Weekly": "Pick a weekday so it shows as due each week.",
                "Quarterly": "Set a day so it shows as due each quarter.",
                "Annual": "Repeats every financial year."}.get(frequency, "")
    if frequency == "Daily":
        return "Due <b>every day</b> — resets each morning."
    lead = {"Weekly": "This week: ", "Monthly": "This month: ",
            "Quarterly": f"This quarter ({c['label']}): "}.get(frequency, "Next: ")
    opens = f" · opens {fmt(c['start'], today)}" if c["start"] else ""
    return f"{lead}due <b>{fmt(c['deadline'], today)}</b>{opens}"
