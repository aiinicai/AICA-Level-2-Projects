"""Unit tests for Finnhub economic calendar adapter."""
import pytest
from app.data_sources.finnhub import FinnhubAdapter
from app.data_sources.http import HttpClient, SourceError


class DummyResponse:
    def __init__(self, data=None, status_code=200):
        self._data = data
        self.status_code = status_code
        self.headers = {}
        self.content = b"{}"
        self.url = "https://finnhub.io/api/v1/calendar/economic"

    def json(self):
        return self._data


class DummySession:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


def test_finnhub_missing_credential():
    adapter = FinnhubAdapter(HttpClient(DummySession(DummyResponse())))
    with pytest.raises(SourceError) as exc:
        adapter.fetch({"config": {}}, credential=None)
    assert exc.value.status == "Not Configured"


def test_finnhub_successful_parsing():
    sample_payload = {
        "economicCalendar": [
            {
                "actual": 5.4,
                "prev": 5.1,
                "country": "IN",
                "currency": "INR",
                "estimate": 5.2,
                "event": "India CPI Inflation YoY",
                "impact": "high",
                "time": "2026-11-12 12:00:00",
                "unit": "%"
            },
            {
                "actual": None,
                "prev": 4.5,
                "country": "US",
                "currency": "USD",
                "estimate": 4.25,
                "event": "Fed Interest Rate Decision",
                "impact": "high",
                "time": "2026-12-16 19:00:00",
                "unit": "%"
            }
        ]
    }
    adapter = FinnhubAdapter(HttpClient(DummySession(DummyResponse(sample_payload))))
    records, config = adapter.fetch({"config": {"days_back": 7, "days_ahead": 30}}, credential="dummy-token")
    assert len(records) == 2
    
    # First record (published)
    r1 = records[0]
    assert r1["kind"] == "Economic"
    assert r1["country"] == "IN"
    assert r1["actual"] == "5.4"
    assert r1["forecast"] == "5.2"
    assert r1["previous"] == "5.1"
    assert r1["status"] == "Published"
    assert r1["importance"] == "High"
    assert r1["category"] == "Inflation"
    
    # Second record (scheduled)
    r2 = records[1]
    assert r2["actual"] is None
    assert r2["forecast"] == "4.25"
    assert r2["status"] == "Scheduled"
    assert r2["category"] == "Interest rates"
