"""Shared fixtures: synthetic PDFs (no real judgments) and a fake Gemini SDK client."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pymupdf as fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE_PAGES = [
    "IN THE HIGH COURT OF EXAMPLELAND\nCivil Appeal No. 123 of 2024\nAlpha Traders Pvt Ltd ... Appellant\n"
    "versus\nBeta Revenue Authority ... Respondent\nCoram: Justice A. Example and Justice B. Sample",
    "The appellant challenged an assessment order dated 01 March 2023. The issue is whether section 9 of "
    "the Example Act applies to the transaction. The appellant argued that the transaction was exempt.",
    "Held: The court finds that section 9 does not apply. The appeal is allowed and the assessment order "
    "is set aside. No order as to costs.",
]


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Never touch the real user configuration or environment key during tests."""
    monkeypatch.setenv("JIA_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("JIA_AUDIT_DIR", str(tmp_path / "Downloads"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


def _make_text_pdf(path: Path, pages: list[str]) -> Path:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 550, 800), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def text_pdf(tmp_path) -> Path:
    return _make_text_pdf(tmp_path / "sample_judgment.pdf", SAMPLE_PAGES)


@pytest.fixture
def long_text_pdf(tmp_path) -> Path:
    pages = [f"Paragraph block for page {i}. " + ("The court considered the evidence carefully. " * 60)
             for i in range(1, 13)]
    return _make_text_pdf(tmp_path / "long_judgment.pdf", pages)


@pytest.fixture
def scanned_pdf(tmp_path) -> Path:
    """A PDF whose only page is an image of text (no text layer)."""
    src = fitz.open()
    page = src.new_page(width=612, height=300)
    page.insert_text((40, 80), "JUDGMENT OF THE SCANNED COURT", fontsize=26)
    page.insert_text((40, 150), "The appeal is dismissed with costs.", fontsize=26)
    png = page.get_pixmap(dpi=200).tobytes("png")
    src.close()

    out = fitz.open()
    p = out.new_page(width=612, height=300)
    p.insert_image(p.rect, stream=io.BytesIO(png).getvalue())
    path = tmp_path / "scanned.pdf"
    out.save(path)
    out.close()
    return path


@pytest.fixture
def encrypted_pdf(tmp_path) -> Path:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret")
    path = tmp_path / "locked.pdf"
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="owner")
    doc.close()
    return path


# ------------------------------------------------------------ fake Gemini ---
SAMPLE_REPORT = """## 1. Case Details
- **Court or tribunal:** High Court of Exampleland (p. 1)
- **Case title:** Alpha Traders Pvt Ltd v. Beta Revenue Authority
- **Citation or case number:** Civil Appeal No. 123 of 2024
- **Date of judgment:** Not stated in the judgment
- **Judges or bench:** Justice A. Example; Justice B. Sample
- **Parties involved:** Alpha Traders Pvt Ltd (Appellant); Beta Revenue Authority (Respondent)

## 2. Executive Summary
The appeal was allowed (p. 3).

## 3. Material Facts
1. An assessment order was passed on 01 March 2023 (p. 2).

## 4. Issues Before the Court
1. Whether section 9 of the Example Act applies.

## 5. Arguments of the Parties
### Appellant
- The transaction was exempt (p. 2).
### Respondent
- Not stated in the judgment

## 6. Relevant Laws and Provisions
- Section 9, Example Act

## 7. Court's Analysis and Reasoning
[Court Finding] Section 9 does not apply (p. 3).

## 8. Final Decision or Order
Appeal allowed; assessment order set aside; no order as to costs (p. 3).

## 9. Ratio Decidendi
[Court Finding] Section 9 does not apply to such transactions.

## 10. Obiter Dicta
None identified.

## 11. Important Precedents Cited
None cited in the judgment.

## 12. Practical Implications
[AI Observation] Similar transactions may fall outside section 9.

## 13. Key Insights From the Judgment
1. **Scope of section 9** is narrower than the authority contended.

## 14. Points for Consideration
### Questions left unresolved
- [Uncertain] Applicability to related-party transactions.
### Compliance considerations
- Review past assessments.
### Risks and limitations
- Short judgment; limited reasoning.
### Possible impact on similar cases
- Persuasive for similar appeals.
### Matters requiring professional or legal review
- Confirm whether an appeal has been filed.

## Disclaimer
This analysis is for educational and research purposes only and is not legal advice.
"""


class FakeModels:
    def __init__(self, responses=None, errors=None):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.calls: list[dict] = []

    def generate_content(self, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.errors:
            err = self.errors.pop(0)
            if err is not None:
                raise err
        text = self.responses.pop(0) if self.responses else SAMPLE_REPORT
        return SimpleNamespace(
            text=text, prompt_feedback=None,
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=50),
        )

    def get(self, model):
        return SimpleNamespace(name=f"models/{model}", input_token_limit=1_000_000)

    def list(self):
        return [
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash-tts", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-embedding-2", supported_actions=["embedContent"]),
        ]


@pytest.fixture
def fake_sdk():
    def _factory(responses=None, errors=None):
        return SimpleNamespace(models=FakeModels(responses, errors))
    return _factory
