"""
Demonstrates Agent 2 (Drafting) and Agent 3 (Compliance) connected end to end:
a plain-English instruction goes into Agent 2, its drafted output goes straight
into Agent 3, with no manual editing in between. Saves the combined result for
each sample prompt to examples/outputs/pipeline/.

Run: python src/run_agent2_then_agent3.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents.compliance import ComplianceAgent
from agents.drafting import DraftingAgent

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "examples" / "outputs" / "pipeline"

SAMPLE_PROMPTS = [
    "Prepare an engagement letter for ABC Pvt Ltd for tax audit AY 2025-26, fees Rs 50,000",
    "Prepare a net worth certificate for Ravi Kumar Sharma as at 31/03/2026 for bank loan purposes",
    "Draft a professional fee note for Sharma Enterprises for GST return filing services, Rs 15,000 plus GST",
    "Draft a representation letter for ABC Pvt Ltd for the statutory audit for FY 2025-26",
]

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    drafting_agent = DraftingAgent()
    compliance_agent = ComplianceAgent()

    for i, prompt in enumerate(SAMPLE_PROMPTS, start=1):
        print(f"\n=== Prompt {i}: {prompt}")
        draft = drafting_agent.run(prompt)
        print(f"  Agent 2 -> {draft['doc_type']} for {draft['client_name']}")

        compliance = compliance_agent.run(draft["draft_text"], draft["doc_type"])
        print(f"  Agent 3 -> {compliance['overall']} | missing: {compliance['missing']}")

        combined = {"agent2": draft, "agent3": compliance}
        out_path = OUTPUT_DIR / f"prompt_{i:02d}.json"
        out_path.write_text(json.dumps(combined, indent=2))
