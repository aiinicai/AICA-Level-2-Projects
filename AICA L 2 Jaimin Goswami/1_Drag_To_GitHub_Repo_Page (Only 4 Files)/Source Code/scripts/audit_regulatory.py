import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT id, title, authority, category, published_at, payload 
    FROM events 
    WHERE kind='Regulatory'
    ORDER BY published_at DESC
""").fetchall()

print(f"Total Regulatory Events: {len(rows)}")
auths = {}
for r in rows:
    auths[r['authority']] = auths.get(r['authority'], 0) + 1

print("Authorities breakdown:", auths)
print("\nSample latest 10 regulatory notices:")
for i, r in enumerate(rows[:10], 1):
    p = json.loads(r['payload'])
    print(f"[{i:02d}] {r['published_at']} | {r['authority']} | {r['category']}")
    print(f"     Title: {r['title']}")
    print(f"     Notice No: {p.get('notice_number')} | URL: {p.get('source_url')}")
    print("-" * 80)

# Check if any have missing dates or empty titles
invalid = [r['id'] for r in rows if not r['title'] or not r['published_at']]
print(f"Invalid / incomplete records: {len(invalid)}")

con.close()
