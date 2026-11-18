"""Sequential session transport and replaceable data-provider contract."""
import time, subprocess, sys, os
from typing import Protocol
import requests
from config import Settings, PATHS, HEADERS, FIELDS, NOT_FOUND, CAPTCHA_ERRORS, STRUCTURE, YEAR_FIELDS, REQUEST_LABELS
from core.validators import validate

class PortalError(Exception):
    def __init__(self, result: str, message: str): super().__init__(message); self.result=result

class DataProvider(Protocol):
    def captcha(self) -> bytes: ...
    def lookup(self,value: str, answer: str) -> dict: ...
    def goods(self,gstin: str) -> dict: ...
    def returns(self,gstin: str,year: str,answer: str = "") -> dict: ...
    def close(self) -> None: ...

class PortalClient:
    def __init__(self,settings: Settings,sleeper=time.sleep):
        self.settings=settings;self.session=requests.Session();self.session.headers.update(HEADERS)
        self.session.headers['Referer']=settings.base+PATHS['page'];self.session.headers['Origin']=settings.base
        self.last=0.;self.sleep=sleeper;self.browser=None;self.pw=None;self.context=None;self.year_values={};self.initialized=False;self.progress=lambda message:None;self.cancel_requested=lambda:False
    def _browser(self):
        from playwright.sync_api import sync_playwright
        self.pw=sync_playwright().start()
        try: self.browser=self.pw.chromium.launch(headless=True)
        except Exception:
            self.progress('Installing the browser fallback for first use. This may take a few minutes…')
            print('Installing Chromium for the portal fallback. This may take a few minutes.',flush=True)
            from playwright._impl._driver import compute_driver_executable
            node,cli=compute_driver_executable()
            subprocess.run([str(node),str(cli),'install','chromium'],check=True,timeout=180)
            self.browser=self.pw.chromium.launch(headless=True)
        if self.cancel_requested():raise PortalError('NETWORK ERROR','Task stopped by user.')
        self.context=self.browser.new_context()
        page=self.context.new_page();page.goto(self.settings.base+PATHS['page'],wait_until='networkidle',timeout=60000)
        self.context.add_cookies([dict(name=c.name,value=c.value,domain=c.domain,path=c.path) for c in self.session.cookies])
    def _request(self,method,path,payload=None):
        for attempt in range(self.settings.retries):
            if self.cancel_requested():raise PortalError('NETWORK ERROR','Task stopped by user.')
            delay=max(0,self.settings.interval-(time.monotonic()-self.last))
            if delay>.05:self.progress(f'Waiting {delay:.1f}s to respect the portal request limit…')
            self.sleep(delay)
            if self.cancel_requested():raise PortalError('NETWORK ERROR','Task stopped by user.')
            self.last=time.monotonic()
            try:
                self.progress(f'{REQUEST_LABELS.get(path.split("?")[0],"Contacting GST portal")} · attempt {attempt+1}/{self.settings.retries}…')
                if self.context:
                    r=self.context.request.fetch(self.settings.base+path,method=method,data=payload,timeout=self.settings.timeout*1000)
                    status=r.status; content=r.body()
                else:
                    r=self.session.request(method,self.settings.base+path,json=payload,timeout=(min(10,self.settings.timeout),self.settings.timeout))
                    status=r.status_code;content=r.content
                if self.cancel_requested():raise PortalError('NETWORK ERROR','Task stopped by user.')
                if status in (403,503) and not self.settings.demo and not self.context:
                    self._browser();continue
                if status==429 or status>=500:
                    if attempt+1<self.settings.retries:
                        self.progress(f'Portal returned HTTP {status}. Retrying after backoff…')
                        self.sleep(max(self.settings.interval,2**(attempt+1)));continue
                if status>=400: raise PortalError('NETWORK ERROR',f'Portal HTTP {status}; wait and retry, or check proxy/firewall.')
                return content
            except PortalError: raise
            except Exception as exc:
                if attempt+1==self.settings.retries: raise PortalError('NETWORK ERROR','Portal unavailable or timed out. Check Internet, proxy, firewall. '+str(exc)) from exc
                self.progress('Connection is slow or interrupted. Retrying with backoff…')
                self.sleep(2**(attempt+1))
        raise PortalError('NETWORK ERROR','Portal retries exhausted')
    def captcha(self) -> bytes:
        if not self.initialized:
            self._request('GET',PATHS['page']);self.initialized=True
        data=self._request('GET',PATHS['captcha']+'?'+STRUCTURE['captcha_query']+'='+str(time.time_ns()))
        if data.lstrip().startswith(b'<'): raise PortalError('NETWORK ERROR','Portal returned HTML instead of a CAPTCHA image.')
        from core.captcha import png_image
        return png_image(data)
    def _json(self,path,payload=None,method="POST"):
        import json
        try: data=json.loads(self._request(method,path,payload))
        except ValueError as exc: raise PortalError('NETWORK ERROR','Unexpected portal response; inspect config.py.') from exc
        if not isinstance(data,dict): raise PortalError('NETWORK ERROR','Unexpected portal JSON structure; inspect config.py.')
        nested=data.get(STRUCTURE['nested_error'])
        code=data.get(FIELDS['error']) or (nested.get(STRUCTURE['error_code']) if isinstance(nested,dict) else None)
        if code in CAPTCHA_ERRORS: raise PortalError('CAPTCHA FAILED','CAPTCHA wrong or expired; enter the refreshed image.')
        if code in NOT_FOUND: raise PortalError('NOT FOUND','No records found / invalid GSTIN reported by portal.')
        if code: raise PortalError('NETWORK ERROR',f'Portal reported {code}')
        return data
    def lookup(self,value: str,answer: str) -> dict:
        v=validate(value)
        return self._json(PATHS[v.kind],{FIELDS[v.kind]:v.value,FIELDS['captcha']:answer})
    def goods(self,gstin: str) -> dict:
        validate(gstin)
        return self._json(PATHS['goods']+'?'+FIELDS['GSTIN']+'='+gstin,method='GET')
    def returns(self,gstin: str,year: str,answer: str = "") -> dict:
        from core.parser import financial_year
        validate(gstin)
        key=(gstin,financial_year(year))
        if not answer or key not in self.year_values:
            years=self._json(PATHS['years']+'?'+FIELDS['GSTIN']+'='+gstin,method='GET')
            options=years.get(YEAR_FIELDS['data'])
            if years.get(YEAR_FIELDS['status']) not in (1,'1',True) or not isinstance(options,list):
                raise PortalError('NETWORK ERROR','Could not load the portal financial-year list. Retry filing lookup.')
            option=next((item for item in options if isinstance(item,dict) and financial_year(item.get(YEAR_FIELDS['label'],''))==financial_year(year)),None)
            if option is None or YEAR_FIELDS['value'] not in option:
                available=', '.join(str(item.get(YEAR_FIELDS['label'],'')) for item in options if isinstance(item,dict))
                raise PortalError('NOT FOUND',f'Financial year {year} is not offered for this taxpayer. Available: {available or "none"}.')
            self.year_values[key]=option[YEAR_FIELDS['value']]
        payload={FIELDS['GSTIN']:gstin,FIELDS['year']:self.year_values[key]}
        if answer: payload[FIELDS['captcha']]=answer
        data=self._json(PATHS['returns'],payload)
        from core.parser import has_filing_status
        if not has_filing_status(data): raise PortalError('NETWORK ERROR','Portal return response did not contain a recognized filing list. Retry filings or check the portal response format.')
        return data
    def close(self):
        self.session.close()
        if self.browser: self.browser.close()
        if self.pw: self.pw.stop()
