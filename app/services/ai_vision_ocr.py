"""
Online AI reading for day-book photos only.

Excel, bank files, aggregators, and all other app data stay on this PC.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image

from app.core.config import BASE_DIR, settings

logger = logging.getLogger("ai_vision_ocr")

_EMPTY_FIELD: Dict[str, Any] = {
    "value": None, "confidence": 0.0, "ocr_confidence": 0.0,
    "numeric_validation_score": 0.0, "description_confidence": 0.0,
    "amount_confidence": 0.0, "classification_confidence": 0.0,
    "status": "NOT_DETECTED", "source_row_id": None, "source_row": "",
    "source_description": "", "raw_description": "", "amount_raw": "",
    "amount_crop_b64": "", "why_selected": "Not detected in register image",
    "candidates": [],
}

_DAYBOOK_PROMPT = """You are reading ONE photo used for Indian restaurant daily reconciliation.

First set image_kind to exactly one of:
- DAYBOOK — handwritten cash register / day book (Receipts & Payments, Opening, Expense lines, Cash Payment, Closing). May be two pages in one photo.
- PETPOOJA — POS / Petpooja computer screen with Payment Mode totals (Cash, Card, Swiggy, Zomato).
- EDC — handheld card machine Payment History (Successful Payments, Payment Received).
- OTHER — anything else.

DAYBOOK / cash register rules:
- Opening / Opning Balance is opening_balance.
- Expense lines (Milk, Water, Parcel/Parsal, Pest Control, grocery, etc.) go in expense_items. site_expenses = their sum. Do NOT treat the expense subtotal as cash sale.
- "Cash Payment" or "Cash sale" is cash (cash sales).
- Closing Balance is closing_balance.
- Ignore Folio. Year 26 means 2026.
- If this page has NO payment-mode sales (no Card/Zomato/Swiggy), leave those sales fields null.

PETPOOJA rules:
- Read Payment Mode: Cash, Card, Swiggy, Zomato (and Dineout if shown).
- cash = Cash mode. credit_card = Card mode (this is Card/QR).
- Ignore Delivery / Dine In / Pick Up order-type totals (those are not payment channels).
- Leave opening, expenses, closing null unless clearly shown.

EDC / card machine rules:
- Payment Received (day total) is credit_card (Card/QR verification).
- Leave cash, zomato, swiggy, opening, expenses, closing null.

Rules for all:
- If a figure is clearly 0, return 0. If missing, return null.
- Date from the document, never from a WhatsApp filename.

Return JSON only:
{
  "image_kind": "DAYBOOK" | "PETPOOJA" | "EDC" | "OTHER",
  "date": "YYYY-MM-DD" or null,
  "opening_balance": number or null,
  "today_sale": number or null,
  "cash": number or null,
  "credit_card": number or null,
  "paytm": number or null,
  "swiggy": number or null,
  "zomato": number or null,
  "dineout": number or null,
  "service_charge": number or null,
  "site_expenses": number or null,
  "salary_advance": number or null,
  "closing_balance": number or null,
  "expense_items": [{"description": "string", "amount": number}]
}
"""

_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)


def _strip_key(value: str) -> str:
    return (value or "").strip().strip('"').strip("'")


def _key_from_dotenv() -> str:
    path = BASE_DIR / ".env"
    try:
        if not path.is_file():
            return ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GEMINI_API_KEY"):
                _, _, val = line.partition("=")
                return _strip_key(val)
    except Exception:
        return ""
    return ""


def _read_key_file() -> str:
    for path in (BASE_DIR / "data" / "gemini_key.txt", BASE_DIR / "gemini_key.txt"):
        try:
            if path.is_file():
                return _strip_key(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return ""


def get_gemini_api_key() -> str:
    return (
        _strip_key(getattr(settings, "GEMINI_API_KEY", None) or "")
        or _strip_key(os.getenv("GEMINI_API_KEY") or "")
        or _strip_key(os.getenv("GOOGLE_API_KEY") or "")
        or _key_from_dotenv()
        or _read_key_file()
    )


def get_openai_api_key() -> str:
    return (
        (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
        or (os.getenv("OPENAI_API_KEY") or "").strip()
    )


def ai_ocr_configured() -> bool:
    return bool(get_gemini_api_key() or get_openai_api_key())


def missing_key_message() -> str:
    return (
        "Day-book photos are read by Google Gemini (online). "
        "Get a free key at https://aistudio.google.com/apikey "
        "then add GEMINI_API_KEY=your_key to the .env file in the project folder "
        "and restart the app. Excel and bank files stay on this PC."
    )


def _jpeg_for_ai(image_bytes: bytes, max_dim: int = 1600, quality: int = 82) -> bytes:
    im = Image.open(io.BytesIO(image_bytes))
    if im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    scale = max_dim / float(max(w, h))
    if scale < 1.0:
        im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("₹", "").replace("Rs", "").strip()
    if text.lower() in ("", "null", "none", "-", "n/a"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

KIND_LABELS = {
    "DAYBOOK": "Cash register",
    "PETPOOJA": "POS screen",
    "EDC": "Card machine",
    "OTHER": "Photo",
}

# Prefer the photo that actually owns the figure. Never average.
FIELD_PRIORITY = {
    "date": ["DAYBOOK", "PETPOOJA", "EDC", "OTHER"],
    "opening_balance": ["DAYBOOK"],
    "site_expenses": ["DAYBOOK"],
    "salary_advance": ["DAYBOOK"],
    "closing_balance": ["DAYBOOK"],
    "cash": ["PETPOOJA", "DAYBOOK"],
    "card_qr": ["PETPOOJA", "EDC", "DAYBOOK"],
    "zomato": ["PETPOOJA", "DAYBOOK"],
    "swiggy": ["PETPOOJA", "DAYBOOK"],
    "dineout": ["PETPOOJA", "DAYBOOK"],
}

VERIFY_PAIRS = (
    ("cash", "PETPOOJA", "DAYBOOK"),
    ("card_qr", "PETPOOJA", "EDC"),
)


def normalize_image_kind(value: Any) -> str:
    raw = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "CASH_BOOK": "DAYBOOK",
        "CASHBOOK": "DAYBOOK",
        "REGISTER": "DAYBOOK",
        "DAY_BOOK": "DAYBOOK",
        "POS": "PETPOOJA",
        "PET_POOJA": "PETPOOJA",
        "PETPOOJ": "PETPOOJA",
        "CARD_MACHINE": "EDC",
        "PAYMENT_HISTORY": "EDC",
        "QR": "EDC",
    }
    raw = aliases.get(raw, raw)
    if raw in KIND_LABELS:
        return raw
    return "DAYBOOK"


def _normalize_date(value: Any, filename: str) -> str:
    from app.services.image_ocr_service import _DATE_PATTERN, _parse_date

    raw = str(value or "").strip()
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if iso:
        return raw
    if raw:
        m = _DATE_PATTERN.search(raw.replace("-", "/"))
        if m:
            return _parse_date(*m.groups())
        named = re.match(
            r"^(\d{1,2})\s+([A-Za-z]+)\s*,?\s*(\d{2,4})?$",
            raw,
        )
        if named:
            day = int(named.group(1))
            month = _MONTH_NAMES.get(named.group(2).lower())
            year_raw = named.group(3)
            year = datetime.now().year
            if year_raw:
                year = int(year_raw)
                if year < 100:
                    year += 2000
            if month and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    fname = filename or ""
    if not re.search(r"whatsapp|img[-_]|screenshot|dcim", fname, re.I):
        m = _DATE_PATTERN.search(fname)
        if m:
            return _parse_date(*m.groups())
    return datetime.now().strftime("%Y-%m-%d")


def _field(value: Optional[float], why: str = "Gemini vision") -> Dict[str, Any]:
    if value is None:
        return dict(_EMPTY_FIELD)
    return {
        **dict(_EMPTY_FIELD),
        "value": float(value),
        "amount_raw": str(value),
        "confidence": 0.92,
        "ocr_confidence": 0.92,
        "numeric_validation_score": 92.0,
        "description_confidence": 0.92,
        "amount_confidence": 0.92,
        "classification_confidence": 0.92,
        "status": "CONFIRMED",
        "source_row": "AI vision",
        "source_description": why,
        "raw_description": why,
        "why_selected": why,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError("AI did not return JSON figures")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("AI JSON was not an object")
    return data


def _gemini_headers(api_key: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }


def _pick_gemini_models(client: httpx.Client, api_key: str) -> List[str]:
    """Ask Gemini which flash models this key can use; fall back to a known list."""
    try:
        res = client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers=_gemini_headers(api_key),
        )
        if res.status_code == 200:
            names = []
            for m in (res.json().get("models") or []):
                name = str(m.get("name") or "").split("/")[-1]
                methods = m.get("supportedGenerationMethods") or []
                if name and "generateContent" in methods and "flash" in name.lower():
                    names.append(name)
            if names:
                preferred = [n for n in _GEMINI_MODELS if n in names]
                extras = [n for n in names if n not in preferred]
                return preferred + extras
    except Exception:
        pass
    return list(_GEMINI_MODELS)


def _call_gemini(jpeg_bytes: bytes, api_key: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt or _DAYBOOK_PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            ],
        }],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }
    last_err = "Gemini request failed"
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
        models = _pick_gemini_models(client, api_key)
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                res = client.post(url, headers=_gemini_headers(api_key), json=payload)
            except httpx.HTTPError as exc:
                last_err = f"Could not reach Gemini: {exc}"
                continue
            if res.status_code in (401, 403):
                raise RuntimeError("Gemini API key was rejected. Create a new key at https://aistudio.google.com/apikey")
            if res.status_code == 429:
                raise RuntimeError("Gemini is busy (rate limit). Wait a moment and try again.")
            if res.status_code in (404, 400) and "not found" in (res.text or "").lower():
                last_err = f"{model} not available"
                continue
            if res.status_code >= 400:
                last_err = f"Gemini HTTP {res.status_code}: {res.text[:240]}"
                if "responseMimeType" in (res.text or ""):
                    payload.get("generationConfig", {}).pop("responseMimeType", None)
                    continue
                continue
            body = res.json()
            err = body.get("error") or {}
            if err:
                last_err = err.get("message") or str(err)
                continue
            parts = (
                ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            )
            text = "".join(p.get("text") or "" for p in parts)
            if not text:
                last_err = "Gemini returned an empty reading"
                continue
            logger.info("[AI OCR] Gemini model=%s", model)
            return _extract_json(text)
    raise RuntimeError(last_err)


def _call_openai(jpeg_bytes: bytes, api_key: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    payload = {
        "model": getattr(settings, "OPENAI_VISION_MODEL", None) or "gpt-4o-mini",
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or _DAYBOOK_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ],
        }],
    }
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
        res = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
    if res.status_code in (401, 403):
        raise RuntimeError("OpenAI API key was rejected. Check OPENAI_API_KEY in .env.")
    if res.status_code >= 400:
        raise RuntimeError(f"OpenAI HTTP {res.status_code}: {res.text[:240]}")
    body = res.json()
    text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    return _extract_json(text)


def extract_figures_from_image(image_bytes: bytes, prompt: Optional[str] = None) -> Dict[str, Any]:
    jpeg = _jpeg_for_ai(image_bytes)
    gemini_key = get_gemini_api_key()
    if gemini_key:
        return _call_gemini(jpeg, gemini_key, prompt=prompt)
    openai_key = get_openai_api_key()
    if openai_key:
        return _call_openai(jpeg, openai_key, prompt=prompt)
    raise RuntimeError(missing_key_message())


def extract_daybook_with_ai(image_bytes: bytes, filename: str) -> Dict[str, Any]:
    t0 = datetime.now()
    parsed = extract_figures_from_image(image_bytes)

    cash = _num(parsed.get("cash"))
    credit = _num(parsed.get("credit_card"))
    paytm = _num(parsed.get("paytm"))
    upi = _num(parsed.get("upi"))
    card_parts = [v for v in (credit, paytm, upi) if v is not None]
    card_qr = sum(card_parts) if card_parts else None
    zomato = _num(parsed.get("zomato"))
    swiggy = _num(parsed.get("swiggy"))
    dineout = _num(parsed.get("dineout"))
    opening = _num(parsed.get("opening_balance"))
    expenses = _num(parsed.get("site_expenses"))
    salary = _num(parsed.get("salary_advance"))
    today_sale = _num(parsed.get("today_sale"))
    closing = _num(parsed.get("closing_balance") or parsed.get("actual_closing_balance"))
    if closing is None and opening is not None and cash is not None:
        closing = round((opening or 0) + (cash or 0) - (expenses or 0) - (salary or 0), 2)

    items_in = parsed.get("expense_items") or []
    itemized: List[Dict[str, Any]] = []
    for i, item in enumerate(items_in, start=1):
        if not isinstance(item, dict):
            continue
        amt = _num(item.get("amount"))
        desc = str(item.get("description") or "").strip()
        if amt is None and not desc:
            continue
        itemized.append({
            "row_id": i,
            "description": desc,
            "amount_raw": "" if amt is None else str(amt),
            "amount": amt,
            "amount_crop_b64": "",
            "why_selected": "Gemini vision",
            "numeric_validation_score": 90.0,
            "status": "CONFIRMED",
        })
    if expenses is None and itemized:
        expenses = sum(i["amount"] or 0.0 for i in itemized) or None

    fields = {
        "cash": _field(cash, "Cash sale"),
        "card_qr": _field(card_qr, "Credit Card + Paytm"),
        "zomato": _field(zomato, "Zomato"),
        "swiggy": _field(swiggy, "Swiggy"),
        "dineout": _field(dineout, "Dineout"),
        "opening_balance": _field(opening, "Opening"),
        "closing_balance": _field(closing, "Closing"),
        "site_expenses": _field(expenses, "Site expenses"),
        "salary_advance": _field(salary, "Salary advance"),
    }
    if itemized and fields["site_expenses"]["value"] is not None:
        fields["site_expenses"]["items"] = itemized
        fields["site_expenses"]["source_description"] = f"{len(itemized)} Expense Items"

    calc_total = round(
        (cash or 0.0) + (card_qr or 0.0) + (zomato or 0.0) + (swiggy or 0.0) + (dineout or 0.0),
        2,
    )
    total_diff = round(today_sale - calc_total, 2) if today_sale is not None else 0.0
    raw_date = parsed.get("date")
    detected_date = _normalize_date(raw_date, filename)
    date_from_document = bool(str(raw_date or "").strip())
    elapsed = round((datetime.now() - t0).total_seconds(), 2)

    parsed_rows = []
    for label, amt in (
        ("Opening", opening),
        ("Today Sale", today_sale),
        ("Cash sale", cash),
        ("Credit Card", credit),
        ("Paytm", paytm),
        ("Swiggy", swiggy),
        ("Zomato", zomato),
        ("Dineout", dineout),
        ("Salary advance", salary),
        ("Closing", closing),
    ):
        if amt is None:
            continue
        parsed_rows.append({
            "row_id": len(parsed_rows) + 1,
            "description_raw": label,
            "amount": amt,
            "amount_raw": str(amt),
            "status": "AI_READ",
        })
    for item in itemized:
        parsed_rows.append({
            "row_id": len(parsed_rows) + 1,
            "description_raw": item["description"],
            "amount": item["amount"],
            "amount_raw": item["amount_raw"],
            "status": "AI_READ",
        })

    image_kind = normalize_image_kind(parsed.get("image_kind"))
    logger.info(
        "[AI OCR] DONE %.2fs kind=%s cash=%s card=%s zomato=%s swiggy=%s dineout=%s",
        elapsed, image_kind, cash, card_qr, zomato, swiggy, dineout,
    )

    return {
        "status": "SUCCESS",
        "image_kind": image_kind,
        "ocr_engine": "gemini" if get_gemini_api_key() else "openai",
        "filename": filename,
        "date": detected_date,
        "date_from_document": date_from_document,
        "date_confidence": 0.9,
        "cash": cash,
        "card_qr": card_qr,
        "zomato": zomato,
        "swiggy": swiggy,
        "dineout": dineout,
        "opening_balance": opening,
        "site_expenses": expenses,
        "salary_advance": salary,
        "closing_balance": closing,
        "fields": fields,
        "parsed_rows": parsed_rows,
        "itemized_expenses": itemized,
        "extraction_result": parsed,
        "extraction_trace": {"ai_json": parsed, "engine": "online_vision"},
        "raw_ocr_response": parsed,
        "handwritten_total": today_sale,
        "calculated_total": calc_total,
        "total_difference": total_diff,
        "image_b64": "",
        "preprocessed_image_b64": "",
        "amount_crop_b64": "",
        "annotated_row_boxes_b64": "",
        "raw_text": json.dumps(parsed, ensure_ascii=False),
        "processing_time_sec": elapsed,
        "source_images": [{
            "filename": filename,
            "image_kind": image_kind,
            "label": KIND_LABELS.get(image_kind, image_kind),
        }],
        "field_sources": {},
        "mismatches": [],
        "verifications": [],
    }


def _reading_value(reading: Dict[str, Any], field: str) -> Any:
    if field == "date":
        if reading.get("date_from_document") is False:
            return None
        return reading.get("date") or None
    val = reading.get(field)
    if val is None or val == "":
        return None
    return val


def _pick_field(
    readings: List[Dict[str, Any]], field: str
) -> Tuple[Any, Optional[str], Optional[Dict[str, Any]]]:
    by_kind: Dict[str, Tuple[Any, Dict[str, Any]]] = {}
    for reading in readings:
        kind = normalize_image_kind(reading.get("image_kind"))
        val = _reading_value(reading, field)
        if val is None:
            continue
        if kind not in by_kind:
            by_kind[kind] = (val, reading)
    for kind in FIELD_PRIORITY.get(field, ["DAYBOOK", "PETPOOJA", "EDC", "OTHER"]):
        if kind in by_kind:
            return by_kind[kind][0], kind, by_kind[kind][1]
    if by_kind:
        kind, pair = next(iter(by_kind.items()))
        return pair[0], kind, pair[1]
    return None, None, None


def _values_by_kind(readings: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for reading in readings:
        kind = normalize_image_kind(reading.get("image_kind"))
        val = _reading_value(reading, field)
        if val is None:
            continue
        out.setdefault(kind, val)
    return out


def _amounts_close(a: Any, b: Any, tol: float = 1.0) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


def merge_register_readings(readings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine 1–5 same-day photos. Each figure is taken from the most
    appropriate source (cash book vs POS vs card machine), never averaged.
    """
    usable = [r for r in readings if r and r.get("status") != "ERROR"]
    if not usable:
        first = readings[0] if readings else {}
        return first or {"status": "ERROR", "error_detail": "No images could be read"}
    if len(usable) == 1:
        one = dict(usable[0])
        kind = normalize_image_kind(one.get("image_kind"))
        one.setdefault("source_images", [{
            "filename": one.get("filename") or "",
            "image_kind": kind,
            "label": KIND_LABELS.get(kind, kind),
        }])
        one.setdefault("field_sources", {})
        one.setdefault("mismatches", [])
        one.setdefault("verifications", [])
        return one

    merged = dict(usable[0])
    field_sources: Dict[str, str] = {}
    merge_fields = (
        "date", "cash", "card_qr", "zomato", "swiggy", "dineout",
        "opening_balance", "site_expenses", "salary_advance", "closing_balance",
    )
    for field in merge_fields:
        val, kind, source = _pick_field(usable, field)
        merged[field] = val
        if kind:
            field_sources[field] = kind
            if field != "date" and source and isinstance(source.get("fields"), dict):
                src_field = dict((source["fields"].get(field) or {}))
                if src_field:
                    src_field["why_selected"] = (
                        f"{KIND_LABELS.get(kind, kind)} — {src_field.get('why_selected') or field}"
                    )
                    merged.setdefault("fields", {})[field] = src_field

    daybook = next(
        (r for r in usable if normalize_image_kind(r.get("image_kind")) == "DAYBOOK"),
        None,
    )
    if daybook:
        if daybook.get("itemized_expenses"):
            merged["itemized_expenses"] = daybook["itemized_expenses"]
        if daybook.get("handwritten_total") is not None:
            merged["handwritten_total"] = daybook["handwritten_total"]

    cash = merged.get("cash")
    card_qr = merged.get("card_qr")
    zomato = merged.get("zomato")
    swiggy = merged.get("swiggy")
    dineout = merged.get("dineout")
    calc_total = round(
        (cash or 0.0) + (card_qr or 0.0) + (zomato or 0.0) + (swiggy or 0.0) + (dineout or 0.0),
        2,
    )
    merged["calculated_total"] = calc_total
    today_sale = merged.get("handwritten_total")
    merged["total_difference"] = (
        round(today_sale - calc_total, 2) if today_sale is not None else 0.0
    )

    mismatches: List[Dict[str, Any]] = []
    verifications: List[Dict[str, Any]] = []
    dates = _values_by_kind(usable, "date")
    unique_dates = {str(v) for v in dates.values() if v}
    if len(unique_dates) > 1:
        mismatches.append({
            "field": "date",
            "values": dates,
            "message": "Photos show different dates: " + ", ".join(
                f"{KIND_LABELS.get(k, k)} {v}" for k, v in dates.items()
            ) + ".",
        })
    for field, kind_a, kind_b in VERIFY_PAIRS:
        values = _values_by_kind(usable, field)
        if kind_a not in values or kind_b not in values:
            continue
        a, b = values[kind_a], values[kind_b]
        label = "Cash" if field == "cash" else "Card/QR"
        if _amounts_close(a, b):
            verifications.append({
                "field": field,
                "value": a,
                "message": (
                    f"{label} matches {KIND_LABELS[kind_a].lower()} and "
                    f"{KIND_LABELS[kind_b].lower()} (₹{float(a):,.0f})."
                ),
            })
        else:
            mismatches.append({
                "field": field,
                "values": values,
                "message": (
                    f"{label} differs: {KIND_LABELS[kind_a]} ₹{float(a):,.0f} vs "
                    f"{KIND_LABELS[kind_b]} ₹{float(b):,.0f}."
                ),
            })

    source_images = []
    for reading in usable:
        kind = normalize_image_kind(reading.get("image_kind"))
        source_images.append({
            "filename": reading.get("filename") or "",
            "image_kind": kind,
            "label": KIND_LABELS.get(kind, kind),
            "date": reading.get("date"),
            "cash": reading.get("cash"),
            "card_qr": reading.get("card_qr"),
            "zomato": reading.get("zomato"),
            "swiggy": reading.get("swiggy"),
            "dineout": reading.get("dineout"),
            "opening_balance": reading.get("opening_balance"),
            "site_expenses": reading.get("site_expenses"),
            "closing_balance": reading.get("closing_balance"),
        })

    parsed_rows: List[Dict[str, Any]] = []
    for reading in usable:
        kind = normalize_image_kind(reading.get("image_kind"))
        for row in reading.get("parsed_rows") or []:
            extra = dict(row)
            extra["source_kind"] = kind
            extra["source_filename"] = reading.get("filename") or ""
            parsed_rows.append(extra)

    merged["status"] = "SUCCESS"
    merged["image_kind"] = "MERGED"
    merged["source_images"] = source_images
    merged["field_sources"] = field_sources
    merged["mismatches"] = mismatches
    merged["verifications"] = verifications
    merged["parsed_rows"] = parsed_rows
    merged["extraction_trace"] = {
        "merged": True,
        "field_sources": field_sources,
        "sources": source_images,
        "mismatches": mismatches,
        "verifications": verifications,
    }
    merged["processing_time_sec"] = round(
        sum(float(r.get("processing_time_sec") or 0) for r in usable), 2
    )
    return merged


def extract_and_merge_register_images(
    items: List[Tuple[bytes, str]],
) -> Dict[str, Any]:
    readings = []
    errors = []
    for content, name in items:
        try:
            one = extract_daybook_with_ai(content, name)
            one["filename"] = name
            if one.get("status") == "ERROR":
                errors.append({"filename": name, "error": one.get("error_detail")})
                continue
            readings.append(one)
        except Exception as exc:
            errors.append({"filename": name, "error": str(exc)})
    if not readings:
        detail = errors[0]["error"] if errors else "No images could be read"
        return {"status": "ERROR", "error_detail": detail, "partial_errors": errors}
    merged = merge_register_readings(readings)
    if errors:
        merged["partial_errors"] = errors
    return merged
