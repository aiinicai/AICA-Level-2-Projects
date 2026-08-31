"""Demo seed: ABC Food Pvt. Ltd. — a complete, reproducible valuation journey.

All figures are illustrative. Every displayed number downstream is computed by
the deterministic engine from this seeded data — nothing is hardcoded in the UI.
Run with:  python -m app.seed
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import (
    AuditLog, Company, FinancialLineItem, FinancialPeriod, User,
    ValuationAssumption, ValuationCase, ValuationRun,
)
from .services.financial.canonical import STATEMENT_OF
from .services.financial.store import compute_case_analytics, persist_ratios
from .services.insights import refresh_insights
from .services.interview.engine import get_active_session, next_question, start_interview, submit_answer
from .services.valuation.orchestrator import calculate_and_persist

CR = 10_000_000.0

# ABC Food Pvt. Ltd. — three coherent years (₹ Cr), FY2024-25 grows 44% to
# deliberately trigger the REV_GROWTH_HIGH rule for the adaptive interview.
ABC_FINANCIALS: dict[str, dict[str, float]] = {
    "FY2022-23": dict(
        revenue=6.10, other_income=0.08, material_cost=3.42, employee_cost=0.82,
        other_operating_expenses=0.90, ebitda=0.96, depreciation=0.21, ebit=0.75,
        finance_cost=0.07, pbt=0.76, tax=0.19, pat=0.57,
        share_capital=1.00, reserves=1.72, net_worth=2.72, fixed_assets=1.95,
        investments=0.15, inventory=0.78, receivables=0.92, cash=0.28,
        other_current_assets=0.35, total_assets=4.43, long_term_borrowings=0.55,
        short_term_borrowings=0.18, trade_payables=0.60, other_liabilities=0.38,
        total_liabilities=1.71,
        cfo=0.71, cfi=-0.52, cff=-0.05, capex=0.50, opening_cash=0.14, closing_cash=0.28,
    ),
    "FY2023-24": dict(
        revenue=8.05, other_income=0.10, material_cost=4.42, employee_cost=1.02,
        other_operating_expenses=1.20, ebitda=1.41, depreciation=0.26, ebit=1.15,
        finance_cost=0.08, pbt=1.17, tax=0.30, pat=0.87,
        share_capital=1.00, reserves=2.44, net_worth=3.44, fixed_assets=2.30,
        investments=0.20, inventory=1.05, receivables=1.28, cash=0.35,
        other_current_assets=0.42, total_assets=5.60, long_term_borrowings=0.45,
        short_term_borrowings=0.15, trade_payables=0.82, other_liabilities=0.74,
        total_liabilities=2.16,
        cfo=0.95, cfi=-0.62, cff=-0.26, capex=0.60, opening_cash=0.28, closing_cash=0.35,
    ),
    "FY2024-25": dict(
        revenue=11.59, other_income=0.12, material_cost=6.26, employee_cost=1.32,
        other_operating_expenses=1.84, ebitda=2.17, depreciation=0.35, ebit=1.82,
        finance_cost=0.09, pbt=1.85, tax=0.47, pat=1.38,
        share_capital=1.00, reserves=3.62, net_worth=4.62, fixed_assets=2.85,
        investments=0.25, inventory=1.42, receivables=1.90, cash=0.18,
        other_current_assets=0.55, total_assets=7.15, long_term_borrowings=0.30,
        short_term_borrowings=0.12, trade_payables=1.05, other_liabilities=0.96,
        total_liabilities=2.53,
        cfo=1.15, cfi=-0.85, cff=-0.47, capex=0.80, opening_cash=0.35, closing_cash=0.18,
    ),
}

# statement page numbers in the (illustrative) source PDFs, for traceability
SOURCE_PAGES = {"pnl": 12, "balance_sheet": 10, "cash_flow": 14}

PEERS = [
    dict(name="Sunrise Textiles Ltd.", industry="Textiles", revenues=(9.8, 10.6, 11.4),
         margin=0.13, multiple=6.5, status="completed", days_ago=95,
         weights={"weight_dcf": 0.2, "weight_market_multiple": 0.6, "weight_adjusted_nav": 0.2}),
    dict(name="GreenTech Solutions", industry="Renewable Energy", revenues=(4.2, 6.4, 9.6),
         margin=0.24, multiple=11.0, status="completed", days_ago=97,
         weights={"weight_dcf": 0.6, "weight_market_multiple": 0.3, "weight_adjusted_nav": 0.1}),
    dict(name="Nova Retail Pvt. Ltd.", industry="Retail", revenues=(14.5, 15.2, 16.1),
         margin=0.09, multiple=7.0, status="completed", days_ago=98,
         weights={"weight_dcf": 0.2, "weight_market_multiple": 0.2, "weight_adjusted_nav": 0.6}),
    dict(name="BluePeak Industries", industry="Industrial Goods", revenues=(7.2, 8.6, 10.8),
         margin=0.16, multiple=8.0, status="interview", days_ago=99,
         weights={"weight_dcf": 0.5, "weight_market_multiple": 0.3, "weight_adjusted_nav": 0.2}),
]

# interview answers for the demo walkthrough (leaves a few questions open)
ABC_ANSWERS: dict[str, tuple[str, str]] = {
    "GROWTH_004": ("New customers", "Won two regional QSR chains and expanded modern-trade "
                                     "distribution during the year."),
    "FCST_001": ("16", "Order book and distribution pipeline support mid-teens growth."),
    "CUST_001": ("10% – 25%", ""),
    "PROF_001": ("Yes, broadly stable", "Input costs hedged through annual contracts."),
    "CAPEX_001": ("Moderate expansion", "New packaging line planned for FY2026-27."),
    "RISK_001": ("None material", ""),
    "BIZ_002": ("50–75% recurring", "Repeat institutional orders dominate."),
    "WC_001": ("Yes", ""),
    "RPT_001": ("At arm's length, disclosed", ""),
    "MGMT_001": ("Partially promoter-dependent", "Professional CEO hired in 2024."),
}


def reset(verbose: bool = True) -> None:
    """Drop and recreate every table *in place*, then reseed.

    Deliberately does NOT delete the database file. Unlinking a SQLite file while
    the server holds it open leaves the running process writing to an orphaned
    inode: uploads appear to succeed, then vanish when the server restarts and
    opens the newly created file. Resetting through the engine keeps one file and
    one inode, so a running server sees the reset immediately.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if verbose:
        print("Database reset — all tables dropped and recreated.")
    seed(verbose=verbose)


def seed(verbose: bool = True) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.execute(select(Company)).scalars().first() is not None:
            if verbose:
                print("Seed skipped — database already contains data.")
            return

        now = datetime.now(timezone.utc)
        today = now.date().isoformat()

        user = User(name="Arjun Demo", role="Analyst", email="arjun.demo@companyval.ai")
        db.add(user)
        db.flush()

        # -- ABC Food Pvt. Ltd. ------------------------------------------------
        abc = Company(name="ABC Food Pvt. Ltd.", industry="Food & Beverages",
                      entity_type="Private Limited Company", country="India")
        db.add(abc)
        db.flush()
        case = ValuationCase(
            company_id=abc.id, created_by=user.id, valuation_date=today,
            currency="INR", units="crore", purpose="Fund Raising",
            promoter_holding_pct=74.50, total_shares=1_000_000,
            notes="Valuation for Series C fund raise to support capacity expansion "
                  "and working capital requirements.",
            status="interview", financials_locked=1,
        )
        db.add(case)
        db.flush()

        periods = list(ABC_FINANCIALS.keys())
        for i, p in enumerate(periods):
            db.add(FinancialPeriod(case_id=case.id, label=p, order_index=i,
                                   end_date=f"20{23 + i}-03-31"))
        # two illustrative reconciliation stories for the review UI
        review_story = {("FY2024-25", "other_income"): (0.12, 0.14),
                        ("FY2023-24", "other_liabilities"): (0.74, 0.72)}
        for p, metrics in ABC_FINANCIALS.items():
            for metric, cr_value in metrics.items():
                statement = STATEMENT_OF.get(metric, "pnl")
                value = cr_value * CR
                py_val, ai_val = value, value
                status, conf, note = "verified", 0.96, ""
                if (p, metric) in review_story:
                    py_cr, ai_cr = review_story[(p, metric)]
                    py_val, ai_val = py_cr * CR, ai_cr * CR
                    status, conf = "needs_review", 0.74
                    note = "Analyst confirmed the Python-extracted figure against page image."
                db.add(FinancialLineItem(
                    case_id=case.id, period_label=p, statement=statement,
                    metric=metric, python_value=py_val, ai_visual_value=ai_val,
                    approved_value=value, original_display=f"{cr_value:,.2f}",
                    unit="crore", source_page=SOURCE_PAGES.get(statement, 10),
                    verification_status=status, confidence=conf,
                    review_note=note, approved_by=user.name,
                ))
        db.commit()

        # accepted assumptions (human-in-the-loop trail on revenue growth)
        assumptions = {
            "revenue_growth": 0.16, "ebitda_margin": 0.18, "wacc": 0.12,
            "terminal_growth": 0.03, "tax_rate": 0.25, "ev_ebitda_multiple": 7.0,
        }
        for key, value in assumptions.items():
            row = ValuationAssumption(case_id=case.id, key=key, value=value,
                                      source="user", status="accepted")
            if key == "revenue_growth":
                row.ai_recommended_value = 0.13
                row.ai_reason = ("Historical CAGR is 37.8% but includes new-customer "
                                 "wins that may not repeat at the same pace; a mid-teens "
                                 "assumption is more defensible than extrapolating 44%.")
            db.add(row)
        db.commit()

        # approved NAV revaluation schedule (factory land held at 1998 cost)
        from .models import NormalisationAdjustment
        db.add(NormalisationAdjustment(
            case_id=case.id, period_label="FY2024-25", metric="Land & Building",
            kind="nav_adjustment", reported_value=2.85 * CR, adjustment=3.50 * CR,
            reason="Factory land carried at 1998 acquisition cost; revalued to a "
                   "conservative fair market estimate for the NAV method.",
            source="analyst", status="approved", approved_by=user.name))
        db.add(NormalisationAdjustment(
            case_id=case.id, period_label="FY2024-25", metric="Investments",
            kind="nav_adjustment", reported_value=0.25 * CR, adjustment=0.20 * CR,
            reason="Quoted mutual-fund investments marked to current NAV.",
            source="analyst", status="approved", approved_by=user.name))

        # interview: start from rules, answer the scripted questions and leave
        # the rest pending so the demo interview is resumable mid-flow
        session = start_interview(db, case)
        from .models import InterviewQuestion
        questions = db.execute(select(InterviewQuestion).where(
            InterviewQuestion.session_id == session.id)
            .order_by(InterviewQuestion.order_index)).scalars().all()
        for q in questions:
            if q.question_code in ABC_ANSWERS and q.status == "pending":
                value, elaboration = ABC_ANSWERS[q.question_code]
                submit_answer(db, case, session, q, value, elaboration)
        db.commit()

        # a short history of valuation runs (older, slightly different assumptions)
        history = [
            (100, {"revenue_growth": 0.12, "ev_ebitda_multiple": 6.0}, "Initial Draft"),
            (65, {"revenue_growth": 0.14, "ev_ebitda_multiple": 6.5}, "Post-Interview"),
            (30, {"revenue_growth": 0.15}, "Assumption Review"),
        ]
        for days_ago, tweaks, label in history:
            for k, v in tweaks.items():
                row = db.execute(select(ValuationAssumption).where(
                    ValuationAssumption.case_id == case.id,
                    ValuationAssumption.key == k)).scalars().first()
                row.value = v
            db.commit()
            run = calculate_and_persist(db, case, analyst=user.name, run_label=label)
            run.created_at = now - timedelta(days=days_ago)
            db.commit()
        # restore accepted base assumptions and produce the current run
        for k, v in assumptions.items():
            row = db.execute(select(ValuationAssumption).where(
                ValuationAssumption.case_id == case.id,
                ValuationAssumption.key == k)).scalars().first()
            row.value = v
        db.commit()
        calculate_and_persist(db, case, analyst=user.name, run_label="Base Case")
        case.status = "completed"

        analytics = compute_case_analytics(db, case.id)
        persist_ratios(db, case.id, analytics)
        refresh_insights(db, case, use_ai=False)
        db.add(AuditLog(case_id=case.id, actor="system", action="demo_seeded",
                        detail={"company": abc.name}))
        db.commit()

        # -- peer companies for the dashboard ---------------------------------
        for peer in PEERS:
            comp = Company(name=peer["name"], industry=peer["industry"],
                           entity_type="Private Limited Company", country="India")
            db.add(comp)
            db.flush()
            pcase = ValuationCase(
                company_id=comp.id, created_by=user.id, valuation_date=today,
                currency="INR", units="crore", purpose="Internal Management Assessment",
                total_shares=0, status="documents", financials_locked=1,
            )
            db.add(pcase)
            db.flush()
            labels = ["FY2022-23", "FY2023-24", "FY2024-25"]
            for i, (label, rev) in enumerate(zip(labels, peer["revenues"])):
                db.add(FinancialPeriod(case_id=pcase.id, label=label, order_index=i))
                m = peer["margin"]
                items = dict(revenue=rev, ebitda=rev * m, depreciation=rev * 0.03,
                             ebit=rev * (m - 0.03), pat=rev * (m - 0.03) * 0.72,
                             net_worth=rev * 0.45, cash=rev * 0.03,
                             long_term_borrowings=rev * 0.10, total_assets=rev * 0.85,
                             cfo=rev * m * 0.8, capex=rev * 0.035)
                for metric, cr_val in items.items():
                    db.add(FinancialLineItem(
                        case_id=pcase.id, period_label=label,
                        statement=STATEMENT_OF.get(metric, "pnl"), metric=metric,
                        python_value=cr_val * CR, approved_value=cr_val * CR,
                        verification_status="verified", confidence=0.9,
                        approved_by=user.name))
            for k, v in ({"ebitda_margin": peer["margin"],
                          "ev_ebitda_multiple": peer["multiple"],
                          "revenue_growth": 0.10, "wacc": 0.13,
                          "terminal_growth": 0.03, "tax_rate": 0.25}
                         | peer["weights"]).items():
                db.add(ValuationAssumption(case_id=pcase.id, key=k, value=v,
                                           source="user", status="accepted"))
            db.commit()
            run = calculate_and_persist(db, pcase, analyst=user.name)
            run.created_at = now - timedelta(days=peer["days_ago"])
            pcase.status = peer["status"]
            pcase.updated_at = now - timedelta(days=peer["days_ago"])
            db.commit()

        if verbose:
            print("Seeded demo data: ABC Food Pvt. Ltd. + 4 peer cases.")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed the CompanyVal AI demo database.")
    parser.add_argument("--reset", action="store_true",
                        help="drop and recreate all tables in place before seeding "
                             "(safe to run while the server is up; never delete the .db file)")
    args = parser.parse_args()
    reset() if args.reset else seed()
