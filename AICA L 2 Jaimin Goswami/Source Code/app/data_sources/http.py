from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from urllib.parse import urlsplit

import requests


class SourceError(RuntimeError):
    def __init__(self, message, status="Error", retry_after=0):
        super().__init__(message)
        self.status,self.retry_after=status,retry_after


class HttpClient:
    def __init__(self, session=None, sleep=time.sleep):
        self.session=session or requests.Session()
        self.sleep=sleep

    def get(self,url,params=None,headers=None):
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, application/json, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)
        for attempt in range(3):
            try:
                response=self.session.get(url,params=params,headers=req_headers,timeout=(8,25),allow_redirects=True)
            except requests.RequestException as exc:
                if attempt<2:
                    self.sleep(2**attempt)
                    continue
                # requests exceptions can include credentials in a query URL: do not expose them.
                raise SourceError(f"Network request failed ({type(exc).__name__}); check connection and source availability") from None
            if response.status_code in (401,403):
                raise SourceError(f"HTTP {response.status_code}: source access restricted; no bypass attempted","Restricted")
            if response.status_code==429:
                retry=response.headers.get("Retry-After","60")
                try:
                    seconds=int(retry)
                except ValueError:
                    try:
                        seconds=max(1,int((parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds()))
                    except Exception:
                        seconds=60
                raise SourceError("HTTP 429: provider rate limit; retry scheduled","Stale",max(1,seconds))
            if response.status_code>=500 and attempt<2:
                self.sleep(2**attempt)
                continue
            if response.status_code not in (200,304):
                raise SourceError(f"HTTP {response.status_code}: source request failed")
            if len(response.content)>20*1024*1024:
                raise SourceError("Source response exceeds 20 MB; use smaller queries")
            if urlsplit(response.url).scheme!="https":
                raise SourceError("Source redirected away from HTTPS; response rejected")
            return response
        raise SourceError("Request could not be completed")

