import sqlite3
import re
from src.db import get_connection, log_audit

def _get_active_company_name():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'Apex Engineering India Private Limited'

def execute_auto_mapping():
    """
    Applies priority mapping rules to non-zero ledgers in tally_import table.
    Hierarchy:
    1. Company Approved Memory (Highest Priority - Permanently frozen and auto-populated without review)
    2. Active Session Approved Mappings (Preserved)
    3. Rule Engine (Tally Group & Ledger Pattern rules)
    4. Fallback Heuristics (Flagged for CA Review)
    """
    conn = get_connection()
    cursor = conn.cursor()

    company_name = 'Apex Engineering India Private Limited'
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    c_row = cursor.fetchone()
    if c_row:
        company_name = c_row[0]

    # 1. Fetch Company Approved Mappings (Permanently frozen)
    cursor.execute("""
    SELECT ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, tax_flag, review_status, approved_by, approved_at
    FROM company_approved_mappings
    WHERE company_name = ?;
    """, (company_name,))
    company_memory = {r['ledger_name']: dict(r) for r in cursor.fetchall()}

    # 2. Fetch existing active mappings if any
    cursor.execute("SELECT ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, review_status, mapped_by FROM ledger_mappings;")
    existing_mappings = {r['ledger_name']: dict(r) for r in cursor.fetchall()}

    # 3. Get mapping rules ordered by priority DESC
    cursor.execute("""
    SELECT rule_type, pattern, schedule3_code, note_no, classification, cash_flow_category, requires_review
    FROM mapping_rules
    ORDER BY priority DESC, id ASC;
    """)
    rules = cursor.fetchall()

    # 4. Get all imported non-zero ledgers
    cursor.execute("""
    SELECT id, ledger_name, tally_group, closing_net FROM tally_import
    WHERE (ABS(closing_net) >= 0.001 OR ABS(prior_closing_net) >= 0.001 OR debit >= 0.001 OR credit >= 0.001);
    """)
    imported_ledgers = cursor.fetchall()

    mapped_count = 0
    review_count = 0
    retained_count = 0

    for ledger in imported_ledgers:
        ledger_name = ledger['ledger_name']
        tally_group = ledger['tally_group']
        closing_net = ledger['closing_net']

        # --- STEP A: Check Company-Specific Approved Memory (FROZEN) ---
        if ledger_name in company_memory:
            mem = company_memory[ledger_name]
            matched_code = mem['schedule3_code']
            matched_note = mem['note_no']
            matched_class = mem['classification_override'] or 'Default'
            matched_cf = mem['cash_flow_category']
            review_status = 'Approved'
            review_note = f'Permanently retained from CA approval for {company_name}'
            mapped_by = 'Company Memory (Approved)'
            retained_count += 1

        # --- STEP B: Check if active session already has an Approved status ---
        elif ledger_name in existing_mappings and existing_mappings[ledger_name].get('review_status') == 'Approved' and existing_mappings[ledger_name].get('schedule3_code'):
            exist = existing_mappings[ledger_name]
            matched_code = exist['schedule3_code']
            matched_note = exist['note_no']
            matched_class = exist['classification_override'] or 'Default'
            matched_cf = exist['cash_flow_category']
            review_status = 'Approved'
            review_note = 'Approved in session'
            mapped_by = exist.get('mapped_by', 'CA Reviewer')

            # Also persist into permanent company memory
            cursor.execute("""
            INSERT INTO company_approved_mappings (company_name, ledger_name, tally_group, schedule3_code, note_no, classification_override, cash_flow_category, review_status, approved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Approved', ?)
            ON CONFLICT(company_name, ledger_name) DO UPDATE SET
                schedule3_code = excluded.schedule3_code,
                note_no = excluded.note_no,
                classification_override = excluded.classification_override,
                cash_flow_category = excluded.cash_flow_category,
                tally_group = COALESCE(excluded.tally_group, company_approved_mappings.tally_group),
                review_status = 'Approved',
                approved_by = excluded.approved_by,
                approved_at = CURRENT_TIMESTAMP;
            """, (company_name, ledger_name, tally_group, matched_code, matched_note, matched_class, matched_cf, mapped_by))
            retained_count += 1

        # --- STEP C: Evaluate Rule Engine for New / Unapproved Ledgers ---
        else:
            matched_code = None
            matched_note = None
            matched_class = 'Default'
            matched_cf = None
            requires_review = 0

            for r in rules:
                r_type = r['rule_type']
                pattern = r['pattern'].lower()
                
                if r_type == 'Tally_Group' and pattern == tally_group.lower():
                    matched_code = r['schedule3_code']
                    matched_note = r['note_no']
                    matched_class = r['classification']
                    matched_cf = r['cash_flow_category']
                    requires_review = r['requires_review']
                    break
                elif r_type == 'Ledger_Contains' and pattern in ledger_name.lower():
                    matched_code = r['schedule3_code']
                    matched_note = r['note_no']
                    matched_class = r['classification']
                    matched_cf = r['cash_flow_category']
                    requires_review = r['requires_review']
                    break

            # Fallback if unmapped
            if not matched_code:
                if 'sale' in ledger_name.lower() or 'income' in ledger_name.lower():
                    matched_code = 'REVENUE_OPERATIONS'
                    matched_note = '22'
                elif 'purchase' in ledger_name.lower() or 'raw material' in ledger_name.lower():
                    matched_code = 'COST_MATERIALS_CONSUMED'
                    matched_note = '24'
                elif closing_net > 0:
                    matched_code = 'OTHER_CURRENT_ASSETS'
                    matched_note = '21'
                else:
                    matched_code = 'OTHER_CURRENT_LIAB'
                    matched_note = '10'
                requires_review = 1

            # Check if master code itself is marked as judgmental
            cursor.execute("SELECT is_judgmental, default_classification, cash_flow_category FROM schedule3_master WHERE code = ?;", (matched_code,))
            master_row = cursor.fetchone()
            if master_row:
                if master_row['is_judgmental'] == 1:
                    requires_review = 1
                if matched_class == 'Default':
                    matched_class = master_row['default_classification']
                if not matched_cf:
                    matched_cf = master_row['cash_flow_category']

            review_status = 'CA Review Required' if requires_review else 'Approved'
            review_note = 'Auto-mapped via Rule Engine. Review required for judgmental classification.' if requires_review else 'Auto-mapped via Rule Engine.'
            mapped_by = 'Rule Engine'

            # If auto-mapped with Approved status (non-judgmental rule), save to company memory as well
            if review_status == 'Approved':
                cursor.execute("""
                INSERT INTO company_approved_mappings (company_name, ledger_name, tally_group, schedule3_code, note_no, classification_override, cash_flow_category, review_status, approved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Approved', 'Rule Engine')
                ON CONFLICT(company_name, ledger_name) DO UPDATE SET
                    schedule3_code = excluded.schedule3_code,
                    note_no = excluded.note_no,
                    classification_override = excluded.classification_override,
                    cash_flow_category = excluded.cash_flow_category,
                    tally_group = COALESCE(excluded.tally_group, company_approved_mappings.tally_group),
                    review_status = 'Approved';
                """, (company_name, ledger_name, tally_group, matched_code, matched_note, matched_class, matched_cf))

        # Insert or Update mapping
        cursor.execute("""
        INSERT INTO ledger_mappings (ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, review_status, review_note, mapped_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ledger_name) DO UPDATE SET
            schedule3_code = excluded.schedule3_code,
            note_no = excluded.note_no,
            classification_override = excluded.classification_override,
            cash_flow_category = excluded.cash_flow_category,
            review_status = excluded.review_status,
            review_note = excluded.review_note,
            mapped_by = excluded.mapped_by,
            mapped_at = CURRENT_TIMESTAMP;
        """, (ledger_name, matched_code, matched_note, matched_class, matched_cf, review_status, review_note, mapped_by))

        mapped_count += 1
        if review_status == 'CA Review Required':
            review_count += 1

    conn.commit()
    conn.close()
    log_audit("AUTO_MAPPING", "ledger_mappings", details=f"Mapped {mapped_count} ledgers for company '{company_name}' ({retained_count} permanently retained from approved memory, {review_count} flagged for CA Review)")
    return mapped_count, review_count

def update_single_mapping(ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, review_status, review_note=None, user_name="CA Reviewer"):
    conn = get_connection()
    cursor = conn.cursor()

    company_name = 'Apex Engineering India Private Limited'
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    c_row = cursor.fetchone()
    if c_row:
        company_name = c_row[0]

    # Get tally_group for this ledger
    cursor.execute("SELECT tally_group FROM tally_import WHERE ledger_name = ?;", (ledger_name,))
    tg_row = cursor.fetchone()
    tally_group = tg_row['tally_group'] if tg_row else None

    # Update active session mapping
    cursor.execute("""
    INSERT INTO ledger_mappings (ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, review_status, review_note, mapped_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ledger_name) DO UPDATE SET
        schedule3_code = excluded.schedule3_code,
        note_no = excluded.note_no,
        classification_override = excluded.classification_override,
        cash_flow_category = excluded.cash_flow_category,
        review_status = excluded.review_status,
        review_note = excluded.review_note,
        mapped_by = excluded.mapped_by,
        mapped_at = CURRENT_TIMESTAMP;
    """, (ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, review_status, review_note, user_name))

    # If Approved, PERMANENTLY FREEZE & RETAIN for this company
    if review_status == 'Approved':
        cursor.execute("""
        INSERT INTO company_approved_mappings (company_name, ledger_name, tally_group, schedule3_code, note_no, classification_override, cash_flow_category, review_status, approved_by, approved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Approved', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(company_name, ledger_name) DO UPDATE SET
            schedule3_code = excluded.schedule3_code,
            note_no = excluded.note_no,
            classification_override = excluded.classification_override,
            cash_flow_category = excluded.cash_flow_category,
            tally_group = COALESCE(excluded.tally_group, company_approved_mappings.tally_group),
            review_status = 'Approved',
            approved_by = excluded.approved_by,
            approved_at = CURRENT_TIMESTAMP;
        """, (company_name, ledger_name, tally_group, schedule3_code, note_no, classification_override, cash_flow_category, user_name))
    else:
        # If user explicitly reset/unapproved, remove from permanent approved memory
        cursor.execute("DELETE FROM company_approved_mappings WHERE company_name = ? AND ledger_name = ?;", (company_name, ledger_name))

    conn.commit()
    conn.close()

    log_audit("MANUAL_MAPPING_OVERRIDE", "ledger_mappings", target_id=ledger_name, details=f"Mapped to {schedule3_code}, status: {review_status} (Company: {company_name})", user_name=user_name)

def bulk_map_tally_group(tally_group, schedule3_code, note_no, classification, cash_flow_category, user_name="CA Reviewer"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT ledger_name FROM tally_import WHERE tally_group = ? AND (ABS(closing_net) >= 0.001 OR ABS(prior_closing_net) >= 0.001 OR debit >= 0.001 OR credit >= 0.001);", (tally_group,))
    ledgers = cursor.fetchall()
    conn.close()
    
    count = 0
    for l in ledgers:
        update_single_mapping(l['ledger_name'], schedule3_code, note_no, classification, cash_flow_category, 'Approved', f'Bulk mapped & approved under group {tally_group}', user_name)
        count += 1

    log_audit("BULK_MAPPING", "company_approved_mappings", details=f"Bulk mapped and permanently approved {count} ledgers under group '{tally_group}' to {schedule3_code}", user_name=user_name)
    return count

def get_mapping_register(filter_status=None):
    conn = get_connection()
    cursor = conn.cursor()

    company_name = 'Apex Engineering India Private Limited'
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    c_row = cursor.fetchone()
    if c_row:
        company_name = c_row[0]


    query = """
    SELECT 
        ti.ledger_name,
        ti.tally_group,
        ti.closing_net,
        ti.prior_closing_net,
        lm.schedule3_code,
        sm.code_alias,
        sm.normal_balance,
        sm.line_item_name as schedule3_head,
        sm.major_head,
        sm.sub_head,
        COALESCE(lm.note_no, sm.note_no) as note_no,
        COALESCE(lm.classification_override, sm.default_classification) as classification,
        COALESCE(lm.cash_flow_category, sm.cash_flow_category) as cash_flow_category,
        COALESCE(lm.review_status, 'CA Review Required') as review_status,
        lm.review_note,
        lm.mapped_by,
        lm.mapped_at,
        CASE WHEN cam.id IS NOT NULL THEN 1 ELSE 0 END as is_company_frozen,
        cam.approved_at as company_approved_at
    FROM tally_import ti
    LEFT JOIN ledger_mappings lm ON ti.ledger_name = lm.ledger_name
    LEFT JOIN schedule3_master sm ON lm.schedule3_code = sm.code
    LEFT JOIN company_approved_mappings cam ON cam.company_name = ? AND cam.ledger_name = ti.ledger_name
    WHERE (ABS(ti.closing_net) >= 0.001 OR ABS(ti.prior_closing_net) >= 0.001 OR ti.debit >= 0.001 OR ti.credit >= 0.001)
    """

    params = [company_name]

    if filter_status:
        query += " AND COALESCE(lm.review_status, 'CA Review Required') = ?"
        params.append(filter_status)

    query += " ORDER BY ti.tally_group ASC, ti.ledger_name ASC;"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

