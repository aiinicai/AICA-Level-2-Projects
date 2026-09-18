"""Panel (jury + adversarial critic) aggregation logic."""

import json

import pytest

import services.generic_validator as gv
from models.check_spec import CheckSpec
from services.jury import ADVERSARIAL_PROMPT, PanelValidator


def _nd():
    # data contains id "1" and amount "100" so grounded citations survive
    tbl = {"name": "S", "headers": ["id", "amount"], "rows": [["1", 100]]}
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET", "tables": [tbl]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET", "tables": [tbl]}],
    }


def _spec(sev="error"):
    return CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Values are correct", "type": "semantic", "severity": sev}]})


@pytest.fixture
def panel_stub(monkeypatch):
    """Patch GenericValidator._complete so jurors (by temperature) and the critic
    (by system prompt) return controllable, grounded verdicts."""
    state = {"juror_by_temp": {}, "critic": ("PASS", "id 1 amount 100 ok")}

    def fake(self, prompt):
        if self.system_prompt == ADVERSARIAL_PROMPT:
            status, ev = state["critic"]
        else:
            status, ev = state["juror_by_temp"].get(self.temperature, ("PASS", "id 1 amount 100 ok"))
        return json.dumps({"criteria_results": [{"id": "C", "status": status, "evidence": ev, "explanation": ev}]})

    monkeypatch.setattr(gv.GenericValidator, "_complete", fake)
    return state


def _run(state, jurors, critic, threshold=0.67, sev="error"):
    # jurors: list of statuses mapped onto temperatures [0.0, 0.4, 0.8]
    temps = [0.0, 0.4, 0.8]
    state["juror_by_temp"] = {temps[i]: (jurors[i], "id 1 amount 100") for i in range(len(jurors))}
    state["critic"] = (critic, "id 1 amount 100 violates policy")
    p = PanelValidator(api_key="x", jury_size=len(jurors), critic_enabled=True, confidence_threshold=threshold)
    res = p.validate(_spec(sev), _nd(), deterministic_results={})
    return {r["id"]: r for r in res["criteria_results"]}, res["summary"]


def test_unanimous_pass(panel_stub):
    rows, summary = _run(panel_stub, ["PASS", "PASS", "PASS"], "PASS")
    assert rows["C"]["status"] == "PASS"
    assert rows["C"]["confidence"] == 1.0


def test_corroborated_fail(panel_stub):
    # one juror + the critic both flag a grounded defect -> FAIL (>=2 corroboration)
    rows, summary = _run(panel_stub, ["FAIL", "PASS", "PASS"], "FAIL")
    assert rows["C"]["status"] == "FAIL"
    assert rows["C"]["votes"]["FAIL"] == 2


def test_lone_critic_dissent_is_unclear(panel_stub):
    # only the critic flags a defect; jurors all PASS -> UNCLEAR, not a false positive
    rows, summary = _run(panel_stub, ["PASS", "PASS", "PASS"], "FAIL")
    assert rows["C"]["status"] == "UNCLEAR"
    assert rows["C"]["votes"]["FAIL"] == 1


def test_pass_confidence_gate(panel_stub):
    # weak agreement on a blocking PASS -> escalate to UNCLEAR
    rows, summary = _run(panel_stub, ["PASS", "UNCLEAR", "UNCLEAR"], "PASS", threshold=0.67)
    assert rows["C"]["status"] == "UNCLEAR"  # 2/4 PASS = 0.5 < 0.67
    assert "low panel confidence" in rows["C"]["note"]


def test_deterministic_not_voted(panel_stub):
    p = PanelValidator(api_key="x", jury_size=3, critic_enabled=True)
    res = p.validate(_spec(), _nd(), deterministic_results={"C": {"status": "FAIL", "detail": "exact mismatch"}})
    row = res["criteria_results"][0]
    assert row["status"] == "FAIL"
    assert row["decided_by"] == "deterministic"
    assert row["confidence"] == 1.0
