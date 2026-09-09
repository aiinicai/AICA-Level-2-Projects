"""
CheckSpec — the derived specification of what "correct" means for a task.

The criteria engine (services/criteria_engine.py) reads the agent's materials
(description/prompt, workflow, reference examples, KB, client context) and emits a
CheckSpec: a list of typed, sourced Criterion objects. Sections 6 (deterministic)
and 7 (AI) then verify the actual output against these criteria.

This is task-agnostic: the same model describes checks for tax forms, invoices,
reports, or anything else.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CriterionType(Enum):
    """How a criterion is best verified."""
    DETERMINISTIC = "deterministic"  # exact/structural (counts, totals, coverage, format)
    SEMANTIC = "semantic"            # requires judgment (tone, completeness, correctness of prose)
    HYBRID = "hybrid"                # both (value correctness that also needs interpretation)


class CriterionSeverity(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CriterionSource(Enum):
    """Origin of a criterion, ordered by authority (lower number = higher priority)."""
    KB = "kb"                  # 1 - domain knowledge / regulations
    CLIENT = "client"          # 2 - client-specific policy
    WORKFLOW = "workflow"      # 3 - the task's workflow steps
    DESCRIPTION = "description"  # 4 - agent description / specialization prompt
    REFERENCE = "reference"    # 5 - inferred from example files
    INFERRED = "inferred"      # 6 - general best-effort inference

    @property
    def priority(self) -> int:
        order = {
            "kb": 1, "client": 2, "workflow": 3,
            "description": 4, "reference": 5, "inferred": 6,
        }
        return order[self.value]


def _coerce_enum(enum_cls, value, default):
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value).strip().lower())
    except (ValueError, AttributeError):
        return default


@dataclass
class Criterion:
    """A single verifiable requirement the output must satisfy."""
    id: str
    statement: str
    type: CriterionType = CriterionType.SEMANTIC
    severity: CriterionSeverity = CriterionSeverity.ERROR
    source: CriterionSource = CriterionSource.INFERRED
    how_to_verify: str = ""
    evidence_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type.value,
            "severity": self.severity.value,
            "source": self.source.value,
            "how_to_verify": self.how_to_verify,
            "evidence_hint": self.evidence_hint,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], index: int = 0) -> "Criterion":
        return cls(
            id=str(d.get("id") or f"C{index + 1}"),
            statement=str(d.get("statement") or d.get("requirement") or "").strip(),
            type=_coerce_enum(CriterionType, d.get("type"), CriterionType.SEMANTIC),
            severity=_coerce_enum(CriterionSeverity, d.get("severity"), CriterionSeverity.ERROR),
            source=_coerce_enum(CriterionSource, d.get("source"), CriterionSource.INFERRED),
            how_to_verify=str(d.get("how_to_verify") or "").strip(),
            evidence_hint=str(d.get("evidence_hint") or "").strip(),
        )


@dataclass
class CheckSpec:
    """The full derived specification for a task."""
    task_summary: str = ""
    criteria: List[Criterion] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def deterministic_criteria(self) -> List[Criterion]:
        return [c for c in self.criteria if c.type in (CriterionType.DETERMINISTIC, CriterionType.HYBRID)]

    @property
    def semantic_criteria(self) -> List[Criterion]:
        return [c for c in self.criteria if c.type in (CriterionType.SEMANTIC, CriterionType.HYBRID)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_summary": self.task_summary,
            "criteria": [c.to_dict() for c in self.criteria],
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_ai_dict(cls, d: Dict[str, Any]) -> "CheckSpec":
        raw = d.get("criteria") or d.get("requirements") or []
        criteria = [Criterion.from_dict(c, i) for i, c in enumerate(raw) if isinstance(c, dict)]
        # Drop empty statements
        criteria = [c for c in criteria if c.statement]
        return cls(
            task_summary=str(d.get("task_summary") or d.get("summary") or "").strip(),
            criteria=criteria,
            notes=[str(n) for n in (d.get("notes") or []) if n],
            metadata=d.get("metadata") or {},
        )
