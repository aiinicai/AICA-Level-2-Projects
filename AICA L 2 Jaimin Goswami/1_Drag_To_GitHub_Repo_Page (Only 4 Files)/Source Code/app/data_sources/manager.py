from datetime import timedelta
import json
import os

from app.data_sources.http import HttpClient, SourceError
from app.data_sources.rss import RSSAdapter
from app.data_sources.trading_economics import TradingEconomicsAdapter
from app.data_sources.finnhub import FinnhubAdapter
from app.services.ingestion import IngestionService
from app.utils.time import parse_instant, stamp, utc_now


from pathlib import Path
import sys


def find_api_txt():
    candidates = [
        Path.cwd() / "API.txt",
        Path.cwd().parent / "API.txt",
        Path(__file__).resolve().parents[2] / "API.txt",
        Path(__file__).resolve().parents[3] / "API.txt",
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.insert(0, exe_dir / "API.txt")
        candidates.insert(1, exe_dir.parent / "API.txt")
    for cand in candidates:
        try:
            if cand and cand.exists():
                return cand
        except Exception:
            continue
    return None


def get_credential(source_id):
    if source_id == "trading_economics" and os.environ.get("TRADING_ECONOMICS_API_KEY"):
        return os.environ["TRADING_ECONOMICS_API_KEY"].strip().strip('"\'')
    if source_id == "finnhub" and os.environ.get("FINNHUB_API_KEY"):
        return os.environ["FINNHUB_API_KEY"].strip().strip('"\'')
    if source_id == "gemini" and os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip().strip('"\'')
    
    # 2. Check API.txt
    api_file = find_api_txt()
    if api_file:
        try:
            for line in api_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lower = line.lower()
                if source_id == "finnhub":
                    if "finnhub" in lower and "=" in line:
                        return line.split("=", 1)[1].strip().strip('"\'')
                    elif "=" not in line and not line.startswith("AIzaSy") and len(line) >= 16:
                        return line.strip().strip('"\'')
                elif source_id == "gemini":
                    if "gemini" in lower and "=" in line:
                        return line.split("=", 1)[1].strip().strip('"\'')
                    elif line.startswith("AIzaSy"):
                        return line.strip().strip('"\'')
        except Exception:
            pass

    # 3. Keyring fallback
    try:
        import keyring
        val = keyring.get_password("Finstock.EventScope", source_id)
        if val:
            return val.strip().strip('"\'')
    except Exception:
        pass
    return None


def set_credential(source_id, value):
    try:
        import keyring
        if value:
            keyring.set_password("Finstock.EventScope", source_id, value.strip().strip('"\''))
    except Exception:
        pass


class SourceManager:
    def __init__(self,db,http=None,clock=utc_now):
        self.db,self.http,self.clock=db,http or HttpClient(),clock

    def sources(self):
        rows=self.db.rows("SELECT * FROM data_sources ORDER BY name")
        for row in rows:
            row["config"]=json.loads(row["config"])
            if row["status"]=="Connected" and row["last_success"] and (self.clock()-parse_instant(row["last_success"])).total_seconds()>2*row["interval_seconds"]:
                row["status"]="Stale"
        return rows

    def refresh(self,source_id,force=False,backfill=False):
        source=next(s for s in self.sources() if s["id"]==source_id)
        if source["adapter"]=="import":
            raise SourceError("This source uses authorized file import; no live endpoint configured","Not Configured")
        if not source["enabled"]:
            raise SourceError("Enable this source after reviewing its usage terms","Not Configured")
        if source["next_attempt"] and parse_instant(source["next_attempt"])>self.clock() and (not force or source["last_error"].startswith("HTTP 429")):
            return None
        now=self.clock()
        self.db.execute("UPDATE data_sources SET last_attempt=? WHERE id=?", (stamp(now),source_id))
        try:
            if source["adapter"]=="rss":
                adapter=RSSAdapter(self.http)
            elif source["adapter"]=="finnhub":
                adapter=FinnhubAdapter(self.http)
            else:
                adapter=TradingEconomicsAdapter(self.http)
            credential = get_credential(source_id) or self.db.setting(f"{source_id}_api_key") or source.get("config", {}).get("api_key")
            records,config=adapter.fetch(source, credential)
            mode="backfill" if backfill or not source["checkpoint"] else "live"
            result=IngestionService(self.db).import_records(records,source_id,mode,sample=False)
            if result.rejected:
                raise SourceError(f"{result.describe()}; inspect ingestion errors. Prior checkpoint retained.")
            self.db.execute("UPDATE data_sources SET status='Connected',last_success=?,next_attempt=?,last_error='',failures=0,config=?,checkpoint=? WHERE id=?", (stamp(now),stamp(now+timedelta(seconds=source["interval_seconds"])),json.dumps(config),stamp(now),source_id))
            return result
        except Exception as exc:
            error=exc if isinstance(exc,SourceError) else SourceError(f"Refresh failed ({type(exc).__name__}); inspect source configuration")
            delay=max(error.retry_after,min(3600,source["interval_seconds"]*2**min(source["failures"],4)))
            self.db.execute("UPDATE data_sources SET status=?,last_error=?,failures=failures+1,next_attempt=? WHERE id=?", (error.status,str(error),stamp(now+timedelta(seconds=delay)),source_id))
            raise error

    def refresh_due(self, force=False):
        results=[]
        for source in self.sources():
            if source["enabled"] and source["adapter"]!="import":
                try:
                    result=self.refresh(source["id"], force=force)
                    if result:
                        results.append(f"{source['name']}: {result.describe()}")
                except SourceError as exc:
                    results.append(f"{source['name']}: {exc}")
        return results
