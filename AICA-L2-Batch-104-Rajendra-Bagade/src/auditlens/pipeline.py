"""
The engagement pipeline: everything from two trial balances and a general
ledger to a completed set of analytical workpapers.

This module holds no audit logic of its own.  It sequences the engine and
carries the results, so that the API, the command line and the tests all
exercise exactly the same path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from . import caro as caro_module
from .financials import (
    FinancialStatements,
    Figures,
    MappedTrialBalance,
    build_statements,
    derive_figures,
    map_trial_balance,
)
from .ingest import GeneralLedger, TrialBalance, load_general_ledger, load_trial_balance
from .je_analytics import JEAnalysis, run_all_tests
from .materiality import (
    Materiality,
    SamplePlan,
    compute_materiality,
    monetary_unit_sample,
    suggest_benchmark,
)
from .ratios import RatioSchedule, build_schedule
from .schedule3 import MappingSummary, summarise

DISCLAIMER = (
    "Machine-generated analytical output. Every figure, selection and draft in "
    "this workpaper requires the review and professional judgement of a "
    "Chartered Accountant before it is relied upon or issued."
)


@dataclass
class EngagementInputs:
    """What the engagement team supplies alongside the accounting records."""

    client_name: str
    financial_year: str
    year_end: date
    company_class: str = "private"                  # "private" | "public"
    principal_repayments: float = 0.0
    credit_sales_ratio: float = 1.0
    credit_purchase_ratio: float = 1.0
    working_capital_limit: float = 0.0
    materiality_benchmark: str | None = None        # None = engine suggests
    materiality_percentage: float | None = None
    performance_pct: float = 0.75
    is_holding_or_subsidiary_of_public: bool = False
    holidays: set[date] = field(default_factory=set)
    sampling_seed: int = 20250401


@dataclass
class EngagementResult:
    inputs: EngagementInputs
    trial_balance: TrialBalance
    prior_trial_balance: TrialBalance | None
    mapped: MappedTrialBalance
    mapping: MappingSummary
    figures: Figures
    prior_figures: Figures | None
    statements: FinancialStatements
    ratios: RatioSchedule
    materiality: Materiality
    materiality_rationale: str
    general_ledger: GeneralLedger | None = None
    je_analysis: JEAnalysis | None = None
    sample: SamplePlan | None = None
    caro: caro_module.CAROChecklist | None = None
    sampling_note: str = ""
    disclaimer: str = DISCLAIMER

    # ---- headline numbers for the dashboard --------------------------
    def headlines(self) -> dict:
        f = self.figures
        return {
            "client": self.inputs.client_name,
            "financial_year": self.inputs.financial_year,
            "revenue": f.revenue_from_operations,
            "profit_before_tax": f.profit_before_tax,
            "profit_after_tax": f.profit_after_tax,
            "total_assets": f.total_assets,
            "trial_balance_tallies": self.trial_balance.balances,
            "trial_balance_difference": self.trial_balance.difference,
            "balance_sheet_tallies": self.statements.balance_sheet_tallies,
            "balance_sheet_reconciliation": self.statements.reconciliation,
            "mapping_coverage": self.mapping.coverage,
            "ledgers_for_review": len(self.mapping.review),
            "overall_materiality": self.materiality.overall,
            "performance_materiality": self.materiality.performance,
            "ratios_requiring_explanation": len(self.ratios.to_explain),
            "je_entries_flagged": len(self.je_analysis.flagged_entries) if self.je_analysis else 0,
            "je_total_entries": self.je_analysis.total_entries if self.je_analysis else 0,
            "benford_conclusion": self.je_analysis.benford.conclusion if self.je_analysis else "",
            "caro_applies": self.caro.applicability.applies if self.caro else None,
            "caro_prefilled": self.caro.prefilled_count if self.caro else 0,
            "sampling_note": self.sampling_note,
        }


def run_engagement(
    *,
    inputs: EngagementInputs,
    trial_balance_path: str | Path,
    prior_trial_balance_path: str | Path | None = None,
    general_ledger_path: str | Path | None = None,
) -> EngagementResult:
    """Run the full analytical review for one engagement."""

    tb = load_trial_balance(trial_balance_path, inputs.financial_year)
    prior_tb = (
        load_trial_balance(prior_trial_balance_path, "prior year")
        if prior_trial_balance_path
        else None
    )

    mapped = map_trial_balance(tb)
    mapped_prior = map_trial_balance(prior_tb) if prior_tb else None
    mapping = summarise(mapped.classifications)

    figures = derive_figures(
        mapped,
        principal_repayments=inputs.principal_repayments,
        credit_sales_ratio=inputs.credit_sales_ratio,
        credit_purchase_ratio=inputs.credit_purchase_ratio,
    )
    prior_figures = (
        derive_figures(
            mapped_prior,
            principal_repayments=inputs.principal_repayments,
            credit_sales_ratio=inputs.credit_sales_ratio,
            credit_purchase_ratio=inputs.credit_purchase_ratio,
        )
        if mapped_prior
        else None
    )

    statements = build_statements(
        mapped,
        mapped_prior,
        profit_for_the_year=figures.profit_after_tax,
        prior_profit=prior_figures.profit_after_tax if prior_figures else None,
    )
    ratios = build_schedule(figures, prior_figures)

    # ---- materiality --------------------------------------------------
    benchmark = inputs.materiality_benchmark
    rationale = ""
    if benchmark is None:
        benchmark, rationale = suggest_benchmark(
            figures.profit_before_tax,
            figures.revenue_from_operations,
            figures.total_assets,
            figures.shareholders_equity,
        )
    amounts = {
        "profit_before_tax": figures.profit_before_tax,
        "revenue": figures.revenue_from_operations,
        "total_assets": figures.total_assets,
        "equity": figures.shareholders_equity,
    }
    materiality = compute_materiality(
        benchmark=benchmark,
        benchmark_amount=amounts[benchmark],
        percentage=inputs.materiality_percentage,
        performance_pct=inputs.performance_pct,
        rationale=rationale,
    )

    result = EngagementResult(
        inputs=inputs,
        trial_balance=tb,
        prior_trial_balance=prior_tb,
        mapped=mapped,
        mapping=mapping,
        figures=figures,
        prior_figures=prior_figures,
        statements=statements,
        ratios=ratios,
        materiality=materiality,
        materiality_rationale=rationale,
    )

    # ---- journal entry testing and sampling ---------------------------
    if general_ledger_path:
        gl = load_general_ledger(general_ledger_path, inputs.financial_year)
        result.general_ledger = gl
        result.je_analysis = run_all_tests(
            gl.df, inputs.year_end, materiality.performance, inputs.holidays
        )

        population = (
            gl.df.groupby("entry_id")
            .agg(amount=("debit", "sum"), description=("narration", "first"))
            .reset_index()
        )
        # Materiality can compute to zero - a dormant company, or a first year
        # with no revenue and no profit. Sampling is then impossible, which is
        # a finding for the auditor, not a crash.
        if materiality.performance > 0 and not population.empty:
            try:
                result.sample = monetary_unit_sample(
                    population,
                    amount_column="amount",
                    id_column="entry_id",
                    description_column="description",
                    tolerable_misstatement=materiality.performance,
                    seed=inputs.sampling_seed,
                )
            except ValueError as exc:
                result.sampling_note = f"No sample was selected: {exc}"
        else:
            result.sampling_note = (
                "No sample was selected. Performance materiality computed to zero, "
                "which means the chosen benchmark is itself zero. Choose a different "
                "benchmark before sampling."
                if materiality.performance <= 0
                else "No sample was selected: the journal entry population is empty."
            )

    # ---- CARO 2020 ----------------------------------------------------
    p = mapped.presented
    applicability = caro_module.check_applicability(
        company_class=inputs.company_class,
        paid_up_capital=p("Share capital"),
        reserves_and_surplus=p("Reserves and surplus"),
        turnover=figures.revenue_from_operations,
        total_borrowings=figures.total_debt,
        total_revenue=figures.total_income,
        is_holding_or_subsidiary_of_public=inputs.is_holding_or_subsidiary_of_public,
    )
    current_ratio = next(
        (r.value for r in ratios.results if r.key == "current_ratio"), None
    )
    cash_profit = figures.profit_after_tax + figures.depreciation
    prior_cash_profit = (
        prior_figures.profit_after_tax + prior_figures.depreciation
        if prior_figures
        else None
    )
    result.caro = caro_module.build_checklist(
        applicability,
        facts={
            "has_ppe": p("Property, plant and equipment") > 0,
            "ppe_value": p("Property, plant and equipment"),
            "has_inventory": figures.inventories > 0,
            "inventory_value": figures.inventories,
            "working_capital_limit": inputs.working_capital_limit,
            "statutory_dues_outstanding": p("Other current liabilities"),
            "has_borrowings": figures.total_debt > 0,
            "borrowings_value": figures.total_debt,
            "cash_loss_current": cash_profit,
            "cash_loss_prior": prior_cash_profit,
            "current_ratio": current_ratio,
            "csr_applicable": any(
                "csr" in str(n).lower() for n in mapped.df["account_name"]
            ),
            "related_party_balances": int(
                sum(
                    1
                    for n in mapped.df["account_name"]
                    if "associate" in str(n).lower() or "subsidiar" in str(n).lower()
                )
            ),
        },
    )

    return result
