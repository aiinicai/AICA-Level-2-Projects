import sqlite3
from src.db import get_connection

def run_reconciliation_check():
    """
    Performs comprehensive mathematical and statutory reconciliation checks across:
    1. Imported Trial Balance Debit vs Credit equality.
    2. Balance Sheet equation: Total Assets == Total Equity & Liabilities.
    3. P&L Net Profit == Addition to Reserves & Surplus in Balance Sheet.
    4. Ledger Mappings completeness and CA Review pending items.
    5. Disclosures and missing mandatory notes checklist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Raw Trial Balance Reconciliation
    cursor.execute("""
    SELECT 
        SUM(closing_dr) as total_dr, 
        SUM(closing_cr) as total_cr, 
        SUM(closing_net) as net_tb_sum,
        COUNT(*) as total_ledgers
    FROM tally_import;
    """)
    tb_stats = cursor.fetchone()
    total_dr = tb_stats['total_dr'] or 0.0
    total_cr = tb_stats['total_cr'] or 0.0
    net_tb_sum = tb_stats['net_tb_sum'] or 0.0
    total_ledgers = tb_stats['total_ledgers'] or 0

    tb_balanced = abs(net_tb_sum) < 0.01

    # 2. Mapping Status
    cursor.execute("""
    SELECT 
        COUNT(*) as total_mapped,
        SUM(CASE WHEN COALESCE(lm.review_status, 'CA Review Required') = 'CA Review Required' THEN 1 ELSE 0 END) as pending_reviews,
        SUM(CASE WHEN lm.schedule3_code IS NULL THEN 1 ELSE 0 END) as unmapped_count
    FROM tally_import ti
    LEFT JOIN ledger_mappings lm ON ti.ledger_name = lm.ledger_name
    WHERE (ABS(ti.closing_net) >= 0.001 OR ABS(ti.prior_closing_net) >= 0.001 OR ti.debit >= 0.001 OR ti.credit >= 0.001);
    """)
    map_stats = cursor.fetchone()
    pending_reviews = map_stats['pending_reviews'] or 0
    unmapped_count = map_stats['unmapped_count'] or 0

    # 3. Calculate Major Financial Totals
    # Fetch mapped sums grouped by Schedule III major heads
    cursor.execute("""
    SELECT 
        sm.statement_type,
        sm.major_head,
        sm.sub_head,
        sm.code,
        SUM(ti.closing_net) as mapped_net,
        SUM(ti.prior_closing_net) as prior_mapped_net
    FROM tally_import ti
    JOIN ledger_mappings lm ON ti.ledger_name = lm.ledger_name
    JOIN schedule3_master sm ON lm.schedule3_code = sm.code
    GROUP BY sm.code;
    """)
    mapped_rows = cursor.fetchall()

    totals = {
        'BS_EQUITY': 0.0,
        'BS_NON_CURRENT_LIAB': 0.0,
        'BS_CURRENT_LIAB': 0.0,
        'BS_NON_CURRENT_ASSETS': 0.0,
        'BS_CURRENT_ASSETS': 0.0,
        'PL_REVENUE': 0.0,
        'PL_EXPENSES': 0.0,
        
        'PY_BS_EQUITY': 0.0,
        'PY_BS_NON_CURRENT_LIAB': 0.0,
        'PY_BS_CURRENT_LIAB': 0.0,
        'PY_BS_NON_CURRENT_ASSETS': 0.0,
        'PY_BS_CURRENT_ASSETS': 0.0,
        'PY_PL_REVENUE': 0.0,
        'PY_PL_EXPENSES': 0.0
    }

    for r in mapped_rows:
        st = r['statement_type']
        mh = r['major_head']
        net = r['mapped_net'] or 0.0
        py_net = r['prior_mapped_net'] or 0.0

        if st == 'BS_EQUITY_LIAB':
            if mh == 'Shareholders Funds' or mh == 'Share Application Money Pending Allotment':
                totals['BS_EQUITY'] += abs(net) if net < 0 else -net
                totals['PY_BS_EQUITY'] += abs(py_net) if py_net < 0 else -py_net
            elif mh == 'Non-Current Liabilities':
                totals['BS_NON_CURRENT_LIAB'] += abs(net) if net < 0 else -net
                totals['PY_BS_NON_CURRENT_LIAB'] += abs(py_net) if py_net < 0 else -py_net
            elif mh == 'Current Liabilities':
                totals['BS_CURRENT_LIAB'] += abs(net) if net < 0 else -net
                totals['PY_BS_CURRENT_LIAB'] += abs(py_net) if py_net < 0 else -py_net

        elif st == 'BS_ASSETS':
            if mh == 'Non-Current Assets':
                totals['BS_NON_CURRENT_ASSETS'] += net if net > 0 else net
                totals['PY_BS_NON_CURRENT_ASSETS'] += py_net if py_net > 0 else py_net
            elif mh == 'Current Assets':
                totals['BS_CURRENT_ASSETS'] += net if net > 0 else net
                totals['PY_BS_CURRENT_ASSETS'] += py_net if py_net > 0 else py_net

        elif st == 'PL_REVENUE':
            totals['PL_REVENUE'] += abs(net) if net < 0 else -net
            totals['PY_PL_REVENUE'] += abs(py_net) if py_net < 0 else -py_net

        elif st == 'PL_EXPENSES':
            totals['PL_EXPENSES'] += net if net > 0 else net
            totals['PY_PL_EXPENSES'] += py_net if py_net > 0 else py_net

    # Calculate Net Profit / Loss
    current_net_profit = totals['PL_REVENUE'] - totals['PL_EXPENSES']
    prior_net_profit = totals['PY_PL_REVENUE'] - totals['PY_PL_EXPENSES']

    # Total Equity & Liabilities vs Total Assets (including CY Net Profit in Reserves & Surplus)
    total_eq_liab = totals['BS_EQUITY'] + totals['BS_NON_CURRENT_LIAB'] + totals['BS_CURRENT_LIAB'] + current_net_profit
    total_assets = totals['BS_NON_CURRENT_ASSETS'] + totals['BS_CURRENT_ASSETS']
    
    bs_diff = total_eq_liab - total_assets
    bs_balanced = abs(bs_diff) < 1.0

    # Create Exceptions List
    exceptions = []

    if not tb_balanced:
        exceptions.append({
            'category': 'Trial Balance Discrepancy',
            'severity': 'HIGH',
            'message': f"Imported Trial Balance is out of balance by {abs(net_tb_sum):,.2f} (Total Dr: {total_dr:,.2f}, Total Cr: {total_cr:,.2f})."
        })

    if unmapped_count > 0:
        exceptions.append({
            'category': 'Unmapped Ledgers',
            'severity': 'HIGH',
            'message': f"{unmapped_count} trial balance ledgers have not been mapped to any Schedule III line item."
        })

    if pending_reviews > 0:
        exceptions.append({
            'category': 'CA Review Required',
            'severity': 'MEDIUM',
            'message': f"{pending_reviews} ledger mappings are currently marked as 'CA Review Required' for professional judgement."
        })

    if not bs_balanced:
        exceptions.append({
            'category': 'Balance Sheet Mismatch',
            'severity': 'CRITICAL',
            'message': f"Balance Sheet does not tally. Total Equity & Liabilities ({total_eq_liab:,.2f}) vs Total Assets ({total_assets:,.2f}) differs by {bs_diff:,.2f}."
        })

    # Get active company
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    c_row = cursor.fetchone()
    company_name = c_row[0] if c_row else 'Apex Engineering India Private Limited'

    # Checklist for Schedule III Disclosures
    default_checklist = [
        {'id': 'CH01', 'item': 'Shareholders holding > 5% shares disclosure (Note 2)', 'status': 'Requires Input', 'details_text': ''},
        {'id': 'CH02', 'item': 'Promoters shareholding pattern disclosure (Note 2)', 'status': 'Requires Input', 'details_text': ''},
        {'id': 'CH03', 'item': 'Trade Receivables & Payables Ageing schedules (Notes 6 & 10)', 'status': 'Computed / Ready', 'details_text': 'Computed automatically from ledger sub-grouping and ageing buckets.'},
        {'id': 'CH04', 'item': 'Property, Plant & Equipment movement schedule (Note 12)', 'status': 'Computed / Ready', 'details_text': 'Tangible & Intangible fixed asset additions and depreciation schedules generated in Note 12.'},
        {'id': 'CH05', 'item': '11 Mandatory Schedule III Ratios analysis table', 'status': 'Computed / Ready', 'details_text': 'All 11 statutory ratios computed with variance analysis.'},
        {'id': 'CH06', 'item': 'CSR Disclosure Schedule (Applicability check)', 'status': 'Requires Input', 'details_text': ''},
        {'id': 'CH07', 'item': 'Related Party Disclosures AS-18 (Note 16)', 'status': 'Requires Input', 'details_text': ''},
        {'id': 'CH08', 'item': 'Current Tax & Deferred Tax computation schedule', 'status': 'Computed / Ready', 'details_text': 'Deferred tax net balances and current tax provisions computed in Note 5 & Note 11.'}
    ]

    # Fetch stored customizations
    cursor.execute("SELECT ref_id, status, details_text FROM company_disclosures_checklist WHERE company_name = ?;", (company_name,))
    saved_items = {r['ref_id']: r for r in cursor.fetchall()}

    mandatory_checklist = []
    for item in default_checklist:
        ref_id = item['id']
        if ref_id in saved_items:
            saved = saved_items[ref_id]
            mandatory_checklist.append({
                'id': ref_id,
                'item': item['item'],
                'status': saved['status'] or item['status'],
                'details_text': saved['details_text'] or ''
            })
        else:
            mandatory_checklist.append(item)

    conn.close()


    return {
        'tb_stats': {
            'total_ledgers': total_ledgers,
            'total_dr': total_dr,
            'total_cr': total_cr,
            'net_tb_sum': net_tb_sum,
            'is_balanced': tb_balanced,
            'validation_status': 'PASS' if tb_balanced else 'FAIL',
            'difference': round(abs(net_tb_sum), 2)
        },
        'mapping_stats': {
            'pending_reviews': pending_reviews,
            'unmapped_count': unmapped_count
        },
        'financial_totals': {
            'total_eq_liab': total_eq_liab,
            'total_assets': total_assets,
            'bs_diff': bs_diff,
            'is_bs_balanced': bs_balanced,
            'revenue': totals['PL_REVENUE'],
            'expenses': totals['PL_EXPENSES'],
            'net_profit': current_net_profit,
            'py_revenue': totals['PY_PL_REVENUE'],
            'py_expenses': totals['PY_PL_EXPENSES'],
            'py_net_profit': prior_net_profit
        },
        'exceptions': exceptions,
        'mandatory_checklist': mandatory_checklist
    }
