import json
import hashlib
from datetime import datetime, timezone

from app.data_sources.http import HttpClient, SourceError
from app.utils.time import stamp

http = HttpClient()
token = "dbrkqdhr01qvp4idje20dbrkqdhr01qvp4idje2g"

records = []
# 1. Try economic calendar
try:
    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {"token": token, "from": "2026-11-01", "to": "2026-11-30"}
    res = http.get(url, params=params)
    data = res.json()
    items = data.get("economicCalendar", [])
    print(f"Economic items: {len(items)}")
except SourceError as e:
    print(f"Economic calendar restricted on free tier: {e}")

# 2. Fetch Corporate Earnings Calendar (Free tier supported!)
try:
    earn_url = "https://finnhub.io/api/v1/calendar/earnings"
    params = {"token": token, "from": "2026-11-01", "to": "2026-11-30"}
    res = http.get(earn_url, params=params)
    data = res.json()
    items = data.get("earningsCalendar", [])
    print(f"Earnings calendar items: {len(items)}")
    for item in items[:20]:
        sym = item.get("symbol") or "Unknown"
        dt_str = item.get("date")
        if not dt_str:
            continue
        qtr = item.get("quarter", 3)
        yr = item.get("year", 2026)
        eps_act = item.get("epsActual")
        eps_est = item.get("epsEstimate")
        rev_act = item.get("revenueActual")
        rev_est = item.get("revenueEstimate")
        is_published = eps_act is not None or rev_act is not None
        raw_id = f"finnhub-earnings-{sym}-{dt_str}-Q{qtr}-{yr}"
        ext_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:24]
        records.append(dict(
            external_id=ext_id,
            kind="Corporate",
            title=f"{sym} Q{qtr} {yr} Financial Results Announcement",
            category="Financial results",
            country="Global",
            company=sym,
            symbol=sym,
            authority="Finnhub Corporate Earnings Calendar",
            indicator="Quarterly Financial Results",
            series_key=f"FINNHUB:{sym}:EPS",
            reporting_period=f"Q{qtr} {yr}",
            scheduled_at=dt_str + "T09:00:00+00:00",
            published_at=dt_str + "T09:00:00+00:00" if is_published else None,
            source_updated_at=stamp(datetime.now(timezone.utc)),
            status="Published" if is_published else "Scheduled",
            date_confirmed=True,
            previous=None,
            forecast=str(eps_est) if eps_est is not None else None,
            actual=str(eps_act) if eps_act is not None else None,
            unit="EPS ($)",
            importance="High" if any(sym.endswith(suffix) for suffix in (".NS", ".BO", ".IN")) or sym in ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META") else "Medium",
            summary=f"Official quarterly corporate results for {sym} (Q{qtr} {yr}). EPS Consensus: {eps_est or 'N/A'}, Actual: {eps_act or 'Pending'}. Revenue Consensus: {rev_est or 'N/A'}, Actual: {rev_act or 'Pending'}.",
            verification="Live Finnhub API feed (free tier)",
            source_url="https://finnhub.io"
        ))
except Exception as e:
    print(f"Earnings failed: {e}")

# 3. Fetch IPO Calendar (Free tier supported!)
try:
    ipo_url = "https://finnhub.io/api/v1/calendar/ipo"
    params = {"token": token, "from": "2026-11-01", "to": "2026-11-30"}
    res = http.get(ipo_url, params=params)
    data = res.json()
    items = data.get("ipoCalendar", [])
    print(f"IPO calendar items: {len(items)}")
    for item in items:
        name = item.get("name") or "New IPO"
        sym = item.get("symbol") or ""
        dt_str = item.get("date")
        if not dt_str:
            continue
        price = item.get("price") or "N/A"
        shares = item.get("numberOfShares") or "N/A"
        status_raw = item.get("status") or "expected"
        status = "Published" if status_raw in ("priced", "traded") else "Scheduled"
        raw_id = f"finnhub-ipo-{name}-{dt_str}"
        ext_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:24]
        records.append(dict(
            external_id=ext_id,
            kind="Corporate",
            title=f"IPO Listing: {name} ({sym})" if sym else f"IPO Listing: {name}",
            category="Capital structure",
            country="Global",
            company=name,
            symbol=sym,
            authority="Finnhub IPO Calendar",
            indicator="Initial Public Offering",
            series_key="",
            reporting_period="",
            scheduled_at=dt_str + "T09:00:00+00:00",
            published_at=dt_str + "T09:00:00+00:00" if status == "Published" else None,
            source_updated_at=stamp(datetime.now(timezone.utc)),
            status=status,
            date_confirmed=True,
            previous=None,
            forecast=str(price),
            actual=str(price) if status == "Published" else None,
            unit="Price Range ($)",
            importance="High",
            summary=f"Public listing announcement for {name} ({sym}) on {item.get('exchange', 'Exchange')}. Offering: {shares} shares at price {price}.",
            verification="Live Finnhub API feed (free tier)",
            source_url="https://finnhub.io"
        ))
except Exception as e:
    print(f"IPO failed: {e}")

print(f"TOTAL PARSED RECORDS: {len(records)}")
if records:
    print("First record:", records[0]["title"], records[0]["scheduled_at"])
