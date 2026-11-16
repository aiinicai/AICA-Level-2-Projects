"""Exercise the actual official-RSS adapters against a separate QA database."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database.store import Database
from app.services.bootstrap import initialize
from app.data_sources.manager import SourceManager

root=Path(__file__).resolve().parents[1]
db=Database(root/"qa-data/live-source-tests.db")
initialize(db)
manager=SourceManager(db)
results=[]
for source_id in ("sebi","rbi_press","rbi_notifications","nse_announcements","nse_circulars"):
    db.execute("UPDATE data_sources SET enabled=1 WHERE id=?",(source_id,))
    record={"source":source_id}
    try:
        result=manager.refresh(source_id,force=True,backfill=True)
        record["result"]=result.describe()
        one=db.rows("SELECT payload FROM source_records WHERE source_id=? LIMIT 1",(source_id,))
        if one:
            event=json.loads(one[0]["payload"])
            record["field_presence"]={k:bool(event.get(k)) for k in ("title","company","original_times","published_at")}
            record["publication_precision"]="date" if len(event["published_at"])==10 else "timestamp"
    except Exception as exc:
        record["error"]=str(exc)
    state=db.rows("SELECT status,last_success,last_error FROM data_sources WHERE id=?",(source_id,))[0]
    record.update(state); results.append(record); print(json.dumps(record),flush=True)
(root/"docs/live-source-test-report.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
errors=db.rows("SELECT message,count(*) AS n FROM ingestion_errors GROUP BY message")
print(json.dumps({"historical_rejection_counts":errors}))

