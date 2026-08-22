"""Pacing and duration-estimate helpers for batch LLM calls over many
document pages.

A real user hit a multi-minute retry storm (visible as many
"Retrying request to /chat/completions" lines from the OpenAI SDK's
own built-in backoff) when running extraction across a genuine 194-page
annual report. That storm wasn't a crash - the SDK's automatic retries
did eventually succeed - but it was slow, unpredictable, and gave no
visibility into what was happening or how long it would take.

This module adds a small, deliberate, PROACTIVE delay between
sequential calls (reducing how often a real account's rate limit gets
hit in the first place, trading an unpredictable retry-driven delay for
a smaller, predictable one) plus a rough upfront duration estimate so
callers can warn the user before a long-running batch starts, rather
than after.
"""

from __future__ import annotations

DEFAULT_REQUEST_DELAY_SECONDS = 0.5

_ASSUMED_CALL_LATENCY_SECONDS = 2.0
_WORST_CASE_MULTIPLIER = 2.5


def estimate_batch_duration_seconds(num_pages: int, delay_seconds: float) -> tuple[float, float]:
    """Return a ROUGH (min_seconds, max_seconds) estimate for processing
    num_pages sequentially with delay_seconds of pacing between each
    call. This cannot know the caller's actual OpenAI account tier,
    network latency, or how many pages will need a retry - it is an
    order-of-magnitude estimate for setting expectations, not a
    guarantee. Returns (0.0, 0.0) for num_pages <= 0.
    """
    if num_pages <= 0:
        return (0.0, 0.0)
    per_page = _ASSUMED_CALL_LATENCY_SECONDS + delay_seconds
    min_seconds = num_pages * per_page
    max_seconds = min_seconds * _WORST_CASE_MULTIPLIER
    return (min_seconds, max_seconds)


def format_duration_estimate(min_seconds: float, max_seconds: float) -> str:
    """Pure function: format a (min, max) second estimate as a human
    string, e.g. '2.6-6.5 minutes' or 'under a minute'."""
    if max_seconds < 60:
        return "under a minute"
    min_minutes = min_seconds / 60.0
    max_minutes = max_seconds / 60.0
    return f"{min_minutes:.1f}-{max_minutes:.1f} minutes"
