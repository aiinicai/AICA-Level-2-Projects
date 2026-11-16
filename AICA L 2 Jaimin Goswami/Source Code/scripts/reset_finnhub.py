import sqlite3

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.execute("UPDATE data_sources SET status='Connected', failures=0, next_attempt=NULL, last_error='' WHERE id='finnhub'")
con.commit()
print("Finnhub reset successfully")
con.close()
