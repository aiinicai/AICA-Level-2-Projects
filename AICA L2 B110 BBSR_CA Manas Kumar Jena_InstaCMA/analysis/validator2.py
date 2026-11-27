"""Checks and delivery gate for InstaCMA (ERROR blocks export, WARN is reported)."""
from core.models import STATEMENT_KINDS, MAX_YEARS

ERROR, WARN, OK = "ERROR", "WARN", "OK"


def _f(v):
    return format(int(round(v)), ",")


def validate(project, result):
    out = []
    years = project.year_list()
    if not years:
        return [(ERROR, "No years defined - set the years on the Client & Years page.")]
    if len(years) > MAX_YEARS:
        out.append((ERROR, "At most %d years can be shown in the CMA format." % MAX_YEARS))
    fys = [y.fy for y in years]
    if fys != list(range(fys[0], fys[0] + len(fys))):
        out.append((ERROR, "Years must be consecutive financial years."))
    if not years[0].from_statement:
        out.append((ERROR, "The first year must be an Audited, Actual or Provisional year."))
    seen_tool = False
    for y in years:
        if not y.from_statement:
            seen_tool = True
        elif seen_tool:
            out.append((ERROR, "FY %s: a statement year cannot follow a tool-built year." % y.label))
    if not result or not result.years:
        return out + [(ERROR, "Nothing calculated yet.")]
    prev = None
    for y in result.years:
        if y["from_statement"]:
            d = y["difference"]
            if abs(d) >= 1:
                out.append((ERROR, "FY %s (%s): liabilities Rs %s and assets Rs %s differ by Rs %s. Check the Review "
                                   "page (a loan split across lines, bank and cash counted twice, a sub-total not "
                                   "ignored). Never plug a difference." % (
                                       y["label"], y["kind"], _f(y["total_liabilities"]), _f(y["total_assets"]), _f(d))))
            else:
                out.append((OK, "FY %s (%s): balance sheet tallies at Rs %s." % (y["label"], y["kind"],
                                                                                 _f(y["total_assets"]))))
            rep = project.reported_net_profit(y["fy"])
            if rep is not None:
                if abs(rep - y["pat"]) >= 1:
                    out.append((WARN, "FY %s: net profit from the mapped lines Rs %s differs from the reported net "
                                      "profit Rs %s." % (y["label"], _f(y["pat"]), _f(rep))))
                else:
                    out.append((OK, "FY %s: net profit agrees with the statement (Rs %s)." % (y["label"], _f(rep))))
            if prev is not None and not project.intake.is_company and prev.get("cap_close") is not None:
                gap = y["cap_open"] - prev["cap_close"]
                if abs(gap) >= 1:
                    out.append((WARN, "FY %s: opening capital Rs %s (worked back from closing capital, profit and "
                                      "drawings) differs from the previous closing capital Rs %s by Rs %s. Check "
                                      "drawings / capital introduced." % (y["label"], _f(y["cap_open"]),
                                                                          _f(prev["cap_close"]), _f(gap))))
            if y["sales"] <= 0:
                out.append((WARN, "FY %s: no sales mapped." % y["label"]))
            bs_stock = sum(ln.v(y["fy"]) for ln in project.lines if ln.head == "stock")
            if bs_stock and abs(bs_stock - y["closing_stock"]) >= 1:
                out.append((WARN, "FY %s: stock in the balance sheet Rs %s differs from closing stock in the P&L Rs %s; "
                                  "the P&L figure is used." % (y["label"], _f(bs_stock), _f(y["closing_stock"]))))
        else:
            if abs(y["difference"]) >= 0.5:
                out.append((ERROR, "FY %s: projected balance sheet does not balance." % y["label"]))
            if prev is not None and abs(y["opening_stock"] - prev["closing_stock"]) >= 0.5:
                out.append((ERROR, "FY %s: opening stock differs from previous closing stock." % y["label"]))
        prev = y
    if result.future and all(abs(y["difference"]) < 0.5 for y in result.future if not y["from_statement"]):
        out.append((OK, "Estimated / projected balance sheets balance; opening = previous closing."))
    if result.summary.get("tl_amount", 0) > 0:
        out.append((OK, "Term loan: principal repaid equals the loan.") if result.summary.get("tl_principal_check")
                   else (ERROR, "Term loan schedule does not clear the loan."))
    return out


def has_errors(checks):
    return any(lv == ERROR for lv, _ in checks)
