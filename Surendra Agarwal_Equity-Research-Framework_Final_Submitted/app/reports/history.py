"""Report history - tracks every report generated in a session (or
restored via Save/Load Session), so the thesis and score can be
compared across successive runs rather than only ever having "the
latest one."

Each entry stores the FULL rendered markdown at generation time, not
just a summary - re-downloading a historical report never requires
recomputation, and a later code change to generator.py's formatting
cannot retroactively alter what an earlier entry actually said.

History is append-only within a session (never edited or removed) -
matching the audit-trail-style discipline used elsewhere in this
project: it is a record of what was actually generated and when, not a
mutable scratchpad.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.reports.generator import ReportContext


class ReportHistoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    company_name: str
    ticker: str
    overall_score: float | None = None
    recommendation: str | None = None
    report_markdown: str


def build_history_entry(ctx: ReportContext, report_markdown: str) -> ReportHistoryEntry:
    """Pure function: given the ReportContext used for one report
    generation and the markdown it produced, build the history entry to
    append. Never recomputes anything - pulls whatever was already on
    ctx at generation time."""
    return ReportHistoryEntry(
        company_name=ctx.company.name,
        ticker=ctx.company.ticker,
        overall_score=ctx.investment_score.overall_score if ctx.investment_score else None,
        recommendation=ctx.thesis.recommendation.value if ctx.thesis else None,
        report_markdown=report_markdown,
    )


def summarize_score_progression(history: list[ReportHistoryEntry]) -> list[dict]:
    """Pure function: history (any order) -> display rows in
    chronological order (oldest first), each with a 'Change' column
    showing the delta from the immediately preceding entry's score -
    None if either score is unavailable, never a fabricated 0."""
    ordered = sorted(history, key=lambda e: e.generated_at)
    rows: list[dict] = []
    prev_score: float | None = None
    for entry in ordered:
        change = None
        if entry.overall_score is not None and prev_score is not None:
            change = entry.overall_score - prev_score
        rows.append({
            "Generated": entry.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            "Score": f"{entry.overall_score:.1f}" if entry.overall_score is not None else "N/A",
            "Change": f"{change:+.1f}" if change is not None else "\u2014",
            "Recommendation": entry.recommendation.upper() if entry.recommendation else "N/A",
            "entry_id": entry.entry_id,
        })
        prev_score = entry.overall_score if entry.overall_score is not None else prev_score
    return rows
