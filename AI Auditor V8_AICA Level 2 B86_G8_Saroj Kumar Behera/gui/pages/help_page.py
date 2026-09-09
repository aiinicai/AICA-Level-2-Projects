"""
AI Auditor V8 - User Manual & Help Page
Interactive reference documentation, auditing standards overview, ratio cheat-sheets, and troubleshooting guide.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextBrowser, QFrame
)
from config.constants import APP_NAME, APP_VERSION

HELP_HTML_CONTENT = f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif; color: #1E293B; line-height: 1.6; padding: 10px;">
    <h1 style="color: #1A365D; font-size: 22px; margin-bottom: 2px;">{APP_NAME} User Manual & Audit Reference Guide</h1>
    <p style="color: #64748B; font-size: 12px; margin-top: 0px;">Version {APP_VERSION} | Professional Desktop Financial Statement Analysis System</p>
    <hr style="border: 0; height: 1px; background: #CBD5E1; margin: 15px 0;">

    <h2 style="color: #2563EB; font-size: 16px;">1. Purpose & Core Workflow</h2>
    <p>
        <b>AI Auditor V8</b> is an offline Windows desktop application engineered for Chartered Accountants, internal auditors, and credit analysts.
        It automates analytical review procedures (under <b>SA 520 / ISA 520</b>) and transforms raw Excel/PDF financial figures into structured audit intelligence.
    </p>
    <ol>
        <li><b>Upload:</b> Ingest multi-period Balance Sheets, P&L, and Cash Flow statements in Excel (.xlsx, .xls) or PDF format.</li>
        <li><b>Review:</b> Verify extracted figures, override line item taxonomy classifications, and add custom line items.</li>
        <li><b>Analyze:</b> Automatic calculation of 30 financial ratios, multi-year horizontal/vertical trends, and significant variances (&ge; 5%).</li>
        <li><b>Audit Support:</b> Review deterministic Chartered Accountant <i>Possible Reasons</i> and substantive <i>Audit Document Checklists</i> (explaining WHY each voucher is required).</li>
        <li><b>Export:</b> Generate 12-sheet Excel diagnostic workbooks and executive Word (.docx) reports.</li>
    </ol>

    <h2 style="color: #2563EB; font-size: 16px;">2. Understanding Analytical Terminology</h2>
    <ul>
        <li><b>ACTUAL DATA:</b> Figures directly extracted from the uploaded financial statement or manually corrected by the user.</li>
        <li><b>CALCULATED RESULTS:</b> Standardized mathematical computations (e.g. Current Ratio, ROE, EBITDA, Net Working Capital).</li>
        <li><b>POSSIBLE REASONS:</b> Objective, non-conclusive audit hypotheses explaining why a line item moved (e.g. sales expansion vs price revisions). <i>Never presented as confirmed facts.</i></li>
        <li><b>AUDIT VERIFICATION REQUIREMENTS:</b> Primary accounting records, reconciliations, and third-party confirmations (SA 505) required to substantiate the balance, with specific audit justifications.</li>
        <li><b>POTENTIAL RISK / ATTENTION AREAS:</b> Objective red-flag signals (e.g. negative operating cash flow with positive PAT, spike in debtor days, leverage > 2.0x).</li>
    </ul>

    <h2 style="color: #2563EB; font-size: 16px;">3. Supported Formats & Guidelines</h2>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #CBD5E1; font-size: 12px;">
        <tr style="background-color: #F1F5F9; font-weight: bold; color: #1E293B;">
            <th>File Type</th>
            <th>Recommended Layout</th>
            <th>Notes</th>
        </tr>
        <tr>
            <td><b>Excel (.xlsx, .xls)</b></td>
            <td>Multi-sheet (Balance Sheet, P&L, Cash Flow) or single sheet with headers.</td>
            <td>Ensure period years (e.g., FY 2023-24, FY 2022-23) appear in header rows.</td>
        </tr>
        <tr>
            <td><b>Searchable PDF (.pdf)</b></td>
            <td>Standard published annual reports or audited financial statements.</td>
            <td>Extracts native vector tables with high precision.</td>
        </tr>
        <tr>
            <td><b>Scanned PDF (.pdf)</b></td>
            <td>Clean, high-resolution scans (300 DPI recommended).</td>
            <td>Processed via built-in Tesseract OCR and contrast enhancement.</td>
        </tr>
    </table>

    <h2 style="color: #2563EB; font-size: 16px;">4. Troubleshooting & FAQs</h2>
    <p><b>Q: What if a line item is mapped incorrectly?</b><br>
    Navigate to the <b>Financial Data Review</b> page, select the correct classification from the dropdown, and click <i>Save Adjustments & Recalculate</i>.</p>

    <p><b>Q: Does this application require an internet connection?</b><br>
    No. AI Auditor V8 is 100% offline. All financial models, ratio algorithms, variance detection, and CA rules are embedded locally.</p>

    <p><b>Q: How do I change the variance threshold from 5% to 10%?</b><br>
    You can adjust the threshold dynamically on the <b>Significant Variations</b> page using the slider/spinbox, or set a new global default on the <b>Settings</b> page.</p>
</div>
"""

class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(HELP_HTML_CONTENT)
        browser.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px;")
        main_layout.addWidget(browser)
