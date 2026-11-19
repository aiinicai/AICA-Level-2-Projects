import sqlite3
import json
from pathlib import Path

db_path = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db")
if not db_path.exists():
    print(f"Database not found at {db_path}")
    raise SystemExit(1)

conn = sqlite3.connect(str(db_path), timeout=15)
cur = conn.cursor()

# 1. Enable official Indian feeds (NSE, SEBI, RBI)
official_ids = ('sebi', 'rbi_press', 'rbi_notifications', 'nse_announcements', 'nse_circulars')
for sid in official_ids:
    cur.execute("UPDATE data_sources SET enabled=1, status='Stale' WHERE id=?", (sid,))

# 2. Set default workspace scope to 'All records'
cur.execute("INSERT OR REPLACE INTO user_settings (key, value) VALUES ('data_scope', '\"All records\"')")

conn.commit()

print("Successfully enabled official Indian live feeds:")
cur.execute("SELECT id, name, enabled, status FROM data_sources WHERE enabled=1")
for row in cur.fetchall():
    print(f"  • {row[1]} (id={row[0]}, status={row[3]})")

cur.execute("SELECT key, value FROM user_settings WHERE key='data_scope'")
scope = cur.fetchone()
print(f"Active workspace scope set to: {scope[1]}")

conn.close()
