import sqlite3
import json
import csv
from pathlib import Path

def audit_database(db_path):
    print("=" * 80)
    print(f"AUDITING DATABASE: {db_path}")
    print("=" * 80)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Total Counts
    cur.execute("SELECT kind, count(*) FROM events GROUP BY kind")
    kind_counts = dict(cur.fetchall())
    print(f"Total Events: {sum(kind_counts.values())} -> {kind_counts}")

    # 2. Economic Events Audit
    cur.execute("""
        SELECT e.id, e.title, e.country, e.authority, e.series_key, e.reporting_period,
               e.scheduled_at, e.published_at, e.status, e.importance, e.payload,
               sr.source_id, sr.external_id
        FROM events e
        LEFT JOIN source_records sr ON e.id = sr.event_id
        WHERE LOWER(e.kind) = 'economic'
        ORDER BY e.country, e.reporting_period, e.published_at
    """)
    econ_events = cur.fetchall()
    print(f"\n[ECONOMIC EVENTS AUDIT: {len(econ_events)} events]")
    
    anomalies = []
    for idx, r in enumerate(econ_events, 1):
        payload = json.loads(r[10]) if r[10] else {}
        prev = payload.get('previous')
        cons = payload.get('consensus')
        act = payload.get('actual')
        unit = payload.get('unit')
        title = r[1]
        country = r[2]
        period = r[5]
        pub_at = r[7]
        sched_at = r[6]
        status = r[8]
        
        # Check for 6.50/6.25 anomaly in India Repo Rate
        if 'repo' in title.lower():
            print(f"--> CHECK REPO RATE: {title} | Period: {period} | Prev: {prev} | Cons: {cons} | Act: {act}")
            if act == '6.50' or prev == '6.50' or act == '6.25':
                anomalies.append(f"Repo Rate has outdated figure (6.50 or 6.25): {title} ({period})")

        # Check for missing critical fields
        if not title:
            anomalies.append(f"Economic event {r[0]} has missing title")
        if not country:
            anomalies.append(f"Economic event {r[0]} has missing country")
        if not period:
            anomalies.append(f"Economic event {r[0]} has missing period")

    print(f"Economic Anomalies detected: {len(anomalies)}")
    for a in anomalies:
        print(f"  ! {a}")

    # 3. Regulatory Events Audit
    cur.execute("""
        SELECT e.id, e.title, e.authority, e.category, e.published_at, rn.notice_number, e.payload
        FROM events e
        LEFT JOIN regulatory_notices rn ON e.id = rn.event_id
        WHERE LOWER(e.kind) = 'regulatory'
        ORDER BY e.published_at DESC
    """)
    reg_events = cur.fetchall()
    print(f"\n[REGULATORY NOTICES AUDIT: {len(reg_events)} events]")
    missing_notice_no = 0
    missing_authority = 0
    reg_by_auth = {}
    for r in reg_events:
        auth = r[2] or "Unknown"
        reg_by_auth[auth] = reg_by_auth.get(auth, 0) + 1
        if not r[5]:
            missing_notice_no += 1
        if not r[2]:
            missing_authority += 1
    print(f"Regulatory breakdown by authority: {reg_by_auth}")
    print(f"Missing Notice Numbers: {missing_notice_no}, Missing Authorities: {missing_authority}")

    # 4. Corporate Events Audit
    cur.execute("""
        SELECT e.id, e.title, e.company, e.symbol, e.exchange, e.category, e.published_at
        FROM events e
        WHERE LOWER(e.kind) = 'corporate'
    """)
    corp_events = cur.fetchall()
    print(f"\n[CORPORATE EVENTS AUDIT: {len(corp_events)} events]")
    missing_title = sum(1 for r in corp_events if not r[1] or not r[1].strip())
    missing_company = sum(1 for r in corp_events if not r[2] or not r[2].strip())
    missing_symbol = sum(1 for r in corp_events if not r[3] or not r[3].strip())
    missing_date = sum(1 for r in corp_events if not r[6] or not r[6].strip())
    print(f"Missing Title: {missing_title}, Missing Company: {missing_company}, Missing Symbol: {missing_symbol}, Missing Date: {missing_date}")

    # 5. Economic Observations Audit
    cur.execute("SELECT count(*) FROM economic_observations")
    total_obs = cur.fetchone()[0]
    print(f"\n[ECONOMIC OBSERVATIONS AUDIT: {total_obs} observations]")
    cur.execute("""
        SELECT series_key, reporting_period, role, value_text, value_decimal, unit
        FROM economic_observations
        WHERE series_key LIKE '%repo%' OR series_key LIKE '%policy%'
    """)
    repo_obs = cur.fetchall()
    print(f"Policy / Repo Rate observations in DB:")
    for o in repo_obs:
        print(f"  {o}")

    conn.close()

if __name__ == '__main__':
    for db in [
        r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope\data\eventscope.db",
        r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db",
        r"C:\Users\ADMIN\Desktop\Capstone\Github\FinstockEventScope\data\eventscope.db"
    ]:
        if Path(db).exists():
            audit_database(db)
        else:
            print(f"File not found: {db}")
