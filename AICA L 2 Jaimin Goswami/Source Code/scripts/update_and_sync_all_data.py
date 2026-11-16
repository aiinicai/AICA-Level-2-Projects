import sqlite3
import csv
import json
import zipfile
import re
from xml.sax.saxutils import escape
from pathlib import Path

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

def update_sample_csv_and_xlsx(dir_path):
    csv_file = Path(dir_path) / "Sample_Financial_Events.csv"
    xlsx_file = Path(dir_path) / "Sample_Financial_Events.xlsx"
    if not csv_file.exists():
        print(f"Skipping {dir_path}, CSV not found", flush=True)
        return

    print(f"Updating {csv_file}...", flush=True)
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))

    fieldnames = [
        "title", "kind", "country", "category", "authority", "company", "symbol", 
        "exchange", "importance", "status", "scheduled_at", "published_at", 
        "previous", "forecast", "actual", "unit", "reporting_period", "source_url"
    ]

    for row in reader:
        t_key = "title" if "title" in row else "\ufefftitle"
        title = row.get(t_key, "")
        
        # Check if RBI repo rate
        if "repo rate cut to 6.25%" in title.lower() or ("rbi monetary policy committee" in title.lower() and row.get("reporting_period") == "Oct 2026"):
            row[t_key] = "RBI Monetary Policy Committee (MPC) Rate Decision: 25 bps Repo Rate Hike to 5.50% & Stance Shift to Calibrated Tightening"
            row["previous"] = "5.25"
            row["forecast"] = "5.50"
            row["actual"] = "5.50"
            row["unit"] = "%"
        elif "rbi monetary policy committee" in title.lower() and row.get("country") == "India":
            row["previous"] = "5.50"
            row["forecast"] = "5.50"
            row["actual"] = ""

        # Check US Fed FOMC
        if "fomc" in title.lower() and row.get("country") == "United States":
            if row.get("reporting_period") == "Nov 2026":
                row["previous"] = "4.75"
                row["forecast"] = "4.50"
                row["actual"] = "4.50"
            elif row.get("reporting_period") == "Dec 2026":
                row["previous"] = "4.50"
                row["forecast"] = "4.25"
                row["actual"] = ""

    # Re-write CSV
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in reader:
            clean_r = {k: r.get(k, r.get("\ufeff" + k, "")) for k in fieldnames}
            writer.writerow(clean_r)

    print(f"Updated CSV: {csv_file}", flush=True)
    
    # Re-generate XLSX
    clean_records = []
    for r in reader:
        clean_records.append({k: r.get(k, r.get("\ufeff" + k, "")) for k in fieldnames})
    create_xlsx(clean_records, fieldnames, xlsx_file)
    print(f"Updated XLSX: {xlsx_file}", flush=True)

def update_database(db_path):
    print("=" * 80, flush=True)
    print(f"UPDATING & AUDITING DATABASE: {db_path}", flush=True)
    print("=" * 80, flush=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Update series_key in economic_observations
    print("Syncing series_key in economic_observations...", flush=True)
    cur.execute("""
        UPDATE economic_observations
        SET series_key = (SELECT series_key FROM events WHERE events.id = economic_observations.event_id)
        WHERE (series_key IS NULL OR series_key = '')
    """)
    print(f"Updated economic_observations rows: {cur.rowcount}", flush=True)

    # 2. Extract and populate regulatory_notices.notice_number
    print("Auditing and populating regulatory_notices...", flush=True)
    cur.execute("""
        SELECT e.id, e.title, e.authority, sr.external_id, e.payload, rn.notice_number
        FROM events e
        LEFT JOIN source_records sr ON e.id = sr.event_id
        LEFT JOIN regulatory_notices rn ON e.id = rn.event_id
        WHERE LOWER(e.kind) = 'regulatory'
    """)
    reg_rows = cur.fetchall()
    updated_reg = 0
    for r in reg_rows:
        eid, title, auth, ext_id, payload_str, cur_not = r
        payload = json.loads(payload_str) if payload_str else {}
        not_num = cur_not or ""

        if not not_num or not_num.strip() == "":
            ext = ext_id or ""
            if "nseindia.com" in ext:
                m = re.search(r'/([^/]+)\.(pdf|zip|docx|xlsx|html)$', ext, re.I)
                if m:
                    not_num = m.group(1)
                else:
                    not_num = ext.split('/')[-1]
            elif "rbi.org.in" in ext:
                if "NotificationUser.aspx?Id=" in ext:
                    m = re.search(r'Id=(\d+)', ext)
                    if m:
                        not_num = f"RBI/2026-27/{m.group(1)}"
                elif "prid=" in ext:
                    m = re.search(r'prid=(\d+)', ext)
                    if m:
                        not_num = f"RBI-PR-{m.group(1)}"
                else:
                    not_num = "RBI-CIRCULAR"
            elif "sebi.gov.in" in ext or auth == "SEBI":
                m = re.search(r'RC\s+No\.?\s*(\d+\s+of\s+\d+)', title, re.I)
                if m:
                    not_num = f"RC No. {m.group(1)}"
                else:
                    m2 = re.search(r'_(\d+)\.html', ext)
                    if m2:
                        not_num = f"SEBI-ORDER-{m2.group(1)}"
                    else:
                        not_num = "SEBI-ORDER"

        if not_num:
            cur.execute("""
                INSERT INTO regulatory_notices (event_id, notice_number, supersedes_external_id)
                VALUES (?, ?, '')
                ON CONFLICT(event_id) DO UPDATE SET notice_number = excluded.notice_number
            """, (eid, not_num))
            payload["notice_number"] = not_num
            cur.execute("UPDATE events SET payload = ? WHERE id = ?", (json.dumps(payload), eid))
            updated_reg += 1

    print(f"Updated {updated_reg} regulatory notice numbers.", flush=True)

    # 3. Fast In-Memory mapping of corporate symbols
    print("Auditing and mapping corporate event symbols in memory...", flush=True)
    cur.execute("SELECT c.name, l.symbol, l.exchange FROM companies c JOIN exchange_listings l ON c.id = l.company_id")
    listings = cur.fetchall()
    sym_map = {}
    for c_name, sym, exch in listings:
        if c_name and sym:
            sym_map[c_name.strip().lower()] = (sym, exch)

    cur.execute("SELECT id, company FROM events WHERE LOWER(kind) = 'corporate' AND (symbol IS NULL OR symbol = '')")
    unmapped = cur.fetchall()
    mapped_count = 0
    for eid, comp in unmapped:
        if not comp:
            continue
        c_key = comp.strip().lower()
        if c_key in sym_map:
            sym, exch = sym_map[c_key]
            cur.execute("UPDATE events SET symbol = ?, exchange = ? WHERE id = ?", (sym, exch, eid))
            mapped_count += 1

    print(f"Fast-mapped {mapped_count} corporate symbols.", flush=True)

    conn.commit()
    conn.close()
    print(f"Database {db_path} update complete.", flush=True)

if __name__ == "__main__":
    for d in [
        r"C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope",
        r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView"
    ]:
        update_sample_csv_and_xlsx(d)

    for db in [
        r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db",
        r"C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db"
    ]:
        if Path(db).exists():
            update_database(db)
