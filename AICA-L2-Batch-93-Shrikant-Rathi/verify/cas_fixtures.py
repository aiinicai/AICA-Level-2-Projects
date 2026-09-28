"""A fictitious detailed CAS (made-up investor and folios, real scheme ISINs and realistic NAVs), built as a PDF at run
time; nothing is committed. Folio 1 is laid out like CAMS (ISIN on the line under the scheme name), folio 2 like KFintech
(ISIN on the same line); folio 3 is a scheme the app does not track; folio 4 has an opening balance."""
from contract_note_fixtures import _pdf, encrypted, inr  # noqa: F401  (encrypted re-exported for the tests)

PASSWORD = "Cas2026x"


def _u(v):
    return f"({abs(v):,.3f})" if v < 0 else f"{v:,.3f}"


def _a(v):
    return f"({inr(abs(v))})" if v < 0 else inr(v)


# (date, description, amount (negative for outflow of units), nav, stamp duty or None)
F1 = [("10-Apr-2026", "Systematic Investment Purchase - Instalment No 1", 9999.50, 115.20, 0.50),
      ("11-May-2026", "Systematic Investment Purchase - Instalment No 2", 9999.50, 116.80, 0.50),
      ("10-Jun-2026", "Systematic Investment Purchase - Instalment No 3", 9999.50, 118.10, 0.50),
      ("15-Jul-2026", "Redemption", -3630.00, 121.00, None),
      ("10-Aug-2026", "Systematic Investment Purchase - Instalment No 4", 9999.50, 120.30, 0.50)]
F2 = [("05-May-2026", "Purchase", 49997.50, 82.50, 2.50),
      ("20-Aug-2026", "Switch Out - To Parag Parikh Liquid Fund", -8300.00, 83.00, None)]
F3 = [("12-Jun-2026", "Purchase", 24998.75, 2950.1234, 1.25)]
F4 = [("12-Jun-2026", "Redemption", -8100.00, 405.00, None)]


def _folio(items, y, folio, header_lines, opening, txns, tamper=False):
    for t in header_lines:
        items.append((40, y, t)); y -= 11
    items.append((40, y, f"Opening Unit Balance: {opening:,.3f}")); y -= 11
    bal, out = opening, []
    for k, (d, desc, amt, nav, stamp) in enumerate(txns):
        units = round(amt / nav, 3)
        bal = round(bal + units, 3)
        shown = bal + (1.0 if tamper and k == 1 else 0.0)
        items.append((40, y, f"{d}   {desc}   {_a(amt)}   {_u(units)}   {nav:,.4f}   {shown:,.3f}")); y -= 11
        if stamp:
            items.append((40, y, f"{d}   *** Stamp Duty ***   {stamp:.2f}")); y -= 11
        out.append((d, units))
    items.append((40, y, f"Closing Unit Balance: {bal:,.3f}      NAV on 31-Aug-2026: INR 0.0000")); y -= 18
    return y, bal


def build(tamper=False):
    items, y = [(40, 570, "Consolidated Account Statement"), (40, 558, "01-Apr-2026 To 31-Aug-2026"),
                (40, 546, "DEMO INVESTOR (fictitious)   PAN: (masked)   Email: demo@example.com")], 526
    close = {}
    y, close["S01"] = _folio(items, y, "11223344 / 55", ["Folio No: 11223344 / 55   KYC: OK   PAN: OK",
                             "P8ICIC-ICICI Prudential Large Cap Fund - Direct Plan - Growth (Advisor: DIRECT) Registrar : CAMS",
                             "ISIN: INF109K016L0(Advisor: DIRECT)"], 0.0, F1, tamper)
    y, close["S05"] = _folio(items, y, "9900112233", ["Folio No: 9900112233",
                             "Parag Parikh Flexi Cap Fund - Regular Plan - Growth - ISIN: INF879O01019 Registrar : KFINTECH"], 0.0, F2)
    pages = [items]
    items, y = [], 570
    y, close["X"] = _folio(items, y, "5566778899", ["Folio No: 5566778899",
                           "Demo Liquid Fund - Direct Plan - Growth - ISIN: INF000A01AB2 Registrar : CAMS"], 0.0, F3)
    y, close["S12"] = _folio(items, y, "4433221100", ["Folio No: 4433221100",
                             "SBI Contra Fund - Direct Plan - Growth - ISIN: INF200K01RA0 Registrar : CAMS"], 100.0, F4)
    pages.append(items)
    return _pdf(pages), close


def summary_only():
    return _pdf([[(40, 570, "Consolidated Account Statement - Summary"), (40, 550, "Folio No: 11223344 / 55"),
                  (40, 539, "ICICI Prudential Large Cap Fund - Direct Plan - Growth - ISIN: INF109K016L0"),
                  (40, 528, "Closing Unit Balance: 250.000")]])
