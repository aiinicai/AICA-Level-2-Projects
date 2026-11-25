import csv
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from sqlalchemy import select

from app.advisory.commentary import lot_commentary, summary_commentary
from app.advisory.delay_model import fit
from app.core.config import BusinessDefaults
from app.engine.forecast import (COVERED, NO_GAP, NOT_SUFFICIENT, BalanceIn, CategoryIn, FacilityIn, Inputs, ItemIn,
                                 OverrideIn, compute)
from app.engine.lots import ACTUAL, CURRENT, build_lots
from app.engine.loader import run_forecast
from app.importers import exceptions as X
from app.importers.pipeline import import_file
from app.models import Category, Override, OverrideAction
from app.services import overrides as OV
from app.services.settings_service import update_business_settings
from app.services.snapshots import save_snapshot

ROOT = Path(__file__).resolve().parents[1]
DAY1 = ROOT / "synthetic_data" / "day1_2026-11-24"
DAY2 = ROOT / "synthetic_data" / "day2_2026-11-25"
ACC = ROOT / "synthetic_data" / "acceptance"


def S(**kw):
    return BusinessDefaults(**{"horizon_months": 1, **kw})


# ======================================================================== lots
def labels(as_of, **kw):
    return [(lt.label, lt.status) for lt in build_lots(as_of, S(**kw))]


def test_month_thirds_and_horizon_months():
    lots = build_lots(date(2026, 11, 23), S(horizon_months=3))
    assert [lt.label for lt in lots] == ["21-30 Nov", "01-10 Dec", "11-20 Dec", "21-31 Dec",
                                         "01-10 Jan", "11-20 Jan", "21-31 Jan"]
    assert lots[0].status == CURRENT and len(build_lots(date(2026, 11, 23), S(horizon_months=2))) == 4
    assert labels(date(2028, 2, 21))[-1] == ("21-29 Feb", CURRENT)          # leap year
    assert labels(date(2027, 2, 5))[-1][0] == "21-28 Feb"


def test_month_start_shows_locked_actuals():
    got = labels(date(2026, 11, 23), grid_start="month_start")
    assert got == [("01-10 Nov", ACTUAL), ("11-20 Nov", ACTUAL), ("21-30 Nov", CURRENT)]


def test_lot_length_and_fixed_days():
    assert [x[0] for x in labels(date(2026, 11, 3), lot_length_days=7)] == [
        "01-07 Nov", "08-14 Nov", "15-21 Nov", "22-30 Nov"]
    got = labels(date(2026, 11, 23), lot_scheme="fixed_days", lot_length_days=7, horizon_lots=3)
    assert got == [("22-28 Nov", CURRENT), ("29 Nov-05 Dec", "forecast"), ("06-12 Dec", "forecast")]


# ======================================================================== engine (hand-worked figures)
AS_OF = date(2026, 12, 1)
CATS = [CategoryIn(1, "Customer collections", "inflow", "Receipts", 10),
        CategoryIn(2, "Vendor PDCs", "outflow", "Suppliers", 10),
        CategoryIn(3, "Payroll", "outflow", "Staff", 30),
        CategoryIn(4, "Other inflows", "inflow", "Receipts", 20),
        CategoryIn(5, "Rent", "outflow", "Overheads", 40)]


def it(key, d, amt, cat=2, src=None, **kw):
    direction = next(c.direction for c in CATS if c.id == cat)
    src = src or ("collections" if direction == "inflow" else "vendor_pdc")
    return ItemIn(hash(key) % 10 ** 6, src, key, cat, direction, d, D(amt), counterparty=f"Party {key}",
                  reference=key, **kw)


def base_items():
    return [it("C1", date(2026, 12, 5), "50000", cat=1),
            it("P1", date(2026, 12, 3), "30000"),
            it("P2", date(2026, 12, 15), "40000"),
            it("P3", date(2026, 12, 25), "60000"),
            it("PAY", date(2026, 12, 28), "45000", cat=3, src="other"),
            it("OVD", date(2026, 11, 20), "5000"),          # overdue -> current lot
            it("FUT", date(2027, 1, 5), "7000"),            # after the horizon
            it("PAID", date(2026, 12, 4), "999", is_paid=True),
            it("USD", date(2026, 12, 4), "111", currency="USD")]


def run(overrides=(), items=None, **kw):
    return compute(Inputs(as_of=AS_OF, settings=kw.pop("settings", S()), items=items or base_items(),
                          categories=CATS, overrides=list(overrides),
                          balances=[BalanceIn("Bank A", "Current", "OMR", AS_OF, D("100000"))],
                          facilities=[FacilityIn("Bank A", "OD", AS_OF, D("20000"))], **kw))


def hold(key, until=None, amount=None, oid=1, **kw):
    return OverrideIn(oid, "vendor_pdc", key, "hold", new_date=until,
                      new_amount=None if amount is None else D(amount), **kw)


def L(fc, name):
    return [str(v) for v in fc.lines[name]]


def test_lot_arithmetic():
    fc = run()
    assert L(fc, "opening") == ["100000.000", "115000.000", "75000.000"]      # each lot opens with previous close
    assert L(fc, "inflows") == ["50000.000", "0.000", "0.000"]
    assert L(fc, "outflows") == ["35000.000", "40000.000", "105000.000"]      # overdue OVD in the current lot
    assert L(fc, "closing") == ["115000.000", "75000.000", "-30000.000"]
    assert L(fc, "fp_before") == ["135000.000", "95000.000", "-10000.000"]
    assert L(fc, "gap_before") == ["0.000", "0.000", "-10000.000"]
    assert fc.lot_status == [NO_GAP, NO_GAP, NOT_SUFFICIENT]
    st = {i.key: i.status for i in fc.items}
    assert st["FUT"] == "beyond_horizon" and st["PAID"] == "paid" and st["USD"] == "other_currency"
    assert "overdue" in next(i for i in fc.items if i.key == "OVD").flags
    assert any("USD item left out" in w for w in fc.warnings)
    assert [r.name for r in fc.outflow_rows] == ["Vendor PDCs", "Payroll", "Rent"]   # rows from categories
    assert fc.erp_opening + sum(fc.daily_net.values()) == fc.lines["closing_after"][-1]


def test_open_ended_hold_raises_its_lot_and_every_later_lot_by_exactly_the_amount():
    """Acceptance: holding a PDC raises the closing of its lot and every later lot by exactly its amount."""
    before, after = run(), run([hold("P2")])
    for k in ("inflows", "outflows", "closing", "fp_before"):                # rows B-F stay as per ERP
        assert after.lines[k] == before.lines[k]
    diff = [a - b for a, b in zip(after.lines["closing_after"], before.lines["closing"])]
    assert diff == [D(0), D("40000"), D("40000")]
    assert L(after, "hold_out") == ["0.000", "40000.000", "0.000"]
    assert L(after, "holds_open") == ["0.000", "40000.000", "0.000"]
    assert L(after, "fp_after") == ["135000.000", "135000.000", "30000.000"]
    assert after.lot_status == [NO_GAP, NO_GAP, COVERED]
    assert "Open-ended" in after.holds[0].hold.warnings[0]


def test_dated_hold_moves_cheque_to_honouring_lot():
    fc = run([hold("P1", until=date(2026, 12, 25))])
    assert L(fc, "hold_out") == ["30000.000", "0.000", "0.000"]
    assert L(fc, "hold_in") == ["0.000", "0.000", "30000.000"]
    assert L(fc, "hold_cum") == ["30000.000", "30000.000", "0.000"]
    assert L(fc, "closing_after") == ["145000.000", "105000.000", "-30000.000"]
    assert fc.lot_status[2] == NOT_SUFFICIENT
    h = fc.holds[0].hold
    assert h.honour_lot == 2 and h.days_held == 22
    assert any("problem has only moved" in w for w in h.warnings)
    assert fc.kpis["holds_total"] == D("30000") and fc.kpis["holds_not_represented"] == D(0)


def test_partial_hold_and_hold_beyond_horizon():
    fc = run([hold("P3", amount="15000"), hold("P2", until=date(2027, 1, 15), oid=2)])
    assert L(fc, "hold_out") == ["0.000", "40000.000", "15000.000"]
    assert L(fc, "holds_open") == ["0.000", "40000.000", "15000.000"]      # neither re-presented in Dec
    assert L(fc, "fp_after") == ["135000.000", "135000.000", "45000.000"]
    p2 = next(h for h in fc.holds if h.key == "P2").hold
    assert p2.honour_lot is None and "after the horizon" in p2.warnings[0]
    assert fc.kpis["holds_not_represented"] == D("55000")


def test_hold_warnings_and_limits():
    fc = run([hold("P1", until=date(2027, 7, 1), amount="99999")], settings=S(horizon_months=8))
    w = " ".join(fc.holds[0].hold.warnings)
    assert "capped" in w and "may be stale" in w and fc.holds[0].hold.amount == D("30000")
    fc = run([OverrideIn(1, "collections", "C1", "hold")])
    assert fc.holds == [] and any("only payments can be held" in x for x in fc.warnings)


def test_defer_moves_amount_with_no_loss():
    """Acceptance: deferring moves the amount to the chosen lot with no loss."""
    before = run()
    after = run([OverrideIn(1, "vendor_pdc", "P1", "defer", target_lot_start=date(2026, 12, 21))])
    assert L(after, "outflows") == ["5000.000", "40000.000", "135000.000"]
    assert sum(after.lines["outflows"]) == sum(before.lines["outflows"])
    assert L(after, "deferred_in") == ["0.000", "0.000", "30000.000"]
    p1 = next(i for i in after.items if i.key == "P1")
    assert p1.lot == 2 and p1.eff_date == date(2026, 12, 21) and "deferred" in p1.flags


def test_redate_reduce_exclude_recategorise():
    fc = run([OverrideIn(1, "vendor_pdc", "P3", "redate", new_date=date(2026, 12, 2)),
              OverrideIn(2, "vendor_pdc", "P2", "reduce", new_amount=D("10000")),
              OverrideIn(3, "other", "PAY", "exclude"),
              OverrideIn(4, "vendor_pdc", "OVD", "recategorise", new_category_id=5),
              OverrideIn(5, "vendor_pdc", "P1", "recategorise", new_category_id=1)])   # wrong direction
    assert L(fc, "outflows") == ["95000.000", "10000.000", "0.000"]
    rent = next(r for r in fc.outflow_rows if r.name == "Rent")
    assert str(rent.values[0]) == "5000.000"
    assert next(i for i in fc.items if i.key == "PAY").status == "excluded"
    assert any("recategorise ignored" in w for w in fc.warnings)


def test_bill_discounted_and_risk_scenario():
    items = base_items() + [it("C2", date(2026, 12, 12), "8000", cat=1, risk_flag=True),
                            it("C3", date(2026, 12, 13), "3000", cat=1, bill_discounted=True)]
    ovr = [OverrideIn(1, "collections", "C1", "risk_adjusted")]
    base, risk = run(ovr, items=items), run(ovr, items=items, exclude_risk=True)
    assert L(base, "inflows") == ["50000.000", "8000.000", "0.000"]          # C3 never counted
    assert L(risk, "inflows") == ["0.000", "0.000", "0.000"]
    assert L(risk, "risk_excluded") == ["50000.000", "8000.000", "0.000"]
    assert next(i for i in risk.items if i.key == "C3").status == "bill_discounted"


def test_pending_override_is_not_applied():
    fc = run([hold("P2", approval="pending")])
    assert fc.holds == [] and "pending approval: hold pending" in next(i for i in fc.items if i.key == "P2").flags


def test_month_and_horizon_totals():
    fc = run([hold("P2")], settings=S(horizon_months=2))
    cols = fc.columns
    assert [c.label for c in cols] == ["01-10 Dec", "11-20 Dec", "21-31 Dec", "Dec 2026 total",
                                       "01-10 Jan", "11-20 Jan", "21-31 Jan", "Jan 2027 total", "Horizon total"]
    dec, jan, hz = cols[3], cols[7], cols[8]
    assert fc.line("opening", dec) == D("100000") and fc.line("closing", dec) == fc.lines["closing"][2]
    assert fc.line("outflows", dec) == D("180000") and fc.line("gap_before", dec) == D("-10000")
    assert fc.line("outflows", hz) == fc.line("outflows", dec) + fc.line("outflows", jan)
    assert fc.line("closing_after", hz) == fc.lines["closing_after"][-1]
    assert fc.status(dec) == COVERED
    pdc = fc.outflow_rows[0]
    assert fc.row(pdc, dec) == D("135000") and fc.row(pdc, jan) == D("7000")      # payroll is its own row
    partial = compute(Inputs(as_of=date(2026, 12, 14), settings=S(), items=[], categories=CATS)).columns
    assert partial[-2].label == "Dec 2026 total *" and partial[-2].partial


def test_tieout_against_previous_snapshot():
    prev = run().to_dict()
    nxt = compute(Inputs(as_of=date(2026, 12, 6), settings=S(), items=base_items(), categories=CATS,
                         balances=[BalanceIn("Bank A", "Current", "OMR", date(2026, 12, 6), D("114500"))],
                         previous={"as_of": prev["as_of"], "opening": prev["erp_opening"],
                                   "daily_net": prev["daily_net"]}))
    t = nxt.tieout["previous"]
    # expected by 6 Dec: 100,000 - 5,000 (overdue, 1 Dec) - 30,000 (3 Dec) + 50,000 (5 Dec) = 115,000
    assert t["expected"] == D("115000") and t["variance"] == D("-500")


def test_fx_opening_and_commentary():
    fc = compute(Inputs(as_of=AS_OF, settings=S(), items=base_items(), categories=CATS,
                        balances=[BalanceIn("Bank A", "Cur", "OMR", AS_OF, D("1000")),
                                  BalanceIn("Bank D", "USD", "USD", AS_OF, D("1000"), D("0.3845"))]))
    assert fc.erp_opening == D("1384.500")
    text = lot_commentary(fc)
    assert "largest outflow is Vendor PDCs" in text[0] and "gap" in text[2]
    assert "No cheques are on hold yet" in summary_commentary(fc)


# ======================================================================== database: acceptance tests
def imp(db, source, path, **kw):
    rep = import_file(db, source, path.name, path.read_bytes(), **kw)
    db.commit()
    assert rep.status in ("accepted", "exceptions"), rep.issues
    return rep


@pytest.fixture
def day1(db):
    for src, f in [("category_list", "category_list.xlsx"), ("bank_balances", "bank_balances.csv"),
                   ("bank_facility", "bank_facility.csv"), ("collections", "erp_receivables.xlsx"),
                   ("vendor_pdc", "erp_pdc_register.xlsx")]:
        imp(db, src, DAY1 / f)
    return db


def test_seventy_pdcs_reproduce_hand_worked_lot_totals(db):
    """Acceptance: ~70 PDCs reproduce the hand-worked lot totals."""
    imp(db, "category_list", DAY1 / "category_list.xlsx")
    imp(db, "vendor_pdc", ACC / "pdc_month_2026_12.xlsx")
    expected = list(csv.DictReader((ACC / "pdc_month_2026_12_expected.csv").open()))
    fc = run_forecast(db, as_of=date(2026, 12, 1), settings=S())
    pdc_row = next(r for r in fc.outflow_rows if r.name == "Vendor PDCs")
    assert sum(1 for i in fc.items if i.status == "active") == 70
    for i, e in enumerate(expected):
        assert fc.fc_lots[i].start.isoformat() == e["start"] and fc.fc_lots[i].end.isoformat() == e["end"]
        assert str(pdc_row.values[i]) == e["total"]
        assert sum(1 for x in fc.items if x.lot == i) == int(e["count"])


def test_hold_service_extend_release_and_history(day1):
    db = day1
    fc0 = run_forecast(db)
    pdc = next(i for i in fc0.items if i.source == "vendor_pdc" and i.lot == 1)
    with pytest.raises(OV.OverrideError, match="honouring date"):
        OV.hold_cheque(db, pdc.key, honour_date=None)
    with pytest.raises(OV.OverrideError, match="after the cheque date"):
        OV.hold_cheque(db, pdc.key, honour_date=pdc.item.planned_date)
    with pytest.raises(OV.OverrideError, match="at most"):
        OV.hold_cheque(db, pdc.key, honour_date=date(2027, 1, 5), amount=pdc.eff_amount + 1)
    OV.hold_cheque(db, pdc.key, honour_date=date(2026, 12, 15), reason="Await delivery note")
    OV.hold_cheque(db, pdc.key, honour_date=date(2027, 1, 5), reason="Extended")       # extension
    db.commit()
    fc = run_forecast(db)
    h = fc.holds[0].hold
    assert h.times_extended == 1 and h.honour_date == date(2027, 1, 5) and h.reason == "Extended"
    assert fc.lines["closing"] == fc0.lines["closing"]
    assert fc.lines["closing_after"][1] - fc0.lines["closing"][1] == pdc.eff_amount
    assert len(db.scalars(select(Override).where(Override.source_key == pdc.key)).all()) == 2
    OV.release_hold(db, pdc.key)
    db.commit()
    assert run_forecast(db).holds == []
    sug = OV.suggest_honour_dates(db, date(2026, 12, 3), date(2026, 11, 24))
    assert sug.default == date(2026, 12, 13) and sug.next_lot == date(2026, 12, 11)


def test_defer_service_validates_target_lot(day1):
    db = day1
    key = next(i.key for i in run_forecast(db).items if i.source == "vendor_pdc")
    with pytest.raises(OV.OverrideError, match="choose one of the forecast lots"):
        OV.set_override(db, "vendor_pdc", key, "defer", target_lot_start=date(2026, 12, 5))
    OV.set_override(db, "vendor_pdc", key, "defer", target_lot_start=date(2026, 12, 21))
    with pytest.raises(OV.OverrideError, match="collections only"):
        OV.set_override(db, "vendor_pdc", key, "risk_adjusted")
    with pytest.raises(OV.OverrideError, match="not in the current data"):
        OV.set_override(db, "vendor_pdc", "NOPE", "exclude")


def test_reupload_keeps_hold_in_forecast(day1):
    db = day1
    key = next(i.key for i in run_forecast(db).items if i.source == "vendor_pdc" and i.lot == 2)
    OV.hold_cheque(db, key, honour_date=date(2027, 1, 15))
    db.commit()
    imp(db, "vendor_pdc", DAY2 / "erp_pdc_register.xlsx")
    fc = run_forecast(db, as_of=date(2026, 11, 24))
    assert [h.key for h in fc.holds] == [key]


def test_new_category_appears_in_report_after_mapping(day1):
    """Acceptance: a new category header appears in the report after mapping."""
    db = day1
    rep = imp(db, "other", DAY1 / "other_recurring_long.xlsx")
    assert "Marketing campaign" not in [r.name for r in run_forecast(db).rows]
    X.add_new_category(db, rep.exceptions[0]["id"], direction="outflow", summary_group="Overheads")
    db.commit()
    row = next(r for r in run_forecast(db).outflow_rows if r.name == "Marketing campaign")
    assert sum(row.values) > 0


def test_approver_switch_makes_overrides_pending(day1):
    db = day1
    update_business_settings(db, {"approver_enabled": True})
    key = next(i.key for i in run_forecast(db).items if i.source == "vendor_pdc")
    OV.set_override(db, "vendor_pdc", key, "exclude")
    db.commit()
    assert all(i.status != "excluded" for i in run_forecast(db).items)


def test_snapshots_lock_actual_lots_and_feed_tieout(day1):
    db = day1
    first = run_forecast(db, as_of=date(2026, 11, 12))
    s1 = save_snapshot(db, first, snapshot_date=date(2026, 11, 12))
    again = save_snapshot(db, first, snapshot_date=date(2026, 11, 12))          # same day: replaced
    assert again.id == s1.id
    db.commit()
    update_business_settings(db, {"grid_start": "month_start"})
    fc = run_forecast(db, as_of=date(2026, 11, 24))
    assert [lt.status for lt in fc.lots[:3]] == [ACTUAL, ACTUAL, CURRENT]
    assert date(2026, 11, 11) in fc.locked and date(2026, 11, 1) not in fc.locked
    assert fc.locked[date(2026, 11, 11)]["lines"]["closing"] == str(first.lines["closing"][0])
    t = fc.tieout["previous"]
    moved = sum((v for d, v in first.daily_net.items() if date(2026, 11, 12) <= d < date(2026, 11, 24)), D(0))
    assert t["movement"] == moved and t["variance"] == fc.erp_opening - (first.erp_opening + moved)


def test_delay_model_learns_and_falls_back(day1):
    db = day1
    imp(db, "payment_history", DAY1 / "payment_history.xlsx")
    m = fit(db)
    assert m.rows == 414 and m.mae_days is not None and m.mae_days < 15
    assert m.predict_days("Unknown customer", 1000)[1].startswith("due date")
    fc = run_forecast(db, use_delay_model=True)
    moved = [i for i in fc.items if "model date" in i.flags]
    assert moved and all(i.eff_date > i.item.planned_date for i in moved)
    assert sum(r.values[0] for r in fc.inflow_rows) != sum(r.values[0] for r in run_forecast(db).inflow_rows)
