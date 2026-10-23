"""Reviewer: casting and tie-outs, Schedule III ratios, disclosure checklist, and an AI analytical review.

run_review() always does the deterministic work. Pass an `llm` (see llm.GeminiLLM) to add the
AI-drafted ratio explanations and observations; without one they are marked as not run.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..model import Model
from .ai import AIResult, Facts, analytical_review, build_facts, explain_ratios
from .checklist import Item, evaluate_checklist
from .ratios import Ratio, compute_ratios
from .tieouts import Check, run_tieouts


@dataclass
class Review:
    company: str
    as_at: object
    tieouts: list
    ratios: list
    checklist: list
    ai: AIResult
    facts: Facts
    ai_requested: bool

    @property
    def summary(self) -> dict:
        t = Counter(c.status for c in self.tieouts)
        s = Counter(i.status for i in self.checklist)
        return {"checks": len(self.tieouts), "passed": t["Pass"], "failed": t["Fail"],
                "ratios_flagged": sum(r.flagged for r in self.ratios),
                "ratios_unmeasured": sum(1 for r in self.ratios if r.prev is None),
                "checklist": dict(s), "ai_observations": len(self.ai.observations),
                "ai_ungrounded": sum(1 for o in self.ai.observations if not o.grounded)}


def run_review(m: Model, mapped=None, llm=None) -> Review:
    mapped = m.mapping if mapped is None else mapped
    tie = run_tieouts(m, mapped)
    ratios = compute_ratios(m)
    facts = build_facts(m, ratios)
    result = AIResult()
    explain_ratios(llm, ratios, facts, result)
    items = evaluate_checklist(m, tie)
    already = [f"{f.ref}: {f.area}. {f.text}" for f in m.flags] + [
        f"{i.id}: {i.requirement}. {i.evidence}" for i in items if i.status == "Observation"]
    analytical_review(llm, m, facts, already, result)
    return Review(m.company, m.as_at, tie, ratios, items, result, facts, llm is not None)
