"""
Free Zone Inbound -> Outbound Reconciliation
============================================

Reads the "DETAILS OF TRANSACTIONS BY (IN/OUT)" inventory sheet (raw data) and
produces a reconciled workbook in the same layout, where every inbound
(IMPORTS INTO FREEZONE) is grouped with the outbound rows (EXPORTS FROM
FREEZONE) that clear it.

Matching rules
--------------
1. Inbound must come first.
2. Outbound date must be on the same date as, or after, the inbound date
   (when both rows carry a time, the outbound time must also be >= inbound time).
3. HS Code and COG of inbound and outbound must be the same.
4. Description (PARTICULARS) need not be identical, but must not be completely
   different: inbound and outbound must share at least one meaningful word
   (more than DESC_MIN_MATCH of the words must agree; 0 = at least one word).
   Packing / reference words (STC, BAGS, CNTR, REF, BE, AS PER INV ...) and
   container / bill numbers are ignored; plurals, joined words
   (MASTER BATCH = MASTERBATCH, MB) and small typos count as a match.
   If a description has no meaningful words at all, it is not used to block.

Within those rules the matcher works in passes, most reliable first:
  a. Outbound description quotes the inbound bill number (M1 or M2) and the
     quantities add up exactly.
  b. Exact quantity match, trying the nearest dates first (same day, 1 day,
     3 days, 1 week ... ). One inbound line can be cleared by several outbound
     lines; if single lines do not match, all lines of the same inbound bill
     (same HS + COG) are tried together.
  c. Leftovers: remaining outbounds quoting the inbound bill, then the next
     available outbound of the same HS + COG (quantity difference shown in
     the DIFFERENCE columns).
Anything still unmatched is listed at the bottom as
"Outbound without Inbound" / "Inbound without Outbound".

DIFFERENCE columns (S:U) = inbound - outbound, on the last row of each group
and on every unmatched row: MISSING (positive) in black, EXCESS (negative)
in red, zero shown as "-".

Usage
-----
    python reconcile.py "Raw Data.xlsx"            (or drag the file onto Run_Reconcile.bat)
    python reconcile.py                            (opens a file picker)
Output: "<input name> - Reconciled.xlsx" next to the input file.
"""

import collections
import datetime
import difflib
import os
import re
import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ---- column positions in the sheet (1-based) ---------------------------------
C_SNO, C_M2, C_PRE, C_M1, C_DATE, C_HS, C_RT, C_DESC, C_COG = range(1, 10)
C_IN_QTY, C_IN_WT, C_IN_VAL = 10, 11, 12
C_OUT_QTY, C_OUT_WT, C_OUT_VAL = 13, 14, 15
C_DIFF_QTY, C_DIFF_WT, C_DIFF_VAL = 19, 20, 21
C_DUTY = 22
C_REMARK, C_GROUP, C_BASIS, C_DESC_MATCH = 23, 24, 25, 26
LAST_DATA_COL = 22

# Rule 4: share of description words that must be exceeded for a match.
# 0 = only completely different descriptions are blocked (at least one word in common).
DESC_MIN_MATCH = 0.0
DESC_IGNORE = set("""AS PER INV INVOICE REF RF BE BOE NO NOS DEC STC CTNR CNTR CTR CONTAINER BAGS BAG
PKGS PKG PLTS PLT PALLETS PALLET PAILS PAIL OF AND THE IN FOR WITH TO ON BY NET WEIGHT KGS KG PCS
ATTACHED DOCUMENT DOCUMENTS DETAILS GRADE SAMPLES SAMPLE FCL FT LCL CODE AWB HWAB PART OTHERS OTHER
THAN""".split())
DESC_SYNONYMS = {"MB": "MASTERBATCH", "ME": "MASTERBATCH", "COLOR": "COLOUR", "COLOURS": "COLOUR"}

DATE_WINDOWS = [0, 1, 3, 7, 15, 30, 60, 120, 365, 100000]   # days
SUBSET_MAX_CANDIDATES = 25
SUBSET_MAX_LINES = 20
SUBSET_MAX_STEPS = 200000

# DIFFERENCE columns: positive (MISSING) black, negative (EXCESS) red, zero "-"
DIFF_FORMAT = '_-* #,##0.00_-;[Red]\\-* #,##0.00_-;_-* "-"??_-;_-@_-'

REMARK_OUT_ONLY = "Outbound without Inbound"
REMARK_IN_ONLY = "Inbound without Outbound"


# ---- helpers ------------------------------------------------------------------
def to_number(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def to_datetime(v):
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, datetime.date):
        return datetime.datetime(v.year, v.month, v.day)
    if isinstance(v, (int, float)):            # Excel serial date
        return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(v))
    s = str(v or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def hs_key(v):
    s = str(v if v is not None else "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def cog_key(v):
    # "GERMANY (Deutschland)" and "GERMANY" are the same country of origin
    return str(v or "").split("(")[0].strip().upper()


def qty_key(q):
    return round((q or 0.0) * 1000)


def desc_words(desc):
    words = set()
    for w in re.split(r"[^A-Z0-9]+", str(desc or "").upper().replace("_X000D_", " ")):
        if len(w) < 2 or any(ch.isdigit() for ch in w) or w in DESC_IGNORE:
            continue                                   # skip numbers, codes, packing words
        words.add(DESC_SYNONYMS.get(w, w))
    return words


def _word_found(word, others, others_joined):
    if word in others:
        return True
    if len(word) >= 4 and word in others_joined:       # MASTER BATCH vs MASTERBATCH
        return True
    for o in others:
        if len(word) >= 3 and len(o) >= 3 and (word.startswith(o) or o.startswith(word)):
            return True                                # INK / INKS, MAGENT / MAGENTA
        if len(word) >= 5 and len(o) >= 5 and difflib.SequenceMatcher(None, word, o).ratio() >= 0.8:
            return True                                # small typos: ADDITVE / ADDITIVE
    return False


def desc_similarity(d1, d2):
    """Share (0..1) of description words that agree; None if either has no usable words."""
    a, b = desc_words(d1), desc_words(d2)
    if not a or not b:
        return None
    a_joined = re.sub(r"[^A-Z]", "", str(d1).upper())
    b_joined = re.sub(r"[^A-Z]", "", str(d2).upper())
    return max(sum(_word_found(w, b, b_joined) for w in a) / len(a),
               sum(_word_found(w, a, a_joined) for w in b) / len(b))


def outbound_is_after(out, inb):
    """Rule 2: outbound on the same date as, or after, the inbound."""
    if out["dt"].time() == datetime.time(0) or inb["dt"].time() == datetime.time(0):
        return out["dt"].date() >= inb["dt"].date()       # no time recorded -> compare dates
    return out["dt"] >= inb["dt"]


def find_subset(cands, target):
    """Earliest-first search for outbound lines whose quantities sum exactly to target."""
    cands = cands[:SUBSET_MAX_CANDIDATES]
    suffix = [0] * (len(cands) + 1)
    for i in range(len(cands) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + cands[i][0]
    result, steps = [None], [0]

    def dfs(i, remaining, chosen):
        if result[0] is not None:
            return
        steps[0] += 1
        if steps[0] > SUBSET_MAX_STEPS:
            return
        if remaining == 0:
            result[0] = list(chosen)
            return
        if i >= len(cands) or remaining < 0 or suffix[i] < remaining or len(chosen) >= SUBSET_MAX_LINES:
            return
        chosen.append(cands[i])
        dfs(i + 1, remaining - cands[i][0], chosen)
        chosen.pop()
        dfs(i + 1, remaining, chosen)

    if target > 0:
        dfs(0, target, [])
    return result[0]


# ---- reading ------------------------------------------------------------------
def find_header_row(ws):
    for r in range(1, 30):
        if str(ws.cell(r, C_SNO).value or "").strip().upper().replace(" ", "") in ("S.NO", "SNO", "S.NO."):
            return r
    raise ValueError("Could not find the header row ('S.No' in column A).")


def read_rows(ws, cached_values, header_row):
    """cached_values: {(row, col): last calculated value} of the same sheet."""

    def cell_value(r, c):
        v = ws.cell(r, c).value
        # Formulas pointing at another workbook (e.g. =VLOOKUP(..,[1]M2!..)) cannot be
        # carried over, so the last calculated value is written instead.
        if isinstance(v, str) and v.startswith("=") and "[" in v:
            return cached_values.get((r, c))
        return v

    rows = []
    r = header_row + 1
    while r <= ws.max_row:
        first = ws.cell(r, C_SNO).value
        if isinstance(first, str) and "TOTAL" in first.upper():
            break
        in_qty = to_number(ws.cell(r, C_IN_QTY).value)
        out_qty = to_number(ws.cell(r, C_OUT_QTY).value)
        if first is not None and (in_qty is not None or out_qty is not None):
            dt = to_datetime(ws.cell(r, C_DATE).value)
            if dt is None:
                raise ValueError(f"Row {r}: could not read the DATE value {ws.cell(r, C_DATE).value!r}")
            is_in = in_qty is not None
            rows.append(dict(
                src_row=r,
                inbound=is_in,
                dt=dt,
                hs=hs_key(ws.cell(r, C_HS).value),
                cog=cog_key(ws.cell(r, C_COG).value),
                qty=in_qty if is_in else out_qty,
                m1=str(ws.cell(r, C_M1).value or "").strip(),
                m2=str(ws.cell(r, C_M2).value or "").strip(),
                desc=str(ws.cell(r, C_DESC).value or ""),
                cells=[(cell_value(r, c), ws.cell(r, c)._style) for c in range(1, LAST_DATA_COL + 1)],
                height=ws.row_dimensions[r].height,
            ))
        r += 1
    return rows, r


# ---- matching -----------------------------------------------------------------
def reconcile(rows):
    inbounds = sorted([x for x in rows if x["inbound"]], key=lambda x: (x["dt"], x["src_row"]))
    outbounds = collections.defaultdict(list)
    for x in rows:
        if not x["inbound"]:
            x["refs"] = set(re.findall(r"\d{9,}", x["desc"]))
            outbounds[(x["hs"], x["cog"])].append(x)
    for k in outbounds:
        outbounds[k].sort(key=lambda x: (x["dt"], x["src_row"]))

    used = set()
    groups = []          # list of (inbound rows, outbound rows, basis)
    assigned = set()

    sim_cache = {}

    def same_item(in_rows, o):
        """Rule 4: outbound description is not completely different from the inbound lot."""
        scores = []
        for x in in_rows:
            key = (id(x), id(o))
            if key not in sim_cache:
                sim_cache[key] = desc_similarity(x["desc"], o["desc"])
            scores.append(sim_cache[key])
        known = [s for s in scores if s is not None]
        return not known or max(known) > DESC_MIN_MATCH

    def candidates(first_in, window, ref_bills=None, in_rows=None):
        in_rows = in_rows or [first_in]
        return [(qty_key(o["qty"]), o) for o in outbounds[(first_in["hs"], first_in["cog"])]
                if id(o) not in used
                and outbound_is_after(o, first_in)
                and (o["dt"].date() - first_in["dt"].date()).days <= window
                and (ref_bills is None or o["refs"] & ref_bills)
                and same_item(in_rows, o)]

    def commit(in_rows, out_rows, basis):
        groups.append((in_rows, out_rows, basis))
        for x in in_rows:
            assigned.add(id(x))
        for o in out_rows:
            used.add(id(o))

    def open_bills():
        bills = collections.defaultdict(list)
        for x in inbounds:
            if id(x) not in assigned:
                bills[(x["m1"], x["hs"], x["cog"])].append(x)
        return sorted(bills.values(), key=lambda b: (min(x["dt"] for x in b), b[0]["src_row"]))

    def exact_pass(window, by_reference, basis):
        for x in inbounds:                                     # single inbound line
            if id(x) in assigned:
                continue
            refs = {x["m1"], x["m2"]} - {""} if by_reference else None
            sub = find_subset(candidates(x, window, refs), qty_key(x["qty"]))
            if sub:
                commit([x], [o for _, o in sub], basis)
        for bill in open_bills():                              # whole inbound bill (same HS + COG)
            if len(bill) < 2:
                continue
            first = min(bill, key=lambda x: x["dt"])
            refs = ({first["m1"]} | {x["m2"] for x in bill}) - {""} if by_reference else None
            sub = find_subset(candidates(first, window, refs, bill), sum(qty_key(x["qty"]) for x in bill))
            if sub:
                commit(bill, [o for _, o in sub], basis)

    exact_pass(DATE_WINDOWS[-1], True, "Bill reference + exact qty")
    for w in DATE_WINDOWS:
        exact_pass(w, False, "Exact qty")

    for bill in open_bills():                                  # leftovers quoting the bill no.
        first = min(bill, key=lambda x: x["dt"])
        refs = ({first["m1"]} | {x["m2"] for x in bill}) - {""}
        c = candidates(first, DATE_WINDOWS[-1], refs, bill)
        if c:
            commit(bill, [o for _, o in c], "Bill reference (qty differs)")
    for x in inbounds:                                         # leftovers: next outbound
        if id(x) in assigned:
            continue
        c = candidates(x, DATE_WINDOWS[-1])
        if c:
            commit([x], [c[0][1]], "Next outbound (qty differs)")

    un_in = [x for x in inbounds if id(x) not in assigned]
    un_out = sorted([o for lst in outbounds.values() for o in lst if id(o) not in used],
                    key=lambda o: (o["cog"], o["dt"]))
    un_in.sort(key=lambda x: (x["cog"], x["dt"]))
    groups.sort(key=lambda g: (g[0][0]["cog"], min(x["dt"] for x in g[0]), g[0][0]["src_row"]))
    return groups, un_out, un_in


# ---- writing ------------------------------------------------------------------
def write_output(wb, ws, header_row, data_end_row, groups, un_out, un_in, out_path):
    old_last = ws.max_row
    # Remember the style of the old GRAND TOTAL row so the new one looks the same
    total_style = [ws.cell(data_end_row, c)._style for c in range(1, ws.max_column + 1)] \
        if data_end_row <= old_last else None
    for mr in list(ws.merged_cells.ranges):
        if mr.min_row > header_row:
            ws.unmerge_cells(str(mr))
    ws.delete_rows(header_row + 1, old_last - header_row)

    hdr_style = ws.cell(header_row, C_DUTY)._style
    for col, title in ((C_REMARK, "REMARKS"), (C_GROUP, "MATCH GROUP"), (C_BASIS, "MATCH BASIS"),
                       (C_DESC_MATCH, "DESC MATCH %")):
        ws.cell(header_row, col).value = title
        ws.cell(header_row, col)._style = hdr_style
    ws.column_dimensions["W"].width = 26
    ws.column_dimensions["X"].width = 13
    ws.column_dimensions["Y"].width = 28
    ws.column_dimensions["Z"].width = 14

    r = header_row + 1
    first_data = r
    pre_formula = re.compile(r"B\d+")
    diff_font = Font(bold=True, color="FF000000")

    def put(x, remark=None, group_no=None, basis=None):
        nonlocal r
        for c, (val, style) in enumerate(x["cells"], start=1):
            cell = ws.cell(r, c)
            if c in (C_DIFF_QTY, C_DIFF_WT, C_DIFF_VAL):
                val = None                              # recalculated per group
            if c == C_PRE and isinstance(val, str) and val.startswith("="):
                val = pre_formula.sub(f"B{r}", val, count=1)
            cell.value = val
            cell._style = style
        if x["height"]:
            ws.row_dimensions[r].height = x["height"]
        if remark:
            ws.cell(r, C_REMARK).value = remark
        if group_no is not None:
            ws.cell(r, C_GROUP).value = group_no
            ws.cell(r, C_BASIS).value = basis
        r += 1

    # DIFFERENCE columns (S:U) = inbound - outbound.
    # Positive = MISSING (black), negative = EXCESS (red), zero = "-".
    cached = {}          # cell ref -> calculated value, so the figures show even before Excel recalculates
    col_totals = collections.defaultdict(float)

    def diff_cell(row, dcol, formula, value):
        value = round(value, 2) + 0.0
        cell = ws.cell(row, dcol)
        cell.value = f"=ROUND({formula},2)"
        cell.number_format = DIFF_FORMAT
        cell.font = diff_font
        cached[cell.coordinate] = value
        col_totals[dcol] += value

    def amounts(rows, first_col):
        return [sum(to_number(x["cells"][first_col + k - 1][0]) or 0.0 for x in rows) for k in range(3)]

    def add_totals(rows):
        for x in rows:
            for c in range(C_IN_QTY, C_OUT_VAL + 1):
                col_totals[c] += to_number(x["cells"][c - 1][0]) or 0.0

    unbalanced = 0
    for n, (ins, outs, basis) in enumerate(groups, start=1):
        start = r
        for x in sorted(ins, key=lambda x: (x["dt"], x["src_row"])):
            put(x, group_no=n, basis=basis)
        in_end = r - 1
        for o in sorted(outs, key=lambda o: (o["dt"], o["src_row"])):
            put(o, group_no=n, basis=basis)
            scores = [s for s in (desc_similarity(x["desc"], o["desc"]) for x in ins) if s is not None]
            pct = ws.cell(r - 1, C_DESC_MATCH)
            pct.value = round(max(scores), 2) if scores else "n/a"
            pct.number_format = "0%"
        end = r - 1
        in_amt, out_amt = amounts(ins, C_IN_QTY), amounts(outs, C_OUT_QTY)
        for k, (dcol, icol, ocol) in enumerate(((C_DIFF_QTY, "J", "M"), (C_DIFF_WT, "K", "N"), (C_DIFF_VAL, "L", "O"))):
            diff_cell(end, dcol, f"SUM({icol}{start}:{icol}{in_end})-SUM({ocol}{in_end + 1}:{ocol}{end})",
                      in_amt[k] - out_amt[k])
        add_totals(ins + outs)
        if qty_key(sum(x["qty"] for x in ins)) != qty_key(sum(o["qty"] for o in outs)):
            unbalanced += 1

    red = PatternFill("solid", fgColor="FFC7CE")
    for x, remark in [(x, REMARK_OUT_ONLY) for x in un_out] + [(x, REMARK_IN_ONLY) for x in un_in]:
        put(x, remark=remark)
        row = r - 1
        ws.cell(row, C_REMARK).fill = red
        in_amt, out_amt = amounts([x], C_IN_QTY), amounts([x], C_OUT_QTY)
        for k, (dcol, icol, ocol) in enumerate(((C_DIFF_QTY, "J", "M"), (C_DIFF_WT, "K", "N"), (C_DIFF_VAL, "L", "O"))):
            diff_cell(row, dcol, f"N({icol}{row})-N({ocol}{row})", in_amt[k] - out_amt[k])
        add_totals([x])
    last_data = r - 1

    total_row = r + 1
    if total_style:
        for c, st in enumerate(total_style, start=1):
            ws.cell(total_row, c)._style = st
    ws.cell(total_row, 1).value = "GRAND TOTAL"
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=9)
    for c in range(C_IN_QTY, C_DIFF_VAL + 1):
        cell = ws.cell(total_row, c)
        L = cell.column_letter
        cell.value = f"=SUM({L}{first_data}:{L}{last_data})"
        cached[cell.coordinate] = round(col_totals[c], 2) + 0.0
        if c >= C_DIFF_QTY:
            cell.number_format = DIFF_FORMAT
    ratio = ws.cell(total_row + 4, C_DIFF_WT)
    ratio.value = f"=T{total_row}/K{total_row}"
    if col_totals[C_IN_WT]:
        cached[ratio.coordinate] = col_totals[C_DIFF_WT] / col_totals[C_IN_WT]

    ws.auto_filter.ref = f"A{header_row}:Z{last_data}"
    ws.freeze_panes = ws.cell(header_row + 1, 1)

    # summary sheet
    if "SUMMARY" in wb.sheetnames:
        del wb["SUMMARY"]
    sm = wb.create_sheet("SUMMARY")
    basis_count = collections.Counter(b for _, _, b in groups)
    lines = [
        ("Inbound to Outbound Reconciliation", None),
        ("Generated on", datetime.datetime.now().strftime("%d-%m-%Y %H:%M")),
        (None, None),
        ("Matched groups", len(groups)),
        ("  of which quantity fully balanced", len(groups) - unbalanced),
        ("  of which quantity differs (see DIFFERENCE columns)", unbalanced),
    ] + [(f"  basis: {k}", v) for k, v in sorted(basis_count.items())] + [
        ("Inbound lines matched", sum(len(g[0]) for g in groups)),
        ("Outbound lines matched", sum(len(g[1]) for g in groups)),
        (REMARK_OUT_ONLY, len(un_out)),
        (REMARK_IN_ONLY, len(un_in)),
        (None, None),
        ("Rules: inbound first; outbound on/after inbound date; same HS Code and COG;", None),
        ("       description must not be completely different (at least one word in common).", None),
    ]
    for i, (k, v) in enumerate(lines, start=1):
        sm.cell(i, 1).value = k
        sm.cell(i, 2).value = v
    sm["A1"].font = Font(bold=True, size=13)
    sm.column_dimensions["A"].width = 58
    sm.column_dimensions["B"].width = 18
    for row in sm.iter_rows(min_col=2, max_col=2):
        for c in row:
            c.alignment = Alignment(horizontal="right")

    wb.active = wb.sheetnames.index(ws.title)
    wb.save(out_path)
    store_cached_values(out_path, wb.sheetnames.index(ws.title) + 1, cached)
    return unbalanced


def store_cached_values(path, sheet_no, cached):
    """openpyxl saves formulas without results; write the results in so the
    DIFFERENCE figures are visible in any viewer, not only after Excel recalculates."""
    import shutil
    import tempfile
    import zipfile
    name = f"xl/worksheets/sheet{sheet_no}.xml"
    pattern = re.compile(r'(<c r="([A-Z]+\d+)"[^>]*>)(<f>[^<]*</f>)<v\s*>\s*</v>|(<c r="([A-Z]+\d+)"[^>]*>)(<f>[^<]*</f>)<v\s*/>')

    def fill(m):
        open_tag, ref, f = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), m.group(6))
        if ref not in cached:
            return m.group(0)
        return f"{open_tag}{f}<v>{repr(float(cached[ref]))}</v>"

    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == name:
                data = pattern.sub(fill, data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)


# ---- entry point --------------------------------------------------------------
def pick_file():
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Select the RAW DATA Excel file",
                                          filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")])
        root.destroy()
        return path
    except Exception:
        return input("Enter the full path of the raw data Excel file: ").strip().strip('"')


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else pick_file()
    if not in_path:
        print("No file selected.")
        return 1
    if not os.path.isfile(in_path):
        print(f"File not found: {in_path}")
        return 1
    base, ext = os.path.splitext(in_path)
    out_path = sys.argv[2] if len(sys.argv) > 2 else f"{base} - Reconciled{ext if ext.lower() in ('.xlsx', '.xlsm') else '.xlsx'}"

    print(f"Reading   : {in_path}")
    wb = openpyxl.load_workbook(in_path, keep_vba=in_path.lower().endswith(".xlsm"), keep_links=False)
    ws = wb.worksheets[0]
    values_wb = openpyxl.load_workbook(in_path, data_only=True, read_only=True)
    cached_values = {(r, c): v for r, row in enumerate(values_wb.worksheets[0].iter_rows(values_only=True), start=1)
                     for c, v in enumerate(row, start=1) if v is not None}
    values_wb.close()
    header_row = find_header_row(ws)
    rows, data_end_row = read_rows(ws, cached_values, header_row)
    n_in = sum(1 for x in rows if x["inbound"])
    print(f"Rows read : {len(rows)}  (inbound {n_in}, outbound {len(rows) - n_in})")

    print("Matching  : ...")
    groups, un_out, un_in = reconcile(rows)

    print(f"Writing   : {out_path}")
    try:
        unbalanced = write_output(wb, ws, header_row, data_end_row, groups, un_out, un_in, out_path)
    except PermissionError:
        print("\nERROR: cannot save the output file. Close it in Excel and run again.")
        return 1

    print()
    print(f"Matched groups             : {len(groups)}  ({unbalanced} with a quantity difference)")
    print(f"{REMARK_OUT_ONLY:27s}: {len(un_out)}")
    print(f"{REMARK_IN_ONLY:27s}: {len(un_in)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
