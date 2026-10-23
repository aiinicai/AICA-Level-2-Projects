"""Prompt templates for the ELA10 tutor."""
from __future__ import annotations

from typing import Final

LANGUAGES: Final[dict[str, tuple[str, str]]] = {
    # label -> (gTTS code, instruction name)
    "English": ("en", "English"),
    "Hindi (हिंदी)": ("hi", "Hindi (Devanagari script)"),
    "Tamil (தமிழ்)": ("ta", "Tamil (Tamil script)"),
    "Bengali (বাংলা)": ("bn", "Bengali (Bengali script)"),
    "Telugu (తెలుగు)": ("te", "Telugu (Telugu script)"),
}

SYLLABUS_MAP_HINT: Final[str] = (
    "Module 1: Scope and Objectives of FM, Types of Financing, Ratio Analysis | "
    "Module 2: Cost of Capital, Capital Structure Decisions, Leverages | "
    "Module 3: Investment Decisions (Capital Budgeting) | "
    "Module 4: Dividend Decisions | "
    "Module 5: Working Capital Management, Cash Management, Receivables Management | "
    "Paper 6B: Introduction to Strategic Management, Strategic Analysis, Strategic Choices, "
    "Strategy Implementation and Evaluation"
)

SYSTEM_INSTRUCTION: Final[str] = (
    "You are a seasoned Senior Partner and CA faculty member mentoring an articleship intern "
    "preparing for CA Intermediate Paper 6 (Financial Management and Strategic Management). "
    "Speak warmly and directly, never like a dry textbook. Be accurate; if you are unsure of a "
    "specific figure about a real company, say the illustration is indicative and avoid inventing "
    "precise numbers. Do not reproduce ICAI study material verbatim."
)

USER_TEMPLATE: Final[str] = """Student name: {name}
Student doubt: {question}

Syllabus map for classification: {syllabus_map}

Respond ENTIRELY in {language_name}, except that formulas, acronyms and section numbers may stay in English.
The VERY FIRST line must be exactly, in English:
MAPPED|<chapter name>|<module label>
(choose the single best chapter and module from the syllabus map; if the doubt is outside Paper 6, write MAPPED|Outside Paper 6 syllabus|N/A and answer briefly).

Then write the explanation using these headed sections:
1. Plain-English core idea (speak to the intern; keep it short).
2. Analogy: ground it in an Indian corporate (e.g. D-Mart's negative working capital cycle, Tata Steel's debt leverage, Infosys's cash reserves) where it genuinely fits.
3. Examiner Traps: specific Board of Studies calculation or interpretation pitfalls.
4. Tier 1 - Real-life scenario: a statutory audit, loan appraisal or CFO dashboard situation.
5. Tier 2 - Inter-paper linkage: Ind AS 109 / AS 16 Borrowing Costs (Paper 1) and Sections 123 and 180 of the Companies Act, 2013 (Paper 2), only where relevant.
6. Tier 3 - CA Final readiness: preview linking to Paper 2 Advanced Financial Management (AFM).

Keep the whole answer under 450 words. Use plain text with simple numbered headings, no tables."""


def build_user_prompt(name: str, question: str, language_label: str) -> str:
    _, language_name = LANGUAGES[language_label]
    return USER_TEMPLATE.format(
        name=name or "Candidate",
        question=question.strip(),
        syllabus_map=SYLLABUS_MAP_HINT,
        language_name=language_name,
    )
