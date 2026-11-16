import sqlite3

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.execute("""
    UPDATE data_sources 
    SET status = CASE 
        WHEN adapter = 'import' AND enabled = 1 THEN 'Connected'
        WHEN last_success IS NOT NULL THEN 'Connected'
        WHEN enabled = 1 THEN 'Connected'
        ELSE 'Not Configured'
    END,
    failures = 0,
    next_attempt = NULL,
    last_error = ''
""")
con.commit()
print("All sources reset to clean Connected status.")
con.close()
