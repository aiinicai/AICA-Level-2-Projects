"""The sample company for TallyPrime: the files balance, and Tally MIS reproduces figures worked out independently."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import make_tally_sample as S  # noqa: E402

from app.engine import reports as R  # noqa: E402
from app.engine.cashflow_ageing import ageing  # noqa: E402
from app.engine.statements import balance_sheet, profit_and_loss  # noqa: E402
from app.model.store import Store  # noqa: E402
from app.sync import Runs, import_files  # noqa: E402


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    out = tmp_path_factory.mktemp("sample")
    books = S.build()
    (out / "m.xml").write_text(S.masters_xml(), encoding="utf-8")
    (out / "v.xml").write_text(S.wrap("Vouchers", "\n".join(books.vouchers)), encoding="utf-8")
    store = Store()
    cid = store.ensure_company(S.COMPANY)
    for f in ("m.xml", "v.xml"):
        run = import_files(store, Runs().new(company_id=cid, mode="file"), cid, [str(out / f)])
        assert run.status == "succeeded", run.error
    yield books, store, R.make_filters(store, cid, "2024-04-01", "2025-09-30", "none")
    store.wipe()


def test_every_voucher_dated_1st_2nd_or_31st():
    for v in S.build().vouchers:
        day = v.split("<DATE>")[1][6:8]
        assert day in ("01", "02", "31"), day  # TallyPrime Educational mode accepts only these


def test_books_balance(loaded):
    _, store, f = loaded
    assert store.scalar("SELECT COUNT(*) FROM vouchers WHERE line_total_paise <> 0") == 0
    assert balance_sheet(f.ctx, "2025-09-30")["totals"]["difference"] == 0


@pytest.mark.parametrize("fy,frm,to", [("24-25", "2024-04-01", "2025-03-31"), ("25-26", "2025-04-01", "2025-09-30")])
def test_profit_and_loss_matches_independent_figures(loaded, fy, frm, to):
    books, _, f = loaded
    e = books.by_fy[fy]
    pl = profit_and_loss(f.ctx, R.DateRange(frm, to)).figures
    assert pl["revenue"].paise == round(e["sales"] * 100)
    assert pl["purchases"].paise == round(e["purchases"] * 100)
    assert pl["netProfit"].paise == round((e["sales"] - e["purchases"] - e["freight"] - sum(e["expenses"].values())) * 100)


def test_balances_match_independent_figures(loaded):
    books, _, f = loaded
    t = balance_sheet(f.ctx, "2025-09-30")["totals"]
    assert t["bank"] == round(books.bal["HDFC Bank"] * 100)
    assert t["tradeReceivables"] == round(sum(s["amt"] for s in books.open_sales) * 100)
    assert t["tradePayables"] == round(sum(p["amt"] for p in books.open_purch) * 100)
    a = ageing(f.ctx, "receivable", "2025-09-30")
    assert a["totals"]["billTotal"] == t["tradeReceivables"] and a["totals"]["billwiseCoveragePct"] == 100
