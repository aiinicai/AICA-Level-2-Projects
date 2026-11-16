import json
import requests
import pytest

from app.data_sources.http import HttpClient,SourceError
from app.data_sources.manager import SourceManager
from app.data_sources.rss import RSSAdapter,rss_time
from app.data_sources.trading_economics import TradingEconomicsAdapter


class Response:
    def __init__(self,content=b"",status=200,data=None,headers=None):
        self.content=content;self.status_code=status;self._data=data;self.headers=headers or {};self.url="https://example.org/feed"
    def json(self):return self._data


class Session:
    def __init__(self,response):self.response=response;self.calls=0
    def get(self,*args,**kwargs):
        self.calls+=1
        if isinstance(self.response,Exception):raise self.response
        return self.response


RSS=b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Official test feed</title><item><title>Test circular</title><link>https://example.org/circular/1</link><pubDate>Fri, 13 Nov 2026 11:00:00 GMT</pubDate><description>Test data only</description></item></channel></rss>'''


def test_rss_parser_and_metadata():
    adapter=RSSAdapter(HttpClient(Session(Response(RSS))))
    records,_=adapter.fetch({"url":"https://example.org/feed","kind":"Regulatory","authority":"RBI"})
    assert len(records)==1
    assert records[0]["published_at"]=="2026-11-13T11:00:00+00:00"
    assert records[0]["source_url"]=="https://example.org/circular/1"
    assert "Fri, 13 Nov" in records[0]["original_times"]["published_at"]


def test_html_block_is_not_a_feed():
    adapter=RSSAdapter(HttpClient(Session(Response(b"<html>Access denied</html>"))))
    with pytest.raises(SourceError):adapter.fetch({"url":"https://example.org/feed","kind":"Regulatory"})


@pytest.mark.parametrize("status,expected",[(401,"Restricted"),(403,"Restricted"),(429,"Stale"),(500,"Error")])
def test_failed_api_requests(status,expected):
    client=HttpClient(Session(Response(status=status,headers={"Retry-After":"120"})),sleep=lambda _:None)
    with pytest.raises(SourceError) as exc:client.get("https://example.org/feed")
    assert exc.value.status==expected
    if status==429:assert exc.value.retry_after==120


def test_secret_redaction_and_retries():
    session=Session(requests.ConnectionError("https://provider.test/?c=SECRET"))
    with pytest.raises(SourceError) as exc:HttpClient(session,sleep=lambda _:None).get("https://example.org/feed")
    assert "SECRET" not in str(exc.value)
    assert session.calls==3


def test_missing_calendar_credentials():
    with pytest.raises(SourceError) as exc:TradingEconomicsAdapter(None).fetch({"config":{}})
    assert exc.value.status=="Not Configured"


def test_calendar_mapping_preserves_missing_fields():
    data=[dict(CalendarId=12,Event="CPI",Country="India",Category="Inflation",Date="2026-11-13T12:00:00",DateSpan="0",Actual="",Previous="0",Forecast=None,TEForecast="4.4",SourceURL="https://example.org/release",Importance=1,Unit="%")]
    adapter=TradingEconomicsAdapter(HttpClient(Session(Response(data=data)),sleep=lambda _:None))
    records,_=adapter.fetch({"config":{"countries":"india","days_back":0,"days_ahead":1}},"test-credential")
    assert records[0]["actual"]=="" and records[0]["forecast"] is None
    assert records[0]["previous"]=="0"
    assert records[0]["provider_forecast"]=="4.4"
    assert "published_at" not in records[0]


def test_source_success_not_configured_failure_and_restart(db,monkeypatch):
    db.execute("UPDATE data_sources SET enabled=1 WHERE id='sebi'")
    manager=SourceManager(db,HttpClient(Session(Response(RSS)),sleep=lambda _:None))
    result=manager.refresh("sebi",True)
    assert result.inserted==1
    source=next(s for s in manager.sources() if s["id"]=="sebi")
    assert source["status"]=="Connected" and source["last_success"] and source["checkpoint"]
    assert not db.rows("SELECT * FROM notification_jobs")
    failed=SourceManager(db,HttpClient(Session(Response(status=403)),sleep=lambda _:None))
    with pytest.raises(SourceError):failed.refresh("sebi",True)
    source=next(s for s in failed.sources() if s["id"]=="sebi")
    assert source["status"]=="Restricted" and source["last_success"]
    assert db.rows("SELECT count(*) AS n FROM events")[0]["n"]==1
    with pytest.raises(SourceError):manager.refresh("rbi_press",True)


def test_malformed_record_does_not_advance_checkpoint(db):
    db.execute("UPDATE data_sources SET enabled=1 WHERE id='sebi'")
    bad=RSS.replace(b"Fri, 13 Nov 2026 11:00:00 GMT",b"unknown")
    manager=SourceManager(db,HttpClient(Session(Response(bad))))
    with pytest.raises(SourceError):manager.refresh("sebi",True)
    source=next(s for s in manager.sources() if s["id"]=="sebi")
    assert source["checkpoint"] is None and source["status"]=="Error"


@pytest.mark.parametrize("raw,expected",[("12 Nov, 2026 +0530","2026-11-12"),("Fri, 13 Nov 2026 09:00:00","2026-11-13"),("13-Nov-2026 09:31:58","2026-11-13"),("Thu, 12 Nov 2026 00:00:00 +0530","2026-11-12")])
def test_real_feed_date_formats_do_not_invent_timezones(raw,expected):
    assert rss_time(raw)==expected


def test_missing_filing_url_retains_feed_reference():
    no_link=RSS.replace(b"<link>https://example.org/circular/1</link>",b"<link></link>")
    records,_=RSSAdapter(HttpClient(Session(Response(no_link)))).fetch({"id":"nse_announcements","url":"https://example.org/feed","kind":"Corporate","authority":"NSE"})
    assert records[0]["source_url"]=="https://example.org/feed"
    assert records[0]["source_reference_kind"]=="feed"
    assert not records[0]["document_url"]

