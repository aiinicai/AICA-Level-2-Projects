"""Read photographed attendance registers (Kitchen / UT) with Gemini."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.ai_vision_ocr import (
    ai_ocr_configured,
    extract_figures_from_image,
    missing_key_message,
)
from app.services.attendance_service import merge_attendance_sheets, normalize_mark, title_case_label

logger = logging.getLogger("attendance_ocr")

_ATTENDANCE_PROMPT = """You are reading a photographed Indian restaurant ATTENDANCE REGISTER
(Kitchen Team / Utility / attendance रजिस्टर). It may be one page or a two-page spread.

Extract every staff row. New names added at the bottom of a list are still staff.

Marks in day columns:
- P = Present
- WO = Weekly Off (O, off, circled O, weekly off)
- L = Leave
- A = Absent, or any other written mark (dash, holiday, cross, etc.)
Empty cell = null. Do not invent marks. Do not output "-".

Also read Total Days and notes such as "2 pending off", "भाग गया", "6 days".

Return JSON only:
{
  "year": 2026,
  "month": 6,
  "team": "Kitchen Team",
  "employees": [
    {
      "name": "SURESH",
      "rank": "chef chinese",
      "team": "Kitchen",
      "marks": {"1": "P", "2": "WO", "3": "A"},
      "total_days": 27,
      "notes": "2 pending off"
    }
  ]
}
If the photo shows only days 1-20 or only 21-31, still return those days. Year 26 means 2026.
"""

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _period_from_text(value: Any) -> Tuple[Optional[int], Optional[int]]:
    text = str(value or "").strip()
    named = re.search(
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
        r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s*,?\s*(\d{2,4})",
        text,
        re.I,
    )
    if named:
        month = _MONTHS.get(named.group(1).lower())
        year = int(named.group(2))
        if year < 100:
            year += 2000
        return year, month
    iso = re.match(r"^(\d{4})-(\d{1,2})$", text)
    if iso:
        return int(iso.group(1)), int(iso.group(2))
    return None, None


def _normalize_employee_row(item: Dict[str, Any], default_team: Optional[str]) -> Optional[Dict[str, Any]]:
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    marks_in = item.get("marks") or item.get("days") or {}
    marks: Dict[str, str] = {}
    if isinstance(marks_in, dict):
        for key, raw in marks_in.items():
            day = _int(key)
            mark = normalize_mark(raw)
            if day and 1 <= day <= 31 and mark:
                marks[str(day)] = mark
    elif isinstance(marks_in, list):
        for i, raw in enumerate(marks_in, start=1):
            mark = normalize_mark(raw)
            if mark:
                marks[str(i)] = mark
    return {
        "name": title_case_label(name) or name,
        "rank": title_case_label(item.get("rank") or item.get("role")),
        "team": title_case_label(item.get("team") or item.get("team_section") or default_team),
        "notes": str(item.get("notes") or "").strip() or None,
        "total_days": _int(item.get("total_days")),
        "marks": marks,
    }


def normalize_attendance_json(parsed: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    year = _int(parsed.get("year") or parsed.get("period_year"))
    month = _int(parsed.get("month") or parsed.get("period_month"))
    if not year or not month:
        y2, m2 = _period_from_text(parsed.get("period") or parsed.get("month_name"))
        year = year or y2
        month = month or m2
    if not year or not month:
        y2, m2 = _period_from_text(filename)
        year = year or y2
        month = month or m2
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    team = str(parsed.get("team") or "").strip() or None
    employees = []
    for item in parsed.get("employees") or parsed.get("staff") or []:
        if not isinstance(item, dict):
            continue
        row = _normalize_employee_row(item, team)
        if row:
            employees.append(row)
    return {
        "status": "SUCCESS",
        "year": year,
        "month": month,
        "team": team,
        "employees": employees,
        "raw": parsed,
    }


def extract_attendance_from_image(image_bytes: bytes, filename: str) -> Dict[str, Any]:
    if not ai_ocr_configured():
        return {
            "status": "ERROR",
            "error_detail": missing_key_message(),
            "last_step": "AI OCR not configured",
        }
    try:
        parsed = extract_figures_from_image(image_bytes, prompt=_ATTENDANCE_PROMPT)
        out = normalize_attendance_json(parsed, filename)
        out["filename"] = filename
        return out
    except Exception as exc:
        logger.exception("Attendance OCR failed")
        return {"status": "ERROR", "error_detail": str(exc), "filename": filename}


def extract_attendance_from_images(items: List[Tuple[bytes, str]]) -> Dict[str, Any]:
    if not items:
        return {"status": "ERROR", "error_detail": "No images uploaded"}
    if len(items) > 5:
        return {"status": "ERROR", "error_detail": "Upload at most 5 attendance photos."}
    readings = []
    errors = []
    for content, name in items:
        one = extract_attendance_from_image(content, name)
        if one.get("status") == "ERROR":
            errors.append({"filename": name, "error": one.get("error_detail")})
            continue
        readings.append(one)
    if not readings:
        return {
            "status": "ERROR",
            "error_detail": errors[0]["error"] if errors else "No images could be read",
            "partial_errors": errors,
        }
    merged = merge_attendance_sheets(readings)
    if errors:
        merged["partial_errors"] = errors
    return merged
