"""AI Reviewer (optional, Gemini) with hallucination controls.

The AI is used only to find additional evidence-based matters that deterministic checks cannot (e.g. a
policy that contradicts a note, a narrative that conflicts with the figures). Every AI observation must
quote the financial statements verbatim; an observation is discarded unless
  - each quoted extract is actually found in the uploaded document,
  - every amount it relies on appears in the document,
  - it is not a bare checklist point (absence of a "negative statement"), and
  - it does not duplicate an observation already raised by the review engine.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.fs_model import FSModel
from core.knowledge_base import KnowledgeBase
from core.review_engine import NATURES

MODEL = "gemini-2.5-flash"

PRINCIPLES = """You are a Technical Reviewer of the Financial Reporting Review Board (FRRB) of ICAI reviewing general purpose
financial statements. Think like a professional reviewer, not a checklist:
1. Accuracy over quantity: report only material, relevant, substantiated deviations. Fewer, stronger observations are better.
2. Applicability first: before any check, establish from the statements that the item / transaction exists. Never report a
   requirement for an item that is nil or absent (e.g. no CWIP -> no CWIP ageing observation).
3. No hallucination: every observation must quote the statements verbatim and give the location (statement / note / row).
4. Never report a checklist point merely because a statement is absent (e.g. benami property, crypto currency, wilful
   defaulter, struck-off companies, layers) - these are required only where the situation exists.
5. Prefer cross-checks: face vs notes, note vs note, policy vs note, ratio table vs workings, related-party note vs balances.
6. Classify each observation as exactly one of: Non-compliance, Inconsistency, Disclosure gap, Potential concern, Requires verification.
"""

EXEMPLARS = """Examples of the expected quality (from the reviewer's past FRRB Technical Review reports):
- Ind AS 24: "Note 28 discloses inter-corporate deposits of Rs. 38,700 lakhs from APL Infrastructure Pvt. Ltd. with interest of
  Rs. 173.40 lakhs and rent of Rs. 2.95 lakhs, but APL Infrastructure Pvt. Ltd. is not included in the related-party list in
  Note 28(A)." Requirement: Ind AS 24 para 18.
- Ind AS 1: "The Statement of Profit and Loss reports OCI of Rs 6.46 lakhs and TCI of Rs 381.09 lakhs, whereas the SOCIE shows OCI
  of Rs 6.13 lakhs and TCI of Rs 380.76 lakhs - the two primary statements do not reconcile." Requirement: Ind AS 1 para 106.
- Ind AS 7: "The policy defines cash equivalents as deposits with original maturity of less than 12 months; Note 10 includes such
  deposits of Rs 2,367.44 lakhs in cash and cash equivalents." Requirement: Ind AS 7 paras 6, 7 and 45.
- Schedule III: "Working capital used in Note 34 for the current ratio, net capital turnover and ROCE excludes MSME trade payables
  and does not reconcile with current assets and current liabilities in the Balance Sheet."
"""

SCHEMA = """Return ONLY a JSON list. Each element:
{"title": "Ind AS 24 | Schedule III ...", "sub_title": "short topic", "nature": "Non-compliance|Inconsistency|Disclosure gap|Potential concern|Requires verification",
 "view": "the reviewer's observation, 2-5 sentences, with the figures", "matter": "what the statements say, with locations",
 "evidence_quotes": ["verbatim extract 1 copied exactly from the statements", "verbatim extract 2"],
 "requirement_refs": ["Ind AS 1, Paragraph 106"], "suggested_correction": "...", "significance": "High|Medium|Low"}
Return [] if you find nothing beyond the observations already raised."""

NEGATIVE_TOPICS = re.compile(r"benami|crypto|virtual currency|wilful defaulter|struck[- ]off|layers|undisclosed income|scheme of arrangement", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[\s|]+", " ", re.sub(r"\[[^\]]*\]", " ", s or "")).strip().lower()


class AIReviewer:

    @classmethod
    def review(cls, model: FSModel, profile: Dict[str, Any], engine_findings: List[Dict[str, Any]],
               checks: List[Dict[str, str]], api_key: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        raw = cls._call(cls._prompt(model, profile, engine_findings, checks), api_key)
        return cls.validate(raw, model, engine_findings)

    @staticmethod
    def _prompt(model: FSModel, profile: Dict[str, Any], findings: List[Dict[str, Any]], checks: List[Dict[str, str]]) -> str:
        na = [f"{c['Area']}: {c['Applicability basis (from the financial statements)']}" for c in checks if c["Applicable"] == "No"]
        raised = [f"- {f['title']} / {f['sub_title']}: {f['view'][:160]}" for f in findings]
        prof = {k: v for k, v in profile.items() if k in ("company_type", "listed", "framework", "schedule_iii_division", "financial_year",
                                                           "unit", "small_company", "smc", "cin")}
        context = KnowledgeBase.retrieval_context(model.full_text, profile.get("framework", ""), limit_chars=8000)
        return "\n\n".join([
            PRINCIPLES, EXEMPLARS,
            f"Entity profile (detected from the statements): {json.dumps(prof)}",
            "Areas established as NOT applicable (do not report on these):\n" + "\n".join(na[:40]),
            "Observations already raised (do not repeat):\n" + ("\n".join(raised) or "none"),
            "Requirement text available from the notified standards:\n" + context,
            "Financial statements (each line prefixed with [sheet rN]):\n\"\"\"\n" + model.full_text[:90000] + "\n\"\"\"",
            SCHEMA,
        ])

    @staticmethod
    def _call(prompt: str, api_key: str) -> List[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192, "responseMimeType": "application/json"}}
        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text[:160]}")
        cands = resp.json().get("candidates", [])
        if not cands:
            return []
        text = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "[]")
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else parsed.get("findings", [])

    @classmethod
    def validate(cls, items: List[Dict[str, Any]], model: FSModel, engine_findings: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        doc = _norm(model.full_text)
        doc_numbers = {round(abs(n), 2) for ln in model.lines for n in ln.numbers}
        existing = [_norm(f["sub_title"] + " " + f["view"]) for f in engine_findings]
        accepted, rejected = [], []
        for it in items:
            view = str(it.get("view", ""))
            quotes = [q for q in it.get("evidence_quotes", []) if isinstance(q, str) and len(q.strip()) >= 12]
            ok_quotes = [q for q in quotes if _norm(q) in doc]
            if not ok_quotes or len(ok_quotes) < len(quotes):
                rejected.append(f"{it.get('sub_title', 'AI item')}: quoted extract not found in the statements")
                continue
            amounts = {round(float(a.replace(",", "")), 2) for a in re.findall(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d{3,}(?:\.\d+)?)", view + " " + str(it.get("matter", "")))}
            amounts = {a for a in amounts if not (1990 <= a <= 2100)}
            unknown = [a for a in amounts if not any(abs(a - d) <= 0.011 for d in doc_numbers)]
            if unknown:
                rejected.append(f"{it.get('sub_title', 'AI item')}: amount(s) {', '.join(map(str, unknown[:3]))} not found in the statements")
                continue
            if NEGATIVE_TOPICS.search(view) and not NEGATIVE_TOPICS.search(" ".join(ok_quotes)):
                rejected.append(f"{it.get('sub_title', 'AI item')}: checklist point without evidence of the situation")
                continue
            words = set(_norm(it.get("sub_title", "") + " " + view).split())
            if any(len(words & set(e.split())) / max(1, len(words)) > 0.6 for e in existing):
                rejected.append(f"{it.get('sub_title', 'AI item')}: duplicates an observation already raised")
                continue
            nature = it.get("nature") if it.get("nature") in NATURES else "Requires verification"
            refs = "; ".join(it.get("requirement_refs", [])) or "Reference Verification Required"
            texts = KnowledgeBase.cited_paragraphs(refs)
            accepted.append({
                "rule_code": "AI-REVIEW", "title": it.get("title", "AI review"), "sub_title": it.get("sub_title", ""), "nature": nature,
                "view": view, "matter": it.get("matter", ""), "evidence": [{"sheet": "Quoted", "row": 0, "text": q} for q in ok_quotes],
                "statutory_ref": refs, "source_requirements": texts, "requirement_text": " | ".join(f"[{t['ref']}] {t['text']}" for t in texts),
                "suggested_correction": it.get("suggested_correction", ""), "significance": it.get("significance", "Medium"),
                "basis": "AI review (quotes verified against the statements)", "category": it.get("sub_title", "AI review"),
                "ref": "AI - quoted extracts", "description": view, "current_disclosure": it.get("matter", ""),
                "action": it.get("suggested_correction", ""), "status": nature, "risk": it.get("significance", "Medium"),
            })
        return accepted, rejected
