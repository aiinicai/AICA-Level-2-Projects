"""Scoped LLM tie-breaker: resolves contested criteria, clamped by the code's guarantees."""

import json

import pytest

import services.generic_validator as gv
from models.check_spec import CheckSpec
from services.jury import ADVERSARIAL_PROMPT, PanelValidator


def _nd():
    tbl = {"name": "S", "headers": ["id", "amount"], "rows": [["1", 100]]}
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET", "tables": [tbl]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET", "tables": [tbl]}],
    }


def _spec(sev="error"):
    return CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Values are correct", "type": "semantic", "severity": sev}]})


@pytest.fixture
def stub(monkeypatch):
    state = {"juror_by_temp": {}, "critic": ("PASS", "id 1 amount 100"),
             "tb": ("FAIL", "id 1 amount 100 is wrong"), "calls": {"n": 0}}

    def fake_complete(self, prompt):
        if self.system_prompt == ADVERSARIAL_PROMPT:
            status, ev = state["critic"]
        else:
            status, ev = state["juror_by_temp"].get(self.temperature, ("PASS", "id 1 amount 100"))
        return json.dumps({"criteria_results": [{"id": "C", "status": status, "evidence": ev, "explanation": ev}]})

    def fake_tb(self, prompt):
        state["calls"]["n"] += 1
        st, ev = state["tb"]
        return json.dumps({"status": st, "evidence": ev, "explanation": ev})

    monkeypatch.setattr(gv.GenericValidator, "_complete", fake_complete)
    monkeypatch.setattr(PanelValidator, "_tiebreak_complete", fake_tb)
    return state


def _panel(threshold=0.67):
    p = PanelValidator(api_key="x", jury_size=3, critic_enabled=True, confidence_threshold=threshold)
    p.tiebreaker_enabled = True
    p.tiebreaker_model = "x"
    return p


def _set(state, jurors, critic):
    temps = [0.0, 0.4, 0.8]
    state["juror_by_temp"] = {temps[i]: (jurors[i], "id 1 amount 100") for i in range(len(jurors))}
    state["critic"] = (critic, "id 1 amount 100")


def test_resolves_contested_to_grounded_fail(stub):
    _set(stub, ["FAIL", "PASS", "PASS"], "PASS")   # fail_n=1 -> mechanical UNCLEAR, contested
    stub["tb"] = ("FAIL", "id 1 amount 100 is wrong")  # grounded (100 exists)
    res = _panel().validate(_spec(), _nd(), deterministic_results={})
    row = res["criteria_results"][0]
    assert row["status"] == "FAIL"
    assert row["decided_by"] == "panel+tiebreak"
    assert row["note"] == "resolved by tie-breaker"
    assert res["metadata"]["tiebreaks"] == 1
    assert stub["calls"]["n"] == 1


def test_ungrounded_fail_stays_unclear(stub):
    _set(stub, ["FAIL", "PASS", "PASS"], "PASS")
    stub["tb"] = ("FAIL", "row 99 value 88888 is wrong")  # cites values not in the data
    row = _panel().validate(_spec(), _nd(), deterministic_results={})["criteria_results"][0]
    assert row["status"] == "UNCLEAR"
    assert "ungrounded" in row["note"]


def test_pass_on_blocking_below_confidence_stays_unclear(stub):
    _set(stub, ["FAIL", "PASS", "PASS"], "PASS")   # confidence 0.25
    stub["tb"] = ("PASS", "id 1 amount 100 fine")
    row = _panel(threshold=0.9).validate(_spec("critical"), _nd(), deterministic_results={})["criteria_results"][0]
    assert row["status"] == "UNCLEAR"
    assert "confidence gate" in row["note"]


def test_pass_applies_on_non_blocking(stub):
    _set(stub, ["FAIL", "PASS", "PASS"], "PASS")
    stub["tb"] = ("PASS", "id 1 amount 100 fine")
    row = _panel().validate(_spec("info"), _nd(), deterministic_results={})["criteria_results"][0]
    assert row["status"] == "PASS"
    assert row["decided_by"] == "panel+tiebreak"


def test_not_called_when_no_disagreement(stub):
    _set(stub, ["PASS", "PASS", "PASS"], "PASS")
    res = _panel().validate(_spec(), _nd(), deterministic_results={})
    assert res["criteria_results"][0]["status"] == "PASS"
    assert stub["calls"]["n"] == 0
    assert res["metadata"]["tiebreaks"] == 0


def test_deterministic_never_tiebroken(stub):
    res = _panel().validate(_spec(), _nd(),
                            deterministic_results={"C": {"status": "FAIL", "detail": "exact mismatch"}})
    row = res["criteria_results"][0]
    assert row["decided_by"] == "deterministic"
    assert stub["calls"]["n"] == 0
