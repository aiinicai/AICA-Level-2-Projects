"""
Loads and validates the DPDP control catalogue.

The catalogue lives in rules/*.yaml, one file per DPDP Rule. This module reads
every file, enforces the schema documented in rules/_SCHEMA.md, and exposes the
controls that apply to a given client profile.

Nothing in this module touches client data. It deals only with the rule set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

# Status a control can be assessed at, and the score factor each carries.
STATUS_FACTORS: dict[str, float] = {
    "Present": 1.0,
    "Partial": 0.5,
    "Absent": 0.0,
}

# Controls at or above this weight score zero without an attached evidence file.
# This is the evidence gate: self-declaration alone never earns marks.
EVIDENCE_GATE_WEIGHT = 4

VALID_SEVERITY = {"low", "medium", "high", "critical"}
VALID_ROLES = {"fiduciary", "processor"}

# Whether a control's legal citation has been checked. "verified" means it was
# checked against the gazette text; "pending" means it was not, and the ledger and
# report say so. The Act and the Rules have pending notifications, so a citation
# nobody has checked must never read as authoritative.
VALID_CITATION_STATUS = ("verified", "pending")

# Rule groups are ordered by the digits after the letter in app.py, report.py and
# ui/js/dom.js, so a malformed rule_id must fail here at startup rather than as a
# 500 from a numeric sort later.
RULE_ID_RE = re.compile(r"[A-Z][0-9]+")

Status = Literal["Present", "Partial", "Absent"]


@dataclass(frozen=True)
class Control:
    """A single assessable control, loaded from YAML."""

    id: str
    rule_id: str
    rule_ref: str
    rule_title: str
    title: str
    question: str
    guidance: str
    evidence_required: list[str]
    weight: int
    severity_if_absent: str
    roles: list[str]
    condition: str | None
    observation: str
    impact: str
    action: str
    # Defaults to pending so a Control built outside the loader never claims a
    # checked citation.
    citation_status: str = "pending"

    @property
    def needs_evidence(self) -> bool:
        """True when this control cannot be scored on self-declaration alone."""
        return self.weight >= EVIDENCE_GATE_WEIGHT


class CatalogueError(ValueError):
    """Raised when a rule file breaks the schema. Fail loudly at startup."""


def _require(block: dict, key: str, where: str):
    if key not in block or block[key] in (None, "", []):
        raise CatalogueError(f"{where}: missing required key '{key}'")
    return block[key]


def _parse_control(raw: dict, rule_id: str, rule_ref: str, rule_title: str,
                   file_citation: str) -> Control:
    """Turn one YAML control block into a validated Control."""
    cid = _require(raw, "id", f"{rule_id} control")
    where = f"control {cid}"

    weight = _require(raw, "weight", where)
    if not isinstance(weight, int) or not 1 <= weight <= 5:
        raise CatalogueError(f"{where}: weight must be an integer 1-5, got {weight!r}")

    severity = _require(raw, "severity_if_absent", where)
    if severity not in VALID_SEVERITY:
        raise CatalogueError(f"{where}: severity_if_absent must be one of {VALID_SEVERITY}")

    applies = _require(raw, "applies_when", where)
    roles = applies.get("role") or []
    if not roles or not set(roles) <= VALID_ROLES:
        raise CatalogueError(f"{where}: applies_when.role must be a subset of {VALID_ROLES}")

    evidence = _require(raw, "evidence_required", where)
    if not isinstance(evidence, list):
        raise CatalogueError(f"{where}: evidence_required must be a list")

    # A control may override its file's citation status, e.g. one clause checked
    # against the gazette while the rest of the file is not.
    citation_status = raw.get("citation_status", file_citation)
    if citation_status not in VALID_CITATION_STATUS:
        raise CatalogueError(f"{where}: citation_status must be verified or pending")

    return Control(
        id=cid,
        rule_id=rule_id,
        rule_ref=rule_ref,
        rule_title=rule_title,
        title=_require(raw, "title", where),
        question=_require(raw, "question", where),
        guidance=_require(raw, "guidance", where),
        evidence_required=evidence,
        weight=weight,
        severity_if_absent=severity,
        roles=list(roles),
        condition=applies.get("condition"),
        # These three feed the Word report when no AI provider is configured.
        observation=_require(raw, "observation", where).strip(),
        impact=_require(raw, "impact", where).strip(),
        action=_require(raw, "action", where).strip(),
        citation_status=citation_status,
    )


def load_catalogue(rules_dir: str | Path = "rules") -> list[Control]:
    """Read every rules/*.yaml file and return all controls, sorted by id.

    Raises CatalogueError on any schema breach or duplicate control id.
    """
    rules_path = Path(rules_dir)
    if not rules_path.is_dir():
        raise CatalogueError(f"rules directory not found: {rules_path}")

    controls: list[Control] = []
    seen: set[str] = set()

    for path in sorted(rules_path.glob("*.yaml")):
        block = yaml.safe_load(path.read_text(encoding="utf-8"))
        rule_id = _require(block, "rule_id", path.name)
        rule_ref = _require(block, "rule_ref", path.name)
        rule_title = _require(block, "rule_title", path.name)
        if not RULE_ID_RE.fullmatch(str(rule_id)):
            raise CatalogueError(
                f"{path.name}: rule_id must be one capital letter followed by digits, "
                f"such as R6 or S4, got {rule_id!r}")
        file_citation = _require(block, "citation_status", path.name)
        if file_citation not in VALID_CITATION_STATUS:
            raise CatalogueError(
                f"{path.name}: citation_status must be verified or pending, got {file_citation!r}")

        for raw in _require(block, "controls", path.name):
            control = _parse_control(raw, rule_id, rule_ref, rule_title, file_citation)
            if control.id in seen:
                raise CatalogueError(f"duplicate control id: {control.id}")
            seen.add(control.id)
            controls.append(control)

    if not controls:
        raise CatalogueError(f"no controls found in {rules_path}")

    return sorted(controls, key=lambda c: (c.rule_id, c.id))


def applicable(controls: list[Control], role: str, flags: set[str] | None = None) -> list[Control]:
    """Filter the catalogue to the controls that apply to this engagement.

    role  -- 'fiduciary' or 'processor', determined per engagement not per firm.
    flags -- named client-profile flags, e.g. {'processes_children'}.

    Controls excluded here drop out of both the numerator and the denominator of
    the score, so an entity is never penalised for a control it cannot trigger.
    """
    flags = flags or set()
    return [
        c for c in controls
        if role in c.roles and (c.condition is None or c.condition in flags)
    ]


def score(
    controls: list[Control],
    responses: dict[str, Status],
    evidence_counts: dict[str, int],
) -> dict:
    """Compute the weighted readiness score.

    responses       -- control id -> assessed status
    evidence_counts -- control id -> number of evidence files attached

    Any control at or above the evidence gate weight scores zero without evidence,
    whatever status the assessor selected. Unanswered controls are treated as Absent.
    """
    earned = 0.0
    available = 0
    gated: list[str] = []

    for c in controls:
        available += c.weight
        status = responses.get(c.id, "Absent")
        factor = STATUS_FACTORS.get(status, 0.0)

        if c.needs_evidence and evidence_counts.get(c.id, 0) == 0:
            if factor > 0:
                gated.append(c.id)  # claimed but unevidenced - report this separately
            factor = 0.0

        earned += c.weight * factor

    pct = round(earned / available * 100, 1) if available else 0.0
    return {
        "score": pct,
        "band": band(pct),
        "earned": round(earned, 1),
        "available": available,
        "controls_assessed": len(controls),
        "gated_for_no_evidence": gated,
    }


def band(pct: float) -> str:
    """Readiness band. Deliberately avoids the word 'compliant'."""
    if pct < 40:
        return "Critical"
    if pct < 70:
        return "Developing"
    if pct < 90:
        return "Substantial"
    return "Mature"


if __name__ == "__main__":
    # Self-check: parse the catalogue and print its shape.
    cat = load_catalogue(Path(__file__).parent / "rules")
    print(f"Loaded {len(cat)} controls from {len({c.rule_id for c in cat})} rules\n")

    for rid in sorted({c.rule_id for c in cat}, key=lambda r: int(r[1:])):
        rows = [c for c in cat if c.rule_id == rid]
        gate = sum(1 for c in rows if c.needs_evidence)
        pending = sum(1 for c in rows if c.citation_status == "pending")
        print(
            f"  {rid:<4} {rows[0].rule_title:<36} "
            f"controls={len(rows):<3} weight={sum(c.weight for c in rows):<4} "
            f"evidence-gated={gate:<3} pending={pending}"
        )

    print(f"\n  TOTAL  controls={len(cat)}  weight={sum(c.weight for c in cat)}")
    n_pending = sum(1 for c in cat if c.citation_status == "pending")
    print(f"  Citation pending verification: {n_pending} of {len(cat)} controls")

    fid = applicable(cat, "fiduciary")
    proc = applicable(cat, "processor")
    kids = applicable(cat, "fiduciary", {"processes_children"})
    print(f"\n  Applicable to fiduciary                 : {len(fid)}")
    print(f"  Applicable to processor                 : {len(proc)}")
    print(f"  Fiduciary + processes children          : {len(kids)}")
