"""One-time live verification script for GeminiClient.

Run with:  python scripts/verify_gemini_live.py

This makes REAL calls to Google's Gemini API - free of charge on the
free tier (Flash/Flash-Lite models), subject to per-model rate limits.
Deliberately NOT part of the pytest suite (every AI-layer test uses
FakeLLMClient, never a live call). Run this once to confirm the real
client works end-to-end; requires GOOGLE_API_KEY to be set in your .env
file first (get one free, no credit card required, at
https://aistudio.google.com).

Tests the same three real code paths as verify_openai_live.py, so the
two scripts' output is directly comparable.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("=" * 70)
    print("LIVE VERIFICATION: GeminiClient")
    print("=" * 70)

    from app.config import get_settings
    from app.core.exceptions import ConfigurationError

    settings = get_settings()
    try:
        settings.require_google_key()
    except ConfigurationError as exc:
        print(f"\nSTOPPED: {exc}")
        print("\nAdd GOOGLE_API_KEY=... to your .env file and try again.")
        print("Get a free key (no credit card required) at https://aistudio.google.com")
        return

    print(f"\nUsing model: {settings.gemini_model}")
    print("(Free tier: Flash/Flash-Lite models, subject to per-model rate limits.")
    print(" Free-tier content is used by Google to improve their products -")
    print(" fine for public documents like a published annual report, not")
    print(" recommended for confidential documents; use the paid tier for those.)")

    from app.ai.llm_client import GeminiClient

    client = GeminiClient()

    print("\n--- Test 1: Basic completion (connectivity/auth check) ---")
    try:
        response = client.complete(
            system="You are a helpful assistant. Follow instructions exactly.",
            user="Reply with exactly the text: VERIFICATION_OK",
        )
        print(f"SUCCESS: model={response.model}")
        print(f"Response text: {response.text!r}")
        if "VERIFICATION_OK" not in response.text:
            print("NOTE: model did not follow the exact-text instruction - worth reviewing, not necessarily a failure.")
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}): {exc}")
        print("\nStopping here - later tests depend on basic connectivity working.")
        return

    print("\n--- Test 2: Document analysis on a real annual report page ---")
    try:
        from app.documents.extractor import extract_document, filter_by_section
        from app.core.enums import DocumentType, DocumentSectionType
        from app.ai.document_analysis import analyze_evidence

        ar_path = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_AR_FY_25-26.pdf"
        evidence = extract_document(ar_path, source_document="Sona BLW Annual Report", document_type=DocumentType.ANNUAL_REPORT)
        governance_pages = filter_by_section(evidence, DocumentSectionType.GOVERNANCE)
        if not governance_pages:
            print("No governance pages found to test against - skipping.")
        else:
            test_page = governance_pages[0]
            print(f"Analyzing page {test_page.page_number} of {ar_path.name}...")
            result = analyze_evidence(test_page, client, focus="corporate governance")
            if result is None:
                print("Model found nothing relevant to 'corporate governance' on this specific page (not an error).")
            else:
                print(f"SUCCESS: claim={result.claim!r}")
                print(f"Confidence: {result.confidence.value}")
                print(f"Model recorded: {result.model_name}")
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}): {exc}")

    print("\n--- Test 3: Pledge disclosure extraction on the real SEBI filing ---")
    try:
        from app.documents.extractor import extract_document
        from app.core.enums import DocumentType
        from app.ai.pledge_extraction import extract_pledge_disclosure_batch, summarize_pledge_status

        pledge_path = PROJECT_ROOT / "data" / "sample" / "SONACOMS_pledge_disclosure_2021.pdf"
        evidence = extract_document(pledge_path, source_document="Sona BLW Pledge Disclosure", document_type=DocumentType.PLEDGE_DISCLOSURE)
        print(f"Analyzing all {len(evidence)} pages of {pledge_path.name}...")
        disclosures = extract_pledge_disclosure_batch(evidence, client, delay_seconds=1.0)
        print(f"Pages with disclosure content found: {len(disclosures)}")
        for d in disclosures:
            print(f"  Page {d['page_number']}: pledge_pct={d['pledge_pct']}, status={d['status']}, summary={d['summary']!r}")

        summary = summarize_pledge_status(disclosures)
        print(f"\nSummarized latest_pledge_pct: {summary['latest_pledge_pct']}")
        print(f"As of date: {summary['as_of_date']}")
        print("\nEXPECTED (per the real document, confirmed live with OpenAI on 2026-08-12):")
        print("  latest_pledge_pct should come out as 0 - the disclosed pledge is on an")
        print("  UPSTREAM holding entity's shares (Singapore VII Topco III), not on")
        print("  Sona BLW's own shares. If this comes out non-zero, the model may have")
        print("  missed that distinction - worth reviewing the per-page summaries above.")
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}): {exc}")

    print("\n" + "=" * 70)
    print("Copy this entire output and share it back for review.")
    print("=" * 70)


if __name__ == "__main__":
    main()
