from datetime import date, timedelta
from urllib.parse import quote

from app.data_sources.http import SourceError


class TradingEconomicsAdapter:
    def __init__(self,http):
        self.http=http

    def fetch(self,source,credential=None):
        if not credential:
            raise SourceError("Enter your licensed Trading Economics API credential","Not Configured")
        config=source.get("config",{})
        countries=config.get("countries","india")
        start=date.fromisoformat(config["start_date"]) if config.get("start_date") else date.today()-timedelta(days=int(config.get("days_back",7)))
        end=date.fromisoformat(config["end_date"]) if config.get("end_date") else date.today()+timedelta(days=int(config.get("days_ahead",30)))
        if start>end or (end-start).days>366:
            raise SourceError("Choose an economic calendar range of at most 366 days")
        records=[]
        for country in countries.split(","):
            if not country.strip():
                continue
            records.extend(self._range(country.strip(),start,end,credential))
        return records,config

    def _range(self,country,start,end,credential):
        path=f"https://api.tradingeconomics.com/calendar/country/{quote(country,safe='')}/{start.isoformat()}/{end.isoformat()}"
        response=self.http.get(path,params={"c":credential,"f":"json"})
        try:
            data=response.json()
        except ValueError:
            raise SourceError("Calendar response was not JSON") from None
        if not isinstance(data,list):
            raise SourceError("Calendar provider returned an unexpected payload; check entitlement")
        if len(data)>=1000:
            if start==end:
                raise SourceError("Provider row cap reached for one day; narrower entitlement/query needed")
            middle=start+(end-start)//2
            self.http.sleep(0.25)
            left=self._range(country,start,middle,credential)
            self.http.sleep(0.25)
            return left+self._range(country,middle+timedelta(days=1),end,credential)
        self.http.sleep(0.25)
        result=[]
        for row in data:
            exact=str(row.get("DateSpan","0"))=="0"
            scheduled=row.get("Date")
            if scheduled and not exact:
                scheduled=scheduled[:10]
            actual=row.get("Actual")
            # Date is the scheduled release time; LastUpdate is not proof of publication time.
            result.append(dict(external_id=str(row.get("CalendarId","")),kind="Economic",title=row.get("Event",""),category=row.get("Category","Economic release"),indicator=row.get("Event",""),series_key=row.get("Ticker") or row.get("Symbol") or f"{row.get('Country')}:{row.get('Event')}",country=row.get("Country",""),authority=row.get("Source",""),reporting_period=row.get("Reference",""),scheduled_at=scheduled,source_timezone="UTC",date_confirmed=exact,status="Published" if actual not in (None,"") else ("Scheduled" if exact else "Tentative"),previous=row.get("Previous"),forecast=row.get("Forecast"),actual=actual,revised=row.get("Revised"),provider_forecast=row.get("TEForecast"),unit=row.get("Unit",""),importance={1:"Low",2:"Medium",3:"High"}.get(row.get("Importance"),"Unknown"),source_url=row.get("SourceURL") or ("https://tradingeconomics.com"+row["URL"] if row.get("URL") else ""),source_updated_at=row.get("LastUpdate"),verification="Licensed provider; original authority link supplied by provider"))
        return result

