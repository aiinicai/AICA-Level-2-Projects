import sqlite3

dbs = [
    r'C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db',
    r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db'
]

for dbp in dbs:
    con = sqlite3.connect(dbp)
    con.execute("DELETE FROM user_settings WHERE key LIKE '%api%' OR key LIKE '%key%'")
    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    remaining = con.execute("SELECT key, value FROM user_settings").fetchall()
    print(f"Cleaned {dbp}: remaining settings = {remaining}")
    con.close()
