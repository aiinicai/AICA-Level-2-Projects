"""
Materiality (SA 320) and audit sampling (SA 530).

SA 320, 'Materiality in Planning and Performing an Audit', requires the
auditor to determine materiality for the financial statements as a whole,
performance materiality, and the threshold below which misstatements are
clearly trivial.  The standard does not prescribe percentages; the
benchmarks below are the commonly applied ranges, and every one of them
is a matter for the auditor's judgement, which the tool records rather
than replaces.

SA 530, 'Audit Sampling', requires a sampling method that gives every
sampling unit a chance of selection.  Monetary unit sampling is
implemented here, with a fixed interval and a documented random start so
that the selection is reproducible and can be re-performed by a reviewer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pandas as pd

from .formatting import inr

BENCHMARKS: dict[str, dict] = {
    "profit_before_tax": {
        "label": "Profit before tax",
        "low": 0.05,
        "high": 0.10,
        "typical": 0.05,
        "when": "Profit-oriented entity with stable earnings",
    },
    "revenue": {
        "label": "Revenue from operations",
        "low": 0.005,
        "high": 0.01,
        "typical": 0.01,
        "when": "Earnings are volatile or marginal; revenue is the primary measure",
    },
    "total_assets": {
        "label": "Total assets",
        "low": 0.01,
        "high": 0.02,
        "typical": 0.01,
        "when": "Asset-holding or investment entity",
    },
    "equity": {
        "label": "Shareholders' equity",
        "low": 0.02,
        "high": 0.05,
        "typical": 0.02,
        "when": "Solvency is the users' principal concern",
    },
}


@dataclass
class Materiality:
    benchmark: str
    benchmark_label: str
    benchmark_amount: float
    percentage: float
    overall: float
    performance: float
    trivial: float
    performance_pct: float
    trivial_pct: float
    rationale: str = ""
    reference: str = "SA 320"

    def as_rows(self) -> list[dict]:
        return [
            {"Item": "Benchmark", "Basis": self.benchmark_label,
             "Amount (Rs)": self.benchmark_amount, "Rate": ""},
            {"Item": "Materiality for the financial statements as a whole",
             "Basis": f"{self.percentage:.2%} of {self.benchmark_label.lower()}",
             "Amount (Rs)": self.overall, "Rate": f"{self.percentage:.2%}"},
            {"Item": "Performance materiality",
             "Basis": f"{self.performance_pct:.0%} of overall materiality",
             "Amount (Rs)": self.performance, "Rate": f"{self.performance_pct:.0%}"},
            {"Item": "Clearly trivial threshold",
             "Basis": f"{self.trivial_pct:.0%} of overall materiality",
             "Amount (Rs)": self.trivial, "Rate": f"{self.trivial_pct:.0%}"},
        ]


def compute_materiality(
    *,
    benchmark: str,
    benchmark_amount: float,
    percentage: float | None = None,
    performance_pct: float = 0.75,
    trivial_pct: float = 0.05,
    rationale: str = "",
) -> Materiality:
    """Determine the materiality set for the engagement.

    `performance_pct` is conventionally 50-75 per cent of overall
    materiality; a lower figure is used where the expectation of
    misstatement is higher.
    """
    if benchmark not in BENCHMARKS:
        raise ValueError(
            f"Unknown benchmark '{benchmark}'. Choose from: {', '.join(BENCHMARKS)}"
        )
    spec = BENCHMARKS[benchmark]
    pct = spec["typical"] if percentage is None else percentage
    if not (spec["low"] <= pct <= spec["high"]):
        rationale = (
            f"{rationale} Rate of {pct:.2%} sits outside the customary "
            f"{spec['low']:.2%}-{spec['high']:.2%} range for this benchmark and "
            "requires documented justification."
        ).strip()

    amount = abs(benchmark_amount)
    overall = round(amount * pct, 2)
    return Materiality(
        benchmark=benchmark,
        benchmark_label=spec["label"],
        benchmark_amount=round(amount, 2),
        percentage=pct,
        overall=overall,
        performance=round(overall * performance_pct, 2),
        trivial=round(overall * trivial_pct, 2),
        performance_pct=performance_pct,
        trivial_pct=trivial_pct,
        rationale=rationale or spec["when"],
    )


def suggest_benchmark(
    profit_before_tax: float, revenue: float, total_assets: float, equity: float
) -> tuple[str, str]:
    """Suggest a benchmark. The auditor confirms it; the tool does not decide."""
    if revenue > 0 and abs(profit_before_tax) / revenue < 0.02:
        return "revenue", (
            "Profit before tax is under 2 per cent of revenue, so an earnings "
            "benchmark would be volatile."
        )
    if profit_before_tax <= 0:
        return "revenue", "The entity reported a loss, so profit is not a stable benchmark."
    if total_assets > 0 and revenue / total_assets < 0.25:
        return "total_assets", "Turnover is low relative to the asset base."
    return "profit_before_tax", "Profit-oriented entity with positive, representative earnings."


# --------------------------------------------------------------------------
# SA 530 - monetary unit sampling
# --------------------------------------------------------------------------

@dataclass
class SampleItem:
    index: int
    identifier: str
    description: str
    amount: float
    selection_point: float
    reason: str


@dataclass
class SamplePlan:
    population_size: int
    population_value: float
    tolerable_misstatement: float
    expected_misstatement: float
    confidence_factor: float
    sampling_interval: float
    random_start: float
    seed: int
    high_value_threshold: float
    items: list[SampleItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reference: str = "SA 530"

    @property
    def sample_size(self) -> int:
        return len(self.items)

    @property
    def is_efficient(self) -> bool:
        """Whether sampling is a sensible response for this population."""
        return not self.warnings

    @property
    def coverage(self) -> float:
        if self.population_value == 0:
            return 0.0
        return round(sum(i.amount for i in self.items) / self.population_value, 4)

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "#": n,
                    "Identifier": i.identifier,
                    "Description": i.description,
                    "Amount (Rs)": i.amount,
                    "Selected because": i.reason,
                }
                for n, i in enumerate(self.items, start=1)
            ]
        )


def monetary_unit_sample(
    population: pd.DataFrame,
    *,
    amount_column: str,
    id_column: str,
    description_column: str,
    tolerable_misstatement: float,
    expected_misstatement: float = 0.0,
    confidence_factor: float = 3.0,
    seed: int = 20250401,
) -> SamplePlan:
    """Select a monetary unit sample.

    Items at or above the sampling interval are individually significant
    and are selected in full; the remainder of the population is sampled
    systematically from a random start.  `confidence_factor` of 3.0
    corresponds to approximately 95 per cent confidence with no errors
    expected.
    """
    if tolerable_misstatement <= 0:
        raise ValueError("Tolerable misstatement must be greater than zero.")

    df = population.copy()
    df[amount_column] = pd.to_numeric(df[amount_column], errors="coerce").fillna(0.0).abs()
    df = df[df[amount_column] > 0].reset_index(drop=True)

    population_value = float(df[amount_column].sum())
    denominator = tolerable_misstatement - (expected_misstatement * confidence_factor)
    if denominator <= 0:
        raise ValueError(
            "Expected misstatement is too high relative to tolerable misstatement; "
            "sampling is not an appropriate response."
        )
    interval = denominator / confidence_factor

    rng = random.Random(seed)
    random_start = rng.uniform(0, interval)

    plan = SamplePlan(
        population_size=len(df),
        population_value=round(population_value, 2),
        tolerable_misstatement=tolerable_misstatement,
        expected_misstatement=expected_misstatement,
        confidence_factor=confidence_factor,
        sampling_interval=round(interval, 2),
        random_start=round(random_start, 2),
        seed=seed,
        high_value_threshold=round(interval, 2),
    )

    high_value = df[df[amount_column] >= interval]
    remainder = df[df[amount_column] < interval].reset_index(drop=True)

    for idx, row in high_value.iterrows():
        plan.items.append(
            SampleItem(
                index=int(idx),
                identifier=str(row[id_column]),
                description=str(row[description_column]),
                amount=round(float(row[amount_column]), 2),
                selection_point=float(row[amount_column]),
                reason=f"Individually significant - at or above the sampling interval of Rs {inr(interval)}",
            )
        )

    cumulative = 0.0
    next_point = random_start
    for idx, row in remainder.iterrows():
        amount = float(row[amount_column])
        cumulative += amount
        while next_point <= cumulative:
            plan.items.append(
                SampleItem(
                    index=int(idx),
                    identifier=str(row[id_column]),
                    description=str(row[description_column]),
                    amount=round(amount, 2),
                    selection_point=round(next_point, 2),
                    reason=f"Systematic selection at monetary unit Rs {inr(next_point)}",
                )
            )
            next_point += interval

    # A sample this large is arithmetically correct but professionally
    # useless: it means the population is very large relative to tolerable
    # misstatement.  Say so, rather than handing the auditor a work
    # programme that cannot be performed.
    if plan.population_size and plan.sample_size / plan.population_size > 0.25:
        plan.warnings.append(
            f"The computed sample of {plan.sample_size} items covers "
            f"{plan.sample_size / plan.population_size:.0%} of the population. "
            "Sampling is not an efficient response here. Consider testing "
            "controls and relying on them, applying substantive analytical "
            "procedures under SA 520, stratifying the population, or "
            "revisiting the materiality benchmark."
        )
    if plan.population_value and plan.population_value / tolerable_misstatement > 200:
        plan.warnings.append(
            f"The population of Rs {inr(plan.population_value, decimals=0)} is "
            f"{plan.population_value / tolerable_misstatement:.0f} times tolerable "
            "misstatement. Confirm that the whole population is the intended "
            "sampling frame rather than a stratum within it."
        )

    return plan
