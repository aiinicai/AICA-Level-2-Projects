#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NCE TOOL v3.0  -  ONE application:  Tally  ->  trial balances (2 years)  ->  ICAI Non-Corporate-Entity financial statements (Excel)

  * Extract from a running Tally through ODBC (your Excel query), for the previous and the current year, OR use trial-balance files you already have.
  * Optional Tally Balance Sheet / Profit & Loss PDFs (real ones, or computed from the ledgers) supply opening stock, nett profit and cross-checks.
  * Output: ONE .xlsx in the ICAI NCE format, fully formula-linked: Review, Details, Balance Sheet, Statement of P&L, Notes 1-26, Disclosures,
    Trial Balance (drop-downs), Workings, Lists.  The ICAI template is built into this file - nothing else is needed.

Windows: double-click run_nce_tool.bat.      Any system:  python nce_tool.py          (window)
Command line:  python nce_tool.py TB1.xlsx TB2.xlsx [PL.pdf BS.pdf ...] -o folder
               python nce_tool.py --from-tally --fy 2026 -o folder          (reads Tally, then builds the workbook)
               python nce_tool.py --check                                    (is everything installed?)
"""
import sys, os, re, io, copy, difflib, datetime, base64, zlib, warnings

warnings.filterwarnings('ignore', message='.*Print area cannot be set.*')
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

try:
    import openpyxl
except ImportError:                                   # first run on a fresh computer: install the one required library
    import subprocess
    print('Installing the Excel library "openpyxl" (one time, needs internet) ...')
    subprocess.call([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', 'openpyxl'])
    try:
        import openpyxl
    except ImportError:
        print('\nCould not install "openpyxl". Please open a Command Prompt and type:   pip install openpyxl pypdf pyodbc')
        sys.exit(1)
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter as CL
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = '3.0'

# (the ICAI template payload `_TEMPLATE_B64` is at the very end of this file)


def load_template():
    """The built-in ICAI template as an openpyxl workbook (a file called NCE_ICAI_Template.xlsx next to this program, if present, overrides it)."""
    ext = os.path.join(HERE, 'NCE_ICAI_Template.xlsx')
    if os.path.exists(ext):
        return openpyxl.load_workbook(ext, keep_links=False)
    return openpyxl.load_workbook(io.BytesIO(zlib.decompress(base64.b64decode(''.join(_TEMPLATE_B64.split())))), keep_links=False)


# ========================================================================================
# 0.  COMMON HELPERS
# ========================================================================================
class ToolError(Exception):
    """An error whose message is meant to be read by the user (no traceback needed)."""


TallyError = ToolError


def clean_name(x):
    x = str(x if x is not None else '').replace('_x000D_', ' ')
    x = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', x)          # Tally's reserved 'Primary' parent arrives as '\x04 Primary'
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', x)).strip()


def clean_entity(s):
    """'ABC TRADERS ( 25-26) (A)'  ->  'ABC Traders'"""
    s = re.sub(r'\(\s*\d{2,4}\s*[-–/]\s*\d{2,4}\s*\)', '', str(s or ''))
    s = re.sub(r'\(\s*[A-Za-z]\s*\)\s*$', '', s).strip(' -,')
    s = re.sub(r'\s+', ' ', s)
    if s and s.upper() == s:
        s = re.sub(r'\bLlp\b', 'LLP', s.title())
    return s


def parse_amount(t):
    """Tally amount text -> float, debit negative (as Tally / ODBC give it). Understands '1,234.50', '-1234.5', '1234.50 Dr', '(1234.50)'."""
    if t is None:
        return 0.0
    if isinstance(t, bool):
        return 0.0
    if isinstance(t, (int, float)):
        return float(t)
    s = str(t).replace(',', '').replace('₹', '').strip()
    if not s:
        return 0.0
    m = re.match(r'^\(?\s*(-?\d+(?:\.\d+)?)\s*\)?\s*(Dr|Cr)?\.?$', s, re.I)
    if not m:
        return 0.0
    x = float(m.group(1))
    if s.startswith('('):
        x = -abs(x)
    if m.group(2):
        x = -abs(x) if m.group(2).lower() == 'dr' else abs(x)
    return x


def fy_label(frm, to):
    return '%02d-%02d' % (frm.year % 100, to.year % 100) if frm.year != to.year else str(to.year)


def safe(x):
    return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|]+', ' ', x)).strip() or 'Entity'


def in_fmt(x):
    """Indian number format, 2 decimals."""
    neg = x < 0
    x = abs(round(x + 1e-9, 2))
    s = '%.2f' % x
    ip, fp = s.split('.')
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ','.join(parts) + ',' + tail
    return ('(-)' if neg else '') + ip + '.' + fp


def _dmy(d):
    return '%d-%s-%02d' % (d.day, d.strftime('%b'), d.year % 100)


def fy_dates(end_year):
    """Indian financial year ending in `end_year`: 1-Apr-(end-1) to 31-Mar-end."""
    return datetime.date(end_year - 1, 4, 1), datetime.date(end_year, 3, 31)


def company_end_year(name):
    """2025 from 'X -(2024-25)', 'X( 24-25) (A)', 'X (2024-2025)' ... None if no year is in the name."""
    m = re.search(r'(\d{2,4})\s*[-–/]\s*(\d{2,4})', name or '')
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    if a < 100:
        a += 2000
    if b < 100:
        b = (a // 100) * 100 + b
    return b if b >= a else None


def pick_companies(names, end_year):
    """(current, previous) company names from the loaded companies, by the year in their names."""
    cur = next((n for n in names if company_end_year(n) == end_year), '')
    prv = next((n for n in names if company_end_year(n) == end_year - 1), '')
    return cur, prv


# ========================================================================================
# 0b.  TALLY  (ODBC only; Tally's HTTP port is used just to list the loaded companies)
# ========================================================================================
DEFAULT_RESERVED = ['Branch / Divisions', 'Capital Account', 'Reserves & Surplus', 'Current Assets', 'Bank Accounts', 'Cash-in-Hand', 'Deposits (Asset)',
                    'Loans & Advances (Asset)', 'Stock-in-Hand', 'Sundry Debtors', 'Current Liabilities', 'Duties & Taxes', 'Provisions', 'Sundry Creditors',
                    'Direct Expenses', 'Direct Incomes', 'Fixed Assets', 'Indirect Expenses', 'Indirect Incomes', 'Investments', 'Loans (Liability)',
                    'Bank OD A/c', 'Bank OCC A/c', 'Secured Loans', 'Unsecured Loans', 'Misc. Expenses (ASSET)', 'Purchase Accounts', 'Sales Accounts', 'Suspense A/c', 'Retained Earnings']
DEFAULT_PARENT = {'Reserves & Surplus': 'Capital Account', 'Bank Accounts': 'Current Assets', 'Cash-in-Hand': 'Current Assets', 'Deposits (Asset)': 'Current Assets',
                  'Loans & Advances (Asset)': 'Current Assets', 'Stock-in-Hand': 'Current Assets', 'Sundry Debtors': 'Current Assets', 'Duties & Taxes': 'Current Liabilities',
                  'Provisions': 'Current Liabilities', 'Sundry Creditors': 'Current Liabilities', 'Bank OD A/c': 'Loans (Liability)', 'Secured Loans': 'Loans (Liability)',
                  'Unsecured Loans': 'Loans (Liability)', 'Bank OCC A/c': 'Loans (Liability)', 'Retained Earnings': 'Reserves & Surplus'}
GROUP_ALIAS = {'income (direct)': 'Direct Incomes', 'income (indirect)': 'Indirect Incomes', 'expenses (direct)': 'Direct Expenses', 'expenses (indirect)': 'Indirect Expenses'}
_CANON = {n.lower(): n for n in DEFAULT_RESERVED}
_CANON.update(GROUP_ALIAS)


def canon_group(n):
    """'Stock-in-hand' / 'Expenses (Indirect)' / spacing variants -> Tally's standard spelling; custom group names are returned unchanged"""
    n = clean_name(n)
    return _CANON.get(n.lower(), n)


PL_ROOTS = ('sales accounts', 'purchase accounts', 'direct expenses', 'direct incomes', 'indirect expenses', 'indirect incomes')


def sanitize_xml(raw):
    """Tally's XML often contains characters XML forbids (e.g. '&#4;' for its reserved 'Primary')."""
    t = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
    t = re.sub(r'&#(?:0*[0-8]|0*1[1-2]|0*1[4-9]|0*2[0-9]|0*3[01]);', '', t)
    t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
    t = re.sub(r'&#x(?:0*[0-8]|0*[bB]|0*[cC]|0*[eE]|0*1[0-9a-fA-F]);', '', t)
    return t


def http_company_names(host='localhost', port=9000, timeout=30):
    """List of every company loaded in Tally (Tally's HTTP port). Used ONLY to fill the company drop-downs; raises on failure."""
    import urllib.request, urllib.error
    import xml.etree.ElementTree as ET
    xml = ('<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>List of Companies</ID></HEADER>'
           '<BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES><TDL><TDLMESSAGE>'
           '<COLLECTION NAME="List of Companies" ISMODIFY="No"><TYPE>Company</TYPE><FETCH>Name</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>')
    req = urllib.request.Request('http://%s:%s' % (host, port), data=xml.encode('utf-8'), headers={'Content-Type': 'text/xml; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.URLError as e:
        raise ToolError('Tally did not answer on %s:%s (%s)' % (host, port, getattr(e, 'reason', e)))
    except Exception as e:
        raise ToolError('Tally did not answer on %s:%s (%s)' % (host, port, e))
    root = ET.fromstring(sanitize_xml(body))
    out = []
    for e in root.iter():
        if e.tag.upper() == 'COMPANY':
            nm = e.attrib.get('NAME') or ''
            if not nm:
                n2 = e.find('NAME')
                nm = (n2.text or '').strip() if n2 is not None else ''
            nm = clean_name(nm)
            if nm and nm not in out:
                out.append(nm)
    return out


class TallyODBC:
    """The very query used in Excel > Get Data > ODBC. Reads the company / period that is OPEN in Tally."""
    QUERY = 'SELECT $Name, $Parent, $_PrimaryGroup, $ClosingBalance FROM Ledger WHERE $ClosingBalance != 0'

    def __init__(self, dsn='TallyODBC64_9000', log=print):
        try:
            import pyodbc
        except ImportError:
            raise ToolError('The Tally connection needs the "pyodbc" library, which is not installed.\n'
                            'Open a Command Prompt and type:   pip install pyodbc\n(or click "Install missing libraries" in the Help tab).')
        self.pyodbc = pyodbc
        self.dsn, self.log = dsn, log
        try:
            self.conn = pyodbc.connect('DSN=%s' % dsn, autocommit=True, timeout=60)
        except Exception as e:
            dsns = ''
            try:
                dsns = '\nODBC data sources found on this computer: %s' % (', '.join(sorted(pyodbc.dataSources().keys())) or '(none)')
            except Exception:
                pass
            raise ToolError('Could not open the ODBC data source "%s".\n%s%s\n\nChecklist: (1) Tally is open and the company is loaded; (2) Tally ODBC port 9000 is enabled '
                            '(F1 Help > Settings > Connectivity); (3) the Data Source name above is correct.' % (dsn, str(e).splitlines()[0] if str(e) else e, dsns))

    def q(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

    def ledgers(self):
        try:
            data = self.q(self.QUERY)
        except Exception as e:
            raise ToolError('Tally refused the ledger query: %s\nIs a company open in Tally (Gateway of Tally)?' % (str(e).splitlines()[0] if str(e) else e))
        out = []
        for r in data:
            nm = clean_name(r[0])
            if not nm:
                continue
            out.append(dict(name=nm, parent=canon_group(r[1]), head=canon_group(r[2]) or canon_group(r[1]), closing=parse_amount(r[3]), opening=0.0))
        try:
            ob = {clean_name(r[0]): parse_amount(r[1]) for r in self.q("SELECT $Name, $OpeningBalance FROM Ledger WHERE $_PrimaryGroup = 'Stock-in-Hand'")}
            for l in out:
                if l['name'] in ob:
                    l['opening'] = ob[l['name']]
        except Exception as e:
            self.log('  (opening balance of the stock ledger not available through ODBC: %s)' % str(e).splitlines()[0])
        return out

    def groups(self):
        gs = {}
        try:
            for r in self.q('SELECT $Name, $Parent FROM Group'):
                gs[canon_group(r[0])] = dict(parent=canon_group(r[1]), reserved=False)
        except Exception as e:
            self.log('  (group tree not available through ODBC - the statements will use the primary groups only)')
        return gs

    def companies(self):
        try:
            return [clean_name(r[0]) for r in self.q('SELECT $Name FROM Company') if r and r[0]]
        except Exception:
            return []

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


class Tree:
    def __init__(self, groups):
        self.g = {}
        low = {n.lower(): n for n in DEFAULT_RESERVED}
        for n, d in (groups or {}).items():
            par = d.get('parent', '')
            if n in DEFAULT_PARENT and ((not par) or 'primary' in par.lower()):
                par = DEFAULT_PARENT[n]       # standard group whose parent was not reported
            self.g[n] = dict(parent=par, reserved=bool(d.get('reserved')) or n.lower() in low)
        for n in DEFAULT_RESERVED:                        # make sure the standard groups exist even if the list was not obtainable
            if n not in self.g:
                self.g[n] = dict(parent=DEFAULT_PARENT.get(n, ''), reserved=True)

    def is_top(self, p):
        return (not p) or 'primary' in p.lower() or p not in self.g

    def chain(self, group):
        """['Current Assets', 'Sundry Debtors'] = root ... immediate group"""
        out, seen, cur = [], set(), group
        while cur and cur in self.g and cur not in seen:
            seen.add(cur); out.insert(0, cur)
            p = self.g[cur]['parent']
            if self.is_top(p):
                break
            cur = p
        return out or ([group] if group else [])

    def head(self, group):
        """what Tally ODBC calls $_PrimaryGroup: the nearest standard (reserved) group above the ledger"""
        cur, seen = group, set()
        while cur and cur in self.g and cur not in seen:
            seen.add(cur)
            if self.g[cur]['reserved']:
                return cur
            p = self.g[cur]['parent']
            if self.is_top(p):
                return cur
            cur = p
        return group


def stock_ledgers(rows):
    return [r for r in rows if r['head'].lower() in ('stock-in-hand', 'stock in hand')]


def compute_info(rows, tree):
    stk = stock_ledgers(rows)
    cs = sum(-r['closing'] for r in stk)
    os_ = sum(-r['opening'] for r in stk)
    netcr = 0.0
    for r in rows:
        ch = tree.chain(r['parent']) if tree else []
        root = (ch[0] if ch else r['head']).lower()
        if root in PL_ROOTS or (not ch and r['head'].lower() in PL_ROOTS):
            netcr += r['closing']
    profit = netcr + cs - os_
    return dict(closing_stock=round(cs, 2), opening_stock=round(os_, 2), nett_profit_computed=round(profit, 2))


# ---- statements (computed from ledger balances, laid out like Tally's condensed T-format) -------------------------
ORDER = {'Current Assets': ['Stock-in-Hand', 'Deposits (Asset)', 'Loans & Advances (Asset)', 'Sundry Debtors', 'Cash-in-Hand', 'Bank Accounts'],
         'Current Liabilities': ['Duties & Taxes', 'Provisions', 'Sundry Creditors'], 'Loans (Liability)': ['Bank OD A/c', 'Secured Loans', 'Unsecured Loans']}


def _node_totals(rows, tree):
    tot, kids, leds = {}, {}, {}
    for r in rows:
        ch = tree.chain(r['parent']) or [r['parent'] or r['head']]
        for g in ch:
            tot[g] = tot.get(g, 0.0) + r['closing']
        for i in range(len(ch) - 1):
            kids.setdefault(ch[i], set()).add(ch[i + 1])
        leds.setdefault(ch[-1], []).append(r)
    return tot, kids, leds


def _items(root, tot, kids, leds, sign, skip_stock=False):
    """children of a root group -> [(label, amount)] ; sub-groups first (standard order, then alphabetical), then ledgers alphabetical."""
    std = ORDER.get(root, [])
    subs = sorted(kids.get(root, []), key=lambda n: (std.index(n) if n in std else 99, n.lower()))
    out = []
    for n in subs:
        if skip_stock and n.lower() == 'stock-in-hand':
            continue
        if abs(tot.get(n, 0)) >= 0.005:
            out.append((n, tot[n] * sign))
    for r in sorted(leds.get(root, []), key=lambda r: r['name'].lower()):
        if abs(r['closing']) >= 0.005 and not (skip_stock and r['head'].lower() == 'stock-in-hand'):
            out.append((r['name'], r['closing'] * sign))
    return out


def build_statements(rows, tree, info, company, frm, to):
    tot, kids, leds = _node_totals(rows, tree)
    os_, cs = info['opening_stock'], info['closing_stock']
    stk = stock_ledgers(rows)
    stk_name = stk[0]['name'] if stk else 'Stock'
    period = '%s to %s' % (_dmy(frm), _dmy(to))

    def rt(name, sign): return tot.get(name, 0.0) * sign
    # ---- Profit & Loss
    L1 = [('Opening Stock', os_, [(stk_name, os_)] if os_ else [])]
    R1 = []
    if abs(rt('Purchase Accounts', -1)) >= 0.005:
        L1.append(('Purchase Accounts', rt('Purchase Accounts', -1), _items('Purchase Accounts', tot, kids, leds, -1)))
    if abs(rt('Direct Expenses', -1)) >= 0.005:
        L1.append(('Direct Expenses', rt('Direct Expenses', -1), _items('Direct Expenses', tot, kids, leds, -1)))
    if abs(rt('Sales Accounts', 1)) >= 0.005:
        R1.append(('Sales Accounts', rt('Sales Accounts', 1), _items('Sales Accounts', tot, kids, leds, 1)))
    if abs(rt('Direct Incomes', 1)) >= 0.005:
        R1.append(('Direct Incomes', rt('Direct Incomes', 1), _items('Direct Incomes', tot, kids, leds, 1)))
    if cs:
        R1.append(('Closing Stock', cs, [(stk_name, cs)]))
    lsum = sum(a for _, a, _ in L1); rsum = sum(a for _, a, _ in R1)
    gp = rsum - lsum
    if gp >= 0:
        L1.append(('Gross Profit c/o', gp, [])); t1 = rsum
    else:
        R1.append(('Gross Loss c/o', -gp, [])); t1 = lsum
    L2, R2 = [], []
    if gp >= 0:
        R2.append(('Gross Profit b/f', gp, []))
    else:
        L2.append(('Gross Loss b/f', -gp, []))
    if abs(rt('Indirect Expenses', -1)) >= 0.005:
        L2.append(('Indirect Expenses', rt('Indirect Expenses', -1), _items('Indirect Expenses', tot, kids, leds, -1)))
    if abs(rt('Indirect Incomes', 1)) >= 0.005:
        R2.append(('Indirect Incomes', rt('Indirect Incomes', 1), _items('Indirect Incomes', tot, kids, leds, 1)))
    np_ = info['nett_profit_computed']
    if np_ >= 0:
        L2.append(('Nett Profit', np_, []))
    else:
        R2.append(('Nett Loss', -np_, []))
    t2 = max(sum(a for _, a, _ in L2), sum(a for _, a, _ in R2))
    pl = dict(title='Profit & Loss A/c', period=period, blocks=[(L1, R1, t1), (L2, R2, t2)], company=company)
    # ---- Balance Sheet
    liab, assets = [], []
    for g in ('Capital Account', 'Loans (Liability)', 'Current Liabilities'):
        if abs(rt(g, 1)) >= 0.005:
            liab.append((g, rt(g, 1), _items(g, tot, kids, leds, 1)))
    bs_rows = [r for r in rows if (tree.chain(r['parent']) or [r['head']])[0].lower() not in PL_ROOTS]
    imbalance = sum(r['closing'] for r in bs_rows)       # Cr - Dr of all balance-sheet ledgers incl. the stock ledger
    if abs(rt('Suspense A/c', 1)) >= 0.005:
        liab.append(('Suspense A/c', rt('Suspense A/c', 1), _items('Suspense A/c', tot, kids, leds, 1)))
    transferred = np_ - imbalance
    pl_items = [('Current Period', np_)]
    if abs(transferred) >= 0.005:
        pl_items.append(('Less: Transferred', -transferred))
    liab.append(('Profit & Loss A/c', sum(a for _, a in pl_items), pl_items))
    for g in ('Fixed Assets', 'Investments'):
        if abs(rt(g, -1)) >= 0.005:
            assets.append((g, rt(g, -1), _items(g, tot, kids, leds, -1)))
    ca_items = []
    if cs:
        ca_items.append(('Closing Stock', cs))
    ca_items += _items('Current Assets', tot, kids, leds, -1, skip_stock=True)
    ca_total = rt('Current Assets', -1) - (sum(-r['closing'] for r in stk) if stk else 0) + cs
    if abs(ca_total) >= 0.005 or ca_items:
        assets.append(('Current Assets', ca_total, ca_items))
    for g in ('Misc. Expenses (ASSET)', 'Branch / Divisions'):
        if abs(rt(g, -1)) >= 0.005:
            assets.append((g, rt(g, -1), _items(g, tot, kids, leds, -1)))
    lt = sum(a for _, a, _ in liab); at = sum(a for _, a, _ in assets)
    bs = dict(title='Balance Sheet', period=period, as_at=_dmy(to), blocks=[(liab, assets, max(lt, at))], company=company, imbalance=lt - at)
    return pl, bs


# ---- minimal PDF writer (no libraries) ------------------------------------------------------------------------
class PDF:
    W, H = 595.0, 842.0

    def __init__(self):
        self.pages, self.cur = [], None
        self.new_page()

    def new_page(self):
        self.cur = []
        self.pages.append(self.cur)

    @staticmethod
    def esc(s):
        s = s.encode('latin-1', 'replace').decode('latin-1')
        return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    @staticmethod
    def width(s, size, bold=False):
        w = 0.0
        for ch in s:
            if ch in '0123456789': w += 0.556
            elif ch in ',.:;ilI|!\'': w += 0.278
            elif ch in 'fjrt()-/ ': w += 0.33
            elif ch in 'mwMW@%': w += 0.85
            elif ch.isupper(): w += 0.68
            else: w += 0.53
        return w * size * (1.05 if bold else 1.0)

    def text(self, x, y, s, size=8.5, bold=False, align='l'):
        if align == 'r':
            x = x - self.width(s, size, bold)
        elif align == 'c':
            x = x - self.width(s, size, bold) / 2
        self.cur.append('BT /%s %.1f Tf %.1f %.1f Td (%s) Tj ET' % ('F2' if bold else 'F1', size, x, y, self.esc(s)))

    def line(self, x1, y1, x2, y2, w=0.5):
        self.cur.append('%.2f w %.1f %.1f m %.1f %.1f l S' % (w, x1, y1, x2, y2))

    def save(self, path):
        objs = []

        def add(b): objs.append(b); return len(objs)
        add(b'')                                                      # 1 catalog (filled later)
        add(b'')                                                      # 2 pages
        f1 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        f2 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        kids = []
        for pg in self.pages:
            content = '\n'.join(pg).encode('latin-1', 'replace')
            c = add(b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream')
            p = add(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] /Contents %d 0 R /Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>'
                     % (self.W, self.H, c, f1, f2)).encode())
            kids.append(p)
        objs[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objs[1] = ('<< /Type /Pages /Count %d /Kids [%s] >>' % (len(kids), ' '.join('%d 0 R' % k for k in kids))).encode()
        out = io.BytesIO(); out.write(b'%PDF-1.4\n'); offs = []
        for i, o in enumerate(objs, 1):
            offs.append(out.tell()); out.write(b'%d 0 obj\n' % i + o + b'\nendobj\n')
        x = out.tell()
        out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
        for o in offs:
            out.write(b'%010d 00000 n \n' % o)
        out.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x))
        with open(path, 'wb') as f:
            f.write(out.getvalue())


def render_statement(st, path, note):
    pdf = PDF()
    X = dict(ll=40, ls=222, lm=288, rl=305, rs=487, rm=553)
    state = dict(y=0)

    def header(cont=False):
        y = 800
        pdf.text(PDF.W / 2, y, st['company'], 11, True, 'c'); y -= 14
        pdf.text(PDF.W / 2, y, st['title'], 10, True, 'c'); y -= 12
        pdf.text(PDF.W / 2, y, st['period'], 8.5, False, 'c'); y -= 18
        l, r = ('Liabilities', 'Assets') if st['title'] == 'Balance Sheet' else ('Particulars', 'Particulars')
        col = ('as at ' + st['as_at']) if st['title'] == 'Balance Sheet' else st['period']
        pdf.text(X['ll'], y, l, 8.5, True); pdf.text(X['lm'], y, col, 8.5, True, 'r'); pdf.text(X['rl'], y, r, 8.5, True); pdf.text(X['rm'], y, col, 8.5, True, 'r')
        y -= 4; pdf.line(X['ll'], y, X['rm'], y); state['y'] = y - 11

    def need(n):
        if state['y'] - 11 * n < 55:
            pdf.text(X['rm'], 40, 'continued ...', 8, False, 'r')
            pdf.new_page(); header(True)
    header()
    for L, R, tot in st['blocks']:
        flatL = [r for it in L for r in [(it[0], it[1], 0)] + [(s[0], s[1], 1) for s in it[2]]]
        flatR = [r for it in R for r in [(it[0], it[1], 0)] + [(s[0], s[1], 1) for s in it[2]]]
        n = max(len(flatL), len(flatR))
        for i in range(n):
            need(1)
            y = state['y']
            for flat, lx, sx, mx in ((flatL, X['ll'], X['ls'], X['lm']), (flatR, X['rl'], X['rs'], X['rm'])):
                if i < len(flat):
                    lab, amt, lvl = flat[i]
                    lab = lab if len(lab) <= 44 else lab[:43] + '.'
                    if lvl == 0:
                        pdf.text(lx, y, lab, 8.5, True); pdf.text(mx, y, in_fmt(amt) if abs(amt) >= 0.005 else '', 8.5, True, 'r')
                    else:
                        pdf.text(lx + 6, y, lab, 8, False); pdf.text(sx, y, in_fmt(amt), 8, False, 'r')
            state['y'] -= 11
        need(2)
        y = state['y']; pdf.line(X['ll'], y + 8, X['rm'], y + 8)
        pdf.text(X['ll'], y - 2, 'Total', 8.5, True); pdf.text(X['lm'], y - 2, in_fmt(tot), 8.5, True, 'r')
        pdf.text(X['rl'], y - 2, 'Total', 8.5, True); pdf.text(X['rm'], y - 2, in_fmt(tot), 8.5, True, 'r')
        pdf.line(X['ll'], y - 6, X['rm'], y - 6)
        state['y'] -= 22
    pdf.text(X['ll'], 28, note, 6.5, False)
    pdf.save(path)


# ---- extraction of one year + writing the files ------------------------------------------------------------------
def write_tb_xlsx(path, rows, info, meta):
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = 'Query1'
    for j, h in enumerate(['$Name', '$Parent', '$_PrimaryGroup', '$ClosingBalance'], 1):
        ws.cell(1, j, h).font = Font(bold=True)
    for i, r in enumerate(sorted(rows, key=lambda r: r['name'].lower()), 2):
        ws.cell(i, 1, r['name']); ws.cell(i, 2, r['parent']); ws.cell(i, 3, r['head'])
        c = ws.cell(i, 4, round(r['closing'], 2)); c.number_format = '#,##0.00;[Red]-#,##0.00'
    ws.column_dimensions['A'].width = 52; ws.column_dimensions['B'].width = 38; ws.column_dimensions['C'].width = 28; ws.column_dimensions['D'].width = 18
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = 'A1:D%d' % (len(rows) + 1)
    inf = wb.create_sheet('Info')
    inf['A1'] = 'Key'; inf['B1'] = 'Value'
    inf['A1'].font = inf['B1'].font = Font(bold=True)
    items = [('company', clean_entity(meta['company'])), ('address', meta.get('address', '')), ('pan', meta.get('pan', '')), ('period_from', meta['frm'].isoformat()),
             ('period_to', meta['to'].isoformat()), ('opening_stock', info['opening_stock']), ('closing_stock', info['closing_stock']),
             ('nett_profit_computed', info['nett_profit_computed']), ('source', meta['source']),
             ('extracted_on', datetime.datetime.now().strftime('%Y-%m-%d %H:%M')), ('tool', 'NCE Tool v%s' % VERSION)]
    for i, (k, v) in enumerate(items, 2):
        inf.cell(i, 1, k); inf.cell(i, 2, v)
    inf.column_dimensions['A'].width = 24; inf.column_dimensions['B'].width = 60
    wb.save(path)


def extract_year(be, company, frm, to, outdir, want_pdf, log, os_override=None):
    log('  Reading the ledgers open in Tally for %s to %s ...' % (_dmy(frm), _dmy(to)))
    meta = dict(company=company, frm=frm, to=to, source='Tally ODBC (DSN %s)' % be.dsn)
    rows = [r for r in be.ledgers() if abs(r['closing']) >= 0.005]
    if not rows:
        raise ToolError('Tally returned NO ledgers with a balance. Check that the right company is open in Tally (Gateway of Tally) and that its period '
                        'is %s to %s.' % (_dmy(frm), _dmy(to)))
    gtree = be.groups()
    for r in rows:              # groups the ODBC group query did not give: hang them under the ledger's primary group
        if r['parent'] and r['parent'] != r['head'] and r['parent'] not in gtree:
            gtree[r['parent']] = dict(parent=r['head'], reserved=False)
    tree = Tree(gtree)
    if not company:
        names = be.companies()
        if len(names) > 1:
            comp = next((n for n in names if company_end_year(n) == to.year), None)
            if comp:
                log('  Several companies are loaded in Tally; using "%s" (year matches).' % comp)
            else:
                comp = names[0]
                log('  ! Several companies are loaded in Tally and none carries the year %d in its name - using the first one: "%s". '
                    'Type the company name in the window if this is wrong.' % (to.year, comp))
            company = comp
        else:
            company = names[0] if names else 'Entity'
        meta['company'] = company
    info = compute_info(rows, tree)
    if os_override is not None and abs(info['opening_stock'] - os_override) > 1:
        log('  Opening stock taken as the previous year\'s closing stock (%s) instead of the stock ledger\'s own opening balance (%s).'
            % (in_fmt(os_override), in_fmt(info['opening_stock'])))
        info['nett_profit_computed'] = round(info['nett_profit_computed'] + info['opening_stock'] - os_override, 2)
        info['opening_stock'] = round(os_override, 2)
    dr = sum(-r['closing'] for r in rows if r['closing'] < 0); cr = sum(r['closing'] for r in rows if r['closing'] > 0)
    log('  %d ledgers; debits %s, credits %s; closing stock %s, opening stock %s, nett profit (computed) %s' %
        (len(rows), in_fmt(dr), in_fmt(cr), in_fmt(info['closing_stock']), in_fmt(info['opening_stock']), in_fmt(info['nett_profit_computed'])))
    base = '%s FY%s' % (safe(clean_entity(company)), fy_label(frm, to))
    xlsx = os.path.join(outdir, base + ' Trial Balance.xlsx')
    write_tb_xlsx(xlsx, rows, info, meta)
    files = [xlsx]
    if want_pdf:
        pl, bs = build_statements(rows, tree, info, clean_entity(company), frm, to)
        for kind, st, fname in (('Balance Sheet', bs, 'Balance Sheet'), ('Profit & Loss', pl, 'Profit and Loss')):
            p = os.path.join(outdir, '%s FY%s %s.pdf' % (safe(clean_entity(company)), fy_label(frm, to), fname))
            render_statement(st, p, 'Computed by NCE Tool v%s from ledger closing balances (condensed Tally layout) - not a Tally print-out.' % VERSION)
            files.append(p)
        log('  Balance Sheet and Profit & Loss PDFs computed from the ledger balances.')
    return files, info, rows, company


def tally_extract(outdir, company, company_py, end_year, dsn='TallyODBC64_9000', want_pdf=True, log=print, ask=None, debug=False):
    """Pull both years out of Tally (ODBC).  `ask(message) -> bool` is called before each year so the user can switch the company / period in Tally."""
    os.makedirs(outdir, exist_ok=True)
    frm, to = fy_dates(end_year); frm_p, to_p = fy_dates(end_year - 1)
    allfiles, infos, rows_seen, comps = [], [], [], []
    for lbl, f_, t_, want in (('previous year', frm_p, to_p, company_py or company), ('current year', frm, to, company)):
        if ask:
            msg = ('Now open the %s in Tally%s.\n\nIn Tally: Alt+F3 (Select Company) - choose it, go to the Gateway of Tally, and make sure the period is %s to %s '
                   '(Alt+F2 changes the period).\n\nPress OK when Tally shows it.' % (lbl, (':\n"%s"' % want) if want else '', _dmy(f_), _dmy(t_)))
            if ask(msg) is False:
                raise ToolError('Cancelled.')
        be = TallyODBC(dsn, log)
        try:
            files, info, rows, comp = extract_year(be, want or None, f_, t_, outdir, want_pdf, log, os_override=(infos[-1]['closing_stock'] if infos else None))
        finally:
            be.close()
        allfiles += files; infos.append(info); comps.append(comp)
        rows_seen.append(sorted((r['name'], round(r['closing'], 2)) for r in rows))
    a_, b_ = rows_seen
    if len(a_) > 5 and a_ == b_:
        raise ToolError('Both years returned IDENTICAL data - Tally was still showing the same company / period when the second year was read.\n'
                        'Run again and, when asked, really switch the company (Alt+F3) or the period (Alt+F2) in Tally before pressing OK.')
    if not infos[0]['opening_stock']:
        log('  note: the previous year\'s opening stock cannot be read from Tally ledgers. If the previous-year stock matters, type it in the "Previous-year opening stock" box '
            '(Client tab) or add that year\'s Tally Profit & Loss PDF.')
    return allfiles


# ----------------------------------------------------------------------------------------
# 1.  READ A TALLY TRIAL BALANCE
# ----------------------------------------------------------------------------------------
STD_GROUPS = {'capital account', 'loans (liability)', 'current liabilities', 'fixed assets', 'current assets',
              'sales accounts', 'purchase accounts', 'direct expenses', 'direct incomes', 'indirect incomes',
              'indirect expenses', 'investments', 'reserves & surplus', 'suspense a/c', 'branch / divisions',
              'misc. expenses (asset)', 'stock-in-hand', 'bank accounts', 'cash-in-hand', 'sundry debtors',
              'sundry creditors', 'duties & taxes', 'provisions', 'deposits (asset)', 'loans & advances (asset)',
              'secured loans', 'unsecured loans', 'bank od a/c', 'expenses (direct)', 'expenses (indirect)',
              'income (direct)', 'income (indirect)', 'direct incomes', 'net profit', 'primary'}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def num(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(',', '').replace('₹', '').strip()
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()')
    m = re.match(r'^(-?\d+(\.\d+)?)\s*(Dr|Cr)?$', s, re.I)
    if not m:
        return 0.0
    x = float(m.group(1))
    return -x if neg else x


def parse_tb(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows())
    # header: last 'Debit' & 'Credit' columns on the same row
    hi = dc = cc = None
    for i, r in enumerate(rows):
        vals = [str(c.value).strip().lower() if c.value is not None else '' for c in r]
        if 'debit' in vals and 'credit' in vals:
            hi = i
            dc = max(j for j, v in enumerate(vals) if v == 'debit')
            cc = max(j for j, v in enumerate(vals) if v == 'credit')
            break
    if hi is None:
        raise ValueError('%s: could not find the "Debit" / "Credit" header row - is this a Tally trial balance?' % os.path.basename(path))
    # entity, address, period
    head_txt = []
    for r in rows[:hi + 1]:
        for c in r:
            if isinstance(c.value, str) and c.value.strip():
                head_txt.append(c.value.strip())
    entity = clean_entity(head_txt[0]) if head_txt else ''
    addr = []
    for t in head_txt[1:6]:
        if re.match(r'^trial balance', t, re.I) or re.search(r'\bto\b.*\d{2}', t):
            break
        addr.append(t.strip(' ,'))
    period = None
    for t in head_txt:
        m = re.search(r'(\d{1,2})[-\s]([A-Za-z]{3})[a-z]*[-\s](\d{2,4})\s*to\s*(\d{1,2})[-\s]([A-Za-z]{3})[a-z]*[-\s](\d{2,4})', t)
        if m:
            def yy(x):
                x = int(x)
                return x + 2000 if x < 100 else x
            period = (datetime.date(yy(m.group(3)), MON[m.group(2).lower()[:3]], int(m.group(1))),
                      datetime.date(yy(m.group(6)), MON[m.group(5).lower()[:3]], int(m.group(4))))
            break
    # body
    body = []
    gt = None
    for r in rows[hi + 1:]:
        c0 = r[0]
        name = str(c0.value).strip() if c0.value not in (None, '') else ''
        if not name:
            continue
        d, c = num(r[dc].value), num(r[cc].value)
        if re.match(r'^grand total', name, re.I):
            gt = (d, c)
            break
        indent = (c0.alignment.indent or 0) if c0.alignment else 0
        bold = bool(c0.font and c0.font.b)
        body.append(dict(name=name, d=d, c=c, indent=indent, bold=bold))
    has_indent = any(b['indent'] > 0 for b in body)
    has_bold = any(b['bold'] for b in body)

    def is_top(b):
        if has_indent:
            return b['indent'] == 0
        if has_bold:
            return b['bold']
        return False
    leaves, groups = [], {}
    cur = None
    for i, b in enumerate(body):
        if is_top(b):
            nxt = body[i + 1] if i + 1 < len(body) else None
            if nxt is not None and not is_top(nxt):
                cur = b['name']
                groups[cur] = (b['d'], b['c'])
            else:  # top-level row without children = a ledger/sub-group shown at group level
                nm = b['name']
                if nm.lower() in STD_GROUPS and nm.lower() not in ('profit & loss a/c',):
                    nm = nm + ' (group total - ledger detail not given in this TB)'
                leaves.append(dict(grp=b['name'] if not nm.lower().startswith('profit') else 'Profit & Loss A/c', name=nm, dr=b['d'], cr=b['c']))
                cur = None
        else:
            leaves.append(dict(grp=cur or 'Ungrouped', name=b['name'], dr=b['d'], cr=b['c']))
    sd = sum(l['dr'] for l in leaves)
    sc = sum(l['cr'] for l in leaves)
    if gt is None:
        gt = (sd, sc)
    return dict(path=path, entity=entity, address=', '.join(addr), period=period, rows=leaves, gt=gt, leaf_totals=(sd, sc))



def _hk(v):
    return re.sub(r'[^a-z]', '', str(v or '').lower())


def _find_header(ws):
    for ri, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
        ks = [_hk(v) for v in row]
        if 'name' in ks and 'closingbalance' in ks:
            return ri, ks
    return None


def is_odbc(path):
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ok = any(_find_header(ws) for ws in wb.worksheets)
        wb.close()
        return ok
    except Exception:
        return False


def read_odbc(path):
    """Tally ODBC extract: one row per ledger - $Name, $Parent, $_PrimaryGroup, $ClosingBalance (assets / debits are negative)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    hdr = None
    for ws in wb.worksheets:
        hdr = _find_header(ws)
        if hdr:
            break
    if not hdr:
        raise ValueError('no $Name / $ClosingBalance header found')
    ri, ks = hdr
    i_n, i_b = ks.index('name'), ks.index('closingbalance')
    i_p = ks.index('parent') if 'parent' in ks else None
    i_g = next((i for i, k in enumerate(ks) if k in ('primarygroup', 'primarygrp')), None)
    rows = []
    for row in ws.iter_rows(min_row=ri + 1, values_only=True):
        if row[i_n] in (None, ''):
            continue
        bal = num(row[i_b])
        if abs(bal) < 0.005:
            continue
        parent = clean_name(row[i_p]) if i_p is not None and row[i_p] else ''
        head = clean_name(row[i_g]) if i_g is not None and row[i_g] else parent
        rows.append(dict(grp=head or 'Ungrouped', parent=parent or head, name=clean_name(row[i_n]),
                         dr=-bal if bal < 0 else 0.0, cr=bal if bal > 0 else 0.0))
    sd, sc = sum(r['dr'] for r in rows), sum(r['cr'] for r in rows)
    info = {}
    for w2 in wb.worksheets:
        if w2.title.strip().lower() == 'info':
            for r_ in w2.iter_rows(values_only=True):
                if r_ and r_[0] and len(r_) > 1 and r_[1] not in (None, ''):
                    info[str(r_[0]).strip().lower()] = r_[1]
    period = None
    try:
        def _d(v):
            if isinstance(v, datetime.datetime): return v.date()
            if isinstance(v, datetime.date): return v
            return datetime.datetime.strptime(str(v)[:10], '%Y-%m-%d').date() if '-' in str(v)[:10] and str(v)[4] == '-' else datetime.datetime.strptime(str(v)[:10], '%d/%m/%Y').date()
        if info.get('period_from') and info.get('period_to'):
            period = (_d(info['period_from']), _d(info['period_to']))
    except Exception:
        period = None
    return dict(path=path, entity=str(info.get('company', '') or ''), address=str(info.get('address', '') or ''), period=period, rows=rows,
                gt=(sd, sc), leaf_totals=(sd, sc), legacy=False, info=info)


def load_tb(path):
    if is_odbc(path):
        return read_odbc(path)
    t = parse_tb(path)
    for r in t['rows']:
        r['parent'] = r['grp']
    t['legacy'] = True
    return t


def pdf_text(path):
    txt = ''
    try:
        import pypdf
        txt = '\n'.join((pg.extract_text() or '') for pg in pypdf.PdfReader(path).pages)
    except Exception:
        txt = ''
    if len(txt.strip()) < 50:
        try:
            import shutil, subprocess
            if shutil.which('pdftotext'):
                txt = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout
        except Exception:
            pass
    if len(txt.strip()) < 50:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                txt = '\n'.join((pg.extract_text() or '') for pg in pdf.pages)
        except Exception:
            pass
    return txt


AMT = r'([\d,]+\.\d{2})'


def parse_pdf(path):
    """Tally Profit & Loss A/c or Balance Sheet PDF -> key totals."""
    t = pdf_text(path)
    if len(t.strip()) < 50:
        raise ValueError('no text could be read (scanned PDF? or install pypdf:  pip install pypdf)')
    head = t[:700]
    kind = 'BS' if re.search(r'Balance\s*Sheet', head, re.I) else ('PL' if re.search(r'Profit\s*&\s*Loss', head, re.I) else None)
    if kind is None:
        raise ValueError('not a Tally Profit & Loss / Balance Sheet')
    m = re.search(r'(\d{1,2})-([A-Za-z]{3})-(\d{2,4})\s+to\s+(\d{1,2})-([A-Za-z]{3})-(\d{2,4})', t)
    period = None
    if m:
        def dt(d, mo, y):
            y = int(y); y += 2000 if y < 100 else 0
            return datetime.date(y, MON[mo.lower()], int(d))
        period = (dt(*m.group(1, 2, 3)), dt(*m.group(4, 5, 6)))
    first = next((ln.strip() for ln in t.splitlines() if ln.strip()), '')
    addr = ''
    lines_ = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines_) > 3:
        out_ = []
        for ln in lines_[1:6]:
            if re.search(r'Profit\s*&\s*Loss|Balance\s*Sheet', ln):
                break
            out_.append(ln.strip(' ,'))
        addr = ', '.join(out_)
    first = re.split(r'Profit\s*&\s*Loss|Balance\s*Sheet|#', first)[0].strip()
    v = {}

    def g(label):
        mm = re.search(label + r'\s*' + AMT, t)
        return num(mm.group(1)) if mm else None
    if kind == 'PL':
        v = dict(os=g(r'Opening\s*Stock'), cs=g(r'Closing\s*Stock'), sales=g(r'Sales\s*Accounts'), purchases=g(r'Purchase\s*Accounts'),
                 profit=g(r'Nett\s*Profit'))
        if v['profit'] is None:
            loss = g(r'Nett\s*Loss')
            v['profit'] = -loss if loss is not None else None
    else:
        tots = [num(x) for x in re.findall(r'T\s*o\s*t\s*a\s*l\s*' + AMT, t)]
        v = dict(bs_total=(max(tots) if tots else None), cs=g(r'Closing\s*Stock'))
    return dict(path=path, kind=kind, period=period, entity=clean_entity(first) if first else '', address=addr, vals=v)


SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.nce_tool_settings.json')
SAVE_KEYS = ('aud_firm', 'aud_frn', 'aud_name', 'aud_desig', 'aud_mno', 'place', 'signers_txt', 'dsn', 'host', 'port', 'out_dir')


def load_settings():
    try:
        import json
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(d):
    try:
        import json
        cur = load_settings()
        cur.update({k: d.get(k, '') for k in SAVE_KEYS if d.get(k)})
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cur, f, indent=1)
    except Exception:
        pass


def parse_signers(txt):
    """'D B Sharma, Partner' per line (or 'Name | Designation')  ->  [(name, designation)]"""
    out = []
    for ln in (txt or '').replace(';', '\n').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.split(r'\s*\|\s*', ln, maxsplit=1) if '|' in ln else ([ln.rsplit(',', 1)[0].strip(), ln.rsplit(',', 1)[1].strip()] if ',' in ln else [ln, ''])
        out.append((m[0].strip(), m[1].strip()))
    return out[:4]


def parse_date(x):
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x if isinstance(x, datetime.date) and not isinstance(x, datetime.datetime) else x.date()
    x = (x or '').strip()
    if not x:
        return None
    for f in ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%d/%m/%y', '%d %b %Y', '%d %B %Y'):
        try:
            return datetime.datetime.strptime(x, f).date()
        except ValueError:
            pass
    return None


def fy_from_name(path):
    b = os.path.basename(path)
    m = re.search(r'(?<![0-9])(?:20)?(\d{2})\s*[-_–]\s*(?:20)?(\d{2})(?![0-9])', b)
    if m:
        a, c = int(m.group(1)), int(m.group(2))
        if (a + 1) % 100 == c:
            return 2000 + c
    return None


PL_HEADS = ('sales accounts', 'purchase accounts', 'direct expenses', 'indirect expenses', 'direct incomes', 'indirect incomes',
            'expenses (direct)', 'expenses (indirect)', 'income (direct)', 'income (indirect)')


def add_derived(t, os_val, profit, cs_pdf, label, log):
    """An ODBC extract has no opening stock, usually no Profit & Loss A/c and no closing-stock credit in the P&L.  Add them (flagged DERIVED)
    so that the trial balance is complete and balances.  If Tally's own 'Profit & Loss A/c' ledger is in the extract it is kept and only the
    opening stock / closing-stock entries are added (and, if the ledger already includes the current-year profit, it is corrected)."""
    rows = t['rows']
    plrows = [r for r in rows if re.match(r'^profit\s*(&|and)\s*loss', r['name'], re.I) or r['grp'].lower() == 'profit & loss a/c']
    stock = sum(r['dr'] - r['cr'] for r in rows if r['grp'].lower() in ('stock-in-hand', 'stock in hand'))
    if abs(stock) < 0.5 and cs_pdf:
        rows.append(dict(grp='Stock-in-Hand', parent='Stock-in-Hand', name='Closing stock (as per Tally P&L PDF)', dr=cs_pdf, cr=0.0, derived=True))
        stock = cs_pdf
    netcr = sum(r['cr'] - r['dr'] for r in rows if r['grp'].lower() in PL_HEADS)
    calc = netcr + stock - os_val
    if profit is None:
        profit = calc
        log('  ! FY%s: nett profit derived from the trial balance (no P&L PDF): %s' % (label, '{:,.2f}'.format(profit)))
    if os_val:
        rows.append(dict(grp='Opening Stock', parent='Opening Stock', name='Opening stock (as per Tally P&L)', dr=os_val, cr=0.0, derived=True))
    else:
        rows.append(dict(grp='Opening Stock', parent='Opening Stock', name='Opening stock (as per Tally P&L)', dr=0.0, cr=0.0, derived=True))
    if plrows:
        if abs(stock) > 0.5:
            rows.append(dict(grp='Excluded', parent='Excluded', name='Closing stock credited in P&L (balancing entry - not presented)', dr=0.0, cr=stock, derived=True))
        net = sum(r['cr'] - r['dr'] for r in rows)
        if abs(net) <= 1:
            t['stock'] = stock; t['profit'] = profit; t['os'] = os_val
            log('  the Tally "Profit & Loss A/c" ledger is in the FY%s extract - treated as retained earnings (Note 4(d)); current-year profit is added to it.' % label)
            return
        if abs(net - profit) <= max(1.0, abs(profit) * 1e-6):
            msg = ('FY%s: the Tally "Profit & Loss A/c" ledger is in the extract AND the books are out by exactly the nett profit, so the profit is already inside the '
                   'equity ledgers (partner capital and/or that ledger). The ledger is shown as retained earnings (Note 4); please confirm where the current-year profit sits.' % label)
            log('  ! ' + msg)
        else:
            log('  ! FY%s: with the Tally "Profit & Loss A/c" ledger the trial balance is out of balance by %s - check the extract.' % (label, '{:,.2f}'.format(net)))
            t['stock'] = stock; t['profit'] = profit; t['os'] = os_val
            return
    rows.append(dict(grp='Profit & Loss A/c', parent='Profit & Loss A/c', name='Profit & Loss A/c (nett profit transferred to partners)',
                     dr=profit if profit >= 0 else 0.0, cr=-profit if profit < 0 else 0.0, derived=True))
    if abs(stock) > 0.5:
        rows.append(dict(grp='Excluded', parent='Excluded', name='Closing stock credited in P&L (balancing entry - not presented)',
                         dr=0.0, cr=stock, derived=True))
    t['stock'] = stock; t['profit'] = profit; t['os'] = os_val

# ----------------------------------------------------------------------------------------
# 2.  MERGE TWO YEARS
# ----------------------------------------------------------------------------------------
def canon(n):
    s = n.lower()
    s = re.sub(r'a/c\.?', '', s)
    s = re.sub(r'[^a-z0-9@%&]', '', s)
    return s


def merge(cy_rows, py_rows):
    ents = []
    pyl = [dict(r, used=False) for r in py_rows]
    # pass 1 exact canonical name
    for r in cy_rows:
        e = dict(name=r['name'], grp=r['grp'], parent=r.get('parent', r['grp']), derived=bool(r.get('derived')), cyD=r['dr'], cyC=r['cr'], pyD=0.0, pyC=0.0, order=len(ents))
        cands = [p for p in pyl if not p['used'] and canon(p['name']) == canon(r['name']) and p['grp'] == r['grp'] and bool(p.get('derived')) == bool(r.get('derived'))]
        if cands:
            p = cands[0]
            p['used'] = True
            e['pyD'], e['pyC'] = p['dr'], p['cr']
        ents.append(e)
    # pass 2 fuzzy (same group)
    for e in ents:
        if e['pyD'] or e['pyC']:
            continue
        best, bs = None, 0.0
        for p in pyl:
            if p['used'] or p['grp'] != e['grp'] or bool(p.get('derived')) != e['derived']:
                continue
            sc = difflib.SequenceMatcher(None, canon(p['name']), canon(e['name'])).ratio()
            if sc > bs:
                best, bs = p, sc
        if best is not None and bs >= 0.82:
            best['used'] = True
            e['pyD'], e['pyC'] = best['dr'], best['cr']
    # pass 3: renamed ledger - one name contains the other (same head group), unique candidate only
    for e in ents:
        if e['pyD'] or e['pyC']:
            continue
        ce = canon(e['name'])
        cands = [p for p in pyl if not p['used'] and p['grp'] == e['grp'] and bool(p.get('derived')) == e['derived'] and len(canon(p['name'])) >= 6 and len(ce) >= 6
                 and (canon(p['name']) in ce or ce in canon(p['name']))]
        peers = [x for x in ents if not (x['pyD'] or x['pyC']) and x['grp'] == e['grp']]
        if len(cands) == 1 and len(peers) >= 1:
            cands[0]['used'] = True
            e['pyD'], e['pyC'] = cands[0]['dr'], cands[0]['cr']
    for p in pyl:
        if not p['used']:
            ents.append(dict(name=p['name'], grp=p['grp'], parent=p.get('parent', p['grp']), derived=bool(p.get('derived')), cyD=0.0, cyC=0.0, pyD=p['dr'], pyC=p['cr'], order=len(ents)))
    return ents


# ----------------------------------------------------------------------------------------
# 3.  AUTO-MAPPING RULES   (ledger/group name  ->  catalogue key)
# ----------------------------------------------------------------------------------------
ASSET_GRPS = ('current assets', 'bank accounts', 'cash-in-hand', 'deposits (asset)', 'loans & advances (asset)', 'sundry debtors',
              'stock-in-hand', 'investments', 'fixed assets', 'misc. expenses (asset)', 'branch / divisions', 'suspense a/c')
EXP_GRPS = ('direct expenses', 'indirect expenses', 'expenses (direct)', 'expenses (indirect)')
INC_GRPS = ('direct incomes', 'indirect incomes', 'income (direct)', 'income (indirect)')


def rx(p, s):
    return re.search(p, s, re.I) is not None


CTX = {'service': False}          # True for a service entity (no purchases / no stock): 'Sales Accounts' then means services
TYPOS = [(r'expensess|expences|expenes', 'expenses'), (r'servises|servicess', 'services'), (r'softwear|sofware', 'software'), (r'maintaince|maintainance|maintenence', 'maintenance'),
         (r'telphone|telepohone|telephon\b', 'telephone'), (r'payble|payabel', 'payable'), (r'intrest|interst', 'interest'), (r'subscrition|subscripton', 'subscription'),
         (r'pheriperals|peripherels', 'peripherals'), (r'salares|salries|salaris', 'salaries'), (r'purhcase|purchse', 'purchase'), (r'out\s+standing', 'outstanding'),
         (r'bulding|buiding', 'building'), (r'convency|convayance', 'conveyance'), (r'\bg\s*s\s*t\b', 'gst'), (r'\bt\s*d\s*s\b', 'tds'), (r'zenarator|generater', 'generator')]


def nn(x):
    """lower-case, single-spaced, common Tally typos repaired - used only for rule matching"""
    s = re.sub(r'\s+', ' ', str(x or '').lower()).strip()
    for p, r_ in TYPOS:
        s = re.sub(p, r_, s)
    return s


def classify(grp, name, parent=''):
    """returns (family_or_None, key_or_None, reason)   reason in {'name','group','default'}"""
    g, n = re.sub(r'\s+', ' ', grp.lower()).strip(), nn(name)
    pn = nn(parent) if parent and nn(parent) != g else ''
    if g == 'excluded':
        return None, 'EXCL', 'name'
    if g in ('stock-in-hand', 'stock in hand'):
        return None, 'CSTK', 'name'
    # ---- capital
    if g == 'capital account' or rx(r'capital a/c|capital account|partner.*capital', n) and not rx(r'expense', g):
        if rx(r'current|drawing|withdraw', n):
            return None, 'N3b', 'name'
        return None, 'N3a', 'name'
    if rx(r'^profit\s*(&|and)\s*loss', n) or g == 'profit & loss a/c':
        return 'pla', None, 'name'
    # ---- stock
    if rx(r'opening stock', n):
        return None, 'OS', 'name'
    if rx(r'closing stock', n) or g in ('stock-in-hand', 'stock in hand'):
        return None, 'CSTK', 'name'
    # ---- reserves
    if g == 'retained earnings':
        return None, 'N4-r11', 'name'
    if g == 'reserves & surplus':
        if rx(r'capital reserve', n): return None, 'N4-r8', 'name'
        if rx(r'revaluation', n): return None, 'N4-r9', 'name'
        return None, 'N4-r10', 'name'
    # ---- fixed assets / investments / misc
    if g == 'fixed assets':
        return None, 'PPE', 'group'
    if g == 'investments' or (g in ('current assets',) and rx(r'^investment', n)):
        return None, 'N12U-r34', 'group'
    if g == 'misc. expenses (asset)':
        return None, 'N14-r128', 'group'
    # ---- loans (liability)
    if g in ('bank od a/c', 'bank occ a/c') or rx(r'overdraft|\bo/?d\b a/c|cash credit|\bcc a/c|\bocc\b', n) and g not in EXP_GRPS:
        return 'bank', None, 'name'
    if g in ('loans (liability)', 'secured loans', 'unsecured loans') or rx(r'^(secured|unsecured) loans?$', n):
        if g != 'secured loans' and rx(r'partner|director|proprietor|promoter|relative|related', n):
            return None, 'N5-r42-LT', 'name'
        if rx(r'^secured loans?$', n) or g == 'secured loans':
            return None, ('N5-r19-LT'), 'name'
        if rx(r'^unsecured loans?$', n) or g == 'unsecured loans':
            return None, ('N5-r35-LT'), 'name'
        if rx(r'partner|director|proprietor|promoter|relative|related', n):
            return None, 'N5-r42-LT', 'name'
        if rx(r'bank|hdfc|sbi|icici|axis|canara|kotak|union|yes|bob|pnb|idbi|indian|finance|leasing|vehicle|car loan|term loan', n):
            return None, 'N5-r19-LT', 'name'
        return None, 'N5-r35-LT', 'name'
    # ---- current liabilities
    if g == 'sundry creditors' or rx(r'creditor', n) and g not in EXP_GRPS and g not in INC_GRPS:
        return 'creditors', None, 'name'
    if g == 'duties & taxes' or (g == 'current liabilities' and rx(r'^duties|\bgst\b|\btds\b|\btcs\b', n)):
        return 'duties', None, 'name'
    if g == 'provisions' or (g == 'current liabilities' and rx(r'provision', n) and not rx(r'^outstanding expenses', n)):
        if rx(r'gratuity', n): return None, 'N8-r14-ST', 'name'
        if rx(r'leave', n): return None, 'N8-r15-ST', 'name'
        return None, 'N8-r19-ST', 'name'
    if g == 'current liabilities':
        if pn and rx(r'\btds\b|\btcs\b', pn): return None, 'N10-r46', 'name'
        if pn and rx(r'\bgst\b|duties', pn): return None, 'N10-r45', 'name'
        if rx(r'interest.*(accrued|payable)', n): return None, 'N10-r42', 'name'
        if rx(r'^outstanding|salary payable|wages payable|expenses payable|audit fee', n): return None, 'N10-r47', 'name'
        return None, 'N10-r47', 'group'
    # ---- assets
    if g == 'sundry debtors' or (g in ASSET_GRPS and rx(r'^sundry debtors|debtor', n)):
        return 'debtors', None, 'name'
    if g == 'cash-in-hand' or (g in ASSET_GRPS and rx(r'^cash', n)):
        return 'cash', None, 'name'
    if g in ASSET_GRPS and rx(r'guarantee|\bbg\b|\bemd\b', n):
        return 'deposits', None, 'name'
    if g in ASSET_GRPS and rx(r'fdr|fixed deposit|\bfd\b|\bf\.\s?d\b|term deposit|margin money', n):
        return None, 'N17-r171', 'name'
    if g == 'bank accounts' or (g in ASSET_GRPS and rx(r'^bank|\bbank a/c|\bbank\b$', n) and not rx(r'charges|interest', n)):
        return 'bank', None, 'name'
    if g in ASSET_GRPS:
        if rx(r'fdr|fixed deposit|\bfd\b|\bf\.\s?d\b|term deposit', n): return None, 'N17-r171', 'name'
        if g == 'deposits (asset)' or rx(r'deposit', n): return 'deposits', None, 'name'
        if rx(r'prepaid', n): return None, 'N13U-r112-ST', 'name'
        if rx(r'interest.*(accrued|receivable)', n): return None, 'N18-r180', 'name'
        if rx(r'tds|tcs|tax deducted|advance tax|income tax|self assess|mat credit|gst|igst|cgst|sgst|input|cenvat|vat|service tax|itc|refund', n):
            return 'taxasset', None, 'name'
        if g == 'loans & advances (asset)' or rx(r'advance|loan', n): return 'loansadv', None, 'name'
        return 'loansadv', None, 'default'
    # ---- income side
    SERV = r'service|job work|labou?r|contract|consult|rental|repair|software|develop|professional|fees?\b|support|maintenance|\bamc\b|subscription|licen[cs]e|hosting|saas|\bit\b|export|outsourc|manpower|training|implementation|webs?ite|app\b|design|testing|royalt|commission'
    if g == 'sales accounts':
        svc = rx(SERV, n + ' ' + pn) or (CTX['service'] and not rx(r'\bgoods\b|products?\b|material|trading|\bsales? of\b', n))
        return None, ('N19-r7' if svc else 'N19-r6'), 'group'
    if g in INC_GRPS:
        if rx(r'interest', n): return None, 'N20-r15', 'name'
        if rx(r'dividend', n): return None, 'N20-r16', 'name'
        if rx(r'gain.*invest|profit.*invest|invest.*(gain|profit)', n): return None, 'N20-r17', 'name'
        if rx(r'grant|subsid', n): return None, 'N19-r8', 'name'
        if rx(r'discount|rebate|round|forex|exchange|sundry bal|written back|misc|rent received|insurance claim|profit on sale|scrap|incentive|refund', n): return None, 'N20-r18', 'name'
        # operating income booked under Direct / Indirect Incomes (typical for service businesses)
        if g in ('direct incomes', 'income (direct)'):
            return None, ('N19-r6' if rx(r'\bsales?\b|goods|product|material', n) and not rx(SERV, n) else 'N19-r7'), 'group'
        if rx(r'\bsales?\b|goods|products?\b', n): return None, 'N19-r6', 'name'
        if rx(SERV, n + ' ' + pn) and not rx(r'other|misc', n): return None, 'N19-r7', 'name'
        return None, 'N20-r18', 'group'
    # ---- purchases / expenses
    if g == 'purchase accounts':
        t_ = n + ' ' + pn
        if rx(r'raw', t_): return None, 'N21-r25', 'name'
        if rx(r'packing', t_): return None, 'N21-r31', 'name'
        if rx(r'services? taken|service taken|sub.?contract', t_): return None, 'N26-r97', 'name'
        if rx(r'transport services|freight', t_): return None, 'N26-r106', 'name'
        if rx(r'postal|courier', t_): return None, 'N26-r101', 'name'
        if rx(r'repairs?\b', t_) and rx(r'machinery', t_): return None, 'N26-r94', 'name'
        return None, 'N21-r45', 'group'
    if g in EXP_GRPS or rx(r'expense', g):
        rules = [
            (r'^(provision for )?income tax|^current tax|^tax expense|^income-tax', 'PLS-r33'),
            (r'interest on (partner|capital|designated)|partner.*interest|interest.*capital', 'N24b'),
            (r'depreciation', 'N25a'), (r'amortis|amortiz', 'N25-r85'),
            (r'(partner|partners).*(remuneration|salary)|remuneration.*partner', 'PR'),
            (r'interest.*(loan|bank|vehicle|car|term|overdraft|\bod\b|\bcc\b)', 'N24-r76'),
            (r'interest|finance charge|processing fee|loan processing', 'N24-r79'),
            (r'forex|exchange (loss|diff)|foreign exchange', 'N26-r108'),
            (r'salar|wages|bonus|stipend|ex.?gratia|incentive', 'N23-r68'),
            (r'consultan|accounting charges|accountant fee|book.?keeping', 'N26-r102'), (r'bad debt', 'N26-r112'), (r'\bpf\b|\bepf|provident|\besi\b|\besic', 'N23-r69'), (r'gratuity', 'N23-r70'),
            (r'staff|welfare|canteen|housing|accommodation|uniform|labour welfare', 'N23-r71'),
            (r'sub.?contract|contract labour|contractor|job work', 'N26-r97'),
            (r'^labou?r|labour', 'N23-r68'),
            (r'audit', 'N26-r99'), (r'insurance', 'N26-r95'), (r'\brent\b', 'N26-r92'),
            (r'electric|power|fuel|diesel|petrol|water charges', 'N26-r91'),
            (r'vehicle', 'N26-r113'),
            (r'repair|maintenance|r\s?&\s?m', 'N26-r94'),
            (r'professional tax|rates|taxes|licen[cs]e|permit|customs|duty|cess|\broc\b|filing fee', 'N26-r96'),
            (r'travel|conveyance|tour|lodging|boarding', 'N26-r98'),
            (r'printing|stationery', 'N26-r100'),
            (r'telephone|telepohone|mobile|postage|courier|internet|communication|broadband', 'N26-r101'),
            (r'provision.*doubtful', 'N26-r112'),
            (r'legal|professional|consult|retainer', 'N26-r102'),
            (r'advertis|publicity|marketing', 'N26-r103'), (r'business promotion|hospitality|entertain|gift', 'N26-r104'),
            (r'commission|brokerage', 'N26-r105'),
            (r'freight|transport|carriage|cartage|hamali|packing|forwarding|clearing|loading|shipping', 'N26-r106'),
            (r'loss on sale', 'N26-r107'), (r'store|spares|consumable', 'N26-r90'),
        ]
        for p, k in rules:
            if pn and rx(p, pn):
                return None, k, 'name'
        for p, k in rules:
            if rx(p, n):
                return None, k, 'name'
        return None, 'N26-r113', ('group' if g in EXP_GRPS else 'default')
    # ---- unknown group: decide by name, else default
    return 'unknown', None, 'default'


def side_key(fam, side, name):
    n = name.lower()
    if fam == 'creditors':
        return 'N9-r25' if side == 'Cr' else 'N13U-r111-ST'
    if fam == 'debtors':
        return 'N16-r145' if side == 'Dr' else 'N10-r47'
    if fam == 'bank':
        return 'N17-r160' if side == 'Dr' else 'N5-r23-ST'
    if fam == 'cash':
        return 'N17-r165' if side == 'Dr' else 'N10-r47'
    if fam == 'deposits':
        return 'N14-r126' if side == 'Dr' else 'N10-r47'
    if fam == 'loansadv':
        return 'N13U-r111-ST' if side == 'Dr' else 'N10-r47'
    if fam in ('duties', 'taxasset'):
        if side == 'Dr':
            if rx(r'refund|government|authorit', n): return 'N13U-r119-ST'
            if rx(r'tds|tcs|tax deducted|advance tax|income tax|self assess', n): return 'N13U-r113-ST'
            return 'N13U-r117-ST' if rx(r'gst|igst|cgst|sgst|input|cenvat|vat|service tax|itc', n) or fam == 'duties' else 'N13U-r113-ST'
        if rx(r'tds|tcs', n): return 'N10-r46'
        return 'N10-r45' if rx(r'gst|igst|cgst|sgst|vat|service tax|duties|duty|cess', n) else 'N10-r47'
    return 'N10-r47' if side == 'Cr' else 'N13U-r111-ST'


ALWAYS_SPLIT = ('creditors', 'debtors', 'bank', 'cash')


def expand(e, pla_key):
    fam, key, reason = classify(e['grp'], e['name'], e.get('parent', ''))
    base = dict(grp=e['grp'])
    out = []
    if fam == 'pla':
        return [dict(e, key=('PLA' if e.get('derived') else pla_key), reason='name')]
    if fam is None:
        return [dict(e, key=key, reason=reason)]
    if fam == 'unknown':
        net = (e['cyD'] - e['cyC']) or (e['pyD'] - e['pyC'])
        k = 'N13U-r111-ST' if net >= 0 else 'N10-r47'
        return [dict(e, key=k, reason='default')]
    dr_any = e['cyD'] > 0 or e['pyD'] > 0
    cr_any = e['cyC'] > 0 or e['pyC'] > 0
    both_same_year = (e['cyD'] > 0 and e['cyC'] > 0) or (e['pyD'] > 0 and e['pyC'] > 0)
    if fam in ALWAYS_SPLIT or (not both_same_year):
        if dr_any and cr_any:
            out.append(dict(e, name=e['name'] + ' - debit balances', cyC=0.0, pyC=0.0, key=side_key(fam, 'Dr', e['name']), reason='name'))
            out.append(dict(e, name=e['name'] + ' - credit balances', cyD=0.0, pyD=0.0, key=side_key(fam, 'Cr', e['name']), reason='name'))
        else:
            side = 'Dr' if dr_any or not cr_any else 'Cr'
            out.append(dict(e, key=side_key(fam, side, e['name']), reason='name'))
        return out
    # both sides in the same year (e.g. Duties & Taxes group): present net
    if fam == 'duties':
        return [dict(e, key=side_key(fam, 'Cr', e['name']), reason='name')]
    return [dict(e, key=side_key(fam, 'Dr', e['name']), reason='name')]


# ----------------------------------------------------------------------------------------
# 4.  BUILD THE WORKBOOK
# ----------------------------------------------------------------------------------------
GRPS_LIST = ['Capital Account', 'Loans (Liability)', 'Secured Loans', 'Unsecured Loans', 'Bank OD A/c', 'Current Liabilities', 'Duties & Taxes',
             'Sundry Creditors', 'Provisions', 'Outstanding Expenses & Provisions', 'Fixed Assets', 'Current Assets', 'Stock-in-Hand', 'Opening Stock',
             'Deposits (Asset)', 'Loans & Advances (Asset)', 'Sundry Debtors', 'Cash-in-Hand', 'Bank Accounts', 'Investments', 'Reserves & Surplus',
             'Sales Accounts', 'Purchase Accounts', 'Direct Expenses', 'Direct Incomes', 'Indirect Incomes', 'Indirect Expenses', 'Profit & Loss A/c',
             'Suspense A/c', 'Misc. Expenses (Asset)', 'Other']
NF = '#,##0.00;(#,##0.00);-'


NOTE_TITLES = {'3a': "Owners'/Partners' Capital Account", '3b': "Owners'/Partners' Current Account", '4': 'Reserves and surplus', '5': 'Borrowings',
               '6': 'Deferred tax', '7': 'Other long-term liabilities', '8': 'Provisions', '9': 'Trade payables', '10': 'Other current liabilities',
               '11': 'Property, plant and equipment', '12': 'Investments', '13': 'Loans and advances', '14': 'Other non-current assets', '15': 'Inventories',
               '16': 'Trade receivables', '17': 'Cash and bank balances', '18': 'Other current assets', '19': 'Revenue from operations', '20': 'Other income',
               '21': 'Purchases / cost of materials', '22': 'Changes in inventories', '23': 'Employee benefits expense', '24': 'Finance costs',
               '25': 'Depreciation and amortisation', '26': 'Other expenses'}
HEAD_ORDER = ['Capital Account', 'Reserves & Surplus', 'Secured Loans', 'Unsecured Loans', 'Loans (Liability)', 'Bank OD A/c', 'Current Liabilities', 'Sundry Creditors',
              'Duties & Taxes', 'Provisions', 'Fixed Assets', 'Investments', 'Stock-in-Hand', 'Current Assets', 'Deposits (Asset)', 'Loans & Advances (Asset)',
              'Sundry Debtors', 'Cash-in-Hand', 'Bank Accounts', 'Misc. Expenses (Asset)', 'Sales Accounts', 'Direct Incomes', 'Indirect Incomes', 'Purchase Accounts',
              'Direct Expenses', 'Indirect Expenses', 'Opening Stock', 'Profit & Loss A/c', 'Excluded']


def head_sort(g):
    gl = [h.lower() for h in HEAD_ORDER]
    return gl.index(g.lower()) if g.lower() in gl else 25.5


def split_cat(c):
    """catalogue entry -> (Note label, Line item)"""
    key, d = c['key'], c['desc']
    if key == 'OS': return 'Note 22 - Changes in inventories', 'Opening stock (feeds Workings A)'
    if key == 'CSTK': return 'Note 15 - Inventories', 'Closing stock ledger (feeds Workings A)'
    if key == 'PLA': return 'Excluded / not presented', 'Profit & Loss A/c - profit already credited to partners'
    if key == 'EXCL': return 'Excluded / not presented', 'Excluded / balancing entry (not presented)'
    if key == 'PR': return 'Statement of P&L', "Partners' remuneration (X)"
    if key.startswith('PLS-'): return 'Statement of P&L', d.split(' - ', 1)[1]
    m = re.match(r'^Note (\d+)([a-z]?)(?:\(([a-z])\))?\s*-\s*(.*)$', d)
    if m:
        n = m.group(1) + m.group(2)
        title = NOTE_TITLES.get(n) or NOTE_TITLES.get(m.group(1), '')
        line, term = m.group(4), ''
        if m.group(3): line = '(%s) %s' % (m.group(3), line)
        for suf in (' [Long-term]', ' [Short-term]'):
            if line.endswith(suf): line, term = line[:-len(suf)], suf
        return 'Note %s - %s%s' % (n, title, term), line
    return 'Other', d


def label_sort(lbl):
    m = re.match(r'^Note (\d+)([a-z]?) - .*?( \[(Long|Short)-term\])?$', lbl)
    if m:
        return (0, int(m.group(1)), m.group(2), 0 if m.group(4) == 'Long' else 1 if m.group(4) == 'Short' else 0)
    return (1 if lbl.startswith('Statement') else 2, 0, '', 0)


def fmt_date(d):
    return d.strftime('%d %B %Y').lstrip('0')


UNITS = [('Actuals', 1, 'Rs.'), ('Hundreds', 100, 'Rs. Hundreds'), ('Thousands', 1000, 'Rs. Thousands'), ('Lakhs', 100000, 'Rs. Lakhs'), ('Crores', 10000000, 'Rs. Crores')]
DISP_SHEETS = ['Balance Sheet', 'Statement of P&L', 'Note 1 to 3', 'Notes to BS 4 to 6', 'Notes to BS 7 to 10', 'Notes to BS 11', 'Notes to BS 12 to 18',
               'Notes to P & L 19 to 26', 'Disclosures']


def _match_paren(f, i):
    """index of the ')' closing the '(' at position i"""
    d = 0
    for j in range(i, len(f)):
        if f[j] == '(': d += 1
        elif f[j] == ')':
            d -= 1
            if d == 0: return j
    return -1


def apply_units(wb, first_row, last_row, default_unit='Actuals', log=print):
    """One drop-down ('Balance Sheet'!H3) rescales every statement / note / disclosure figure: Actuals, Hundreds, Thousands, Lakhs, Crores.
    Amounts are divided where they leave the Trial Balance / Workings (helper columns U:V of the Trial Balance), everything else is arithmetic on
    already-scaled cells, so totals stay consistent.  Workings / Review formulas that read the statements multiply back, so checks stay in rupees."""
    import re
    bs, ls, tb, wk = wb['Balance Sheet'], wb['Lists'], wb['Trial Balance'], wb['Workings']
    DIV = "'Balance Sheet'!$H$4"
    # unit table
    for j, h in enumerate(('Unit', 'Divisor', 'Label')): ls.cell(1, 13 + j, h).font = Font(bold=True)
    for i, (u, d, l) in enumerate(UNITS):
        ls.cell(2 + i, 13, u); ls.cell(2 + i, 14, d); ls.cell(2 + i, 15, l)
    ls.column_dimensions['M'].width = 14; ls.column_dimensions['O'].width = 20
    # the selector
    for mr in list(bs.merged_cells.ranges):
        if mr.min_col >= 7 and mr.min_row <= 6:
            bs.unmerge_cells(str(mr))
    yel = PatternFill('solid', fgColor='FFF2CC')
    bs['H2'] = 'SHOW ALL FIGURES IN  (drop-down)'; bs['H2'].font = Font(bold=True, color='1F3864')
    bs['H3'] = default_unit if default_unit in [u[0] for u in UNITS] else 'Actuals'
    bs['H3'].font = Font(bold=True, size=12, color='0000FF'); bs['H3'].fill = yel
    bs['H3'].alignment = Alignment(horizontal='center')
    bs['H3'].border = openpyxl.styles.Border(*(openpyxl.styles.Side(style='medium'),) * 4)
    bs['H4'] = '=IFERROR(INDEX(Lists!$N$2:$N$6,MATCH($H$3,Lists!$M$2:$M$6,0)),1)'
    bs['H5'] = '=IFERROR(INDEX(Lists!$O$2:$O$6,MATCH($H$3,Lists!$M$2:$M$6,0)),"Rs.")'
    for c_ in ('H4', 'H5'): bs[c_].font = Font(size=8, color='808080'); bs[c_].alignment = Alignment(horizontal='center')
    bs['H6'] = 'Choose Actuals / Hundreds / Thousands / Lakhs / Crores - the Balance Sheet, P&L, all Notes and Disclosures change together. '\
               'Type adjustments (Workings, Disclosures) in rupees.'
    bs['H6'].font = Font(italic=True, size=8, color='808080'); bs['H6'].alignment = Alignment(wrap_text=True, vertical='top'); bs.row_dimensions[6].height = max(bs.row_dimensions[6].height or 15, 15)
    bs.column_dimensions['H'].width = 34
    dv = DataValidation(type='list', formula1='"%s"' % ','.join(u[0] for u in UNITS), allow_blank=False, showErrorMessage=True, errorTitle='Units',
                        error='Choose Actuals, Hundreds, Thousands, Lakhs or Crores.', promptTitle='Show figures in', prompt='Pick the unit - every figure in the statements changes.',
                        showInputMessage=True)
    bs.add_data_validation(dv); dv.add('H3')
    # helper columns in the Trial Balance (display amounts divided by the unit)
    tb['U4'] = 'FY CY amount in selected unit (helper)'; tb['V4'] = 'FY PY amount in selected unit (helper)'
    for c_ in ('U4', 'V4'):
        tb[c_].font = Font(bold=True, color='808080'); tb[c_].alignment = Alignment(wrap_text=True, vertical='center')
    for r in range(first_row, last_row + 1):
        tb['U%d' % r] = '=IF(ISNUMBER(K%d),K%d/%s,0)' % (r, r, DIV); tb['V%d' % r] = '=IF(ISNUMBER(L%d),L%d/%s,0)' % (r, r, DIV)
        tb['U%d' % r].number_format = tb['K%d' % first_row].number_format; tb['V%d' % r].number_format = tb['L%d' % first_row].number_format
        tb['U%d' % r].font = Font(color='808080'); tb['V%d' % r].font = Font(color='808080')
    tb.column_dimensions['U'].width = 18; tb.column_dimensions['V'].width = 18
    # which Workings single cells hold amounts
    def w_amount(ref):
        m = re.match(r'\$?([A-Z]+)\$?(\d+)$', ref)
        c = wk['%s%s' % (m.group(1), m.group(2))]
        v = c.value
        return ('#,##0' in (c.number_format or '')) and not (isinstance(v, str) and not v.startswith('='))
    AMT_COLS = set('DEFGHIJKLM')

    def tf(f):
        f = re.sub(r"'Trial Balance'!\$K\$(\d+):\$K\$(\d+)", r"'Trial Balance'!$U$\1:$U$\2", f)
        f = re.sub(r"'Trial Balance'!\$L\$(\d+):\$L\$(\d+)", r"'Trial Balance'!$V$\1:$V$\2", f)
        # Workings sum ranges inside SUMIFS( -> wrap the call
        out, i = '', 0
        while True:
            m = re.compile(r"SUMIFS\(Workings!\$([A-Z])\$\d+:\$[A-Z]\$\d+,").search(f, i)
            if not m: out += f[i:]; break
            j = _match_paren(f, m.start() + 6)
            if m.group(1) in AMT_COLS and j > 0:
                out += f[i:m.start()] + '(' + f[m.start():j + 1] + '/' + DIV + ')'; i = j + 1
            else:
                out += f[i:m.end()]; i = m.end()
        f = out
        f = re.sub(r"Workings!(\$?[A-Z]+\$?\d+)(?![\d:])", lambda m: ('(Workings!%s/%s)' % (m.group(1), DIV)) if w_amount(m.group(1)) else m.group(0), f)
        f = re.sub(r'ABS\((\w+)-(\w+)\)<0\.01', r'ABS(\1-\2)<0.01/' + DIV, f)
        return f
    n_f = n_lab = 0
    for sn in DISP_SHEETS:
        ws = wb[sn]
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith('='):
                    nv = tf(v)
                    if nv != v: c.value = nv; n_f += 1
                elif isinstance(v, str) and re.search(r'Amount in\s+Rs\.', v):
                    mm = re.search(r'Amount in\s+Rs\.', v)
                    pre, post = v[:mm.start()], v[mm.end():]
                    c.value = '=%s"Amount in "&%s&"%s"' % (('"%s"&' % pre.replace('"', '""')) if pre else '', "'Balance Sheet'!$H$5", post.replace('"', '""'))
                    n_lab += 1
                elif isinstance(v, (int, float)) and v != 0 and '#,##0' in (c.number_format or ''):
                    log('  ! %s!%s holds a typed amount (%s): type it in rupees - it is NOT rescaled by the unit selector.' % (sn, c.coordinate, v))
    # Workings (and Review) read the statements: multiply back so every check stays in rupees
    stm = '|'.join(re.escape(x) for x in DISP_SHEETS if x != 'Disclosures')
    for sn in ('Workings', 'Review'):
        for row in wb[sn].iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith('=') and re.search(r"'(%s)'!" % stm, v):
                    c.value = re.sub(r"('(?:%s)'!\$?[A-Z]+\$?\d+)(?![\d:])" % stm, lambda m: '(%s*%s)' % (m.group(1), DIV), v)
    log('  Unit selector added (Balance Sheet H3): %d formulas rescaled, %d labels made dynamic.' % (n_f, n_lab))


def build(cy, py, meta, out_path, log=print):
    ENT = meta['entity']
    ENT_D = ENT + (' (PAN: %s)' % meta['pan'] if meta.get('pan') else '')
    cyY, pyY = meta['cyY'], meta['pyY']
    wb = load_template()
    wb._external_links = []                      # the ICAI file carries 80 broken external links -> Excel 'repair' prompt
    for n_ in list(wb.defined_names):          # ~3,700 junk names inherited from the ICAI file (#REF!, arrays, old reports)
        del wb.defined_names[n_]
    for ws_ in wb.worksheets:
        for n_ in list(ws_.defined_names):
            t_ = ws_.defined_names[n_].attr_text or ''
            if '#REF!' in t_ or '[' in t_:
                del ws_.defined_names[n_]
    if 'Note' in wb.sheetnames:
        del wb['Note']          # ICAI disclaimer sheet - not part of the financial statements
    ws_bs = wb['Balance Sheet']; ws_pl = wb['Statement of P&L']; n13 = wb['Note 1 to 3']; n46 = wb['Notes to BS 4 to 6']
    n710 = wb['Notes to BS 7 to 10']; n11 = wb['Notes to BS 11']; n1218 = wb['Notes to BS 12 to 18']; npl = wb['Notes to P & L 19 to 26']
    NPL = 'Notes to P & L 19 to 26'; N46 = 'Notes to BS 4 to 6'; N710 = 'Notes to BS 7 to 10'; N1218 = 'Notes to BS 12 to 18'

    # ---------------- catalogue of mappable lines ----------------
    CAT = []; TG = []

    def lab(ws, row):
        v = ws['B%d' % row].value
        v = v.strip() if isinstance(v, str) else ''
        a = ws['A%d' % row].value
        a = a if isinstance(a, str) and not a.startswith('=') else ''
        return (a + ' ' + v).strip()[:75]

    def addc(key, desc, nat, typ, loc, tg=None):
        CAT.append(dict(key=key, desc=desc, nat=nat, typ=typ, loc=loc))
        if tg:
            TG.append((tg[0], tg[1], tg[2], tg[3], key))

    addc('N3a', "Note 3a - Partners'/owner's capital accounts (feeds Note 3 workings)", 'Cr', 'BS', 'Note 1 to 3 / Workings C')
    addc('N3b', "Note 3b - Partners'/owner's current accounts & drawings (feeds Note 3 workings)", 'Cr', 'BS', 'Note 1 to 3 / Workings C')
    addc('PPE', 'Note 11 - Property, plant & equipment (feeds Workings B)', 'Dr', 'BS', 'Notes to BS 11 / Workings B')
    addc('OS', 'Opening stock (P&L - feeds Note 22 workings)', 'Dr', 'PL', 'Notes to P & L row 53 / Workings A')
    addc('CSTK', 'Closing stock ledger (Note 15 & 22 - via Workings A)', 'Dr', 'BS', 'Workings A (closing stock)')
    addc('PLA', 'Profit & Loss A/c balance - profit already appropriated to partners (not presented)', 'Dr', 'PLA', 'Excluded; used to derive closing stock')
    addc('PR', "P&L item X - Partners' remuneration", 'Dr', 'PL', 'Statement of P&L row 30', ('Statement of P&L', 30, 'D', 'F'))
    addc('EXCL', 'Excluded / not presented', 'Dr', 'BS', '-')

    def block(sheet, note, rows, cols, nat, typ, suffix='', prefix='', over=None):
        ws = wb[sheet]
        for r in rows:
            key = over[r] if over and r in over else 'N%s-r%d%s' % (note, r, suffix)
            d = 'Note %s - %s%s' % (note, prefix, lab(ws, r)) + (' [Long-term]' if suffix == '-LT' else ' [Short-term]' if suffix == '-ST' else '')
            addc(key, d, nat, typ, '%s row %d' % (sheet, r), (sheet, r, cols[0], cols[1]))

    block(NPL, 19, [6, 7, 8, 9], 'EG', 'Cr', 'PL'); block(NPL, 19, [11], 'EG', 'Dr', 'PL', prefix='Less: ')
    block(NPL, 20, [15, 16, 17, 18], 'EG', 'Cr', 'PL')
    for r, dsc in ((25, 'Purchases of raw material'), (31, 'Purchases of packing material'), (37, 'Purchases of other materials (components)'),
                   (45, 'Purchases of stock-in-trade'), (46, 'Purchases of stock-in-trade - other line (ii)'), (47, 'Purchases of stock-in-trade - other line (iii)')):
        addc('N21-r%d' % r, 'Note 21 - ' + dsc, 'Dr', 'PL', '%s row %d' % (NPL, r), (NPL, r, 'E', 'G'))
    block(NPL, 23, [68, 69, 70, 71], 'EG', 'Dr', 'PL'); block(NPL, 24, [76, 77, 79, 80], 'EG', 'Dr', 'PL')
    addc('N24b', "Note 24(b) - Interest on partners' capital", 'Dr', 'PL', '%s row 78' % NPL, (NPL, 78, 'E', 'G'))
    addc('N25a', 'Note 25(a) - Depreciation on tangible assets', 'Dr', 'PL', '%s row 84' % NPL, (NPL, 84, 'E', 'G'))
    addc('N25-r85', 'Note 25(b) - Amortisation on intangible assets', 'Dr', 'PL', '%s row 85' % NPL, (NPL, 85, 'E', 'G'))
    block(NPL, 26, range(90, 114), 'EG', 'Dr', 'PL')
    for r, d_ in ((22, 'Exceptional items'), (26, 'Extraordinary items'), (33, 'Current tax'), (34, 'Excess/short provision of tax for earlier years')):
        addc('PLS-r%d' % r, 'Statement of P&L - ' + d_, 'Dr', 'PL', 'Statement of P&L row %d' % r, ('Statement of P&L', r, 'D', 'F'))
    block(N46, 4, [8, 9, 10, 11], 'GI', 'Cr', 'BS')
    NOTE5 = {19: 'Secured term loans - from banks', 20: 'Secured term loans - from other parties', 23: 'Secured loans repayable on demand - from banks',
             24: 'Secured loans repayable on demand - from other parties', 26: 'Secured deferred payment liabilities', 27: 'Secured loans from related parties',
             28: 'Secured finance lease obligation (maturities)', 29: 'Secured other loans & advances',
             34: 'Unsecured term loans - from banks', 35: 'Unsecured term loans - from other parties', 38: 'Unsecured loans repayable on demand - from banks',
             39: 'Unsecured loans repayable on demand - from other parties', 41: 'Unsecured deferred payment liabilities', 42: 'Unsecured loans from related parties',
             43: 'Unsecured finance lease obligation (maturities)', 44: 'Unsecured other loans & advances'}
    for r, d_ in NOTE5.items():
        if r not in (23, 24, 38, 39):
            addc('N5-r%d-LT' % r, 'Note 5 - %s [Long-term]' % d_, 'Cr', 'BS', '%s row %d (LT)' % (N46, r), (N46, r, 'G', 'I'))
        if r != 28:
            addc('N5-r%d-ST' % r, 'Note 5 - %s [Short-term]' % d_, 'Cr', 'BS', '%s row %d (ST)' % (N46, r), (N46, r, 'J', 'K'))
    block(N710, 7, [7, 8], 'FH', 'Cr', 'BS')
    block(N710, 8, [14, 15, 17, 18, 19, 20], 'CE', 'Cr', 'BS', suffix='-LT')
    block(N710, 8, [14, 15, 17, 19, 20], 'FH', 'Cr', 'BS', suffix='-ST')
    block(N710, 9, [24, 25], 'FH', 'Cr', 'BS'); block(N710, 10, [40, 41, 42, 43, 44, 45, 46, 47], 'FH', 'Cr', 'BS')
    w12 = wb[N1218]
    for r in [10, 13, 14, 15, 16, 17, 18, 19]:
        addc('N12Q-r%d' % r, 'Note 12 - Non-current investments, quoted/other: ' + lab(w12, r), 'Dr', 'BS', '%s row %d' % (N1218, r), (N1218, r, 'G', 'J'))
    for r in [23, 26, 29, 30, 31, 32, 33, 34, 35]:
        addc('N12U-r%d' % r, 'Note 12 - Non-current investments, unquoted: ' + lab(w12, r), 'Dr', 'BS', '%s row %d' % (N1218, r), (N1218, r, 'G', 'J'))
    for r in range(54, 61):
        addc('N12CQ-r%d' % r, 'Note 12 - Current investments, quoted: ' + lab(w12, r), 'Dr', 'BS', '%s row %d' % (N1218, r), (N1218, r, 'G', 'J'))
    for r in range(65, 71):
        addc('N12CU-r%d' % r, 'Note 12 - Current investments, unquoted: ' + lab(w12, r), 'Dr', 'BS', '%s row %d' % (N1218, r), (N1218, r, 'G', 'J'))
    L13 = {84: 'Capital advances - considered good', 85: 'Capital advances - doubtful', 88: 'Loans/advances to partners or relatives', 90: 'Other loans and advances',
           91: 'Prepaid expenses', 92: 'Advance tax and TDS', 93: 'CENVAT credit receivable', 94: 'VAT credit receivable', 95: 'Service tax credit receivable',
           96: 'GST input credit receivable', 97: 'Security deposits', 98: 'Balance with government authorities'}
    for off, sec, pre in ((0, 'Secured', '13S'), (21, 'Unsecured', '13U')):
        for r, d_ in L13.items():
            rr = r + off
            addc('N%s-r%d-LT' % (pre, rr), 'Note 13 - %s loans & advances: %s [Long-term]' % (sec, d_), 'Dr', 'BS', '%s row %d (LT)' % (N1218, rr), (N1218, rr, 'F', 'G'))
            addc('N%s-r%d-ST' % (pre, rr), 'Note 13 - %s loans & advances: %s [Short-term]' % (sec, d_), 'Dr', 'BS', '%s row %d (ST)' % (N1218, rr), (N1218, rr, 'I', 'J'))
    block(N1218, 14, [126, 127, 128], 'IJ', 'Dr', 'BS'); block(N1218, 15, [132, 133, 134, 136, 137, 138], 'IJ', 'Dr', 'BS')
    for r, d_ in ((144, 'Less than 6 months - secured, good'), (145, 'Less than 6 months - unsecured, good'), (146, 'Less than 6 months - doubtful'),
                  (150, 'Over 6 months - secured, good'), (151, 'Over 6 months - unsecured, good'), (152, 'Over 6 months - doubtful'), (154, 'Unbilled receivables')):
        addc('N16-r%d' % r, 'Note 16 - Trade receivables: ' + d_, 'Dr', 'BS', '%s row %d' % (N1218, r), (N1218, r, 'I', 'J'))
    block(N1218, 17, [160, 161, 163, 164, 165, 170, 171, 172, 173], 'IJ', 'Dr', 'BS'); block(N1218, 18, [180, 181], 'IJ', 'Dr', 'BS')
    addc('N4-sur', 'Note 4(d) - Undistributed surplus (alias of N4-r11)', 'Cr', 'BS', '-')  # unused alias placeholder (kept out of lists)
    CAT.pop()
    # --- note label / line item for every catalogue entry (drives the cascading drop-downs)
    for c_ in CAT:
        c_['label'], c_['line'] = split_cat(c_)
    CAT.sort(key=lambda c_: label_sort(c_['label']))      # stable: keeps template order inside a note
    seen_ = set()
    for c_ in CAT:
        k_ = (c_['label'], c_['line'])
        if k_ in seen_:
            c_['line'] = '%s [%s]' % (c_['line'], c_['key'])
        seen_.add((c_['label'], c_['line']))
    CATD = {c['key']: c for c in CAT}

    # ---------------- entities -> mapping rows ----------------
    ents = merge(cy['rows'], py['rows'])
    CTX['service'] = not any(e['grp'].lower() in ('purchase accounts', 'stock-in-hand', 'stock in hand') for e in ents)
    # P&L A/c key: PLA (profit already appropriated) when it is a debit balance, else surplus
    pla = [e for e in ents if classify(e['grp'], e['name'], e.get('parent', ''))[0] == 'pla']
    pla_dr = sum(e['cyD'] - e['cyC'] for e in pla) or sum(e['pyD'] - e['pyC'] for e in pla)
    has_der = any(e.get('derived') for e in pla)
    has_real = any(not e.get('derived') for e in pla)
    if has_real and has_der:        # Tally's own ledger = retained earnings; the derived row = profit already transferred to the equity accounts
        pla_key = 'N4-r11'; toggle_default = 'N'
    elif has_real:                  # only Tally's own P&L A/c ledger (legacy export, or profit not yet in any equity account)
        pla_key = 'PLA' if pla_dr >= 0 else 'N4-r11'; toggle_default = 'N' if pla_key == 'PLA' else 'Y'
    else:
        pla_key = 'PLA'; toggle_default = 'N'
    grp_order = []
    for e in ents:
        if e['grp'] not in grp_order:
            grp_order.append(e['grp'])
    rows = []
    for e in ents:
        for r in expand(e, pla_key):
            if r['key'] not in CATD:
                log('  ! internal: key %s not in catalogue for "%s" - using Miscellaneous' % (r['key'], r['name']))
                r['key'] = 'N26-r113'; r['reason'] = 'default'
            rows.append(r)
    rows.sort(key=lambda r: (head_sort(r['grp']), r.get('parent', '').lower(), r['name'].lower()))
    rows = [r for r in rows if any((r['cyD'], r['cyC'], r['pyD'], r['pyC']))]

    # ---------------- Trial Balance sheet (control panel: change a drop-down -> every statement updates) ----------------
    mp = wb.create_sheet('Trial Balance'); wk = wb.create_sheet('Workings'); rv = wb.create_sheet('Review'); ls = wb.create_sheet('Lists')
    hdr = ['Sl', 'Ledger Name', 'Parent Group  (▼)', 'Head Group  (▼)', 'Note No (auto)', 'Note Label  (▼)', 'Line Item  (▼)',
           'Closing Balance FY%s (Tally: Dr = -ve)' % meta['cyL'], 'Closing Balance FY%s' % meta['pyL'], 'Sign (-1 = Dr item)',
           'Display Amount FY%s' % meta['cyL'], 'Display Amount FY%s' % meta['pyL'], 'Validation', 'Key (auto)', 'Type (auto)', 'Nature (auto)',
           'Appears in (auto)', 'Auto-map basis', 'Lookup (helper)']
    mp['A1'] = ENT_D + ' - Trial Balance'; mp['A1'].font = Font(bold=True, size=14)
    mp['A2'] = 'Financial year ending %s   (previous year: %s)' % (fmt_date(meta['cy_end']), fmt_date(meta['py_end'])); mp['A2'].font = Font(italic=True, color='595959')
    mp['A3'] = ('HOW TO USE: pick a new Note Label (column F) and then a Line Item (column G) from the yellow drop-downs - the Balance Sheet, P&L and all Notes update by formula. '
                'Parent / Head group (C, D) are labels you may correct. Validation (M): ✓ fine, ✗ pick a Line Item for the note, ! unusual balance, ? auto-map was a guess, ◇ derived entry.')
    mp['A3'].alignment = Alignment(wrap_text=True, vertical='top'); mp.merge_cells('A3:M3'); mp.row_dimensions[3].height = 44; mp['A3'].font = Font(bold=True, color='375623')
    HR = 4
    for i, h in enumerate(hdr, 1):
        c = mp.cell(HR, i, h); c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='375623' if i in (3, 4, 6, 7) else '1F3864')
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    mp.row_dimensions[HR].height = 46
    R0 = HR + 1
    blue = Font(color='0000FF'); yellow = PatternFill('solid', fgColor='FFF2CC'); orange = PatternFill('solid', fgColor='F8CBAD'); grey = PatternFill('solid', fgColor='E7E6E6')
    green_f = Font(color='006100')
    NLIST = len(CAT) + 1
    LR = 'Lists!$%s$2:$%s$' + str(NLIST + 400)
    for i, r in enumerate(rows):
        x = R0 + i
        cd = CATD[r['key']]
        vals = {1: i + 1, 2: r['name'], 3: r.get('parent', r['grp']), 4: r['grp'], 6: cd['label'], 7: cd['line'],
                8: round(r['cyC'] - r['cyD'], 2), 9: round(r['pyC'] - r['pyD'], 2)}
        for j, v in vals.items():
            c = mp.cell(x, j, v)
            if j in (8, 9): c.number_format = NF; c.font = blue
            if j in (3, 4, 6, 7): c.font = blue; c.fill = yellow
        if r['reason'] == 'default':
            mp.cell(x, 6).fill = orange; mp.cell(x, 7).fill = orange
        mp.cell(x, 20, '=IFERROR(IF(INDEX(Lists!$U$5:$U$104,MATCH($B%d,Lists!$Q$5:$Q$104,0))="\u2713 Active",MATCH($B%d,Lists!$Q$5:$Q$104,0),0),0)' % (x, x))
        mp.cell(x, 19, '=IF($T%d>0,IFERROR(MATCH(INDEX(Lists!$R$5:$R$104,$T%d)&"|"&INDEX(Lists!$S$5:$S$104,$T%d),%s,0),0),IFERROR(MATCH($F%d&"|"&$G%d,%s,0),0))' % (x, x, x, LR % ('G', 'G'), x, x, LR % ('G', 'G')))
        mp.cell(x, 5, '=IF($S%d=0,"",INDEX(%s,$S%d))' % (x, LR % ('H', 'H'), x)).font = green_f
        mp.cell(x, 10, '=IF($P%d="Dr",-1,1)' % x)
        mp.cell(x, 11, '=H%d*J%d' % (x, x)).number_format = NF
        mp.cell(x, 12, '=I%d*J%d' % (x, x)).number_format = NF
        mp.cell(x, 14, '=IF($S%d=0,"UNMAPPED",INDEX(%s,$S%d))' % (x, LR % ('C', 'C'), x))
        mp.cell(x, 15, '=IF($S%d=0,"BS",INDEX(%s,$S%d))' % (x, LR % ('E', 'E'), x))
        mp.cell(x, 16, '=IF($S%d=0,"Dr",INDEX(%s,$S%d))' % (x, LR % ('D', 'D'), x))
        mp.cell(x, 17, '=IF($S%d=0,"",INDEX(%s,$S%d))' % (x, LR % ('F', 'F'), x))
        basis = 'Derived (not in Tally extract)' if r.get('derived') else {'name': 'Rule (ledger name)', 'group': 'Rule (group)', 'default': 'DEFAULT - REVIEW'}[r['reason']]
        mp.cell(x, 18, basis)
        mp.cell(x, 13, ('=IF($T{x}>0,"\u21aa Re-mapped in the Lists sheet (panel on the right)",IF($N{x}="UNMAPPED","✗ Pick a Line Item that belongs to the Note Label",IF(LEFT($R{x},7)="Derived","◇ Derived entry (balancing figure, not a ledger)",'
                        'IF(AND(OR($K{x}<-0.5,$L{x}<-0.5),$N{x}<>"N3b",ISERROR(SEARCH("return",$B{x}))),"! Unusual (opposite-side) balance - check mapping",'
                        'IF($R{x}="DEFAULT - REVIEW","? Auto-map was a guess - please review","✓")))))').format(x=x))
        if r.get('derived'):
            for j in range(1, 13): mp.cell(x, j).fill = grey
            mp.cell(x, 6).fill = grey; mp.cell(x, 7).fill = grey
        r['row'] = x
    RL = R0 + max(len(rows), 1) - 1
    tr = RL + 1
    mp.cell(tr, 2, 'TOTAL of all lines (Cr - Dr) - should be nil').font = Font(bold=True)
    for j in (8, 9):
        c = mp.cell(tr, j, '=SUM(%s%d:%s%d)' % (CL(j), R0, CL(j), RL)); c.font = Font(bold=True); c.number_format = '#,##0.00;(#,##0.00);"OK - nil"'
    mp.cell(tr + 1, 2, 'of which: as received from Tally (before derived entries)')
    mp.cell(tr + 1, 8, '=%s-%s' % ('H%d' % tr, 'H%d' % (tr + 2))); mp.cell(tr + 1, 9, '=%s-%s' % ('I%d' % tr, 'I%d' % (tr + 2)))
    mp.cell(tr + 2, 2, 'of which: derived entries (opening stock, P&L A/c, closing-stock balancing entry)')
    mp.cell(tr + 2, 8, '=SUMIFS(H%d:H%d,R%d:R%d,"Derived*")' % (R0, RL, R0, RL)); mp.cell(tr + 2, 9, '=SUMIFS(I%d:I%d,R%d:R%d,"Derived*")' % (R0, RL, R0, RL))
    for rr in (tr + 1, tr + 2):
        for j in (8, 9): mp.cell(rr, j).number_format = NF
    for col, w in zip('ABCDEFGHIJKLMNOPQRS', [5, 46, 28, 24, 8, 40, 58, 20, 20, 8, 18, 18, 54, 14, 7, 8, 38, 26, 8]):
        mp.column_dimensions[col].width = w
    for col in 'NOPQRS':
        mp.column_dimensions[col].outlineLevel = 1
    mp.column_dimensions['S'].hidden = True; mp.column_dimensions['T'].hidden = True
    mp['S4'] = 'Lookup (helper)'; mp['T4'] = 'Re-map row (helper)'
    mp.freeze_panes = 'C5'
    mp.auto_filter.ref = 'A%d:M%d' % (HR, RL)
    from openpyxl.formatting.rule import FormulaRule
    mp.conditional_formatting.add('M%d:M%d' % (R0, RL + 60), FormulaRule(formula=['LEFT($M%d,1)="✗"' % R0], fill=PatternFill('solid', bgColor='FFC7CE', fgColor='FFC7CE'), font=Font(color='9C0006', bold=True)))
    mp.conditional_formatting.add('M%d:M%d' % (R0, RL + 60), FormulaRule(formula=['LEFT($M%d,1)="!"' % R0], fill=PatternFill('solid', bgColor='FFEB9C', fgColor='FFEB9C'), font=Font(color='9C5700')))
    mp.conditional_formatting.add('M%d:M%d' % (R0, RL + 60), FormulaRule(formula=['LEFT($M%d,1)="?"' % R0], fill=PatternFill('solid', bgColor='FCE4D6', fgColor='FCE4D6'), font=Font(color='833C0B')))
    mp.conditional_formatting.add('M%d:M%d' % (R0, RL + 60), FormulaRule(formula=['LEFT($M%d,1)="✓"' % R0], font=Font(color='006100')))
    mp.conditional_formatting.add('G%d:G%d' % (R0, RL + 60), FormulaRule(formula=['$N%d="UNMAPPED"' % R0], fill=PatternFill('solid', bgColor='FFC7CE', fgColor='FFC7CE')))

    def RNG(col): return "'Trial Balance'!$%s$%d:$%s$%d" % (col, R0, col, RL + 60)

    def SM(key, yr): return 'SUMIFS(%s,%s,"%s")' % (RNG('K' if yr == 'cy' else 'L'), RNG('N'), key)

    # ---------------- Workings ----------------
    W = wk
    W['A1'] = ENT + ' - Workings supporting the ICAI NCE statements'; W['A1'].font = Font(bold=True, size=13)
    bold = Font(bold=True); hf = PatternFill('solid', fgColor='D9E1F2'); italic_red = Font(italic=True, color='C00000')

    def head(r, text):
        W.cell(r, 1, text).font = Font(bold=True, color='FFFFFF')
        for j in range(1, 12): W.cell(r, j).fill = PatternFill('solid', fgColor='1F3864')

    head(3, 'A. Closing stock - not part of a Tally trial balance')
    for c_, t in (('A4', 'Item'), ('C4', 'FY%s' % meta['cyL']), ('D4', 'FY%s' % meta['pyL'])):
        W[c_] = t; W[c_].font = bold; W[c_].fill = hf
    W['A5'] = 'Net credit of all P&L ledgers incl. opening stock (Cr - Dr)'
    W['C5'] = '=SUMIFS(%s,%s,"PL")' % (RNG('H'), RNG('O'))
    W['D5'] = '=SUMIFS(%s,%s,"PL")' % (RNG('I'), RNG('O'))
    W['A6'] = 'Profit & Loss A/c (debit) in TB = profit appropriated to partners (key PLA)'
    W['C6'] = '=-SUMIFS(%s,%s,"PLA")' % (RNG('H'), RNG('N'))
    W['D6'] = '=-SUMIFS(%s,%s,"PLA")' % (RNG('I'), RNG('N'))
    W['A7'] = 'Closing stock - derived (= row 6 - row 5)'; W['C7'] = '=C6-C5'; W['D7'] = '=D6-D5'
    W['A8'] = 'Closing stock - ledger mapped to CSTK (if any)'; W['C8'] = '=' + SM('CSTK', 'cy'); W['D8'] = '=' + SM('CSTK', 'py')
    W['A9'] = 'Closing stock - YOUR OVERRIDE (type the physical-stock value here; leave blank to use ledger / derived)'
    W['C9'].font = blue; W['D9'].font = blue; W['C9'].fill = yellow; W['D9'].fill = yellow
    W['A10'] = 'Closing stock USED in Note 15 / Note 22'
    W['C10'] = '=IF(C9<>"",C9,IF(C8<>0,C8,IF($C$12="Y",0,C7)))'; W['D10'] = '=IF(D9<>"",D9,IF(D8<>0,D8,IF($C$12="Y",0,D7)))'
    W['A11'] = 'Opening stock ledger (TB)'; W['C11'] = '=' + SM('OS', 'cy'); W['D11'] = '=' + SM('OS', 'py')
    W['A12'] = 'P&L A/c treatment: N = TB profit already credited to partners (closing stock can be derived); Y = P&L A/c is an unappropriated balance (closing stock MUST be typed in row 9)'
    W['C12'] = toggle_default; W['C12'].font = blue; W['C12'].fill = yellow
    dvy = DataValidation(type='list', formula1='"Y,N"', allow_blank=False); W.add_data_validation(dvy); dvy.add('C12')
    W['A13'] = 'Check: PY derived closing stock vs CY opening-stock ledger (nil = TB is consistent)'; W['D13'] = '=D7-C11'
    W['A14'] = 'The derived closing stock is a BALANCING figure - confirm it against the stock statement.'; W['A14'].font = italic_red
    for r in range(5, 14):
        for c in 'CD': W['%s%d' % (c, r)].number_format = NF

    # B. PPE
    head(16, 'B. Property, plant & equipment - ledger-wise (a TB gives closing WDV only)')
    ph = ['Ledger', 'Class (Note 11)', 'Dep. rate (editable)', 'WDV prior year-end', 'WDV current year-end', 'CY additions (derived)', 'CY depreciation', 'PY dep - rate-implied',
          'PY dep - allocated to TB total', 'WDV at start of PY (gross-block proxy)', 'CY deductions (WDV removed)', 'CY dep - existing', 'CY dep - new assets']
    for j, h in enumerate(ph, 1):
        c = W.cell(17, j, h); c.font = bold; c.fill = hf; c.alignment = Alignment(wrap_text=True, vertical='center')
    W.row_dimensions[17].height = 48

    def cls(n):
        n = n.lower()
        if rx(r'\bland\b|plot', n): return 'Freehold land'
        if rx(r'building|shed|premises|factory', n): return 'Buildings'
        if rx(r'\bcars?\b|vehicle|bike|motor ?cycle|scooter|scooty|honda|suzuki|activa|two wheeler|truck|lorry|\bvan\b|\bauto\b|jeep|\bbus\b|tempo|tractor', n): return 'Vehicles'
        if rx(r'furniture|fixture|fitting|name board|almirah|rack|cabinet|interior', n): return 'Furniture & Fixtures'
        if rx(r'computer|laptop|printer|camera|phone|mobile|\btv\b|television|\bac\b|air cond|conditioner|splitair|cctv|office equip|battery|\bups\b|inverter|\bfan\b|scanner|projector|server|intercom|timer|lock system', n): return 'Office equipment'
        if rx(r'plant|machin|equipment|electric|tool|generator|crane|pump|compressor|weld|lathe|drill|instrument', n): return 'Plant and Equipment'
        return 'Others'

    DEF_RATE = {'Freehold land': 0.0, 'Buildings': 0.10, 'Plant and Equipment': 0.15, 'Office equipment': 0.15, 'Furniture & Fixtures': 0.10, 'Vehicles': 0.15, 'Others': 0.15}
    fa = [r for r in rows if r['key'] == 'PPE']
    P0 = 18
    if not fa:
        fa = [dict(name='(no fixed-asset ledgers found)', row=None, cyD=0, cyC=0, pyD=0, pyC=0)]
    PE = P0 + len(fa) - 1
    SUMNEW = 'SUMIFS($E$%d:$E$%d,$D$%d:$D$%d,0)' % (P0, PE, P0, PE)
    for i, r in enumerate(fa):
        x = P0 + i
        c_ = cls(r['name'])
        pyw, cyw = (r['pyD'] - r['pyC']), (r['cyD'] - r['cyC'])
        rate = DEF_RATE[c_]
        if pyw > 0 and 0 < cyw <= pyw:
            rr = 1 - cyw / pyw
            if 0.02 <= rr <= 0.6: rate = round(rr, 2)
        W.cell(x, 1, r['name']); W.cell(x, 2, c_)
        W.cell(x, 3, rate).number_format = '0%'; W.cell(x, 3).font = blue
        if r['row']:
            W.cell(x, 4, "='Trial Balance'!L%d" % r['row']); W.cell(x, 5, "='Trial Balance'!K%d" % r['row'])
        else:
            W.cell(x, 4, 0); W.cell(x, 5, 0)
        W.cell(x, 8, '=IF(C%d<1,D%d*C%d/(1-C%d),0)' % (x, x, x, x))
        W.cell(x, 9, '=IF($H$%d=0,0,H%d/$H$%d*SUMIFS(%s,%s,"N25a"))' % (PE + 1, x, PE + 1, RNG('L'), RNG('N')))
        W.cell(x, 10, '=D%d+I%d' % (x, x))
        W.cell(x, 11, '=IF(AND(D%d>0,E%d=0),D%d,0)' % (x, x, x))
        W.cell(x, 12, '=IF(D%d>0,IF(E%d=0,0,IF(E%d<=D%d,D%d-E%d,D%d*C%d)),0)' % (x, x, x, x, x, x, x, x))
        W.cell(x, 13, '=IF(AND(D%d=0,E%d>0),MAX(0,SUMIFS(%s,%s,"N25a")-SUM($L$%d:$L$%d))*E%d/%s,0)' % (x, x, RNG('K'), RNG('N'), P0, PE, x, SUMNEW))
        W.cell(x, 7, '=L%d+M%d' % (x, x))
        W.cell(x, 6, '=IF(D%d=0,E%d+M%d,IF(E%d<=D%d,0,E%d-D%d+L%d))' % (x, x, x, x, x, x, x, x))
        for j in range(4, 14):
            if j != 3: W.cell(x, j).number_format = NF
    # editable class list (feeds the drop-down above AND the column headings / SUMIFS of Note 11)
    W.cell(16, 15, 'Asset classes - edit the names here (max 7 = the 7 columns of Note 11)').font = bold
    W.cell(17, 15, 'Class list (drop-down source)').font = bold; W.cell(17, 15).fill = hf
    for k_, nm_ in enumerate(DEF_RATE.keys()):
        c_ = W.cell(18 + k_, 15, nm_); c_.font = blue; c_.fill = yellow
    W.column_dimensions['O'].width = 30
    W.cell(26, 15, 'Ledgers whose class is not in this list (must be 0):').font = italic_red
    W.cell(27, 15, '=SUMPRODUCT(--($B$%d:$B$%d<>""),--(COUNTIF($O$18:$O$24,$B$%d:$B$%d)=0))' % (P0, PE, P0, PE))
    W.cell(28, 15, 'If you rename a class, re-pick the new name for the ledgers that used the old one; Note 11 columns follow this list.').font = Font(italic=True, size=9)
    dvcls = DataValidation(type='list', formula1='$O$18:$O$24', allow_blank=False, showErrorMessage=True, errorTitle='Pick from list',
                           error='Choose the class from the drop-down (the list can be edited in Workings, column O).', promptTitle='Class (Note 11)',
                           prompt='Pick from the list. To change the list itself, edit Workings column O (rows 18-24).', showInputMessage=True)
    W.add_data_validation(dvcls); dvcls.add('B%d:B%d' % (P0, PE))
    t = PE + 1
    W.cell(t, 1, 'Total').font = bold
    for j in range(4, 14):
        W.cell(t, j, '=SUM(%s%d:%s%d)' % (CL(j), P0, CL(j), PE)).number_format = NF; W.cell(t, j).font = bold
    W.cell(t + 1, 1, 'Check vs TB: WDV totals / depreciation - all should be nil')
    W.cell(t + 1, 4, '=D%d-SUMIFS(%s,%s,"PPE")' % (t, RNG('L'), RNG('N'))); W.cell(t + 1, 5, '=E%d-SUMIFS(%s,%s,"PPE")' % (t, RNG('K'), RNG('N')))
    W.cell(t + 1, 7, '=G%d-SUMIFS(%s,%s,"N25a")' % (t, RNG('K'), RNG('N'))); W.cell(t + 1, 9, '=I%d-SUMIFS(%s,%s,"N25a")' % (t, RNG('L'), RNG('N')))
    for j in (4, 5, 7, 9): W.cell(t + 1, j).number_format = '#,##0.00;(#,##0.00);"OK - nil"'
    W.cell(t + 2, 1, ('Notes: (i) Original cost / accumulated depreciation are not in a TB; Note 11 shows the block at WDV as at the start of the previous year (derived = closing WDV + previous-year '
                      'depreciation, assuming no additions/disposals that year) with depreciation accumulated from that date. (ii) Previous-year depreciation by class is allocated pro-rata to rate-implied '
                      'depreciation (rates inferred from the ledger movement - editable in column C). (iii) Current-year addition = new ledger: closing WDV + the depreciation not explained by existing ledgers. '
                      '(iv) PPE ledgers are listed as at generation - to add/remove a ledger edit this table.')).alignment = Alignment(wrap_text=True, vertical='top')
    W.merge_cells(start_row=t + 2, start_column=1, end_row=t + 2, end_column=10); W.row_dimensions[t + 2].height = 75

    def PR_(col): return 'Workings!$%s$%d:$%s$%d' % (col, P0, col, PE)

    # C. Partners
    plist, generic = [], []
    for r in rows:
        if r['key'] in ('N3a', 'N3b'):
            nm = re.sub(r'\b(capital|current|contribution|drawings?|withdrawals?|a/c|account|accounts|ac|of|the|partner)\b', ' ', r['name'], flags=re.I)
            nm = re.sub(r'[^\w\.\s&]', ' ', nm); nm = re.sub(r'\s+', ' ', nm).strip()
            if not nm:
                generic.append(r['name']); continue
            if canon(nm) not in [canon(p) for p in plist]:
                plist.append(nm)
    if not plist:
        plist = ['Proprietor']
    elif generic:
        msg = ('Capital-account ledger(s) %s carry no partner name - they are shown against the first partner (%s). Move them in Workings C if they belong to someone else.'
               % (', '.join('"%s"' % g_ for g_ in generic), plist[0]))
        log('  ! ' + msg); meta.setdefault('notes', []).append(msg)
    warn_partners = len(plist) > 4
    plist = plist[:4]
    base = t + 4
    head(base, "C. Owners'/partners' accounts - movement derived from the TBs")
    ch = ['Particulars', '', 'Opening (= TB prior year-end)', 'Closing (TB)', 'Share of profit', 'Remuneration', 'Interest on capital  (INPUT)', 'Withdrawals (net) - balancing', 'Capital introduced  (INPUT)']
    for j, h in enumerate(ch, 1):
        c = W.cell(base + 1, j, h); c.font = bold; c.fill = hf; c.alignment = Alignment(wrap_text=True, vertical='center')
    W.row_dimensions[base + 1].height = 45
    n = len(plist)
    RATC, REMC = {}, {}
    rr_ = base + 2
    W.cell(rr_, 1, 'Profit-sharing ratio (editable; must total 100%)').font = bold; rr_ += 1
    for p in plist:
        W.cell(rr_, 1, '   %s' % p); W.cell(rr_, 3, round(1.0 / n, 6)).number_format = '0.00%'; W.cell(rr_, 3).font = blue; W.cell(rr_, 3).fill = yellow
        RATC[p] = '$C$%d' % rr_; rr_ += 1
    W.cell(rr_ - n, 4, 'Assumed equal (not stated in a TB) - please confirm vs partnership deed').font = italic_red
    W.cell(rr_, 1, "Partners' remuneration - share (editable; must total 100%)").font = bold; rr_ += 1
    for p in plist:
        W.cell(rr_, 1, '   %s' % p); W.cell(rr_, 3, round(1.0 / n, 6)).number_format = '0.00%'; W.cell(rr_, 3).font = blue; W.cell(rr_, 3).fill = yellow
        REMC[p] = '$C$%d' % rr_; rr_ += 1
    y = rr_ + 1
    prow = {}
    for acct, key in (('3a', 'N3a'), ('3b', 'N3b')):
        for p in plist:
            W.cell(y, 1, '%s - %s' % (p, 'Capital a/c' if acct == '3a' else 'Current a/c'))
            esc_ = p.replace('~', '~~').replace('*', '~*').replace('?', '~?')
            if p == 'Proprietor':
                pats = ['"*"']
            else:
                pats = ['"*%s*"' % esc_ if len(p) > 2 else '"%s *"' % esc_]
                if p == plist[0]:
                    pats += ['"%s"' % g_.replace('"', '""').replace('~', '~~').replace('*', '~*').replace('?', '~?') for g_ in generic]
            W.cell(y, 3, '=' + '+'.join('SUMIFS(%s,%s,"%s",%s,%s)' % (RNG('L'), RNG('N'), key, RNG('B'), c_) for c_ in pats))
            W.cell(y, 4, '=' + '+'.join('SUMIFS(%s,%s,"%s",%s,%s)' % (RNG('K'), RNG('N'), key, RNG('B'), c_) for c_ in pats))
            if acct == '3a':
                W.cell(y, 5, '=$C$6*%s' % RATC[p])
                W.cell(y, 6, '=SUMIFS(%s,%s,"PR")*%s' % (RNG('K'), RNG('N'), REMC[p])); W.cell(y, 7, 0)
                W.cell(y, 9, 0)
                for jj in (7, 9): W.cell(y, jj).font = blue; W.cell(y, jj).fill = yellow
                W.cell(y, 8, '=C%d+I%d+E%d+F%d+G%d-D%d' % (y, y, y, y, y, y))
            else:
                W.cell(y, 5, 0); W.cell(y, 6, 0); W.cell(y, 7, 0); W.cell(y, 8, '=C%d-D%d' % (y, y))
            for j in range(3, 10): W.cell(y, j).number_format = NF
            prow[(acct, p)] = y; y += 1
    W.cell(y, 1, "Interest on partners' capital charged in P&L (Note 24(b)). Type each partner's interest in the yellow column G above; until then it is included in 'Withdrawals (net)'.")
    W.cell(y, 7, '=' + SM('N24b', 'cy')).number_format = NF
    INT_RNG = 'G%d:G%d' % (prow[('3a', plist[0])], prow[('3a', plist[-1])])
    W.cell(y + 1, 1, 'Check: sum of partners closing balances vs TB (mapped N3a + N3b)')
    W.cell(y + 1, 4, '=SUM(D%d:D%d)-%s-%s' % (prow[('3a', plist[0])], y - 1, SM('N3a', 'cy'), SM('N3b', 'cy'))).number_format = '#,##0.00;(#,##0.00);"OK - nil"'
    # D. checks
    ck = y + 3
    head(ck, 'D. Integrity checks (all should show OK - nil)')
    checks = [("Balance Sheet - total liabilities = total assets, current year", "='Balance Sheet'!D24-'Balance Sheet'!D46"),
              ("Balance Sheet - total liabilities = total assets, previous year", "='Balance Sheet'!F24-'Balance Sheet'!F46"),
              ("P&L profit for the year = Profit & Loss A/c in TB, current year (only when P&L A/c treatment = N)", "=IF($C$12=\"N\",'Statement of P&L'!D44-C6,0)"),
              ("P&L profit for the year = Profit & Loss A/c in TB, previous year (only when P&L A/c treatment = N)", "=IF($C$12=\"N\",'Statement of P&L'!F44-D6,0)"),
              ("Previous-year closing stock = current-year opening stock ledger", "=IF(OR($C$12=\"Y\",D9<>\"\"),0,D13)"),
              ("Share of profit credited to partners (Note 3) = profit for the year, current year (only when treatment = N)", "=IF($C$12=\"N\",'Note 1 to 3'!I17-'Statement of P&L'!D44,0)"),
              ("Interest on capital typed in Workings C = P&L interest (checked only if you typed any)", "=IF(SUM(%s)=0,0,SUM(%s)-%s)" % (INT_RNG, INT_RNG, SM('N24b', 'cy'))),
              ("Profit-sharing ratios total 100%", "=SUM(%s)-1" % ','.join(RATC.values())),
              ("Remuneration shares total 100%", "=SUM(%s)-1" % ','.join(REMC.values())),
              ("Trial Balance (incl. derived entries) nets to nil, current year", "='Trial Balance'!H%d" % tr),
              ("Trial Balance (incl. derived entries) nets to nil, previous year", "='Trial Balance'!I%d" % tr),
              ("Closing stock ledger in the TB = closing stock derived from the P&L figures, current year", "=IF(AND(C8<>0,C9=\"\"),C7-C8,0)"),
              ("Closing stock ledger in the TB = closing stock derived from the P&L figures, previous year", "=IF(AND(D8<>0,D9=\"\"),D7-D8,0)"),
              ("Tally PDF: nett profit = profit in this workbook, current year", "=IF(ISNUMBER(C{e0}),E{e0}-C{e0},0)"),
              ("Tally PDF: nett profit = profit in this workbook, previous year", "=IF(ISNUMBER(D{e0}),F{e0}-D{e0},0)"),
                                          ("Tally PDF: Sales Accounts = Sales ledgers in this workbook, current year", "=IF(ISNUMBER(C{e2}),E{e2}-C{e2},0)"),
              ("Tally PDF: Sales Accounts = Sales ledgers in this workbook, previous year", "=IF(ISNUMBER(D{e2}),F{e2}-D{e2},0)"),
                                          ("Ledgers left UNMAPPED (count)", '=COUNTIF(%s,"UNMAPPED")' % RNG('N'))]
    EB = ck + len(checks) + 3          # section E (Tally PDF cross-check) starts here
    for i, (l, f) in enumerate(checks):
        f = f.replace('{e0}', str(EB + 2)).replace('{e1}', str(EB + 3)).replace('{e2}', str(EB + 4)).replace('{e3}', str(EB + 5))
        W.cell(ck + 1 + i, 1, l); c = W.cell(ck + 1 + i, 4, f); c.number_format = '#,##0.00;(#,##0.00);"OK - nil"'
    CK0, CK1 = ck + 1, ck + len(checks)
    head(EB, 'E. Cross-check with the Tally Profit & Loss A/c and Balance Sheet PDFs (typed from the PDFs - blank if no PDF was supplied)')
    for j, h in enumerate(['Item', '', 'Tally PDF FY%s' % meta['cyL'], 'Tally PDF FY%s' % meta['pyL'], 'This workbook FY%s' % meta['cyL'], 'This workbook FY%s' % meta['pyL']], 1):
        c = W.cell(EB + 1, j, h); c.font = bold; c.fill = hf; c.alignment = Alignment(wrap_text=True)
    cpd, ppd = cy.get('pdf', {}), py.get('pdf', {})
    erows = [('Nett profit (Tally P&L)', 'profit', "='Statement of P&L'!D44", "='Statement of P&L'!F44"),
             ('Balance sheet total (Tally)', 'bs_total', "='Balance Sheet'!D24", "='Balance Sheet'!F24"),
             ('Sales Accounts (net of returns)', 'sales', '=SUMIFS(%s,%s,"Sales Accounts")' % (RNG('H'), RNG('D')), '=SUMIFS(%s,%s,"Sales Accounts")' % (RNG('I'), RNG('D'))),
             ('Purchase Accounts (net of returns)', 'purchases', '=-SUMIFS(%s,%s,"Purchase Accounts")' % (RNG('H'), RNG('D')), '=-SUMIFS(%s,%s,"Purchase Accounts")' % (RNG('I'), RNG('D'))),
             ('Closing stock', 'cs', '=C10', '=D10'), ('Opening stock', 'os', '=C11', '=D11')]
    for i, (lbl_, k_, fc, fp) in enumerate(erows):
        r_ = EB + 2 + i
        W.cell(r_, 1, lbl_)
        for col, src in ((3, cpd), (4, ppd)):
            v_ = src.get(k_)
            c = W.cell(r_, col, v_ if v_ is not None else None); c.number_format = NF; c.font = blue
        W.cell(r_, 5, fc).number_format = NF; W.cell(r_, 6, fp).number_format = NF
        for col, a_, b_ in ((7, 'C', 'E'), (8, 'D', 'F')):
            W.cell(r_, col, '=IF(ISNUMBER(%s%d),%s%d-%s%d,"")' % (a_, r_, b_, r_, a_, r_)).number_format = '#,##0.00;(#,##0.00);"nil"'
    W.cell(EB + 1, 7, 'Difference CY'); W.cell(EB + 1, 8, 'Difference PY')
    for col in (7, 8):
        W.cell(EB + 1, col).font = bold; W.cell(EB + 1, col).fill = hf
    W.cell(EB + 9, 1, ('Why the Balance Sheet total differs from Tally: Tally nets debit and credit balances inside each group (e.g. creditors with debit balances, duties & taxes), '
                       'whereas this workbook presents each ledger on its natural side (debit balances of creditors as assets, credit balances of debtors / GST / TDS as liabilities) as Schedule III / '
                       'the ICAI format requires - so both sides of the balance sheet are larger by the same amount. Purchases and Sales are compared ledger-group by ledger-group (Sales Accounts / Purchase Accounts as in Tally); some purchase ledgers (services taken, '
                       'transport, sub-contract) are presented under Other expenses (Note 26) and operating income booked under Direct Incomes is shown in Revenue (Note 19).')).alignment = Alignment(wrap_text=True, vertical='top')
    W.merge_cells(start_row=EB + 9, start_column=1, end_row=EB + 9, end_column=8); W.row_dimensions[EB + 9].height = 62
    for col, wd in zip('ABCDEFGHIJKLM', [78, 22, 18, 18, 18, 18, 18, 20, 20, 22, 18, 18, 18]):
        W.column_dimensions[col].width = wd

    # ---------------- wire catalogue lines to Trial Balance ----------------
    refstyle = {}
    for sh in set(tg[0] for tg in TG):
        for row in wb[sh].iter_rows():
            for c in row:
                if isinstance(c.value, (int, float)) and c.number_format != 'General':
                    refstyle.setdefault((sh, c.column_letter), c)
    for sh, row, cc, pc, key in TG:
        ws = wb[sh]
        for col, yr in ((cc, 'cy'), (pc, 'py')):
            c = ws['%s%d' % (col, row)]
            if c.number_format == 'General' and (sh, col) in refstyle:
                c._style = copy.copy(refstyle[(sh, col)]._style)
            c.value = '=' + SM(key, yr)
    # ---------------- template fixes ----------------
    ws_pl['D31'] = '=D28-D30'; ws_pl['F31'] = '=F28-F30'; ws_pl['D38'] = '=D31-D36'; ws_pl['F38'] = '=F31-F36'
    for r_ in (30, 31):
        for c_ in 'DF': ws_pl['%s%d' % (c_, r_)].number_format = ws_pl['D28'].number_format
    ws_bs['D33'] = "='Notes to BS 12 to 18'!G20+'Notes to BS 12 to 18'!G36"; ws_bs['F33'] = "='Notes to BS 12 to 18'!J20+'Notes to BS 12 to 18'!J36"
    # surplus (Note 4(d)) when P&L A/c is an unappropriated balance
    n46['G11'] = '=%s+IF(Workings!$C$12="Y",\'Statement of P&L\'!D44,0)' % SM('N4-r11', 'cy')
    n46['I11'] = '=%s+IF(Workings!$C$12="Y",\'Statement of P&L\'!F44,0)' % SM('N4-r11', 'py')
    # stock lines
    n1218['I135'] = '=Workings!C10'; n1218['J135'] = '=Workings!D10'
    npl['E53'] = '=Workings!C11'; npl['G53'] = '=Workings!D11'; npl['E58'] = '=Workings!C10'; npl['G58'] = '=Workings!D10'
    n710['B25'] = 'Total outstanding dues of creditors other than micro, small and medium enterprises (MSME split not available)'
    n710['B47'] = 'Other payables - outstanding expenses & provisions / others (specify nature)'
    n1218['B111'] = 'Other loans and advances (specify nature)'
    npl['B45'] = 'Purchases of stock-in-trade (net of purchase returns)'
    npl['B113'] = 'Miscellaneous expenses (incl. bank charges and other minor items)'
    # ---------------- Note 3 ----------------
    for i, p in enumerate(plist):
        r3 = 13 + i; r3b = 23 + i; a = prow[('3a', p)]; b = prow[('3b', p)]
        n13['B%d' % r3] = p; n13['C%d' % r3] = '=Workings!%s' % RATC[p]; n13['C%d' % r3].number_format = '0%'
        n13['D%d' % r3] = '=Workings!C%d' % a; n13['E%d' % r3] = '=Workings!I%d' % a; n13['F%d' % r3] = '=Workings!F%d' % a; n13['G%d' % r3] = '=Workings!G%d' % a
        n13['H%d' % r3] = '=Workings!H%d' % a; n13['I%d' % r3] = '=Workings!E%d' % a
        n13['B%d' % r3b] = p; n13['C%d' % r3b] = '=Workings!%s' % RATC[p]; n13['C%d' % r3b].number_format = '0%'
        n13['D%d' % r3b] = '=Workings!C%d' % b; n13['E%d' % r3b] = 0; n13['F%d' % r3b] = 0; n13['G%d' % r3b] = 0
        n13['H%d' % r3b] = '=Workings!H%d' % b; n13['I%d' % r3b] = 0
    for k in range(len(plist), 4):
        for r3 in (13 + k, 23 + k):
            for c_ in 'BCDEFGHI': n13['%s%d' % (c_, r3)] = None
    n13['F18'] = '=' + SM('PR', 'py'); n13['G18'] = '=' + SM('N24b', 'py'); n13['I18'] = '=Workings!D6'; n13['E18'] = 0; n13['H18'] = 0
    n13['D18'] = '=%s-F18-G18-I18' % SM('N3a', 'py')
    n13['D28'] = '=' + SM('N3b', 'py')
    for c_ in 'EFGHI': n13['%s28' % c_] = 0
    n13['B30'] = ("Notes: (1) Partners' share of profit and remuneration are assumed in the ratios shown in Workings C (not available from a TB). (2) Interest on capital charged in the P&L is "
                  "credited to partners' accounts; unless the partner-wise interest / capital introduced are typed into Workings C they are included in 'Withdrawals during the year' (net). (3) Previous-year row: "
                  "opening balance is derived (closing balance less previous-year appropriations) and is net of that year's drawings / capital introduced.")
    n13['B30'].alignment = Alignment(wrap_text=True, vertical='top'); n13.merge_cells('B30:J30'); n13.row_dimensions[30].height = 75
    # ---------------- Note 11 ----------------
    colmap = {'Freehold land': 'C', 'Buildings': 'D', 'Plant and Equipment': 'E', 'Office equipment': 'F', 'Furniture & Fixtures': 'G', 'Vehicles': 'H', 'Others': 'I'}
    sy = meta['cy_start'].year; py_start = meta['py_start'].year

    def sif(col, cl_): return '=SUMIFS(%s,%s,Workings!$O$%d)' % (PR_(col), PR_('B'), 18 + list(colmap).index(cl_))
    lab11 = {9: 'At 1 April %d' % sy, 10: 'Additions', 11: 'Deductions/Adjustments', 12: 'At 1 April %d' % py_start, 13: 'Additions', 14: 'Deductions/Adjustments',
             15: 'At 31 March %d' % cyY, 16: 'At 31 March %d' % pyY, 18: 'At 1 April %d' % sy, 19: 'Charge for the year', 20: 'Deductions/Adjustments', 21: 'At 1 April %d' % py_start,
             22: 'Charge for the year', 23: 'Deductions/Adjustments', 24: 'At 31 March %d' % cyY, 25: 'At 31 March %d' % pyY, 27: 'At 31 March %d' % pyY, 28: 'At 31 March %d' % cyY}
    for r_, l in lab11.items(): n11['B%d' % r_] = l
    for cl_ in 'CDEFGHI':
        nm = [k for k, v in colmap.items() if v == cl_][0]
        n11['%s7' % cl_] = '=Workings!$O$%d' % (18 + list(colmap).index(nm))
        n11['%s12' % cl_] = sif('J', nm); n11['%s13' % cl_] = 0; n11['%s14' % cl_] = 0
        n11['%s16' % cl_] = '=%s12+%s13-%s14' % (cl_, cl_, cl_)
        n11['%s9' % cl_] = '=%s16' % cl_; n11['%s10' % cl_] = sif('F', nm); n11['%s11' % cl_] = sif('K', nm)
        n11['%s15' % cl_] = '=%s9+%s10-%s11' % (cl_, cl_, cl_)
        n11['%s21' % cl_] = 0; n11['%s22' % cl_] = sif('I', nm); n11['%s23' % cl_] = 0
        n11['%s25' % cl_] = '=%s21+%s22-%s23' % (cl_, cl_, cl_)
        n11['%s18' % cl_] = '=%s25' % cl_; n11['%s19' % cl_] = sif('G', nm); n11['%s20' % cl_] = 0
        n11['%s24' % cl_] = '=%s18+%s19-%s20' % (cl_, cl_, cl_)
        n11['%s27' % cl_] = '=%s16-%s25' % (cl_, cl_); n11['%s28' % cl_] = '=%s15-%s24' % (cl_, cl_)
    for r_ in list(range(9, 17)) + list(range(18, 26)) + [27, 28]:
        n11['J%d' % r_] = '=SUM(C%d:I%d)' % (r_, r_)
    n11['B29'] = 'Note: original cost and accumulated depreciation before the start of the previous year are not available; the gross block is stated at WDV as at 1 April %d (see Workings B).' % py_start
    n11['B29'].font = Font(italic=True, size=9)
    ilab = {35: 'At 1 April %d' % sy, 36: 'Additions', 37: 'Deductions/Adjustments', 38: 'At 1 April %d' % py_start, 39: 'Additions', 40: 'Deductions/Adjustments', 41: 'At 31 March %d' % cyY,
            42: 'At 31 March %d' % pyY, 44: 'At 1 April %d' % sy, 45: 'Charge for the year', 46: 'Deductions/Adjustments', 47: 'At 1 April %d' % py_start, 48: 'Charge for the year',
            49: 'Deductions/Adjustments', 50: 'At 31 March %d' % cyY, 51: 'At 31 March %d' % pyY, 53: 'At 31 March %d' % pyY, 54: 'At 31 March %d' % cyY}
    for r_, l in ilab.items(): n11['B%d' % r_] = l
    for r_ in list(range(35, 43)) + list(range(44, 52)):
        for cl_ in 'CDEFGHIJK': n11['%s%d' % (cl_, r_)] = 0
        n11['L%d' % r_] = '=SUM(C%d:K%d)' % (r_, r_)
    for cl_ in 'CDEFGHIJKL':
        n11['%s53' % cl_] = '=%s42-%s51' % (cl_, cl_); n11['%s54' % cl_] = '=%s41-%s50' % (cl_, cl_)
    # ---------------- text replacements ----------------
    cy_end_s, py_end_s = fmt_date(meta['cy_end']), fmt_date(meta['py_end'])

    def rep_year(ws):
        for row in ws.iter_rows():
            lit = [c for c in row if isinstance(c.value, str) and '20XX' in c.value and not c.value.startswith('=')]
            alt = 0
            for c in lit:
                v = c.value
                if 'April 20XX' in v:
                    c.value = v.replace('April 20XX', 'April %d' % sy); continue
                if '31st March, 20XX' in v or ('March 20XX' in v and 'ended' in v.lower()):
                    c.value = v.replace('20XX', str(cyY)); continue
                c.value = v.replace('20XX', str(cyY) if alt == 0 else str(pyY)); alt ^= 1
    for ws in (ws_bs, ws_pl, n13, n46, n710, n11, n1218, npl): rep_year(ws)
    for ws in (ws_bs, n13, n46, n710, n11, n1218, npl, ws_pl):
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and not c.value.startswith('='):
                    if c.value.startswith('Name of the Non-Corporate Entity') or c.value.strip() == 'Name of the Entity': c.value = ENT_D
                    if c.value.startswith('Balance Sheet as at'): c.value = 'Balance Sheet as at ' + cy_end_s
                    if c.value.startswith('Statement of Profit and Loss for the year ended'): c.value = 'Statement of Profit and Loss for the year ended ' + cy_end_s
                    if c.value.startswith('(Amount in Rs. XX)'): c.value = '(Amount in Rs.)'
    ws_bs['D4'] = '31 March %d' % cyY if meta['cy_end'].month == 3 and meta['cy_end'].day == 31 else cy_end_s
    ws_bs['F4'] = '31 March %d' % pyY if meta['py_end'].month == 3 and meta['py_end'].day == 31 else py_end_s
    # Notes 1 & 2 (house-style wording)
    nature = meta.get('nature') or '[nature of business - to be completed]'
    n13['A6'] = ('%s is a non-corporate entity engaged in the business of %s. The firm/entity is registered and operates from %s. These financial statements have been prepared for the year ended %s '
                 'to present the state of affairs and the results of operations of the entity for the reporting period.%s'
                 % (ENT, nature, meta['address'] or '[address]', cy_end_s, (' Partners / proprietor: %s.' % ', '.join(plist))))
    n13['A8'] = ("1. Basis of preparation: The financial statements have been prepared under the historical cost convention on the accrual basis of accounting and in accordance with the ICAI Technical/Guidance Note on financial statements of non-corporate entities and applicable Accounting Standards.\n"
                 "2. Use of estimates: The preparation of financial statements requires management to make estimates and assumptions that affect the reported amounts of assets, liabilities, income and expenses. Actual results could differ from those estimates.\n"
                 "3. Revenue recognition: Revenue is recognised when it is earned and no significant uncertainty exists as to its realisation.\n"
                 "4. Property, plant & equipment and depreciation: Fixed assets are stated at cost less depreciation. Depreciation is provided on WDV basis at the rates considered appropriate.\n"
                 "5. Inventories: Inventories are valued at lower of cost and net realisable value.\n"
                 "6. Investments: Long-term investments are stated at cost; current investments at lower of cost and fair value.\n"
                 "7. Employee benefits: Contributions to defined contribution schemes are charged to the statement of profit and loss as incurred.\n"
                 "8. Provisions: Provisions are recognised for present obligations that can be reliably estimated.")
    for c_, h in (('A6', 62), ('A8', 190)):
        n13[c_].alignment = Alignment(wrap_text=True, vertical='top'); n13.row_dimensions[int(c_[1:])].height = h
        try: n13.merge_cells('%s:J%s' % (c_, c_[1:]))
        except Exception: pass
    ws_bs['A52'] = 'Balance check (Liabilities = Assets)'
    ws_bs['D52'] = '=IF(ABS(D24-D46)<0.01,"✓ Balanced","⚠ Mismatch - see Workings D")'; ws_bs['F52'] = '=IF(ABS(F24-F46)<0.01,"✓ Balanced","⚠ Mismatch - see Workings D")'
    ws_bs['A52'].font = Font(italic=True, size=9)
    # ---------------- Lists ----------------
    for j, h in enumerate(['Note label', 'Line item', 'Key', 'Nature', 'Type', 'Appears in', 'Label|Line (lookup)', 'Note no', 'Note labels (unique)', 'Parent groups', 'Head groups'], 1):
        c = ls.cell(1, j, h); c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='1F3864')
    for i, c_ in enumerate(CAT, 2):
        mm = re.match(r'^Note (\d+[a-z]?)', c_['label'])
        for j, v in enumerate([c_['label'], c_['line'], c_['key'], c_['nat'], c_['typ'], c_['loc'], c_['label'] + '|' + c_['line'], mm.group(1) if mm else ''], 1):
            ls.cell(i, j, v)
    labels = []
    for c_ in CAT:
        if c_['label'] not in labels: labels.append(c_['label'])
    for i, l_ in enumerate(labels, 2): ls.cell(i, 9, l_)
    heads = list(HEAD_ORDER[:-3]) + [h for h in ['Stock-in-Hand'] if h not in HEAD_ORDER]
    for e_ in ents:
        if e_['grp'] not in heads and e_['grp'] not in ('Opening Stock', 'Profit & Loss A/c', 'Excluded'): heads.append(e_['grp'])
    parents = []
    for h in heads + ['Outstanding Expenses & Provisions', 'Staff Salaries A/c', 'Labour Wages A/c']:
        if h not in parents: parents.append(h)
    for e_ in ents:
        pr_ = e_.get('parent', e_['grp'])
        if pr_ not in parents and e_['grp'] not in ('Opening Stock', 'Profit & Loss A/c', 'Excluded'): parents.append(pr_)
    parents = sorted(set(parents), key=lambda x: x.lower())
    for i, g in enumerate(parents, 2): ls.cell(i, 10, g)
    for i, g in enumerate(heads + ['Opening Stock', 'Profit & Loss A/c', 'Excluded'], 2): ls.cell(i, 11, g)
    for col, wd in zip('ABCDEFGHIJK', [48, 70, 16, 8, 8, 40, 8, 8, 48, 36, 30]): ls.column_dimensions[col].width = wd
    ls.column_dimensions['G'].hidden = True
    dvC = DataValidation(type='list', formula1='Lists!$J$2:$J$%d' % (len(parents) + 1), allow_blank=True, showErrorMessage=False)
    dvD = DataValidation(type='list', formula1='Lists!$K$2:$K$%d' % (len(heads) + 4), allow_blank=True, showErrorMessage=False)
    dvF = DataValidation(type='list', formula1='Lists!$I$2:$I$%d' % (len(labels) + 1), allow_blank=False, showErrorMessage=True, errorTitle='Pick from list',
                         error='Please choose a Note Label from the drop-down list.', promptTitle='Note label', prompt='Choose the note, then pick the Line Item in the next column.', showInputMessage=True)
    dvG = DataValidation(type='list', formula1='OFFSET(Lists!$B$1,MATCH($F%d,Lists!$A$1:$A$%d,0)-1,0,COUNTIF(Lists!$A$1:$A$%d,$F%d),1)' % (R0, NLIST, NLIST, R0),
                         allow_blank=False, showErrorMessage=True, errorTitle='Pick from list', error='Choose a Line Item from the drop-down (it lists only lines of the chosen Note Label).',
                         promptTitle='Line item', prompt='Lists only the lines of the Note Label chosen in the previous column.', showInputMessage=True)
    for dv_, col_ in ((dvC, 'C'), (dvD, 'D'), (dvF, 'F'), (dvG, 'G')):
        mp.add_data_validation(dv_); dv_.add('%s%d:%s%d' % (col_, R0, col_, RL + 60))
    # ---------------- Re-map panel on the Lists sheet ----------------
    PR0, PR1 = 5, 104
    ls['Q1'] = 'RE-MAP A LEDGER  -  move any ledger to any note / line of the financial statements'; ls['Q1'].font = Font(bold=True, size=13, color='1F3864')
    ls['Q2'] = ('HOW: in the yellow cells choose (1) the LEDGER from the drop-down, (2) the NOTE it should go to, (3) the LINE ITEM of that note. The Balance Sheet, P&L and all notes update at once. '
                'To undo, clear the three yellow cells of that row. Column T shows where the tool had put the ledger; column U must say "Active".')
    ls['Q2'].alignment = Alignment(wrap_text=True, vertical='top'); ls.merge_cells('Q2:U2'); ls.row_dimensions[2].height = 48; ls['Q2'].font = Font(color='375623', bold=True)
    for j, h in enumerate(['1. Ledger (pick)', '2. Move to Note (pick)', '3. Line item (pick)', 'Where the tool had put it (automatic)', 'Status'], 17):
        c = ls.cell(4, j, h); c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='375623' if j < 20 else '1F3864'); c.alignment = Alignment(wrap_text=True, vertical='center')
    ls.row_dimensions[4].height = 30
    TBF, TBG, TBB = "'Trial Balance'!$F$%d:$F$%d" % (R0, RL), "'Trial Balance'!$G$%d:$G$%d" % (R0, RL), "'Trial Balance'!$B$%d:$B$%d" % (R0, RL)
    for r_ in range(PR0, PR1 + 1):
        for j in (17, 18, 19):
            c = ls.cell(r_, j); c.fill = yellow; c.font = blue
        ls.cell(r_, 20, '=IF(Q%d="","",IFERROR(INDEX(%s,MATCH(Q%d,%s,0))&"  /  "&INDEX(%s,MATCH(Q%d,%s,0)),"ledger not found"))' % (r_, TBF, r_, TBB, TBG, r_, TBB)).font = Font(color='595959')
        ls.cell(r_, 21, '=IF(Q%d="","",IF(ISNA(MATCH(Q%d,%s,0)),"\u2717 Ledger not found",IF(OR(R%d="",S%d=""),"Pick the Note and the Line item",IF(ISNA(MATCH(R%d&"|"&S%d,$G$2:$G$%d,0)),"\u2717 Line item does not belong to that Note","\u2713 Active"))))'
                        % (r_, r_, TBB, r_, r_, r_, r_, NLIST + 400)).font = Font(bold=True)
    dvQ = DataValidation(type='list', formula1=TBB, allow_blank=True, showErrorMessage=True, errorTitle='Pick from list', error='Choose a ledger from the drop-down.',
                         promptTitle='Ledger', prompt='Pick the ledger you want to move.', showInputMessage=True)
    dvR = DataValidation(type='list', formula1='$I$2:$I$%d' % (len(labels) + 1), allow_blank=True, showErrorMessage=True, errorTitle='Pick from list', error='Choose a Note from the drop-down.',
                         promptTitle='Note', prompt='Pick the note this ledger should go to.', showInputMessage=True)
    dvS = DataValidation(type='list', formula1='OFFSET($B$1,MATCH($R%d,$A$1:$A$%d,0)-1,0,COUNTIF($A$1:$A$%d,$R%d),1)' % (PR0, NLIST, NLIST, PR0), allow_blank=True, showErrorMessage=True,
                         errorTitle='Pick from list', error='Choose a Line item from the drop-down (pick the Note first).', promptTitle='Line item', prompt='Lists only the lines of the Note chosen in column R.', showInputMessage=True)
    for dv_, col_ in ((dvQ, 'Q'), (dvR, 'R'), (dvS, 'S')):
        ls.add_data_validation(dv_); dv_.add('%s%d:%s%d' % (col_, PR0, col_, PR1))
    from openpyxl.formatting.rule import FormulaRule as FR_
    ls.conditional_formatting.add('U%d:U%d' % (PR0, PR1), FR_(formula=['LEFT($U%d,1)="\u2717"' % PR0], font=Font(color='9C0006', bold=True), fill=PatternFill('solid', bgColor='FFC7CE', fgColor='FFC7CE')))
    ls.conditional_formatting.add('U%d:U%d' % (PR0, PR1), FR_(formula=['LEFT($U%d,1)="\u2713"' % PR0], font=Font(color='006100', bold=True)))
    mp.conditional_formatting.add('B%d:G%d' % (R0, RL + 60), FR_(formula=['$T%d>0' % R0], fill=PatternFill('solid', bgColor='DDEBF7', fgColor='DDEBF7')))
    for col, wd in zip('QRSTU', [42, 46, 62, 62, 34]): ls.column_dimensions[col].width = wd
    ls.column_dimensions['P'].width = 3
    ls.sheet_properties.tabColor = 'C55A11'
    # Review sheet: pointer
    # ---------------- Review sheet ----------------
    rv['A1'] = 'REVIEW - read this first'; rv['A1'].font = Font(bold=True, size=14)
    lines = ['Generated by NCE Tool v%s from: %s  (current year)  and  %s  (previous year)%s.' % (VERSION, os.path.basename(cy['path']), os.path.basename(py['path']),
                                                                                         ('; Tally PDFs: ' + ', '.join(meta.get('pdfs', []))) if meta.get('pdfs') else '; no Tally PDFs supplied'),
             'EASIEST WAY TO MOVE A LEDGER: sheet "Lists", yellow panel on the right (columns Q-U): pick the ledger, the note and the line item - everything updates. (Alternatively use the drop-downs in the Trial Balance sheet.) HOW TO CORRECT FIGURES: go to sheet "Trial Balance", pick another Note Label (yellow, column F) and then a Line Item (column G) for any ledger - all notes, the Balance Sheet and the P&L update by formula. Orange = auto-map was a guess.',
             'Closing stock is not in a Tally TB: see Workings A (derived / override). Partner ratios, remuneration shares and depreciation rates are editable inputs (blue/yellow cells in Workings).',
             'STILL TO COMPLETE BY YOU: PAN / nature of business (Note 1 text), sheet "Disclosures" (related parties, contingent liabilities), partner-wise interest / capital introduced (Workings C), MSME split, debtor ageing, split of loans / deposits into long-term and short-term.',
             'Formulas calculate when the file is opened in Excel (press F9 / Ctrl+Alt+F9 if values look blank).']
    for i, l in enumerate(lines, 3):
        rv.cell(i, 1, l).alignment = Alignment(wrap_text=True, vertical='top'); rv.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8); rv.row_dimensions[i].height = 32
    r0 = 8
    nts = list(meta.get('notes') or [])
    if nts:
        rv.cell(r0, 1, 'ASSUMPTIONS AND WARNINGS FROM THE TOOL - please read').font = Font(bold=True, color='FFFFFF')
        for j in range(1, 9): rv.cell(r0, j).fill = PatternFill('solid', fgColor='C00000')
        for i_, t_ in enumerate(nts, 1):
            c_ = rv.cell(r0 + i_, 1, '%d. %s' % (i_, t_)); c_.alignment = Alignment(wrap_text=True, vertical='top'); c_.font = Font(color='9C0006')
            rv.merge_cells(start_row=r0 + i_, start_column=1, end_row=r0 + i_, end_column=8); rv.row_dimensions[r0 + i_].height = 16 * (1 + len(t_) // 120)
        r0 += len(nts) + 2
    rv.cell(r0, 1, 'CHECK RESULTS (live)').font = Font(bold=True, color='FFFFFF')
    for j in range(1, 9): rv.cell(r0, j).fill = PatternFill('solid', fgColor='1F3864')
    for i in range(CK0, CK1 + 1):
        rv.cell(r0 + 1 + i - CK0, 1, '=Workings!A%d' % i)
        c = rv.cell(r0 + 1 + i - CK0, 7, '=IF(ABS(Workings!D%d)<0.01,"OK","CHECK")' % i)
        rv.merge_cells(start_row=r0 + 1 + i - CK0, start_column=1, end_row=r0 + 1 + i - CK0, end_column=6)
    r1 = r0 + 3 + len(checks)
    rv.cell(r1, 1, 'LEDGERS MAPPED BY DEFAULT (please review in Trial Balance)').font = Font(bold=True, color='FFFFFF')
    for j in range(1, 9): rv.cell(r1, j).fill = PatternFill('solid', fgColor='C55A11')
    for j, h in enumerate(['Ledger', 'Parent group', 'Current year (display)', 'Previous year (display)', 'Currently mapped to'], 1):
        c = rv.cell(r1 + 1, j, h); c.font = bold; c.fill = hf
    k = r1 + 2
    for r in rows:
        if r['reason'] == 'default':
            rv.cell(k, 1, r['name']); rv.cell(k, 2, r.get('parent', r['grp']))
            rv.cell(k, 3, "='Trial Balance'!K%d" % r['row']).number_format = NF; rv.cell(k, 4, "='Trial Balance'!L%d" % r['row']).number_format = NF
            rv.cell(k, 5, "='Trial Balance'!F%d&\" / \"&'Trial Balance'!G%d" % (r['row'], r['row'])); k += 1
    if k == r1 + 2: rv.cell(k, 1, '(none)')
    for col, wd in zip('ABCDEFGH', [60, 26, 20, 20, 80, 4, 10, 4]): rv.column_dimensions[col].width = wd

    # ---------------- Disclosures sheet (AS 18 / contingent liabilities) ----------------
    ds = wb.create_sheet('Disclosures')
    ds['A1'] = ENT_D + ' - Additional disclosures'; ds['A1'].font = Font(bold=True, size=13)
    ds['A2'] = ('Related-party transactions (AS 18) and contingent liabilities / commitments cannot come from a trial balance: type them in the yellow cells. '
                "Partners' remuneration and interest are pre-filled from the mapping.")
    ds['A2'].alignment = Alignment(wrap_text=True, vertical='top'); ds.merge_cells('A2:G2'); ds.row_dimensions[2].height = 34

    def dh(r, text, ncols=7):
        ds.cell(r, 1, text).font = Font(bold=True, color='FFFFFF')
        for j in range(1, ncols + 1): ds.cell(r, j).fill = PatternFill('solid', fgColor='1F3864')
    dh(4, 'A. Related party transactions (AS 18)')
    for j, h in enumerate(['Related party', 'Relationship', 'Nature of transaction', 'Amount CY', 'Amount PY', 'Outstanding CY', 'Outstanding PY'], 1):
        c = ds.cell(5, j, h); c.font = bold; c.fill = hf; c.alignment = Alignment(wrap_text=True)
    pre = [('Partners (collectively)', 'Partners / key management personnel', "Remuneration to partners", '=' + SM('PR', 'cy'), '=' + SM('PR', 'py')),
           ('Partners (collectively)', 'Partners / key management personnel', "Interest on partners' capital", '=' + SM('N24b', 'cy'), '=' + SM('N24b', 'py'))]
    for i in range(10):
        r_ = 6 + i
        for j in range(1, 8):
            c = ds.cell(r_, j); c.fill = yellow; c.font = blue
            if j >= 4: c.number_format = NF
        if i < len(pre):
            for j, v in enumerate(pre[i], 1): ds.cell(r_, j, v)
    dh(18, 'B. Contingent liabilities and commitments')
    for j, h in enumerate(['Particulars', '', '', 'CY', 'PY'], 1):
        c = ds.cell(19, j, h); c.font = bold; c.fill = hf
    cl = ['Claims against the entity not acknowledged as debts', 'Guarantees given', 'Letters of credit / bills discounted',
          'Disputed statutory demands (income tax / GST) under appeal', 'Other contingent liabilities / commitments']
    for i, l in enumerate(cl):
        r_ = 20 + i
        ds.cell(r_, 1, l)
        for j in (4, 5):
            c = ds.cell(r_, j, 0); c.fill = yellow; c.font = blue; c.number_format = NF
    ds.cell(25, 1, 'Total').font = bold
    for j in (4, 5):
        c = ds.cell(25, j, '=SUM(%s20:%s24)' % (CL(j), CL(j))); c.font = bold; c.number_format = NF
    for col, wd in zip('ABCDEFG', [38, 34, 36, 16, 16, 16, 16]): ds.column_dimensions[col].width = wd

    # ---------------- Details sheet (assessee / auditor / place & date) + signature blocks ----------------
    dt = wb.create_sheet('Details')
    dt['A1'] = 'DETAILS PRINTED AT THE FOOT OF THE BALANCE SHEET AND PROFIT & LOSS ACCOUNT'; dt['A1'].font = Font(bold=True, size=13)
    dt['A2'] = 'Type or correct the yellow cells - the signature blocks on both statements update automatically.'; dt['A2'].font = Font(italic=True, color='595959')

    def dhead(r, text):
        dt.cell(r, 1, text).font = Font(bold=True, color='FFFFFF')
        for j in range(1, 4): dt.cell(r, j).fill = PatternFill('solid', fgColor='1F3864')

    def drow(r, label, val, hint=''):
        dt.cell(r, 1, label)
        c = dt.cell(r, 2, val); c.fill = yellow; c.font = blue; c.alignment = Alignment(wrap_text=True, vertical='top')
        if hint: dt.cell(r, 3, hint).font = Font(italic=True, color='7F7F7F')
    dhead(3, 'A. Assessee (the entity)')
    drow(4, 'Name of the firm / entity', ENT, 'printed after "For ..." on the right-hand signature block')
    drow(5, 'Address', meta.get('address', ''), 'printed under the name on the Balance Sheet and P&L')
    drow(6, 'PAN', meta.get('pan', ''))
    dhead(8, 'B. Signatories for the assessee (partners / proprietor)')
    dt.cell(9, 2, 'Name').font = bold; dt.cell(9, 3, 'Designation').font = bold
    sg = list(meta.get('signers') or [])
    if not sg:
        for nm_ in plist[:4]:
            if nm_ != 'Proprietor':
                sg.append((nm_.upper(), 'Partner' if len(plist) > 1 else 'Proprietor'))
    for i in range(4):
        for j in (2, 3):
            c = dt.cell(10 + i, j, sg[i][j - 2] if i < len(sg) else ''); c.fill = yellow; c.font = blue
        dt.cell(10 + i, 1, 'Signatory %d' % (i + 1))
    dhead(15, 'C. Auditor')
    drow(16, 'Firm name', meta.get('aud_firm', ''), 'e.g. Praveen Nahata & Associates')
    drow(17, 'Firm registration no. (FRN)', meta.get('aud_frn', ''), 'e.g. 010071S')
    drow(18, 'Name of CA (proprietor / partner)', meta.get('aud_name', ''), 'e.g. Praveen Kumar Nahata  (printed as "CA. <name>")')
    drow(19, 'Designation', meta.get('aud_desig', ''), 'Proprietor / Partner')
    drow(20, 'Membership no.', meta.get('aud_mno', ''))
    drow(21, 'UDIN', meta.get('aud_udin', ''))
    dhead(23, 'D. Place and date of signing')
    drow(24, 'Place', meta.get('place', ''))
    drow(25, 'Date', meta.get('sign_date'), 'dd/mm/yyyy')
    dt['B25'].number_format = 'dd/mm/yyyy'; dt['B25'].alignment = Alignment(horizontal='left')
    dt.column_dimensions['A'].width = 36; dt.column_dimensions['B'].width = 52; dt.column_dimensions['C'].width = 52

    def sig_block(ws, r0):
        f9 = Font(name='Arial', size=10); fb = Font(name='Arial', size=10, bold=True)
        notes_r = r0 - 2
        ws['B%d' % notes_r] = 'The accompanying notes 1 to 26 are an integral part of these financial statements'; ws['B%d' % notes_r].font = Font(name='Arial', size=10, italic=True)
        L = [('As per our report of even date attached', f9),
             ('="For "&Details!B16', fb),
             ('=IF(Details!B17="","","FRN No."&Details!B17&", Chartered Accountants")', f9),
             (None, f9), (None, f9),
             ('=IF(Details!B18="","","CA. "&Details!B18)', fb),
             ('=IF(Details!B19&Details!B20="","",Details!B19&IF(Details!B20="","",", M.No.: "&Details!B20))', f9),
             ('="UDIN : "&Details!B21', f9),
             ('="Place : "&Details!B24', f9),
             ('="Date : "&IF(Details!B25="","",TEXT(Details!B25,"dd/mm/yyyy"))', f9)]
        for i, (v, f) in enumerate(L):
            c = ws['B%d' % (r0 + i)]; c.value = v; c.font = f; c.alignment = Alignment(horizontal='left')
        ws['D%d' % (r0 + 1)] = '="For "&UPPER(Details!B4)'; ws['D%d' % (r0 + 1)].font = fb
        for i in range(4):
            rn = r0 + 3 + 2 * i
            ws['D%d' % rn] = '=IF(Details!B%d="","",UPPER(Details!B%d))' % (10 + i, 10 + i); ws['D%d' % rn].font = fb
            ws['D%d' % (rn + 1)] = '=IF(Details!C%d="","","("&Details!C%d&")")' % (10 + i, 10 + i); ws['D%d' % (rn + 1)].font = f9
        return r0 + 11
    ws_bs['A3'] = '=Details!B5'; ws_bs['A3'].font = Font(italic=True, size=9); ws_bs['A3'].alignment = Alignment(horizontal='left')
    ws_pl['A3'] = "='Balance Sheet'!A3"; ws_pl['A3'].font = Font(italic=True, size=9); ws_pl['A3'].alignment = Alignment(horizontal='left')
    bs_end = sig_block(ws_bs, 55)
    ws_bs['B51'] = None
    pl_end = sig_block(ws_pl, 52)
    ws_pl['B46'] = None
    ws_pl['B48'] = '* wherever applicable'

    # ---------------- presentation clean-up ----------------
    ACC2 = '_ * #,##0.00_ ;_ * (#,##0.00);_ * "-"??_ ;_ @_ '
    STMT = (ws_bs, ws_pl, n13, n46, n710, n11, n1218, npl)
    TYPO = [('abount', 'about'), ('Purhcase', 'Purchase'), ('maturitites', 'maturities'), ('guranteed', 'guaranteed'), ('Aggreagte', 'Aggregate'), ('Recepie', 'Recipe'),
            ('Liscense', 'License'), ('Investments property', 'Investment property'), ('Stock-in- Trade', 'Stock-in-Trade'), ('(IXI-XII)', '(XI-XII)'),
            ('(XIVII-XVIII)', '(XIV-XV)'), ('(XIII+XIVI)', '(XIII+XVI)'), ('Scedule', 'Schedule')]
    ROMAN = {'XIVII': 'XIV', 'XVIII': 'XV', 'XIVI': 'XVI'}
    for ws in STMT:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and not v.startswith('='):
                    nv = ROMAN.get(v.strip(), v)
                    for a_, b_ in TYPO: nv = nv.replace(a_, b_)
                    if nv != v: c.value = nv
                    continue
                isnum = isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith('='))
                if not isnum or c.column == 1: continue
                if ws in (ws_bs, ws_pl) and c.column <= 3: continue
                nf = c.number_format
                if '%' in nf: continue
                if '#,##0' in nf or (nf == 'General' and c.column >= 4):
                    c.number_format = ACC2
    for r_ in (11, 17, 23, 37, 45):
        if not ws_bs['B%d' % r_].value: ws_bs['B%d' % r_] = 'Sub-total'
    for r_, t_ in ((24, "Total - Owners' funds and liabilities"), (46, 'Total - Assets')):
        for col in 'ABC':
            if isinstance(ws_bs['%s%d' % (col, r_)].value, str) and ws_bs['%s%d' % (col, r_)].value.strip().lower() == 'total':
                ws_bs['%s%d' % (col, r_)] = t_
    from openpyxl.worksheet.properties import PageSetupProperties
    for ws in STMT + (ds,):
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
    ws_pl.print_area = 'A1:F%d' % pl_end; n13.print_area = 'A2:J30'; n11.print_title_rows = '2:3'
    ws_bs.print_area = 'A1:F%d' % bs_end
    n13.page_setup.orientation = 'landscape'; n11.page_setup.orientation = 'landscape'; ds.page_setup.orientation = 'landscape'
    wb.properties.title = '%s - Financial statements (NCE format) FY %s' % (ENT, meta['fyfull'])
    wb.properties.creator = 'NCE Tool v%s' % VERSION; wb.properties.lastModifiedBy = 'NCE Tool'; wb.properties.subject = 'ICAI Non-Corporate Entity format'
    apply_units(wb, R0, RL + 60, meta.get('units') or 'Actuals', log)
    order = ['Review', 'Details', 'Balance Sheet', 'Statement of P&L', 'Note 1 to 3', 'Notes to BS 4 to 6', 'Notes to BS 7 to 10', 'Notes to BS 11', 'Notes to BS 12 to 18',
             'Notes to P & L 19 to 26', 'Disclosures', 'Trial Balance', 'Workings', 'Lists']
    wb._sheets = [wb[n_] for n_ in order]
    wb.active = 0
    for ws in wb.worksheets: ws.sheet_view.tabSelected = (ws.title == 'Review')
    wb.save(out_path)
    # python-side summary
    info = dict(partners=plist, warn_partners=warn_partners, n_rows=len(rows), n_default=sum(1 for r in rows if r['reason'] == 'default'), toggle=toggle_default,
                n_ppe=len([r for r in rows if r['key'] == 'PPE']), pla_key=pla_key)
    return info


# ----------------------------------------------------------------------------------------
# 5.  DRIVER
# ----------------------------------------------------------------------------------------
def safe_name(x):
    return re.sub(r'\s+', '_', re.sub(r'[^\w\- ]+', '', x).strip()) or 'Entity'


def plan(files, entity=None, pan='', nature='', py_os=None, log=print, extra=None):
    """files: two trial-balance .xlsx (any order) + optional Tally P&L / Balance Sheet PDFs.  Returns (cy, py, meta)."""
    files = list(files)
    notes = []
    _log = log

    def log(m):
        if str(m).lstrip().startswith('!'):
            notes.append(str(m).strip().lstrip('! ').strip())
        _log(m)
    tbs = [f for f in files if f.lower().endswith(('.xlsx', '.xlsm'))]
    pdfs = [f for f in files if f.lower().endswith('.pdf')]
    if len(tbs) != 2:
        raise ToolError('Please give exactly TWO trial-balance Excel files (one for each year); %d found.' % len(tbs))
    T = []
    for f in tbs:
        if not os.path.exists(f):
            raise ToolError('File not found: %s' % f)
        try:
            t = load_tb(f)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError('Could not read "%s" as a Tally trial balance (%s).\nIt must be an Excel file with the columns $Name, $Parent, $_PrimaryGroup, $ClosingBalance '
                            '(Tally ODBC extract) or the Tally trial-balance export with Debit / Credit columns. Is the file open in Excel or damaged?' % (os.path.basename(f), str(e).splitlines()[0] if str(e) else type(e).__name__))
        if not t['rows']:
            raise ToolError('"%s" contains no ledgers with a balance.' % os.path.basename(f))
        t['fy'] = (t['period'][1].year if t.get('period') else fy_from_name(f))
        log('  %s: %d ledgers (%s format)' % (os.path.basename(f), len(t['rows']), 'older Tally export' if t['legacy'] else 'ODBC extract'))
        T.append(t)
    sig = lambda t: sorted((r['name'], round(r['dr'], 2), round(r['cr'], 2)) for r in t['rows'])
    if len(T[0]['rows']) > 5 and sig(T[0]) == sig(T[1]):
        raise ToolError('The two trial-balance files contain IDENTICAL balances (%s and %s) - you have probably selected the same year twice. Select the previous-year file and the current-year file.'
                        % (os.path.basename(T[0]['path']), os.path.basename(T[1]['path'])))
    P = []
    for f in pdfs:
        try:
            d = parse_pdf(f)
            P.append(d)
            log('  %s: Tally %s, period %s' % (os.path.basename(f), 'Profit & Loss' if d['kind'] == 'PL' else 'Balance Sheet',
                                              ('%s to %s' % d['period']) if d['period'] else 'not detected'))
        except Exception as e:
            log('  ! could not use %s: %s' % (os.path.basename(f), e))
    # ---- which TB is the current year?
    if T[0]['fy'] and T[1]['fy'] and T[0]['fy'] != T[1]['fy']:
        cy, py = (T[0], T[1]) if T[0]['fy'] > T[1]['fy'] else (T[1], T[0])
    else:
        pend = sorted({d['period'][1].year for d in P if d['period']})
        if len(pend) == 2 and all(t['legacy'] is False for t in T):
            # match by closing stock ledger against the PDF closing stock
            def stk(t): return sum(r['dr'] - r['cr'] for r in t['rows'] if r['grp'].lower() in ('stock-in-hand', 'stock in hand'))
            pcs = {d['period'][1].year: d['vals'].get('cs') for d in P if d['kind'] == 'PL' and d['period']}
            m0 = [y for y, v in pcs.items() if v is not None and abs(v - stk(T[0])) < 1]
            if len(m0) == 1:
                T[0]['fy'] = m0[0]; T[1]['fy'] = [y for y in pend if y != m0[0]][0]
                cy, py = (T[0], T[1]) if T[0]['fy'] > T[1]['fy'] else (T[1], T[0])
            else:
                cy, py = T[1], T[0]
                log('  ! could not tell which file is which year - assuming the SECOND file is the CURRENT year (put FY25-26 etc. in the file names to be safe).')
        else:
            cy, py = T[1], T[0]
            log('  ! could not tell which file is which year - assuming the SECOND file is the CURRENT year (put FY25-26 etc. in the file names to be safe).')
    cy_end_y = cy['fy'] or (max([d['period'][1].year for d in P if d['period']] or [datetime.date.today().year]))
    py_end_y = py['fy'] or (cy_end_y - 1)
    for t_, y_ in ((cy, cy_end_y), (py, py_end_y)):
        t_['pdf'] = {}
        t_['pdfs'] = []
    for d in P:
        if not d['period']:
            continue
        y_ = d['period'][1].year
        tgt = cy if y_ == cy_end_y else py if y_ == py_end_y else None
        if tgt is None:
            log('  ! %s belongs to a different year (%s) - ignored.' % (os.path.basename(d['path']), y_)); continue
        for k_, v_ in d['vals'].items():
            if v_ is not None:
                tgt['pdf'][k_] = v_
        tgt['pdfs'].append(os.path.basename(d['path']))
        if d['period'] and not tgt.get('period'):
            tgt['period'] = d['period']
        if d['entity'] and not tgt.get('entity'):
            tgt['entity'] = d['entity']
        if d.get('address') and not tgt.get('address'):
            tgt['address'] = d['address']
    for t_ in (cy, py):      # details written by Tally Extract (used only when the PDFs did not supply them)
        inf = t_.get('info') or {}
        for k_ in ('entity', 'address'):
            if not t_.get(k_) and inf.get({'entity': 'company'}.get(k_, k_)):
                t_[k_] = str(inf.get({'entity': 'company'}.get(k_, k_)))
        if not pan and inf.get('pan'):
            pan = str(inf['pan'])
    # ---- derived entries for ODBC extracts (opening stock, P&L A/c, closing-stock balancing entry)
    def stk(t): return sum(r['dr'] - r['cr'] for r in t['rows'] if r['grp'].lower() in ('stock-in-hand', 'stock in hand'))
    py_stock, cy_stock = stk(py), stk(cy)
    cy_os = cy['pdf'].get('os')
    if cy_os is None:
        cy_os = py_stock if py_stock else (py['pdf'].get('cs') or 0.0)
        if not cy_os and (cy.get('info') or {}).get('opening_stock'):
            cy_os = float(cy['info']['opening_stock'])
        if not cy['legacy']:
            log('  Opening stock FY%d taken from the closing stock of FY%d: %s' % (cy_end_y, py_end_y, '{:,.2f}'.format(cy_os)))
    py_os_v = py['pdf'].get('os')
    if py_os_v is None:
        py_os_v = py_os if py_os is not None else float((py.get('info') or {}).get('opening_stock') or 0.0)
        if not py['legacy'] and py_os is None and not py_os_v and (py_stock or cy_os):
            log('  ! Opening stock of the previous year is not known (no previous-year P&L PDF): assumed NIL.  Give the P&L PDF or --py-opening-stock, otherwise previous-year profit is wrong.')
    if not cy['legacy']:
        add_derived(cy, cy_os, cy['pdf'].get('profit'), cy['pdf'].get('cs'), '%d' % cy_end_y, log)
    if not py['legacy']:
        add_derived(py, py_os_v, py['pdf'].get('profit'), py['pdf'].get('cs'), '%d' % py_end_y, log)
    for t_, nm_ in ((cy, 'current'), (py, 'previous')):
        net = sum(r['cr'] - r['dr'] for r in t_['rows'])
        if abs(net) > 1:
            log('  ! WARNING: the %s-year trial balance (with derived entries) is out of balance by %s - check opening stock / profit figures / missing ledgers.' % (nm_, '{:,.2f}'.format(net)))
    if cy['pdf'].get('cs') is not None and abs(cy['pdf']['cs'] - cy_stock) > 1 and cy_stock:
        log('  ! closing stock in the TB (%s) differs from the Tally P&L PDF (%s)' % ('{:,.2f}'.format(cy_stock), '{:,.2f}'.format(cy['pdf']['cs'])))
    cye = cy['period'][1] if cy.get('period') else datetime.date(cy_end_y, 3, 31)
    cys = cy['period'][0] if cy.get('period') else datetime.date(cy_end_y - 1, 4, 1)
    pye = py['period'][1] if py.get('period') else datetime.date(py_end_y, 3, 31)
    pys = py['period'][0] if py.get('period') else datetime.date(py_end_y - 1, 4, 1)
    if (cye.month, cye.day) != (3, 31):
        log('  ! note: year-end is not 31 March - labels in the template are generated for the detected dates; please review headings.')

    def lbl(s_, e_):
        return '%02d-%02d' % (s_.year % 100, e_.year % 100) if s_.year != e_.year else str(e_.year)

    def full(s_, e_):
        return '%d-%02d' % (s_.year, e_.year % 100) if s_.year != e_.year else str(e_.year)
    ent = entity or cy.get('entity') or py.get('entity')
    if not ent:
        ent = re.sub(r'(?i)\b(fy)?\s*\d{2,4}\s*[-_]\s*\d{2,4}\b|trial[ _]*balance|\.xlsx?|[_-]+', ' ', os.path.splitext(os.path.basename(cy['path']))[0]).strip().title() or 'Name of the Entity'
        log('  ! entity name not found in the files - using "%s" (change it in the window / --entity).' % ent)
    meta = dict(entity=ent.strip(), address=cy.get('address') or py.get('address') or '', pan=(pan or '').strip().upper(),
                nature=(nature or '').strip(), cyY=cye.year, pyY=pye.year, cy_end=cye, py_end=pye, cy_start=cys, py_start=pys,
                cyL=lbl(cys, cye), pyL=lbl(pys, pye), fyfull=full(cys, cye), pdfs=cy['pdfs'] + py['pdfs'], notes=notes)
    ex = dict(load_settings()); ex.update({k: v for k, v in (extra or {}).items() if v not in (None, '', [])})
    if ex.get('address'):
        meta['address'] = ex['address']
    meta['units'] = ex.get('units') or 'Actuals'
    meta.update(aud_firm=ex.get('aud_firm', ''), aud_frn=ex.get('aud_frn', ''), aud_name=ex.get('aud_name', ''), aud_desig=ex.get('aud_desig', ''),
                aud_mno=ex.get('aud_mno', ''), aud_udin=ex.get('aud_udin', ''), place=ex.get('place', ''),
                sign_date=parse_date(ex.get('date')) or datetime.date.today(), signers=ex.get('signers') or [])
    return cy, py, meta


def default_filename(meta):
    # e.g.  NCE_ABC_Traders_FY2025-26.xlsx   (client name + latest financial year)
    return 'NCE_%s_FY%s.xlsx' % (safe_name(meta['entity']), meta['fyfull'])


def generate(files, out_path=None, entity=None, pan='', nature='', py_os=None, log=print, extra=None):
    log('Reading files ...')
    cy, py, meta = plan(files, entity, pan, nature, py_os, log, extra)
    fname = default_filename(meta)
    if not out_path:
        out_path = unique_path(os.path.join(os.path.dirname(os.path.abspath(cy['path'])), fname))
    elif os.path.isdir(out_path):
        out_path = unique_path(os.path.join(out_path, fname))
    log('Current year  : FY %s (%s)  -> %s' % (meta['fyfull'], os.path.basename(cy['path']), meta['cy_end']))
    log('Previous year : FY %s (%s)' % (meta['pyL'], os.path.basename(py['path'])))
    log('Entity        : %s' % meta['entity'])
    try:
        info = build(cy, py, meta, out_path, log)
    except PermissionError:
        raise ToolError('Cannot save "%s" - is it open in Excel? Close it (or choose another folder) and try again.' % out_path)
    log('Mapped %d lines automatically; %d were default guesses (orange in the Trial Balance sheet / listed in the Review sheet).' % (info['n_rows'], info['n_default']))
    log('Partners / owners detected: %s' % ', '.join(info['partners']))
    if info['warn_partners']:
        log('  ! more than 4 partners found - only the first 4 are shown in Note 3.')
    save_settings(dict(meta, **{k: v for k, v in (extra or {}).items() if v}))
    log('Saved: %s' % out_path)
    log('Open it in Excel, read the "Review" sheet first, then use the drop-downs in the "Trial Balance" sheet to correct any mapping.')
    return out_path



# ----------------------------------------------------------------------------------------
# 6.  ONE-CLICK PIPELINE  (Tally -> trial balances -> NCE workbook)
# ----------------------------------------------------------------------------------------
def unique_path(path):
    """never overwrite an existing file (it may be open in Excel): NCE_X_FY2025-26.xlsx -> NCE_X_FY2025-26 (2).xlsx"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    for i in range(2, 500):
        p = '%s (%d)%s' % (base, i, ext)
        if not os.path.exists(p):
            return p
    return path


def run_pipeline(o, log=print, ask=None):
    """o: dict(mode='tally'|'files', tb=[...], pdf=[...], dsn, company, company_py, end_year, out_dir, want_pdf, entity, pan, nature, pyos, extra)
    Returns the path of the NCE workbook."""
    out_dir = o.get('out_dir') or os.path.join(os.path.expanduser('~'), 'Documents')
    try:
        os.makedirs(out_dir, exist_ok=True)
        probe = os.path.join(out_dir, '.nce_write_test')
        with open(probe, 'w') as f:
            f.write('x')
        os.remove(probe)
    except Exception as e:
        raise ToolError('Cannot write to the output folder "%s" (%s). Choose another folder in step 3.' % (out_dir, e))
    if o.get('mode') == 'tally':
        if not o.get('end_year'):
            raise ToolError('Enter the year in which the current financial year ENDS (e.g. 2026 for FY 2025-26).')
        log('STEP 1 of 2 - reading Tally (ODBC) ...')
        data_dir = os.path.join(out_dir, 'Tally_data')
        files = tally_extract(data_dir, o.get('company') or '', o.get('company_py') or '', int(o['end_year']), o.get('dsn') or 'TallyODBC64_9000',
                              bool(o.get('want_pdf', True)), log, ask, o.get('debug'))
        log('Tally files saved in: %s' % data_dir)
        log('STEP 2 of 2 - preparing the NCE workbook ...')
    else:
        files = list(o.get('tb') or []) + list(o.get('pdf') or [])
    pv = o.get('pyos')
    if isinstance(pv, str):
        pv = pv.strip().replace(',', '')
        try:
            pv = float(pv) if pv else None
        except ValueError:
            raise ToolError('"Previous-year opening stock" must be a number.')
    return generate(files, out_dir, o.get('entity') or None, o.get('pan') or '', o.get('nature') or '', pv, log, o.get('extra'))


def open_path(p):
    try:
        if sys.platform.startswith('win'):
            os.startfile(p)
        elif sys.platform == 'darwin':
            import subprocess; subprocess.Popen(['open', p])
        else:
            import subprocess; subprocess.Popen(['xdg-open', p])
    except Exception:
        pass


def system_check(log=print):
    """What is installed? (shown in the Help tab and by  --check)"""
    ok = True
    log('Python %s on %s' % (sys.version.split()[0], sys.platform))
    for mod, need, why in (('openpyxl', True, 'Excel files (required)'), ('pypdf', False, 'reading Tally PDFs (optional - falls back to pdftotext / pdfplumber)'),
                           ('pyodbc', False, 'talking to Tally (needed only for "Extract from Tally")'), ('tkinter', False, 'this window (command line works without it)')):
        try:
            m = __import__(mod)
            log('  [OK]      %-9s %s %s' % (mod, getattr(m, '__version__', ''), '- ' + why))
        except Exception:
            log('  [%s] %-9s not installed - %s' % ('MISSING' if need else 'missing', mod, why))
            ok = ok and not need
    try:
        import pyodbc
        ds = [k for k in pyodbc.dataSources().keys()]
        tally = [k for k in ds if 'tally' in k.lower()]
        log('  ODBC data sources: %s' % (', '.join(ds) or '(none)'))
        log('  Tally data source %s' % ('found: ' + ', '.join(tally) if tally else 'NOT found - install/enable Tally ODBC (see Help)'))
    except Exception:
        pass
    try:
        wb = load_template()
        log('  [OK]      built-in ICAI template: %d sheets' % len(wb.sheetnames))
    except Exception as e:
        log('  [ERROR]   built-in ICAI template could not be loaded: %s' % e); ok = False
    return ok


def install_libs(log=print):
    import subprocess
    for pkg in ('openpyxl', 'pypdf', 'pyodbc'):
        log('Installing %s ...' % pkg)
        try:
            r = subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', pkg], capture_output=True, text=True, timeout=600)
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:]
            log('   ' + (tail[0] if tail else ('done' if r.returncode == 0 else 'failed')))
        except Exception as e:
            log('   failed: %s' % e)
    log('Finished. Close and re-open the NCE Tool if a library was newly installed.')


HELP_TEXT = """HOW TO USE  (5 minutes per client)

A.  Easiest - straight from Tally
    1. Open Tally with the client's company loaded (Gateway of Tally).  Tally's ODBC server must be on (port 9000).
    2. Tab 1 - choose "Extract from Tally", press "Test connection / list companies", check the year (2026 = FY 2025-26).
    3. Tab 2 - type PAN / nature of business / signatories / auditor details (auditor details are remembered for the next client).
    4. Tab 3 - choose a folder and press "Create NCE financial statements".  When the tool asks, switch Tally to the PREVIOUS year
       (Alt+F3 Select Company / Alt+F2 Period) and press OK, then to the CURRENT year and press OK.
    5. Open the finished Excel file.  Read the sheet "Review" first.

B.  From files you already have
    Tab 1 - choose "Use files I already have": the two trial-balance Excel files (Tally ODBC extract with $Name, $Parent, $_PrimaryGroup,
    $ClosingBalance - or the older Tally trial-balance export) and, if you have them, the Tally Profit & Loss and Balance Sheet PDFs of both years.

TALLY SETTINGS (one-time)
    Tally Prime: F1 Help > Settings > Connectivity > Client/Server configuration > ODBC server = Yes, port 9000.
    Windows: install the Tally ODBC driver (comes with Tally) - its data source is normally called TallyODBC64_9000.

CORRECTING FIGURES
    In the Excel file, sheet "Trial Balance": pick another Note Label / Line Item (yellow drop-downs) for any ledger and everything updates.
    Orange cells = the tool had to guess.  "Workings" holds closing stock, fixed-asset depreciation, partners' ratios.
    "Balance Sheet" cell H3 changes the units (Actuals / Hundreds / Thousands / Lakhs / Crores).

IF SOMETHING GOES WRONG
    A plain-language message appears.  A log file (NCE_Tool_log.txt) is saved next to the output.  Send me a screenshot of the log box.
"""


# ----------------------------------------------------------------------------------------
# 7.  WINDOW
# ----------------------------------------------------------------------------------------
def gui(preload=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    import threading, queue
    try:                                            # sharp text on high-resolution Windows screens
        import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    root.title('NCE Tool v%s  -  Tally to ICAI Non-Corporate-Entity financial statements' % VERSION)
    root.geometry('1000x820'); root.minsize(900, 700)
    st = load_settings()
    today = datetime.date.today()
    V = {k: tk.StringVar(value=st.get(k, '')) for k in ('entity', 'pan', 'nature', 'pyos', 'address', 'aud_firm', 'aud_frn', 'aud_name', 'aud_desig', 'aud_mno',
                                                          'aud_udin', 'place')}
    V['date'] = tk.StringVar(value=today.strftime('%d/%m/%Y'))
    V['mode'] = tk.StringVar(value='tally')
    V['dsn'] = tk.StringVar(value=st.get('dsn', 'TallyODBC64_9000'))
    V['host'] = tk.StringVar(value=st.get('host', 'localhost')); V['port'] = tk.StringVar(value=st.get('port', '9000'))
    V['company'] = tk.StringVar(); V['company_py'] = tk.StringVar()
    V['fy'] = tk.StringVar(value=str(today.year if today.month >= 4 else today.year - 1))   # the financial year just completed (Oct 2026 -> FY 2025-26 -> 2026)
    V['out'] = tk.StringVar(value=st.get('out_dir', os.path.join(os.path.expanduser('~'), 'Documents')))
    V['units'] = tk.StringVar(value='Actuals')
    V['pdf'] = tk.BooleanVar(value=True); V['openfile'] = tk.BooleanVar(value=True); V['debug'] = tk.BooleanVar(value=False)
    tbf, pdff = [], []
    lb1, lb2 = tk.StringVar(value='(none selected)'), tk.StringVar(value='(none selected)')
    if preload:
        tbf[:] = [p for p in preload if p.lower().endswith(('.xlsx', '.xlsm'))]
        pdff[:] = [p for p in preload if p.lower().endswith('.pdf')]
        if tbf: lb1.set('; '.join(os.path.basename(x) for x in tbf)); V['mode'].set('files')
        if pdff: lb2.set('; '.join(os.path.basename(x) for x in pdff))

    tk.Label(root, text='NCE Tool', font=('Arial', 16, 'bold'), fg='#1F3864').pack(anchor='w', padx=14, pady=(8, 0))
    tk.Label(root, text='Tally  ->  trial balances  ->  ICAI Non-Corporate-Entity Balance Sheet, P&L and Notes 1-26 (Excel, fully formula-linked)',
             fg='#595959').pack(anchor='w', padx=14)
    nb = ttk.Notebook(root); nb.pack(fill='both', expand=True, padx=10, pady=8)
    t1, t2, t3, t4 = (ttk.Frame(nb, padding=10) for _ in range(4))
    nb.add(t1, text='  1. Source  '); nb.add(t2, text='  2. Client & signatures  '); nb.add(t3, text='  3. Create  '); nb.add(t4, text='  Help  ')

    def lab_entry(parent, text, var, r, width=60, show=None):
        ttk.Label(parent, text=text).grid(row=r, column=0, sticky='w', pady=2, padx=(0, 8))
        e = ttk.Entry(parent, textvariable=var, width=width)
        e.grid(row=r, column=1, sticky='we', pady=2)
        return e

    # ---------- tab 1
    ttk.Radiobutton(t1, text='Extract from Tally now  (Tally open, ODBC)', variable=V['mode'], value='tally').grid(row=0, column=0, sticky='w')
    ttk.Radiobutton(t1, text='Use files I already have  (trial-balance Excel files + optional Tally PDFs)', variable=V['mode'], value='files').grid(row=0, column=1, sticky='w', padx=20)
    ft = ttk.LabelFrame(t1, text=' From Tally ', padding=10); ft.grid(row=1, column=0, columnspan=2, sticky='we', pady=8)
    ff = ttk.LabelFrame(t1, text=' From files ', padding=10); ff.grid(row=2, column=0, columnspan=2, sticky='we', pady=4)
    t1.columnconfigure(1, weight=1); ft.columnconfigure(1, weight=1); ff.columnconfigure(1, weight=1)
    lab_entry(ft, 'ODBC data source name', V['dsn'], 0, 30)
    lab_entry(ft, 'Tally host / port  (company list only)', V['host'], 1, 30)
    ttk.Entry(ft, textvariable=V['port'], width=8).grid(row=1, column=2, padx=6)
    cb = ttk.Combobox(ft, textvariable=V['company'], width=62)
    cbp = ttk.Combobox(ft, textvariable=V['company_py'], width=62)
    ttk.Label(ft, text='Company - CURRENT year\n(type or pick; blank = whatever is open)').grid(row=3, column=0, sticky='w', pady=2); cb.grid(row=3, column=1, sticky='we')
    ttk.Label(ft, text='Company - PREVIOUS year\n(only if it is a separate company in Tally)').grid(row=4, column=0, sticky='w', pady=2); cbp.grid(row=4, column=1, sticky='we')
    lab_entry(ft, 'Current financial year ENDS in\n(2026 = FY 2025-26)', V['fy'], 5, 10)
    ttk.Checkbutton(ft, text='Also create the Balance Sheet and Profit & Loss PDFs (needed for cross-checks)', variable=V['pdf']).grid(row=6, column=0, columnspan=2, sticky='w', pady=2)
    names = []

    def fetch():
        found, errs = [], []
        try:
            be = TallyODBC(V['dsn'].get().strip(), logf)
            try:
                for n in be.companies():
                    if n not in found: found.append(n)
            finally:
                be.close()
        except Exception as e:
            errs.append(str(e))
        try:
            for n in http_company_names(V['host'].get().strip() or 'localhost', V['port'].get().strip() or '9000', 15):
                if n not in found: found.append(n)
        except Exception as e:
            errs.append('company list: ' + str(e).splitlines()[0])
        if not found:
            messagebox.showerror('NCE Tool', 'Could not read the companies from Tally.\n\n' + '\n\n'.join(errs)); return
        names[:] = found
        cb['values'] = names; cbp['values'] = names
        yrs = [y for y in (company_end_year(n) for n in names) if y]
        if yrs:
            ey = max(yrs); V['fy'].set(str(ey))
            cur, prv = pick_companies(names, ey)
            if cur: V['company'].set(cur)
            if prv: V['company_py'].set(prv)
        elif not V['company'].get():
            V['company'].set(names[0])
        logf('Connected to Tally. Companies found: ' + '; '.join(names))
        if V['company'].get(): logf('  Current year : ' + V['company'].get())
        if V['company_py'].get(): logf('  Previous year: ' + V['company_py'].get())
        messagebox.showinfo('NCE Tool', 'Connected to Tally.\n\nCompanies: ' + '\n'.join(names) + '\n\nCheck the company boxes and the year.')
    ttk.Button(ft, text='Test connection / list companies', command=fetch).grid(row=2, column=0, columnspan=2, sticky='w', pady=4)

    def pick_tb():
        ps = filedialog.askopenfilenames(title='Select the TWO trial-balance files (Ctrl+click for both)', filetypes=[('Excel', '*.xlsx *.xlsm')])
        if ps: tbf[:] = list(ps); lb1.set('; '.join(os.path.basename(x) for x in ps))

    def pick_pdf():
        ps = filedialog.askopenfilenames(title='Select the Tally Profit & Loss and Balance Sheet PDFs (up to 4)', filetypes=[('PDF', '*.pdf')])
        if ps: pdff[:] = list(ps); lb2.set('; '.join(os.path.basename(x) for x in ps))
    b1 = ttk.Button(ff, text='Select the two trial balances...', command=pick_tb); b1.grid(row=0, column=0, sticky='w')
    ttk.Label(ff, textvariable=lb1, wraplength=620).grid(row=0, column=1, sticky='w', padx=8)
    b2 = ttk.Button(ff, text='Select Tally PDFs (optional)...', command=pick_pdf); b2.grid(row=1, column=0, sticky='w', pady=4)
    ttk.Label(ff, textvariable=lb2, wraplength=620).grid(row=1, column=1, sticky='w', padx=8)

    def mode_changed(*_):
        on_t = V['mode'].get() == 'tally'
        def setstate(w, enabled):
            for c in w.winfo_children():
                try: c.configure(state='normal' if enabled else 'disabled')
                except tk.TclError: pass
                setstate(c, enabled)
        setstate(ft, on_t); setstate(ff, not on_t)
        for c in (cb, cbp):
            c.configure(state='normal' if on_t else 'disabled')
    V['mode'].trace_add('write', mode_changed); mode_changed()

    # ---------- tab 2
    t2.columnconfigure(1, weight=1)
    r = 0
    for lbl, key in (('Entity / firm name  (read from Tally / PDFs if blank)', 'entity'), ('Address', 'address'), ('PAN', 'pan'), ('Nature of business (Note 1)', 'nature')):
        lab_entry(t2, lbl, V[key], r); r += 1
    ttk.Label(t2, text='Signatories for the assessee\none per line: "Name, Designation"').grid(row=r, column=0, sticky='nw', pady=2)
    sig_box = tk.Text(t2, height=3, width=60); sig_box.grid(row=r, column=1, sticky='we', pady=2); sig_box.insert('1.0', st.get('signers_txt', '')); r += 1
    ttk.Separator(t2).grid(row=r, column=0, columnspan=2, sticky='we', pady=6); r += 1
    for lbl, key in (('Auditor - firm name', 'aud_firm'), ('Firm registration no. (FRN)', 'aud_frn'), ('CA name (proprietor / partner)', 'aud_name'),
                     ('Designation (Proprietor / Partner)', 'aud_desig'), ('Membership no.', 'aud_mno'), ('UDIN', 'aud_udin'), ('Place of signing', 'place'),
                     ('Date of signing (dd/mm/yyyy)', 'date')):
        lab_entry(t2, lbl, V[key], r, 40); r += 1
    ttk.Separator(t2).grid(row=r, column=0, columnspan=2, sticky='we', pady=6); r += 1
    ttk.Label(t2, text='Show figures in').grid(row=r, column=0, sticky='w')
    ttk.Combobox(t2, textvariable=V['units'], values=[u[0] for u in UNITS], state='readonly', width=14).grid(row=r, column=1, sticky='w'); r += 1
    lab_entry(t2, 'Previous-year opening stock (only if no\nprevious-year P&L PDF is available)', V['pyos'], r, 20); r += 1
    ttk.Label(t2, text='Auditor details, place and folder are remembered for the next client. Everything can also be edited later in the "Details" sheet of the Excel file.',
              foreground='#595959').grid(row=r, column=0, columnspan=2, sticky='w', pady=6)

    # ---------- tab 3
    t3.columnconfigure(0, weight=1); t3.rowconfigure(4, weight=1)
    fr = ttk.Frame(t3); fr.grid(row=0, column=0, sticky='we'); fr.columnconfigure(1, weight=1)
    ttk.Label(fr, text='Save everything in folder').grid(row=0, column=0, sticky='w', padx=(0, 8))
    ttk.Entry(fr, textvariable=V['out']).grid(row=0, column=1, sticky='we')
    ttk.Button(fr, text='Browse...', command=lambda: V['out'].set(filedialog.askdirectory() or V['out'].get())).grid(row=0, column=2, padx=6)
    ttk.Checkbutton(t3, text='Open the Excel file when finished', variable=V['openfile']).grid(row=1, column=0, sticky='w')
    ttk.Checkbutton(t3, text="Keep a troubleshooting log (always saved as NCE_Tool_log.txt in the folder when something fails)", variable=V['debug']).grid(row=2, column=0, sticky='w')
    btn = tk.Button(t3, text='Create NCE financial statements', font=('Arial', 13, 'bold'), bg='#1F3864', fg='white', activebackground='#2F5597', activeforeground='white')
    btn.grid(row=3, column=0, sticky='w', pady=8, ipadx=14, ipady=5)
    pb = ttk.Progressbar(t3, mode='indeterminate'); pb.grid(row=3, column=0, sticky='e', padx=10)
    pb.grid_remove()
    log_box = scrolledtext.ScrolledText(t3, height=16, font=('Consolas', 9)); log_box.grid(row=4, column=0, sticky='nsew')

    # ---------- help tab
    t4.columnconfigure(0, weight=1); t4.rowconfigure(0, weight=1)
    ht = scrolledtext.ScrolledText(t4, wrap='word', font=('Arial', 10)); ht.grid(row=0, column=0, sticky='nsew'); ht.insert('1.0', HELP_TEXT); ht.configure(state='disabled')
    fb = ttk.Frame(t4); fb.grid(row=1, column=0, sticky='w', pady=6)

    def logf(m):
        log_box.insert('end', str(m) + '\n'); log_box.see('end')

    def do_check():
        nb.select(t3); log_box.delete('1.0', 'end'); system_check(logf)

    def do_install():
        nb.select(t3); log_box.delete('1.0', 'end')
        threading.Thread(target=lambda: install_libs(lambda m: q.put(('log', m))), daemon=True).start()
    ttk.Button(fb, text='System check', command=do_check).pack(side='left')
    ttk.Button(fb, text='Install missing libraries', command=do_install).pack(side='left', padx=8)

    # ---------- run in a worker thread (window stays responsive)
    q = queue.Queue()
    state = dict(busy=False)

    def options():
        ex = {k: V[k].get().strip() for k in ('address', 'aud_firm', 'aud_frn', 'aud_name', 'aud_desig', 'aud_mno', 'aud_udin', 'place', 'date')}
        ex['signers'] = parse_signers(sig_box.get('1.0', 'end')); ex['units'] = V['units'].get() or 'Actuals'
        ex['signers_txt'] = sig_box.get('1.0', 'end').strip()
        end_year = None
        if V['mode'].get() == 'tally':
            try:
                end_year = int(V['fy'].get().strip())
                if not 2000 < end_year < 2100: raise ValueError
            except ValueError:
                raise ToolError('Enter the year in which the financial year ENDS as four digits, e.g. 2026 for FY 2025-26.')
        else:
            if len(tbf) != 2:
                raise ToolError('Please select exactly TWO trial-balance Excel files (one for each year) - click "Select the two trial balances".')
            if len(pdff) > 4:
                raise ToolError('Please select at most four PDFs (Profit & Loss and Balance Sheet of both years).')
        if V['date'].get().strip() and parse_date(V['date'].get().strip()) is None:
            raise ToolError('The date of signing must look like 31/07/2026.')
        return dict(mode=V['mode'].get(), tb=list(tbf), pdf=list(pdff), dsn=V['dsn'].get().strip(), company=V['company'].get().strip(), company_py=V['company_py'].get().strip(),
                    end_year=end_year, out_dir=V['out'].get().strip(), want_pdf=V['pdf'].get(), entity=V['entity'].get().strip(), pan=V['pan'].get().strip(),
                    nature=V['nature'].get().strip(), pyos=V['pyos'].get(), extra=ex, debug=V['debug'].get())

    def ask_main(msg):
        ev = threading.Event(); box = {}
        q.put(('ask', msg, ev, box)); ev.wait()
        return box.get('ans', False)

    def worker(o):
        buf = []

        def lg(m):
            buf.append(str(m)); q.put(('log', str(m)))
        try:
            out = run_pipeline(o, lg, ask_main)
            q.put(('done', out))
        except ToolError as e:
            lg('ERROR: %s' % e)
            q.put(('fail', str(e), buf, o))
        except Exception as e:
            import traceback
            lg('UNEXPECTED ERROR: %s' % e); lg(traceback.format_exc())
            q.put(('fail', 'Something unexpected went wrong:\n%s\n\nThe log below has the details - please send a screenshot of it.' % e, buf, o))

    def poll():
        try:
            while True:
                m = q.get_nowait()
                if m[0] == 'log':
                    logf(m[1])
                elif m[0] == 'ask':
                    m[3]['ans'] = messagebox.askokcancel('NCE Tool - action needed in Tally', m[1]); m[2].set()
                elif m[0] == 'done':
                    finish(); out = m[1]
                    if V['openfile'].get(): open_path(out)
                    if messagebox.askyesno('NCE Tool', 'Done!\n\n%s\n\nOpen the folder?' % out):
                        open_path(os.path.dirname(out))
                elif m[0] == 'fail':
                    finish()
                    try:
                        d = m[3].get('out_dir') or '.'
                        with open(os.path.join(d, 'NCE_Tool_log.txt'), 'w', encoding='utf-8') as f:
                            f.write('\n'.join(m[2]))
                    except Exception:
                        pass
                    messagebox.showerror('NCE Tool', m[1])
        except queue.Empty:
            pass
        root.after(120, poll)

    def finish():
        state['busy'] = False; btn.configure(state='normal'); pb.stop(); pb.grid_remove()

    def go():
        if state['busy']:
            return
        try:
            o = options()
        except ToolError as e:
            messagebox.showwarning('NCE Tool', str(e)); return
        log_box.delete('1.0', 'end'); state['busy'] = True; btn.configure(state='disabled'); pb.grid(); pb.start(12)
        nb.select(t3)
        threading.Thread(target=worker, args=(o,), daemon=True).start()
    btn.configure(command=go)
    root.after(120, poll)
    try:
        import pyodbc  # noqa
    except ImportError:
        logf('Note: "pyodbc" is not installed, so "Extract from Tally" will not work yet. Help tab > Install missing libraries. (Using your own files works.)')
        if V['mode'].get() == 'tally' and not preload:
            pass
    root.mainloop()


# ----------------------------------------------------------------------------------------
# 8.  COMMAND LINE
# ----------------------------------------------------------------------------------------
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description='NCE Tool v%s - Tally -> ICAI Non-Corporate-Entity financial statements (Excel). Run with no arguments to open the window.' % VERSION)
    ap.add_argument('files', nargs='*', help='two trial-balance .xlsx files and (optionally) the Tally Profit & Loss / Balance Sheet PDFs of both years')
    ap.add_argument('-o', '--output', help='output file or folder (default name: NCE_<Entity>_FY<year>.xlsx)')
    g = ap.add_argument_group('read straight from Tally (ODBC)')
    g.add_argument('--from-tally', action='store_true', help='extract both years from the running Tally first'); g.add_argument('--fy', type=int, help='year the financial year ENDS in (2026 = FY 2025-26)')
    g.add_argument('--dsn', default='TallyODBC64_9000'); g.add_argument('--company'); g.add_argument('--company-py', help='previous-year company name if it is a different company in Tally')
    g.add_argument('--no-pdf', action='store_true', help='do not create the computed Balance Sheet / P&L PDFs'); g.add_argument('--extract-only', action='store_true', help='stop after writing the Tally files')
    g.add_argument('--list-companies', action='store_true', help='show the companies Tally reports and exit'); g.add_argument('--host', default='localhost'); g.add_argument('--port', default='9000')
    ap.add_argument('--entity'); ap.add_argument('--pan'); ap.add_argument('--nature', help='nature of business for Note 1')
    ap.add_argument('--py-opening-stock', type=float, help='previous-year opening stock (if no previous-year P&L PDF)')
    ap.add_argument('--address'); ap.add_argument('--signer', action='append', help='"Name, Designation" (repeat up to 4 times)')
    ap.add_argument('--aud-firm'); ap.add_argument('--aud-frn'); ap.add_argument('--aud-name'); ap.add_argument('--aud-desig'); ap.add_argument('--aud-mno'); ap.add_argument('--udin')
    ap.add_argument('--place'); ap.add_argument('--date', help='dd/mm/yyyy')
    ap.add_argument('--units', choices=[u[0] for u in UNITS], default='Actuals', help='initial unit of the drop-down on the Balance Sheet')
    ap.add_argument('--check', action='store_true', help='check the installation and exit'); ap.add_argument('--version', action='version', version='NCE Tool %s' % VERSION)
    a = ap.parse_args(argv)
    try:
        if a.check:
            return 0 if system_check() else 1
        if a.list_companies:
            names = []
            try:
                be = TallyODBC(a.dsn); names = be.companies(); be.close()
            except ToolError as e:
                print('ODBC: %s' % e)
            try:
                names += [n for n in http_company_names(a.host, a.port, 15) if n not in names]
            except ToolError as e:
                print('Company list: %s' % e)
            print('\n'.join(names) or '(no companies reported)')
            return 0
        if not a.files and not a.from_tally:
            try:
                import tkinter  # noqa
            except ImportError:
                print('The window needs "tkinter" (part of the standard Python installer). Use the command line instead - see  python nce_tool.py --help')
                return 2
            return gui()
        ex = dict(address=a.address, aud_firm=a.aud_firm, aud_frn=a.aud_frn, aud_name=a.aud_name, aud_desig=a.aud_desig, aud_mno=a.aud_mno, aud_udin=a.udin,
                  place=a.place, date=a.date, units=a.units, signers=parse_signers('\n'.join(a.signer or [])))
        if a.from_tally:
            if not a.fy:
                ap.error('--from-tally needs --fy (year the financial year ends, e.g. 2026)')
            outdir = a.output if a.output and not a.output.lower().endswith('.xlsx') else os.path.dirname(a.output or '') or '.'
            if a.extract_only:
                files = tally_extract(os.path.join(outdir, 'Tally_data'), a.company or '', a.company_py or '', a.fy, a.dsn, not a.no_pdf, print,
                                      lambda m: (print('\n' + m), input('Press Enter when ready (Ctrl+C to cancel) ... '), True)[2])
                print('\nFiles:'); [print('  ' + f) for f in files]
                return 0
            o = dict(mode='tally', dsn=a.dsn, company=a.company, company_py=a.company_py, end_year=a.fy, out_dir=outdir, want_pdf=not a.no_pdf, entity=a.entity, pan=a.pan or '',
                     nature=a.nature or '', pyos=a.py_opening_stock, extra=ex)
            run_pipeline(o, print, lambda m: (print('\n' + m), input('Press Enter when ready (Ctrl+C to cancel) ... '), True)[2])
            return 0
        generate(a.files, a.output, a.entity, a.pan or '', a.nature or '', a.py_opening_stock, extra=ex)
        return 0
    except ToolError as e:
        print('\nERROR: %s' % e)
        return 1
    except KeyboardInterrupt:
        print('\nCancelled.')
        return 1




# ---- built-in ICAI template (compressed) ----
_TEMPLATE_B64 = (
    'eNqMtwVYFW23P0x3SUuKdHdId3d3SApS0iBd0t0d0qB0Snc3Socg3QiS3+yN73ve5/zPub5zXbBn9szsWfdav1jrVpaDhsGGgIBAgNBzlDKQHF'
    'CQTgK+jQH/GMC/mb2p8gd7BydmEwcHJnfb9woTCsjdLChw6x2qro1p4SSFaOIC4dltE0wuwQ20tkG3J0cwQnYeHoOE+Uxhr6kaUiXOmH7asrMN'
    'oArPk98Kjgznhef99KpiXfGPrCZALyQlge7Jt13wC2ZF4RndbPy6N8skaekykSzqVsOrQtWzqc3BW01NWr5MhITxy5NSMAJL7k0KPexThNoIjl'
    'r2zrD9vRlsB3wLnvI/UuATVw3XhYSAeICCgHjxnymY2n8wB+XQF29g082CHfIku+etcPsZw7qLNjAALS0Y9UTUs67LJ4ii6vYkxaJBsSHD4IiN'
    '+uQuk5ua2iTgq2a3ZgNU4U5uppwBZzgLq5tcJayIdDWmdRmV5FTqiBi9TdmYCklc7qF4jB9UZHEJnAJyGe2+fzZ+mF06diQLonrjeQjz9094lj'
    'o62l0Y6spiBTjn1IIfZj4e/RQ+gFl5SP7cXLWuVKh1s46EZGm5qpoZ9WaELaK+hKRMZH6/PGIK9b3eQ73/N5FjBQ+Vj+ouBtx7ouXsTmdTdxbf'
    'askv3Qs4bPHxUzbFjWBHV/Iu9Jr0tyfsCIzXrh12N2gGXoSxhlncCe6JtXuttzDe+D85bRrv//neU7sc8ylGhshbjh9GHqvWGkfD04me32Cmr7'
    'Qw6g/2KpFcIiPey+EPlrCiBSnJeLNpcIi3ewTCekMZPrhFvocbgqLRpphwFJ13U9yf3m84zswo/ROI7tCl8wFYCIgFQggILOCq+3tmZytzW/Pn'
    'T1YQFEc6SjGEnNgd5GfEFc2NCTIWrrXlFuUKXO/yVlzrM3Cvdkd52O34t+KODrm4Z0niYjFgHUU2+yEhk3TD5P5wIEsoF/rArt7LbMpk2iYzQc'
    '3uxEYerd2dXN/zN3+4EhmdZH0Rf15o/ibFBvd12AR0ehDjgWKHW+k7slIHTON+rOkaKnFdLbdV3xOkVc0XYYhQt+J2W8k4tEl2Sw2XJgQjI/yU'
    'iBWozZ+qA/IQjoTXsdYJ2VsNy22/sxaFBWMSQS8t9ZBdIe7/YjBxwTIIIC22OJKHdXn5kVLWAksQS8oHrVKZeRqWnPouDuuHCRSx6XyNsE+n0u'
    '1P/xqMHtUu0ZGybdKR1ea3E59SdUXKp67OlWS0MGEKPBWpu7siJ/ea9TK82B+vAp7YqpaOXFvGI43QOtvRNfnktBsXnBfVsglK3PV3Vko9OBvD'
    'F264k0/1jlyXlsrWCZ3aWoPs57mWVzxhT8bPVmsej1YULQsCrnduoig/2jvZ9FRuOin3WrHpilqeZUpYwL384LqCYA/V9mYFwimx8qguQFDl4L'
    'AVf+1XPvw6/6T2FEypjGzId/h0tGj4gE15/FUqbT3aoo/NHElDEtN4HBqMBz3YYvOjZF+yfZ/2/6hd7v9JmAmdUCR9dL7dndrrIUUNWnDE3A9i'
    '7ng4nPgiJOnL/7CzvcU86l665fuwkWDk87iMos572pei5OP1+2efVs7j44op9EetdX+0k5lUaeeIzFwxkkBbOEizV+NSUzEslcrrCLFwxloSOO'
    'uViBZU+hnqWW5awqwskF+iTrScBcJ7tVWgTyWxtfzuMmu58CSd7MxqnJ36Zaxwmfp5jzG2TBMOx0WtWrewXTk5qw/FC/N3IAOttmIpxPPeR8Ug'
    'sMauFNRtLnjvIzP9Uc7zwq5n5WwpVIIflnfO6sdICZMRQXDp475zU8lgx7oT+KAvISpqbPFWRrsvauFUe+N7CWt0WnRbmIaZ6rnV6/vwns8B0q'
    'FBjrOonxKp0pfeqqpcw4WUmaHcCWb0ahQqO5uJrvZmHgwKCO6L8yhG8c5QTFeTDr54rxKJ1sRG11X+Mj6KDI1H5+Vxa2LJxecrYgLJHdT4yshg'
    'WkqELztbQaisMsO6RqWzrArjdEuRois+Wg3FpwY8vfJDtdoVWhuPoZSe6DEJ0FA6Z1WiHeWT9qbBhkkjeEYpvz5/n787zlRo08QSLIwkLkUk5z'
    'Y3nKRMJbg0ZiP9iWLx4EvQZUrbEoAMO54Tt75PXpZfgFD8anqIMqjGjFg28QNiI5oN5ck9gVzX48fxjFVuyKg5QfTwvRAf9KzqIam8WVhONrgD'
    'JJv37WksxRBVtGNno9Nt7J9/pHOThWKMrwryEF6JcrwnGJWO/fPNmAV1JDhUWpLnlXkkUQGZoqlCI6fRCafCoubWWGElFoVBZqtophukShmjxJ'
    'CholSyutQuTN35fnbwx8yGCrJLo1P84k4lC3PkWpZ3Ou10Ch62bMwE71eTFW0/d+G8KI21Rh8pyR1OKfryLr750WVi7N6BFQ6/bMpTlyN9vKMk'
    '+Bu+LhsRplFlahr6CKegpjiRRBciwddqnt7cRr3DKj9ZHq79GX8/FJeRKK2xezZkXCP4pB/+OgQbNVSc9d/xTu89isQEp2drtXYfuRXe6efSri'
    '7ZyDY45f2whfnDiaIL5a/SIKWHi0e3qRw8/elWAFJBnAn5UjQWN032kznzN3aDobM2Oxz+8Nd4kvuxIdLKJc50mEFEJdPjCyxO+7d/eM3V59PS'
    'WtgYfeB/pn71Sf5GmPaAG140V+gsHq2Hkm47XCXy/Q7dTfA4fPzX4W9jpkEBJeZNawkjPqSGVflgJ5J6l9o+F/ujAq5geuTh9lwHtQ12tgP7u3'
    'uM/BgLYsqAKPdSnaK19x8geLk5t9g0n94TcqKLOEm0Mdf8mc1c0d44rO178Lb0gjPysmxdNFRU0Wud/VnwWajtZl1wcDWwdTqVVqct0BMCb3b8'
    '8gRx3XRCxu0R6p++Pwz/RccYBQLiRAgCAv/Z993sP9g4WZmbOzsxgw9g86/M0HFa4sH0e0IqqFykSCKW43H3INb4E8uvSBRD/8H1XFYudgxJwl'
    'p6OPrXArp0APwgXGcTF3p1L1V65wBcCyFjJj/1XsxhXPXybXPE5uHWT9aJ64GZdw0+Zq2v+GR/M+zE28YfB2T6KpAW/RA07yp6XxdR5M7lVNT6'
    'KpL6IuF80ZZXSAbNA7v/kKu+pscOr5DZkkE2W0hxsrD9lPOj+2gE8syfIUF3Y/pk36WLu0YTn5Tlc2RRLltnu27iiFqWsMpEWyFFxakzvCUmO9'
    'qTG6PB7NpxS3ov+WzmGQensbuuUM4MbY+aDoul+0yJF/aK7kaPivEr1sTih0X4JB3hFrXjcxp5h7zuGwW06j6ZN/q6EK1K8aR9SeUKealCSRLv'
    's/AMkG9yqDUFNlHefGzyTfrGKMhdQJvuKrTwYJgc+ybo7pXpL5lLy6YhUiHFtrB6k6V1jO0jzieE5vatZlfyu3T+p3EY9Q/qATrUKpqP9gJalZ'
    'nk1lhBHgVXZCMJWcqabUn3lJuD1XzVrib6houwQn18u1Zfz+JCiXid+mm6RBGP6VkPcqV3X4nC7+0Jr8YpVAsb7yPgyFoZychNFXbj0h2aCOkf'
    'fi9w5xENnZnZiDkJ0etI0ekgNWvDnG1beTx4CM7OvT16HepO+f2duf1nWiMYDxYhmQRLekbdi1BsUkVkgXuDc6Fl+Z4mbXJNj+E+MvvUCfsA4t'
    'r4yiQhtgOqMF8+pWnveLg3tbiOJDvM8x1P2yZsdydxlydm6ReheARFNme5I/siiTfbCeH1pbEKHqHphhtFWtpr5bWvkDY5a4e3O5HY6AcPott+'
    'xyybl+otr0e8kZd+QErXMbi+jnS+04upxDbAYLVTYk12K279ifFLE1/PqJb84O76GuKbzRkE/8dOPGUKVD9N6M5xFT5qOFOez59JxFc22MfpXp'
    '597HtlF8iBvhBKI82ee/0r36NaW2wMWcot8yiQs9HieIgtWbB6KHNJbxzCFq+eK8kFw8wbcfqqINhyrQMaCTcJiq6FPMpZh36go0r/rR23/lF4'
    'uSU9hyGkAX85gUkGDcHD2a+xzYP9yvp7V6fqGkV7poqD8pna8oPy1vI+JE/YfDwmWHn1wRKhRMagUTgzOTInC+sZJwKU6KC8pj/vohWLlFZUtK'
    '4xllSibt9YvOuX8v7EnZsXFtrExSJLVuvf2I7BBp/aKUeGhYVP9HkpcrpScp2GwfuRya/oOs3KojXEPwf+jgX99YHzNyZcVAT/cpF1pB74kOYS'
    '807M2gpz8ahOGwx3TCgP4jOUrY947Y0MrN/fVZdEkjRQoxKmNkLWJbqjxv4Zcn1s0HZk6O1RjWjzvkBspp6xNSmqSWLiR6X9QgZLe3mLRBnkEz'
    'i58OoyCgEHBf3dcFPOFMulAsoJWUh7NJkmyyUnijexWIXlJwtbM3b2sT4vB6ZwV+m96g5NknAp4rMQaqU9QV6/CJXKwSMmD3U4RzK7+FPzPuMJ'
    'TVzGR177Nf3XKGrvCcTwCclUbNoJrJMdXaEkClllyQ6Z4wOgpxlkRKW9dX9/uDoaaUW+TjX1+ILPNs0wF8XWqtLgHJPix+aRaLsexrJe5DChEJ'
    'Yx61P2KXHhbbuEiQOppAkJ23fpr2ho8zcVuggJnRZfgqX53p/zdlAulv4adsEUuk+udbZcoab1tcMX6sRHYNE6fNQnI99B0qjgUTB1qIp94WRe'
    'otMvo5d5mSSHzrneZqzXP2Ztut01UWWuc2KnjVbK/0VD1jhLUNsartWBCFa7DFpOyo/YOrmroZqjRsF4gUVbDx13XPhxXcfeWiIK0c0/sMLWr3'
    '7J0hb59XjsJ717idpG++T2AJcVfOnp5KjJGatH71wdixW4w0HW6tXOiqwpm25Bhezut9AvDLFCpu5nlg+2nCXX+Qeku2amzpwlT/VRNEaEl5Yh'
    'hoZEJgJbeNHLkPdViLPc+GleLwfz0uHt7xNJVVZuiTY3UOYqkFhmQLxCP80rPBE7UBfeFpuQulVSCu23iYQ+zck+XvEaa9W6m+Aylmp/V0VzX2'
    'yfSl8+QDEm9UaZNJUBGn6/nFruG4GvKq+y0cCI1kSS7oVlIHSf7WG00ctWU7VDnxQ4QoujwJR1wQBU2ZLckp6pE8eKk6kvG9obLBnzGIOSJQa9'
    'oWXm8bbfo+PCKA5ZWdliKzK3Bmnw0NX8it+kX1Xns2rvvYLG1o5DoycIdCnR7V/8kdv/xSkaPybn1PPkU2hYzyRfeIZ8SNlptIJNLA2JeQlwdQ'
    'kbZoT20yFxdabl4OoLdKdQNH/emmu+1SmhHTPs1ep3EGgtmIu1OgN8twNywhn8itWwRkE9Dw9u9L4oC0LjmO/YSdSIUa1Ps9xkSMRzp1Bq/dHo'
    '6OC0zCH5OZ86AyPQifIC1L2FsG+4u+lOf5X+gSfR+6iNljSU+x6rpNWM2b/GJfd91g+Ugiu0CM81wnAiazJ8YU5rztbNpqia6jZmtET4zlsILt'
    'uknCrNCL6vmH4uGT+1G+WiXZZ+uvcKvrELNDmMLoFf9zTS13Dbt6uD0en/4F46GzxRj0FSzaTe7zDIFNOEGlHdxirIK1mx9IMuxTGDyit5h/mp'
    '2q4gF+KFfUWfUahDh+nmkkYm/JnYoBgJMaUBhQGyiWx2dDx3gCqhjOkM1WUrRtHPA1pa68j7HFxSBCSk+hf7rYZGDH7Ou6QvoNxqYMdayE5Jkq'
    'MwHHaTNL0jFRbxM0YjC01m8zfolWNqxKBsM9BPw1sT3b/YIm3ZEoi6E+ZBndRXuhkVusjDpJ3R3eQvnFcemPUx54eTYp8inPuvQZjCiZ1DWhQO'
    'fNygkcVSEMNgnzY1RKkfTl0SzjQm36FOZXv01al2+cTNj7P4lRqXclgjUPjsNpZ7/uKx4meUS1t1V4VC2xJLFj49rIOFonxSQBU9+hZ18jaszH'
    'fnvLeQ3d6J4oGYKS/Dr3+PUaqY7Sk4YdBMQdg6+xLsJ1c34EC/rcDvfMf753O4SP1uWQSsmXy1nzKnlml17jsU1c/WZaYRsIWMuBim1RDjU2F5'
    '2sp2xnpuEuE+WTCOGvCCK/w4QjKBRzhlyK+mf1nHVC9Qqn42VfDCqBToN2aG3GZb4XIk6z+HCNxLH4ae61flp6uhVg6DuLI53GSC/kEfhKORUi'
    'QgPf+yHhti2LzG1lrc2QUqvxwLwyCfPOj3qK2b6Fff0T0aV9FPTH/e1XkcKSIsNMDUDW29x3oNNYd4W+/K1qCYy4pp8FbMOQx1ipLLTPyt2GJv'
    'SFuNuLA8ZcBFnCLWqC6colpKfd1BULluoHMz8tQ205H8y/1k39FFC5bLJA0o6zJMfcdEx+zC8JX3SBY0D2+R58xpsjRCx42T1VNKlA3yp3VcQo'
    'bNU7NyntprlIUVggPKfsbXcCLnJGrgIVmQP0wG7tfEoanqvfBWNlAVdZGRgd9Tbo6sG1PYpY+AmVWn4EGvGWDbb0LfJL3vkH7pqcxysPtE5b9f'
    'E42mtaDpMEdJqp7y0bkJLWlEf4koiMAJg+cyN4QIRvHPcHgk3TK0L7xo130h6cmUyp+hJLbVghaY4Gg5ZfkzElt2bOtR5QYWZ7WQ13iYc3aZok'
    'OI+1ptJVR8e6pX2B4cc5Q06gm5zqXAi9WXiIL3h/HUtdpzewrzxfLQrvmqSTaqST6Ha8fsx4dKfg+7agI7XfFFhAbz/q5VqizJcBnenAa/FXFH'
    'RBmeo5DDRyTZq2/KfeUvwsPxtOrUaVreH89lhtChbd6r0kbun4foIojX/FJP4ULIi8qF0KHW5xJdT0upV5bLHcMpOVYXYVQnTn6z5b88j3ScIG'
    'ZIYlYeXeWfrFqM5OMWFWe0Gh+NcP+O8EZt5csfm7yyg/L993aOMMzIpJsOhFUjBBJX5I8sPl9/y2BXafjTYV9sPTp8vHA45NptsEzfmBWF0k4T'
    'iExfUvxe+yJLeJMoo1yw12JBhcHYyVL0Ez/OEZ8dEeziiuAnI6Qmx+ZOeNoOogsYekv0dxg6d37wMJvKP7kiPV5hnJfrkPyUT/OZm3D1DziXmG'
    'HdNY5WbHoflL7l64r1xuD75gDqupNwWkUpIvz40TDOWy2nxpVV2/KTbNfo4mPtW+XsufGK6c5y9ryxuf3MP5S8j/ok9kcGHa8GRs6Vz+s01IjN'
    'nzAL0clill83bNNZSrURvjN/s/2rTVvqD/Xq0B3FL1cNXy8zfheZCPvMMa6N/lftdVI/0b3KB7FMH897KHYcydFxZ16NUi8Ds75BsG/tpllMEs'
    '7AgpBib/PyTuTTPek/dyVRKXMK2MCuxIr/f92VsIF3JXq2TovSmI/0tfpz/T+IIMdQXhFllKXihfL8cOrTyekYZsHXCOqV7Y6+OPgi9QWh3tP4'
    'QJACrr7FcmdPc2JmbHeTEsFX3Obz299OW3+mzG2IB5YuFKl1K+b6w1bh9bYDzXCCCKlDvmyoUS+GDOtQyRJ+6Wld8bHcavKxcY7Tb0WVwuti+q'
    '1vtBLCsGjLpXjj+bltfbvGvP4ceW252KWC2VkST++XzErpzRfG5Y4PWyddjPqDZlndO9MrNEIfoHOCrV1+3FplrUnrrcUvO56UpVidsEfMd424'
    '7DJ1dPIb66zgRmQN8G2XSlQkD8n7wHbt2G247yt940Gvcmn10jqpK2Uep6+QIGx7jypStuGJEkB6O/yxdKw7NUxFgBX+kb+8+rzzey9B59snxZ'
    '0yITybqbK7nAudCcxPkAFS1KpbnXdfWiMXUhhb+5Kttw/bmtq4Ptqjhnh7TdKbrQWkKNEFqred7E3h+uNRPtWmpM+/xevroqotysLs8PTjCaW1'
    '1xdqrnP0sWD6zj5FSGQfaMl144/aqqKhm1Y2qN7nXzZXoYdCz27gkTsyVvZNvl6L8Pe3Q8QI0updH4t8X+NNmEP4N79XenAyNzu7A0OZ+Pukj0'
    'XLmQ9hJhQJ1GXaFDO/vzQI6kJGrudCyRf6OOva6SRGWFUhaV9FNHGGF06pNJOxJqiLlzW3u/lSfs83Qv6gbPYtRjdvCnYNK1kGRg0tWeu4eU/L'
    'oRpdAu9LouGdoEN2stYuc2LhL36xeBjnw70GRsXTrTwwzcjrAwWt38NwKHpSYeldCeFi2dO2mH+kvArHN7PG/YLjpaE4mNihLvf7ruM9Uwvp41'
    '5OhCKK2pxYyuNmUAfCj6BYBcQfnPb9v7HIMrBqJoIO4VI07ik/+BogQqGIcpGZqYlykZstBECEx44h/rAUdQ0coRMegqKR8YsbLlyFnswVumtC'
    'dMU4r5polzhZey3iwRhWj1XzhuxOftDOQcf86Ntm3jElt94HZW7nuREUzsqHeURTt+qLTBbReQHFOS9eA9P99B9ZUnqWkM3EJXqF3ZZzBNVCgd'
    'pk81TNnP5Up2HiWDccC/HSbTs1JNaOIXptxy9WKcycRH+nxa6s14Rz3wVz35Vye63AxYxVF/6YkLQ6ndnN8NR8VKzWwH+Pj3EyOVWB6eLB1b7a'
    'VzskGFNhgtMlw7U6Keu4gBajTfRV73dr7Q8fY6NUztk1j6cxe7WIreixKIfe6mZ5ItZOF28/pIZAqCV/RD1s/YR5X2M1lB/LRjCEDIcD0DAqqw'
    'LCzg6Y+WJEU5D+u+sU4jbQ6hj1yOJHDKfi5Pk0ha5wQ7kiR14YfIZwtHwZHRkT1XX8DTaDyX6LOta71AdZl2sKcDxWXJC6dmax+GlXa2PWknSd'
    'KMjGIUm5pVTmolwkmHIEuKyqa3OhvXQhwQeEFzFzjO9cF37OeI1+lqzfU6K5IcfJMs0erTtz+VU0FYwn+n47OFb31jDY5CXJFTt8RA99wSrPJ0'
    'zZB5xdl11Rqxiyu2Mu67C3JiaIPbzS+D8MpCxQfvQFdnwNyLfMimffF1M3YSrHiMgw9uk14dpbOe6+6g5LDLllQsMVWqxas1gTswyj2lnOhrTy'
    'wZx0hZ7MhErPgXG2/UQ3iXHQolcQcVSHxnzL/Rme7QPjrQKJ9jrJoIwH1hT+F+InxB00/cUrf6dekd1urdOB4SuDkuOUQ1qE5KmOBJ+UdltCOC'
    'Vh4oLC8Ui24uqmKUuoi5dCl2k8fZbeU+vsIn/kMzdrbzE0coamOacvHRgcF1IvizIq8dro+kiSvuR+jUmVZWdDqu01xg1lGVEzJuE47exGQqrl'
    'h90BfpQ6kj+0n2asyTNK9S3tgJpzEEpVUParE7KG1TZZ3Te13PqznYW6rwGiS3ywi8DjViNI/WxJLJb0RLoJq+Iicc0OWXXkaHvdP2CU2x9lmZ'
    'WnInE429wQ/shoRK3Y+2XS2VQk7KcDvxsc6e5nm6OxVOL5OTDH9bLOnccyOLge3fYJY3FmmLA8D8dYBTbaRTdYjbQAyU5nS5ura5tRDTYxmY0i'
    'QP2l6Tal9OJV+93BwUvlDifhS1toyWaoab/sbdFVxgrIEb4csvkyq8TgKAkNrkSH9yr1ClSHjolbanMKeTo4mnzrBuzUm0VQcIxeSIw/emUSmD'
    'x/jSLn7zIefit/pY6Bhlw/p4MsKkbNdoWFoITBZHKCYJRGWI7KUliJ1d+OVMDNoJ6RlcNpG39n+os6se/CI2PsZGo4Ve0K+0Qzuz9sJYSlpyBM'
    'bQ4H+NaUtpI9d6T+8BW+UaL3BSXRhad3XWNDDYOoD3xuGbGhJt+YY921WngpfrMUHynATkMrCv/O8XzGQ89yrR2+M7QA6jGLzoyclc9vBQubx1'
    'U96DRHDbq0SCmZTA2ZXX8rb3HOZkut9GjnyuKP2+we6ZXk08hiw+LABjmMHgR3rnrC4MBiV/7a/EQTK2WG9W6Yyt2yYvIgK1npUeSxyX5ty5bT'
    'kPrJa3L4tQr1UKDbEtZq5+GbvkNkMf4xEmMrTW512PafJ21SsGhkRBe8T6t6BjFIROEKF6sv/NXizexet16jVqoVbNZhIl88WSKVzuwK/LwdKM'
    'QIJ7p4RKQt/Nn+UVgCCvilp6WPvUAgAz8sLiL2C0YOyheIlN9+9pPcQhPAF5F4/r7wTieLHoTrpHIe3cgupqETsqp3QnyZl8e7qd6YRVq31DVZ'
    'YVcSbioj/0ZCnnYjVa03Uc3ATfGFmo/4mkGit1tcDS1TOpplrknsux8Kso1pS1dhyDaneZv3QixayOFvkMqwmGmqaFqk/FTscrrZ/P2ppAp0t/'
    'MGrS7FMgRyVZhp8mmf/6JfpedTpL/m+zadSEJy6i2a+mnHTfujZnK+0BBCOEs4r8mynoAEtkQWzbyWEaY4GcqI1Y1Mfwn3anCe4C4Mq19Vdn5K'
    'viLzgVdWrlVRycxo/zfFxDETk/doWx2Z+FfOcy8kiF0b0bp5KOGG/L8bJ/FT5J2/Mr1RavHOz5x00kglgha7exmQHyOq6i92JkEWg5AZ/wrJNB'
    'DvKaynhFuFHjYvwS4joh5LsBSNbyR9352E9iW1qzwshBj3SFhJggrFKI0q3X5h3ZtR2Q90ZUS1LUmq3dW5NG+pRsNEp0cwN4nmf0yOYGIbMFSg'
    'DhviamcA0jhgKC3ILSGnJEIO5w3PhHjd/Y5J/M4p2CLn01k8LxIW/Ecrmtfi428UNHZSCodHlXzsNHbhRi6xp16fkpEfOqvSoGPvrTiv+lgZxw'
    'W8jfuTeF6E3biEwYLqKFItHXfNUxkpsXiks6KMMx0vEZ4X586hfiw5Zr2d7dfkTI4thS0Q/jmcV05CFbZPUyKrkqsISadG851ZpUJwhYpTTO6u'
    '9y52BYXEW/Os3vnqeOy0JBe2pUgNGWvzpCzNGVRKIrnwMAtR/pWfohwr2OniLXGUWEnLqXanRcWj6ALcxNw8G1PGluN0cLeQrSd6rsn8UUeh/d'
    '0aqhSa59bDL3p+F+7lRhbyVDK8sY3/0Dk56kAkmYythUTHgLChrUqhoSqgLBOn5iGOrm4hoPxwd2+Cjv0bye1si66EQ/wzB6ySmCEn3aaXxnly'
    'd9oqxNreq66CwLdlbCdKaDW7X9dEejnE4SX0kcVccYl/t4LSX8lGXDnpaghgmkP7HGT6o4DlFUdx89cYmO8MeCS9ti5J3k6kBqrq6unjAr6hwg'
    '64Eca1LvdaWVL3P6VM4K19pXKUw+fUdt1l7BloXdZdvZURvzcLFuJt2/ese6Gw1iJSZu6IEjV9VICGaorvHk5kRQqjQhflKQrCkuUZC6qJ+Caq'
    'ihDae4+M5EVp29J6Bu+lU65cain9Z9z1oBn515QYuodZMs85QS9FggwHTn6Nc3vWt+spLiQ6gQc4C5hlt1+WKrr6CmvEWYMXOreCeh53u28fkJ'
    'bwKg4HHn+pi+QwXQdI1DQaNKwe5lAunNTVXwo2XWUujGjSfcCKI9mYjBUcr7WkFQotjMkm0S4jUpGlahUSeRg/1CqxNvhuI1Af4OK61kPRczkk'
    'LzjA+6eTGv+M9dNG81hHZVKtet4j3KM+7OlXc6NhN0c3vaIJmFtHrilbjP68rX5GdyQTTLdj5s8TKrXSHbReP2rIoKnsj3dKyTzcqtXa9Plv/9'
    'tOYkjyhUsPPAQEHtX/upNgB+8kdE+c8gdxHx4fw5nKGwyLasg/QBZoxpeJS+RaWFaeHS2txIgvSTMGoC8O7TxceYlYRc54m/h8ZBFRXHNiLs6Q'
    'I41YSuG4o19zZPq+dsczdOLJR4aG1TO4wNeOfuHjuY74eoljKRSqw2JC0mfQvYk28Hc1ZGDX5PdQlenWDsYJxtq7pUuaTZqNkcjtgQfBUUNSj8'
    'z25atRQ+9Ntcs2rD7ErcffGIIXOHgdxA73XJhPMinu+d0oQ81hv/mHCjhMXq6tXpEYY3aW4KtG39j3Gp3XmiafTKdI4NoKGhO76wSSYO1tQK+F'
    '08aYonBXktz5ph9rHbD0m211/ViI6Zvrx6PWgr0KPcX5UintIIr8J3v68stmZAfttDEq/46NCjbBZsfEfeJkvf3p5pPWvCHRiA296ETMQbmD3J'
    'BKfDHLrxmOR4HFTysG9rOmhO2oMdVW41F3O2PuPC2OFL9pvc/cKavn3MLfH3CMj3QcbmO7zHT457HDROqSOsUd0ze8je+1IUMyHrqjoVU66uko'
    'p31TwJLVbiqW1BIFQ4fZRMHaEdBbJl0hh9k6lRvVU8VzyPyliD1UzTGS+Y2k91L1qGI+mrUGPB7F1rFL6gfrkPmStldbHFPbBOnBr9s6xqbxkn'
    'FaTOM31yEtoewRkfccvcVlHMurxEMcgvw3H02bfjGssFVvvc/+JN22SgAVhjyrrUURgxOmEY/t1hFU5GlVFLrjOTgnhizwc4/MCB1WdlAY9XNs'
    'MvY03cBin3xZkjzshM4Uf8HPNOJu+dmWFhVMqgOayB+yQQGmNlhv6CWTd+nR2fsTUNfuRxnY8Q5TWPROfCxYbrbQ5/S1b5snxdgFOBbEqkh0d8'
    'mU0P940iiL2u90JzuZdKQhbxtLobnyyhN5Tcj/TpX4ONJdfJn66YN102aIe4IZTQLKEn1LXKB9iwbMexwB6iku3VDtyR5PA2xNhipzAqmDT7/E'
    'zcnT3s8a/tBGI3ErH33b0U7BP/I0VrRBhtlUU77/KXzUf1R1Es/J1rpG22TMnuFM8HZf3iJhqIJp8P5Dn4DqeiKUJTZPsXAKFB72rkqukr8I6m'
    'Ky5El5qHfzTkGQ9/DdCc27alNcQtSBKlKtDwdTVmgajLkyjcO3h6aLWpyN899vPTQqkQMZay/9riulz5r0OZAWSwvnaL8uBusMeQ2qLicTHNIp'
    'XtyvdHyfUzrBDqqd5yX9gIukWXcBz8DM1Pqm9RbH7Xsf6j1+/434Ot2+B72LN/lN2OD0mOMYdxNq59buHs1NiG20Tly+Tx2NalMlreDZw4vPKC'
    'NZR38CZbsarMx7RD36VcJxqZTYfhAUrZFXL5ltyOH/Iq6asTcKu6pjHnlnCXfnN7OqaTnp+Duj2IPzQU1f/XbP16uAkxC9dtWD53z18aP9KkHO'
    '2jJPsciOcD1zLIqYBnN5F6EGM7mwVsCwoaS4p3qhkgQczq7w2ejiqunVgvZPzvkPUbRr5BecmMsES6IUpVN67zK8g97JvUPmSrxdbIusvBSIIo'
    'pSP59nME1qo56shqPzQJxMylU1fD1d8Nqbji32lfr5Is2XqH9/KIwsHbbJS1V/qJQzJxbVCVWdz0ukBMLLmodJx4Rflg4KB9TXoNEd5P77Y3KY'
    'a0mhdtE+wKOowrv0vQCC+vR87jCjem7BJTKmuixfYSHlawG66eLX0IiLSXViia6fptFUFslk+cTfhdbVje0sV7j+Wv+Ytq8SEK7Im5Sb7zhGN1'
    'mtWGlxtcSs9b2NSvuQz3wgbcQvD6VTkTvtAEr/pQM59FdGRX2DTtE4SK9dszzkU+yXXzcU+Q38vgz6rXhsHkBBSUA03MvkIrjz+UatsdL3QJOP'
    '9XiknU2oeI7+yAm+aNd9LF0MEdDk2JF+h4bgoOkfzcnbyg2fUrtkEksPH3UViGuQ2sYk74NXtP5euTZaiudzQfJLgoXojUvTX3t4VTMkwnRaP5'
    'Q0kBGAhSKSIwfOU6CzlMTvtvldFX7IGWDYikLWepTWxFoqyxlCcKASkRhBpIttP64dKSBihlWkdZD0d0JypnUQ8SeBvcXGn11Hd2ib7DrrduNZ'
    'nf9u79R2WkBsb5O1duyuV9qxdtZQdEM3sDQ8/+OsG9217Yj+bInIfuDHE8kActRWMFM0Hs0AcuIW7PCZai5w/Py30E0ObX7ReELaI5xFH2NGF6'
    'SFBb3yHNscNtxFDtz9HdqE3xjmAktpAY50zzTwQx5A3nU/C6zPbQMOQpiT51zReC08hq+ImJVBMeT8mZSjU8IvS6RzwlHWu8+geA3vjRlLGIBD'
    'DExdzT+XArXt7v+hTb1QSuJW3QwCLxpv8mwT3kbk3dTZpi9F7mfbv+8EPRy8BevcluvUluvQhs+yANsEOq7vQ+GGo3wXo0Y28Cse9EN129yD+i'
    'gBdziOZYSHQQP1dVsJSqJz6Y8NEfM9PuglnztfOju2GcA1T/aduZqct7D8MUiFUuYxFB5A5h2wyfwWo9J2EkSY/4tmSGe0MdVscuDlhCJuPj/u'
    'Xh5/d+sJLY4Vy749H4mdu+bHnqI6BTUV33erBbwk2uGGr15s919VhbZWKLSjoRPJCX475Oj+pfcnX8NWbxhPGeUP0/cHoX82/qvtpdBKDgiIz7'
    '2Q/1vj5wA1/m/eeilLPPE7d49IlaSuZUr2S68dyXYrf78x16Olr21tVNS6Gm8bbnh/oG4xTD7kkmbUAVkYhPBCWNrY6jqvfAPFh5T2FRMM+eDN'
    'Y+PY75SVlDlroT8PG4+O1wuWRr/vvjAbtX33vqnx1D7Otm+vIhE5f1frrX28kbM0wexq1Fi+PQDh2eQ7pVj8u6/nw8PN4dz1hr2QnZF3x5+GDi'
    'OhKp9lRdc1EpLkJSHDL8fcHQ9XOheHN6G+VUK+P+6E2tyvHha2f80plT90tHef5czf5XALdZOi1eDFXWzdmlw16dmTUC/NFXcI3uV5exTL81AR'
    'nfvOl6+5mvH/8P5xz7VWJfSIygTjs3D542cHV0ZojiDDidbTaccOyTjLZ9+HIbGnhntoplUsol6fgFV7ro4bIUZBTxKeoX2fK5MTZnPEp+uD/b'
    'F9ku+G3AQ+q74h5Rdb7lcksgMDI22ICUhCtw8fGj1rm5+urwYeUjoEnSaoSLVykteOr5+W73/buaTSXC2796Nn3BncnPxsLC4Yc7JVn0m3TEBf'
    'c70b6/Hvnbh8jLmb29DiryDtWSNJ7iClSlblkHBYIv16BLmE9lXhum3P86DlHFYczWVdGRrtqq1e4In8daigg1WXSyp06EsH+RzCFcNBE3Qiru'
    'bo1/O7OxDHaOt2CO0QB2jaWkKQ0tOk0rdkYQJPIxl7KlFFYnVkyH986pfWKq6XY0SHS9LE5t5fOi1oC9Sn7Eo6qU9TTakaVNeNqShl5OXf5hhe'
    'tUYvLqLM1VMLlYeflbSOKXvcjVx1vKGztwlhsPyGyAsTyCBGPokDt5LOdI5y1KXI/KRS6RhnGWSLkS14jjJW0K9S/9uK2oeiiWRJPDvPpU5jAc'
    'ugSSHrhtId56wU+kTXhqlman5fmvxsw6F9kF39LSk9c8PveUmBhjB20oNJXcKkRSrF9v7P9VzW9Qp1Lf2lXSefxMMWvjjb2OJptBKW/dYemHdV'
    'GWvNS9dqamjgs26WeTu03T7GMchWl0SwZvGWhlWGofTMlgoOM0E8vowwB19QHlPI+mNG2IveGIqFGYnsvLTZG66ZpsGE20e5U+/eYsGnt2sWiw'
    'UGN3HGuotU5xTc4pztY3UqMUu9v2KubIuiZFeouKXBl8qXxMttPma8K9BtlGEouQTula2gaXhV2LPbql+4luzgAA9JMZ7E535otj9gqEGx/dzf'
    '6MKa6ywjDCzIAIXKAFPeOrIoArJQDko6yv7gLcwZ+dBVySA7RwLB2rwL73lh+xNmW9jN7C+jw6WWcUmCsJGTlqY/R/F8BaD7KjGt4BUZ4CW1yB'
    '3HW3/U+5Wv2QpaEXCi20qBq37bMC4x5yo2R3KwxIs3t4w619bd6MJkl1Qso9683AyZeooy9rn/G+Tyq5lJB2siok5GNpn38OvEbKiVxf1DkMtk'
    'CWatKKckaSFcalu76aXd1HJ0qLB4rByDsXD+EVnEuXoU8eKQfvRmsnYp1kQk6yqNGphIkkJeGXTqzknLghoCvhl0s85JVp5z7E2lohpaMrkl3m'
    'jcGiXH1iXHBTl9Cjhl7QRlPmMXTaXR6WtUjsXdd/VoHvFf1bYfFvFdu5XXH3RDlcwTStTMZW1ROE1oTn0YJQmFsA0SRIryztQ9OuZ1zMoG6ZRD'
    '0F5O7zo0X9tkib1WcbAyiJEfQtVIurbxmj169EwLbZCSOAn+EUrC+S3F/NUiicY3PEuyRZK5bx26VPlHKldeMlxQFtvSZvEQ6hsPka/54xNhOv'
    'nM4ikoIY5jZcxk4QKjZAIUkq7Z8W3vlT8otIhQyXyAWmdki5JRgpAnC3wlAmkVJZ6/bsxhcVBHIwPpPmvrXc8B65CXb6OSD3VasqebWAbBX9aS'
    'TEVPYKq8MlY/jSMcXGYPg4gsLDV2Ao7Zkn0qHY8LoTVIIaPX6U+QJl40a/J1L94YqAJvJJcPTUsRWhrFHrIfnxlBQieEdgxKALbkVtGU7r0yi4'
    'Dd4qsEmijIG9zSquRBCKbgunx1uHVO1bD4l37c0pQKlhDBEg02lBx+ZWKaIrLQk6wdAgpQyhKsw+pYJDK60OsCbDKYhEcccNks2LO88qZfEcVE'
    'VIY5JDNYgBqLUskEQK8TpPUX8kBYxIrE/oSok3gt4wDhHiqfLw4PQD0zXTRFSafG4JxOlaToIkGnVuGSXtSnqGEOXHNLp7pSnAsGzjzTqTSUCu'
    'Q0irSROBWs86zDgTOUz+DEZxNPpWtIILgHKYY8IZZfJwwmqqNwgVBGKogiDa8qlaKSmS/QqM7mQpFyF8IZsexxaLtWqz6kRaGcwULO6VbefFAP'
    'bMnCFYr67VMmIqFknbffltPtqZuULKbhITSXW0aNozK3qsRZcixjMGt1Ukyg/lCoW9Z/V6rNNJdOAaGB85pcCdN7XzaO9SaV4mYWh9x0nTXtwx'
    'IdVbB8fAV8JydbmLU9Ku5aeuFtw/DdS7mywQEzAYiQqy0ZHfWoa3Zta5tp3aWWvb04mcQrK9TkxfQ6fus64LqtTbx1Ke+JJe/sZZ1x2fBdGpqG'
    'QGla2W+fIjEXJbpiSS+hmbx96it1ztWJ3oCyeUrIku675pDTT4a9Dvgf9TE/lrXl9HRuscE2a8gLsIUZDjjg22aW8OKtowJfhhyqBblB1cCLcA'
    'RVw6nagQ5FYsY0Vua3dYgNAMlw6dTqRH3JrsxLjaxrJ0ZrT10pje0H/Yiy1XCjKQekOQHaIoKjh0zROSWkCuu2nAhYza+fCXOuIFg24oDkqmJl'
    '4q8gmiSpwmgBR0igOIB0iJCPX+EB6QG4fRz7Tn4e2liADaGGxJoAubhbmU0AtADYVfTTkqV327PaJ/D64NhJ19D84NhbDxAxZdnYqnOeQrnCLk'
    'rhpf3ACTg6XRtpbsFOOYCDu9AcJonMPJiNNSSyfZ1YIVBqqqzfg/I672gjuWTVx5EdwJDkcrJFAUwZfRX46gDSKgJQXe7bDXV82bYcVXB4AGNs'
    'Ok9VSY1fD4mSCkoHJUApp0v2Zcg06q/VCP7mnij5N/dwWM1hClDxX0q5U+ig+xGCc7SLe9b8kPqF5gNvKDh7L9CdxLC5NhOe7rs07SbCkK1vOW'
    'HBaiY0adnaPDghmCeWnrNHdR9A8Av8XYB8THr2vArAw5mCMupg9bnViUuAh6xzVsCzAA87AR7+0Db+rI/pRwfgvbsVvwvInQiONAUmh+7kF8tp'
    'kzyOPQ5Ig/MgDYq3OuKNePQAhqhfsYPa82J1oq97hYXo5EGfIRNJbOrycpBi2JPGUvkvAV6qXxZGlo3fvQn8uwhL5bkE0TLrk18oZV6q8pyLwJ'
    '2yHGztOYBIyBWXHIjCKV5CEFhgEIhBIEC4DVKwUvpdg5S5SwXyA301LGABAOWg3SPkTYEn1AZfDXpC6JLHUfBAAFyhOYB0j1DXGvGE0Aqty68A'
    'WohqWA2J30mcbPrVpELgfja2WtSVD2B9QFgAccD8tGQgyk59hjHAUZHSQBDYmGGmxYd3UQGMUjKpU8n/YOjn9mwOZDOpgCQ9zTDMBOrC/7PyxQ'
    'z7rrpvgIxoI8KzE1XmPITMVWZmeMvogDtlnrcve3RBJ89J00b8TRoHuaIO8MHg61q1bnLg9W0gpxHTQ+HnUuvT65sFM/8UN42i1RFobSBWVMWB'
    'mQ/3EkYHXViPAhMWnhBE/82H94ABaSoCBtQAGNBwCWBAtn/DW+qpX12KhdavTjT8C3i9/wDeAAx8bZAUSHAiYJhxAef/yfK9SZ7Tfu6L0yDFYl'
    'Sr9jhhCNTJr7ec9vjRpz5MuMchG+7AVxDpi6hxFYPzeu+a0Vz4KjMBYuuH/i3AQl5RsYu6xuqES8n+XjGGzbecA+WVhLdlU6ArtzL+GlGAb3QO'
    'cwD1v2VhP6eYKj6eGb2JW6FCFHQhtbQbWsinLIJxuDd0Lkpv3F/YwCuQ2G4rCtsG2L96B0nUQZD1B21TAuXm2+7oNTrzk7ITFqgUHAKAWdWQFK'
    'mAlbg7wcmNhCNAW1B2Z+xUoAyqSJkSF3f4RwKD9CsIJPXrwlTrS8sMQjAd5j42NYfBakqCnbA0GtwTTp6dSIwqjrYU/z1oEsCWJKSk+wXrHgg2'
    'Zz2gF15BpIrCicxDTxKEiXeJ9HWXsiS6C23/1YDSm78aoA39q4Ft5bmZk9fznkJzBS3UfeoF33L2Va4SoMoJTorf+idVg9mo+YJERQ8tomuAqq'
    't4+E7nLyHMYmVmM3ve1lX/JaT1pInpMyJcz4hYmv4nIjpRfzmhWZBPba7usjphDbSCaKAV6ESVZfvgVc8DJ2BBgB7Zp4bVBFpBPxT9FrgpZpLz'
    'gxIEe04kqBFotGnIo4JFaR8nU0foVp3JDehjos96lYVoAzCAZdSeM5AflLJgKygBvbkC3JvBPnD1txEcmBJrADZpRIpc2q28+3CrLY8TonXu48'
    '3wFQn47ZcYWM0GGajJ7VX0zn/ykaII5hQNrEygARz2Q66SA8owydAeIwy5WkU3RgU1Aj+7OGlMIlDrSLyC4AeLcf4OEg9sg9uA+4OqD0ius6Cs'
    'eE2i4tJH2P+/e8FSLxT995rICc/OmE/8vGGCGqtKA+tADzgpNl1HFPOn3XsmAIckISNAAPDieuhfgVtBhRiYAGggAgw8E2Al187oSwEPMICNtI'
    'RDk3AazOsQnZbsbx5vApF96tG2gLjMe2xouyV/NCetiJ4zBmYaUNGJ2cLkh95+rc4P2Zr/C/fzcNImUcQKVIEW5D8QlXHS2ETvQcYbdl2L63Ln'
    'eTTgj4RjMO8HxNmrwf3pJ6WBx00WuhYMhOP6CQr3ThwU7lsuzhs/xBhQV/33hCFfOmA8E6EbDw2MP1bcqwMfVlmw3TsENS9CNhBOFgaeTf4WZH'
    'Xxe+COc+bjHdHi/Q1uuzM4nMlGBc191lkn4UPn3ybzxV5l5ct8CVGJ8hVl5TAkcSs7d7zFdhQlf77rNupvensz1BHCQ+3VQd1k7u+1bXGcjPZf'
    'bTzIbfRWjdfOJeeb2rrGt8ea5rcVQKSaWkWfxA0TPwJ+YbSKQJjK/b2rrfkt8gWcVyp3N9UOqiurfZDtKOGh6eogYRr396G2ZkN64GYad77Fjg'
    'LD1/263Ix/pfusWUYgXZkBYzCyrItWKm+Yn1nOS1wOdJag65lqB26UAS8h4v+aLChXlehnjw5c2OGZ1J11uJ06C4pGWtKgSTQMlseIaJSBXMfA'
    'ua6M8hEjV/DS71qs6kQKas6OEa3/WzJmsriBUTjAK4C5ZsiOaB0OTOhnA9EORQkA5gpizLCAwKjn8jZIrbQbcjuti0qkAL/ht26pyHizrjLXtz'
    'LqDzX3YA0ckDSMpseIJlUuvES4nf5712T7TBKowLxvsXqFb+sJSvF5rFh9DW5g2GDFzEtTIKF5PxPogHP/9xWQEh7dc6AZ85VRyJgypmPgDXD/'
    'iCc15hb1XyX9F4Nk5BH/nRFYomTgsS0U3KMP4kRirxxsQZG6Luv+NaoxqhowHkDqI72T0EHvtCnENBeAsI+VBflyxPuFYU8IjdAKUFEKdmz+Kz'
    '/waKY4AB7Npp9Hs3eRXLr/Hs06/9/RzPR5NOMqWVo4sEAD5sIaux1FvdlnGMsiWtOgYcvu5oDUgU1gYcYbIJ5bgN0OBBXY/p7RawTVEy1QgXrf'
    'As3hP2Yxfbxnxhy83bDDj772MQBlOHTZC3aAjiqR/xOCyy5AE7wCQlYN7M5EAOtoe7Y9xn+pErikT/7/o8r85/nfwTsUEKXdDkiUQLLu/2OWPq'
    'rGwDx8q2081/hfif5rspZ5KwtxEgc0vd0lfNtuYKMJsnlADH6NgxxUB5AswWCicmICezKgOKDR6n/mqd67+QJ7nP9W2P8A8j8GrejnQcu0bup/'
    'HrQ8/ylEvv+bECGJOTuwnNnhn3cU4I4ByX08lcirwu30bzcFC/FfSwF3chGwkQN+05UX8SzELNH/SDBUgfL/qMR/iQEzTTWmqwgPpHsxqim7th'
    'hggAG2lt7P8/OXmOBW0DxzBU5uBut5mrslAdwceC8y4OZjYDe32wG5uRs7PDCzlAPvolP3luG+sOCNwtEcq8O5ZIevo5LPj94hWcNgkjnu2dLr'
    'pmSljdEKkot/OnVXaKLgc4rhBr5An7nLNfWbifBXkRMF8H8K5ROlRMQnWcNiUmGCQUCZuj5weXNtJv7H3HtcAHLKR6fYSUl41mj5YNkJA6tJt9'
    'FpQmJUZPpkuWeKoC53q1lKjUrGrneLr5tyKNq9jVyfDXrGW6mJ4mW8hbW0GVv+plGMPUIKhdzmGeMGQQL1GY8ED0waJvpCkCyu5OgsBpNKQy+W'
    'tqhr/ccw6gOEahrTTUQiMqxteX4RpcFCHax1q0+I+pWkLb9e77za+3S8YYWalUvdAgr5u3cLZyP+pxK/IRZTmr8LBYtL/uouiT1iipnbyRkxcE'
    'eFf/VFFWsadswBYuirFCiHCK7ZMMHy3TPUDcxtNX5IUJay4Cy/TYOzbHQGZ8m8As5ywBmcJftKTwFnp4XXR9e+AtoEio7NM4GNeDNtiBgRukhY'
    'OLibEAeZGgaSNUymqXbS03AHGTZGki+IC6n6EQMvu8kGG9ybKNXzWaBuoh3C2Jiy/XbvrjxLvdjy72vs9oUnMY9SrtSuYcQf+ojnBOBZ/cuv1K'
    '/1e4koDOYEiCrzcC41rq2GKYY63dvI9OOJIgcALNm/4kKr4cvdm8q9VqOnY/19k+0g84HV72Qyf1HFYF6giowo4GNkaCOotIuKL5hUFPuxMLw7'
    'DBtdlCQThWgvyy5jbKXqjOYdV7AwrvCu9a+JemGq5l1WnF44xV4aALy0YQkYP/Cjihv+5PnF66NYk/ifl52NQXIWxiEwVOT7ncdn6Q5hvx/8AA'
    'ol5kC2UeoXnLP7HSCEUghBO0iVmJn01gHF2bYkKPjUbvSFtJWafJj5YPAY8dPvEc8aL6j8x82qw+zA1M652xovprdo8eOHJNHzk5RdZf1CrsTm'
    'mNuWEGvAmn3gTqMdhlAqyP1Lsa6s4PnD5LNK5H9sEXZTDk9AtD/HVAsSi8+BbKJSr2GZfiPWZPbn5atXtz7foo+yI2k6KixbqV8tMh8sApFvI+'
    '4aoKWU5Nets5YE8FjhZU5c0WPmJxVhV5YE0tnCgFdpPedCpf8aGhoodP49yjrjBubRHeS/1xIFxK2iJoq/l+frq6lmwVXASo4Kru4VggJR6MoZ'
    'TCGDFTCFjNzAFPrxTCF7NzCFVlYAoeiK+LrFFMmDXu8FyqSOEa6UJRlfO8KfNpLysZoyrhQnider7TV4AZwbBEk5kJlkQEyUTsa8+OA43JH+bu'
    '2fpEvZAINa2sEMaj9RKP8azhAp8ahi8lIHX+6hoFu1hqU92Vdd2xC3H+qp5GtbBWcA2imJQhoIxuf6rWICWnmJmRpZgtU2ACh28Rq6nRqIKW/z'
    '9fhN5MCNVCDluAnDaQwcKB6HgjYXbv/rJyuQI1wFgxPN2gAnau8OTpR4FZyorzs4UTKSdW3DedcAkjPBqUB5xVnK1f9CjQ3aiYLljcoX95iFIL'
    'mGEzftG6J+zKfdv1FDn6OigaJyKYBJpLsAYu4vd4C5RvN8q1gYRykuMWCxPGyBxeISCxaLwE8Bft3AdKSWQS+Of3IoDAXlVADQuuUsNrkafkQV'
    'MnJOj/Y6KeQaZpUKUBDabrKhCQh9LDoVfEgA+Jp7FAxQRHsPcEQDcMSrlGd57vgXkFM51JNcZEekBhaOtIUWcNKI5Hj8BRQHFATiC2LKaCc2XB'
    'FL8o2UxOuEeBxB6HZyMJzEYDj1lXgo/rz8/PU9ANlMkLmpCcN5TBklwNrjCzBrn9rArBU+AVhLbW529ahSD1Jn8CpYnXnXDnVw5LviJ1OJMgBf'
    'PyqBtGkuHcuW73MJMntQys+8/YKQQiMEDZi9JLAoy2dxyoHEafxDGz/ivmAPJE6hb2BxKqPDRFt1VEh9o361z3ysevIGZLZK38Bmq34CmK3iZP'
    'kq4HugFz67AciEWKSgErCuKq7dpZrM7nwWfoMUpIJ2kN3jHunrrL1JBJBv9x9pKr4ACgvvBS5szzOU1eDCeh8+Q1kDhvLbIWT0trkn3a4FupVU'
    'qvjDoUD7syCBoGwsnfRgLgFuD7LaEAeQeBuDbNR94ByIN2J/WkIcIyTRREIAdK65j8z+Lb72ZWFrNeHFdopLMxDrztz7WABSxdex2GtCBLCDb8'
    'dgO2j0QpeyUQ7wuf6rErdnNwA1MTX81G7tTVKcMHlZzRuUm+eA9ogLJcCCsMEBqxCTGCJpGAiRTeN81dN3vXS5uVaF6BQAp31dfhkji3WkVD64'
    'f18wLf4wc2KpeSdl/gmR4rPZ1kMBWy9R/HkNHUii8hkU2nM3UjNqVCAEw8FBFv46bkKpV9VdVDLYck+eUZUCo7qAhSbjI6kHijzEofO8gDptbt'
    'x+rYsY3IhBkFMwasYFVw8K6TKQI5uWAjdlcfsXzmNwR0a6AQkwJqe8S4EpJ3ja/SsZoPH7SPJhFuoXrTZHl/+76EvXfAwf0UzDAFSvifpN7wt6'
    'MH+x4AJyBcGaUQTY9Dm7sPClQCUh4QlpFtlwDnacxq2UZdjvYg0zl8cpnfzHvWv28oeC2l6YeNWaM+DKWzQZD50k4H2GFukU2ho3UsLPif8LTj'
    'kz4/9KVfzOp/MaBAgr6rxA6BnCE0JTiIP0OTuEPSIIacMXTDo+cAif2otdTAseyGNfbCuFA/Umx8AAFb4MdHKl1JGjc0DqH5gqrCrLtSgEhcca'
    'WthW0S+UDjcyEikboBHlq57MQhlXNi5Eh6JuwnAWgxSoji+HIm9ijASkrU7BRquzwb6OChb4X+x5wb6x/IJOB1/l2R9LePNP3q18dwed3Mu80P'
    'nsq0489VgXXjEuVBZd4nv7MGoN3HoLJUP7A/TM3xoANm3xHrPC+r7AlgYkMNCMANTADQR+MgxVBgD+bRQFmw5oAf9v8/Pv4QD6wouIZ4E1UN5m'
    'z0dFXQMnf0FYwvzLPtuw28bN+8jqcHAJVoV0JUbJaJnLwVyIlANVwPm59/7bN8zgdqSNP6S1/GpZs0JMeb928vX0DdCjpkxWnPBjzmLQ5DJBNk'
    'oMaoJW6WCdP069+VuBXSKVx8JPFdNCvFJ1QpWvyy9ixl/8f7z8dVSVbfstDAsiSCONgCBISEuDCEgZNIKANJLSDVKChHS3sASUDgHpFES6JBaw'
    '6O500Qu+a4XPfbu/37P3N77x7vcfrpNrnTHPecxjHscaDkQEYZsunZE5Oj4WwNh/y+lpd08BoKYDXsi97wWtEujIUryLDSB4TY2nZsTBw9OCbD'
    'K85BEy+JP7COemQkaAGO7cXk9Q1R9+/6MoSTlE9h1GVQ3JnA+zATl2EwORfmNnT+boEQCOolqQFOxHXQNyX3l/+Yb9tr5383n5q+1ZruMezVk7'
    'oWbFqmuemKv77+nmzLdbPP1XWplK6XbBUYWgIx2iUrQaX2jUctub8lP+CV9tRbOoc+hl1K7Blt+4vIHXuys0IxONGI10o+ktzfqu3D5yLtjh0q'
    'ZjvUTGa8cKH11xHy3uXRaJ7aTz0bYNB7pIvF8SL3u2TaAnDlCHrNRpn4Pj5aO2pCsRy9yrfbrcJLKSBeiwxglVUKG7l5yMXXdWtelQEUfd/bAV'
    '06H6cosYsnSF6sjh4nVn0GDD2LIIa9hMomxF+VoOR2qS7G53luxLZ14s5n4/j9TrSSKncU89SfoLFt0kxKybHu2wbHZ0SbgNXP2wqInIrfAbls'
    'hTzrl4RsqGFydibmJHNREeM81TfvrYjBd8GvmdM7ImRwyq9zFsx5JLQewIrHl2TtH8S8RD9LNLINnJ6pvqyUsccaPTE4fy8yrY2yubpLI1IRb+'
    '3ApN8r7urLRyi8t7/p+u+8J+b8xmPTwo2ei4KvM6OWu+PLK7ghWfXrazXL1X9t2tZxTOHX2SsvLBjnghrsvN4WB6eInCxfM096OVl1SlNxrU7N'
    'SlEYvOSysJr22K1ueGHnTdkDyyw4RmeIF1s/wkjg7SQQcBnZbtVkhUrfpuSWg2c+02cx5v9jEevp/9bTrNHmZmOqSozb9LGLeY3LVNRfaw++ww'
    'DvdYqmMCWi279dunU2kX7eXH2Sv8TE/PjxNdbhIzpYn1oybHLlAj2HoUzWIa42vbkv8w83PATYxVaF7VvStcSHixL4XqKhm0HwTa933ko7t7BI'
    'Ge23nWaJytd4GUmjwbG4I9C0eXhl0PrwlF/9j2mrYVLz7+fj5j51p/kcXfmxVvyifn2ta5gjWRImtZI2vJRn4jcS6s2Qrc4bntVghd5VY+3j/n'
    '3iRsbpgJ8P3xxSpYNapIuSe4HiQ0p1vhNMXrpJvYRzmBz5hGZ3K5WC1ODvtd2uwr5MZttHEVT2i1f8IsNP3EiLqLfGeZQdpV9HBjqveq4fQt72'
    'FoiofGRZkd5YSOnOBrE6Fwa5/oQOV9ZiED1eT0rmyVJLvm2w0wO36+u6kp0eVbnIxpD8qp5QQlOls1fStc96vxrbF89W3oeKv2ubKc3EhUx7+0'
    'Qlg5JhaVDQS/3uD8eFLS4l13u+aWZa+DQAPZxSCstmvy12abgyzL/tuKG47j9Oa7AYRrRYuePdjmH/dWWPlr+2RkxKlOGtiFsVcwwli96s71lk'
    'RsF13E+hg+inpOTc/VyL6dWuedxywpCx/S+mnBIbQfbv8T2y6y9eIHXUwK7tuOIa4sHmlgv12c1uH1cM8WcN9wiVxtKx+oa5fwmNvNIInupa/3'
    'kcu5M/fJ1qhyIeFslX3YwWw5W7911oxjKxVLgwjOId+0A1/f9kYWz8Ph8L0SerF0y6k9gUVXLyyt0wyMBrqpC066w52Vr3o9j/bckch/Z2HKO2'
    'CYMSw9jHS5FWhje59yXu+xex1pDa2N0lH2dTpHMzCVbessN51v14DbQJ8Q40eHVmol4Sipj3u9+EJtXz+0VvXaUxOqLb/f6adxLqfn3DGEWHo8'
    'nuSDjHylT/uqCVX+DC7caqXROsBtgx8YRNKfHa1DGWl0K3Cq9cf7mkARp8H11rlHnhBSipW+xy+T1eSEFwOEPtrfCRRZbb1LoZrsxPURcRXe2B'
    'TLgZPTi7aSo96ZQ7uZduWqwtIeicTdXc24vsWlxQ0010ttG/Oj7HDrn522lBMNj3KynW1XIDLQzl6+1nr/PeeVB56jvNS9760/6oCqN2S2eVPK'
    '6Bx1QDd72D6Lqhbiitgxhle6Xn4axv6Bb9lj/ZSQN4U6o/rtlMwbWwZoTchIksI938F1mQX9coFwCP9HiEkAn5L78O2fYn1dRYQNzG11H1qLwC'
    'YBbjfm18Pnq0oqzRvMLqmO0F6OdFcXKhcWz+a/g+ARKu6Ce443z132Bb87hrXd/MNIo6IhJblq5wyzrv3gdMp7JU1CvhAbNzPowUAb4deFjUft'
    'YlfOnqf7mlc3vY5/43nV1xnstGUl7h6L2t6lmg8nmbFv9SAtx+3i4ciK1uvEJah7CLAqtcBc+aj6md4yxYGCPq8Y/VSbErQ92M4w0jCYsAdWzZ'
    'mcyc064ZXqhbPMWNj1ItLy8NIHJnLvqFy+Z9tSBLVpmu0bPvkeG1uIc1iq9iuzXS9NogwuJltHiNMzsPLpF7GKK+9unBkJ7ZUhtuaHJjdYony0'
    'K0QPcparfn6Eq1t4vqHRxKr3AcekfNXPJBpnt5VPw6EcU7fZzayKlByzA71Gl+rpyjcza2gfsADC8iAVfzSBn5+f44str9qp6GAdxvotxgbNOo'
    'wYYoNpj/sOQjzHdb3meosepn2dTM2zl73M2g5pJkqAYJzat9+LLEk5nM+9H/RlZoBKAEEomhPXehAy9r6IfRv9Elrj+bb1o8ZUWwmPwY3Om4ik'
    '7RU3iOycOjSNdL0VWLvag5XZ83Vm2TS3QpFNaJTKDuRbVzRCRdgqrvey9/KIE44vbTjsNkfAAikIYsfefr/JmJyB/aHezSlp9r6TTfmjwXbznt'
    'AJjOZluC7asFefswynY6pEGmU6825bXmtc4nczT1aiwDheKGig8PWOxgZxsts+GUAlhUbdlwEOvOpKzXXMRxU8FB9XdvCGgbxINJhYaG1QnRL/'
    'SNIvPI/P8rHQmU4pJxbiW+gMVsiJzmx8eFN71h9i7WKblu77rahfff/lo1cvl39BqlFZoEsrVF77pEc12fNb791dAinXBQedIhonbiez3R4J7Z'
    'e5aXXydB/YbAvzlapTk8SJInj6JkQBlWMsmKlDezH0Yx0enZtoQxeZYyEX+T5TMkfIJKBmrKEdWd6eo+7bXhOGS8UiB10I3Uk87rWejFG/ueM3'
    'ZBLsKIAKR/sktMe8im2buII8p8S6PF702RCi1FWrdBy5Xny94+vg+h3eRpcaOEMEonovpnQ2nETGLg5Xrm9dtR+aTTvidv0nUfSeBgHWsSWlb5'
    '9az4eVznXPVgdaa2N16VEhHtfXuHFo1rftiNjewiypcFjP1sy0drpEya0+JaFxDrm99oFttnhF+WnHwFkvucfvRfO+7QzECppSofrQJOsMkaPA'
    'JpNDry5LuKPVhdZ4jPWuaNNVe38xf6KsDDJYTXoP4XMCDPfjk7seZ0W/5bVCW4fNI21uBS6t833lfG5dnTI8iz5XhVHTc23nmn0S2keuGO+3p6'
    '05u/o/vrDblRpYySfZ2lN02TTCT+0XqK5ficZNn9UD9T/RPL0dvZM8sc6ltkV3yX/qpNpY+5sPmRiuj/VW3pyZq5z6mzmFrLA6+1mgyYShD23P'
    'fa6237KZH6//XuZmv6X3dmv9V2338YdvrxP79+XdKia2WC75MLkrCn+aJiKOcxF38NRitmUp1XsJJdxspYdXm5QOWK14Eof+ajaUZCv6pNM7qL'
    'VjcfEJQ6vO9U0YXRzM7ODyhHn99k6hG3tNRdDDrXOJDPOkwB4aBAmb/CIKiYGeXJ+G1bm0yTE9AIPwoUZzOzd7a6t9sOnYQgZuz3Vp9bZ3X3Pz'
    'SnOmu3xLJ/SY2rG08ry8oZmwcGVWApasx9L2yHcOyBrhqNYpUYdOWdKVsRDpGbKA3M0Arq6Pnj+/cnGOpAj5X9G+NHTR8h+YrerpgOFsLcPojN'
    'jPaiZ39IGmpMkWXAjD/Jk2ewFi7hkAVbOPD2C0QbzP90zLvc5UflZ3RH39VMh0sdzz5vQWBXTx7fG8TwV7MftxtD88saY+e/qWl0wdYsWJ+9Jv'
    'diNYcXnUoGYNWsTy+gVhdzq4abzX86uP59R0KmjqM/XB7zP7c2sCyCre6GY2hxM+sg152Fk3tapAOTVFcxxNNVef/bVHqVO1U2zrsBRy1m65mN'
    'RmK6gzvhdnJxKjg+ML+9Emvh02NVwYI8Gf83tydb8lVj4i6vKoZ3b9dTPFLKdb/eilctzuJdpVXyoY+9DwQXf5xGOzujar9EA3TjvKSI8lVliR'
    'kEEiZKCQIm53pvSOJmhs7+Hak3RH5ZGo+Ik3H1jFGuRevZXg16c4ZK68S3crdHfHbGuu97yOBZdijK3+6fLBBmASrtEpXE6WQnj2PtHLbMQzsr'
    '+m2EcBs/giiuMUSAAk8Wc6wQzF44blBsaKU36vPtfLrjMT3hTYpQu0Rmf7QpPbR+88KqTxqgokiQG5IP+VCLTmC/ttK0YCp1QvHQ8p6VqbDXbG'
    'aoOrKtoSKBcGYllYDhcf76zr4OK+vkJvKZrkiuxw3CWd+llhBqbnFtO73nuT2oza6mRjY0Hsai3XbbW5YFERtrgCOYfl2h3HRRUen19wuCb1Gg'
    'sltxOYPbgiPm39rD3dy+E6xbESmFvxYV2vbYsVHzTD2b8AgbLssbNfRZ/C3lxB3kCFPZonLtCHbwZ7a0l4V7F6CbAJ3zlb3bpXL888gc888f1e'
    'fSti7BD3kSJDidf2Af7hr+L5Fy3tzwiU37vF7TZlwASHtuxD+UjGCZm/BmNv4ZK4fz//Wr1fNIHdi6vcrBtczZaYj1Flzua3CumzxXouiOcSuD'
    'A34TdQszKxX3tPuDGJh+oUK+XwZktU57tVLxFuNPJbnxiuTa32yGLbe2KY5JYDPc5zPOWq+7Pc40Gg7q2IGbpaz6AXOcOemHBpHRzjwYNkukvF'
    'YLmTMU+/xZfAW30rOf24Yc955oGdVU9aDjhRuf/yyvFbcM8c7Mf+p/ega4MG5FWcrG/PiK02WBa0K1B3wyk2Zk5R/qjfNvTKpQuj4DsGW7KkRn'
    'IL7ox7Y4R5n5KhvruoX3LdNwXs0tHRSMGzD1Llhq5zYg5VVd7YcWqOVaIuVdeSk66F3aTvJ78WRjx3dLNT2RxYk75iCfoE4qvH0Onn6i8KiYt1'
    'cF7uG1qg3+TrPxxzhID8936b70NA1gVd4tO/jmsHLiYXsXRc1rFFf6w1CM6/DwT7djXP89HTYXzK5uFT5vOcOlx777HR3ML5+HLfn9PX2fKOBw'
    'HoPXqGh9/q9P641ztR4kemxo8zvxsshdhyVjez3VSmOLXmdYiOKe/oU7QN7KksRqVlBreQBqDwfrRZh9YbLA2VU/pF9DRe7+kTAwcgr5s0V8XL'
    'NGMJ1kSlwGXOHuvv+m+Jdvxa/nK9LmMQyqGnL3qy1UK6HukRJqb3WPST1U29NsSHiYOV8A8/vQhQQqxSIhHtg38gKr2GJ5+URLD2QYNyjA3nFx'
    'ptGU7bK1lgKeNLI61C1qdYzj/Y8KzIbqzPDRP/YIusX9Q98iPhwmn9nvLhO42b+SlfQmCYv709s7F8YuUXf2fJJ9Zd5VXq0cCGnNpjiYgNmXom'
    '1eAbVplo67DBN0zksJK/sf4ucjzW1Cafnnbwlk55ESfZ5/eE3kQ6G+M3X8BXf3e2DriPOF0UhSs0sjIUfkBR1uviLPiqwrU/AP9PUwwU776c/z'
    'OZBn6bd5FagX/m2BdpkH6+LmpM9md1a9lLVTgGDeE/lHQgKHlIrnBb7ZNjzsL8EolEB4eqWUWQ1Er2RDFj0JKWNHCz2aK7QSMVQfDbp+aeqi4v'
    'rHkIfxAZYCIfq05x6UwPrWzyd7Znc5nP1+rheIqV+4siI7RyEv7KCXgVxgW8Koe/OgJeFey0vijL+ERP+5FtFdsx1/i1+WNRYQ1fYJ6bSjRBkz'
    'd/45r6fM1C/vNf3/NTcZXbPcJigUU9DbLCkSKjN2akTgl/31Od578Z8PoXPc/c0FK50kyP6PS4Y6vsY2HhuLvmC0WN92gHtaU6tJ2fiX7avElr'
    'XsmE0FI/r/wvND3lNeFN9mdYoMpWw6LbY61wElS3gyqzAHrAxKJjasCLdAZn3S2OZwCjhre5xBMRBOKjqJX9I6Ghrygm+f9wjJgyV2H2g+3Vn6'
    'Al/gmaKSogFtqoUP23KXqux7mvxoxxgMtPnfLMmh2/vZ4hPiA9w6cSHKUp+GLH/yKXdOAWrXi1e9AHhXjjvvdxM3KWgtxUXy4ojj5Y3h/7Bt/1'
    'AWd76ks4ypwvWsMIXX4jtXoF4N/5uv6G9gUGr2ZoZR0QCmbiMFIrbfi9fjC0/4RT8MQ4xvi16mPRkzH6ENnUCFn4ZxyBZhHFcPTvh4q+I67Kky'
    'qQDJ+MJ1eBiZS0xZgh/OAQWWsymWdwer6/fByPYOWvF7nOn3GkyjSImOBU3tC5oRorPtQ47q1dfGSXdL5cuEv3EiiiQoXn59NL731pSfoPwi9c'
    'yvW8D5jWuClWJsKWdqsjfNYf3s6JFXlKrhxL4R6qOeur56MP866FNfhMKe5oguach1e/9kJYrqh/ehr85McXYtsV8tzr7/A9rZbW1Lni5ilQTu'
    'u7PImiUG6QKD6abVIShEA3HOjYLK/OtnxOTxyOjU5doNYHZJf1MEuYAfss+lt034bgmIFG71e7vjM0jC0jcd/vNc6UJDb/uO/3zEtL3EdnJlii'
    'WeRyf/R4t7pZYYzOD4tr1wi2tm+/tDtP+m4Pq9E9FcoiRXlVNXFJvHI1enXj7z9xwhV5rTx/+9o1947/+rfNAoi/bU7XcVoUjg28wungHqYdeh'
    '3mNqS6/OFAVs64wJx9UqCeuoyQ5JsMJDxRllNWs3IVzM26jy7ZyfiyQ1xBWZsO+w5zS9zT2Ghxr9KNWTdu2SF334YSofooc27FisaGmnFOg1Cw'
    'l5u+TVgEg7IGLFVoY+Ds1Li6OMyrcnbdxftWr1lXu5W+bX+J+JbEuZqBd95Mqkvt/aaRmZ1tqEDpbGmYCxS2mOI75runc3rx6xudrq73+MpAu/'
    'TQhVNhlS9bWukoBfRxB1eQoOayVdlEwujPwrDcKHOQf8/AY+IqyJbQ6UD5SdPw5fa2fsHusUvtWVFA3mFquodiJUxXTECo/W3xUVQ53+6sBvTs'
    'ay+4XWLy8AXorCLlaF0aMr56oZeuBFnqqFAYEjSO0oB6nmMXTwaNqoa5lFm/sqk9a7Zrnyf6pRk8DtvVtz3fnXee1IP6HtdRnLMWsoqt1C/kvL'
    'rSrH2jL57RN9CgsR/fXJy2X7E1pVxhkvHz+nnxGVcoV8G8x9QdG+1it/Ort7OEnu2rqjRnfpOWp1VWBeCSsiqd1OPKUI+PGR6ly2ZXQ1aXT8DY'
    'r3C7tsTwY4XRbDC0wXKDlbe0bE66PKJN0qM7jMEc3TAV4QnDcQHKSfzI78KjMiMCt2C+lqH1mIuLmMrtogf1grElEUtrDcxCMa6Kn11J1rvGwy'
    'N66+VWXjLOO9Nqg2XMBG71Vp5kWLeDoG12ZqCo25OqPGUVMCNSSNt41JWJ2zns01GUnIuz+HGcheD6r73zzC26iOW1J0pf6fovh9wzYHMe0MXx'
    'aizHnPQxwsrxqDezd8YmfveMKgfLtZ5e0nAT5FQd90AaukrFR0bdSm315Gg/wzpYRmW79xZlvPecoWBfdcWyFzO7ehLuqudXXQZXB/dP7Pedof'
    'Npb0pgs+UQp6HtiUhpl1ib59TJ18Kvxdm6ZqoT/mp7/HZc3q6aU8iG2NviTaC8S3/f6LzupImubUajjb6QPnRJgDtwlbNbsUk78XTS0+IgR6W2'
    'fMKuNndXVt+z3UyjqGFwVmCm1KPR67Qd1+wKNkvHdftLjo1PtJe3yq3ADnOntmydO9P7Ft+zPe9g37kV9ZmE6lFmSa43umJ/8HeRe6OZcVnSfA'
    '5bwmd+p0Yrwg1pVB1RhB2EDEdrYSf2v1kNf3Yqg/QLqxUXE6h3q6dPByIvv1DiabZczpQ5+/SK16c4OHYRfV8iCtmhmYxo1vuyUunuPc68P507'
    'oaTJ7Qbxyp+S6nviJgsrFq4/IxQYt7LTs8m4GiOFFlZzHXY46gl+qXtD41ez7lITxGfo9o6TgONl9vtK0PmIpcTxdIlTx9wt2h4zr4ol28Q6vf'
    'SkgDSq6USC6UTXXFpaIWdvw8c/w7uVC+26M3B280v06zP1Rh4+AXH86kf3trHuLZKEQnpp/Da0W3aVDX3XzeRkVqRlVugZnGhiYFrTHhI24MDU'
    'bc96mzIO0IweeNNY/O49J6LY04Dod7AvaVR3u0QXnSmTuiWXD443u/cG8TB2WvxFSGpKNbLLaWpG9O721slv2muIXxyCQeTry8aXFedSW1VKJE'
    '94zhNjM5li9HFymNA5nwnxtU4qLdrrNr/UeVSyTWBt+DBZ9OwE86tOy841HefeR6ANo4XnCxbKXZJ89q+eXrS5H6xibTb0gz3ZJzWPfWE9ESDh'
    '+p06iN0d3sU9eT1vdgg1cQma2/A2rbkCev1ZUVAJmECvY6YaNlP2emoKn8elvUGCS0jC3T1/5FuMyN4j0a+SWDnzLSX8bZIVPT+pGnyT+QdoSS'
    'LSIqHYrvM7jRCfil6Hu1P4e9GKgfURgS6sLhbVep9eY29quSkwjtitKgzj8S8KJd7yEcbzMItNrifuc2mmq4bwLB0nyO7X6WnuymZ2tyruqwvu'
    'bH7itqQpq9022kjen3LhcVKooMgb9RwpuFas5ntW0lWflkJLFEFLdJc6cq+3JfzAKV3IzvRwB8/W+a2ZPcRuSXS5PvMGj5CWgkjvI9HwZEfK24'
    'KOfY8pLVwlxVwlw0XpL2MIVA4r7ALdqrVX6pOqilxdZcS+MBqP3NqPj0y2T/Z0pnywzMNvvbR1U4j/oTEH9CJg90MaAe9KNL3T2rFzgmHehOdI'
    'kWSfGuF0HLEQfxtvoprP2+5MummCdONgcYWwavc3vJk/6raFHAnHsGXHjLuNdoaMfsS3RUeFimCmNvLu2tZ9vuCk87V1TjJlcfLG8epWsqhQry'
    'wFL/m6X1XcPxLaOygRtpV44XtZ9fAK3Hy5nP/rK1dTwihkx/5qZ6/MSn3qhITtB8SH0S3qDvjDK+U7QqVQeouXn8y6ngiwXO/L6GH+rRv0lqvt'
    'kVtN6s+QpuPhJOnKS/u8scZmj/bD9lmxiuDmVZd0uyOhdC6O39Glo7nNZH06jQ7HJoJfWPhG4ibirZxaUZAHv8ZUBE8Prs0bCjqb8FynperNcV'
    '5SnlYkt8vOUXeZ33pnKJh5/SziIy3Pt3eiht3/rCq8DtD97uq9kCs6nUKDaKf4rPDU5PdAl9kgV/YnZFRJBYtT1Ya29bT+LfOP3aStFrdpNNx1'
    'ZxyKOc9oyx2wNCJ0uWpod4JpaWQr7Gn0NViT/K0izmg/CsUDu1rsvXeL93/XvEOO5mU8JvHBSTFnMCPWbyUkfNnWPq8vVquemHfTVsk+6xvs1W'
    'phK2Rl93Rx0gN3/6f194+F6K5Y41mv2/rwdgikm/VWLGTwvtanfZ82Wqt2mjEy/ER1UNaCnyXhFnxXWPX8Ds2nt1augFFWKoto2rG9LtAesqot'
    'KjRomLZq0vcM9ShtL/DyhKrLvhyB1E3V2l1gemun3s1+ZB3fq+s2gHWzKDUogoaZkcrip2uR3vuTgVHM7yHliVHb5S/LrAtewcqU4/vkm06H0a'
    'JyMcTkUD/dpPnmuqLMqjAUJWNJjsqjYBhx66DDWoUgc8DNRBN7Wx+Y3oh5rv0gqfyMVveYD0t4xcAlJC++/ZtcG0F//HKQmfIXidRytZEX96nz'
    'qVts0eqvWw89WF2fZWTFXKubjjyKx+PPnkxoNLIXbypz1pW4kXewbTjyiEj4zlH1sm1tieub8u3RdlG7V8OWbHbHVdMlPUf75npiSQ+XWdq7PS'
    'FF8dCLs73N6eJjy4ktA39djwL7N7OG94WCNVWOd7V8enpcPG94zPasmEYlsCT01bu9aLQ97Dv/Mpy0kkd3jfS689H18Re8g1vB1uECBRoPKR3s'
    'ZHS9uzZzdJuKnVadoGm2vqtx6ToYu0S6zjwptBkl+VT4i/dhriUQ27ZbBBkMyXJ5s/2P3jtIHyoWlmXgqT6a+P6hWH3k989N/W/5YUfQVVeTZp'
    'sqj9o3WDW3A9rojw9yqLMLBcHkpwftPUk9rrOuuUczkU4trreJZ2MYdz3XbscZjw9DSya/5lq18A6Gz1sQZEYZr4E+zCfVTXH02DS5ZjT68ksL'
    'Z8jhUdd2R33lbmiRCQgi1x2+iZk6RAl6FfRJrW6Hng7/Ta5Gez/U3Who24uBEg1HjocJ+BlEnfp9cMYET5WnTmifeGfizKduKVzG3VlVmOFWVh'
    'ijWJ0wTczNIdmFILN7dULY0nSNzyjlWJ8O3Sd8ezFxXhDOJHESfZBYTi09MxN8Z/a46fDkqEQhb2oLdLqbe15vW+YP+l0aRaB9TMFtN5tPxbc5'
    '7n6elFpXFdXSAHa9U+hVArPeq+1YaFS7Uz1rVV/86gG7XUJzIW+2bXr/stdqv5I4VwdNupduomW6WOZGNtGoNR7/Q5GMka4HG0sn6izcE0ovRy'
    'FNXJsbIfM2szaqSaPi4KKRj5uN22fgi+M26rbgnfP1+lSBZnfu7fd9HVnjzovLxSITwTDID4ndatsnIQUsjV6VG/OfduxLK2mYXX/yOLmdO6iu'
    'rR0tLqhsHmFXsgTmOZp8mtheHO4jGg2gxfCuNz5/qccMTQvVgzQ/IQkfJsFx84q7v6+ogvo5PRhuB1SHPc4tIjIP2nDjI/LnRsGX68Uzs+eUdY'
    'Z49d6ZZLMjTC9sRY91uMKMR7F8jsPArm11sAtZPeEINjX90AgPyy27+qWohLozRw2q5Z4VToPS2Uafoxo7N1+IaQP4oMfdo3kU8kZzq3TXMbeq'
    'oGkXdKeKkHiUrPnti5UmzdOOlxHR5d6/hvT8G3ex5mN26zF7FSnaf7j9XuL0d7vJhUmZ5TBut1SH9aCFMqKNNEJaiL9j/iTD7kPB3GCRf58Ozs'
    '0ZBvfguazgEiGaayRtIcLMghiu8e9g0329WpEatuMa/tO4B0ebyX67PrR8Yvuv9uZvzR4Ul0Dwgg2wmh5QV4gGwtNfquKDRkJZPfEOYFU9dIZu'
    '3CDLACl1bL5B3XXel60xp/17S56n0z5bsJW0Em59SG5xsCxl8cAOBRvZzPzjt9AaLtBxtctHobjsS2zWuhQaqGzhptnBtSFn3/FOUzLAF/KLCQ'
    '6UZYe9j5sgURHMEy/eu6JX5RMMS5puRGkU/8gTWyJYCjA+ERctqa2UvAOejJTMckz1M6PvcBTFUbrhuE5gsvfez/rF+Td6Jdas3ezFV3q4Cw4R'
    'OzcZ2NqoLDAdONqy99SJNHfog3L9a3zD8rkSZU8V21X6guqqkz/64eZicMmgfjpJ89kvXu9nFSUTXj1nBA+FYH28msrTXsixMIe+IT9dIQDHmy'
    'feemtGpehhRpV5luRnVvPTPFHVi01Xecc+3d3Mw0CjcPoSx5t1w870OFZX6JbbT9vuxY6bj3zCc8R8wlVuAd2R6+tbVEy5xsdbkXr+r4+hR2hy'
    'b6QeuNHRgsNffY60kn3yWUWkU5JPbVGnQvUtmxr3ztN0rfTxRgHIo6T0g4xxhue5MsCXO/lcGUKyBwBzQlffO6ZUDe4K3xnRdeMJryUYpFhV/B'
    'imY5Ma54Cxi7n2iuHX49ddBvz16rQdYtAdN/umvNHvP8D6I2rF2CUCGzpOTXmBc6to/l9GhrqgiSuM+7IjSRglENGbxP5AXUs9ssV/7Qn5qDdi'
    'G09sJoKLbPbNusdGTiVpBzAMMZKd+V7o8RTgvhPNwG65ybNullNnr95Rml+HpXBN7h3QNI7KZtfdzFtMQS4sCHvi8kClgw+NEo15ulc9KXyD+F'
    'OkOToPukJdSj4X7eiXf3ad9lIXwtpwZ77G2PI5LWWjXFUPc2QftWnzQ5MavcqnkiXX/pwSUcuAVovOg9pXaCUUYwmn5c9OyezE0ezXSN7dMvzV'
    'p+DyuuT/+YUXrVkPND/Ta177A/enboy/LhqKrgJqJ1kcxxuGqHva9pLd7yR794ev/xsLfRIgyewrf336AOuva4r8tVHv439fzJjgrzOd/uIg+f'
    '2/4bXT/EXXfz3yIrLngabJ33D9/ron5l9nUv0F7//5hd4Ou8kcRxJsbevSKvRPbz7HfHXbW5Gxk+omDgb24y5J+deDzQL2Jy4f2wZkvKwNvu9M'
    'nn6bNXP7djHzhmWkn8xdzB/9sZQK7+AvSsvbfsOMrET3MJiuc0bAlElN1qyuk59vu8PoqZD7npEA+978z74FlhgeaI/96O+yUllYfrS6/dhV8g'
    '8APmDiLdTETc/uSrH5bDG0T5LRRPF43/jfgCujDjDe/TnW4vbjQL//fCZy0wv8+9EfTHnL9HTL9Ndu+Ad8Mvn05cEYf5bY9f9M9fj5xANTEnX+'
    'yEF41AHeu/+so6JbpvqzTrWHD3bcVycALEZMhtX4J5qjx5tfI0VYQ6Ic5wAG68C1P1d/lYGtkoH25yqVYiSf/n0os+S/D1V49+9DU679dShaN9'
    '81FFnZ//3AYrrMoQOFD3/tQ/TXPnf/2kfqr30C/gau+hfwv9hilvkL+N8HXlIrT90GFiMm+1jJ9/Dd+utQhr8O/T1rN3/ZKCeDrdalKh+aqHRm'
    'F274+drz6OeRr9S+FQ35Ul9nvKHir+44EpvFFHzZg095/x3x59jsRFJOrN+zd1qeosXTJ9BUfrZ4Ocvdbv5nIf+TXbAtn9o1pqdMTzjvpzq0kc'
    '1Gw1flxGsdrlJeEnBkYeQv5THJVszbWgqw/Nm/1gZvmlz1/9Y4Posz6ohkreoDEn6fzf9b4xxSG78ykFS1LIop27R/jcPGCP6Tp6n42WQ//qRk'
    '9srA/d/mqLD8/z9+EVqVBwZJ+8qhDrwUC74MZ33MJvLm2dCFB4F52x+4Qav2gn8+mHIl+IfAbZo6TlS4nCAizjp/jqhy+tddVwdtbqGCDenPhD'
    'DAZZCq9s20zAfzX6H4f2scTdxbZ/fiaPGQ35UjQuxMcK1qigb8HLPikkIjkszrzpyYLI5cHL5Zp8ldJGY/5hspHJ8Rd2TaaloWnaeQxeRbakJI'
    'NvFn5wNXXd4YPmmEtHkXQ3hjrFDjOGCcjRoPA2MIarxKYpqlcO0+nMyuXuZuGW10NYQC1+vLA6RzolY2kTsr+GYpJJsRITCkfJdJ4blxF7m+LY'
    'TXiFwKETETpV4p8V4pJNEK4K3uVIVTWBR+pivxdnxL2PC/DDzA4xqSCF7wZ8nSJ8h4m6SSrq3+USHUjEhy4I8QkiyueVOhmFO8ur7WiDwiXiUO'
    'HUaGfE9sqfYpmAGZ0caKOB+LGVHZTU0wF07zH9av/SsC/9M4PqvYCE/qX2KR/r85jg85fiC19gN5517XhOl8Bg7HmaGqyf3p7fAwevHt6gkX6P'
    '1ZokOXADnp7/FB/Ljvw6bpgRh89qXLg8rHeZ55fHLaexjvV6XC9Q53mR6latj3QMdo1GGXc1IiT5FZYOZrn0mDVM6X+nbq3oGY5RYBZ+TE5zZ3'
    'cMCDj1GpIOCMpiuNdR+ZYKI3SzLfowJxqFITRKCGJC1F+J854ZT/zJHDQ20EkM8YZLX2B9Wttj+Hkf5zGDCnOhA1R/H+5O26a/9sZIv7P0yCJ2'
    '0raiOs+xT1SVkWtofMzWd7r0YG2hXL9HcbTKFVliwPirEI6Txd9j93+60diIrWC59diP7m3pWafWzrJetFUUvwulJ5iz7sRK1GvJmAsTL4/IRP'
    '1oyL2CTJ7fHKFIv6eYBSLFusqE5a4dgKV9+G2A2njJA3nA6xkjGfmCheX5SKWx+uLoAbfLiEHtrpieU3JaezsxQRxvXAmtPe1F8lPaeO0sjOyY'
    'AZcMs2sW0ccY8eKmuM/vbVpZn0Zk2tLtYcNS2zPMgpEqQbGDs1q9RZgSz0QgquxgiXm8OizIu7OA5dyq70sHbzrZtewn670q2G7WrAzn2u6cH+'
    'l//yt9PxotlL/No1exH0//bPYoLwfxar9NbxpH6SuGQwv2GUe7xpiavhwVm6vVuhsOBz98tMiscX2c6FVAaReyO2x6WzMiEJLH5xNxk2DQ3qhn'
    'HMiDpDcT52kzy72OtoG94dAIE3+yYkmqemJa5OVg7NDk9gkOoBOonSZl0J3+O9mibCztzgXG5w2h5IubnR28frlcHst7imqcZirOvnRz3QbVga'
    'yMfiavtgPZfuTpPtju0uOEnZfMCg2avW5+xw+mxnPopuVt2uztfd9xyy2ndEN3P5u20RardJuNl35YEncbXuengc3LNHyD0O6fRwOjf1vvI6t/'
    'c9+nb5ezENtLkrof7e7JxvO+qiY/ssatXE6+jidD5qaHi7T6wheq8J065fkDDqEJrbx71ZX89jABEyv3rrfnIwvwjVO7Gxjb5YdTx33T263G9L'
    'fOsDM3d3ghjs4U+XzJYSEjbbXZk6VsAE5gWKdsfohCCab2kvd+k27ZrtTfTcj6+mm062hZtqt0ecpxrDjOpXjBR9Gn30rw7sj0HVQmkDEk37dv'
    '22Y6CS5hmbGYmLB/rNRdln/dZUEuJTj6qvPI86qkG2TYW6rxv57PrFfbxnxLw8jCb0Q/pAECF9DaOL5aMmWDU3+MpL+yQg+2j2tHvDrxitR7L5'
    '6wg3B/SO/Jdmvjqf5UoZcmhr1pF276Yda+waBXHjVVBBbJKxvlaveM+ngPamr+MwoRGv3IiCyFevjlvnj0QKdnVt+hzAHc3RJ7Dq11HJUw0Ktv'
    'dKP912lqK2j5BJNQAPpM3bbN56oiK3bWaiudctOqFxHpu/sfsG0qCbV540tp47SaHibulskODg+qbgaHkkvlFBpzaynEQzQVWzYbmb9WG+xvmr'
    'h60Ja42uqYX49ddd0JRtrO9NGghoOrKAf8oyVL0U175iTPYymTTImlvr2KwS/PZ0a4xflrvLVWjV9d7ezOTLGIur6186fayoJVQ56mvDyLsKnv'
    '4Qf/n8orBKlPgBiPUsHreZl/eBG49std7z24G2x4H6SY11rM49Afo5gXlO9dwDj7ta61mVOn5MQD5ZUSRsJKt56jhvZ1lPN1njKooyRRC7UmEf'
    'j4SFObqeO3I92Jhsf55vzGQS8iKtIFLmXF5zaYTZJ8PuCXGuYEKkwlYi94O7L4YYTHdOspJMGEnY2eR3lEgkzvCvtrh1bOlCZOjMmX1W7J6g5w'
    'q6mFNCYn7kK+rJMpsRe6dPjqiuQZsGwz7CB5VrIV0jqqvQJjF5+O8fBUjM7YAV6m/64ich+Yq0pjqHUpXH8hHEJXzEO/kUZMtFR8u6CyPz+C7K'
    'sVvvGzvz9S4MZyMxlLatSULGHclEKsME/BcFpEKwa7XIhfXJSYEXX969/iI5NL2+0NG8SHcl20MrcUB73smtew9Y0aEd8uKhOeMtvnCGXFcu2z'
    'hh9UryaY9+2cyHVQ5qRxtZg3orz4olccU3pnZ7Kn7kp0ct/Fb42Jg+eZqnPgAHmB5VDm1Q24apZQd4y7U+gi5kf3w0m3W/tttBx6xFfCKsSLQX'
    'LFPZ/FbWjHaFOsvY6qUJ2K+FmKL+UL6BtVeZnN1pM6mRQ1m3KJmzVrXtIihv/JFB1V5olZL2DZUarTJMi+CsbV0NkgRriAQR64LUF+sJn3XJmB'
    'MyKyzSJiniZqk0wQ6VmKPRJkN5BTEFllo2ZvClJ/i67KSGQj3suBQrNaDI4z7kfPkNcWX/h7rSt/zYuod9H2PZS7IbrI5ODVZWXTiuTWb+GLBS'
    '3iZ5qUB65kG7GeLKWpY3OWy8z5bVO7CpJfpNuktPp8M/k/b5RUOkqdTDeM5ERjbV9zy9xzLtvZ97B6xmiSjY3Ht2Ouvu7gudL3AfHsIHFlarlG'
    'y/fCq4xxkkSqljrZxa9U2mo13TSI4Y2xxJSr+y1ErLZ9kGeHfRviJ2Z9xQHFOMrzZql0wBUbNhVkmHgKiXPzwfy8LDyKiRqa8z8inXKhc0Nc17'
    'x1P0jrXeCp8MP4gC3xRXOdDfKFBq3lj1y1cA3ZSFonp5kCn9J+H34to9vPYxJ5V5llQrccDDBngcVX520KaSdhTItdLD5P1VIqJ3yBsdE93XNZ'
    'nkFyZjozTWgqd7z57R0ihoXXUmkuy6qc9OHuU4AZPPzm1Z9XI5M/rBH0yT5/iHce2xAnzVm891s1zNTp6F8u5nZdrPP1LtEr+g0cCBAFzC6FO7'
    'XFkPnCTyPmyaRPS1aJAU51VSrbBnEQsItXkpqscemSXbhqw74/dLrnw4dubsl5TTbvjelfrRr/DuZFylCLsytuoAb5asz85rnm93vhp/4hAX/t'
    'Au+ZD0xCN5liihaFqb0Nh0iOAGOdkKECXjLA454Q83ZB7GB3RglllYBKNLEB4KqIaIX7R6SatnjZkn24U8H7vAw4isURq7BK7oQ67BiUtGwFoo'
    '2hmoIR//2GgUDTeF/AYuFikv7V685ZXF/Dve3Ot3RLfpuGhUMFxaePNgi4HXu7MJ3Okr3VrsJUNG0MI+k8viYZE+0yiiZD10Igvzc2XddxLgkW'
    'HaDMZEl9fN4pznkdDm0JbgJ3JfIIZKw2UtAxt81S6VSRtKHsZ2o32h0NSnxNinkjb0Qrf9ptVDsQRQYeiPAfRi4DUbsS/Xr1dZ4aHfBrLyZIHf'
    'Y9kHso6OnWRzVUmjcoCBRly0tlplM6gwVabvdWEjTHf0nj25LueBE9n7wkpAQ+v7GTUBQbR698XmpM018SQa1Nx/BLPhMoo1G+cl8zQkA5Clbw'
    'TMB2uF7rySln0/Lys938pi/s2EzieI7UabcinpaW3mIntQuy4ubEpLNL89rqQRNjXYRdlmXGrqY7smHN51wwDgzdwQD7eIHJjLxxbE8vL8vNbh'
    's94dw+3d1Z8x0doZAD7qJJpHYgAJ9jEt2g2VnQOK4dVjGQhd5VPubb2TTwGdu7d+ASiYemE6b5qr23phUhbQIfiIjCiDzuV+ndUjMvwMlMrNkS'
    'qfO6VKYpA4foANIYCrg7SKNqN7wFtxwTx/nFfiWCBEIimUUw3TEsSkHXYxxR7LTlgO0FX6tF5sdHJ2oJHhbsUHK1+J41CZvmH4ldiJheXrgQtE'
    'GWkKGLZLxoCCTwHdnGUaNTGwwWNnsUBsgx182mXcdZYJWFZSHt3tlYdZ8Hh6KatnETbzNN9lU5VQxzcmrgKyT4xI/YdLuY/FHMN+hbo1fLN7l7'
    'psVTJUGd8GYouYfO7kxOl6RFdWg7B4f3EpVx4dHUrKSZndAs/43Kl5OiK2PQkeGP1016/im1UIKBjIwFA4UyXGDwaBDCxZwE6BZxQZexhgTqxf'
    'LMrcH6iurLKRE22rOIILtPi/AY5RqMX6TXrCmAqJUF4dwEJv/y9IKSB22YWBL8by8ZnPzjm6Xi2tPkcgagaxK04u549d+pTwY6fI6gKR/HXvTY'
    'br9jYwoUV7EoicBl49W1uoH6+EkDoepatUTu+AotjdYSAGtnnlPOWMvAh/Ao7b+8G0ERx0ig9nsVsl01ArE/Bw9fuUPhw5QPgVWqukY0BplIE2'
    'wbkHTsPRJ9psVcBO0khQQ9FH2rFwlUg7Lj8GwNjeRtB07ETNWLK9p+5j+3qyEh5uG4X6Kmk/EITSVeMfMQUowMUklfNHTE9MWr1ecegrxJ/W5q'
    'K3HvLxyroV52Z9P4RbFSfcqsQ0cDLowu4fONHFfd1WWVoVlzOCzOdfTFETS8i3J57WCqGCFwQPHqA1/K4ELG2AGaHPehlvAI3PREdr/wCo85TO'
    'WrEEYriDj/3xix6guo6vhXDL6hyAhyDLxyJ5F/BxQny4j+u0InnKKzFGA+zLzSbZ4FYCXFRgGaazPdxDMjhtZ5C9QMSCIMCuCPF1Ey1kYYM8s8'
    'iJnlmxv6VdNGKQQtosYNg+ULeykyA0uWdC7gDEC/BxQNreMDF4yk1W/hho+81q1w4PnGYZpUUwsYTmfoDCQyC/QxNkH8ZrxfP+z9ouJ5SQTfBf'
    '6DCGu9M9a8QC1XFXdzYJzcQfA2plgC45ELmmGsS0XXHPKgbELo8MWgmHZVLuK4CncgSi3dXu2DyPSQAr+xN0c0swg4Tmg60CTnbM7osptQeGE9'
    'gpvBLVKEhfulu7IzsDTr9pIRxK/kbAsrkJ4FDysu+XZaUnWl9kGpr6rj7qFZJBaCwxzwSmYoOyABtZpAVUkyFhySlOmj8bY5CoFkCFrfgZ0gNs'
    'FOEpB4jLilhAuf7oyEkHpXAbvPo3A3CijtXx3BEK90YqfCe/fO+/KHzyReacqS++eG/ph+cjhPiHVlmxUOnrfgwlccCDIgT0xbjnYuoh4OZkOl'
    'l4T5CIjiOXut8XwWBTD1Hq3n3WybEAdycW1cNvQCyPMzD6f5UA5z7yfk/Ijvm8WZ3Vx0OuXamT1KeYyJtKoV0ZGJUReWMpMD1kIAEK4HITZs6W'
    'qSW8ziiShQW5su4d8oCaDp8edSy0eZ2NMQK5tyYfxHaGnhJ6VXxSXkpVsOb5mu1O4DZMVprM20mhHYingYD6fRROWTjOrFLqAlIEdb7zKl8Q/n'
    'nFHswmiyDPQBSYDGfvcjLzOUJna2HBBZSuAv8bx1qObQe4iQiFl+mpSjZy/G2VBcC+cLZVvgH+wIrwBw2kPxSi/GH52QUHmc7KanfciVP+OIMp'
    'yh40UPZQ8sceRlGZWBgE1z6sWa4EYaITFF3tXwvLEAVavv2dKYsJoLmfJLzwZE9kw2WHk8cSxnRxoPy/KG2+Fcgy7xPtAlIOCfIXS6uCzEaQTE'
    'Ag4a1VbS9Oa0fv+SSGch46FT67qFW3DuHlR1WbN6hqU4hSWjEzstpUp6KqzW1UtYkw0lzUfqCyspoRijag1Ak4VBSLySRwwiMNcn1XGebe3PZu'
    'ICwTPQUh8nBVkSFLEjPbRDAo9/n3w9cP4KUPKDmA1XWwWsNbh/MgZFbuUCOC+CmcOci4TeUXIf6wlbGongR/9P2FR/CH5cIjeDmmykI8tLMSfk'
    'u3/VaaqTJGFr9UeJPCA++w6G7f5HAIqQpoAyqyCWxQcg4JhRpuEDZkuIGurK+KtO5/A2wYXjLhFiJ5Cwx/hMGByPrcWUEEjdiU8pe4fHki0Lcp'
    'waMGlLpOhJggAzamCN1DBoBESc3VOz/zmGP4X2vfa6SSFpFKokUqiTYsBPEb7gdX1lorF47b8O7dhYN0MtO6jAZJFQuievPDS1/eKBkyD3U1UY'
    'ZOhowX8LvmHRPAoOoQHuorASZD1b4SRDGGDLjIIh0L/GDrzf/esRAmOqaGZnRKlZJVP6Y2ZOgxpFK1p86qNUEXRvhPAOGoKBdEER0RsvYVM+2v'
    'Anx10yNdVOcJqvTRolzUBeWiYzFIF9VBuWg1gIn6JV78qYd0u2QbXEQeJMqd34DsEVLX5v+XXX1F2lUkMrIkCVttpZnPM+fhzt4Q8mwcYPKQGV'
    'n5GvJR+aaoiKzHqnHIhEtLRToWMAGp7LTUgF6GEsQLJFPUKKbsjMdH4R3xwSH8KHhFEYJ3xHVsL8m3VQxVjcQ5X+6kve7Wf6moCy+MKNf8p1UH'
    '3sFbdaD2RSJrHyLVgN1AP0BAUWZtQyACipozItfgDRS8b0Go6n8jptT/LiY9wAHgLbsyAhCg/Dy6DWe4lizK8tQGL7QUYkCbyQE2wXAV4EAIlJ'
    'dXX6EiV8kAjxxTt8pn70QToPUufloi1gmQU/lHTiiSdP8UmuJncxzbQM8lGqSXbgr/nqfDhsnx8O6LlVXBjGhL4IRqdW2tiVspPCBy9uO+B6bc'
    '8iSIokz9n3aOUEI+wX8ZHrqpn8iiHIEsytX4qFojiNI4PsqTBFEar7qLBFWNj9K4DUrjNtL/0dPG7f+znvKs8t5ZnMBFXpWZlTmPrMqDnZdaXv'
    '8EE9FPEP1jBqY+MxYIV/qMB/cC8lOP1yiqqKWRXecMJTFvWM3R8eHPaKTKhYKQJXDmx9fCUq0HgGEb+SiqoyQDl0fqP73U/7fE19q4e+3gaKAu'
    '8IISAsLyD0XKSWAoFNncq0rw9wI913pw0HpishKYEN8k0l0Z/shwV4ZPxB/KKKLb2AyFw4A37k88rODk1EYCX0LjT2ojkX7tUsQBeE/Wt8z/7t'
    'c5zx8j/LoE6de6KL+2kka2K+AglLBjkalWyVR7QA8XT+K3nhfFgHh0kMw42aAyrZIJLmtAlJSu0L++oaOq7ZOEwDjaGGz4V3R4J8LCBb8pkoxI'
    'nBss56/3jXxkEUwakCBcntQhHXjUPEWmfglK1HlPkd8PShiQeNzIUH5UiGpW9BRRXe8bVFELM9KcBbre3gFqNszbiPYpDdmNN2R2Z8XAIVmWOc'
    '7SvDgq53dA0HMXEYRqGabzPas8NYuTsmS4fyBYaghBytqOBinrBgeUrCORvfiMMLLUHv6McfUoACq/UCTKkBxQX1siGJE0CT3YmhxBGRJxArLF'
    'RREzlGifDOJILKKbHCl7ZxHsXy/4TxdH7H0SeBqK0BOKJrx/0QSoUfxfXzTlAeckg7dKnuce9Iz/v/TjffA2E4zsx8GoUhKJ7Mdd/2s/rpjgv4'
    'LoxzuQqR+J5AicgerHH6H6cRZkJbFSRnVJj1CRO0JVksk4ZI5tonKs5PW4gFgaqmyi1AKkwECKQ/HHrQ8KycphCecryeVJGkg3YkdCUoRDepLg'
    'v4hwI9RXhDAkJLdQVDNCioLEjIT0UBEJaYcfBWkYBUkJBemhItKM3ICo8cP7tsOgUL+g9Oj7h4fMSIu0yyu3MAG+2v0PXUlaEE6gHLzlvUAGrh'
    'lZbln/KrdpqHzLvouEJIT6VucxHA1XUjVI8/3j3hofalDnULWJhpRXecZaYpHSBya9oW0vsto3L0lJT9/SD36LF3jI/mJpS8ef7W4cVK4az6WV'
    'eZJ+hvheWOI5c0prUg6JoGqws7whMa9qFPAg4R16spDYwmSSJb6e2MJiUq60npj5bFxpjB3fhLn2rpZZVed2NUYXfox8H/n6j3vH13vqEoUvXX'
    '0YDO8AWj7VqZLpEztns4dN3vtlpqrltwlmjhEZaD9yA17EmneN84JL8bH1K35lDkJdXpPwql45y88R82pjufTMkQgOCR4k0uvxa1NU3k7+vMVz'
    'Ya04MW0dq9a2p5a9RZz8uYGnXIK/mUkFOyUvrY5pEDulCFRnyoMN6RIt0OFNIwp7W6CDnhQdUgc8QNHPzgqMfBJuJj8xvlFiVwCAustu7/2C6Z'
    'eZn7bfZhpbjIjywJEb8CLW/HSCFyxEhj1Thp41CNVTkxR23ckZhKarAvsP1JkOYqdZVHjIR3OlFoHrTL9ip+VB6pjsAQizdUx72Cl72b+YoIGL'
    'T+y6dWe1eW93XDF4Z24+1GGyZtmst+2KpfZftsPVm51YCupksg9zNo4791s269GdnZBpERMGAJmTCBzSFLdA0xU/9xlXooPdBAG2xgFgq8RdFf'
    'E2KZv1yeXFBWjs9N26EkQnAQojYdPE/AAwamrKvDuWHcTXcTG6spab6nP2vowC0FjqEeyw18PZ2crmJUoGlqRME48HKIylTfPWBGybTE9wajtK'
    'f423TdnE8gdgLTuHOauxHF+XB5PX+iSDbiZ3WJ3XX7oOixiJ64FcexKfpgXawV8c37srrl3qKp/4NMPUIUxXopflO7joHaszLBXngyuHI2wyFT'
    'ijYpp3PECxSpb25i/ZOKhNNZ64EYmLbTWGohTzxjQmOhv3ZJn1UOxZ1kqHe7dus6uLFPPmnC2Veqtr+Z2dRA5AXYnVg1CrpCmiWn67GCVdR4mv'
    'eABOMNctHsJ5HGBBSKoHs+bcWaXy5z6GOnRwqTeDUwZ4exd4cW+AuN60xMCTuMHohkzmZtrndzxbn5WBQd3zzoDpqRYVFutyzg3JaI5XO572OA'
    'apSuMm01OSgOi1hYSIAHpOVC1jz1r32sRNS+zegKKx62v94KoH9xWHP7e9mXjC6eydHUvNkHTK+Svk+Q5W4gink3c2MdphXkkLNOL5SG9cPTpY'
    'iC1GEPcAR3c2T2ZFbBQyC3xwb8CxEdiR9N/qupMHqMsJO+VrGjWlVyszJIsAYz0LODBBvpugQxkzYbqP674ADbcADvdjNX3hCVDXLHEewG0fPo'
    'boXRJXp+vvEbjwTbrwvzt+DyzZ9XKUXor9bir6DIC1CsAC30Nf8dP326xnVuUbOAbgCIR8054CaCt5ZtJf0QzTA14saZ9V90L1FK5eQt+REZmW'
    '0N3cQB7BhjwCoEdnxA/IRSMhIR4gpPCPuO7GuThd91PuNKFL8Pv0rBMg8K0k1Tw8+C0qTNa5myuY5UtBhh7zvGBCuEH04FKsy8CVdYJSFpbXeb'
    '2PofxI73ATTE/iK5CLQ7OXJXSdxCmHpPZ24FIs5hgxeTQKYLKyf6k2muramQAZ0bbW0lmlHTGvkVB1ST4geYbrhWkmQ46zDS9Ofm0ggbEhgSl1'
    'BtAluKgZjFy4qwKiib9l2wG4zf17U5HKK2cucVNEHNy6a4hBbYN9iBJpe2Cb1kgf/uFmwCZcITnEK/CrpyklK8PZZb4rrickFD0RgJjzbC+IjC'
    'iwxC4WvfXroRwwWGtQfZhY2/Rs4xajmD0pIHcEbcoIVQ3eMym3tbWJPWjtvOS5Svz0HE6VpAqLSautraEKNmS9rtYPLnb9mkFoxDPbD7r6NU9Z'
    'mGvptFqBmEQ8w+i93gSICYie8jkQvXGZSY4zwCpek8Bp8gULCcJZSqptyiSy39aCsyR+n17soZ362llGP3Xl65TN88939luvP/GTZEKcCDhYUR'
    'r1TQUg2VYw0dOisSXYvNUM3H0683qhj0wDIGXAIzAAst+lO6sJaOqgFdBUIdwZAgFnYILHD7hoKaD1d6UtUO+EvJRc7xvADBQsAybe1ftzl/AX'
    'Bxw3dFfOMqRa5j1k4HERRMZFHpGAgL1PkLvQP6VQHO/DV7a6brzIEhm6syKpwgQniz6PhHfiiSk94F5wrM5SzFsrmJhxX9NL0qg74S4a2AMY4D'
    '0hGS5u3Zy4JR9D7FkGsOb1pP+jqAhNAK3j1HRC27yIG4zh1sDORj9Z1gklSxd6A+hDUz3q2+sYv3y2/1nqgKLY8rlJJUzUV85CeVu3tYCHVOv2'
    'iUlJ6QZC61JgTRcg/w5aZUXzAXNn8urRNRgNeefRAuRbgRIcFTowg8GGHEZW01SACqEmGyqEWURfeeEm6h1HShSULsTm7C29GjEJBERRLYpy3i'
    '8b6VfvcQxepX/tAlQjiSRrEFF37kED54PDgbqjIldDC9QUlac1tCBAQPKAX1FwOXsvwv2KgutXiDJgDHuAMSySIGMYoYzEJSQeIxh2CUjsBPCr'
    'G1OAXwE2qtYC+BUrRpEYOz2O3izLjQDz1QhgMOyR7crh5A0aYdR3n2Ml+hyGCBAIgQrhBbrLcQetPU0vDeX/iSic0byAbWdA/Ymo9NNnQsTwM0'
    'nCFCHHvM4K8AJ9Bc3Ab9Pzj7D+kAUO6fXAqWne9Ex/mvHlHXC/Fze1CAG9r5y9lbwh8zCxxoc+jxhxxAh2mnWYKBG8oSHIQjQ0cFNPRhoaIEJv'
    'dUygL4AjbUHmoAVx1bCLE/TTMwRTTjDJaIQnxCilopRFeAinys4XTGgNlJzJ6uZNrCq43gFPv64N1Bz0ne0zP45/3EoTEURZABY5ENRDOYRONm'
    'JcOXh5viCsoTKrPJs2bMdM9oscYspBFm0POed/UZYzUJ8b7AGlpiNgpSjFooSVAnQNc0DOmRILHH4DApnw7HNfVjMgMKDHUkY7dgM+6KogtU/Z'
    'ZMdBs2rD+SAFFnqGZjTukQ0MnGfy4CK5B/1w644wDrLi+H1ntoaHyh6ZdV5SzBd5/M+8jU7uZvOCq5EGWk1KbNvB4uQt7wF3euTjVwjtGtBYAL'
    '5o0+oCJ9QJ+xC+Xd//h3e3gIqy7dqGKWlpRLpFGkG6JAQEAQEp6e7uLkmVUumQFkG6cxQlpEE6BqQbBIYYBr5rBu/7ucPn/d/vX//61zrVa67Z'
    '5z6Pfexj733iWrD0IaYAondqz/yh8gKCCgiCoGwSgiyEylWvVR6gHuf9h8r1Xv1e5SzH4WsIlWtcq1zjWuWtj36p3OkPlSv/UrnTL5W3Kl+r/E'
    'Tgl8pnfqm8Vfla5XusaPZsWg/eNLYVvw+27iICptad6+mn/Nfpd3rdEpTh7TMt5tsLTw69+x+Ai8yXY1SpTMRFQeq/DL98RQQkVxiPJHCBOQXu'
    'wKAkuMihzW3Fm/8v5WTx+mFvQInaotLov7u6prrRXURXJ73u6qTXXd2o8Y9OxdVI7+qzyJDZgJA50PzgF6tTbMACuB/vAMJaIbKpXocLS8l8QA'
    'MEMwC+uG7qMdKgzir4DcZB/YGO5zxwg+G87p/1j8RNwzFiUaSarAEhnH40v5mULcTWnO6gbqtjaEtiGJrfUvGZmxlTsghx1brIUIFPA6d2/qr/'
    'tHbggjyOoCx5g+nXFPyoeD0F69l+TcEPv8ZNCdF1C63/i7gO/gdxMS4ZIJAZV1zzpX/NV/b/NAWhv/g6kfjF1+kvvk4krvkCQ3/xtUd8zVer6j'
    'VfYEHEtIG7Cnb4ih0FF4MEYpZIvYZLpS7XN59aCZcD0au08j4na7EgCvA/Yw/6HhdQIWL6KF/PTUSvQtVF9IQ/7uzAZM5FTBv4RVwVThVi9tmu'
    '2sBn3yQ8i/DmZY5oofVbGFWINC6fm0hgGQaIMhwJxItfHXUcrh37ugW2Nl5uRBZFSg5khSqCMwLm27q7xQzBl+OXven72HWSB26nCWu0YHtqgY'
    'vDHdjcDuy8Y5UVVB/icjj687z3fHtxdGr18Hz7R6Bb89lhZH36PmX9+kwcN9Oep8IumGmIOzLn0OlJ8+vqOAMke8wKQlAnUjqSPXYFOWgVSQ/J'
    'PrVrPsKOgrvUF/b5gzbXdoclzB+yscjavVlf3bVVpOyVGll/MnFC61S+NyBhXya4xb0FVYaGcZ6unZ9v2AcEVbcJa4wdrtq7wI4ODtuzx8Kuzs'
    'szeL6bmFBFDJASoIMikCiR7XErsECFSOnI9ngVN0BJPvbyt889TNaTCmpJPNWOFl/kfnqIPElgzBj8ClkAeZLEuFqsrjrYMgg5cvFWo0pmllaN'
    'QZctgfZ4S2kp1tXPjaIgP68AMsf846nIj9xXM1enBY6B3tCNItpLwsAlyZH0/HRL/NkPyar4cVtF/dlXgZ7kmIJWEyeCVmRXsGOIi59d3RV/I1'
    'gffOUJ3Zo7315bW/NoMLr6ud8V0CBfPnN1bpSqd5i8W9/UV7tbMVuLPrlPWZgpsa9y+fMwObJ8kR88n90adMl1UiW3ukI0Rv4IyR6lghVkCeap'
    'nRM1PmEF3ULSQ7Efa02KMNPm1slshM176XjoNEHG/K4yA0yK8R9x+uPNBl74esGO/CGQ9Deu0xvW35HT2q9aqJTn+7kHAi/3F3/s0fKSrIHvTk'
    'vSDjKhV9CD5JAoUYFjbCItHF/r1uOSs2R6pfRYF3XwtjudhWqmgr0s8EVPoGJ1efhkFguGhg9Wky9GTC5BtdQSHyeyaXcdB0LJ5pbLtu3Q9trm'
    '5+ee5zIWlb6YuGNFxSPD5//K8nhj1MF5lX/hdmsTgVH2rpOgUfa41dXhee/SFZ7HqGT91Vs/vaWJhksz2BlkycBzd3nshGizyrn5cuXMBXYAGc'
    '22OpmYSU7gm9iwexoUNKkPtrgzQPWkSbR0FUg23t055IK1SuoC6ETmUHtL1SpI/WUWTVb24PycuP+F+FrwZYVFBuo2irFM8CskAfRJNGMN/NL+'
    'MJzdkFof50/iDQs0+vtidW6f0ie4vQ936mn96c593LQyYRen7n71AWnFrmSted3+Zdl/czGK1/td+gW6/jtgAZtD6liXJsqGIFb7zE2NjXOzEr'
    'NWdolCehZlKmh83FcoITJosQRCcgtoIRpoAyI8XnZcwF9YyZgtvsiHZKdIDX7hJYxlzsc/O/tC2P3b2s7OK1u/OAW1nbWHFMwFdBvubu5TZDLu'
    '/8XNKKblY7fxEF0WuYVc1MNnSAtjON4PcHyctXHKncTaSjYZZGjMHw65mM9uU4WQYVIxOD8H3UNhwcxgcB4P8SF05+NLdh0GHpD2N2+I0YWKNb'
    'CHTgiygjUVzc/mtktX2JeRkf6+56wXHNLoWop6mEwbrM29ENKbjeHFfbWll7DHFtA0iBrgjTxI6B0CokeRx6RidA4FsaJYUae0z1IYqFUcQC+B'
    'AB9OzVuvxrRtaxTLxKV8GtM8/uhQUXss4scpmth3Z0oYhZtASHYBM8QMTYVA6OECcBAtGH2uCanlA27TkI/ziTRt5WudVvunNvsHmYbr26ia8o'
    'ntQ0gtDxYIQhjRYgmFpBZIQqqxt0m42CpW6mUXNMMF0PCDm8nS6tBKHEtWhyK6z84PbAAl+W51lqdVos4wYv517/3QRoPEBuupLWyBhiTMlg9D'
    'kAlk55MmmkpkLZ+zCIXl7nHwv86yt+sXfbI2LUs6efSMYf+DtJ4pBsiAkKqSVau1iR19a8/Rs24VZeEGSiQmFb3zSxAWShFmhoex54tmlGZLJT'
    'RDTWvVHaQGt/AtRoGxTUfuR4am8h8ySv6S43w5UXvMjDHjSIf5kKnmVrkZJwDYMGQGGcixvH372JidF3RLjyuB0eoM8x/YKBw+jlnb3QzR5p9+'
    'Joq0a7jGWDe+qV0/Hl/SNSWsLf8PUGPGGg5qeQF8aIZj1uBtuBbjJgVLmndyiRt85d96eCAZ0jlHgQhRujAzvlsT3wTc73iOWddvAZbDsZM7H5'
    'oDqHvmFZh6xHn/plCE0IMah7TGASpdqSvfaqYTbzvLJm53MSP9I9lyzZrUKTPVQHiOY4DxM5pKPU0vSp5IT8Gkrf7FCvmbKKZr/8zXzkvHtz/J'
    'CJmmy2xriD2QZlujdqNerBueDYluRvjTDzdmEf5TUnKUj/mnjUUAPsoYBVI2HY1klSR2L0xGhf9FiDX7ezk9KQzQXK/HF60nsCrNHL6TE27CPh'
    'G6fyGH8vNPlwsj7WZNC5u2y90EWUQZ7/LS/YMHkmk2NeuSZYAw8thJNjXSJlxgUa/jTc5vRdJxicTORof/tXAwMxidQ265RoPYwyFqeMHNDEKm'
    'tA89RNE+LxFRx0kcLQjq0riY/ghnNrJm+CMxdM4xIHKUNcK+ldQf6pakqPCtFsDWGJ+p5OGwvXjLJiGVXfuvOO8v6KVe0dA4Xja09lrsD4paBq'
    'yTr86NHsP6D2f6R4/7z3uPR/emUG+VV1383F852LKEuUMWF0dXgTnnsev/sMsUT5yS23Gvfk0R7JTMciIiV86nL+kkUV7uNN1BE2cU1NoccNlS'
    'MDvruOtabnPBtsSNHxckUcu9vrN0vAoKnFzWTDvZitvqmjme2Zmact4qBwf6NOiCW1t1JcGXnkGQ06MKn8mLsxS/6FHtxrX6QdqJk8EtiHIQ9s'
    'Th0trMGtXYtuaHpbjwPqMVEXcuc8KxN63UyA3SC8wo5UCsJ5uEMy4flNSPxVB+8kq2sweDcNDwCIWkF26HEKOpEArJLIiF6laPK1Aj6dPvE4Vo'
    'A+XqQVUJLWpaSKKjGXZJmQ1JOMVxZZH7W4ZxQw4xV6c5qFO0MZG0MVtkFwCBatPLb7OyQdOknyQ7OEGyBLYX+Zv/VoB8aAOEDeugFgGkP8FNC5'
    'mWqLfWafr4BznG2arexcO6EfxXiRAIycMbuTTyAnYIMBYAlWKvRCmrayZ97pXjhQhBSELVvf/WxiNAwihk/4LVy6Ym6wTH9EQWP+Sf/qVDYACa'
    'P8xPuM+oKnVLVcl2XzydaoeFxQ7+U02Y+tYVZq2yf0W0Yz/3cI5p+LV4oni0uzGXbyjon8LNGQ4U+PMMbQZ5e88tx8OnRF5TjFOvFV4xofxmA/'
    'rfNuTjedTXB1h3ba9x46umzwTtZBN+Y1uh1A48wf3HJIsA+aC5NVtR7HxkcA4HAT2VGsnrreuX+Q+7uQGhc9WxjM1+t4KkdivRQ37DNLYUtOQv'
    'xJVvap9oD5v1z2+LOwRTd/1TOVQhOK88tQj/mk4rTa+ZUBbv0qmCaWLsactXxhAz9OB/SeDJkAA7CjehN9ChSL8RzpROt1oylO9l7bhss+ajVt'
    'PyIf0rpxQ75f8Jh9T1y+WHQI8g0sC+d5ljmJZzqP9SjXRepiZaGYF3NKgEdaFMIHZSd2yubgFLwnJIoAR9Jo6MsA/Y66D1N2BDZ5yDZDnwt4YM'
    '+5tIDdCTtrhJS/65unfmJ/Zx5toMhH0Or+j+JYfbNZ9iQKS/wnnbTUhZWjgT/no7aydh+1E+qlsB5t/aKL1zLChcirIU889yi6aq/GTbdN+lnM'
    '8aXdbyXxcGzAx5nnqj8Y9OhpTWVqS/RGe7FJWpeTjts5u3bZZsrsowN2C4a035m4P0PvztoALbpleCPS5N10qFEKP/iziGUN3od+KavyhgT2CE'
    'PFWuv0oSrTEHDcz980KCG+KGxkXQILvwVspqErhZaJ9EGagdOow+nglD398pCWqbB5dmD+yOTwxuVfd3TJVvVa8dLx2PHlsGnKxN1Y8i1W+lJ9'
    'PqGWHUn3p7wS5aYOflkK3Qtl7qU++zlXHzPWekP9NTJsLjF7h/Q8y58ufC7lffqdRZmgNh70pDPDVtDPw8fcl5x7K9gcvDxY2THTVQb1EkOGt8'
    'cGouXLyqVc/rRFTg1ElRksTVaMST3vL27r3tYtRgIIKmk4AKU5W2k00R0qv+c9qt5kgZ8Dbv3NIccZI7/6ppRG93fMI66bOqE8yLoRC/+q9lDX'
    'GTT/kvK2iCpBYakYMUDv4zz1qngUxFecaCejEty7lSzmhCaEUIDOcY6x727z6C9PVUdXn4NeytQHeqYsfoCPcli07jstGbjWK8XPrwb/JJvolC'
    'gQNSqUCpNjO8ukihbXop+eYtjjftHuFpDmqC/jZhep7n/jdTmL/bIUzXvjpjzj/ANs6lzT/VGrK1gv5A3NP5uW/sWY7JaqSCOFw5ruc3UqkPPV'
    'e7LoYsLnIyUoZmfONA+NSYX92/CHz4aKjb7HM3oU3SjzXL8Yp0c9Ls6Cm9uGbX+kYULYVl4N1hYiRA3xdBuq91T9hfSSeK/HAw6qT9pojdUo2g'
    '4on6XF3JgL/w1urhThcYLL69ubWScfXJCQRd2V0UdoFUt7f0BvrYdr3W/t5baOxdCg7Etz9tgdo5f2y/UWDRfnVsurfWIQ82CguB7fwADeI3Zw'
    '9u4SLirxEYFc+a+2Cz1xoR19OO7gWd2Qb5Ze7B/E+/XNjxNLX3419cWPhH6t4Lrb9CUByj1nqns11SbDdKjdrwvZEITzmPx2mt4b+LlM45GqSJ'
    'xsfQKMsH71QiQ04/Hn5fZ7B1J0T+raDZQqdeYFrCmw33j62Zj2vjVG1NZHWi0OwZbvnfmH9AtasYszQCk4nX3zJAr1D+rc8PqIsW3uIvfBw/3V'
    'n5iuO9wIv0jyaHqc/gbHGoF9icvHjc2uiGAynlMgShJiP/o4E+WCAKYU8Hp8+04pY75WbqVSB7HqDQNOAi/b34b6AkY+pPXWRN7E5MtbcJe+yC'
    'VEa+4qS042L+xq7xwnF418I7QG9tNuRmCo52Ti/Sbxh827tXsW0YMUFsvYa3/Uy/gcIAHenv7QMlRAmoVQLApsNwDU9s2kgonAsV6R+3OBAwb7'
    'mujtr8yA3xn2aK7jsHLt5v+i38xovDk10LoR+s0zlF1pFZuf8cP2hchA2u8mIPmxmzcql9YzzXWSlCfkOW1xeNGtH/L5zYWdcOd1TJ4Pf+lkNG'
    'miQYXVmd/OAXGnFixt8kdyXO+w5kmYlG/Nz3aP3F7wiW/DE8MVEzvY41kceij/Zbbsvqcsfk8KtoxLsZfn9E/HGaFqV4ue9RS8zvj/AZo3zmcK'
    'SzOWzGivKb1FxGdak72dQOjxbJq2b/LtAzxiyJ1jwARCqNuPl/AdF9lAWAUPI94oj+PQjdkdHqfPnBRBpxpf/iIsl+XbdKajDxpm/Sb8tJ+Idu'
    'VY5VD7q4ksC6LtFvUlayGmXVE5HFTHnEMfXO6tF/oVMAsR9+0O9i5ZcXUxJA7Icf9DukY1QHHFND1eZhiIN+F62m25dqcxlEIPZD1Uy/47yfEP'
    'j6/x8g/O8ie3ZO9329rAM/0YuErt/OJY5SoRcJW6fKxYniom+KuWt4zqbre2Q9lROZRCOuL+2OO4wlW0SQKeWON3xDNpnA4CEJd0Amh7jvwPaQ'
    'jFJc1n16kYh1tFyNqAE6kch1lFylqDKGmGRDZqU4GhHRo6GRvC6VqFh6kZB1kly+qAH6puB1otySqB8FEz0jeSxDeOI1R+vkJLlmUSp0IuHruL'
    'luUVx0Tc/X2XK9N5ZG1796ZqQPcXI9kCeglnFHGWaVtSLIlHFHHmaWLRe5f9X1Ay/HT4mWVrm8zkzW6wttdgk6V45bPFfc7vDZ8wGZJrEm+Qkm'
    '95v5vXng9XmJIMNywbWJ9K3swNOqwHMHWO/57u7Z9lLHBHS/emz885JktvhHyVojFQgMAq2Zd/0yucf9sp/+w+Vl5rfB4nbwZa1J7IVpe7Zl4y'
    'bSd2Fz67bstL727JJNaOMHV/1LaPEgzG+lLVuLC6rivjDSOEE5v6S/Mt8jCoU1J21xftxXlRQzvKoz1JeEefpd+XvWX5Jo+e1nUnrbsRsIa04Y'
    'OrSnLW3oGQtgONQFLTMgTeM/LaAUrfAY/Z5z9/zYpNrnNLEL/hPluKoeB+xk2p52UkJczB7P2Km9dR5/q3+iqzqyaOYYVgjbbaQFzxqAwWJBLY'
    'H67cJ+uFfQo0WI0da+PRnTycG5I8wMmmwmMed4eTlkEdTRNSQ5Dvw8gZQtOX95KhdO5NssECQmBpuPOSi6wvj7b6w/qjE64pNCQnpD+V9/Y10Q'
    '/hvr/QGw1zNyiSvtnzW+fPWVtnvxHgX7QeRHzBLKBfm+voFX4tV+Xi6VUsWs0Yu3iumnqlqDYMwPvmOAPkQyqDd7SfY1fI87w7TUQvFODf980k'
    '4T254h4Vi/NuWUnQUpojX0F8uWBLf6evieuEBt3M53932aWZZhi6c2boVBNJItIgESjoJxH4eLirRNJbTLJRw8oWTl7U5XkOSlrT38wbWiuUBo'
    '8tL20cXG6OopNH1ndHGC1pCJ+4j2sgm6fzB7sTi2tQf86G4fNJ11BUmVuAr0ujzbJzuXiWzlzYhrVp2B2XhNDsbOnEi2nKrNflwRc5IYDVzea9'
    '4pZ7ESEw0Qu2gS2qW5UsCQbre7NIWEX150vFidmR/iPl3h7nI4TCarPlw8pK3fGzyZKWL5ofz0zBRCG9lRlD3vkFUX5BgoBBNOHcxsv/zu30sr'
    '2D66d+GnNP35FTeYBq/9ftAzcQGjR13VAdNtooLyrTlX/lOGbcv0PXyuXyWnjUYuOy6+d05Sb4Gf1hPS4bfOZdSdRBYFzYlnSV7u53rf85ttA4'
    'tJZl75nno07rSwtduRg6mzVHauBgNb/UWgXP3mDOvNYPHsgUhV6kfESYd7qsuHbyKyPaEQ1WyBdg8p59tvKPIIfOTpRbDv5Z9y9ShpLhOSVOXF'
    'o8b8aOYgTaCy6UrAE/q555rDS3qoVBXLQPmEiS1LxoPKtjtBXvT+3t2fyF/F0nLWb8dshVXgBTSLZ24ZpGfkPbeQ18HD6vUeZHITn1hFTeINLG'
    'Ty/Rxjf3t9+JGTlX0SeZJJqVPqaSrv/Q5nMM/ZwyTKNJNup0dICaQRVrdPKRMfmBfkNGLXX5QpPBWJY1QXWei3TlG7B7kzbuvtmwjG0uyMeJTK'
    '94YiK4/IJczszX2xDuIxTh+6p7beEW6nEY/flY8WlZQ8j1EN72N6ypeWga3LgHtzSSSeeWTIueyGbiIFzcAxXSVXW9Od2URs3Vzc4bFwegbSKi'
    'ZBSIfGF87ieObwxcYmgdl4bF11wJSZnvicZPjlnSLpO0dMA2NDrQfF8exui5oyLOB47EY23P6hLsF86TJFGT73A2Dz2vTXfmtXtuVGFxcJMdXZ'
    'N9g+XMABU0IMpD/1KaCLrD+SnnYfft/HVSWsz5fOsopY26RykQHMecU6hP3hD1lfevRxYZTZOOYcnINDg4LmqLpFSdbr65Q/Q0r5lO4fHXGSS6'
    '1+470ZECCjEl+7tL3IulRYSgf9rG6Qmcb4M7RPsZdHzGw2kbxHf1rUw8djzVPGMd7HNLVMhVLQBoOVY9TZEJxLuzry2D4BnzpAJjSqpUZMxguc'
    'SJfLM+8YMUosSxLNTCECLUQjDK94LGMF/6JigKtsN9VJkUAtP2lz8zn1a7rcbo6OfTRXjdAoad3CEmijHpEsSaNFk0jYLGB+F3EG3CGx6OtRfg'
    'Fyq6TInKqeZ7oMEQN3tmaJXN4IpJIlRefU9ky7CCg5sOjaDjD2O0uHmtuYkgvFpPeFW/ywduRNTorOa+oRq32MO6c8bmm6tuK+otwZvWJi7VR1'
    'Kykqp20jbITI5UgwtQjwBEJ4ChN0rHiq8VQodSUpJK+jp6XiMRWzymqBhelbqxeNwiH3Ozaw1PuUFx2zVCaWzDP0aCIYWLY+E927L6ybnBSV9+'
    '2rGN/XYUuh1meig6XVfEm8LH4mxYXWbryvAW8DcCBUASqrqRY/7rrzagNnDvdMP7YXzuYa6dF5RhOhwLL1neierIiuVVIU40iPvu6dCAUy5cNJ'
    'gkpZkSmyJNsYBZbqEV5n2ab4wsxxPHIsBgdVZcNjJEdFApsmpB1n31CFUQyCKU3urUKJ7B0LA/5qx60jcicr7f7SdN+AuuK3Bh61jluQqTotz7'
    'GJpmKwFfTZlIfZViFaj70de/Omw0NmBcumZzvxCXSprk3VVAkqq3VSfmPkDaxSvBZ6Ndr9IXpETHxzyGr6Hg2OCvGf3RumF4/QWB9HllCrqMZ/'
    'rmmapmeUwh7dto0cJc5XoLI6fPYj3Ma7tgMLSz3FUFvUnEmB/rmFKX8nziiHdeRLYGP9O8RGd5z1XEmD/Ncupj63GTJLw5l/cLxNS0fXEc3Ioj'
    'PPegZwwGLXNcWRoAL5pq5MuGGepIceq8By+JnXRVYkFUgw48hGnZtjSlnTDUEmTN30aM7yNGNBpqj74hWeQuJS+RvBtUDOGJQZS6l5iWTT5BB+'
    '1Z9ZGZ18ghNHYbIDqEZhFNkOwJTACyQoAZGgKESC6EeABG1vf8DylAk1L8QYxytiUbAUMYZzbV5ICM9BYuq1R91FoXTmkZ42QDwArLdJIYwjFl'
    'ppxAqeY2xwAq9j7vkVc587jrnLGFozPcAXqh2cLx5qBFrsUUw7BDcAWsCOoXagbTds7g1duM3zayLxdOBEJrD1fgGYyNK7c80EXDNb0ZkDQOQH'
    'WNKdqSsmUe5VWklRAHyRell4ROEWpsArz4x+og0bUyDmfQgaffUXQEsiqTgIX1ycxPL5r31sU+E56P+SpK1cQQnQRYMIbsQdBM91wnXICC5VVA'
    'lShQcso92rtK+FOYtwRgbPR09LDUBjluIopzUQm2yao9SHMkROeK9z8uY6J7mPr3Pyi0G2yl/Bfrv/eXrxOZpaISr8tNy+ah64Jr/dx4EL7M3G'
    'rRrE3no6ToRTBRNfRD5I4OZAekyA6ABzBGNArd69lk54QRrDSE9pDS6A69YqVqpnN6Dga4/Y1zDzu3eIPYCo02mIa1T9DY5Bjn5PhsR+vtX3AD'
    'n6Ph2CYzpCo3dbW3wIF+TW9pbEpAM+LjYUbUmTkWM3QQquoFHi5307oy+0P4bO0FDe7w+FB9s9K9HjPcbZsDL86Ys7Dq8PIu35GyHXqsRAMGlz'
    'jXnk+pCExiX7JIXB/OucI2zgyl2zgKPNt7lVIyMHCPZPbgv/F9wqigysiruWIWSlQGABKBjOqBj3KJzgx9XvEKaOUnDTb+44VT8Qgif5JXgTkV'
    '8EI7KvnnLt8qFNZsAcRjPrtWaJiRAShrN67VU9xVIKLlWTphvXm/XeJZbc0fEPja+sEcNNUBkvZoYrcoCDEJBdY9Vj+KvYal2GzG0cJf6H+a91'
    'bciFGAyYV31SESSKVSIK81rq/6xx9WvumfhfIRB8v6bxkTJtKbUrEeKtEP210Uu0R/2HvPDgi695zC/UG4LHaNt0Q/EeJIBxqe8nD3ACu9IXgg'
    '3zTD2G/9SXKFzsBf9LBp/2TN6MfUnc2wF44eQglMl/XVuDqMPi/9SheTnHGEmCimWjxQLQbLg5EPVnkwpE/fYXKJv6KCUhvy/Mnq8bntcq6ZvW'
    'RyvpQIGPeQ3P6zWAjzFKOn5fmT2rG5436gEfXygV7pAlT95cIpqPdYme4+Va3CFPnlQGPpYBHwW4THYok1McpbJ4BWIZzWwQzVbjOk5deJxuFo'
    'jap7aq/vu08c36JT316yb2SPm6iX13x3H9OikU+3KnMyvj1ZKrxbVM7l63MDW4WopYothKq30ouxICbIsLgSh7OVCv0w3nohHRZb0gJRYAJQLE'
    'zeb2VPL/D73L51e/fnPdG9R/IVP8NVJ+IRtxx4l5XulCRc6SFAm4eabDAC9Zm2ghhsw+jV54xDuIZm2o+4EVeOXaCwIaoKEOopmOAGPFlx7Rp1'
    'UIAFSiFnBUjQhUXIhMesAdtSpcN8H4+9UDqw5U8pDPiNl0hxP1uovCj+JDNNYyDmJ4+lMnhc2WhHiTEIhEamXhek9l/suYAe4e+a8DTBA0scPd'
    'kDX6GBYCsmISBBoJIOtZdxy4rHuAIO+SA5S6wFPYeve6hcTDeweCCUzEPHk6PtXyaqlbohYxjizg4wh+n4BHOIsYnGTXp7Z8U+YB5PA/y/4IUf'
    'MtQBlyVOJelyHchdL1ELqe0HyVGp2dLuYZOvBrjJ1JNFxKBYj4VDkRBMB7GoufxbUMrmkyQdCEcGNhe90ngHp8svoSQC5Uj+gS4YguwcUJdInk'
    'xuuWnqi0ZT8PHMV9XT4jiLlThJg7YtUIYX371SUM/m+Vrvtf9NRmacl1W7SLf3xAdE/Ir4t/704NdytxxtwSxeGXHNPW6Ffb4R1ffcgoU0Ud13'
    'boJwgayj0yjiQEqnqp8MYpp7rnfYoY7VgaOyW8GnScLBj91lpjM+aWKdxEpzQ6A11feazyuMz3y61+y/nRkvmqzy0y5jhQoIqbimuAcrp71kN0'
    'j9rhsK/NrJha9VG6fZYQVelJTUKrM+DKltFvw7lyfkwOUgwcr0eZOtOTxeeZaldKHBl92CnAS4ZHupbpYM5FzTauN9Mt4dEgtOfA6Dax0yJYTx'
    'ji2n2ntfnVtmtk2DEEcdo4dKa7zR1w65y+9i3L0HVgwO1VY+p2T0blib5Zpuhj3AJwCuBRZktwtUDmqxrU3OmZbfLBUQ29W9dOi8E6BcpivPLw'
    'xatMdyGhD+2VqtRcsbtO23yRL/IuKP1WnO/VBJk5sjQbbytM6CgB8LA9eVWp2QaUJnvE3N7rlJuwADYuhl9UVstmfMpNWUI/06cf8XpWsVPjjW'
    '9NEifMjL4w3nkyMcmCR7b1dtscTo7SVM+sCuRlpaqBmYHI44zEB4lYWycvq7UNzLKEnpYmIk3hRL7QIKKDo6Peogj9Tp/+lIiuuW/R+C1at6Gw'
    'PtxiDY+shOkBBEgeK1Z8Y+a2sNlJU6eIW4oQMzKvNh5pEdOD1UaZr2xY8QGLzi6KKOa7TZnaRAo/P2dZ/HwkOsXvGd3xCfgSngtm5Krka2fF18'
    '5St00HJkfLKlWo7qg8Cu4Ll0G8dX8PtwS4gb8zqD9URJF9R1X1CHjXS42n9Sh4G8CsSUQHHVk0fYv2ZRbCP40gWHTqhllRc6eIFwIZNxUbfLtS'
    'ZIwmEUFujSNZBvUeBTxM8T1EEgBIQBJ+HQR3yodwCicYiMGRxa9z8qqsMgmPGB5fMQKYz+qTSuC7cqq/AHsiZP4aeKctQlWaGNzN6+fbowNd5I'
    'dEd3y9jhkOpf61uNV2zIROMtwZHfZMu13XyxpWe8pyareRwgqHFs8+hfTPngfT99gdsGc67bo0gLewZs++R+mmZVQIbG7XAX9e/PEGrXv2saew'
    '1fbbCR2ra3BARQBvxbwQrHH/BZyr44z3jrf0dLzBD+cKACT3tbMCBLaAzV+BNptvv5vQYbn29RnhS18EIY0iPDL4O0BrzMgMT/Cm8oF3K3gYv8'
    'QA9wEUliKK+nSbnKhl/quagJup9yBjdqVukdGApA6vfbUgspk6JWAI2CgnwWu/YoIAM9JeHYCSj5AGAAXOa/a13NivBSk6hdPp6Peq1h2RTaAK'
    '4GHxwbP5R44QOqOD1wBcsiNwyZrT72wUGO+0IUoAjvMPxiDuA5Nh5ZVc1IDO6DJnLg1Es7IEzP9VAnOn/7sSSKzkMzLLFAbqCSmVPTIGHu1sDi'
    'DG7rbrjHvNDbBj5Y/UHUwfvKlJqAuaiBW2Ydxxe7ST8lpgpI5/+h6LQ/6OXY2Z3LTCzIQCX2dgwCuPHzzwoLiuZVsg85ccXQeKsoIQrcEuIpdG'
    'QghgiHKKZ5uZsAYkpVZXnnDrpcEFxdasCYJ65/eISqBm03pExwnXG99IYTdV/SHk0A7zuYxAMdMDTwRt8K4HF8/gtUDe/lGcup8nZ8r/72rgQd'
    'LkWuL0PUaHbgkXhE+yaxF5Vil1xga98tiAR5laA5e3AqUNoE8EIwfwHfmuswMz0HJ6BerrWqfC+wUGzsQuQiJA1HDKZ3rKbkORBMZTO77Agboi'
    'whyEh4noDfBkAv07ESmgSLz3/SM/FIG/9aDzFHfEPzoIdpOdtt9jd+4G/w8J0E1odlx7ixb1QBgRZ7IoFZx6smtNIKrJPPw6myR15TlEnVkhrz'
    'x2Ec4MhZ7C8SbjkZYwvSOC1/boaEQfdf2hJ779/yIDmds/R9j8HuoXTYCz4f99G9nvc3gOXVqcmEroMxw6uR9Gy/qYxfVOf+4hPrcnFP6/sqNn'
    'CvuxuIPlVy1nNZnU84MDtPXVtkHzmUFXl2OpUZRHY6LntIQUWjY6K5hbiy3i/fO0se7rtJbZgl3Vl7G+9eBt8I6AanX2QPohZNQzyFFyMrTdSb'
    'BryvOqISCjZ9k9C2bj5n9ykG1leul0hR4bg3KVEJub+piMhau+Gb/fiCigQXOaxnGEeu/ya3jB11tkHA5p9PPgn/1x2XiD0EP7+mzY8dEcLSjE'
    'PBn1UdWe/YPy2JWuUpiEVFHKBLg9CKbqJKC6HL+zXXQn4uoIvFtwcTkGnQAH0e9yD5i0DVtaLPBoQ7lnRs9+DDpZBUlsW50MdjHC3OqmJDddrh'
    'b0fkAlXAYF8ZFKuHSg2A57yDDvNIcBki4lEnEpe5tNHOXxpwNl0nmVFxR6npGrOBuKtGmm1NPPRo/a28hcPbB8XhfkeJf0ztpxbXWgBrh9mh5I'
    'DNoNmBIT1xAYGg6cJYS5nMTyrs2FuC75XNWIZ67fl9I9EhJ9ck4VNJdZF7Qf3gBN6yNe5HlaPNCR8+W94H2Hq3mqd9xlZuNBgZdHnn5irWkwh3'
    'bR0aDA8wZhR1WawvDNz0/QUuap8NrR4syKP4preB+PxbqIH9/2e80q6HYHw62wI82DeL78/KzBZ3bAtyjs6uDx2pI8uK+7g48RV/N8X8xHdy1T'
    'VUNVwqgCwrmvfZYRJmTTvEyhZ/f4+euaoR7d0Rs2bm36hjM4ERCv4cN6FnzBthZfDeusAw1eA/HLgp7h3oeea5kPNYfPBoghz8xorjhiBjBGlr'
    'Rf+fyoHElh6bSTtBosX3lvpMQTp7TdIjkyteMISV5a7N2tySvRdYvbb8iDRq+5Har+tPJztN9l9xwflChPApUw79v6rIRwl6/BSn5Woc1zhnjd'
    '8xrs7ZltqC4GL/mcj4uqijZPRk/Plu9stJy4nPhAAr0u7kNXy2dO7nuAafHWxDMfWUafsI1eJV32oBlrRp6hmj8wei5CENnt303GiHoeel8aHJ'
    'fYusCClXL8iMj9iziIBknLQwcUguVqjDJAhX4kwiUVezgKobZkVmSI7/jSfbzr+szgkxsooOuHl8PtEhGOhWch+uzxdjdcPz4oOx6FGNipgqKp'
    'RM1aDrPvMYmZ9QVCj9y9zh8LBku2nD6ul51ZSt55UTLaXSlsZ0/p4mbrlGE5361AkMoDHErHS/RQrjODnykmXpbw8xFMoUBAfUMnnwaWoOgkUu'
    '8EZIwiW67o8EA4g4sVUxF+NsEbkhvMr7AUY0ITc98Znwc+4aV8Y89x1/DTcWG1WcFgZEfyjgv4wm38jXysexG/qANYnHZmRj6Iy4LO3qRUkZek'
    'Djec8wWWXsTnpJwKk/PAyTc30ylwZvyCJkkk7eNm6u/7O6p4kdTVR8LM6LSwv7C91IyWrlS/q8V2Rwv7q2KODrCltPS78s9KnYD9Lra1rs3Rwz'
    'Ofw/t+V1S46nihJJ0fmOSlvqnF/0yhW7mrIIxNVLiHUVwhRUHaTQuTapKiD5KgkXCK6zh3I4tE+UL/UhNL/TtW4vee2svjL8jRW2jFW4TngVSK'
    'lJGuHHiiQVRyXyArNL5Bk0HQMnYK0TRfSP/GIWRuF7ZXDSsUrjz7aoTFAJyIVnyI1nPIJJfNovCORSEnbuiEgalUliwgen6Cl/q2ffqFv9Dohr'
    'XsN0y6atHSAKW+tyU31ytLb66XzGBxPk9X2oZOSMJ2VMEcMaIxINqW1piCB4l6dD07Z4UeLvUQfw1JJK0AnPw2/hRvtvgTlO49PBwhAalY5Xiz'
    'hMtbCkE4+e2oNQHJwpzS+e1fUy4h39OtgmauGHVcbz2I8dIB9aM06tIJMnJyxd8iU3iBYQ11TMp7qH7vwzBszCqE/3xnxSqEqRY5YM2UkLG4P7'
    'IlVi7R93nb3r777CJr2h6j7/nWWMENol6UaAtCxiTEwwrheVtztYuXlYmXNsoj1ZD8oobxiIE4+UQNuh7ydztX1uz8X99/P0pevpGUZlTMxB3c'
    'jabDHN9NomAeczuBFfEQO3SSZ/6w8MFNTcJbridIfkiAARKJAlKMXfiqEB6WZMhzo+C6PR72U9kQKq2Xs0Syb5dvDLkjlaCNuKPYiISc56PYCI'
    'fU6AM2z0oWv7yPOAQOG3c2qgQOS0IFfCURK/RG3+ZkQTy8GjqZaNDlZJGf+XiZ2NLycY5COzH5AQS5NPF9M5ual2anuzZzoi/Ro1Yg8U9K2173'
    '6Dy5YPZJ3R+1kn5kiKKGVaGYm1UmK27gw3kpZiIzrc7gICwNxk8fS1F/Gd5vlJgcSls3mdiC9o3E+K2ssml02pefz6R8TcPRPsiieDxvo2W3ct'
    'l7T3ecvLyibU0Rl7QMNeLFJFonU2JyvLl+U/1lAz/tT3Ss6Bng8Hj7dp1YyAsYs49wrtNZwcKlIC4DWloX0YZJ9FHFy+EOxMM+ZoCkdJ0Ph3x6'
    '16Vp65f+pfXCR9lWBBhDN5MUEpWYegrGB4RjUBNXiR65+XD2d7hUEBnkkk5Sd7P3KAHi6zMauf+uPN/mgdEjDVv67TfL4S15BGi2P4lsHKPv16'
    '+VjB9p2g1qH8sYH9fLnjejFljxH7SinVMCkZ3rMcA4Ey6TFIKUEHqL1IVx1l5CqH6k4735xMIt4S/kKGk/MDNV1H+QvNNYouA4XUSTtmZfB5WH'
    'iakcdvdneqmctJkvnPFopTKecOIlP8vyK7qfuEbU4xa97AMk0od90CJaTHJEvjYLrE9DwcBtJELfWmJ9KKvCfb+f38vP+ypTkIAZU/Z2SR/+AX'
    'qubEiU2hJRsUv091PMgKsprpLOUWHMxyIMjQEhZzOXM1uT3jLvpgLokXQs8KbIQt3xpOM7rfdIbOALYBqzFKJCTILCUcFNP+n/jmB2Wuygiwn5'
    'HpbZ27Ob8ylMd++8101nkMpkkKJ+t9MFwt54+u72c83N1s4WPBzARLq8A831tm1zocIYsNCtoXjVtgJvu02IjBTtRo0a08XtB9PnRoslhQP6yf'
    'fc34KgJqW88nvHbbLze+4W+6k1lWu0yRGfTh4nobfiW7i0NdPKs3uPkny999Xle5ywV04arEk0KAN2okR4oX5bsgWcOTOZlbVREWryWOp2BxDP'
    'PGUnSfjBM38RQuk0gYdpAg9mvNrGqmwiMrKl1qBbEpJtjSfjXufmqPiRld+ociY6yH8691FYHtKXFyXYUufs+c1+GH9KH8cuNne1E3TJXe70KQ'
    'yEVNJX6R1QEu9kNv2JNbEQWIxHAeBnwmmr3fXCkJ3sWHB/4JEvmdhjnIpvVK8mmtd9pu9bVjrH3LeLub+FGQBu1gLIaC402fDGr8AI1mRNzPjr'
    'Qp5u6yhdfpyw/FhJjJr7xgev9MHm1fbMD+0chJWU2t6eZev6eF+YQR/wiIsnViiOSIxuFWsF5eiFObXWM0x/82MfCWm00lw7H9/b2lu/1769Fx'
    '8YKXD04PN9nN4Ov2BxpFIUnZsVDwXwRV2iQaQoExR9r/ftB6m86AmnQhYdVI4K7zCSTiEPguqpU87YIs/31eMs5kJmMx/eiuh6LVFSfsS8BUo+'
    'WmLoFOTpGfppfPMWDbmz0wNVUwn3d91iRRPfgqVM0AVph1eNTE4SYm03IYyds+la59oRDNTtyD3LHduqGOzpfNG586zjxhP5BsQSbnXlPiIXil'
    'UvuFR3VvkjzcovzyKn6qv3aZjPe/3FkYI1yTdPKYYmULvL9KpUZNWKJoLbZkKRHCRRtPYtAz5RtnK1VL/OGfM5Jzkvtlk01Cp7op+FB8UHZ9W7'
    'g4OTOcF2vk5CD/wEZXYMUH07CEfn++NJBuJJaHL2IrsUf3BQ4sQFrThBSLNuthnyro6NwMopnmO7B/N9RxZ4J/j03rNp/25KtvwC+XVoTtUzEQ'
    '2znJ/cjX1tnw9BLkpcfENS6Dpvc8Kn0Y/k2ORSrRTgC5hkjBZvfZLiHn5rX+aFYquiqurMTVxNS00+8BOR2bEBQNxiPONjgi/Aq0l1oiR75+dV'
    'ozepi2th7ZubbZdeN01vjKdbWbc2IrdWxvhECMloRuBqksutQyurxiJKqV68DWK2hJCOZ8eV7W4F9dApGG/4RCRlUQ5R5qdY1p/FCyq8nxKXBo'
    'Mfjwg0j/lzKFwyp9jm4wfqzp2MdnUc+HtUk9U2lF/dgCEhl6pbkzchByCr3/voHP5sEbv2M4AI2dXzWDaO3MvY20+fSCJr7K1hUNjxErb4G/sH'
    '4BFe1POYXOr3Pws3Zjk5e0dEsWWNbVLv7fuPfQvOKn/m1xbj2LU3nlW+ifEZ0kH6QeX9/G4X7Mdz7JNvtCS+eFPBhoO5a/GktlHs3wm039PTvN'
    'vx62PzC3/TGqMOqcf0O+JouBRwwg2u0VaYphzyE5AamQ+eJ6CzoX23EwlS9ONXm2bn2IFNLFAetZ2klQYvYOgUxC9oK+yzfz/UUlhnZzpCrYHR'
    '6YaU38H2PzZi2SclOEUqISE6xcbyJ2XcJ4U/XACd7H0pSJv4Rts5N/EpNqZ/sCbwdThaWwzhKeLhEhgW6loLJdEoRrB2wv9mYf/Lggzb/waaBI'
    'gN+Foaxegrpj/iIQg+w9j3x2RDyi/Z0dpQUGiN3wJf04eUmyLs6EMkgfQsgLEv/HNBg1fVNwLxACcfqLAugCUmt7CmAF+AkFDNbwTGogVeHqMB'
    'FvCn67VLeBqDFkhDdCqMWFnluTP7zbVrJechBIQ4Tq5MMP71uU1OjGlJ+V+rHVVzNzVPCdWXmiM+DFYTYPVt96vsRi231Vpcs1d7i/AR9Qs2tD'
    'OFcGMXexon2+QCnzXR+AvqW86tsmXJ3ceZQoPc+DxcT38mutLxjKlhgYLnDx9f6Y0fcW5tOW1g3KHG6RuMHGwFvcvsFRnS2/4WErFXETyhsXxM'
    '4kMdfUqFWEgO4HKtL2vWi74Y6NqKk0WdfWaPZovOjrTPxy+QS3nbO6AD1DUt4nFq28Lq8MV4BGvQ+ZqVt7LTeI7tctBMWxqMATTyia3AGhSJuI'
    'RF4UT4AlruiSh3yibT+72NTEF0krzLK7a4n6l7h1mZSDo2Q824U8FtFt2N45+sS1Bg9EbftdGPhsrhRVfJK7r3vdCJf4US1Xdg9ITiiMv7oXE4'
    'iCLkBd7TNipDBucCKfDnoVrkT74/Zr/NUX3MGuywm9xDhiBVYBt7RFo8UsiGHVRc8UB9tgKa7HM+tvaGyhfrDZP9MMRogHIrpsu3fqqqgOaeGZ'
    'mkAn90j8YLof7VU0ZcReld3DfztHmOdc9NUHVuVDR1FEqyNxrzlU7i2uHJBNEwuRwa27MLgM3UnWLQBkOdAm0Vq/ScyE/bnMQwJbw3KY09cmhB'
    'kFZqrbC217vYumWoSQHyL4TkGXP0nmfPtWFMooLYgsfCH+wSdRuAXKkrtpt7fczykt4Lej4RbV7Ybt6jyQ+1osNqoegEzKgLsQcdBj4DvVTGvB'
    'FPB9JqCx25MZL8tXvA5CQSZnOiMLLmAll03odAcehkkLWQS3d5NHXqDed6OPsin57KlNwuPMbUAFdrRd4i/8mxe7s9UEisXbw9CDKucV6Hmhx6'
    'iwe0iUfpYnNraQQTYVmgJX3L2qjc1DzIYU9gNzPd5WeYHBfoGgid3K1VmRs/vdBGfZ8X7zmVkOPURGvnfE1SzaDbN0HqzOphl33m9c62/HZyE1'
    '/m3d3u0Uuik8+387m32VVGmh92G6+coYuEzH6URrcbFBzqWXbcubcuD/rWYVqDs2WUoL7AVdp2sGsJ2/bn0Uu7Tz2xBLFxmw9wORnct0L39qc0'
    'JgVt5kYJE5Pes8pFQJXk0gq99SzUN0gaw3IeWoB35NGv1Q2ns/3dFISydzgwLyj8MfmYk3+TuqNaayeRgnCwJlKJKO7g7UP6+2amKeOMj2HOk6'
    'LnROJoBrHb+cfJS5BDyxOhmUuIT7PkGbcGM4EiUgmSVvKjl3avb0/I8XyUTzkv23n+5vGTjgpZkQ+oFnelAlv6tqd8DvVER9OvJBxps8GZ3Dgm'
    'qpFrjJ+umjdgAlbf5j9+dbza3d8wVZo0UgX3X8LAVwEC0NVDF6iFl7dELZRns/1q8cqbEds3CXEWw51cYBE+3iIsDJTNrO/O8zRndama1Q66hM'
    'ZJDs4ncExlbjyDODZDq3ygy3460LZBfud7OrG4FU1vtGNd9NnLqX40kOjABUf2zESbwUQ7FrPZ+wrZBwNeED6c36iuDF7c6wpCqA46+K2eqKfe'
    'VbYNViMeOOVhFSskiaJ8bfnxC5WkITtPV9y15bBtHZFNnatsNWfgeapKfnb2YIIhmuJNeErU6bnZlh8aI6Rp/VYn+o1OtPa3tsuNqh/HJ1MdkM'
    'PFmsNyxc3XuP4Y460opVxuy81UZ3gIhGDdm5q3ur1utGEMZcZ6Qh9YCR+snl0cOOO26uy1cQQLfvr2NHhspTbLpcXnoxmVE0qvB6hqT7nE/xuR'
    'j8Ye6koJFkJ02HPYCeMFDu9S0x4ItzOqotuidNJV8yPz6jzH1cpyoiN1qccmLxUHP4j5AZdbO5G3RLvLI207wpdv5OQ9yaGWh5HJy2dTgpLnYG'
    'QxDF+VsEsLOYKP/B+e9cMuPQyWuVkzuLdy9+UHbtdgn8K2bpA/ETLiQkEvWRQs7Q7+fOZKyqOD326ijE4ykLxlFya1nEg54V97S+rjezUnKEYI'
    'PmYpgY6ds2nyTIrfzOzScsMgtSmtrJTQJbUf/zDlHnvtGkrRY31Bvwd8uITrw/QV43R5ef1FOges4xwxUn0FxG5MrPwUjmpXDkEoypshMJ7Cdz'
    'JRoGdhlwMlUq0fta2b8abwLpJFLtOB+SlgfmyEwSRzFeqQQqhjNwQOq31fjoXjMEE/ExLE19Wu4GT7ZjSa2hk3AFP2DordzR8xiTASNtaHLh+7'
    'GtAltGLjEm6NrednbYO81/XfiQMenPsaJ0xH1mYxy45vT4AaG5f0mdT4z4+bq1FXc9ZCXB8af5SazanNluacvouwOAxf8mFy5t+cMCcIuJ07nP'
    'lMQc+uZqKkoLTNroXmieV4p82EgMCLd/3fTsT7hVcdSWt0oW1FwkuzHwMEwlLeqDyWo+05EnSsXQxyXRv3f3UVij3+maFifGHy7MNLEaOHzgDM'
    'c0JFe7+agMfbJLaLFN9nOvjf10cjAvwUImLL86izMLE9oeTmlZtIY8ScaBiSDkDnQjeuoqlvrJr+1r0yKWMq8tR3ZIfWb8ZG+ZkCWRg/YgJUmq'
    'nE2qDKIVhQSVrye1pPi210LHJ0NTNfJvxgzwEHiR1tnILqxbYH9zDZFIILuqrY3MdPItXzjAp6RekoRSiPWOGEGyXUvy9nwkcQzkd9lvLgLOVl'
    'dxelWLQsE8IHrg8RP3vOjoi56H4+IxHxXaLXhAnebmteIKGju+qxSKX8t3/etdWXnvHo9lxQkye/84T8DuO3/U6a/WCnddV8DGQdO55l1e99z+'
    'u24ndA2bHzSu/mleSSAuU8wjA4ZLhD8eBJjWiJSksZ8qSuovYeVrPGsjW3PbI7Cb9ZDi43FqWCYzg7fsbYGHgD8AGM+c/Dmih11DfWz+dkjkyi'
    '5E6i6B0+Dhsmp8h+Mlgae8L/eVLo1Y9OS8Ia3bO2ooS7XiXv+qdPxF8ZN+pB7dHvkTuI4lF2ojgE5w1PRhxQttuSKPBj10Bvytq9Sotw4eU2FK'
    'gMmCJhllbbtncfbKi0MYW6ElbpptG+axkJciZRxtq0ID5LLiFY8vX+44NdXD9d54/x8aoHOKb8m06cqPtSYTlDyDXj79nEB0HcdE33MVb8loNu'
    'AAy7L5j6uFFImbDJibwyoIAJ+QnjFBBs8nsa38VD+si/mf/ktfjndqcB09MDSyy51+IhDp59Jn5GggJMdklW96OXWPTwJec5Bqxd0Z3aXkfpeY'
    'FtOCkisYI4+DfPHp0QBAy9P2r9XBZq7ZASYKJv+7299s3DVm2/V0nvOTmo5li5firWiL469UR/cpmJ/NKEUPG5kodr0GRQyYnmTIbKDGjHtutW'
    'dzTuKtoDuygufgpXj8ikHD2XVP8ZLvNTgYZbn588F+hEJgl7J0yk/dIxi3J95YXaMWUeJ5p6C8VRKckHAh1G52Kpq0DRW7WRy8XuG6pvL30nQe'
    'BYpFt5egvoaVKmspTyY/E3iL5QHDWL4o5j6tvyLO9GUTtNrGq47HoeVd4OsOYd4iFkHGkUZ860BF+QDNMQKjywG9o75oF7/hQ/wQgpM0hX/erT'
    '2nK2irkzlzeckJ7XMfZ28SeZe8CDKr2wS+vnnyhClG5G5A7nzK2GkPHf/W5AXPSOoqXOZkDRyy5bWVLd1f1sf39cPjd51vb72pAfmsTtoS0HJA'
    'SYBYcwXzI7m5ptsASu2Pp5J5vFnoGqCP7ssXsEQ01N5ZS+T5AElcwKY/QyH7wsgC1DV9IaYbyOrrg3oHfkReZ0p/YGOsHL3QmdO0aC7QJO45M0'
    'XulFD96AwtLhzRQew9BFe6DJy7XZcklSj93kgR/PWLv8qRs+JRBBz43wu4za5nbaYf5i/kKOqsheeVpsv87hWXYkX3H0edGcOVBMZfCCEtjAqD'
    'zmWw/OlPB8oYA6IPfxKZIWZilhw3fj7qkJaMd5Rub8D3v5xW/2fVOXJ9rWHRU6IrTzta+hsy0mPXv23x1uIC6iAFEZmQ+FRZu/TsXyvs379v1q'
    'HMshKmOuRSVXd9PlnMq7AAILtlh3+v7ihvErUAG6zGWseuHPWxZs1BZs8m+Lr/oJpwk4NMQy6qqz8SOHmImi1f9EMaqW+3SeQbGAUXHl/d3j9k'
    'spykBSNbaEu38e3ELDrLjCmftURNkQa6WQStcO2k7Wb1ExNZWiMgwd3Z3lqA9ozhTfVdnLsg6UHMg6iZvxHNuB9Ea4r2+c7dTT1gP3XwxXL/Y9'
    'I+Q7CXf+9BrqArMkFsS0eK6o6BT4mD9chO9rXPG5kZobK7F35vwapRB1MCmKHRoX/+33RHY1dhb62Mjqs/yLmKQoNcoTvC0kKN2WO9XkaOurRW'
    'oap/dtY7LkbiygovyRBIdXvjO0FOE7cd8JU4sdis5xkC/Rxykdbpe51zrN1ShlXmgPk9SaIwPdW25BPSzENViut5chslCCIK3j/HUyBud4lire'
    'xS7mwNPPwsK5bFcrZ/4iox8XHK9yDAabUwPu8Ad5ZyRkq75BS4c97peghqzFFU1BlxY1DgMjp8yqoeI3A7OHd5a2D3xm0uoIz/0h8hgbfxD+jq'
    '1VKQB3kzXno8w6HXYsnnKRBHFa7PqQo8y6bp/ZK1aifKRfAgRZ3H9FlM+YTeE9R5i/8Z7uJoneCKGUbZZL7KHoSOEfVvHgvJqN7iL0QK8aG5GD'
    't3nTztNhBayJf3oZYn6at18ZnKB6c3ZbYaSG+1FkkeeAW35esgaT4h/x57BSMyvKS/Dv1zIqjqKci3BsAT9TBoOwQ/hRkoF2rpjnKM+pvEfBje'
    '6UX+6Qxnc4N23Ft5/HyKdxl2+UMJW8hXrqErgsOlxdaDrKx8+j/ZFiR/n7m+3UB3mwu+YD35bs3buAvqUgULWyw1nPSL4ZgFIhjdAqqk+CwYmE'
    '+Fo8gLFlt7vD/ujgO9zwp/emQz1jQF0OuOMPjxdZsmfUQbYLXvK+lnmwfrjVCPg54M3W4U9v9Yzo4fWMAG0NU2pp5E/TpqJGzOdij3oi2+TOCY'
    'MRESlvvG9bBThr8zwyT5I2iovqbN8B72ZlrVPd29TOv/0HLfTtcqydAKiLzbudHGGBN9nLgCZE9+scmbaR937pyf0ALRGOh2IC/aR7joAgT9Xm'
    'ng0NDL0AmrJ/quM+f9M0774ziTR71DiBge199/Mx1bDNcKjN4Rel1SD6Wd/Tg1W8i5XpwwMpgp96L8bJ/VdrZGAP7ZD+c4zE+Pt6a+oHGDTuT4'
    '0ss2mPyT4+fGedeTw/szjzbeeo0qGyfWo7KNWjJsSNx9sD848CeNI4fteMnjLSlIBLXt8ShqHJaNRk1Rcz9EGE+KNXvzE0zqrJUiLc8Fn5BgoZ'
    'So0JARKi0rBTxiOzSIz0atB0c6iO3xd+kA8fy2t/KJwO6w20pLH3Odndp3JtkQ5Vz4llvt7h3CJ30Ea3qnEPGnp37fvHQmzFArIJtvtLzQZoIt'
    'mDbT6TbQVBba0ZpRe9d0hGkrBr7yEjRPkEM9dTgOLsOx1abN1TjVoLq7tNmbv+7LhBeaLup97x0kQaOYV3rk/4CTm+JV+WXF4P6GEi4Q22omI4'
    's8W6e66B71TCgvNswOSOoGq/9EovsW7kiYrX4cVBw5wn88Mg3Pij7+8k0U2u9X27+z05t5PwRkpzz7kzk3yt1+v+bQ+uNtuar+Q6sOJOCPe5gv'
    'bszka2VVxXvx/2jIlkXvepnR42ltbN87wQz/YbC9Jhn6EVDzEipEkPtZShxe+fWBDmUOy8QB+P/ZDQZu03FXwgxaAbdnkKH2o4N9F/vP50aq52'
    '0OMYPfhW0fOHe8EkV8hhidWNMbfIwNoV4w/l/uJulivpfPhhqORy/PABm7J0IK/56b3hkL/jxHP+elsv5RYZD8I4Zbclz3rIFC5DIHOPGaPEm0'
    '1sAX/SxE2Ko4YtZF1EQxkyppMVxiWcxfj2bl8iN0qIEHISGRPQGiKAg93ZS3zmROlwdcvGL/xZB7aNH3x4WvMQkN694KeIUuxrU+/PupWnRj5H'
    'KJTPLT/d5VB5A6zGuFMW74kBaC8cHRU55LNhXkjwF3uFse30e7f+T2NfAR7XrqRpZmZmZuaYIWZIzMzMzMzMFDPHzMzMzGzHTDGzvU7um3fnZe'
    '7sbn9fH7Vaql+lUlWpjrqlE+Px9efFC+ARTC9X7cqUM573slMgA0Y6zvAzzvBv7BT8rUhpuHpvvILXa/U670wYZ3fczrglgig0aKccCqdjbgrF'
    'QRTF2dFnBw4r+jiJY1Qs66zJqBkJYeu9gViO6AMjEbFar14+QrlqQrF+sL+4ZSDUISWK/i6cIisiDYEY25aHGqbJ8LNFFJHhdlP4zdQ+/4G9e+'
    '1t47Turdh4cA8xpmjd6aKzf0yek1hsD+Y3U1mH0eRljj8W6+G0eayXJ5pNzSIGvkQNXEsSfEMKnuUhQK0tcY06xvvLYep6+fCp1LQK3Z/qNMwc'
    'qlRZUYb9QBSJxbk7uo5Ff2tKd4nYlNp/ba/wgKIlmLabG/4tKU4C76YZOo0NZSbMuXVAJmsSNTohpHH9WQ3tiwXedAGK2krSEfsmH4JJPSCrFW'
    'lERnzCF6NbJowbmmKI3/b6MSY3MGCai/IO/holyeNfIfpb3y9F8zo13Hl5IW5/PI3KRR60DG1FOihn/nRY++2bJfxVz1VJ1YhnQVk0BR0Kpj3O'
    'VY1r2BpEvKE7fDc978t6aw2VGT7TY3qsW93LBrKvMKSAoX/ibeHeEEQ27FDupiVsmaEoop3IwWjizn2KRR9Y78DkuWJx7NOfg5aOK9igFUdsmT'
    'HhvQ9bBeD6KShcT0ifgy4qAbX58mLrnHaW9opklF5UZO387Cw7WbTfLjg+O06i/eZ6R53Bw9tg3cMRl0/IaI811if6/s04Onj5zSazfTPjqPYA'
    'GPHt/HyB1V0sCX8lOB+4gi6nFPCjnS3YEMC6i2Oi3Cg5E1ZcqsZAKO7+oZrr+bc20tfpu+/Rk6uDSmpsGxZKz/h3on4uuIux4DjBU4miYlbUH7'
    'OWjQHS9pDBWKzvgDdjTdzLSOy45ecEZORDYZ8KFq6rmcYPD/7NpX79eg67RTB7VsgXX6ajerRmyoOQHei34OjuadLc94kg15ndLdKO3H6ZmwZN'
    '50Lk1xzDjPtM1byCgzUH+GnwECWEcsKWqQ+hbBwQOYBO179q3Rh4IuZ8Cpdxn3jlIwhkhs0uReDi6AsRdYjtFhrbIgRyQBUEDy4mgpPvFvr6Ew'
    'GwBSrHXyiiyZLOziWEk+eDPcHDLQRiK9ZwIDyiNknhQ6oAODjGHd4qim3CnlbqgApBk3eE0ZDnIrsouOqAe0YIzcCpbkLRtdQESB5hl2SfKUUI'
    'XBw9YYE2lJ8I26gYOX81jmVNuU0o4RIC8FdtDU0JF0fK7XnQfxWXSkJW0pG2tRD85g3D1pHS8ajP+WDW13S/WbYp+BBY+GOq2s/madSHhqXShr'
    'SGnP5opYl2J0x5f8iS88WW88lW89XwvDyW8BcAH92OmmqPuWEw2IjLv9jToJZ0KafZrkf6aHCFW5gRv1OpIesSZ8fH5CVswcvom8lLy+zv5Hjq'
    'd4Kz8TuRWv2deCz9TmAI99/cdwCnXdjCmvmwwYV3OYn3374dIZMiMnOHpi6L943J6Bk5ITHWxqekZgiPnZIYGblDwwnl/jtH/r9XDA9JpdUzag'
    'hJWSb6/8g4D6/EUPxRNDo11gCPBH2UtZzMrRTpph0V1AUO8tsZ/z7cAKQCeKsrHfGIVn9GXTS/MULcehm1ReQxg71SFE0LCjP+iYno1lDqeDRk'
    'LpmxhJ5YQXsgvyPis+cfBVmiGnMK3sfwIURGnljMJ7MhqlkDY08sO7lJA2OnLHpGRYzM3JEpy6ZjYzLERk5YzLWzIakZfxZNEBk5oTHX1n4U9Y'
    '+d0ugZObsru54IYt3QDQv+V7T8azM7KtAioM3WWMjphF4Nd/jQOQ1Za+3/I6MuYtAYNmyFGrtORdaqKOxUmnKSFJayTGVkJMZzTfd1bCzKhUi9'
    'OCW1nMioISx1mUrPqDQlFfcyokDug7udav6cj3Hp27Ugik5ddu0bm9D/yDFz/cohwgeH8PxCaSK4+hg0sbHTj9zBx3j+KiuNEMFjriVemAz7VY'
    'VGANX1oyEVHcqwD+zqLjkURubWjzESGRuj++g54kfNJJHQrppiQPm+MTgaLSwEykEAGlK3PHlvRAgf+L/u9H6fGQChAd7lu2g3aK7jOIsdCdaG'
    'BoaP8DsK/H2yAUITnA9wJSeoWN3WcaQosBa0//+kXUsA8zxjx7qlG5zS6TLX/R2+/T5sgNAGF+BZi/rMyweIVtI9T75zUeLrGtjviPb3cRmCW1'
    'wAcG1JHFrX2nr1i0g/6kFcaWH+0CbznksslbZ70TzASsgf9Qz/xRkgOrKgA64geFR81G5XXA87FiyHDNFgYPevwB0dQgOqqQ8x9wSBy0bjmAOO'
    'xsEjb9pnV+FH038j1/qLfBRn0Hcv2ZoFy0YjCAcd7F9qQbllJxdSIXTYZRslQ5EjM1XK/BolxAX4120ZQhOLGLYNDv+vZRIOMaoEOarDxCyvQc'
    'ISgK5/tZ6WB8sBl/2r+W95aFNxs+w9NNi3XHAloAD/6twMjmWXLYBm8JTvLk63D1pPx7RJl+1nBoD/Eh0Q3VjgIVfAHQ75gRLzUNfVWvguy7Hj'
    'N7D2KKH/kt74tBsu+LQjBC4HnS1OsIG/KHAUcA2g7//kcJsDjhI8EgwHPOHfWm8axbbFkY8j+NG/GVscBbgP4cFR/NuOfzP3mTPggzmFwY8PJi'
    'xbHNk4/9YJ+zrAQcI9hL9kR7iX/SFZHzv+v9kCwwlOEPpgS4YzSmhEIA9wEHDP5z8EQxn8a1zO/y9s9dtWyozzSsGnX+/f3mc1DMKvPp/Nzpou'
    'dODmX65DH0zW7t598tTU2ii/vuovpc53lbqoMMNLax1QUrVrnECCVzB0Dh+7vhdxa5T55F0ZarptqGZ4g8obbiBDduPNG+E13vNsrhQ531LrZu'
    'h5/fQ8mQ6/OhqUUrQ8e/fp0fQN9/HBRZVmLWpy3AmDJdfA250jCz7rpjMNN6BhcF/bYc/Vm+PbLZ+Wpov3SmYWH/tqudX9wbir89L7zx3TWm+e'
    '9lWPjY4Uz8J3vre65+gzePq09GvndHIsVsvX+9brSfB2jdT95+Szyzbih+3rc7v4t+/jseyDZ/voyJotpg91y3zWmSt8myd8HW9vZ5fJy+eXwe'
    'jjuTOyrZ6jD6bX6tz4WPGF9k8jXmWmaX7R7UzaUru/VmRWKO+f3oH+86AF/mQAZltUAIBdT4D/7aAFjl8HLZRrmtuvctS8Umtsfo8sYgqF7CiR'
    '1kAVr4v7brCQOLbxKiWZMB4pbPZ5RGZ/kZ4fCISSFSvbqHRft8QX7QnhkNeE5+G8oKxjUVZ1QYXvrjXXy/t2jiV4eVy63WvkzvS1gccANNFi1C'
    'yL7Ub/1uUL/nea9brEu1bswQb/dM80dOXGi5WL89JV573q5T0RJ23VW9tO2dKsawvljrZOIuWd8MrH3S+9HU3Nns6f8WutVa8rgWk7x9M3R92f'
    'QJPXb7jYH3mpj9toyqhWOzqftsZ4kZCqmSxj3ydrk91+NiryJdKXUm16FMLmOC0rK33B4zVeNYo9c6rjrT5S9k7ae1vlWjfsZAQ+Wty17mS0zJ'
    'rNmsMrvH5VlCqAqQmueZnoeKzTTTuaNGq1WK8aKLjxnlS9x4YkxKt/iG7oPgveIFJyfWg0edKEZgHdISyvFWl+du4wzdzQFlFeIFstHNQk7gzf'
    'jGOAy526MNQeTY7GBF/wPKnVVk9ubXmtvJ2Zv9p065DEUTsiLE1vbfOEWHhSYd/LpDaSLXlszovugq0s89Sq0z6bxX9JhakPrEGkwqVb3LbBnQ'
    'iF27mVnimxaYa61xARBpqEk0pw0Qh1zu0jtPac7I6EBIo2v2xGe6+jVOPPj/I5gZBxDABLFNLi5PEk2Zcl2aHKRUatbg5TcYjoimw5X79tamCm'
    'nyVr91ROpFfqx+N+hb0bBF9BPPRxWG5a3uh4KreoSYuSNn8bv1p691f2ft5qa/342r3weKnT/Il+fqbUzl2xQgHVdgmfJHdk7Yuh5bqr9mKuvk'
    '9zpVadXHiSmXwu2nqJCHX9ITH6I/E0BOQK5so0Xij5fPQ7HlGlouDawwv4foiF71BSxhgsAAJX7EGsUhI6DZyHOZUaWdF6bnP7WxV9tIj+XuBt'
    'vdfzaGt60IIRkalTUU+oUP26l3XmJmv/ZSvdz3Lx9AiwsAGqxoXXzdnXbfws7VdLxC7N7NJTjurcau3agzIOo4UGqns02EDFEQ8PWBY3RiXWIO'
    'hY0txXxIW3AviG9yjqKOJsbUjVCMoO7i88fpyHunBclrr5bmWUNxQHmqz7tF1qmyYRhmecX/f2m6wIdOJlRBCa2iMnG+8wglHpkZ91UmPFda0V'
    'ipmPAFkoWZhLJr4feGT4kgWCkQXuk4m0i8dO5LOaKASk9aVsl/Hmmx/fU97qBxkqN5ZS0aatUFGbf0Fbr8rus8iQv6qtJsgjBs4jts/b3ThUMb'
    '4BY+EayNrlSy8qQ9LvcMlvqK8AqKFhq6Jha4xYaje9mcyx1D8YD5SARpkYbdFSNNQUSiHRIGUO5Iy0fn+yywCpJXkDdeCjlue5e94p1Wngoudt'
    'kB0gE2R4hrDaPCirMFa60s9YTK3nZOMTCA/p7kUMjMiM6hWqcMazK9+n1PbOSs57kMQZEz3oMX5QX+iSrfqCIZyxWiR7A9sPEIXXZmEitC1EEc'
    'ZtJZJ1mz7fnMvIUgGXtjnaC4GlDCvdEyhwmAV90cRQ5xvTgsSqLyZNYIL9rGTTsd1MEQihC9Vtbh9XeEXsWk13H3OtEnES7QpMJBkQYb8p3I3w'
    'pAcCFAZtOfNJX2VQTIuGhM2vyMCgrzOC+qfbbM9UUe7wYXAQMYxIZqAcjDyzcJIN5jH3+UA5b/di1pYyySKRWg0oM3KurvroC+emQT/YSaRGIG'
    'xKbV8AJOO2qQGQPHFcCSKtor8rbOXB98NPjrkL+hLGRIa6898a9/qZz2QsHvxZtIvrPkEQCKcgIC+IkU3xErniTyPxpQBfummh5G6UUoSzx0Fe'
    'xjp5do4qYLmeCDVMNPJtmxgIPg2BLIjtzCLMko6BiZcJjCF2IIeN2F7c+Bbj7PK+3teIOyuFut8FmENCxhqEPTBDQUkVnT9Bwf2QDJBTYD7WNq'
    'LmX4VgHOxAqY7XOVsy60MSs5HndyE3A1Li9BMgylkh5B9tDbqzROZhEhZq8oMYx/XjuxBRbUzrkCtXlMF/TbOr2s2UcUhapjNnOtkLlchUtS4+'
    '0jEtu7FZ2ju50U327RV8ySRzCtdjS2A7DowicopmdEDBGDFN6C0pRqZgZs+G37799jlYK7FD5fkLCCG+e67tqT6jLpEFRLcVRYCPs9atIMnyPo'
    'TXSWdiyfR1QLp/1Urz7o7mWSnjZx27GP38JFINNodh4JAAhOJmpB4M/yFm/6HZ/lKcc3O/carvnrndrSYjx0WJbHOhhgtCdynooOFqdcA19F5G'
    'pqBw4pM+J7eB/C481wwDSZRSOjNMRxq+yDIF1nwWbAtjLXxKJ+RYPeZc7hUYohT8ZAZN9CBALL6wzOQGQDFJlAdUASwazZJ0327JBzIdP4kjbC'
    'MAh6H7efSFQQvtYAKQqtYg63mRs0Db7stwCb/AW4ceFOONknPQ2d1hc8Uxcm5ECH7XkWoD+taNIMg0JCNvSZ3YEO0JapB58nnmTNisDfng2yOc'
    'mtOEC3h5CIwaI8Qq490cq/Adr6a3MfD7aaj64mPDKz95BOprysICYfmEG8QLyuR1DvDsJPLHRb/9qGIsquXOUL5vnkSGPpqootw5jnpR9FUHHJ'
    'Q+QIgQN0eSLgKlgmzYTSDfRlqhgi7Tbo8AARjhR0vNiQYWrIY01t2VSRereZeNVJcNTBdGWYQ+zdx8lRwiLBzVO0BKC0pniIvn0lnrefOq8xlm'
    'v8z2nSa67bMgh8Pz11WJgjN9bUBgpcJwTXhgtOElO8xvU+eBMbMoPRgpgt4OsDW1/iU1J/rjBz2fWf1aPGIO4eodPbcyfUlRj5LrzH9QrgbEzu'
    'R8mGdwjU4qy2E1/UN0d7OoVErTgYYDwALnOI7PHrYPKXN1RaZ2z5twL927YACjeG2LS1qiECIGP+FyQel493ePUqPulzgI/TgJx8uvVODdPlfN'
    'cVfNKzylTD1b5qfepD0pP1Q0eQZHuhl0Mv0DYsMZZZV7eUQCKMXgQKPpiQzD+9BFfEJ9AZCnAPJG+u5Q+cGJVY4ZukBYuijqPB1gTcqdbdPuSK'
    'rPCE1XONHNkFa3cKb8Zr1H3+7nZPduye/gX0xcbr3aVyK1v/D+TJMB3SYnHvGXFYXoT2NVFD3qOkkUXBaTjTkFcGX44Z3Adw8Rx3cgmIJ9Izhl'
    'JJBPaLWFCAysWKI7jMkDbt7iz7renXauI+0Mk3Z+nH6uJz3YgHEjWHX0Ew14w2Ex+0jO+bvY2zyy8Jd6DudP4EKRxeilx8Mqo3clrHtPz+ltLr'
    'Nfj8A0kNGeuhx4yKR4BKRbDVP7GlH91RL8HzzoT3n6jjWGMZa6axeLZHUBPNck317fiQbr3wH1WL+7ASWqJbmQLStqUThk3xJcfLujig/KNGjK'
    'FABDBaNswskHABSnleQBPncfhKbkT6t674pfW2Te6oBKYDFVhiEl6Q4bQpr0wdm8FIRKILMQ/JkburrNQ2LOdSAIy+f7uqGn8QjCUE+zXTOFWT'
    'br/hYBVKIT7AmKwEOYoBEfNb4MNcUGdmVh7G90/S142ppeaaWV30Dyw+WqHvJTB7cj9AlDDFJX7uK+MlWeZH1ZOlAf5Fxv3Uy8Ipo/z+z/osYz'
    'Q5CMflaIx1Y50prSOB7e5pX77a6ahv228iyUTulULjEaNSOkfhkaEYNWUUfKI1YMrqLK0EM+gn/qRnAerY3x89XlM642wdbugaDv+MOjfg8pmV'
    'TVZtuuYGCq4CHRJ34jO0+LSRp0qoy+ou7egRlq5p8YwXl4OCE0iEzsAdnbgkBnPIeBQzUt9NctbxyV5lJmLp9um0Fx4aVerjOAD0LB5IdInB6Y'
    'So5P2EEoxnqcQbrSRd89uTYE7GGdQMpeIMPf3ram4rp7Onq0xkfe1ofqfZ0gv4eWyVZ6xJKzqvjdkabfAFusgeVJdYd+EQwYRc65dKuhh9gluN'
    'htZYbyJap59uMRfEZ30yUg5p5vAKqLvIwVnhlMOvSEVQZ5WRF3Q7gzgYgWNgiN6caj7eNRM9maNlCYXyRX3M7JFi/BcmGJnyuJLpIZVBpebq38'
    'lJSPtf3Qnd+5My0FR/V4AH0jYQ88vAz0qtbWs8Ffi1V5b+JruTUNtLqWBxpnBLoESUoI8gmLTCMTYnxRAhioqc5ElFGuiUUL0Mm03eZwJvf3wH'
    '5WqAfIMRP3qc4F0BfxBaSGqjuIlNnPBGwgwzNZ6KvkQz0JO3N53zOKd/TGlKFNgceSppWJs0KD1a5EhfdgtFoQpxe8c7VLTZmfUXkIcsITwUc0'
    'JDzegO4X3d0aP9aYfuh2QT6oAWwoxCtenEMPsQgdQqLzP6hpRwgQgohttiBI1fKhbQQ/jtgCiqVFVEUKISHk+FEFo0cfgTAKRt4DStkbPY4Iv2'
    'GPb3IVPPxWRe1tZHGuZLDaVlJ+OkhIbcYggkuAKSKcBJEabN2H3q8jSxpAxBcJDysO5l8FjnCIlaZovx/pNAibPlMx6tcS66h/NhN8pdKtBULo'
    'G0IDyYCEoUPCwEDg60vi65sEQkWHMRXb5ZDMtCn1yfZp6O1eDm1wAtpZcvLISrkjP3An30unB8EfEoYxBoZxikn4IUU7m7O5Q+eV0JujYRGRlX'
    'Q34Ky500jn9k6FoikBUgyGzKZPzq5PbhRxW98jJ4iw4nsd5/647DbhFje6VINRmKBo0PBPVDNn7Z7BC8HxfcljhUb1E9JVy1mq3nLmZXtKKExV'
    'Z6ex155XCMIaJx541pI2uk0+UhSS7QcAD+dAQNIhQnmEHwjquWiCHXnZrds+SAb8qxgdJWLbQqcUHiHfllUhCZ1oyBNSG6ZO67h9hbZ55nCci2'
    'pZ96VM5b5jUyB8xF9CH2pnGjUWqrcV26xlkmAOTxoKXX/ExcERmGag6e2ScW980nI9Mf5FzeGZMjXGzbbhvmPo+1NivQw8Jy4y+7PFe4ziq7FN'
    'BYbeKkkgwhlb3Fkg+nkAzGVGjA1bb02ZN9qCkJpHo5Ohmk9D6qk/DDnNfZB/uC/d+jHGTj4sM1v5SYRm0ZcqTANuv5XZ+ewj0UVwaZVeWFJY6H'
    'oWKVvKuKAgz7SZVIG86muWbU5AbnYFpEo5yTYUnr7Dkezgmly+ZcRrrI4ZKhZC1W2QOFTxOFRTcbQxESLY4SeNBc17GmqsYajjmoWzJyp1PNpj'
    'h/V1yV4Mo+f+KO2vzLxCdbjC4CctPhdVqiGFHF0ZpJJSKTa6HE2msE0GEhaEJGBdmWdvs/kpRAbJmzwz35gvDqPoAqLqv2Xn/Qpw9ERz+PKyKV'
    'NiiwGYiAlxmIi/W4KaYBN/b+c7CsAUWVKzydeK0ySoISWSJLIQ0g+oFiHss2IO+aFgRXJPlvtVytZVN19chY4Zy2DBdUVTUhLcqIW+lOy99hlo'
    'uDACNQsgOB+nmWbOpq4Dw4FUnp6lZYEgro1tpoKgF4e2xQAwdcCCrbHwjd57yZDIRdt7vOHMklLaCBFIoWaI2VZuAwScVNUs37DE5jTKJimMkJ'
    '/zGBQD49RRI1RQFAPkSwZLgxSuKVJ8RnyHhw1hicSHD18echfDu934Xm8hD3j3tbv5vnBFyaeBcW7760VkuYvY8djuX4YZmHIPxyglCHzxqcmc'
    'mel6I8x9l2hcaTBKiuz426Re2TYIoUFnXszRmkOAVIF7zvRXrrg1bkEnWjKNw6Cu/h7ndoTPIpVuH4qMKBmHYy7OhEOjByuuVRdsCFcOf3i3oP'
    'xCQ+KYrbgg49mFCaiM0xIi23YCLfB4p2XCoBmy9xBRXyLJYdLncowEh3W/Bz3a9IWjYdAC/Fx+y42VHwEGggkQojkK1xw+uje+R8Xd3xiw+iFg'
    'cRbjWCeICxkmsYx5wYrg61py6TL/Ayt3vuv8rdMdbwjZSSGjddkj42Z1IlXTQSsZRxMG3DkIDoluRH0AYlubOZ75OYHC7k9STb7pHlQXeVrl0u'
    '7uXpufZFsEpvplBZHqGOCWdrW8SmN2U2qbfWr4tQtZOuVj+gMrPPvEFuX7wuzY+51q2s+1F9JP/uVsRnwPVGeV6+y4pkrrGEPewv4SPjlIUvwi'
    'Rjz6lgPXkKIitRKvzZqxDQuyprcQ9Bq2sFjxQmM/bPyG4zr60c+5IlhTJzZLbzhXz1Te4NWrds1YnMRS1qdBWsEbC8zjs959zzoM1HfAV+4pwd'
    '36K4I28aG9PFlxHvSR+fVgYpZwEO7S8H0/P4/g48Rd/DwraQiC21Cee63NnMogN41UbvLOgW7UTvIDiFEgBgFLzllRQ4OoYBgX6Tdt15M/NzUe'
    'WsxrZmozVHzxgUOLQJAoQaSZAECjJV+j1pneIL9JOV/Rsi0esVSqXVSrrr0z46P8euzTBZGXgAW4DeczZTcgCBgQxOK1xGOsGL+43tcM+uOhan'
    'SxeYfNezWAdkSBAQr5gaga/L5vVW1AhUpuSm7gsbpwc471BPbZjoVKB0WqKZcGNI/BlxbJ3aa1tXwvHBwUCqtnaE1wAw50yQR5hEKyW1SWILIP'
    'b23Iytx0Fx8qj7XNtnp0RiIgxFK1PV+xsQTeHpSMRT7JLzaFHyX0U1PY+oKCiA34jsbXOTqGsPClC2qnPZfra+UTr2S7g5gX2zF49/4ItRc/OP'
    'QIqY++0vljL1nSZoFYd6eFh3nbbivWp6RBvHJ9ZfhOWSBa3Af8tc4C2eL2Ayy3xoh5TLNxZe288yJIrpNSidFPaqiQBlSfKdAKbvNIqM7hGkI/'
    '13178ggCq20E4Ai/L8QFKcEljrLP/uYNn/bSQ0knZ5nLdZKtvcEaer1G+evec9shW99+4O238yiwC7fPfdGH2QLD5KmCvMM+Hki0jx7y/HmEWe'
    'RTCYPBRu5rqumnAqD+iLckFLckX4rJMeVkcwsy+VAYTIoPktusPonFJg5iHajvWAr5o+MJAmSXxUvpZgi7++zfOKIZjEkPnljke09HU5nK96xW'
    'oJGzDoZLpTAg9hAkGI/GLWUysihedCLQY/nJYJflsxyjVhT3oOb/BJHxPg4v6VP3zP7CYk9IinhzLve1RbggNAZsimgRl0oT0tTFDmcXJCxzbg'
    'JSnp6dnmEbCZlMEIKuZiNnJlHCTU+IowpQVXAg4MP1QuSMgFlgqpJ+qibEWsrWKtPU+RXjBcgZAhNpluRnwLL7Jz+fM3NJ61q3Gqm/RoHSjno4'
    'v1veV5xzhhqNnmuuk8f1pZfzbD03W08mdax3yKm8Cd9//0nvYJTwZaR1tOHm4LQR5fw79vjZJiz2iNPzik9wTY6+pofbyIy0UrXsXLGlKtuOvw'
    'fo46VOdfw3keTv7t4ieb2FWkXBpyNcU+9Km1d8tXcZg6zu3C6tETPt1RoP8Q39KPmuiQWb7p9X2LXRBx0WvdoRtDc63HWKGtjPfLvPHUec3hWM'
    'lfw7rdUTzNwXilUYaJxm3+leW70rn8+8Af9zmVa2DJw2HRkAgKQDEAD2r2VaewdXC0P7X2uzZ5qW1ruicG/UfugcdcHmxMtR+ptkpo2cIM5d9S'
    'o690J8NFU2eqTT5ZYFNTNkr7dF1TjqMixMrB6Y38/QRCwk01z7tm0+ww1zau7JXj/0auIcdO/qdWhk3J5fvbxliYmVnrS6MGp6pm8Mju6MSKfR'
    'FrpesrZ+Uls3vnRoYIKn3Rd7ZcDBpS0crnH2avFQ0aC7UrTJ4KW5rt24vCvKfrnOWlalx4J1F1heE+EKn3TL8u8Et3673Jd+4HQx5/V+Knw6s+'
    '7kyX9ctR7h2/RsfLt9nhS4KG440pec3QyiV9t8narwnw6H63AbeLtVv36cVT6xzhqxpk9n6/R6fzSXnCV/lubrfUFpo8WG6KB6t6L3ePXQne1N'
    '31m44FuOiTZPq7RuLdnOG0fIytrIH13/fP/cfpWce3JEBOeVMTHphj7rapdIul+dfkSUypfIdz8Ov3jEM+7XtlUNJGngpfqqpRU1Yh30ynZGE2'
    'eYVs5N726yKVvzrT/aViDo8iSTJtJrbKc0GEgY7+Uhp2GvVJrYnTZof1Xo0TCRxvqAURa9gnamTqF//vNWodaG4bDDOdxVMMsrUpv6/jA9/Owd'
    '8eZcDV6D5zm5xzoidDRrG26YtsvquFXlhFtysu6DkAvmDOtbGkN6lJQyoa6Ye6Ts0ztU9DC2cwroWcCXTFLtnYYZM1pAv6xC1aQ3p6pwkIEioS'
    'RC9jYRTqoFcXbEQ3/7frszk9dBCtRhjw5FKrD2q+Dr2WfTzMHlq5qHGi+j191Sye7968Gi59z7VYsnlNto9y1wpSOe1FQ6a/rv1tUDnvWPltyx'
    'oqR5ilirTrVvX9pGFdPGdyyKiFIXKb25+TIG2V0vPZLWNlI7Xd2sucSveTRR8I2Gb9g0ZRYvnl5AtoY/Jrus26vWeiYvzfCmtnpL/OzC8GcUod'
    'QCeGXQyUdQYAwNufh9USuCSWsoMzfPIrq4prHipAuqZdCjBEGFBEM35utUoCdHqCt8Vw6MomaUBLpp2e44gr7xPgnRRrlRKBHZbNzgHwBq8uMR'
    'oOEiQvwRM/tCuuKag9eP4LMbk+zc9lQ0WJ5tJU1NQrtbWhV8WNrOugGWXrSrlJ047S4mHDau32fmh0pKh44oGzu2ZANVfMjpNKXL4EFnn58fZ1'
    'td7Vo1+oym8sZlL2pZoiuvSTTTNidkiyYbQToHVDM1sPGFuiMLF5/Pyrt52t+QkmE3SWtV29YAuN3acjC0T4Vs7tKbIpDTjNczkb6F2ahZsK02'
    '7Q/KK+ok7pQSNcuAxYNNo64Y93pemae9/5T7PMZ6AGZkTeeV1c8+vPv0vBt5Zhncehe8dAdeuYL/NYQz29oLntf5me1KOOUuWvVS+QDWzYHY+G'
    'pxyOwQWxH0QTONtBO9HRPRS/MFwfiWKC3pu2MlrHnWRb3/Zs3R6+AD42ZXaV43BMsNDMYiVxZsonVQiQmgVZ3BFvkQDe5PNniyn4CEXZOmlXUc'
    'expGcoIqUpgGsBSrRHGo9rSHbBEuw2wo2GvVLd3zwSaH6et3N8ieSKqQRCleICdv+dN4ddgBE07qQ9RyPQ0/YFyD0f2Ds3jnTc1eMsEJRWCSPO'
    'ofO34i4CxY67wI/Dx/WVt0q5tGE7rWYf+J1IvNjuG8IQpoZuOUcT1UBgHVYK4yhxGEcXqu+9PuMZHuWGmTquf9U9nVj/2S9nb1W/Eql0OKT2yV'
    '9dxqZ9P++rdbUl+24UzCawoCEjKocX3LrNcI4dAMUVZWJ40Z3u9EfQwpo6JaDe1KtMgkQRVZEdVDPK0xxIcxIrn4xSKoY3uDkacBd+Y4c+PPLc'
    '+FHaIsoMZiMOcQjTjOQcbEyeWcDMYY7UPVGiSp88v3G+qKltZ7BGzxXs/Z351IyCUE9eIEsBz87eTZdSTM+CFSNoqg+SdzZvGHhoKqNX+ILnJL'
    'WErQhK6cyVr7mIZsvCLzlvsldxSjMRbieaYIC8k27hdfK8mFCssjXZb6SY2qa+MnHtZ9CUyjGFeQMHaYlfLWduE6DwljyKTIVPEUNA+CiTNZqy'
    '7mHmYdagfG0BUKj71V2BDqOaNmegM+pwkXYxazsjVcKxYdyefPl6ZB1cNHno+Oprbf+xq2rwpxjKUjjnW28G1jcvpNS4YvfIl+DjCpb5axFvAe'
    'iN0kLANnIGB6MYXAlATZjI6b388GeeDzNhZXRIV/PnL4JoY4eVIMGd2HcSOb0nX5FgjvksSpbAyRNdCQqZ6N3GvBA8n0xVAWUCuNWmoPOJ+i0Z'
    'qVEFCqzQ1cgt3WcF4SmH/2m+kiclZxmNADb4xgvQYcI05TMD+5wigmgzWfi+Omu5jO92FNoZTvokz1zfvxOfgK5LPp3UFa31xtP5UbsU0BkzJu'
    'LKvc3Gu7WJvrrZHEZSF0jztHTNVYH/bg6QXAMaB8qHUneLqTrlMrpBmqymZ2dNUOf2g5hlKgo88WMURglGu6cRKKzp0tKgrEW4AjgNJmBqh8uO'
    'OstFS2CcgRgAhxTLa/exoOKC5mZFkcigBJDIlIFeLnKcJCpmLPgAwY5DkIIIFEum0zITlNaWIapQsqMmB/H7EXEhcK5pjq4hRjautr5Lh9bBNi'
    'xYFyv0JCvuTZ7uG+zDu7UCia9yQtLDJgWwhM3Bq8nxMwB3hdbEnMiUNuVR3ArYQBs92EX4ncQU8YYtqBVr45nQG0VTXNhJQBU+Nfqs8VuxQv9A'
    '9s+SngUkjZYSPFO+r26yBJjcWsAcjHIJ9A1hhc4nwvZ9RUfTkt6cokoN6H4QtiQ96vck8hHU2Wj1VlwkeXQ3pm0MPr8BFT/Gk8UKP0NRbVfKJ+'
    '2vLreekQH5qWn7iQV4oRzyXIjCKZT2ccpP4hXkbXnDJ1aEmFbz5lsW9EBwO10nu5eVQlkKyXmUtrbu7yZJ3bSkqj5FGYNoI0SokZTp0plQIRZA'
    'QWw91XX/2NdpY6IUrSktDr/IDQyNAAnbWGoh1TnhfgI5NDdJd1Xp0RezeUr2pxEMsU4ZAaSTGJz1vphzKn4NYb0qmQzcZ8A0qN6t0g4GpUwiIm'
    'Zwo9O+Jl/eLYaTC+YNqfDvLzrrVjvykIHUxlM5uoIC8hYgGr1P7QdDBxwON75g1ZUp8OkRya29b61D1aS0zsC4qrR2ZCM5KNhh7dEkAn5IPIMR'
    'WDpSR6UBHa474V8twlnrH92T3CPxjGKdoIWMusDiCHXMCkllIKMWtrnjCXyA2McGU+FALCsv3cfFnOdRzSDKDfPPyGe8e7YIubi6VScodkdLlQ'
    'QNle+FOLKAXiiCHx5TkwaAP18jbHiMxBNnS0okshVIlE9JJNTMNyq63KQbcdYM73+mHnEn4LVuASHNJo8uSHMFl5ZSN0H1XNWM2UmhzJxFCc/h'
    'GtRAIPgW3g5mppom5PceA2QHNYLSKqPJ6E/LxiCplC5h75RaovabTHBbV0ubHmCD3U6saCtrfkWuzAgbQcETVKKuMnRj9iyvKKyZJtn+PfiVlW'
    '8uPrp8wAgjdC7QHGsrpKoavR+pSbxURrS3pTPY5PKxAmKrpJyZjEiEpZ59rJeWdW/FJaTIGH5I2LpQWGoKsGGOXlMQVAL5BFVc8h/OEiwzmBmU'
    'yNB7MUpI3DggLMTDMDIJJHTvzTEFR2UjkSOWfkChbVHyG7lsswXKSKEkYEv8MQCuSoFa0jDGRTRSmISzXgY2tJ2yyHv9fRlgqBpLKy4fSiwLrS'
    'asmM7jq7NCS4EjrVVjT7DTOaXx9qQBSdihLNqChjHxGoHyId0l8lg6OpD5tGZwd45s2h7h3WGcokxM3T2g6Q+l5a8z1CnUY6JviHtNACUNJlyu'
    'WZZ84U1oqPqxdgsqHYvCRIbbGnoRh3VgfLOcHVtsgppkwJkz4Ctxk0CQkz8FKmvwoPauAMsIJp9v1YDLLAyrWJft0WxcSRahoco2YwU1tuu3Ug'
    '3TCxG3CRmAD0N34MF/mCDmjN4yuV7B3JcDxATCSpFFQT+0PINXcxGpATh7svv52fS2eyVDeRF2qGDD6TcVpCFxkMxp7z+uJbI1Fs5a5TNylg+w'
    'VVjA2O/Lgx/SD6LIa4F5gwAJz8XOBiH80zD1EccMPduw2nB2JhUlCilEM48DQjCQV8bBYCxBxlnRbBiQhNe/qFSeWS3NOVO0smL70q7UEK9pc5'
    'rPgWW2AFyN6f5SUgO6QXhlDUFKAKvcVDZC0DQKnQe0dGOUialq5YoldeUdwhZk8v1RDtePvQ/uoPFRtsNvwTJ3AEJEhJ4DFy3NpG/J2ACL6OS4'
    'tGdyztlTWKo+n4Qk70XY8mR1Q/quHfWRPZlaQVguna3oglYvTPQXWc2RRxAE+4H5dxjdjlwhIBRR5p22eRgGa4SVEtREtTPtlRyOvL4Crn6925'
    '3Ge7A9Jw3a+WP/NSaTH9ELMfwGDqOsNwTD1mvtyeh2zUt5d26bapBjZUhpAI8CbyRZXfxZVpAgYmc8Hz8TkFEk04FwRESvrkR2SYfoqIMxHV1Q'
    'fLBSnjAyNylldjYCKgJOtZrEvT3YtYn8mvfEEVvXEAEltwWDW5jR6vMe6IxDqswqLAyVjKhRlgkNdjjqlMTfUILIfq4lrPJbW+a6byKWqiyiF3'
    'x9HJ7KbJlakKEDPHIZVX66iIv7Ae/t4M6pxwmNwSqnj/zIeKeEGGWJiIsCoYbW0VZ2iIeSIGT24X5giAdYIAKzYwfmdwmVUH1R4KpAz8Do5BTA'
    'wOPN9++9YC2NGHohbcDF+eDlWUIKDL39EnxjkbTvB8yt4G3OyER2eGWlxG/RJOodRpkTI8US3QTmlGTpK6GIJxmbuKpjxbmYBY4YsouTX8KW5X'
    '6UvLHQBdxSHPhEGlzonvKWpZXpcV+04UhXLKBgzbQ/u888HnHrvufPoTNVNbL0/Mvid4mC1KuSFQqHq+0B8UeNLhnJXKuli07gKPC6DBD5PH8Z'
    'KCOdgSMgkKB63vjiZhWAm4nCwiizHsOALzgAmIZAqrs+JODtDRGD8gemEzGd4dB3IgjKdQMQeDifLqVwfiKJXOcKpdkZ18e3pDlIthuXMGp8Bz'
    'qigC7RhIF0FgKVDh6DFJNsZlmVI2mO90GUgTFUDGrKR05gp9ccashiw06ww4SSXvHr74suiWH5jULCE75H7xb40Hj+VNDAovWUN83CUGVP6AaK'
    'miDUwrFiyPt9jrPrViEJghb4ZE1YANh6zYcnVuEGit5tvp1Mtm28wBi675Fpk7mjhUDUnUaFs6qq2QY6j9DFUk60ZNrVJCD+UPwSwbyqQ0FEcI'
    'etxGandSpDcht/1zFgF5G9IefHhNgOq50qVi0k9+C++uH7YlITxsHmMFATnRueq7elh/DGytAQdjohK16UuzbFKHbPI6RD5QTwtfSSos8VTaaa'
    'abwIqXvSXg7YP2bNaq0H7tDjEUuyauyAikgw/gbeMFyicoGekKdUtWOyj5UBsUi7iRBX2jyWnonQZa+PFtTD2/AMmX/e4AecHmIZJxaQQ4MUM4'
    '5mlxLOQjKmXigcEavW9lCO03dUFT4m5w3XdLGawol6yZFnES+n4MwXVbADpXTXCOEEgDyuJ2Xb5Mmtih8TYBIuVaPY+SQdi5wuL0CfnhcfHzEc'
    'VlYKZ48ogFegnXCYW6ZRt03nqAXYGAFfzOOp1d7ijYltUyERG3wWoWrWFoDXMDOo2hkdCxfuc9HJZQfsnEg3fde8i4q8GLh3ZnAKcUog5dCEGq'
    '35dW7O6qiyGI6Sl1L/NvBOVZabdIysI3iB0ssiRcWMqB2+zTNV9sGyfbeauiAZogIs3BvwptcSPJxob1q6Rl1j/4he2Q5DfVxYXXj6Rk2bBOXG'
    'MsoSvYwNovwhXX/QRr7noDwkXZVbhMrutnKwabdXaDolXkOtbboRX+ERU+Tz42CFImniVx7VbvKvDzKXoBuORwTqXGAXv9ek420BDk4Ahbhwq6'
    'kzBVOxj6rYvQ1+XsvYsRjaYEIgY9myugqttiV/Gt2VP4lKZPfR6bgEnXohiPuNTfJyrqfEyCKlqDm3/ZOwZOTsucH3xtA0IXWMkby41ZLjvAwB'
    'DyO6vEEnDkRm8Cl6ygLEIc31xbaTyyGT9UCPxEoGEhhfAeoQIgUwCXvg6RU86qVQ5fS9TBdZa10kHRfm/wiylepd/JTXdMqXVS69lkt11LyKQb'
    'X8GyHtcmbUj3vBDTZPzeAorLY5dIi4qU88LX2zff27euprwRsae79Cf3Sr1mY+fFqqOK7WvNwbvWhhTRBXde7Q7qoGIC+Y7ksberDW++9cFlHl'
    'Wv5RzsxXVlBXfn2fyjQtyOYicStvuz87Djczd8Y9GU86cIMzGdVdM65sT0Aea13kUGlCBfdmdWGJHppfOOle0lgIgoamsFbjRD/9aFNDCiMKpy'
    '6Qbk4m/sB0WPN2Z4F7K5fly1D0ZPDJN8VvSZt05Z3hHGw716Ne0n7amt6a1OWe/mfRP7n2Zd01A9SUdVXzAm6di0a1dLbwezH+RuWh6N8Vxc9+'
    'xeK9/CzlKv1F5R7ccXomF9Pz5TqvN5599jqm8WtRn1slW0MzXwMjfwfuFVdN7Te80qz3oyJuvvfGLPkALznx4SnQ4PVwNBZ2uJFN1/f1qwWBpD'
    'bvCSkj0zscS35A5mufa1lErn6LsrdJKpay/JWNiX+LQ+hhwv/mqy+sQouyTaPcBd+P7kBSM7z8eMkSJfr1s7rvOcONzn1P9T71N0lCjaccSY9+'
    '2ufjqpf7eBgne/RqkYA8ZSRcqySaeekA7DUgWMhMhVv5vDTZsMbvkY0N02XdT19Tvwf67iJYe14nR95JCBAACgP1JtO0MLe3q6X9eMuGarXgYY'
    'fu/+qUwG8CnCEGbDSzSQR0ClXPglJNAwkYzOypUC2xhoTNdPPEhreKb8Zxz5DeElGK8ICqZq802AnxtIo00nYgUr5mjwWINn+IVX9YWq1Gh4+e'
    'kwjRrbDdCK7POVQzQWMwo+rdLLClj7VHJJ2QqafpZkhvs5PuPNdH8NwyqyJ0GcqI7lMrv35rQlPp1DpIKWJjI8m4tb4I07eBcze1SpT1Tnpn74'
    'aGvyFSpqTZ80wlav7o3Vbxj+1AvgPzu66M8VHPDRSc6PXsL//a9SPWtr818Llu1JmrKrH1r2HoYusmtGIjN7oy9NiqHXRaVUDkEXm970A2Kwwi'
    'IZqNOrYTWqjp9N9CjRPirv3tMDJ6uJHf3KiaaPtoUeU7lE2eTTGZjvCJQaUj19YUJ6amgM6TRZArtvmoSEnaLcd0k0Yd0UEFLA81t36vIcmKdP'
    'zzaQDhWZV2zCztk6MDA3QsfNxqKfvgIFI+GZZrrlBH8l3CcX7MnbSquSJwPVLwlGR07+ajaUWSCWdOAXkTi6pg042c9z26FjAYK/0NscXkGwGO'
    'jaiizmbUeOYgVlGcdRJy490BkCpouka7ID+bkgI36XJDWI20zqCz3TtFS4vk7aCHHukTOl0ZctdrTBr8TFCb2JVqx0xxuJ7wqujKn8otHCbNSU'
    'i+EzkiM0hMqgUonBHJSmx7hIoi6isUL1t4y9ph3FiWw2iSOjdCmQrmncY9FCWKraz3BIyCwvUiNHiwKBNN8Jw3mTTjVMwhhmgFip+COxsgcGgS'
    'lH7TkEq3HjoZQ1elEvokoNxXCUutJYdcbXfXU1dCXMUuJwmUQq1M6gVEuDyuqJawjtBhFgEc6XOL57GZ9hdTWcmJSyJc1C2qRlYV/emhw5e066'
    'NPMldN3e+j46uoRArnZmpSl4XxScV90P893YLvLd7TrRFx++RYsbSFGBr5vgP8gv8l3bHkivoGdjKqYfRxY8PZWwkkVWbLqwP5ceW0EC85la6k'
    'JeBg1f+WAnm2Cbu2i+dZ1fhuJb6+OnYdNh0D+kD7ei/8y9MQPeIHtncq8xrbLAWl3xxfJsBOXzWItqrIpSmj9wDV9esHuzqn2pYtjgwet2G2T6'
    'vixHxN3kNMfo3BnVfDKO8Wxkx/fIH+PhGKmuafjc+cf6ehZZqsniR+4nKAAA1l8K+5dx/ne1/W2o/XPjcH4MMOA/lQndAcKzQ8B4XC/NPHxBR8'
    'VAGspYj1fD3bqw4LWGZCRXTzc3S5YB1ccjj0qsaEAbK84olVlr1wHk5PWLTI1o7nrzWSpmeRIqgErDaysQchmkujyNii3vUjFxLtDexVkMl1Ga'
    'mPsLejO9QXrnm5jnQ8r88pxQ7Sq2FqIs/RaZs2CHqZay7PbuipqBNrM/+xC9Z6v46L1nBwLQvvgnAdXdwEuAUFzCq0FOjfBRoGY7CCJctotgsV'
    '6olWnLNmUGd3JYeSde7C/uQWdBIIB7Pf9hv63a+bSsgAAAweAfzurjW3UhaysHQysH7a+uNob2mr+fvJcoLfvhsILeJeZP5oxgMCDKWwGUl3z5'
    'ENScI9Po+zcO3z5Z3RP6ivZ/JXETT1jyymK/IwxvzACPwMqjNbIV+YEf0NUGRMzoiEcjJoEeQcIbVP+TqXIPq8+CKyN8TRVIErIe69LuEqRgzS'
    'QsE7tDdM8CDXwKQyz6uS8psX/GvdxOHAddXd0jjwRccCRRE05pZDcAWc82aUrUCwznWKsRwY+KQG2Yn37GJsmkjn/FtKtOeydCTDmJKrhnD7uX'
    'lPIJoKYLyidC5j433ovJNli3Uwt235nJk39CA/Qglhxty27NlsTScUcVAqjkjTwzhObTg+eUTKvPTrKF1UUwtCM7PMo6W9ugtrHHTOfUoAUJb4'
    'XYzq4RCa+V2I4+LxK+M/Gl7Xs070ZG6fuTucn93GfDaI/p185RWTlJQCAU4L/lLDoo/TnxIzf+8UYA+PvlA/jramCtL2dnbWNPr2tj80vkf1Jz'
    'CyuEqX3UfP3wtIj/Qd3736n1re0M/4m8J3j1avBD3xex/xrkv8mlgH5bgIOJoaXhX1fGfwIYAa9U1YEBALjg+2vvwL8BfIUh/nEnwT+iRCbPS6'
    'N8oJjw/ImygvKPKEz/hDIsiujY+6Gt6GR/opAQ/iMK8z+h3O6tBpezAAAU9AH+gYJL+Y8oLP+EAs2pL7v94UVcBv/kBUDrH1FY/wllyO6l04MX'
    'AMCGE+gPFHTXf0Rh+yeUPx+k+TfKcOP//ljNP1H+3CXyNwrT4/++Z+RPlD9/xPxb4ZbhAP/zJ80/Sf+MnP4mzSIC/O9x1J+Ef0YifxOGEAP+GZ'
    'f8SfznrPA3MScZ4P9ljvgT5093+jfOZ3LAf3KucpKgYAC/fQICAAUIAEAFxS+H8H8AZLuQpw=='
)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
