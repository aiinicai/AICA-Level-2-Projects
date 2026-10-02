"""
Verification of the MCP server (mcp_server/lookthrough_mcp.py).

A. Tie-out: every tool's figures are compared with verify/reference_metrics.json, written by a separate
   run of recompute.py. Proves the tool layer's unit conversions (Rs -> crore/lakh, fraction -> %),
   rounding and field mapping; the engine itself is already reconciled against the app.
B. QC gate: a note built from tool outputs must pass verify_note; the same note with one figure altered
   (mutation) and a note with an invented figure must fail and name the offending figure.
C. Input validation: unknown identifiers and out-of-range arguments are refused.
D. End-to-end over stdio, as Claude Desktop runs it: initialise, list tools (all read-only), call tools,
   fetch the prompt.

Usage:  python verify/mcp_check.py      (run recompute.py first so reference_metrics.json is current)
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "mcp_server"))
_live = ROOT / "data" / "live" / "dataset.json"
subprocess.run([sys.executable, str(HERE / "recompute.py"), str(_live if _live.exists() else ROOT / "data" / "snapshot" / "dataset.json")], check=True, capture_output=True)
REF = json.loads((HERE / "reference_metrics.json").read_text())

import lookthrough_mcp as S  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


# ------------------------------------------------------------------ A. tie-out
fam = REF["family"]
ps = S.portfolio_summary("ALL")["data"]
check("summary: family value (cr)", close(ps["value_cr"], fam["value"] / 1e7, 0.005), (ps["value_cr"], fam["value"] / 1e7))
check("summary: family XIRR (%)", close(ps["xirr_pct"], REF["family_xirr"] * 100, 0.005), (ps["xirr_pct"], REF["family_xirr"]))
check("summary: not looked through (cr)", close(ps["look_through"]["not_looked_through_cr"], fam["unmapped"] / 1e7, 0.005))
bad = [m for m, v in REF["per_member"].items() if not close(S.portfolio_summary(m)["data"]["value_cr"], v["value"] / 1e7, 0.005)]
check("summary: value of every entity (cr)", not bad, bad)
bad = [m for m, x in REF["member_xirr"].items() if not close(S.portfolio_summary(m)["data"]["xirr_pct"], None if x is None else x * 100, 0.005)]
check("summary: XIRR of every entity (%)", not bad, bad)

lt = S.look_through_exposure("ALL", 10)["data"]
check("look-through: HHI", close(lt["concentration"]["hhi"], fam["hhi"], 0.00005), (lt["concentration"]["hhi"], fam["hhi"]))
check("look-through: top-10 share (%)", close(lt["concentration"]["top10_pct"], fam["top10"], 0.005))
ref_top = REF["top10"]
bad = [r["symbol"] for r in lt["top_exposures"] if not close(r["total_cr"], ref_top.get(r["symbol"], -1) / 1e7, 0.005)]
check("look-through: top-10 exposures, name and amount", not bad and [r["symbol"] for r in lt["top_exposures"]] == list(ref_top), bad)
bad = [k for k, v in REF["sectors"].items() if not close(lt["sector_weights_pct"].get(k), v, 0.005)]
check("look-through: every sector weight (%)", not bad, bad)

nf = 0
bad = []
for sid, f in REF["fund"].items():
    d = S.fund_report(sid)["data"]
    pairs = [("return_1y_pct", "r1y", 100), ("cagr_3y_pct", "cagr3", 100), ("volatility_pct", "vol", 100), ("max_drawdown_pct", "mdd", 100),
             ("sharpe", "sharpe", 1), ("sortino", "sortino", 1), ("beta", "beta", 1), ("alpha_pct", "alpha", 100),
             ("tracking_error_pct", "te", 100), ("information_ratio", "ir", 1), ("rolling_1y_beat_rate_pct", "roll_beat", 100)]
    for k, rk, mult in pairs:
        nf += 1
        if not close(d[k], None if f.get(rk) is None else f[rk] * mult, 0.005):
            bad.append(f"{sid}.{k}")
check(f"fund_report: {nf} metrics across {len(REF['fund'])} schemes", not bad, bad[:8])

bad, n = [], 0
for key, v in REF["overlap"].items():
    a, b = key.split("|")
    n += 1
    if not close(S.fund_overlap(a, b)["data"]["overlap_pct"], v, 0.005):
        bad.append(key)
check(f"fund_overlap: all {n} scheme pairs (incl. not-computable)", not bad, bad[:8])

bad = []
for m, t in REF["tax"].items():
    d = S.tax_position(m)["data"]
    for k, rk in [("realised_short_term_lakh", "realised_st"), ("realised_long_term_lakh", "realised_lt"), ("unrealised_short_term_lakh", "unrealised_st"),
                  ("unrealised_long_term_lakh", "unrealised_lt"), ("tax_if_all_sold_lakh", "tax_if_all_sold"), ("exemption_headroom_lakh", "harvest_headroom")]:
        if not close(d[k], t[rk] / 1e5, 0.005):
            bad.append(f"{m}.{k}")
check(f"tax_position: 6 figures x {len(REF['tax'])} entities (lakh)", not bad, bad)

bad, n = [], 0
for code, rat in REF["ratios"].items():
    d = S.company_report(code)["data"]["ratios"]
    for k, v in rat.items():
        n += 1
        if not close(d.get(k), v, 0.005 if k != "fscore" else 0):
            bad.append(f"{code}.{k}")
check(f"company_report: {n} ratios across {len(REF['ratios'])} companies", not bad, bad[:8])

st = S.stress_test(-20)["data"]
check("stress_test(-20): matches reference scenario", close(st["estimated_change_cr"], REF["stress"]["market_minus20"] / 1e7, 0.005))

pc = S.policy_check("ALL")["data"]
single = [t for t in pc["tests"] if t["test"].startswith("Single stock") and t["status"] == "BREACH"]
check("policy_check: single-stock breach iff top exposure > limit",
      bool(single) == (fam["top_pct"] > S.E.POL["max_single_stock_pct"]), (fam["top_pct"], len(single)))
check("policy_check: a test with no value is NOT COMPUTABLE, never 'within limit'",
      all(t["status"] == "NOT COMPUTABLE" for t in pc["tests"] if t["value"] is None)
      and pc["not_computable"] == sum(t["value"] is None for t in pc["tests"]), [t for t in pc["tests"] if t["value"] is None])
check("policy_check: HHI status agrees with limit",
      next(t for t in pc["tests"] if t["test"] == "HHI")["status"] == ("BREACH" if fam["hhi"] > S.E.POL["max_hhi"] else "within limit"))

_eq_all = float(S.E.lt_all.total.sum()) + float(S.E.unmapped_all)
check("stress: an impossible -500% market move loses at most the whole equity (no share falls more than 100%)",
      0 < -S.E.stress_market(-5.0) <= _eq_all + 1e-6, (S.E.stress_market(-5.0), _eq_all))

# ------------------------------------------------------------------ B. QC gate
top = lt["top_exposures"][0]
note = (f"[FACT] Family portfolio value is Rs {ps['value_cr']} cr with XIRR {ps['xirr_pct']}% (portfolio_summary, as on 31-Aug-2026).\n"
        f"[CALC] Largest look-through exposure: {top['company']} at {top['pct_of_equity']}% of equity, Rs {top['total_cr']} cr "
        f"(look_through_exposure); the single-stock limit is 10% (policy_check).\n"
        f"[CALC] HHI {lt['concentration']['hhi']}; top-10 share {lt['concentration']['top10_pct']}%.\n"
        f"[CALC] A 20% market fall would change equity by Rs {st['estimated_change_cr']} cr (stress_test).\n"
        "Tax: sections 196 and 198 of the Income-tax Act, 2025 (FY 2026-27).")
v = S.verify_note(note)["data"]
check("verify_note: note built from tool outputs passes", v["passed"] and v["traced"] >= 7, v)
mutated = note.replace(str(ps["value_cr"]), f"{ps['value_cr'] + 1.37:.2f}")
v = S.verify_note(mutated)["data"]
check("verify_note: ONE altered figure is caught (mutation)", not v["passed"] and len(v["untraced"]) == 1
      and v["untraced"][0]["figure"] == f"{ps['value_cr'] + 1.37:.2f}", v["untraced"])
v = S.verify_note("The fund returned 23.45% last year and AUM is Rs 812.6 cr.")["data"]
check("verify_note: invented figures are flagged", not v["passed"] and {u["figure"] for u in v["untraced"]} == {"23.45", "812.6"}, v["untraced"])
v = S.verify_note(f"Value Rs {ps['value_cr']*100:.0f} lakh; XIRR {ps['xirr_pct']/100:.4f} as a fraction.")["data"]
check("verify_note: unit restatements (crore->lakh, %->fraction) trace", v["passed"], v)

# binding: the right number is not enough, it must be the right field, in the right unit, from the cited tool
cash = ps["look_through"]["cash_in_funds_cr"]
v = S.verify_note(f"A 20% market fall is scored at a portfolio beta of {cash} (stress_test).")["data"]
check("verify_note binding: a value that only coincides with another field (cash in funds as 'beta') is refused",
      not v["passed"] and v["untraced"][0]["figure"] == f"{cash}", v["untraced"])
v = S.verify_note(f"HDFC Bank is {top['pct_of_equity']}% of look-through equity (fund_overlap).")["data"]
check("verify_note binding: a figure cited to a tool that did not return it is refused, naming the right tool",
      not v["passed"] and "look_through_exposure" in v["untraced"][0]["reason"], v["untraced"])
v = S.verify_note(f"HDFC Bank exposure is Rs {top['pct_of_equity']} cr (look_through_exposure).")["data"]
check("verify_note binding: a percentage written as Rs crore is refused (unit)", not v["passed"] and "writes it as Rs crore" in v["untraced"][0]["reason"], v["untraced"])
v = S.verify_note(f"The top-10 share of equity is {ps['xirr_pct']}%.")["data"]
check("verify_note binding: a returned value attached to the wrong description is refused (XIRR as top-10 share)",
      not v["passed"] and "does not name that figure" in v["untraced"][0]["reason"], v["untraced"])
v = S.verify_note(f"HDFC Bank: Rs {top['total_cr']} cr held directly (look_through_exposure).")["data"]
check("verify_note binding: a sibling field of the same record (total described as 'held directly') is refused",
      not v["passed"] and "describes direct_cr" in v["untraced"][0]["reason"], v["untraced"])
v = S.verify_note(f"HDFC Bank: Rs {top['direct_cr']} cr is held directly and Rs {top['via_funds_cr']} cr through mutual funds (look_through_exposure).")["data"]
check("verify_note binding: two fields of one record in one sentence both bind to the right field",
      v["passed"] and [d["source"].split(".")[-1] for d in v["traced_detail"]] == ["direct_cr", "via_funds_cr"], v)
v = S.verify_note(f"HDFC Bank: Rs {top['via_funds_cr']} cr is held directly and Rs {top['direct_cr']} cr through mutual funds (look_through_exposure).")["data"]
check("verify_note binding: two fields of one record SWAPPED in one sentence are refused", not v["passed"], v)
for tool, args in [("fund_overlap", {"scheme_a": "S01", "scheme_b": "S02"}), ("company_report", {"symbol": "HDFCBANK"}), ("data_provenance", {})]:
    getattr(S, tool)(**args)
sample = (ROOT / "examples" / "sample_ic_note.md").read_text(encoding="utf-8").split("\n---\n")[0]
v = S.verify_note(sample)["data"]
check("verify_note binding: the published sample IC note passes with every figure bound to its field", v["passed"] and v["traced"] >= 30, v["untraced"])
v = S.verify_note(f"XIRR is {ps['xirr_pct']}% and the portfolio beta is {st['portfolio_beta']} (portfolio_summary; stress_test).")["data"]
check("verify_note binding: the same values with the right description, unit and citation pass", v["passed"] and v["traced"] == 2, v)

# ------------------------------------------------------------------ C. input validation
for label, fn in [("unknown member", lambda: S.portfolio_summary("M9")), ("unknown scheme", lambda: S.fund_report("S99")),
                  ("unknown company", lambda: S.company_report("NOSUCHCO")), ("tax for ALL refused", lambda: S.tax_position("ALL")),
                  ("stress out of range", lambda: S.stress_test(-95)), ("same scheme twice", lambda: S.fund_overlap("S01", "S01"))]:
    try:
        fn()
        check(f"validation: {label}", False, "no error raised")
    except ValueError:
        check(f"validation: {label}", True)


# ------------------------------------------------------------------ D. end-to-end over stdio
def attr(obj, *names):
    """mcp v2 client models use snake_case (read_only_hint); v1 used camelCase (readOnlyHint)."""
    return next((getattr(obj, n) for n in names if hasattr(obj, n)), None)


async def e2e():
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server" / "lookthrough_mcp.py")], cwd=str(ROOT))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            names = sorted(t.name for t in tools)
            check("stdio: server lists 11 tools", len(names) == 11, names)
            ro = lambda t: bool(t.annotations and attr(t.annotations, "read_only_hint", "readOnlyHint"))  # noqa: E731
            check("stdio: every tool is annotated read-only", all(ro(t) for t in tools), [t.name for t in tools if not ro(t)])
            res = await s.call_tool("portfolio_summary", {"member": "ALL"})
            body = attr(res, "structured_content", "structuredContent") or json.loads(res.content[0].text)
            body = body.get("result", body)
            check("stdio: portfolio_summary returns the family value", close(body["data"]["value_cr"], ps["value_cr"], 0.0), body.get("data", {}).get("value_cr"))
            bad = await s.call_tool("fund_report", {"scheme_id": "S99"})
            msg = " ".join(getattr(c, "text", "") for c in bad.content)
            check("stdio: invalid input -> tool error whose message names the valid ids",
                  bool(attr(bad, "is_error", "isError")) and "S01" in msg, msg[:160])
            pr = await s.get_prompt("ic_note", {"question": "Is the family over-exposed to banks?"})
            check("stdio: ic_note prompt renders", "verify_note" in pr.messages[0].content.text)


asyncio.run(e2e())

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} MCP checks passed")
(HERE / "mcp_result.txt").write_text("\n".join(("PASS  " if ok else "FAIL  ") + n for n, ok, _ in results) +
                                     f"\n\n{len(results) - len(failed)}/{len(results)} MCP checks passed\n", encoding="utf-8")
sys.exit(1 if failed else 0)
