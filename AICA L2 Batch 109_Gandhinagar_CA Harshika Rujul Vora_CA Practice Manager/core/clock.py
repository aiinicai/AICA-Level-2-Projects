"""Indian Standard Time everywhere, so a hosted server (which runs on UTC) shows the firm's real date and time.
India has no daylight saving, so a fixed +05:30 offset is exact and needs no timezone database."""
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def now() -> datetime:
    """Current Indian time as a naive datetime (matches the text timestamps stored in the database)."""
    return datetime.now(IST).replace(tzinfo=None)


def today() -> date:
    return now().date()
