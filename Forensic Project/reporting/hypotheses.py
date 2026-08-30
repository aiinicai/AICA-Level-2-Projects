"""
Hypothesis generator and working paper register formatter.
"""
import string
from typing import Dict, List, Any

import pandas as pd

UNRESOLVED = "\u2014"  # em dash, shown where a template asks for a value the rule did not capture


class _SafeContext(dict):
    """
    Formatting context that never raises on a missing placeholder and records
    which names could not be resolved, so the caller can decide whether to
    append the rule's factual detail line.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing = set()

    def __missing__(self, key):
        self.missing.add(key)
        return UNRESOLVED


def _hypothesis_context(row) -> _SafeContext:
    """
    Build the substitution context for a hypothesis template.

    Resolution order:
      1. an explicit `context` dict attached by the rule function,
      2. the exception row's own columns,
      3. documented aliases for the names the YAML templates use,
      4. an em dash for anything the rule did not capture.

    Aliases are only declared where the exception row genuinely carries that
    value. `turnover_total`, for example, is deliberately NOT aliased to
    `observed_value` — for TB-07 the observed value is the closing balance, and
    the old alias produced the false statement "turnover of 0.0".
    """
    ctx = _SafeContext()

    try:
        items = row.items()
    except AttributeError:
        items = dict(row).items()
    for k, v in items:
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            ctx[k] = v

    extra = row.get("context") if hasattr(row, "get") else None
    if isinstance(extra, dict):
        ctx.update({k: v for k, v in extra.items() if v is not None})

    subject = row.get("subject", UNRESOLVED)
    observed = row.get("observed_value", UNRESOLVED)

    for alias, value in (
        ("ledger_name", subject),
        ("group", subject),
        ("fy", row.get("fy_span") or row.get("fy", UNRESOLVED)),
        ("closing_net", observed),
        ("balance_curr", observed),
        ("ratio_pct", observed),
    ):
        if alias not in ctx or ctx.get(alias) in (None, ""):
            ctx[alias] = value

    return ctx


def build_hypothesis_text(row) -> str:
    """
    Render a rule's hypothesis template against an exception row.

    Templates are authored in the rule YAML and reference values the rule
    computed. Where a value was not captured the placeholder resolves to an em
    dash rather than leaving a literal `{placeholder}` on screen, and the rule's
    factual detail line is appended so no figure is lost.
    """
    hyp_tmpl = str(row.get("hypothesis", "") or "").strip()
    detail = str(row.get("detail", "") or "").strip()

    if not hyp_tmpl or hyp_tmpl.lower() == "nan":
        return (f"Rule {row.get('rule_id')} exception on {row.get('subject')} "
                f"in {row.get('fy_span') or row.get('fy')}: {detail}")

    ctx = _hypothesis_context(row)
    try:
        text = string.Formatter().vformat(hyp_tmpl, (), ctx)
    except (IndexError, ValueError):
        # Positional '{}' or malformed braces in a template — render it literally.
        text = hyp_tmpl

    if detail and ctx.missing:
        text = f"{text} Observed: {detail}."
    return text


def build_hypothesis_register(exceptions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Hypothesis Register DataFrame with audit testing tracking columns
    (Proved, Disproved, Not Proved, Auditor Notes).
    """
    if exceptions_df.empty:
        return pd.DataFrame(columns=[
            "Rule ID", "Financial Year", "Subject / Ledger", "Flag",
            "Hypothesis", "Suggested Procedure", "Proved", "Disproved", "Not Proved", "Auditor Notes"
        ])
        
    rows = []
    for idx, r in exceptions_df.iterrows():
        proc = r.get("procedure", [])
        proc_str = "\n".join([f"• {p}" for p in proc]) if isinstance(proc, list) else str(proc)
        hyp = build_hypothesis_text(r)
        
        rows.append({
            "Rule ID": r.get("rule_id"),
            "Financial Year": r.get("fy"),
            "Subject / Ledger": r.get("subject"),
            "Flag": str(r.get("flag", "")).upper(),
            "Hypothesis": hyp,
            "Suggested Procedure": proc_str,
            "Proved": "",
            "Disproved": "",
            "Not Proved": "",
            "Auditor Notes": ""
        })
        
    return pd.DataFrame(rows)
