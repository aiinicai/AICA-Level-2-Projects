import sqlite3
db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
conn = sqlite3.connect(db_path)
conn.execute("UPDATE data_sources SET status='Connected', enabled=1 WHERE id='india_official_import'")
conn.commit()
print("Source india_official_import enabled and marked Connected.")
