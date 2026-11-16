import sqlite3, json

db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

event_id = "b63f64f0-1a53-5426-80c3-be431a8dfdde"
row = cursor.execute("SELECT payload FROM events WHERE id=?", (event_id,)).fetchone()

if row:
    payload = json.loads(row["payload"])
    payload["previous"] = "6.25"
    payload["forecast"] = "6.50"
    payload["actual"] = "6.50"
    payload["summary"] = "OFFICIAL RECORD · RBI Monetary Policy Committee voted to increase the policy repo rate by 25 bps from 6.25% to 6.50% to anchor inflation expectations while calibrating policy stance to 'Neutral' to support balanced domestic growth."
    
    cursor.execute("UPDATE events SET payload=? WHERE id=?", (json.dumps(payload), event_id))
    
    # Update economic_observations
    cursor.execute("UPDATE economic_observations SET value_text='6.25', value_decimal='6.25' WHERE event_id=? AND role='previous'", (event_id,))
    cursor.execute("UPDATE economic_observations SET value_text='6.50', value_decimal='6.50' WHERE event_id=? AND role='consensus'", (event_id,))
    cursor.execute("UPDATE economic_observations SET value_text='6.50', value_decimal='6.50' WHERE event_id=? AND role='actual'", (event_id,))
    
    conn.commit()
    print("Successfully updated October RBI Repo Rate to show rate increase: Previous 6.25% -> Actual 6.50% (+25 bps).")
else:
    print("Event not found.")

conn.close()
