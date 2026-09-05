"""
Human-readable rendering of a pipeline result.

Turns the machine result from SectionPipeline.run() into a plain-text report that
explains, for a person: what the overall verdict is, HOW each criterion was checked
(deterministic code vs. AI vs. the panel of models), what the panel actually did
(which models voted and how), and the evidence behind every non-pass.
"""

from typing import Any, Dict, List

_STATUS_ICON = {"PASS": "[PASS]", "FAIL": "[FAIL]", "UNCLEAR": "[????]",
                "WARN": "[WARN]", "INDETERMINATE": "[????]"}

_DECIDED_LABEL = {
    "deterministic": "deterministic code (exact)",
    "ai": "AI reasoning",
    "ai_tools": "AI + data tools",
    "ai_full_read": "AI (read 100% of data)",
    "ai_chunked": "AI (read all data in chunks)",
    "ai_sampled": "AI (sampled — data too large)",
    "panel": "panel of models (vote)",
    "panel+tiebreak": "panel + LLM tie-breaker",
}

_SEV_LABEL = {"critical": "CRITICAL", "error": "ERROR", "warning": "WARNING", "info": "info"}
_STATUS_ORDER = {"FAIL": 0, "UNCLEAR": 1, "PASS": 2}


def _line(ch: str = "-", n: int = 72) -> str:
    return ch * n


def _decided_label(row: Dict[str, Any]) -> str:
    key = row.get("decided_by") or row.get("verified_by") or "ai"
    return _DECIDED_LABEL.get(key, key)


def render_report(result: Dict[str, Any]) -> str:
    out: List[str] = []
    gv = result.get("generic_validation") or {}
    summary = gv.get("summary", {})
    rows: List[Dict[str, Any]] = gv.get("criteria_results", []) or []
    meta = gv.get("metadata", {})
    cost = result.get("cost") or (result.get("generic") or {}).get("cost") or {}

    # ---- header ----------------------------------------------------------
    out.append(_line("="))
    out.append("  TASK CHECK REPORT")
    out.append(_line("="))
    task_summary = gv.get("task_summary") or (result.get("check_spec") or {}).get("task_summary", "")
    if task_summary:
        out.append(f"What this task is: {task_summary}")
        out.append("")
    overall = summary.get("overall_status", "UNKNOWN")
    out.append(f"  OVERALL VERDICT : {_STATUS_ICON.get(overall, '')} {overall}")
    if "overall_confidence" in summary:
        out.append(f"  Confidence      : {round(summary['overall_confidence'] * 100)}%")
    out.append(f"  Engine mode     : {result.get('mode', '?')}"
               + (f" (specialization: {result['specialization']})" if result.get("specialization") else ""))
    if cost:
        out.append(f"  Cost            : ${cost.get('cost_usd', cost.get('total_usd', 0)):.4f}"
                   f"  ({cost.get('input_tokens', 0)} in / {cost.get('output_tokens', 0)} out tokens,"
                   f" {cost.get('calls', 0)} model calls)")
    out.append(f"  Criteria        : {summary.get('total', len(rows))} checked  |  "
               f"{summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, "
               f"{summary.get('unclear', 0)} need review")
    out.append("")

    # ---- how it was checked ---------------------------------------------
    by_method: Dict[str, int] = {}
    for r in rows:
        by_method[_decided_label(r)] = by_method.get(_decided_label(r), 0) + 1
    out.append(_line())
    out.append("  HOW EACH CRITERION WAS CHECKED")
    out.append(_line())
    for method, count in sorted(by_method.items(), key=lambda kv: -kv[1]):
        out.append(f"   - {count:>2} via {method}")
    out.append("")

    # ---- what the panel did ---------------------------------------------
    if meta.get("validator") == "panel":
        out.append(_line())
        out.append("  WHAT THE PANEL DID")
        out.append(_line())
        out.append(f"   Jurors      : {meta.get('jurors')} neutral reviewer(s)")
        models = meta.get("jury_models") or []
        if models:
            out.append(f"   Juror models: {', '.join(models)}")
        out.append(f"   Critic      : {'on (adversarial reviewer)' if meta.get('critic') else 'off'}")
        out.append(f"   Total voices: {meta.get('reviewers')} per criterion")
        out.append("   Rule        : a FAIL needs >=2 reviewers to agree; a lone dissent -> needs review")
        out.append(f"   Confidence  : blocking PASS below {round(meta.get('confidence_threshold', 0) * 100)}%"
                   f" is held back as 'needs review'")
        if meta.get("tiebreaks"):
            out.append(f"   Tie-breaks  : {meta['tiebreaks']} contested criterion(s) decided by the judge model")
        out.append("")

    # ---- per-criterion detail (FAIL, then UNCLEAR, then PASS) ------------
    out.append(_line())
    out.append("  CRITERION-BY-CRITERION")
    out.append(_line())
    for r in sorted(rows, key=lambda x: (_STATUS_ORDER.get(x.get("status"), 9), x.get("id", ""))):
        status = r.get("status", "?")
        out.append(f"{_STATUS_ICON.get(status, '[?]')} {r.get('id')}  ({_SEV_LABEL.get(r.get('severity'), r.get('severity'))})")
        out.append(f"      {r.get('statement', '')}")
        line = f"      checked by: {_decided_label(r)}"
        if r.get("confidence") is not None and r.get("decided_by", "").startswith("panel"):
            line += f"  |  confidence {round(r['confidence'] * 100)}%"
        if r.get("coverage") and r.get("coverage") != "full":
            line += f"  |  coverage: {r['coverage']}"
        out.append(line)
        if status != "PASS" and r.get("evidence"):
            out.append(f"      evidence  : {_truncate(str(r['evidence']), 300)}")
        if r.get("note"):
            out.append(f"      note      : {r['note']}")
        # show individual panel votes when present (a list of [role, verdict] pairs;
        # deterministic rows store a non-list marker, which we skip)
        votes = r.get("votes")
        if isinstance(votes, list):
            parts = []
            for item in votes:
                if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict):
                    role, v = item
                    parts.append(f"{role}:{v.get('status') or '?'}")
            if parts:
                out.append(f"      votes     : {', '.join(parts)}")
        out.append("")

    out.append(_line("="))
    out.append(f"  RESULT: {_STATUS_ICON.get(overall, '')} {overall}"
               + (f"  ({round(summary['overall_confidence'] * 100)}% confidence)"
                  if "overall_confidence" in summary else ""))
    out.append(_line("="))
    return "\n".join(out)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + " ..."
