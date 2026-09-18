"""
Criteria Derivation Engine.

Reads an agent's materials — task description / specialization prompt, the workflow,
the structure of the actual input/output files, reference example files, KB, and
client context — and derives a CheckSpec: a precise, typed checklist of what a
correct output must satisfy. This is the task-agnostic replacement for hand-coded,
per-task rules; the actual verification happens in Sections 6 (deterministic) and
7 (AI) against this spec.

The LLM call is isolated in `_complete()` so tests can stub it, and routed through
services/llm_client so AI_DERIVATION_MODEL may name an OpenAI or Anthropic model.
"""

import json
import os
from typing import Any, Dict, List, Optional

from models.check_spec import CheckSpec
from services.llm_client import complete as llm_complete

SYSTEM_PROMPT = (
    "You are a meticulous quality-assurance lead. Given a task's description, its "
    "workflow, the structure of the input and output files, reference examples, and "
    "any domain knowledge, you produce a precise, exhaustive checklist of verifiable "
    "criteria that the OUTPUT must satisfy to be considered correct. "
    "Prefer concrete, checkable statements over vague ones. Do not invent requirements "
    "that are not supported by the materials. Respond ONLY with valid JSON."
)


def _truncate(text: str, limit: int = 6000) -> str:
    if not text:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


class CriteriaEngine:
    """Derive a CheckSpec from task materials using an LLM."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 temperature: float = 0.1):
        self.model = model or os.getenv("AI_DERIVATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature

    # -- main entry --------------------------------------------------------

    def derive(
        self,
        *,
        task_description: str = "",
        workflow_text: str = "",
        input_summary: str = "",
        output_summary: str = "",
        reference_materials: str = "",
        kb_materials: str = "",
        client_materials: str = "",
    ) -> CheckSpec:
        prompt = self._build_prompt(
            task_description=task_description,
            workflow_text=workflow_text,
            input_summary=input_summary,
            output_summary=output_summary,
            reference_materials=reference_materials,
            kb_materials=kb_materials,
            client_materials=client_materials,
        )
        raw = self._complete(prompt)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            data = {"criteria": []}
        spec = CheckSpec.from_ai_dict(data)
        spec.metadata.setdefault("model", self.model)
        spec.metadata.setdefault("criteria_count", len(spec.criteria))
        return spec

    # -- overridable LLM seam (stubbed in tests) ---------------------------

    def _complete(self, prompt: str) -> str:
        return llm_complete(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.temperature,
            api_key=self.api_key,
            json_mode=True,
        )

    # -- prompt ------------------------------------------------------------

    def _build_prompt(self, **m: str) -> str:
        sections = [
            ("TASK DESCRIPTION / WHAT TO CHECK", m.get("task_description", "")),
            ("WORKFLOW (declared steps)", m.get("workflow_text", "")),
            ("INPUT FILES (structure & sample)", m.get("input_summary", "")),
            ("OUTPUT FILES (structure & sample)", m.get("output_summary", "")),
            ("REFERENCE EXAMPLES (what good looks like)", m.get("reference_materials", "")),
            ("DOMAIN KNOWLEDGE (KB)", m.get("kb_materials", "")),
            ("CLIENT CONTEXT / POLICIES", m.get("client_materials", "")),
        ]
        body = "\n\n".join(
            f"## {title}\n{_truncate(content)}" for title, content in sections if content and content.strip()
        )
        if not body.strip():
            body = "(No materials were provided.)"

        return f"""Derive the checklist of criteria a correct OUTPUT must satisfy for this task.

{body}

Produce JSON in EXACTLY this shape:
{{
  "task_summary": "one or two sentences describing what this task is and what a correct output means",
  "criteria": [
    {{
      "id": "C1",
      "statement": "a single, concrete, verifiable requirement the output must meet",
      "type": "deterministic | semantic | hybrid",
      "severity": "critical | error | warning | info",
      "source": "kb | client | workflow | description | reference | inferred",
      "how_to_verify": "how a checker should verify this (e.g. compare input id column to output id column)",
      "evidence_hint": "where to look (file/sheet/field)"
    }}
  ],
  "notes": ["any caveats or assumptions"]
}}

Guidance:
- "deterministic": exact/structural and checkable without judgment — counts, totals, coverage (every input record present in output), required fields non-empty, value/format equality, regex/format conformance.
- "semantic": needs judgment — phrasing, completeness, correctness of explanation.
- "hybrid": value correctness that also needs interpretation.
- Mark coverage/completeness and value-equality requirements as "deterministic" so they can be machine-checked.
- Be comprehensive but do not duplicate the same requirement in different words.
- Prefer requirements grounded in the workflow and reference examples over generic ones.
"""


# ==================== material assembly from pipeline data ====================

def _summarize_artifacts(artifacts: List[Dict[str, Any]], max_rows: int = 8) -> str:
    """Render normalized artifacts (uniform text/tables view) into a compact summary."""
    parts: List[str] = []
    for art in artifacts or []:
        name = art.get("file", "unknown")
        dtype = art.get("document_type", "")
        parts.append(f"- {name} ({dtype})")
        for table in art.get("tables", []) or []:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            parts.append(f"  table '{table.get('name')}' columns: {headers}; {len(rows)} rows")
            for row in rows[:max_rows]:
                parts.append(f"    {row}")
        text = (art.get("text") or "").strip()
        if text and not art.get("tables"):
            parts.append("  text: " + _truncate(text, 1200).replace("\n", " "))
    return "\n".join(parts)


def gather_pipeline_materials(
    normalized_data: Dict[str, Any],
    workflow_data: Dict[str, Any],
    task_description: str = "",
    client_context_texts: Optional[List[str]] = None,
    kb_texts: Optional[List[str]] = None,
    reference_texts: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Assemble the material strings the CriteriaEngine.derive() expects."""
    workflow_text_parts: List[str] = []
    for wf in (workflow_data or {}).get("declared_workflows", []):
        src = wf.get("workflow_file") or wf.get("source_file") or "workflow"
        workflow_text_parts.append(f"# {src}")
        for step in wf.get("steps", []):
            num = step.get("step_number") or step.get("sequence") or ""
            heading = step.get("heading") or step.get("title") or ""
            raw = step.get("raw_text") or step.get("description") or ""
            workflow_text_parts.append(f"{num}. {heading} {raw}".strip())

    return {
        "task_description": task_description or "",
        "workflow_text": "\n".join(workflow_text_parts),
        "input_summary": _summarize_artifacts((normalized_data or {}).get("normalized_inputs", [])),
        "output_summary": _summarize_artifacts((normalized_data or {}).get("normalized_outputs", [])),
        "reference_materials": "\n\n".join(reference_texts or []),
        "kb_materials": "\n\n".join(kb_texts or []),
        "client_materials": "\n\n".join(client_context_texts or []),
    }


def derive_check_spec(
    normalized_data: Dict[str, Any],
    workflow_data: Dict[str, Any],
    task_description: str = "",
    client_context_texts: Optional[List[str]] = None,
    kb_texts: Optional[List[str]] = None,
    reference_texts: Optional[List[str]] = None,
    engine: Optional[CriteriaEngine] = None,
) -> CheckSpec:
    """Convenience: assemble materials from pipeline data and derive a CheckSpec."""
    engine = engine or CriteriaEngine()
    materials = gather_pipeline_materials(
        normalized_data, workflow_data, task_description,
        client_context_texts, kb_texts, reference_texts,
    )
    return engine.derive(**materials)
