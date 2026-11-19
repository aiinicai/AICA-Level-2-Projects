import sqlite3, json
from pathlib import Path

dbs = [
    r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db',
    r'C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db'
]

for dbp in dbs:
    if not Path(dbp).exists():
        continue
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # 1. Update October 2026 event (Hike to 5.50%)
    oct_row = cur.execute("SELECT id, payload FROM events WHERE title LIKE '%Repo Rate%' AND (scheduled_at LIKE '2026-10%' OR published_at LIKE '2026-10%')").fetchone()
    if oct_row:
        p = json.loads(oct_row['payload'])
        p['previous'] = "5.25"
        p['forecast'] = "5.50"
        p['actual'] = "5.50"
        p['summary'] = "OFFICIAL RECORD · RBI Monetary Policy Committee voted to increase the policy repo rate by 25 bps from 5.25% to 5.50% to anchor inflation expectations while calibrating policy stance to 'Neutral' to support balanced domestic growth."
        p_json = json.dumps(p, ensure_ascii=False, sort_keys=True)
        cur.execute("UPDATE events SET payload=?, revision=revision+1, updated_at='2026-11-16T04:30:00+00:00' WHERE id=?", (p_json, oct_row['id']))
        cur.execute("UPDATE source_records SET payload=? WHERE event_id=?", (p_json, oct_row['id']))
        cur.execute("UPDATE economic_observations SET value_text='5.50', value_decimal='5.50' WHERE event_id=? AND role='actual'", (oct_row['id'],))
        cur.execute("UPDATE economic_observations SET value_text='5.25', value_decimal='5.25' WHERE event_id=? AND role='previous'", (oct_row['id'],))
        cur.execute("UPDATE economic_observations SET value_text='5.50', value_decimal='5.50' WHERE event_id=? AND role='forecast'", (oct_row['id'],))
        print(f"Updated October Repo Rate in {dbp}")

    # 2. Update August 2026 event (Held at 5.25%)
    aug_row = cur.execute("SELECT id, payload FROM events WHERE title LIKE '%Repo Rate%' AND (scheduled_at LIKE '2026-08%' OR published_at LIKE '2026-08%')").fetchone()
    if aug_row:
        p = json.loads(aug_row['payload'])
        p['previous'] = "5.25"
        p['forecast'] = "5.25"
        p['actual'] = "5.25"
        p['summary'] = "OFFICIAL RECORD · RBI Monetary Policy Committee kept the policy repo rate steady at 5.25% with focus on balanced growth and inflation targets."
        p_json = json.dumps(p, ensure_ascii=False, sort_keys=True)
        cur.execute("UPDATE events SET payload=?, revision=revision+1, updated_at='2026-11-16T04:30:00+00:00' WHERE id=?", (p_json, aug_row['id']))
        cur.execute("UPDATE source_records SET payload=? WHERE event_id=?", (p_json, aug_row['id']))
        cur.execute("UPDATE economic_observations SET value_text='5.25', value_decimal='5.25' WHERE event_id=? AND role IN ('actual', 'previous', 'forecast')", (aug_row['id'],))
        print(f"Updated August Repo Rate in {dbp}")

    # 3. Update December 2026 upcoming event (Prior 5.50%, Forecast 5.50%)
    dec_row = cur.execute("SELECT id, payload FROM events WHERE title LIKE '%Repo Rate%' AND (scheduled_at LIKE '2026-12%' OR published_at LIKE '2026-12%')").fetchone()
    if dec_row:
        p = json.loads(dec_row['payload'])
        p['previous'] = "5.50"
        p['forecast'] = "5.50"
        p['actual'] = None
        p_json = json.dumps(p, ensure_ascii=False, sort_keys=True)
        cur.execute("UPDATE events SET payload=?, revision=revision+1, updated_at='2026-11-16T04:30:00+00:00' WHERE id=?", (p_json, dec_row['id']))
        cur.execute("UPDATE source_records SET payload=? WHERE event_id=?", (p_json, dec_row['id']))
        cur.execute("UPDATE economic_observations SET value_text='5.50', value_decimal='5.50' WHERE event_id=? AND role IN ('previous', 'forecast')", (dec_row['id'],))
        print(f"Updated December Repo Rate in {dbp}")

    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    con.close()

print("All databases successfully updated to 5.50% Repo Rate!")
