#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial_Dashboard.py  -  QuickBooks Online Financial Analytics Dashboard
==========================================================================
Zero third-party dependencies (Python standard library only).
Reads QBO exports (General Ledger, month-wise P&L, month-wise Balance Sheet)
from a folder you select, validates / reconciles them, and opens a CFO-style
dashboard in your browser (served locally on 127.0.0.1 - nothing is uploaded).

Run:  double-click Run_Dashboard.bat   OR   python Financial_Dashboard.py   OR   F5 in IDLE
"""
import sys, os, re, io, json, math, time, zipfile, threading, subprocess, traceback
import webbrowser, datetime, collections, socket, urllib.parse, calendar, bisect
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

APP_NAME = "Financial Analytics Dashboard"
sys.setrecursionlimit(20000)


def ensure_dependencies():
    """This app needs only the Python standard library. Verify the modules it uses."""
    needed = ["zipfile", "xml.etree.ElementTree", "http.server", "json", "threading", "subprocess"]
    missing = []
    for m in needed:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if missing:
        print("ERROR: your Python installation is missing standard modules:", ", ".join(missing))
        print("Reinstall Python from python.org (standard installer).")
        sys.exit(1)


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
_MN = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
       'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
_MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def num(v):
    """Coerce a cell to float or None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return None
    s = str(v).strip().replace('$', '').replace(',', '').replace('\u00a0', '')
    if not s or s in ('-', '\u2014', '\u2013'):
        return None
    neg = s.startswith('(') and s.endswith(')')
    if neg:
        s = s[1:-1]
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def parse_month(v):
    """Return 'YYYY-MM' for a month header (text 'Jan 2025' / date) else None."""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return "%04d-%02d" % (v.year, v.month)
    if not isinstance(v, str):
        return None
    s = v.strip()
    m = re.match(r"^([A-Za-z]{3,9})\.?[\s\-/,']*(\d{4}|\d{2})$", s)
    if m and m.group(1)[:3].lower() in _MN:
        y = int(m.group(2))
        if y < 100:
            y += 2000
        return "%04d-%02d" % (y, _MN[m.group(1)[:3].lower()])
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return "%04d-%02d" % (int(m.group(1)), int(m.group(2)))
    return None


def ym_add(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + (m - 1) + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def ym_label(ym):
    return "%s %s" % (_MONTH_ABBR[int(ym[5:7]) - 1], ym[:4])


def ym_quarter(ym):
    return "%s-Q%d" % (ym[:4], (int(ym[5:7]) - 1) // 3 + 1)


def norm(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().lower()


def clean_json(o):
    """Make structure JSON-safe (NaN/inf -> None, round floats)."""
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
        return round(o, 4)
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, set):
        return sorted(clean_json(v) for v in o)
    return o


# ----------------------------------------------------------------------------
# XLSX reader (zip + xml, no external libraries)
# ----------------------------------------------------------------------------
_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
_RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
_BUILTIN_DATE_FMTS = {14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47}


class Sheet(object):
    def __init__(self):
        self.rows = {}
        self.max_row = 0
        self.max_col = 0
        self.dim_rows = 0
        self.name = ''

    def get(self, r, c):
        row = self.rows.get(r)
        if row is None or c >= len(row):
            return None
        return row[c]

    def row(self, r):
        return self.rows.get(r) or []


def _col_idx(ref):
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n - 1


def _date_styles(z, names):
    if 'xl/styles.xml' not in names:
        return set()
    try:
        root = ET.fromstring(z.read('xl/styles.xml'))
    except Exception:
        return set()
    custom = set()
    nf = root.find(_NS + 'numFmts')
    if nf is not None:
        for f in nf.findall(_NS + 'numFmt'):
            code = re.sub(r'"[^"]*"|\[[^\]]*\]', '', f.get('formatCode') or '')
            if re.search(r'[ymd]', code, re.I) and not re.search(r'0\.0|#', code):
                custom.add(int(f.get('numFmtId')))
    out = set()
    xfs = root.find(_NS + 'cellXfs')
    if xfs is not None:
        for i, xf in enumerate(xfs.findall(_NS + 'xf')):
            fid = int(xf.get('numFmtId') or 0)
            if fid in _BUILTIN_DATE_FMTS or fid in custom:
                out.add(i)
    return out


def _first_sheet_path(z, names):
    try:
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relmap = {r.get('Id'): r.get('Target') for r in rels}
        sheets = wb.find(_NS + 'sheets')
        for s in sheets.findall(_NS + 'sheet'):
            if s.get('state') in ('hidden', 'veryHidden'):
                continue
            tgt = relmap.get(s.get(_RNS + 'id'))
            if tgt:
                tgt = tgt.lstrip('/')
                p = tgt if tgt.startswith('xl/') else 'xl/' + tgt
                if p in names:
                    return p, s.get('name')
    except Exception:
        pass
    for n in sorted(names):
        if n.startswith('xl/worksheets/') and n.endswith('.xml'):
            return n, 'Sheet1'
    raise ValueError("No worksheet found in file")


def _excel_date(serial):
    try:
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(serial))
    except Exception:
        return None


_REF_RE = re.compile(r'([A-Z]{1,3})(\d+)')


def _eval_pending(sh, pending):
    """Evaluate simple formulas (+ - * / SUM) for cells that have no cached value."""
    memo = {}

    def val(r, c, depth):
        k = (r, c)
        if k in memo:
            return memo[k]
        v = sh.get(r, c)
        if v is None and k in pending:
            memo[k] = 0.0
            v = ev(pending[k], depth + 1)
            sh_set(r, c, v)
        x = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
        memo[k] = x
        return x

    def sh_set(r, c, v):
        row = sh.rows.setdefault(r, [])
        while len(row) <= c:
            row.append(None)
        row[c] = v

    def rng_sum(part, depth):
        part = part.strip()
        m = re.match(r'^([A-Z]{1,3})(\d+):([A-Z]{1,3})(\d+)$', part)
        if m:
            c1, r1, c2, r2 = _col_idx(m.group(1)), int(m.group(2)), _col_idx(m.group(3)), int(m.group(4))
            t = 0.0
            for rr in range(min(r1, r2), max(r1, r2) + 1):
                for cc in range(min(c1, c2), max(c1, c2) + 1):
                    t += val(rr, cc, depth)
            return t
        m = _REF_RE.fullmatch(part)
        if m:
            return val(int(m.group(2)), _col_idx(m.group(1)), depth)
        try:
            return float(part)
        except ValueError:
            return 0.0

    def ev(f, depth):
        if depth > 400:
            return None
        f = f.upper().replace('$', '').lstrip('=')
        f = re.sub(r'SUM\(([^)]*)\)', lambda m: repr(sum(rng_sum(p, depth) for p in m.group(1).split(','))), f)
        f = _REF_RE.sub(lambda m: repr(val(int(m.group(2)), _col_idx(m.group(1)), depth)), f)
        if not re.fullmatch(r'[0-9eE+\-*/(). ]*', f):
            return None
        try:
            return float(eval(f, {'__builtins__': {}}, {}))
        except Exception:
            return None

    for (r, c) in list(pending.keys()):
        if sh.get(r, c) is None:
            val(r, c, 0)


def read_xlsx(path, max_rows=None, progress=None):
    """Read the first visible worksheet. Returns Sheet (rows are 0-based column lists)."""
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    shared = []
    if 'xl/sharedStrings.xml' in names:
        with z.open('xl/sharedStrings.xml') as f:
            for ev, el in ET.iterparse(f):
                if el.tag == _NS + 'si':
                    shared.append(''.join(t.text or '' for t in el.iter(_NS + 't')))
                    el.clear()
    date_styles = _date_styles(z, names)
    spath, sname = _first_sheet_path(z, names)
    sh = Sheet()
    sh.name = sname
    pending = {}
    with z.open(spath) as f:
        for ev, el in ET.iterparse(f):
            tag = el.tag
            if tag == _NS + 'dimension':
                m = re.search(r':[A-Z]+(\d+)$', el.get('ref') or '')
                if m:
                    sh.dim_rows = int(m.group(1))
            elif tag == _NS + 'row':
                r = int(el.get('r') or (sh.max_row + 1))
                vals = []
                for c in el.findall(_NS + 'c'):
                    ref = c.get('r')
                    ci = _col_idx(ref) if ref else len(vals)
                    t = c.get('t')
                    v = c.find(_NS + 'v')
                    fe = c.find(_NS + 'f')
                    val = None
                    if t == 'inlineStr':
                        is_ = c.find(_NS + 'is')
                        if is_ is not None:
                            val = ''.join(x.text or '' for x in is_.iter(_NS + 't'))
                    elif v is None or v.text is None:
                        val = None
                    elif t == 's':
                        try:
                            val = shared[int(v.text)]
                        except Exception:
                            val = None
                    elif t == 'str':
                        val = v.text
                    elif t == 'e':
                        val = None
                    elif t == 'b':
                        val = bool(int(v.text))
                    else:
                        try:
                            val = float(v.text)
                        except ValueError:
                            val = None
                        s = c.get('s')
                        if val is not None and s is not None and int(s) in date_styles:
                            val = _excel_date(val)
                    if val is None and fe is not None and fe.text:
                        pending[(r, ci)] = fe.text
                    while len(vals) <= ci:
                        vals.append(None)
                    vals[ci] = val
                el.clear()
                if any(x is not None for x in vals):
                    sh.rows[r] = vals
                sh.max_row = max(sh.max_row, r)
                sh.max_col = max(sh.max_col, len(vals))
                if progress and sh.dim_rows and r % 2000 == 0:
                    progress(min(1.0, r / float(sh.dim_rows)))
                if max_rows and r >= max_rows:
                    break
    z.close()
    if pending:
        for (r, c) in pending:
            sh.rows.setdefault(r, [])
        _eval_pending(sh, pending)
        sh.max_row = max([sh.max_row] + list(sh.rows.keys()))
    return sh


# ----------------------------------------------------------------------------
# File detection
# ----------------------------------------------------------------------------
def sniff(path):
    try:
        sh = read_xlsx(path, max_rows=14)
    except Exception:
        return None
    texts = []
    for r in range(1, 9):
        v = sh.get(r, 0)
        texts.append(str(v).strip() if v is not None else '')
    joined = ' '.join(texts).lower()
    has_txn_hdr = False
    for r in range(1, 15):
        for v in sh.row(r):
            if isinstance(v, str) and norm(v) in ('transaction date', 'date'):
                has_txn_hdr = True
                if norm(v) == 'date' and 'general ledger' not in joined:
                    has_txn_hdr = False
    rtype = None
    if 'general ledger' in joined or (has_txn_hdr and 'ledger' in joined):
        rtype = 'GL'
    elif re.search(r'profit\s*(and|&)\s*loss|income statement|statement of (operations|income)', joined):
        rtype = 'PL'
    elif 'balance sheet' in joined or 'statement of financial position' in joined:
        rtype = 'BS'
    elif has_txn_hdr:
        rtype = 'GL'
    if not rtype:
        return None
    return {'path': path, 'name': os.path.basename(path), 'type': rtype,
            'company': texts[0], 'title': texts[1], 'period_text': texts[2],
            'mtime': os.path.getmtime(path)}


def list_excel_files(folder, depth=2):
    out = []
    base_depth = folder.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(folder):
        if root.count(os.sep) - base_depth >= depth:
            dirs[:] = []
        for fn in files:
            if fn.startswith('~$'):
                continue
            if fn.lower().endswith(('.xlsx', '.xlsm')):
                out.append(os.path.join(root, fn))
    out.sort(key=lambda p: (p.count(os.sep), p.lower()))
    return out


def scan_folder(folder):
    if not folder or not os.path.isdir(folder):
        raise ValueError("Folder not found: %s" % folder)
    files, skipped = [], []
    for p in list_excel_files(folder):
        info = sniff(p)
        if info:
            files.append(info)
        else:
            skipped.append({'name': os.path.basename(p), 'path': p})
    by = collections.defaultdict(list)
    for f in files:
        by[f['type']].append(f)
    companies = collections.Counter(norm(f['company']) for f in files)
    top_company = companies.most_common(1)[0][0] if companies else ''
    chosen, warnings = {}, []
    for t in ('PL', 'BS', 'GL'):
        c = by.get(t, [])
        if not c:
            continue
        c.sort(key=lambda f: (norm(f['company']) == top_company, f['mtime']), reverse=True)
        chosen[t] = c[0]['path']
        if len(c) > 1:
            warnings.append("Multiple %s files found; using the most recent: %s" % (
                {'PL': 'Profit & Loss', 'BS': 'Balance Sheet', 'GL': 'General Ledger'}[t], c[0]['name']))
    return {'folder': folder, 'files': files, 'chosen': chosen, 'warnings': warnings, 'skipped': skipped}


# ----------------------------------------------------------------------------
# Statement parsing (QBO P&L / Balance Sheet)
# ----------------------------------------------------------------------------
_TOTAL_RE = re.compile(r'^total\s+for\s+(.+)$|^total\s+(.+)$', re.I)
_CALC_RE = re.compile(r'^(gross profit|gross margin|net operating income|net other income|net income|net earnings|'
                      r'net profit|net loss|operating income|net ordinary income|net income \(loss\)|income from operations)$', re.I)
_FOOTER_RE = re.compile(r'(accrual|cash)\s+basis|gmt[+-]|^basis:', re.I)


def pl_section(top):
    t = norm(top)
    if t in ('other income', 'other income/expense', 'other revenue') or t.startswith('other income'):
        return 'othinc'
    if t.startswith('other expense'):
        return 'othexp'
    if t.startswith(('cost of goods', 'cost of sales', 'cogs', 'cost of revenue', 'cost of services')):
        return 'cogs'
    if t.startswith(('income', 'revenue', 'sales', 'turnover')):
        return 'income'
    if 'expense' in t:
        return 'opex'
    return None


def bs_class(path, label):
    for p in path:
        t = norm(p)
        if t in ('assets', 'total assets') or t == 'asset':
            return 'asset'
        if t == 'liabilities':
            return 'liab'
        if t == 'equity' or t == "owner's equity" or t == "shareholders' equity" or t == "stockholders' equity":
            return 'equity'
    t = norm(label)
    if 'equity' in t or 'retained' in t or 'capital' in t:
        return 'equity'
    if 'liabilit' in t or 'payable' in t or 'loan' in t:
        return 'liab'
    return 'asset'


class Statement(object):
    def __init__(self, kind):
        self.kind = kind
        self.months = []
        self.leaves = []        # dicts
        self.reported = {}      # path tuple -> vals (reported 'Total for X')
        self.calcs = {}         # normalized label -> vals
        self.header_row = 0
        self.company = ''
        self.title = ''
        self.period_text = ''
        self.basis = ''
        self.nodes = []         # flat pre-order tree nodes
        self.node_by_path = {}
        self.warnings = []

    def mi(self, ym):
        try:
            return self.months.index(ym)
        except ValueError:
            return None


def parse_statement(sh, kind):
    # header row = first row with >= 2 month cells
    hr, mcols = None, []
    for r in range(1, min(sh.max_row, 20) + 1):
        cols = []
        for ci, v in enumerate(sh.row(r)):
            if ci == 0:
                continue
            ym = parse_month(v)
            if ym:
                cols.append((ci, ym))
        if len(cols) >= 2:
            hr, mcols = r, cols
            break
    if hr is None:
        raise ValueError("No month-wise columns found. Export the report with 'Display columns by: Months'.")
    seen = set()
    cols2 = []
    for ci, ym in mcols:
        if ym in seen:
            continue
        seen.add(ym)
        cols2.append((ci, ym))
    mcols = cols2
    st = Statement(kind)
    st.header_row = hr
    st.months = [ym for _, ym in mcols]
    st.company = str(sh.get(1, 0) or '').strip()
    st.title = str(sh.get(2, 0) or '').strip()
    st.period_text = str(sh.get(3, 0) or '').strip()
    for r in range(sh.max_row, max(sh.max_row - 6, hr), -1):
        v = sh.get(r, 0)
        if isinstance(v, str) and re.search(r'(accrual|cash)\s+basis', v, re.I):
            st.basis = 'Accrual' if 'accrual' in v.lower() else 'Cash'
            break
    # collect rows
    rows = []
    for r in range(hr + 1, sh.max_row + 1):
        lab = sh.get(r, 0)
        if lab is None:
            continue
        lab = re.sub(r'\s+', ' ', str(lab)).strip()
        if not lab or _FOOTER_RE.search(lab):
            continue
        raw = [sh.get(r, ci) for ci, _ in mcols]
        vals = [num(v) for v in raw]
        rows.append({'row': r, 'label': lab, 'vals': vals, 'has': any(v is not None for v in vals)})
    # pair 'Total for X' rows with their group header rows
    starts = {}   # header idx -> total idx
    totals = {}   # total idx -> header idx
    for i, row in enumerate(rows):
        m = _TOTAL_RE.match(row['label'])
        if not m:
            continue
        gname = norm(m.group(1) or m.group(2))
        for j in range(i - 1, -1, -1):
            if j in starts:
                continue
            if norm(rows[j]['label']) == gname and not _TOTAL_RE.match(rows[j]['label']):
                starts[j] = i
                totals[i] = j
                break
    n = len(st.months)
    stack = []
    lid = 0
    for i, row in enumerate(rows):
        lab, vals = row['label'], row['vals']
        if i in starts:
            stack.append(lab)
            if row['has']:
                lid += 1
                st.leaves.append({'id': lid, 'label': lab, 'display': lab + ' (general)', 'gl_name': lab,
                                  'path': tuple(stack), 'vals': [v or 0.0 for v in vals], 'direct': True,
                                  'row': row['row']})
            continue
        if i in totals:
            key = tuple(stack)
            if stack:
                st.reported[key] = [v or 0.0 for v in vals]
                stack.pop()
            continue
        if _TOTAL_RE.match(lab) and not row['has']:
            continue
        if not stack and _CALC_RE.match(lab):
            st.calcs[norm(lab)] = [v or 0.0 for v in vals]
            continue
        if not stack and not row['has']:
            continue   # stray label
        if not row['has']:
            continue   # empty account line
        lid += 1
        st.leaves.append({'id': lid, 'label': lab, 'display': lab, 'gl_name': lab, 'path': tuple(stack),
                          'vals': [v or 0.0 for v in vals], 'direct': False, 'row': row['row']})
    if not st.leaves:
        raise ValueError("No accounts found in the statement.")
    # classify leaves
    for lf in st.leaves:
        if kind == 'PL':
            sec = pl_section(lf['path'][0]) if lf['path'] else None
            lf['section'] = sec or 'opex'
        else:
            lf['cls'] = bs_class(lf['path'], lf['label'])
    st.nodes, st.node_by_path = build_tree(st.leaves)
    return st


def build_tree(leaves):
    nodes, by_path = [], {}
    for lf in leaves:
        path = lf['path']
        for d in range(1, len(path) + 1):
            p = path[:d]
            if p not in by_path:
                nd = {'path': p, 'name': p[-1], 'level': d - 1, 'leaf': None, 'leaves': [], 'kind': 'group',
                      'parent': p[:-1] if d > 1 else None}
                by_path[p] = nd
                nodes.append(nd)
        if lf['direct']:
            nd = {'path': path + (lf['display'],), 'name': lf['display'], 'level': len(path), 'leaf': lf,
                  'leaves': [lf], 'kind': 'leaf', 'parent': path}
        else:
            nd = {'path': path + (lf['label'],), 'name': lf['label'], 'level': len(path), 'leaf': lf, 'leaves': [lf],
                  'kind': 'leaf', 'parent': path if path else None}
        by_path[nd['path']] = nd
        nodes.append(nd)
        for d in range(1, len(path) + 1):
            by_path[path[:d]]['leaves'].append(lf)
    return nodes, by_path


# ----------------------------------------------------------------------------
# General ledger parsing
# ----------------------------------------------------------------------------
_GL_HDR = {
    'distribution account': 'acct', 'account': 'acct', 'account name': 'acct',
    'transaction date': 'date', 'date': 'date',
    'transaction type': 'type', 'type': 'type',
    'num': 'num', 'no.': 'num', 'number': 'num',
    'name': 'name', 'description': 'desc', 'memo/description': 'desc', 'memo': 'desc',
    'split': 'split', 'split account': 'split', 'amount': 'amount', 'balance': 'balance',
    'debit': 'debit', 'credit': 'credit',
}
# record tuple indexes
R_DATE, R_ACCT, R_TYPE, R_NUM, R_NAME, R_DESC, R_SPLIT, R_AMT, R_BAL, R_DR, R_CR, R_ROW = range(12)
DEBIT_NORMAL = ('asset', 'cogs', 'opex', 'othexp')


def parse_gl_date(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return "%04d-%02d-%02d" % (v.year, v.month, v.day)
    if not isinstance(v, str):
        return None
    s = v.strip()
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:
            a, b = b, a
        return "%04d-%02d-%02d" % (y, a, b)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return "%s-%s-%s" % m.groups()
    return None


class GLData(object):
    def __init__(self):
        self.recs = []
        self.accounts = collections.OrderedDict()   # name -> info
        self.acct_month = collections.defaultdict(lambda: collections.defaultdict(float))
        self.acct_month_dr = collections.defaultdict(lambda: collections.defaultdict(float))
        self.acct_month_cr = collections.defaultdict(lambda: collections.defaultdict(float))
        self.acct_month_n = collections.defaultdict(lambda: collections.defaultdict(int))
        self.date_min = None
        self.date_max = None
        self.company = ''
        self.title = ''
        self.period_text = ''
        self.basis = ''
        self.warnings = []
        self.has_dc_cols = False
        self.months = []
        self.skipped_rows = 0


def parse_gl(sh, progress=None):
    hr, colmap = None, {}
    for r in range(1, min(sh.max_row, 20) + 1):
        cm = {}
        for ci, v in enumerate(sh.row(r)):
            if isinstance(v, str) and norm(v) in _GL_HDR:
                key = _GL_HDR[norm(v)]
                if key not in cm:
                    cm[key] = ci
        if 'date' in cm and ('amount' in cm or ('debit' in cm and 'credit' in cm)):
            hr, colmap = r, cm
            break
    if hr is None:
        raise ValueError("General Ledger header row (Transaction date / Amount) not found.")
    gl = GLData()
    gl.company = str(sh.get(1, 0) or '').strip()
    gl.title = str(sh.get(2, 0) or '').strip()
    gl.period_text = str(sh.get(3, 0) or '').strip()
    for r in range(sh.max_row, max(sh.max_row - 6, hr), -1):
        v = sh.get(r, 0)
        if isinstance(v, str) and re.search(r'(accrual|cash)\s+basis', v, re.I):
            gl.basis = 'Accrual' if 'accrual' in v.lower() else 'Cash'
            break
    gl.has_dc_cols = 'debit' in colmap and 'credit' in colmap and 'amount' not in colmap
    # section label column: first column (A) ; QBO puts account headers there
    cur = None
    g = lambda row, key: (row[colmap[key]] if key in colmap and colmap[key] < len(row) else None)
    raw = []
    total_rows = n_tot = 0
    for r in range(hr + 1, sh.max_row + 1):
        row = sh.row(r)
        if not row:
            continue
        a = row[0] if len(row) else None
        if a is not None and str(a).strip() != '' and ('date' not in colmap or colmap['date'] != 0):
            a = re.sub(r'\s+', ' ', str(a)).strip()
            if _FOOTER_RE.search(a):
                continue
            m = _TOTAL_RE.match(a)
            if m:
                nm_ = (m.group(1) or m.group(2)).strip()
                is_sub = nm_.lower().endswith(' with sub-accounts')
                if is_sub:
                    nm_ = nm_[:-len(' with sub-accounts')]
                info = gl.accounts.get(nm_)
                if info is not None and 'amount' in colmap:
                    info['reported_total_sub' if is_sub else 'reported_total'] = num(g(row, 'amount'))
                n_tot += 1
                continue
            cur = a
            if cur not in gl.accounts:
                gl.accounts[cur] = {'name': cur, 'begin': 0.0, 'has_begin': False, 'count': 0, 'reported_total': None,
                                    'reported_total_sub': None, 'cls': None, 'last_balance': None}
            continue
        # beginning balance row
        desc_acct = g(row, 'acct')
        if isinstance(desc_acct, str) and norm(desc_acct) == 'beginning balance':
            if cur:
                b = num(g(row, 'balance'))
                gl.accounts[cur]['begin'] = b or 0.0
                gl.accounts[cur]['has_begin'] = b is not None
            continue
        d = parse_gl_date(g(row, 'date'))
        if d is None:
            continue
        if cur is None:
            cur = str(desc_acct or 'Unassigned')
            gl.accounts.setdefault(cur, {'name': cur, 'begin': 0.0, 'has_begin': False, 'count': 0,
                                         'reported_total': None, 'reported_total_sub': None, 'cls': None, 'last_balance': None})
        if gl.has_dc_cols:
            dr, cr = num(g(row, 'debit')), num(g(row, 'credit'))
            amt = (dr or 0.0) - (cr or 0.0)
        else:
            amt = num(g(row, 'amount'))
            if amt is None:
                gl.skipped_rows += 1
                amt = 0.0
            dr = cr = None
        bal = num(g(row, 'balance'))
        typ = g(row, 'type')
        raw.append((d, cur, str(typ or '').strip(), str(g(row, 'num') or '').strip(),
                    str(g(row, 'name') or '').strip(), str(g(row, 'desc') or '').strip(),
                    str(g(row, 'split') or '').strip(), amt, bal, dr, cr, r))
        if progress and len(raw) % 3000 == 0:
            progress(0.5 + 0.5 * min(1.0, r / float(max(sh.max_row, 1))))
    return gl, raw


def finalize_gl(gl, raw, pl, bs):
    """Classify accounts, compute debit/credit columns, monthly sums."""
    clsmap = {}
    if pl:
        for lf in pl.leaves:
            clsmap.setdefault(lf['gl_name'], lf['section'])
        for nd in pl.nodes:
            if nd['kind'] == 'group':
                clsmap.setdefault(nd['name'], nd['leaves'][0]['section'] if nd['leaves'] else 'opex')
    if bs:
        for lf in bs.leaves:
            clsmap[lf['gl_name']] = lf['cls']
        for nd in bs.nodes:
            if nd['kind'] == 'group':
                clsmap.setdefault(nd['name'], nd['leaves'][0]['cls'] if nd['leaves'] else 'asset')
    prev = 'asset'
    for name, info in gl.accounts.items():
        c = clsmap.get(name)
        if c is None:
            c = prev
            info['cls_guess'] = True
        info['cls'] = c
        prev = c
    recs = []
    months = set()
    dmin = dmax = None
    for t in raw:
        info = gl.accounts[t[R_ACCT]]
        cls = info['cls']
        amt = t[R_AMT]
        if t[R_DR] is not None or t[R_CR] is not None:
            dr, cr = t[R_DR] or 0.0, t[R_CR] or 0.0
            amt = (dr - cr) if cls in DEBIT_NORMAL else (cr - dr)
        else:
            if cls in DEBIT_NORMAL:
                dr, cr = (amt, 0.0) if amt >= 0 else (0.0, -amt)
            else:
                dr, cr = (0.0, amt) if amt >= 0 else (-amt, 0.0)
        rec = (t[R_DATE], t[R_ACCT], t[R_TYPE], t[R_NUM], t[R_NAME], t[R_DESC], t[R_SPLIT], amt, t[R_BAL], dr, cr, t[R_ROW])
        recs.append(rec)
        ym = t[R_DATE][:7]
        months.add(ym)
        gl.acct_month[t[R_ACCT]][ym] += amt
        gl.acct_month_dr[t[R_ACCT]][ym] += dr
        gl.acct_month_cr[t[R_ACCT]][ym] += cr
        gl.acct_month_n[t[R_ACCT]][ym] += 1
        info['count'] += 1
        if t[R_BAL] is not None:
            info['last_balance'] = t[R_BAL]
        if dmin is None or t[R_DATE] < dmin:
            dmin = t[R_DATE]
        if dmax is None or t[R_DATE] > dmax:
            dmax = t[R_DATE]
    gl.recs = recs
    gl.date_min, gl.date_max = dmin, dmax
    if dmin:
        a, b = dmin[:7], dmax[:7]
        mm, k = [], a
        while k <= b:
            mm.append(k)
            k = ym_add(k, 1)
        gl.months = mm
    return gl


# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------
class Model(object):
    pass


def load_model(paths, progress=None):
    """paths: {'PL':..., 'BS':..., 'GL':...} (any subset, at least PL or BS)."""
    def prog(frac, msg):
        if progress:
            progress(frac, msg)
    m = Model()
    m.paths = dict(paths)
    m.warnings = []
    m.pl = m.bs = m.gl = None
    m.files = {}
    prog(0.02, "Reading Profit & Loss")
    if paths.get('PL'):
        sh = read_xlsx(paths['PL'])
        m.pl = parse_statement(sh, 'PL')
        m.files['PL'] = {'name': os.path.basename(paths['PL']), 'company': m.pl.company, 'period_text': m.pl.period_text,
                         'basis': m.pl.basis, 'path': paths['PL']}
    prog(0.12, "Reading Balance Sheet")
    if paths.get('BS'):
        sh = read_xlsx(paths['BS'])
        m.bs = parse_statement(sh, 'BS')
        m.files['BS'] = {'name': os.path.basename(paths['BS']), 'company': m.bs.company, 'period_text': m.bs.period_text,
                         'basis': m.bs.basis, 'path': paths['BS']}
    if not m.pl and not m.bs:
        raise ValueError("Need at least a Profit & Loss or a Balance Sheet export.")
    raw = None
    if paths.get('GL'):
        prog(0.2, "Reading General Ledger (large file - please wait)")
        sh = read_xlsx(paths['GL'], progress=lambda f: prog(0.2 + 0.5 * f, "Reading General Ledger"))
        prog(0.72, "Parsing General Ledger")
        gl, raw = parse_gl(sh)
        m.files['GL'] = {'name': os.path.basename(paths['GL']), 'company': gl.company, 'period_text': gl.period_text,
                         'basis': gl.basis, 'path': paths['GL']}
        m.gl = gl
        del sh
    prog(0.85, "Classifying accounts & reconciling")
    if m.gl:
        finalize_gl(m.gl, raw, m.pl, m.bs)
        raw = None
    names = [norm(x.company) for x in (m.pl, m.bs, m.gl) if x is not None and x.company]
    m.company = ''
    for x in (m.pl, m.bs, m.gl):
        if x is not None and x.company:
            m.company = x.company
            break
    if len(set(names)) > 1:
        m.warnings.append("Company name differs between files: " + " | ".join(sorted(set(
            x.company for x in (m.pl, m.bs, m.gl) if x is not None and x.company))))
    bases = set(x.basis for x in (m.pl, m.bs, m.gl) if x is not None and x.basis)
    if len(bases) > 1:
        m.warnings.append("Accounting basis differs between files (%s)." % ", ".join(sorted(bases)))
    m.basis = next(iter(bases)) if len(bases) == 1 else ''
    m.pl_months = set(m.pl.months) if m.pl else set()
    m.bs_months = set(m.bs.months) if m.bs else set()
    m.months = sorted(m.pl_months | m.bs_months)
    # fill gaps between first and last month (so period math is contiguous)
    if m.months:
        allm, k = [], m.months[0]
        while k <= m.months[-1]:
            allm.append(k)
            k = ym_add(k, 1)
        if len(allm) != len(m.months):
            m.warnings.append("Some months are missing between %s and %s in the statements." % (
                ym_label(m.months[0]), ym_label(m.months[-1])))
        m.months = [x for x in allm]
    if m.pl and m.bs and m.pl_months != m.bs_months:
        m.warnings.append("P&L covers %s-%s and Balance Sheet covers %s-%s; each module uses its own available months." % (
            ym_label(m.pl.months[0]), ym_label(m.pl.months[-1]), ym_label(m.bs.months[0]), ym_label(m.bs.months[-1])))
    if m.gl:
        gm = m.gl.months
        out_of = 0
        if m.months:
            lo, hi = m.months[0] + '-01', m.months[-1] + '-31'
            out_of = sum(1 for r in m.gl.recs if r[R_DATE] < lo or r[R_DATE] > hi)
        m.gl_outside = out_of
        if out_of:
            m.warnings.append("General Ledger has %s transactions outside the statement period (%s-%s); the dashboard "
                              "analyses only %s - %s." % (format(out_of, ','), ym_label(gm[0]), ym_label(gm[-1]),
                                                           ym_label(m.months[0]), ym_label(m.months[-1])))
        if m.months and (gm[0] > m.months[0] or gm[-1] < m.months[-1]):
            m.warnings.append("General Ledger does not cover the full statement period; GL-based checks cover only %s - %s." % (
                ym_label(gm[0]), ym_label(gm[-1])))
    else:
        m.gl_outside = 0
        m.warnings.append("No General Ledger file loaded - GL module and GL reconciliations are disabled.")
    prog(0.9, "Computing analytics")
    return m


# ----------------------------------------------------------------------------
# Analytics engine
# ----------------------------------------------------------------------------
def sdiv(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def delta(cur, prev):
    """Absolute and % change; % is None when base is zero or the sign flips."""
    if cur is None or prev is None:
        return {'abs': None, 'pct': None, 'note': 'na'}
    d = cur - prev
    if prev == 0:
        return {'abs': d, 'pct': None, 'note': 'zero' if d != 0 else None}
    if (prev < 0 < cur) or (cur < 0 < prev):
        return {'abs': d, 'pct': None, 'note': 'sign'}
    return {'abs': d, 'pct': d / abs(prev), 'note': None}


def favorable(d, better):
    """better: 'up' / 'down' / None -> 'good' / 'bad' / 'flat' / None"""
    if d is None or better is None:
        return None
    if abs(d) < 0.005:
        return 'flat'
    return 'good' if ((d > 0) == (better == 'up')) else 'bad'


SEC_BETTER = {'income': 'up', 'othinc': 'up', 'cogs': 'down', 'opex': 'down', 'othexp': 'down'}
SEC_LABEL = {'income': 'Income', 'cogs': 'Cost of Goods Sold', 'opex': 'Operating Expenses',
             'othinc': 'Other Income', 'othexp': 'Other Expenses'}


def money(x):
    if x is None:
        return 'N/A'
    return ('-' if x < 0 else '') + '$' + format(abs(x), ',.0f')


def money2(x):
    if x is None:
        return 'N/A'
    return ('-' if x < 0 else '') + '$' + format(abs(x), ',.2f')


def pctf(x, d=1):
    return 'N/A' if x is None else format(x * 100, '.%df' % d) + '%'


class Ctx(object):
    pass


class Analytics(object):
    def __init__(self, model):
        self.m = model
        self.pl = model.pl
        self.bs = model.bs
        self.gl = model.gl
        self._recon = None
        self._gl_cache = collections.OrderedDict()
        self._build_pl_series()
        self._build_bs_series()
        self.account_options = self._account_options()

    # ---------------- series -------------------------------------------------
    def _build_pl_series(self):
        pl = self.pl
        self.pl_idx = {}
        self.pls = None
        if not pl:
            return
        n = len(pl.months)
        self.pl_idx = {ym: i for i, ym in enumerate(pl.months)}
        S = {k: [0.0] * n for k in ('income', 'cogs', 'opex', 'othinc', 'othexp', 'da', 'interest', 'int_inc', 'tax')}
        for lf in pl.leaves:
            sec, lab = lf['section'], lf['label']
            for i, v in enumerate(lf['vals']):
                S[sec][i] += v
                if sec in ('opex', 'cogs', 'othexp'):
                    if re.search(r'depreciat|amortiz', lab, re.I):
                        S['da'][i] += v
                    if re.search(r'interest', lab, re.I) and not re.search(r'income|earned|receiv', lab, re.I):
                        S['interest'][i] += v
                    if re.search(r'income tax|provision for (income )?tax|corporate tax|franchise tax|federal tax|state tax', lab, re.I):
                        S['tax'][i] += v
                if sec == 'othinc' and re.search(r'interest', lab, re.I):
                    S['int_inc'][i] += v
        self.pls = S

    def _build_bs_series(self):
        bs = self.bs
        self.bs_idx = {}
        self.bss = None
        if not bs:
            return
        n = len(bs.months)
        self.bs_idx = {ym: i for i, ym in enumerate(bs.months)}
        keys = ('asset', 'liab', 'equity', 'cash', 'cur_assets', 'cur_liab', 'receivables', 'ar_trade', 'payables',
                'inventory', 'lt_liab', 'fixed', 'bs_ni')
        S = {k: [0.0] * n for k in keys}
        flags = {'cur_assets': False, 'cur_liab': False, 'cash': False, 'receivables': False, 'payables': False,
                 'inventory': False, 'bs_ni': False, 'lt_liab': False}
        for lf in bs.leaves:
            cls, lab = lf['cls'], lf['label']
            pn = [norm(p) for p in lf['path']]
            is_cur_a = cls == 'asset' and any('current assets' in p for p in pn)
            is_cash = cls == 'asset' and (any(re.search(r'\bbank\b|\bcash\b', p) for p in pn) or
                                          re.search(r'^(cash|petty cash|checking|savings)\b', lab, re.I) is not None)
            is_ar = cls == 'asset' and (any(re.search(r'accounts receivable|\ba/r\b', p) for p in pn) or
                                        re.search(r'accounts receivable|\(a/r\)', lab, re.I) is not None)
            is_recv = is_cur_a and re.search(r'receivable', lab, re.I) is not None
            is_ap = cls == 'liab' and (any(re.search(r'accounts payable|\ba/p\b', p) for p in pn) or
                                       re.search(r'accounts payable|\(a/p\)', lab, re.I) is not None)
            is_cur_l = cls == 'liab' and any('current liabilities' in p for p in pn)
            is_lt = cls == 'liab' and any(re.search(r'long.?term', p) for p in pn)
            is_inv = cls == 'asset' and re.search(r'inventory', lab + ' ' + ' '.join(pn), re.I) is not None
            is_fixed = cls == 'asset' and any('fixed assets' in p for p in pn)
            is_ni = cls == 'equity' and re.match(r'^(net income|net profit|current year earnings|profit for the year)', lab, re.I) is not None
            for i, v in enumerate(lf['vals']):
                S[cls if cls != 'liab' else 'liab'][i] += v
                if is_cur_a: S['cur_assets'][i] += v
                if is_cash: S['cash'][i] += v
                if is_ar: S['ar_trade'][i] += v
                if is_ar or is_recv: S['receivables'][i] += v
                if is_ap: S['payables'][i] += v
                if is_cur_l: S['cur_liab'][i] += v
                if is_lt: S['lt_liab'][i] += v
                if is_inv: S['inventory'][i] += v
                if is_fixed: S['fixed'][i] += v
                if is_ni: S['bs_ni'][i] += v
            flags['cur_assets'] |= is_cur_a
            flags['cash'] |= is_cash
            flags['receivables'] |= (is_ar or is_recv)
            flags['payables'] |= is_ap
            flags['cur_liab'] |= is_cur_l
            flags['lt_liab'] |= is_lt
            flags['inventory'] |= is_inv
            flags['bs_ni'] |= is_ni
        self.bss = S
        self.bsflags = flags

    def _account_options(self):
        opts = []
        seen = set()
        for st in (self.pl, self.bs):
            if not st:
                continue
            for nd in st.nodes:
                if nd['kind'] == 'group' and len(nd['path']) > 1:
                    v = 'grp:' + ' > '.join(nd['path'])
                    opts.append({'v': v, 'l': 'Group: ' + ' > '.join(nd['path'][1:] if len(nd['path']) > 2 else nd['path'])})
        names = []
        for st in (self.pl, self.bs):
            if st:
                for lf in st.leaves:
                    names.append(lf['gl_name'])
        if self.gl:
            names.extend(self.gl.accounts.keys())
        for nme in names:
            if nme not in seen:
                seen.add(nme)
                opts.append({'v': 'acct:' + nme, 'l': nme})
        return opts

    def resolve_accounts(self, token):
        """Return a set of GL/P&L/BS account names, or None for 'no filter'."""
        if not token:
            return None
        if token.startswith('acct:'):
            return {token[5:]}
        if token.startswith('grp:'):
            path = tuple(x.strip() for x in token[4:].split(' > '))
            out = set()
            for st in (self.pl, self.bs):
                if st and path in st.node_by_path:
                    out |= {lf['gl_name'] for lf in st.node_by_path[path]['leaves']}
            return out or set()
        t = token.lower()
        out = set()
        names = set()
        for st in (self.pl, self.bs):
            if st:
                names |= {lf['gl_name'] for lf in st.leaves}
        if self.gl:
            names |= set(self.gl.accounts.keys())
        for n_ in names:
            if t in n_.lower():
                out.add(n_)
        return out

    # ---------------- period resolution --------------------------------------
    def ctx(self, q):
        months = self.m.months
        c = Ctx()
        pt = q.get('ptype', 'all')
        pv = q.get('pval', '')
        if pt == 'month':
            sel = [pv] if pv in months else [months[-1]]
        elif pt == 'quarter':
            sel = [x for x in months if ym_quarter(x) == pv]
        elif pt == 'year':
            sel = [x for x in months if x[:4] == pv]
        elif pt == 'ytd':
            end = pv if pv in months else months[-1]
            sel = [x for x in months if x[:4] == end[:4] and x <= end]
        elif pt == 'custom':
            a = q.get('from') or months[0]
            b = q.get('to') or months[-1]
            if a > b:
                a, b = b, a
            sel = [x for x in months if a <= x <= b]
        else:
            pt = 'all'
            sel = list(months)
        if not sel:
            sel = list(months)
            pt = 'all'
        c.ptype, c.sel, c.start, c.end = pt, sel, sel[0], sel[-1]
        c.pl_sel = [x for x in sel if x in self.pl_idx]
        c.bs_sel = [x for x in sel if x in self.bs_idx]
        c.bs_end = c.bs_sel[-1] if c.bs_sel else None
        c.label = ym_label(sel[0]) if len(sel) == 1 else '%s \u2013 %s' % (ym_label(sel[0]), ym_label(sel[-1]))
        mode = q.get('cmp', 'prev')
        L = len(sel)
        k = {'prev': L, 'mom': 1, 'qoq': 3, 'yoy': 12}.get(mode)
        c.mode = mode if k else 'none'
        c.cmp = None
        c.cmp_label = ''
        c.ok_pl = c.ok_bs = False
        c.reason = ''
        c.bs_cmp = None
        if k:
            cm = [ym_add(x, -k) for x in sel]
            c.cmp = cm
            c.cmp_label = ym_label(cm[0]) if len(cm) == 1 else '%s \u2013 %s' % (ym_label(cm[0]), ym_label(cm[-1]))
            mname = {'prev': 'Prior period', 'mom': 'MoM', 'qoq': 'QoQ', 'yoy': 'YoY'}[mode]
            c.cmp_name = mname
            reasons = []
            if self.pl:
                c.ok_pl = all(x in self.pl_idx for x in sel) and all(x in self.pl_idx for x in cm)
                if not c.ok_pl:
                    if not all(x in self.pl_idx for x in sel):
                        reasons.append("selected period is outside the P&L range")
                    else:
                        reasons.append("%s needs %s which is not in the P&L (data %s \u2013 %s)" % (
                            mname, c.cmp_label, ym_label(self.pl.months[0]), ym_label(self.pl.months[-1])))
            if self.bs and c.bs_end:
                c.bs_cmp = ym_add(c.bs_end, -k)
                c.ok_bs = c.bs_cmp in self.bs_idx
                if not c.ok_bs and not reasons:
                    reasons.append("%s needs balance sheet at %s which is not available" % (mname, ym_label(c.bs_cmp)))
            c.reason = '; '.join(reasons)
        else:
            c.cmp_name = 'None'
        c.acct = self.resolve_accounts(q.get('acct', ''))
        c.acct_token = q.get('acct', '')
        try:
            c.mat_abs = float(q.get('mat_abs', 1000))
        except ValueError:
            c.mat_abs = 1000.0
        try:
            c.mat_pct = float(q.get('mat_pct', 10)) / 100.0
        except ValueError:
            c.mat_pct = 0.10
        return c

    def period_info(self, c):
        m = self.m
        return {
            'label': c.label, 'start': c.start, 'end': c.end, 'months': c.sel, 'ptype': c.ptype,
            'cmp': {'mode': c.mode, 'name': c.cmp_name, 'label': c.cmp_label, 'ok_pl': c.ok_pl, 'ok_bs': c.ok_bs,
                    'reason': c.reason, 'months': c.cmp or []},
            'pl_partial': bool(self.pl and len(c.pl_sel) != len(c.sel)),
            'bs_end': c.bs_end, 'acct': c.acct_token,
        }

    # ---------------- metrics -------------------------------------------------
    def pl_m(self, months):
        if not self.pl:
            return None
        idx = [self.pl_idx[x] for x in months if x in self.pl_idx]
        if not idx:
            return None
        S = self.pls
        s = lambda k: sum(S[k][i] for i in idx)
        rev, cogs, opex, oi, oe = s('income'), s('cogs'), s('opex'), s('othinc'), s('othexp')
        gp = rev - cogs
        op = gp - opex
        ni = op + oi - oe
        ebitda = ni + s('interest') - s('int_inc') + s('tax') + s('da')
        return {'revenue': rev, 'cogs': cogs, 'gross_profit': gp, 'opex': opex, 'operating_income': op,
                'other_income': oi, 'other_expense': oe, 'net_income': ni, 'ebitda': ebitda,
                'total_expenses': cogs + opex + oe, 'da': s('da'), 'interest': s('interest'), 'tax': s('tax'),
                'gm': sdiv(gp, rev), 'om': sdiv(op, rev), 'em': sdiv(ebitda, rev), 'nm': sdiv(ni, rev),
                'opex_ratio': sdiv(opex + cogs, rev), 'n': len(idx)}

    def bs_m(self, ym):
        if not self.bs or ym is None or ym not in self.bs_idx:
            return None
        i = self.bs_idx[ym]
        S, F = self.bss, self.bsflags
        g = lambda k: S[k][i]
        ca = g('cur_assets') if F['cur_assets'] else None
        cl = g('cur_liab') if F['cur_liab'] else None
        cash = g('cash') if F['cash'] else None
        recv = g('receivables') if F['receivables'] else None
        out = {'assets': g('asset'), 'liabilities': g('liab'), 'equity': g('equity'), 'cash': cash,
               'current_assets': ca, 'current_liabilities': cl,
               'working_capital': (ca - cl) if (ca is not None and cl is not None) else None,
               'current_ratio': sdiv(ca, cl) if (ca is not None and cl is not None) else None,
               'receivables': recv, 'payables': g('payables') if F['payables'] else None,
               'inventory': g('inventory') if F['inventory'] else None,
               'lt_liab': g('lt_liab') if F['lt_liab'] else None, 'fixed': g('fixed')}
        if cl and cl != 0 and ca is not None:
            quick_assets = (cash or 0) + (recv or 0)
            out['quick_ratio'] = quick_assets / cl if (cash is not None or recv is not None) else None
            out['cash_ratio'] = (cash / cl) if cash is not None else None
        else:
            out['quick_ratio'] = out['cash_ratio'] = None
        return out

    def ratios_for(self, months, end_bs, open_bs):
        """All ratios for a period. months: P&L months; end_bs/open_bs: month-end BS months."""
        p = self.pl_m(months) if months else None
        b = self.bs_m(end_bs)
        bo = self.bs_m(open_bs) if open_bs else None
        R = {}
        n = p['n'] if p else 0
        ann = (12.0 / n) if n else None
        if p:
            R['gm'], R['om'], R['em'], R['nm'], R['opex_ratio'] = p['gm'], p['om'], p['em'], p['nm'], p['opex_ratio']
        if b:
            for k in ('current_ratio', 'quick_ratio', 'cash_ratio', 'working_capital'):
                R[k] = b[k]
            R['de'] = sdiv(b['liabilities'], b['equity']) if b['equity'] and b['equity'] > 0 else None
            R['debt_ratio'] = sdiv(b['liabilities'], b['assets'])
            R['equity_ratio'] = sdiv(b['equity'], b['assets'])
            R['eq_mult'] = sdiv(b['assets'], b['equity']) if b['equity'] and b['equity'] > 0 else None
            R['lt_de'] = sdiv(b['lt_liab'], b['equity']) if (b['lt_liab'] is not None and b['equity'] and b['equity'] > 0) else None
        if p and b:
            def avg(key):
                if b.get(key) is None:
                    return None
                if bo and bo.get(key) is not None:
                    return (b[key] + bo[key]) / 2.0
                return b[key]
            a_assets, a_eq, a_rec = avg('assets'), avg('equity'), avg('receivables')
            R['roa'] = sdiv(p['net_income'] * ann, a_assets) if (ann and a_assets and a_assets > 0) else None
            R['roe'] = sdiv(p['net_income'] * ann, a_eq) if (ann and a_eq and a_eq > 0) else None
            R['asset_turn'] = sdiv(p['revenue'] * ann, a_assets) if (ann and a_assets and a_assets > 0) else None
            if a_rec and a_rec > 0 and p['revenue'] > 0:
                R['ar_turn'] = p['revenue'] * ann / a_rec
                R['dso'] = 365.0 / R['ar_turn']
            else:
                R['ar_turn'] = R['dso'] = None
            a_ap = avg('payables')
            cost = p['cogs'] + p['opex']
            if a_ap and a_ap > 0 and cost > 0:
                R['ap_turn'] = cost * ann / a_ap
                R['dpo'] = 365.0 / R['ap_turn']
            else:
                R['ap_turn'] = R['dpo'] = None
            a_inv = avg('inventory')
            if a_inv and a_inv > 0 and p['cogs'] > 0:
                R['inv_turn'] = p['cogs'] * ann / a_inv
            else:
                R['inv_turn'] = None
            # cash coverage (months of operating cost covered by cash)
            mo_cost = (p['cogs'] + p['opex']) / n if n else None
            R['cash_months'] = sdiv(b['cash'], mo_cost) if (b['cash'] is not None and mo_cost and mo_cost > 0) else None
        return R

    # ---------------- overview -----------------------------------------------
    def _spark_months(self, c):
        months = [x for x in self.m.months if x <= c.end][-12:]
        return months

    def overview(self, c):
        cur = self.pl_m(c.pl_sel) if c.pl_sel else None
        prev = self.pl_m(c.cmp) if (c.ok_pl and c.cmp) else None
        bcur = self.bs_m(c.bs_end)
        bprev = self.bs_m(c.bs_cmp) if (c.ok_bs and c.bs_cmp) else None
        sm = self._spark_months(c)

        def pl_spark(key):
            out = []
            for x in sm:
                mm = self.pl_m([x])
                out.append(mm[key] if mm else None)
            return out

        def bs_spark(key):
            out = []
            for x in sm:
                mm = self.bs_m(x)
                out.append(mm[key] if mm else None)
            return out

        kp = []

        def add(key, label, fmt, cv, pv, better, spark, note='', pp=False):
            d = delta(cv, pv)
            if pp and cv is not None and pv is not None:
                d = {'abs': cv - pv, 'pct': None, 'note': 'pp'}
            kp.append({'key': key, 'label': label, 'fmt': fmt, 'value': cv, 'prev': pv, 'abs': d['abs'], 'pct': d['pct'],
                       'dnote': d['note'], 'fav': favorable(d['abs'], better), 'spark': spark, 'note': note})
        g = lambda dct, k: (dct[k] if dct else None)
        add('revenue', 'Revenue', 'money', g(cur, 'revenue'), g(prev, 'revenue'), 'up', pl_spark('revenue') if self.pl else [])
        add('gross_profit', 'Gross Profit', 'money', g(cur, 'gross_profit'), g(prev, 'gross_profit'), 'up', pl_spark('gross_profit') if self.pl else [])
        add('ebitda', 'EBITDA', 'money', g(cur, 'ebitda'), g(prev, 'ebitda'), 'up', pl_spark('ebitda') if self.pl else [],
            'Net income + interest + taxes + depreciation & amortization')
        add('net_income', 'Net Profit', 'money', g(cur, 'net_income'), g(prev, 'net_income'), 'up', pl_spark('net_income') if self.pl else [])
        add('gm', 'Gross Margin', 'pct', g(cur, 'gm'), g(prev, 'gm'), 'up', pl_spark('gm') if self.pl else [], pp=True)
        add('em', 'EBITDA Margin', 'pct', g(cur, 'em'), g(prev, 'em'), 'up', pl_spark('em') if self.pl else [], pp=True)
        add('nm', 'Net Margin', 'pct', g(cur, 'nm'), g(prev, 'nm'), 'up', pl_spark('nm') if self.pl else [], pp=True)
        add('total_expenses', 'Total Expenses', 'money', g(cur, 'total_expenses'), g(prev, 'total_expenses'), 'down',
            pl_spark('total_expenses') if self.pl else [], 'COGS + operating expenses + other expenses')
        add('assets', 'Total Assets', 'money', g(bcur, 'assets'), g(bprev, 'assets'), 'up', bs_spark('assets') if self.bs else [])
        add('liabilities', 'Total Liabilities', 'money', g(bcur, 'liabilities'), g(bprev, 'liabilities'), 'down',
            bs_spark('liabilities') if self.bs else [])
        add('equity', "Owners' Equity", 'money', g(bcur, 'equity'), g(bprev, 'equity'), 'up', bs_spark('equity') if self.bs else [])
        add('working_capital', 'Working Capital', 'money', g(bcur, 'working_capital'), g(bprev, 'working_capital'), 'up',
            bs_spark('working_capital') if self.bs else [], 'Current assets - current liabilities')
        add('current_ratio', 'Current Ratio', 'ratio', g(bcur, 'current_ratio'), g(bprev, 'current_ratio'), 'up',
            bs_spark('current_ratio') if self.bs else [])
        add('cash', 'Cash & Bank', 'money', g(bcur, 'cash'), g(bprev, 'cash'), 'up', bs_spark('cash') if self.bs else [])
        # trends over every analysis month
        tr = {'months': self.m.months}
        for key in ('revenue', 'cogs', 'gross_profit', 'opex', 'ebitda', 'net_income', 'gm', 'em', 'nm', 'total_expenses'):
            tr[key] = []
        for x in self.m.months:
            mm = self.pl_m([x])
            for key in ('revenue', 'cogs', 'gross_profit', 'opex', 'ebitda', 'net_income', 'gm', 'em', 'nm', 'total_expenses'):
                tr[key].append(mm[key] if mm else None)
        for key in ('assets', 'liabilities', 'equity', 'cash', 'working_capital', 'current_ratio'):
            tr[key] = []
        for x in self.m.months:
            mm = self.bs_m(x)
            for key in ('assets', 'liabilities', 'equity', 'cash', 'working_capital', 'current_ratio'):
                tr[key].append(mm[key] if mm else None)
        out = {'period': self.period_info(c), 'kpis': kp, 'trend': tr,
               'expense_mix': self.expense_mix(c), 'sel_months': c.sel}
        top = self.insights(c)
        out['top_insights'] = top[:4]
        return out

    def expense_mix(self, c):
        if not self.pl or not c.pl_sel:
            return []
        idx = [self.pl_idx[x] for x in c.pl_sel]
        pidx = [self.pl_idx[x] for x in c.cmp] if (c.ok_pl and c.cmp) else None
        rows = []
        for nd in self.pl.nodes:
            if nd['level'] != 1:
                continue
            sec = nd['leaves'][0]['section'] if nd['leaves'] else None
            if sec not in ('opex', 'cogs', 'othexp'):
                continue
            v = sum(lf['vals'][i] for lf in nd['leaves'] for i in idx)
            pv = sum(lf['vals'][i] for lf in nd['leaves'] for i in pidx) if pidx else None
            if abs(v) < 0.005 and not pv:
                continue
            rows.append({'name': nd['name'], 'value': v, 'prev': pv, 'sec': sec, 'is_group': nd['kind'] == 'group',
                         'drill': ('grp:' + ' > '.join(nd['path'])) if nd['kind'] == 'group' else 'acct:' + nd['leaf']['gl_name'],
                         'children': sorted(({'name': lf['display'], 'value': sum(lf['vals'][i] for i in idx)} for lf in nd['leaves']),
                                            key=lambda r: -abs(r['value']))[:12] if nd['kind'] == 'group' else []})
        rows.sort(key=lambda r: -abs(r['value']))
        return rows

    # ---------------- P&L ----------------------------------------------------
    def pl_table(self, c):
        if not self.pl:
            return {'available': False}
        pl = self.pl
        cols = c.pl_sel
        idx = [self.pl_idx[x] for x in cols]
        pidx = [self.pl_idx[x] for x in c.cmp] if (c.ok_pl and c.cmp) else None
        accset = c.acct
        S = self.pls
        rows = []
        cur_m = self.pl_m(cols)
        rev = cur_m['revenue'] if cur_m else None

        def mkrow(rid, label, level, kind, sec, vals, pvals, gl, better, drill=None, extra=None):
            tot = sum(vals)
            ptot = sum(pvals) if pvals is not None else None
            d = delta(tot, ptot)
            r = {'id': rid, 'label': label, 'level': level, 'kind': kind, 'sec': sec, 'vals': vals, 'total': tot,
                 'prev': ptot, 'abs': d['abs'], 'pct': d['pct'], 'dnote': d['note'],
                 'fav': favorable(d['abs'], better), 'pct_rev': sdiv(tot, rev), 'drill': drill, 'gl': gl}
            if extra:
                r.update(extra)
            return r

        def node_rows(top_name, sec):
            out = []
            for nd in pl.nodes:
                if nd['path'][0] != top_name:
                    continue
                leaves = nd['leaves']
                if accset is not None:
                    leaves = [lf for lf in leaves if lf['gl_name'] in accset]
                    if not leaves:
                        continue
                vals = [sum(lf['vals'][i] for lf in leaves) for i in idx]
                pv = [sum(lf['vals'][i] for lf in leaves) for i in pidx] if pidx else None
                if nd['level'] == 0:
                    kind = 'section'
                    label = nd['name']
                elif nd['kind'] == 'group':
                    kind, label = 'group', nd['name']
                else:
                    kind, label = 'leaf', nd['name']
                if kind != 'section' and all(abs(v) < 0.005 for v in vals) and (pv is None or all(abs(v) < 0.005 for v in pv)):
                    continue
                if kind == 'group':
                    drill = 'grp:' + ' > '.join(nd['path'])
                else:
                    drill = 'acct:' + (nd['leaf']['gl_name'] if nd['leaf'] else nd['name'])
                out.append(mkrow('p|' + '|'.join(nd['path']), label, nd['level'], kind, sec, vals, pv,
                                 sorted({lf['gl_name'] for lf in leaves}), SEC_BETTER.get(sec), drill,
                                 {'parent': ('p|' + '|'.join(nd['parent'])) if nd['parent'] else None}))
            return out
        tops = collections.OrderedDict()
        for nd in pl.nodes:
            if nd['level'] == 0:
                sec = pl_section(nd['name']) or 'opex'
                tops[nd['name']] = sec
        order = ['income', 'cogs', 'opex', 'othinc', 'othexp']

        def calc_row(rid, label, key_fn):
            vals = [key_fn(i) for i in idx]
            pv = [key_fn(i) for i in pidx] if pidx else None
            return mkrow(rid, label, 0, 'calc', None, vals, pv, [], 'up')
        gp = lambda i: S['income'][i] - S['cogs'][i]
        op = lambda i: gp(i) - S['opex'][i]
        ni = lambda i: op(i) + S['othinc'][i] - S['othexp'][i]
        ebitda = lambda i: ni(i) + S['interest'][i] - S['int_inc'][i] + S['tax'][i] + S['da'][i]
        for sec in order:
            for top, s_ in tops.items():
                if s_ == sec:
                    rows.extend(node_rows(top, sec))
            if accset is None:
                has_cogs = any(s_ == 'cogs' for s_ in tops.values())
                if (sec == 'cogs' and has_cogs) or (sec == 'income' and not has_cogs):
                    rows.append(calc_row('c|gp', 'Gross Profit', gp))
                if sec == 'opex':
                    rows.append(calc_row('c|op', 'Operating Income', op))
        if accset is None:
            rows.append(calc_row('c|ni', 'Net Income', ni))
            e = calc_row('c|ebitda', 'EBITDA (memo)', ebitda)
            e['kind'] = 'memo'
            rows.append(e)
        return {'available': True, 'months': cols, 'month_labels': [ym_label(x) for x in cols], 'rows': rows,
                'cmp_ok': bool(pidx), 'revenue': rev, 'filtered': accset is not None}

    # ---------------- Balance sheet -----------------------------------------
    def bs_table(self, c):
        if not self.bs:
            return {'available': False}
        bs = self.bs
        cols = c.bs_sel
        if not cols:
            return {'available': True, 'empty': True, 'months': []}
        idx = [self.bs_idx[x] for x in cols]
        prev_idx = self.bs_idx.get(ym_add(cols[0], -1))
        end_i = self.bs_idx[c.bs_end]
        cmp_i = self.bs_idx[c.bs_cmp] if (c.ok_bs and c.bs_cmp) else None
        accset = c.acct
        rows = []
        for nd in bs.nodes:
            leaves = nd['leaves']
            if accset is not None:
                leaves = [lf for lf in leaves if lf['gl_name'] in accset]
                if not leaves:
                    continue
            bal = [sum(lf['vals'][i] for lf in leaves) for i in idx]
            allz = all(abs(v) < 0.005 for v in bal)
            cur = sum(lf['vals'][end_i] for lf in leaves)
            prv = sum(lf['vals'][cmp_i] for lf in leaves) if cmp_i is not None else None
            if allz and nd['level'] > 0 and (prv is None or abs(prv) < 0.005):
                continue
            mov = []
            for k, i in enumerate(idx):
                pi = idx[k - 1] if k > 0 else prev_idx
                mov.append((sum(lf['vals'][i] for lf in leaves) - sum(lf['vals'][pi] for lf in leaves)) if pi is not None else None)
            cls = leaves[0]['cls']
            d = delta(cur, prv)
            better = {'asset': 'up', 'equity': 'up', 'liab': 'down'}.get(cls)
            kind = 'section' if nd['level'] == 0 else ('group' if nd['kind'] == 'group' else 'leaf')
            drill = ('grp:' + ' > '.join(nd['path'])) if nd['kind'] == 'group' else 'acct:' + (nd['leaf']['gl_name'])
            rows.append({'id': 'b|' + '|'.join(nd['path']), 'parent': ('b|' + '|'.join(nd['parent'])) if nd['parent'] else None,
                         'label': nd['name'], 'level': nd['level'], 'kind': kind, 'cls': cls, 'bal': bal, 'mov': mov,
                         'cur': cur, 'prev': prv, 'abs': d['abs'], 'pct': d['pct'], 'dnote': d['note'],
                         'fav': favorable(d['abs'], better), 'drill': drill})
        # accounting equation by month (all BS months)
        eq = []
        S = self.bss
        for i, ym in enumerate(bs.months):
            a, l, e = S['asset'][i], S['liab'][i], S['equity'][i]
            eq.append({'month': ym, 'label': ym_label(ym), 'assets': a, 'liabilities': l, 'equity': e, 'le': l + e,
                       'diff': a - l - e, 'ok': abs(a - l - e) <= 0.01})
        mv = {'months': bs.months, 'assets': S['asset'], 'liabilities': S['liab'], 'equity': S['equity'],
              'cash': S['cash'] if self.bsflags['cash'] else None,
              'working_capital': [(S['cur_assets'][i] - S['cur_liab'][i]) if (self.bsflags['cur_assets'] and self.bsflags['cur_liab']) else None
                                  for i in range(len(bs.months))],
              'receivables': S['receivables'] if self.bsflags['receivables'] else None}
        return {'available': True, 'months': cols, 'month_labels': [ym_label(x) for x in cols], 'rows': rows,
                'equation': eq, 'trend': mv, 'end': c.bs_end, 'cmp_end': c.bs_cmp if cmp_i is not None else None,
                'cmp_ok': cmp_i is not None, 'filtered': accset is not None}

    # ---------------- Variance & growth ------------------------------------
    def variance(self, c):
        if not self.pl:
            return {'available': False, 'reason': 'No P&L loaded'}
        if not (c.cmp and c.ok_pl):
            return {'available': True, 'comparable': False, 'reason': c.reason or 'Select a comparison period (MoM / QoQ / YoY / Prior period).',
                    'period': self.period_info(c)}
        pl = self.pl
        idx = [self.pl_idx[x] for x in c.sel]
        pidx = [self.pl_idx[x] for x in c.cmp]
        accset = c.acct
        rows, leaves_out = [], []
        for nd in pl.nodes:
            if nd['level'] == 0:
                continue
            leaves = nd['leaves']
            if accset is not None:
                leaves = [lf for lf in leaves if lf['gl_name'] in accset]
                if not leaves:
                    continue
            sec = leaves[0]['section']
            cv = sum(lf['vals'][i] for lf in leaves for i in idx)
            pv = sum(lf['vals'][i] for lf in leaves for i in pidx)
            if abs(cv) < 0.005 and abs(pv) < 0.005:
                continue
            d = delta(cv, pv)
            better = SEC_BETTER.get(sec)
            impact = d['abs'] if better == 'up' else -d['abs']
            material = abs(d['abs']) >= c.mat_abs and (d['pct'] is None or abs(d['pct']) >= c.mat_pct)
            r = {'label': nd['name'], 'path': ' > '.join(nd['path'][:-1]), 'level': nd['level'], 'kind': nd['kind'], 'sec': sec,
                 'sec_label': SEC_LABEL.get(sec, sec), 'cur': cv, 'prev': pv, 'abs': d['abs'], 'pct': d['pct'], 'dnote': d['note'],
                 'impact': impact, 'fav': favorable(d['abs'], better), 'material': material,
                 'drill': ('grp:' + ' > '.join(nd['path'])) if nd['kind'] == 'group' else 'acct:' + nd['leaf']['gl_name']}
            rows.append(r)
            if nd['kind'] == 'leaf':
                leaves_out.append(r)
        pos = sorted([r for r in leaves_out if r['impact'] > 0.005], key=lambda r: -r['impact'])[:8]
        neg = sorted([r for r in leaves_out if r['impact'] < -0.005], key=lambda r: r['impact'])[:8]
        # waterfall (net income bridge)
        cur_m, prev_m = self.pl_m(c.sel), self.pl_m(c.cmp)
        steps = [{'label': 'Revenue', 'value': cur_m['revenue'] - prev_m['revenue']}]
        if cur_m['cogs'] or prev_m['cogs']:
            steps.append({'label': 'Cost of goods sold', 'value': -(cur_m['cogs'] - prev_m['cogs'])})
        exp = []
        for nd in pl.nodes:
            if nd['level'] == 1 and nd['leaves'] and nd['leaves'][0]['section'] == 'opex':
                dv = sum(lf['vals'][i] for lf in nd['leaves'] for i in idx) - sum(lf['vals'][i] for lf in nd['leaves'] for i in pidx)
                exp.append({'label': nd['name'], 'value': -dv})
        exp.sort(key=lambda r: -abs(r['value']))
        top, rest = exp[:7], exp[7:]
        steps.extend(top)
        if rest:
            steps.append({'label': 'Other operating expenses', 'value': sum(r['value'] for r in rest)})
        oth = (cur_m['other_income'] - prev_m['other_income']) - (cur_m['other_expense'] - prev_m['other_expense'])
        if abs(oth) > 0.005:
            steps.append({'label': 'Other income / (expense), net', 'value': oth})
        wf = {'start': prev_m['net_income'], 'end': cur_m['net_income'], 'steps': steps,
              'check': prev_m['net_income'] + sum(s['value'] for s in steps) - cur_m['net_income']}
        # summary table
        summ = []
        for key, label, better in (('revenue', 'Revenue', 'up'), ('cogs', 'Cost of goods sold', 'down'), ('gross_profit', 'Gross profit', 'up'),
                                   ('opex', 'Operating expenses', 'down'), ('operating_income', 'Operating income', 'up'),
                                   ('ebitda', 'EBITDA', 'up'), ('net_income', 'Net income', 'up')):
            d = delta(cur_m[key], prev_m[key])
            summ.append({'label': label, 'cur': cur_m[key], 'prev': prev_m[key], 'abs': d['abs'], 'pct': d['pct'],
                         'dnote': d['note'], 'fav': favorable(d['abs'], better)})
        # balance sheet movers
        bsm = []
        if self.bs and c.ok_bs and c.bs_end:
            ei, ci = self.bs_idx[c.bs_end], self.bs_idx[c.bs_cmp]
            for lf in self.bs.leaves:
                if accset is not None and lf['gl_name'] not in accset:
                    continue
                cv, pv = lf['vals'][ei], lf['vals'][ci]
                if abs(cv - pv) < 0.005:
                    continue
                d = delta(cv, pv)
                bsm.append({'label': lf['label'], 'cls': lf['cls'], 'cur': cv, 'prev': pv, 'abs': d['abs'], 'pct': d['pct'],
                            'dnote': d['note'], 'drill': 'acct:' + lf['gl_name']})
            bsm.sort(key=lambda r: -abs(r['abs']))
        return {'available': True, 'comparable': True, 'period': self.period_info(c), 'rows': rows, 'top_pos': pos, 'top_neg': neg,
                'waterfall': wf, 'summary': summ, 'bs_movers': bsm[:15],
                'mat_abs': c.mat_abs, 'mat_pct': c.mat_pct * 100.0}

    # ---------------- Ratios -------------------------------------------------
    RATIO_DEFS = [
        ('Profitability', 'gm', 'Gross margin', 'pct', 'up', 'Gross profit / Revenue'),
        ('Profitability', 'om', 'Operating margin', 'pct', 'up', 'Operating income / Revenue'),
        ('Profitability', 'em', 'EBITDA margin', 'pct', 'up', 'EBITDA / Revenue'),
        ('Profitability', 'nm', 'Net margin', 'pct', 'up', 'Net income / Revenue'),
        ('Profitability', 'opex_ratio', 'Cost-to-revenue ratio', 'pct', 'down', '(COGS + operating expenses) / Revenue'),
        ('Profitability', 'roa', 'Return on assets (annualized)', 'pct', 'up', 'Net income x 12/months / average total assets'),
        ('Profitability', 'roe', 'Return on equity (annualized)', 'pct', 'up', 'Net income x 12/months / average equity'),
        ('Liquidity', 'current_ratio', 'Current ratio', 'ratio', 'up', 'Current assets / Current liabilities'),
        ('Liquidity', 'quick_ratio', 'Quick ratio', 'ratio', 'up', '(Cash + receivables) / Current liabilities'),
        ('Liquidity', 'cash_ratio', 'Cash ratio', 'ratio', 'up', 'Cash / Current liabilities'),
        ('Liquidity', 'working_capital', 'Working capital', 'money', 'up', 'Current assets - Current liabilities'),
        ('Liquidity', 'cash_months', 'Cash runway (months of costs)', 'num1', 'up', 'Cash / average monthly (COGS + operating expenses)'),
        ('Leverage', 'de', 'Liabilities to equity', 'ratio', 'down', 'Total liabilities / Equity (N/A if equity <= 0)'),
        ('Leverage', 'debt_ratio', 'Liabilities to assets', 'pct', 'down', 'Total liabilities / Total assets'),
        ('Leverage', 'equity_ratio', 'Equity ratio', 'pct', 'up', 'Equity / Total assets'),
        ('Leverage', 'eq_mult', 'Equity multiplier', 'ratio', None, 'Total assets / Equity'),
        ('Leverage', 'lt_de', 'Long-term liabilities to equity', 'ratio', 'down', 'Long-term liabilities / Equity'),
        ('Efficiency', 'asset_turn', 'Asset turnover (annualized)', 'ratio', 'up', 'Revenue x 12/months / average total assets'),
        ('Efficiency', 'ar_turn', 'Receivables turnover', 'ratio', 'up', 'Revenue (annualized) / average receivables'),
        ('Efficiency', 'dso', 'Days sales outstanding', 'days', 'down', '365 / receivables turnover'),
        ('Efficiency', 'ap_turn', 'Payables turnover', 'ratio', None, 'Costs (annualized) / average accounts payable'),
        ('Efficiency', 'dpo', 'Days payables outstanding', 'days', None, '365 / payables turnover'),
        ('Efficiency', 'inv_turn', 'Inventory turnover', 'ratio', 'up', 'COGS (annualized) / average inventory'),
    ]
    NA_REASON = {
        'current_ratio': 'needs Current Assets and Current Liabilities groups in the balance sheet',
        'quick_ratio': 'needs current liabilities and cash / receivables accounts',
        'cash_ratio': 'needs a cash/bank group and current liabilities',
        'working_capital': 'needs Current Assets and Current Liabilities groups',
        'cash_months': 'needs cash and positive operating costs in the period',
        'roa': 'needs P&L and balance sheet for the period', 'roe': 'needs positive equity and P&L/BS for the period',
        'de': 'equity is zero or negative', 'eq_mult': 'equity is zero or negative', 'lt_de': 'no long-term liabilities group, or equity <= 0',
        'asset_turn': 'needs P&L and balance sheet for the period',
        'ar_turn': 'no receivables accounts, or no revenue', 'dso': 'no receivables accounts, or no revenue',
        'ap_turn': 'no Accounts Payable account in the balance sheet', 'dpo': 'no Accounts Payable account in the balance sheet',
        'inv_turn': 'no inventory or cost of goods sold', 'gm': 'no revenue in the period', 'om': 'no revenue in the period',
        'em': 'no revenue in the period', 'nm': 'no revenue in the period', 'opex_ratio': 'no revenue in the period',
    }

    def _interpret(self, key, v, p):
        if v is None:
            return ''
        if key == 'gm':
            return 'Keeps %s of each revenue dollar after direct costs.' % pctf(v)
        if key == 'nm':
            return ('Net loss: costs exceed revenue by %s of revenue.' % pctf(-v)) if v < 0 else 'Retains %s of revenue as net profit.' % pctf(v)
        if key == 'em':
            return 'Operating cash profitability before interest, tax and D&A: %s of revenue.' % pctf(v)
        if key == 'om':
            return 'Operating income is %s of revenue.' % pctf(v)
        if key == 'opex_ratio':
            return 'Total operating cost consumes %s of revenue.' % pctf(v)
        if key == 'current_ratio':
            return 'Short-term liquidity is stretched: current liabilities exceed current assets.' if v < 1 else (
                'Adequate short-term cover (above 1.0x).' if v < 2 else 'Strong short-term cover (2.0x or higher).')
        if key == 'quick_ratio':
            return 'Cash and receivables do not fully cover current liabilities.' if v < 1 else 'Liquid assets cover current liabilities.'
        if key == 'cash_ratio':
            return 'Cash alone covers %s of current liabilities.' % pctf(v, 0)
        if key == 'working_capital':
            return 'Negative working capital: short-term obligations exceed short-term assets.' if v < 0 else 'Positive working capital cushion.'
        if key == 'cash_months':
            return 'Cash covers about %.1f months of average operating costs.' % v
        if key == 'de':
            return 'Creditors fund %.2fx the owners\' stake.' % v
        if key == 'debt_ratio':
            return '%s of assets are financed by liabilities.' % pctf(v, 0)
        if key == 'equity_ratio':
            return '%s of assets are owner-financed.' % pctf(v, 0)
        if key == 'roa':
            return 'Annualized profit generated per dollar of assets.'
        if key == 'roe':
            return 'Annualized return on owners\' equity.'
        if key == 'dso':
            return 'Receivables take about %.0f days to convert to cash.' % v
        if key == 'asset_turn':
            return 'Each dollar of assets supports $%.2f of annualized revenue.' % v
        return ''

    def ratios(self, c):
        if not c.pl_sel and not c.bs_end:
            return {'available': False}
        open_bs = ym_add(c.bs_sel[0], -1) if c.bs_sel else None
        cur = self.ratios_for(c.pl_sel, c.bs_end, open_bs)
        prev = None
        if c.cmp and (c.ok_pl or c.ok_bs):
            k = {'prev': len(c.sel), 'mom': 1, 'qoq': 3, 'yoy': 12}[c.mode]
            pe = c.bs_cmp if c.ok_bs else None
            prev = self.ratios_for(c.cmp if c.ok_pl else [], pe, ym_add(pe, -len(c.bs_sel)) if (pe and c.bs_sel) else None)
        rows = []
        for grp, key, name, fmt, better, formula in self.RATIO_DEFS:
            v = cur.get(key)
            pv = prev.get(key) if prev else None
            d = delta(v, pv) if prev else {'abs': None, 'pct': None, 'note': 'na'}
            if fmt == 'pct' and v is not None and pv is not None:
                d = {'abs': v - pv, 'pct': None, 'note': 'pp'}
            rows.append({'group': grp, 'key': key, 'name': name, 'fmt': fmt, 'value': v, 'prev': pv, 'abs': d['abs'],
                         'pct': d['pct'], 'dnote': d['note'], 'fav': favorable(d['abs'], better), 'formula': formula,
                         'interp': self._interpret(key, v, cur) if v is not None else 'N/A \u2013 ' + self.NA_REASON.get(key, 'insufficient data')})
        # monthly trend
        keys = ['gm', 'em', 'nm', 'current_ratio', 'quick_ratio', 'de', 'roa', 'roe']
        tr = {'months': self.m.months}
        for k in keys:
            tr[k] = []
        for x in self.m.months:
            r = self.ratios_for([x] if x in self.pl_idx else [], x if x in self.bs_idx else None,
                                ym_add(x, -1) if ym_add(x, -1) in self.bs_idx else None)
            for k in keys:
                tr[k].append(r.get(k))
        return {'available': True, 'period': self.period_info(c), 'rows': rows, 'trend': tr}

    # ---------------- Insights ----------------------------------------------
    def insights(self, c):
        out = []
        sev_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}

        def add(sev, title, detail, module, key=None):
            out.append({'sev': sev, 'title': title, 'detail': detail, 'module': module, 'key': key or title})
        cur = self.pl_m(c.pl_sel) if c.pl_sel else None
        prev = self.pl_m(c.cmp) if (c.ok_pl and c.cmp) else None
        # data integrity
        rec = self.reconcile()
        for chk in rec['checks']:
            if chk['status'] == 'fail':
                add('high', 'Unreconciled: ' + chk['name'], chk['summary'], 'recon')
            elif chk['status'] == 'warn':
                add('medium', 'Check: ' + chk['name'], chk['summary'], 'recon')
        if cur:
            if cur['net_income'] < 0:
                add('high', 'Net loss for %s' % c.label,
                    'Net income is %s on revenue of %s (net margin %s).' % (money(cur['net_income']), money(cur['revenue']), pctf(cur['nm'])), 'pl')
            if prev:
                dr = delta(cur['revenue'], prev['revenue'])
                if dr['pct'] is not None and abs(dr['pct']) >= 0.15:
                    add('high' if dr['pct'] < 0 else 'info', 'Revenue %s %s vs %s' % ('fell' if dr['pct'] < 0 else 'grew', pctf(abs(dr['pct'])), c.cmp_name),
                        'Revenue moved from %s (%s) to %s (%s), a change of %s.' % (money(prev['revenue']), c.cmp_label, money(cur['revenue']), c.label, money(dr['abs'])), 'variance')
                for key, label in (('gm', 'Gross margin'), ('nm', 'Net margin'), ('em', 'EBITDA margin')):
                    if cur[key] is not None and prev[key] is not None and cur[key] - prev[key] <= -0.05:
                        add('medium', '%s declined %.1f pts' % (label, (prev[key] - cur[key]) * 100),
                            '%s fell from %s (%s) to %s (%s).' % (label, pctf(prev[key]), c.cmp_label, pctf(cur[key]), c.label), 'ratios')
                dn = delta(cur['net_income'], prev['net_income'])
                if dn['abs'] is not None and abs(dn['abs']) >= max(c.mat_abs, 0.05 * abs(prev['net_income'])) and dn['abs'] < 0:
                    add('medium', 'Net profit decreased by %s' % money(-dn['abs']),
                        'Net income moved from %s to %s versus %s.' % (money(prev['net_income']), money(cur['net_income']), c.cmp_name), 'variance')
                # biggest unfavorable account swings
                v = self.variance(c)
                if v.get('comparable'):
                    for r in v['top_neg'][:3]:
                        if r['material']:
                            add('medium', '%s: unfavorable change of %s' % (r['label'], money(-r['impact'])),
                                '%s moved from %s to %s (%s%s) vs %s.' % (r['label'], money(r['prev']), money(r['cur']), money(r['abs']),
                                                                         (', ' + pctf(r['pct'])) if r['pct'] is not None else '', c.cmp_name), 'variance')
        # revenue volatility across analysis months
        if self.pl and len(self.pl.months) >= 6:
            rv = self.pls['income']
            peak = max(rv) if rv else 0
            if peak > 0:
                low = [i for i, x in enumerate(rv) if x < 0.1 * peak]
                if len(low) >= 3 and len(low) / float(len(rv)) >= 0.25:
                    add('medium', 'Revenue is lumpy',
                        '%d of %d months have revenue below 10%% of the peak month (%s in %s). Monthly cash planning and monthly margin comparisons may be unreliable.' % (
                            len(low), len(rv), money(peak), ym_label(self.pl.months[rv.index(peak)])), 'pl')
        # expense spikes: account-month vs its own average
        if self.pl and c.pl_sel:
            n = len(self.pl.months)
            spikes = []
            for lf in self.pl.leaves:
                if lf['section'] not in ('opex', 'cogs', 'othexp') or n < 6:
                    continue
                vals = lf['vals']
                for ym in c.pl_sel:
                    i = self.pl_idx[ym]
                    others = [vals[j] for j in range(n) if j != i]
                    mu = sum(others) / len(others)
                    var = sum((x - mu) ** 2 for x in others) / len(others)
                    sd = math.sqrt(var)
                    if vals[i] - mu >= max(c.mat_abs * 2, 3 * sd) and vals[i] > 0 and mu > 0 and vals[i] >= 2.5 * mu:
                        spikes.append((vals[i] - mu, lf['label'], ym, vals[i], mu))
            spikes.sort(reverse=True)
            for dv, lab, ym, v, mu in spikes[:4]:
                add('medium', 'Unusual expense: %s in %s' % (lab, ym_label(ym)),
                    '%s was %s versus a typical month of %s (%.1fx the average of other months).' % (lab, money(v), money(mu), v / mu), 'pl')
            neg = [(lf['label'], sum(lf['vals'][self.pl_idx[x]] for x in c.pl_sel)) for lf in self.pl.leaves
                   if lf['section'] in ('opex', 'cogs') and sum(lf['vals'][self.pl_idx[x]] for x in c.pl_sel) < -c.mat_abs]
            for lab, v in sorted(neg, key=lambda t: t[1])[:3]:
                add('low', 'Negative expense balance: %s' % lab,
                    '%s totals %s in the selected period (credits exceed debits). Confirm this is a reclassification or reversal rather than a posting error.' % (lab, money(v)), 'pl')
            unc = [(lf['label'], sum(lf['vals'][self.pl_idx[x]] for x in c.pl_sel)) for lf in self.pl.leaves
                   if re.search(r'uncategori[sz]ed|ask my accountant|suspense', lf['label'], re.I)]
            for lab, v in unc:
                if abs(v) >= 0.5:
                    add('medium', 'Uncategorized balance: %s' % lab, '%s carries %s in the selected period; it should be classified before closing the books.' % (lab, money(v)), 'pl')
        # balance sheet signals
        b = self.bs_m(c.bs_end)
        bp = self.bs_m(c.bs_cmp) if (c.ok_bs and c.bs_cmp) else None
        if b:
            if b['working_capital'] is not None and b['working_capital'] < 0:
                add('high', 'Negative working capital at %s' % ym_label(c.bs_end),
                    'Current assets %s vs current liabilities %s (current ratio %s).' % (money(b['current_assets']), money(b['current_liabilities']), '%.2fx' % b['current_ratio'] if b['current_ratio'] is not None else 'N/A'), 'bs')
            if bp:
                if b['cash'] is not None and bp['cash'] not in (None, 0):
                    dc = delta(b['cash'], bp['cash'])
                    if dc['pct'] is not None and abs(dc['pct']) >= 0.25:
                        add('high' if dc['pct'] < 0 else 'info', 'Cash %s %s vs %s' % ('dropped' if dc['pct'] < 0 else 'rose', pctf(abs(dc['pct']), 0), c.cmp_name),
                            'Cash & bank moved from %s (%s) to %s (%s).' % (money(bp['cash']), ym_label(c.bs_cmp), money(b['cash']), ym_label(c.bs_end)), 'bs')
                if b['receivables'] is not None and bp['receivables'] not in (None, 0):
                    dr_ = delta(b['receivables'], bp['receivables'])
                    rg = delta(cur['revenue'], prev['revenue']) if (cur and prev) else {'pct': None}
                    if dr_['pct'] is not None and dr_['pct'] >= 0.25:
                        extra = ''
                        if rg['pct'] is not None and rg['pct'] < dr_['pct']:
                            extra = ' Revenue grew only %s over the same comparison.' % pctf(rg['pct'])
                        add('medium', 'Receivables grew %s vs %s' % (pctf(dr_['pct'], 0), c.cmp_name),
                            'Receivables moved from %s to %s.%s' % (money(bp['receivables']), money(b['receivables']), extra), 'bs')
                if b['liabilities'] is not None and bp['liabilities'] not in (None, 0):
                    dl = delta(b['liabilities'], bp['liabilities'])
                    if dl['pct'] is not None and dl['pct'] >= 0.25 and dl['abs'] >= c.mat_abs * 10:
                        add('medium', 'Liabilities up %s vs %s' % (pctf(dl['pct'], 0), c.cmp_name),
                            'Total liabilities rose from %s to %s.' % (money(bp['liabilities']), money(b['liabilities'])), 'bs')
            if b['equity'] is not None and b['equity'] < 0:
                add('high', 'Negative equity', 'Owners\' equity is %s at %s.' % (money(b['equity']), ym_label(c.bs_end)), 'bs')
            # abnormal-sign accounts at the end month
            ei = self.bs_idx[c.bs_end]
            flagged = []
            for lf in self.bs.leaves:
                v = lf['vals'][ei]
                if abs(v) < max(c.mat_abs, 1.0):
                    continue
                if re.search(r'accumulated|depreciation|allowance|contra|opening balance|distribution|draw|owner|pay & personal', lf['label'], re.I):
                    continue
                if (lf['cls'] == 'asset' and v < 0) or (lf['cls'] == 'liab' and v < 0):
                    flagged.append((abs(v), lf['label'], v, lf['cls']))
            flagged.sort(reverse=True)
            for _, lab, v, cl in flagged[:3]:
                add('low', 'Abnormal balance: %s' % lab,
                    '%s is a %s account but carries a %s balance of %s at %s. Check for misposted entries or a reclass to the opposite side.' % (
                        lab, 'liability' if cl == 'liab' else 'asset', 'debit' if cl == 'liab' else 'credit', money(abs(v)), ym_label(c.bs_end)), 'bs')
        # distributions vs profit (informational)
        if self.bs and c.ok_bs and cur:
            ei, ci = self.bs_idx[c.bs_end], self.bs_idx[c.bs_cmp]
            dist = [lf for lf in self.bs.leaves if re.search(r'distribution|draw', lf['label'], re.I) and lf['cls'] == 'equity']
            if dist:
                mov = sum(lf['vals'][ei] - lf['vals'][ci] for lf in dist)
                if mov < -c.mat_abs and cur['net_income'] is not None and -mov > max(cur['net_income'], 0):
                    add('info', 'Distributions exceed profit',
                        'Shareholder distributions/draws moved by %s over the period versus net income of %s.' % (money(mov), money(cur['net_income'])), 'bs')
        out.sort(key=lambda r: sev_order[r['sev']])
        return out

    # ---------------- Reconciliation ----------------------------------------
    def reconcile(self):
        if self._recon is not None:
            return self._recon
        checks = []
        TOL = 0.011

        def chk(name, status, summary, items=None, cols=None):
            checks.append({'name': name, 'status': status, 'summary': summary, 'items': items or [], 'cols': cols or []})

        pl, bs, gl = self.pl, self.bs, self.gl
        if pl:
            bad, mx, n = [], 0.0, 0
            for key, vals in pl.reported.items():
                nd = pl.node_by_path.get(key)
                if not nd:
                    continue
                n += 1
                s = [sum(lf['vals'][i] for lf in nd['leaves']) for i in range(len(pl.months))]
                d = max(abs(a - b) for a, b in zip(s, vals))
                mx = max(mx, d)
                if d > TOL:
                    bad.append({'item': ' > '.join(key), 'detail': 'max difference %s' % money2(d)})
            chk('P&L: account detail ties to reported subtotals', 'ok' if not bad else 'fail',
                '%d reported subtotals re-computed from account lines; %s.' % (n, 'all agree (no double counting of parents/subtotals)' if not bad else '%d differ (max %s)' % (len(bad), money2(mx))),
                bad[:15], ['item', 'detail'])
            rep_ni = pl.calcs.get('net income')
            if rep_ni:
                diffs = []
                for i, ym in enumerate(pl.months):
                    mm = self.pl_m([ym])
                    if abs(mm['net_income'] - rep_ni[i]) > TOL:
                        diffs.append({'item': ym_label(ym), 'detail': 'computed %s vs reported %s' % (money2(mm['net_income']), money2(rep_ni[i]))})
                chk('P&L: Net Income recomputed vs reported', 'ok' if not diffs else 'fail',
                    '%d months compared; %s.' % (len(pl.months), 'dashboard net income equals QuickBooks net income every month' if not diffs else '%d months differ' % len(diffs)),
                    diffs[:15], ['item', 'detail'])
            else:
                chk('P&L: Net Income recomputed vs reported', 'na', 'No "Net Income" line found in the P&L to compare with.')
            neg_rev = [ym_label(ym) for i, ym in enumerate(pl.months) if self.pls['income'][i] < 0]
            if neg_rev:
                chk('P&L: negative revenue months', 'warn', 'Revenue is negative in: ' + ', '.join(neg_rev[:6]))
        if bs:
            bad, mx, n = [], 0.0, 0
            for key, vals in bs.reported.items():
                nd = bs.node_by_path.get(key)
                if not nd:
                    continue
                n += 1
                s = [sum(lf['vals'][i] for lf in nd['leaves']) for i in range(len(bs.months))]
                d = max(abs(a - b) for a, b in zip(s, vals))
                mx = max(mx, d)
                if d > TOL:
                    bad.append({'item': ' > '.join(key), 'detail': 'max difference %s' % money2(d)})
            chk('Balance Sheet: account detail ties to reported subtotals', 'ok' if not bad else 'fail',
                '%d reported subtotals re-computed from account lines; %s.' % (n, 'all agree' if not bad else '%d differ (max %s)' % (len(bad), money2(mx))),
                bad[:15], ['item', 'detail'])
            S = self.bss
            eqbad = []
            for i, ym in enumerate(bs.months):
                d = S['asset'][i] - S['liab'][i] - S['equity'][i]
                if abs(d) > TOL:
                    eqbad.append({'item': ym_label(ym), 'detail': 'Assets - (Liabilities + Equity) = %s' % money2(d)})
            chk('Balance Sheet: Assets = Liabilities + Equity', 'ok' if not eqbad else 'fail',
                '%d month-end balance sheets tested; %s.' % (len(bs.months), 'accounting equation holds in every month' if not eqbad else '%d months out of balance' % len(eqbad)),
                eqbad[:15], ['item', 'detail'])
        if pl and bs and self.bsflags['bs_ni']:
            diffs, tested = [], 0
            cum = {}
            for i, ym in enumerate(pl.months):
                y = ym[:4]
                full_year_start = (y + '-01') in self.pl_idx
                mm = self.pl_m([ym])
                cum[y] = cum.get(y, 0.0) + mm['net_income']
                if ym in self.bs_idx and full_year_start:
                    tested += 1
                    bv = self.bss['bs_ni'][self.bs_idx[ym]]
                    if abs(bv - cum[y]) > TOL:
                        diffs.append({'item': ym_label(ym), 'detail': 'Balance sheet NI %s vs P&L year-to-date %s (diff %s)' % (money2(bv), money2(cum[y]), money2(bv - cum[y]))})
            if tested:
                chk('P&L vs Balance Sheet: current-year earnings', 'ok' if not diffs else 'fail',
                    '%d month-ends compared (P&L year-to-date net income vs equity "Net Income" line, calendar fiscal year); %s.' % (tested, 'agree' if not diffs else '%d differ' % len(diffs)),
                    diffs[:15], ['item', 'detail'])
        if gl and pl:
            diffs, tested, missing = [], 0, []
            lo, hi = gl.months[0], gl.months[-1]
            for lf in pl.leaves:
                nm_ = lf['gl_name']
                am = gl.acct_month.get(nm_)
                if nm_ not in gl.accounts:
                    if any(abs(v) > TOL for v in lf['vals']):
                        missing.append(nm_)
                    continue
                for i, ym in enumerate(pl.months):
                    if ym < lo or ym > hi:
                        continue
                    tested += 1
                    g = am.get(ym, 0.0) if am else 0.0
                    if abs(g - lf['vals'][i]) > TOL:
                        diffs.append({'item': '%s | %s' % (nm_, ym_label(ym)), 'detail': 'P&L %s vs GL %s (diff %s)' % (money2(lf['vals'][i]), money2(g), money2(lf['vals'][i] - g)), 'abs': abs(lf['vals'][i] - g)})
            diffs.sort(key=lambda r: -r['abs'])
            st = 'ok' if not diffs and not missing else ('fail' if diffs else 'warn')
            s = '%s account-months compared between P&L and GL; %s.' % (format(tested, ','), 'all agree' if not diffs else '%d differ' % len(diffs))
            if missing:
                s += ' %d P&L accounts with balances have no GL section: %s.' % (len(missing), ', '.join(missing[:5]))
            chk('General Ledger vs P&L (account x month)', st, s, diffs[:20], ['item', 'detail'])
        if gl and bs:
            diffs, tested, notf = [], 0, []
            lo, hi = gl.months[0], gl.months[-1]
            ni_by_year = {}
            if pl:
                for i_, ym_ in enumerate(pl.months):
                    ni_by_year[ym_[:4]] = ni_by_year.get(ym_[:4], 0.0) + self.pl_m([ym_])['net_income']
            full_years = set(y for y in ni_by_year if all(("%s-%02d" % (y, k)) in self.pl_idx for k in range(1, 13)))
            explained = []
            re_unver = set()
            for lf in bs.leaves:
                nm_ = lf['gl_name']
                info = gl.accounts.get(nm_)
                if re.match(r'^(net income|net profit|current year earnings)', nm_, re.I):
                    continue
                if info is None:
                    if any(abs(v) > TOL for v in lf['vals']):
                        notf.append(nm_)
                    continue
                is_re = re.search(r'retained earnings', nm_, re.I) is not None
                cum = info['begin']
                am = gl.acct_month.get(nm_, {})
                run = {}
                for ym in gl.months:
                    cum += am.get(ym, 0.0)
                    run[ym] = cum
                for i, ym in enumerate(bs.months):
                    if ym < lo or ym > hi:
                        continue
                    tested += 1
                    glv = run[ym]
                    if is_re:
                        # QuickBooks closes prior-year net income into Retained Earnings automatically (no GL line)
                        glv += sum(ni_by_year[y] for y in full_years if y < ym[:4] and y >= lo[:4])
                        if abs(glv - lf['vals'][i]) <= TOL and abs(run[ym] - lf['vals'][i]) > TOL and 'RE' not in explained:
                            explained.append('RE')
                    if is_re and abs(glv - lf['vals'][i]) > TOL and any(str(y_) not in full_years for y_ in range(int(lo[:4]), int(ym[:4]))):
                        re_unver.add(nm_)
                        continue
                    if abs(glv - lf['vals'][i]) > TOL:
                        diffs.append({'item': '%s | %s' % (nm_, ym_label(ym)), 'detail': 'Balance sheet %s vs GL balance %s (diff %s)' % (money2(lf['vals'][i]), money2(glv), money2(lf['vals'][i] - glv)), 'abs': abs(lf['vals'][i] - glv)})
            diffs.sort(key=lambda r: -r['abs'])
            st = 'ok' if not diffs and not notf and not re_unver else ('fail' if diffs else 'warn')
            s = '%s account month-end balances compared (GL beginning balance + cumulative activity vs balance sheet); %s.' % (format(tested, ','), 'all agree' if not diffs else '%d differ' % len(diffs))
            if explained:
                s += ' Retained Earnings includes the automatic year-end close of prior-year net income (QuickBooks posts it without a GL line); it was added to the GL balance before comparing.'
            if re_unver:
                s += ' Retained Earnings could not be verified for periods after a year-end because the P&L does not cover the full prior year (QuickBooks rolls prior-year net income into it automatically).'
            if notf:
                s += ' Not found in GL: ' + ', '.join(notf[:5]) + '.'
            chk('General Ledger vs Balance Sheet (account x month-end)', st, s, diffs[:20], ['item', 'detail'])
        if gl:
            bad = []
            unver = []
            grp_names = {}
            for st_ in (pl, bs):
                if st_:
                    for nd in st_.nodes:
                        if nd['kind'] == 'group':
                            grp_names.setdefault(nd['name'], set()).update(lf['gl_name'] for lf in nd['leaves'])
            for nm_, info in gl.accounts.items():
                own = sum(gl.acct_month.get(nm_, {}).values())
                desc = sum(sum(gl.acct_month.get(x, {}).values()) for x in grp_names.get(nm_, {nm_}))
                rep = info['reported_total_sub'] if info['reported_total_sub'] is not None else info['reported_total']
                if rep is not None:
                    if abs(own - rep) > TOL and abs(desc - rep) > TOL and nm_ in grp_names:
                        unver.append(nm_)
                    elif abs(own - rep) > TOL and abs(desc - rep) > TOL:
                        bad.append({'item': nm_, 'detail': 'sum of lines %s (with sub-accounts %s) vs QuickBooks total %s' % (money2(own), money2(desc), money2(rep))})
                elif info['last_balance'] is not None and info['count'] and abs(info['begin'] + own - info['last_balance']) > TOL:
                    bad.append({'item': nm_, 'detail': 'beginning + activity %s vs running balance %s' % (money2(info['begin'] + own), money2(info['last_balance']))})
            msg = '%d GL accounts, %s transactions; %s.' % (len(gl.accounts), format(len(gl.recs), ','), 'all account totals agree' if not bad else '%d accounts differ' % len(bad))
            if unver:
                msg += ' %d parent accounts (%s) include sub-accounts that are not in the loaded statements, so their totals could not be fully verified.' % (len(unver), ', '.join(unver[:4]))
            chk('General Ledger: line items tie to account totals / running balance', 'fail' if bad else ('warn' if unver else 'ok'), msg, bad[:15], ['item', 'detail'])
            guess = [n_ for n_, i in gl.accounts.items() if i.get('cls_guess') and i['count']]
            if guess:
                chk('General Ledger: account classification', 'warn',
                    '%d GL accounts are not in the P&L or Balance Sheet; debit/credit class inferred from ledger order: %s.' % (len(guess), ', '.join(guess[:6])))
            if gl.skipped_rows:
                chk('General Ledger: blank amounts', 'warn', '%d transactions have a blank amount and are treated as 0.00.' % gl.skipped_rows)
            ym0, ym1 = gl.months[0], gl.months[-1]
            if self.m.months:
                if ym0 <= self.m.months[0] and ym1 >= self.m.months[-1]:
                    chk('General Ledger covers statement period', 'ok', 'GL %s \u2013 %s fully covers analysis period %s \u2013 %s%s.' % (
                        ym_label(ym0), ym_label(ym1), ym_label(self.m.months[0]), ym_label(self.m.months[-1]),
                        ('; %s out-of-period transactions are excluded' % format(self.m.gl_outside, ',')) if self.m.gl_outside else ''))
                else:
                    chk('General Ledger covers statement period', 'warn', 'GL %s \u2013 %s does not cover the full analysis period %s \u2013 %s.' % (
                        ym_label(ym0), ym_label(ym1), ym_label(self.m.months[0]), ym_label(self.m.months[-1])))
        for w in self.m.warnings:
            if 'differs' in w or 'missing' in w.lower():
                chk('File validation', 'warn', w)
        order = {'fail': 0, 'warn': 1, 'ok': 2, 'na': 3}
        n_ok = sum(1 for k in checks if k['status'] == 'ok')
        n_fail = sum(1 for k in checks if k['status'] == 'fail')
        n_warn = sum(1 for k in checks if k['status'] == 'warn')
        self._recon = {'checks': checks, 'n_ok': n_ok, 'n_fail': n_fail, 'n_warn': n_warn}
        return self._recon

    # ---------------- General ledger ----------------------------------------
    def _gl_bounds(self, c):
        return c.start + '-01', c.end + '-31'

    def gl_filter(self, c, q):
        gl = self.gl
        lo, hi = self._gl_bounds(c)
        types = set(t for t in (q.get('types') or '').split('|') if t)
        text = (q.get('text') or '').strip().lower()
        try:
            amin = float(q['amt_min']) if q.get('amt_min') not in (None, '') else None
        except ValueError:
            amin = None
        try:
            amax = float(q['amt_max']) if q.get('amt_max') not in (None, '') else None
        except ValueError:
            amax = None
        me = q.get('month_end') == '1'
        cls = q.get('cls') or ''
        key = (lo, hi, c.acct_token, tuple(sorted(types)), text, amin, amax, me, cls)
        if key in self._gl_cache:
            self._gl_cache.move_to_end(key)
            return self._gl_cache[key]
        accset = c.acct
        out = []
        clsmap = {k: v['cls'] for k, v in gl.accounts.items()}
        pl_cls = ('income', 'cogs', 'opex', 'othinc', 'othexp')
        for r in gl.recs:
            d = r[R_DATE]
            if d < lo or d > hi:
                continue
            if accset is not None and r[R_ACCT] not in accset:
                continue
            if types and r[R_TYPE] not in types:
                continue
            a = abs(r[R_AMT])
            if amin is not None and a < amin:
                continue
            if amax is not None and a > amax:
                continue
            if cls == 'pl' and clsmap[r[R_ACCT]] not in pl_cls:
                continue
            if cls == 'bs' and clsmap[r[R_ACCT]] in pl_cls:
                continue
            if me:
                y, mth, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
                if dd < calendar.monthrange(y, mth)[1] - 2:
                    continue
            if text and text not in (r[R_ACCT] + ' ' + r[R_NAME] + ' ' + r[R_DESC] + ' ' + r[R_SPLIT] + ' ' + r[R_NUM] + ' ' + r[R_TYPE]).lower():
                continue
            out.append(r)
        self._gl_cache[key] = out
        if len(self._gl_cache) > 6:
            self._gl_cache.popitem(last=False)
        return out

    def gl_rows(self, c, q):
        if not self.gl:
            return {'available': False}
        recs = self.gl_filter(c, q)
        sort = q.get('sort', 'date')
        desc = q.get('dir', 'asc') == 'desc'
        keyf = {'date': lambda r: (r[R_DATE], r[R_ROW]), 'acct': lambda r: (r[R_ACCT].lower(), r[R_DATE]), 'type': lambda r: r[R_TYPE],
                'name': lambda r: r[R_NAME].lower(), 'amount': lambda r: r[R_AMT], 'debit': lambda r: r[R_DR], 'credit': lambda r: r[R_CR],
                'desc': lambda r: r[R_DESC].lower(), 'split': lambda r: r[R_SPLIT].lower(), 'num': lambda r: r[R_NUM]}.get(sort)
        if keyf:
            recs = sorted(recs, key=keyf, reverse=desc)
        try:
            page = max(0, int(q.get('page', 0)))
            size = min(500, max(10, int(q.get('size', 100))))
        except ValueError:
            page, size = 0, 100
        chunk = recs[page * size:(page + 1) * size]
        rows = [{'date': r[R_DATE], 'acct': r[R_ACCT], 'type': r[R_TYPE], 'num': r[R_NUM], 'name': r[R_NAME],
                 'desc': r[R_DESC][:240], 'split': r[R_SPLIT], 'amount': r[R_AMT], 'debit': r[R_DR], 'credit': r[R_CR]} for r in chunk]
        return {'available': True, 'total': len(recs), 'page': page, 'size': size, 'rows': rows,
                'sum_debit': sum(r[R_DR] for r in recs), 'sum_credit': sum(r[R_CR] for r in recs), 'sum_amount': sum(r[R_AMT] for r in recs)}

    def gl_summary(self, c, q):
        if not self.gl:
            return {'available': False, 'reason': 'No General Ledger file loaded'}
        gl = self.gl
        recs = self.gl_filter(c, q)
        clsmap = {k: v['cls'] for k, v in gl.accounts.items()}
        pl_cls = ('income', 'cogs', 'opex', 'othinc', 'othexp')
        dr = sum(r[R_DR] for r in recs)
        cr = sum(r[R_CR] for r in recs)
        by_type = collections.OrderedDict()
        monthly = collections.OrderedDict()
        for ym in c.sel:
            monthly[ym] = {'month': ym, 'label': ym_label(ym), 'debit': 0.0, 'credit': 0.0, 'count': 0}
        for r in recs:
            t = by_type.setdefault(r[R_TYPE] or '(none)', {'type': r[R_TYPE] or '(none)', 'count': 0, 'debit': 0.0, 'credit': 0.0})
            t['count'] += 1
            t['debit'] += r[R_DR]
            t['credit'] += r[R_CR]
            m_ = monthly.get(r[R_DATE][:7])
            if m_:
                m_['debit'] += r[R_DR]
                m_['credit'] += r[R_CR]
                m_['count'] += 1
        # account movement table
        acc = {}
        for r in recs:
            a = acc.setdefault(r[R_ACCT], {'acct': r[R_ACCT], 'cls': clsmap[r[R_ACCT]], 'count': 0, 'debit': 0.0, 'credit': 0.0, 'net': 0.0})
            a['count'] += 1
            a['debit'] += r[R_DR]
            a['credit'] += r[R_CR]
            a['net'] += r[R_AMT]
        unfiltered = (not c.acct and not q.get('types') and not q.get('text') and not q.get('amt_min') and not q.get('amt_max')
                      and q.get('month_end') != '1' and not q.get('cls'))
        for nm_, a in acc.items():
            info = gl.accounts[nm_]
            op = info['begin'] + sum(v for k, v in gl.acct_month.get(nm_, {}).items() if k < c.start)
            a['opening'] = op
            a['closing'] = op + a['net'] if unfiltered else None
        # largest
        big = sorted(recs, key=lambda r: -abs(r[R_AMT]))[:15]
        largest = [self._rec_dict(r) for r in big]
        # unusual (z-score within account, P&L accounts)
        stats = {}
        for r in recs:
            if clsmap[r[R_ACCT]] not in pl_cls:
                continue
            s = stats.setdefault(r[R_ACCT], [0, 0.0, 0.0])
            s[0] += 1
            s[1] += r[R_AMT]
            s[2] += r[R_AMT] ** 2
        unusual = []
        for r in recs:
            s = stats.get(r[R_ACCT])
            if not s or s[0] < 8:
                continue
            mu = s[1] / s[0]
            var = max(s[2] / s[0] - mu * mu, 0.0)
            sd = math.sqrt(var)
            if sd <= 0:
                continue
            z = (r[R_AMT] - mu) / sd
            if abs(z) >= 3 and abs(r[R_AMT]) >= c.mat_abs:
                d = self._rec_dict(r)
                d['z'] = z
                d['mean'] = mu
                unusual.append(d)
        unusual.sort(key=lambda d: -abs(d['z']))
        # duplicates
        groups = collections.defaultdict(list)
        for r in recs:
            if abs(r[R_AMT]) < 0.005:
                continue
            groups[(r[R_DATE], r[R_ACCT], round(abs(r[R_AMT]), 2), r[R_NAME] or r[R_DESC][:60])].append(r)
        dups = []
        for k, lst in groups.items():
            if len(lst) >= 2:
                dups.append({'date': k[0], 'acct': k[1], 'amount': lst[0][R_AMT], 'count': len(lst), 'name': k[3][:80],
                             'type': lst[0][R_TYPE], 'total': sum(x[R_AMT] for x in lst)})
        dups.sort(key=lambda d: -abs(d['total']))
        # month-end entries
        me_rows = collections.OrderedDict()
        for r in recs:
            d = r[R_DATE]
            y, mth, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
            if dd >= calendar.monthrange(y, mth)[1] - 2 and (r[R_TYPE] == 'Journal Entry'):
                m_ = me_rows.setdefault(d[:7], {'month': d[:7], 'label': ym_label(d[:7]), 'count': 0, 'debit': 0.0, 'credit': 0.0})
                m_['count'] += 1
                m_['debit'] += r[R_DR]
                m_['credit'] += r[R_CR]
        types_all = sorted({r[R_TYPE] for r in gl.recs if r[R_TYPE]})
        return {'available': True, 'count': len(recs), 'debit': dr, 'credit': cr, 'net': sum(r[R_AMT] for r in recs),
                'by_type': list(by_type.values()), 'monthly': list(monthly.values()),
                'accounts': sorted(acc.values(), key=lambda a: -(a['debit'] + a['credit'])),
                'largest': largest, 'unusual': unusual[:25], 'n_unusual': len(unusual), 'duplicates': dups[:40], 'n_dups': len(dups),
                'month_end': list(me_rows.values()), 'types_all': types_all, 'period': self.period_info(c),
                'gl_range': [gl.date_min, gl.date_max], 'outside': self.m.gl_outside}

    def _rec_dict(self, r):
        return {'date': r[R_DATE], 'acct': r[R_ACCT], 'type': r[R_TYPE], 'name': r[R_NAME], 'desc': r[R_DESC][:160],
                'amount': r[R_AMT], 'debit': r[R_DR], 'credit': r[R_CR], 'split': r[R_SPLIT]}

    def gl_account_detail(self, c, name):
        if not self.gl or name not in self.gl.accounts:
            return {'available': False}
        gl = self.gl
        info = gl.accounts[name]
        months = c.sel
        am = gl.acct_month.get(name, {})
        cum = info['begin'] + sum(v for k, v in am.items() if k < c.start)
        series = []
        for ym in months:
            net = am.get(ym, 0.0)
            cum += net
            series.append({'month': ym, 'label': ym_label(ym), 'debit': gl.acct_month_dr[name].get(ym, 0.0),
                           'credit': gl.acct_month_cr[name].get(ym, 0.0), 'net': net, 'balance': cum,
                           'count': gl.acct_month_n[name].get(ym, 0)})
        return {'available': True, 'name': name, 'cls': info['cls'], 'series': series}


# ----------------------------------------------------------------------------
# Report data used by both exporters
# ----------------------------------------------------------------------------
def build_report(A, q):
    c = A.ctx(q)
    rep = {'c': c, 'company': A.m.company, 'basis': A.m.basis}
    rep['overview'] = A.overview(c)
    rep['pl'] = A.pl_table(c)
    rep['bs'] = A.bs_table(c)
    rep['var'] = A.variance(c)
    rep['ratios'] = A.ratios(c)
    rep['insights'] = A.insights(c)
    rep['recon'] = A.reconcile()
    call = A.ctx({'ptype': 'all', 'cmp': 'none', 'acct': q.get('acct', '')})
    rep['pl_all'] = A.pl_table(call)
    rep['generated'] = datetime.datetime.now().strftime('%d %b %Y %H:%M')
    return rep


# ----------------------------------------------------------------------------
# XLSX writer
# ----------------------------------------------------------------------------
def _xesc(s):
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(s))
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _colname(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


XS = {'default': 0, 'title': 1, 'hdr': 2, 'money': 3, 'pct': 4, 'bold': 5, 'money_b': 6, 'text_b': 7, 'ratio': 8,
      'date': 9, 'note': 10, 'int': 11, 'wrap': 12, 'pct_b': 13}

_XSTYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="4"><numFmt numFmtId="164" formatCode="#,##0.00;[Red](#,##0.00);&quot;-&quot;"/><numFmt numFmtId="165" formatCode="0.0%;[Red]-0.0%;&quot;-&quot;"/><numFmt numFmtId="166" formatCode="0.00&quot;x&quot;"/><numFmt numFmtId="167" formatCode="yyyy-mm-dd"/></numFmts>
<fonts count="5">
<font><sz val="10"/><name val="Arial"/></font>
<font><b/><sz val="10"/><name val="Arial"/></font>
<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>
<font><b/><sz val="14"/><color rgb="FF1F3A5F"/><name val="Arial"/></font>
<font><i/><sz val="9"/><color rgb="FF667085"/><name val="Arial"/></font>
</fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF1F3A5F"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEEF2F7"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="14">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="1" fillId="3" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>
<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="167" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="165" fontId="1" fillId="3" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


class XlsxBook(object):
    def __init__(self):
        self.sheets = []

    def add(self, name, rows, widths=None, freeze=None, autofilter=False):
        name = re.sub(r'[\[\]:*?/\\]', '-', name)[:31]
        self.sheets.append({'name': name, 'rows': rows, 'widths': widths or [], 'freeze': freeze, 'af': autofilter})

    def _sheet_xml(self, sh):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
        maxc = max([len(r) for r in sh['rows']] + [1])
        out.append('<dimension ref="A1:%s%d"/>' % (_colname(maxc - 1), max(len(sh['rows']), 1)))
        pane = ''
        if sh['freeze']:
            fr, fc = sh['freeze']
            attrs = ''
            if fc:
                attrs += ' xSplit="%d"' % fc
            if fr:
                attrs += ' ySplit="%d"' % fr
            pane = '<pane%s topLeftCell="%s%d" activePane="%s" state="frozen"/>' % (
                attrs, _colname(fc), fr + 1, 'bottomRight' if (fr and fc) else ('bottomLeft' if fr else 'topRight'))
        out.append('<sheetViews><sheetView workbookViewId="0" showGridLines="0">%s</sheetView></sheetViews>' % pane)
        out.append('<sheetFormatPr defaultRowHeight="14"/>')
        if sh['widths']:
            out.append('<cols>')
            for i, w in enumerate(sh['widths']):
                out.append('<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, w))
            out.append('</cols>')
        out.append('<sheetData>')
        for ri, row in enumerate(sh['rows'], start=1):
            if not row:
                continue
            out.append('<row r="%d">' % ri)
            for ci, cell in enumerate(row):
                if cell is None:
                    continue
                style = 0
                if isinstance(cell, tuple):
                    cell, style = cell[0], XS.get(cell[1], 0) if isinstance(cell[1], str) else cell[1]
                if cell is None or cell == '':
                    continue
                ref = '%s%d' % (_colname(ci), ri)
                if isinstance(cell, bool):
                    out.append('<c r="%s" t="b" s="%d"><v>%d</v></c>' % (ref, style, 1 if cell else 0))
                elif isinstance(cell, (int, float)):
                    if isinstance(cell, float) and (math.isnan(cell) or math.isinf(cell)):
                        continue
                    out.append('<c r="%s" s="%d"><v>%s</v></c>' % (ref, style, repr(float(cell)) if isinstance(cell, float) else cell))
                else:
                    out.append('<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, style, _xesc(cell)))
            out.append('</row>')
        out.append('</sheetData>')
        if sh['af'] and sh['rows']:
            hr = sh['af'] if isinstance(sh['af'], int) and not isinstance(sh['af'], bool) else 1
            out.append('<autoFilter ref="A%d:%s%d"/>' % (hr, _colname(maxc - 1), len(sh['rows'])))
        out.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>')
        out.append('<pageSetup orientation="landscape" fitToHeight="0"/>')
        out.append('</worksheet>')
        return ''.join(out)

    def save(self):
        buf = io.BytesIO()
        z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
        n = len(self.sheets)
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
                   ''.join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1) for i in range(n)) +
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' +
                   ''.join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (_xesc(s['name']), i + 1, i + 1) for i, s in enumerate(self.sheets)) + '</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
                   ''.join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i in range(n)) +
                   '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>' % (n + 1))
        z.writestr('xl/styles.xml', _XSTYLES)
        for i, s in enumerate(self.sheets):
            z.writestr('xl/worksheets/sheet%d.xml' % (i + 1), self._sheet_xml(s))
        z.close()
        return buf.getvalue()


def _xl_date(s):
    try:
        y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
        return (datetime.date(y, m, d) - datetime.date(1899, 12, 30)).days
    except Exception:
        return s


def _fmt_style(fmt):
    return {'money': 'money', 'pct': 'pct', 'ratio': 'ratio', 'num1': 'ratio', 'days': 'int'}.get(fmt, 'money')


def export_xlsx(A, q):
    rep = build_report(A, q)
    c, ov = rep['c'], rep['overview']
    wb = XlsxBook()
    # Summary
    rows = [[(rep['company'], 'title')], [('Management MIS - Financial Analysis', 'bold')],
            [('Period', 'bold'), c.label], [('Comparison', 'bold'), ('%s: %s' % (c.cmp_name, c.cmp_label)) if c.cmp else 'None'],
            [('Basis', 'bold'), rep['basis'] or 'n/a'], [('Generated', 'bold'), rep['generated']],
            [('Account filter', 'bold'), c.acct_token or 'None (KPIs always use all accounts)'], [],
            [('KPI', 'hdr'), ('Current', 'hdr'), ('Comparison', 'hdr'), ('Change', 'hdr'), ('Change %', 'hdr'), ('Status', 'hdr')]]
    for k in ov['kpis']:
        st = _fmt_style(k['fmt'])
        rows.append([k['label'], (k['value'], st) if k['value'] is not None else 'N/A',
                     (k['prev'], st) if k['prev'] is not None else 'N/A',
                     (k['abs'], 'pct' if k['dnote'] == 'pp' else st) if k['abs'] is not None else 'N/A',
                     (k['pct'], 'pct') if k['pct'] is not None else ('n/m' if k['abs'] is not None and k['dnote'] != 'pp' else ''),
                     {'good': 'Favorable', 'bad': 'Unfavorable', 'flat': 'Flat', None: ''}[k['fav']]])
    rows.append([])
    rows.append([('Notes: EBITDA = net income + interest expense - interest income + income taxes + depreciation & amortization. '
                  'Margin changes are shown in percentage points. n/m = not meaningful (zero base or sign change). Source figures come from the loaded QuickBooks exports.', 'note')])
    wb.add('Summary', rows, [32, 18, 18, 18, 14, 14])

    def pl_sheet(name, t, with_cmp):
        if not t.get('available') or not t.get('rows'):
            wb.add(name, [['Not available']])
            return
        hdr = [('Account', 'hdr')] + [(l, 'hdr') for l in t['month_labels']] + [('Total', 'hdr')]
        if with_cmp and t['cmp_ok']:
            hdr += [('Comparison', 'hdr'), ('Change', 'hdr'), ('Change %', 'hdr')]
        hdr += [('% of revenue', 'hdr')]
        rws = [[(rep['company'] + ' - ' + name, 'title')], [c.label if with_cmp else 'All months'], [], hdr]
        for r in t['rows']:
            bold = r['kind'] in ('section', 'calc', 'group')
            line = [('    ' * r['level'] + r['label'], 'bold' if bold else 'default')]
            line += [(v, 'money_b' if r['kind'] in ('section', 'calc') else 'money') for v in r['vals']]
            line.append((r['total'], 'money_b' if bold else 'money'))
            if with_cmp and t['cmp_ok']:
                line += [(r['prev'], 'money') if r['prev'] is not None else '', (r['abs'], 'money') if r['abs'] is not None else '',
                         (r['pct'], 'pct') if r['pct'] is not None else ('n/m' if r['abs'] else '')]
            line.append((r['pct_rev'], 'pct') if r['pct_rev'] is not None else 'N/A')
            rws.append(line)
        wb.add(name, rws, [44] + [13] * (len(t['month_labels']) + 1) + [14, 14, 11, 12], freeze=(4, 1))
    pl_sheet('P&L Selected', rep['pl'], True)
    pl_sheet('P&L All Months', rep['pl_all'], False)
    bs = rep['bs']
    if bs.get('available') and bs.get('rows'):
        hdr = [('Account', 'hdr')] + [(l, 'hdr') for l in bs['month_labels']]
        if bs['cmp_ok']:
            hdr += [('Comparison (%s)' % ym_label(bs['cmp_end']), 'hdr'), ('Change', 'hdr'), ('Change %', 'hdr')]
        rws = [[(rep['company'] + ' - Balance Sheet (month-end balances)', 'title')], [], [], hdr]
        for r in bs['rows']:
            bold = r['kind'] in ('section', 'group')
            line = [('    ' * r['level'] + r['label'], 'bold' if bold else 'default')]
            line += [(v, 'money_b' if r['kind'] == 'section' else 'money') for v in r['bal']]
            if bs['cmp_ok']:
                line += [(r['prev'], 'money') if r['prev'] is not None else '', (r['abs'], 'money') if r['abs'] is not None else '',
                         (r['pct'], 'pct') if r['pct'] is not None else '']
            rws.append(line)
        rws.append([])
        rws.append([('Accounting equation (all months)', 'bold')])
        rws.append([('Month', 'hdr'), ('Assets', 'hdr'), ('Liabilities', 'hdr'), ('Equity', 'hdr'), ('L + E', 'hdr'), ('Difference', 'hdr'), ('Status', 'hdr')])
        for e in bs['equation']:
            rws.append([e['label'], (e['assets'], 'money'), (e['liabilities'], 'money'), (e['equity'], 'money'), (e['le'], 'money'),
                        (e['diff'], 'money'), 'OK' if e['ok'] else 'UNRECONCILED'])
        wb.add('Balance Sheet', rws, [44] + [14] * (len(bs['month_labels']) + 3), freeze=(4, 1))
    v = rep['var']
    if v.get('comparable'):
        rws = [[(rep['company'] + ' - Variance Analysis', 'title')],
               ['%s vs %s (%s)' % (c.label, c.cmp_label, c.cmp_name)],
               ['Materiality: abs >= %s and %% >= %s%% (n/m = zero base or sign change)' % (money(v['mat_abs']), format(v['mat_pct'], '.0f'))], [],
               [(h, 'hdr') for h in ('Account', 'Parent', 'Type', 'Current', 'Comparison', 'Change', 'Change %', 'Impact on net income', 'Status', 'Material')]]
        for r in v['rows']:
            rws.append([('    ' * (r['level'] - 1) + r['label'], 'bold' if r['kind'] == 'group' else 'default'), r['path'], r['sec_label'],
                        (r['cur'], 'money'), (r['prev'], 'money'), (r['abs'], 'money'),
                        (r['pct'], 'pct') if r['pct'] is not None else 'n/m', (r['impact'], 'money'),
                        {'good': 'Favorable', 'bad': 'Unfavorable', 'flat': 'Flat', None: ''}[r['fav']], 'Yes' if r['material'] else ''])
        wb.add('Variance', rws, [44, 28, 20, 14, 14, 14, 11, 16, 13, 10], freeze=(5, 1), autofilter=5)
    rt = rep['ratios']
    if rt.get('available'):
        rws = [[(rep['company'] + ' - Financial Ratios', 'title')], [c.label], [],
               [(h, 'hdr') for h in ('Group', 'Ratio', 'Current', 'Comparison', 'Change', 'Formula', 'Interpretation')]]
        for r in rt['rows']:
            st = _fmt_style(r['fmt'])
            rws.append([r['group'], r['name'], (r['value'], st) if r['value'] is not None else 'N/A',
                        (r['prev'], st) if r['prev'] is not None else 'N/A', (r['abs'], 'pct' if r['dnote'] == 'pp' else st) if r['abs'] is not None else '',
                        r['formula'], r['interp']])
        wb.add('Ratios', rws, [14, 36, 14, 14, 14, 52, 70], freeze=(4, 0))
    rws = [[(rep['company'] + ' - Automated Insights', 'title')], [c.label], [],
           [(h, 'hdr') for h in ('Severity', 'Insight', 'Detail')]]
    for i in rep['insights']:
        rws.append([i['sev'].upper(), i['title'], (i['detail'], 'wrap')])
    wb.add('Insights', rws, [12, 52, 120], freeze=(4, 0))
    rws = [[(rep['company'] + ' - Reconciliation & Data Integrity', 'title')], [], [(h, 'hdr') for h in ('Status', 'Check', 'Result')]]
    for k in rep['recon']['checks']:
        rws.append([{'ok': 'PASS', 'fail': 'FAIL', 'warn': 'WARNING', 'na': 'N/A'}[k['status']], k['name'], (k['summary'], 'wrap')])
        for it in k['items'][:20]:
            rws.append(['', '    ' + it['item'], it['detail']])
    wb.add('Reconciliation', rws, [12, 60, 120])
    if A.gl:
        s = A.gl_summary(c, q)
        rws = [[(rep['company'] + ' - GL Account Movements', 'title')], ['%s | opening/closing shown when no transaction filters are applied' % c.label], [],
               [(h, 'hdr') for h in ('Account', 'Class', 'Transactions', 'Opening balance', 'Debits', 'Credits', 'Net movement', 'Closing balance')]]
        for a in s['accounts']:
            rws.append([a['acct'], a['cls'], (a['count'], 'int'), (a['opening'], 'money'), (a['debit'], 'money'), (a['credit'], 'money'),
                        (a['net'], 'money'), (a['closing'], 'money') if a['closing'] is not None else ''])
        wb.add('GL Accounts', rws, [44, 12, 13, 16, 16, 16, 16, 16], freeze=(4, 1), autofilter=4)
        recs = sorted(A.gl_filter(c, q), key=lambda r: (r[R_DATE], r[R_ROW]))
        rws = [[(h, 'hdr') for h in ('Date', 'Account', 'Type', 'Num', 'Name', 'Description', 'Split', 'Amount', 'Debit', 'Credit')]]
        for r in recs[:1000000]:
            rws.append([(_xl_date(r[R_DATE]), 'date'), r[R_ACCT], r[R_TYPE], r[R_NUM], r[R_NAME], r[R_DESC][:300], r[R_SPLIT],
                        (r[R_AMT], 'money'), (r[R_DR], 'money'), (r[R_CR], 'money')])
        wb.add('GL Detail', rws, [12, 34, 18, 10, 28, 60, 28, 14, 14, 14], freeze=(1, 0), autofilter=True)
    return wb.save()


# ----------------------------------------------------------------------------
# PDF writer (vector charts, tables) - Helvetica, no external libs
# ----------------------------------------------------------------------------
_HW = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
       556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
       667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556,
       556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_HB = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
       556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
       667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611,
       611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]

PAL = ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#64748b', '#f97316']


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


class PDF(object):
    W, H = 842.0, 595.0

    def __init__(self, title, company):
        self.pages = []
        self.cur = None
        self.title = title
        self.company = company

    def new_page(self):
        self.cur = []
        self.pages.append(self.cur)
        return self.cur

    def tw(self, s, size, bold=False):
        tbl = _HB if bold else _HW
        t = 0
        for ch in s:
            o = ord(ch)
            t += tbl[o - 32] if 32 <= o <= 126 else 556
        return t * size / 1000.0

    @staticmethod
    def _enc(s):
        s = str(s).replace('\u2013', '-').replace('\u2014', '-').replace('\u2192', '->').replace('\u25b2', '^').replace('\u25bc', 'v')
        s = s.encode('cp1252', 'replace').decode('cp1252')
        return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    def fit(self, s, w, size, bold=False):
        s = str(s)
        if self.tw(s, size, bold) <= w:
            return s
        while s and self.tw(s + '...', size, bold) > w:
            s = s[:-1]
        return s + '...'

    def text(self, x, y, s, size=9, bold=False, color='#111827', align='l', rot=0):
        if s is None:
            return
        s = str(s)
        w = self.tw(s, size, bold)
        if align == 'r':
            x -= w
        elif align == 'c':
            x -= w / 2.0
        r, g, b = _rgb(color)
        font = 'F2' if bold else 'F1'
        if rot:
            a = math.radians(rot)
            tm = '%.4f %.4f %.4f %.4f %.2f %.2f Tm' % (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), x, self.H - y)
        else:
            tm = '1 0 0 1 %.2f %.2f Tm' % (x, self.H - y)
        self.cur.append('BT /%s %.1f Tf %.3f %.3f %.3f rg %s (%s) Tj ET' % (font, size, r, g, b, tm, self._enc(s)))

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.5):
        ops = ''
        if fill:
            ops += '%.3f %.3f %.3f rg ' % _rgb(fill)
        if stroke:
            ops += '%.3f %.3f %.3f RG %.2f w ' % (_rgb(stroke) + (lw,))
        op = 'B' if (fill and stroke) else ('f' if fill else 'S')
        self.cur.append('%s%.2f %.2f %.2f %.2f re %s' % (ops, x, self.H - y - h, w, h, op))

    def line(self, x1, y1, x2, y2, color='#cbd5e1', lw=0.5, dash=None):
        d = '[%s] 0 d ' % dash if dash else ''
        r, g, b = _rgb(color)
        self.cur.append('%s%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S%s' % (
            d, r, g, b, lw, x1, self.H - y1, x2, self.H - y2, ' [] 0 d' if dash else ''))

    def poly(self, pts, fill=None, stroke=None, lw=1.0, close=False):
        if len(pts) < 2:
            return
        ops = ''
        if fill:
            ops += '%.3f %.3f %.3f rg ' % _rgb(fill)
        if stroke:
            ops += '%.3f %.3f %.3f RG %.2f w 1 j 1 J ' % (_rgb(stroke) + (lw,))
        path = '%.2f %.2f m ' % (pts[0][0], self.H - pts[0][1]) + ' '.join('%.2f %.2f l' % (px, self.H - py) for px, py in pts[1:])
        if close or fill:
            path += ' h'
        op = 'B' if (fill and stroke) else ('f' if fill else 'S')
        self.cur.append(ops + path + ' ' + op)

    def save(self):
        n = len(self.pages)
        for i, pg in enumerate(self.pages):
            self.cur = pg
            self.line(36, self.H - 30, self.W - 36, self.H - 30, '#d0d5dd', 0.5)
            self.text(36, self.H - 18, 'Prepared locally from QuickBooks Online exports. Figures are reconciled to source reports; unreconciled items are flagged.', 7, color='#667085')
            self.text(self.W - 36, self.H - 18, 'Page %d of %d' % (i + 1, n), 7, color='#667085', align='r')
        objs = []

        def add(b):
            objs.append(b)
            return len(objs)
        add(b'')  # catalog placeholder
        add(b'')  # pages placeholder
        f1 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        f2 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        import zlib
        kids = []
        for pg in self.pages:
            data = zlib.compress('\n'.join(pg).encode('cp1252', 'replace'))
            cid = add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(data) + data + b'\nendstream')
            pid = add(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>' % (
                self.W, self.H, f1, f2, cid)).encode())
            kids.append(pid)
        objs[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objs[1] = ('<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % k for k in kids), len(kids))).encode()
        out = io.BytesIO()
        out.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offs = []
        for i, o in enumerate(objs, start=1):
            offs.append(out.tell())
            out.write(b'%d 0 obj\n' % i + o + b'\nendobj\n')
        xr = out.tell()
        out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
        for o in offs:
            out.write(b'%010d 00000 n \n' % o)
        info = ('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xr)).encode()
        out.write(info)
        return out.getvalue()


def _nice_ticks(lo, hi, n=5):
    if hi == lo:
        hi = lo + 1
    span = hi - lo
    raw = span / float(n)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    t0 = math.floor(lo / step) * step
    t1 = math.ceil(hi / step) * step
    ticks, v = [], t0
    while v <= t1 + step * 0.01:
        ticks.append(v)
        v += step
    return ticks


def _cmoney(v):
    a = abs(v)
    if a >= 1e6:
        s = '%.1fM' % (a / 1e6)
    elif a >= 1e3:
        s = '%.0fK' % (a / 1e3)
    else:
        s = '%.0f' % a
    return ('-' if v < 0 else '') + '$' + s


def pdf_combo(p, x, y, w, h, title, labels, bars=None, lines=None, fmt=_cmoney, stacked=False, pct=False):
    """bars: [(name, values, color)], lines: [(name, values, color)]"""
    p.text(x, y + 10, title, 10, True, '#1f3a5f')
    top = y + 34
    left, right, bottom = x + 44, x + w - 8, y + h - 30
    series = (bars or []) + (lines or [])
    allv = []
    if stacked and bars:
        for i in range(len(labels)):
            pos = sum(max(b[1][i] or 0, 0) for b in bars)
            neg = sum(min(b[1][i] or 0, 0) for b in bars)
            allv += [pos, neg]
        for s in (lines or []):
            allv += [v for v in s[1] if v is not None]
    else:
        for s in series:
            allv += [v for v in s[1] if v is not None]
    if not allv:
        p.text(x + w / 2, y + h / 2, 'No data', 9, color='#98a2b3', align='c')
        return
    lo, hi = min(min(allv), 0), max(max(allv), 0)
    ticks = _nice_ticks(lo, hi, 4)
    lo, hi = ticks[0], ticks[-1]
    yv = lambda v: bottom - (v - lo) / (hi - lo) * (bottom - top)
    for t in ticks:
        p.line(left, yv(t), right, yv(t), '#e5e7eb', 0.4)
        p.text(left - 4, yv(t) + 2.5, fmt(t) if not pct else '%.0f%%' % (t * 100), 6.5, color='#667085', align='r')
    n = len(labels)
    slot = (right - left) / float(max(n, 1))
    if bars:
        nb = 1 if stacked else len(bars)
        bw = min(slot * 0.7 / nb, 22)
        for i in range(n):
            cx = left + slot * (i + 0.5)
            if stacked:
                posb = negb = 0
                for b in bars:
                    v = b[1][i] or 0
                    if v >= 0:
                        p.rect(cx - bw / 2, yv(posb + v), bw, max(yv(posb) - yv(posb + v), 0.2), b[2])
                        posb += v
                    else:
                        p.rect(cx - bw / 2, yv(negb), bw, max(yv(negb + v) - yv(negb), 0.2), b[2])
                        negb += v
            else:
                for j, b in enumerate(bars):
                    v = b[1][i]
                    if v is None:
                        continue
                    bx = cx - nb * bw / 2 + j * bw
                    y0, y1 = yv(0), yv(v)
                    p.rect(bx, min(y0, y1), bw * 0.92, max(abs(y1 - y0), 0.2), b[2])
    for s in (lines or []):
        pts = []
        for i, v in enumerate(s[1]):
            if v is None:
                if len(pts) > 1:
                    p.poly(pts, stroke=s[2], lw=1.4)
                pts = []
                continue
            pts.append((left + slot * (i + 0.5), yv(v)))
        if len(pts) > 1:
            p.poly(pts, stroke=s[2], lw=1.4)
        for pt in pts:
            p.rect(pt[0] - 1.3, pt[1] - 1.3, 2.6, 2.6, s[2])
    p.line(left, yv(0), right, yv(0), '#94a3b8', 0.6)
    step = max(1, int(math.ceil(n / 12.0)))
    for i in range(0, n, step):
        p.text(left + slot * (i + 0.5), bottom + 10, labels[i], 6.5, color='#667085', align='c')
    lx = x + 44
    for s in series:
        p.rect(lx, y + 18, 7, 7, s[2])
        p.text(lx + 10, y + 24.5, s[0], 7, color='#475467')
        lx += 22 + p.tw(s[0], 7)


def pdf_doughnut(p, x, y, w, h, title, items):
    p.text(x, y + 10, title, 10, True, '#1f3a5f')
    if not items:
        p.text(x + w / 2, y + h / 2, 'No data', 9, color='#98a2b3', align='c')
        return
    total = sum(max(v, 0) for _, v in items)
    if total <= 0:
        p.text(x + w / 2, y + h / 2, 'No data', 9, color='#98a2b3', align='c')
        return
    cx, cy, R, r = x + 80, y + 38 + 80, 76, 44
    a0 = -math.pi / 2
    for i, (nm_, v) in enumerate(items):
        v = max(v, 0)
        a1 = a0 + 2 * math.pi * v / total
        pts, k = [], max(2, int((a1 - a0) / math.radians(3)) + 1)
        for j in range(k + 1):
            a = a0 + (a1 - a0) * j / k
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        for j in range(k, -1, -1):
            a = a0 + (a1 - a0) * j / k
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        p.poly(pts, fill=PAL[i % len(PAL)], stroke='#ffffff', lw=0.6)
        a0 = a1
    p.text(cx, cy - 1, _cmoney(total), 9, True, '#1f3a5f', 'c')
    p.text(cx, cy + 9, 'total', 7, color='#667085', align='c')
    ly = y + 38
    for i, (nm_, v) in enumerate(items):
        p.rect(x + 175, ly + i * 15 - 6, 7, 7, PAL[i % len(PAL)])
        p.text(x + 187, ly + i * 15, p.fit(nm_, w - 250, 7.5), 7.5, color='#344054')
        p.text(x + w - 4, ly + i * 15, '%s  %.0f%%' % (_cmoney(v), v / total * 100), 7.5, color='#475467', align='r')


def pdf_waterfall(p, x, y, w, h, title, wf):
    p.text(x, y + 10, title, 10, True, '#1f3a5f')
    steps = [('Prior NI', wf['start'], 'total')] + [(s['label'], s['value'], 'step') for s in wf['steps']] + [('Current NI', wf['end'], 'total')]
    run = 0.0
    levels = []
    for lab, v, kind in steps:
        if kind == 'total':
            levels.append((0.0, v))
            run = v
        else:
            levels.append((run, run + v))
            run += v
    lo = min(min(a, b) for a, b in levels + [(0, 0)])
    hi = max(max(a, b) for a, b in levels + [(0, 0)])
    ticks = _nice_ticks(lo, hi, 4)
    lo, hi = ticks[0], ticks[-1]
    top, bottom, left, right = y + 24, y + h - 70, x + 44, x + w - 6
    yv = lambda v: bottom - (v - lo) / (hi - lo) * (bottom - top)
    for t in ticks:
        p.line(left, yv(t), right, yv(t), '#e5e7eb', 0.4)
        p.text(left - 4, yv(t) + 2.5, _cmoney(t), 6.5, color='#667085', align='r')
    n = len(steps)
    slot = (right - left) / n
    bw = min(slot * 0.66, 30)
    for i, ((lab, v, kind), (a, b)) in enumerate(zip(steps, levels)):
        cx = left + slot * (i + 0.5)
        col = '#1f3a5f' if kind == 'total' else ('#10b981' if v >= 0 else '#ef4444')
        p.rect(cx - bw / 2, min(yv(a), yv(b)), bw, max(abs(yv(a) - yv(b)), 0.5), col)
        p.text(cx, min(yv(a), yv(b)) - 3, _cmoney(v), 6.5, color='#344054', align='c')
        p.text(cx - 3, bottom + 9, p.fit(lab, 72, 6.5), 6.5, color='#475467', rot=-40)
    p.line(left, yv(0), right, yv(0), '#94a3b8', 0.6)


def _chg_text(k):
    if k['abs'] is None:
        return 'No comparison', '#667085'
    col = {'good': '#067647', 'bad': '#b42318'}.get(k['fav'], '#667085')
    arrow = '^' if k['abs'] > 0 else ('v' if k['abs'] < 0 else '=')
    if k['dnote'] == 'pp':
        return '%s %.1f pts' % (arrow, abs(k['abs']) * 100), col
    if k['pct'] is not None:
        return '%s %.1f%%' % (arrow, abs(k['pct']) * 100), col
    if k['fmt'] == 'money':
        return '%s %s (n/m)' % (arrow, _cmoney(abs(k['abs']))), col
    return '%s %.2f' % (arrow, abs(k['abs'])), col


def _kfmt(k, v):
    if v is None:
        return 'N/A'
    if k['fmt'] == 'pct':
        return '%.1f%%' % (v * 100)
    if k['fmt'] == 'ratio':
        return '%.2fx' % v
    return money(v)


def _pdf_header(p, rep, subtitle):
    p.rect(0, 0, p.W, 44, '#1f3a5f')
    p.text(36, 28, rep['company'], 14, True, '#ffffff')
    p.text(p.W - 36, 28, subtitle, 10, False, '#dbe4f0', 'r')


def _table(p, rep, x, y, cols, rows, title=None, row_h=14, hdr_h=18, bottom=545, on_new=None):
    """cols: [(label, width, align)], rows: list of (cells, style) style: dict(bold,fill,color list per cell)"""
    if title:
        p.text(x, y + 10, title, 10, True, '#1f3a5f')
        y += 18

    def header(yy):
        p.rect(x, yy, sum(c[1] for c in cols), hdr_h, '#eef2f7')
        cx = x
        for lab, w, al in cols:
            p.text(cx + (w - 6 if al == 'r' else 6), yy + 12, lab, 7.5, True, '#344054', al)
            cx += w
        return yy + hdr_h
    y = header(y)
    for cells, st in rows:
        if y + row_h > bottom:
            p.new_page()
            if on_new:
                on_new()
            y = header(50)
        if st.get('fill'):
            p.rect(x, y, sum(c[1] for c in cols), row_h, st['fill'])
        cx = x
        for i, (lab, w, al) in enumerate(cols):
            s = cells[i] if i < len(cells) else ''
            col = (st.get('colors') or {}).get(i, st.get('color', '#111827'))
            txt = p.fit(s, w - 10, 7.5, st.get('bold', False))
            p.text(cx + (w - 6 if al == 'r' else 6 + st.get('indent', 0) * (1 if i == 0 else 0)), y + 9.8, txt, 7.5, st.get('bold', False), col, al)
            cx += w
        p.line(x, y + row_h, x + sum(c[1] for c in cols), y + row_h, '#eef0f3', 0.3)
        y += row_h
    return y + 8


def export_pdf(A, q):
    rep = build_report(A, q)
    c, ov = rep['c'], rep['overview']
    p = PDF('MIS Report', rep['company'])
    sub = 'Management MIS Report  |  %s' % c.label
    # ---------- page 1: KPIs
    p.new_page()
    _pdf_header(p, rep, sub)
    p.text(36, 78, 'Management MIS Report', 20, True, '#1f3a5f')
    p.text(36, 96, 'Reporting period: %s' % c.label, 10, color='#475467')
    cmp_txt = ('%s comparison: %s' % (c.cmp_name, c.cmp_label)) if (c.cmp and (c.ok_pl or c.ok_bs)) else (
        'Comparison unavailable: ' + c.reason if c.cmp else 'No comparison selected')
    p.text(36, 109, cmp_txt, 8.5, color='#667085')
    p.text(p.W - 36, 96, 'Basis: %s   |   Generated: %s' % (rep['basis'] or 'n/a', rep['generated']), 8.5, color='#667085', align='r')
    kp = [k for k in ov['kpis'] if k['key'] != 'ebitda_dummy']
    chosen = ['revenue', 'gross_profit', 'ebitda', 'net_income', 'gm', 'nm', 'total_expenses', 'assets', 'liabilities', 'equity', 'working_capital', 'current_ratio']
    kmap = {k['key']: k for k in kp}
    cw, chh, gap = (p.W - 72 - 3 * 10) / 4.0, 70, 10
    for i, key in enumerate(chosen):
        k = kmap[key]
        cx = 36 + (i % 4) * (cw + gap)
        cy = 124 + (i // 4) * (chh + gap)
        p.rect(cx, cy, cw, chh, '#ffffff', '#d0d5dd', 0.7)
        p.rect(cx, cy, 3, chh, '#2563eb')
        p.text(cx + 12, cy + 16, k['label'].upper(), 7.5, True, '#667085')
        p.text(cx + 12, cy + 40, _kfmt(k, k['value']), 17, True, '#101828')
        t, col = _chg_text(k)
        p.text(cx + 12, cy + 57, t, 8, True, col)
        if k['prev'] is not None:
            p.text(cx + cw - 10, cy + 57, 'vs ' + _kfmt(k, k['prev']), 7.5, color='#667085', align='r')
    y = 124 + 3 * (chh + gap) + 6
    p.text(36, y + 6, 'Key insights', 11, True, '#1f3a5f')
    y += 16
    sevcol = {'high': '#b42318', 'medium': '#b54708', 'low': '#475467', 'info': '#175cd3'}
    shown = [i for i in rep['insights'] if i['module'] != 'recon'][:5] or rep['insights'][:5]
    for ins in shown:
        p.rect(36, y - 7, 6, 6, sevcol[ins['sev']])
        p.text(48, y - 1, p.fit(ins['title'] + ' - ' + ins['detail'], p.W - 96, 8), 8, color='#344054')
        y += 13
    rc = rep['recon']
    p.text(36, y + 8, 'Data integrity: %d checks passed, %d warnings, %d failed (see Reconciliation page).' % (rc['n_ok'], rc['n_warn'], rc['n_fail']),
           8.5, True, '#067647' if not rc['n_fail'] else '#b42318')
    # ---------- page 2: charts
    p.new_page()
    _pdf_header(p, rep, sub)
    tr = ov['trend']
    labs = [ym_label(m_)[:3] + " '" + m_[2:4] for m_ in tr['months']]
    colw = (p.W - 72 - 16) / 2.0
    pdf_combo(p, 36, 56, colw, 230, 'Monthly revenue and net profit', labs,
              bars=[('Revenue', [v or 0 for v in tr['revenue']], '#2563eb')], lines=[('Net profit', tr['net_income'], '#10b981')])
    pdf_combo(p, 36 + colw + 16, 56, colw, 230, 'Profitability margins (monthly, capped at +/-100%)', labs,
              lines=[('EBITDA margin', [None if v is None else max(-1.0, min(1.0, v)) for v in tr['em']], '#8b5cf6'), ('Net margin', [None if v is None else max(-1.0, min(1.0, v)) for v in tr['nm']], '#10b981')], pct=True)
    mix = [(r['name'], r['value']) for r in ov['expense_mix'] if r['value'] > 0][:8]
    rest = sum(r['value'] for r in ov['expense_mix'] if r['value'] > 0) - sum(v for _, v in mix)
    if rest > 0.5:
        mix.append(('All other', rest))
    pdf_doughnut(p, 36, 300, colw, 230, 'Expense composition (selected period)', mix)
    pdf_combo(p, 36 + colw + 16, 300, colw, 230, 'Assets, liabilities and equity (month-end)', labs,
              bars=[('Liabilities', [v or 0 for v in tr['liabilities']], '#f59e0b'), ('Equity', [v or 0 for v in tr['equity']], '#2563eb')], stacked=True)
    # ---------- P&L summary
    t = rep['pl']
    if t.get('available') and t.get('rows'):
        p.new_page()
        _pdf_header(p, rep, sub + '  |  Profit & Loss')
        cols = [('Account', 300, 'l'), ('Current', 90, 'r'), ('Comparison', 90, 'r'), ('Change', 90, 'r'), ('Change %', 70, 'r'), ('% of revenue', 70, 'r')]
        rows = []
        for r in t['rows']:
            if r['level'] > 1:
                continue
            bold = r['kind'] in ('section', 'calc', 'group')
            colr = {'good': '#067647', 'bad': '#b42318'}.get(r['fav'], '#344054')
            cells = [r['label'], money(r['total']), money(r['prev']) if r['prev'] is not None else '-',
                     money(r['abs']) if r['abs'] is not None else '-',
                     ('%.1f%%' % (r['pct'] * 100)) if r['pct'] is not None else ('n/m' if r['abs'] else '-'),
                     ('%.1f%%' % (r['pct_rev'] * 100)) if r['pct_rev'] is not None else 'N/A']
            rows.append((cells, {'bold': bold, 'fill': '#f4f6fa' if r['kind'] in ('section', 'calc') else None, 'indent': r['level'] * 10,
                                 'colors': {3: colr, 4: colr}}))
        _table(p, rep, 36, 56, cols, rows, 'Profit & Loss summary - %s%s' % (c.label, '' if t['cmp_ok'] else ' (no comparison)'),
               on_new=lambda: _pdf_header(p, rep, sub + '  |  Profit & Loss'))
    # ---------- variance
    v = rep['var']
    if v.get('comparable'):
        p.new_page()
        _pdf_header(p, rep, sub + '  |  Variance')
        pdf_waterfall(p, 36, 56, p.W - 72, 250, 'Net income bridge: %s to %s (%s)' % (c.cmp_label, c.label, c.cmp_name), v['waterfall'])
        cols = [('Account', 180, 'l'), ('Current', 62, 'r'), ('Prior', 62, 'r'), ('Impact on NI', 70, 'r')]
        pos = [([r['label'], money(r['cur']), money(r['prev']), money(r['impact'])], {'colors': {3: '#067647'}}) for r in v['top_pos'][:7]]
        neg = [([r['label'], money(r['cur']), money(r['prev']), money(r['impact'])], {'colors': {3: '#b42318'}}) for r in v['top_neg'][:7]]
        _table(p, rep, 36, 318, cols, pos, 'Top favorable changes', bottom=560)
        _table(p, rep, 36 + 394 + 20, 318, cols, neg, 'Top unfavorable changes', bottom=560)
    # ---------- balance sheet + ratios
    bs = rep['bs']
    p.new_page()
    _pdf_header(p, rep, sub + '  |  Balance Sheet & Ratios')
    y = 56
    if bs.get('available') and bs.get('rows'):
        cols = [('Account', 230, 'l'), ('Balance', 85, 'r'), ('Comparison', 85, 'r'), ('Change', 80, 'r'), ('%', 50, 'r')]
        rows = []
        for r in bs['rows']:
            if r['level'] > 1:
                continue
            rows.append(([r['label'], money(r['cur']), money(r['prev']) if r['prev'] is not None else '-',
                          money(r['abs']) if r['abs'] is not None else '-', ('%.1f%%' % (r['pct'] * 100)) if r['pct'] is not None else '-'],
                         {'bold': r['kind'] in ('section', 'group'), 'fill': '#f4f6fa' if r['kind'] == 'section' else None, 'indent': r['level'] * 10}))
        eqs = bs['equation'][-1]
        rows.append((['Accounting equation check (A - L - E)', money2(eqs['diff']), '', '', 'OK' if eqs['ok'] else 'FAIL'], {'bold': True, 'colors': {4: '#067647' if eqs['ok'] else '#b42318'}}))
        y = _table(p, rep, 36, y, cols, rows, 'Balance sheet at %s' % ym_label(bs['end']) if bs.get('end') else 'Balance sheet',
                   on_new=lambda: _pdf_header(p, rep, sub + '  |  Balance Sheet & Ratios'))
    rt = rep['ratios']
    if rt.get('available'):
        cols = [('Ratio', 190, 'l'), ('Current', 70, 'r'), ('Comparison', 70, 'r'), ('Interpretation', 330, 'l')]
        rows = []

        def rfmt(r, v):
            if v is None:
                return 'N/A'
            return {'pct': '%.1f%%' % (v * 100), 'ratio': '%.2fx' % v, 'money': money(v), 'days': '%.0f d' % v, 'num1': '%.1f' % v}[r['fmt']]
        for r in rt['rows']:
            rows.append(([r['name'], rfmt(r, r['value']), rfmt(r, r['prev']), r['interp']], {}))
        p.new_page()
        _pdf_header(p, rep, sub + '  |  Financial Ratios')
        _table(p, rep, 36, 56, cols, rows, 'Financial ratios', on_new=lambda: _pdf_header(p, rep, sub + '  |  Financial Ratios'))
    # ---------- insights + recon
    p.new_page()
    _pdf_header(p, rep, sub + '  |  Insights & Data Integrity')
    cols = [('Severity', 60, 'l'), ('Insight', 230, 'l'), ('Detail', 440, 'l')]
    rows = [([i['sev'].upper(), i['title'], i['detail']], {'colors': {0: sevcol[i['sev']]}}) for i in rep['insights']][:30]
    y = _table(p, rep, 36, 56, cols, rows, 'Automated insights (rule-based, from actual figures)',
               on_new=lambda: _pdf_header(p, rep, sub + '  |  Insights & Data Integrity'))
    cols = [('Status', 60, 'l'), ('Check', 250, 'l'), ('Result', 420, 'l')]
    rows = [([{'ok': 'PASS', 'fail': 'FAIL', 'warn': 'WARN', 'na': 'N/A'}[k['status']], k['name'], k['summary']],
             {'colors': {0: {'ok': '#067647', 'fail': '#b42318', 'warn': '#b54708', 'na': '#667085'}[k['status']]}}) for k in rep['recon']['checks']]
    _table(p, rep, 36, y + 6, cols, rows, 'Reconciliation checks', on_new=lambda: _pdf_header(p, rep, sub + '  |  Insights & Data Integrity'))
    return p.save()


# ----------------------------------------------------------------------------
# Browser UI (single page, no external resources)
# ----------------------------------------------------------------------------
INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Financial Analytics Dashboard</title>
<style>
:root{--bg:#f4f6fa;--card:#ffffff;--text:#101828;--muted:#667085;--border:#e4e7ec;--grid:#e9edf3;--primary:#1f3a5f;--accent:#2563eb;
--good:#067647;--goodbg:#e7f6ee;--bad:#b42318;--badbg:#fdecea;--warn:#b54708;--warnbg:#fff4e5;--info:#175cd3;--infobg:#e8f0fe;
--side:#14233b;--sidetext:#c7d3e6;--shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08);--row:#f8fafc;--hdr:#eef2f7}
[data-theme=dark]{--bg:#0b1220;--card:#121b2f;--text:#e6edf7;--muted:#93a4bf;--border:#223049;--grid:#1d2940;--primary:#7aa7e8;--accent:#5b9bff;
--good:#4ade80;--goodbg:#10301f;--bad:#f87171;--badbg:#3a1618;--warn:#fbbf24;--warnbg:#38290c;--info:#7db0ff;--infobg:#142544;
--side:#0a1018;--sidetext:#a9b8cf;--shadow:0 1px 2px rgba(0,0,0,.4);--row:#16213a;--hdr:#18233b}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{font-family:"Segoe UI",Inter,system-ui,-apple-system,Arial,sans-serif;background:var(--bg);color:var(--text);font-size:13.5px;line-height:1.4}
button,input,select{font-family:inherit;font-size:13px;color:var(--text)}
#app{display:flex;min-height:100vh}
#side{width:228px;flex:none;background:var(--side);color:var(--sidetext);display:flex;flex-direction:column;position:sticky;top:0;height:100vh}
.brand{padding:18px 18px 14px;border-bottom:1px solid rgba(255,255,255,.08)}
.brand b{display:block;color:#fff;font-size:15px;letter-spacing:.2px}
.brand span{font-size:11.5px;opacity:.7;display:block;margin-top:3px;word-break:break-word}
#nav{padding:10px 8px;flex:1;overflow:auto}
.nav-i{display:flex;align-items:center;gap:11px;padding:9px 12px;border-radius:8px;color:var(--sidetext);cursor:pointer;margin-bottom:2px;font-size:13.5px;user-select:none}
.nav-i svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:none}
.nav-i:hover{background:rgba(255,255,255,.07);color:#fff}
.nav-i.on{background:var(--accent);color:#fff}
.nav-i.dis{opacity:.4;pointer-events:none}
.nav-sep{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;opacity:.5;padding:12px 12px 4px}
.side-f{padding:12px 14px;border-top:1px solid rgba(255,255,255,.08);font-size:11.5px;opacity:.85}
#main{flex:1;min-width:0;display:flex;flex-direction:column}
#top{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px 14px;align-items:flex-end;box-shadow:var(--shadow)}
#top h1{font-size:17px;margin:0 8px 0 0;align-self:center;white-space:nowrap}
.f{display:flex;flex-direction:column;gap:3px}
.f label{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.f select,.f input{height:32px;border:1px solid var(--border);border-radius:7px;background:var(--card);padding:0 8px;min-width:96px;outline:none}
.f select:focus,.f input:focus{border-color:var(--accent);box-shadow:0 0 0 2px rgba(37,99,235,.18)}
.f input.acct{width:210px}
.grow{flex:1}
button{cursor:pointer;border:1px solid var(--border);background:var(--card);border-radius:7px;height:32px;padding:0 12px;font-weight:600}
button:hover{border-color:var(--accent);color:var(--accent)}
button.pri{background:var(--accent);border-color:var(--accent);color:#fff}
button.pri:hover{filter:brightness(1.08);color:#fff}
button.ghost{background:transparent}
button.sm{height:24px;padding:0 8px;font-size:11px}
button:disabled{opacity:.5;cursor:not-allowed}
.menu{position:relative}
.menu-p{position:absolute;right:0;top:36px;background:var(--card);border:1px solid var(--border);border-radius:9px;box-shadow:0 8px 24px rgba(16,24,40,.18);min-width:250px;padding:6px;display:none;z-index:40}
.menu.open .menu-p{display:block}
.menu-p div{padding:9px 11px;border-radius:6px;cursor:pointer;font-weight:500}
.menu-p div:hover{background:var(--row)}
.menu-p small{display:block;color:var(--muted);font-weight:400}
#banner{padding:0 20px}
.note{margin:10px 0 0;padding:9px 12px;border-radius:8px;font-size:12.5px;display:flex;gap:8px;align-items:flex-start;justify-content:space-between}
.note.warn{background:var(--warnbg);color:var(--warn)}.note.info{background:var(--infobg);color:var(--info)}.note.bad{background:var(--badbg);color:var(--bad)}.note.good{background:var(--goodbg);color:var(--good)}
.note button{height:20px;padding:0 6px;font-size:11px;background:transparent;border:0;color:inherit}
#page{padding:16px 20px 40px;flex:1}
.strip{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:12.5px;margin:2px 0 12px}
.strip b{color:var(--text)}
.kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(205px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:11px;padding:12px 14px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent)}
.kpi-l{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);font-weight:600}
.kpi-v{font-size:23px;font-weight:700;margin:4px 0 4px;letter-spacing:-.3px}
.kpi-d{display:flex;align-items:center;gap:7px;font-size:11.5px;flex-wrap:wrap}
.spark{position:absolute;right:10px;top:12px;opacity:.9}
.muted{color:var(--muted)}
.chip{display:inline-flex;align-items:center;gap:3px;padding:1px 7px;border-radius:20px;font-weight:600;font-size:11.5px;white-space:nowrap}
.chip.good{background:var(--goodbg);color:var(--good)}.chip.bad{background:var(--badbg);color:var(--bad)}
.chip.flat,.chip.na{background:var(--hdr);color:var(--muted)}
.chip.high{background:var(--badbg);color:var(--bad)}.chip.medium{background:var(--warnbg);color:var(--warn)}
.chip.low{background:var(--hdr);color:var(--muted)}.chip.info{background:var(--infobg);color:var(--info)}
.chip.ok{background:var(--goodbg);color:var(--good)}.chip.fail{background:var(--badbg);color:var(--bad)}.chip.warn{background:var(--warnbg);color:var(--warn)}
.grid{display:grid;gap:14px;margin-bottom:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr))}
.card{background:var(--card);border:1px solid var(--border);border-radius:11px;box-shadow:var(--shadow);min-width:0}
.card-h{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;padding:12px 14px 0}
.card-h h3{margin:0;font-size:14px}
.sub{font-size:11.5px;color:var(--muted);margin-top:1px}
.cbody{padding:6px 8px 10px;min-height:60px}
.pad{padding:12px 14px}
.sec-t{font-size:15px;font-weight:700;margin:18px 0 8px}
.tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px}
.tools label{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:5px}
.tools input[type=text],.tools input[type=number]{height:30px;border:1px solid var(--border);border-radius:7px;padding:0 8px;background:var(--card);width:120px}
.seg{display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.seg span{padding:5px 11px;cursor:pointer;font-weight:600;font-size:12px;color:var(--muted)}
.seg span.on{background:var(--accent);color:#fff}
.tbl-wrap{overflow:auto;max-height:68vh;border-top:1px solid var(--border)}
table.tbl{width:100%;border-collapse:separate;border-spacing:0;font-size:12.5px}
.tbl th{position:sticky;top:0;background:var(--hdr);text-align:left;padding:8px 10px;font-weight:700;font-size:11.5px;white-space:nowrap;border-bottom:1px solid var(--border);z-index:2;color:var(--text)}
.tbl th.sortable{cursor:pointer}.tbl th.sortable:hover{color:var(--accent)}
.tbl td{padding:6px 10px;border-bottom:1px solid var(--grid);white-space:nowrap;max-width:420px;overflow:hidden;text-overflow:ellipsis}
.tbl td.wrap{white-space:normal;min-width:240px}
.tbl .num{text-align:right;font-variant-numeric:tabular-nums}
.tbl tr:hover td{background:var(--row)}
.tbl td.sticky,.tbl th.sticky{position:sticky;left:0;background:var(--card);z-index:1;min-width:270px;max-width:340px}
.tbl th.sticky{background:var(--hdr);z-index:3}
.tbl tr:hover td.sticky{background:var(--row)}
.tbl tr.r-section td{font-weight:700;background:var(--hdr)}.tbl tr.r-section td.sticky{background:var(--hdr)}
.tbl tr.r-calc td{font-weight:700;background:var(--hdr);border-top:1px solid var(--border)}.tbl tr.r-calc td.sticky{background:var(--hdr)}
.tbl tr.r-group td{font-weight:600}
.tbl tr.r-memo td{font-style:italic;color:var(--muted)}
.neg{color:var(--bad)}
.caret{display:inline-block;width:14px;cursor:pointer;color:var(--muted);user-select:none}
.lnk{cursor:pointer;color:var(--accent)}.lnk:hover{text-decoration:underline}
.tfoot td{font-weight:700;background:var(--hdr);position:sticky;bottom:0}
.pager{display:flex;gap:8px;align-items:center;padding:8px 14px;border-top:1px solid var(--border);color:var(--muted);font-size:12px}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--border);padding:0 10px;overflow:auto}
.tabs div{padding:10px 14px;cursor:pointer;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;white-space:nowrap}
.tabs div.on{color:var(--accent);border-color:var(--accent)}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.pill{padding:3px 10px;border-radius:20px;border:1px solid var(--border);cursor:pointer;font-size:12px;font-weight:600;color:var(--muted);background:var(--card)}
.pill.on{background:var(--accent);border-color:var(--accent);color:#fff}
.ins{display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid var(--grid);align-items:flex-start}
.ins:last-child{border:0}
.ins h4{margin:0 0 2px;font-size:13.5px}.ins p{margin:0;color:var(--muted);font-size:12.5px}
.chk{padding:12px 14px;border-bottom:1px solid var(--grid)}
.chk-h{display:flex;gap:10px;align-items:center;cursor:pointer}
.chk-h b{flex:1}
.chk p{margin:5px 0 0;color:var(--muted);font-size:12.5px}
.chk-d{display:none;margin-top:8px}.chk.open .chk-d{display:block}
#overlay{position:fixed;inset:0;background:rgba(10,16,28,.55);display:none;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(2px)}
#overlay.on{display:flex}
.ov-c{background:var(--card);border-radius:14px;padding:24px 28px;width:min(440px,90vw);box-shadow:0 20px 50px rgba(0,0,0,.35)}
.ov-c h3{margin:0 0 4px}.bar{height:8px;background:var(--hdr);border-radius:6px;overflow:hidden;margin:14px 0 8px}
.bar i{display:block;height:100%;background:var(--accent);width:0;transition:width .25s}
#topbar-load{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0;z-index:200;transition:width .3s,opacity .3s}
#tip{position:fixed;pointer-events:none;background:#101828;color:#fff;padding:7px 10px;border-radius:7px;font-size:12px;z-index:300;display:none;max-width:340px;box-shadow:0 6px 18px rgba(0,0,0,.35);line-height:1.5}
#tip i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px}
#toast{position:fixed;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:400}
#toast div{background:#101828;color:#fff;padding:10px 14px;border-radius:9px;box-shadow:0 6px 18px rgba(0,0,0,.35);max-width:380px}
#toast div.err{background:#b42318}
.land{max-width:860px;margin:30px auto}
.land .hero{padding:28px;text-align:center}
.land .hero h2{margin:0 0 6px;font-size:22px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.dz{border:2px dashed var(--border);border-radius:12px;padding:26px;text-align:center;margin-top:16px}
.badge{padding:2px 8px;border-radius:5px;font-size:11px;font-weight:700;background:var(--infobg);color:var(--info)}
.empty{padding:34px;text-align:center;color:var(--muted)}
.spin{width:22px;height:22px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:sp 0.8s linear infinite;display:inline-block;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}
@media (max-width:980px){#side{width:62px}.brand span,.nav-i b,.side-f,.nav-sep,.brand b small{display:none}.nav-i{justify-content:center}}
@media print{#side,#top,.tools,button{display:none!important}}
</style>
</head>
<body>
<div id="topbar-load"></div>
<div id="app">
  <aside id="side">
    <div class="brand"><b>Financial Analytics<small></small></b><span id="brand-co">No data loaded</span></div>
    <nav id="nav"></nav>
    <div class="side-f" id="side-f">Local &amp; private: files are read on this computer only.</div>
  </aside>
  <div id="main">
    <header id="top"></header>
    <div id="banner"></div>
    <section id="page"></section>
  </div>
</div>
<div id="overlay"><div class="ov-c"><h3 id="ov-t">Loading</h3><div class="muted" id="ov-m">Starting...</div><div class="bar"><i id="ov-b"></i></div><div class="muted" style="font-size:12px">Large General Ledger files can take a little while.</div></div></div>
<div id="tip"></div>
<div id="toast"></div>
<script>
'use strict';
/* ===== helpers ===== */
const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const ymLabel = ym => MON[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4);
const ymShort = ym => MON[+ym.slice(5, 7) - 1] + " '" + ym.slice(2, 4);
const ymAdd = (ym, k) => { const t = +ym.slice(0, 4) * 12 + (+ym.slice(5, 7) - 1) + k; return String(Math.floor(t / 12)).padStart(4, '0') + '-' + String(t % 12 + 1).padStart(2, '0'); };
const ymQ = ym => ym.slice(0, 4) + '-Q' + (Math.floor((+ym.slice(5, 7) - 1) / 3) + 1);
const nf0 = new Intl.NumberFormat('en-US', {maximumFractionDigits: 0});
const nf2 = new Intl.NumberFormat('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const F = {
  money: v => v == null ? 'N/A' : (Math.abs(v) < 0.5 ? '$0' : (v < 0 ? '-' : '') + '$' + nf0.format(Math.abs(v))),
  money2: v => v == null ? 'N/A' : (v < 0 ? '-' : '') + '$' + nf2.format(Math.abs(v)),
  pct: (v, d) => v == null ? 'N/A' : (v * 100).toFixed(d == null ? 1 : d) + '%',
  ratio: v => v == null ? 'N/A' : v.toFixed(2) + 'x',
  num1: v => v == null ? 'N/A' : v.toFixed(1),
  days: v => v == null ? 'N/A' : Math.round(v) + ' days',
  int: v => v == null ? 'N/A' : nf0.format(v),
  compact: v => { if (v == null) return ''; const a = Math.abs(v); const s = a >= 1e9 ? (a / 1e9).toFixed(1) + 'B' : a >= 1e6 ? (a / 1e6).toFixed(1) + 'M' : a >= 1e3 ? (a / 1e3).toFixed(a >= 1e5 ? 0 : 1).replace(/\.0$/, '') + 'K' : a.toFixed(0); return (v < 0 ? '-' : '') + '$' + s; },
};
const fmtBy = (f, v) => (F[f] || F.money)(v);
const moneyCell = v => v == null ? '<span class="muted">-</span>' : `<span class="${v < -0.005 ? 'neg' : ''}">${F.money(v)}</span>`;
const COL = {rev: '#2563eb', cogs: '#f59e0b', gp: '#06b6d4', ebitda: '#8b5cf6', ni: '#10b981', loss: '#ef4444', assets: '#06b6d4', liab: '#f59e0b', equity: '#2563eb', cash: '#10b981', wc: '#8b5cf6', debit: '#2563eb', credit: '#f59e0b'};
const PAL = ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#64748b', '#f97316', '#14b8a6', '#a855f7'];
const FONT = 'Segoe UI, Inter, Arial, sans-serif';
const T = () => { const cs = getComputedStyle(document.documentElement); const g = n => cs.getPropertyValue(n).trim(); return {text: g('--text'), muted: g('--muted'), grid: g('--grid'), bg: g('--card'), border: g('--border')}; };

/* ===== state ===== */
const S = {meta: null, page: 'overview', f: {ptype: 'ytd', pval: '', from: '', to: '', cmp: 'yoy', acct: '', mat_abs: 1000, mat_pct: 10},
  collapsed: {}, charts: {}, plView: 'amt', bsView: 'bal', gl: {text: '', types: [], cls: '', amin: '', amax: '', me: false, sort: 'date', dir: 'asc', page: 0, size: 100, tab: 'txns'},
  var: {material: false, leaf: true}, insSev: 'all', acctMap: {}, token: 0};

function qs(extra) {
  const f = S.f, p = new URLSearchParams();
  p.set('ptype', f.ptype); if (f.pval) p.set('pval', f.pval); if (f.from) p.set('from', f.from); if (f.to) p.set('to', f.to);
  p.set('cmp', f.cmp); if (f.acct) p.set('acct', f.acct); p.set('mat_abs', f.mat_abs); p.set('mat_pct', f.mat_pct);
  if (extra) for (const k in extra) if (extra[k] !== '' && extra[k] != null) p.set(k, extra[k]);
  return p.toString();
}
let loadN = 0;
function progressBar(on) {
  const b = $('#topbar-load'); loadN += on ? 1 : -1;
  if (loadN > 0) { b.style.opacity = 1; b.style.width = '70%'; } else { loadN = 0; b.style.width = '100%'; setTimeout(() => { b.style.opacity = 0; b.style.width = '0'; }, 250); }
}
async function api(path, extra, raw) {
  progressBar(true);
  try {
    const url = path + (raw ? '' : '?' + qs(extra));
    const r = await fetch(url);
    const j = await r.json();
    if (!r.ok || (j && j.error && !j.loaded && r.status >= 400)) throw new Error(j.error || r.statusText);
    return j;
  } finally { progressBar(false); }
}
async function post(path, body) {
  const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})});
  const j = await r.json();
  if (!r.ok) { const e = new Error(j.error || r.statusText); e.data = j; throw e; }
  return j;
}
function toast(msg, err) {
  const d = document.createElement('div'); if (err) d.className = 'err'; d.textContent = msg; $('#toast').appendChild(d);
  setTimeout(() => d.remove(), err ? 7000 : 3500);
}
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

/* delta chip */
function chip(r, fmt) {
  if (r == null || r.abs == null) return '<span class="chip na">-</span>';
  const a = r.abs;
  const arrow = a > 1e-6 ? '&#9650;' : (a < -1e-6 ? '&#9660;' : '&#9632;');
  let txt;
  if (r.dnote === 'pp') txt = Math.abs(a * 100).toFixed(1) + ' pts';
  else if (r.pct != null) txt = Math.abs(r.pct * 100).toFixed(1) + '%';
  else if (r.dnote === 'sign') txt = 'n/m';
  else if (r.dnote === 'zero') txt = 'new';
  else txt = fmtBy(fmt || 'money', Math.abs(a));
  const title = 'Change: ' + (r.dnote === 'pp' ? (a * 100).toFixed(2) + ' percentage points' : fmtBy(fmt || 'money', a)) + (r.dnote === 'sign' ? ' (percent not meaningful: sign change)' : r.dnote === 'zero' ? ' (zero base)' : '');
  return `<span class="chip ${r.fav || 'flat'}" title="${esc(title)}">${arrow} ${txt}</span>`;
}

/* ===== tooltip ===== */
const tip = $('#tip');
document.addEventListener('mousemove', e => {
  const t = e.target.closest ? e.target.closest('[data-tip]') : null;
  if (!t) { tip.style.display = 'none'; return; }
  tip.innerHTML = t.getAttribute('data-tip');
  tip.style.display = 'block';
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + 14, y = e.clientY + 14;
  if (x + w > innerWidth - 8) x = e.clientX - w - 14;
  if (y + h > innerHeight - 8) y = e.clientY - h - 14;
  tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
});
document.addEventListener('mouseleave', () => tip.style.display = 'none');

/* ===== chart library (SVG strings; explicit colors so PNG export works) ===== */
function niceTicks(lo, hi, n) {
  n = n || 5; if (hi === lo) hi = lo + 1;
  const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  let step = mag; for (const m of [1, 2, 2.5, 5, 10]) { step = m * mag; if (step >= raw) break; }
  const t0 = Math.floor(lo / step) * step, t1 = Math.ceil(hi / step) * step, out = [];
  for (let v = t0; v <= t1 + step * 0.01; v += step) out.push(+v.toFixed(10));
  return out;
}
const svgOpen = (w, h) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" font-family="${FONT}" style="display:block;max-width:100%">`;
const tipRow = (c, n, v) => `<i style="background:${c}"></i>${esc(n)}: <b>${v}</b>`;
const noData = (w, h, t) => `${svgOpen(w, h)}<text x="${w / 2}" y="${h / 2}" text-anchor="middle" fill="#98a2b3" font-size="13">${esc(t || 'No data for this selection')}</text></svg>`;

function drawCombo(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 280), H = o.h || 290;
  const L = o.left || 60, R = 14, Tp = 36, B = 34, n = o.labels.length;
  const fmt = o.fmt || F.compact, tfmt = o.tfmt || fmt;
  const all = [];
  const bars = o.series.filter(s => s.type === 'bar'), lines = o.series.filter(s => s.type !== 'bar');
  const clipv = v => (v == null ? v : (o.clip ? Math.max(o.clip[0], Math.min(o.clip[1], v)) : v));
  if (o.stacked) {
    for (let i = 0; i < n; i++) { let p = 0, q = 0; bars.forEach(s => { const v = s.data[i] || 0; if (v >= 0) p += v; else q += v; }); all.push(p, q); }
    lines.forEach(s => s.data.forEach(v => { if (v != null) all.push(clipv(v)); }));
  } else o.series.forEach(s => s.data.forEach(v => { if (v != null) all.push(clipv(v)); }));
  if (!all.length || n === 0) return noData(W, H);
  let lo = Math.min(0, ...all), hi = Math.max(0, ...all);
  if (o.min != null) lo = o.min; const ticks = niceTicks(lo, hi, 5); lo = ticks[0]; hi = ticks[ticks.length - 1];
  const top = Tp, bot = H - B, x0 = L, x1 = W - R, slot = (x1 - x0) / n;
  const y = v => bot - (v - lo) / (hi - lo) * (bot - top);
  let s = svgOpen(W, H);
  if (o.sel && o.sel[1] - o.sel[0] + 1 < n) s += `<rect x="${x0 + slot * o.sel[0]}" y="${top}" width="${slot * (o.sel[1] - o.sel[0] + 1)}" height="${bot - top}" fill="${COL.rev}" opacity=".07"/>`;
  ticks.forEach(t => { s += `<line x1="${x0}" x2="${x1}" y1="${y(t)}" y2="${y(t)}" stroke="${th.grid}"/><text x="${x0 - 6}" y="${y(t) + 4}" text-anchor="end" font-size="10.5" fill="${th.muted}">${o.axisFmt ? o.axisFmt(t) : fmt(t)}</text>`; });
  const inSel = i => !o.sel || (i >= o.sel[0] && i <= o.sel[1]);
  const nb = o.stacked ? 1 : Math.max(bars.length, 1), bw = Math.min(slot * 0.72 / nb, 34);
  for (let i = 0; i < n; i++) {
    const cx = x0 + slot * (i + 0.5);
    if (o.stacked) {
      let pb = 0, qb = 0;
      bars.forEach(sr => { const v = sr.data[i] || 0; if (!v) return; if (v >= 0) { s += `<rect x="${cx - bw / 2}" y="${y(pb + v)}" width="${bw}" height="${Math.max(y(pb) - y(pb + v), .3)}" fill="${sr.color}" opacity="${inSel(i) ? 1 : .45}"/>`; pb += v; } else { s += `<rect x="${cx - bw / 2}" y="${y(qb)}" width="${bw}" height="${Math.max(y(qb + v) - y(qb), .3)}" fill="${sr.color}" opacity="${inSel(i) ? 1 : .45}"/>`; qb += v; } });
    } else bars.forEach((sr, j) => {
      const v = sr.data[i]; if (v == null) return; const cv = clipv(v);
      const bx = cx - nb * bw / 2 + j * bw, y0 = y(0), y1 = y(cv);
      const col = (sr.negColor && v < 0) ? sr.negColor : sr.color;
      s += `<rect x="${bx}" y="${Math.min(y0, y1)}" width="${bw * 0.92}" height="${Math.max(Math.abs(y1 - y0), .3)}" rx="1.5" fill="${col}" opacity="${inSel(i) ? 1 : .45}"/>`;
    });
  }
  s += `<line x1="${x0}" x2="${x1}" y1="${y(0)}" y2="${y(0)}" stroke="${th.muted}" stroke-opacity=".5"/>`;
  lines.forEach(sr => {
    let seg = [], path = '';
    sr.data.forEach((v, i) => { if (v == null) { if (seg.length) path += 'M' + seg.join('L'); seg = []; return; } seg.push((x0 + slot * (i + .5)).toFixed(1) + ',' + y(clipv(v)).toFixed(1)); });
    if (seg.length) path += 'M' + seg.join('L');
    if (sr.type === 'area') { sr.data.forEach(() => { }); }
    s += `<path d="${path}" fill="none" stroke="${sr.color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>`;
    sr.data.forEach((v, i) => { if (v != null) s += `<circle cx="${x0 + slot * (i + .5)}" cy="${y(clipv(v))}" r="2.8" fill="${th.bg}" stroke="${sr.color}" stroke-width="1.8"/>`; });
  });
  const step = Math.max(1, Math.ceil(n / Math.max(Math.floor((x1 - x0) / 52), 1)));
  for (let i = 0; i < n; i += step) s += `<text x="${x0 + slot * (i + .5)}" y="${bot + 17}" text-anchor="middle" font-size="10.5" fill="${th.muted}">${esc(o.labels[i])}</text>`;
  let lx = x0;
  o.series.forEach(sr => { s += `<rect x="${lx}" y="12" width="9" height="9" rx="2" fill="${sr.color}"/><text x="${lx + 13}" y="20.5" font-size="11.5" fill="${th.text}">${esc(sr.name)}</text>`; lx += 30 + sr.name.length * 6.1; });
  for (let i = 0; i < n; i++) {
    let tp = `<b>${esc(o.labels[i])}</b>`;
    o.series.forEach(sr => { const v = sr.data[i]; tp += '<br>' + tipRow(sr.color, sr.name, v == null ? 'N/A' : tfmt(v)); });
    if (o.stacked) tp += '<br>Total: <b>' + tfmt(bars.reduce((a, sr) => a + (sr.data[i] || 0), 0)) + '</b>';
    s += `<rect x="${x0 + slot * i}" y="${top}" width="${slot}" height="${bot - top}" fill="transparent" data-tip="${esc(tp)}"/>`;
  }
  return s + '</svg>';
}

function arcPath(cx, cy, R, r, a0, a1) {
  const p = (rad, a) => [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
  const large = a1 - a0 > Math.PI ? 1 : 0, A = p(R, a0), B = p(R, a1), C = p(r, a1), D = p(r, a0);
  return `M${A[0]},${A[1]}A${R},${R} 0 ${large} 1 ${B[0]},${B[1]}L${C[0]},${C[1]}A${r},${r} 0 ${large} 0 ${D[0]},${D[1]}Z`;
}
function drawDonut(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 280), H = o.h || 290;
  const items = o.items.filter(i => i.value > 0);
  const total = items.reduce((a, b) => a + b.value, 0);
  if (!total) return noData(W, H);
  const wide = W > 470, R = wide ? Math.min(H / 2 - 14, 118) : Math.min(W / 2 - 14, 100), r = R * 0.6;
  const cx = wide ? R + 16 : W / 2, cy = wide ? H / 2 : R + 12;
  let s = svgOpen(W, wide ? H : H + items.length * 18 - 40), a0 = -Math.PI / 2;
  items.forEach((it, i) => {
    let a1 = a0 + 2 * Math.PI * it.value / total; if (items.length === 1) a1 = a0 + 2 * Math.PI - 0.0001;
    const tp = `<b>${esc(it.name)}</b><br>${(o.fmt || F.money)(it.value)} &middot; ${(it.value / total * 100).toFixed(1)}%`;
    s += `<path d="${arcPath(cx, cy, R, r, a0, a1)}" fill="${it.color || PAL[i % PAL.length]}" stroke="${th.bg}" stroke-width="1.5" data-tip="${esc(tp)}"${it.drill ? ` data-drill="${esc(it.drill)}" style="cursor:pointer"` : ''}/>`;
    a0 = a1;
  });
  s += `<text x="${cx}" y="${cy - 2}" text-anchor="middle" font-size="17" font-weight="700" fill="${th.text}">${F.compact(total)}</text><text x="${cx}" y="${cy + 14}" text-anchor="middle" font-size="11" fill="${th.muted}">${esc(o.center || 'total')}</text>`;
  const lx = wide ? cx + R + 30 : 16;
  let ly = wide ? Math.max(18, cy - items.length * 10) : cy + R + 24;
  items.forEach((it, i) => {
    s += `<rect x="${lx}" y="${ly - 9}" width="9" height="9" rx="2" fill="${it.color || PAL[i % PAL.length]}"/><text x="${lx + 14}" y="${ly}" font-size="11.5" fill="${th.text}">${esc(it.name.length > 30 ? it.name.slice(0, 29) + '…' : it.name)}</text><text x="${W - 12}" y="${ly}" text-anchor="end" font-size="11.5" fill="${th.muted}">${F.compact(it.value)} · ${(it.value / total * 100).toFixed(0)}%</text>`;
    ly += 18;
  });
  return s + '</svg>';
}

function drawWaterfall(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 320), H = o.h || 340;
  const steps = [{label: o.startLabel || 'Start', v: o.start, t: 'total'}].concat(o.steps.map(s => ({label: s.label, v: s.value, t: 'step'})), [{label: o.endLabel || 'End', v: o.end, t: 'total'}]);
  let run = 0; const lv = steps.map(s => { if (s.t === 'total') { run = s.v; return [0, s.v]; } const a = run; run += s.v; return [a, run]; });
  const all = [0]; lv.forEach(a => all.push(a[0], a[1]));
  const ticks = niceTicks(Math.min(...all), Math.max(...all), 5), lo = ticks[0], hi = ticks[ticks.length - 1];
  const L = 62, R = 12, Tp = 20, B = 92, x0 = L, x1 = W - R, top = Tp, bot = H - B, slot = (x1 - x0) / steps.length, bw = Math.min(slot * .66, 46);
  const y = v => bot - (v - lo) / (hi - lo) * (bot - top);
  let s = svgOpen(W, H);
  ticks.forEach(t => { s += `<line x1="${x0}" x2="${x1}" y1="${y(t)}" y2="${y(t)}" stroke="${th.grid}"/><text x="${x0 - 6}" y="${y(t) + 4}" text-anchor="end" font-size="10.5" fill="${th.muted}">${F.compact(t)}</text>`; });
  steps.forEach((st, i) => {
    const [a, b] = lv[i], cx = x0 + slot * (i + .5), col = st.t === 'total' ? '#1f3a5f' : (st.v >= 0 ? '#10b981' : '#ef4444');
    const tp = `<b>${esc(st.label)}</b><br>${st.t === 'total' ? 'Net income' : 'Impact on net income'}: <b>${F.money(st.v)}</b>`;
    s += `<rect x="${cx - bw / 2}" y="${Math.min(y(a), y(b))}" width="${bw}" height="${Math.max(Math.abs(y(a) - y(b)), 1)}" rx="2" fill="${st.t === 'total' ? (document.documentElement.dataset.theme === 'dark' ? '#7aa7e8' : '#1f3a5f') : col}" data-tip="${esc(tp)}"/>`;
    s += `<text x="${cx}" y="${Math.min(y(a), y(b)) - 5}" text-anchor="middle" font-size="10.5" font-weight="600" fill="${th.text}">${F.compact(st.v)}</text>`;
    if (i < steps.length - 1) s += `<line x1="${cx + bw / 2}" x2="${cx + slot - bw / 2}" y1="${y(lv[i][1])}" y2="${y(lv[i][1])}" stroke="${th.muted}" stroke-dasharray="3 3" stroke-opacity=".6"/>`;
    const lab = st.label.length > 24 ? st.label.slice(0, 23) + '…' : st.label;
    s += `<text transform="translate(${cx + 4},${bot + 14}) rotate(40)" font-size="10.5" fill="${th.muted}">${esc(lab)}</text>`;
  });
  s += `<line x1="${x0}" x2="${x1}" y1="${y(0)}" y2="${y(0)}" stroke="${th.muted}" stroke-opacity=".6"/>`;
  return s + '</svg>';
}

function drawHBar(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 300), rowH = 26, items = o.items, H = Math.max(items.length * rowH + 16, 60);
  if (!items.length) return noData(W, 70, o.empty || 'Nothing to show');
  const L = Math.min(W * 0.42, 230), R = 80, mx = Math.max(...items.map(i => Math.abs(i.value)));
  let s = svgOpen(W, H);
  items.forEach((it, i) => {
    const y = 8 + i * rowH, w = (W - L - R) * Math.abs(it.value) / mx;
    const lab = it.label.length > 34 ? it.label.slice(0, 33) + '…' : it.label;
    s += `<text x="${L - 8}" y="${y + 14}" text-anchor="end" font-size="11.5" fill="${th.text}">${esc(lab)}</text><rect x="${L}" y="${y + 3}" width="${Math.max(w, 1.5)}" height="16" rx="2" fill="${it.color || o.color || COL.rev}" data-tip="${esc(it.tip || it.label + ': ' + F.money(it.value))}"${it.drill ? ` data-drill="${esc(it.drill)}" style="cursor:pointer"` : ''}/><text x="${L + w + 6}" y="${y + 15}" font-size="11.5" fill="${th.muted}">${F.compact(it.value)}</text>`;
  });
  return s + '</svg>';
}

function squarify(data, x, y, w, h) {
  const total = data.reduce((s, d) => s + d.value, 0), out = [];
  let rest = data.map(d => Object.assign({}, d, {area: d.value / total * w * h}));
  let cx = x, cy = y, cw = w, ch = h;
  const worst = (r, ra, short) => { const s2 = short * short, mx = Math.max(...r.map(a => a.area)), mn = Math.min(...r.map(a => a.area)); return Math.max(s2 * mx / (ra * ra), ra * ra / (s2 * mn)); };
  while (rest.length) {
    const short = Math.min(cw, ch); let row = [rest[0]], ra = rest[0].area, i = 1;
    while (i < rest.length) { const nr = row.concat([rest[i]]), na = ra + rest[i].area; if (worst(nr, na, short) <= worst(row, ra, short)) { row = nr; ra = na; i++; } else break; }
    if (cw >= ch) { const rw = ra / ch; let yy = cy; row.forEach(a => { const hh = a.area / rw; out.push(Object.assign({}, a, {x: cx, y: yy, w: rw, h: hh})); yy += hh; }); cx += rw; cw -= rw; }
    else { const rh = ra / cw; let xx = cx; row.forEach(a => { const ww = a.area / rh; out.push(Object.assign({}, a, {x: xx, y: cy, w: ww, h: rh})); xx += ww; }); cy += rh; ch -= rh; }
    rest = rest.slice(row.length);
  }
  return out;
}
function drawTreemap(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 300), H = o.h || 300;
  const items = o.items.filter(i => i.value > 0).sort((a, b) => b.value - a.value);
  if (!items.length) return noData(W, H);
  const total = items.reduce((a, b) => a + b.value, 0), rects = squarify(items, 0, 0, W, H);
  let s = svgOpen(W, H);
  rects.forEach((r, i) => {
    let tp = `<b>${esc(r.name)}</b><br>${F.money(r.value)} &middot; ${(r.value / total * 100).toFixed(1)}% of total`;
    if (r.children && r.children.length) tp += '<br><br>' + r.children.slice(0, 8).map(c => esc(c.name) + ': ' + F.money(c.value)).join('<br>');
    if (r.prev != null) tp += `<br><br>Comparison: ${F.money(r.prev)}`;
    const col = PAL[i % PAL.length];
    s += `<rect x="${r.x + 1}" y="${r.y + 1}" width="${Math.max(r.w - 2, 0)}" height="${Math.max(r.h - 2, 0)}" rx="3" fill="${col}" fill-opacity=".88" stroke="${th.bg}" data-tip="${esc(tp)}"${r.drill ? ` data-drill="${esc(r.drill)}" style="cursor:pointer"` : ''}/>`;
    if (r.w > 70 && r.h > 34) {
      const mc = Math.floor((r.w - 14) / 6.4);
      s += `<text x="${r.x + 8}" y="${r.y + 18}" font-size="11.5" font-weight="600" fill="#fff" pointer-events="none">${esc(r.name.length > mc ? r.name.slice(0, Math.max(mc - 1, 3)) + '…' : r.name)}</text><text x="${r.x + 8}" y="${r.y + 33}" font-size="11" fill="#fff" fill-opacity=".92" pointer-events="none">${F.compact(r.value)}</text>`;
    }
  });
  return s + '</svg>';
}

function drawHeatmap(el, o) {
  const th = T(), W = Math.max(el.clientWidth - 8, 320), rows = o.rows, cols = o.cols, n = cols.length;
  if (!rows.length) return noData(W, 80);
  const L = Math.min(210, W * .3), Tp = 40, cellH = 22, H = Tp + rows.length * cellH + 10, cw = (W - L - 10) / n;
  let s = svgOpen(W, H);
  const step = Math.max(1, Math.ceil(n / Math.floor((W - L) / 44)));
  cols.forEach((c, i) => { if (i % step === 0) s += `<text x="${L + cw * (i + .5)}" y="${Tp - 10}" text-anchor="middle" font-size="10.5" fill="${th.muted}">${esc(c)}</text>`; });
  rows.forEach((r, j) => {
    const y = Tp + j * cellH, mx = Math.max(...r.vals.map(Math.abs), 1);
    const mc = Math.max(8, Math.floor((L - 12) / 6.1)); s += `<text x="${L - 8}" y="${y + 15}" text-anchor="end" font-size="11" fill="${th.text}">${esc(r.name.length > mc ? r.name.slice(0, mc - 1) + '…' : r.name)}</text>`;
    r.vals.forEach((v, i) => {
      const a = Math.min(Math.abs(v) / mx, 1), col = v < 0 ? '#ef4444' : '#2563eb';
      s += `<rect x="${L + cw * i + 1}" y="${y + 1}" width="${Math.max(cw - 2, 1)}" height="${cellH - 2}" rx="2" fill="${v === 0 ? th.grid : col}" fill-opacity="${v === 0 ? .5 : (0.12 + 0.88 * a).toFixed(2)}" data-tip="${esc('<b>' + r.name + '</b><br>' + cols[i] + ': <b>' + F.money(v) + '</b>')}"/>`;
    });
  });
  return s + '</svg>';
}

function spark(vals, color) {
  const v = (vals || []).filter(x => x != null);
  if (v.length < 2) return '';
  const w = 84, h = 26, mn = Math.min(...v), mx = Math.max(...v), rng = mx - mn || 1;
  const pts = (vals || []).map((x, i) => x == null ? null : [(i / (vals.length - 1) * (w - 4) + 2).toFixed(1), (h - 3 - (x - mn) / rng * (h - 6)).toFixed(1)]).filter(Boolean);
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts.map(p => p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts[pts.length - 1][0]}" cy="${pts[pts.length - 1][1]}" r="2.2" fill="${color}"/></svg>`;
}

/* chart cards + registry */
function cc(id, title, sub, extra) {
  return `<div class="card ${extra || ''}"><div class="card-h"><div><h3>${esc(title)}</h3>${sub ? `<div class="sub">${esc(sub)}</div>` : ''}</div><button class="ghost sm" data-png="${id}" title="Download this chart as PNG">PNG</button></div><div class="cbody" id="${id}"></div></div>`;
}
function reg(id, fn) { S.charts[id] = fn; }
function drawAll() {
  Object.keys(S.charts).forEach(id => { const el = document.getElementById(id); if (el) { try { el.innerHTML = S.charts[id](el); } catch (e) { console.error('chart', id, e); el.innerHTML = '<div class="empty">Chart error: ' + esc(e.message) + '</div>'; } } });
}
function exportPNG(id, quiet) {
  const el = document.getElementById(id); const svg = el && el.querySelector('svg'); if (!svg) { if (!quiet) toast('Nothing to export', true); return; }
  const th = T(), w = +svg.getAttribute('width'), h = +svg.getAttribute('height');
  const c = svg.cloneNode(true); c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect'); bg.setAttribute('width', w); bg.setAttribute('height', h); bg.setAttribute('fill', th.bg); c.insertBefore(bg, c.firstChild);
  c.querySelectorAll('rect[fill=transparent]').forEach(r => r.remove());
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(c)], {type: 'image/svg+xml;charset=utf-8'}));
  const img = new Image();
  img.onload = () => {
    const cv = document.createElement('canvas'); cv.width = w * 2; cv.height = h * 2; const x = cv.getContext('2d'); x.scale(2, 2); x.drawImage(img, 0, 0);
    cv.toBlob(b => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); const t = el.closest('.card').querySelector('h3').textContent; a.download = t.replace(/[^A-Za-z0-9]+/g, '_') + '.png'; a.click(); URL.revokeObjectURL(url); }, 'image/png');
  };
  img.onerror = () => toast('PNG export failed', true);
  img.src = url;
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-png]'); if (b) { exportPNG(b.getAttribute('data-png')); return; }
  const d = e.target.closest('[data-drill]'); if (d) { drillTo(d.getAttribute('data-drill')); }
});

/* ===== tables ===== */
function dataTable(host, cfg) {
  const st = {sort: cfg.sort || null, dir: cfg.dir || 'desc', q: '', page: 0};
  const ps = cfg.pageSize || 0, cols = cfg.cols;
  host.innerHTML = (cfg.search ? `<div class="tools"><input type="text" placeholder="${esc(cfg.placeholder || 'Search…')}" data-s style="width:240px"><span class="muted" data-cnt></span>${cfg.toolsHtml || ''}</div>` : '') + '<div data-tw></div><div data-pg></div>';
  const tw = $('[data-tw]', host), pg = $('[data-pg]', host), cnt = $('[data-cnt]', host);
  let shown = [];
  function view() {
    let rows = cfg.rows;
    if (st.q && cfg.search) { const q = st.q.toLowerCase(); rows = rows.filter(r => cfg.search(r).toLowerCase().indexOf(q) >= 0); }
    if (st.sort) {
      const c = cols.find(c => c.k === st.sort), f = c && (c.sv || (r => r[c.k]));
      if (f) rows = rows.slice().sort((a, b) => { let x = f(a), y = f(b); if (x == null) x = typeof y === 'string' ? '' : -Infinity; if (y == null) y = typeof x === 'string' ? '' : -Infinity; if (typeof x === 'string') { x = x.toLowerCase(); y = String(y).toLowerCase(); } return (x > y ? 1 : x < y ? -1 : 0) * (st.dir === 'asc' ? 1 : -1); });
    }
    return rows;
  }
  function draw() {
    const rows = view(), total = rows.length; shown = ps ? rows.slice(st.page * ps, (st.page + 1) * ps) : rows;
    if (cnt) cnt.textContent = nf0.format(total) + ' rows';
    let h = `<div class="tbl-wrap" style="max-height:${cfg.maxh || '62vh'}"><table class="tbl"><thead><tr>` + cols.map(c => `<th class="${c.num ? 'num' : ''} ${(c.sv || c.sortable) ? 'sortable' : ''}" data-k="${c.k}">${c.label}${st.sort === c.k ? (st.dir === 'asc' ? ' &#9650;' : ' &#9660;') : ''}</th>`).join('') + '</tr></thead><tbody>';
    if (!shown.length) h += `<tr><td colspan="${cols.length}" class="empty">${esc(cfg.empty || 'No matching rows')}</td></tr>`;
    shown.forEach((r, i) => {
      h += `<tr data-i="${i}" ${cfg.onRow ? 'style="cursor:pointer"' : ''}>` + cols.map(c => `<td class="${c.num ? 'num' : ''} ${c.wrap ? 'wrap' : ''} ${c.cls ? c.cls(r) : ''}" ${c.tip ? `data-tip="${esc(c.tip(r))}"` : ''}>${c.r ? c.r(r) : esc(r[c.k])}</td>`).join('') + '</tr>';
    });
    if (cfg.totals && total) { const t = cfg.totals(rows); h += '<tr class="tfoot">' + cols.map((c, i) => `<td class="${c.num ? 'num' : ''}">${t[i] == null ? '' : t[i]}</td>`).join('') + '</tr>'; }
    tw.innerHTML = h + '</tbody></table></div>';
    if (ps) { const pages = Math.max(1, Math.ceil(total / ps)); pg.innerHTML = `<div class="pager"><button class="sm" data-pp ${st.page <= 0 ? 'disabled' : ''}>&lsaquo; Prev</button><span>Page ${st.page + 1} of ${pages}</span><button class="sm" data-pn ${st.page >= pages - 1 ? 'disabled' : ''}>Next &rsaquo;</button></div>`; }
  }
  host.addEventListener('click', e => {
    const th = e.target.closest('th[data-k]'), tc = th && cols.find(c => c.k === th.dataset.k);
    if (th && tc && (tc.sv || tc.sortable)) {
      const k = th.dataset.k; if (st.sort === k) st.dir = st.dir === 'asc' ? 'desc' : 'asc'; else { st.sort = k; st.dir = 'desc'; } st.page = 0; draw(); return;
    }
    if (e.target.closest('[data-pp]')) { st.page = Math.max(0, st.page - 1); draw(); return; }
    if (e.target.closest('[data-pn]')) { st.page++; draw(); return; }
    const tr = e.target.closest('tr[data-i]'); if (tr && cfg.onRow && !e.target.closest('[data-drill]')) cfg.onRow(shown[+tr.dataset.i]);
  });
  const si = $('[data-s]', host); if (si) si.addEventListener('input', debounce(() => { st.q = si.value; st.page = 0; draw(); }, 150));
  draw();
}

function treeTable(host, cfg) {
  const key = cfg.key, rows = cfg.rows;
  const kids = new Set(rows.map(r => r.parent).filter(Boolean));
  if (!S.collapsed[key]) { S.collapsed[key] = new Set(rows.filter(r => kids.has(r.id) && r.level >= 1).map(r => r.id)); }
  const coll = S.collapsed[key], byId = {}; rows.forEach(r => byId[r.id] = r);
  function visible(r) { let p = r.parent; while (p) { if (coll.has(p)) return false; p = byId[p] ? byId[p].parent : null; } return true; }
  function draw() {
    let h = '<div class="tbl-wrap" style="max-height:' + (cfg.maxh || '70vh') + '"><table class="tbl"><thead><tr>' + cfg.cols.map((c, i) => `<th class="${i === 0 ? 'sticky' : (c.num ? 'num' : '')}">${c.label}</th>`).join('') + '</tr></thead><tbody>';
    rows.forEach(r => {
      if (!visible(r)) return;
      h += `<tr class="r-${r.kind}">` + cfg.cols.map((c, i) => {
        if (i === 0) {
          const hasK = kids.has(r.id), car = hasK ? `<span class="caret" data-t="${esc(r.id)}">${coll.has(r.id) ? '&#9656;' : '&#9662;'}</span>` : '<span class="caret"></span>';
          const lab = r.drill ? `<span class="lnk" data-drill="${esc(r.drill)}" title="Show transactions in the General Ledger">${esc(r.label)}</span>` : esc(r.label);
          return `<td class="sticky" style="padding-left:${10 + r.level * 16}px">${car}${lab}</td>`;
        }
        return `<td class="num">${c.r(r)}</td>`;
      }).join('') + '</tr>';
    });
    host.innerHTML = h + '</tbody></table></div>';
  }
  host.addEventListener('click', e => { const t = e.target.closest('[data-t]'); if (!t) return; const id = t.dataset.t; if (coll.has(id)) coll.delete(id); else coll.add(id); draw(); });
  host._expand = () => { coll.clear(); draw(); };
  host._collapse = () => { rows.forEach(r => { if (kids.has(r.id) && r.level >= 1) coll.add(r.id); }); draw(); };
  draw();
}

/* ===== shared page bits ===== */
const empty = t => `<div class="card"><div class="empty">${t}</div></div>`;
function periodStrip(p) {
  S.lastPeriod = p;
  const c = p.cmp;
  let cm = c.mode === 'none' ? 'None' : ((c.ok_pl || c.ok_bs) ? `<b>${esc(c.name)}</b>: ${esc(c.label)}` : `<span class="neg">unavailable</span> (${esc(c.reason || 'insufficient data')})`);
  return `<div class="strip"><span>Period: <b>${esc(p.label)}</b> (${p.months.length} month${p.months.length > 1 ? 's' : ''})</span><span>Comparison: ${cm}</span>${p.acct ? `<span>Account filter: <b>${esc(labelForToken(p.acct))}</b></span>` : ''}${p.pl_partial ? '<span class="neg">P&amp;L covers only part of this period</span>' : ''}</div>`;
}
function labelForToken(t) { const o = S.meta.account_options.find(o => o.v === t); return o ? o.l : t; }
function kpiCard(k) {
  const col = k.fav === 'bad' ? COL.loss : (k.fav === 'good' ? COL.ni : COL.rev);
  const na = k.value == null;
  return `<div class="kpi" ${k.note ? `data-tip="${esc(k.note)}"` : ''}><div class="kpi-l">${esc(k.label)}</div><div class="kpi-v">${na ? '<span class="muted">N/A</span>' : fmtBy(k.fmt, k.value)}</div><div class="kpi-d">${chip(k, k.fmt)}<span class="muted">${k.prev != null ? 'vs ' + fmtBy(k.fmt, k.prev) : ''}</span></div><div class="spark">${spark(k.spark, col)}</div></div>`;
}
const selIdx = (months, sel) => { if (!sel || !sel.length) return null; const a = months.indexOf(sel[0]), b = months.indexOf(sel[sel.length - 1]); return a < 0 ? null : [a, b]; };
function insightRow(i) {
  const modmap = {pl: 'pl', bs: 'bs', variance: 'variance', ratios: 'ratios', recon: 'recon'};
  return `<div class="ins"><span class="chip ${i.sev}">${i.sev.toUpperCase()}</span><div style="flex:1"><h4>${esc(i.title)}</h4><p>${esc(i.detail)}</p></div><button class="sm ghost" onclick="go('${modmap[i.module] || 'insights'}')">View</button></div>`;
}

/* ===== pages ===== */
const PAGES = {};
PAGES.overview = async ctx => {
  const d = await api('/api/overview');
  const tr = d.trend, sel = selIdx(tr.months, d.sel_months), labs = tr.months.map(ymShort);
  if (!ctx.set(periodStrip(d.period) + `<div class="kpis">${d.kpis.map(kpiCard).join('')}</div>
    <div class="grid g2">${cc('c-rev', 'Revenue and net profit', 'Monthly; the selected period is highlighted')}${cc('c-mar', 'Profitability margins', 'Monthly EBITDA and net margin (axis capped at ±100%)')}</div>
    <div class="grid g2">${cc('c-mix', 'Expense composition', 'Selected period; click a slice to see transactions')}${cc('c-bsm', 'Funding of assets', 'Month-end liabilities + equity (bars) equal total assets (line)')}</div>
    <div class="grid g2">${cc('c-cash', 'Cash and working capital', 'Month-end balances')}<div class="card"><div class="card-h"><div><h3>Automated insights</h3><div class="sub">Rule-based, from actual figures</div></div><button class="sm" onclick="go('insights')">All insights</button></div>${d.top_insights.length ? d.top_insights.map(insightRow).join('') : '<div class="empty">No alerts for this period.</div>'}</div></div>`)) return;
  reg('c-rev', el => drawCombo(el, {labels: labs, sel, series: [{name: 'Revenue', type: 'bar', data: tr.revenue, color: COL.rev}, {name: 'Net profit', type: 'line', data: tr.net_income, color: COL.ni}]}));
  reg('c-mar', el => drawCombo(el, {labels: labs, sel, clip: [-1, 1], fmt: v => F.pct(v, 0), tfmt: v => F.pct(v, 1), series: [{name: 'EBITDA margin', type: 'line', data: tr.em, color: COL.ebitda}, {name: 'Net margin', type: 'line', data: tr.nm, color: COL.ni}]}));
  reg('c-mix', el => { const m = d.expense_mix.filter(r => r.value > 0), top = m.slice(0, 8), rest = m.slice(8).reduce((a, b) => a + b.value, 0); const items = top.map(r => ({name: r.name, value: r.value, drill: r.drill})); if (rest > 0) items.push({name: 'All other', value: rest, color: '#94a3b8'}); return drawDonut(el, {items, center: 'expenses'}); });
  reg('c-bsm', el => drawCombo(el, {labels: labs, sel, stacked: true, series: [{name: 'Liabilities', type: 'bar', data: tr.liabilities.map(v => v == null ? null : v), color: COL.liab}, {name: 'Equity', type: 'bar', data: tr.equity, color: COL.equity}, {name: 'Total assets', type: 'line', data: tr.assets, color: COL.assets}]}));
  reg('c-cash', el => drawCombo(el, {labels: labs, sel, series: [{name: 'Cash & bank', type: 'bar', data: tr.cash, color: COL.cash}, {name: 'Working capital', type: 'line', data: tr.working_capital, color: COL.wc}]}));
};

PAGES.pl = async ctx => {
  const d = await api('/api/pl'), t = d.table;
  if (!t.available) { ctx.set(empty('No Profit &amp; Loss file is loaded.')); return; }
  const tr = d.trend, sel = selIdx(tr.months, d.period.months), labs = tr.months.map(ymShort);
  const revRows = t.rows.filter(r => r.kind === 'section' && r.sec === 'income');
  const revM = t.months.map((_, i) => revRows.reduce((a, r) => a + r.vals[i], 0));
  const cmpOk = t.cmp_ok;
  if (!ctx.set(periodStrip(d.period) + `<div class="grid g2">${cc('c-pt', 'Revenue, gross profit, EBITDA and net profit', 'Monthly trend, selected period highlighted')}${cc('c-tm', 'Expense composition', 'Size = spend in the selected period; click to drill into the ledger')}</div>
    <div class="grid g2">${cc('c-pm', 'Margins', 'Monthly EBITDA and net margin (axis capped at ±100%)')}${cc('c-hm', 'Expense heat map', 'Largest accounts by month; darker = higher spend')}</div>
    <div class="card"><div class="card-h"><div><h3>Profit &amp; Loss</h3><div class="sub">${t.filtered ? 'Filtered to the selected account/category. ' : ''}Click an account name to see its ledger transactions. Variance is vs ${cmpOk ? esc(d.period.cmp.label) : 'n/a (comparison unavailable)'}</div></div></div>
    <div class="tools"><div class="seg" id="plv"><span data-v="amt" class="${S.plView === 'amt' ? 'on' : ''}">Amounts</span><span data-v="cs" class="${S.plView === 'cs' ? 'on' : ''}">Common-size (% of revenue)</span></div><button class="sm" id="plx">Expand all</button><button class="sm" id="plc">Collapse groups</button></div><div id="pltbl"></div></div>`)) return;
  reg('c-pt', el => drawCombo(el, {labels: labs, sel, series: [{name: 'Revenue', type: 'bar', data: tr.revenue, color: COL.rev}, {name: 'Gross profit', type: 'line', data: tr.gross_profit, color: COL.gp}, {name: 'EBITDA', type: 'line', data: tr.ebitda, color: COL.ebitda}, {name: 'Net profit', type: 'line', data: tr.net_income, color: COL.ni}]}));
  reg('c-tm', el => drawTreemap(el, {items: d.mix.map(r => ({name: r.name, value: r.value, prev: r.prev, children: r.children, drill: r.drill}))}));
  reg('c-pm', el => drawCombo(el, {labels: labs, sel, clip: [-1, 1], fmt: v => F.pct(v, 0), tfmt: v => F.pct(v, 1), series: [{name: 'Gross margin', type: 'line', data: tr.gm, color: COL.gp}, {name: 'EBITDA margin', type: 'line', data: tr.em, color: COL.ebitda}, {name: 'Net margin', type: 'line', data: tr.nm, color: COL.ni}]}));
  reg('c-hm', el => { const lv = t.rows.filter(r => r.kind === 'leaf' && r.sec !== 'income' && r.sec !== 'othinc').sort((a, b) => Math.abs(b.total) - Math.abs(a.total)).slice(0, 14); return drawHeatmap(el, {rows: lv.map(r => ({name: r.label, vals: r.vals})), cols: t.month_labels.map(l => l.replace(/ 20/, " '"))}); });
  const cols = [{label: 'Account'}].concat(t.months.map((m, i) => ({label: t.month_labels[i], num: 1, r: r => { const v = r.vals[i]; if (S.plView === 'amt') return moneyCell(v); const den = revM[i]; return den ? `<span class="${v < 0 ? 'neg' : ''}">${F.pct(v / den)}</span>` : '<span class="muted">-</span>'; }})));
  cols.push({label: 'Total', num: 1, r: r => `<b>${S.plView === 'amt' ? moneyCell(r.total) : (t.revenue ? F.pct(r.total / t.revenue) : '-')}</b>`});
  if (cmpOk) { cols.push({label: 'Comparison', num: 1, r: r => moneyCell(r.prev)}); cols.push({label: 'Change', num: 1, r: r => moneyCell(r.abs)}); cols.push({label: 'Change %', num: 1, r: r => chip(r)}); }
  cols.push({label: '% of revenue', num: 1, r: r => r.pct_rev == null ? '<span class="muted">N/A</span>' : F.pct(r.pct_rev)});
  const host = $('#pltbl'); treeTable(host, {key: 'pl', rows: t.rows, cols});
  $('#plx').onclick = () => host._expand(); $('#plc').onclick = () => host._collapse();
  $$('#plv span').forEach(s => s.onclick = () => { S.plView = s.dataset.v; $$('#plv span').forEach(x => x.classList.toggle('on', x === s)); treeTable(host, {key: 'pl', rows: t.rows, cols}); });
};

PAGES.bs = async ctx => {
  const d = await api('/api/bs'), t = d.table;
  if (!t.available) { ctx.set(empty('No Balance Sheet file is loaded.')); return; }
  if (t.empty) { ctx.set(periodStrip(d.period) + empty('The selected period has no balance sheet months.')); return; }
  const tr = t.trend, sel = selIdx(tr.months, t.months), labs = tr.months.map(ymShort), cmpOk = t.cmp_ok;
  const eqLast = t.equation.filter(e => t.months.includes(e.month)).slice(-1)[0];
  const allOk = t.equation.every(e => e.ok);
  if (!ctx.set(periodStrip(d.period) + `<div class="note ${allOk ? 'good' : 'bad'}"><span>Accounting equation (Assets = Liabilities + Equity): <b>${allOk ? 'holds in all ' + t.equation.length + ' month-end balance sheets' : t.equation.filter(e => !e.ok).length + ' month(s) do not balance - see table below'}</b>. Balances shown at ${esc(ymLabel(t.end))}${cmpOk ? ', compared with ' + esc(ymLabel(t.cmp_end)) : ''}.</span></div>
    <div class="grid g2" style="margin-top:12px">${cc('b-st', 'Assets vs liabilities + equity', 'Stacked liabilities and equity reconcile to the total assets line')}${cc('b-cw', 'Cash and working capital', 'Month-end balances')}</div>
    <div class="grid g2">${cc('b-mix', 'Asset composition', 'At ' + ymLabel(t.end))}${cc('b-rc', 'Receivables trend', tr.receivables ? 'Month-end receivable accounts' : 'No receivable accounts identified')}</div>
    <div class="card"><div class="card-h"><div><h3>Balance sheet</h3><div class="sub">${t.filtered ? 'Filtered to the selected account/category. ' : ''}Click an account name to see its ledger transactions</div></div></div>
    <div class="tools"><div class="seg" id="bsv"><span data-v="bal" class="${S.bsView === 'bal' ? 'on' : ''}">Month-end balances</span><span data-v="mov" class="${S.bsView === 'mov' ? 'on' : ''}">Monthly movements</span></div><button class="sm" id="bsx">Expand all</button><button class="sm" id="bsc">Collapse groups</button></div><div id="bstbl"></div></div>
    <div class="sec-t">Accounting equation by month</div><div class="card" id="bseq"></div>`)) return;
  reg('b-st', el => drawCombo(el, {labels: labs, sel, stacked: true, series: [{name: 'Liabilities', type: 'bar', data: tr.liabilities, color: COL.liab}, {name: 'Equity', type: 'bar', data: tr.equity, color: COL.equity}, {name: 'Total assets', type: 'line', data: tr.assets, color: COL.assets}]}));
  reg('b-cw', el => drawCombo(el, {labels: labs, sel, series: [{name: 'Cash & bank', type: 'bar', data: tr.cash || tr.months.map(() => null), color: COL.cash}, {name: 'Working capital', type: 'line', data: tr.working_capital, color: COL.wc}]}));
  reg('b-mix', el => drawDonut(el, {items: t.rows.filter(r => r.cls === 'asset' && r.level === 1).map(r => ({name: r.label, value: r.cur, drill: r.drill})), center: 'assets'}));
  reg('b-rc', el => tr.receivables ? drawCombo(el, {labels: labs, sel, series: [{name: 'Receivables', type: 'bar', data: tr.receivables, color: COL.gp}]}) : noData(400, 200, 'No receivable accounts in the balance sheet'));
  const cols = [{label: 'Account'}].concat(t.months.map((m, i) => ({label: t.month_labels[i], num: 1, r: r => S.bsView === 'bal' ? moneyCell(r.bal[i]) : moneyCell(r.mov[i])})));
  if (cmpOk) { cols.push({label: 'Comparison', num: 1, r: r => moneyCell(r.prev)}); cols.push({label: 'Change', num: 1, r: r => moneyCell(r.abs)}); cols.push({label: 'Change %', num: 1, r: r => chip(r)}); }
  const host = $('#bstbl'); treeTable(host, {key: 'bs', rows: t.rows, cols});
  $('#bsx').onclick = () => host._expand(); $('#bsc').onclick = () => host._collapse();
  $$('#bsv span').forEach(s => s.onclick = () => { S.bsView = s.dataset.v; $$('#bsv span').forEach(x => x.classList.toggle('on', x === s)); treeTable(host, {key: 'bs', rows: t.rows, cols}); });
  dataTable($('#bseq'), {rows: t.equation, sort: null, maxh: '40vh', cols: [{k: 'label', label: 'Month-end'}, {k: 'assets', label: 'Assets', num: 1, r: r => F.money2(r.assets)}, {k: 'liabilities', label: 'Liabilities', num: 1, r: r => F.money2(r.liabilities)}, {k: 'equity', label: 'Equity', num: 1, r: r => F.money2(r.equity)}, {k: 'le', label: 'L + E', num: 1, r: r => F.money2(r.le)}, {k: 'diff', label: 'Difference', num: 1, r: r => F.money2(Math.abs(r.diff) < 0.005 ? 0 : r.diff)}, {k: 'ok', label: 'Status', r: r => `<span class="chip ${r.ok ? 'ok' : 'fail'}">${r.ok ? 'Balanced' : 'Unreconciled'}</span>`}]});
};

const glQ = () => { const g = S.gl; return {text: g.text, types: g.types.join('|'), amt_min: g.amin, amt_max: g.amax, month_end: g.me ? '1' : '', cls: g.cls}; };
PAGES.gl = async ctx => {
  if (!S.meta.has_gl) { ctx.set(empty('No General Ledger file is loaded.')); return; }
  const g = S.gl, sm = await api('/api/gl_summary', glQ());
  const nUn = sm.n_unusual, nDup = sm.n_dups;
  const kp = (l, v, n) => `<div class="kpi"><div class="kpi-l">${l}</div><div class="kpi-v">${v}</div><div class="kpi-d muted">${n || ''}</div></div>`;
  const typePills = sm.types_all.map(t => `<span class="pill ${g.types.includes(t) ? 'on' : ''}" data-ty="${esc(t)}">${esc(t)}</span>`).join('');
  if (!ctx.set(periodStrip(sm.period) + (sm.outside ? `<div class="note info"><span>${nf0.format(sm.outside)} ledger transactions fall outside the statement period and are excluded (ledger range ${esc(sm.gl_range[0])} to ${esc(sm.gl_range[1])}).</span></div><div style="height:10px"></div>` : '') +
    `<div class="kpis">${kp('Transactions', nf0.format(sm.count), 'in selected period & filters')}${kp('Total debits', F.money(sm.debit), 'account-natural sign')}${kp('Total credits', F.money(sm.credit))}${kp('Debits minus credits', F.money(sm.debit - sm.credit), Math.abs(sm.debit - sm.credit) < 0.01 ? 'ledger is balanced' : 'difference - review filters / data')}${kp('Unusual transactions', nf0.format(nUn), 'P&amp;L accounts, |z| ≥ 3')}${kp('Possible duplicates', nf0.format(nDup), 'same date, account, amount, payee')}</div>
    <div class="card" style="margin-bottom:14px"><div class="tools"><input type="text" id="gl-q" placeholder="Search payee, memo, account, number…" value="${esc(g.text)}" style="width:280px"><label>Amount ≥ <input type="number" id="gl-a" value="${esc(g.amin)}" placeholder="min"></label><label>≤ <input type="number" id="gl-b" value="${esc(g.amax)}" placeholder="max"></label>
    <div class="seg" id="gl-c"><span data-c="" class="${g.cls === '' ? 'on' : ''}">All accounts</span><span data-c="pl" class="${g.cls === 'pl' ? 'on' : ''}">P&amp;L accounts</span><span data-c="bs" class="${g.cls === 'bs' ? 'on' : ''}">Balance sheet</span></div>
    <label><input type="checkbox" id="gl-m" ${g.me ? 'checked' : ''}> Month-end (last 3 days)</label><button class="sm" id="gl-x">Clear filters</button></div><div class="tools" style="padding-top:0"><span class="muted">Type:</span><div class="pills">${typePills}</div></div></div>
    <div class="grid g2">${cc('g-m', 'Monthly ledger activity', 'Debits vs credits in the selected period')}${cc('g-t', 'Activity by transaction type', 'Total absolute amount (debits + credits)')}</div>
    <div class="card"><div class="tabs" id="gl-tabs">${[['txns', 'Transactions'], ['accounts', 'Account movements'], ['largest', 'Largest'], ['unusual', 'Unusual (' + nUn + ')'], ['dups', 'Possible duplicates (' + nDup + ')'], ['me', 'Month-end journals'], ['trend', 'Account trend']].map(([k, l]) => `<div data-tab="${k}" class="${g.tab === k ? 'on' : ''}">${l}</div>`).join('')}</div><div id="gl-body"></div></div>`)) return;
  reg('g-m', el => drawCombo(el, {labels: sm.monthly.map(m => ymShort(m.month)), series: [{name: 'Debits', type: 'bar', data: sm.monthly.map(m => m.debit), color: COL.debit}, {name: 'Credits', type: 'bar', data: sm.monthly.map(m => m.credit), color: COL.credit}]}));
  reg('g-t', el => drawHBar(el, {items: sm.by_type.map(t => ({label: t.type + ' (' + nf0.format(t.count) + ')', value: t.debit + t.credit, tip: t.type + '<br>Debits: ' + F.money(t.debit) + '<br>Credits: ' + F.money(t.credit) + '<br>Transactions: ' + nf0.format(t.count)})).sort((a, b) => b.value - a.value), color: COL.rev}));
  const bind = (id, ev, fn) => { const e = document.getElementById(id); if (e) e.addEventListener(ev, fn); };
  const upd = (patch, focus) => { Object.assign(g, patch, {page: 0}); S.focus = focus || null; renderPage(true); };
  bind('gl-q', 'input', debounce(e => upd({text: e.target.value}, 'gl-q'), 350));
  bind('gl-a', 'input', debounce(e => upd({amin: e.target.value}, 'gl-a'), 450));
  bind('gl-b', 'input', debounce(e => upd({amax: e.target.value}, 'gl-b'), 450));
  bind('gl-m', 'change', e => upd({me: e.target.checked}));
  bind('gl-x', 'click', () => upd({text: '', types: [], cls: '', amin: '', amax: '', me: false}));
  $$('#gl-c span').forEach(s => s.onclick = () => upd({cls: s.dataset.c}));
  $$('.pill[data-ty]').forEach(p => p.onclick = () => { const t = p.dataset.ty, i = g.types.indexOf(t); const n = g.types.slice(); if (i >= 0) n.splice(i, 1); else n.push(t); upd({types: n}); });
  const body = $('#gl-body');
  async function tab() {
    $$('#gl-tabs div').forEach(x => x.classList.toggle('on', x.dataset.tab === g.tab));
    const k = g.tab;
    if (k === 'txns') {
      body.innerHTML = '<div class="empty"><span class="spin"></span></div>';
      const r = await api('/api/gl_rows', Object.assign(glQ(), {sort: g.sort, dir: g.dir, page: g.page, size: g.size}));
      const pages = Math.max(1, Math.ceil(r.total / r.size));
      const th = (k_, l, num) => `<th class="sortable ${num ? 'num' : ''}" data-s="${k_}">${l}${g.sort === k_ ? (g.dir === 'asc' ? ' &#9650;' : ' &#9660;') : ''}</th>`;
      body.innerHTML = `<div class="tools"><span class="muted">${nf0.format(r.total)} transactions &middot; debits ${F.money(r.sum_debit)} &middot; credits ${F.money(r.sum_credit)} &middot; difference ${F.money(r.sum_debit - r.sum_credit)}</span></div><div class="tbl-wrap" style="max-height:60vh"><table class="tbl"><thead><tr>${th('date', 'Date')}${th('acct', 'Account')}${th('type', 'Type')}${th('name', 'Payee / name')}${th('desc', 'Description')}${th('split', 'Split')}${th('debit', 'Debit', 1)}${th('credit', 'Credit', 1)}</tr></thead><tbody>${r.rows.map(x => `<tr><td>${esc(x.date)}</td><td>${esc(x.acct)}</td><td>${esc(x.type)}</td><td>${esc(x.name)}</td><td data-tip="${esc(x.desc)}">${esc(x.desc.slice(0, 70))}</td><td>${esc(x.split)}</td><td class="num">${x.debit ? F.money2(x.debit) : ''}</td><td class="num">${x.credit ? F.money2(x.credit) : ''}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">No transactions match the filters</td></tr>'}</tbody></table></div><div class="pager"><button class="sm" id="pp" ${g.page <= 0 ? 'disabled' : ''}>&lsaquo; Prev</button><span>Page ${g.page + 1} of ${pages}</span><button class="sm" id="pn" ${g.page >= pages - 1 ? 'disabled' : ''}>Next &rsaquo;</button><span style="flex:1"></span>Rows: <select id="psz">${[50, 100, 250, 500].map(n => `<option ${n === g.size ? 'selected' : ''}>${n}</option>`).join('')}</select></div>`;
      $$('th[data-s]', body).forEach(h => h.onclick = () => { const k2 = h.dataset.s; if (g.sort === k2) g.dir = g.dir === 'asc' ? 'desc' : 'asc'; else { g.sort = k2; g.dir = k2 === 'date' || k2 === 'acct' || k2 === 'type' || k2 === 'name' || k2 === 'desc' || k2 === 'split' ? 'asc' : 'desc'; } g.page = 0; tab(); });
      $('#pp', body).onclick = () => { g.page--; tab(); }; $('#pn', body).onclick = () => { g.page++; tab(); }; $('#psz', body).onchange = e => { g.size = +e.target.value; g.page = 0; tab(); };
    } else if (k === 'accounts') {
      dataTable(body, {rows: sm.accounts, sort: 'debit', search: r => r.acct + ' ' + r.cls, placeholder: 'Search accounts…', pageSize: 100,
        onRow: r => drillTo('acct:' + r.acct),
        cols: [{k: 'acct', label: 'Account', sv: r => r.acct, r: r => `<span class="lnk">${esc(r.acct)}</span>`}, {k: 'cls', label: 'Class', sv: r => r.cls}, {k: 'count', label: 'Txns', num: 1, sv: r => r.count, r: r => nf0.format(r.count)}, {k: 'opening', label: 'Opening', num: 1, sv: r => r.opening, r: r => moneyCell(r.opening)}, {k: 'debit', label: 'Debits', num: 1, sv: r => r.debit, r: r => moneyCell(r.debit)}, {k: 'credit', label: 'Credits', num: 1, sv: r => r.credit, r: r => moneyCell(r.credit)}, {k: 'net', label: 'Net movement', num: 1, sv: r => r.net, r: r => moneyCell(r.net)}, {k: 'closing', label: 'Closing', num: 1, sv: r => r.closing, r: r => r.closing == null ? '<span class="muted" title="Shown only when no transaction filters are applied">n/a</span>' : moneyCell(r.closing)}]});
    } else if (k === 'largest') {
      dataTable(body, {rows: sm.largest, sort: 'amt', cols: [{k: 'date', label: 'Date', sv: r => r.date}, {k: 'acct', label: 'Account', sv: r => r.acct}, {k: 'type', label: 'Type'}, {k: 'name', label: 'Payee'}, {k: 'desc', label: 'Description', r: r => esc(r.desc.slice(0, 80)), tip: r => r.desc}, {k: 'amt', label: 'Amount', num: 1, sv: r => Math.abs(r.amount), r: r => moneyCell(r.amount)}]});
    } else if (k === 'unusual') {
      body.innerHTML = '<div class="pad muted">Transactions in P&amp;L accounts whose amount is at least 3 standard deviations from that account\'s average (accounts with 8+ transactions, amount ≥ the materiality threshold).</div><div id="ut"></div>';
      dataTable($('#ut', body), {rows: sm.unusual, sort: 'z', empty: 'No unusual transactions found', cols: [{k: 'date', label: 'Date', sv: r => r.date}, {k: 'acct', label: 'Account', sv: r => r.acct}, {k: 'name', label: 'Payee'}, {k: 'desc', label: 'Description', r: r => esc(r.desc.slice(0, 70)), tip: r => r.desc}, {k: 'amount', label: 'Amount', num: 1, sv: r => r.amount, r: r => moneyCell(r.amount)}, {k: 'mean', label: 'Account average', num: 1, sv: r => r.mean, r: r => moneyCell(r.mean)}, {k: 'z', label: 'z-score', num: 1, sv: r => Math.abs(r.z), r: r => r.z.toFixed(1)}]});
    } else if (k === 'dups') {
      body.innerHTML = '<div class="pad muted">Groups of 2+ lines in the same account with the same date, amount and payee/description. Review for double-posting; legitimate repeat charges also appear here.</div><div id="dt"></div>';
      dataTable($('#dt', body), {rows: sm.duplicates, sort: 'tot', empty: 'No possible duplicates found', cols: [{k: 'date', label: 'Date', sv: r => r.date}, {k: 'acct', label: 'Account', sv: r => r.acct}, {k: 'name', label: 'Payee / description'}, {k: 'type', label: 'Type'}, {k: 'count', label: 'Count', num: 1, sv: r => r.count}, {k: 'amount', label: 'Each', num: 1, sv: r => r.amount, r: r => moneyCell(r.amount)}, {k: 'tot', label: 'Group total', num: 1, sv: r => Math.abs(r.total), r: r => moneyCell(r.total)}]});
    } else if (k === 'me') {
      body.innerHTML = '<div class="pad muted">Journal entries dated in the last 3 days of each month (typical closing / adjusting entries).</div><div id="mt"></div>';
      dataTable($('#mt', body), {rows: sm.month_end, sort: null, empty: 'No month-end journal entries in this period', cols: [{k: 'label', label: 'Month'}, {k: 'count', label: 'Entries', num: 1}, {k: 'debit', label: 'Debits', num: 1, r: r => moneyCell(r.debit)}, {k: 'credit', label: 'Credits', num: 1, r: r => moneyCell(r.credit)}]});
    } else if (k === 'trend') {
      const tk = S.f.acct;
      if (!tk || !tk.startsWith('acct:')) { body.innerHTML = '<div class="empty">Choose a single account in the “Account / category” filter (or click an account in the Account movements tab) to see its monthly balance and movement.</div>'; return; }
      const a = await api('/api/gl_account', {name: tk.slice(5)});
      if (!a.available) { body.innerHTML = '<div class="empty">This account has no ledger section.</div>'; return; }
      body.innerHTML = `<div class="pad"><b>${esc(a.name)}</b> <span class="chip info">${esc(a.cls)}</span></div><div class="grid g2" style="padding:0 12px">${cc('g-ab', 'Month-end balance', 'Opening balance + cumulative activity (ledger)')}${cc('g-am', 'Debits and credits', 'By month')}</div>`;
      reg('g-ab', el => drawCombo(el, {labels: a.series.map(s => ymShort(s.month)), series: [{name: 'Balance', type: 'bar', data: a.series.map(s => s.balance), color: COL.rev, negColor: COL.loss}]}));
      reg('g-am', el => drawCombo(el, {labels: a.series.map(s => ymShort(s.month)), series: [{name: 'Debits', type: 'bar', data: a.series.map(s => s.debit), color: COL.debit}, {name: 'Credits', type: 'bar', data: a.series.map(s => s.credit), color: COL.credit}]}));
      drawAll();
    }
  }
  $$('#gl-tabs div').forEach(x => x.onclick = () => { g.tab = x.dataset.tab; tab(); });
  await tab();
};

PAGES.variance = async ctx => {
  const d = await api('/api/variance');
  if (!d.available) { ctx.set(empty(esc(d.reason || 'Not available'))); return; }
  if (!d.comparable) { ctx.set(periodStrip(d.period) + `<div class="note warn"><span><b>Comparison unavailable.</b> ${esc(d.reason)} Pick a different period or comparison type (the options that are not possible with the loaded data are disabled in the filter bar).</span></div>`); return; }
  const wf = d.waterfall, v = S.var;
  if (!ctx.set(periodStrip(d.period) + `<div class="grid g2">${cc('v-wf', 'Net income bridge', d.period.cmp.label + ' → ' + d.period.label)}<div class="card"><div class="card-h"><div><h3>Period comparison</h3><div class="sub">${esc(d.period.cmp.name)}: ${esc(d.period.label)} vs ${esc(d.period.cmp.label)}</div></div></div><div id="v-sum"></div></div></div>
    <div class="grid g2">${cc('v-pos', 'Top favorable changes', 'Impact on net income, leaf accounts; click a bar for transactions')}${cc('v-neg', 'Top unfavorable changes', 'Impact on net income, leaf accounts; click a bar for transactions')}</div>
    <div class="card"><div class="card-h"><div><h3>Account variance</h3><div class="sub">Material = |change| ≥ threshold and |% change| ≥ threshold (% not meaningful when the base is zero or changes sign)</div></div></div>
    <div class="tools"><label>Materiality $ <input type="number" id="m-a" value="${esc(S.f.mat_abs)}"></label><label>% <input type="number" id="m-p" value="${esc(S.f.mat_pct)}" style="width:80px"></label><label><input type="checkbox" id="v-mat" ${v.material ? 'checked' : ''}> Material only</label><label><input type="checkbox" id="v-leaf" ${v.leaf ? 'checked' : ''}> Accounts only (hide group subtotals)</label></div><div id="v-tbl"></div></div>
    <div class="sec-t">Balance sheet movers</div><div class="card" id="v-bs"></div>`)) return;
  reg('v-wf', el => drawWaterfall(el, {start: wf.start, end: wf.end, steps: wf.steps, startLabel: 'Prior net income', endLabel: 'Current net income'}));
  dataTable($('#v-sum'), {rows: d.summary, cols: [{k: 'label', label: 'Line'}, {k: 'cur', label: 'Current', num: 1, r: r => moneyCell(r.cur)}, {k: 'prev', label: 'Comparison', num: 1, r: r => moneyCell(r.prev)}, {k: 'abs', label: 'Change', num: 1, r: r => moneyCell(r.abs)}, {k: 'pct', label: '%', num: 1, r: r => chip(r)}], maxh: '40vh'});
  reg('v-pos', el => drawHBar(el, {items: d.top_pos.map(r => ({label: r.label, value: Math.abs(r.impact), color: COL.ni, drill: r.drill, tip: `<b>${esc(r.label)}</b><br>${F.money(r.prev)} → ${F.money(r.cur)}<br>Impact on net income: <b>${F.money(r.impact)}</b>`})), empty: 'No favorable movement'}));
  reg('v-neg', el => drawHBar(el, {items: d.top_neg.map(r => ({label: r.label, value: Math.abs(r.impact), color: COL.loss, drill: r.drill, tip: `<b>${esc(r.label)}</b><br>${F.money(r.prev)} → ${F.money(r.cur)}<br>Impact on net income: <b>${F.money(r.impact)}</b>`})), empty: 'No unfavorable movement'}));
  let rows = d.rows; if (v.leaf) rows = rows.filter(r => r.kind === 'leaf'); if (v.material) rows = rows.filter(r => r.material);
  dataTable($('#v-tbl'), {rows, sort: 'impact', search: r => r.label + ' ' + r.path + ' ' + r.sec_label, placeholder: 'Search accounts…', pageSize: 100, maxh: '56vh', empty: 'No accounts match',
    cols: [{k: 'label', label: 'Account', sv: r => r.label, r: r => `<span class="lnk" data-drill="${esc(r.drill)}">${esc(r.label)}</span>`}, {k: 'sec_label', label: 'Type', sv: r => r.sec_label}, {k: 'cur', label: 'Current', num: 1, sv: r => r.cur, r: r => moneyCell(r.cur)}, {k: 'prev', label: 'Comparison', num: 1, sv: r => r.prev, r: r => moneyCell(r.prev)}, {k: 'abs', label: 'Change', num: 1, sv: r => r.abs, r: r => moneyCell(r.abs)}, {k: 'pct', label: '% change', num: 1, sv: r => r.pct, r: r => chip(r)}, {k: 'impact', label: 'Impact on net income', num: 1, sv: r => r.impact, r: r => `<span class="${r.impact < 0 ? 'neg' : ''}">${F.money(r.impact)}</span>`}, {k: 'material', label: 'Material', sv: r => r.material ? 1 : 0, r: r => r.material ? '<span class="chip warn">Material</span>' : ''}]});
  dataTable($('#v-bs'), {rows: d.bs_movers, sort: 'abs', empty: 'No balance sheet comparison available', maxh: '40vh', cols: [{k: 'label', label: 'Account', sv: r => r.label, r: r => `<span class="lnk" data-drill="${esc(r.drill)}">${esc(r.label)}</span>`}, {k: 'cls', label: 'Class', sv: r => r.cls, r: r => ({asset: 'Asset', liab: 'Liability', equity: 'Equity'}[r.cls])}, {k: 'cur', label: 'Current', num: 1, sv: r => r.cur, r: r => moneyCell(r.cur)}, {k: 'prev', label: 'Comparison', num: 1, sv: r => r.prev, r: r => moneyCell(r.prev)}, {k: 'abs', label: 'Change', num: 1, sv: r => Math.abs(r.abs), r: r => moneyCell(r.abs)}, {k: 'pct', label: '%', num: 1, sv: r => r.pct, r: r => chip(r)}]});
  const ma = $('#m-a'), mp = $('#m-p');
  const reMat = debounce(() => { S.f.mat_abs = +ma.value || 0; S.f.mat_pct = +mp.value || 0; renderPage(true); }, 500);
  ma.oninput = reMat; mp.oninput = reMat;
  $('#v-mat').onchange = e => { v.material = e.target.checked; renderPage(true); };
  $('#v-leaf').onchange = e => { v.leaf = e.target.checked; renderPage(true); };
};

PAGES.ratios = async ctx => {
  const d = await api('/api/ratios');
  if (!d.available) { ctx.set(empty('No data for ratios')); return; }
  const groups = ['Profitability', 'Liquidity', 'Leverage', 'Efficiency'], tr = d.trend, labs = tr.months.map(ymShort), sel = selIdx(tr.months, d.period.months);
  const hasPrev = d.rows.some(r => r.prev != null);
  let html = periodStrip(d.period) + `<div class="grid g3">${cc('r-p', 'Margins', 'Monthly (axis capped at ±100%)')}${cc('r-l', 'Liquidity', 'Current and quick ratio')}${cc('r-d', 'Leverage', 'Liabilities to equity')}</div>`;
  groups.forEach(g => {
    html += `<div class="sec-t">${g}</div><div class="card"><div class="tbl-wrap" style="max-height:none"><table class="tbl"><thead><tr><th>Ratio</th><th class="num">Current</th>${hasPrev ? '<th class="num">Comparison</th><th class="num">Change</th>' : ''}<th>Interpretation</th></tr></thead><tbody>` +
      d.rows.filter(r => r.group === g).map(r => `<tr><td data-tip="${esc(r.formula)}"><b>${esc(r.name)}</b></td><td class="num">${r.value == null ? '<span class="muted">N/A</span>' : fmtBy(r.fmt, r.value)}</td>${hasPrev ? `<td class="num">${r.prev == null ? '<span class="muted">N/A</span>' : fmtBy(r.fmt, r.prev)}</td><td class="num">${chip(r, r.fmt)}</td>` : ''}<td class="wrap muted">${esc(r.interp)}</td></tr>`).join('') + '</tbody></table></div></div>';
  });
  html += '<p class="muted" style="margin-top:10px">Hover a ratio name to see its formula. Ratios show N/A when the supporting accounts are not present or the denominator is zero/negative. Return and turnover ratios are annualized using the number of months in the period.</p>';
  if (!ctx.set(html)) return;
  reg('r-p', el => drawCombo(el, {labels: labs, sel, clip: [-1, 1], fmt: v => F.pct(v, 0), tfmt: v => F.pct(v, 1), h: 260, series: [{name: 'Gross', type: 'line', data: tr.gm, color: COL.gp}, {name: 'EBITDA', type: 'line', data: tr.em, color: COL.ebitda}, {name: 'Net', type: 'line', data: tr.nm, color: COL.ni}]}));
  reg('r-l', el => drawCombo(el, {labels: labs, sel, clip: [0, 30], fmt: v => v.toFixed(1) + 'x', tfmt: F.ratio, h: 260, series: [{name: 'Current ratio', type: 'line', data: tr.current_ratio, color: COL.rev}, {name: 'Quick ratio', type: 'line', data: tr.quick_ratio, color: COL.cash}]}));
  reg('r-d', el => drawCombo(el, {labels: labs, sel, clip: [0, 20], fmt: v => v.toFixed(1) + 'x', tfmt: F.ratio, h: 260, series: [{name: 'Liabilities / equity', type: 'bar', data: tr.de, color: COL.liab}]}));
};

PAGES.insights = async ctx => {
  const d = await api('/api/insights');
  const sevs = ['all', 'high', 'medium', 'low', 'info'], cnt = s => d.insights.filter(i => s === 'all' || i.sev === s).length;
  const list = d.insights.filter(i => S.insSev === 'all' || i.sev === S.insSev);
  if (!ctx.set(periodStrip(d.period) + `<div class="card"><div class="tools"><div class="pills">${sevs.map(s => `<span class="pill ${S.insSev === s ? 'on' : ''}" data-sv="${s}">${s === 'all' ? 'All' : s[0].toUpperCase() + s.slice(1)} (${cnt(s)})</span>`).join('')}</div><span class="muted">Generated from rules applied to your actual figures - no external AI service is used.</span></div>${list.length ? list.map(insightRow).join('') : '<div class="empty">No alerts at this severity for the selected period.</div>'}</div>`)) return;
  $$('.pill[data-sv]').forEach(p => p.onclick = () => { S.insSev = p.dataset.sv; renderPage(true); });
};

PAGES.recon = async ctx => {
  const d = await api('/api/recon', null, true);
  const st = {ok: 'PASS', fail: 'FAIL', warn: 'WARNING', na: 'N/A'};
  if (!ctx.set(`<div class="strip"><span><b>${d.n_ok}</b> passed</span><span><b>${d.n_warn}</b> warnings</span><span><b class="${d.n_fail ? 'neg' : ''}">${d.n_fail}</b> failed</span><span>Every figure is recomputed from account lines and compared with the source reports. Differences are flagged, never adjusted.</span></div><div class="card">${d.checks.map((k, i) => `<div class="chk" data-i="${i}"><div class="chk-h"><span class="chip ${k.status}">${st[k.status]}</span><b>${esc(k.name)}</b>${k.items.length ? '<span class="muted">details &#9662;</span>' : ''}</div><p>${esc(k.summary)}</p>${k.items.length ? `<div class="chk-d"><table class="tbl"><tbody>${k.items.map(it => `<tr><td>${esc(it.item)}</td><td class="wrap muted">${esc(it.detail)}</td></tr>`).join('')}</tbody></table></div>` : ''}</div>`).join('')}</div>`)) return;
  $$('.chk-h').forEach(h => h.onclick = () => h.parentElement.classList.toggle('open'));
};

/* ===== data / folder page ===== */
const TYPE_NAMES = {GL: 'General Ledger', PL: 'Profit & Loss', BS: 'Balance Sheet'};
PAGES.data = async ctx => {
  const m = S.meta; let h = '';
  if (m.loaded) {
    const fr = t => m.files[t] ? `<tr><td><span class="badge">${TYPE_NAMES[t]}</span></td><td>${esc(m.files[t].name)}</td><td>${esc(m.files[t].period_text)}</td><td>${esc(m.files[t].company)}</td></tr>` : `<tr><td><span class="badge">${TYPE_NAMES[t]}</span></td><td colspan="3" class="muted">Not loaded</td></tr>`;
    h += `<div class="card" style="margin-bottom:14px"><div class="card-h"><div><h3>${esc(m.company)}</h3><div class="sub">${esc(m.folder || '')} &middot; ${m.basis ? esc(m.basis) + ' basis' : ''}</div></div><button class="pri" id="b-reload">Refresh data</button></div><div class="cbody"><table class="tbl"><thead><tr><th>Report</th><th>File</th><th>Period (as exported)</th><th>Company (in file)</th></tr></thead><tbody>${['PL', 'BS', 'GL'].map(fr).join('')}</tbody></table></div>
      <div class="pad muted">Analysis window: ${esc(ymLabel(m.months[0]))} – ${esc(ymLabel(m.months[m.months.length - 1]))}${m.has_gl ? ` &middot; ledger: ${nf0.format(m.gl_count)} transactions (${esc(m.gl_range[0])} to ${esc(m.gl_range[1])})` : ''} &middot; Reconciliation: ${m.recon.n_ok} passed, ${m.recon.n_warn} warnings, ${m.recon.n_fail} failed</div></div>`;
    if (m.warnings.length) h += m.warnings.map(w => `<div class="note warn"><span>${esc(w)}</span></div>`).join('') + '<div style="height:12px"></div>';
  }
  h += `<div class="card ${m.loaded ? '' : 'land'}"><div class="hero"><h2>${m.loaded ? 'Load a different company' : 'Financial Analytics Dashboard'}</h2><div class="muted">Select the folder that contains the QuickBooks Online exports for one company: <b>General Ledger</b>, month-wise <b>Profit &amp; Loss</b> and month-wise <b>Balance Sheet</b> (.xlsx). Files are detected automatically and never modified.</div>
    <div class="dz"><div class="row" style="justify-content:center"><button class="pri" id="b-pick" style="height:40px;padding:0 22px;font-size:14px">Select folder…</button><span class="muted">or</span><input type="text" id="p-path" placeholder="Paste folder path, e.g. C:\\Clients\\ABC Inc\\2026" style="width:360px;height:38px;border:1px solid var(--border);border-radius:8px;padding:0 10px;background:var(--card)"><button id="b-scan" style="height:38px">Scan folder</button></div></div><div id="scanres" style="text-align:left;margin-top:16px"></div></div></div>`;
  ctx.set(h);
  const rl = $('#b-reload'); if (rl) rl.onclick = async () => { try { await post('/api/reload'); await waitLoad(); toast('Data refreshed'); } catch (e) { toast(e.message, true); } };
  $('#b-pick').onclick = async () => {
    const b = $('#b-pick'); b.disabled = true; b.textContent = 'Waiting for folder dialog…';
    try { const r = await post('/api/pick_folder', {}); if (r.path) { $('#p-path').value = r.path; await scanAndLoad(r.path); } else if (r.error) { toast('Folder dialog unavailable: ' + r.error + '. Paste the folder path instead.', true); $('#p-path').focus(); } }
    catch (e) { toast(e.message, true); } finally { b.disabled = false; b.textContent = 'Select folder…'; }
  };
  $('#b-scan').onclick = () => { const p = $('#p-path').value.trim(); if (p) scanAndLoad(p); else toast('Enter a folder path first', true); };
  $('#p-path').onkeydown = e => { if (e.key === 'Enter') $('#b-scan').click(); };
};
async function scanAndLoad(folder) {
  try {
    const sc = await post('/api/scan', {folder});
    renderScan(sc);
    if (sc.chosen.PL || sc.chosen.BS) await loadFolder(folder, sc.chosen);
    else toast('No QuickBooks reports were recognised automatically - map the files manually below.', true);
  } catch (e) { toast(e.message, true); }
}
function renderScan(sc) {
  const el = $('#scanres'); if (!el) return;
  const all = sc.files.map(f => ({name: f.name, path: f.path, type: f.type})).concat((sc.skipped || []).map(f => ({name: f.name, path: f.path, type: ''})));
  const sel = t => `<div class="f"><label>${TYPE_NAMES[t]}</label><select data-map="${t}" style="min-width:260px"><option value="">(none)</option>${all.map(f => `<option value="${esc(f.path)}" ${sc.chosen[t] === f.path ? 'selected' : ''}>${esc(f.name)}${f.type ? '' : ' (not recognised)'}</option>`).join('')}</select></div>`;
  el.innerHTML = `<div class="sec-t" style="margin-top:0">Detected files</div><table class="tbl"><thead><tr><th>File</th><th>Detected as</th><th>Company</th><th>Period</th></tr></thead><tbody>${sc.files.map(f => `<tr><td>${esc(f.name)}</td><td><span class="badge">${TYPE_NAMES[f.type]}</span></td><td>${esc(f.company)}</td><td>${esc(f.period_text)}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">No QuickBooks reports recognised</td></tr>'}</tbody></table>${(sc.warnings || []).map(w => `<div class="note warn"><span>${esc(w)}</span></div>`).join('')}
  <div class="sec-t">Manual file mapping</div><div class="row">${['GL', 'PL', 'BS'].map(sel).join('')}<button class="pri" id="b-mload" style="align-self:flex-end">Load with this mapping</button></div>`;
  $('#b-mload').onclick = () => { const p = {}; $$('select[data-map]').forEach(s => { if (s.value) p[s.dataset.map] = s.value; }); if (!p.PL && !p.BS) { toast('Select at least a P&L or a Balance Sheet file', true); return; } loadFolder(sc.folder, p); };
}
async function loadFolder(folder, paths) {
  try { overlay(true, 'Loading', 'Starting…', 0.02); await post('/api/load', {folder, paths}); await waitLoad(true); } catch (e) { overlay(false); toast(e.message, true); }
}
function overlay(on, t, m, p) { $('#overlay').classList.toggle('on', on); if (t) $('#ov-t').textContent = t; if (m != null) $('#ov-m').textContent = m; if (p != null) $('#ov-b').style.width = Math.round(p * 100) + '%'; }
async function waitLoad(fresh) {
  overlay(true, 'Loading data', 'Reading files…', 0.03);
  for (;;) {
    const s = await (await fetch('/api/status')).json();
    overlay(true, null, s.message || '…', s.progress);
    if (s.state === 'ready') break;
    if (s.state === 'error') { overlay(false); throw new Error(s.error || 'Load failed'); }
    await new Promise(r => setTimeout(r, 250));
  }
  await loadMeta(fresh); overlay(false);
}

/* ===== filters / top bar ===== */
const inRange = (m, r) => r && m >= r[0] && m <= r[1];
function selMonths() {
  const M = S.meta.months, f = S.f; let sel;
  if (f.ptype === 'month') sel = [M.includes(f.pval) ? f.pval : M[M.length - 1]];
  else if (f.ptype === 'quarter') sel = M.filter(m => ymQ(m) === f.pval);
  else if (f.ptype === 'year') sel = M.filter(m => m.slice(0, 4) === f.pval);
  else if (f.ptype === 'ytd') { const e = M.includes(f.pval) ? f.pval : M[M.length - 1]; sel = M.filter(m => m.slice(0, 4) === e.slice(0, 4) && m <= e); }
  else if (f.ptype === 'custom') { let a = f.from || M[0], b = f.to || M[M.length - 1]; if (a > b) { const t = a; a = b; b = t; } sel = M.filter(m => m >= a && m <= b); }
  else sel = M.slice();
  return sel.length ? sel : M.slice();
}
function cmpAvail(mode) {
  if (mode === 'none') return {ok: true};
  const m = S.meta, sel = selMonths(), k = {prev: sel.length, mom: 1, qoq: 3, yoy: 12}[mode], cm = sel.map(x => ymAdd(x, -k));
  if (m.has_pl) { const ok = sel.every(x => inRange(x, m.pl_range)) && cm.every(x => inRange(x, m.pl_range)); if (ok) return {ok: true}; if (!m.has_bs) return {ok: false, why: 'needs ' + ymLabel(cm[0]) + ' – ' + ymLabel(cm[cm.length - 1]) + ' in the P&L'}; }
  if (m.has_bs) { const be = sel.filter(x => inRange(x, m.bs_range)).slice(-1)[0]; if (be && inRange(ymAdd(be, -k), m.bs_range) && !m.has_pl) return {ok: true}; }
  return {ok: false, why: 'needs ' + ymLabel(cm[0]) + (cm.length > 1 ? ' – ' + ymLabel(cm[cm.length - 1]) : '') + ' which is outside the loaded data'};
}
function defaultFilters() {
  const M = S.meta.months, last = M[M.length - 1];
  S.f = {ptype: 'ytd', pval: last, from: M[0], to: last, cmp: 'none', acct: '', mat_abs: 1000, mat_pct: 10};
  for (const c of ['yoy', 'prev', 'qoq', 'mom']) { if (cmpAvail(c).ok) { S.f.cmp = c; break; } }
  S.var = {material: false, leaf: true};
}
const PTYPES = [['all', 'All periods'], ['month', 'Month'], ['quarter', 'Quarter'], ['year', 'Year'], ['ytd', 'Year to date'], ['custom', 'Custom range']];
const CMPS = [['none', 'No comparison'], ['prev', 'Prior period'], ['mom', 'Month over month'], ['qoq', 'Quarter over quarter'], ['yoy', 'Year over year']];
const TITLES = {overview: 'Executive Overview', pl: 'Profit & Loss Analytics', bs: 'Balance Sheet', gl: 'General Ledger', variance: 'Variance & Growth', ratios: 'Financial Ratios', insights: 'Automated Insights', recon: 'Reconciliation & Data Integrity', data: 'Data & Files'};
function renderTop() {
  const top = $('#top'), m = S.meta;
  if (!m.loaded || S.page === 'data') {
    top.innerHTML = `<h1>${TITLES[S.page]}</h1><div class="grow"></div>${m.loaded ? '<div class="f"><label>&nbsp;</label><button id="b-back">Back to dashboard</button></div>' : ''}<div class="f"><label>&nbsp;</label><button id="b-theme" title="Light / dark mode">Theme</button></div>`;
    const bb = $('#b-back'); if (bb) bb.onclick = () => go('overview'); $('#b-theme').onclick = toggleTheme; return;
  }
  const f = S.f, M = m.months;
  const opts = (arr, cur, lab) => arr.map(v => `<option value="${v}" ${v === cur ? 'selected' : ''}>${lab ? lab(v) : v}</option>`).join('');
  let val = '';
  if (f.ptype === 'month' || f.ptype === 'ytd') val = `<div class="f"><label>${f.ptype === 'ytd' ? 'As of' : 'Month'}</label><select id="f-pv">${opts(M, f.pval, ymLabel)}</select></div>`;
  else if (f.ptype === 'quarter') val = `<div class="f"><label>Quarter</label><select id="f-pv">${opts(m.quarters, f.pval)}</select></div>`;
  else if (f.ptype === 'year') val = `<div class="f"><label>Year</label><select id="f-pv">${opts(m.years, f.pval)}</select></div>`;
  else if (f.ptype === 'custom') val = `<div class="f"><label>From</label><select id="f-from">${opts(M, f.from, ymLabel)}</select></div><div class="f"><label>To</label><select id="f-to">${opts(M, f.to, ymLabel)}</select></div>`;
  const cmpOpts = CMPS.map(([v, l]) => { const a = cmpAvail(v); return `<option value="${v}" ${v === f.cmp ? 'selected' : ''} ${a.ok ? '' : 'disabled'}>${l}${a.ok ? '' : ' (n/a)'}</option>`; }).join('');
  S.acctMap = {}; m.account_options.forEach(o => S.acctMap[o.l] = o.v);
  top.innerHTML = `<h1>${TITLES[S.page]}</h1><div class="f"><label>Period</label><select id="f-pt">${PTYPES.map(([v, l]) => `<option value="${v}" ${v === f.ptype ? 'selected' : ''}>${l}</option>`).join('')}</select></div>${val}
    <div class="f"><label>Compare to</label><select id="f-cmp">${cmpOpts}</select></div>
    <div class="f"><label>Account / category</label><div class="row" style="gap:4px;flex-wrap:nowrap"><input class="acct" id="f-acct" list="acl" placeholder="All accounts" value="${esc(f.acct ? labelForToken(f.acct) : '')}"><datalist id="acl">${m.account_options.map(o => `<option value="${esc(o.l)}">`).join('')}</datalist><button class="sm" id="f-ax" title="Clear account filter" ${f.acct ? '' : 'disabled'}>✕</button></div></div>
    <div class="grow"></div>
    <div class="f"><label>&nbsp;</label><button id="b-refresh" title="Re-read the source files">Refresh</button></div>
    <div class="f"><label>&nbsp;</label><div class="menu" id="expm"><button class="pri" id="b-exp">Export ▾</button><div class="menu-p"><div data-x="pdf">MIS report (PDF)<small>KPIs, charts, P&amp;L, variance, ratios, insights</small></div><div data-x="xlsx">Detailed analysis (Excel)<small>All tables incl. filtered ledger transactions</small></div><div data-x="png">Charts on this page (PNG)<small>One image per chart</small></div></div></div></div>
    <div class="f"><label>&nbsp;</label><button id="b-theme" title="Light / dark mode">Theme</button></div>`;
  const chg = patch => { Object.assign(S.f, patch); if (!cmpAvail(S.f.cmp).ok && S.f.cmp !== 'none') { /* keep: server explains */ } renderTop(); renderPageD(); };
  $('#f-pt').onchange = e => { const t = e.target.value; const patch = {ptype: t}; const last = M[M.length - 1]; if (t === 'month' || t === 'ytd') patch.pval = last; if (t === 'quarter') patch.pval = m.quarters[m.quarters.length - 1]; if (t === 'year') patch.pval = m.years[m.years.length - 1]; if (t === 'custom') { patch.from = M[0]; patch.to = last; } chg(patch); };
  const pv = $('#f-pv'); if (pv) pv.onchange = e => chg({pval: e.target.value});
  const fr = $('#f-from'); if (fr) fr.onchange = e => chg({from: e.target.value});
  const to = $('#f-to'); if (to) to.onchange = e => chg({to: e.target.value});
  $('#f-cmp').onchange = e => chg({cmp: e.target.value});
  const ac = $('#f-acct'); ac.onchange = () => { const v = ac.value.trim(); chg({acct: v ? (S.acctMap[v] || v) : ''}); };
  $('#f-ax').onclick = () => chg({acct: ''});
  $('#b-refresh').onclick = async () => { try { await post('/api/reload'); await waitLoad(); toast('Data refreshed from source files'); } catch (e) { toast(e.message, true); } };
  $('#b-exp').onclick = e => { e.stopPropagation(); $('#expm').classList.toggle('open'); };
  $$('#expm [data-x]').forEach(d => d.onclick = () => { $('#expm').classList.remove('open'); const x = d.dataset.x; if (x === 'png') { const ids = Object.keys(S.charts).filter(id => document.getElementById(id)); if (!ids.length) { toast('No charts on this page', true); return; } ids.forEach((id, i) => setTimeout(() => exportPNG(id, true), i * 350)); toast('Downloading ' + ids.length + ' chart image(s)…'); } else { toast(x === 'pdf' ? 'Building the MIS report…' : 'Building the Excel workbook…'); window.location.href = '/export/' + x + '?' + qs(S.page === 'gl' ? glQ() : null); } });
  $('#b-theme').onclick = toggleTheme;
}
document.addEventListener('click', () => { const m = $('#expm'); if (m) m.classList.remove('open'); });
function toggleTheme() { const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = t; try { localStorage.setItem('fd-theme', t); } catch (e) { } drawAll(); }
const NAV = [['overview', 'Overview', '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>'],
  ['pl', 'Profit & Loss', '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>'],
  ['bs', 'Balance Sheet', '<path d="M12 3v18M5 7h14"/><path d="M5 7l-3 7a3 3 0 006 0L5 7zM19 7l-3 7a3 3 0 006 0l-3-7z"/>'],
  ['gl', 'General Ledger', '<path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3V4z"/><path d="M9 9h6M9 13h6"/>'],
  ['variance', 'Variance & Growth', '<path d="M4 8h13l-3-3M20 16H7l3 3"/>'],
  ['ratios', 'Financial Ratios', '<circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5L5 19"/>'],
  ['insights', 'Insights', '<path d="M9 18h6M10 21h4M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z"/>'],
  ['recon', 'Reconciliation', '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>'],
  ['data', 'Data & Files', '<path d="M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V6z"/>']];
function renderNav() {
  const ok = S.meta && S.meta.loaded;
  $('#nav').innerHTML = NAV.map(([k, l, ic], i) => (i === 0 ? '<div class="nav-sep">Analysis</div>' : (k === 'recon' ? '<div class="nav-sep">Quality & data</div>' : '')) + `<div class="nav-i ${S.page === k ? 'on' : ''} ${(!ok && k !== 'data') ? 'dis' : ''}" data-p="${k}" title="${l}"><svg viewBox="0 0 24 24">${ic}</svg><b style="font-weight:600">${l}</b></div>`).join('');
  $$('.nav-i').forEach(n => n.onclick = () => go(n.dataset.p));
  $('#brand-co').textContent = ok ? S.meta.company : 'No data loaded';
}
function go(p) { S.page = p; try { history.replaceState(null, '', '#' + p); } catch (e) { } renderNav(); renderTop(); renderPage(); window.scrollTo(0, 0); }
function drillTo(token) {
  S.f.acct = token; S.gl.tab = 'txns'; S.gl.page = 0; S.page = 'gl'; try { history.replaceState(null, '', '#gl'); } catch (e) { }
  renderNav(); renderTop(); renderPage();
}
function renderBanner() {
  const b = $('#banner'); let h = '';
  if (S.meta && S.meta.loaded && S.page !== 'data') {
    if (!S.bannerOff) (S.meta.warnings || []).slice(0, 4).forEach(w => { h += `<div class="note warn"><span>${esc(w)}</span><button onclick="S.bannerOff=true;renderBanner()">Dismiss</button></div>`; });
    const p = S.lastPeriod; if (p && p.cmp.mode !== 'none' && !p.cmp.ok_pl && !p.cmp.ok_bs && ['overview', 'pl', 'bs', 'variance', 'ratios', 'insights'].includes(S.page)) h += `<div class="note info"><span>Comparison disabled: ${esc(p.cmp.reason || 'insufficient data')}. Absolute figures are still shown.</span></div>`;
  }
  b.innerHTML = h;
}
let focusId = null;
async function renderPage(silent) {
  const host = $('#page'), tok = ++S.token; S.charts = {};
  if (!S.meta.loaded && S.page !== 'data') S.page = 'data';
  const fe = document.activeElement; const keep = silent && S.focus && fe && fe.id === S.focus ? {id: fe.id, pos: fe.selectionStart} : null;
  if (!silent) host.innerHTML = '<div class="empty"><span class="spin"></span> Preparing view…</div>';
  const ctx = {host, tok, set: html => { if (tok !== S.token) return false; host.innerHTML = html; return true; }};
  try { await PAGES[S.page](ctx); }
  catch (e) { console.error(e); if (tok === S.token) host.innerHTML = `<div class="note bad"><span>Could not build this view: ${esc(e.message)}</span></div>`; }
  if (tok === S.token) { drawAll(); renderBanner(); if (keep) { const e2 = document.getElementById(keep.id); if (e2) { e2.focus(); try { e2.setSelectionRange(keep.pos, keep.pos); } catch (x) { } } } }
}
const renderPageD = debounce(() => renderPage(), 120);
let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(drawAll, 150); });

/* ===== init ===== */
async function loadMeta(fresh) {
  const prev = S.meta; S.meta = await api('/api/meta', null, true);
  if (!S.meta.loaded) return;
  if (fresh || !prev || !prev.loaded) { defaultFilters(); S.gl = Object.assign(S.gl, {text: '', types: [], cls: '', amin: '', amax: '', me: false, page: 0, tab: 'txns'}); S.collapsed = {}; S.bannerOff = false; if (fresh) S.page = 'overview'; }
  else { const M = S.meta.months; if (!M.includes(S.f.pval) && ['month', 'ytd'].includes(S.f.ptype)) S.f.pval = M[M.length - 1]; }
  renderNav(); renderTop(); renderPage();
}
(async function init() {
  try { const t = localStorage.getItem('fd-theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) { }
  const h = (location.hash || '').replace('#', ''); if (PAGES[h]) S.page = h;
  S.meta = {loaded: false, months: [], account_options: []};
  renderNav(); renderTop();
  try {
    const s = await (await fetch('/api/status')).json();
    if (s.state === 'loading') { await waitLoad(true); return; }
    if (s.loaded) { await loadMeta(true); if (PAGES[h]) go(h); return; }
  } catch (e) { }
  S.page = 'data'; renderNav(); renderTop(); renderPage();
})();

</script>
</body>
</html>
'''


# ----------------------------------------------------------------------------
# Local server
# ----------------------------------------------------------------------------
class State(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.status = {'state': 'idle', 'progress': 0.0, 'message': '', 'error': None}
        self.A = None
        self.scan = None
        self.folder = None
        self.version = 0


ST = State()


def set_status(state=None, progress=None, message=None, error='keep'):
    with ST.lock:
        if state is not None:
            ST.status['state'] = state
        if progress is not None:
            ST.status['progress'] = progress
        if message is not None:
            ST.status['message'] = message
        if error != 'keep':
            ST.status['error'] = error


def meta_payload():
    A = ST.A
    if A is None:
        return {'loaded': False}
    m = A.m
    months = m.months
    years = sorted({x[:4] for x in months})
    quarters = sorted({ym_quarter(x) for x in months})
    files = {}
    for t, f in m.files.items():
        files[t] = {'name': f['name'], 'company': f['company'], 'period_text': f['period_text'], 'basis': f['basis'], 'path': f['path']}
    return clean_json({
        'loaded': True, 'company': m.company, 'basis': m.basis, 'folder': ST.folder,
        'months': months, 'month_labels': {x: ym_label(x) for x in months}, 'years': years, 'quarters': quarters,
        'has_pl': A.pl is not None, 'has_bs': A.bs is not None, 'has_gl': A.gl is not None,
        'pl_range': [A.pl.months[0], A.pl.months[-1]] if A.pl else None,
        'bs_range': [A.bs.months[0], A.bs.months[-1]] if A.bs else None,
        'gl_range': [A.gl.date_min, A.gl.date_max] if A.gl else None,
        'gl_count': len(A.gl.recs) if A.gl else 0, 'gl_outside': m.gl_outside,
        'files': files, 'warnings': m.warnings, 'scan': ST.scan, 'version': ST.version,
        'account_options': A.account_options,
        'recon': {'n_ok': A.reconcile()['n_ok'], 'n_fail': A.reconcile()['n_fail'], 'n_warn': A.reconcile()['n_warn']},
    })


def load_worker(paths, folder, scan):
    try:
        set_status('loading', 0.01, 'Starting', None)
        t0 = time.time()
        model = load_model(paths, progress=lambda f, msg: set_status('loading', f, msg))
        A = Analytics(model)
        A.reconcile()
        set_status('loading', 0.97, 'Preparing dashboard')
        with ST.lock:
            ST.A = A
            ST.folder = folder
            ST.scan = scan
            ST.version += 1
        set_status('ready', 1.0, 'Loaded in %.1fs' % (time.time() - t0), None)
    except Exception as e:
        traceback.print_exc()
        set_status('error', 0.0, 'Failed to load', str(e))


def start_load(paths, folder, scan):
    if ST.status['state'] == 'loading':
        return False
    t = threading.Thread(target=load_worker, args=(paths, folder, scan), daemon=True)
    t.start()
    return True


def scan_payload(sc):
    return {'folder': sc['folder'], 'chosen': sc['chosen'], 'warnings': sc['warnings'], 'skipped': sc['skipped'],
            'files': [{'path': f['path'], 'name': f['name'], 'type': f['type'], 'company': f['company'], 'period_text': f['period_text']} for f in sc['files']]}


def pick_folder_dialog(initial=None):
    code = (
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "r = tk.Tk()\n"
        "r.withdraw()\n"
        "try:\n"
        "    r.attributes('-topmost', True)\n"
        "except Exception:\n"
        "    pass\n"
        "d = filedialog.askdirectory(title='Select the folder that contains the QuickBooks General Ledger, P&L and Balance Sheet exports', initialdir=%r or None)\n"
        "print(d or '')\n" % (initial or ''))
    kw = {}
    if os.name == 'nt':
        kw['creationflags'] = 0x08000000
    exe = sys.executable
    if exe and exe.lower().endswith('pythonw.exe') and os.path.exists(exe[:-5] + '.exe'):
        exe = exe[:-5] + '.exe'
    try:
        r = subprocess.run([exe, '-c', code], capture_output=True, text=True, timeout=600, **kw)
        out = (r.stdout or '').strip().splitlines()
        if r.returncode == 0:
            return {'path': out[-1].strip() if out else ''}
        return {'path': '', 'error': (r.stderr or 'Folder dialog failed').strip().splitlines()[-1]}
    except Exception as e:
        return {'path': '', 'error': str(e)}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'FinDash/1.0'

    def log_message(self, fmt, *args):
        pass

    def _ok_host(self):
        h = (self.headers.get('Host') or '').split(':')[0].lower()
        return h in ('127.0.0.1', 'localhost', '[::1]')

    def _send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(clean_json(obj), allow_nan=False, separators=(',', ':')))

    def _q(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[-1] for k, v in urllib.parse.parse_qs(u.query, keep_blank_values=True).items()}
        return u.path, q

    def do_GET(self):
        if not self._ok_host():
            return self._send(403, 'Forbidden', 'text/plain')
        path, q = self._q()
        try:
            if path in ('/', '/index.html'):
                return self._send(200, INDEX_HTML, 'text/html; charset=utf-8')
            if path == '/favicon.ico':
                return self._send(204, b'', 'image/x-icon')
            if path == '/api/status':
                with ST.lock:
                    s = dict(ST.status)
                s['loaded'] = ST.A is not None
                return self._json(s)
            if path == '/api/meta':
                return self._json(meta_payload())
            A = ST.A
            if path.startswith('/api/') or path.startswith('/export/'):
                if A is None:
                    return self._json({'error': 'No data loaded'}, 409)
                if path == '/api/overview':
                    return self._json(A.overview(A.ctx(q)))
                if path == '/api/pl':
                    c = A.ctx(q)
                    return self._json({'period': A.period_info(c), 'table': A.pl_table(c), 'mix': A.expense_mix(c),
                                       'trend': A.overview(c)['trend']})
                if path == '/api/bs':
                    c = A.ctx(q)
                    return self._json({'period': A.period_info(c), 'table': A.bs_table(c)})
                if path == '/api/variance':
                    return self._json(A.variance(A.ctx(q)))
                if path == '/api/ratios':
                    return self._json(A.ratios(A.ctx(q)))
                if path == '/api/insights':
                    c = A.ctx(q)
                    return self._json({'period': A.period_info(c), 'insights': A.insights(c)})
                if path == '/api/recon':
                    return self._json(A.reconcile())
                if path == '/api/gl_summary':
                    return self._json(A.gl_summary(A.ctx(q), q))
                if path == '/api/gl_rows':
                    return self._json(A.gl_rows(A.ctx(q), q))
                if path == '/api/gl_account':
                    return self._json(A.gl_account_detail(A.ctx(q), q.get('name', '')))
                if path == '/export/xlsx':
                    data = export_xlsx(A, q)
                    fn = re.sub(r'[^A-Za-z0-9_-]+', '_', A.m.company or 'Company') + '_Financial_Analysis.xlsx'
                    return self._send(200, data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                      {'Content-Disposition': 'attachment; filename="%s"' % fn})
                if path == '/export/pdf':
                    data = export_pdf(A, q)
                    fn = re.sub(r'[^A-Za-z0-9_-]+', '_', A.m.company or 'Company') + '_MIS_Report.pdf'
                    return self._send(200, data, 'application/pdf', {'Content-Disposition': 'attachment; filename="%s"' % fn})
            return self._send(404, 'Not found', 'text/plain')
        except Exception as e:
            traceback.print_exc()
            return self._json({'error': '%s: %s' % (type(e).__name__, e)}, 500)

    def do_POST(self):
        if not self._ok_host():
            return self._send(403, 'Forbidden', 'text/plain')
        path, q = self._q()
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n).decode('utf-8') or '{}') if n else {}
        except Exception:
            body = {}
        try:
            if path == '/api/pick_folder':
                return self._json(pick_folder_dialog(body.get('initial') or ST.folder))
            if path == '/api/scan':
                sc = scan_folder(body.get('folder', '').strip().strip('"'))
                return self._json(scan_payload(sc))
            if path == '/api/load':
                folder = body.get('folder', '').strip().strip('"')
                paths = body.get('paths')
                sc = scan_folder(folder)
                if not paths:
                    paths = sc['chosen']
                paths = {k: v for k, v in paths.items() if v}
                if not paths:
                    return self._json({'error': 'No QuickBooks GL / P&L / Balance Sheet files were recognised in this folder. Use manual mapping.', 'scan': scan_payload(sc)}, 422)
                ok = start_load(paths, folder, scan_payload(sc))
                return self._json({'started': ok, 'scan': scan_payload(sc)})
            if path == '/api/reload':
                if ST.A is None or not ST.folder:
                    return self._json({'error': 'Nothing to refresh'}, 409)
                paths = {t: f['path'] for t, f in ST.A.m.files.items()}
                sc = scan_folder(ST.folder) if os.path.isdir(ST.folder) else ST.scan
                ok = start_load(paths, ST.folder, scan_payload(sc) if isinstance(sc, dict) and 'chosen' in sc else sc)
                return self._json({'started': ok})
            return self._send(404, 'Not found', 'text/plain')
        except Exception as e:
            traceback.print_exc()
            return self._json({'error': str(e)}, 400)


def find_free_port(start=8765):
    for port in range(start, start + 60):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', port))
            s.close()
            return port
        except OSError:
            s.close()
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main(argv=None):
    ensure_dependencies()
    argv = list(sys.argv[1:] if argv is None else argv)
    no_browser = '--no-browser' in argv
    folder_arg = None
    port_arg = None
    for i, a in enumerate(argv):
        if a == '--folder' and i + 1 < len(argv):
            folder_arg = argv[i + 1]
        if a == '--port' and i + 1 < len(argv):
            port_arg = int(argv[i + 1])
    port = port_arg or find_free_port()
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    srv.daemon_threads = True
    url = 'http://127.0.0.1:%d/' % port
    print('=' * 64)
    print(' %s' % APP_NAME)
    print(' Running locally at %s   (data never leaves this computer)' % url)
    print(' Your browser will open automatically. Close this window or press')
    print(' Ctrl+C to stop the dashboard.')
    print('=' * 64)
    if folder_arg:
        try:
            sc = scan_folder(folder_arg)
            if sc['chosen']:
                start_load(sc['chosen'], folder_arg, scan_payload(sc))
        except Exception as e:
            print('Could not auto-load folder:', e)
    if not no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
