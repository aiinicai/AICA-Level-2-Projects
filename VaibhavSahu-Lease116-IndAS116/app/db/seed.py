"""First-run defaults and optional demonstration data (clearly labelled DEMO)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..engine.calendar_utils import add_months, month_end, next_day, prev_day
from ..engine.journals import ROLE_CATALOG
from ..services.security import ROLES, hash_password
from .models import (AssetClass, Company, Counterparty, Deposit, DiscountRate, Entity, FxRate, GLBalance, GLMapping, Lease,
                     LeaseAssessment, LeaseCost, LeaseEventRow, LeaseOptionRow, PaymentScheduleRow, RestorationObligation, Role, User)

DEFAULT_ADMIN_PASSWORD = "admin116"
DEMO_PASSWORD = "Lease@116"
ASSET_CLASSES = [("BLDG", "Buildings"), ("LAND", "Land"), ("VEH", "Vehicles"), ("PM", "Plant and machinery"),
                 ("IT", "IT equipment"), ("FF", "Furniture and fixtures")]


def seed_defaults(db: Session) -> None:
    for code, (name, perms) in ROLES.items():
        r = db.scalar(select(Role).where(Role.code == code))
        if r is None:
            db.add(Role(code=code, name=name, permissions=perms))
        else:
            r.name, r.permissions = name, perms
    db.flush()
    comp = db.scalar(select(Company))
    if comp is None:
        comp = Company(name="Lease116 Workspace", framework="IND_AS_116", functional_currency="INR", fy_start_month=4, settings={})
        db.add(comp)
        db.flush()
        db.add(Entity(company_id=comp.id, code="E01", name="Head Office", functional_currency="INR"))
        for code, name in ASSET_CLASSES:
            db.add(AssetClass(company_id=comp.id, code=code, name=name))
        for role, (code, name, _) in ROLE_CATALOG.items():
            db.add(GLMapping(company_id=comp.id, role=role, account_code=code, account_name=name))
    if db.scalar(select(User).where(User.username == "admin")) is None:
        admin_role = db.scalar(select(Role).where(Role.code == "ADMIN"))
        db.add(User(username="admin", full_name="Administrator", role_id=admin_role.id, password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                    must_change_password=True))
    db.commit()


# ------------------------------------------------------------------------------------------ demo data
def _user(db: Session, username: str, full: str, role: str) -> User:
    u = db.scalar(select(User).where(User.username == username))
    if u is None:
        r = db.scalar(select(Role).where(Role.code == role))
        u = User(username=username, full_name=full, role_id=r.id, password_hash=hash_password(DEMO_PASSWORD))
        db.add(u)
        db.flush()
    return u


def _cp(db: Session, comp: Company, name: str, related: bool = False) -> Counterparty:
    c = db.scalar(select(Counterparty).where(Counterparty.name == name))
    if c is None:
        c = Counterparty(company_id=comp.id, name=name, related_party=related, vendor_id=f"V{abs(hash(name)) % 90000 + 10000}")
        db.add(c)
        db.flush()
    return c


def _ac(db: Session, name: str) -> AssetClass:
    return db.scalar(select(AssetClass).where(AssetClass.name == name))


def load_demo_data(db: Session, admin) -> int:
    from ..services.lease_service import calculate, regenerate_payments
    from ..services.workflow_service import transition

    comp = db.scalar(select(Company))
    if db.scalar(select(Lease.id).where(Lease.description.like("DEMO%"))):
        return 0
    prep = _user(db, "preparer", "Priya (Preparer)", "PREPARER")
    rev = _user(db, "reviewer", "Rahul (Reviewer)", "REVIEWER")
    appr = _user(db, "approver", "Anita (Approver)", "APPROVER")
    _user(db, "auditor", "Arjun (Auditor)", "AUDITOR")
    _user(db, "accountant", "Lata (Lease Accountant)", "LEASE_ACCOUNTANT")
    for u in (prep, rev, appr):
        db.refresh(u)
    ent = db.scalar(select(Entity).where(Entity.code == "DEMO"))
    if ent is None:
        ent = Entity(company_id=comp.id, code="DEMO", name="DEMO Industries Limited (illustrative)", functional_currency="INR")
        db.add(ent)
        db.flush()
    s = dict(comp.settings or {})
    pol = dict(s.get("policies") or {})
    if pol.get("low_value_threshold") in (None, ""):
        pol["low_value_threshold"] = "350000"
    s["policies"] = pol
    comp.settings = s
    bld = _ac(db, "Buildings")
    bld.short_term_election = True
    _ac(db, "IT equipment").short_term_election = True
    for lo, hi, rate in ((0, 12, "8.50"), (13, 36, "9.00"), (37, 60, "9.25"), (61, 120, "9.75"), (121, 600, "10.25")):
        db.add(DiscountRate(company_id=comp.id, scope="PORTFOLIO", currency="INR", tenor_from_months=lo, tenor_to_months=hi,
                            rate_pct=Decimal(rate), rate_type="IBR", security="Secured by leased asset",
                            source="DEMO — illustrative build-up (reference rate + credit spread + term/security adjustments)",
                            methodology="Build-up: government securities yield for tenor + entity credit spread + lease-specific adjustment",
                            effective_date=date(2024, 4, 1), status="Approved", approved_by=appr.id, approved_at=datetime.now()))
    db.add(DiscountRate(company_id=comp.id, scope="PORTFOLIO", currency="USD", tenor_from_months=0, tenor_to_months=120,
                        rate_pct=Decimal("6.00"), rate_type="IBR", source="DEMO — illustrative", effective_date=date(2024, 4, 1),
                        status="Approved", approved_by=appr.id, approved_at=datetime.now()))
    # FX: USD/INR monthly (illustrative)
    d0 = date(2025, 3, 31)
    for k in range(0, 30):
        dd = month_end(add_months(d0, k))
        rate = Decimal("85.40") + Decimal("0.12") * k
        db.add(FxRate(from_ccy="USD", to_ccy="INR", rate_date=dd, rate=rate, rate_type="CLOSING", source="DEMO — illustrative"))
        db.add(FxRate(from_ccy="USD", to_ccy="INR", rate_date=dd, rate=rate - Decimal("0.06"), rate_type="AVERAGE", source="DEMO"))
    db.add(FxRate(from_ccy="USD", to_ccy="INR", rate_date=date(2025, 4, 1), rate=Decimal("85.40"), rate_type="SPOT", source="DEMO"))
    db.flush()

    created = []

    def new_lease(code, desc, cls, lessor, comm, end, cfg, rate, **kw) -> Lease:
        l = Lease(lease_code=code, company_id=comp.id, entity_id=ent.id, description=desc, asset_class_id=_ac(db, cls).id,
                  counterparty_id=_cp(db, comp, lessor, kw.pop("related", False)).id, commencement_date=comm, availability_date=comm,
                  contract_end=end, contract_date=kw.pop("contract_date", comm - timedelta(days=15)), currency=kw.pop("currency", "INR"),
                  discount_rate_pct=Decimal(rate) if rate else None, generator_config=cfg, created_by=prep.id, status="Draft",
                  rate_source=kw.pop("rate_source", "Portfolio IBR table (DEMO)"), **kw)
        db.add(l)
        db.flush()
        db.add(LeaseAssessment(lease_id=l.id, identified_asset=True, substitution_rights="NONE", economic_benefits=True, directs_use=True,
                               contains_lease=True, exemption=l.lease_type if l.lease_type in ("SHORT_TERM", "LOW_VALUE") else "NONE",
                               conclusion="Contract conveys the right to control the use of an identified asset (DEMO)."))
        db.flush()
        created.append(l)
        return l

    def cfg(amount, start, end, **k):
        c = {"amount": str(amount), "start_date": start.isoformat(), "end_date": end.isoformat(), "frequency_months": 1,
             "timing": "ADVANCE", "alignment": "ANNIVERSARY", "escalations": [], "rent_free": [], "non_lease_amount": "0"}
        c.update(k)
        return c

    # 1 Office — leave and licence (from the sample agreement)
    c1, e1 = date(2025, 4, 1), date(2030, 3, 31)
    l1 = new_lease("DEMO-001", "DEMO — Office premises, Andheri East, Mumbai (leave & licence)", "Buildings", "ABC Realty Private Limited",
                   c1, e1, cfg(450000, c1, e1, alignment="CALENDAR", due_day=7, non_lease_amount="55000",
                               escalations=[{"value": "5", "every_months": 12, "compounding": True}],
                               rent_free=[{"start": c1.isoformat(), "end": (c1 + timedelta(days=59)).isoformat()}]), "9.25",
                   location="Andheri East, Mumbai", cost_centre="CC-ADMIN", contract_number="LL/2025/017", contract_date=date(2025, 3, 15))
    l1.options.append(LeaseOptionRow(kind="TERMINATION", holder="LESSEE", exercise_date=date(2028, 3, 31), reasonably_certain=True,
                                     rationale="Significant fit-out spend (₹2.1 Cr) and relocation cost; location critical — reasonably "
                                               "certain not to exit after lock-in.", description="Lessee may terminate after 36-month lock-in"))
    l1.options.append(LeaseOptionRow(kind="EXTENSION", holder="LESSOR", exercise_date=date(2030, 4, 1), extension_end_date=date(2035, 3, 31),
                                     reasonably_certain=False, renewal_escalation_pct=Decimal("15"),
                                     rationale="Renewal only by mutual consent — not a lessee option (B34).", description="Renewal by mutual consent"))
    l1.deposits.append(Deposit(amount=Decimal("2700000"), payment_date=c1, refund_date=date(2030, 4, 1), market_rate_pct=Decimal("9.00"),
                               treat_difference_as_prepaid_rent=True))
    l1.costs += [LeaseCost(kind="IDC", cost_date=c1, amount=Decimal("118500"), description="Stamp duty & registration"),
                 LeaseCost(kind="IDC", cost_date=c1, amount=Decimal("450000"), description="Brokerage")]
    l1.restorations.append(RestorationObligation(estimated_cost=Decimal("1500000"), settlement_date=date(2030, 3, 31),
                                                 discount_rate_pct=Decimal("8.0"), recognition_date=c1, notes="Removal of fit-outs (DEMO estimate)"))
    # 2 Warehouse
    c2, e2 = date(2025, 2, 1), date(2034, 1, 31)
    l2 = new_lease("DEMO-002", "DEMO — Warehouse Shed B-2, Bhiwandi (lease deed 3+3+3)", "Buildings", "PQR Logistics Parks LLP", c2, e2,
                   cfg(1200000, c2, e2, due_day=5, escalations=[{"value": "15", "every_months": 36, "compounding": True}]), "9.75",
                   location="Bhiwandi, Thane", cost_centre="CC-LOG")
    l2.options.append(LeaseOptionRow(kind="TERMINATION", holder="LESSEE", exercise_date=date(2028, 1, 31), reasonably_certain=True,
                                     rationale="Hub for western region distribution; racking installed", description="Break after 3 years"))
    l2.options.append(LeaseOptionRow(kind="EXTENSION", holder="LESSEE", exercise_date=date(2034, 2, 1), extension_end_date=date(2039, 1, 31),
                                     reasonably_certain=False, rationale="Too far in the future to be reasonably certain",
                                     description="Renewal for 5 years at lessee's option"))
    l2.deposits.append(Deposit(amount=Decimal("7200000"), payment_date=c2, refund_date=date(2034, 2, 1), market_rate_pct=Decimal("9.25")))
    # 3 Equipment with purchase option (left pending approval)
    c3, e3 = date(2025, 7, 1), date(2028, 6, 30)
    l3 = new_lease("DEMO-003", "DEMO — 4 CNC machining centres (equipment lease)", "Plant and machinery", "DEF Leasing Limited", c3, e3,
                   cfg(600000, c3, e3, frequency_months=3, timing="ARREARS"), "10.50", useful_life_end=date(2035, 6, 30), cost_centre="CC-PROD")
    l3.options.append(LeaseOptionRow(kind="PURCHASE", holder="LESSEE", exercise_date=e3, price=Decimal("500000"), reasonably_certain=True,
                                     rationale="Option price ₹5 lakh vs expected fair value ₹60 lakh — bargain", description="Purchase option"))
    # 4 Vehicle — modified
    c4, e4 = date(2024, 10, 1), date(2027, 9, 30)
    l4 = new_lease("DEMO-004", "DEMO — Leased car for CFO (operating lease vendor)", "Vehicles", "GHI Fleet Services Private Limited", c4, e4,
                   cfg(45000, c4, e4), "9.00", cost_centre="CC-FIN")
    # 5 Retail store — variable rent + impairment
    c5, e5 = date(2025, 9, 1), date(2034, 8, 31)
    l5 = new_lease("DEMO-005", "DEMO — Retail store G-14, Sample Mall, Bengaluru", "Buildings", "STU Malls Private Limited", c5, e5,
                   cfg(300000, c5, e5, non_lease_amount="225000", escalations=[{"value": "15", "every_months": 36, "compounding": True}]),
                   "9.75", location="Bengaluru", cost_centre="CC-RETAIL")
    l5.options.append(LeaseOptionRow(kind="TERMINATION", holder="LESSEE", exercise_date=date(2028, 8, 31), reasonably_certain=False,
                                     rationale="New format store; performance uncertain — not reasonably certain to continue beyond lock-in",
                                     description="Lessee may exit after 3-year lock-in"))
    # 6 USD colocation (FX)
    c6, e6 = date(2025, 4, 1), date(2027, 3, 31)
    l6 = new_lease("DEMO-006", "DEMO — Data-centre colocation rack (USD)", "IT equipment", "Global Colo Pte Ltd (DEMO)", c6, e6,
                   cfg(10000, c6, e6, timing="ARREARS"), "6.00", currency="USD", cost_centre="CC-IT", rate_source="USD portfolio IBR (DEMO)")
    # 7 Short-term guest house
    c7, e7 = date(2025, 6, 1), date(2026, 4, 30)
    new_lease("DEMO-007", "DEMO — Guest house, Pune (11-month leave & licence)", "Buildings", "Mr. Sample Owner", c7, e7,
              cfg(60000, c7, e7), None, lease_type="SHORT_TERM")
    # 8 Low-value laptops
    c8, e8 = date(2025, 4, 1), date(2028, 3, 31)
    l8 = new_lease("DEMO-008", "DEMO — 25 laptops (operating rental)", "IT equipment", "JKL Rentals Private Limited", c8, e8,
                   cfg(4000, c8, e8), None, lease_type="LOW_VALUE")
    a8 = db.scalar(select(LeaseAssessment).where(LeaseAssessment.lease_id == l8.id))
    a8.asset_value_when_new = Decimal("80000")
    a8.benefits_on_own, a8.not_highly_dependent = True, True
    a8.conclusion = "Laptops (value when new ₹80,000 each) — low-value assets; lessee benefits from each on its own (B3–B5)."
    # 9 Branch office — terminated early
    c9, e9 = date(2024, 7, 1), date(2029, 6, 30)
    l9 = new_lease("DEMO-009", "DEMO — Branch office, Kharadi, Pune", "Buildings", "MNO Properties", c9, e9, cfg(150000, c9, e9), "9.00",
                   cost_centre="CC-SALES")
    # 10 Lessor operating lease (escalating rent, interest-free deposit received; classified without an implicit rate)
    c10, e10 = date(2025, 1, 1), date(2029, 12, 31)
    l10 = new_lease("DEMO-010", "DEMO — Floor 3 of owned building leased to tenant (lessor)", "Buildings", "PQRS Consulting LLP",
                    c10, e10, cfg(200000, c10, e10, escalations=[{"value": "5", "every_months": 12, "compounding": True}]), None,
                    role="LESSOR", rate_source=None,
                    lessor_details={"fair_value": "50000000", "carrying_amount": "32000000", "economic_life_months": 600,
                                    "lessor_idc": "200000"})
    l10.deposits.append(Deposit(amount=Decimal("1200000"), payment_date=c10, refund_date=date(2030, 1, 1), market_rate_pct=Decimal("9.00"),
                                treat_difference_as_prepaid_rent=True, notes="Interest-free deposit received from the tenant (DEMO)"))
    # 12 Lessor finance lease — machine leased to a customer (not a manufacturer / dealer)
    c12, e12 = date(2025, 4, 1), date(2030, 3, 31)
    l12 = new_lease("DEMO-012", "DEMO — CNC machine leased to a customer (lessor, finance lease)", "Plant and machinery",
                    "VWX Engineering Private Limited", c12, e12, cfg(150000, c12, e12, frequency_months=3, timing="ARREARS"), None,
                    role="LESSOR", rate_source=None, cost_centre="CC-LEASING",
                    lessor_details={"fair_value": "2500000", "carrying_amount": "2100000", "economic_life_months": 72,
                                    "unguaranteed_residual": "200000", "lessor_idc": "25000"})
    # 11 Sale and leaseback
    c11 = date(2025, 4, 1)
    e11 = prev_day(add_months(c11, 12 * 18))
    l11 = new_lease("DEMO-011", "DEMO — Corporate office building sale and leaseback (IFRS 16 IE24 pattern)", "Buildings",
                    "Buyer: XYZ REIT Trust (DEMO)", c11, e11, cfg(12000000, c11, e11, frequency_months=12, timing="ARREARS"), "4.50",
                    lease_type="SALE_LEASEBACK",
                    slb_details={"is_sale": True, "carrying_amount": "100000000", "sale_consideration": "200000000",
                                 "fair_value": "180000000", "asset_description": "Corporate office building",
                                 "assessment_notes": "Control transferred (legal title, possession, risks & rewards) — Ind AS 115.38; "
                                                     "no repurchase option (DEMO)"},
                    policy_overrides={"daycount": "MONTHS/12"})
    db.flush()
    for l in created:
        regenerate_payments(db, l, prep)
    # variable revenue share lines on the retail store (expected amounts)
    for k in range(1, 7):
        d = month_end(add_months(c5, k))
        l5.payments.append(PaymentScheduleRow(line_no=900 + k, payment_date=d, lease_amount=Decimal("45000") + Decimal("5000") * k,
                                              non_lease_amount=Decimal(0), category="VARIABLE",
                                              description="Revenue share 12% over MG (actual)", source="MANUAL"))
    db.flush()

    def approve(l: Lease):
        calculate(db, l, prep)
        transition(db, l, "submit", prep)
        transition(db, l, "start_review", rev)
        transition(db, l, "approve", appr, "Reviewed and approved (DEMO)")

    for l in (l1, l2, l4, l5, l6, created[6], l8, l9, l10, l11, l12):
        approve(l)
    calculate(db, l3, prep)
    transition(db, l3, "submit", prep)
    # events
    def event(l: Lease, etype, eff, desc, details, subtype=None):
        ev = LeaseEventRow(lease_id=l.id, event_type=etype, subtype=subtype, effective_date=eff, description=desc, details=details,
                           status="Draft", prepared_by=prep.id)
        l.events.append(ev)
        db.flush()
        l.status = "Draft"
        approve(l)

    event(l4, "MODIFICATION", date(2026, 4, 1), "Term extended by 12 months; rent reduced to ₹42,000 (negotiated)",
          {"revised_rate_pct": "9.10", "new_term_end": "2028-09-30", "payments_mode": "GENERATE",
           "new_payment_terms": {"amount": "42000", "start_date": "2026-04-01", "end_date": "2028-09-30", "frequency_months": 1,
                                 "timing": "ADVANCE", "alignment": "ANNIVERSARY"}})
    event(l5, "IMPAIRMENT", date(2026, 3, 31), "Store underperforming — impairment of ROU (value in use)",
          {"impairment_amount": "2500000", "cgu": "Store G-14 Bengaluru", "rationale": "Footfall 35% below plan; VIU ₹ per DCF (DEMO)"})
    event(l9, "TERMINATION", date(2026, 7, 1), "Branch closed — lease terminated with 2 months' rent as penalty",
          {"penalty": "300000"})
    event(l10, "MODIFICATION", date(2026, 7, 1), "Rent renegotiated to ₹2,30,000 p.m. from July 2026 (5% annual escalation continues)",
          {"payments_mode": "GENERATE", "new_payment_terms": {"amount": "230000", "start_date": "2026-07-01", "end_date": "2029-12-31",
                                                              "frequency_months": 1, "timing": "ADVANCE", "alignment": "ANNIVERSARY",
                                                              "escalations": [{"value": "5", "every_months": 12, "compounding": True}]}},
          subtype="OPERATING_MODIFICATION")
    event(l12, "ECL", date(2026, 3, 31), "Loss allowance on the lease receivable — simplified approach (DEMO)",
          {"loss_allowance": "25000"})
    # GL balances for reconciliation demo (books slightly different from recomputation)
    for code, bal in (("23010", Decimal("-212500000.00")), ("13010", Decimal("245000000.00")), ("13020", Decimal("-18500000.00"))):
        db.add(GLBalance(company_id=comp.id, entity_id=ent.id, account_code=code, as_of=date(2026, 3, 31), balance=bal,
                         source="DEMO trial balance"))
    return len(created)
