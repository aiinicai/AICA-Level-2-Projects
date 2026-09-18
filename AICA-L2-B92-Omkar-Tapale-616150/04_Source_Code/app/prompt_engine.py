"""
Layer 1 of the Prompt-to-Action Engine (Section 2.2 of the project plan):
offline, instant, free rule-based keyword + date/time parsing.
Covers the everyday phrasing patterns from the plan's example table.
Returns a dict describing the detected intent + a confidence flag so the
UI can show a confirmation card when confidence is low, instead of guessing.
"""
import re
import datetime as dt
import dateparser
from dateparser.search import search_dates

PRIORITY_WORDS = {
    "urgent": "URGENT",
    "high priority": "HIGH",
    "high": "HIGH",
    "medium priority": "MEDIUM",
    "low priority": "LOW",
    "low": "LOW",
}

WFH_WORDS = ["wfh", "work from home", "working from home"]
WFO_WORDS = ["wfo", "work from office", "in office", "from office"]
HALF_DAY_WORDS = ["half day", "half-day"]
DONE_WORDS = ["mark", "done", "complete", "completed", "close"]
LEAVE_WORDS = ["leave", "casual leave", "sick leave", "vacation", "pl", "cl", "sl"]
MEETING_WORDS = ["meeting", "schedule", "call with", "sync with"]
RESIGN_WORDS = ["resign", "resignation", "quit", "last working day"]
PENDING_WORDS = ["pending action", "pending", "follow up", "follow-up"]
TASK_WORDS = ["task", "add task", "todo", "to-do"]
REMINDER_WORDS = ["remind", "reminder"]


def _extract_priority(text: str) -> str:
    low = text.lower()
    for word, level in PRIORITY_WORDS.items():
        if word in low:
            return level
    return "MEDIUM"


def _extract_dates(text: str):
    """Returns list of (matched_text, datetime) tuples found in the prompt."""
    settings = {"PREFER_DATES_FROM": "future", "RELATIVE_BASE": dt.datetime.now()}
    found = search_dates(text, settings=settings)
    return found or []


def _date_range(text: str):
    """Detect 'A to B' or 'A-B' style ranges for leave/WFH spans."""
    m = re.search(
        r"(.+?)\s(?:to|-|through|till|until)\s(.+)", text, flags=re.IGNORECASE
    )
    dates = _extract_dates(text)
    if len(dates) >= 2:
        d1 = dates[0][1].date()
        d2 = dates[1][1].date()
        if d2 < d1:
            d1, d2 = d2, d1
        return d1, d2
    if len(dates) == 1:
        d = dates[0][1].date()
        return d, d
    return None, None


def parse_prompt(text: str) -> dict:
    """Main entry point. Returns:
    {
      intent: TASK|MEETING|PENDING_ACTION|ATTENDANCE|LEAVE|REMINDER|RESIGNATION|TASK_UPDATE|UNKNOWN,
      confidence: HIGH|LOW,
      fields: {...intent-specific...},
      raw_prompt_text: original text
    }
    """
    low = text.lower().strip()
    result = {"raw_prompt_text": text, "fields": {}, "confidence": "HIGH"}

    # --- Task status update: "mark task 'x' as done" ---
    if any(w in low for w in DONE_WORDS) and ("task" in low or "'" in text or '"' in text):
        title_match = re.search(r"['\"](.+?)['\"]", text)
        title = title_match.group(1) if title_match else None
        result["intent"] = "TASK_UPDATE"
        result["fields"] = {"title_contains": title, "new_status": "DONE"}
        result["confidence"] = "HIGH" if title else "LOW"
        return result

    # --- Resignation ---
    if any(w in low for w in RESIGN_WORDS):
        dates = _extract_dates(text)
        lwd = dates[0][1].date() if dates else None
        result["intent"] = "RESIGNATION"
        result["fields"] = {"last_working_day": lwd, "reason": text}
        result["confidence"] = "HIGH" if lwd else "LOW"
        return result

    # --- Attendance: WFH / WFO / Half day ---
    if any(w in low for w in WFH_WORDS + WFO_WORDS + HALF_DAY_WORDS):
        if any(w in low for w in HALF_DAY_WORDS):
            status = "HALF_DAY"
        elif any(w in low for w in WFH_WORDS):
            status = "WFH"
        else:
            status = "WFO"
        start, end = _date_range(text)
        if not start:
            start = end = dt.date.today()
        result["intent"] = "ATTENDANCE"
        result["fields"] = {"status": status, "start_date": start, "end_date": end}
        return result

    # --- Leave ---
    if any(w in low for w in LEAVE_WORDS):
        start, end = _date_range(text)
        result["intent"] = "LEAVE"
        result["fields"] = {"start_date": start, "end_date": end, "reason": text}
        result["confidence"] = "HIGH" if start else "LOW"
        return result

    # --- Meeting ---
    if any(w in low for w in MEETING_WORDS):
        dates = _extract_dates(text)
        when = dates[0][1] if dates else None
        result["intent"] = "MEETING"
        result["fields"] = {
            "title": text,
            "start_date": when.date() if when else None,
            "start_time": when.strftime("%H:%M") if when and when.hour else None,
            "priority": _extract_priority(text),
        }
        result["confidence"] = "HIGH" if when else "LOW"
        return result

    # --- Pending action ---
    if any(w in low for w in PENDING_WORDS):
        dates = _extract_dates(text)
        due = dates[0][1].date() if dates else None
        result["intent"] = "PENDING_ACTION"
        result["fields"] = {"title": text, "due_date": due, "priority": _extract_priority(text)}
        result["confidence"] = "HIGH" if due else "LOW"
        return result

    # --- Reminder ---
    if any(w in low for w in REMINDER_WORDS):
        dates = _extract_dates(text)
        when = dates[0][1].date() if dates else None
        result["intent"] = "REMINDER"
        result["fields"] = {"title": text, "start_date": when, "priority": "MEDIUM"}
        result["confidence"] = "HIGH" if when else "LOW"
        return result

    # --- Task (default catch-all when 'task' mentioned, or fallback) ---
    if any(w in low for w in TASK_WORDS) or True:
        dates = _extract_dates(text)
        due = dates[0][1].date() if dates else None
        result["intent"] = "TASK"
        result["fields"] = {"title": text, "due_date": due, "priority": _extract_priority(text)}
        result["confidence"] = "HIGH" if any(w in low for w in TASK_WORDS) else "LOW"
        return result
