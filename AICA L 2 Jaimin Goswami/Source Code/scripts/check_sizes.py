import sqlite3

db_path = r'C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [c[1] for c in cur.fetchall()]
    length_terms = [f"coalesce(length(cast([{c}] as blob)), 0)" for c in cols]
    sql = f"SELECT sum({' + '.join(length_terms)}) FROM [{t}]"
    try:
        cur.execute(sql)
        size = cur.fetchone()[0] or 0
        print(f"{t}: {size:,} bytes")
    except Exception as e:
        print(f"{t}: error {e}")
