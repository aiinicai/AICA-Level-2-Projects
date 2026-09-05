"""Tool-calling validator loop: tool dispatch, aggregation, deterministic authority."""

from models.check_spec import CheckSpec
from services.tool_validator import ToolCallingValidator


def _tbl(name, headers, rows):
    return {"name": name, "headers": headers, "rows": rows}


def _nd():
    rows = [[str(i), i * 10] for i in range(1, 51)]
    out = [[str(i), i * 10] for i in range(1, 51)]
    out[4] = ["5", 999]  # id 5 amount wrong
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET",
                               "tables": [_tbl("reg", ["id", "amount"], rows)]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET",
                                "tables": [_tbl("reg", ["id", "amount"], out)]}],
    }


def _spec():
    return CheckSpec.from_ai_dict({"criteria": [
        {"id": "C1", "statement": "Every input id appears with the right amount in the output",
         "type": "hybrid", "severity": "critical"}]})


class _ScriptedValidator(ToolCallingValidator):
    """Drives the loop: first turn calls reconcile(), second turn returns the verdict
    grounded in what reconcile actually returned (value 999, present in the data)."""

    def __init__(self, **kw):
        super().__init__(api_key="x", **kw)
        self.turn = 0
        self.saw_tool_result = False

    def _chat(self, messages):
        self.turn += 1
        if self.turn == 1:
            return {"content": None, "tool_calls": [{"id": "t1", "name": "reconcile", "arguments": {}}]}
        # confirm the tool result was fed back into the conversation
        self.saw_tool_result = any(m.get("role") == "tool" for m in messages)
        return {"content": '{"criteria_results": [{"id": "C1", "status": "FAIL",'
                           ' "evidence": "id 5 amount 999 mismatch", "explanation": "wrong amount"}]}',
                "tool_calls": []}


def test_loop_calls_tool_then_returns_grounded_verdict():
    v = _ScriptedValidator()
    res = v.validate(_spec(), _nd(), deterministic_results={})
    row = res["criteria_results"][0]
    assert v.turn == 2
    assert v.saw_tool_result is True              # reconcile result was appended as a tool message
    assert row["status"] == "FAIL"               # grounded (999 exists in data) -> kept
    assert row["verified_by"] == "ai_tools"
    assert res["metadata"]["validator"] == "tool_loop"
    assert res["metadata"]["coverage"] == "full"


def test_deterministic_result_overrides_model():
    class V(ToolCallingValidator):
        def _chat(self, messages):
            return {"content": '{"criteria_results": [{"id": "C1", "status": "PASS", "evidence": "x"}]}',
                    "tool_calls": []}
    res = V(api_key="x").validate(_spec(), _nd(),
                                  deterministic_results={"C1": {"status": "FAIL", "detail": "5 missing"}})
    row = res["criteria_results"][0]
    assert row["status"] == "FAIL"               # deterministic floor wins over the model
    assert row["verified_by"] == "deterministic"


def test_loop_terminates_on_runaway_tool_calls():
    class V(ToolCallingValidator):
        def _chat(self, messages):
            # never stops calling tools -> loop must bail out after max_iters
            return {"content": None, "tool_calls": [{"id": "t", "name": "list_tables", "arguments": {}}]}
    v = V(api_key="x", max_iters=3)
    res = v.validate(_spec(), _nd(), deterministic_results={})
    # no verdict produced -> criterion is UNCLEAR, but the call returns cleanly
    assert res["criteria_results"][0]["status"] == "UNCLEAR"
