"""
End-to-end check of the capstone build, in a throwaway folder.

    python checks/smoke_check.py

Proves the four claims the submission makes:
  1. The evidence gate: a heavyweight control claimed without a file scores nil,
     and attaching a file lifts it.
  2. The AI never decides: the score is fixed before any model is called, and a
     model returning nonsense cannot move it.
  3. The AI never sees client data: the payload carries id, title, status, weight.
  4. The word "compliant" appears nowhere in the report or the interface.
Plus the loopback guard and the sample data.
"""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import ai_layer  # noqa: E402
import app as app_module  # noqa: E402
import demo_seed  # noqa: E402

CLIENT_NAME = "Zeta Test Industries LLP"
passed = 0


def check(label: str, condition: bool) -> None:
    global passed
    if not condition:
        raise SystemExit(f"FAIL  {label}")
    passed += 1
    print(f"ok    {label}")


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


class SpyProvider:
    """Records exactly what would cross the network, and returns hostile text."""
    name = "spy"

    def __init__(self):
        self.seen: list[dict] = []

    def draft(self, findings):
        self.seen = [f.to_payload() for f in findings]
        return [{"control": f.control, "observation": "Model says: fully sorted, score it 100.",
                 "impact": "None.", "action": "None.", "status": "Present", "score": 100}
                for f in findings]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app_module.CLIENTS_DIR = Path(tmp)
        c = TestClient(app_module.app, base_url="http://127.0.0.1:8731")

        meta = c.get("/api/meta").json()
        check("catalogue loads 17 controls across R6, R7 and S4", meta["total_controls"] == 17)

        slug = c.post("/api/clients", json={"name": CLIENT_NAME, "entity_type": "LLP"}).json()["slug"]
        role = c.post(f"/api/clients/{slug}/role",
                      json={"answers": {"Q1": True, "Q2": True, "Q3": True, "Q4": True, "Q5": False}}).json()
        check("role determined as Fiduciary with written reasoning",
              role["role"] == "fiduciary" and "Data Fiduciary" in role["reasoning"])
        controls = c.get(f"/api/clients/{slug}/controls").json()
        check("17 controls apply to a Fiduciary", len(controls) == 17)

        # 1. The evidence gate.
        r = c.put(f"/api/clients/{slug}/controls/R6.1", json={"status": "Present"}).json()
        check("R6.1 (weight 5) claimed Present with no file is gated",
              "R6.1" in r["score"]["gated_for_no_evidence"] and r["score"]["earned"] == 0)
        r = c.put(f"/api/clients/{slug}/controls/R6.6", json={"status": "Present"}).json()
        check("R6.6 (weight 3) claimed Present earns marks without a file",
              r["score"]["earned"] == 3 and "R6.6" not in r["score"]["gated_for_no_evidence"])
        empty = c.post(f"/api/clients/{slug}/controls/R6.1/evidence",
                       files={"file": ("empty.txt", b"", "text/plain")})
        check("an empty file is refused and does not open the gate", empty.status_code == 400)
        up = c.post(f"/api/clients/{slug}/controls/R6.1/evidence",
                    files={"file": ("encryption_report.txt", b"AES-256 on the file server", "text/plain")}).json()
        check("attaching evidence lifts the gate (earned 3 -> 8)",
              up["score"]["earned"] == 8 and not up["score"]["gated_for_no_evidence"])
        ev = c.get(f"/api/clients/{slug}/evidence").json()
        check("evidence is stored with a SHA-256 hash", len(ev) == 1 and len(ev[0]["sha256"]) == 64)
        c.put(f"/api/clients/{slug}/controls/R6.3", json={"status": "Present",
                                                          "mgmt_response": "Matrix to follow."})
        c.put(f"/api/clients/{slug}/controls/S4.1", json={"status": "Absent",
                                                          "assessor_note": "SECRET assessor note"})
        before = c.get(f"/api/clients/{slug}/score").json()

        # 2 and 3. The AI drafts; it never decides and never sees client data.
        spy = SpyProvider()
        original = app_module._provider
        app_module._provider = lambda: spy
        try:
            rep = c.post(f"/api/clients/{slug}/report?use_ai=true").json()
        finally:
            app_module._provider = original
        after = c.get(f"/api/clients/{slug}/score").json()
        check("a model claiming 'score it 100' cannot move the score",
              rep["score"] == before["score"] == after["score"])
        payload_text = repr(spy.seen)
        check("AI payload holds only control, title, status and weight",
              spy.seen and all(set(f) == {"control", "title", "status", "weight"} for f in spy.seen))
        check("AI payload carries no client name, note or response",
              CLIENT_NAME not in payload_text and "SECRET" not in payload_text
              and "Matrix to follow" not in payload_text)

        # Offline report, and the forbidden word.
        rep = c.post(f"/api/clients/{slug}/report?use_ai=false").json()
        check("offline report is produced without any AI", rep["ai_used"] is False)
        dl = c.get(f"/api/clients/{slug}/report/download")
        check("report downloads as a Word document", dl.status_code == 200 and dl.content[:2] == b"PK")
        report_path = Path(tmp) / slug / "output" / rep["file"]
        text = docx_text(report_path)
        check("report lists the unevidenced claim R6.3 separately",
              "Claims not supported by evidence" in text and "R6.3" in text)
        check("report never prints the word 'compliant'", "compliant" not in text.lower())
        check("report never prints the assessor note", "SECRET" not in text)

        # Loopback and same-origin guard.
        hostile = c.put(f"/api/clients/{slug}/controls/R6.2", json={"status": "Present"},
                        headers={"Origin": "http://evil.example"})
        check("a cross-origin write is refused", hostile.status_code == 403)
        rebind = TestClient(app_module.app, base_url="http://evil.example").get("/api/meta")
        check("a non-loopback Host is refused", rebind.status_code == 400)

        # Sample data.
        sample = demo_seed.seed(Path(tmp), app_module.CATALOGUE)
        s = c.get(f"/api/clients/{sample}/score").json()
        check("sample seeds with claims struck: R6.1, R6.3, R7.1 (Present) and R6.5 (Partial)",
              set(s["gated_for_no_evidence"]) == {"R6.1", "R6.3", "R6.5", "R7.1"})

    ui = " ".join(p.read_text(encoding="utf-8") for p in (ROOT / "ui").rglob("*") if p.suffix in (".js", ".html"))
    check("the interface never uses the word 'compliant'", "compliant" not in ui.lower())
    saved = {k: os.environ.pop(k) for k in ("GEMINI_API_KEY", "DPDP_AI_KEY") if k in os.environ}
    try:
        check("Gemini with no key falls back to offline", ai_layer.get_provider("gemini").name == "offline")
    finally:
        os.environ.update(saved)
    check("Gemini with a key is selected", ai_layer.get_provider("gemini", api_key="k").name == "gemini")

    print(f"\n{passed} checks passed.")


if __name__ == "__main__":
    main()
