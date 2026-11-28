"""Synthetic GSTR-2B files laid out like the portal downloads (made-up data, for tests only)."""
from __future__ import annotations

import json
from pathlib import Path

B2B_TOP = ["GSTIN of supplier", "Trade/Legal name", "Invoice details", None, None, None, "Place of supply",
           "Supply Attract Reverse Charge", "Taxable Value (₹)", "Tax Amount", None, None, None,
           "GSTR-1/IFF/GSTR-5 Period", "GSTR-1/IFF/GSTR-5 Filing Date", "ITC Availability", "Reason",
           "Applicable % of Tax Rate", "Source", "IRN", "IRN Date"]
B2B_SUB = [None, None, "Invoice number", "Invoice type", "Invoice Date", "Invoice Value(₹)", None, None, None,
           "Integrated Tax(₹)", "Central Tax(₹)", "State/UT Tax(₹)", "Cess(₹)"] + [None] * 8
CDNR_TOP = ["GSTIN of supplier", "Trade/Legal name", "Credit note/Debit note details", None, None, None, None,
            "Place of supply", "Supply Attract Reverse Charge", "Taxable Value (₹)", "Tax Amount", None, None, None,
            "GSTR-1/IFF/GSTR-5 Period", "GSTR-1/IFF/GSTR-5 Filing Date", "ITC Availability", "Reason"]
CDNR_SUB = [None, None, "Note number", "Note type", "Note Supply type", "Note date", "Note Value (₹)", None, None,
            None, "Integrated Tax(₹)", "Central Tax(₹)", "State/UT Tax(₹)", "Cess(₹)", None, None, None, None]
B2BA_TOP = ["Invoice details", None, "GSTIN of supplier", "Trade/Legal name", "Revised details", None, None, None,
            "Place of supply", "Supply Attract Reverse Charge", "Taxable Value (₹)", "Tax Amount", None, None, None,
            "GSTR-1/IFF/GSTR-5 Period", "GSTR-1/IFF/GSTR-5 Filing Date", "ITC Availability", "Reason"]
B2BA_SUB = ["Original Invoice number", "Original Invoice date", None, None, "Invoice number", "Invoice type",
            "Invoice Date", "Invoice Value(₹)", None, None, None, "Integrated Tax(₹)", "Central Tax(₹)",
            "State/UT Tax(₹)", "Cess(₹)", None, None, None, None]


def make_2b_excel(path: Path, b2b: list[tuple], cdnr: list[tuple] = (), b2ba: list[tuple] = (),
                  period_month: str = "October", fy: str = "2026-27", gstin: str = "") -> Path:
    """b2b rows: (gstin, name, inv_no, date 'dd-mm-yyyy', value, pos, rc, taxable, igst, cgst, sgst, cess, itc)
    cdnr rows: (gstin, name, note_no, 'Credit Note'/'Debit Note', date, value, taxable, igst, cgst, sgst, itc)
    b2ba rows: (orig_no, orig_date, gstin, name, inv_no, date, value, taxable, igst, cgst, sgst, itc)"""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Read me"
    ws.append(["Goods and Services Tax - GSTR-2B"])
    ws.append([f"Financial Year {fy}"])
    ws.append([f"Tax Period {period_month}"])
    ws.append([f"GSTIN {gstin}"])
    s = wb.create_sheet("ITC Available")
    s.append(["Summary of ITC available"])
    s = wb.create_sheet("B2B")
    s.append(["Taxable inward supplies received from registered persons"])
    s.append([])
    s.append([])
    s.append([])
    s.append(B2B_TOP)
    s.append(B2B_SUB)
    for r in b2b:
        g, n, no, dt, val, pos, rc, tx, ig, cg, sg, ce, itc = r
        s.append([g, n, no, "Regular", dt, val, pos, rc, tx, ig, cg, sg, ce, "Oct'26", "11-11-2026", itc, "", "",
                  "", "", ""])
    s = wb.create_sheet("B2BA")
    s.append(["Amendments to previously filed invoices"])
    s.append([])
    s.append([])
    s.append([])
    s.append(B2BA_TOP)
    s.append(B2BA_SUB)
    for r in b2ba:
        on, od, g, n, no, dt, val, tx, ig, cg, sg, itc = r
        s.append([on, od, g, n, no, "Regular", dt, val, "08-Rajasthan", "No", tx, ig, cg, sg, 0, "Oct'26",
                  "11-11-2026", itc, ""])
    s = wb.create_sheet("B2B-CDNR")
    s.append(["Debit/Credit notes (Original)"])
    s.append([])
    s.append([])
    s.append([])
    s.append(CDNR_TOP)
    s.append(CDNR_SUB)
    for r in cdnr:
        g, n, no, typ, dt, val, tx, ig, cg, sg, itc = r
        s.append([g, n, no, typ, "Regular", dt, val, "08-Rajasthan", "No", tx, ig, cg, sg, 0, "Oct'26",
                  "11-11-2026", itc, ""])
    wb.save(path)
    return path


def make_2b_json(path: Path, b2b: list[tuple], rtnprd: str = "102026", gstin: str = "",
                 with_items: bool = True) -> Path:
    """b2b rows: (gstin, name, inv_no, 'dd-mm-yyyy', value, pos, rev 'Y'/'N', taxable, igst, cgst, sgst, cess, itcavl)"""
    sups: dict[str, dict] = {}
    for g, n, no, dt, val, pos, rev, tx, ig, cg, sg, ce, itc in b2b:
        sup = sups.setdefault(g, {"ctin": g, "trdnm": n, "supprd": rtnprd, "supfildt": "11-11-2026", "inv": []})
        doc = {"inum": no, "typ": "R", "dt": dt, "val": val, "pos": pos, "rev": rev, "itcavl": itc, "rsn": ""}
        amounts = {"txval": tx, "igst": ig, "cgst": cg, "sgst": sg, "cess": ce}
        if with_items:
            doc["items"] = [dict(num=1, rt=5, **amounts)]
        else:
            doc.update(amounts)
        sup["inv"].append(doc)
    payload = {"data": {"data": {"gstin": gstin, "rtnprd": rtnprd, "gendt": "14-11-2026",
                                 "docdata": {"b2b": list(sups.values()), "ecom": []}}}}
    path.write_text(json.dumps(payload))
    return path
