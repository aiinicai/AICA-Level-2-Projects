"""Technical Knowledge Base built from the reviewer's reference materials.

knowledge_base/standards_paragraphs.json holds paragraph-level text of every Ind AS and AS
(extracted from the notified standards in the project's "IND AS & other laws" materials folder).

This module:
1. Replaces each finding's citation with a verified reference (Ind AS / AS paragraph numbers checked
   against the standard text; Schedule III items cited as per the 2021 amendment structure).
2. Attaches the actual requirement text of every cited Ind AS / AS paragraph to the finding, so the
   reviewer sees the source requirement next to the observation.
3. Supplies relevant paragraphs to the Gemini prompt (retrieval) so live AI findings are grounded.
"""

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "standards_paragraphs.json")

# Schedule III, Part I - Additional Regulatory Information. Division II item numbers verified against
# the Ind AS disclosure checklist in the materials folder; Division I is cited by description.
_ARI = "Additional Regulatory Information"
SCH3_ITEMS = {
    "SCH3-TITLE-DEEDS": ("6L(i)", f"{_ARI} - Title deeds of immovable property not held in name of the company"),
    "SCH3-LOANS-TO-PROMOTERS-KMPS": ("6L(v)", f"{_ARI} - Loans or advances to promoters, directors, KMPs and related parties"),
    "SCH3-CWIP-AGEING": ("6L(vi)", f"{_ARI} - Capital work-in-progress ageing schedule and completion schedule"),
    "SCH3-INTANGIBLE-CWIP": ("6L(vii)", f"{_ARI} - Intangible assets under development ageing schedule"),
    "SCH3-BENAMI-PROPERTY": ("6L(viii)", f"{_ARI} - Details of benami property held"),
    "SCH3-BANK-RETURNS-RECON": ("6L(ix)", f"{_ARI} - Borrowings secured against current assets (quarterly returns / statements)"),
    "SCH3-WILFUL-DEFAULTER": ("6L(x)", f"{_ARI} - Wilful defaulter"),
    "SCH3-STRUCK-OFF": ("6L(xi)", f"{_ARI} - Relationship with struck off companies"),
    "SCH3-ROC-CHARGES": ("6L(xii)", f"{_ARI} - Registration of charges or satisfaction with Registrar of Companies"),
    "SCH3-LAYERING": ("6L(xiii)", f"{_ARI} - Compliance with number of layers of companies"),
    "SCH3-RATIOS-OMISSION": ("6L(xiv)", f"{_ARI} - Ratios"),
    "SCH3-RATIOS-VARIANCE": ("6L(xiv)", f"{_ARI} - Ratios (explanation for change of more than 25%)"),
}

# Citations re-stated after checking the paragraph text in the knowledge base.
VERIFIED_REFS = {
    "SCH3-TP-AGEING": "Schedule III, {div}, Part I - General Instructions: Trade Payables ageing schedule (MCA Notification G.S.R. 207(E) dated 24.03.2021)",
    "SCH3-MSMED-SEC22": "Section 22 of the MSMED Act, 2006 read with Schedule III, {div}, Part I - General Instructions: Trade Payables",
    "SCH3-TR-AGEING": "Schedule III, {div}, Part I - General Instructions: Trade Receivables ageing schedule (MCA Notification G.S.R. 207(E) dated 24.03.2021)",
    "SCH3-PROMOTER-TABLE": "Schedule III, {div}, Part I - General Instructions: Share Capital - Shares held by promoters at the end of the year",
    "SCH3-EARMARKED-BANK": "Schedule III, {div}, Part I - General Instructions: Cash and cash equivalents / Bank balances (earmarked balances, margin money)",
    "SCH3-DIRECTOR-RECEIVABLES": "Schedule III, {div}, Part I - General Instructions: Trade Receivables (debts due by directors or other officers)",
    "SCH3-UNDISCLOSED-INCOME": "Schedule III, {div}, Part II - General Instructions: Additional Information - Undisclosed income",
    "SCH3-CRYPTO-CURRENCY": "Schedule III, {div}, Part II - General Instructions: Additional Information - Crypto currency or virtual currency",
    "SCH3-ROUNDING-OFF": "Schedule III - General Instructions for preparation of financial statements: Rounding off (based on Total Income)",
    "ARITH-BS-EQUATION": "Section 129(1) of the Companies Act, 2013 read with Schedule III, {div}, Part I",
    "ARITH-CFS-RECON": "Ind AS 7, Paragraph 45 / AS 3, Paragraph 42",
    "INDAS-16-PPE-POLICY": "Ind AS 16, Paragraphs 7, 12 and 13",
    "INDAS-19-MORTALITY": "Ind AS 19, Paragraph 144",
    "AS-15-MORTALITY": "AS 15, Paragraph 120(l)",
    "PPE-USEFUL-LIVES-JUSTIFICATION": "Schedule II to the Companies Act, 2013, Part A (justification for useful life different from Part C, supported by technical advice); Ind AS 16, Paragraph 73(c)",
    "AS-20-EPS-OMISSION": "AS 20, Paragraphs 8 and 48; Schedule III, Division I, Part II",
    "AS-9-REVENUE-POLICY": "AS 9, Paragraphs 11 to 14; AS 1, Paragraph 24",
    "SCH3-FOREX-UNHEDGED": "Ind AS 107, Paragraphs 33 and 34 (currency risk exposure)",
    "INDAS-12-TAX-RECON": "Ind AS 12, Paragraph 81(c)",
}

# Out-of-date clause letters used in earlier versions of the engine (e.g. "Clause 6(S)").
_STALE_CLAUSE = re.compile(r"\s*(?:under|per|as per)?\s*(?:Schedule III\s*)?Clause\s+6\([A-Z]{1,2}\)", re.I)
_CITE = re.compile(
    r"\b(Ind AS|AS)\s+(\d{1,3})(?:\s*\([^)]*\))?(?:,\s*|\s+)(?:Paragraphs?|Para\.?|paras?\.?)\s*"
    r"([A-Z]?\d{1,3}[A-Z]?(?:\([a-z]+\))?(?:\s*(?:,|and|&|to|-)\s*[A-Z]?\d{1,3}[A-Z]?(?:\([a-z]+\))?)*)"
    r"|\b(Ind AS)\s+(\d{1,3})\.(\d{1,3}[A-Z]?)\b"
)


@lru_cache(maxsize=1)
def _load() -> Dict[str, Dict[str, str]]:
    try:
        with open(KB_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class KnowledgeBase:
    """Looks up standard paragraphs and grounds findings in the reference materials."""

    @staticmethod
    def paragraph(standard: str, para: str) -> Optional[str]:
        para = re.sub(r"\([a-z]+\)$", "", para.strip())
        return _load().get(standard, {}).get(para)

    @staticmethod
    def find_paragraph(standard: str, phrase: str) -> Optional[Dict[str, str]]:
        """Locates the paragraph of a standard whose text contains the phrase (used to cite by content, not by memory)."""
        rx = re.compile(re.escape(phrase).replace(r"\ ", r"\s+"), re.I)
        for para, text in _load().get(standard, {}).items():
            if rx.search(text):
                return {"ref": f"{standard}.{para}", "para": para, "text": text}
        return None

    @classmethod
    def cited_paragraphs(cls, citation: str) -> List[Dict[str, str]]:
        """Returns [{'ref': 'Ind AS 19.145', 'text': ...}] for every paragraph in a citation string."""
        out, seen = [], set()
        for m in _CITE.finditer(citation or ""):
            if m.group(1):
                std, num = m.group(1), m.group(2)
                parts = re.split(r"\s*(?:,|and|&)\s*", m.group(3))
                expanded = []
                for p in parts:
                    rng = re.match(r"(\d+)\s*(?:to|-)\s*(\d+)$", p)
                    if rng and int(rng.group(2)) - int(rng.group(1)) <= 4:
                        expanded += [str(n) for n in range(int(rng.group(1)), int(rng.group(2)) + 1)]
                    else:
                        expanded.append(p)
            else:
                std, num, expanded = m.group(4), m.group(5), [m.group(6)]
            for p in expanded:
                key = f"{std} {num}.{p}"
                text = cls.paragraph(f"{std} {num}", p)
                if text and key not in seen:
                    seen.add(key)
                    out.append({"ref": key, "text": text})
        return out

    @staticmethod
    def verified_reference(rule_code: str, division: str, current: str) -> str:
        div = division or "Division II"
        if rule_code in SCH3_ITEMS:
            item, desc = SCH3_ITEMS[rule_code]
            if div == "Division I":
                return f"Schedule III, Division I, Part I - General Instructions: {desc} (MCA Notification G.S.R. 207(E))"
            return f"Schedule III, {div}, Part I - General Instructions para {item}: {desc} (MCA Notification G.S.R. 207(E))"
        if rule_code in VERIFIED_REFS:
            ref = VERIFIED_REFS[rule_code].format(div=div)
            if rule_code == "ARITH-CFS-RECON":
                return "AS 3, Paragraph 42" if div == "Division I" else "Ind AS 7, Paragraph 45"
            return ref
        return current

    @classmethod
    def enrich_issue(cls, issue: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """Applies verified citation, strips stale clause letters and attaches source requirement text."""
        item = dict(issue)
        code = item.get("rule_code", "")
        division = profile.get("schedule_iii_division", "Division II")
        current = item.get("statutory_ref") or item.get("technical_ref") or ""
        ref = cls.verified_reference(code, division, current)
        item["statutory_ref"] = ref
        for field in ("suggested_correction", "action", "description"):
            if item.get(field):
                item[field] = _STALE_CLAUSE.sub("", item[field]).replace(" .", ".").strip()
        paras = cls.cited_paragraphs(ref)
        item["source_requirements"] = paras
        item["requirement_text"] = " | ".join(f"[{p['ref']}] {p['text']}" for p in paras)
        return item

    @classmethod
    def retrieval_context(cls, doc_text: str, framework: str, limit_chars: int = 9000) -> str:
        """Selects disclosure paragraphs relevant to the document for grounding the Gemini prompt."""
        is_ind_as = "ind as" in (framework or "").lower()
        topics = {
            ("Ind AS 7", "AS 3"): r"cash\s+flow",
            ("Ind AS 16", "AS 10"): r"property,\s+plant|fixed\s+assets",
            ("Ind AS 19", "AS 15"): r"gratuity|employee\s+benefit",
            ("Ind AS 12", "AS 22"): r"deferred\s+tax",
            ("Ind AS 24", "AS 18"): r"related\s+part",
            ("Ind AS 37", "AS 29"): r"provision|contingent",
            ("Ind AS 2", "AS 2"): r"inventor",
            ("Ind AS 115", "AS 9"): r"revenue",
            ("Ind AS 116", "AS 19"): r"lease",
            ("Ind AS 33", "AS 20"): r"earnings\s+per\s+share|profit\s+for\s+the\s+year",
            ("Ind AS 108", "AS 17"): r"segment",
            ("Ind AS 21", "AS 11"): r"foreign\s+currency",
        }
        kb = _load()
        chunks, used = [], 0
        for (ind, legacy), pat in topics.items():
            if not re.search(pat, doc_text or "", re.I):
                continue
            std = ind if is_ind_as else legacy
            for para, text in kb.get(std, {}).items():
                if re.search(r"\b(shall|should) disclose\b|\bshall present\b", text):
                    piece = f"[{std}.{para}] {text[:400]}"
                    if used + len(piece) > limit_chars:
                        return "\n".join(chunks)
                    chunks.append(piece)
                    used += len(piece)
        return "\n".join(chunks)
