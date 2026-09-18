"""Full-data check tools: each runs over 100% of the data and returns a small result."""

from services.tools import TOOL_SCHEMAS, dispatch


def _tbl(name, headers, rows):
    return {"name": name, "headers": headers, "rows": rows}


def _nd():
    in_rows = [[str(i), i * 10] for i in range(1, 101)]      # ids 1..100, amount = id*10
    out_rows = [[str(i), i * 10] for i in range(1, 96)]      # output is MISSING ids 96..100
    out_rows[0] = ["1", 999]                                 # and id 1 has a wrong amount
    return {
        "normalized_inputs": [{"file": "in.csv", "document_type": "SPREADSHEET",
                               "tables": [_tbl("reg", ["id", "amount"], in_rows)]}],
        "normalized_outputs": [{"file": "out.csv", "document_type": "SPREADSHEET",
                                "tables": [_tbl("reg", ["id", "amount"], out_rows)]}],
        "_text": [{"file": "notes.txt", "text": "Approved by manager BSR12345"}],
    }


def test_list_tables():
    res = dispatch("list_tables", {}, _nd())
    assert res["count"] == 2
    names = {(t["side"], t["name"], t["row_count"]) for t in res["tables"]}
    assert ("input", "reg", 100) in names
    assert ("output", "reg", 95) in names


def test_count_rows_and_filter():
    nd = _nd()
    assert dispatch("count_rows", {"side": "input"}, nd)["count"] == 100
    # one output row has amount 999
    r = dispatch("count_rows", {"side": "output", "column": "amount", "equals": "999"}, nd)
    assert r["count"] == 1


def test_lookup():
    r = dispatch("lookup", {"side": "output", "column": "id", "value": "1"}, _nd())
    assert r["matches"]["total"] == 1
    assert r["matches"]["shown"][0]["amount"] == 999


def test_aggregate_full_data():
    # sum of amounts 10..1000 step 10 over the full input = 10*(1+..+100) = 50500
    r = dispatch("aggregate", {"side": "input", "column": "amount", "op": "sum"}, _nd())
    assert r["result"] == 50500
    assert r["n"] == 100


def test_reconcile_finds_missing_and_mismatch():
    r = dispatch("reconcile", {}, _nd())
    assert r["missing_key_count"] == 5            # ids 96..100 absent from output
    assert r["value_mismatch_count"] >= 1         # id 1 amount differs (10 vs 999)
    assert r["input_count"] == 100 and r["output_count"] == 95


def test_search_text():
    r = dispatch("search_text", {"query": "BSR12345"}, {
        "normalized_inputs": [{"file": "notes.txt", "text": "Approved by manager BSR12345", "tables": []}],
        "normalized_outputs": [],
    })
    assert r["matches"]["total"] == 1
    assert r["ranking"] == "bm25"


def test_search_text_bm25_ranks_relevant_passage():
    nd = {
        "normalized_inputs": [{"file": "doc.txt", "tables": [], "text":
            "The weather was sunny and pleasant.\n\n"
            "Remittance to the vendor occurred beyond the net 30 payment terms."}],
        "normalized_outputs": [],
    }
    # query terms only partially overlap; naive full-string substring would find nothing,
    # BM25 should still surface the payment passage on top (overlap: net, 30, payment, vendor)
    r = dispatch("search_text", {"query": "vendor paid late net 30 payment"}, nd)
    top = r["matches"]["shown"][0]
    assert "net 30" in top["snippet"].lower()
    assert top["score"] > 0


def test_search_text_tables_use_exact_match():
    nd = {
        "normalized_inputs": [{"file": "t.csv", "text": "",
                               "tables": [_tbl("S", ["id", "code"], [["1", "BSR777"], ["2", "BSR888"]])]}],
        "normalized_outputs": [],
    }
    r = dispatch("search_text", {"query": "BSR777"}, nd)
    rows = [h for h in r["matches"]["shown"] if "row" in h]
    assert len(rows) == 1 and rows[0]["row"] == ["1", "BSR777"]


def test_get_rows_slice_is_bounded():
    r = dispatch("get_rows", {"side": "input", "start": 0, "count": 1000}, _nd())
    assert r["returned"] <= 50                    # capped to _MAX_ITEMS
    assert r["row_count"] == 100


def test_unknown_tool_and_bad_args_are_safe():
    assert "error" in dispatch("nope", {}, _nd())
    assert "error" in dispatch("count_rows", {"side": "input", "column": "missing"}, _nd())
    assert "error" in dispatch("lookup", {"side": "input"}, _nd())  # missing required args


def test_schemas_cover_every_tool():
    from services.tools import _TOOLS
    schema_names = {s["name"] for s in TOOL_SCHEMAS}
    assert schema_names == set(_TOOLS.keys())
