import sqlite3
import csv
import json
import zipfile
from xml.sax.saxutils import escape
from pathlib import Path

target_dir = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView")
db_path = target_dir / "data" / "eventscope.db"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

sample_rows = cursor.execute("SELECT payload FROM events WHERE sample = 1").fetchall()
records = [json.loads(r[0]) for r in sample_rows]
print(f"Retrieved {len(records)} sample events.")

fields = [
    "title", "kind", "country", "category", "authority", "company", "symbol", 
    "exchange", "importance", "status", "scheduled_at", "published_at", 
    "previous", "forecast", "actual", "unit", "reporting_period", "source_url"
]

csv_path = target_dir / "Sample_Financial_Events.csv"
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        writer.writerow({k: rec.get(k, "") for k in fields})
print(f"Wrote CSV to {csv_path}")

def create_xlsx(records, fields, out_path):
    rows_xml = []
    hdr_cells = "".join([f'<c t="inlineStr"><is><t>{escape(col)}</t></is></c>' for col in fields])
    rows_xml.append(f'<row r="1">{hdr_cells}</row>')
    
    for r_idx, rec in enumerate(records, start=2):
        cell_xmls = []
        for c_idx, field in enumerate(fields):
            val = str(rec.get(field) or "")
            cell_xmls.append(f'<c t="inlineStr"><is><t>{escape(val)}</t></is></c>')
        rows_xml.append(f'<row r="{r_idx}">{"".join(cell_xmls)}</row>')
    
    sheet_data = "".join(rows_xml)
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>{sheet_data}</sheetData>
</worksheet>"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="Sample Events" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>"""

    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

xlsx_path = target_dir / "Sample_Financial_Events.xlsx"
create_xlsx(records, fields, xlsx_path)
print(f"Wrote XLSX to {xlsx_path}")

cursor.execute("DELETE FROM economic_observations WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM corporate_announcements WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM regulatory_notices WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM event_revisions WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM source_records WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM notification_jobs WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM event_ai_cache WHERE event_id IN (SELECT id FROM events WHERE sample = 1)")
cursor.execute("DELETE FROM events WHERE sample = 1")
conn.commit()
cursor.execute("VACUUM")

remaining = cursor.execute("SELECT count(*) FROM events").fetchone()[0]
conn.close()

print(f"Purge complete. Remaining active live events in database: {remaining}")
