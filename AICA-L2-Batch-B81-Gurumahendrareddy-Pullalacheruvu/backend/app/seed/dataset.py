"""Seeded demonstration dataset — Northwind Robotics Pvt Ltd.

An 18-month startup ledger (Mar-2025 → Aug-2026) built so that the numbers on
every screen actually tie:

  * Bank balances are derived from the ledger, not asserted separately.
  * The opening balance is back-solved so the closing position hits the target.
  * Receivables, payables and statutory dues are real open items with real
    due dates, so ageing, weighted collections and the 13-week calendar are
    computed from data rather than hard-coded.

The story the data tells, deliberately:
  Series A closed Feb-2025. Cash is now ₹ 4.62 Cr with ₹ 45 L lien-marked.
  Net burn is ₹ ~62 L and rising. Runway is under 7 months, which puts the
  fundraise trigger date in the past week. One client is 36% of receivables
  and 47 days late on ₹ 84 L. GST of ₹ 22 L falls due on 20-Sep with a
  funding gap. That is a company that needs this tool.
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import (
    Account, ActivityLog, Alert, AlertDelivery, AlertRule, BankAccount,
    BankBalanceHistory, Bill, BoardPack, BurnCategory, CollectionPerformance,
    Commitment, CommitmentType, CostNature, Covenant, Criticality, Customer,
    Definition, EmployeeLiability, Entity, ExpectedInflow, Facility,
    ForecastSnapshot, FunctionCost, FundingRound, HeadcountMonth,
    HiringPlanItem, Invoice, LedgerEntry, NextRaise, Plan, PlanLine, Receipt,
    RepaymentScheduleItem, Role, Scenario, ScoreHistory, Setting,
    StatutoryDue, StatutoryHead, SyncRun, UnbilledWork, User, VarianceNote,
    VarianceType, Vendor,
)
from app.seed import reference as ref

# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------
TODAY = date(2026, 9, 4)
AS_ON = date(2026, 8, 31)            # books closed to here
HISTORY_START = date(2025, 3, 1)
TARGET_CLOSING_CASH = 46_200_000.0   # ₹ 4.62 Cr total incl. the lien-marked FD
FD_RESTRICTED = 4_500_000.0          # ₹ 45 L (lien against the OD facility)
UNRECONCILED = 320_000.0             # books exceed bank by this (cheques not presented)

L = 100_000.0      # one lakh
CR = 10_000_000.0  # one crore

rng = random.Random(20260904)


def months_between(start: date, end: date) -> list[date]:
    out, cur = [], date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur += relativedelta(months=1)
    return out


MONTHS = months_between(HISTORY_START, AS_ON)          # 18 months
N = len(MONTHS)


def month_end(d: date) -> date:
    return (date(d.year, d.month, 1) + relativedelta(months=1)) - timedelta(days=1)


def jitter(pct: float = 0.06) -> float:
    return 1.0 + rng.uniform(-pct, pct)


# ---------------------------------------------------------------------------
# Monthly financial model
# ---------------------------------------------------------------------------
def build_monthly_model() -> list[dict]:
    """Per-month category spend and collections, growing over 18 months."""
    rows = []
    for i, m in enumerate(MONTHS):
        # Scale note: Northwind bills ~₹ 1.9 Cr a month and is people-heavy, so
        # input credit is thin and net GST is large. That is what makes a
        # ₹ 22 L GST liability arithmetically consistent with the revenue line.
        t = i / max(N - 1, 1)                       # 0 .. 1 across the period
        people = (96 * L) + (44 * L) * t            # 96 L -> 140 L
        tech = (13 * L) + (7 * L) * t               # 13 -> 20
        delivery = (19 * L) + (9 * L) * t           # 19 -> 28
        facilities = (6.5 * L) + (1.5 * L) * t
        marketing = (6.5 * L) + (3.5 * L) * t
        professional = (3.0 * L) + (1.0 * L) * t
        statutory = (23 * L) + (10 * L) * t         # net GST + PF + ESI + PT + TDS
        finance = (1.0 * L) + (4.0 * L) * t         # steps up once debt is drawn
        other = (3.0 * L) + (1.0 * L) * t
        collections = (130 * L) + (60 * L) * t      # 1.30 Cr -> 1.90 Cr

        spend = {
            BurnCategory.PEOPLE: people * jitter(0.03),
            BurnCategory.TECH: tech * jitter(0.10),
            BurnCategory.DELIVERY: delivery * jitter(0.16),
            BurnCategory.FACILITIES: facilities * jitter(0.04),
            BurnCategory.MARKETING: marketing * jitter(0.22),
            BurnCategory.PROFESSIONAL: professional * jitter(0.25),
            BurnCategory.STATUTORY: statutory * jitter(0.08),
            BurnCategory.FINANCE_COST: (finance if i >= 7 else 0.4 * L) * jitter(0.05),
            BurnCategory.OTHER: other * jitter(0.18),
        }
        rows.append(dict(month=m, spend=spend, collections=collections * jitter(0.11)))
    return rows


# One-off items, deliberately visible so the "recurring vs one-off" split has
# something to show and the Reclassify button has something to act on.
ONE_OFFS = [
    dict(month=date(2025, 11, 1), day=18, amount=-35 * L, party="Northwind ESOP Trust",
         category=BurnCategory.PEOPLE, narration="ESOP buy-back - 2025 liquidity window",
         classified_by="Meera Iyer"),
    dict(month=date(2026, 1, 1), day=22, amount=-28 * L, party="Studio Kaarya Interiors",
         category=BurnCategory.FACILITIES, narration="Office fit-out, Whitefield floor 4",
         classified_by="Meera Iyer"),
    dict(month=date(2026, 5, 1), day=14, amount=-22 * L, party="Rao & Associates",
         category=BurnCategory.PROFESSIONAL, narration="Settlement of ex-vendor claim",
         classified_by="Guru Mahendra"),
    dict(month=date(2025, 10, 1), day=9, amount=500 * L, party="Alteria Capital",
         category=BurnCategory.FINANCE_COST, narration="Venture debt tranche 1 drawn",
         classified_by="Meera Iyer"),
    dict(month=date(2026, 3, 1), day=27, amount=-18 * L, party="Bharat Metro Rail Corp",
         category=BurnCategory.DELIVERY, narration="Site rework at Phase-2 depot (non-billable)",
         classified_by="Guru Mahendra"),
]


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------
CUSTOMERS = [
    # name, terms, owner, segment, pay_behaviour_days, share_of_revenue
    ("Bharat Metro Rail Corporation", 45, "Anand Rao", "Infrastructure", 62, 0.16),
    ("Sundaram Precision Works Ltd", 30, "Anand Rao", "Manufacturing", 41, 0.19),
    ("Kaveri Cement Industries Ltd", 45, "Priya Nair", "Manufacturing", 58, 0.15),
    ("GreenGrid Energy Pvt Ltd", 30, "Priya Nair", "Energy", 34, 0.13),
    ("Deccan Logistics Park LLP", 30, "Anand Rao", "Logistics", 47, 0.11),
    ("Vertex Semiconductor India", 60, "Priya Nair", "Electronics", 66, 0.09),
    ("Northstar Warehousing Pvt Ltd", 30, "Anand Rao", "Logistics", 29, 0.07),
    ("Ashwin Textiles Mills Ltd", 45, "Priya Nair", "Manufacturing", 62, 0.04),
]

VENDORS = [
    # name, terms, criticality, category
    ("Amazon Web Services India", 15, Criticality.HIGH, BurnCategory.TECH),
    ("Atlassian Pty Ltd", 30, Criticality.MEDIUM, BurnCategory.TECH),
    ("Datadog India Pvt Ltd", 30, Criticality.MEDIUM, BurnCategory.TECH),
    ("Sentinel Security Labs", 30, Criticality.MEDIUM, BurnCategory.TECH),
    ("Prestige Tech Park Ltd", 5, Criticality.HIGH, BurnCategory.FACILITIES),
    ("BESCOM", 10, Criticality.HIGH, BurnCategory.FACILITIES),
    ("Sparkle Facility Services", 30, Criticality.LOW, BurnCategory.FACILITIES),
    ("Velocity Talent Partners", 45, Criticality.LOW, BurnCategory.PEOPLE),
    ("Zenith Contract Engineering", 30, Criticality.HIGH, BurnCategory.DELIVERY),
    ("Mahalaxmi Sensor Systems", 45, Criticality.HIGH, BurnCategory.DELIVERY),
    ("Yatra Corporate Travel", 15, Criticality.LOW, BurnCategory.DELIVERY),
    ("Hivemind Digital LLP", 30, Criticality.LOW, BurnCategory.MARKETING),
    ("IndiaTech Summit Events", 30, Criticality.LOW, BurnCategory.MARKETING),
    ("Rao & Associates", 30, Criticality.MEDIUM, BurnCategory.PROFESSIONAL),
    ("Krishnan & Co, Chartered Accountants", 30, Criticality.HIGH, BurnCategory.PROFESSIONAL),
    ("Bajaj Allianz General Insurance", 15, Criticality.MEDIUM, BurnCategory.OTHER),
]

FUNCTIONS = [
    # function, headcount at Aug-26, fully loaded cost per head per month
    ("Engineering", 45, 1.62 * L),
    ("Sales & Marketing", 20, 1.48 * L),
    ("Operations", 20, 1.05 * L),
    ("G&A", 10, 1.35 * L),
]

USERS = [
    ("Guru Mahendra Reddy", "guru@northwindrobotics.in", "cashrunway", Role.CFO, "+919900112233"),
    ("Meera Iyer", "meera@northwindrobotics.in", "cashrunway", Role.FINANCE, "+919900112244"),
    ("Vikram Shenoy", "vikram@northwindrobotics.in", "cashrunway", Role.ADMIN, "+919900112255"),
    ("Rohan Kapadia", "rohan@northstarventures.in", "cashrunway", Role.BOARD, "+919900112266"),
]


def seed_users(db: Session) -> int:
    """Create the sign-in accounts and nothing else.

    A database with no accounts is a dead application — sign-in fails with no
    explanation because there is nobody to check the password against. So the
    accounts are bootstrapped on first start, and the *data* is a separate
    decision the person makes on the first-run screen: load the demonstration
    company, or set up their own.
    """
    from app.core.security import hash_password

    if db.query(User).count():
        return 0
    for name, email, pwd, role, phone in USERS:
        db.add(User(name=name, email=email, password_hash=hash_password(pwd),
                    role=role, phone=phone, is_active=True))
    db.commit()
    return len(USERS)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def seed_all(db: Session, wipe: bool = True) -> dict:
    from app.core.security import hash_password

    if wipe:
        _wipe(db)

    stats: dict[str, int] = {}

    # -- users -------------------------------------------------------------
    for name, email, pwd, role, phone in USERS:
        db.add(User(name=name, email=email, password_hash=hash_password(pwd),
                    role=role, phone=phone, is_active=True))
    db.flush()
    stats["users"] = len(USERS)

    # -- entities ----------------------------------------------------------
    india = Entity(name="Northwind Robotics Pvt Ltd", code="IN", currency="INR",
                   fx_to_inr=1.0, is_consolidated=False, tally_company="Northwind Robotics Pvt Ltd",
                   min_cash_floor=20_000_000.0, sort_order=1,
                   books_closed_upto=AS_ON,
                   last_data_update=datetime(2026, 9, 4, 7, 20))
    sg = Entity(name="Northwind Robotics Pte Ltd", code="SG", currency="SGD",
                fx_to_inr=66.4, is_consolidated=False, tally_company=None,
                min_cash_floor=2_000_000.0, sort_order=2,
                books_closed_upto=AS_ON,
                last_data_update=datetime(2026, 9, 3, 18, 5))
    con = Entity(name="Consolidated", code="CONS", currency="INR", fx_to_inr=1.0,
                 is_consolidated=True, min_cash_floor=22_000_000.0, sort_order=3,
                 books_closed_upto=AS_ON,
                 last_data_update=datetime(2026, 9, 4, 7, 20))
    db.add_all([india, sg, con])
    db.flush()
    stats["entities"] = 3

    # -- reference ---------------------------------------------------------
    _seed_definitions(db)
    accounts = _seed_accounts(db, india)
    _seed_settings(db, india)
    stats["accounts"] = len(accounts)

    # -- masters -----------------------------------------------------------
    customers = _seed_customers(db, india)
    vendors = _seed_vendors(db, india)
    stats["customers"] = len(customers)
    stats["vendors"] = len(vendors)

    # -- transactions ------------------------------------------------------
    model = build_monthly_model()
    # Receivables first: the ledger posts the actual receipts against invoices,
    # so collections on screen and cash in the bank can never disagree.
    receipts = _seed_receivables(db, india, customers, model)
    stats["receipts"] = len(receipts)

    entries, monthly_net = _seed_ledger(db, india, accounts, model, customers,
                                        vendors, receipts)
    stats["ledger_entries"] = len(entries)

    opening_cash = _back_solve_opening(monthly_net)
    banks = _seed_banks(db, india, opening_cash, monthly_net)
    stats["bank_accounts"] = len(banks)

    _seed_people(db, india, model)
    _seed_payables(db, india, vendors)
    _seed_capital(db, india)
    _seed_planning(db, india, model)
    _seed_alerts(db, india)
    _seed_activity(db, india)

    # Light dataset for the Singapore entity so the dropdown is not a dead end.
    _seed_singapore(db, sg)

    db.commit()
    stats["opening_cash"] = int(opening_cash)
    stats["closing_cash"] = int(TARGET_CLOSING_CASH)
    return stats


def _wipe(db: Session) -> None:
    from app.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
def _seed_definitions(db: Session) -> None:
    for d in ref.DEFINITIONS:
        db.add(Definition(term=d["term"], plain_english=d["plain_english"],
                          formula=d.get("formula"), basis_note=d.get("basis_help"),
                          category=d.get("category", "General"),
                          updated_by="Guru Mahendra Reddy"))
    db.flush()


def _seed_accounts(db: Session, entity: Entity) -> dict[str, Account]:
    out: dict[str, Account] = {}
    for name, group, cls, sub, cat, nature, is_cash in ref.CHART_OF_ACCOUNTS:
        a = Account(entity_id=entity.id, name=name, parent_group=group,
                    classification=cls, sub_type=sub, burn_category=cat,
                    cost_nature=nature, is_cash=is_cash,
                    external_id=f"TALLY-{abs(hash(name)) % 10**8:08d}")
        db.add(a)
        out[name] = a
    db.flush()
    return out


def _seed_settings(db: Session, entity: Entity) -> None:
    rows = [
        ("min_cash_floor", "20000000", "number", "Minimum cash floor (₹)"),
        ("fundraise_lead_months", "6", "number", "Months of lead time to close a round"),
        ("bank_concentration_threshold", "0.60", "number", "Flag when one bank holds more than"),
        ("client_concentration_threshold", "0.25", "number", "Flag when one client exceeds this share of AR"),
        ("books_bank_amber", "200000", "number", "Books vs bank amber threshold (₹)"),
        ("books_bank_red", "1000000", "number", "Books vs bank red threshold (₹)"),
        ("austerity_cut_pct", "35", "number", "Discretionary cut assumed in the austerity case (%)"),
        ("sync_schedule", "Every 4 hours, 06:00–22:00 IST", "string", "Accounting sync schedule"),
    ]
    for k, v, t, label in rows:
        db.add(Setting(entity_id=entity.id, key=k, value=v, value_type=t,
                       label=label, updated_by="Vikram Shenoy"))
    db.flush()


def _seed_customers(db: Session, entity: Entity) -> list[Customer]:
    out = []
    for name, terms, owner, segment, behaviour, share in CUSTOMERS:
        c = Customer(entity_id=entity.id, name=name, credit_terms_days=terms,
                     owner=owner, segment=segment,
                     contact_person=f"{name.split()[0]} Finance Desk",
                     last_contact=AS_ON - timedelta(days=rng.randint(2, 40)),
                     source="tally", created_by="Tally sync",
                     notes=f"Typically pays in ~{behaviour} days against {terms}-day terms.")
        db.add(c)
        out.append(c)
    db.flush()
    return out


def _seed_vendors(db: Session, entity: Entity) -> list[Vendor]:
    out = []
    for name, terms, crit, cat in VENDORS:
        v = Vendor(entity_id=entity.id, name=name, credit_terms_days=terms,
                   criticality=crit, burn_category=cat, on_hold=False,
                   source="tally", created_by="Tally sync")
        db.add(v)
        out.append(v)
    db.flush()
    return out


# ---------------------------------------------------------------------------
# Receivables — invoices and receipts drive both AR ageing and cash inflow
# ---------------------------------------------------------------------------
def _seed_receivables(db: Session, entity: Entity, customers: list[Customer],
                      model: list[dict]) -> list[dict]:
    """Generate 18 months of invoices and the receipts against them.

    Returns the receipt rows so the ledger generator can post the actual cash
    inflows rather than an assumed collections figure.
    """
    behaviour = {n: b for (n, t, o, s, b, sh) in CUSTOMERS}
    share = {n: sh for (n, t, o, s, b, sh) in CUSTOMERS}
    receipts_out: list[dict] = []
    inv_seq = 1000

    for i, row in enumerate(model):
        m = row["month"]
        billed_total = row["collections"] * 1.15
        for c in customers:
            amt = billed_total * share[c.name] * jitter(0.20)
            if amt < 40_000:
                continue
            inv_seq += 1
            inv_date = m + timedelta(days=rng.randint(3, 26))
            due = inv_date + timedelta(days=c.credit_terms_days)
            beh = behaviour[c.name]
            # Actual payment date = behaviour days from invoice, with spread
            pay_date = inv_date + timedelta(days=max(int(beh * jitter(0.28)), 8))

            inv = Invoice(
                entity_id=entity.id, customer_id=c.id, invoice_no=f"NWR/26/{inv_seq}",
                invoice_date=inv_date, due_date=due, amount=round(amt, 2),
                outstanding=round(amt, 2), status="open",
                source="tally", created_by="Tally sync",
                external_id=f"TLY-INV-{inv_seq}",
            )
            db.add(inv)
            db.flush()

            if pay_date <= AS_ON:
                db.add(Receipt(entity_id=entity.id, invoice_id=inv.id, customer_id=c.id,
                               received_on=pay_date, amount=round(amt, 2),
                               mode="NEFT", reference=f"UTR{rng.randint(10**9, 10**10 - 1)}",
                               source="tally", created_by="Tally sync"))
                inv.outstanding = 0.0
                inv.status = "paid"
                receipts_out.append(dict(date=pay_date, amount=amt, party=c.name))
            else:
                # Still open at the as-on date — this is the live AR book.
                inv.collection_probability = _probability(inv.due_date, beh)

    db.flush()
    _apply_ar_narrative(db, entity, customers)
    _seed_ar_extras(db, entity, customers, model)
    return receipts_out


def _probability(due: date, behaviour_days: int) -> float:
    """How likely is this to arrive in the next 30 days, given how this client
    actually behaves? Overridable by a human in the UI."""
    days_late = (AS_ON - due).days
    if days_late < -30:
        base = 0.45
    elif days_late < 0:
        base = 0.72
    elif days_late < 30:
        base = 0.80
    elif days_late < 60:
        base = 0.62
    elif days_late < 90:
        base = 0.44
    else:
        base = 0.28
    if behaviour_days > 75:
        base *= 0.85
    elif behaviour_days < 35:
        base = min(base * 1.12, 0.95)
    return round(base, 2)


def _apply_ar_narrative(db: Session, entity: Entity, customers: list[Customer]) -> None:
    """Plant the specific facts the CFO called out: a ₹ 84 L invoice 47 days
    overdue from the largest client, and two genuine disputes."""
    bmrc = next(c for c in customers if c.name.startswith("Bharat Metro"))
    ashwin = next(c for c in customers if c.name.startswith("Ashwin"))
    vertex = next(c for c in customers if c.name.startswith("Vertex"))

    # The headline overdue invoice
    hero_due = AS_ON - timedelta(days=47)
    db.add(Invoice(
        entity_id=entity.id, customer_id=bmrc.id, invoice_no="NWR/26/0947",
        invoice_date=hero_due - timedelta(days=45), due_date=hero_due,
        amount=8_400_000.0, outstanding=8_400_000.0, status="open",
        collection_probability=0.55, promised_date=date(2026, 9, 22),
        promised_amount=5_000_000.0,
        source="tally", created_by="Tally sync", external_id="TLY-INV-0947",
    ))

    # A real AR book has a tail. Without these the 61–90 and 90+ buckets sit
    # empty and the ageing chart says nothing.
    deccan = next(c for c in customers if c.name.startswith("Deccan"))
    kaveri = next(c for c in customers if c.name.startswith("Kaveri"))
    sundaram = next(c for c in customers if c.name.startswith("Sundaram"))
    aged = [
        (bmrc, "NWR/26/0881", 71, 2_640_000, 0.48,
         "Retention against Phase-1; client says it releases on final completion certificate."),
        (vertex, "NWR/26/0855", 84, 1_180_000, 0.42, None),
        (kaveri, "NWR/26/0798", 96, 1_920_000, 0.34,
         "Client's plant shutdown pushed their whole payment cycle."),
        (ashwin, "NWR/26/0764", 128, 740_000, 0.22,
         "Repeatedly promised and not paid. Candidate for legal notice."),
        (deccan, "NWR/26/0902", 63, 1_350_000, 0.55, None),
        (sundaram, "NWR/26/0921", 38, 2_080_000, 0.72, None),
    ]
    for cust, no, days_late, amt, prob, note in aged:
        due = AS_ON - timedelta(days=days_late)
        db.add(Invoice(
            entity_id=entity.id, customer_id=cust.id, invoice_no=no,
            invoice_date=due - timedelta(days=cust.credit_terms_days),
            due_date=due, amount=float(amt), outstanding=float(amt),
            status="open", collection_probability=prob,
            source="tally", created_by="Tally sync",
        ))
        if note:
            cust.notes = f"{cust.notes or ''} {no}: {note}".strip()

    # Disputes — never mixed into ageing (SPEC 4)
    db.add(Invoice(
        entity_id=entity.id, customer_id=ashwin.id, invoice_no="NWR/26/0812",
        invoice_date=date(2026, 4, 18), due_date=date(2026, 6, 2),
        amount=1_640_000.0, outstanding=1_640_000.0, status="disputed",
        is_disputed=True, dispute_reason="Client disputes 220 sensor units billed but not commissioned at Unit-2.",
        dispute_raised_on=date(2026, 6, 14), dispute_owner="Anand Rao",
        expected_resolution=date(2026, 10, 15), collection_probability=0.35,
        source="manual", created_by="Anand Rao",
    ))
    db.add(Invoice(
        entity_id=entity.id, customer_id=vertex.id, invoice_no="NWR/26/0863",
        invoice_date=date(2026, 5, 9), due_date=date(2026, 7, 8),
        amount=920_000.0, outstanding=920_000.0, status="disputed",
        is_disputed=True, dispute_reason="Rate revision under the FY27 MSA not reflected; client withholding the differential.",
        dispute_raised_on=date(2026, 7, 21), dispute_owner="Priya Nair",
        expected_resolution=date(2026, 9, 30), collection_probability=0.60,
        source="manual", created_by="Priya Nair",
    ))
    db.flush()


def _seed_ar_extras(db: Session, entity: Entity, customers: list[Customer],
                    model: list[dict]) -> None:
    # Invoicing gap — cash we are sitting on by our own delay (SPEC 4)
    gaps = [
        ("Bharat Metro Rail Corporation", "Phase-2 depot commissioning, milestone 3", 3_150_000.0, 41,
         "Client sign-off sheet pending from site engineer", "Anand Rao"),
        ("GreenGrid Energy Pvt Ltd", "August AMC and remote monitoring", 620_000.0, 12,
         "Awaiting PO amendment for revised rate", "Priya Nair"),
        ("Deccan Logistics Park LLP", "Retrofit of 14 dock sensors", 880_000.0, 26,
         "Delivery note not returned by client stores", "Anand Rao"),
        ("Sundaram Precision Works Ltd", "Q2 usage-based overage", 470_000.0, 8,
         "Usage report being reconciled", "Meera Iyer"),
    ]
    for cname, desc, amt, days, blocker, owner in gaps:
        c = next(x for x in customers if x.name == cname)
        db.add(UnbilledWork(entity_id=entity.id, customer_id=c.id, description=desc,
                            amount=amt, delivered_on=AS_ON - timedelta(days=days),
                            expected_invoice_date=AS_ON + timedelta(days=rng.randint(4, 20)),
                            blocker=blocker, owner=owner,
                            source="manual", created_by=owner))

    # Promised vs actually received, last 6 months (SPEC 4)
    perf = [(0.86, 0.92), (0.79, 0.95), (0.91, 0.88), (0.74, 0.90), (0.81, 0.86), (0.69, 0.83)]
    for k, (recv_ratio, target_ratio) in enumerate(perf):
        m = date(2026, 3, 1) + relativedelta(months=k)
        row = next((r for r in model if r["month"] == m), None)
        base = row["collections"] if row else 70 * L
        promised = base * 1.18
        db.add(CollectionPerformance(entity_id=entity.id, month=m,
                                     promised=round(promised, 2),
                                     received=round(promised * recv_ratio, 2),
                                     target=round(promised / max(target_ratio, 0.1) * 0.9, 2)))

    # Non-AR expected inflows (manual register)
    db.add_all([
        ExpectedInflow(entity_id=entity.id, description="GST refund - FY25-26 inverted duty claim",
                       inflow_type="Refund", expected_on=date(2026, 10, 12), amount=1_850_000.0,
                       probability=0.7, counterparty="GST Department",
                       source="manual", created_by="Meera Iyer",
                       notes="Filed 22-Jul-26. Officer has raised no query so far."),
        ExpectedInflow(entity_id=entity.id, description="Security deposit release - old Koramangala office",
                       inflow_type="Deposit Release", expected_on=date(2026, 9, 25), amount=1_200_000.0,
                       probability=0.85, counterparty="Sterling Estates",
                       source="manual", created_by="Meera Iyer",
                       notes="Handover completed, deduction of ~₹1.5 L expected for repairs."),
        ExpectedInflow(entity_id=entity.id, description="Series B - first tranche (indicative)",
                       inflow_type="Funding", expected_on=date(2027, 3, 31), amount=200_000_000.0,
                       probability=0.35, counterparty="TBD",
                       source="manual", created_by="Guru Mahendra Reddy",
                       notes="Not in any base-case forecast. Term sheet not signed."),
    ])
    db.flush()


# ---------------------------------------------------------------------------
# Ledger — every cash movement, dated within its month
# ---------------------------------------------------------------------------
def _seed_ledger(db: Session, entity: Entity, accounts: dict[str, Account],
                 model: list[dict], customers: list[Customer], vendors: list[Vendor],
                 receipts: list[dict]) -> tuple[list, list[float]]:
    entries = []
    monthly_net: list[float] = []

    payroll_split = [("Salaries - Engineering", 0.470), ("Salaries - Sales & Marketing", 0.175),
                     ("Salaries - Operations", 0.125), ("Salaries - G&A", 0.082),
                     ("Employer PF & ESI", 0.104), ("Staff Welfare", 0.028),
                     ("Recruitment Fees", 0.016)]

    cat_accounts = {
        BurnCategory.TECH: ["AWS Cloud Hosting", "Software Subscriptions",
                            "Data & API Licences", "Security & Compliance Tools"],
        BurnCategory.DELIVERY: ["Contractor & Freelance Cost", "Hardware & Sensor Purchases",
                                "Field Installation Cost", "Travel - Client Delivery"],
        BurnCategory.FACILITIES: ["Office Rent", "Electricity & Utilities",
                                  "Housekeeping & Security", "Repairs & Maintenance"],
        BurnCategory.MARKETING: ["Digital Marketing", "Events & Conferences", "Content & Brand"],
        BurnCategory.PROFESSIONAL: ["Legal & Secretarial", "Audit & Tax Fees", "Consultancy Charges"],
        BurnCategory.FINANCE_COST: ["Interest on Venture Debt", "Bank Charges",
                                    "Processing & Facility Fees"],
        BurnCategory.OTHER: ["Insurance", "Miscellaneous Expenses"],
        BurnCategory.STATUTORY: ["GST Payable", "TDS Payable", "PF Payable",
                                 "ESI Payable", "Professional Tax Payable"],
    }
    vendor_by_cat: dict[str, list[Vendor]] = {}
    for v in vendors:
        vendor_by_cat.setdefault(v.burn_category, []).append(v)

    receipts_by_month: dict[tuple[int, int], list[dict]] = {}
    for r in receipts:
        receipts_by_month.setdefault((r["date"].year, r["date"].month), []).append(r)

    voucher = 5000
    for i, row in enumerate(model):
        m = row["month"]
        me = month_end(m)
        net = 0.0

        # --- inflows: actual receipts against invoices -----------------
        for r in receipts_by_month.get((m.year, m.month), []):
            voucher += 1
            e = LedgerEntry(entity_id=entity.id, account_id=accounts["Sundry Debtors"].id,
                            txn_date=r["date"], voucher_type="Receipt",
                            voucher_no=f"RCT/{voucher}", party=r["party"],
                            narration=f"Collection from {r['party']}",
                            debit=round(r["amount"], 2), credit=0.0,
                            cash_amount=round(r["amount"], 2), source="seed")
            db.add(e); entries.append(e); net += r["amount"]

        # --- payroll on the last working day ---------------------------
        people = row["spend"][BurnCategory.PEOPLE]
        pay_day = me
        while pay_day.weekday() >= 5:
            pay_day -= timedelta(days=1)
        for acc_name, pct in payroll_split:
            amt = people * pct
            voucher += 1
            e = LedgerEntry(entity_id=entity.id, account_id=accounts[acc_name].id,
                            txn_date=pay_day, voucher_type="Payment",
                            voucher_no=f"PAY/{voucher}", party="Payroll",
                            narration=f"{acc_name} - {m.strftime('%b-%y')}",
                            debit=0.0, credit=round(amt, 2), cash_amount=round(-amt, 2),
                            burn_category=BurnCategory.PEOPLE,
                            cost_nature=CostNature.DISCRETIONARY if "Welfare" in acc_name
                            or "Recruitment" in acc_name else CostNature.FIXED,
                            source="seed")
            db.add(e); entries.append(e); net -= amt

        # --- statutory payments on their statutory dates ----------------
        stat_total = row["spend"][BurnCategory.STATUTORY]
        for acc_name, pct, day in [("GST Payable", 0.665, 20), ("TDS Payable", 0.170, 7),
                                   ("PF Payable", 0.118, 15), ("ESI Payable", 0.032, 15),
                                   ("Professional Tax Payable", 0.015, 20)]:
            amt = stat_total * pct
            d = min(date(m.year, m.month, day), me)
            voucher += 1
            e = LedgerEntry(entity_id=entity.id, account_id=accounts[acc_name].id,
                            txn_date=d, voucher_type="Payment", voucher_no=f"STA/{voucher}",
                            party="Government of India",
                            narration=f"{acc_name.replace(' Payable','')} for {(m - relativedelta(months=1)).strftime('%b-%y')}",
                            debit=0.0, credit=round(amt, 2), cash_amount=round(-amt, 2),
                            burn_category=BurnCategory.STATUTORY,
                            cost_nature=CostNature.VARIABLE, source="seed")
            db.add(e); entries.append(e); net -= amt

        # --- vendor payments across the remaining categories ------------
        for cat in [BurnCategory.TECH, BurnCategory.DELIVERY, BurnCategory.FACILITIES,
                    BurnCategory.MARKETING, BurnCategory.PROFESSIONAL,
                    BurnCategory.FINANCE_COST, BurnCategory.OTHER]:
            total = row["spend"][cat]
            names = cat_accounts[cat]
            weights = [rng.uniform(0.6, 1.4) for _ in names]
            wsum = sum(weights)
            pool = vendor_by_cat.get(cat, vendors)
            for acc_name, w in zip(names, weights):
                amt = total * w / wsum
                if amt < 5000:
                    continue
                d = date(m.year, m.month, min(rng.randint(2, 27), me.day))
                v = rng.choice(pool)
                acc = accounts[acc_name]
                voucher += 1
                e = LedgerEntry(entity_id=entity.id, account_id=acc.id,
                                txn_date=d, voucher_type="Payment",
                                voucher_no=f"PMT/{voucher}", party=v.name,
                                narration=f"{acc_name} - {m.strftime('%b-%y')}",
                                debit=0.0, credit=round(amt, 2), cash_amount=round(-amt, 2),
                                burn_category=cat, cost_nature=acc.cost_nature,
                                source="seed")
                db.add(e); entries.append(e); net -= amt

        # --- one-off items ---------------------------------------------
        for o in ONE_OFFS:
            if o["month"] == m:
                d = date(m.year, m.month, min(o["day"], me.day))
                voucher += 1
                e = LedgerEntry(entity_id=entity.id, txn_date=d,
                                voucher_type="Receipt" if o["amount"] > 0 else "Payment",
                                voucher_no=f"ONE/{voucher}", party=o["party"],
                                narration=o["narration"],
                                debit=max(o["amount"], 0.0), credit=max(-o["amount"], 0.0),
                                cash_amount=float(o["amount"]),
                                burn_category=o["category"], cost_nature=CostNature.VARIABLE,
                                is_one_off=True, one_off_note=o["narration"],
                                classified_by=o["classified_by"], source="seed")
                db.add(e); entries.append(e); net += o["amount"]

        # --- venture debt repayments from Jan-26 ------------------------
        if m >= date(2026, 1, 1):
            for acc_name, amt in [("Venture Debt - Alteria", 2_083_333.0),
                                  ("Interest on Venture Debt", None)]:
                if amt is None:
                    outstanding = 50_000_000.0 - 2_083_333.0 * ((m.year - 2026) * 12 + m.month - 1)
                    amt = max(outstanding, 0) * 0.155 / 12
                d = min(date(m.year, m.month, 5), me)
                voucher += 1
                e = LedgerEntry(entity_id=entity.id, account_id=accounts[acc_name].id,
                                txn_date=d, voucher_type="Payment", voucher_no=f"LON/{voucher}",
                                party="Alteria Capital",
                                narration=f"Venture debt {'principal' if 'Debt' in acc_name else 'interest'} - {m.strftime('%b-%y')}",
                                debit=0.0, credit=round(amt, 2), cash_amount=round(-amt, 2),
                                burn_category=BurnCategory.FINANCE_COST,
                                cost_nature=CostNature.FIXED, source="seed")
                db.add(e); entries.append(e); net -= amt

        monthly_net.append(net)

    db.flush()
    return entries, monthly_net


def _back_solve_opening(monthly_net: list[float]) -> float:
    """Choose the opening balance so the closing position lands on target.
    Keeps the demo narrative fixed while the transactions stay random."""
    return TARGET_CLOSING_CASH - sum(monthly_net)


def _seed_banks(db: Session, entity: Entity, opening: float,
                monthly_net: list[float]) -> list[BankAccount]:
    running = opening
    history: list[tuple[date, float]] = []
    for i, m in enumerate(MONTHS):
        running += monthly_net[i]
        history.append((month_end(m), running))

    closing = history[-1][1]
    unrestricted = closing - FD_RESTRICTED
    split = [("HDFC Bank Ltd", "Northwind Operating A/c", "Operating", "xxxx4471", 0.62,
              "Rohit Mehra / Guru Mahendra Reddy (jointly above ₹ 10 L)", 1_000_000.0),
             ("ICICI Bank Ltd", "Collections A/c", "Collection", "xxxx8820", 0.24,
              "Meera Iyer (view only) / Guru Mahendra Reddy", 500_000.0),
             ("Axis Bank Ltd", "Payroll A/c", "Payroll", "xxxx3096", 0.12,
              "Guru Mahendra Reddy", 12_000_000.0),
             ("Kotak Mahindra Bank", "Petty Cash & Imprest", "Operating", "xxxx1153", 0.02,
              "Meera Iyer", 100_000.0)]

    banks = []
    for inst, name, purpose, masked, pct, sig, limit in split:
        b = BankAccount(entity_id=entity.id, institution=inst, account_name=name,
                        account_masked=masked, purpose=purpose,
                        balance=round(unrestricted * pct, 2),
                        books_balance=round(unrestricted * pct + UNRECONCILED * pct, 2),
                        is_restricted=False, signatory=sig, approval_limit=limit,
                        as_on=AS_ON, source="manual", created_by="Meera Iyer",
                        sort_order=len(banks))
        db.add(b); banks.append(b)

    fd = BankAccount(entity_id=entity.id, institution="HDFC Bank Ltd",
                     account_name="Fixed Deposit - lien marked", account_masked="xxxx7702",
                     purpose="Deposit", balance=FD_RESTRICTED, books_balance=FD_RESTRICTED,
                     is_restricted=True,
                     restriction_reason="Lien marked against the ₹ 1.00 Cr working-capital OD facility and a ₹ 20 L performance bank guarantee issued to Bharat Metro Rail.",
                     maturity_date=date(2027, 2, 14), signatory="Guru Mahendra Reddy",
                     approval_limit=0.0, as_on=AS_ON, source="manual",
                     created_by="Meera Iyer", sort_order=9)
    db.add(fd); banks.append(fd)
    db.flush()

    for as_on, bal in history:
        db.add(BankBalanceHistory(entity_id=entity.id, as_on=as_on, balance=round(bal, 2),
                                  books_balance=round(bal + UNRECONCILED, 2)))
    db.flush()
    return banks


# ---------------------------------------------------------------------------
# Payables, statutory dues, commitments
# ---------------------------------------------------------------------------
OPEN_BILLS = [
    # vendor, bill_no, days_before_as_on, terms_days, amount, category, deferrable, deferral_cost, penalty, approver
    ("Amazon Web Services India", "AWS/IN/26/0891", 12, 15, 1_240_000, BurnCategory.TECH,
     False, 0, "Service suspension after 7 days past due", "Vikram Shenoy"),
    ("Zenith Contract Engineering", "ZCE/2026/214", 38, 30, 1_680_000, BurnCategory.DELIVERY,
     True, 33_600, "2% per month on delayed payment", "Guru Mahendra Reddy"),
    ("Mahalaxmi Sensor Systems", "MSS/26-27/077", 44, 45, 2_150_000, BurnCategory.DELIVERY,
     True, 0, "Supply hold on next PO", "Guru Mahendra Reddy"),
    ("Prestige Tech Park Ltd", "PTP/RENT/SEP26", -4, 5, 480_000, BurnCategory.FACILITIES,
     False, 0, "18% p.a. interest per the lease deed", "Meera Iyer"),
    ("Velocity Talent Partners", "VTP/INV/1122", 61, 45, 620_000, BurnCategory.PEOPLE,
     True, 0, "None", "Vikram Shenoy"),
    ("Krishnan & Co, Chartered Accountants", "KCO/26/0345", 9, 30, 350_000, BurnCategory.PROFESSIONAL,
     True, 0, "None", "Guru Mahendra Reddy"),
    ("Datadog India Pvt Ltd", "DD/IN/9921", 5, 30, 285_000, BurnCategory.TECH,
     True, 0, "None", "Vikram Shenoy"),
    ("Hivemind Digital LLP", "HD/2026/58", 21, 30, 410_000, BurnCategory.MARKETING,
     True, 0, "None", "Priya Nair"),
    ("IndiaTech Summit Events", "ITS/26/SPON/09", -18, 30, 750_000, BurnCategory.MARKETING,
     True, 0, "Sponsorship slot released if unpaid by 30-Sep", "Priya Nair"),
    ("Bajaj Allianz General Insurance", "BAGI/RENEW/26", -9, 15, 385_000, BurnCategory.OTHER,
     False, 0, "Cover lapses on non-payment", "Meera Iyer"),
    ("Sentinel Security Labs", "SSL/26/441", 2, 30, 240_000, BurnCategory.TECH,
     True, 0, "None", "Vikram Shenoy"),
    ("Yatra Corporate Travel", "YCT/26/8871", 27, 15, 196_000, BurnCategory.DELIVERY,
     True, 0, "Corporate account moved to prepaid", "Meera Iyer"),
    ("BESCOM", "BESCOM/SEP/26", -6, 10, 168_000, BurnCategory.FACILITIES,
     False, 0, "Disconnection notice after 15 days", "Meera Iyer"),
    ("Sparkle Facility Services", "SFS/26/0912", 16, 30, 142_000, BurnCategory.FACILITIES,
     True, 0, "None", "Meera Iyer"),
    ("Rao & Associates", "RA/26/0188", 33, 30, 275_000, BurnCategory.PROFESSIONAL,
     True, 0, "None", "Guru Mahendra Reddy"),
]

STATUTORY_OPEN = [
    # head, period, due_date, amount, earmarked, notes
    (StatutoryHead.TDS, "Aug-26", date(2026, 9, 7), 560_000, 560_000,
     "Section 194J and 192 deductions for August."),
    (StatutoryHead.PF, "Aug-26", date(2026, 9, 15), 390_000, 390_000, None),
    (StatutoryHead.ESI, "Aug-26", date(2026, 9, 15), 105_000, 105_000, None),
    (StatutoryHead.GST, "Aug-26", date(2026, 9, 20), 2_200_000, 1_550_000,
     "GSTR-3B for August. ₹ 6.5 L short against the earmark — this is the funding gap."),
    (StatutoryHead.PT, "Aug-26", date(2026, 9, 20), 50_000, 50_000, None),
    (StatutoryHead.ADVANCE_TAX, "Q2 FY26-27", date(2026, 9, 15), 0, 0,
     "Nil — company is in losses, no advance tax liability computed."),
    (StatutoryHead.TDS, "Sep-26", date(2026, 10, 7), 578_000, 0, None),
    (StatutoryHead.PF, "Sep-26", date(2026, 10, 15), 402_000, 0, None),
    (StatutoryHead.GST, "Sep-26", date(2026, 10, 20), 2_310_000, 0, None),
]


def _seed_payables(db: Session, entity: Entity, vendors: list[Vendor]) -> None:
    vmap = {v.name: v for v in vendors}
    # SCALE lets the open-bill book be resized without rewriting the table.
    # At 1.0 these bills imply ~26 days DPO on non-payroll spend, which is right.
    SCALE = 1.0
    for (vn, bno, days_ago, terms, amt, cat, deferrable, dcost, penalty, approver) in OPEN_BILLS:
        amt = amt * SCALE
        dcost = dcost * SCALE
        due = AS_ON - timedelta(days=days_ago)
        v = vmap[vn]
        db.add(Bill(entity_id=entity.id, vendor_id=v.id, bill_no=bno,
                    bill_date=due - timedelta(days=terms), due_date=due,
                    amount=float(amt), outstanding=float(amt),
                    description=f"{cat} — {vn}", burn_category=cat,
                    deferrable=deferrable, deferral_cost=float(dcost),
                    penalty_note=penalty, approver=approver,
                    status="unpaid", source="tally", created_by="Tally sync"))

    for head, period, due, amt, earmarked, notes in STATUTORY_OPEN:
        status = "pending"
        if amt and earmarked >= amt:
            status = "funded"
        if due < TODAY and amt:
            status = "overdue"
        db.add(StatutoryDue(entity_id=entity.id, head=head, period=period, due_date=due,
                            amount=float(amt), funded=bool(amt and earmarked >= amt),
                            earmarked_amount=float(earmarked), status=status,
                            notes=notes, source="tally", created_by="Meera Iyer"))

    # 12 months of statutory payment history, with two late payments
    late = {date(2025, 12, 20): 18_400.0, date(2026, 6, 20): 31_200.0}
    for k in range(12):
        m = date(2025, 9, 1) + relativedelta(months=k)
        for head, day, base in [(StatutoryHead.GST, 20, 1_960_000), (StatutoryHead.TDS, 7, 505_000),
                                (StatutoryHead.PF, 15, 352_000), (StatutoryHead.ESI, 15, 95_000),
                                (StatutoryHead.PT, 20, 45_000)]:
            due = date(m.year, m.month, day)
            amt = base * (1 + 0.02 * k) * jitter(0.05)
            pen = late.get(due, 0.0) if head == StatutoryHead.GST else 0.0
            db.add(StatutoryDue(entity_id=entity.id, head=head,
                                period=(m - relativedelta(months=1)).strftime("%b-%y"),
                                due_date=due, amount=round(amt, 2), funded=True,
                                earmarked_amount=round(amt, 2), status="paid",
                                paid_on=due + timedelta(days=2 if pen else 0),
                                interest_penalty_paid=pen, source="tally",
                                created_by="Tally sync"))

    commitments = [
        (CommitmentType.CLOUD, "Amazon Web Services India", "Annual committed-use discount plan",
         9_600_000, 6_240_000, False, 0, 1_100_000, date(2026, 4, 1), date(2027, 3, 31),
         800_000, BurnCategory.TECH, "Vikram Shenoy"),
        (CommitmentType.LEASE, "Prestige Tech Park Ltd", "Whitefield office, floors 3 & 4",
         17_280_000, 5_760_000, True, 180, 2_880_000, date(2026, 1, 1), date(2028, 12, 31),
         480_000, BurnCategory.FACILITIES, "Meera Iyer"),
        (CommitmentType.OFFER, "3 engineering hires (offers issued)", "Offers accepted, joining Oct–Nov 26",
         5_112_000, 0, True, 0, 0, date(2026, 10, 1), date(2027, 9, 30),
         426_000, BurnCategory.PEOPLE, "Guru Mahendra Reddy"),
        (CommitmentType.PO, "Mahalaxmi Sensor Systems", "PO/26/0338 — 1,200 vibration sensor units",
         3_840_000, 1_450_000, True, 30, 240_000, date(2026, 7, 1), date(2026, 12, 31),
         0, BurnCategory.DELIVERY, "Guru Mahendra Reddy"),
        (CommitmentType.RETAINER, "Krishnan & Co, Chartered Accountants", "FY26-27 audit and tax retainer",
         1_800_000, 750_000, True, 60, 0, date(2026, 4, 1), date(2027, 3, 31),
         150_000, BurnCategory.PROFESSIONAL, "Meera Iyer"),
        (CommitmentType.CLOUD, "Datadog India Pvt Ltd", "Observability platform, 24-month term",
         4_320_000, 1_620_000, False, 0, 620_000, date(2026, 2, 1), date(2028, 1, 31),
         180_000, BurnCategory.TECH, "Vikram Shenoy"),
        (CommitmentType.OTHER, "IndiaTech Summit Events", "Platinum sponsorship, Feb-27 edition",
         2_250_000, 750_000, True, 90, 375_000, date(2026, 8, 1), date(2027, 2, 28),
         0, BurnCategory.MARKETING, "Priya Nair"),
    ]
    for (ctype, party, desc, total, consumed, cancellable, notice, exit_cost,
         starts, ends, runrate, cat, owner) in commitments:
        db.add(Commitment(entity_id=entity.id, commitment_type=ctype, counterparty=party,
                          description=desc, total_value=float(total),
                          consumed_to_date=float(consumed), cancellable=cancellable,
                          notice_period_days=notice, exit_cost=float(exit_cost),
                          starts_on=starts, ends_on=ends, monthly_runrate=float(runrate),
                          burn_category=cat, owner=owner, source="manual", created_by=owner))
    db.flush()


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
def _seed_people(db: Session, entity: Entity, model: list[dict]) -> None:
    for i, row in enumerate(model):
        t = i / max(N - 1, 1)
        actual = int(round(38 + 57 * t))
        db.add(HeadcountMonth(entity_id=entity.id, month=row["month"],
                              funded_headcount=actual + (5 if i >= N - 6 else 2),
                              actual_headcount=actual,
                              approved_unfilled=5 if i >= N - 6 else 2,
                              offers_accepted_not_joined=3 if i >= N - 3 else rng.randint(0, 2),
                              people_cost=round(row["spend"][BurnCategory.PEOPLE], 2),
                              attrition=rng.randint(0, 2),
                              source="manual", created_by="Vikram Shenoy"))

    total_hc = sum(h for _, h, _ in FUNCTIONS)
    for i in range(12):
        m = MONTHS[N - 12 + i]
        row = model[N - 12 + i]
        scale = (0.82 + 0.18 * i / 11)
        for fn, hc, cost in FUNCTIONS:
            fhc = max(int(round(hc * scale)), 1)
            db.add(FunctionCost(entity_id=entity.id, month=m, function=fn,
                                headcount=fhc,
                                fully_loaded_cost_per_head=round(cost, 2),
                                total_cost=round(fhc * cost, 2),
                                source="manual", created_by="Vikram Shenoy"))

    hires = [
        ("Senior Firmware Engineer", "Engineering", 2, date(2026, 10, 1), 165_000, 180_000, "accepted"),
        ("Field Deployment Lead", "Operations", 1, date(2026, 10, 15), 105_000, 0, "accepted"),
        ("Enterprise Account Executive", "Sales & Marketing", 2, date(2026, 11, 1), 148_000, 220_000, "offer-out"),
        ("QA Automation Engineer", "Engineering", 1, date(2026, 11, 15), 118_000, 90_000, "planned"),
        ("Finance Analyst", "G&A", 1, date(2026, 12, 1), 95_000, 0, "planned"),
        ("ML Engineer", "Engineering", 2, date(2027, 1, 15), 178_000, 250_000, "planned"),
    ]
    for role, fn, pos, start, cost, onetime, status in hires:
        db.add(HiringPlanItem(entity_id=entity.id, role=role, function=fn, positions=pos,
                              planned_start=start, monthly_cost_each=float(cost),
                              one_time_cost=float(onetime), status=status,
                              approved_by="Guru Mahendra Reddy",
                              source="manual", created_by="Vikram Shenoy"))

    db.add(EmployeeLiability(entity_id=entity.id, as_on=AS_ON,
                             gratuity_accrued=3_180_000.0,
                             leave_encashment_accrued=1_940_000.0,
                             bonus_accrued=2_650_000.0, funded_amount=0.0,
                             notes="Unfunded. No gratuity trust or LIC policy in place; the full amount is a future cash call.",
                             source="manual", created_by="Meera Iyer"))
    db.flush()


# ---------------------------------------------------------------------------
# Capital & debt
# ---------------------------------------------------------------------------
def _seed_capital(db: Session, entity: Entity) -> None:
    alteria = Facility(entity_id=entity.id, lender="Alteria Capital",
                       facility_type="Venture Debt", sanctioned=50_000_000.0,
                       drawn=50_000_000.0, interest_rate=15.5, tenure_months=36,
                       start_date=date(2025, 10, 9), end_date=date(2028, 10, 9),
                       next_repayment_date=date(2026, 9, 5), next_repayment_amount=2_515_000.0,
                       security_given="First charge on movable assets; personal guarantee of the two founders.",
                       source="manual", created_by="Meera Iyer")
    hdfc = Facility(entity_id=entity.id, lender="HDFC Bank Ltd",
                    facility_type="Working Capital OD", sanctioned=25_000_000.0,
                    drawn=0.0, interest_rate=11.25, tenure_months=12,
                    start_date=date(2026, 2, 14), end_date=date(2027, 2, 13),
                    next_repayment_date=None, next_repayment_amount=0.0,
                    security_given="₹ 45 L fixed deposit under lien; hypothecation of book debts.",
                    source="manual", created_by="Meera Iyer")
    db.add_all([alteria, hdfc])
    db.flush()

    outstanding = 50_000_000.0 - 2_083_333.0 * 8
    for k in range(12):
        d = date(2026, 9, 5) + relativedelta(months=k)
        interest = max(outstanding, 0) * 0.155 / 12
        db.add(RepaymentScheduleItem(entity_id=entity.id, facility_id=alteria.id,
                                     due_date=d, principal=2_083_333.0,
                                     interest=round(interest, 2), paid=False,
                                     source="derived", created_by="System"))
        outstanding -= 2_083_333.0

    # Venture debt on a pre-profit company is not covenanted on DSCR — operating
    # cash flow is negative by design. Lenders test liquidity and runway instead.
    covenants = [
        ("Current Ratio not below 1.90x", "current_ratio", ">=", 1.90, 10.0, date(2026, 9, 30), "Quarterly"),
        ("Minimum runway of 6.0 months", "runway_months", ">=", 6.0, 15.0, date(2026, 9, 30), "Monthly"),
        ("Minimum unrestricted cash of ₹ 3.00 Cr", "cash_available", ">=", 30_000_000.0, 20.0, date(2026, 9, 30), "Monthly"),
        ("Debt–Equity not above 0.60x", "debt_equity", "<=", 0.60, 15.0, date(2027, 3, 31), "Annually"),
        ("Quick Ratio not below 1.50x", "quick_ratio", ">=", 1.50, 12.0, date(2026, 9, 30), "Quarterly"),
    ]
    for name, key, op, val, buf, test, freq in covenants:
        db.add(Covenant(entity_id=entity.id, facility_id=alteria.id, name=name,
                        metric_key=key, operator=op, required_value=val,
                        amber_buffer_pct=buf, test_date=test, test_frequency=freq,
                        source="manual", created_by="Meera Iyer",
                        notes="Tested on standalone India financials."))

    db.add_all([
        FundingRound(entity_id=entity.id, round_name="Seed", closed_on=date(2023, 11, 20),
                     amount=45_000_000.0, instrument="CCPS",
                     investor="Antler India, angel syndicate",
                     post_money_valuation=280_000_000.0, cash_remaining=0.0,
                     notes="Fully deployed by Jan-2025.",
                     source="manual", created_by="Guru Mahendra Reddy"),
        FundingRound(entity_id=entity.id, round_name="Series A", closed_on=date(2025, 2, 27),
                     amount=180_000_000.0, instrument="CCPS",
                     investor="Northstar Ventures (lead), Antler India (follow-on)",
                     post_money_valuation=920_000_000.0, cash_remaining=41_700_000.0,
                     notes="₹ 4.17 Cr of the round remains unspent as at 31-Aug-26.",
                     source="manual", created_by="Guru Mahendra Reddy"),
        NextRaise(entity_id=entity.id, target_amount=350_000_000.0,
                  target_close_date=date(2027, 3, 31), lead_time_months=6,
                  instrument="Equity — Series B", status="Not started",
                  notes="Two of the three existing investors have pro-rata rights that must be notified 30 days before a term sheet is signed.",
                  is_active=True, source="manual", created_by="Guru Mahendra Reddy"),
    ])
    db.flush()


# ---------------------------------------------------------------------------
# Plans, variances, scenarios, score history, forecast accuracy
# ---------------------------------------------------------------------------
PLAN_MONTHS = months_between(date(2026, 4, 1), date(2027, 3, 1))

# The plan's category mix has to match the shape of the actual burn, or every
# line-item variance reads as a scandal when it is really a mapping error.
# Statutory is large because the company is people-heavy (thin input credit,
# so net GST is high); Finance Costs carry the venture-debt principal.
PLAN_OUTFLOW_MIX = {
    BurnCategory.PEOPLE: 0.505, BurnCategory.TECH: 0.073, BurnCategory.DELIVERY: 0.102,
    BurnCategory.FACILITIES: 0.029, BurnCategory.MARKETING: 0.037,
    BurnCategory.PROFESSIONAL: 0.015, BurnCategory.STATUTORY: 0.117,
    BurnCategory.FINANCE_COST: 0.108, BurnCategory.OTHER: 0.014,
}


def _plan_lines(plan: Plan, opening: float, coll0: float, coll_g: float,
                out0: float, out_g: float) -> list[PlanLine]:
    rows, closing = [], opening
    for k, m in enumerate(PLAN_MONTHS):
        inflow = coll0 * ((1 + coll_g) ** k)
        outflow = out0 * ((1 + out_g) ** k)
        closing = closing + inflow - outflow
        rows.append(PlanLine(plan_id=plan.id, month=m, line_type="inflow",
                             category="Customer Collections", amount=round(inflow, 2)))
        for cat, share in PLAN_OUTFLOW_MIX.items():
            rows.append(PlanLine(plan_id=plan.id, month=m, line_type="outflow",
                                 category=cat, amount=round(outflow * share, 2)))
        rows.append(PlanLine(plan_id=plan.id, month=m, line_type="closing",
                             category="Closing Cash", amount=round(closing, 2)))
    return rows


def _seed_planning(db: Session, entity: Entity, model: list[dict]) -> None:
    opening_row = db.query(BankBalanceHistory).filter(
        BankBalanceHistory.entity_id == entity.id,
        BankBalanceHistory.as_on == date(2026, 3, 31)).first()
    opening = opening_row.balance if opening_row else 78_000_000.0

    v1 = Plan(entity_id=entity.id, name="FY26-27 Operating Plan", version="v1.0",
              note="Board-approved plan tabled at the 18-Apr-26 meeting. Assumes the Bharat Metro Phase-2 extension closes in Q1.",
              uploaded_by="Guru Mahendra Reddy", uploaded_on=datetime(2026, 4, 14, 16, 42),
              is_active=False, is_locked=True, board_approved=True,
              approved_by="Guru Mahendra Reddy", seconded_by="Rohan Kapadia",
              approved_on=date(2026, 4, 18), period_from=date(2026, 4, 1),
              period_to=date(2027, 3, 31), opening_cash=round(opening, 2),
              source_filename="FY26-27_Operating_Plan_v1.xlsx",
              source="upload", created_by="Guru Mahendra Reddy")
    db.add(v1); db.flush()
    db.add_all(_plan_lines(v1, opening, 19_500_000, 0.040, 24_000_000, 0.018))

    v2 = Plan(entity_id=entity.id, name="FY26-27 Operating Plan — Revised", version="v2.0",
              note="Reforecast after the Phase-2 extension slipped to Q3 and two enterprise deals pushed out. Not yet tabled to the board.",
              uploaded_by="Meera Iyer", uploaded_on=datetime(2026, 7, 12, 11, 8),
              is_active=True, is_locked=False, board_approved=False,
              period_from=date(2026, 4, 1), period_to=date(2027, 3, 31),
              opening_cash=round(opening, 2), supersedes_id=v1.id,
              source_filename="FY26-27_Operating_Plan_v2_revised.xlsx",
              source="upload", created_by="Meera Iyer")
    db.add(v2); db.flush()
    db.add_all(_plan_lines(v2, opening, 18_200_000, 0.025, 24_800_000, 0.015))
    db.flush()

    variances = [
        (date(2026, 4, 1), None, VarianceType.TIMING,
         "Bharat Metro milestone-2 certification slipped from 22-Apr to 09-May; ₹ 62 L collection moved a month.",
         "Anand Rao", "Reverses in May. No revenue lost.", "closed"),
        (date(2026, 5, 1), BurnCategory.PROFESSIONAL, VarianceType.ONE_OFF,
         "Settlement of the ex-vendor claim with Rao & Associates, ₹ 22 L, not in plan.",
         "Guru Mahendra Reddy", "Board informed on 21-May. Non-recurring.", "closed"),
        (date(2026, 6, 1), BurnCategory.PEOPLE, VarianceType.COST_OVERRUN,
         "Two senior engineering hires closed at 14% above the banded offer to beat a competing offer.",
         "Vikram Shenoy", "Permanent uplift to the people run-rate of ~₹ 3.9 L per month.", "actioned"),
        (date(2026, 7, 1), None, VarianceType.VOLUME,
         "Two enterprise deals in the Q2 pipeline pushed to Q3; ₹ 84 L of planned billing did not happen.",
         "Priya Nair", "Both still live. Reforecast in plan v2.0.", "explained"),
        (date(2026, 7, 1), BurnCategory.TECH, VarianceType.PERMANENT,
         "AWS committed-use plan renewed at a higher tier following the Phase-2 data volumes.",
         "Vikram Shenoy", "₹ 1.8 L per month above plan, will not reverse.", "explained"),
        (date(2026, 8, 1), None, VarianceType.TIMING,
         "Bharat Metro invoice NWR/26/0947 of ₹ 84 L unpaid at month end, 47 days past due.",
         "Anand Rao", "Client has promised ₹ 50 L by 22-Sep. Balance being escalated.", "open"),
        (date(2026, 8, 1), BurnCategory.MARKETING, VarianceType.TIMING,
         "IndiaTech Summit sponsorship invoiced in August against a September plan line.",
         "Priya Nair", "Timing only.", "explained"),
    ]
    for month, cat, vtype, driver, owner, comment, status in variances:
        db.add(VarianceNote(entity_id=entity.id, plan_id=v2.id, month=month, category=cat,
                            variance_type=vtype, driver=driver, owner=owner,
                            comment=comment, status=status,
                            source="manual", created_by=owner))

    for s in ref.PREBUILT_SCENARIOS:
        db.add(Scenario(entity_id=entity.id, name=s["name"], note=s["note"],
                        levers=json.dumps(s["levers"]), is_prebuilt=True,
                        sort_order=s["sort_order"], source="seed",
                        created_by="System"))
    db.add(Scenario(entity_id=entity.id, name="Metro pays, hiring frozen",
                    note="Saved 28-Aug-26 ahead of the founders' review: assumes Bharat Metro clears ₹ 84 L in September and we hold all open roles.",
                    levers=json.dumps(dict(top_client_delay_days=0, collections_pct_of_plan=100,
                                           hiring="freeze", discretionary_cut_pct=20,
                                           funding_slip_months=0, new_funding_amount=0,
                                           new_funding_date=None, revenue_pct_of_plan=100,
                                           price_increase_pct=0)),
                    is_prebuilt=False, is_pinned=True, sort_order=10,
                    source="manual", created_by="Guru Mahendra Reddy"))

    # 12 months of liquidity score with the events that moved it
    score_path = [
        (74.0, "Series A cash still largely intact."),
        (73.0, None), (71.0, "Venture debt drawn — leverage added, cash improved."),
        (72.0, None), (69.0, "Office fit-out and ESOP buy-back in the same quarter."),
        (67.0, None), (66.0, None),
        (64.0, "DSO crossed 90 days for the first time."),
        (63.0, None), (61.0, "Two enterprise deals pushed to Q3."),
        (64.0, "₹ 1.1 Cr collected in a single week from Sundaram and GreenGrid."),
        (58.0, "Bharat Metro ₹ 84 L past due; runway fell below 7 months."),
    ]
    for k, (score, event) in enumerate(score_path):
        m = date(2025, 9, 1) + relativedelta(months=k)
        band = "Strong" if score >= 80 else "Adequate" if score >= 65 else "Tight" if score >= 45 else "Critical"
        db.add(ScoreHistory(entity_id=entity.id, month=m, score=score, band=band,
                            event_note=event,
                            components=json.dumps(dict(
                                runway=round(score * 0.30, 1), days_cash=round(score * 0.20, 1),
                                statutory_cover=round(score * 0.20, 1),
                                receivables_quality=round(score * 0.15, 1),
                                structure=round(score * 0.15, 1)))))

    # 8 weeks of forecast-vs-actual so Tab 6 can state its own accuracy
    errors = [0.031, -0.058, 0.042, -0.091, 0.024, -0.067, 0.038, -0.049]
    for k, err in enumerate(errors):
        week_start = AS_ON - timedelta(days=AS_ON.weekday()) - timedelta(weeks=(8 - k))
        hist = db.query(BankBalanceHistory).filter(
            BankBalanceHistory.entity_id == entity.id,
            BankBalanceHistory.as_on <= week_start).order_by(
            BankBalanceHistory.as_on.desc()).first()
        actual = hist.balance if hist else TARGET_CLOSING_CASH
        db.add(ForecastSnapshot(entity_id=entity.id,
                                made_on=week_start - timedelta(days=7),
                                week_start=week_start,
                                forecast_closing=round(actual * (1 + err), 2),
                                actual_closing=round(actual, 2),
                                confidence="High" if abs(err) < 0.05 else "Medium"))
    db.flush()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def _seed_alerts(db: Session, entity: Entity) -> None:
    users = db.query(User).all()
    cfo = next(u for u in users if u.role == Role.CFO)
    fin = next(u for u in users if u.role == Role.FINANCE)
    recipients = f"{cfo.phone},{fin.phone}"

    # Read the concentration straight off the seeded book so the alert text can
    # never contradict what Tab 4 shows.
    from sqlalchemy import func as _f
    top = (db.query(Customer.name, _f.sum(Invoice.outstanding))
             .join(Invoice, Invoice.customer_id == Customer.id)
             .filter(Invoice.entity_id == entity.id)
             .group_by(Customer.name)
             .order_by(_f.sum(Invoice.outstanding).desc()).first())
    total_ar = (db.query(_f.sum(Invoice.outstanding))
                  .filter(Invoice.entity_id == entity.id).scalar() or 1.0)
    top_name, top_amt = (top[0], top[1]) if top else ("Bharat Metro Rail Corporation", 0.0)
    top_pct = round(top_amt / total_ar * 100, 1)

    rules: dict[str, AlertRule] = {}
    for r in ref.ALERT_RULES:
        ar = AlertRule(entity_id=entity.id, code=r["code"], name=r["name"],
                       description=r["description"], enabled=True,
                       threshold=r["threshold"], threshold_unit=r["threshold_unit"],
                       severity=r["severity"], channels=r["channels"],
                       cooldown_hours=r["cooldown_hours"],
                       quiet_hours_start=22, quiet_hours_end=7,
                       recipients=recipients,
                       escalate_after_hours=r["escalate_after_hours"],
                       escalate_to=cfo.phone if r["escalate_after_hours"] else None,
                       source="seed", created_by="Vikram Shenoy")
        db.add(ar); rules[r["code"]] = ar
    db.flush()

    fired = [
        ("runway_below_months", "Red", "Runway has fallen to 6.7 months",
         "Runway on the current run-rate is 6.7 months against a 9-month threshold. Cash-out date is 21-Mar-27. The fundraise trigger date has already passed.",
         6.7, 9.0, "months", 0.0, "/runway-burn", 2, "active", None, None),
        ("statutory_unfunded_within_days", "Red", "GST of ₹ 22.0 L due 20-Sep is ₹ 6.5 L short",
         "GSTR-3B liability for August is ₹ 22.00 L falling due on 20-Sep-26. Only ₹ 15.50 L is earmarked. Gap ₹ 6.50 L.",
         6.5, 10.0, "days", 650_000.0, "/money-out?sub=statutory", 1, "acknowledged",
         "Guru Mahendra Reddy", "Chasing ₹ 50 L from Bharat Metro; will earmark on receipt."),
        ("client_above_pct_of_receivables", "Amber",
         f"{top_name} is {top_pct}% of receivables",
         f"A single client accounts for {top_pct}% of total receivables (₹ {top_amt / 100000:,.1f} L "
         f"of ₹ {total_ar / 100000:,.1f} L) against a 25% threshold. ₹ 84.0 L of that is 47 days past due.",
         top_pct, 25.0, "pct", 8_400_000.0, "/money-in", 5, "active", None, None),
        ("books_bank_difference_above", "Amber", "Books and bank differ by ₹ 3.20 L",
         "Unreconciled difference of ₹ 3.20 L between the books position and the bank position as at 31-Aug-26.",
         320_000.0, 500_000.0, "inr", 320_000.0, "/setup?layer=sources", 4, "active", None, None),
        ("covenant_headroom_below_pct", "Amber", "Current ratio headroom inside the warning band",
         "Current ratio is tracking close to the 1.90x covenant floor. Headroom is inside the 10% "
         "warning band with the next test on 30-Sep-26.",
         8.4, 10.0, "pct", 0.0, "/capital-debt", 3, "active", None, None),
        ("plan_variance_above_pct", "Amber", "August cash variance is 14.2% behind plan v2.0",
         "Actual closing cash for August is ₹ 4.62 Cr against the plan's ₹ 5.39 Cr — 14.2% behind.",
         14.2, 10.0, "pct", 7_700_000.0, "/plan-vs-actual", 6, "resolved",
         "Meera Iyer", "Explained as timing — Bharat Metro receipt. Variance note recorded."),
        ("cashout_moved_more_than_days", "Red", "Cash-out date moved 19 days earlier this week",
         "Cash-out date moved from 09-Apr-27 to 21-Mar-27 — 19 days earlier — driven by the Bharat Metro receipt not landing.",
         19.0, 14.0, "days", 0.0, "/", 3, "acknowledged", "Guru Mahendra Reddy",
         "Escalated to the board chair. Series B outreach starting this week."),
        ("data_not_updated_for_hours", "Grey", "Tally sync last succeeded 61 hours ago",
         "The Tally connector has not completed a successful sync since 02-Sep-26 06:00 IST. Figures may be stale.",
         61.0, 48.0, "hours", 0.0, "/setup?layer=sources", 8, "resolved",
         "Vikram Shenoy", "Tally server was restarted after a Windows update. Sync resumed 04-Sep 07:20."),
    ]

    for (code, sev, title, msg, tv, th, unit, stake, link, days_ago,
         status, ack_by, action) in fired:
        rule = rules[code]
        triggered = datetime(2026, 9, 4, 8, 15) - timedelta(days=days_ago)
        a = Alert(entity_id=entity.id, rule_id=rule.id, rule_code=code, severity=sev,
                  title=title, message=msg, triggered_on=triggered,
                  trigger_value=tv, threshold_value=th, value_unit=unit,
                  amount_at_stake=stake, deep_link=link, status=status,
                  acknowledged_by=ack_by,
                  acknowledged_on=triggered + timedelta(hours=rng.randint(2, 20)) if ack_by else None,
                  action_taken=action,
                  resolved_on=triggered + timedelta(days=1) if status == "resolved" else None)
        db.add(a); db.flush()
        rule.last_fired_at = triggered

        for ch in rule.channels.split(","):
            for rec in recipients.split(",") if ch == "sms" else [cfo.email]:
                db.add(AlertDelivery(alert_id=a.id, channel=ch, recipient=rec,
                                     sent_on=triggered + timedelta(minutes=2),
                                     delivered=True,
                                     read=status in ("acknowledged", "resolved") or rng.random() > 0.35,
                                     provider_message_id=f"wamid.{rng.randint(10**14, 10**15-1)}"
                                     if ch == "sms" else None))

    # Two muted/ignored alerts so the honesty panel on Tab 11 has something to say
    for k, (code, title) in enumerate([
        ("payables_exceed_receivables_due", "Payables due exceed weighted collectible"),
        ("books_bank_difference_above", "Books and bank differ by ₹ 2.40 L"),
    ]):
        rule = rules[code]
        triggered = datetime(2026, 8, 20, 9, 0) + timedelta(days=k * 3)
        a = Alert(entity_id=entity.id, rule_id=rule.id, rule_code=code, severity="Amber",
                  title=title, message=f"{title}. No action recorded.",
                  triggered_on=triggered, trigger_value=1.14, threshold_value=1.0,
                  value_unit="ratio", amount_at_stake=0.0, deep_link="/money-out",
                  status="muted")
        db.add(a); db.flush()
        db.add(AlertDelivery(alert_id=a.id, channel="sms", recipient=cfo.phone,
                             sent_on=triggered, delivered=True, read=False,
                             provider_message_id=f"wamid.{rng.randint(10**14, 10**15-1)}"))
    db.flush()


# ---------------------------------------------------------------------------
# Activity log + sync history
# ---------------------------------------------------------------------------
def _seed_activity(db: Session, entity: Entity) -> None:
    rows = [
        (0, "Vikram Shenoy", "synced", "Tally", "Sync completed — 1,284 vouchers, 3 new ledgers."),
        (0, "Guru Mahendra Reddy", "acknowledged", "Alert",
         "Acknowledged 'Cash-out date moved 19 days earlier this week'."),
        (1, "Meera Iyer", "updated", "AlertRule",
         "Changed 'Runway below threshold' from 6 months to 9 months."),
        (2, "Guru Mahendra Reddy", "created", "Scenario",
         "Saved scenario 'Metro pays, hiring frozen'."),
        (4, "Meera Iyer", "updated", "Commitment",
         "Recorded ₹ 7.5 L consumed against the IndiaTech Summit sponsorship."),
        (7, "Guru Mahendra Reddy", "reclassified", "LedgerEntry",
         "Reclassified 'Settlement of ex-vendor claim' ₹ 22 L as one-off."),
        (12, "Meera Iyer", "uploaded", "BankStatement",
         "Uploaded HDFC operating account statement for August — 214 rows, 2 rejected."),
        (18, "Vikram Shenoy", "updated", "Setting",
         "Raised the minimum cash floor from ₹ 1.20 Cr to ₹ 1.50 Cr."),
        (54, "Meera Iyer", "uploaded", "Plan",
         "Uploaded 'FY26-27 Operating Plan — Revised' v2.0 and made it active."),
        (139, "Guru Mahendra Reddy", "approved", "Plan",
         "Board-approved 'FY26-27 Operating Plan' v1.0, seconded by Rohan Kapadia."),
    ]
    for days_ago, who, action, obj, summary in rows:
        db.add(ActivityLog(entity_id=entity.id, user_name=who, action=action,
                           object_type=obj, summary=summary,
                           at=datetime(2026, 9, 4, 9, 30) - timedelta(days=days_ago,
                                                                     hours=rng.randint(0, 8))))

    syncs = [(0, "success", 1284, None), (0, "success", 96, None),
             (2, "failed", 0, "Connection refused — Tally server not reachable on localhost:9000."),
             (2, "failed", 0, "Connection refused — Tally server not reachable on localhost:9000."),
             (3, "success", 842, None), (3, "success", 311, None),
             (4, "partial", 640, "3 vouchers skipped: ledger 'Suspense A/c' has no classification mapping."),
             (5, "success", 1102, None)]
    for days_ago, status, records, msg in syncs:
        start = datetime(2026, 9, 4, 6, 0) - timedelta(days=days_ago, hours=rng.randint(0, 12))
        db.add(SyncRun(entity_id=entity.id, source="tally", started_at=start,
                       finished_at=start + timedelta(seconds=rng.randint(12, 180)),
                       status=status, records=records, message=msg,
                       triggered_by="Scheduler"))
    db.flush()


# ---------------------------------------------------------------------------
# Singapore — small but real, so the entity dropdown is not a dead end
# ---------------------------------------------------------------------------
def _seed_singapore(db: Session, sg: Entity) -> None:
    bank = BankAccount(entity_id=sg.id, institution="DBS Bank Ltd",
                       account_name="Northwind SG Operating", account_masked="xxxx0042",
                       purpose="Operating", balance=8_640_000.0, books_balance=8_640_000.0,
                       is_restricted=False, signatory="Guru Mahendra Reddy",
                       approval_limit=1_000_000.0, as_on=AS_ON,
                       source="manual", created_by="Meera Iyer")
    db.add(bank); db.flush()

    running = 12_400_000.0
    for m in MONTHS[-12:]:
        running -= rng.uniform(2.4 * L, 3.6 * L)
        db.add(BankBalanceHistory(entity_id=sg.id, as_on=month_end(m),
                                  balance=round(running, 2), books_balance=round(running, 2)))
    bank.balance = round(running, 2)
    bank.books_balance = round(running, 2)

    for i, m in enumerate(MONTHS[-12:]):
        db.add(HeadcountMonth(entity_id=sg.id, month=m, funded_headcount=7,
                              actual_headcount=6 if i < 8 else 7, approved_unfilled=1,
                              offers_accepted_not_joined=0,
                              people_cost=round(rng.uniform(18 * L, 22 * L), 2),
                              source="manual", created_by="Vikram Shenoy"))
        me = month_end(m)
        db.add(LedgerEntry(entity_id=sg.id, txn_date=me, voucher_type="Payment",
                           voucher_no=f"SG/PAY/{i}", party="Payroll",
                           narration=f"Singapore payroll - {m.strftime('%b-%y')}",
                           debit=0.0, credit=20 * L, cash_amount=-20 * L,
                           burn_category=BurnCategory.PEOPLE,
                           cost_nature=CostNature.FIXED, source="seed"))
        db.add(LedgerEntry(entity_id=sg.id, txn_date=me - timedelta(days=6),
                           voucher_type="Receipt", voucher_no=f"SG/RCT/{i}",
                           party="Vertex Semiconductor Pte Ltd",
                           narration="APAC licence revenue", debit=17 * L, credit=0.0,
                           cash_amount=17 * L, source="seed"))
    db.flush()
