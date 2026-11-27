"""Quick CMA: statements in, CMA workbook + PDF out, with only the loan inputs asked.

Everything else is decided automatically: client name and proprietor from the statement heading,
years (actual years from the file, estimated years up to the current financial year, then projected
years), bank-norm defaults, and a tally fix where one line of the client's balance sheet is counted twice.
"""
import datetime as dt
import os
import re

from core.models import CMAProject, YearDef, MAX_YEARS
from analysis.layout import SINGLE_HEADS
from analysis.engine import compute
from analysis import validator2 as V


def _f(v):
    return format(int(round(v)), ",")


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', " ", name or "Client").strip() or "Client"


def read_heading(paths):
    """Client name, proprietor/partner, address and place from the top rows of the first Excel sheet."""
    info = {}
    for p in paths:
        if not p.lower().endswith((".xlsx", ".xlsm", ".xls")):
            continue
        try:
            import openpyxl
            wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
            for ws in wb.worksheets:
                if ws.sheet_state != "visible":
                    continue
                texts = []
                for row in ws.iter_rows(min_row=1, max_row=6, max_col=10, values_only=True):
                    t = [str(v).strip() for v in row if isinstance(v, str) and str(v).strip()]
                    if t:
                        texts.append(t[0])
                for t in texts:
                    lo = t.lower()
                    if re.search(r"account|balance sheet|particulars|year ended|as on|as at", lo):
                        break
                    m = re.match(r"(prop(rietor|rietress)?|partners?)\s*[:.\-]\s*(.+)", t, re.I)
                    if m:
                        info.setdefault("signatory", m.group(3).strip())
                        info.setdefault("title", "Partner" if m.group(1).lower().startswith("partner")
                                        else "Proprietor")
                    elif "name" not in info:
                        info["name"] = re.sub(r"^m/s\.?\s*", "", t, flags=re.I).strip()
                    elif "address" not in info:
                        info["address"] = t
                for row in ws.iter_rows(min_row=1, max_row=120, max_col=12, values_only=True):
                    for v in row:
                        if isinstance(v, str):
                            m = re.match(r"\s*place\s*[:.\-]\s*(\S.*)", v, re.I)
                            if m and "place" not in info:
                                info["place"] = m.group(1).strip()
                if "name" in info:
                    return info
        except Exception:
            continue
    if paths:
        info["name"] = re.sub(r"[_\-]+", " ", os.path.splitext(os.path.basename(paths[0]))[0]).strip()
    return info


def current_fy(today=None):
    d = today or dt.date.today()
    return d.year + 1 if d.month >= 4 else d.year      # FY named by its ending year


def plan_years(actual, provisional, projected=2, today=None, audited=None):
    """Actual years from the file, Estimated up to the current FY, then Projected."""
    actual = sorted(set(actual))
    years = [YearDef(fy, "Provisional" if fy in provisional else ("Audited" if fy in (audited or ()) else "Actual"))
             for fy in actual]
    fy = actual[-1] + 1
    while fy <= current_fy(today):
        years.append(YearDef(fy, "Estimated"))
        fy += 1
    if fy == actual[-1] + 1:                             # nothing estimated: first new year is the estimate
        years.append(YearDef(fy, "Estimated"))
        fy += 1
    for _ in range(projected):
        years.append(YearDef(fy, "Projected"))
        fy += 1
    # keep within the format: drop the oldest actual years first, at least one actual kept
    while len(years) > MAX_YEARS and sum(1 for y in years if y.from_statement) > 1:
        years.pop(0)
    return years[:MAX_YEARS]


ASSET_PREFER = ("bank_balance", "cash_in_hand")


def fix_tally(project, log):
    """Where a statement year's difference equals one line exactly, that line is counted twice: ignore it.
    Returns the years still not tallying as [(fy, difference)]."""
    left = []
    for _ in range(3):
        r = compute(project)
        bad = [(y["fy"], y["difference"]) for y in r.years if y["from_statement"] and abs(y["difference"]) >= 1]
        if not bad:
            return []
        changed = False
        left = []
        for fy, d in bad:
            side = 1 if d < 0 else 0                    # assets too high -> look on the assets side
            cands = [s for s in project.source_lines if s.year == fy and s.statement == "BS" and s.side == side
                     and s.head not in ("ignore", "", "_reported_net_profit", "capital", "drawings")
                     and abs(abs(d) - s.amount) < 1]
            cands.sort(key=lambda s: (s.head not in ASSET_PREFER,))
            if cands:
                s = cands[0]
                s.head, s.note = "ignore", "Quick CMA: removed - the client's balance sheet counts it twice"
                log("FY %d-%02d: the client's balance sheet differs by Rs %s, exactly the line '%s'. That line "
                    "is counted twice and has been left out. Please confirm." % (fy - 1, fy % 100, _f(abs(d)),
                                                                                 s.label.strip()))
                changed = True
            else:
                left.append((fy, d))
        project.build_lines_from_sources(SINGLE_HEADS)
        if not changed:
            break
    return left


def carry_difference(project, left, log):
    """Only on the user's say-so: carry an unexplained difference as a visible line."""
    from core.models import SourceLine
    for fy, d in left:
        if d < 0:     # assets exceed liabilities
            head, side = "other_cl", 0
        else:
            head, side = "loans_advances", 1
        project.source_lines.append(SourceLine(year=fy, statement="BS", label="Difference in client's balance sheet "
                                               "(to be checked)", amount=abs(d), head=head, confidence=100,
                                               source="Quick CMA", note="carried on user's instruction", side=side))
        log("FY %d-%02d: difference of Rs %s carried as 'Difference in client's balance sheet (to be checked)'."
            % (fy - 1, fy % 100, _f(abs(d))))
    project.build_lines_from_sources(SINGLE_HEADS)


def build(paths, opts, settings=None, log=print, use_ai=None):
    """opts: client_name, cc_limit, cc_rate, tl_amount, tl_rate, tl_months, tl_method, projected, unit.
    Returns (project, left) where left = statement years that still do not tally."""
    from extraction.reader import read_files
    settings = settings or {}
    if use_ai is None:
        use_ai = bool(settings.get("use_ai_for_pdf"))
    lines = read_files(paths, settings, use_ai=use_ai, log=log)
    if not lines:
        raise ValueError("Nothing could be read from the file(s).")
    p = CMAProject()
    p.source_lines = lines
    actual = sorted({s.year for s in lines if s.year})
    prov = {s.year for s in lines if getattr(s, "year_kind", "") == "Provisional"}
    aud = {s.year for s in lines if getattr(s, "year_kind", "") == "Audited"}
    p.years = plan_years(actual, prov, int(opts.get("projected", 2)), audited=aud)
    from core.models import STATEMENT_KINDS
    for y in p.years:                        # year types the user set earlier for this client
        k = (opts.get("kinds") or {}).get(y.fy)
        if y.from_statement and k in STATEMENT_KINDS:
            y.kind = k
    keep = {y.fy for y in p.years}
    p.source_lines = [s for s in lines if s.year in keep]
    head = read_heading(paths)
    it = p.intake
    it.client_name = opts.get("client_name") or head.get("name", "Client")
    it.signatory_name = head.get("signatory", "")
    it.signatory_title = head.get("title", "Proprietor")
    it.address = head.get("address", "")
    it.place = head.get("place", "")
    heads = {s.head for s in lines}
    if "share_capital" in heads:
        it.constitution, it.signatory_title = "Private Limited Company", "Director"
    elif it.signatory_title == "Partner":
        it.constitution = "Partnership Firm"
    if any(s.head == "wages" or s.head == "power_fuel" for s in lines) and \
            any(re.search(r"raw material|manufactur", s.label, re.I) for s in lines):
        it.nature = "Manufacturing"
    cc = float(opts.get("cc_limit") or 0)
    it.has_cc = cc > 0
    it.cc_limit = cc
    it.cc_rate = (opts.get("cc_rate") or 10) / 100.0
    tl = float(opts.get("tl_amount") or 0)
    it.has_tl = tl > 0
    if it.has_tl:
        it.tl_amount = tl
        it.tl_rate = (opts.get("tl_rate") or 10) / 100.0
        it.tl_tenure_months = int(opts.get("tl_months") or 60)
        it.tl_method = opts.get("tl_method") or "Equal EMI"
        it.tl_use = opts.get("tl_use") or "Capex"
    it.unit = opts.get("unit") or "Actual"
    p.build_lines_from_sources(SINGLE_HEADS)
    log("Read %s: %d lines; years %s." % (it.client_name, len(p.source_lines),
                                          ", ".join("%s %s" % (y.label, y.kind) for y in p.years)))
    left = fix_tally(p, log)
    return p, left


def fit(project, settings=None, log=print, turnover=True, dscr=True):
    """Turnover to the green band, DSCR into the bank's range, positive cash (statement years untouched)."""
    from analysis.engine import fit_dscr, fit_turnover, fix_cash, fix_ratios
    sd = (settings or {}).get("defaults")
    notes = fit_turnover(project, sd, log=log) if turnover else []
    if dscr:
        notes += fit_dscr(project, sd, log=log)
    else:
        notes += fix_cash(project, sd, log=log)
    notes += fix_ratios(project, sd, log=log)
    from analysis.engine import tidy_creditors
    if notes:
        notes += tidy_creditors(project, sd, log=log)
        notes += fix_ratios(project, sd, log=log)
        notes += fix_cash(project, sd, log=log)
    return notes


def export(project, out_folder, settings=None, log=print, pdf=True, xlsx_path=None, save_json=True):
    """Workbook (+ PDF) into out_folder. Returns (xlsx, pdf_or_None, result, checks)."""
    from reports.cma_writer import generate_workbook
    from core.audit_trail import TRAIL
    settings = settings or {}
    r = compute(project, settings.get("defaults"))
    checks = V.validate(project, r)
    if V.has_errors(checks):
        raise ValueError("\n".join(m for lv, m in checks if lv == V.ERROR))
    os.makedirs(out_folder, exist_ok=True)
    base = "CMA data - %s" % safe(project.intake.client_name)
    xlsx = xlsx_path or os.path.join(out_folder, base + ".xlsx")
    TRAIL.log("Quick CMA export", xlsx)
    generate_workbook(project, r, xlsx, settings, TRAIL.rows())
    log("Excel: " + xlsx)
    out_pdf = None
    if pdf:
        from reports import pdf_export
        try:
            out_pdf, rep = pdf_export.export_pdf(xlsx, os.path.join(out_folder, base + ".pdf"), log=lambda *a: None)
            log("PDF: %s (%d pages)" % (out_pdf, rep["pages"]))
        except pdf_export.NoConverter as e:
            log("PDF not made (%s). Open the Excel file and use File > Save as > PDF." % e)
        except Exception as e:
            log("PDF not made: %s. Open the Excel file and use File > Save as > PDF." % e)
    if save_json:
        try:
            project.save(os.path.join(out_folder, safe(project.intake.client_name) + ".cma.json"))
        except OSError:
            pass
    return xlsx, out_pdf, r, checks


def capacity_note(project, result, settings=None):
    """When DSCR is above the maximum: explain, and give the largest term loan the cash flows can service."""
    import copy
    from analysis.engine import suggest_tl_amount
    from core.models import norm
    sd = (settings or {}).get("defaults")
    it = project.intake
    dmax, dmin = norm(it, "dscr_max", sd), norm(it, "dscr_min", sd)
    ds = [y["dscr"] for y in result.future if y.get("dscr") is not None]
    if not ds or max(ds) <= dmax:
        return []
    p = copy.deepcopy(project)
    if not p.intake.has_tl:
        p.intake.has_tl, p.intake.tl_amount = True, 500000
        p.intake.tl_rate = p.intake.tl_rate or 0.10
    cap = suggest_tl_amount(p, sd) or 0
    out = ["DSCR is above the maximum of %.2f: the projected cash accruals are much larger than the loan "
           "repayments, so repayment capacity is not a concern. Banks insist only on the minimum (%.2f)." % (dmax, dmin)]
    if cap:
        out.append("Largest term loan these cash flows can service with DSCR of at least %.2f in every year: "
                   "about Rs %s (same rate and tenure). Enter the actual loan amount the client needs; do not "
                   "raise the loan only to bring DSCR down." % (dmin, _f(cap)))
    out.append("The first (estimated) year always shows a higher DSCR because the loan runs only part of that year.")
    return out


def summary(result):
    """Plain-language bank test lines."""
    out = []
    for y in result.years:
        if y["from_statement"]:
            continue
        bits = ["%s %s:" % (y["label"], y["kind"]), "Sales Rs %s" % _f(y["sales"])]
        if y.get("drawing_power") is not None and y.get("cc_limit"):
            bits.append("Drawing power Rs %s vs limit Rs %s %s" % (
                _f(y["drawing_power"]), _f(y["cc_limit"]), "PASS" if y["drawing_power"] >= y["cc_limit"] else "FAIL"))
        if y.get("dscr") is not None:
            bits.append("DSCR %.2f" % y["dscr"])
        if y.get("turnover_multiple") is not None:
            bits.append("Turnover %.1fx %s" % (y["turnover_multiple"], y.get("turnover_status", "")))
        out.append("  ".join(bits))
    s = result.summary or {}
    if s.get("dscr_avg") is not None:
        out.append("Average DSCR %.2f (%s)" % (s["dscr_avg"], s.get("dscr_status", "")))
    return out
