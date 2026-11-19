"""Tally replies for the fictional demo company (Aarohan Infotech Private Limited, FY 2026-27), plus small hand-made
replies for cases the demo books don't have (USD export invoice, Latin-1 narration, numbering series).
Every build must pass these. They hold the cases a simulated Tally never had:
- Profit & Loss A/c closing that already includes this year's profit
- Tally's own Trial Balance report shape, item invoices with stock, two share capital ledgers
- USD amounts in Tally's "$ x @ ? rate/$ = ? y" form, invoice-view entries sent in both lists
- cp1252 bytes, and voucher numbering with a manual number
The Trial Balance file is computed straight from the demo books, not by the app, so the comparison is independent."""
import csv
import gzip
import json
from decimal import Decimal as D
from pathlib import Path

from app.engine import numbering, reports, sch3
from app.tally import parsers

R = Path(__file__).parent / "demodata"
CO = "AAROHAN INFOTECH PRIVATE LIMITED"


def _closings():
    d = json.loads((R / "aarohan_closings.json").read_text())
    cl = {k: {"parent": v["parent"], "opening": D(v["opening"]), "closing": D(v["closing"])}
          for k, v in d["closings"].items()}
    return d["groups"], cl, D(d["stock"]["closing"])


def _tally_tb():
    return parsers.parse_tb_report((R / "aarohan_tally_tb.xml").read_bytes())


def test_trial_balance_and_balance_sheet_match_tally():
    groups, cl, stock = _closings()
    rep = reports.build(groups, cl, None, stock_period=(D(0), stock), stock_cum=(D(0), stock))
    tb = _tally_tb()
    reports.add_tally_only_lines(rep, tb)
    assert reports.compare_tb(rep, tb) == []                       # every TB line equals Tally's own TB
    assert rep.tb_dr == rep.tb_cr
    assert abs(sum(n.amount for n in rep.bs_liabilities + rep.bs_assets)) < D("0.01")
    assert not [n for n in rep.notes if n.startswith("Difference")]


def test_known_figures():
    """Figures from the demo pack's answer key (6_Expected_Results)."""
    groups, cl, stock = _closings()
    rep = reports.build(groups, cl, None, stock_period=(D(0), stock), stock_cum=(D(0), stock))
    tbl = {n.name: n.amount for n in rep.trial_balance}
    assert tbl["Profit & Loss A/c"] == D("1506380.50")             # brought forward only
    assert tbl["Sales Accounts"] == D("7542900.00")
    assert rep.gross_profit == D("7346050.00") and rep.net_profit == D("2151673.09")
    assert cl["HDFC Bank CA 50200012345678"]["closing"] == D("-1395918.62")   # bank 14,03,711.92 less BRS items
    assert tbl["Capital Account"] == D("1000000.00")               # both share capital ledgers (6 + 4 lakh)


def test_tally_only_line_is_added():
    groups, cl, stock = _closings()
    rep = reports.build(groups, cl, None, stock_period=(D(0), stock), stock_cum=(D(0), stock))
    tb = _tally_tb() + [("Unadjusted Forex Gain/Loss", D("1250.00"), D("0"))]
    reports.add_tally_only_lines(rep, tb)
    assert {n.name: n.amount for n in rep.trial_balance}["Unadjusted Forex Gain/Loss"] == D("-1250.00")


class _Replay:
    """Tally stand-in that answers only with the recorded demo replies."""
    def __init__(self):
        self.groups_, self.cl, self.stock = _closings()
        self.tb = _tally_tb()

    def groups(self, company):
        return self.groups_

    def ledger_closings(self, company, frm, to):
        if frm < "20260401":
            raise RuntimeError("no recording for the previous year")
        return self.cl

    def stock_values(self, company, frm, to):
        return D(0), self.stock

    def trial_balance_report(self, company, frm, to):
        if frm < "20260401":
            raise RuntimeError("no recording")
        return self.tb, b""


def test_schedule_iii_balances():
    st = sch3.fetch(_Replay(), CO, "20260401", "20261031", {}, {})
    assert abs(st.totals["eq_c"] - st.totals["as_c"]) < D("0.01"), st.notes


def test_day_book_parses_and_balances():
    vs = parsers.parse_vouchers(gzip.decompress((R / "aarohan_vouchers.xml.gz").read_bytes()))
    assert len(vs) == 394
    for v in vs:
        assert sum(D(e["amount"]) * (1 if e["dr"] else -1) for e in v["entries"]) == 0, v["number"]
    item = [v for v in vs if v["voucher_type"] == "Purchase" and any(e["ledger"] == "Purchase - Hardware"
                                                                     for e in v["entries"])]
    assert item                                                     # ledger inside the stock lines is read


def test_usd_vouchers_latin1_and_invoice_view():
    vs = parsers.parse_vouchers((R / "forex_vouchers.xml").read_bytes())
    assert len(vs) == 3 and parsers.LAST_SKIPPED[0] == 0            # cp1252 'Café' in a narration
    assert "Café" in vs[2]["narration"]
    for v in vs:
        assert sum(D(e["amount"]) * (1 if e["dr"] else -1) for e in v["entries"]) == 0, v["number"]
    sale = vs[0]
    assert len(sale["entries"]) == 2                                # both entry lists sent: read once
    deb = [e for e in sale["entries"] if e["dr"]][0]
    assert deb["fc"] == "50000.00" and deb["rate"] == "90.5291" and deb["cur"] == "$"
    assert parsers.forex("-$ 50000.00 @ ? 90.5291/$  = -? 4526455.00")["inr"] == D("-4526455.00")


def test_gstins_found():
    found = parsers.scan_gstins(gzip.decompress((R / "aarohan_masters.xml.gz").read_bytes()))
    assert "29AAHCC9120B1ZW" in found and "27AACCV3381N1ZU" in found


def _numbers():
    return [(r["number"], r["date"]) for r in csv.DictReader((R / "journal_numbers.csv").open())]


def test_next_journal_number():
    from unittest.mock import patch
    with patch.object(numbering.history, "vouchers", return_value=[]):
        assert numbering.next_number(None, "c", "Journal", "20261022", _numbers()) == "137"


def test_check_company_on_demo_books(tmp_path):
    from types import SimpleNamespace as NS
    from unittest.mock import patch
    from app.engine import healthcheck

    class Live(_Replay):
        host, port, timeout = "localhost", 9000, 5

        def companies(self):
            return [{"name": CO}]

        def voucher_ids(self, company, frm, to):
            return {"1", "2", "3"}

        def voucher_numbers(self, company, vt, frm, to):
            return _numbers()

    r = healthcheck.collect(Live(), CO, "20260401", "20261031", {}, {}, {}, ["Journal"])
    comp = NS(id="c", name=CO, gstin="24AAHCA4821K1ZR")
    with patch.object(numbering.history, "vouchers", return_value=[]):
        checks = healthcheck.evaluate(None, comp, r, {"1", "2"}, 2, {"Journal": "Automatic (Manual Override)"})
    by = {k.title: k for k in checks}
    assert by["Trial Balance matches Tally line by line"].status == "ok"
    assert by["Balance Sheet balances"].status == "ok"
    assert by["Schedule III Balance Sheet balances"].status == "ok"
    assert by["The app's copy of the day book is out of date"].detail.startswith("1 voucher(s)")
    assert "next would be 137" in by["Journal: numbering 'Automatic (Manual Override)'"].detail
    assert not any(k.title == "Foreign-currency balances present" for k in checks)   # INR-only company
