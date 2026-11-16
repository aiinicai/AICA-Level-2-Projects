from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
import re

import feedparser

from app.data_sources.http import SourceError
from app.utils.time import normalize_time


def rss_time(raw,verified_zone=None):
    """Retain date precision when an RSS publisher omits an offset; never guess IST."""
    if not raw:
        return None
    text=raw.strip()
    if re.fullmatch(r"\d{1,2} [A-Za-z]{3}, \d{4} [+-]\d{4}",text):
        return datetime.strptime(text,"%d %b, %Y %z").date().isoformat()
    dt=None
    try:
        dt=parsedate_to_datetime(text)
    except (ValueError,TypeError):
        for pattern in ("%d-%b-%Y %H:%M:%S","%Y-%m-%d","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S"):
            try:
                dt=datetime.strptime(text,pattern); break
            except ValueError:
                pass
    if dt is None:
        return None
    if not re.search(r"\d{1,2}:\d{2}",text) or (dt.hour==0 and dt.minute==0 and dt.second==0):
        return dt.date().isoformat()
    if dt.tzinfo is None and not verified_zone:
        return dt.date().isoformat()
    return normalize_time(dt.isoformat(),verified_zone)


def plain(value):
    return unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def classify(title, kind):
    text=title.casefold()
    choices=[("Financial results",("financial result","quarterly result","annual result")),("Board meeting",("board meeting",)),("Dividend",("dividend",)),("Bonus issue",("bonus",)),("Stock split",("split",)),("Buyback",("buyback","buy back")),("Rights issue",("rights issue",)),("Fundraising",("fund rais","fundrais","allotment")),("Merger / acquisition",("merger","acquisition","amalgamation")),("Management change",("director","management","resignation")),("Shareholding",("shareholding",)),("Material agreement",("agreement","contract",)),("Consultation",("consultation",)),("Monetary policy",("monetary policy","repo rate","mpc")),("Settlement",("settlement",)),("Circular",("circular",))]
    for category,words in choices:
        if any(word in text for word in words):
            return category
    return "Corporate disclosure" if kind=="Corporate" else "Regulatory notice"


class RSSAdapter:
    def __init__(self,http):
        self.http=http

    def fetch(self,source,credential=None):
        config=source.get("config",{})
        response=self.http.get(source["url"],headers={k:v for k,v in {"If-None-Match":config.get("etag"),"If-Modified-Since":config.get("last_modified")}.items() if v})
        if response.status_code==304:
            return [],config
        feed=feedparser.parse(response.content)
        if not feed.get("version") or (feed.get("bozo") and not feed.entries):
            raise SourceError("Response is not a readable RSS/Atom feed (possibly a block page)")
        records=[]
        for entry in feed.entries:
            title=plain(entry.get("title",""))
            # Do not interpret an article body as structured financial facts.
            raw_date=entry.get("published") or entry.get("updated")
            published=rss_time(raw_date,config.get("source_timezone"))
            url=entry.get("link","")
            external=entry.get("id") or url or hashlib.sha256((title+str(raw_date)+plain(entry.get("summary",""))).encode()).hexdigest()
            record=dict(external_id=external,kind=source["kind"],title=title,category=classify(title,source["kind"]),country=source.get("country","India"),authority=source.get("authority",""),source_url=url,published_at=published,status="Published",importance="Unknown",summary="Official feed headline. Open the original source for the complete disclosure. Category is a rule-based application classification.",original_times={"published_at":raw_date},verification="Official RSS metadata; category assigned by application")
            if source["kind"]=="Corporate":
                # Issuer names are only mapped when the feed explicitly supplies one.
                record["company"]=plain(entry.get("companyname") or entry.get("company") or "")
                record["symbol"]=plain(entry.get("symbol") or "")
                record["exchange"]=source["authority"]
                if source.get("id")=="nse_announcements":
                    # Confirmed against the official NSE RSS schema: title is issuer, description is filing subject.
                    subject=plain(entry.get("summary") or entry.get("description") or "")
                    record["company"]=title
                    record["title"]=f"{title} · {subject}" if subject else title
                    record["category"]=classify(subject,"Corporate")
                    record["document_url"]=url
                    record["summary"]=subject or record["summary"]
            if published and len(published)==10 and raw_date and ":" in raw_date:
                record["verification"]+="; exact time conversion unavailable (timezone or timestamp precision not established)"
            if not url:
                record["source_url"]=source["url"]
                record["source_reference_kind"]="feed"
                record["verification"]+="; original filing link missing from the source feed"
                record["summary"]+=" Original filing URL is unavailable in this RSS entry. The retained source reference opens the official feed itself."
            records.append(record)
        return records,{**config,"etag":response.headers.get("ETag"),"last_modified":response.headers.get("Last-Modified")}

