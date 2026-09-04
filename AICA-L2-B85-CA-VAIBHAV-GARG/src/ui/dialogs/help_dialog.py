"""In-app help and documentation dialog."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QLabel
)
from src.config import COLORS


HELP_HTML = """
<h2>Schedule III Ratio Analyser — In-App User Guide</h2>

<h3>1. Overview & Workflow</h3>
<p>The application computes the 11 Analytical Ratios mandated under Clause 6(L) of the General Instructions to Schedule III of the Companies Act, 2013 (applicable from FY 2021-22). The workflow is 100% unattended and requires only 3 user actions:</p>
<ol>
  <li><b>Create Client:</b> Enter the client name.</li>
  <li><b>Upload Current Year File:</b> Drag & drop or browse the current financial year Excel workbook (.xlsx/.xlsm).</li>
  <li><b>Upload Previous Year File:</b> Drag & drop or browse the previous financial year Excel workbook (.xlsx/.xlsm).</li>
</ol>
<p>Upon upload of the second file, the analysis runs automatically and presents the complete analytical ratios note with driver explanations and export options.</p>

<h3>2. Expected Excel Workbook Format</h3>
<p>The application dynamically parses standard Schedule III financial statements containing three sheets:</p>
<ul>
  <li><b>Balance Sheet (BS):</b> Synonyms: <code>BS</code>, <code>Balance Sheet</code>, <code>B/S</code>.</li>
  <li><b>Profit and Loss (PL):</b> Synonyms: <code>PL</code>, <code>PL </code>, <code>P&L</code>, <code>Statement of Profit and Loss</code>.</li>
  <li><b>Cash Flow (CF):</b> Synonyms: <code>CF</code>, <code>Cash Flow</code>, <code>Cash Flow Statement</code>.</li>
</ul>
<p><i>Note:</i> The header row is automatically detected by scanning for <code>Particulars</code>. Figures columns are automatically bound to reporting and comparative years from header text (e.g. <code>As at March 31 2026</code>, <code>For the year ended 31.03.2026</code>).</p>

<h3>3. The 11 Schedule III Mandated Ratios</h3>
<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
  <tr style="background-color: #0B4F8C; color: white;">
    <th>#</th><th>Ratio</th><th>Numerator</th><th>Denominator</th><th>Unit</th>
  </tr>
  <tr><td>1</td><td>Current Ratio</td><td>Current Assets</td><td>Current Liabilities</td><td>x</td></tr>
  <tr><td>2</td><td>Debt-Equity Ratio</td><td>Total Debt</td><td>Shareholders' Equity</td><td>x</td></tr>
  <tr><td>3</td><td>Debt Service Coverage Ratio</td><td>Earnings Available for Debt Service (EADS)</td><td>Debt Service (Interest + Principal Repayment)</td><td>x</td></tr>
  <tr><td>4</td><td>Return on Equity (ROE)</td><td>Net Profit After Tax − Preference Dividend</td><td>Average Shareholders' Equity</td><td>%</td></tr>
  <tr><td>5</td><td>Inventory Turnover Ratio</td><td>Cost of Goods Sold (COGS)</td><td>Average Inventories</td><td>x</td></tr>
  <tr><td>6</td><td>Trade Receivables Turnover</td><td>Net Credit Sales</td><td>Average Trade Receivables</td><td>x</td></tr>
  <tr><td>7</td><td>Trade Payables Turnover</td><td>Net Credit Purchases</td><td>Average Trade Payables</td><td>x</td></tr>
  <tr><td>8</td><td>Net Capital Turnover</td><td>Net Revenue</td><td>Average Working Capital</td><td>x</td></tr>
  <tr><td>9</td><td>Net Profit Ratio</td><td>Profit After Tax (PAT)</td><td>Net Revenue</td><td>%</td></tr>
  <tr><td>10</td><td>Return on Capital Employed (ROCE)</td><td>Earnings Before Interest and Tax (EBIT)</td><td>Capital Employed</td><td>%</td></tr>
  <tr><td>11</td><td>Return on Investment (ROI)</td><td>Income from Investments</td><td>Average Total Investments</td><td>%</td></tr>
</table>

<h3>4. Standard Accounting Assumptions (§8)</h3>
<ul>
  <li><b>Credit Sales:</b> 100% of sales treated as credit sales (disclosed in output).</li>
  <li><b>Credit Purchases:</b> 100% of purchases treated as credit purchases (disclosed in output).</li>
  <li><b>Debt Service Principal Repayment:</b> Derived via 3-step waterfall (Extract from CF → Derive from borrowings movement → Validate articulation).</li>
  <li><b>Variance Flagging:</b> Default threshold 25% per Schedule III mandate.</li>
</ul>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule III Ratio Analyser — Guide & Documentation")
        self.setMinimumSize(780, 560)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        layout.addWidget(browser)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
