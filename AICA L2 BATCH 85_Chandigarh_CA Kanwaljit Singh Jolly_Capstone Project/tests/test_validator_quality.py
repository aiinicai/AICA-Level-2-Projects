"""Generic validator quality gates: truncation honesty, grounding, anti-rubber-stamp."""

import json

from models.check_spec import CheckSpec
from services.generic_validator import GenericValidator, _render_side


def _tbl(name, headers, rows):
    return {"name": name, "headers": headers, "rows": rows}


def _nd(in_rows, out_rows):
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET",
                               "tables": [_tbl("S", ["id", "amount"], in_rows)]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET",
                                "tables": [_tbl("S", ["id", "amount"], out_rows)]}],
    }


def _stub(verdicts, budget=2000):
    # Pin a small read window so these logic tests are deterministic regardless of the
    # model-auto-sized default (the sampling test relies on a window the data exceeds).
    class V(GenericValidator):
        def _complete(self, prompt):
            return json.dumps({"criteria_results": verdicts})
    return V(api_key="x", budget=budget)


def test_render_side_truncation_flag():
    big = {"normalized_outputs": [{"file": "o.csv", "document_type": "SPREADSHEET",
            "tables": [_tbl("S", ["id", "v"], [[str(i), i] for i in range(5000)])]}]}
    text, truncated = _render_side(big["normalized_outputs"], "OUTPUT", budget=2000)
    assert truncated is True
    assert "more rows not shown" in text


def test_ungrounded_failure_downgraded():
    nd = _nd([["1", 100], ["2", 200], ["3", 300]], [["1", 100], ["2", 200], ["3", 300]])
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Amounts are plausible", "type": "semantic", "severity": "error"}]})
    # AI fails citing values that do NOT exist anywhere in the data -> ungrounded -> UNCLEAR
    res = _stub([{"id": "C", "status": "FAIL", "evidence": "Row 9 shows 88888 which is invalid",
                  "explanation": "bad"}]).validate(spec, nd, deterministic_results={})
    c = res["criteria_results"][0]
    assert c["status"] == "UNCLEAR"
    assert res["metadata"]["ungrounded_failures_removed"] == 1


def test_grounded_failure_kept():
    nd = _nd([["1", 100], ["2", 200], ["3", 300]], [["1", 100], ["2", 200], ["3", 300]])
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Amounts are plausible", "type": "semantic", "severity": "error"}]})
    # cites real values present in the data -> stays FAIL
    res = _stub([{"id": "C", "status": "FAIL", "evidence": "id 2 has amount 200 which violates policy",
                  "explanation": "bad"}]).validate(spec, nd, deterministic_results={})
    assert res["criteria_results"][0]["status"] == "FAIL"


def test_coverage_unclear_when_read_in_chunks_never_sampled():
    # BOTH sides exceed the window -> cross-product chunking reads 100% (NEVER sampled).
    # A coverage/completeness claim still can't be confirmed from a single chunk, so it
    # stays UNCLEAR (to be settled by the deterministic check), while a local semantic
    # judgment can still pass. Crucially: coverage is "full", not "sampled".
    big = [[str(i), i] for i in range(300)]
    nd = _nd(big, big)
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "COV", "statement": "Every record is complete", "type": "semantic", "severity": "critical"},
        {"id": "TONE", "statement": "The wording is professional", "type": "semantic", "severity": "info"}]})
    res = _stub([{"id": "COV", "status": "PASS", "evidence": "looks complete", "explanation": "ok"},
                 {"id": "TONE", "status": "PASS", "evidence": "reads well", "explanation": "ok"}]
                ).validate(spec, nd, deterministic_results={})
    by = {r["id"]: r for r in res["criteria_results"]}
    assert res["metadata"]["truncated"] is False      # nothing was sampled away
    assert res["metadata"]["coverage"] == "full"      # 100% read
    assert res["metadata"]["read_chunks"] > 1         # via cross-product chunks
    assert by["COV"]["status"] == "UNCLEAR"           # completeness not confirmable per-chunk
    assert by["COV"]["verified_by"] == "ai_chunked"
    assert by["TONE"]["status"] == "PASS"             # local judgment is fine


def test_anti_rubber_stamp_not_over_aggressive():
    nd = _nd([["1", 100]], [["1", 100]])
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Values are correct", "type": "semantic", "severity": "error"}]})
    # PASS whose evidence says "no values are missing" must NOT be downgraded
    res = _stub([{"id": "C", "status": "PASS", "evidence": "no values are missing", "explanation": "all good"}]
                ).validate(spec, nd, deterministic_results={})
    assert res["criteria_results"][0]["status"] == "PASS"
