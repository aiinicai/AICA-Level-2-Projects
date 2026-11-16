"""Finnhub Calendar adapter for real-time global and Indian financial releases.
Supports macroeconomic indicators (when permitted), live corporate earnings announcements,
and IPO calendars on the free tier at https://finnhub.io (60 calls/minute).
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import re

from app.data_sources.http import SourceError
from app.utils.time import normalize_time, stamp


class FinnhubAdapter:
    def __init__(self, http):
        self.http = http

    def fetch(self, source, credential=None):
        if not credential:
            raise SourceError("Enter your free Finnhub API key in Settings (sign up at finnhub.io)", "Not Configured")
        
        credential = str(credential).strip().strip('"\'')
        config = dict(source.get("config", {}))
        today = date.today()
        start = date.fromisoformat(config["start_date"]) if config.get("start_date") else today - timedelta(days=int(config.get("days_back", 7)))
        end = date.fromisoformat(config["end_date"]) if config.get("end_date") else today + timedelta(days=int(config.get("days_ahead", 30)))
        
        if start > end or (end - start).days > 366:
            raise SourceError("Choose an economic calendar range of at most 366 days")
        
        records = []
        economic_attempted = False

        # 1. Attempt Macroeconomic Calendar (available on institutional/standard tiers)
        if not config.get("economic_restricted", False):
            try:
                url = "https://finnhub.io/api/v1/calendar/economic"
                params = {
                    "token": credential,
                    "from": start.isoformat(),
                    "to": end.isoformat()
                }
                response = self.http.get(url, params=params)
                data = response.json()
                if isinstance(data, dict) and "economicCalendar" in data:
                    economic_attempted = True
                    calendar = data.get("economicCalendar", [])
                    for item in calendar:
                        event_name = item.get("event") or "Economic release"
                        country = item.get("country") or "Global"
                        raw_time = item.get("time")
                        
                        scheduled_at = None
                        if raw_time:
                            try:
                                dt = datetime.strptime(raw_time.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                                scheduled_at = stamp(dt)
                            except ValueError:
                                try:
                                    d = datetime.strptime(raw_time.strip(), "%Y-%m-%d").date()
                                    scheduled_at = d.isoformat()
                                except ValueError:
                                    scheduled_at = raw_time.strip()
                        
                        actual = item.get("actual")
                        estimate = item.get("estimate")
                        prev = item.get("prev")
                        unit = item.get("unit") or ""
                        impact = str(item.get("impact", "medium")).lower()
                        importance = "High" if impact == "high" else ("Low" if impact == "low" else "Medium")
                        
                        is_published = actual is not None and str(actual).strip() != ""
                        status = "Published" if is_published else "Scheduled"
                        
                        raw_id = f"finnhub-{country}-{event_name}-{raw_time}"
                        external_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:24]
                        
                        name_lower = event_name.lower()
                        if any(w in name_lower for w in ("cpi", "inflation", "ppi", "wpi", "price")):
                            category = "Inflation"
                        elif any(w in name_lower for w in ("rate", "interest", "fomc", "central bank", "mpc", "repo")):
                            category = "Interest rates"
                        elif any(w in name_lower for w in ("gdp", "growth", "gross domestic")):
                            category = "GDP"
                        elif any(w in name_lower for w in ("payroll", "employment", "unemployment", "job", "labor")):
                            category = "Employment"
                        elif any(w in name_lower for w in ("pmi", "manufacturing", "services", "industrial", "production")):
                            category = "Production"
                        elif any(w in name_lower for w in ("trade", "export", "import", "current account")):
                            category = "Trade"
                        else:
                            category = "Economic release"
                        
                        records.append(dict(
                            external_id=external_id,
                            kind="Economic",
                            title=f"{event_name} ({country})",
                            category=category,
                            country=country,
                            authority="Finnhub Economic Calendar",
                            indicator=event_name,
                            series_key=f"FINNHUB:{country}:{event_name}",
                            reporting_period="",
                            scheduled_at=scheduled_at,
                            published_at=scheduled_at if is_published else None,
                            source_updated_at=stamp(datetime.now(timezone.utc)),
                            status=status,
                            date_confirmed=bool(scheduled_at and ":" in str(scheduled_at)),
                            previous=str(prev) if prev is not None else None,
                            forecast=str(estimate) if estimate is not None else None,
                            actual=str(actual) if actual is not None else None,
                            unit=unit,
                            importance=importance,
                            summary=f"Live economic announcement retrieved from Finnhub API. Impact: {importance}. Currency: {item.get('currency', 'N/A')}.",
                            verification="Live Finnhub API feed",
                            source_url="https://finnhub.io"
                        ))
            except SourceError as e:
                if "403" in str(e) or getattr(e, "status", "") == "Restricted":
                    config["economic_restricted"] = True
                else:
                    raise

        # 2. Free Tier Support: Fetch Corporate Earnings Calendar & IPOs if economic was restricted or alongside
        if not records:
            try:
                earn_url = "https://finnhub.io/api/v1/calendar/earnings"
                params = {
                    "token": credential,
                    "from": start.isoformat(),
                    "to": end.isoformat()
                }
                res_earn = self.http.get(earn_url, params=params)
                data_earn = res_earn.json()
                for item in data_earn.get("earningsCalendar", [])[:300]:
                    sym = item.get("symbol") or "Unknown"
                    dt_str = item.get("date")
                    if not dt_str:
                        continue
                    qtr = item.get("quarter", 3)
                    yr = item.get("year", today.year)
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
                        country="India" if any(sym.endswith(sfx) for sfx in (".NS", ".BO", ".IN")) else "Global",
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
                        importance="High" if any(sym.endswith(sfx) for sfx in (".NS", ".BO", ".IN")) or sym in ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META") else "Medium",
                        summary=f"Official quarterly corporate results for {sym} (Q{qtr} {yr}). EPS Consensus: {eps_est or 'N/A'}, Actual: {eps_act or 'Pending'}. Revenue Consensus: {rev_est or 'N/A'}, Actual: {rev_act or 'Pending'}.",
                        verification="Live Finnhub API feed (free tier)",
                        source_url="https://finnhub.io"
                    ))
            except Exception:
                pass

            # Fetch IPO listings
            try:
                ipo_url = "https://finnhub.io/api/v1/calendar/ipo"
                params = {
                    "token": credential,
                    "from": start.isoformat(),
                    "to": end.isoformat()
                }
                res_ipo = self.http.get(ipo_url, params=params)
                data_ipo = res_ipo.json()
                for item in data_ipo.get("ipoCalendar", []):
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
                        country="India" if "india" in str(item.get("exchange", "")).lower() else "Global",
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
            except Exception:
                pass

        if not records:
            raise SourceError("Finnhub returned 0 records. Ensure your token is active at finnhub.io.", "Stale")
            
        return records, config
