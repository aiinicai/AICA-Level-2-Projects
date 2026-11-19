import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT id, title, country, category, authority, scheduled_at, published_at, payload 
    FROM events 
    WHERE kind='Economic'
    ORDER BY country, COALESCE(scheduled_at, published_at)
""").fetchall()

print(f"Total Economic Events: {len(rows)}")
for i, r in enumerate(rows, 1):
    p = json.loads(r['payload'])
    print(f"[{i:02d}] ID: {r['id']}")
    print(f"     Title: {r['title']}")
    print(f"     Country: {r['country']} | Authority: {r['authority']} | Cat: {r['category']}")
    print(f"     Date: {r['scheduled_at'] or r['published_at']} | Status: {p.get('status')}")
    print(f"     Previous: {p.get('previous')} | Consensus: {p.get('forecast')} | Actual: {p.get('actual')} {p.get('unit')}")
    print(f"     Period: {p.get('reporting_period')} | URL: {p.get('source_url')}")
    print(f"     Summary: {p.get('summary')}")
    print("=" * 80)
con.close()
