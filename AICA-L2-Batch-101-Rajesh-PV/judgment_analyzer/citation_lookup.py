"""Optional online lookup of a judgment's reported citation (Gemini with Google Search grounding).

Orders downloaded from a tribunal or court website usually carry only the appeal number; reporters such
as Taxmann print a citation. Given the appeal number, forum, parties and date, this asks Gemini to search
the web for a reported citation. The answer is only a SUGGESTION: it is shown with the web sources found,
and the reviewer must check it before using it. Nothing from the judgment text is sent - only these facts.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

LOOKUP_SYSTEM = (
    "You find the reported citation of an Indian court or tribunal decision using web search. Report a "
    "citation ONLY if a search result shows it for this exact case (same appeal number or same parties, forum "
    "and date). Never construct or guess a citation. If none is found, say NONE."
)


@dataclass
class CitationSuggestion:
    citation: str = ""
    confidence: str = ""
    note: str = ""
    sources: list = field(default_factory=list)  # [(title, uri)]

    @property
    def found(self) -> bool:
        return bool(self.citation)


def lookup_prompt(facts: dict) -> str:
    return f"""Find the reported citation(s) (for example "[2026] 190 taxmann.com 964 (Chennai - Trib.)" or
"(2024) 160 ITD 1") for this decision:

Case: {facts.get('case_title', '')}
Appellant: {facts.get('appellant', '')}
Respondent: {facts.get('respondent', '')}
Forum / bench: {facts.get('court', '')}
Appeal / case number: {facts.get('case_number', '')}
Assessment year: {facts.get('assessment_year', '')}
Date of order: {facts.get('judgment_date', '')}

Reply in exactly this format:
CITATION: <citation as printed by the reporter, or NONE>
CONFIDENCE: <high / medium / low>
NOTE: <one line: which source shows it and how it matches (appeal number / parties / date)>"""


def parse_lookup(text: str) -> tuple[str, str, str]:
    def grab(label):
        m = re.search(rf"(?im)^\s*\**{label}\**\s*:\s*(.+)$", text or "")
        return m.group(1).strip().strip("*").strip() if m else ""
    citation = grab("CITATION")
    if citation.upper().startswith("NONE") or citation.lower() in ("not found", "n/a", "-"):
        citation = ""
    return citation, grab("CONFIDENCE").lower(), grab("NOTE")


def lookup_citation(client, facts: dict, cancel_event: threading.Event | None = None) -> CitationSuggestion:
    result = client.generate(lookup_prompt(facts), LOOKUP_SYSTEM, cancel_event=cancel_event, web_search=True,
                             max_output_tokens=1024)
    citation, confidence, note = parse_lookup(result.text)
    sources = result.sources or []
    if citation and not sources:
        # A citation with no web source behind it cannot be trusted.
        note = (note + " " if note else "") + "(No web source was returned, so this suggestion was discarded.)"
        citation = ""
    return CitationSuggestion(citation, confidence, note, sources[:5])
