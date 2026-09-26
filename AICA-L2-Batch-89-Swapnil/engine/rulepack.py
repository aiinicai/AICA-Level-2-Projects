"""Load and validate the YAML rule pack (brief §6). The app refuses to start on
an invalid pack; :class:`RulePackError` names the file and row that failed."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .types import ENTITY_TYPES

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "rulepack"
DOMAIN_FILES = ["companies_onetime.yaml", "companies_annual.yaml", "companies_event.yaml",
                "llp.yaml", "directors.yaml"]

Anchor = Literal[
    "INCORPORATION", "FY_END", "FY_START", "AGM_DEADLINE", "AGM_ACTUAL_OR_DEADLINE",
    "BOARD_APPROVAL_OR_AGM", "HALF_YEAR_END", "CALENDAR_FIXED", "EVENT_DATE",
    "FIRST_AUDITOR_APPOINTMENT", "DIN_CYCLE", "DIN_FY_END", "DETAIL_CHANGE",
]
Recurrence = Literal["once", "annual", "half_yearly", "march31", "event", "first_trigger",
                     "din_annual", "din_cycle", "din_event"]
FeeRegime = Literal["NONE", "PER_DAY_100", "MULTIPLIER", "CHARGE", "FIXED_KYC", "LLP_MATRIX"]


class RulePackError(Exception):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Offset(Strict):
    days: int = 0
    months: int = 0


class Fixed(Strict):
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)


Expr = Union[str, dict[str, Any]]


class Rule(Strict):
    code: str = Field(pattern=r"^[A-Z0-9_]+$")
    form: str
    title: str
    entity_types: list[str]
    applicability: list[Expr] = ["always"]
    anchor: Anchor
    offset: Offset = Offset()
    fixed: Fixed | None = None
    half: Literal[1, 2] | None = None
    recurrence: Recurrence
    event_types: list[str] = []
    provisional: bool = False           # due date is an estimate until an actual anchor is known
    interpretation: bool = False
    fee_regime: FeeRegime = "NONE"
    fee_slab: Literal["S139", "LLP_ANNUAL"] | None = None
    variant: str | None = None          # name of a variant function in predicates.VARIANTS
    law: str
    penalty_summary: str = ""
    sources: list[str] = []
    effective_from: date
    effective_to: date | None = None
    verified: bool = False
    verified_by: str | None = None
    verified_on: date | None = None
    notes: str = ""

    @field_validator("entity_types")
    @classmethod
    def _types(cls, v: list[str]) -> list[str]:
        bad = set(v) - ENTITY_TYPES
        if bad:
            raise ValueError(f"unknown entity type(s) {sorted(bad)}")
        return v

    @model_validator(mode="after")
    def _consistency(self) -> "Rule":
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to is before effective_from")
        if self.anchor == "CALENDAR_FIXED" and not self.fixed:
            raise ValueError("CALENDAR_FIXED anchor needs 'fixed: {month, day}'")
        if self.recurrence == "event" and not self.event_types:
            raise ValueError("event rule needs event_types")
        return self

    def in_force(self, d: date) -> bool:
        return self.effective_from <= d and (self.effective_to is None or d <= self.effective_to)

    @property
    def content_hash(self) -> str:
        """Hash of the legal content — verification fields excluded, so signing
        a row off does not change the hash obligations were computed with."""
        body = self.model_dump(mode="json", exclude={"verified", "verified_by", "verified_on"})
        return hashlib.sha256(canonical_json(body).encode()).hexdigest()[:16]


class Threshold(Strict):
    code: str
    values: dict[str, float]
    effective_from: date
    effective_to: date | None = None
    law: str
    verified: bool = False
    verified_by: str | None = None
    verified_on: date | None = None

    def in_force(self, d: date) -> bool:
        return self.effective_from <= d and (self.effective_to is None or d <= self.effective_to)


class DomainFile(Strict):
    domain: str
    thresholds: list[Threshold] = []
    rules: list[Rule]


class FeeTable(Strict):
    code: str
    law: str
    sources: list[str] = []
    effective_from: date
    effective_to: date | None = None
    verified: bool = False
    verified_by: str | None = None
    verified_on: date | None = None
    data: dict[str, Any]


class FeesFile(Strict):
    domain: Literal["fees"]
    tables: list[FeeTable]


class Scheme(Strict):
    code: str
    kind: Literal["FEE_RELIEF", "NO_ADDITIONAL_FEE", "DUE_DATE_EXTENSION"]
    circular_ref: str
    url: str = ""
    window_from: date
    window_to: date
    rule_codes: list[str]
    applies_to: list[Literal["COMPANY", "LLP"]] = ["COMPANY"]
    period_keys: list[str] = []          # empty = any period
    additional_fee_factor: float = 0.0   # share of additional fee still payable
    new_due_date: date | None = None
    respects_ccfs_exclusion: bool = False
    verified: bool = False
    verified_by: str | None = None
    verified_on: date | None = None
    notes: str = ""


class SchemesFile(Strict):
    domain: Literal["schemes"]
    schemes: list[Scheme]


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)


class RulePack:
    def __init__(self, version: str, rules: list[Rule], thresholds: list[Threshold],
                 fee_tables: list[FeeTable], schemes: list[Scheme]):
        self.version = version
        self.rules = rules
        self.thresholds = thresholds
        self.fee_tables = {t.code: t for t in fee_tables}
        self._fee_rows = fee_tables
        self.schemes = schemes
        self.by_code = {r.code: r for r in rules}

    # ---------------------------------------------------------------- lookups
    def rule(self, code: str) -> Rule:
        try:
            return self.by_code[code]
        except KeyError:
            raise RulePackError(f"No rule with code {code!r}") from None

    def threshold(self, code: str, on: date) -> Threshold:
        for t in self.thresholds:
            if t.code == code and t.in_force(on):
                return t
        raise RulePackError(f"No {code} threshold in force on {on.isoformat()}")

    def fee_table(self, code: str, on: date | None = None) -> FeeTable:
        rows = [t for t in self._fee_rows if t.code == code
                and (on is None or (t.effective_from <= on and (t.effective_to is None or on <= t.effective_to)))]
        if not rows:
            raise RulePackError(f"No fee table {code!r}" + (f" in force on {on}" if on else ""))
        return rows[-1]

    @property
    def content_hash(self) -> str:
        body = {"rules": {r.code: r.content_hash for r in self.rules},
                "thresholds": [t.model_dump(mode="json", exclude={"verified", "verified_by", "verified_on"}) for t in self.thresholds],
                "fees": [t.model_dump(mode="json", exclude={"verified", "verified_by", "verified_on"}) for t in self._fee_rows],
                "schemes": [s.model_dump(mode="json", exclude={"verified", "verified_by", "verified_on"}) for s in self.schemes]}
        return hashlib.sha256(canonical_json(body).encode()).hexdigest()

    def unverified(self, codes: list[str]) -> list[str]:
        return sorted({c for c in codes if not self.rule(c).verified})

    def check_exportable(self, codes: list[str]) -> None:
        """Client-facing exports are blocked while any included rule is unverified (§6.3)."""
        bad = self.unverified(codes)
        if bad:
            raise UnverifiedRuleError(bad)

    def with_verifications(self, verified: dict[str, tuple[str, date]]) -> "RulePack":
        """Overlay in-app partner sign-offs (stored in the DB) onto the YAML rows."""
        rules = [r.model_copy(update={"verified": True, "verified_by": verified[r.code][0],
                                      "verified_on": verified[r.code][1]}) if r.code in verified else r
                 for r in self.rules]
        return RulePack(self.version, rules, self.thresholds, self._fee_rows, self.schemes)


class UnverifiedRuleError(Exception):
    def __init__(self, codes: list[str]):
        self.codes = codes
        super().__init__("Export blocked: these rules are not yet verified by a partner: " + ", ".join(codes))


# -------------------------------------------------------------------- loader
def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RulePackError(f"Rule pack file missing: {path.name}") from None
    except yaml.YAMLError as e:
        raise RulePackError(f"{path.name}: YAML syntax error: {e}") from None


def _describe(path: Path, raw: Any, err: ValidationError) -> str:
    lines = [f"{path.name}: invalid rule pack"]
    for e in err.errors():
        loc = list(e["loc"])
        where = ".".join(str(x) for x in loc)
        if len(loc) >= 2 and loc[0] in ("rules", "tables", "schemes", "thresholds") and isinstance(loc[1], int):
            try:
                where += f" (code={raw[loc[0]][loc[1]].get('code')})"
            except Exception:  # pragma: no cover - best effort
                pass
        lines.append(f"  - {where}: {e['msg']}")
    return "\n".join(lines)


def load(directory: Path | str | None = None) -> RulePack:
    from .predicates import validate_expr, VARIANTS  # late import: predicates imports types only

    d = Path(directory) if directory else DEFAULT_DIR
    version_file = d / "VERSION"
    if not version_file.exists():
        raise RulePackError("Rule pack VERSION file missing")
    version = version_file.read_text(encoding="utf-8").strip()

    rules: list[Rule] = []
    thresholds: list[Threshold] = []
    for name in DOMAIN_FILES:
        raw = _load_yaml(d / name)
        try:
            f = DomainFile.model_validate(raw)
        except ValidationError as e:
            raise RulePackError(_describe(d / name, raw, e)) from None
        for r in f.rules:
            try:
                for expr in r.applicability:
                    validate_expr(expr)
                if r.variant and r.variant not in VARIANTS:
                    raise ValueError(f"unknown variant function {r.variant!r}")
            except ValueError as e:
                raise RulePackError(f"{name}: rule {r.code}: {e}") from None
        rules.extend(f.rules)
        thresholds.extend(f.thresholds)

    codes = [r.code for r in rules]
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    if dupes:
        raise RulePackError(f"Duplicate rule codes: {dupes}")

    raw = _load_yaml(d / "fees.yaml")
    try:
        fees = FeesFile.model_validate(raw)
    except ValidationError as e:
        raise RulePackError(_describe(d / "fees.yaml", raw, e)) from None
    from .fees import validate_fee_tables
    try:
        validate_fee_tables(fees.tables)
    except ValueError as e:
        raise RulePackError(f"fees.yaml: {e}") from None

    raw = _load_yaml(d / "schemes.yaml")
    try:
        schemes = SchemesFile.model_validate(raw)
    except ValidationError as e:
        raise RulePackError(_describe(d / "schemes.yaml", raw, e)) from None
    for s in schemes.schemes:
        unknown = set(s.rule_codes) - set(codes)
        if unknown:
            raise RulePackError(f"schemes.yaml: scheme {s.code} references unknown rule codes {sorted(unknown)}")

    return RulePack(version, rules, thresholds, fees.tables, schemes.schemes)
