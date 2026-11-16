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
    
    row = cur.execute("SELECT id, payload FROM events WHERE id='f6570a8e-c216-52f4-a5f4-00ff6db7782d'").fetchone()
    if row:
        p = json.loads(row['payload'])
        p['company'] = "Nordic American Tankers Ltd"
        p['symbol'] = "NAT"
        p_json = json.dumps(p, ensure_ascii=False, sort_keys=True)
        cur.execute("UPDATE events SET company='Nordic American Tankers Ltd', symbol='NAT', payload=? WHERE id='f6570a8e-c216-52f4-a5f4-00ff6db7782d'", (p_json,))
        cur.execute("UPDATE source_records SET payload=? WHERE event_id='f6570a8e-c216-52f4-a5f4-00ff6db7782d'", (p_json,))
        print("Updated NAT record in", dbp)
    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    con.close()

print("NAT corporate record successfully calibrated.")
