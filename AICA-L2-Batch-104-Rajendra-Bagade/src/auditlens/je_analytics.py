"""
Journal entry testing.

SA 240, 'The Auditor's Responsibilities Relating to Fraud in an Audit of
Financial Statements', requires the auditor to test the appropriateness of
journal entries recorded in the general ledger, because management
override of controls is present in every entity.  These routines produce
the population of entries that warrant that testing.

Every test returns a reason and the amount involved.  A flag is not a
finding -- it is a selection for the auditor to examine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from .formatting import inr

# Benford's law - expected frequency of each leading digit.
BENFORD_EXPECTED: dict[int, float] = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


@dataclass
class Flag:
    entry_id: str
    test: str
    reason: str
    amount: float
    posting_date: date | None = None
    posted_by: str = ""
    severity: str = "review"     # "review" | "elevated"


@dataclass
class JETestResult:
    name: str
    reference: str
    description: str
    flags: list[Flag] = field(default_factory=list)
    population: int = 0

    @property
    def flagged(self) -> int:
        return len({f.entry_id for f in self.flags})

    @property
    def rate(self) -> float:
        return 0.0 if self.population == 0 else round(self.flagged / self.population, 4)


def _entry_totals(gl: pd.DataFrame) -> pd.DataFrame:
    """One row per journal entry, with its value and attributes."""
    grouped = gl.groupby("entry_id").agg(
        value=("debit", "sum"),
        posting_date=("posting_date", "min"),
        posted_by=("posted_by", "first"),
        narration=("narration", "first"),
        lines=("debit", "size"),
    )
    return grouped.reset_index()


def test_round_amounts(gl: pd.DataFrame, threshold: int = 100000) -> JETestResult:
    """Entries for suspiciously round sums, which rarely arise from a
    genuine underlying transaction."""
    entries = _entry_totals(gl)
    res = JETestResult(
        name="Round-sum entries",
        reference="SA 240 para 32(a)",
        description=f"Entries for an exact multiple of Rs {inr(threshold, decimals=0)}.",
        population=len(entries),
    )
    for row in entries.itertuples(index=False):
        if row.value >= threshold and row.value % threshold == 0:
            res.flags.append(
                Flag(
                    entry_id=row.entry_id,
                    test=res.name,
                    reason=f"Value is an exact multiple of Rs {inr(threshold, decimals=0)}",
                    amount=round(float(row.value), 2),
                    posting_date=row.posting_date.date() if pd.notna(row.posting_date) else None,
                    posted_by=row.posted_by,
                )
            )
    return res


def test_weekend_and_holiday(gl: pd.DataFrame, holidays: set[date] | None = None) -> JETestResult:
    """Entries posted on a non-working day."""
    holidays = holidays or set()
    entries = _entry_totals(gl)
    res = JETestResult(
        name="Non-working day postings",
        reference="SA 240 para A43",
        description="Entries posted on a Saturday, Sunday or declared holiday.",
        population=len(entries),
    )
    for row in entries.itertuples(index=False):
        if pd.isna(row.posting_date):
            continue
        d = row.posting_date.date()
        weekday = row.posting_date.weekday()
        if weekday >= 5 or d in holidays:
            label = "holiday" if d in holidays else row.posting_date.strftime("%A")
            res.flags.append(
                Flag(
                    entry_id=row.entry_id,
                    test=res.name,
                    reason=f"Posted on a {label}",
                    amount=round(float(row.value), 2),
                    posting_date=d,
                    posted_by=row.posted_by,
                )
            )
    return res


def test_period_end_concentration(
    gl: pd.DataFrame, year_end: date, window_days: int = 7, materiality: float = 0.0
) -> JETestResult:
    """Material entries posted in the closing days of the year, where the
    risk of management override is highest."""
    entries = _entry_totals(gl)
    cutoff = year_end - timedelta(days=window_days)
    res = JETestResult(
        name="Period-end material entries",
        reference="SA 240 para 32(a)(ii)",
        description=(
            f"Entries above performance materiality posted between "
            f"{cutoff:%d-%b-%Y} and {year_end:%d-%b-%Y}."
        ),
        population=len(entries),
    )
    for row in entries.itertuples(index=False):
        if pd.isna(row.posting_date):
            continue
        d = row.posting_date.date()
        if cutoff <= d <= year_end and float(row.value) >= materiality:
            res.flags.append(
                Flag(
                    entry_id=row.entry_id,
                    test=res.name,
                    reason=f"Material entry posted {(year_end - d).days} day(s) before year end",
                    amount=round(float(row.value), 2),
                    posting_date=d,
                    posted_by=row.posted_by,
                    severity="elevated",
                )
            )
    return res


def test_backdated_entries(gl: pd.DataFrame, tolerance_days: int = 30) -> JETestResult:
    """Entries recorded materially later than the date they are posted to.
    Requires an 'entry_date' column; skipped where the client's system
    does not capture it."""
    res = JETestResult(
        name="Back-dated entries",
        reference="SA 240 para 32(a)",
        description=f"Entries recorded more than {tolerance_days} days after their posting date.",
    )
    if "entry_date" not in gl.columns:
        res.description += " Not performed - the ledger export carries no entry timestamp."
        return res

    entries = gl.groupby("entry_id").agg(
        value=("debit", "sum"),
        posting_date=("posting_date", "min"),
        entry_date=("entry_date", "min"),
        posted_by=("posted_by", "first"),
    ).reset_index()
    res.population = len(entries)

    for row in entries.itertuples(index=False):
        if pd.isna(row.posting_date) or pd.isna(row.entry_date):
            continue
        lag = (row.entry_date - row.posting_date).days
        if lag > tolerance_days:
            res.flags.append(
                Flag(
                    entry_id=row.entry_id,
                    test=res.name,
                    reason=f"Recorded {lag} days after the posting date",
                    amount=round(float(row.value), 2),
                    posting_date=row.posting_date.date(),
                    posted_by=row.posted_by,
                    severity="elevated",
                )
            )
    return res


def test_seldom_used_combinations(gl: pd.DataFrame, max_occurrences: int = 2) -> JETestResult:
    """Debit/credit account pairings that appear only rarely in the year --
    the classic signature of an entry made outside the normal process."""
    pairs: dict[tuple[str, str], list[tuple[str, float, object, str]]] = {}
    for entry_id, lines in gl.groupby("entry_id"):
        debits = lines[lines["debit"] > 0]["account_name"].tolist()
        credits = lines[lines["credit"] > 0]["account_name"].tolist()
        value = float(lines["debit"].sum())
        posted_by = str(lines["posted_by"].iloc[0])
        posting_date = lines["posting_date"].min()
        for d in debits:
            for c in credits:
                pairs.setdefault((d, c), []).append((entry_id, value, posting_date, posted_by))

    res = JETestResult(
        name="Seldom-used account combinations",
        reference="SA 240 para 32(a)(ii)",
        description=f"Debit/credit pairings occurring {max_occurrences} time(s) or fewer in the year.",
        population=int(gl["entry_id"].nunique()),
    )
    seen: set[str] = set()
    for (dr, cr), occurrences in pairs.items():
        if len(occurrences) <= max_occurrences:
            for entry_id, value, posting_date, posted_by in occurrences:
                if entry_id in seen:
                    continue
                seen.add(entry_id)
                res.flags.append(
                    Flag(
                        entry_id=entry_id,
                        test=res.name,
                        reason=f"'{dr}' against '{cr}' occurs {len(occurrences)} time(s) in the year",
                        amount=round(value, 2),
                        posting_date=posting_date.date() if pd.notna(posting_date) else None,
                        posted_by=posted_by,
                    )
                )
    return res


def test_unusual_users(gl: pd.DataFrame, min_share: float = 0.02) -> JETestResult:
    """Entries posted by a user who posts almost nothing else -- often a
    senior user acting outside the normal process."""
    entries = _entry_totals(gl)
    res = JETestResult(
        name="Infrequent posting users",
        reference="SA 240 para A43",
        description=f"Entries by users accounting for less than {min_share:.0%} of the year's entries.",
        population=len(entries),
    )
    if entries.empty:
        return res
    share = entries["posted_by"].value_counts(normalize=True)
    rare = set(share[share < min_share].index)
    for row in entries.itertuples(index=False):
        if row.posted_by in rare:
            res.flags.append(
                Flag(
                    entry_id=row.entry_id,
                    test=res.name,
                    reason=f"'{row.posted_by}' posted {share[row.posted_by]:.1%} of entries this year",
                    amount=round(float(row.value), 2),
                    posting_date=row.posting_date.date() if pd.notna(row.posting_date) else None,
                    posted_by=row.posted_by,
                    severity="elevated",
                )
            )
    return res


@dataclass
class BenfordResult:
    """First-digit distribution of the entry population."""

    observed: dict[int, int] = field(default_factory=dict)
    expected: dict[int, float] = field(default_factory=dict)
    observed_pct: dict[int, float] = field(default_factory=dict)
    total: int = 0
    mad: float = 0.0            # mean absolute deviation
    conclusion: str = ""

    @property
    def conforms(self) -> bool:
        return self.mad < 0.012


def benford_first_digit(gl: pd.DataFrame, min_amount: float = 100.0) -> BenfordResult:
    """Benford first-digit test on journal entry values.

    Interpretation follows the conventional mean-absolute-deviation bands
    (Nigrini): below 0.006 close conformity, 0.006-0.012 acceptable,
    0.012-0.015 marginal, above 0.015 non-conformity.  A departure is a
    reason to look, not evidence of misstatement.
    """
    entries = _entry_totals(gl)
    values = entries.loc[entries["value"] >= min_amount, "value"]

    counts = {d: 0 for d in range(1, 10)}
    for v in values:
        digits = str(int(abs(v)))
        if digits and digits[0] != "0":
            counts[int(digits[0])] += 1

    total = sum(counts.values())
    res = BenfordResult(observed=counts, expected=dict(BENFORD_EXPECTED), total=total)
    if total == 0:
        res.conclusion = "Population too small for the test to be meaningful."
        return res

    res.observed_pct = {d: counts[d] / total for d in range(1, 10)}
    res.mad = round(
        sum(abs(res.observed_pct[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)) / 9, 5
    )
    if res.mad < 0.006:
        res.conclusion = "Close conformity to the expected distribution."
    elif res.mad < 0.012:
        res.conclusion = "Acceptable conformity."
    elif res.mad < 0.015:
        res.conclusion = "Marginally non-conforming; extend enquiry."
    else:
        res.conclusion = "Non-conforming; the entry population warrants focused testing."
    return res


@dataclass
class JEAnalysis:
    tests: list[JETestResult] = field(default_factory=list)
    benford: BenfordResult | None = None
    total_entries: int = 0

    @property
    def all_flags(self) -> list[Flag]:
        return [f for t in self.tests for f in t.flags]

    @property
    def flagged_entries(self) -> set[str]:
        return {f.entry_id for f in self.all_flags}

    def flags_frame(self) -> pd.DataFrame:
        rows = [
            {
                "Entry ID": f.entry_id,
                "Test": f.test,
                "Reason": f.reason,
                "Amount (Rs)": f.amount,
                "Posting date": f.posting_date,
                "Posted by": f.posted_by,
                "Severity": f.severity,
            }
            for f in self.all_flags
        ]
        return pd.DataFrame(rows)


def run_all_tests(
    gl: pd.DataFrame,
    year_end: date,
    performance_materiality: float,
    holidays: set[date] | None = None,
) -> JEAnalysis:
    analysis = JEAnalysis(total_entries=int(gl["entry_id"].nunique()))
    analysis.tests = [
        test_round_amounts(gl),
        test_weekend_and_holiday(gl, holidays),
        test_period_end_concentration(gl, year_end, materiality=performance_materiality),
        test_backdated_entries(gl),
        test_seldom_used_combinations(gl),
        test_unusual_users(gl),
    ]
    analysis.benford = benford_first_digit(gl)
    return analysis
