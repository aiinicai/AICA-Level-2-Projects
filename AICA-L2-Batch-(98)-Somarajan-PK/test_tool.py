"""End-to-end API test of the whole flow. Run: python test_tool.py"""
import json, tempfile, threading, urllib.error, urllib.request
import openpyxl
import mock_tally, tool_server


def call(base, path, body=None, headers=None, raw=False):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read()
            return r.status, (data if raw else json.loads(data)), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), e.headers


def test_flow():
    mt = mock_tally.serve(0); threading.Thread(target=mt.serve_forever, daemon=True).start()
    tport = mt.server_address[1]
    data, exp = tempfile.mkdtemp(), tempfile.mkdtemp()
    ts = tool_server.serve(0, data, open_browser=False, export_dir=exp); threading.Thread(target=ts.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{ts.server_address[1]}"
    # 1. connector
    s, r, _ = call(base, "/api/tally/test", {"host": "localhost", "port": tport}); assert s == 200 and len(r["bank_ledgers"]) == 2
    s, r, _ = call(base, "/api/tally/pull", {"host": "localhost", "port": tport, "from": "01-10-2026", "to": "31-10-2026"}); assert s == 200
    tally = r["data"]; bank = tally["banks"][0]
    assert call(base, "/api/tally/test", {"host": "8.8.8.8"})[0] == 400
    assert call(base, "/api/tally/test", {"host": "localhost", "port": 1})[0] == 502
    assert call(base, "/api/tally/test", {}, {"Origin": "http://evil.example"})[0] == 403
    # 2. demo statement + check
    demo = call(base, "/api/demo")[1]; stmt = demo["statements"][bank["name"]]
    s, info, _ = call(base, "/api/statement/check", {"csv": stmt}); assert s == 200 and info["rows"] == 36 and info["opening"] == 521500.0
    assert call(base, "/api/statement/check", {"csv": "Foo,Bar\n1,2"})[0] == 400
    # 3. reconcile
    body = dict(bank=bank["name"], entity=tally["company"], period_from="01-10-2026", period_to="31-10-2026",
                books=dict(opening_balance=bank["opening_balance"], rows=bank["rows"]), statement_csv=stmt,
                opening_csv=demo["opening"][bank["name"]], settings=demo["settings"])
    s, r, _ = call(base, "/api/reconcile", body); assert s == 200, r
    res, rid = r["result"], r["run_id"]
    assert res["reconciled"] and res["diff"] == 0 and res["metrics"]["bank_matched"] == 32 and len(res["items"]) == 11 and len(res["flags"]) == 10
    n = len(res["entries"]); assert n == 5
    # 4. export is blocked until approved / decided
    ex = lambda **ap: call(base, "/api/export", {"run_id": rid, "approval": ap}, raw=True)
    assert ex(approved=False, reviewer="CA", decisions=["Approved"] * n)[0] == 400
    assert ex(approved=True, reviewer="", decisions=["Approved"] * n)[0] == 400
    assert ex(approved=True, reviewer="CA", decisions=["Approved"] * (n - 1) + [None])[0] == 400
    assert call(base, "/api/export", {"run_id": "nope", "approval": {}}, raw=True)[0] == 410
    # 5. approved export
    dec = ["Approved"] * (n - 1) + ["Rejected"]
    s, blob, h = ex(approved=True, reviewer="Test CA", remarks="ok", decisions=dec)
    assert s == 200 and h["X-File-Name"].endswith("_APPROVED.xlsx")
    wb = openpyxl.load_workbook(h["X-Saved-To"])
    assert wb.sheetnames[0] == "Approval" and {"Summary", "Matched", "Unmatched", "BRS", "Exceptions", "Journal entries"} <= set(wb.sheetnames)
    ap = {r[0].value: r[1].value for r in wb["Approval"].iter_rows(min_row=2)}
    assert ap["Approved by"] == "Test CA" and ap["Journal entries approved / rejected"] == f"{n-1} / 1"
    assert [r[5].value for r in wb["Journal entries"].iter_rows(min_row=2, max_row=n + 1)] == dec
    # 6. second bank still works and shows unreconciled-difference rule via remarks
    bank2 = tally["banks"][1]
    b2 = dict(body, bank=bank2["name"], books=dict(opening_balance=bank2["opening_balance"], rows=bank2["rows"]),
              statement_csv=demo["statements"][bank2["name"]], opening_csv="")
    r2 = call(base, "/api/reconcile", b2)[1]["result"]; assert r2["reconciled"] and r2["metrics"]["bank_matched"] == 4
    html = urllib.request.urlopen(base + "/").read().decode(); assert "Approve &amp; export" in html or "Approve & export" in html


if __name__ == "__main__":
    test_flow(); print("full-flow tests pass")
