"""Tests for app/data/market_data.py.

RediffMoneyProvider's parsing tests use synthetic HTML built directly
from the markup confirmed in the person's own RediffDataPull_v2 VBA
macro (row structure, pagination link, "Showing X - Y of Z" total).
No live network call is made here — see the provider's docstring for
its verification status.
"""

from __future__ import annotations

import pytest

from app.core.enums import ExchangeCode
from app.core.models import Company
from app.data.market_data import (
    MarketDataProvider,
    RediffMoneyProvider,
    YFinanceProvider,
    get_market_data_provider,
)

_SAMPLE_HTML = """
<html><body>
<table>
<tr><td><a href="/x">Sona BLW Precision Forgings</a></td><td class="alignC">A</td><td class="alignR">468.30</td><td class="alignR">481.50</td><td class="alignR"><span class="green">+  13.20</span></td></tr>
<tr><td><a href="/y">Nuvoco Vistas Corp.</a></td><td class="alignC">A</td><td class="alignR">341.50</td><td class="alignR">376.35</td><td class="alignR"><span class="green">+  10.20</span></td></tr>
<tr><td><a href="/z">Some Losing Co</a></td><td class="alignC">A</td><td class="alignR">100.00</td><td class="alignR">85.50</td><td class="alignR"><span class="red">-  14.50</span></td></tr>
</table>
Showing 1 - 100 of 419
<a href='//money.rediff.com/gainers/bse/daily/groupa?start=101&amp;end=200' class="grey"><u>Next</u> &gt;</a>
</body></html>
"""

_SAMPLE_HTML_NO_NEXT = """
<table>
<tr><td><a>Last Page Co</a></td><td class="alignC">B</td><td class="alignR">10.00</td><td class="alignR">11.00</td><td class="alignR"><span class="green">+  1.00</span></td></tr>
</table>
Showing 401 - 419 of 419
"""


class TestRediffPageParsing:
    def test_parses_three_rows_from_confirmed_markup(self):
        provider = RediffMoneyProvider()
        rows, next_url, total = provider._parse_page(_SAMPLE_HTML)
        assert len(rows) == 3

    def test_company_name_with_period_parsed_correctly(self):
        provider = RediffMoneyProvider()
        rows, _, _ = provider._parse_page(_SAMPLE_HTML)
        assert rows[1][0] == "Nuvoco Vistas Corp."

    def test_negative_change_parsed_correctly(self):
        provider = RediffMoneyProvider()
        rows, _, _ = provider._parse_page(_SAMPLE_HTML)
        assert rows[2][4] == -14.50

    def test_embedded_double_space_in_change_does_not_break_parsing(self):
        # "+  13.20" (double space) is the exact case the macro's CleanNum
        # comment calls out as breaking naive IsNumeric/CDbl.
        provider = RediffMoneyProvider()
        rows, _, _ = provider._parse_page(_SAMPLE_HTML)
        assert rows[0][4] == 13.20

    def test_next_link_normalized_from_protocol_relative_and_entity(self):
        provider = RediffMoneyProvider()
        _, next_url, _ = provider._parse_page(_SAMPLE_HTML)
        assert next_url == "https://money.rediff.com/gainers/bse/daily/groupa?start=101&end=200"

    def test_showing_total_extracted(self):
        provider = RediffMoneyProvider()
        _, _, total = provider._parse_page(_SAMPLE_HTML)
        assert total == 419

    def test_last_page_has_no_next_link(self):
        provider = RediffMoneyProvider()
        rows, next_url, total = provider._parse_page(_SAMPLE_HTML_NO_NEXT)
        assert len(rows) == 1
        assert next_url is None
        assert total == 419

    def test_empty_html_produces_no_rows_and_no_crash(self):
        provider = RediffMoneyProvider()
        rows, next_url, total = provider._parse_page("")
        assert rows == []
        assert next_url is None
        assert total == 0

    def test_clean_num_strips_embedded_whitespace_and_commas(self):
        assert RediffMoneyProvider._clean_num("+  1,234.50") == 1234.50
        assert RediffMoneyProvider._clean_num("-  14.57") == -14.57
        assert RediffMoneyProvider._clean_num("not a number") is None

    def test_normalize_url_handles_protocol_relative_and_entity(self):
        result = RediffMoneyProvider._normalize_url(
            "//money.rediff.com/x?a=1&amp;b=2"
        )
        assert result == "https://money.rediff.com/x?a=1&b=2"


class TestProviderFactory:
    def test_yfinance_provider_resolved(self):
        assert isinstance(get_market_data_provider("yfinance"), YFinanceProvider)

    def test_rediff_provider_resolved(self):
        assert isinstance(get_market_data_provider("rediff"), RediffMoneyProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            get_market_data_provider("bloomberg")

    def test_both_providers_conform_to_interface(self):
        assert isinstance(get_market_data_provider("yfinance"), MarketDataProvider)
        assert isinstance(get_market_data_provider("rediff"), MarketDataProvider)


class TestRediffScopeLimitations:
    def test_get_price_history_raises_not_implemented(self):
        # Documented scope limit: confirmed markup only covers the
        # Gainers/Losers snapshot, not a historical OHLC page.
        from datetime import date

        provider = RediffMoneyProvider()
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        with pytest.raises(NotImplementedError):
            provider.get_price_history(company, date(2024, 1, 1), date(2024, 12, 31))
