"""Materiality under SA 320 and sampling under SA 530."""

from __future__ import annotations

import pandas as pd
import pytest

from auditlens.materiality import (
    BENCHMARKS,
    compute_materiality,
    monetary_unit_sample,
    suggest_benchmark,
)


# --------------------------------------------------------------------------
# SA 320
# --------------------------------------------------------------------------

def test_materiality_arithmetic():
    m = compute_materiality(
        benchmark="profit_before_tax", benchmark_amount=1_00_00_000, percentage=0.05
    )
    assert m.overall == 5_00_000
    assert m.performance == 3_75_000      # 75 per cent of overall
    assert m.trivial == 25_000            # 5 per cent of overall


def test_performance_materiality_percentage_is_configurable():
    m = compute_materiality(
        benchmark="revenue", benchmark_amount=10_00_00_000,
        percentage=0.01, performance_pct=0.50,
    )
    assert m.overall == 10_00_000
    assert m.performance == 5_00_000


def test_negative_benchmark_is_taken_in_absolute_terms():
    m = compute_materiality(
        benchmark="profit_before_tax", benchmark_amount=-80_00_000, percentage=0.05
    )
    assert m.benchmark_amount == 80_00_000
    assert m.overall == 4_00_000


def test_rate_outside_the_customary_range_demands_justification():
    m = compute_materiality(
        benchmark="profit_before_tax", benchmark_amount=1_00_00_000, percentage=0.20
    )
    assert "outside the customary" in m.rationale
    assert "documented justification" in m.rationale


def test_rate_inside_the_range_carries_no_such_warning():
    m = compute_materiality(
        benchmark="profit_before_tax", benchmark_amount=1_00_00_000, percentage=0.07
    )
    assert "outside the customary" not in m.rationale


def test_unknown_benchmark_is_rejected():
    with pytest.raises(ValueError, match="Unknown benchmark"):
        compute_materiality(benchmark="ebitda", benchmark_amount=1_00_00_000)


def test_default_rate_is_the_typical_one_for_the_benchmark():
    for key, spec in BENCHMARKS.items():
        m = compute_materiality(benchmark=key, benchmark_amount=1_00_00_000)
        assert m.percentage == spec["typical"]
        assert spec["low"] <= m.percentage <= spec["high"]


def test_benchmark_suggestion_avoids_a_marginal_profit():
    benchmark, why = suggest_benchmark(
        profit_before_tax=8_00_000, revenue=10_00_00_000,
        total_assets=6_00_00_000, equity=3_00_00_000,
    )
    assert benchmark == "revenue"
    assert "2 per cent" in why


def test_benchmark_suggestion_avoids_a_loss():
    benchmark, why = suggest_benchmark(
        profit_before_tax=-50_00_000, revenue=10_00_00_000,
        total_assets=6_00_00_000, equity=3_00_00_000,
    )
    assert benchmark == "revenue"
    assert "loss" in why


def test_benchmark_suggestion_prefers_assets_for_an_asset_heavy_entity():
    benchmark, _ = suggest_benchmark(
        profit_before_tax=2_00_00_000, revenue=5_00_00_000,
        total_assets=100_00_00_000, equity=60_00_00_000,
    )
    assert benchmark == "total_assets"


def test_benchmark_suggestion_uses_profit_for_a_normal_trading_entity():
    benchmark, _ = suggest_benchmark(
        profit_before_tax=1_50_00_000, revenue=10_00_00_000,
        total_assets=8_00_00_000, equity=5_00_00_000,
    )
    assert benchmark == "profit_before_tax"


# --------------------------------------------------------------------------
# SA 530
# --------------------------------------------------------------------------

@pytest.fixture
def population() -> pd.DataFrame:
    return pd.DataFrame(
        [{"id": f"INV{i:04d}", "desc": f"Invoice {i}", "amount": 10_000 + i * 137}
         for i in range(500)]
    )


def test_sampling_interval_and_size(population):
    plan = monetary_unit_sample(
        population, amount_column="amount", id_column="id",
        description_column="desc", tolerable_misstatement=30_00_000,
    )
    # interval = tolerable / confidence factor
    assert plan.sampling_interval == pytest.approx(10_00_000, abs=1)
    expected = plan.population_value / plan.sampling_interval
    assert abs(plan.sample_size - expected) <= 2


def test_selection_is_reproducible(population):
    kwargs = dict(
        amount_column="amount", id_column="id", description_column="desc",
        tolerable_misstatement=30_00_000, seed=12345,
    )
    a = monetary_unit_sample(population, **kwargs)
    b = monetary_unit_sample(population, **kwargs)
    assert [i.identifier for i in a.items] == [i.identifier for i in b.items]
    assert a.random_start == b.random_start


def test_a_different_seed_gives_a_different_selection(population):
    kwargs = dict(
        amount_column="amount", id_column="id", description_column="desc",
        tolerable_misstatement=30_00_000,
    )
    a = monetary_unit_sample(population, seed=1, **kwargs)
    b = monetary_unit_sample(population, seed=2, **kwargs)
    assert [i.identifier for i in a.items] != [i.identifier for i in b.items]


def test_items_above_the_interval_are_always_selected():
    pop = pd.DataFrame([
        {"id": "BIG", "desc": "Individually significant", "amount": 50_00_000},
        {"id": "S1", "desc": "Small", "amount": 5_000},
        {"id": "S2", "desc": "Small", "amount": 5_000},
    ])
    plan = monetary_unit_sample(
        pop, amount_column="amount", id_column="id", description_column="desc",
        tolerable_misstatement=30_00_000,
    )
    selected = {i.identifier for i in plan.items}
    assert "BIG" in selected
    assert any("Individually significant" in i.reason for i in plan.items)


def test_zero_tolerable_misstatement_is_rejected(population):
    with pytest.raises(ValueError, match="greater than zero"):
        monetary_unit_sample(
            population, amount_column="amount", id_column="id",
            description_column="desc", tolerable_misstatement=0,
        )


def test_excessive_expected_misstatement_is_rejected(population):
    with pytest.raises(ValueError, match="not an appropriate response"):
        monetary_unit_sample(
            population, amount_column="amount", id_column="id",
            description_column="desc",
            tolerable_misstatement=10_00_000, expected_misstatement=5_00_000,
        )


def test_an_impractical_sample_is_called_out(population):
    """A sample covering most of the population is arithmetically right and
    professionally useless; the engine must say so."""
    plan = monetary_unit_sample(
        population, amount_column="amount", id_column="id",
        description_column="desc", tolerable_misstatement=50_000,
    )
    assert not plan.is_efficient
    assert any("not an efficient response" in w for w in plan.warnings)


def test_a_proportionate_sample_carries_no_warning(population):
    plan = monetary_unit_sample(
        population, amount_column="amount", id_column="id",
        description_column="desc", tolerable_misstatement=1_50_00_000,
    )
    assert plan.is_efficient
    assert plan.sample_size < len(population) * 0.25


def test_zero_and_negative_amounts_are_excluded():
    pop = pd.DataFrame([
        {"id": "A", "desc": "Live", "amount": 5_00_000},
        {"id": "B", "desc": "Nil", "amount": 0},
        {"id": "C", "desc": "Credit note", "amount": -2_00_000},
    ])
    plan = monetary_unit_sample(
        pop, amount_column="amount", id_column="id", description_column="desc",
        tolerable_misstatement=30_00_000,
    )
    assert plan.population_size == 2          # the nil item is dropped
    assert plan.population_value == 7_00_000  # the credit note counts at its absolute value


def test_engagement_sample_records_its_parameters(engagement):
    plan = engagement.sample
    assert plan.seed == 20250401
    assert plan.sampling_interval > 0
    assert plan.tolerable_misstatement == engagement.materiality.performance
    frame = plan.as_frame()
    assert set(frame.columns) == {"#", "Identifier", "Description", "Amount (Rs)", "Selected because"}
