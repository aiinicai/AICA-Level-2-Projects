"""Evaluate AuditSense against the labelled fictional findings.

Run from the project directory after configuring OPENAI_API_KEY:

    python evaluation/evaluate.py

The script writes results.json and summary.md in the evaluation directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.reviewer import ELEMENTS, review_finding  # noqa: E402


def expected_weaknesses(value: str) -> set[str]:
    """Convert the human label into the elements expected to be flagged."""
    if not value or value.strip().lower() in {"none", "nan"}:
        return set()
    return {item.strip() for item in value.split(";") if item.strip()}


def build_payload(row: pd.Series) -> dict[str, str]:
    return {
        "title": str(row["title"]),
        "process": str(row["process"]),
        "draft_observation": str(row["draft_observation"]),
        "evidence": str(row["evidence"]),
        "criteria": "",
    }


def evaluate_row(row: pd.Series) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row["id"]),
        "manual_status": str(row["manual_status"]),
        "expected_weaknesses": sorted(expected_weaknesses(str(row["missing_elements"]))),
        "expected_unsupported_claim": str(row["unsupported_claims"]) != "None stated.",
    }
    try:
        review = review_finding(build_payload(row))
        flagged = {
            element
            for element in ELEMENTS
            if review["element_analysis"][element]["status"] != "present"
        }
        result.update(
            {
                "error": "",
                "ai_status": review["overall_status"],
                "ai_flagged_weaknesses": sorted(flagged),
                "ai_unsupported_claim_count": len(review["unsupported_claims"]),
                "status_match": review["overall_status"] == row["manual_status"],
                "weaknesses_match": flagged == expected_weaknesses(str(row["missing_elements"])),
                "unsupported_claim_detected": bool(review["unsupported_claims"]),
                "review": review,
            }
        )
    except Exception as error:  # Continue the batch and record the failure.
        result.update(
            {
                "error": str(error),
                "ai_status": "",
                "ai_flagged_weaknesses": [],
                "ai_unsupported_claim_count": 0,
                "status_match": False,
                "weaknesses_match": False,
                "unsupported_claim_detected": False,
            }
        )
    return result


def write_summary(results: list[dict[str, Any]], output_dir: Path) -> None:
    completed = [item for item in results if not item["error"]]
    status_matches = sum(item["status_match"] for item in completed)
    weakness_matches = sum(item["weaknesses_match"] for item in completed)
    expected_claims = sum(item["expected_unsupported_claim"] for item in results)
    detected_claims = sum(
        item["unsupported_claim_detected"]
        for item in results
        if item["expected_unsupported_claim"]
    )

    summary = [
        "# AuditSense evaluation summary",
        "",
        "This evaluation uses only the fictional labelled dataset.",
        "",
        f"- Findings attempted: {len(results)}",
        f"- Findings completed: {len(completed)}",
        f"- API or processing errors: {len(results) - len(completed)}",
        f"- Exact overall-status matches: {status_matches}/{len(completed) or 1}",
        f"- Exact weakness-set matches: {weakness_matches}/{len(completed) or 1}",
        f"- Unsupported-claim detections: {detected_claims}/{expected_claims or 1}",
        "",
        "## Interpretation",
        "",
        "Exact matches are diagnostic metrics, not proof that the AI is correct.",
        "Every suggested finding still requires auditor verification and professional judgment.",
    ]
    (output_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only the first N findings.")
    args = parser.parse_args()

    data_path = PROJECT_DIR / "data" / "synthetic_findings.csv"
    output_dir = PROJECT_DIR / "evaluation"
    findings = pd.read_csv(data_path, keep_default_na=False)
    if args.limit > 0:
        findings = findings.head(args.limit)

    results = [evaluate_row(row) for _, row in findings.iterrows()]
    (output_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_summary(results, output_dir)
    print(f"Evaluated {len(results)} fictional findings.")
    print(f"Results: {output_dir / 'results.json'}")
    print(f"Summary: {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
