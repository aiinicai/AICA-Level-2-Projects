"""
Regenerate examples/ from the current dataset: MCP tool outputs for typical committee questions and
the monthly-monitor payload. Every figure comes from the MCP tools (the reconciled engine).

Usage:  python tools/make_examples.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp_server"))
sys.path.insert(0, str(ROOT / "bridge"))
OUT = ROOT / "examples"
OUT.mkdir(exist_ok=True)

import lookthrough_mcp as S  # noqa: E402
import monitor_push as M  # noqa: E402

calls = [
    ("Who and what is in the portfolio?", "list_entities", {}),
    ("How is the family doing overall?", "portfolio_summary", {"member": "ALL"}),
    ("What do we really own once funds are looked through?", "look_through_exposure", {"member": "ALL", "top_n": 10}),
    ("Are we within the investment policy?", "policy_check", {"member": "ALL"}),
    ("How similar are our two large-cap funds?", "fund_overlap", {"scheme_a": "S01", "scheme_b": "S02"}),
    ("How has Parag Parikh Flexi Cap performed?", "fund_report", {"scheme_id": "S05"}),
    ("What are HDFC Bank's fundamentals and our exposure?", "company_report", {"symbol": "HDFCBANK"}),
    ("What is the HUF's capital-gains position?", "tax_position", {"member": "M3"}),
    ("What if the market falls 20%?", "stress_test", {"market_move_pct": -20}),
    ("Where did the data come from?", "data_provenance", {}),
]
examples = []
for question, tool, args in calls:
    examples.append({"question": question, "tool": tool, "arguments": args, "result": getattr(S, tool)(**args)})
(OUT / "mcp_tool_outputs.json").write_text(json.dumps(examples, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

payload = M.build_payload()
(OUT / "monitor_payload.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
print("examples written:", [p.name for p in OUT.iterdir()])
