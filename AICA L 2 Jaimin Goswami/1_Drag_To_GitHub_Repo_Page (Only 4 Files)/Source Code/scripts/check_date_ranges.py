import sqlite3
from datetime import datetime, timezone
from pathlib import Path

db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

today_iso = "2026-11-14T00:00:00"

print("=== OVERALL DATABASE HORIZON ===")
r_all = c.execute("""
    SELECT 
        MIN(COALESCE(scheduled_at, published_at, effective_at)) as min_date,
        MAX(COALESCE(scheduled_at, published_at, effective_at)) as max_date,
        COUNT(*) as total_count
    FROM events
""").fetchone()

print(f"Total Active Records: {r_all['total_count']}")
print(f"Earliest Loaded Date: {r_all['min_date']}")
print(f"Latest Future Date:   {r_all['max_date']}\n")

print("=== BREAKDOWN BY KIND ===")
for kind in ("Economic", "Corporate", "Regulatory"):
    r = c.execute("""
        SELECT 
            MIN(COALESCE(scheduled_at, published_at, effective_at)) as min_date,
            MAX(COALESCE(scheduled_at, published_at, effective_at)) as max_date,
            COUNT(*) as total,
            SUM(CASE WHEN COALESCE(scheduled_at, published_at, effective_at) < ? THEN 1 ELSE 0 END) as past_count,
            SUM(CASE WHEN COALESCE(scheduled_at, published_at, effective_at) >= ? THEN 1 ELSE 0 END) as future_count
        FROM events
        WHERE kind = ?
    """, (today_iso, today_iso, kind)).fetchone()
    
    print(f"[{kind.upper()}]")
    print(f"  Count: {r['total']} (Historical/Past: {r['past_count']}, Upcoming/Future: {r['future_count']})")
    print(f"  From:  {r['min_date']}")
    print(f"  Until: {r['max_date']}")
    print()

print("=== KEY FUTURE / UPCOMING EVENTS (SAMPLE) ===")
future_events = c.execute("""
    SELECT title, kind, authority, COALESCE(scheduled_at, published_at, effective_at) as event_date
    FROM events
    WHERE COALESCE(scheduled_at, published_at, effective_at) >= ?
    ORDER BY event_date ASC
    LIMIT 10
""", (today_iso,)).fetchall()

for ev in future_events:
    print(f"  • {ev['event_date']} | [{ev['kind']}] {ev['title']} ({ev['authority']})")

print("\n=== LATEST DATED FUTURE EVENTS ===")
latest_events = c.execute("""
    SELECT title, kind, authority, COALESCE(scheduled_at, published_at, effective_at) as event_date
    FROM events
    ORDER BY event_date DESC
    LIMIT 5
""").fetchall()

for ev in latest_events:
    print(f"  • {ev['event_date']} | [{ev['kind']}] {ev['title']} ({ev['authority']})")
