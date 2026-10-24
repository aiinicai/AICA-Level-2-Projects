import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engine as E  # noqa: E402
import store  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_root(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "ROOT", tmp_path / "companies")


def _data():
    m, _ = E.standardise(pd.DataFrame({"Vendor Name": ["Micro Co", "Small Co"], "MSME Category": ["Micro", "Small"],
                                       "PAN": ["ABCDE1234F", None], "Agreed Credit Days": [None, 30],
                                       "Udyam Registration Date": ["01-04-2021", None]}), "vendor_master")
    b, _ = E.standardise(pd.DataFrame({"Bill No": ["1", "2", "3"], "Vendor Name": ["Micro Co", "Micro Co", "Small Co"],
                                       "Bill Date": ["01-07-2026", "10-07-2026", "05-08-2026"], "Bill Amount": [100, 200, 300],
                                       "Acceptance Date": ["03-07-2026", None, None], "Branch": ["Chennai", None, "Pune"]}), "bills")
    p, _ = E.standardise(pd.DataFrame({"Vendor Name": ["Micro Co", "Micro Co"], "Payment Date": ["20-07-2026", "25-08-2026"],
                                       "Amount Paid": [100, 50], "Bill No": ["1", None], "Payment Mode": ["TReDS", None]}), "payments")
    return m, b, p


def test_company_crud_and_isolated_runs():
    a = store.create_company("Acme LLP")
    c = store.create_company("Beta Pvt Ltd")
    m, b, p = _data()
    rid = store.save_run(a, "Apr–Sep 2026", b, p, m, "2026-09-30", 2026, ["a warning"])
    assert [r["id"] for r in store.list_runs(a)] == [rid] and store.list_runs(c) == []
    assert store.list_runs(a)[0]["name"] == "Apr–Sep 2026" and store.list_runs(a)[0]["bills"] == 3
    store.delete_company(a)
    assert [x["slug"] for x in store.list_companies()] == [c]


def test_saved_run_reproduces_identical_results():
    a = store.create_company("Acme LLP")
    m, b, p = _data()
    before = E.build_ledger(b, p, m, "2026-09-30").ledger
    rid = store.save_run(a, "r", b, p, m, "2026-09-30", 2026, [])
    run = store.load_run(a, rid)
    after = E.build_ledger(run["bills"], run["pays"], run["master"], run["as_of"]).ledger
    cols = ["Bill No", "Vendor Name", "Category", "Covered", "Accepted On", "Due Date", "Paid", "Outstanding", "Status", "Branch"]
    pd.testing.assert_frame_equal(before[cols].reset_index(drop=True), after[cols].reset_index(drop=True), check_dtype=False)
    assert run["fy"] == 2026 and run["as_of"] == pd.Timestamp("2026-09-30")
    assert run["pays"].loc[0, "Payment Mode"] == "TReDS"


def test_run_without_payments_and_reasons_roundtrip_and_delete():
    a = store.create_company("Acme LLP")
    m, b, _ = _data()
    empty = pd.DataFrame(columns=["vkey", "bkey", "Payment Date", "Amount Paid", "Reference", "Payment Mode", "Vendor Name", "Bill No"])
    rid = store.save_run(a, "", b, empty, m, "2026-09-30", 2026, [])
    run = store.load_run(a, rid)
    assert len(run["pays"]) == 0 and run["meta"]["name"] == rid           # blank name falls back to id
    E.build_ledger(run["bills"], run["pays"], run["master"], run["as_of"])  # still computes
    store.save_reasons(a, rid, {"Micro Co": "Dispute on quality", "Small Co": "  ", "X": None})
    assert store.load_run(a, rid)["reasons"] == {"Micro Co": "Dispute on quality"}
    rid2 = store.save_run(a, "second", b, empty, m, "2026-09-30", 2026, [])
    assert rid2 != rid and len(store.list_runs(a)) == 2
    store.delete_run(a, rid)
    assert [r["id"] for r in store.list_runs(a)] == [rid2]
