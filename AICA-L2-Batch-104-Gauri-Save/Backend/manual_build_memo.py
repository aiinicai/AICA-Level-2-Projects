"""
Manual workflow helper, step 2 — builds the final Word memo using a narrative
you generated manually via Claude.ai (paste the JSON response into a file).

CHANGE: expected fees are computed against actual Operating Revenue from
Revenue Support Schedule documents. This script auto-discovers files
matching "revenue_schedule_*" in the same directory as the agreement,
matching manual_export.py's behaviour. Use --revenue-schedules to point
elsewhere explicitly.

Usage:
    python manual_build_memo.py <narrative.json> <agreement_path> <invoice_path_1> ...
    python manual_build_memo.py <narrative.json> <agreement_path> --revenue-schedules <dir> -- <invoice_path_1> ...
"""

import sys
import os
import glob
import json
from extraction import process_document
from reconciliation import reconcile_all
from memo_builder import build_batch_memo


def _parse_args(argv):
    """argv excludes narrative_path. Returns (agreement_path, revenue_schedule_dir_or_None, invoice_paths)."""
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
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    narrative_path = sys.argv[1]
    agreement_path, revenue_dir, invoice_paths = _parse_args(sys.argv[2:])

    if revenue_dir is None:
        revenue_dir = os.path.dirname(agreement_path) or "."
    revenue_schedule_paths = sorted(glob.glob(os.path.join(revenue_dir, "revenue_schedule_*")))

    with open(narrative_path, "r") as f:
        narrative = json.load(f)

    agreement = process_document(agreement_path, "agreement")
    invoices = [process_document(p, "invoice") for p in invoice_paths]
    revenue_schedules = [process_document(p, "revenue_schedule") for p in revenue_schedule_paths]
    reconciliations = reconcile_all(agreement, invoices, revenue_schedules)

    output_path = "../output/Invoice_Reconciliation_Manual.docx"
    build_batch_memo(agreement, reconciliations, narrative, output_path, revenue_schedules=revenue_schedules)
    print(f"Memo built successfully: {output_path}")
    if not revenue_schedule_paths:
        print(f"NOTE: no revenue_schedule_* files were found in {revenue_dir} — fee amounts could "
              f"not be independently verified for any invoice.")


if __name__ == "__main__":
    main()
