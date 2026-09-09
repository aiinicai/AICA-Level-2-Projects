"""
Run the Task Checker pipeline against a LOCAL task folder (no OneDrive, no UI).

The folder must look like:
    <task_folder>/
        Inputs/      one or more input files
        Outputs/     the actual output(s) to be checked
        Workflow.txt the workflow / instructions

Usage:
    python run_local.py "C:/path/to/task_folder"
    python run_local.py "C:/path/to/task_folder" --desc "Reconcile the output against the inputs"

Needs a real key in your .env so the AI step can run:
    OPENAI_API_KEY=...        (for gpt-* models)   OR
    OPENROUTER_API_KEY=...    (for vendor/model names, e.g. openai/gpt-4o)
The model is chosen by AI_VALIDATION_MODEL / AI_TOOL_LOOP_MODEL in .env.
"""

import argparse
import io
import json
import os
import sys

# Match app_standalone.py: allow emoji logging on a legacy Windows console.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from services.file_source import LocalDirSource  # noqa: E402
from services.section_pipeline import SectionPipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_folder", help="Path to the local task folder")
    ap.add_argument("--desc", default="", help="What to check / task description")
    ap.add_argument("--json", action="store_true", help="Print the full result as JSON")
    ap.add_argument("--brief", action="store_true", help="Also print the terse per-criterion list")
    args = ap.parse_args()

    folder = os.path.abspath(args.task_folder)
    if not os.path.isdir(folder):
        print(f"Not a folder: {folder}")
        return 1

    pipeline = SectionPipeline(
        user_id="local", agent_id="local", file_source=LocalDirSource(folder)
    )
    result = pipeline.run(task_folder="/", task_description=args.desc)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0

    from services.report import render_report
    print(render_report(result))
    if not args.brief:
        return 0

    gv = result.get("generic_validation") or {}
    summary = gv.get("summary", {})
    print(f"\nmode={result.get('mode')}  specialization={result.get('specialization')}")
    print(f"overall: {summary.get('overall_status', '?')}")
    cost = (result.get("generic") or {}).get("cost") or result.get("cost") or {}
    if cost:
        print(f"cost: ${cost.get('total_usd', 0):.4f}  "
              f"({cost.get('total_in_tokens', 0)} in / {cost.get('total_out_tokens', 0)} out)")

    print("\nper-criterion:")
    for r in gv.get("criteria_results", []):
        line = f"  [{r.get('status'):<7}] {r.get('id')}: {r.get('statement', '')}"
        meta = r.get("decided_by") or r.get("verified_by")
        if meta:
            line += f"   ({meta})"
        print(line)
        ev = r.get("evidence")
        if ev and r.get("status") != "PASS":
            print(f"            evidence: {ev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
