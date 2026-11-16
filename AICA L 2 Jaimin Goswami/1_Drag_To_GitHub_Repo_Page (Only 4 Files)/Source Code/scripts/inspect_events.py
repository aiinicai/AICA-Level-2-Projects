import sqlite3
db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

total = c.execute("SELECT count(*) FROM events").fetchone()[0]
print(f"TOTAL ACTIVE LIVE EVENTS: {total}\n")

print("--- BREAKDOWN BY KIND ---")
for row in c.execute("SELECT kind, count(*) as cnt FROM events GROUP BY kind ORDER BY cnt DESC").fetchall():
    print(f"  {row['kind']}: {row['cnt']}")

print("\n--- BREAKDOWN BY CATEGORY ---")
for row in c.execute("SELECT category, count(*) as cnt FROM events GROUP BY category ORDER BY cnt DESC LIMIT 15").fetchall():
    print(f"  {row['category']}: {row['cnt']}")

print("\n--- BREAKDOWN BY AUTHORITY / ISSUER ---")
for row in c.execute("SELECT authority, count(*) as cnt FROM events WHERE authority != '' GROUP BY authority ORDER BY cnt DESC LIMIT 15").fetchall():
    print(f"  {row['authority']}: {row['cnt']}")

print("\n--- DATE RANGE ---")
dates = c.execute("SELECT MIN(COALESCE(scheduled_at, published_at)) as min_d, MAX(COALESCE(scheduled_at, published_at)) as max_d FROM events").fetchone()
print(f"  From: {dates['min_d']} To: {dates['max_d']}")

print("\n--- SAMPLE CORPORATE ANNOUNCEMENTS ---")
for row in c.execute("SELECT title, authority, scheduled_at, published_at FROM events WHERE kind='Corporate' LIMIT 5").fetchall():
    print(f"  • {row['title']} | Authority: {row['authority']}")

print("\n--- SAMPLE REGULATORY NOTICES ---")
for row in c.execute("SELECT title, authority, scheduled_at, published_at FROM events WHERE kind='Regulatory' LIMIT 5").fetchall():
    print(f"  • {row['title']} | Authority: {row['authority']}")

print("\n--- SAMPLE ECONOMIC EVENTS ---")
for row in c.execute("SELECT title, authority, scheduled_at, published_at FROM events WHERE kind='Economic' LIMIT 5").fetchall():
    print(f"  • {row['title']} | Authority: {row['authority']}")
