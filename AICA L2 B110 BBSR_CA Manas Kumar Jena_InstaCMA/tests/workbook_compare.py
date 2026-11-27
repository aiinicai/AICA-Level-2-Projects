"""
Compare a recalculated CMA workbook with the engine figure by figure
(P&L, Balance Sheet, CMA Tests, DSCR, FORM-III tally, CHECK of OB = CB).
"""
import openpyxl

from analysis.engine import compute
from reports.cma_writer import Ctx, PLLayout, BSLayout, _ct_layout


def compare(path, project, result, tol=1.0):
    c = Ctx(project, result, {})
    PL, B, CT = PLLayout(c), BSLayout(c), _ct_layout(c)
    wb = openpyxl.load_workbook(path, data_only=True)
    pl, bs, ct, ds, f3 = wb["Profit and Loss"], wb["Balance Sheet"], wb["CMA Tests"], wb["DSCR"], wb["FORM-III"]
    diffs = []

    def chk(where, label, got, exp, t=tol):
        if got is None:
            got = 0.0
        if isinstance(got, str) or abs(float(got) - float(exp)) > t:
            diffs.append((where, label, got, exp))
    for i, y in enumerate(result.years):
        L = y["label"]
        chk("P&L " + L, "sales", sum(pl["I%d" % PL.row(ln.id, i, "right")].value or 0 for ln in c.sales_l), y["sales"])
        chk("P&L " + L, "purchases", pl[PL.E("purchases", i)].value, y["purchases"])
        chk("P&L " + L, "closing stock", pl[PL.I("closing_stock", i)].value, y["closing_stock"])
        chk("P&L " + L, "gross profit", pl[PL.E("gp_cd", i)].value, y["gross_profit"])
        chk("P&L " + L, "interest", pl[PL.E("interest", i)].value, y["interest"])
        chk("P&L " + L, "depreciation", pl[PL.E("depreciation", i)].value, y["depreciation"])
        chk("P&L " + L, "net profit", pl[PL.E("np_cd", i)].value, y["pat"])
        T = B.start(i) + B.total
        chk("BS " + L, "total liabilities", bs["D%d" % T].value, y["total_liabilities"])
        chk("BS " + L, "total assets", bs["I%d" % T].value, y["total_assets"])
        chk("BS " + L, "difference", bs["K%d" % T].value, 0)
        chk("BS " + L, "cash at bank", bs["I%d" % B.R("bank", i)].value, y["bank_balance"])
        chk("BS " + L, "debtors", bs["I%d" % B.R("debt", i)].value, y["debtors"])
        chk("BS " + L, "creditors", bs["C%d" % B.L("cred", i)].value, y["creditors"])
        chk("BS " + L, "owners", bs["D%d" % B.L("drw", i)].value + (bs["D%d" % B.L("share", i)].value if c.company else 0),
            y["owners"])
        chk("FORM-III " + L, "liab-assets", (f3["%s62" % "EFGHIJKLMN"[i]].value or 0) - (f3["%s142" % "EFGHIJKLMN"[i]].value or 0), 0, 0.05)
        if i in CT["cols"]:
            col = CT["cols"][i]
            chk("CMA Tests " + L, "drawing power", ct["%s%d" % (col, CT["rows"]["dp"])].value, y["drawing_power"])
            st = ct["%s%d" % (col, CT["rows"]["dp_status"])].value
            if st != y["dp_status"]:
                diffs.append(("CMA Tests " + L, "dp status", st, y["dp_status"]))
            if CT["rows"]["ob_all"] and not y["from_statement"]:
                ob = ct["%s%d" % (col, CT["rows"]["ob_all"])].value
                if ob != ("PASS" if y["bank_balance"] >= 0 else "FAIL"):
                    diffs.append(("CMA Tests " + L, "OB=CB", ob, "PASS"))
            if y.get("dscr") is not None:
                chk("DSCR " + L, "dscr", ds["%s18" % col].value, y["dscr"], 0.0005)
    return diffs
