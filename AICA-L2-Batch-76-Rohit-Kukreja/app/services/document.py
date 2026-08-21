"""Assemble a document from the clause repository and an engagement's answers.

Build Prompt v2 §2 (`services/document`) and §3.4. The output is a node tree;
what it becomes — HTML now, DOCX in Phase 9 — is the renderer's business.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.clauses.model import AUTO_ALPHA, Clause, ClauseSet, DataType, RenderAs, RenderBlock
from app.clauses.resolve import (
    ResolvedClause,
    UnresolvedClauseError,
    evaluate,
    resolve,
    unresolved_tokens,
)
from app.core.formatting import DateStyle, format_date, group_indian
from app.render.base import Document, Heading, Node, Para, Signature, Table

Responses = dict[str, Any]
ChildRows = dict[str, list[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class BuiltDocument:
    """A rendered tree plus everything that would block an export (§18.4)."""

    document: Document
    unanswered: tuple[str, ...] = ()
    missing_narratives: tuple[str, ...] = ()
    missing_rows: tuple[str, ...] = ()
    placeholders: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    not_applicable: tuple[str, ...] = ()
    """Clauses skipped because an applicability flag they require is false.

    Reported for the same reason as `omitted`: a section absent because the
    engine ruled it out and a section absent because it was never authored
    look identical on the page.
    """
    excluded_by: frozenset[str] = frozenset()
    """The applicability flags that ruled `not_applicable` out.

    Carried so the page can say *which* determination emptied the document and
    on what figures, rather than reporting a bare count of absent clauses.
    """
    omitted: tuple[str, ...] = ()
    """Clauses deliberately left out of the document.

    Not a defect and not blocking — but shown in the preview, because a
    paragraph missing by design and a paragraph missing by accident look
    identical in the finished report.
    """

    @property
    def exportable(self) -> bool:
        """No unresolved placeholder, no empty mandatory field, no missing
        narrative or required child row. Exceptions do not block — a
        qualified opinion is a legitimate outcome, not a defect."""
        return not (
            self.unanswered or self.missing_narratives or self.missing_rows or self.placeholders
        )

    @property
    def has_body(self) -> bool:
        """Whether anything beyond headings actually printed.

        A document whose every clause was ruled out still renders its title, so
        the page looked like a document that had simply come out blank. The IFC
        annexure did exactly that for an IFC-exempt company and nothing on the
        screen said why -- the same defect as a dropdown that shows an answer it
        has not stored. `not_applicable` was populated for precisely this and
        was never read by a template.
        """
        return any(not isinstance(node, Heading) for node in self.document.nodes)

    @property
    def blocking_count(self) -> int:
        return (
            len(self.unanswered)
            + len(self.missing_narratives)
            + len(self.missing_rows)
            + len(self.placeholders)
        )


def _answer(clause: Clause, responses: Responses) -> Any:
    if clause.input is None:
        return None
    return responses.get(clause.input.key)


def format_cell(value: Any, datatype: DataType) -> str:
    """Format one child-table cell for a statutory document (§12).

    An empty cell must be blank, never the string "None", and an amount must
    carry lakh/crore grouping — `str(Decimal("4260000.00"))` in a signed
    annexure is exactly the class of defect §19 forbids.
    """
    if value is None:
        return ""
    if datatype is DataType.AMOUNT:
        return group_indian(value)
    if datatype is DataType.NUMBER:
        return group_indian(value)
    if datatype is DataType.DATE and isinstance(value, date):
        return format_date(value, DateStyle.LONG)
    return str(value)


def _table_for(clause: Clause, rows: list[dict[str, Any]]) -> Table:
    block = clause.repeating_block
    assert block is not None  # guarded by the caller
    headers = tuple(column.label or column.key for column in block.columns)
    body = tuple(
        tuple(format_cell(row.get(column.key), column.datatype) for column in block.columns)
        for row in rows
    )
    return Table(headers=headers, rows=body, clause_id=clause.id)


def build_document(
    clause_set: ClauseSet,
    document_id: str,
    fy_end: date,
    *,
    responses: Responses | None = None,
    child_rows: ChildRows | None = None,
    context: dict[str, Any] | None = None,
    applicable: frozenset[str] | None = None,
) -> BuiltDocument:
    """Resolve every in-force clause of one document into a node tree.

    `applicable` is the set of applicability flags that came out true for
    this engagement (§7). A clause naming a flag it does not carry is not
    printed — Key Audit Matters for an unlisted private company, the CARO
    annexure for an exempt one. Passing `None` prints everything, which is
    what the machinery tests want and never what a real render wants.
    """
    responses = responses or {}
    child_rows = child_rows or {}
    base_context = {**(context or {}), **_transaction_facts(responses)}

    template = clause_set.documents.get(document_id)
    title = template.title if template else document_id

    document = Document(
        id=document_id,
        title=title,
        template_version=clause_set.manifest.template_version,
    )
    document.add(Heading(text=title, level=1))

    unanswered: list[str] = []
    missing_narratives: list[str] = []
    missing_rows: list[str] = []
    exceptions: list[str] = []
    omitted: list[str] = []
    # Letters are handed out as the paragraphs are emitted, so an omitted
    # clause consumes none and everything below it closes up.
    next_letter = 0

    not_applicable: list[str] = []
    # The flags that did the excluding, so the page can name the determination
    # rather than just report a count of missing clauses.
    excluded_by: set[str] = set()

    for clause in clause_set.for_document(document_id, fy_end):
        if applicable is not None and not set(clause.requires) <= applicable:
            not_applicable.append(clause.id)
            excluded_by.update(set(clause.requires) - applicable)
            continue

        value = _answer(clause, responses)

        if clause.input is not None and value is None:
            # Master data answers what it can. An input the profile determines
            # is not put to the user at all -- and, more to the point, does not
            # leave the clause unanswered, which would drop the disclosure from
            # the document entirely instead of printing the nil paragraph.
            value = _derived_answer(clause, base_context)

        if clause.input is not None and value is None:
            if clause.input.mandatory:
                unanswered.append(clause.id)
            continue

        clause_context = {**base_context, "value": value}
        try:
            resolved = resolve(clause, clause_context)
        except UnresolvedClauseError:
            # An answer the repository has no wording for. Recording it beats
            # printing a clause that silently says nothing.
            unanswered.append(clause.id)
            continue

        if resolved.variant.omit:
            # Reported, not dropped: the preview needs to show that this
            # paragraph was considered and deliberately left out.
            omitted.append(clause.id)
            continue

        number: str | None = None
        if clause.number == AUTO_ALPHA:
            number = _alpha(next_letter)
            next_letter += 1

        narrative = str(responses.get(f"{clause.id}.narrative", "") or "")
        document.extend(
            _nodes_for(clause, resolved, child_rows.get(clause.id, []), number, narrative)
        )

        if resolved.is_exception:
            exceptions.append(clause.id)
        if (
            resolved.requires_narrative
            and not str(responses.get(f"{clause.id}.narrative", "")).strip()
        ):
            missing_narratives.append(clause.id)
        if _rows_short(clause, resolved, child_rows.get(clause.id, [])):
            missing_rows.append(clause.id)

    placeholders = [token for text in document.text_nodes() for token in unresolved_tokens(text)]

    return BuiltDocument(
        document=document,
        unanswered=tuple(unanswered),
        missing_narratives=tuple(missing_narratives),
        missing_rows=tuple(missing_rows),
        placeholders=tuple(placeholders),
        exceptions=tuple(exceptions),
        not_applicable=tuple(not_applicable),
        excluded_by=frozenset(excluded_by),
        omitted=tuple(omitted),
    )


def _transaction_facts(responses: dict[str, Any]) -> dict[str, bool]:
    """Facts about the year's transactions, read from answers already given.

    Decision 78. CARO paragraph 3(iii) opens "whether during the year the
    company has made investments in, provided any guarantee or security or
    granted any loans or advances in the nature of loans ... IF SO, --", and
    everything from (a) to (f) hangs off that chapeau.

    The tool did not honour it. Clauses (b) to (f) each defaulted to their
    positive wording, so a company that had granted nothing still issued a
    CARO annexure opining that the terms of its loans were "not prejudicial to
    the interest of the Company" and that repayments "have been regular" --
    assertions about transactions that did not exist. The firm reported it on
    21 August 2026.

    Derived here rather than asked, because it is already known: (a)(A) and
    (a)(B) establish the loans, advances, guarantees and security, and
    `caro.iii.investments` the remaining limb. Asking a sixth time would be a
    sixth chance to answer inconsistently.

    Unanswered is NOT taken as "none". An auditor who has not yet reached
    clause (a) has not said there were no loans, and defaulting (b) to (f) on
    a question nobody answered would put the same false assertion back with a
    different provenance.
    """

    def answered_none(key: str) -> bool:
        return str(responses.get(key, "")).strip() == "none"

    no_loans = answered_none("caro.iii.a.A") and answered_none("caro.iii.a.B")
    return {
        "caro_no_loans_granted": no_loans,
        "caro_nothing_under_iii": no_loans and answered_none("caro.iii.investments"),
    }


def _derived_answer(clause: Clause, context: dict[str, Any]) -> str | None:
    """The first `input.defaults` entry whose condition holds, if any.

    Only reached when the engagement has no answer of its own, so a derived
    answer never overrides one the auditor gave.
    """
    if clause.input is None:
        return None
    for default in clause.input.defaults:
        if default.when is None or evaluate(default.when, context):
            return default.value
    return None


def _paragraphs(body: str) -> list[str]:
    """Split a clause body into paragraphs.

    Clause bodies are authored as YAML folded scalars (`>`). Folding turns a
    single line break into a space and a blank line into one newline — so any
    newline surviving into the loaded body is a paragraph break the author
    put there deliberately. Splitting on it is what keeps Rule 11(e)'s parts
    (i), (ii) and (iii) as three paragraphs instead of one run-on block.

    HTML collapses whitespace, so without this the break is simply lost.
    """
    return [chunk.strip() for chunk in re.split(r"[ \t]*\r?\n\s*", body) if chunk.strip()]


def _alpha(index: int) -> str:
    """0 -> (a), 25 -> (z), 26 -> (aa). Past (z) is unreachable in practice."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("a") + remainder) + letters
    return f"({letters})"


def _nodes_for(
    clause: Clause,
    resolved: ResolvedClause,
    rows: list[dict[str, Any]],
    number: str | None = None,
    narrative: str = "",
) -> list[Node]:
    chunks = _paragraphs(resolved.body) or [resolved.body]
    render_as = resolved.variant.render_as or clause.render_as

    # An exception variant is written as a lead-in — "the matters are as
    # follows:" — and the matter itself is the narrative. Without this the
    # document prints the lead-in and stops, so a qualified opinion's Basis
    # section, a fraud disclosure and a going concern uncertainty would each
    # announce themselves and then say nothing.
    tail = _paragraphs(narrative) if resolved.requires_narrative and narrative.strip() else []

    if render_as is RenderAs.HEADING:
        # A heading is one line by construction; anything after the first is
        # an authoring mistake, and dropping it silently would hide it.
        return [Heading(text=" ".join(chunks), level=clause.heading_level, clause_id=clause.id)]
    if render_as is RenderAs.SIGNATURE:
        return [Signature(lines=tuple(chunks))]
    if render_as is RenderAs.SECTION:
        nodes: list[Node] = [
            Heading(text=chunks[0], level=clause.heading_level, clause_id=clause.id)
        ]
        nodes.extend(Para(text=chunk, clause_id=clause.id) for chunk in chunks[1:])
        if resolved.variant.render_block is RenderBlock.TABLE and clause.repeating_block:
            nodes.append(_table_for(clause, rows))
        nodes.extend(Para(text=chunk, clause_id=clause.id) for chunk in tail)
        return nodes

    # The clause number belongs to the first paragraph only; continuation
    # paragraphs carry their own markers from the authored text.
    nodes = [
        Para(
            text=chunks[0],
            clause_id=clause.id,
            number=clause.number if number is None else number,
        )
    ]
    nodes.extend(Para(text=chunk, clause_id=clause.id) for chunk in chunks[1:])
    if resolved.variant.render_block is RenderBlock.TABLE and clause.repeating_block:
        nodes.append(_table_for(clause, rows))
    nodes.extend(Para(text=chunk, clause_id=clause.id) for chunk in tail)
    return nodes


def _rows_short(clause: Clause, resolved: ResolvedClause, rows: list[dict[str, Any]]) -> bool:
    """A table variant with fewer rows than the block requires."""
    block = clause.repeating_block
    if block is None or resolved.variant.render_block is not RenderBlock.TABLE:
        return False
    return len(rows) < block.min_rows
