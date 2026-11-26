"""
test_tenderiq.py
End-to-end verification suite for TenderIQ:
- Generates a realistic sample tender dataset (multi-page HTML portal with homepage,
  paginated search results, tender detail pages, PDF document, ZIP archive containing PDFs,
  scanned/empty PDF, and CAPTCHA/block edge cases).
- Serves the sample portal over localhost HTTP.
- Tests Playwright browser navigation, pagination, deduplication, detail extraction,
  PDF/ZIP downloading, PyPDF extraction + scanned PDF detection,
  AI analysis (live OpenAI if OPENAI_API_KEY is configured, plus deterministic mock fallback test),
  Excel workbook generation, and PDF management report generation.
"""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading
import zipfile

from openpyxl import load_workbook
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from browser_agent import extract_pdfs_from_zip, run_tender_scraper, validate_url
from document_analyser import analyse_tender_documents, extract_pdf_text, load_openai_config
from report_generator import EXCEL_FILENAME, PDF_FILENAME, generate_excel_report, generate_pdf_report
from tender_extractor import (
    NOT_AVAILABLE,
    TenderRecord,
    classify_page_type,
    deduplicate_tenders,
    detect_captcha_or_block,
)

BASE_DIR = Path(__file__).resolve().parent
TEST_WORK_DIR = BASE_DIR / "_test_artifacts"


def _create_sample_text_pdf(path: Path, pages_lines: list[list[str]]) -> None:
    """Create a multi-page searchable PDF using ReportLab."""
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    for page_lines in pages_lines:
        y = 780
        c.setFont("Helvetica", 11)
        for line in page_lines:
            c.drawString(50, y, line)
            y -= 18
        c.showPage()
    c.save()


def _create_blank_scanned_pdf(path: Path) -> None:
    """Create a PDF with a blank page (simulating an un-OCR'd scanned PDF)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as f:
        writer.write(f)


def _build_sample_portal(portal_dir: Path) -> None:
    """Create a sample multi-page tender portal + sample PDF/ZIP files."""
    if portal_dir.exists():
        shutil.rmtree(portal_dir)
    (portal_dir / "docs").mkdir(parents=True, exist_ok=True)

    # Sample Tender 1 PDF (2 pages with full procurement criteria)
    _create_sample_text_pdf(
        portal_dir / "docs" / "NIT_SOLAR_001.pdf",
        [
            [
                "NOTICE INVITING TENDER - REF: PWR/SOLAR/2026/001",
                "Organisation: National Clean Energy Corporation Ltd.",
                "Department: Solar Grid Procurement Wing",
                "Location: Jaipur, Rajasthan",
                "Purpose: Supply, installation, and commissioning of 500 kW Grid-Connected Solar PV System.",
                "Products Required: Tier-1 Mono-PERC Solar Modules (540Wp+), String Inverters, SCADA Telemetry.",
                "Scope of Work: Design, engineering, civil foundation, mounting structures, DC/AC cabling, and 5-year O&M.",
                "Technical Specifications: IEC 61215 / IEC 61730 certified modules, IP65 inverters, efficiency >= 98.2%.",
                "Estimated Tender Value: INR 2,50,00,000 (2.50 Crore)",
                "EMD Requirement: INR 5,00,000 via Bank Guarantee or Online NEFT.",
                "Tender Fee: INR 5,900 (non-refundable).",
            ],
            [
                "ELIGIBILITY & COMMERCIAL TERMS - REF: PWR/SOLAR/2026/001",
                "Minimum Annual Turnover: INR 4,00,00,000 average over last 3 financial years (FY23-24, FY24-25, FY25-26).",
                "Past Experience: At least 2 completed grid solar projects of >= 300 kW capacity in the last 5 years.",
                "Manufacturing/Supply Capability: OEM authorization or valid MNRE channel partner certificate.",
                "Performance Security: 10% of contract value within 14 days of LOA.",
                "Important Deadlines: Pre-bid Meeting: 2026-12-05; Bid Submission Deadline: 2026-12-18 17:00 IST.",
                "Required Registrations: Valid GSTIN, PAN, ISO 9001:2015, and Class-A Electrical Contractor License.",
                "Commercial Conditions: 70% payment on delivery, 20% on commissioning, 10% after 90-day performance test.",
                "Disqualification Conditions: Blacklisted firms, incomplete EMD, or missing OEM authorization will be rejected.",
                "Risk Observations: Liquidated damages of 0.5% per week up to max 10% for delays beyond 120 days.",
            ],
        ],
    )

    # Sample Tender 2 ZIP containing a PDF + a scanned blank PDF
    t2_pdf = portal_dir / "docs" / "_tmp_t2_spec.pdf"
    _create_sample_text_pdf(
        t2_pdf,
        [
            [
                "TENDER SPECIFICATION - REF: IT/CLOUD/2026/002",
                "Purpose: Enterprise Cloud Backup & Disaster Recovery Managed Services.",
                "Scope of Work: 200 TB encrypted off-site replication with RPO <= 15 min and RTO <= 2 hours.",
                "Minimum Annual Turnover: INR 10,00,00,000 in each of last 3 years.",
                "Past Experience: Minimum 3 government cloud DR implementations.",
                "EMD Requirement: INR 3,00,000; Tender Fee: INR 2,500; Performance Security: 5% PBG.",
                "Important Deadlines: Bid Closing Date: 2026-12-22 15:00.",
                "Required Certificates: ISO 27001, SOC 2 Type II, MeitY Empanelment.",
                "Commercial Conditions: Quarterly billing in arrears; 99.95% SLA uptime.",
                "Risk Observations: Strict data residency within India required; penalty for SLA breach.",
            ]
        ],
    )
    t2_scanned = portal_dir / "docs" / "_tmp_t2_annexure_scanned.pdf"
    _create_blank_scanned_pdf(t2_scanned)
    with zipfile.ZipFile(portal_dir / "docs" / "TENDER_002_DOCS.zip", "w") as zf:
        zf.write(t2_pdf, arcname="IT_Cloud_DR_Specification.pdf")
        zf.write(t2_scanned, arcname="Signed_Annexure_Scanned.pdf")
    t2_pdf.unlink()
    t2_scanned.unlink()

    # Sample Tender 3 PDF (on page 2 of listing)
    _create_sample_text_pdf(
        portal_dir / "docs" / "MED_EQUIP_003.pdf",
        [
            [
                "NOTICE INVITING TENDER - REF: HLT/MED/2026/003",
                "Purpose: Supply of 25 Automated Hematology Analyzers for District Hospitals.",
                "Scope of Work: Supply, installation, reagent pack starter kit, and 3-year comprehensive warranty.",
                "Minimum Annual Turnover: INR 1,50,00,000 over last 3 years.",
                "Past Experience: Supplied at least 15 analyzers to public hospitals in last 3 years.",
                "EMD Requirement: INR 1,50,000; Tender Fee: INR 1,000.",
                "Bid Closing Date: 2026-12-28.",
                "Required Certificates: CDSCO Medical Device License, CE/FDA certification, ISO 13485.",
            ]
        ],
    )

    # Homepage
    (portal_dir / "index.html").write_text(
        """<!DOCTYPE html>
<html><head><title>GovProcure Sample Portal</title></head>
<body>
  <h1>National Procurement Portal</h1>
  <p>Welcome to the official e-procurement system.</p>
  <nav>
    <a href="about.html">About Us</a> |
    <a href="tenders_page1.html">Active Tenders Search</a> |
    <a href="help.html">Help Desk</a>
  </nav>
</body></html>""",
        encoding="utf-8",
    )

    # Listing Page 1 (2 tenders + duplicate test + Next link)
    (portal_dir / "tenders_page1.html").write_text(
        """<!DOCTYPE html>
<html><head><title>Active Tenders - Page 1</title></head>
<body>
  <h1>Active Tender Search Results</h1>
  <table border="1">
    <tr>
      <th>Tender ID</th><th>Tender Title</th><th>Organisation</th>
      <th>Location</th><th>Published Date</th><th>Closing Date</th><th>Estimated Value</th>
    </tr>
    <tr>
      <td>PWR/SOLAR/2026/001</td>
      <td><a href="detail_001.html">500 kW Grid-Connected Solar PV System</a></td>
      <td>National Clean Energy Corp</td>
      <td>Jaipur</td>
      <td>2026-11-15</td>
      <td>2026-12-18</td>
      <td>INR 2,50,00,000</td>
    </tr>
    <tr>
      <td>IT/CLOUD/2026/002</td>
      <td><a href="detail_002.html">Enterprise Cloud Backup &amp; DR Services</a></td>
      <td>State IT Infrastructure Ltd</td>
      <td>Bengaluru</td>
      <td>2026-11-18</td>
      <td>2026-12-22</td>
      <td>INR 1,80,00,000</td>
    </tr>
  </table>
  <div class="pagination"><a href="tenders_page2.html" rel="next">Next &gt;</a></div>
</body></html>""",
        encoding="utf-8",
    )

    # Listing Page 2 (includes 1 duplicate of 001 + 1 new tender 003)
    (portal_dir / "tenders_page2.html").write_text(
        """<!DOCTYPE html>
<html><head><title>Active Tenders - Page 2</title></head>
<body>
  <h1>Active Tender Search Results (Page 2)</h1>
  <table border="1">
    <tr>
      <th>Tender ID</th><th>Tender Title</th><th>Organisation</th>
      <th>Location</th><th>Published Date</th><th>Closing Date</th><th>Estimated Value</th>
    </tr>
    <tr>
      <td>PWR/SOLAR/2026/001</td>
      <td><a href="detail_001.html">500 kW Grid-Connected Solar PV System</a></td>
      <td>National Clean Energy Corp</td>
      <td>Jaipur</td>
      <td>2026-11-15</td>
      <td>2026-12-18</td>
      <td>INR 2,50,00,000</td>
    </tr>
    <tr>
      <td>HLT/MED/2026/003</td>
      <td><a href="detail_003.html">Supply of 25 Automated Hematology Analyzers</a></td>
      <td>State Health Directorate</td>
      <td>Pune</td>
      <td>2026-11-20</td>
      <td>2026-12-28</td>
      <td>INR 75,00,000</td>
    </tr>
  </table>
</body></html>""",
        encoding="utf-8",
    )

    # Detail pages
    (portal_dir / "detail_001.html").write_text(
        """<!DOCTYPE html>
<html><head><title>Tender Detail - PWR/SOLAR/2026/001</title></head>
<body>
  <h1>500 kW Grid-Connected Solar PV System</h1>
  <table>
    <tr><th>Tender Reference</th><td>PWR/SOLAR/2026/001</td></tr>
    <tr><th>Organisation</th><td>National Clean Energy Corporation Ltd.</td></tr>
    <tr><th>Department</th><td>Solar Grid Procurement Wing</td></tr>
    <tr><th>Location</th><td>Jaipur, Rajasthan</td></tr>
    <tr><th>Published Date</th><td>2026-11-15</td></tr>
    <tr><th>Closing Date</th><td>2026-12-18</td></tr>
    <tr><th>Estimated Value</th><td>INR 2,50,00,000</td></tr>
    <tr><th>EMD Amount</th><td>INR 5,00,000</td></tr>
    <tr><th>Tender Fee</th><td>INR 5,900</td></tr>
  </table>
  <p><a href="docs/NIT_SOLAR_001.pdf">Download NIT Document (PDF)</a></p>
</body></html>""",
        encoding="utf-8",
    )

    (portal_dir / "detail_002.html").write_text(
        """<!DOCTYPE html>
<html><head><title>Tender Detail - IT/CLOUD/2026/002</title></head>
<body>
  <h1>Enterprise Cloud Backup &amp; DR Services</h1>
  <table>
    <tr><th>Tender Reference</th><td>IT/CLOUD/2026/002</td></tr>
    <tr><th>Organisation</th><td>State IT Infrastructure Ltd</td></tr>
    <tr><th>Department</th><td>Cloud &amp; Data Center Division</td></tr>
    <tr><th>Location</th><td>Bengaluru, Karnataka</td></tr>
    <tr><th>Published Date</th><td>2026-11-18</td></tr>
    <tr><th>Closing Date</th><td>2026-12-22</td></tr>
    <tr><th>Estimated Value</th><td>INR 1,80,00,000</td></tr>
    <tr><th>EMD Amount</th><td>INR 3,00,000</td></tr>
    <tr><th>Tender Fee</th><td>INR 2,500</td></tr>
  </table>
  <p><a href="docs/TENDER_002_DOCS.zip">Download Bid Package (ZIP)</a></p>
</body></html>""",
        encoding="utf-8",
    )

    (portal_dir / "detail_003.html").write_text(
        """<!DOCTYPE html>
<html><head><title>Tender Detail - HLT/MED/2026/003</title></head>
<body>
  <h1>Supply of 25 Automated Hematology Analyzers</h1>
  <table>
    <tr><th>Tender Reference</th><td>HLT/MED/2026/003</td></tr>
    <tr><th>Organisation</th><td>State Health Directorate</td></tr>
    <tr><th>Department</th><td>Medical Equipment Cell</td></tr>
    <tr><th>Location</th><td>Pune, Maharashtra</td></tr>
    <tr><th>Published Date</th><td>2026-11-20</td></tr>
    <tr><th>Closing Date</th><td>2026-12-28</td></tr>
    <tr><th>Estimated Value</th><td>INR 75,00,000</td></tr>
    <tr><th>EMD Amount</th><td>INR 1,50,000</td></tr>
    <tr><th>Tender Fee</th><td>INR 1,000</td></tr>
  </table>
  <p><a href="docs/MED_EQUIP_003.pdf">Download Tender NIT (PDF)</a></p>
</body></html>""",
        encoding="utf-8",
    )

    # CAPTCHA test page
    (portal_dir / "captcha.html").write_text(
        """<!DOCTYPE html><html><head><title>Security Check</title></head>
        <body><h1>Verify you are human</h1><div class="g-recaptcha"></div></body></html>""",
        encoding="utf-8",
    )


class _MockChoiceMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _MockChoice:
    def __init__(self, content: str) -> None:
        self.message = _MockChoiceMessage(content)


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_MockChoice(content)]


class _MockCompletions:
    def create(self, **kwargs):
        user_msg = kwargs["messages"][-1]["content"]
        payload = {
            "purpose": "Procurement verified from extracted PDF text.",
            "products_services": "Solar PV / Cloud DR / Medical Analyzers (per document).",
            "scope_of_work": "Supply, installation, commissioning, and support (Page 1).",
            "technical_specifications": "Conforms to IEC/ISO standards specified in document (Page 1).",
            "turnover_requirement": "Verified annual turnover requirement per NIT (Page 2).",
            "experience_requirement": "Prior completed projects requirement stated in NIT (Page 2).",
            "capability_requirement": "OEM authorization / manufacturing capability required (Page 2).",
            "emd_requirement": "EMD requirement specified in tender document (Page 1).",
            "tender_fee": "Non-refundable tender fee specified in tender document (Page 1).",
            "performance_security": "Performance Bank Guarantee required post-LOA (Page 2).",
            "important_deadlines": "Submission deadline stated in tender schedule (Page 2).",
            "required_certificates": "GSTIN, PAN, ISO certifications required (Page 2).",
            "commercial_conditions": "Milestone-based payment and SLA terms (Page 2).",
            "disqualification_conditions": "Incomplete EMD or missing authorization leads to rejection (Page 2).",
            "risk_observations": "Liquidated damages / SLA penalty clauses apply (Page 2).",
            "overall_summary": f"Concise AI summary generated from {len(user_msg)} chars of tender text.",
            "document_references": "Tender PDFs",
        }
        return _MockResponse(json.dumps(payload))


class _MockChat:
    def __init__(self) -> None:
        self.completions = _MockCompletions()


class MockOpenAIClient:
    """Deterministic mock OpenAI client used when no live OPENAI_API_KEY is configured."""

    def __init__(self) -> None:
        self.chat = _MockChat()


def run_all_tests() -> None:
    if TEST_WORK_DIR.exists():
        shutil.rmtree(TEST_WORK_DIR, ignore_errors=True)
    TEST_WORK_DIR.mkdir(parents=True, exist_ok=True)

    portal_dir = TEST_WORK_DIR / "sample_portal"
    downloads_dir = TEST_WORK_DIR / "downloads"
    output_dir = TEST_WORK_DIR / "output"
    _build_sample_portal(portal_dir)

    # 1. Unit checks: URL validation, CAPTCHA detection, Zip Slip protection
    assert validate_url("")[0] is False
    assert validate_url("not a url")[0] is False
    assert validate_url("https://example.com/tenders")[0] is True
    assert detect_captcha_or_block((portal_dir / "captcha.html").read_text())[0] == "captcha"
    assert detect_captcha_or_block("Access Denied - Error 403", status_code=403)[0] == "blocked"
    assert classify_page_type((portal_dir / "index.html").read_text()) == "homepage"
    assert classify_page_type((portal_dir / "tenders_page1.html").read_text()) == "listing"
    assert classify_page_type((portal_dir / "detail_001.html").read_text()) == "detail"

    # Zip Slip safety test
    evil_zip = TEST_WORK_DIR / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../outside.pdf", b"%PDF-1.4 fake")
    zip_test_dir = TEST_WORK_DIR / "zip_safe"
    zip_test_dir.mkdir(parents=True, exist_ok=True)
    ext_pdfs, _ = extract_pdfs_from_zip(evil_zip, zip_test_dir)
    assert len(ext_pdfs) == 1 and ext_pdfs[0].parent == zip_test_dir.resolve()
    assert not (TEST_WORK_DIR / "outside.pdf").exists()

    # 2. Start local HTTP server serving the sample tender portal
    handler = partial(SimpleHTTPRequestHandler, directory=str(portal_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    try:
        base_url = f"http://127.0.0.1:{port}"

        # 2a. Test CAPTCHA detection via live Playwright Chromium
        captcha_res = run_tender_scraper(f"{base_url}/captcha.html", downloads_dir)
        assert captcha_res.status == "captcha", f"Expected captcha, got {captcha_res.status}"

        # 2b. Test Homepage -> Tender Search -> Pagination -> Detail Pages -> PDF & ZIP Download
        logs: list[str] = []
        res = run_tender_scraper(
            f"{base_url}/index.html",
            downloads_dir,
            progress_cb=lambda s, d, p: logs.append(f"{p:.2f} | {s}: {d}"),
        )
        assert res.status == "success", f"Scrape failed: {res.status} - {res.message}"
        # 3 unique tenders (001 deduplicated across page 1 & 2, plus 002 and 003)
        assert len(res.tenders) == 3, f"Expected 3 unique tenders, got {len(res.tenders)}"
        # 4 PDFs total: 1 from NIT_SOLAR_001.pdf, 2 extracted from TENDER_002_DOCS.zip, 1 from MED_EQUIP_003.pdf
        assert res.total_documents_downloaded == 4, (
            f"Expected 4 PDFs downloaded/extracted, got {res.total_documents_downloaded}"
        )

        # 2c. Test direct single tender detail page scraping
        single_res = run_tender_scraper(f"{base_url}/detail_001.html", TEST_WORK_DIR / "dl_single")
        assert single_res.status == "success" and len(single_res.tenders) == 1
        assert single_res.tenders[0].tender_id == "PWR/SOLAR/2026/001"
        assert single_res.tenders[0].emd_amount == "INR 5,00,000"

        # 3. Verify PyPDF extraction & Scanned PDF detection
        scanned_hits = 0
        extracted_hits = 0
        for t in res.tenders:
            for pdf in t.downloaded_files:
                txt, _, st_code, _ = extract_pdf_text(Path(pdf))
                if st_code == "scanned":
                    scanned_hits += 1
                elif st_code == "extracted" and txt:
                    extracted_hits += 1
        assert extracted_hits == 3, f"Expected 3 extractable PDFs, got {extracted_hits}"
        assert scanned_hits == 1, f"Expected 1 scanned PDF, got {scanned_hits}"

        # 4. Test AI analysis (use live OpenAI if key configured, otherwise verify both missing-key skip and mock client)
        api_key, _ = load_openai_config(BASE_DIR)
        if api_key:
            stats = analyse_tender_documents(res.tenders, env_dir=BASE_DIR)
            print(f"[INFO] Live OpenAI analysis completed: {stats.tenders_analysed} analysed.")
        else:
            # First test graceful skip when key is missing
            skip_stats = analyse_tender_documents(res.tenders, env_dir=BASE_DIR)
            assert skip_stats.api_key_configured is False
            assert skip_stats.tenders_analysed == 0
            # Then run with deterministic MockOpenAIClient to verify full pipeline & reports
            stats = analyse_tender_documents(
                res.tenders, env_dir=BASE_DIR, client_override=MockOpenAIClient()
            )
            print("[INFO] Verified missing-key skip AND full AI pipeline with MockOpenAIClient.")

        assert stats.tenders_analysed == 3, f"Expected 3 analysed tenders, got {stats.tenders_analysed}"
        assert stats.documents_unanalysed == 1, f"Expected 1 scanned unanalysed doc, got {stats.documents_unanalysed}"

        # 5. Test Excel generation & verify structure
        excel_path = generate_excel_report(res.tenders, output_dir)
        assert excel_path.exists() and excel_path.name == EXCEL_FILENAME
        wb = load_workbook(excel_path)
        assert wb.sheetnames == ["TENDER MASTER", "AI TENDER SUMMARY"]
        assert wb["TENDER MASTER"].max_row == 4  # 1 header + 3 tenders
        assert wb["AI TENDER SUMMARY"].max_row == 4
        assert wb["TENDER MASTER"].freeze_panes == "A2"
        assert wb["TENDER MASTER"].auto_filter.ref == "A1:M4"

        # 6. Test PDF report generation & verify readable pages
        pdf_path = generate_pdf_report(
            tenders=res.tenders,
            source_url=res.source_url,
            total_documents_downloaded=res.total_documents_downloaded,
            analysis_stats=stats,
            output_dir=output_dir,
        )
        assert pdf_path.exists() and pdf_path.name == PDF_FILENAME
        pdf_reader = PdfReader(str(pdf_path))
        assert len(pdf_reader.pages) == 4, f"Expected 4 PDF pages (1 Exec + 3 Tenders), got {len(pdf_reader.pages)}"
        page1_text = pdf_reader.pages[0].extract_text() or ""
        assert "EXECUTIVE SUMMARY" in page1_text.upper()

        print("ALL TENDERIQ END-TO-END TESTS PASSED!")
        print(f" - Tenders identified: {len(res.tenders)}")
        print(f" - Documents downloaded/extracted: {res.total_documents_downloaded}")
        print(f" - Tenders analysed: {stats.tenders_analysed}")
        print(f" - Unanalysed (scanned) docs: {stats.documents_unanalysed}")
        print(f" - Excel report: {excel_path}")
        print(f" - PDF report: {pdf_path}")

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run_all_tests()
