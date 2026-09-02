import sys
import os
from pathlib import Path
import pytest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
import services.gemini_service as gemini_service
import services.knowledge_vault as knowledge_vault
from engines.draft_risk_checker import DraftRiskChecker

def test_run_procedural_checks():
    # Test case 1: DIN absent
    extraction_no_din = "Assessment Year: 2017-18\nPrimary Section Invoked: Section 148\nDIN: Not found in notice"
    flags1 = app.run_procedural_checks(extraction_no_din)
    assert any("DIN ABSENT" in f for f in flags1)
    assert any("TIME-BARRED" in f for f in flags1) # AY 2017-18 is < 2018
    assert any("REASSESSMENT" in f for f in flags1) # Section 148
    
    # Test case 2: Valid DIN but format manual verification
    extraction_format_ver = "Assessment Year: 2019-20\nPrimary Section Invoked: Section 143(2)\nDIN: INVALID_FORMAT_123"
    flags2 = app.run_procedural_checks(extraction_format_ver)
    assert any("DIN FORMAT" in f for f in flags2)
    assert any("SAVINGS-CLAUSE" in f for f in flags2) # AY 2019-20 is between 2018 and 2020

def test_clean_markdown_from_draft():
    markdown_text = "### Heading\nThis is **bold** and *italic* text with `code`.\n- Bullet 1\n- Bullet 2"
    cleaned = app.clean_markdown_from_draft(markdown_text)
    assert "Heading" in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "_" not in cleaned
    assert "Bullet 1" in cleaned

def test_split_for_portal():
    large_text = "Paragraph 1\n\n" * 4000 # very large text
    chunks = app.split_for_portal(large_text, max_chars=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1200 for c in chunks) # allowance for headers

def test_make_portal_safe_text():
    raw_text = "Rs. \u20b9 100,000 \u2014 registered with \u201cquotes\u201d."
    safe = app.make_portal_safe_text(raw_text)
    assert "\u20b9" not in safe
    assert "Rs. Rs. 100,000 - registered with \"quotes\"." in safe

def test_word_export_docx():
    if app.DOCX_AVAILABLE:
        draft = "This is a draft reply."
        cover = "Dear AO, please find attached."
        extraction = "Notice under Section 143(2)."
        pkg = app.build_word_package(draft, cover, extraction)
        assert isinstance(pkg, bytes)
        assert len(pkg) > 0

def test_gemini_service_api_key_resolution(monkeypatch):
    monkeypatch.setattr(gemini_service, "get_api_key", lambda: "")
    with pytest.raises(gemini_service.APICallError) as exc_info:
        gemini_service.call_gemini("gemini-2.5-flash", "test prompt")
    assert "Gemini API key not found" in str(exc_info.value)
