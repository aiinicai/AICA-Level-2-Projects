import sqlite3, json

db_path = r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db'
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Find the US Fed event currently dated in November
row = cur.execute("""
    SELECT * FROM events 
    WHERE country='United States' AND title LIKE '%FOMC%' AND scheduled_at LIKE '2026-11%'
""").fetchone()

if row:
    event_id = row['id']
    payload = json.loads(row['payload'])
    
    new_scheduled = "2026-10-29T18:00:00+00:00" # 23:30 IST on Oct 29 (October ending)
    new_period = "Oct 2026"
    new_summary = "OFFICIAL RECORD · Federal Open Market Committee (FOMC) October Meeting: Voted to lower the target range for the federal funds rate by 25 basis points to 4.50%-4.75%, noting economic activity has continued to expand at a solid pace and inflation has progressed toward the 2 percent objective."
    
    payload['scheduled_at'] = new_scheduled
    payload['published_at'] = new_scheduled
    payload['reporting_period'] = new_period
    payload['summary'] = new_summary
    if 'original_times' in payload and isinstance(payload['original_times'], dict):
        payload['original_times']['scheduled_at'] = new_scheduled
        payload['original_times']['published_at'] = new_scheduled
        
    new_payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    
    # 1. Update events table
    cur.execute("""
        UPDATE events 
        SET scheduled_at=?, published_at=?, reporting_period=?, payload=?, revision=revision+1, updated_at='2026-11-14T09:10:00+00:00'
        WHERE id=?
    """, (new_scheduled, new_scheduled, new_period, new_payload_json, event_id))
    
    # 2. Update source_records table
    cur.execute("""
        UPDATE source_records
        SET payload=?, retrieved_at='2026-11-14T09:10:00+00:00'
        WHERE event_id=?
    """, (new_payload_json, event_id))
    
    # 3. Add revision record
    cur.execute("""
        INSERT INTO event_revisions (event_id, revision, source_id, recorded_at, source_updated_at, payload, changed_fields)
        VALUES (?, 2, 'trading_economics', '2026-11-14T09:10:00+00:00', '2026-10-29T18:00:00+00:00', ?, ?)
    """, (event_id, new_payload_json, json.dumps(['scheduled_at', 'published_at', 'reporting_period', 'summary'])))
    
    # 4. Update economic_observations reporting_period
    cur.execute("""
        UPDATE economic_observations
        SET reporting_period=?, revision=2
        WHERE event_id=?
    """, (new_period, event_id))
    
    con.commit()
    print(f"Successfully updated US Fed FOMC event {event_id} to {new_scheduled} ({new_period})")
else:
    print("No November US Fed FOMC event found to update.")

con.close()
