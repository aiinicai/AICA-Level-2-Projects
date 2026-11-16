from dataclasses import dataclass
import json
from pathlib import Path

from app.database.events import EventRepository
from app.notifications.engine import NotificationEngine
from app.services.validation import validate_event
from app.utils.time import stamp


@dataclass
class ImportResult:
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    rejected: int = 0
    run_id: int = 0

    def describe(self):
        return f"{self.inserted} added · {self.updated} revised · {self.duplicates} unchanged/grouped · {self.rejected} rejected"


def read_xlsx(path):
    import zipfile, xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            for si in tree.findall(f"{ns}si"):
                t = si.find(f"{ns}t")
                shared.append(t.text if t is not None and t.text else "".join(si.itertext()))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        rows = []
        for row in sheet.findall(f".//{ns}row"):
            r_vals = []
            for c in row.findall(f"{ns}c"):
                t = c.get("t")
                v = c.find(f"{ns}v")
                is_node = c.find(f"{ns}is/{ns}t")
                if is_node is not None and is_node.text:
                    val = is_node.text
                elif t == "s" and v is not None and v.text:
                    val = shared[int(v.text)] if int(v.text) < len(shared) else ""
                elif v is not None and v.text:
                    val = v.text
                else:
                    val = ""
                r_vals.append(val)
            rows.append(r_vals)
        if not rows:
            return []
        headers = rows[0]
        result = []
        for r in rows[1:]:
            d = {}
            for i, h in enumerate(headers):
                if h:
                    d[str(h).strip()] = r[i] if i < len(r) else ""
            result.append(d)
        return result


class IngestionService:
    def __init__(self, db, notifications=None):
        self.db=db
        self.events=EventRepository(db)
        self.notifications=notifications or NotificationEngine(db)

    def ensure_source(self, source_id, name=None, adapter="import"):
        self.db.execute("INSERT OR IGNORE INTO data_sources(id,name,adapter,status) VALUES(?,?,?,'Not Configured')", (source_id,name or source_id,adapter))

    def import_records(self, records, source_id="manual", mode="backfill", sample=None):
        if mode not in ("backfill","live","import"):
            raise ValueError("Invalid ingestion mode")
        self.ensure_source(source_id)
        result=ImportResult()
        result.run_id=self.db.execute("INSERT INTO ingestion_logs(source_id,started_at,mode) VALUES(?,?,?)", (source_id,stamp(),mode))
        for index,record in enumerate(records,1):
            try:
                event=validate_event(record,source_id=source_id,sample=sample)
                with self.db.transaction() as conn:
                    event_id,action=self.events.save(conn,event)
                    self.notifications.on_ingested(conn,event_id,action,mode)
                if action=="duplicate":
                    result.duplicates+=1
                else:
                    setattr(result,action,getattr(result,action)+1)
            except (ValueError,TypeError,KeyError) as exc:
                result.rejected+=1
                ref=str(record.get("external_id", "")) if isinstance(record,dict) else ""
                self.db.execute("INSERT INTO ingestion_errors(run_id,row_number,message,record_ref) VALUES(?,?,?,?)", (result.run_id,index,str(exc)[:1000],ref[:200]))
        self.db.execute("UPDATE ingestion_logs SET completed_at=?,inserted=?,updated=?,duplicates=?,rejected=?,status=? WHERE id=?", (stamp(),result.inserted,result.updated,result.duplicates,result.rejected,"Partial" if result.rejected else "Complete",result.run_id))
        self.notifications.reconcile()
        return result

    def import_file(self, path, source_id="manual", sample=None):
        path=Path(path)
        if path.stat().st_size > 100*1024*1024:
            raise ValueError("Import file exceeds the 100 MB limit; split into smaller batches")
        if path.suffix.lower()==".csv":
            import pandas as pd
            records=pd.read_csv(path,dtype=str,keep_default_na=False,encoding="utf-8-sig").to_dict(orient="records")
        elif path.suffix.lower()==".xlsx":
            records=read_xlsx(path)
        elif path.suffix.lower()==".json":
            data=json.loads(path.read_text(encoding="utf-8-sig"))
            records=data.get("events") if isinstance(data,dict) else data
            if not isinstance(records,list):
                raise ValueError("JSON must be an array of events or an object with an events array")
            if isinstance(data,dict) and data.get("sample") is True:
                sample=True
        else:
            raise ValueError("Choose an Excel (.xlsx), CSV or JSON file")
        return self.import_records(records,source_id,"import",sample)
