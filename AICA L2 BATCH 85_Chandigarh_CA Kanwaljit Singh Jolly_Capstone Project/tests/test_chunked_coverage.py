"""Chunked full-coverage reading: the validator reads 100% of large content."""

import json

from models.check_spec import CheckSpec
from services.generic_validator import GenericValidator, _chunk_side, _side_size


def _tbl(name, headers, rows):
    return {"name": name, "headers": headers, "rows": rows}


def _nd(in_rows, out_rows):
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET",
                               "tables": [_tbl("S", ["id", "amount"], in_rows)]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET",
                                "tables": [_tbl("S", ["id", "amount"], out_rows)]}],
    }


def test_chunk_side_covers_every_row():
    rows = [[str(i), i] for i in range(500)]
    arts = [{"file": "o.csv", "document_type": "SPREADSHEET", "tables": [_tbl("S", ["id", "amount"], rows)]}]
    chunks = _chunk_side(arts, "OUTPUT", budget=400)
    assert len(chunks) > 1  # forced to split
    blob = "\n".join(chunks)
    # every row id must appear somewhere across the chunks (nothing dropped)
    for i in range(500):
        assert f"'{i}'" in blob or f"[{i}," in blob or f", {i}]" in blob


class _PerChunkStub(GenericValidator):
    """Returns a verdict keyed by what row values appear in the current chunk's prompt."""

    def __init__(self, defect_value, **kw):
        super().__init__(api_key="x", **kw)
        self.defect_value = defect_value
        self.calls = 0

    def _complete(self, prompt):
        self.calls += 1
        # FAIL only on the chunk that actually contains the planted defect value
        if self.defect_value in prompt:
            return json.dumps({"criteria_results": [
                {"id": "LOCAL", "status": "FAIL",
                 "evidence": f"amount {self.defect_value} is wrong", "explanation": "bad"}]})
        return json.dumps({"criteria_results": [
            {"id": "LOCAL", "status": "PASS", "evidence": "row looks fine", "explanation": "ok"}]})


def test_defect_in_last_chunk_is_caught():
    # small input (stays whole), large output (chunked); defect sits in a late row
    out_rows = [[str(i), i] for i in range(400)]
    out_rows[399] = ["399", "DEFECT777"]
    nd = _nd([["1", 1]], out_rows)
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "LOCAL", "statement": "Each amount is a valid number", "type": "semantic", "severity": "error"}]})

    v = _PerChunkStub("DEFECT777", budget=1500)
    res = v.validate(spec, nd, deterministic_results={})
    row = res["criteria_results"][0]

    assert v.calls > 1                            # multiple chunks were read
    assert res["metadata"]["coverage"] == "full"  # nothing sampled away
    assert res["metadata"]["read_chunks"] > 1
    assert row["status"] == "FAIL"                # defect in a late chunk still caught
    assert row["verified_by"] == "ai_full_read"


def test_small_task_is_single_full_read():
    nd = _nd([["1", 100]], [["1", 100]])
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "C", "statement": "Values are correct", "type": "semantic", "severity": "error"}]})

    class V(GenericValidator):
        def _complete(self, prompt):
            return json.dumps({"criteria_results": [
                {"id": "C", "status": "PASS", "evidence": "id 1 amount 100", "explanation": "ok"}]})

    res = V(api_key="x").validate(spec, nd, deterministic_results={})
    assert res["metadata"]["read_chunks"] == 1
    assert res["metadata"]["coverage"] == "full"
    assert res["criteria_results"][0]["verified_by"] == "ai_full_read"


def test_side_size_grows_with_rows():
    small = _side_size([{"tables": [_tbl("S", ["id"], [["1"]])]}])
    big = _side_size([{"tables": [_tbl("S", ["id"], [[str(i)] for i in range(1000)])]}])
    assert big > small
