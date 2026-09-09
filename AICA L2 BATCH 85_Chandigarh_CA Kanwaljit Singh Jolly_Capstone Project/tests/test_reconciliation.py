"""Multi-table reconciliation + fuzzy column mapping in generic_checks."""

from models.check_spec import CheckSpec
from services.generic_checks import _compute_facts, _map_columns, run_generic_checks

SPEC = CheckSpec.from_ai_dict({"criteria": [
    {"id": "COV", "statement": "Every input id appears in the output", "type": "deterministic", "severity": "critical"},
    {"id": "VAL", "statement": "Amount values match per id", "type": "deterministic", "severity": "error"},
]})


def _tbl(name, headers, rows):
    return {"name": name, "headers": headers, "rows": rows}


def _nd(inputs, outputs):
    return {
        "normalized_inputs": [{"file": f"in{i}.csv", "document_type": "SPREADSHEET", "tables": [t]}
                              for i, t in enumerate(inputs)],
        "normalized_outputs": [{"file": f"out{i}.csv", "document_type": "SPREADSHEET", "tables": [t]}
                               for i, t in enumerate(outputs)],
    }


def test_fuzzy_column_mapping():
    # case/punctuation differences normalize to an exact match
    assert _map_columns(["PAN", "TDS Amount"], ["pan", "tds_amount"]) == {"PAN": "pan", "TDS Amount": "tds_amount"}
    # substring match (Amount -> Amount Paid)
    assert _map_columns(["Amount"], ["Amount Paid"]) == {"Amount": "Amount Paid"}


def test_renamed_columns_still_reconcile():
    inp = [_tbl("S", ["id", "Amount"], [["1", 100], ["2", 200]])]
    ok = run_generic_checks(SPEC, _nd(inp, [_tbl("S", ["ID", "Amount Paid"], [["1", 100], ["2", 200]])]))
    bad = run_generic_checks(SPEC, _nd(inp, [_tbl("S", ["ID", "Amount Paid"], [["1", 100], ["2", 999]])]))
    assert ok["VAL"]["status"] == "PASS"
    assert bad["VAL"]["status"] == "FAIL"


def test_multi_table_all_reconciled():
    inp = [_tbl("A", ["id", "amount"], [["1", 10]]), _tbl("B", ["pan", "tds"], [["X", 5]])]
    out = [_tbl("A", ["id", "amount"], [["1", 10]]), _tbl("B", ["pan", "tds"], [["X", 5]])]
    facts = _compute_facts(_nd(inp, out))
    assert len(facts["pairs"]) == 2
    assert facts["unreconciled_input_tables"] == 0
    r = run_generic_checks(SPEC, _nd(inp, out))
    assert r["COV"]["status"] == "PASS"


def test_partial_reconciliation_does_not_false_pass():
    # second input table has no matching output -> coverage must NOT be asserted PASS
    inp = [_tbl("A", ["id", "amount"], [["1", 10]]), _tbl("B", ["pan", "tds"], [["X", 5]])]
    out = [_tbl("A", ["id", "amount"], [["1", 10]])]
    facts = _compute_facts(_nd(inp, out))
    assert facts["unreconciled_input_tables"] == 1
    r = run_generic_checks(SPEC, _nd(inp, out))
    assert "COV" not in r or r["COV"]["status"] != "PASS"
