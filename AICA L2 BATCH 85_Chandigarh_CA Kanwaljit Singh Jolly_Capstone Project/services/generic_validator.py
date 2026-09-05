"""
Generic AI Validator.

Verifies the actual output against a derived CheckSpec, criterion by criterion,
with cited evidence. This is the task-agnostic counterpart to the TDS-specific
Section 7 validator: it works for any task because it validates against the
derived criteria rather than hand-coded rules.

Deterministic criteria may already have authoritative results from
services/generic_checks.py; those are passed in and the AI is told to trust them
(it focuses on semantic/hybrid judgment and on anything still unresolved).

The LLM call is isolated in `_complete()` so tests can stub it, and it is routed
through services/llm_client so a juror/critic model may be OpenAI *or* Anthropic.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models.check_spec import CheckSpec, Criterion, CriterionSeverity
from services.generic_checks import _norm
from services.llm_client import complete as llm_complete

SYSTEM_PROMPT = (
    "You are a rigorous quality reviewer. You are given a checklist of criteria and "
    "the actual task input and output. For EACH criterion, decide PASS, FAIL, or "
    "UNCLEAR strictly from the evidence, and cite the specific evidence (real values, "
    "rows, or fields that appear in the data). Never mark PASS to be agreeable; never "
    "mark FAIL without concrete evidence you can point to in the data. If a criterion "
    "already has a deterministic result, return that same status. If the data is marked "
    "as a truncated SAMPLE, you may NOT mark PASS for any criterion that requires checking "
    "every record / full coverage / completeness — return UNCLEAR instead. "
    "Respond ONLY with valid JSON."
)

# Per-call read WINDOW in characters. By default this is AUTO-SIZED from the model's
# context window — you don't set it. AI_VALIDATION_CHAR_BUDGET is an optional override.
# It's a per-call cap, not a cost floor: you only pay for the data that actually exists,
# so a large window just means large inputs get read fully (in one or a few calls)
# instead of being sampled (which is what forced criteria to UNCLEAR before).
_BUDGET_ENV = os.getenv("AI_VALIDATION_CHAR_BUDGET")
_DEFAULT_BUDGET = int(_BUDGET_ENV) if (_BUDGET_ENV or "").strip().isdigit() else 24000


def _auto_char_budget(model: str) -> int:
    """Pick a read window from the model's context window (chars ~= tokens * 4)."""
    m = (model or "").lower()
    if "gemini" in m:
        ctx = 1_000_000
    elif "claude" in m:
        ctx = 200_000
    elif "gpt-4.1" in m or "gpt-5" in m or "o3" in m or "o4" in m:
        ctx = 400_000
    elif "gpt-4o" in m or "o1" in m or "gpt-4-turbo" in m:
        ctx = 128_000
    else:
        ctx = 32_000   # conservative default for unknown models
    # ~30% of context as the per-call window, capped so a single call stays sane.
    return min(int(ctx * 4 * 0.3), 400_000)


def _resolve_budget(model: str, explicit: Optional[int]) -> int:
    """Explicit arg wins; else the env override; else auto-size from the model."""
    if explicit is not None:
        return explicit
    if (_BUDGET_ENV or "").strip().isdigit():
        return int(_BUDGET_ENV)
    return _auto_char_budget(model)

_BLOCKING = {CriterionSeverity.CRITICAL, CriterionSeverity.ERROR}
_PROBLEM_WORDS = ("mismatch", "not found", "incorrect", "does not match",
                  "inconsistent", "is absent", "is wrong")
# Criteria that assert full coverage/completeness — unsafe to PASS on truncated data.
_COVERAGE_WORDS = ("every", "all ", "each", "complete", "entire", "no missing",
                   "none missing", "full coverage", "no records", "whole", "no input")


def _render_side(artifacts: List[Dict[str, Any]], label: str,
                 budget: int = _DEFAULT_BUDGET) -> Tuple[str, bool]:
    """
    Render input/output artifacts up to a character budget.

    Returns (text, truncated). `truncated` is True if any rows/text/artifacts were
    dropped — the caller then forbids full-coverage PASS verdicts on this data.
    """
    parts: List[str] = []
    used = 0
    truncated = False
    artifacts = artifacts or []

    for idx, art in enumerate(artifacts):
        header = f"### {label}: {art.get('file', 'unknown')} ({art.get('document_type', '')})"
        parts.append(header)
        used += len(header)

        for table in art.get("tables", []) or []:
            line = f"table '{table.get('name')}' columns {table.get('headers')}:"
            parts.append(line)
            used += len(line)
            rows = table.get("rows") or []
            for i, row in enumerate(rows):
                rowstr = f"  {row}"
                if used + len(rowstr) > budget:
                    parts.append(f"  ... [{len(rows) - i} more rows not shown]")
                    truncated = True
                    break
                parts.append(rowstr)
                used += len(rowstr)

        text = (art.get("text") or "").strip()
        if text and not art.get("tables"):
            if used + len(text) > budget:
                avail = max(0, budget - used)
                parts.append(text[:avail] + "\n... [truncated]")
                truncated = True
                used = budget
            else:
                parts.append(text)
                used += len(text)

        if used >= budget and idx < len(artifacts) - 1:
            parts.append(f"... [{len(artifacts) - idx - 1} more file(s) not shown]")
            truncated = True
            break

    return "\n".join(parts), truncated


def _side_size(artifacts: List[Dict[str, Any]]) -> int:
    """Approximate the rendered character size of a side (for chunking decisions)."""
    total = 0
    for art in artifacts or []:
        total += 60  # header
        for table in art.get("tables", []) or []:
            total += 60  # table header line
            for row in table.get("rows") or []:
                total += len(f"  {row}")
        total += len(art.get("text") or "")
    return total


def _chunk_side(artifacts: List[Dict[str, Any]], label: str,
                budget: int = _DEFAULT_BUDGET) -> List[str]:
    """
    Render a side into one OR MORE chunk strings, each within `budget`, such that
    EVERY row and all text is included across the chunks (no data dropped).

    This is what turns the budget from a hard cap into a per-call window: a large
    side becomes N chunks that are validated one-by-one and aggregated, so the model
    reads 100% of the content instead of a truncated sample.
    """
    chunks: List[str] = []
    cur: List[str] = []
    used = 0

    def flush():
        nonlocal cur, used
        if cur:
            chunks.append("\n".join(cur))
            cur, used = [], 0

    for art in artifacts or []:
        header = f"### {label}: {art.get('file', 'unknown')} ({art.get('document_type', '')})"
        if used + len(header) > budget:
            flush()
        cur.append(header)
        used += len(header)

        for table in art.get("tables", []) or []:
            line = f"table '{table.get('name')}' columns {table.get('headers')}:"
            if used + len(line) > budget and cur:
                flush()
            cur.append(line)
            used += len(line)
            for row in table.get("rows") or []:
                rowstr = f"  {row}"
                if used + len(rowstr) > budget and cur:
                    flush()
                    cur.append(f"{line} (cont.)")  # re-establish table context in the new chunk
                    used += len(line)
                cur.append(rowstr)
                used += len(rowstr)

        text = (art.get("text") or "").strip()
        if text and not art.get("tables"):
            start = 0
            while start < len(text):
                avail = max(1, budget - used)
                piece = text[start:start + avail]
                cur.append(piece)
                used += len(piece)
                start += len(piece)
                if start < len(text):
                    flush()

    flush()
    return chunks or [""]


def _is_coverage_criterion(c: Criterion) -> bool:
    text = f"{c.statement} {c.how_to_verify}".casefold()
    return any(w in text for w in _COVERAGE_WORDS)


def _cited_tokens(text: str) -> List[str]:
    """Extract concrete values an evidence string claims to have found in the data."""
    if not text:
        return []
    tokens = re.findall(r'-?\d[\d,]*\.?\d+|\b\d{2,}\b', text)          # numbers
    tokens += re.findall(r'"([^"]{2,60})"|\'([^\']{2,60})\'', text)    # quoted (tuples)
    tokens += re.findall(r'\b[A-Z0-9]{4,}\b', text)                    # identifiers/codes
    flat: List[str] = []
    for t in tokens:
        if isinstance(t, tuple):
            flat.extend(x for x in t if x)
        elif t:
            flat.append(t)
    return flat


def _build_data_index(normalized_data: Dict[str, Any]) -> Tuple[set, str]:
    """Index every cell value + a casefolded text blob, for grounding AI claims."""
    values: set = set()
    blob_parts: List[str] = []
    for side in ("normalized_inputs", "normalized_outputs"):
        for art in (normalized_data or {}).get(side, []):
            for table in art.get("tables", []) or []:
                for row in table.get("rows", []) or []:
                    for cell in row:
                        nv = _norm(cell)
                        if nv:
                            values.add(nv)
                            blob_parts.append(nv)
            text = art.get("text") or ""
            if text:
                blob_parts.append(text.casefold())
    return values, "\n".join(blob_parts)


def _is_grounded(token: str, values: set, blob: str) -> bool:
    nv = _norm(token)
    if nv and nv in values:
        return True
    return bool(token) and token.casefold() in blob


class GenericValidator:
    """Validate output against a CheckSpec using an LLM."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 temperature: float = 0.1, system_prompt: Optional[str] = None,
                 budget: Optional[int] = None):
        self.model = model or os.getenv("AI_VALIDATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        # Auto-sized from the model's context window unless explicitly overridden.
        self.budget = _resolve_budget(self.model, budget)

    # -- main entry --------------------------------------------------------

    def validate(
        self,
        check_spec: CheckSpec,
        normalized_data: Dict[str, Any],
        workflow_data: Optional[Dict[str, Any]] = None,
        deterministic_results: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not check_spec.criteria:
            return self._empty_result(check_spec, "No criteria were derived for this task.")

        det = deterministic_results or {}
        in_arts = normalized_data.get("normalized_inputs", [])
        out_arts = normalized_data.get("normalized_outputs", [])
        budget = self.budget

        # Decide how to read the data so that 100% is ALWAYS read — never sampled:
        #  - both sides fit   -> one full-read call
        #  - one side large   -> keep the smaller side whole, chunk the larger side,
        #                        one call per chunk (every row read)
        #  - both sides large -> CROSS-PRODUCT chunk: pair every input chunk with every
        #                        output chunk, so each part of both sides is read and
        #                        cross-referenced (100% coverage; more calls, no sampling)
        in_size, out_size = _side_size(in_arts), _side_size(out_arts)
        pairs: List[Tuple[str, str]] = []
        if in_size <= budget and out_size <= budget:
            in_text, _ = _render_side(in_arts, "INPUT", budget)
            out_text, _ = _render_side(out_arts, "OUTPUT", budget)
            pairs = [(in_text, out_text)]
        elif in_size <= budget:  # output is the big side
            in_text, _ = _render_side(in_arts, "INPUT", budget)
            pairs = [(in_text, oc) for oc in _chunk_side(out_arts, "OUTPUT", budget)]
        elif out_size <= budget:  # input is the big side
            out_text, _ = _render_side(out_arts, "OUTPUT", budget)
            pairs = [(ic, out_text) for ic in _chunk_side(in_arts, "INPUT", budget)]
        else:  # both sides large — cross-product so EVERY part of both is read (100%)
            in_chunks = _chunk_side(in_arts, "INPUT", budget)
            out_chunks = _chunk_side(out_arts, "OUTPUT", budget)
            pairs = [(ic, oc) for ic in in_chunks for oc in out_chunks]
        coverage = "full"   # we always read everything now; sampling is never used

        sampled = False
        per_chunk_ai: List[Dict[str, Dict[str, Any]]] = []
        for in_text, out_text in pairs:
            prompt = self._build_prompt(check_spec, in_text, out_text, sampled, det)
            try:
                data = json.loads(self._complete(prompt))
            except (json.JSONDecodeError, TypeError):
                data = {"criteria_results": []}
            by_id = {}
            for r in data.get("criteria_results") or data.get("results") or []:
                if isinstance(r, dict) and r.get("id"):
                    by_id[str(r["id"])] = r
            per_chunk_ai.append(by_id)

        data_index = _build_data_index(normalized_data)
        return self._post_process(per_chunk_ai, check_spec, det, coverage, len(pairs), data_index)

    # -- overridable LLM seam (stubbed in tests) ---------------------------

    def _complete(self, prompt: str) -> str:
        return llm_complete(
            model=self.model,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
            api_key=self.api_key,
            json_mode=True,
        )

    # -- prompt ------------------------------------------------------------

    def _build_prompt(self, check_spec, inputs_text, outputs_text, truncated, deterministic_results) -> str:
        criteria_lines = []
        for c in check_spec.criteria:
            known = deterministic_results.get(c.id)
            known_str = f"  [DETERMINISTIC RESULT ALREADY KNOWN: {known.get('status')} — {known.get('detail', '')}]" if known else ""
            criteria_lines.append(
                f"- {c.id} ({c.type.value}, {c.severity.value}): {c.statement}"
                + (f"\n    how_to_verify: {c.how_to_verify}" if c.how_to_verify else "")
                + (f"\n{known_str}" if known_str else "")
            )
        criteria_block = "\n".join(criteria_lines)

        trunc_banner = ""
        if truncated:
            trunc_banner = (
                "\n⚠️ NOTE: the INPUT/OUTPUT below is a TRUNCATED SAMPLE (not all rows/files shown). "
                "Do NOT mark PASS for any criterion that requires checking every record or full "
                "coverage/completeness — return UNCLEAR for those.\n"
            )

        return f"""TASK: {check_spec.task_summary or '(no summary)'}
{trunc_banner}
## CRITERIA TO VERIFY
{criteria_block}

## ACTUAL INPUT
{inputs_text}

## ACTUAL OUTPUT
{outputs_text}

For every criterion above, return JSON in EXACTLY this shape:
{{
  "criteria_results": [
    {{
      "id": "C1",
      "status": "PASS | FAIL | UNCLEAR",
      "evidence": "specific evidence from the input/output (cite real values, rows, fields)",
      "explanation": "one sentence why"
    }}
  ]
}}
Rules:
- Decide each criterion only from the evidence shown.
- If a deterministic result is already known for a criterion, return that same status.
- Cite concrete values that actually appear in the data; do not invent values.
- Use UNCLEAR when the evidence is insufficient (including truncated data for coverage criteria).
"""

    # -- post-processing ---------------------------------------------------

    def _clean_one(self, ai: Dict[str, Any], values: set, blob: str) -> Tuple[str, str, str, str]:
        """Clean a single AI verdict: anti-rubber-stamp + grounding gate.

        Returns (status, evidence, explanation, note). Coverage/truncation honesty
        is applied at the aggregation level (it depends on read mode), not here.
        """
        status = str(ai.get("status", "UNCLEAR")).upper()
        evidence = str(ai.get("evidence", "")).strip()
        explanation = str(ai.get("explanation", "")).strip()
        note = ""
        if status not in ("PASS", "FAIL", "UNCLEAR"):
            status = "UNCLEAR"

        if status == "PASS" and any(w in (evidence + " " + explanation).lower() for w in _PROBLEM_WORDS):
            status, note = "UNCLEAR", "PASS cited a problem"

        if status == "FAIL":
            cited = _cited_tokens(evidence + " " + explanation)
            if cited and not any(_is_grounded(t, values, blob) for t in cited):
                status, note = "UNCLEAR", "FAIL evidence not found in data (ungrounded)"

        return status, evidence, explanation, note

    def _post_process(self, per_chunk_ai, check_spec, deterministic_results,
                      coverage, n_chunks, data_index) -> Dict[str, Any]:
        values, blob = data_index
        chunked = n_chunks > 1
        sampled = coverage == "sampled"
        ungrounded_removed = 0
        truncation_downgrades = 0

        results: List[Dict[str, Any]] = []
        for c in check_spec.criteria:
            det = deterministic_results.get(c.id)

            if det:  # deterministic result (full data) is always authoritative
                results.append(self._row(
                    c, str(det.get("status", "UNCLEAR")).upper(),
                    det.get("detail", ""), det.get("detail", ""),
                    "deterministic", "full", ""))
                continue

            # gather this criterion's (cleaned) verdict from every chunk
            verdicts = [self._clean_one(chunk.get(c.id, {}), values, blob) for chunk in per_chunk_ai]
            ungrounded_removed += sum(1 for v in verdicts if v[3].startswith("FAIL evidence not found"))

            if sampled:
                # single sampled read: forbid coverage PASS (we did not see all data)
                status, evidence, explanation, note = verdicts[0] if verdicts else ("UNCLEAR", "", "", "")
                if status == "PASS" and _is_coverage_criterion(c):
                    status, note = "UNCLEAR", "coverage criterion on sampled data"
                    truncation_downgrades += 1
                verified_by = "ai_sampled"
            elif chunked and _is_coverage_criterion(c):
                # A grounded defect found in ANY chunk is a real defect -> FAIL.
                # But "all chunks passed" does NOT prove a global coverage/completeness
                # claim (a chunk can't see the whole), so absence-of-defect -> UNCLEAR,
                # to be confirmed by the deterministic check or a human.
                fails = [v for v in verdicts if v[0] == "FAIL"]
                if fails:
                    status, evidence, explanation, note = "FAIL", fails[0][1], fails[0][2], fails[0][3]
                    verified_by = "ai_full_read"
                else:
                    ev = next((v[1] for v in verdicts if v[1]), "")
                    status, evidence, explanation = "UNCLEAR", ev, ev
                    note = "coverage criterion needs deterministic verification (read in chunks)"
                    verified_by = "ai_chunked"
            else:
                # local criterion: aggregate across chunks (a grounded FAIL anywhere wins;
                # PASS only if every chunk passed; otherwise UNCLEAR)
                status, evidence, explanation, note = self._aggregate(verdicts)
                verified_by = "ai_full_read"

            results.append(self._row(c, status, evidence, explanation, verified_by, coverage, note))

        summary = self._summarize(check_spec, results)
        summary["metadata"]["coverage"] = coverage
        summary["metadata"]["read_chunks"] = n_chunks
        summary["metadata"]["truncated"] = sampled
        summary["metadata"]["ungrounded_failures_removed"] = ungrounded_removed
        summary["metadata"]["truncation_downgrades"] = truncation_downgrades
        summary["metadata"]["fully_verified"] = sum(
            1 for r in results if r["coverage"] == "full" and r["status"] in ("PASS", "FAIL"))
        return summary

    def _aggregate(self, verdicts) -> Tuple[str, str, str, str]:
        if not verdicts:
            return "UNCLEAR", "", "", ""
        fails = [v for v in verdicts if v[0] == "FAIL"]
        if fails:
            return ("FAIL", fails[0][1], fails[0][2], fails[0][3])
        if all(v[0] == "PASS" for v in verdicts):
            return ("PASS", verdicts[0][1], verdicts[0][2], "")
        unclear = next((v for v in verdicts if v[0] == "UNCLEAR"), verdicts[0])
        return ("UNCLEAR", unclear[1], unclear[2], unclear[3])

    def _row(self, c, status, evidence, explanation, verified_by, coverage, note) -> Dict[str, Any]:
        return {
            "id": c.id,
            "statement": c.statement,
            "type": c.type.value,
            "severity": c.severity.value,
            "source": c.source.value,
            "status": status,
            "evidence": evidence,
            "explanation": explanation,
            "decided_by": "deterministic" if verified_by == "deterministic" else "ai",
            "verified_by": verified_by,
            "coverage": coverage,
            "note": note,
        }

    def _summarize(self, check_spec, results) -> Dict[str, Any]:
        sev_by_id = {c.id: c.severity for c in check_spec.criteria}
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        unclear = sum(1 for r in results if r["status"] == "UNCLEAR")
        blocking_fail = any(r["status"] == "FAIL" and sev_by_id.get(r["id"]) in _BLOCKING for r in results)
        blocking_unclear = any(r["status"] == "UNCLEAR" and sev_by_id.get(r["id"]) in _BLOCKING for r in results)

        if blocking_fail:
            overall = "FAIL"
        elif failed:
            overall = "WARN"
        elif blocking_unclear:
            overall = "INDETERMINATE"
        else:
            overall = "PASS"

        return {
            "task_summary": check_spec.task_summary,
            "criteria_results": results,
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "unclear": unclear,
                "overall_status": overall,
            },
            "metadata": {
                "model": self.model,
                "validator": "generic",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    def _empty_result(self, check_spec, message) -> Dict[str, Any]:
        return {
            "task_summary": check_spec.task_summary,
            "criteria_results": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "unclear": 0,
                        "overall_status": "INDETERMINATE"},
            "metadata": {"model": self.model, "validator": "generic", "note": message,
                         "timestamp": datetime.utcnow().isoformat()},
        }
