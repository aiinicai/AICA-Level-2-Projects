"""
Manual workflow helper — for use WITHOUT any live LLM API key.

Runs extraction + reconciliation (the deterministic parts, no API needed),
then prints a ready-to-paste prompt block so you can generate the narrative
manually via any chat LLM (Claude.ai, Gemini web, etc.) instead of calling
an API directly.

If you have a working Gemini API key configured in .env, you likely don't
need this — just run `python server.py` and use the real API via agent.py
instead. This script exists as a no-key fallback.

CHANGE: expected fees are now computed against actual Operating Revenue
from Revenue Support Schedule documents (not figures embedded in the
agreement). This script auto-discovers any files matching
"revenue_schedule_*" in the same directory as the agreement — no separate
argument needed for the common case of keeping them together in
sample_docs/. Use --revenue-schedules to point elsewhere explicitly.

Usage:
    python manual_export.py <agreement_path> <invoice_path_1> <invoice_path_2> ...
    python manual_export.py <agreement_path> --revenue-schedules <dir> -- <invoice_path_1> ...

Example:
    python manual_export.py ../sample_docs/agreement_management_services.pdf \\
        ../sample_docs/invoice_01_april_correct.pdf \\
        ../sample_docs/invoice_03_june_amount_mismatch.pdf \\
        ../sample_docs/invoice_04_july_party_mismatch.pdf \\
        ../sample_docs/invoice_05_august_currency_mismatch.pdf \\
        ../sample_docs/invoice_06_sept_scanned.png
"""

import sys
import os
import glob
import json
from extraction import process_document
from reconciliation import reconcile_all
from agent import SYSTEM_PROMPT, _findings_to_text


def _parse_args(argv):
    """Returns (agreement_path, revenue_schedule_dir_or_None, invoice_paths)."""
    if "--revenue-schedules" in argv:
        idx = argv.index("--revenue-schedules")
        agreement_path = argv[0]
        revenue_dir = argv[idx + 1]
        rest = argv[idx + 2:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        return agreement_path, revenue_dir, rest
    return argv[0], None, argv[1:]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    agreement_path, revenue_dir, invoice_paths = _parse_args(sys.argv[1:])

    if revenue_dir is None:
        revenue_dir = os.path.dirname(agreement_path) or "."
    revenue_schedule_paths = sorted(glob.glob(os.path.join(revenue_dir, "revenue_schedule_*")))

    print("Processing documents (extraction + reconciliation)...", file=sys.stderr)
    if revenue_schedule_paths:
        print(f"Found {len(revenue_schedule_paths)} revenue schedule(s) in {revenue_dir}", file=sys.stderr)
    else:
        print(f"WARNING: no revenue_schedule_* files found in {revenue_dir} — fee amounts will not "
              f"be independently verifiable; every invoice will get a 'No Reference Data' REVIEW finding.",
              file=sys.stderr)
    print(file=sys.stderr)

    agreement = process_document(agreement_path, "agreement")
    invoices = [process_document(p, "invoice") for p in invoice_paths]
    revenue_schedules = [process_document(p, "revenue_schedule") for p in revenue_schedule_paths]
    reconciliations = reconcile_all(agreement, invoices, revenue_schedules)

    status_counts = {}
    for r in reconciliations:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    findings_text = _findings_to_text(reconciliations)

    user_prompt = f"""Batch summary: {len(reconciliations)} invoices reviewed against one master
intercompany agreement.

Status breakdown: {json.dumps(status_counts)}

Detailed findings per invoice:
{findings_text}

Respond ONLY in JSON with keys: "executive_summary", "prioritized_items" (list of strings,
most urgent first — reference invoice filenames), "recommended_next_steps" (list of strings).
No preamble, no markdown fences.
"""

    print("=" * 78)
    print("STEP 1: Copy everything between the lines below into a NEW chat")
    print("        (Claude.ai, Gemini web, or any other chat LLM)")
    print("=" * 78)
    print()
    print("--- SYSTEM CONTEXT (paste first, as your own message) ---")
    print(SYSTEM_PROMPT)
    print()
    print("--- THEN PASTE THIS AS YOUR NEXT MESSAGE ---")
    print(user_prompt)
    print()
    print("=" * 78)
    print("STEP 2: Copy Claude's JSON response and save it as narrative.json")
    build_cmd = ["python manual_build_memo.py narrative.json", agreement_path]
    if revenue_schedule_paths:
        build_cmd += ["--revenue-schedules", revenue_dir, "--"]
    build_cmd += invoice_paths
    print("STEP 3: Run:", " ".join(build_cmd))
    print("=" * 78)


if __name__ == "__main__":
    main()
