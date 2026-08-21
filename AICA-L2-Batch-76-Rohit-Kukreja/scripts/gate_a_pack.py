"""Build the Gate A review pack. Review and Sign-Off Protocol, Gate A.

    python scripts/gate_a_pack.py [--out DIR]

Gate A is the signing partner reading the statutory wording. 189 clauses of
YAML is not something anyone can read; six rendered documents in the
scenarios that actually differ is. This script produces those, plus the two
lists a reviewer needs beside them:

  QUESTIONS.md    every question the clause files raise, in one place
  PROVENANCE.md   which wording came from the firm's own precedents and
                  which I wrote, per clause

The provenance list is the important one. Roughly two in five bodies are
adapted from a precedent the firm already signs; the rest are mine, because
the precedents are all clean-opinion files and show only the nil case. The
ones marked AUTHORED are where a reading error would go unnoticed.

Nothing here touches the application database. Scenarios are built directly
from the clause repository so the pack is reproducible and cannot disturb
real engagement data.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clauses.loader import load_clause_set
from app.clauses.model import CONTEXT_VARIABLES, Clause, ClauseSet, DataType
from app.config import get_settings
from app.render import docx as docx_renderer
from app.services.document import BuiltDocument, build_document

FY_END = date(2026, 3, 31)

DOCUMENTS = (
    "engagement_letter",
    "auditors_report",
    "caro_2020",
    "ifc_report",
    "mrl",
    "directors_report",
)

# A specimen firm and client. Deliberately not a real one — the pack is
# about the wording, and a plausible name invites the reader to check the
# facts instead of the prose.
BASE_CONTEXT: dict[str, str] = {
    "company_name": "Specimen Private Limited",
    "cin": "U00000XX2010PTC000000",
    "registered_addr": "1 Specimen Road, Mumbai 400001",
    "fy_code": "2025-26",
    "financial_year": "2025-26",
    "fy_start_long": "1st April, 2025",
    "fy_end_long": "31st March, 2026",
    "fy_end_numeric": "31-03-2026",
    "place": "Mumbai",
    "framework_ref": "Companies (Accounting Standards) Rules, 2021",
    "framework": "igaap",
    "opinion_type": "clean",
    "going_concern": "none",
    "report_date_long": "1st September, 2026",
    "firm_name": "Your Firm Name",
    "firm_frn": "000000W",
    "firm_address": "1 Specimen Street, Mumbai 400001",
    "partner_name": "Signing Partner",
    "partner_mno": "000000",
    "udin": "26000000AAAAAA0000",
}

# No square brackets: §18.4's pre-export scan treats "[...]" as an
# unresolved placeholder and would block every document in the pack. It was
# right to — the guard caught this text on the first run.
SPECIMEN_NARRATIVE = (
    "SPECIMEN NARRATIVE. This text is typed by the user for each engagement and "
    "is not part of the clause repository. It appears here only so that the "
    "wording around it can be read in context."
)


@dataclass(frozen=True)
class Scenario:
    """One set of answers, chosen to exercise wording that differs."""

    key: str
    title: str
    why: str
    applicable: frozenset[str]
    context: dict[str, str] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="01-clean-private-company",
        title="Clean private company — CARO applies, IFC exempt",
        why=(
            "The commonest file. Everything nil, opinion unmodified. If the "
            "wording is wrong here it is wrong on most engagements."
        ),
        applicable=frozenset({"caro"}),
        answers={
            "iar.resp.auditor": "ifc_exempt",
            "iar.143.3.i": "exempt",
            "iar.197.16": "na",
            "eng.ifc.scope": "exempt",
            "eng.header": "continuing",
        },
    ),
    Scenario(
        key="02-qualified-opinion",
        title="Qualified opinion",
        why=(
            "Checks that the Basis for Qualified Opinion section, the opinion "
            "paragraph and the Board's Report explanation all agree, and that "
            "the description of the matter is actually printed."
        ),
        applicable=frozenset({"caro"}),
        context={"opinion_type": "qualified"},
        answers={
            "iar.resp.auditor": "ifc_exempt",
            "iar.143.3.i": "exempt",
            "iar.197.16": "na",
            "eng.ifc.scope": "exempt",
            "eng.header": "continuing",
        },
    ),
    Scenario(
        key="03-ifc-applicable",
        title="IFC reporting applies — Annexure B issued",
        why=(
            "The one decision that spans three documents. The section "
            "143(3)(i) paragraph, the Annexure B heading and opinion, and the "
            "engagement letter must all use the same statutory phrase."
        ),
        applicable=frozenset({"caro", "ifc"}),
        answers={
            "iar.resp.auditor": "ifc_applicable",
            "iar.143.3.i": "unmodified",
            "iar.197.16": "na",
            "eng.ifc.scope": "applicable",
            "eng.header": "continuing",
        },
    ),
    Scenario(
        key="04-branch-audited-by-another",
        title="Branch audited by another auditor",
        why=(
            "The only scenario in which the section 143(3) paragraphs are "
            "lettered differently. Statutory (c) appears and every letter "
            "below it shifts. Check the letters run (a) to (h) with no gap."
        ),
        applicable=frozenset({"caro"}),
        answers={
            "iar.143.3.c": "by_other",
            "iar.143.3.b": "kept_with_branch_returns",
            "iar.resp.auditor": "ifc_exempt",
            "iar.143.3.i": "exempt",
            "iar.197.16": "na",
            "eng.ifc.scope": "exempt",
            "eng.experts": "branch",
            "eng.header": "continuing",
        },
    ),
    Scenario(
        key="05-caro-exempt",
        title="CARO does not apply",
        why=(
            "Checks that nothing references an annexure the tool has not "
            "produced. The CARO annexure should be empty and the auditor's "
            "report should say the Order does not apply."
        ),
        applicable=frozenset(),
        answers={
            "iar.caro.ref": "exempt",
            "iar.resp.auditor": "ifc_exempt",
            "iar.143.3.i": "exempt",
            "iar.197.16": "na",
            "eng.ifc.scope": "exempt",
            "eng.header": "continuing",
        },
    ),
    Scenario(
        key="06-exceptions-throughout",
        title="Every exception path",
        why=(
            "The last option of every clause, so that no exception wording "
            "escapes review by never being rendered. Not a realistic file — "
            "read it as a wording checklist, not as a document."
        ),
        applicable=frozenset({"caro", "ifc", "s197", "csr", "internal_audit", "secretarial_audit"}),
        context={"opinion_type": "adverse", "going_concern": "material_uncertainty"},
        answers={},  # filled with the LAST option of every clause below
    ),
)


def _cell(datatype: DataType) -> Any:
    if datatype in (DataType.AMOUNT, DataType.NUMBER):
        return Decimal("4260000")
    if datatype is DataType.DATE:
        return date(2025, 10, 17)
    return "Specimen"


def _answers_for(clauses: list[Clause], scenario: Scenario) -> dict[str, Any]:
    """First option of every clause, then the scenario's overrides.

    The "every exception" scenario takes the last option instead, which is
    the convention every clause in the repository follows: nil first,
    exception last.
    """
    last = scenario.key.startswith("06")
    out: dict[str, Any] = {}
    for clause in clauses:
        # Every clause gets a narrative, not only those with an input:
        # `iar.basis.modified` and `bdr.auditor.remarks` have none, because
        # they branch on the engagement's opinion type, and they still
        # require the matter to be described.
        out[f"{clause.id}.narrative"] = SPECIMEN_NARRATIVE
        if clause.input is None or not clause.input.options:
            continue
        options = clause.input.options
        out[clause.input.key] = (options[-1] if last else options[0]).value
    out.update(scenario.answers)
    return out


def _child_rows(clauses: list[Clause]) -> dict[str, list[dict[str, Any]]]:
    return {
        c.id: [{col.key: _cell(col.datatype) for col in c.repeating_block.columns}]
        for c in clauses
        if c.repeating_block is not None
    }


def _build(clause_set: ClauseSet, document_id: str, scenario: Scenario) -> BuiltDocument:
    clauses = list(clause_set.for_document(document_id, FY_END))
    context = {**BASE_CONTEXT, **scenario.context}
    missing = CONTEXT_VARIABLES - set(context)
    if missing:  # pragma: no cover - guards a typo in BASE_CONTEXT
        raise SystemExit(f"BASE_CONTEXT is missing {sorted(missing)}")
    return build_document(
        clause_set,
        document_id,
        FY_END,
        responses=_answers_for(clauses, scenario),
        child_rows=_child_rows(clauses),
        context=context,
        applicable=scenario.applicable,
    )


# --------------------------------------------------------------------------
# Provenance and questions, read out of the clause files themselves
# --------------------------------------------------------------------------

_FIRM = re.compile(r"^\s*#.*\bfirm wording\b", re.I | re.M)
_AUTHORED = re.compile(r"^\s*#.*\bAUTHORED\b", re.M)

# Phrases I used in the clause files when something needs the partner,
# split by what the partner has to do about it. Everything authored is
# flagged somewhere; only the first tier is a question that blocks.
# Directive forms only. A bare "Gate A" also appears in boilerplate that
# merely explains what Gate A is for, and matching it swept 48 clauses into
# the list that ask nothing.
_DECISIONS = (
    "CONFIRM AT GATE A",
    "NOTE FOR GATE A",
    "WORTH A LOOK AT GATE A",
    "NOT SETTLED",
    "DISCREPANCY",
    "IS A DERIVATION",
    "UNCONFIRMED",
    "FOR THE PARTNER",
    "MUST CONFIRM",
)
_DEPARTURES = (
    "NOT IN THE REGISTER",
    "ORDER CHANGED",
    "LANGUAGE CHANGED",
    "VOICE NORMALISED",
    "REPLACES THE EARLIER",
    "CITATION CORRECTED",
    "ORDER CHANGED FROM THE REGISTER",
)


def _comment_blocks(text: str) -> list[str]:
    """Contiguous runs of `#` comment lines, as paragraphs."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        elif current:
            blocks.append(" ".join(current).strip())
            current = []
    if current:
        blocks.append(" ".join(current).strip())
    return [b for b in blocks if b]


def _clause_files(content: Path) -> list[tuple[str, Path, str]]:
    out: list[tuple[str, Path, str]] = []
    for path in sorted(content.rglob("*.yaml")):
        if path.name in {"manifest.yaml", "applicability_rules.yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^id:\s*(\S+)\s*$", text, re.M)
        if match:
            out.append((match.group(1), path, text))
    return out


def write_provenance(content: Path, out: Path, clause_set: ClauseSet) -> None:
    root = content.parent
    by_document: dict[str, list[str]] = {}
    totals = {"firm": 0, "authored": 0}

    for clause_id, path, text in _clause_files(content):
        clause = clause_set.get(clause_id)
        firm = len(_FIRM.findall(text))
        authored = len(_AUTHORED.findall(text))
        totals["firm"] += firm
        totals["authored"] += authored
        mark = "**AUTHORED**" if authored and not firm else ("firm" if firm else "—")
        by_document.setdefault(clause.document, []).append(
            f"| `{clause_id}` | {clause.title} | {clause.clause_ref} | {mark} | "
            f"{firm} | {authored} | `{path.relative_to(root).as_posix()}` |"
        )

    lines = [
        "# Gate A — provenance of every clause",
        "",
        "Read the rows marked **AUTHORED** first. Those are bodies I wrote because",
        "the firm's precedents are clean-opinion files and show only the nil case:",
        "the exception wording, the modified opinions, the non-compliance paragraphs.",
        "A mistake there is a mistake nobody has ever signed off.",
        "",
        "Rows marked `firm` are adapted from a precedent the firm already issues.",
        "They still need reading — adapting is not copying — but the risk is lower.",
        "",
        f"Counted across the repository: **{totals['firm']} firm-sourced** comments and",
        f"**{totals['authored']} authored** comments across {len(clause_set)} clauses.",
        "",
    ]
    for document in DOCUMENTS:
        rows = by_document.get(document, [])
        lines += [
            f"## {clause_set.documents[document].title}",
            "",
            "| Clause | Title | Reference | Source | firm | authored | File |",
            "|---|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    (out / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


def _collect(content: Path, clause_set: ClauseSet, markers: tuple[str, ...]) -> list[str]:
    root = content.parent
    entries: list[str] = []
    for clause_id, path, text in _clause_files(content):
        clause = clause_set.get(clause_id)
        hits = [
            block
            for block in _comment_blocks(text)
            if any(marker in block.upper() for marker in markers)
        ]
        if not hits:
            continue
        entries.append(f"### `{clause_id}` — {clause.title}\n")
        entries.append(f"*{clause.clause_ref}* · `{path.relative_to(root).as_posix()}`\n")
        for block in hits:
            entries.append(f"- [ ] {block}\n")
        entries.append("")
    return entries


def write_questions(content: Path, out: Path, clause_set: ClauseSet) -> None:
    decisions = _collect(content, clause_set, _DECISIONS)
    departures = _collect(content, clause_set, _DEPARTURES)

    rules = (content / "applicability_rules.yaml").read_text(encoding="utf-8")
    unconfirmed = len(re.findall(r"needs_review:\s*true", rules))
    total_rules = len(re.findall(r"needs_review:\s*(?:true|false)", rules))

    lines = [
        "# Gate A — questions for the signing partner",
        "",
        "Every one of these is written into the clause file it belongs to. This is",
        "the same text, collected so it can be worked through in one sitting.",
        "",
        "Each box is a decision only the partner can take: a wording choice, a",
        "citation I could not confirm, or a departure from the firm's own",
        "precedent that I made deliberately and flagged rather than hid.",
        "",
        "## Thresholds",
        "",
        (
            f"`content/applicability_rules.yaml` holds {total_rules} applicability rules. "
            + (
                f"**{unconfirmed} still marked `needs_review` and unconfirmed.**"
                if unconfirmed
                else "**All confirmed by the partner** — see decision 23 in "
                "docs/GATE_A_DECISIONS.md."
            )
        ),
        "",
        "They decide whether CARO, IFC reporting, CSR, internal audit, secretarial",
        "audit and Key Audit Matters apply at all. A wrong threshold does not produce",
        "wrong wording — it produces a document that should never have been generated,",
        "or omits one that should have been, and nothing in the tool will flag it.",
        "",
        (
            "- [x] Thresholds confirmed 17 August 2026."
            if not unconfirmed
            else "- [ ] Confirm all applicability thresholds against the current rules."
        ),
        "",
        "## Decisions — these need an answer",
        "",
        "Wording I could not settle, citations I could not confirm, and points where",
        "the firm's own precedent and my reading of the statute disagree.",
        "",
        *decisions,
        "## Departures — these need noting, not deciding",
        "",
        "Places where I deliberately did something other than what the precedent or",
        "the approved register said, and said so. Each is defensible; none is hidden.",
        "Reject any of them and it is a small edit.",
        "",
        *departures,
    ]
    (out / "QUESTIONS.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "gate_a_pack",
        help="output directory (created if absent)",
    )
    args = parser.parse_args()

    content = get_settings().content_path
    clause_set = load_clause_set(content)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    index = [
        "# Gate A review pack",
        "",
        f"Clause repository `{clause_set.manifest.template_version}` · "
        f"{len(clause_set)} clauses · FY ending {FY_END.strftime('%d-%m-%Y')}",
        "",
        "Every clause in the repository is still marked `needs_review`. Nothing here",
        "has been approved; this pack exists so that it can be.",
        "",
        "Start with **PROVENANCE.md** to see which wording is the firm's and which is",
        "mine, then **QUESTIONS.md** for the decisions I could not take. The documents",
        "below are the same clauses rendered, so the prose can be read as a document",
        "rather than as YAML.",
        "",
        "Amounts, dates and narratives in these files are specimen values. The wording",
        "around them is what is under review.",
        "",
    ]

    written = 0
    for scenario in SCENARIOS:
        folder = out / scenario.key
        folder.mkdir(exist_ok=True)
        index += [f"## {scenario.title}", "", scenario.why, ""]

        for document_id in DOCUMENTS:
            built = _build(clause_set, document_id, scenario)
            title = clause_set.documents[document_id].title
            path = folder / f"{document_id}.docx"
            docx_renderer.render(
                built.document,
                path,
                client_name=BASE_CONTEXT["company_name"],
                fy_code=f"FY {BASE_CONTEXT['fy_code']}",
            )
            written += 1

            notes = []
            if built.not_applicable:
                notes.append(f"{len(built.not_applicable)} clause(s) not applicable")
            if built.omitted:
                notes.append(f"{len(built.omitted)} omitted by design")
            if built.exceptions:
                notes.append(f"{len(built.exceptions)} exception(s)")
            if not built.exportable:
                notes.append(f"**{built.blocking_count} BLOCKING**")
            index.append(
                f"- [{title}]({scenario.key}/{document_id}.docx)"
                + (f" — {'; '.join(notes)}" if notes else "")
            )
        index.append("")

    write_provenance(content, out, clause_set)
    write_questions(content, out, clause_set)
    (out / "README.md").write_text("\n".join(index), encoding="utf-8")

    print(f"Gate A pack written to {out}")
    print(f"  {written} documents across {len(SCENARIOS)} scenarios")
    print("  README.md, PROVENANCE.md, QUESTIONS.md")


if __name__ == "__main__":
    main()
