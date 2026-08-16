#!/usr/bin/env python3
"""
itr_import_parse.py — Parse Computax "Returns Filed Details" XLS/XLSX
Uses only xlrd (for .xls) or openpyxl (for .xlsx) — no pandas required.
Called by itr_import.php: python3 itr_import_parse.py <filepath> <ext>
Outputs JSON to stdout.
"""
import sys, json, re

def parse_date_dmy(val):
    """Convert dd/mm/yyyy -> yyyy-mm-dd, handles trailing text like '(EV)'"""
    if not val:
        return None
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', str(val).strip())
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None

def parse_ack(val):
    """Return ACK as string, handles numeric float like 652039940170726.0"""
    if val is None or str(val).strip() in ('', 'nan', 'None'):
        return None
    try:
        # xlrd returns large ints as float (e.g. 6.52e14) — convert via int
        s = str(int(float(str(val).strip())))
        return s if 10 <= len(s) <= 15 else None
    except (ValueError, TypeError):
        s = re.sub(r'[\s\-]', '', str(val).strip())
        return s if 10 <= len(s) <= 15 else None

def is_ev(val):
    return '(EV)' in str(val or '').upper()

def clean(val):
    s = str(val).strip()
    return '' if s in ('nan', 'None', '-') else s

def find_header_row(rows):
    """Find the row index where PAN column header appears"""
    for i, row in enumerate(rows):
        vals = [clean(v).upper() for v in row]
        if 'PAN' in vals:
            return i
    return None

def col_index(header_row, *names):
    """Find column index by name (case-insensitive partial match)"""
    for name in names:
        for i, h in enumerate(header_row):
            if name.lower() in str(h).lower():
                return i
    return None

def parse_xls(filepath):
    try:
        import xlrd
    except ImportError:
        return None, 'xlrd not installed. Run: pip install xlrd --break-system-packages'
    try:
        wb = xlrd.open_workbook(filepath)
        ws = wb.sheet_by_index(0)
        all_rows = [[ws.cell_value(r, c) for c in range(ws.ncols)] for r in range(ws.nrows)]
        return all_rows, None
    except Exception as e:
        return None, str(e)

def parse_xlsx(filepath):
    try:
        import openpyxl
    except ImportError:
        return None, 'openpyxl not installed. Run: pip install openpyxl --break-system-packages'
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active
        all_rows = [[cell.value for cell in row] for row in ws.iter_rows()]
        return all_rows, None
    except Exception as e:
        return None, str(e)

def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Usage: itr_import_parse.py <filepath> <ext>'}))
        sys.exit(1)

    filepath = sys.argv[1]
    ext      = sys.argv[2].lower().strip('.')

    if ext == 'xls':
        all_rows, err = parse_xls(filepath)
    else:
        all_rows, err = parse_xlsx(filepath)

    if err:
        print(json.dumps({'error': err}))
        sys.exit(1)

    header_idx = find_header_row(all_rows)
    if header_idx is None:
        print(json.dumps({'error': 'Header row not found. Expected a row containing PAN column.'}))
        sys.exit(1)

    header = all_rows[header_idx]
    col_pan      = col_index(header, 'pan')
    col_ack      = col_index(header, 'return serial number')
    col_filed    = col_index(header, 'date of return filing')
    col_ev       = col_index(header, 'electronic verified', 'form v send')
    col_gti      = col_index(header, 'gross income', 'gross total')
    col_itr_form = col_index(header, 'itr type', 'itr_type')
    col_name     = col_index(header, 'name of assessee', 'name')

    if col_pan is None or col_ack is None:
        print(json.dumps({'error': f'PAN or Return Serial Number column not found. Headers: {header[:10]}'}))
        sys.exit(1)

    rows = []
    for row in all_rows[header_idx + 1:]:
        if len(row) <= col_pan:
            continue
        pan = clean(row[col_pan]).upper()
        if not pan or len(pan) != 10 or not pan[0].isalpha():
            continue

        ack      = parse_ack(row[col_ack]) if col_ack is not None and col_ack < len(row) else None
        filed    = parse_date_dmy(row[col_filed]) if col_filed is not None and col_filed < len(row) else None
        ev_raw   = row[col_ev] if col_ev is not None and col_ev < len(row) else ''
        e_verif  = is_ev(ev_raw)
        gti      = None
        if col_gti is not None and col_gti < len(row):
            try:
                g = row[col_gti]
                if g not in (None, '') and str(g).strip() not in ('nan','None','-'):
                    gti = float(g)
            except (ValueError, TypeError):
                pass
        itr_form = clean(row[col_itr_form]) if col_itr_form is not None and col_itr_form < len(row) else ''
        name     = clean(row[col_name]) if col_name is not None and col_name < len(row) else ''

        rows.append({
            'pan':        pan,
            'itr_ack':    ack,
            'filed_date': filed,
            'e_verified': e_verif,
            'gti':        gti,
            'itr_form':   itr_form or None,
            'name':       name,
        })

    print(json.dumps({'rows': rows, 'count': len(rows)}))

if __name__ == '__main__':
    main()
