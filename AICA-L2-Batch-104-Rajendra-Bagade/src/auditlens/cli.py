"""
Command line entry point.

    python -m auditlens --samples
    python -m auditlens --tb tb.csv --prior prior.csv --gl ledger.csv \
        --client "Acme Private Limited" --fy 2024-25 --year-end 2025-03-31

Produces the same figures as the web application, because both call the
same engine.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from .formatting import compact, inr
from .narrate import draft_all
from .pipeline import EngagementInputs, run_engagement
from .report import build_workbook

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"

RULE = "-" * 76


def _heading(text: str) -> None:
    print(f"\n{text}\n{RULE}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auditlens",
        description="Statutory audit analytical review for Indian companies.",
    )
    parser.add_argument("--tb", help="Trial balance for the year under audit (CSV or Excel)")
    parser.add_argument("--prior", help="Comparative trial balance")
    parser.add_argument("--gl", help="General ledger, for SA 240 testing")
    parser.add_argument("--client", default="Sample Client Private Limited")
    parser.add_argument("--fy", default="2024-25", help="Financial year, e.g. 2024-25")
    parser.add_argument("--year-end", default="2025-03-31", help="YYYY-MM-DD")
    parser.add_argument("--company-class", default="private", choices=["private", "public"])
    parser.add_argument("--principal-repayments", type=float, default=0.0)
    parser.add_argument("--credit-sales-ratio", type=float, default=1.0)
    parser.add_argument("--credit-purchase-ratio", type=float, default=1.0)
    parser.add_argument("--working-capital-limit", type=float, default=0.0)
    parser.add_argument("--benchmark", default=None,
                        choices=["profit_before_tax", "revenue", "total_assets", "equity"])
    parser.add_argument("--out", default="AuditLens_workpaper.xlsx",
                        help="Path for the Excel workpaper")
    parser.add_argument("--drafts", action="store_true",
                        help="Also draft the memorandum and the ratio notes")
    parser.add_argument("--samples", action="store_true",
                        help="Run against the bundled synthetic client")

    args = parser.parse_args(argv)

    if args.samples:
        tb = SAMPLES / "trial_balance_FY2024-25.csv"
        prior = SAMPLES / "trial_balance_FY2023-24.csv"
        gl = SAMPLES / "general_ledger_FY2024-25.csv"
        client = "Bharat Precision Components Private Limited"
        principal, credit_sales, credit_purchases, wc_limit = (
            75_00_000, 0.92, 0.95, 6_00_00_000
        )
    elif args.tb:
        tb, prior, gl = Path(args.tb), args.prior, args.gl
        client = args.client
        principal = args.principal_repayments
        credit_sales = args.credit_sales_ratio
        credit_purchases = args.credit_purchase_ratio
        wc_limit = args.working_capital_limit
    else:
        parser.error("Supply --tb, or --samples to run the bundled synthetic client.")
        return 2

    inputs = EngagementInputs(
        client_name=client,
        financial_year=args.fy,
        year_end=datetime.strptime(args.year_end, "%Y-%m-%d").date(),
        company_class=args.company_class,
        principal_repayments=principal,
        credit_sales_ratio=credit_sales,
        credit_purchase_ratio=credit_purchases,
        working_capital_limit=wc_limit,
        materiality_benchmark=args.benchmark,
    )

    result = run_engagement(
        inputs=inputs,
        trial_balance_path=tb,
        prior_trial_balance_path=prior,
        general_ledger_path=gl,
    )
    h = result.headlines()

    _heading(f"{client} - financial year {args.fy}")
    print(f"  Revenue                {compact(h['revenue']):>18}")
    print(f"  Profit before tax      {compact(h['profit_before_tax']):>18}")
    print(f"  Profit after tax       {compact(h['profit_after_tax']):>18}")
    print(f"  Total assets           {compact(h['total_assets']):>18}")
    print(f"  Trial balance          {'tallies' if h['trial_balance_tallies'] else 'DOES NOT TALLY':>18}")
    print(f"\n  {result.statements.reconciliation}")

    _heading("Materiality (SA 320)")
    m = result.materiality
    print(f"  Benchmark              {m.benchmark_label} ({m.percentage:.2%})")
    print(f"  Overall                {compact(m.overall):>18}")
    print(f"  Performance            {compact(m.performance):>18}")
    print(f"  Clearly trivial        {compact(m.trivial):>18}")
    print(f"  Rationale: {m.rationale}")

    _heading("Schedule III ratios")
    for r in result.ratios.results:
        flag = "  <- explain in the notes" if r.requires_explanation else ""
        prior_text = "n/a" if r.prior_value is None else f"{r.prior_value:.2f}"
        variance = "n/a" if r.variance is None else f"{r.variance * 100:+.1f}%"
        print(f"  {r.name:<38} {r.formatted():>12}   prev {prior_text:>8}  {variance:>8}{flag}")

    _heading("Schedule III mapping")
    print(f"  Coverage {h['mapping_coverage']:.1%}; {h['ledgers_for_review']} ledger(s) need your classification:")
    for c in result.mapping.review:
        print(f"    {c.account_code:<8} {c.account_name:<52} -> {c.head}")

    if result.je_analysis:
        _heading("Journal entry testing (SA 240)")
        for t in result.je_analysis.tests:
            print(f"  {t.name:<38} {t.flagged:>5} flagged of {t.population}   ({t.rate:.2%})")
        b = result.je_analysis.benford
        print(f"  Benford first-digit MAD {b.mad:.5f} - {b.conclusion}")

    if result.sample:
        _heading("Sample (SA 530)")
        s = result.sample
        print(f"  Interval Rs {inr(s.sampling_interval)}, random start Rs {inr(s.random_start)}, seed {s.seed}")
        print(f"  {s.sample_size} items selected, {s.coverage:.1%} of value")
        for w in s.warnings:
            print(f"  ! {w}")

    if result.caro:
        _heading("CARO 2020")
        print(f"  {'Applies' if result.caro.applicability.applies else 'Does not apply'}: "
              f"{' '.join(result.caro.applicability.reasons)}")
        print(f"  {result.caro.prefilled_count} of {len(result.caro.clauses)} clauses "
              "pre-populated from the books.")

    if args.drafts:
        drafts = draft_all(result)
        _heading(f"Drafts ({drafts['memorandum'].source})")
        print(drafts["memorandum"].body)
        for d in drafts["ratio_notes"]:
            print(f"\n  {d.title}\n  {d.body}")

    path = build_workbook(result, args.out)
    _heading("Workpaper")
    print(f"  Written to {path}")
    print(f"\n{result.disclaimer}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
