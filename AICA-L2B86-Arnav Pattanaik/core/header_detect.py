"""
Header row auto-detection for division-wise billing Excel exports.

Schema-free: this module has no knowledge of what column names "should"
exist. It only looks at the structural shape of the first two rows of a
sheet (row 1 or row 2) and picks whichever looks more like a header row
based on generic signals: non-blank cell density and text-vs-numeric
composition. Header rows are almost always mostly-text with several
non-blank cells; data rows below them are typically a mix including
numbers.
"""

from dataclasses import dataclass

CANDIDATE_ROWS_TO_CHECK = 2  # only ever consider row 1 or row 2, per spec
MIN_NONBLANK_CELLS = 2


@dataclass
class HeaderDetectionResult:
    header_row_index: int  # 0-based index into the raw rows
    confidence: str  # 'high' | 'medium' | 'low'
    reason: str
    candidate_headers: list[str]


def _looks_numeric(v) -> bool:
    if isinstance(v, (int, float)):
        return True
    s = str(v).strip().replace(",", "")
    try:
        float(s)
        return True
    except ValueError:
        return False


def _row_signal(row: list) -> tuple[int, float]:
    """Returns (non_blank_count, text_ratio) for a row."""
    non_blank = [v for v in row if v is not None and str(v).strip() != ""]
    if not non_blank:
        return 0, 0.0
    text_like = sum(1 for v in non_blank if not _looks_numeric(v))
    return len(non_blank), text_like / len(non_blank)


def detect_header_row(raw_rows: list[list]) -> HeaderDetectionResult:
    """
    Check only row 1 (index 0) and row 2 (index 1) of the sheet and decide
    which is more likely to be the header row. No column-name vocabulary is
    used — purely structural (cell density + text-vs-numeric composition).

    Row 1 is preferred by default (the common case). Row 2 is chosen instead
    only if row 1 looks weak (e.g. a title banner with a single non-blank
    cell, or mostly blank) AND row 2 looks like a stronger header candidate.
    """
    if not raw_rows:
        return HeaderDetectionResult(0, "low", "file is empty", [])

    scan_limit = min(CANDIDATE_ROWS_TO_CHECK, len(raw_rows))
    scores = []
    for idx in range(scan_limit):
        row = list(raw_rows[idx]) if raw_rows[idx] is not None else []
        count, text_ratio = _row_signal(row)
        score = 0.0
        if count >= MIN_NONBLANK_CELLS:
            score += count
        score += text_ratio * 5
        if count <= 1:
            score -= 10
        scores.append((idx, score, count, text_ratio))

    best_idx, best_score, best_count, best_text_ratio = max(scores, key=lambda t: t[1])

    if best_count >= MIN_NONBLANK_CELLS and best_text_ratio >= 0.6:
        confidence = "high"
    elif best_count >= MIN_NONBLANK_CELLS:
        confidence = "medium"
    else:
        confidence = "low"

    candidate_headers = [
        str(v).strip() if v is not None else "" for v in raw_rows[best_idx]
    ] if best_idx < len(raw_rows) else []

    reason = f"row {best_idx + 1}: {best_count} non-blank cell(s), {best_text_ratio:.0%} text-like"
    return HeaderDetectionResult(
        header_row_index=best_idx, confidence=confidence, reason=reason,
        candidate_headers=candidate_headers,
    )
