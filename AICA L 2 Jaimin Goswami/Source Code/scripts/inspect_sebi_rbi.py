import sqlite3
import json

db_path = r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT e.id, e.title, e.authority, e.category, e.published_at, e.payload, sr.external_id, sr.source_id, rn.notice_number
    FROM events e
    LEFT JOIN source_records sr ON e.id = sr.event_id
    LEFT JOIN regulatory_notices rn ON e.id = rn.event_id
    WHERE LOWER(e.kind) = 'regulatory' AND e.authority IN ('SEBI', 'RBI')
    LIMIT 20
""")

rows = cur.fetchall()
print(f"Sample of {len(rows)} SEBI/RBI regulatory rows:")
for r in rows:
    p = json.loads(r[5]) if r[5] else {}
    print(f"ID: {r[0][:8]} | Auth: {r[2]} | NoticeNo: '{r[8]}' | Title: {r[1][:60]}")
    print(f"    External ID: {r[6]}")
    print(f"    Payload keys: {list(p.keys())}")
    for k in p:
        if any(w in k.lower() for w in ['notice', 'circular', 'ref', 'number', 'doc', 'link']):
            print(f"       {k} = {p[k]}")

conn.close()
