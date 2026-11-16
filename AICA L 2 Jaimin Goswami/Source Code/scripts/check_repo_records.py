import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row
rows = con.execute("SELECT id, title, scheduled_at, published_at, payload FROM events WHERE title LIKE '%Repo Rate%'").fetchall()

print(f"Found {len(rows)} Repo Rate records:")
for r in rows:
    p = json.loads(r['payload'])
    print(r['id'], '| Date:', r['scheduled_at'] or r['published_at'])
    print('  Previous:', p.get('previous'), '| Forecast:', p.get('forecast'), '| Actual:', p.get('actual'))
    print('  Summary:', p.get('summary'))
    print('---')
con.close()
