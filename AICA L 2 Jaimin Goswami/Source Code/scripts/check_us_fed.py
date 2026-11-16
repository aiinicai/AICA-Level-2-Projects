import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row
rows = con.execute("""
    SELECT id, title, country, authority, scheduled_at, published_at, payload 
    FROM events 
    WHERE country='United States' AND (title LIKE '%Fed%' OR title LIKE '%FOMC%' OR title LIKE '%Interest Rate%')
""").fetchall()

print(f"Found {len(rows)} matching events:")
for r in rows:
    p = json.loads(r['payload'])
    print("ID:", r['id'])
    print("Title:", r['title'])
    print("Scheduled:", r['scheduled_at'])
    print("Published:", r['published_at'])
    print("Previous:", p.get('previous'), "Forecast:", p.get('forecast'), "Actual:", p.get('actual'))
    print("Summary:", p.get('summary'))
    print("---")
con.close()
