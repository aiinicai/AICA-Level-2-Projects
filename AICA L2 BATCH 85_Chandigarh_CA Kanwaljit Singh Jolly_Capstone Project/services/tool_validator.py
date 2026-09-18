"""
Tool-calling validator (optional, env-gated by AI_TOOL_LOOP_ENABLED).

Instead of rendering the data into the prompt, this validator gives the model the
full-data TOOLS from services/tools.py and lets it CALL them. The model reads the
criteria + a cheap table overview, calls tools (reconcile/lookup/count/…) that run
over 100% of the data, reasons over the small results, and emits per-criterion
verdicts. Coverage is complete and token cost stays flat as files grow, because the
raw rows never enter the prompt — only tiny tool results do.

Deterministic results (services/generic_checks.py) remain the authoritative floor;
the verdict cleaning (grounding gate, anti-rubber-stamp) and output shape are reused
from GenericValidator so this drops into the pipeline interchangeably.

The single LLM seam is `_chat()` (one tool-calling step), stubbed in tests.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from models.check_spec import CheckSpec
from services import tools as toolkit
from services.generic_validator import GenericValidator, _build_data_index
from services.llm_client import complete_with_tools

logger = logging.getLogger(__name__)

TOOL_SYSTEM_PROMPT = (
    "You are a rigorous quality reviewer with TOOLS that query the full task data. "
    "For each criterion, DECIDE how to verify it: if a tool fits (reconcile() for "
    "input→output coverage/value checks; lookup()/count_rows()/aggregate()/search_text() "
    "for specifics), CALL it and judge from the result. If NO tool fits (a wording/quality/"
    "semantic judgment), use get_rows()/search_text() to READ the relevant content, then "
    "judge it directly. Use list_tables() first to see what exists. Cite concrete values "
    "the tools returned; never invent values. When you have enough evidence, STOP calling "
    "tools and reply with ONLY the final JSON verdict (no tool call). Mark a criterion FAIL "
    "only with grounded evidence, PASS only when confirmed, else UNCLEAR."
)


def agentic_validation_enabled() -> bool:
    """Agentic (tool-using) validation is the DEFAULT; set AI_TOOL_LOOP_ENABLED=false
    to force the plain chunked validator instead."""
    return os.getenv("AI_TOOL_LOOP_ENABLED", "true").strip().lower() == "true"


class ToolCallingValidator:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 temperature: float = 0.0, max_iters: Optional[int] = None):
        self.model = (model or os.getenv("AI_TOOL_LOOP_MODEL")
                      or os.getenv("AI_VALIDATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini"))
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        try:
            self.max_iters = max_iters if max_iters is not None else int(os.getenv("AI_TOOL_LOOP_MAX_ITERS", "6"))
        except ValueError:
            self.max_iters = 6

    # -- LLM seam (one tool-calling step) ---------------------------------

    def _chat(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        return complete_with_tools(
            model=self.model, system_prompt=TOOL_SYSTEM_PROMPT, messages=messages,
            tools=toolkit.TOOL_SCHEMAS, temperature=self.temperature, api_key=self.api_key)

    # -- main entry --------------------------------------------------------

    def validate(self, check_spec: CheckSpec, normalized_data: Dict[str, Any],
                 workflow_data: Optional[Dict[str, Any]] = None,
                 deterministic_results: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        det = deterministic_results or {}
        gv = GenericValidator(model=self.model, api_key=self.api_key)  # reused for cleaning/shape
        if not check_spec.criteria:
            return gv._empty_result(check_spec, "No criteria were derived for this task.")

        overview = toolkit.dispatch("list_tables", {}, normalized_data)
        messages: List[Dict[str, Any]] = [{"role": "user", "content": self._build_prompt(check_spec, overview, det)}]

        final_content = None
        for _ in range(self.max_iters):
            resp = self._chat(messages)
            calls = resp.get("tool_calls") or []
            if calls:
                messages.append(self._assistant_msg(resp.get("content"), calls))
                for call in calls:
                    result = toolkit.dispatch(call["name"], call.get("arguments", {}), normalized_data)
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(result)[:4000]})
                continue
            final_content = resp.get("content")
            break
        else:
            # ran out of iterations still calling tools — ask once for the final verdict
            messages.append({"role": "user", "content": "Stop calling tools. Reply now with ONLY the final JSON verdict."})
            try:
                final_content = (self._chat(messages) or {}).get("content")
            except Exception as e:  # noqa: BLE001
                logger.warning("Tool-loop final step failed: %s", e)

        ai_by_id = self._parse(final_content)
        values, blob = _build_data_index(normalized_data)
        result = gv._post_process([ai_by_id], check_spec, det, "full", 1, (values, blob))
        # relabel AI-decided rows so the report shows tools were used
        for row in result["criteria_results"]:
            if row.get("verified_by") == "ai_full_read":
                row["verified_by"] = "ai_tools"
        result["metadata"]["validator"] = "tool_loop"
        result["metadata"]["model"] = self.model
        return result

    # -- helpers -----------------------------------------------------------

    def _assistant_msg(self, content, calls) -> Dict[str, Any]:
        return {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"], "arguments": json.dumps(c.get("arguments", {}))}}
                for c in calls
            ],
        }

    def _parse(self, content) -> Dict[str, Dict[str, Any]]:
        if not content:
            return {}
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # tolerate prose around the JSON object
            start, end = content.find("{"), content.rfind("}")
            if start == -1 or end == -1:
                return {}
            try:
                data = json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                return {}
        by_id = {}
        for r in data.get("criteria_results") or data.get("results") or []:
            if isinstance(r, dict) and r.get("id"):
                by_id[str(r["id"])] = r
        return by_id

    def _build_prompt(self, check_spec, overview, det) -> str:
        lines = []
        for c in check_spec.criteria:
            known = det.get(c.id)
            suffix = f"  [DETERMINISTIC RESULT KNOWN: {known.get('status')} — {known.get('detail', '')}]" if known else ""
            lines.append(f"- {c.id} ({c.type.value}, {c.severity.value}): {c.statement}"
                         + (f"  how_to_verify: {c.how_to_verify}" if c.how_to_verify else "") + suffix)
        return f"""TASK: {check_spec.task_summary or '(no summary)'}

## TABLES AVAILABLE (call tools to inspect their data)
{json.dumps(overview, default=str)}

## CRITERIA TO VERIFY
{chr(10).join(lines)}

For each criterion: call a tool if one fits, or read the relevant content with
get_rows()/search_text() if it's a semantic judgment. Then reply with ONLY this JSON:
{{"criteria_results": [{{"id": "C1", "status": "PASS | FAIL | UNCLEAR",
  "evidence": "concrete values the tools returned", "explanation": "one sentence"}}]}}
- If a deterministic result is already known for a criterion, return that same status.
- Cite only values the tools actually returned; do not invent values.
"""
