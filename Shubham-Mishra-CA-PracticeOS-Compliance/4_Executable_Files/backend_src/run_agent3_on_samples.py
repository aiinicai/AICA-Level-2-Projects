"""
Batch-runs Agent 3 (Compliance) against every sample drafted document in
examples/inputs/ and saves the reports to examples/outputs/agent3/.
See examples/inputs/compliance_test_expectations.md for expected results.
Run: python src/run_agent3_on_samples.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents.compliance import ComplianceAgent

INPUT_DIR = Path(__file__).resolve().parent.parent / "examples" / "inputs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "examples" / "outputs" / "agent3"

SAMPLES = [
    "sample_engagement_letter_complete.txt",
    "sample_engagement_letter_missing_fees.txt",
    "sample_engagement_letter_missing_scope_and_responsibilities.txt",
    "sample_net_worth_certificate_missing_udin.txt",
]

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    agent = ComplianceAgent()
    for name in SAMPLES:
        path = INPUT_DIR / name
        print(f"Checking {name} ...")
        text = path.read_text(encoding="utf-8")
        result = agent.run(text)
        out_path = OUTPUT_DIR / (path.stem + ".json")
        out_path.write_text(json.dumps(result, indent=2))
        print(f"  -> {result['overall']} | missing: {result['missing']} | needs_review: {result['needs_review']}")
