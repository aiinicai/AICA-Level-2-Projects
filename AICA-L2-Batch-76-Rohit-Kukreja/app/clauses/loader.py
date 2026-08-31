"""YAML → ClauseSet. Build Prompt v2 §3.3.

Authoring mistakes are caught here, at load, rather than in a rendered
document under a partner's signature.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.clauses.model import (
    CONTEXT_VARIABLES,
    CarryForward,
    Clause,
    ClauseInput,
    ClauseOption,
    ClauseSet,
    ClauseVariant,
    DataType,
    DocumentTemplate,
    FixedRow,
    InputDefault,
    IssuedBy,
    Manifest,
    RenderAs,
    RenderBlock,
    RepeatingBlock,
    RepeatingColumn,
    Severity,
)
from app.clauses.resolve import ExpressionError, UnresolvedClauseError, evaluate, resolve
from app.core import arithmetic
from app.core.applicability import FLAGS

MANIFEST_NAME = "manifest.yaml"
_NON_CLAUSE_FILES = {MANIFEST_NAME, "applicability_rules.yaml"}


class ClauseValidationError(ValueError):
    """One or more clause files are malformed. Carries every problem found."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        joined = "\n  - ".join(problems)
        super().__init__(f"{len(problems)} clause repository problem(s):\n  - {joined}")


# --------------------------------------------------------------------------
# Field coercion
# --------------------------------------------------------------------------


def _as_date(value: Any, where: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ClauseValidationError([f"{where}: bad date {value!r}"]) from exc
    raise ClauseValidationError([f"{where}: bad date {value!r}"])


def _enum[T](enum_cls: type[T], value: Any, where: str, default: T | None = None) -> T:
    if value is None and default is not None:
        return default
    try:
        return enum_cls(value)  # type: ignore[call-arg]
    except ValueError as exc:
        allowed = ", ".join(str(m) for m in enum_cls)  # type: ignore[attr-defined]
        raise ClauseValidationError([f"{where}: {value!r} is not one of ({allowed})"]) from exc


def _options(raw: Any, where: str) -> tuple[ClauseOption, ...]:
    if not raw:
        return ()
    out: list[ClauseOption] = []
    for item in raw:
        if not isinstance(item, dict) or "value" not in item:
            raise ClauseValidationError([f"{where}: each option needs a `value`"])
        out.append(ClauseOption(value=str(item["value"]), label=str(item.get("label", ""))))
    return tuple(out)


def _input_defaults(raw: Any, where: str, allowed: frozenset[str]) -> tuple[InputDefault, ...]:
    """Parse `input.defaults` -- answers derived from master data.

    A default naming a value the input does not offer is rejected here rather
    than at render time, where it would surface as an unresolved clause long
    after the typo was made.
    """
    if not raw:
        return ()
    if not isinstance(raw, list):
        raise ClauseValidationError([f"{where}: `defaults` must be a list"])
    out: list[InputDefault] = []
    for item in raw:
        if not isinstance(item, dict) or "value" not in item:
            raise ClauseValidationError([f"{where}: each default needs a `value`"])
        value = str(item["value"])
        if allowed and value not in allowed:
            raise ClauseValidationError(
                [f"{where}: default {value!r} is not one of this input's options"]
            )
        when = item.get("when")
        out.append(InputDefault(when=None if when is None else str(when), value=value))
    return tuple(out)


def _input(raw: Any, where: str) -> ClauseInput | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ClauseValidationError([f"{where}: `input` must be a mapping"])
    if "key" not in raw:
        raise ClauseValidationError([f"{where}: `input.key` is required"])
    options = _options(raw.get("options"), f"{where}.options")
    return ClauseInput(
        key=str(raw["key"]),
        datatype=_enum(DataType, raw.get("datatype"), f"{where}.datatype", DataType.TEXT),
        label=str(raw.get("label", "")),
        carry_forward=_enum(
            CarryForward,
            raw.get("carry_forward"),
            f"{where}.carry_forward",
            CarryForward.PROMPT,
        ),
        mandatory=bool(raw.get("mandatory", True)),
        options=options,
        defaults=_input_defaults(
            raw.get("defaults"), f"{where}.defaults", frozenset(o.value for o in options)
        ),
    )


def _repeating_block(raw: Any, where: str) -> RepeatingBlock | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ClauseValidationError([f"{where}: `repeating_block` must be a mapping"])
    for required in ("entity", "columns"):
        if required not in raw:
            raise ClauseValidationError([f"{where}: `repeating_block.{required}` is required"])
    columns: list[RepeatingColumn] = []
    for i, col in enumerate(raw["columns"]):
        if not isinstance(col, dict) or "key" not in col:
            raise ClauseValidationError([f"{where}.columns[{i}]: needs a `key`"])
        columns.append(
            RepeatingColumn(
                key=str(col["key"]),
                label=str(col.get("label", "")),
                datatype=_enum(
                    DataType, col.get("datatype"), f"{where}.columns[{i}]", DataType.TEXT
                ),
                required=bool(col.get("required", False)),
                options=tuple(str(o) for o in col.get("options", ())),
            )
        )
    fixed_rows = _fixed_rows(raw.get("fixed_rows"), f"{where}.fixed_rows")

    return RepeatingBlock(
        entity=str(raw["entity"]),
        columns=tuple(columns),
        when=raw.get("when"),
        min_rows=int(raw.get("min_rows", 0)),
        carry_forward=_enum(
            CarryForward, raw.get("carry_forward"), f"{where}.carry_forward", CarryForward.PROMPT
        ),
        fixed_rows=fixed_rows,
    )


def _fixed_rows(raw: Any, where: str) -> tuple[FixedRow, ...]:
    """A prescribed schedule: the rows are declared, only the figures typed.

    Every problem below is raised at LOAD time. A sub-total that refers to a
    row spelled differently would otherwise be silently blank on a signed
    Board's Report, which is exactly the class of defect §3.3 exists to stop.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list) or not raw:
        raise ClauseValidationError([f"{where}: must be a non-empty list"])

    rows: list[FixedRow] = []
    problems: list[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or "key" not in item or "particulars" not in item:
            problems.append(f"{where}[{i}]: needs a `key` and `particulars`")
            continue
        rows.append(
            FixedRow(
                key=str(item["key"]),
                particulars=str(item["particulars"]),
                computed=(str(item["computed"]) if item.get("computed") else None),
            )
        )
    if problems:
        raise ClauseValidationError(problems)

    keys = [r.key for r in rows]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        problems.append(f"{where}: duplicate row keys {duplicates}")

    # A sub-total may only refer to rows ABOVE it. Referring downwards would
    # make the schedule's order meaningless and could not be evaluated in one
    # pass; a self-reference would not terminate at all.
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if row.computed is not None:
            try:
                referenced = arithmetic.names(row.computed, f"{where}[{i}].computed")
            except arithmetic.ArithmeticExpressionError as exc:
                problems.append(str(exc))
            else:
                unknown = sorted(referenced - set(keys))
                if unknown:
                    problems.append(f"{where}[{i}]: `computed` refers to unknown row(s) {unknown}")
                below = sorted(referenced - seen - set(unknown))
                if below:
                    problems.append(
                        f"{where}[{i}] ({row.key!r}): `computed` refers to {below}, "
                        "which come later in the schedule"
                    )
        seen.add(row.key)

    if problems:
        raise ClauseValidationError(problems)
    return tuple(rows)


def _variants(raw: Any, where: str) -> tuple[ClauseVariant, ...]:
    if not raw:
        raise ClauseValidationError([f"{where}: at least one variant is required"])
    out: list[ClauseVariant] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or "body" not in item:
            raise ClauseValidationError([f"{where}[{i}]: each variant needs a `body`"])
        severity = item.get("severity")
        render_block = item.get("render_block")
        out.append(
            ClauseVariant(
                body=str(item["body"]),
                when=item.get("when"),
                requires_narrative=bool(item.get("requires_narrative", False)),
                severity=(
                    _enum(Severity, severity, f"{where}[{i}].severity")
                    if severity is not None
                    else None
                ),
                render_block=(
                    _enum(RenderBlock, render_block, f"{where}[{i}].render_block")
                    if render_block is not None
                    else None
                ),
                render_as=(
                    _enum(RenderAs, item["render_as"], f"{where}[{i}].render_as")
                    if item.get("render_as") is not None
                    else None
                ),
                omit=bool(item.get("omit", False)),
            )
        )
    return tuple(out)


def clause_from_dict(raw: dict[str, Any], source: Path | None = None) -> Clause:
    where = str(source) if source else raw.get("id", "<clause>")
    for required in ("id", "document", "title", "variants"):
        if required not in raw:
            raise ClauseValidationError([f"{where}: `{required}` is required"])
    applicability = raw.get("applicability") or {}
    requires = tuple(str(r) for r in applicability.get("requires", ()))
    # An applicability flag that does not exist is not a no-op: `build_document`
    # skips any clause whose requirements are not all satisfied, so a typo here
    # silently deletes the clause from every document it belongs to. That is
    # exactly how `requires: [caro_applicable]` — the engine's flag is `caro` —
    # kept two CARO clauses out of the annexure without a word of warning.
    unknown = sorted(set(requires) - set(FLAGS))
    if unknown:
        raise ClauseValidationError(
            [f"{where}: unknown applicability flag(s) {unknown}; valid flags are {list(FLAGS)}"]
        )
    return Clause(
        id=str(raw["id"]),
        document=str(raw["document"]),
        order=int(raw.get("order", 0)),
        title=str(raw["title"]),
        clause_ref=str(raw.get("clause_ref", "")),
        number=str(raw.get("number", "")),
        effective_from=_as_date(raw.get("effective_from"), f"{where}.effective_from"),
        effective_to=_as_date(raw.get("effective_to"), f"{where}.effective_to"),
        requires=requires,
        input=_input(raw.get("input"), f"{where}.input"),
        repeating_block=_repeating_block(raw.get("repeating_block"), where),
        variants=_variants(raw.get("variants"), f"{where}.variants"),
        optional=bool(raw.get("optional", False)),
        needs_review=bool(raw.get("needs_review", False)),
        source_path=str(source) if source else "",
        render_as=_enum(RenderAs, raw.get("render_as", "para"), f"{where}.render_as"),
        heading_level=int(raw.get("heading_level", 2)),
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def unreachable_options(clause: Clause) -> tuple[str, ...]:
    """Option values that select no variant.

    A control the user can set that changes no document is the prototype's
    worst defect class (§18.3, `test_no_dead_controls.py`).
    """
    if clause.input is None or clause.input.datatype is not DataType.SELECT:
        return ()
    has_fallback = any(v.when is None for v in clause.variants)
    if has_fallback:
        return ()
    dead: list[str] = []
    for option in clause.input.options:
        context: dict[str, Any] = {"value": option.value}
        if not any(v.when is not None and _safe_eval(v.when, context) for v in clause.variants):
            dead.append(option.value)
    return tuple(dead)


def _safe_eval(expression: str, context: dict[str, Any]) -> bool:
    try:
        return evaluate(expression, context)
    except ExpressionError:
        return False


def validate(clauses: list[Clause]) -> list[str]:
    problems: list[str] = []
    seen: dict[str, str] = {}

    for clause in clauses:
        where = clause.source_path or clause.id

        if clause.id in seen:
            problems.append(
                f"{where}: duplicate clause id {clause.id!r} (also in {seen[clause.id]})"
            )
        seen[clause.id] = where

        if (
            clause.effective_from
            and clause.effective_to
            and clause.effective_from > clause.effective_to
        ):
            problems.append(f"{where}: effective_from is after effective_to")

        if clause.input and clause.input.datatype is DataType.SELECT and not clause.input.options:
            problems.append(f"{where}: a select input needs options")

        if RenderAs.SECTION in {clause.render_as} | {
            v.render_as for v in clause.variants if v.render_as
        }:
            for ref in section_without_heading(clause):
                problems.append(
                    f"{where}: {ref} is a single paragraph, so the whole clause would "
                    "render as a section heading; give it a heading line and a body, "
                    "or drop `render_as: section`"
                )

        for i, variant in enumerate(clause.variants):
            if variant.when is None:
                continue
            try:
                evaluate(variant.when, _probe_context(clause))
            except ExpressionError as exc:
                problems.append(f"{where}: variants[{i}] {exc}")

        if clause.input is not None:
            for i, default in enumerate(clause.input.defaults):
                if default.when is None:
                    continue
                try:
                    evaluate(default.when, _probe_context(clause))
                except ExpressionError as exc:
                    problems.append(f"{where}: input.defaults[{i}] {exc}")

        if clause.repeating_block is not None:
            block = clause.repeating_block
            if not block.columns:
                problems.append(f"{where}: repeating_block has no columns")
            if block.min_rows < 0:
                problems.append(f"{where}: repeating_block.min_rows must be >= 0")
            if block.when is not None:
                try:
                    evaluate(block.when, _probe_context(clause))
                except ExpressionError as exc:
                    problems.append(f"{where}: repeating_block.when {exc}")
            if any(v.render_block is None for v in clause.variants) and not any(
                v.render_block is RenderBlock.TABLE for v in clause.variants
            ):
                problems.append(
                    f"{where}: has a repeating_block but no variant renders it "
                    f"(set `render_block: table`) — child rows would be collected and never printed"
                )

            # `repeating_block.when` decides whether the WORKSPACE offers the
            # table; `variant.render_block` decides whether the DOCUMENT prints
            # one, and `min_rows` is enforced from the second. Two mechanisms
            # answering one question, so they must agree. When they did not, a
            # nil answer hid the table on screen and still demanded a row on
            # export, and the auditor had no control anywhere to satisfy it.
            if block.when is not None and clause.input is not None:
                for option in clause.input.options:
                    context = _probe_context(clause)
                    context["value"] = option.value
                    try:
                        chosen = resolve(clause, context)
                        offered = bool(evaluate(block.when, context))
                    except (ExpressionError, UnresolvedClauseError):
                        continue  # reported elsewhere
                    if chosen.variant.render_block is RenderBlock.TABLE and not offered:
                        problems.append(
                            f"{where}: answering {option.value!r} prints a table but "
                            f"repeating_block.when hides it — the row would be demanded "
                            f"on export and never offered on the workspace"
                        )

        for dead in unreachable_options(clause):
            problems.append(f"{where}: option {dead!r} matches no variant — a dead control (§18.3)")

    return problems


# Must match `app.services.document._paragraphs`, which is what actually
# splits a body at render time. Two different splits would mean this check
# passes on a clause the renderer still sets as one paragraph.
_PARAGRAPH_SPLIT = re.compile(r"[ \t]*\r?\n\s*")


def section_without_heading(clause: Clause) -> tuple[str, ...]:
    """Variants of a `render_as: section` clause that have no body under the heading.

    A section clause renders its FIRST paragraph as the heading and the rest
    as body. A variant written as a single paragraph therefore renders its
    entire text as a heading — which is silent: the document still builds,
    still exports, and simply has a paragraph of statutory prose set as a
    section title. Caught here instead.
    """
    bad: list[str] = []
    for i, variant in enumerate(clause.variants):
        if variant.omit:
            continue
        if (variant.render_as or clause.render_as) is not RenderAs.SECTION:
            continue
        if variant.requires_narrative:
            # The body is the heading and the lead-in; the matter itself is
            # the narrative, which the renderer appends. Legitimate.
            continue
        paragraphs = [c for c in _PARAGRAPH_SPLIT.split(variant.body) if c.strip()]
        if len(paragraphs) < 2:
            bad.append(f"{clause.id}.variants[{i}]")
    return tuple(bad)


def _probe_context(clause: Clause) -> dict[str, Any]:
    """A context with every name a clause's expressions may legitimately use."""
    context: dict[str, Any] = dict.fromkeys(CONTEXT_VARIABLES)
    context["value"] = None
    if clause.input is not None:
        context[clause.input.key.replace(".", "_")] = None
    return context


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ClauseValidationError([f"{path}: expected a YAML mapping"])
    return data


def load_manifest(content_dir: Path) -> Manifest:
    path = content_dir / MANIFEST_NAME
    if not path.exists():
        raise ClauseValidationError([f"{path}: manifest.yaml is required (§3.3)"])
    raw = _read_yaml(path)
    if "template_version" not in raw:
        raise ClauseValidationError([f"{path}: `template_version` is required"])
    review = raw.get("review") or {}
    return Manifest(
        template_version=str(raw["template_version"]),
        changelog=tuple(str(entry) for entry in raw.get("changelog", ())),
        reviewed_on=_as_date(review.get("date"), f"{path}.review.date"),
        reviewed_by=str(review.get("by", "")),
        review_method=str(review.get("method", "")),
    )


def load_documents(content_dir: Path) -> dict[str, DocumentTemplate]:
    path = content_dir / MANIFEST_NAME
    raw = _read_yaml(path)
    documents: dict[str, DocumentTemplate] = {}
    for doc_id, spec in (raw.get("documents") or {}).items():
        spec = spec or {}
        raw_issuer = str(spec.get("issued_by", IssuedBy.FIRM.value))
        try:
            issued_by = IssuedBy(raw_issuer)
        except ValueError as exc:
            # Rejected at load rather than defaulting to the firm: a typo here
            # would silently put the auditor's letterhead on the client's own
            # representation letter, which is the mistake this field exists to
            # prevent.
            # The error type carries a LIST of problems, not a message — passing
            # a bare string makes it report one problem per character.
            raise ClauseValidationError(
                [
                    f"{path}: document {doc_id!r} has issued_by {raw_issuer!r}; "
                    f"expected one of {[m.value for m in IssuedBy]}"
                ]
            ) from exc

        documents[str(doc_id)] = DocumentTemplate(
            id=str(doc_id),
            title=str(spec.get("title", doc_id)),
            clause_ids=tuple(str(c) for c in spec.get("clauses", ())),
            short_title=str(spec.get("short_title", "")),
            issued_by=issued_by,
        )
    return documents


def load_clause_set(content_dir: Path) -> ClauseSet:
    """Load and validate the whole repository."""
    if not content_dir.exists():
        raise ClauseValidationError([f"{content_dir}: content directory not found"])

    clauses: list[Clause] = []
    problems: list[str] = []
    for path in sorted(content_dir.rglob("*.yaml")):
        if path.name in _NON_CLAUSE_FILES:
            continue
        try:
            clauses.append(clause_from_dict(_read_yaml(path), path))
        except ClauseValidationError as exc:
            problems.extend(exc.problems)
        except yaml.YAMLError as exc:
            problems.append(f"{path}: invalid YAML — {exc}")

    problems.extend(validate(clauses))
    if problems:
        raise ClauseValidationError(problems)

    return ClauseSet(
        manifest=load_manifest(content_dir),
        clauses=tuple(sorted(clauses, key=lambda c: (c.document, c.order, c.id))),
        documents=load_documents(content_dir),
    )
