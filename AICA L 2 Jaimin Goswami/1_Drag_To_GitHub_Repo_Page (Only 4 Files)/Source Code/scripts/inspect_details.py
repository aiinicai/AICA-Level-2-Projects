import sqlite3
import json

db_path = r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== SAMPLE 10 ECONOMIC OBSERVATIONS ===")
cur.execute("SELECT id, event_id, revision, series_key, reporting_period, role, value_text, value_decimal, unit FROM economic_observations LIMIT 10")
for r in cur.fetchall():
    print(r)

print("\n=== SAMPLE 10 REGULATORY NOTICES JOINED WITH EVENTS ===")
cur.execute("""
    SELECT e.id, e.title, e.authority, rn.notice_number, rn.supersedes_external_id, e.payload
    FROM events e
    LEFT JOIN regulatory_notices rn ON e.id = rn.event_id
    WHERE LOWER(e.kind) = 'regulatory'
    LIMIT 10
""")
for r in cur.fetchall():
    payload = json.loads(r[5]) if r[5] else {}
    print(f"ID: {r[0][:8]} | Auth: {r[2]} | NoticeNo: {r[3]} | Title: {r[1][:50]} | PayloadNotice: {payload.get('notice_number') or payload.get('circular_number') or payload.get('reference_number')}")

print("\n=== CHECK MISSING DATES IN CORPORATE EVENTS ===")
cur.execute("""
    SELECT id, title, company, symbol, scheduled_at, published_at, payload
    FROM events
    WHERE LOWER(kind) = 'corporate' AND (published_at IS NULL OR published_at = '')
    LIMIT 5
""")
for r in cur.fetchall():
    print(r[:6])

conn.close()
