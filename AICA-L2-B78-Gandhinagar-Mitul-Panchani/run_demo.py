"""Command-line harness for the nine AI memory governance scenarios."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from amg.audit import verify_chain  # noqa: E402
from amg.config import get_settings  # noqa: E402
from amg.db import reset_db  # noqa: E402
from amg.demo.persona import SCENARIO_2, SCENARIO_2B, SESSION_1  # noqa: E402
from amg.demo.scenarios import run_all, seed_session_one  # noqa: E402
from amg.models import ChainVerification, EntailmentVerdict, ScenarioResult  # noqa: E402
from amg.providers import (  # noqa: E402
    get_llm_provider,
    last_provider_report,
    reset_provider_state,
)
from amg.providers.budget import budget_report  # noqa: E402
from amg.providers.cache import cache_entry_count, cache_write_count  # noqa: E402


PREWARM_EXPECTED_CALLS = 29
CONFIDENCE_CALL_ALLOWANCE = 4


def _db_path() -> Path:
    configured = Path(get_settings().db_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def _reset_runtime_settings() -> None:
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)


def _provider_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    before_providers = before.get("providers", {})
    after_providers = after.get("providers", {})
    if not isinstance(before_providers, dict) or not isinstance(after_providers, dict):
        return result
    for provider, totals in after_providers.items():
        if not isinstance(totals, dict):
            continue
        old = before_providers.get(provider, {})
        old_models = old.get("models", {}) if isinstance(old, dict) else {}
        models: dict[str, Any] = {}
        new_models = totals.get("models", {})
        if isinstance(new_models, dict):
            for model, model_totals in new_models.items():
                if not isinstance(model_totals, dict):
                    continue
                old_model = old_models.get(model, {}) if isinstance(old_models, dict) else {}
                calls = int(model_totals.get("calls", 0)) - int(old_model.get("calls", 0))
                tokens = int(model_totals.get("tokens", 0)) - int(old_model.get("tokens", 0))
                if calls or tokens:
                    models[str(model)] = {"calls": calls, "tokens": tokens}
        calls = sum(int(item["calls"]) for item in models.values())
        tokens = sum(int(item["tokens"]) for item in models.values())
        if calls or tokens:
            result[str(provider)] = {"calls": calls, "tokens": tokens, "models": models}
    return result


def _validate_live_mode(*, require_voyage: bool) -> tuple[bool, str]:
    settings = get_settings()
    missing: list[str] = []
    if settings.offline:
        missing.append("AMG_OFFLINE must be 0")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY is missing")
    if require_voyage and not settings.voyage_api_key:
        missing.append("VOYAGE_API_KEY is missing")
    if missing:
        return False, "; ".join(missing)
    return True, "live-mode prerequisites are present"


def _print_budget(label: str, report: dict[str, Any]) -> None:
    print(
        f"{label}: {report['calls_used']}/{report['cap']} calls used "
        f"({report['remaining']} remaining, UTC {report['date']})"
    )


def _run_prewarm() -> int:
    valid, reason = _validate_live_mode(require_voyage=True)
    if not valid:
        print(f"Prewarm refused before any provider call: {reason}", file=sys.stderr)
        return 2
    before = budget_report()
    remaining = int(before["remaining"])
    if PREWARM_EXPECTED_CALLS > remaining:
        print(
            "Prewarm refused before any provider call: "
            f"needs {PREWARM_EXPECTED_CALLS} calls but only {remaining} remain under "
            "AMG_DAILY_LIVE_CALL_CAP.",
            file=sys.stderr,
        )
        return 2

    os.environ["AMG_CACHE_MODE"] = "refresh"
    _reset_runtime_settings()
    print(f"Prewarm call plan: {PREWARM_EXPECTED_CALLS} live calls.")
    _print_budget("Budget before", before)
    writes_before = cache_write_count()
    conn = reset_db(_db_path())
    try:
        results = run_all(conn)
        chain = verify_chain(conn)
    finally:
        conn.close()
    after = budget_report()
    calls = int(after["calls_used"]) - int(before["calls_used"])
    writes = cache_write_count() - writes_before
    print(f"Live calls made: {calls}")
    print("Per provider/model:")
    print(json.dumps(_provider_delta(before, after), indent=2, sort_keys=True))
    print(f"Cache entries written: {writes} ({cache_entry_count()} total on disk)")
    _print_budget("Budget after", after)
    all_passed = all(result.passed for result in results)
    cache_complete = writes == PREWARM_EXPECTED_CALLS
    print(
        f"Scenario result: {'PASS' if all_passed else 'FAIL'}; "
        f"chain valid: {chain.valid}; cache complete: {cache_complete}"
    )
    if not cache_complete:
        print(
            "Prewarm incomplete: one or more expected operations did not produce a genuine live cache write.",
            file=sys.stderr,
        )
    return 0 if all_passed and chain.valid and cache_complete else 1


def _run_confidence_recording() -> int:
    valid, reason = _validate_live_mode(require_voyage=False)
    if not valid:
        print(f"Confidence recording refused before any provider call: {reason}", file=sys.stderr)
        return 2
    before = budget_report()
    remaining = int(before["remaining"])
    if CONFIDENCE_CALL_ALLOWANCE > remaining:
        print(
            "Confidence recording refused before any provider call: "
            f"reserves up to {CONFIDENCE_CALL_ALLOWANCE} calls but only {remaining} remain.",
            file=sys.stderr,
        )
        return 2
    os.environ["AMG_CACHE_MODE"] = "refresh"
    _reset_runtime_settings()
    llm = get_llm_provider()
    existing = str(SESSION_1["inputs"][0])
    observations: list[tuple[str, EntailmentVerdict]] = []
    for label, definition in (("2", SCENARIO_2), ("2b", SCENARIO_2B)):
        verdict = llm.check_entailment(str(definition["inputs"][0]), existing)
        report = last_provider_report().get("entailment", {})
        if report.get("provider_name") != "gemini" or report.get("served_by") != "live":
            print(
                f"Scenario {label} was not served live by Gemini ({report}); result not recorded.",
                file=sys.stderr,
            )
            return 1
        observations.append((label, verdict))

    threshold = get_settings().contradiction_min_confidence
    positive = observations[0][1]
    additive = observations[1][1]
    separates = (
        positive.contradicts
        and positive.confidence >= threshold
        and not (additive.contradicts and additive.confidence >= threshold)
    )
    for label, verdict in observations:
        print(
            f"Scenario {label}: contradicts={verdict.contradicts}, "
            f"confidence={verdict.confidence:.3f}"
        )
    print(f"Configured threshold {threshold:.3f} separates the pair: {separates}")
    if positive.contradicts and not additive.contradicts:
        recommended = min(threshold, positive.confidence)
        print(
            f"Recommended threshold: {recommended:.2f} "
            "(the boolean separates 2b; retain a recall-oriented margin below Scenario 2)."
        )
    elif positive.contradicts and positive.confidence > additive.confidence:
        recommended = (positive.confidence + additive.confidence) / 2
        print(f"Recommended threshold: {recommended:.2f} (midpoint of observed confidences).")
    else:
        print("Recommended threshold: none; the live pair is not separable by this threshold rule.")
    after = budget_report()
    _print_budget("Budget before", before)
    _print_budget("Budget after", after)
    return 0 if separates else 1


def _print_human(
    results: list[ScenarioResult], chain: ChainVerification
) -> None:
    for result in results:
        print(f"\n=== Scenario {result.id}: {result.title} ===")
        print(result.what_it_proves)
        for step in result.steps:
            print(f"  {step}")
        for item in result.evidence:
            print(
                f"  - {item['assertion']}: expected={item['expected']!r}, "
                f"actual={item['actual']!r}"
            )
        print(f"  {'PASS' if result.passed else 'FAIL'} ({result.audit_rows_written} audit rows)")
    print("\n=== Summary ===")
    print(f"{'Scenario':<10} {'Result':<7} Proves")
    print(f"{'-' * 10} {'-' * 7} {'-' * 60}")
    for result in results:
        print(f"{result.id:<10} {('PASS' if result.passed else 'FAIL'):<7} {result.what_it_proves}")
    print(f"\nFinal verify_chain(): {chain.valid} ({chain.rows_checked} rows; {chain.reason})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-db", action="store_true", help="leave the SQLite demo DB on disk")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON only")
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument("--prewarm-cache", action="store_true", help="populate cache using live providers")
    exclusive.add_argument("--record-confidence", action="store_true", help="record live Scenario 2/2b entailment values")
    args = parser.parse_args()

    if args.prewarm_cache:
        return _run_prewarm()
    if args.record_confidence:
        return _run_confidence_recording()

    path = _db_path()
    conn = reset_db(path)
    try:
        seed_session_one(conn)
        results = run_all(conn)
        chain = verify_chain(conn)
    finally:
        conn.close()
    if args.json:
        print(
            json.dumps(
                {
                    "results": [result.model_dump(mode="json") for result in results],
                    "verify_chain": chain.model_dump(mode="json"),
                    "all_passed": all(result.passed for result in results) and chain.valid,
                },
                indent=2,
            )
        )
    else:
        _print_human(results, chain)
    if not args.keep_db:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return 0 if all(result.passed for result in results) and chain.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
