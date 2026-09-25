"""
Batch-runs Agent 1 (Onboarding) against every sample PAN/GST document in
examples/inputs/ and saves the extracted JSON to examples/outputs/agent1/.
Run: python src/run_agent1_on_samples.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents.onboarding import OnboardingAgent

INPUT_DIR = Path(__file__).resolve().parent.parent / "examples" / "inputs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "examples" / "outputs" / "agent1"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
# these are drafted-document / prompt fixtures for Agent 2/3, not onboarding docs
SKIP = {"sample_pan_scanned.pdf"}  # already covered by sample_pan_individual_01.png

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    agent = OnboardingAgent()
    id_doc_names = {
        "sample_pan_individual_01.png", "sample_pan_individual_02.png",
        "sample_gst_cert_company_01.png", "sample_gst_cert_proprietor_01.png",
        "sample_gst_cert_text_layer.pdf", "sample_pan_scanned.pdf",
    }
    for path in sorted(INPUT_DIR.iterdir()):
        if path.name not in id_doc_names:
            continue
        print(f"Processing {path.name} ...")
        result = agent.run(str(path))
        out_path = OUTPUT_DIR / (path.stem + ".json")
        out_path.write_text(json.dumps(result, indent=2))
        status = "OK" if result["valid"] else "ISSUES: " + str(result["issues"])
        print(f"  -> {out_path.name} [{status}]")
