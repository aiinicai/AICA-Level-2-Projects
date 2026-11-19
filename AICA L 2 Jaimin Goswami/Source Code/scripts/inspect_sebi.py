import sqlite3
import json

db_path = r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT e.id, e.title, e.authority, sr.external_id, e.payload
    FROM events e
    LEFT JOIN source_records sr ON e.id = sr.event_id
    WHERE LOWER(e.kind) = 'regulatory' AND e.authority = 'SEBI'
    LIMIT 10
""")

for r in cur.fetchall():
    print(f"Title: {r[1][:60]} | ExtID: {r[3]}")

conn.close()
