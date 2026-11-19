import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT id, title, country, category, authority, scheduled_at, published_at, payload 
    FROM events 
    WHERE kind='Economic' AND country='India'
    ORDER BY COALESCE(scheduled_at, published_at)
""").fetchall()

print(f"Total Indian Economic Events: {len(rows)}\n")
for i, r in enumerate(rows, 1):
    p = json.loads(r['payload'])
    print(f"[{i:02d}] {r['title']}")
    print(f"     Date: {r['scheduled_at'] or r['published_at']} | Status: {p.get('status')}")
    print(f"     Prev: {p.get('previous')} | Cons: {p.get('forecast')} | Act: {p.get('actual')} {p.get('unit')}")
    print(f"     Period: {p.get('reporting_period')}")
    print(f"     Summary: {p.get('summary')}")
    print("-" * 80)
con.close()
