from dataclasses import fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
from urllib.parse import urlsplit

from app.models.events import DATE_FIELDS, IMPORTANCE, KINDS, STATUSES, Event
from app.utils.time import normalize_time


class ValidationError(ValueError):
    pass


def boolean(value, default=False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if str(value).lower().strip() in ("true", "1", "yes"):
        return True
    if str(value).lower().strip() in ("false", "0", "no"):
        return False
    raise ValidationError(f"Invalid boolean: {value}")


def clean_value(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in ("", "nan", "nat", "none", "null", "n/a", "na", "--") else text


def numeric(value: str | None, unit: str = "") -> Decimal | None:
    if value is None:
        return None
    try:
        text=value.replace(",", "").strip()
        if unit and text.endswith(unit):
            text=text[:-len(unit)].strip()
        number = Decimal(text)
        return number if number.is_finite() else None
    except InvalidOperation:
        return None  # Preserve source strings/ranges; never guess a multiplier or unit.


def safe_url(value: str) -> str:
    if not value:
        return ""
    url = urlsplit(value)
    if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password:
        raise ValidationError("Source/document URLs must be public HTTP(S) links without credentials")
    return value


def validate_event(record: dict, source_id: str | None = None, sample: bool | None = None) -> Event:
    if not isinstance(record, dict):
        raise ValidationError("Each event must be an object")
    allowed = {f.name for f in fields(Event)}
    data = {k: v for k, v in record.items() if k in allowed}
    for key, value in list(data.items()):
        if key not in ("sample", "date_confirmed", "original_times"):
            data[key] = clean_value(value)
    if source_id:
        data["source_id"] = source_id
    data["sample"] = boolean(data.get("sample")) if sample is None else sample
    data["date_confirmed"] = boolean(data.get("date_confirmed"), True)
    for key in ("source_id", "kind", "title", "category"):
        if not data.get(key):
            raise ValidationError(f"Missing required field: {key}")
    if data["kind"] not in KINDS:
        raise ValidationError("kind must be Economic, Corporate or Regulatory")
    data["status"] = data.get("status") or "Published"
    data["importance"] = data.get("importance") or "Unknown"
    if data["status"] not in STATUSES or data["importance"] not in IMPORTANCE:
        raise ValidationError("Invalid status or importance")
    data["source_url"] = safe_url(data.get("source_url") or "")
    data["document_url"] = safe_url(data.get("document_url") or "")
    if not data["sample"] and not data["source_url"]:
        raise ValidationError("Non-sample records require their original source URL")
    original = data.get("original_times") or {}
    if isinstance(original, str):
        original = json.loads(original)
    for key in DATE_FIELDS:
        original.setdefault(key, data.get(key))
        try:
            data[key] = normalize_time(data.get(key), data.get("source_timezone"))
        except (ValueError, KeyError) as exc:
            raise ValidationError(f"{key}: {exc}") from exc
    data["original_times"] = original
    if not any(data.get(k) for k in ("scheduled_at", "published_at", "effective_at", "deadline_at")):
        raise ValidationError("At least one event/publication/effective/deadline date is required")
    if data["status"] in ("Scheduled", "Tentative") and not data["scheduled_at"]:
        raise ValidationError("Scheduled/tentative events need a scheduled date")
    if data["status"] == "Tentative":
        data["date_confirmed"] = False
    if not data["date_confirmed"] and data["status"] == "Scheduled":
        data["status"] = "Tentative"
    if not data.get("external_id"):
        identity = [data.get(k) for k in ("source_url", "title", "kind", "company", "reporting_period")]
        data["external_id"] = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    for f in fields(Event):
        if f.name in data and data[f.name] is None and isinstance(f.default, str):
            data[f.name] = ""
    data["isin"] = data.get("isin", "").upper()
    for key in ("previous", "forecast", "actual", "revised", "provider_forecast"):
        data[key] = clean_value(data.get(key))
    return Event(**data)
