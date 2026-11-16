import sqlite3, json
db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, title, scheduled_at, published_at, payload FROM events WHERE title LIKE '%Repo Rate%'").fetchall()
for r in rows:
    p = json.loads(r["payload"])
    print("ID:", r["id"])
    print("Title:", r["title"])
    print("Previous:", p.get("previous"), "Consensus:", p.get("forecast"), "Actual:", p.get("actual"))
    print("Summary:", p.get("summary"))
    print("-" * 50)
