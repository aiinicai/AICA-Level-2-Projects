from datetime import datetime, timedelta, timezone

from ipt.core.timefmt import fmt, local


def test_utc_db_time_shown_as_local():
    utc = datetime(2026, 11, 22, 5, 0, 0)
    offset = datetime.now(timezone.utc).astimezone().utcoffset()
    assert local(utc) == utc + offset
    assert fmt(None) == "" and fmt(utc, seconds=True).endswith(":00")
    assert isinstance(timedelta, type)
