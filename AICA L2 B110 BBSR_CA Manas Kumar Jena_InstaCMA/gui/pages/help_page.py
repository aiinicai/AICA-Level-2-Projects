"""Help."""
from PyQt5.QtWidgets import QTextBrowser

from gui.pages.base_page import BasePage

GUIDE = """
<h3>Step by step</h3>
<ol>
<li><b>Settings</b> (once): your firm details; an AI model (any provider - Gemini, Claude, OpenAI, OpenRouter /
Groq / DeepSeek, or a local Ollama model) if you want PDFs read by AI.</li>
<li><b>Client &amp; years</b>: borrower details and the type of each year - Audited, Provisional, Estimated,
Projected (up to 7). Tick "client figures" for an estimated / projected year if the client gave its own.</li>
<li><b>Upload</b> the P&amp;L and Balance Sheet: PDF (normal or scanned), Excel (any layout) or photos.</li>
<li><b>Review &amp; group</b>: every line with its CMA head and group (Schedule III for companies, T-form for
others). Each statement year must tally to the rupee. Then lock the actual years.</li>
<li><b>Inputs</b>: cash credit, term loan (Equal EMI / Equal Principal), existing loans, year-wise assumptions,
norms and DSCR (drawings deducted or not), GST turnover. Blank = default.</li>
<li><b>Projections, Term loan, Bank tests, Checks</b>: review the results.</li>
<li><b>Export</b>: the CMA workbook in the built-in format and one A4 PDF of all pages.</li>
</ol>
<h3>Rules</h3>
<ul>
<li>Sales = previous x (1 + growth); variable expenses keep their ratio to sales, fixed are held;
purchases balanced to the previous gross profit %.</li>
<li>Drawing power = (stock - creditors) x (1 - stock margin) + debtors x (1 - debtor margin) must exceed the CC
limit every year; debtor days are raised only as needed (cap 90).</li>
<li>DSCR = (net profit + depreciation + interest [- drawings if chosen]) / (CC interest on the full limit +
term-loan interest and principal + existing loans).</li>
<li>Cash at bank is the balancing figure; opening balances always equal the previous closing balances.</li>
</ul>
<p>Everything except AI reading runs offline. The CMA format is built into the application.</p>
"""


class HelpPage(BasePage):
    title = "Help"
    subtitle = "InstaCMA  |  Developed by CA Manas Kumar Jena  |  Contact: +91 9337820330"
    scroll = False

    def build(self):
        t = QTextBrowser()
        t.setHtml(GUIDE)
        self.body.addWidget(t)
