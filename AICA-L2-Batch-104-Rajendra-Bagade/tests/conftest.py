from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from auditlens.ingest import load_general_ledger, load_trial_balance  # noqa: E402
from auditlens.pipeline import EngagementInputs, run_engagement       # noqa: E402

SAMPLES = ROOT / "samples"
TB_CURRENT = SAMPLES / "trial_balance_FY2024-25.csv"
TB_PRIOR = SAMPLES / "trial_balance_FY2023-24.csv"
GL_CURRENT = SAMPLES / "general_ledger_FY2024-25.csv"

HOLIDAYS = {date(2024, 8, 15), date(2024, 10, 2), date(2025, 1, 26)}


@pytest.fixture(scope="session")
def tb():
    return load_trial_balance(TB_CURRENT, "2024-25")


@pytest.fixture(scope="session")
def tb_prior():
    return load_trial_balance(TB_PRIOR, "2023-24")


@pytest.fixture(scope="session")
def gl():
    return load_general_ledger(GL_CURRENT, "2024-25")


@pytest.fixture(scope="session")
def engagement():
    inputs = EngagementInputs(
        client_name="Bharat Precision Components Private Limited",
        financial_year="2024-25",
        year_end=date(2025, 3, 31),
        principal_repayments=75_00_000,
        credit_sales_ratio=0.92,
        credit_purchase_ratio=0.95,
        working_capital_limit=6_00_00_000,
        holidays=HOLIDAYS,
    )
    return run_engagement(
        inputs=inputs,
        trial_balance_path=TB_CURRENT,
        prior_trial_balance_path=TB_PRIOR,
        general_ledger_path=GL_CURRENT,
    )
