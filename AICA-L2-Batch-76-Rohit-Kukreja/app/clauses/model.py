"""Clause repository domain model. Build Prompt v2 §3.1 and §3.2.

No statutory sentence appears in this file, or in any other `.py` file
(§18.2). Everything here describes *shape*; the words live in `content/`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class CarryForward(StrEnum):
    """Rollover policy. Build Prompt v2 §6.1 — this vocabulary is closed."""

    ALWAYS = "always"
    PROMPT = "prompt"
    NEVER = "never"


class DataType(StrEnum):
    SELECT = "select"
    TEXT = "text"
    LONGTEXT = "longtext"
    AMOUNT = "amount"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    COMPUTED = "computed"
    STATIC = "static"


class Severity(StrEnum):
    """Feeds the consistency engine (§9)."""

    INFO = "info"
    EXCEPTION = "exception"


class RenderBlock(StrEnum):
    TABLE = "table"


class RenderAs(StrEnum):
    """What kind of node a clause becomes.

    A statutory report is not a wall of paragraphs: "Basis for Opinion" and
    "Report on Other Legal and Regulatory Requirements" are headings, and the
    firm name / FRN / partner / membership number / UDIN block is a signature
    block. Rendering those as body paragraphs is how the prototype produced
    documents that had to be re-formatted by hand before signing.
    """

    PARA = "para"
    HEADING = "heading"
    SIGNATURE = "signature"
    SECTION = "section"
    """First paragraph is the section heading, the rest are body paragraphs.

    "Basis for Opinion", "Key Audit Matters" and the two responsibilities
    sections are each one clause whose text opens with its own heading. Split
    into a separate heading clause they would be two rows the partner has to
    keep in step; rendered as plain paragraphs the DOCX export loses every
    section break in the report.
    """


CONTEXT_VARIABLES: frozenset[str] = frozenset(
    {
        "company_name",
        "cin",
        "registered_addr",
        "fy_code",
        "financial_year",
        "fy_start_long",
        "fy_end_long",
        "fy_end_numeric",
        "place",
        "framework_ref",
        "framework",
        # Whether the financial statements include a cash flow statement.
        # Section 2(40) proviso: a One Person Company, a small company, a
        # dormant company and a start-up private company need not include one.
        # NOT a property of private companies generally -- dropping it for
        # every private company would be wrong, and that is the reading the
        # request arrived with.
        "cash_flow_required",
        # True when the profile records a subsidiary, an associate or a joint
        # venture. Rule 8(5)(iv) needs the nil paragraph in every other case,
        # and the profile already carries all three flags -- so the Board's
        # Report derives the answer instead of asking for it again.
        "has_group_companies",
        # Clause (e) of s.134(5) -- the internal financial controls limb of the
        # Directors' Responsibility Statement -- applies by its own words only
        # "in the case of a listed company". Printing it for an unlisted
        # company states something the directors are not required to state and
        # may not be able to.
        "is_listed_company",
        # s.92(3)/s.134(3)(a): the Board's Report gives the web address where
        # the annual return is placed. A company with no website has none.
        "has_website",
        # s.148(1): whether the company is in an industry for which the Central
        # Government has specified cost records.
        "cost_records_required",
        # CARO 3(iii). Whether the year had any of the transactions the
        # clause's chapeau makes (a) to (f) conditional on -- loans, advances,
        # guarantees, security, investments. Derived from the answers to (a)(A),
        # (a)(B) and the chapeau question, never asked again.
        "caro_no_loans_granted",
        "caro_nothing_under_iii",
        # Rule 8(5)(iii). Whether anyone joined or left the Board during the
        # year, read from the client's own register -- the same register the
        # disclosure's table is built from. Without this the answer defaulted
        # to "no change" while the table underneath it listed two.
        "directors_changed_in_year",
        # MGT-9 Part I. Recorded on the client, not the profile: a company's
        # date of incorporation does not change, so it is not versioned.
        "date_of_incorp_long",
        "opinion_type",
        "going_concern",
        "report_date_long",
        "firm_name",
        "firm_frn",
        "firm_address",
        "partner_name",
        "partner_mno",
        "udin",
    }
)
"""Names a clause's `when` expression and `{{ }}` tokens may use.

Declared here, next to the clause model, so the loader can reject a typo at
load time instead of at render time — an expression naming a variable that
does not exist would otherwise raise while a document was being built, which
is the worst moment to find out. `render_context_for` must supply exactly
this set, and `test_render_context.py` fails if the two drift apart.
"""


AUTO_ALPHA = "auto:alpha"
"""A `number` meaning "letter me by my position among the paragraphs that print".

Most statutory numbering is fixed by the instrument — CARO clause (ix)(a) is
(ix)(a) whatever else appears — so `number` is normally a literal string. The
section 143(3) paragraphs are the exception: a firm letters them (a), (b),
(c)... down the list it actually prints, so a conditional paragraph appearing
or disappearing shifts every letter below it.

Hard-coding those letters would produce a correctly worded report with the
wrong references the first time a client has a branch audited by another
auditor. Clauses carrying this marker are lettered at build time instead.
The clause *id* still holds the statutory letter, so the two never merge.
"""


@dataclass(frozen=True, slots=True)
class ClauseOption:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class InputDefault:
    """An answer the master data supplies, so the user is not asked for it.

    `when` is evaluated against the engagement's context -- the same restricted
    expression language a variant uses. The first default whose condition holds
    provides the answer, and only when the user has not answered themselves, so
    a derived answer is always overridable from the questionnaire.

    Why this exists: an unanswered mandatory input makes the whole clause vanish
    from the document (`document.build`), so a disclosure the firm never
    consciously skipped goes missing from a draft Board's Report. Deriving the
    common answer from what the profile already records removes the unanswered
    state rather than reporting it.
    """

    when: str | None
    value: str


@dataclass(frozen=True, slots=True)
class ClauseInput:
    key: str
    datatype: DataType
    label: str = ""
    carry_forward: CarryForward = CarryForward.PROMPT
    mandatory: bool = True
    options: tuple[ClauseOption, ...] = ()
    defaults: tuple[InputDefault, ...] = ()

    @property
    def option_values(self) -> frozenset[str]:
        return frozenset(o.value for o in self.options)


@dataclass(frozen=True, slots=True)
class RepeatingColumn:
    key: str
    label: str
    datatype: DataType
    required: bool = False
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FixedRow:
    """One line of a FIXED schedule -- a table whose rows are not the user's to
    choose (§3.2, decision 73).

    A free table asks "what are the particulars?" and gets a different answer
    from every article assistant. Where a statutory format prescribes the lines
    and their order, the lines are declared here and only the figures are
    typed.

    `computed` is a sum of other rows in the same schedule, by key. A computed
    row is never typed: it is recalculated whenever the schedule is saved, so a
    sub-total cannot be left disagreeing with the lines above it.
    """

    key: str
    particulars: str
    computed: str | None = None

    @property
    def is_computed(self) -> bool:
        return self.computed is not None


@dataclass(frozen=True, slots=True)
class RepeatingBlock:
    """A table of child records rather than a single answer (§3.2)."""

    entity: str
    columns: tuple[RepeatingColumn, ...]
    when: str | None = None
    min_rows: int = 0
    carry_forward: CarryForward = CarryForward.PROMPT
    fixed_rows: tuple[FixedRow, ...] = ()

    @property
    def column_keys(self) -> tuple[str, ...]:
        return tuple(c.key for c in self.columns)

    @property
    def is_schedule(self) -> bool:
        """True when the rows are prescribed and only the figures are typed."""
        return bool(self.fixed_rows)

    @property
    def amount_columns(self) -> tuple[str, ...]:
        """The columns a schedule takes figures in -- every column but the
        first, which carries the prescribed particulars."""
        return tuple(c.key for c in self.columns if c.datatype is DataType.AMOUNT)


@dataclass(frozen=True, slots=True)
class ClauseVariant:
    """One rendering of a clause, selected by its `when` expression.

    `when is None` marks the fallback variant. A clause with no matching
    variant is a hard error, never a silent skip (§3.3).
    """

    body: str
    when: str | None = None
    requires_narrative: bool = False
    severity: Severity | None = None
    render_block: RenderBlock | None = None
    render_as: RenderAs | None = None
    """Overrides the clause's own `render_as` for this variant only.

    Needed because heading-ness is not always a property of the clause. The
    standard "Basis for Opinion" paragraph owns its heading when the opinion
    is clean, but when the opinion is modified the heading has already been
    printed by the clause that describes the modification — so the same
    clause is a section in one case and a plain paragraph in another.
    """
    omit: bool = False
    """Drop the clause from the document instead of printing it.

    Distinct from a clause that prints "not applicable": some paragraphs are
    reported only when the matter arises, and the firm's report format simply
    has no paragraph for them otherwise. Section 143(3)(c) is the case — with
    no branch audited by another auditor there is nothing to report and no
    para is printed, which is why the surrounding letters have to be
    positional (see `AUTO_ALPHA`).

    An omitted variant still needs a body: it is what the preview shows in
    place of the clause, so a reviewer can see the clause was considered and
    deliberately left out rather than lost.
    """


@dataclass(frozen=True, slots=True)
class Clause:
    id: str
    document: str
    order: int
    title: str
    clause_ref: str
    variants: tuple[ClauseVariant, ...]
    number: str = ""
    effective_from: date | None = None
    effective_to: date | None = None
    requires: tuple[str, ...] = ()
    input: ClauseInput | None = None
    repeating_block: RepeatingBlock | None = None
    optional: bool = False
    needs_review: bool = False
    source_path: str = ""
    render_as: RenderAs = RenderAs.PARA
    heading_level: int = 2

    def in_force(self, fy_end: date) -> bool:
        """Effective-date filter against the engagement's FY end (§3.3)."""
        if self.effective_from is not None and fy_end < self.effective_from:
            return False
        return self.effective_to is None or fy_end <= self.effective_to

    @property
    def is_static(self) -> bool:
        return self.input is None


class IssuedBy(StrEnum):
    """Whose letterhead a document goes out on.

    Not a formatting preference. A Management Representation Letter is written
    BY the company TO the auditor, and a Board's Report is issued by the
    directors — putting the audit firm's letterhead on either makes the auditor
    appear to have written the client's own representations. The other four are
    the firm's own documents.
    """

    FIRM = "firm"
    COMPANY = "company"


@dataclass(frozen=True, slots=True)
class DocumentTemplate:
    id: str
    title: str
    clause_ids: tuple[str, ...] = ()
    short_title: str = ""
    """What a person calls this document.

    The statutory titles run to nine words -- "Annexure A to the Independent
    Auditor's Report - CARO 2020" -- which is right at the head of the document
    and wrong on a navigation card. Declared in the manifest beside the full
    title, never derived in a template: an abbreviation of a statutory
    instrument is content, and content does not belong in markup.

    Falls back to `title`, so a document that has not been given one is merely
    verbose rather than nameless."""
    issued_by: IssuedBy = IssuedBy.FIRM
    """Declared per document in the manifest, defaulting to the firm.

    In the manifest rather than in code because it is a fact about the
    instrument, alongside its title — and because a document added later should
    have to state whose paper it is."""


@dataclass(frozen=True, slots=True)
class Manifest:
    template_version: str
    changelog: tuple[str, ...] = ()
    reviewed_on: date | None = None
    reviewed_by: str = ""
    review_method: str = ""
    """How Gate A was actually conducted.

    Clearing `needs_review` on a clause records that the firm has approved
    its wording. Nothing else in the repository says who approved it, when,
    or on what basis — so a blanket sign-off and a clause-by-clause reading
    would leave identical traces. They are not the same event and a later
    reader is entitled to know which one happened.

    `review_method` is free text and is meant to be honest: "clause by
    clause", "blanket sign-off on the partner's instruction", "sampled".
    """


@dataclass(slots=True)
class ClauseSet:
    """Every clause loaded from `content/`, indexed for lookup."""

    manifest: Manifest
    clauses: tuple[Clause, ...] = ()
    documents: dict[str, DocumentTemplate] = field(default_factory=dict)
    # slots=True means every attribute must be declared; a plain assignment
    # in __post_init__ would raise.
    _by_id: dict[str, Clause] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {c.id: c for c in self.clauses}

    def get(self, clause_id: str) -> Clause:
        try:
            return self._by_id[clause_id]
        except KeyError:
            raise KeyError(f"clause not found: {clause_id}") from None

    def __contains__(self, clause_id: object) -> bool:
        return clause_id in self._by_id

    def __len__(self) -> int:
        return len(self.clauses)

    def for_document(self, document: str, fy_end: date | None = None) -> tuple[Clause, ...]:
        """Clauses of one document in render order, optionally date-filtered."""
        found = [c for c in self.clauses if c.document == document]
        if fy_end is not None:
            found = [c for c in found if c.in_force(fy_end)]
        return tuple(sorted(found, key=lambda c: (c.order, c.id)))

    @property
    def needs_review(self) -> tuple[Clause, ...]:
        """Clauses whose wording is not yet settled (§19, protocol §5)."""
        return tuple(c for c in self.clauses if c.needs_review)
