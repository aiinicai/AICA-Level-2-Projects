"""
Run the MCP tools a committee note relies on, then put the note through verify_note (the QC gate).

Usage:  python tools/check_note.py examples/sample_ic_note.md      -> writes <note>.verify.json, exit 1 if any figure is untraced
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp_server"))
import lookthrough_mcp as S  # noqa: E402

note_path = Path(sys.argv[1])
for tool, args in [("list_entities", {}), ("portfolio_summary", {"member": "ALL"}), ("look_through_exposure", {"member": "ALL", "top_n": 10}),
                   ("policy_check", {"member": "ALL"}), ("fund_overlap", {"scheme_a": "S01", "scheme_b": "S02"}),
                   ("company_report", {"symbol": "HDFCBANK"}), ("stress_test", {"market_move_pct": -20}), ("data_provenance", {})]:
    getattr(S, tool)(**args)
body = note_path.read_text(encoding="utf-8").split("\n---\n")[0]  # the verification footer itself is not part of the note
res = S.verify_note(body)["data"]
out = note_path.with_suffix(".verify.json")
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"passed={res['passed']} traced={res['traced']} untraced={len(res['untraced'])} skipped={res['skipped']}")
for u in res["untraced"]:
    print("  UNTRACED", u["figure"], "|", u["context"])
sys.exit(0 if res["passed"] else 1)
