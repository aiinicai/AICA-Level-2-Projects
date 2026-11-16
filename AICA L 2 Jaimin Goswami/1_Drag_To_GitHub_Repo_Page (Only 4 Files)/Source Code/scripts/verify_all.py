import sqlite3
import csv

print("=== CHECKING SAMPLE CSV REPO ROWS ===", flush=True)
with open(r'C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\Sample_Financial_Events.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        t = row.get('title') or ''
        if 'repo' in t.lower():
            print(f"  {t[:65]} | Prev: {row.get('previous')} | Act: {row.get('actual')}", flush=True)

print("\n=== CHECKING REGULATORY NOTICES ===", flush=True)
conn = sqlite3.connect(r'C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db')
cur = conn.cursor()
cur.execute("SELECT count(*) FROM regulatory_notices WHERE notice_number IS NOT NULL AND notice_number != ''")
print(f"Populated regulatory notice numbers: {cur.fetchone()[0]} / 75", flush=True)

cur.execute("SELECT e.authority, rn.notice_number, e.title FROM events e JOIN regulatory_notices rn ON e.id = rn.event_id LIMIT 6")
for r in cur.fetchall():
    print(f"  Auth: {r[0]} | Notice: {r[1]} | Title: {r[2][:45]}", flush=True)

print("\n=== CHECKING OBSERVATIONS SERIES KEY ===", flush=True)
cur.execute("SELECT count(*) FROM economic_observations WHERE series_key IS NOT NULL AND series_key != ''")
print(f"Populated observations series_key: {cur.fetchone()[0]} / 155", flush=True)
conn.close()
