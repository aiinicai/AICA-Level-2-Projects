from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def stamp(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(UTC).isoformat(timespec="seconds")


def parse_instant(value: str | None) -> datetime | None:
    if not value or len(value) == 10:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("An exact timestamp must include an offset or a verified source timezone")
    return result.astimezone(UTC)


def normalize_time(value, source_timezone: str | None = None) -> str | None:
    if value is None or str(value).strip() in ("", "None", "null", "NaN", "nan", "NaT"):
        return None
    text = str(value).strip()
    if len(text) == 10:
        return date.fromisoformat(text).isoformat()
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        if not source_timezone:
            raise ValueError(f"Timestamp {text!r} has no offset/source timezone")
        zone = ZoneInfo(source_timezone)
        first, second = dt.replace(tzinfo=zone, fold=0), dt.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError("Ambiguous or nonexistent local time: supply an explicit UTC offset")
        if first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != dt:
            raise ValueError("Nonexistent local time")
        dt = first
    return stamp(dt)


def safe_zone(zone: str | None) -> ZoneInfo:
    if not zone:
        return ZoneInfo("Asia/Kolkata")
    try:
        return ZoneInfo(zone)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def display_time(value: str | None, zone: str = "Asia/Kolkata") -> str:
    if not value:
        return "Unavailable"
    if len(value) == 10:
        try:
            d = date.fromisoformat(value)
            return d.strftime("%d %b %Y") + " · date only"
        except Exception:
            return f"{value} · date only"
    try:
        instant = parse_instant(value)
        if not instant:
            return f"{value} · date only"
        dt = instant.astimezone(safe_zone(zone))
        return dt.strftime("%d %b %Y  %H:%M %Z")
    except Exception:
        return str(value)


def local_date(value: str | None, zone: str = "Asia/Kolkata") -> str | None:
    if not value:
        return None
    if len(value) == 10:
        return value
    try:
        instant = parse_instant(value)
        if not instant:
            return value[:10]
        return instant.astimezone(safe_zone(zone)).date().isoformat()
    except Exception:
        return str(value)[:10]


PRIMARY_ZONES = [
    "Asia/Kolkata",
    "America/New_York",
    "Europe/London",
    "Europe/Frankfurt",
    "Asia/Tokyo",
    "Asia/Singapore",
    "Australia/Sydney",
    "Australia/Perth",
    "UTC",
]


def zones() -> list[str]:
    all_z = sorted(available_timezones())
    return PRIMARY_ZONES + [z for z in all_z if z not in PRIMARY_ZONES]

