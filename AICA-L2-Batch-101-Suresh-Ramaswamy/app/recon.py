"""Reconciliation of the filed returns of one financial year:

  1. Books (the invoice files / templates in this app)  vs  GSTR-1 as filed            - month by month, table by table
  2. GSTR-1 as filed  vs  GSTR-3B Table 3.1                                             - the portal's own auto-fill rules
  3. GSTR-3B: tax declared in 3.1 vs tax payable in 6.1, and payable vs paid           - month by month
  4. GSTR-9  vs  the year's filed GSTR-1 / GSTR-3B, and vs the books                   - Tables 4, 5, 6A and 9
  5. GSTR-9C (audited turnover + reconciling items, typed in)  vs  GSTR-9 Table 5N

Every row: check, period, source A (value, tax), source B (value, tax), differences, status, likely reason.
Status: OK (difference within Rs 1), DIFF, INFO (for information), MISSING (a return is not uploaded).
"""
from decimal import Decimal

from . import annual
from .returns import D5, V5, Z, add5, g1_expected_3b, g1_figures, g3b_figures, load_filed, tax_of

TOL = Decimal("1")

# One table per comparison (screen sub-tabs and Excel sheets): (name, areas, source 1, source 2)
RECON_TABLES = [
    ("1 Books vs GSTR-1", ("Books vs GSTR-1",), "Books", "GSTR-1 filed"),
    ("2 GSTR-1 vs GSTR-3B", ("GSTR-1 vs GSTR-3B",), "GSTR-1 filed", "GSTR-3B filed"),
    ("3 GSTR-3B tax paid", ("GSTR-3B tax",), "Declared / payable", "Payable / paid"),
    ("4 GSTR-9 vs GSTR-1+3B", ("GSTR-9 vs returns",), "GSTR-9", "GSTR-1 + 3B of the year"),
    ("5 Books vs GSTR-9", ("Books vs GSTR-9",), "Books", "GSTR-9"),
    ("6 GSTR-9 vs GSTR-9C", ("GSTR-9 vs GSTR-9C",), "GSTR-9C (books)", "GSTR-9"),
    ("Missing - information", ("Coverage", "GSTR-9"), "", ""),
]


def rows_for(rows, areas):
    return [r for r in rows if r["area"] in areas]
OK, DIFF, INFO, MISSING = "OK", "DIFF", "INFO", "MISSING"


def _row(area, period, check, a_name, a, b_name, b, reason="", value=True, tax=True, status=None):
    """a / b: 5-figure dicts (or None). Differences are A - B."""
    av = a["value"] if (a is not None and value) else None
    bv = b["value"] if (b is not None and value) else None
    at = tax_of(a) if (a is not None and tax) else None
    bt = tax_of(b) if (b is not None and tax) else None
    dv = (av - bv) if (av is not None and bv is not None) else None
    dt = (at - bt) if (at is not None and bt is not None) else None
    if status is None:
        bad = (dv is not None and abs(dv) > TOL) or (dt is not None and abs(dt) > TOL)
        status = DIFF if bad else OK
    return {"area": area, "period": period, "check": check, "a_name": a_name, "a_value": av, "a_tax": at,
            "b_name": b_name, "b_value": bv, "b_tax": bt, "d_value": dv, "d_tax": dt, "status": status,
            "reason": reason if status != OK else ""}


def _v(value=Z, igst=Z, cgst=Z, sgst=Z, cess=Z):
    return {"value": value, "igst": igst, "cgst": cgst, "sgst": sgst, "cess": cess}


def _from_books(x):
    return _v(x["taxable"], x["igst"], x["cgst"], x["sgst"], x["cess"])


def _any(v):
    return any(abs(v[k]) > 0 for k in V5)


def month_rows(label, books_m, g1, g3b):
    """books_m: annual.metrics() of the month (or None). g1 / g3b: stored return dicts (or None)."""
    rows = []
    f1 = g1_figures(g1["data"]) if g1 else None
    f3 = g3b_figures(g3b["data"]) if g3b else None
    have = ", ".join(n for n, x in (("books", books_m), ("GSTR-1", g1), ("GSTR-3B", g3b)) if x)
    missing = [n for n, x in (("GSTR-1", g1), ("GSTR-3B", g3b)) if not x]
    if missing and (books_m or g1 or g3b):
        rows.append(_row("Coverage", label, "Returns uploaded", have or "-", None, "", None,
                         f"Upload the filed {' and '.join(missing)} PDF of this month to reconcile it",
                         status=MISSING))
    for x in (g1, g3b):
        if x and x.get("ocr"):
            rows.append(_row("Coverage", label, f"{x['form']} read with OCR", x["file"], None, "", None,
                             "Part of the PDF was a picture - figures read by OCR may be wrong or missing. Use the "
                             "original PDF downloaded from the portal.", status=INFO))
    # ---- 1 books vs GSTR-1
    if books_m and f1:
        bm = {k: _from_books(books_m[k]) for k in ("b2b", "b2cl", "b2cs", "exp", "cdn", "nilex")}
        pairs = [
            ("B2B (Table 4 + 6B + 6C)", bm["b2b"], add5(f1["b2b"], f1["rcm"], f1["sezwp"], f1["sezwop"], f1["de"]),
             "Invoices missing in the filed return or in the books, or reported in another month"),
            ("B2C Large (Table 5)", bm["b2cl"], f1["b2cl"], "Check invoices above Rs 1 lakh to other states"),
            ("B2C Others (Table 7)", bm["b2cs"], f1["b2cs"], "B2C sales or their credit notes differ"),
            ("Exports (Table 6A)", bm["exp"], add5(f1["expwp"], f1["expwop"]), "Check shipping bills / export invoices"),
            ("Credit / debit notes (Table 9B)", bm["cdn"],
             add5(f1["n_reg"], f1["n_rcm"], f1["n_sez"], f1["n_de"], f1["nu_b2cl"], f1["nu_expwp"], f1["nu_expwop"]),
             "Notes missing or reported in another month"),
            ("Nil / exempt / non-GST (Table 8)", bm["nilex"], add5(f1["nil"], f1["exempt"], f1["nongst"]),
             "Check exempt / nil-rated sales"),
        ]
        for name, a, b, why in pairs:
            if _any(a) or _any(b):
                rows.append(_row("Books vs GSTR-1", label, name, "Books", a, "GSTR-1 filed", b, why,
                                 tax=name != "Nil / exempt / non-GST (Table 8)"))
        if books_m.get("docs_total") and f1["docs"]:
            d = (books_m["docs_total"] - books_m.get("docs_cancelled", 0) + books_m.get("docs_cn", 0)
                 + books_m.get("docs_dn", 0))
            r = _row("Books vs GSTR-1", label, "Documents issued, net (Table 13)", "Books", _v(Decimal(d)),
                     "GSTR-1 filed", _v(Decimal(f1["docs"])), "Document series or cancelled count differ", tax=False)
            if r["d_value"]:                                 # a count: any difference matters
                r["status"], r["reason"] = DIFF, "Document series or cancelled count differ"
            rows.append(r)
    # ---- 2 GSTR-1 vs GSTR-3B 3.1
    if f1 and f3:
        exp = g1_expected_3b(f1)
        t = f3["3.1"]
        amend = any(_any(f1[k]) for k in f1 if isinstance(f1[k], dict) and k.startswith(("a_", "na", "n_", "nu_")))
        why_a = ("3B was changed after the auto-fill, or supplies / notes / amendments were reported in a different "
                 "month" + (" - this GSTR-1 has amendments or notes, which also go into 3.1(a)" if amend else ""))
        rows.append(_row("GSTR-1 vs GSTR-3B", label, "3.1(a) Outward taxable supplies", "GSTR-1 filed", exp["a"],
                         "GSTR-3B 3.1(a)", t["a"], why_a))
        if exp["a_rcm_value"] and not tax_of(exp["a"]) and not tax_of(t["a"]):
            rows.append(_row("GSTR-1 vs GSTR-3B", label, "3.1(a) value without tax", "GSTR-1 Table 4B (RCM)",
                             _v(exp["a_rcm_value"]), "", None,
                             "Supplies on which the RECIPIENT pays tax (reverse charge, e.g. GTA): value is reported "
                             "in 3.1(a) with no tax for the supplier - correct", tax=False, status=INFO))
        for k, name, why in (("b", "3.1(b) Zero rated (exports / SEZ)", "Exports or SEZ supplies differ"),
                             ("c", "3.1(c) Nil rated / exempted", "Exempt / nil-rated supplies differ"),
                             ("e", "3.1(e) Non-GST", "Non-GST supplies differ")):
            if _any(exp[k]) or _any(t[k]):
                rows.append(_row("GSTR-1 vs GSTR-3B", label, name, "GSTR-1 filed", exp[k], f"GSTR-3B 3.1({k})", t[k], why,
                                 tax=k == "b"))
    # ---- 3 GSTR-3B: declared vs payable vs paid
    if f3 and f3["found_61"]:
        t, p = f3["3.1"], f3["pay"]
        decl = add5(t["a"], t["b"])
        pay = _v(Z, *[p[f"A_{h}_payable"] for h in ("igst", "cgst", "sgst", "cess")])
        rows.append(_row("GSTR-3B tax", label, "Output tax: 3.1(a)+(b) vs 6.1 payable", "3.1 declared", decl,
                         "6.1 payable", pay, "6.1 should equal the tax in 3.1(a) + 3.1(b) (+3.1.1(i) for e-commerce "
                         "operators)", value=False))
        rcm = _v(Z, *[p[f"B_{h}_payable"] for h in ("igst", "cgst", "sgst", "cess")])
        rows.append(_row("GSTR-3B tax", label, "Reverse charge: 3.1(d) vs 6.1(B) payable", "3.1(d) declared", t["d"],
                         "6.1(B) payable", rcm, "Reverse-charge tax must be paid in cash", value=False))
        for part, name in (("A", "Tax paid (other than RCM)"), ("B", "Tax paid (reverse charge)")):
            payable = _v(Z, *[p[f"{part}_{h}_payable"] for h in ("igst", "cgst", "sgst", "cess")])
            paid = _v(Z, *[p[f"{part}_{h}_itc"] + p[f"{part}_{h}_cash"] for h in ("igst", "cgst", "sgst", "cess")])
            if _any(payable) or _any(paid):
                rows.append(_row("GSTR-3B tax", label, name, "Payable", payable, "Paid (ITC + cash)", paid,
                                 "Short payment - pay through DRC-03 with interest", value=False))
        intr = sum((p[f"{a}_{h}_interest"] for a in "AB" for h in ("igst", "cgst", "sgst", "cess")), Z)
        late = sum((p[f"{a}_{h}_late_fee"] for a in "AB" for h in ("igst", "cgst", "sgst", "cess")), Z)
        if intr or late:
            rows.append(_row("GSTR-3B tax", label, "Interest / late fee paid", "Interest", _v(intr), "Late fee",
                             _v(late), "Return filed late or tax paid late - record in books (expense, not ITC)",
                             tax=False, status=INFO))
    return rows


def _sum(months, fn):
    out = _v()
    for m in months:
        out = add5(out, fn(m))
    return out


def annual_rows(fy, g1s, g3bs, g9, year=None):
    """g1s / g3bs: {'2025-04': doc, ...}. g9: stored GSTR-9 dict or None. year: annual.build_year() (books)."""
    rows = []
    f1 = [g1_figures(d["data"]) for _, d in sorted(g1s.items())]
    f3 = [g3b_figures(d["data"]) for _, d in sorted(g3bs.items())]
    cover = f"GSTR-1 for {len(f1)} of 12 months, GSTR-3B for {len(f3)} of 12 months"
    if not g9:
        if f1 or f3:
            rows.append(_row("GSTR-9", f"FY {fy}", "GSTR-9 not uploaded", cover, None, "", None,
                             "Upload the GSTR-9 PDF (system computed draft or filed) to compare the year", status=MISSING))
        return rows
    G = g9["data"]

    def g4(code):
        r = G.get("4" + code) or {}
        return _v(*[Decimal(str(r.get(k, "0"))) for k in ("value", "igst", "cgst", "sgst", "cess")])

    def g5(code):
        return _v(Decimal(str((G.get("5" + code) or {}).get("value", "0"))))

    if len(f1) < 12 or len(f3) < 12:
        rows.append(_row("GSTR-9", f"FY {fy}", "Months available", cover, None, "", None,
                         "Differences below are expected until all 12 months are uploaded", status=INFO))
    exp = {
        "4A": (_sum(f1, lambda f: add5(f["b2cl"], f["b2cs"])), "Table 5 + Table 7 of GSTR-1"),
        "4B": (_sum(f1, lambda f: f["b2b"]), "Table 4A of GSTR-1"),
        "4C": (_sum(f1, lambda f: f["expwp"]), "Table 6A (with payment)"),
        "4D": (_sum(f1, lambda f: f["sezwp"]), "Table 6B (with payment)"),
        "4E": (_sum(f1, lambda f: f["de"]), "Table 6C"),
        "4F": (_sum(f1, lambda f: add5(f["adv"], f["a_adv"], f["adj"], f["a_adj"], sign=[1, 1, -1, -1])),
               "Table 11A - 11B"),
        "4G": (_sum(f3, lambda f: f["3.1"]["d"]), "GSTR-3B 3.1(d)"),
    }
    names = {"4A": "4A Supplies to unregistered persons (B2C)", "4B": "4B Supplies to registered persons (B2B)",
             "4C": "4C Exports with payment of tax", "4D": "4D SEZ supplies with payment of tax",
             "4E": "4E Deemed exports", "4F": "4F Advances (net)", "4G": "4G Inward supplies on reverse charge"}
    for code, (e, src) in exp.items():
        a = g4(code[1])
        if _any(a) or _any(e):
            rows.append(_row("GSTR-9 vs returns", f"FY {fy}", names[code], "GSTR-9", a, src, e,
                             "Check the months: a supply may be in the wrong table or not yet in GSTR-1"))
    notes4 = _sum(f1, lambda f: add5(f["n_reg"], f["n_sez"], f["n_de"], f["nu_b2cl"], f["nu_expwp"]))
    rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "4J - 4I Debit notes less credit notes (net)", "GSTR-9",
                     add5(g4("J"), g4("I"), sign=[1, -1]), "Table 9B of GSTR-1 (net)", notes4,
                     "Notes netted in GSTR-1; GSTR-9 shows credit and debit notes separately"))
    am4 = _sum(f1, lambda f: add5(*[f[k] for k in ("a_b2b", "a_b2cl", "a_expwp", "a_sezwp", "a_de", "a_b2cs",
                                                   "na_reg", "na_sez", "na_de", "nau_b2cl", "nau_expwp")]))
    rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "4K - 4L Amendments (net)", "GSTR-9",
                     add5(g4("K"), g4("L"), sign=[1, -1]), "Tables 9A / 9C / 10 of GSTR-1 (net)", am4,
                     "Amendments of the previous year made in this year's GSTR-1 belong in the previous year's GSTR-9"))
    exp5 = {
        "A": (_sum(f1, lambda f: f["expwop"]), "Table 6A (without payment)", "5A Exports without payment of tax"),
        "B": (_sum(f1, lambda f: f["sezwop"]), "Table 6B (without payment)", "5B SEZ supplies without payment"),
        "C": (_sum(f1, lambda f: f["rcm"]), "Table 4B (reverse charge)", "5C Supplies taxable on reverse charge"),
        "D": (_sum(f1, lambda f: f["exempt"]), "Table 8 exempted", "5D Exempted"),
        "E": (_sum(f1, lambda f: f["nil"]), "Table 8 nil rated", "5E Nil rated"),
        "F": (_sum(f1, lambda f: f["nongst"]), "Table 8 non-GST", "5F Non-GST supply"),
    }
    for code, (e, src, name) in exp5.items():
        a = g5(code)
        if _any(a) or _any(e):
            rows.append(_row("GSTR-9 vs returns", f"FY {fy}", name, "GSTR-9", a, src, e,
                             "Check the months / tables in GSTR-1", tax=False))
    n5 = _sum(f1, lambda f: add5(f["n_rcm"], f["nu_expwop"]))
    rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "5I - 5H Notes on non-taxable supplies (net)", "GSTR-9",
                     add5(g5("I"), g5("H"), sign=[1, -1]), "Table 9B of GSTR-1 (RCM / without payment)", n5,
                     "Credit notes on reverse-charge / zero-rated supplies", tax=False))
    a5 = _sum(f1, lambda f: add5(*[f[k] for k in ("a_rcm", "a_expwop", "a_sezwop", "na_rcm", "nau_expwop")]))
    rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "5J - 5K Amendments (net)", "GSTR-9",
                     add5(g5("J"), g5("K"), sign=[1, -1]), "Tables 9A / 9C of GSTR-1 (net)", a5,
                     "Amendments of the previous year made in this year's GSTR-1 belong in the previous year's GSTR-9",
                     tax=False))
    # ITC and tax paid
    if f3:
        itc = _v()
        for f in f3:
            for k in ("A1", "A2", "A3", "A4", "A5"):
                x = f["itc"].get(k)
                if x:
                    itc = add5(itc, _v(Z, x["igst"], x["cgst"], x["sgst"], x["cess"]))
        r6 = G.get("6A") or {}
        a6 = _v(Z, *[Decimal(str(r6.get(h, "0"))) for h in ("igst", "cgst", "sgst", "cess")])
        rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "6A ITC availed (GSTR-3B 4A)", "GSTR-9 6A", a6,
                         "Sum of GSTR-3B 4A", itc, "GSTR-9 6A is auto-filled from 3B 4A of the year", value=False))
        pay = _v()
        paid = _v()
        intr = Z
        for f in f3:
            p = f["pay"]
            pay = add5(pay, _v(Z, *[p[f"A_{h}_payable"] + p[f"B_{h}_payable"] for h in ("igst", "cgst", "sgst", "cess")]))
            paid = add5(paid, _v(Z, *[p[f"A_{h}_itc"] + p[f"A_{h}_cash"] + p[f"B_{h}_itc"] + p[f"B_{h}_cash"]
                                      for h in ("igst", "cgst", "sgst", "cess")]))
            intr += sum((p[f"{a}_{h}_interest"] for a in "AB" for h in ("igst", "cgst", "sgst", "cess")), Z)
        g9pay = _v(Z, *[Decimal(str((G.get("9" + c) or {}).get("payable", "0"))) for c in "ABCD"])
        g9paid = _v(Z, *[Decimal(str((G.get("9" + c) or {}).get("paid", "0"))) for c in "ABCD"])
        rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "9 Tax payable", "GSTR-9 Table 9", g9pay,
                         "Sum of GSTR-3B 6.1 payable", pay, "Check months not uploaded or tax paid through DRC-03",
                         value=False))
        rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "9 Tax paid", "GSTR-9 Table 9", g9paid,
                         "Sum of GSTR-3B 6.1 paid", paid, "Check months not uploaded or tax paid through DRC-03",
                         value=False))
        if g9pay != g9paid:
            rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "9 Payable vs paid in GSTR-9", "Payable", g9pay,
                             "Paid", g9paid, "Short payment for the year - pay through DRC-03 before filing GSTR-9",
                             value=False))
        e9 = Decimal(str((G.get("9E") or {}).get("payable", "0")))
        if e9 or intr:
            rows.append(_row("GSTR-9 vs returns", f"FY {fy}", "9E Interest", "GSTR-9 9E", _v(e9),
                             "Sum of GSTR-3B interest", _v(intr), "Interest paid outside GSTR-3B (DRC-03)", tax=False))
    # GSTR-9 vs books
    if year and any(r["has_data"] for r in year["months"]):
        bk = year["g9"]
        for code, name in (("4A", "4A B2C"), ("4B", "4B B2B"), ("4C", "4C Exports with payment"),
                           ("4D", "4D SEZ with payment"), ("4E", "4E Deemed exports"), ("4F", "4F Advances (net)"),
                           ("4I", "4I Credit notes"), ("4J", "4J Debit notes"), ("5A", "5A Exports without payment"),
                           ("5B", "5B SEZ without payment"), ("5D", "5D Exempted"), ("5E", "5E Nil rated"),
                           ("5F", "5F Non-GST")):
            b = _from_books(bk[code])
            a = g4(code[1]) if code[0] == "4" else g5(code[1])
            if _any(a) or _any(b):
                rows.append(_row("Books vs GSTR-9", f"FY {fy}", name, "Books (this app)", b, "GSTR-9", a,
                                 "GSTR-9 (auto-filled from GSTR-1 / 3B) differs from the books: a supply missed or "
                                 "wrong in the monthly returns, or books not complete for the year",
                                 tax=code[0] == "4"))
        tx = lambda x: x["igst"] + x["cgst"] + x["sgst"] + x["cess"]   # noqa: E731
        bt = sum((tx(bk[c]) for c in ("4A", "4B", "4C", "4D", "4E", "4F", "4J")), Z) - tx(bk["4I"])
        g9t = sum((Decimal(str((G.get("9" + c) or {}).get("payable", "0"))) for c in "ABCD"), Z)
        g9t -= tax_of(g4("G"))                                        # RCM tax on purchases is not in the sales books
        if bt or g9t:
            rows.append(_row("Books vs GSTR-9", f"FY {fy}", "Output tax for the year (books vs GSTR-9 Table 9)",
                             "Books (this app)", _v(Z, bt), "GSTR-9 Table 9 payable (less 4G RCM)", _v(Z, g9t),
                             "Tax on supplies in the books but not declared - declare in GSTR-9 and pay through "
                             "DRC-03 with interest", value=False))
    return rows


def ninec_rows(db, client, fy, g9):
    """GSTR-9C Part II Table 5: turnover as per the audited accounts + reconciling items, against the turnover declared
    in GSTR-9 Table 5N. The 9C figures are typed by the user (Enter GSTR-9C figures on tab 15)."""
    ann = annual.load_entries(db, client["id"], fy).get(annual.ANNUAL_KEY, {})
    has9c = str(ann.get("fs_turnover", "")).strip() != ""
    if not has9c and not g9:
        return []
    if not has9c:
        return [_row("GSTR-9 vs GSTR-9C", f"FY {fy}", "GSTR-9C figures not entered", "", None, "", None,
                     "Click 'Enter GSTR-9C figures' and type the audited turnover and the reconciling items",
                     status=MISSING)]
    fs, adj = Decimal(str(ann.get("fs_turnover", "0") or "0")), Decimal(str(ann.get("c9_adj", "0") or "0"))
    reconciled = _v(fs + adj)
    rows = [_row("GSTR-9 vs GSTR-9C", f"FY {fy}", "9C 5A Turnover per audited financial statements", "GSTR-9C", _v(fs),
                 "", None, "", tax=False, status=INFO),
            _row("GSTR-9 vs GSTR-9C", f"FY {fy}", "9C 5B-5P Net reconciling items", "GSTR-9C", _v(adj), "", None, "",
                 tax=False, status=INFO)]
    n5 = (g9 or {}).get("data", {}).get("5N") if g9 else None
    if not n5:
        rows.append(_row("GSTR-9 vs GSTR-9C", f"FY {fy}", "Turnover as reconciled (5A + items) vs GSTR-9 Table 5N",
                         "GSTR-9C", reconciled, "GSTR-9 Table 5N", None,
                         "Upload the GSTR-9 PDF (Table 5N could not be read or the return is not uploaded)",
                         tax=False, status=MISSING))
    else:
        rows.append(_row("GSTR-9 vs GSTR-9C", f"FY {fy}", "Turnover as reconciled (5A + items) vs GSTR-9 Table 5N",
                         "GSTR-9C (books)", reconciled, "GSTR-9", _v(Decimal(str(n5.get("value", "0")))),
                         "Reconciling items are incomplete or the audited turnover is wrong; or GSTR-9 differs from the books",
                         tax=False))
    return rows


def build(db, client, fy, year=None, settings=None, schema=None):
    """All reconciliation rows for the FY (months in FY order, then the year)."""
    filed = load_filed(db, client["id"], fy)
    g1s, g3bs = filed.get("GSTR1", {}), filed.get("GSTR3B", {})
    g9 = (filed.get("GSTR9") or {}).get("FY")
    rows = []
    months = year["months"] if year else []
    seen = set()
    for r in months:
        key = f"{r['year']}-{r['month']:02d}"
        seen.add(key)
        bm = r["m"] if r["has_data"] else None
        g1, g3 = g1s.get(key), g3bs.get(key)
        if bm or g1 or g3:
            rows += month_rows(r["label"], bm, g1, g3)
    for key in sorted(set(g1s) | set(g3bs)):
        if key not in seen:
            rows += month_rows(key, None, g1s.get(key), g3bs.get(key))
    rows += annual_rows(fy, g1s, g3bs, g9, year)
    rows += ninec_rows(db, client, fy, g9)
    return rows


def summary_counts(rows):
    out = {OK: 0, DIFF: 0, INFO: 0, MISSING: 0}
    for r in rows:
        out[r["status"]] = out.get(r["status"], 0) + 1
    return out


def filed_list(db, client_id, fy):
    """Rows for the 'Filed returns' list: form, period, file, ARN date, key figures, notes."""
    filed = load_filed(db, client_id, fy)
    out = []
    order = {"GSTR1": 0, "GSTR3B": 1, "GSTR9": 2}
    for form in sorted(filed, key=lambda f: order.get(f, 9)):
        for key, d in sorted(filed[form].items()):
            if form == "GSTR1":
                f = g1_figures(d["data"])
                e = g1_expected_3b(f)
                fig = (f"Outward value {e['a']['value'] + e['b']['value'] + e['c']['value'] + e['e']['value']:,.2f}; "
                       f"tax {tax_of(e['a']) + tax_of(e['b']):,.2f}; documents {f['docs']}")
            elif form == "GSTR3B":
                f = g3b_figures(d["data"])["3.1"]
                fig = (f"3.1(a) {f['a']['value']:,.2f} tax {tax_of(f['a']):,.2f}; (b) {f['b']['value']:,.2f}; "
                       f"(c) {f['c']['value']:,.2f}; (d) RCM tax {tax_of(f['d']):,.2f}")
            else:
                g = d["data"]
                fig = ", ".join(f"{k} {Decimal(str(v.get('value', '0'))):,.2f}" for k, v in sorted(g.items())
                                if k[0] in "45" and "value" in v and Decimal(str(v["value"])))[:200]
            out.append({"form": form, "key": key, "period": key if form != "GSTR9" else f"FY {d.get('fy')}",
                        "file": d.get("file", ""), "arn": d.get("arn_date", ""), "figures": fig,
                        "notes": "; ".join(d.get("messages", []))})
    return out


def export_sheets(path, client, fy, rows, filed_rows):
    """Add 'Reconciliation' and 'Filed returns' sheets to the YTD workbook already saved at path."""
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = load_workbook(path)
    head = PatternFill("solid", fgColor="1F3864")
    white = Font(bold=True, color="FFFFFF")
    fills = {DIFF: PatternFill("solid", fgColor="FFD6D6"), MISSING: PatternFill("solid", fgColor="FFF3C4"),
             INFO: PatternFill("solid", fgColor="FFF3C4"), OK: PatternFill("solid", fgColor="DFF5DF")}

    def top(ws, title, header, widths):
        ws.append([f"{client['name']}  |  {client['gstin']}  |  FY {fy}"])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append([title])
        ws.append([])
        ws.append(header)
        for c in ws[4]:
            c.fill, c.font = head, white
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A5"

    f = lambda v: float(v) if v is not None else None   # noqa: E731
    for name, areas, s1, s2 in RECON_TABLES:
        part = rows_for(rows, areas)
        ws = wb.create_sheet(name)
        if s1:
            top(ws, f"{name.split(' ', 1)[1]}: difference = {s1} - {s2}",
                ["Status", "Period", "Check", f"{s1} value", f"{s1} tax", f"{s2} value", f"{s2} tax",
                 f"Difference value ({s1} - {s2})", f"Difference tax ({s1} - {s2})", "Likely reason / action",
                 "Figures compared", "Remarks (staff)"], [9, 11, 42, 16, 14, 16, 14, 18, 16, 70, 45, 30])
            for r in part:
                ws.append([r["status"], r["period"], r["check"], f(r["a_value"]), f(r["a_tax"]), f(r["b_value"]),
                           f(r["b_tax"]), f(r["d_value"]), f(r["d_tax"]), r["reason"],
                           f"{r['a_name']}  vs  {r['b_name']}", ""])
                ws.cell(ws.max_row, 1).fill = fills.get(r["status"], PatternFill())
                for c in range(4, 10):
                    ws.cell(ws.max_row, c).number_format = "#,##0.00;[Red]-#,##0.00"
        else:
            top(ws, "Returns missing and information", ["Status", "Period", "Check", "Detail", "Action", "Remarks (staff)"],
                [10, 12, 40, 50, 80, 30])
            for r in part:
                ws.append([r["status"], r["period"], r["check"], r["a_name"], r["reason"], ""])
                ws.cell(ws.max_row, 1).fill = fills.get(r["status"], PatternFill())
        if not part:
            ws.append(["No rows - nothing uploaded for this comparison yet."])
        ws.append([])
        ws.append(["Figures are read from the PDFs downloaded from the GST portal - verify on the portal. "
                   "R Suresh & Associates, Chartered Accountants"])
    ws2 = wb.create_sheet("Filed returns")
    top(ws2, "Filed returns uploaded", ["Return", "Period", "File", "ARN date", "Key figures", "Notes"],
        [10, 12, 45, 12, 90, 60])
    for r in filed_rows:
        ws2.append([r["form"], r["period"], r["file"], r["arn"], r["figures"], r["notes"]])
    wb.save(path)


def how_to_fix(r) -> str:
    """Plain-language remedy for a reconciliation row (the CA decides; these are the usual routes)."""
    if r["status"] == OK:
        return "Nothing to do - the figures agree."
    if r["status"] == MISSING:
        return "Download the filed return PDF from the GST portal (Returns > View e-filed returns) and upload it on tab 15."
    if r["status"] == INFO:
        return "For information only. Check it once; no correction is needed if it is as expected."
    a, chk = r["area"], r["check"]
    short = (r["d_tax"] or 0) > 0 or (r["d_value"] or 0) > 0
    if a == "Books vs GSTR-1":
        return ("Open the month (double-click) and compare the invoices. If an invoice is missing in GSTR-1 or wrong, "
                "report it / amend it (Table 9A / 9C) in the next GSTR-1. If the books are wrong, correct the books.")
    if a == "GSTR-1 vs GSTR-3B":
        if short:
            return ("GSTR-3B shows less than GSTR-1 (GSTR-1 is correct). A filed GSTR-3B cannot be revised: add the "
                    "short value and tax in Table 3.1 of the next month's GSTR-3B, or pay the tax through DRC-03. "
                    "Interest u/s 50 @ 18% p.a. applies from the original due date to the date of payment. "
                    "Note the adjustment in the working papers and in GSTR-9 Table 9.")
        return ("GSTR-3B shows more than GSTR-1. If an earlier month's GSTR-3B was short by the same amount, this is "
                "that shortfall being made good - nothing more to do (interest u/s 50 for the delay). Otherwise check "
                "whether an invoice is missing in GSTR-1 (report it in the next GSTR-1) or the 3B was over-reported "
                "(reduce it in a later 3B, within the time limit).")
    if a == "GSTR-3B tax":
        return ("Tax payable and tax declared / paid do not agree. Pay any short tax through DRC-03 with interest, "
                "or adjust it in the next GSTR-3B.")
    if a == "GSTR-9 vs returns":
        if chk.startswith("9"):
            return ("Tax payable for the year is more than the tax paid in the GSTR-3B returns. Pay the difference "
                    "through DRC-03 (with interest) before filing GSTR-9, and show it in Table 9 / 14.")
        return ("GSTR-9 does not agree with the year's GSTR-1 / 3B. Check that every month is uploaded, then correct "
                "the GSTR-9 figures (it is a draft until filed). Amendments made after the year go in Tables 10-14.")
    if a == "Books vs GSTR-9":
        if short:
            return ("The books have more than GSTR-9 (auto-filled from GSTR-1 / 3B). Find the month in table 1 "
                    "(Books vs GSTR-1). Declare the missed supply in GSTR-9 (Table 4 / 5 as applicable; Table 10 if "
                    "it was declared in the next year's returns up to the time limit), and pay the tax through DRC-03 "
                    "with interest u/s 50. Keep the working for GSTR-9C where applicable.")
        return ("GSTR-9 has more than the books: check for supplies reported twice or wrongly in GSTR-1 / 3B, or "
                "entries missing in the books. Reduce in GSTR-9 only within the law (Table 11 for later reductions) "
                "and correct the books if they are incomplete.")
    if a == "GSTR-9 vs GSTR-9C":
        return ("The turnover per the audited accounts (after the reconciling items in 9C Table 5B-5P) does not agree "
                "with GSTR-9 Table 5N. Check unbilled revenue, unadjusted advances, credit notes, discounts and other "
                "items in 9C, and the books; the unreconciled amount must be explained in 9C Table 5R.")
    return "Check the figures and correct the return or the books."
