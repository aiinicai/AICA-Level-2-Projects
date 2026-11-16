import csv
from datetime import date
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.demo import demo_records

target=Path(__file__).resolve().parents[1]/"sample_data"
target.mkdir(exist_ok=True)
records=demo_records(date(2026,11,13))
(target/"synthetic_events.json").write_text(json.dumps({"sample":True,"provenance":"Entirely synthetic. Not real releases or filings. Fixed anchor 2026-11-13.","events":records},indent=2,ensure_ascii=False),encoding="utf-8")
columns=sorted({key for row in records for key in row})
with (target/"synthetic_events.csv").open("w",newline="",encoding="utf-8-sig") as stream:
    writer=csv.DictWriter(stream,fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)
print(f"Wrote {len(records)} labelled synthetic examples to JSON and CSV")

