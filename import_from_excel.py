#!/usr/bin/env python3
"""
One-time importer: converts the source 'Billing' + 'Prime Cost' sheets of the
Kashyap & Co. workbook into data/db.json, the seed database used by the app.

Usage:
    python3 scripts/import_from_excel.py /path/to/Capstone_Project_Level_2_KV.xlsx

This script is provided for transparency/reproducibility only. The app itself
does NOT need Excel or Python to run -- data/db.json already ships with the
project, pre-built by this script. Re-run it only if you want to rebuild the
seed data from a fresh copy of the source workbook (this OVERWRITES
data/db.json, so keep a backup if you have made manual entries in the app).

Requires: openpyxl, pandas  (pip install openpyxl pandas)
"""
import sys
import re
import math
import json
from collections import Counter, defaultdict

try:
    import openpyxl
    import pandas as pd
except ImportError:
    print("This script needs 'openpyxl' and 'pandas'. Install with:")
    print("    pip install openpyxl pandas")
    sys.exit(1)

MANAGER_NAMES = ['Manager 1', 'Manager 2', 'Manager 3', 'Manager 4']
OVERHEAD_RATE = 0.30  # kept here only for the printed sanity-check; the live
                       # app computes this itself in lib/allocation.js


def norm_client(x):
    """Clean up client / capstone names, fixing known typos like 'Clent'."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    x = str(x).strip()
    x = re.sub(r'^Clent', 'Client', x)
    x = re.sub(r'\s+', ' ', x)
    return x


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def clean_str(x):
    """Coerce a cell value to a plain string, turning NaN/None into ''."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ''
    return str(x).strip()


def main(path):
    wb = openpyxl.load_workbook(path, data_only=True)

    # ---------------- Billing sheet: Sales Register ----------------
    ws = wb['Billing']
    brows = []
    for r in range(9, 151):
        row = [ws.cell(row=r, column=c).value for c in range(1, 8)]
        if row[1] is None:
            continue
        brows.append(row)
    bdf = pd.DataFrame(brows, columns=['Date', 'Capstone', 'Manager', 'VoucherType', 'MID', 'Milestone', 'Amount'])
    bdf['Capstone'] = bdf['Capstone'].apply(norm_client)
    bdf['Manager'] = bdf['Manager'].astype(str).str.strip()
    bdf['Amount'] = bdf['Amount'].astype(float)

    # ---------------- Billing sheet: Credit Note ----------------
    crows = []
    for r in range(157, 164):
        row = [ws.cell(row=r, column=c).value for c in range(1, 9)]
        if row[1] is None:
            continue
        crows.append(row)
    cdf = pd.DataFrame(crows, columns=['Date', 'Capstone', 'Blank', 'VoucherType', 'MID', 'Milestone', 'Amount', 'Other'])
    cdf['Capstone'] = cdf['Capstone'].apply(norm_client)
    cdf['Amount'] = cdf['Amount'].astype(float)
    cdf['Other'] = cdf['Other'].fillna(0).astype(float)

    # ---------------- Prime Cost sheet ----------------
    ws2 = wb['Prime Cost']
    prows = []
    for r in range(8, 170):
        b, c, d, e, f = [ws2.cell(row=r, column=col).value for col in range(2, 7)]
        if d is None and e is None and (f is None or f == ' '):
            continue
        prows.append((r, b, c, d, e, f))
    pdf = pd.DataFrame(prows, columns=['row', 'SlNo', 'Designation', 'Manager', 'Capstone', 'PrimeCost'])
    pdf['Capstone'] = pdf['Capstone'].apply(norm_client)
    pdf['Manager'] = pdf['Manager'].astype(str).str.strip()
    pdf['PrimeCost'] = pdf['PrimeCost'].astype(float)

    # ---------------- Assignments (= clients / capstones) ----------------
    all_clients = sorted(
        set(bdf['Capstone'].dropna().unique())
        | set(pdf.loc[pdf['Capstone'].notna() & (pdf['Capstone'] != 'Many Assignments'), 'Capstone'].unique())
    )

    sales_by_client = bdf.groupby('Capstone')['Amount'].sum()
    credit_by_client = cdf.groupby('Capstone')['Amount'].sum()

    cost_client_mgr = (
        pdf[pdf['Capstone'].notna() & (pdf['Capstone'] != 'Many Assignments')]
        .groupby('Capstone')['Manager']
        .agg(lambda s: Counter(s).most_common(1)[0][0])
    )
    bill_client_mgr = bdf.groupby('Capstone')['Manager'].agg(lambda s: Counter(s).most_common(1)[0][0])

    manager_id = {name: slugify(name) for name in MANAGER_NAMES}
    manager_id['Partner'] = 'partner'

    assignments = []
    assignment_id_by_name = {}
    for cl in all_clients:
        mgr_name = cost_client_mgr.get(cl) or bill_client_mgr.get(cl)
        mgr_id = manager_id.get(mgr_name, None)
        billing = float(sales_by_client.get(cl, 0.0) - credit_by_client.get(cl, 0.0))
        aid = 'assignment-' + slugify(cl)
        assignment_id_by_name[cl] = aid
        assignments.append({
            'id': aid,
            'name': cl,
            'managerId': mgr_id,
            'status': 'completed' if billing > 0 else 'in-progress',
            'notes': '',
            'createdAt': '2026-04-01',
        })

    # ---------------- Managers ----------------
    managers = [{'id': manager_id[n], 'name': n, 'isPartner': False} for n in MANAGER_NAMES]
    managers.append({'id': 'partner', 'name': 'Partner', 'isPartner': True})

    # ---------------- Staff / prime cost rows ----------------
    staff = []
    sidx = 1
    for _, row in pdf.iterrows():
        mgr_name = row['Manager']
        capstone = row['Capstone']
        cost = float(row['PrimeCost'])
        designation = row['Designation'] if isinstance(row['Designation'], str) else 'Staff'
        sl_no = row['SlNo']

        if mgr_name == 'Partner':
            scope = 'partner'
            mgr_id = 'partner'
            a_id = None
        elif capstone == 'Many Assignments':
            scope = 'many'
            mgr_id = manager_id.get(mgr_name)
            a_id = None
        else:
            scope = 'dedicated'
            mgr_id = manager_id.get(mgr_name)
            a_id = assignment_id_by_name.get(capstone)

        label = designation if not (isinstance(sl_no, float) and math.isnan(sl_no)) else designation
        sl_label = '' if sl_no is None or (isinstance(sl_no, float) and math.isnan(sl_no)) else f' #{int(sl_no)}'
        staff.append({
            'id': f'staff-{sidx}',
            'name': f'{designation}{sl_label}',
            'designation': designation,
            'managerId': mgr_id,
            'assignmentId': a_id,
            'scope': scope,
            'cost': cost,
            'period': 'Apr-Aug 2026',
            'notes': '',
        })
        sidx += 1

    # ---------------- Revenue (billing + credit notes) ----------------
    revenue = []
    ridx = 1
    for _, row in bdf.iterrows():
        aid = assignment_id_by_name.get(row['Capstone'])
        if aid is None:
            continue
        revenue.append({
            'id': f'rev-{ridx}',
            'assignmentId': aid,
            'date': row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date']),
            'type': 'billing',
            'voucherType': clean_str(row['VoucherType']),
            'mid': clean_str(row['MID']),
            'milestone': clean_str(row['Milestone']),
            'amount': float(row['Amount']),
            'otherCharges': 0,
            'notes': '',
        })
        ridx += 1
    for _, row in cdf.iterrows():
        aid = assignment_id_by_name.get(row['Capstone'])
        if aid is None:
            continue
        revenue.append({
            'id': f'rev-{ridx}',
            'assignmentId': aid,
            'date': row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date']),
            'type': 'credit',
            'voucherType': clean_str(row['VoucherType']),
            'mid': clean_str(row['MID']),
            'milestone': clean_str(row['Milestone']),
            'amount': float(row['Amount']),
            'otherCharges': float(row['Other']),
            'notes': 'Credit note',
        })
        ridx += 1

    db = {
        'meta': {
            'firmName': 'Kashyap & Co.',
            'firmTagline': 'Chartered Accountants - Risk Advisory Practice',
            'overheadRate': OVERHEAD_RATE,
            'sourcePeriod': '1-Apr-26 to 31-Aug-26',
            'nextIds': {'staff': sidx, 'revenue': ridx},
        },
        'managers': managers,
        'assignments': assignments,
        'staff': staff,
        'revenue': revenue,
    }

    out_path = 'data/db.json'
    with open(out_path, 'w') as f:
        json.dump(db, f, indent=2)
    print(f'Wrote {out_path}: {len(assignments)} assignments, {len(staff)} staff rows, {len(revenue)} revenue rows.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 scripts/import_from_excel.py <path-to-xlsx>')
        sys.exit(1)
    main(sys.argv[1])
