"""One-time live verification script for OpenAIClient.

Run with:  python scripts/verify_openai_live.py

This makes REAL calls to the OpenAI API and will incur a small cost
(a handful of short gpt-4o calls, well under $0.01 total) - it is
deliberately NOT part of the pytest suite (every AI-layer test uses
FakeLLMClient, never a live call). Run this once to confirm the real
client works end-to-end; requires OPENAI_API_KEY to be set in your .env
file first.

Tests three real code paths, in increasing order of realism:
  1. A bare completion call (basic connectivity/auth check)
  2. Document analysis (app/ai/document_analysis.py) on a real page of
     the bundled Sona BLW annual report
  3. Pledge disclosure extraction (app/ai/pledge_extraction.py) on the
     real bundled SEBI Regulation 31 filing - this is the most
     "legally precise, must get the upstream-vs-target distinction
     right" test in this project, so it's a meaningful real check.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("=" * 70)
    print("LIVE VERIFICATION: OpenAIClient")
    print("=" * 70)

    from app.config import get_settings
    from app.core.exceptions import ConfigurationError

    settings = get_settings()
    try:
        settings.require_openai_key()
    except ConfigurationError as exc:
        print(f"\nSTOPPED: {exc}")
        print("\nAdd OPENAI_API_KEY=sk-... to your .env file and try again.")
        return

    print(f"\nUsing model: {settings.openai_model}")

    from app.ai.llm_client import OpenAIClient

    client = OpenAIClient()

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
        disclosures = extract_pledge_disclosure_batch(evidence, client)
        print(f"Pages with disclosure content found: {len(disclosures)}")
        for d in disclosures:
            print(f"  Page {d['page_number']}: pledge_pct={d['pledge_pct']}, status={d['status']}, summary={d['summary']!r}")

        summary = summarize_pledge_status(disclosures)
        print(f"\nSummarized latest_pledge_pct: {summary['latest_pledge_pct']}")
        print(f"As of date: {summary['as_of_date']}")
        print("\nEXPECTED (per the real document, verified during development with FakeLLMClient):")
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
