"""Market data provider — Module 1.

Abstracted behind MarketDataProvider so the concrete source (yfinance
today) can be swapped for a paid NSE feed later without touching
anything in analysis/technical.py or valuation/*.py, which only depend
on this interface.
"""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from app.core.models import Company

logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Raised when a market data fetch fails (network, invalid symbol, no data)."""


class MarketDataProvider(ABC):
    """Interface every price-data source must implement."""

    @abstractmethod
    def get_price_history(
        self, company: Company, start: date, end: date
    ) -> pd.DataFrame:
        """Return a DataFrame indexed by date with at least an 'close' column
        (also typically 'open', 'high', 'low', 'volume'). Raises
        MarketDataError if no data is available — never returns an empty
        DataFrame silently, since a downstream caller could mistake that
        for "flat/zero prices" rather than "fetch failed"."""

    @abstractmethod
    def get_current_price(self, company: Company) -> float | None:
        """Return the latest available price, or None if unavailable."""


def _parse_indian_number(s: str) -> float:
    """Parse a comma-formatted number (Indian digit grouping, e.g.
    '24,07,579' or '1,97,59,98,935.90') into a float. Python's float()
    can't handle embedded commas regardless of grouping style, so this
    just strips them — grouping position doesn't matter once removed."""
    return float(s.replace(",", "").strip())


def load_nse_csv_price_history(csv_path: Path) -> pd.DataFrame:
    """Load daily OHLCV history from an NSE bhavcopy-style CSV export
    (the format NSE's own website produces for a symbol's historical
    data download: columns Symbol/Series/Date/Prev Close/Open Price/
    High Price/Low Price/Last Price/Close Price/Average Price/Total
    Traded Quantity/Turnover/No. of Trades/Deliverable Qty/% Dly Qt).

    Handles the specific quirks of this export format:
    - UTF-8 BOM at the start of the file
    - Trailing whitespace in column headers
    - Indian-style comma-grouped numbers (e.g. "24,07,579") in
      quantity/turnover columns
    - Dates as "DD-Mon-YY" (e.g. "10-Aug-26")
    - Rows in descending (newest-first) date order — re-sorted ascending
      here since every downstream technical-indicator function expects
      chronological order

    Returns a DataFrame indexed by date with columns: open, high, low,
    close, volume — the same shape YFinanceProvider.get_price_history()
    returns, so both are interchangeable inputs to app/analysis/technical.py.
    """
    if not csv_path.exists():
        raise MarketDataError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    required = {"Date", "Series", "Open Price", "High Price", "Low Price", "Close Price", "Total Traded Quantity"}
    missing = required - set(df.columns)
    if missing:
        raise MarketDataError(
            f"{csv_path.name} is missing expected column(s): {sorted(missing)}. "
            f"Found columns: {list(df.columns)}. This loader expects the standard "
            "NSE historical-data CSV export format."
        )

    # NSE exports can include rows from non-continuous-trading series on
    # the same date as a normal "EQ" row — e.g. "BL" (Block Deal, large
    # negotiated trades reported outside the regular order book). Mixing
    # these into a daily OHLC series would corrupt it (a single block
    # trade's "OHLC" is really just one negotiated price, not a trading
    # range) and can produce duplicate dates. Restrict to the standard
    # continuous-market "EQ" series, which is what every downstream
    # technical indicator assumes.
    other_series = df.loc[df["Series"].str.strip() != "EQ", "Series"].unique().tolist()
    if other_series:
        excluded_count = int((df["Series"].str.strip() != "EQ").sum())
        logger.info(
            "%s: excluding %d row(s) from non-'EQ' series %s (e.g. Block "
            "Deal rows) — using only standard continuous-market trading days.",
            csv_path.name, excluded_count, other_series,
        )
    df = df.loc[df["Series"].str.strip() == "EQ"].reset_index(drop=True)

    result = pd.DataFrame(index=pd.to_datetime(df["Date"].str.strip(), format="%d-%b-%y"))
    result["open"] = df["Open Price"].astype(str).apply(_parse_indian_number).values
    result["high"] = df["High Price"].astype(str).apply(_parse_indian_number).values
    result["low"] = df["Low Price"].astype(str).apply(_parse_indian_number).values
    result["close"] = df["Close Price"].astype(str).apply(_parse_indian_number).values
    result["volume"] = df["Total Traded Quantity"].astype(str).apply(_parse_indian_number).values

    result = result.sort_index()  # ascending, oldest first

    if result.index.duplicated().any():
        dup_count = int(result.index.duplicated().sum())
        raise MarketDataError(
            f"{csv_path.name} contains {dup_count} duplicate date(s) after parsing. "
            "Refusing to silently pick one — check the source export for repeated rows."
        )

    return result


class CSVPriceProvider(MarketDataProvider):
    """Provider backed by a pre-downloaded NSE historical-data CSV export.

    This is the PRIMARY price data source for this project (per the
    person's own instruction): more reliable than a live network call,
    since it doesn't depend on this environment's network access or
    Yahoo Finance's NSE coverage. YFinanceProvider remains available as
    a live-refresh backup for dates beyond what a static CSV covers.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._df: pd.DataFrame | None = None  # lazy-loaded, cached

    def _load(self) -> pd.DataFrame:
        if self._df is None:
            self._df = load_nse_csv_price_history(self._csv_path)
        return self._df

    def get_price_history(self, company: Company, start: date, end: date) -> pd.DataFrame:
        df = self._load()
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        result = df.loc[mask]
        if result.empty:
            raise MarketDataError(
                f"No rows in {self._csv_path.name} fall within {start} to {end}. "
                f"CSV covers {df.index.min().date()} to {df.index.max().date()}."
            )
        return result

    def get_current_price(self, company: Company) -> float | None:
        df = self._load()
        if df.empty:
            return None
        return float(df["close"].iloc[-1])


class YFinanceProvider(MarketDataProvider):
    """Default provider using yfinance. No API key required."""

    def get_price_history(self, company: Company, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf  # imported lazily so Milestone 0/1 don't hard-require it at import time

        symbol = company.market_data_symbol
        logger.info("Fetching price history for %s from %s to %s", symbol, start, end)
        try:
            df = yf.download(
                symbol, start=start.isoformat(), end=end.isoformat(),
                progress=False, auto_adjust=True,
            )
        except Exception as exc:  # network/library failures — never silently swallowed
            raise MarketDataError(f"yfinance download failed for {symbol}: {exc}") from exc

        if df is None or df.empty:
            raise MarketDataError(
                f"No price data returned for {symbol} in range {start} to {end}. "
                "Check the ticker/exchange suffix, or try a wider date range."
            )

        # yfinance can return MultiIndex columns for a single-symbol download
        # depending on version; normalize to flat lowercase column names.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]

        return df

    def get_current_price(self, company: Company) -> float | None:
        import yfinance as yf

        symbol = company.market_data_symbol
        try:
            ticker = yf.Ticker(symbol)
            fast_info = ticker.fast_info
            price = fast_info.get("lastPrice") if fast_info else None
            if price is None:
                logger.warning("No current price available for %s", symbol)
                return None
            return float(price)
        except Exception as exc:
            logger.warning("Failed to fetch current price for %s: %s", symbol, exc)
            return None


class RediffMoneyProvider(MarketDataProvider):
    """Fallback provider using money.rediff.com HTML scraping.

    Ported from the person's own RediffDataPull_v2 VBA macro, which
    confirmed (via a live page dump) the actual markup for BSE
    Gainers/Losers listing pages:

        <tr><td><a>Company</a></td><td class="alignC">Group</td>
        <td class="alignR">PrevClose</td><td class="alignR">CurrPrice</td>
        <td class="alignR"><span class="green|red">+/- Change</span></td>...</tr>

    with pagination via a "Next" link containing `start=<digits>` in its
    href, and a "Showing X - Y of Z" total used to detect a short pull.
    The retry/stale-page-detection strategy (fingerprint the first row;
    if a retry returns an identical fingerprint, treat it as a stale
    cached copy and retry with a cache-busting param) is preserved here.

    SCOPE LIMIT — read before using get_price_history():
    The confirmed markup above is for the Gainers/Losers SNAPSHOT
    listing (today's movers), not a per-company historical OHLC page.
    Rediff's historical-data page structure was not part of the
    supplied macro and is therefore NOT verified here. Accordingly:

      - get_current_price() is implemented: it scans the Gainers/Losers
        tables (Groups A/B/T) for a company-name match. This only
        finds a price if the stock is CURRENTLY among that day's
        top movers in one of those groups — it is a best-effort
        fallback, not a general-purpose quote lookup, and will
        legitimately return None most days for most stocks.
      - get_price_history() raises NotImplementedError rather than
        guess an unverified page structure. If you have (or can find)
        a saved HTML dump of Rediff's per-company historical price
        page, send it and I will implement this properly against
        confirmed markup instead of a guess.

    For actual historical OHLC / technical analysis (Module 6),
    YFinanceProvider remains the primary provider.
    """

    _ROW_PATTERN = re.compile(
        r"<tr>\s*<td>(?:<a[^>]*>)?([^<]+)(?:</a>)?</td>\s*"
        r'<td class="alignC">([A-Za-z]+)</td>\s*'
        r'<td class="alignR">([\d,\.]+)</td>\s*'
        r'<td class="alignR">([\d,\.]+)</td>\s*'
        r'<td class="alignR">(?:<span[^>]*>)?\s*([+\-]?[\s\d,\.]+)(?:</span>)?</td>',
        re.IGNORECASE | re.MULTILINE,
    )
    _NEXT_LINK_PATTERN = re.compile(
        r"href=(['\"])([^'\"]*start=\d+[^'\"]*)\1[^>]*>\s*(?:<u>)?\s*Next",
        re.IGNORECASE,
    )
    _TOTAL_PATTERN = re.compile(r"Showing\s+\d+\s*-\s*\d+\s*of\s*(\d+)", re.IGNORECASE)

    _GROUPS = ("A", "B", "T")
    _MAX_RETRIES = 4
    _MAX_PAGES_PER_SECTION = 60
    _RETRY_WAIT_SECONDS = 0.9
    _INTER_PAGE_WAIT_SECONDS = 0.5

    def __init__(self, request_timeout_seconds: int = 15) -> None:
        self._timeout = request_timeout_seconds

    @staticmethod
    def _clean_num(s: str) -> float | None:
        """Port of VBA CleanNum: strips commas/%/all whitespace (including
        the embedded double-space Rediff renders in "+  10.20") so the
        result parses as a float."""
        x = s.replace("\xa0", " ").replace(",", "").replace("%", "")
        x = "".join(x.split())  # strip ALL whitespace, not just ends
        try:
            return float(x)
        except ValueError:
            return None

    @staticmethod
    def _normalize_url(u: str) -> str:
        result = u.strip().replace("&amp;", "&")
        if result.startswith("//"):
            result = "https:" + result
        return result

    def _get_html(self, url: str) -> str:
        import requests

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=self._timeout)
            if resp.status_code == 200:
                return resp.text
            return ""
        except Exception as exc:
            logger.warning("Rediff GET failed for %s: %s", url, exc)
            return ""

    def _parse_page(self, html: str) -> tuple[list[tuple], str | None, int]:
        """Returns (rows, next_url, total_count). Each row is
        (company_name, group, prev_close, curr_price, pct_change)."""
        rows: list[tuple] = []
        for m in self._ROW_PATTERN.finditer(html):
            company = m.group(1).strip()
            group = m.group(2).strip()
            prev = self._clean_num(m.group(3))
            curr = self._clean_num(m.group(4))
            chg = self._clean_num(m.group(5))
            if company and prev is not None and curr is not None and chg is not None:
                rows.append((company, group, prev, curr, chg))

        next_url = None
        next_match = self._NEXT_LINK_PATTERN.search(html)
        if next_match:
            next_url = self._normalize_url(next_match.group(2))

        total = 0
        total_match = self._TOTAL_PATTERN.search(html)
        if total_match:
            total = int(total_match.group(1))

        return rows, next_url, total

    def _fetch_all_pages_once(self, base_url: str) -> tuple[list[tuple], int]:
        all_rows: list[tuple] = []
        current_url: str | None = base_url
        last_signature: str | None = None
        page_count = 0
        expected_total = 0

        while current_url and page_count < self._MAX_PAGES_PER_SECTION:
            page_count += 1
            got_good_page = False
            page_rows: list[tuple] = []
            next_url: str | None = None

            for attempt in range(1, self._MAX_RETRIES + 1):
                request_url = current_url
                if attempt > 1:
                    sep = "&" if "?" in request_url else "?"
                    request_url = f"{request_url}{sep}_cb={int(time.time() * 1000)}"

                html = self._get_html(request_url)
                if not html:
                    logger.debug(
                        "Rediff fetch empty (page %d attempt %d): %s", page_count, attempt, request_url
                    )
                    time.sleep(self._RETRY_WAIT_SECONDS)
                    continue

                page_rows, next_url, page_total = self._parse_page(html)
                if page_count == 1 and page_total:
                    expected_total = page_total

                if not page_rows:
                    got_good_page = True  # genuinely no more data
                    break

                signature = f"{page_rows[0][0]}|{page_rows[0][3]}"
                if page_count > 1 and signature == last_signature:
                    logger.debug(
                        "Rediff stale page detected (page %d attempt %d): %s",
                        page_count, attempt, signature,
                    )
                    time.sleep(self._RETRY_WAIT_SECONDS)
                    continue

                got_good_page = True
                last_signature = signature
                break

            if not got_good_page:
                logger.warning(
                    "Rediff: gave up after %d attempts on page %d of %s",
                    self._MAX_RETRIES, page_count, base_url,
                )
                break
            if not page_rows:
                break

            all_rows.extend(page_rows)

            if not next_url or next_url == current_url:
                break
            current_url = next_url
            time.sleep(self._INTER_PAGE_WAIT_SECONDS)

        return all_rows, expected_total

    def _fetch_section(self, base_url: str, max_section_attempts: int = 3) -> list[tuple]:
        """Port of FetchAllPages: retries the WHOLE section if the pull
        came up short of Rediff's own stated total, rather than silently
        keeping a partial result."""
        best_rows: list[tuple] = []
        for section_attempt in range(1, max_section_attempts + 1):
            rows, expected_total = self._fetch_all_pages_once(base_url)
            if len(rows) > len(best_rows):
                best_rows = rows
            if expected_total == 0 or len(rows) >= expected_total:
                break
            logger.info(
                "Rediff section %s got %d of %d, retrying (attempt %d)",
                base_url, len(rows), expected_total, section_attempt,
            )
            time.sleep(1.2)
        return best_rows

    def get_price_history(self, company: Company, start: date, end: date) -> pd.DataFrame:
        raise NotImplementedError(
            "RediffMoneyProvider.get_price_history() is not implemented: the "
            "supplied RediffDataPull macro confirms markup for the Gainers/"
            "Losers snapshot listing only, not a per-company historical price "
            "page. Use YFinanceProvider for historical OHLC / technical "
            "analysis, or supply a saved HTML dump of Rediff's historical-"
            "price page for this company and it can be implemented properly."
        )

    def get_current_price(self, company: Company) -> float | None:
        """Best-effort: scans today's BSE Gainers/Losers (Groups A/B/T) for
        a company-name match. Only succeeds if the company is currently
        among that day's top movers in one of those groups — returns None
        otherwise, which is the expected common case, not a failure."""
        target_name = company.name.strip().lower()
        for section_type in ("gainers", "losers"):
            for group in self._GROUPS:
                url = f"https://money.rediff.com/{section_type}/bse/daily/group{group.lower()}"
                rows = self._fetch_section(url)
                for company_name, _group, _prev, curr_price, _chg in rows:
                    if target_name in company_name.strip().lower() or company_name.strip().lower() in target_name:
                        logger.info(
                            "Matched %s in Rediff %s/Group%s: %s @ %.2f",
                            company.name, section_type, group, company_name, curr_price,
                        )
                        return curr_price
        logger.info(
            "%s not found in today's BSE Gainers/Losers (Groups A/B/T) on Rediff — "
            "expected unless it's currently a top mover.",
            company.name,
        )
        return None


def get_market_data_provider(provider_name: str, *, csv_path: Path | None = None) -> MarketDataProvider:
    """Factory: resolve a configured provider name to an instance.

    Driven by Settings.market_data_provider so switching providers is a
    one-line .env change, not a code change anywhere downstream.

    Args:
        csv_path: required when provider_name == 'csv' — path to an
            NSE historical-data CSV export (see CSVPriceProvider).
    """
    normalized = provider_name.strip().lower()
    if normalized == "csv":
        if csv_path is None:
            raise ValueError("csv_path is required when provider_name='csv'.")
        return CSVPriceProvider(csv_path)
    if normalized == "yfinance":
        return YFinanceProvider()
    if normalized in ("rediff", "money.rediff.com", "rediffmoney"):
        return RediffMoneyProvider()
    raise ValueError(
        f"Unknown MARKET_DATA_PROVIDER '{provider_name}'. Supported: 'csv', 'yfinance', 'rediff'."
    )
