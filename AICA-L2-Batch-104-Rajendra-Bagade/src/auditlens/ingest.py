"""
Ingestion and validation of the trial balance and general ledger.

Nothing downstream runs until the trial balance actually balances -- an
unbalanced trial balance is a data problem, not an audit finding, and the
engine says so rather than producing financial statements that do not tie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

TB_REQUIRED_COLUMNS = ["account_code", "account_name", "debit", "credit"]
GL_REQUIRED_COLUMNS = [
    "entry_id",
    "posting_date",
    "account_code",
    "account_name",
    "debit",
    "credit",
    "narration",
    "posted_by",
]

# Column headers vary from client to client.  These are the aliases seen
# often enough to be worth handling without a manual mapping step.
TB_ALIASES: dict[str, str] = {
    "code": "account_code",
    "gl code": "account_code",
    "ledger code": "account_code",
    "account code": "account_code",
    "a/c code": "account_code",
    "ledger": "account_name",
    "ledger name": "account_name",
    "particulars": "account_name",
    "account": "account_name",
    "account name": "account_name",
    "description": "account_name",
    "dr": "debit",
    "debit amount": "debit",
    "debit (rs.)": "debit",
    "cr": "credit",
    "credit amount": "credit",
    "credit (rs.)": "credit",
}


class IngestError(ValueError):
    """Raised when a file cannot be used at all."""


def _normalise_headers(df: pd.DataFrame, aliases: dict[str, str]) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower()
        key = " ".join(key.split())
        if key in aliases:
            renamed[col] = aliases[key]
        else:
            renamed[col] = key.replace(" ", "_")
    return df.rename(columns=renamed)


def _read_any(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise IngestError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(path)
    raise IngestError(f"Unsupported file type: {suffix}. Provide CSV or Excel.")


def _to_amount(series: pd.Series) -> pd.Series:
    """Indian accounting exports carry commas, blanks, brackets and 'Dr'/'Cr'."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("Dr", "", regex=False)
        .str.replace("Cr", "", regex=False)
        .str.strip()
    )
    # (1,234) means negative in many exports.
    cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    cleaned = cleaned.replace({"": "0", "nan": "0", "None": "0", "-": "0"})
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


@dataclass
class TrialBalance:
    """A validated trial balance for one financial year."""

    financial_year: str
    df: pd.DataFrame
    total_debit: float = 0.0
    total_credit: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def difference(self) -> float:
        return round(self.total_debit - self.total_credit, 2)

    @property
    def balances(self) -> bool:
        # One rupee of tolerance absorbs rounding in the client's export.
        return abs(self.difference) <= 1.00

    def net_balance(self, account_code: str | int) -> float:
        """Debit-positive net balance of one ledger."""
        rows = self.df[self.df["account_code"].astype(str) == str(account_code)]
        return float(rows["debit"].sum() - rows["credit"].sum())


def load_trial_balance(path: str | Path, financial_year: str) -> TrialBalance:
    df = _normalise_headers(_read_any(path), TB_ALIASES)

    missing = [c for c in TB_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise IngestError(
            "Trial balance is missing required column(s): "
            + ", ".join(missing)
            + f". Found: {', '.join(map(str, df.columns))}"
        )

    warnings: list[str] = []

    df["account_code"] = df["account_code"].astype(str).str.strip()
    df["account_name"] = df["account_name"].astype(str).str.strip()
    df["debit"] = _to_amount(df["debit"])
    df["credit"] = _to_amount(df["credit"])

    blank = df["account_name"].isin(["", "nan", "None"])
    if blank.any():
        warnings.append(f"{int(blank.sum())} ledger(s) have no name and were dropped.")
        df = df[~blank]

    both = (df["debit"] != 0) & (df["credit"] != 0)
    if both.any():
        warnings.append(
            f"{int(both.sum())} ledger(s) carry both a debit and a credit balance; "
            "the net balance has been used."
        )

    dupes = df["account_code"].duplicated(keep=False)
    if dupes.any():
        warnings.append(
            f"{int(dupes.sum())} row(s) share an account code; balances were aggregated."
        )
        df = (
            df.groupby(["account_code", "account_name"], as_index=False)[["debit", "credit"]]
            .sum()
        )

    df = df.reset_index(drop=True)

    return TrialBalance(
        financial_year=financial_year,
        df=df,
        total_debit=round(float(df["debit"].sum()), 2),
        total_credit=round(float(df["credit"].sum()), 2),
        warnings=warnings,
    )


@dataclass
class GeneralLedger:
    """Journal entry population for the year, used for SA 240 testing."""

    financial_year: str
    df: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return int(self.df["entry_id"].nunique())

    @property
    def line_count(self) -> int:
        return len(self.df)

    def unbalanced_entries(self) -> pd.DataFrame:
        """Entries whose debits do not equal their credits."""
        totals = self.df.groupby("entry_id")[["debit", "credit"]].sum()
        diff = (totals["debit"] - totals["credit"]).abs()
        return totals[diff > 0.01].reset_index()


def load_general_ledger(path: str | Path, financial_year: str) -> GeneralLedger:
    df = _normalise_headers(_read_any(path), TB_ALIASES)

    missing = [c for c in GL_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise IngestError(
            "General ledger is missing required column(s): " + ", ".join(missing)
        )

    warnings: list[str] = []
    df["debit"] = _to_amount(df["debit"])
    df["credit"] = _to_amount(df["credit"])
    df["posting_date"] = pd.to_datetime(df["posting_date"], errors="coerce", dayfirst=True)

    undated = df["posting_date"].isna()
    if undated.any():
        warnings.append(f"{int(undated.sum())} line(s) have an unreadable posting date.")
        df = df[~undated]

    for col in ("account_name", "narration", "posted_by", "entry_id"):
        df[col] = df[col].astype(str).str.strip()
    df["account_code"] = df["account_code"].astype(str).str.strip()

    if "entry_date" in df.columns:
        df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce", dayfirst=True)

    return GeneralLedger(
        financial_year=financial_year,
        df=df.reset_index(drop=True),
        warnings=warnings,
    )
