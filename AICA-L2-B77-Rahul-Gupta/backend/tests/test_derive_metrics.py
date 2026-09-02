"""Metrics a Schedule III statement states only implicitly must be derived.

A Schedule III P&L never prints "EBITDA" or "EBIT", and a Division I balance
sheet presents shareholders' funds as a section rather than a "Net worth" line.
All three were therefore unreachable from a real uploaded document.

That mattered because the valuation fills gaps with constants —
``ebitda_margin or 0.15`` in orchestrator.build_inputs — so a DCF built from real
statements silently ran on an assumed 15% margin instead of the company's own,
and adjusted NAV was dropped for want of net worth. Nothing surfaced either.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.database import Base
from app.models import FinancialLineItem, ValuationCase
from app.services.financial.derive import derive_missing_metrics

LAKH = 100_000.0


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _case(db) -> str:
    case = ValuationCase(company_id="c1", valuation_date="2026-03-31")
    db.add(case)
    db.commit()
    return case.id


def _add(db, case_id: str, metric: str, lakh: float, period: str = "FY2023-24"):
    db.add(FinancialLineItem(case_id=case_id, period_label=period, statement="pnl",
                             metric=metric, python_value=lakh * LAKH))
    db.commit()


def _value(db, case_id: str, metric: str, period: str = "FY2023-24"):
    row = db.execute(select(FinancialLineItem).where(
        FinancialLineItem.case_id == case_id,
        FinancialLineItem.metric == metric,
        FinancialLineItem.period_label == period)).scalars().first()
    return None if row is None else row.python_value


def test_derives_ebit_ebitda_and_net_worth(db):
    """The real fixture's numbers: PBT 80 + interest 24, + dep 28; SC 100 + res 160."""
    case = _case(db)
    for metric, lakh in [("pbt", 80), ("finance_cost", 24), ("depreciation", 28),
                         ("share_capital", 100), ("reserves", 160)]:
        _add(db, case, metric, lakh)

    assert derive_missing_metrics(db, case) == 3
    assert _value(db, case, "ebit") == pytest.approx(104 * LAKH)
    assert _value(db, case, "ebitda") == pytest.approx(132 * LAKH)
    assert _value(db, case, "net_worth") == pytest.approx(260 * LAKH)


def test_chained_derivation_uses_a_just_derived_value(db):
    """EBITDA depends on EBIT, which is itself derived in the same pass."""
    case = _case(db)
    for metric, lakh in [("pbt", 80), ("finance_cost", 24), ("depreciation", 28)]:
        _add(db, case, metric, lakh)
    derive_missing_metrics(db, case)
    assert _value(db, case, "ebitda") == pytest.approx(132 * LAKH)


def test_never_overrides_a_value_read_off_the_statement(db):
    case = _case(db)
    for metric, lakh in [("pbt", 80), ("finance_cost", 24), ("ebit", 999)]:
        _add(db, case, metric, lakh)
    derive_missing_metrics(db, case)
    assert _value(db, case, "ebit") == pytest.approx(999 * LAKH), "stated value must win"


def test_incomplete_components_derive_nothing(db):
    """A partial P&L must not produce a confidently wrong EBIT."""
    case = _case(db)
    _add(db, case, "pbt", 80)  # no finance_cost
    assert derive_missing_metrics(db, case) == 0
    assert _value(db, case, "ebit") is None


def test_derived_rows_say_how_they_were_derived(db):
    case = _case(db)
    for metric, lakh in [("share_capital", 100), ("reserves", 160)]:
        _add(db, case, metric, lakh)
    derive_missing_metrics(db, case)
    row = db.execute(select(FinancialLineItem).where(
        FinancialLineItem.case_id == case,
        FinancialLineItem.metric == "net_worth")).scalars().first()
    assert row.original_label == "Derived: Share Capital + Reserves & Surplus"


def test_each_period_derives_independently(db):
    case = _case(db)
    for period, pbt in [("FY2022-23", 60), ("FY2023-24", 80)]:
        _add(db, case, "pbt", pbt, period)
        _add(db, case, "finance_cost", 20, period)
    derive_missing_metrics(db, case)
    assert _value(db, case, "ebit", "FY2022-23") == pytest.approx(80 * LAKH)
    assert _value(db, case, "ebit", "FY2023-24") == pytest.approx(100 * LAKH)
