"""Dialog providing rich statutory, financial, and audit guidance for a selected ratio."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextBrowser, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

RATIO_GUIDANCE = {
    "current_ratio": {
        "name": "Current Ratio",
        "clause": "Clause 6(L)(i) of General Instructions to Schedule III, Part I",
        "formula": "Current Assets ÷ Current Liabilities",
        "numerator": "Current Assets (Inventories, Trade Receivables, Cash & Bank, Short-term Loans & Advances, Other Current Assets)",
        "denominator": "Current Liabilities (Short-term Borrowings, Trade Payables, Other Current Liabilities, Short-term Provisions)",
        "significance": (
            "Measures the entity's short-term liquidity and ability to cover short-term obligations with assets that can be converted into cash within twelve months or the operating cycle.<br><br>"
            "<b>Audit Relevance:</b> A steep drop signals potential working capital distress or default risk on vendor dues / short-term loans. A ratio far exceeding industry benchmarks may indicate idle cash, inventory buildup, or slow-moving debtors."
        ),
        "guidelines": (
            "• <b>Standard Benchmark:</b> 1.33x to 2.00x is generally considered healthy for manufacturing/trading entities.<br>"
            "• <b>Adverse Variance (>25% drop):</b> Often caused by aggressive capex funded via short-term debt, accumulation of current maturities, or operational losses.<br>"
            "• <b>Favourable Variance (>25% rise):</b> Indicates improved liquidity, debt repayment, or higher short-term buffer."
        )
    },
    "debt_equity_ratio": {
        "name": "Debt-Equity Ratio",
        "clause": "Clause 6(L)(ii) of General Instructions to Schedule III, Part I",
        "formula": "Total Debt ÷ Shareholders' Equity",
        "numerator": "Total Debt = Long-term Borrowings + Short-term Borrowings + Current Maturities of Long-Term Debt",
        "denominator": "Shareholders' Equity = Equity Share Capital + Preference Share Capital + Reserves & Surplus (Net of DTL)",
        "significance": (
            "Measures financial leverage and capital gearing — the proportion of borrowed capital relative to net worth.<br><br>"
            "<b>Audit Relevance:</b> Essential for assessing long-term solvency and capital structure sustainability. High leverage increases financial risk and debt service pressure."
        ),
        "guidelines": (
            "• <b>Standard Benchmark:</b> < 1.0x to 1.5x for most industries (infrastructure / capital heavy may go up to 2:1).<br>"
            "• <b>High Ratio:</b> Greater dependency on lenders and sensitivity to interest rate fluctuations.<br>"
            "• <b>Low Ratio:</b> Conservative capital structure with strong solvency cushion."
        )
    },
    "dscr": {
        "name": "Debt Service Coverage Ratio (DSCR)",
        "clause": "Clause 6(L)(iii) of General Instructions to Schedule III, Part I",
        "formula": "Earnings Available for Debt Service ÷ Debt Service",
        "numerator": "EADS = Profit after Tax + Depreciation & Amortisation + Finance Costs + Non-Cash Adjustments",
        "denominator": "Debt Service = Interest & Finance Charges Paid + Principal Repayments of Long-term Debt + Lease Payments",
        "significance": (
            "Measures the entity's ability to service its annual debt obligations (interest plus principal repayments) out of operational cash profits.<br><br>"
            "<b>Audit Relevance:</b> Primary metric used by lenders and statutory auditors to verify debt repayment capacity and covenant compliance."
        ),
        "guidelines": (
            "• <b>Standard Benchmark:</b> > 1.25x to 1.50x. A DSCR below 1.00x indicates operational earnings are insufficient to service existing debt.<br>"
            "• <b>Variance Analysis:</b> Significant variance arises from shifts in operating profitability, interest cost changes, or commencement of debt repayment schedules."
        )
    },
    "return_on_equity": {
        "name": "Return on Equity (ROE)",
        "clause": "Clause 6(L)(iv) of General Instructions to Schedule III, Part I",
        "formula": "(Profit After Tax − Preference Dividend) ÷ Average Shareholders' Equity",
        "numerator": "Net Profit for the period attributable to equity shareholders",
        "denominator": "Average Shareholders' Equity = (Opening Equity + Closing Equity) ÷ 2",
        "significance": (
            "Measures the profitability generated on the capital invested by shareholders.<br><br>"
            "<b>Audit Relevance:</b> Reflects management's efficiency in generating returns on net worth. A key driver for valuation, investor confidence, and equity appraisal."
        ),
        "guidelines": (
            "• <b>Standard Benchmark:</b> 12% to 20% in healthy operating environments.<br>"
            "• <b>Variance Drivers:</b> Highly sensitive to PAT swings, changes in profit margins, asset turnover, and financial leverage."
        )
    },
    "inventory_turnover": {
        "name": "Inventory Turnover Ratio",
        "clause": "Clause 6(L)(v) of General Instructions to Schedule III, Part I",
        "formula": "Cost of Goods Sold (COGS) ÷ Average Inventories",
        "numerator": "COGS = Cost of Materials Consumed + Purchases of Stock-in-Trade + Changes in Inventories",
        "denominator": "Average Inventories = (Opening Inventory + Closing Inventory) ÷ 2",
        "significance": (
            "Measures how many times inventory is sold and replaced over the financial year.<br><br>"
            "<b>Audit Relevance:</b> Low turnover signals inventory obsolescence, slow-moving stock, or overstocking. High turnover indicates efficient supply chain management or potential stockout risks."
        ),
        "guidelines": (
            "• <b>Higher Turnover:</b> Efficient working capital and lower holding costs.<br>"
            "• <b>Lower Turnover:</b> Potential need for inventory valuation write-down under Ind AS 2 / AS 2 (NRV testing)."
        )
    },
    "trade_receivables_turnover": {
        "name": "Trade Receivables Turnover Ratio",
        "clause": "Clause 6(L)(vi) of General Instructions to Schedule III, Part I",
        "formula": "Net Credit Sales ÷ Average Trade Receivables",
        "numerator": "Net Credit Sales = Net Revenue from Operations × Credit Sales %",
        "denominator": "Average Trade Receivables = (Opening Receivables + Closing Receivables) ÷ 2",
        "significance": (
            "Measures the efficiency with which the company collects outstanding trade debts from customers.<br><br>"
            "<b>Audit Relevance:</b> Slower collections (lower turnover) correlate with rising credit risk, ageing book debts, and increased expected credit loss (ECL) provisions."
        ),
        "guidelines": (
            "• <b>Days Sales Outstanding (DSO):</b> 365 ÷ Ratio.<br>"
            "• <b>Variance Drivers:</b> Credit policy changes, revenue concentration, dispute resolutions, or customer collection delays."
        )
    },
    "trade_payables_turnover": {
        "name": "Trade Payables Turnover Ratio",
        "clause": "Clause 6(L)(vii) of General Instructions to Schedule III, Part I",
        "formula": "Net Credit Purchases ÷ Average Trade Payables",
        "numerator": "Net Credit Purchases = (Materials Consumed + Stock Purchases) × Credit Purchases %",
        "denominator": "Average Trade Payables = (Opening Trade Payables + Closing Trade Payables) ÷ 2",
        "significance": (
            "Measures the frequency with which the company pays off its trade creditors and vendors.<br><br>"
            "<b>Audit Relevance:</b> A significant drop may indicate vendor payment delays or liquidity strain. MSME compliance (Section 15 of MSMED Act, 45-day rule) must be evaluated."
        ),
        "guidelines": (
            "• <b>Days Payable Outstanding (DPO):</b> 365 ÷ Ratio.<br>"
            "• <b>Variance Drivers:</b> Better vendor credit terms, liquidity preservation, or change in raw material sourcing."
        )
    },
    "net_capital_turnover": {
        "name": "Net Capital Turnover Ratio",
        "clause": "Clause 6(L)(viii) of General Instructions to Schedule III, Part I",
        "formula": "Net Revenue from Operations ÷ Average Working Capital",
        "numerator": "Net Revenue from Operations (Net of GST / Excise)",
        "denominator": "Average Working Capital = (Opening Working Capital + Closing Working Capital) ÷ 2",
        "significance": (
            "Measures how effectively working capital is deployed to generate revenue.<br><br>"
            "<b>Audit Relevance:</b> Highlights working capital efficiency. If working capital is very small, the ratio can be volatile."
        ),
        "guidelines": (
            "• <b>Higher Ratio:</b> Lean working capital usage.<br>"
            "• <b>Negative / Zero Denominator:</b> Reported as 'Not meaningful' with footnote if working capital is in deficit."
        )
    },
    "net_profit_ratio": {
        "name": "Net Profit Ratio",
        "clause": "Clause 6(L)(ix) of General Instructions to Schedule III, Part I",
        "formula": "(Profit After Tax ÷ Net Revenue from Operations) × 100",
        "numerator": "Profit/(Loss) for the Year (PAT)",
        "denominator": "Net Revenue from Operations (Gross Revenue less GST)",
        "significance": (
            "Measures overall bottom-line profitability per rupee of revenue generated.<br><br>"
            "<b>Audit Relevance:</b> Reflects comprehensive operational efficiency after accounting for direct costs, overheads, depreciation, finance costs, and taxes."
        ),
        "guidelines": (
            "• <b>Variance Analysis:</b> Driven by gross margin changes, fixed cost leverage, finance cost fluctuations, and corporate tax rates."
        )
    },
    "roce": {
        "name": "Return on Capital Employed (ROCE)",
        "clause": "Clause 6(L)(x) of General Instructions to Schedule III, Part I",
        "formula": "(EBIT ÷ Capital Employed) × 100",
        "numerator": "Earnings Before Interest & Tax (PBT + Finance Costs)",
        "denominator": "Capital Employed = Tangible Net Worth + Total Debt + Deferred Tax Liability",
        "significance": (
            "Measures how efficiently the entity generates operating profits from all long-term capital providers (equity + debt).<br><br>"
            "<b>Audit Relevance:</b> Benchmark for comparing performance across companies with different capital structures and financing choices."
        ),
        "guidelines": (
            "• <b>Healthy ROCE:</b> Should comfortably exceed the entity's weighted average cost of capital (WACC)."
        )
    },
    "roi": {
        "name": "Return on Investment (ROI)",
        "clause": "Clause 6(L)(xi) of General Instructions to Schedule III, Part I",
        "formula": "(Income from Investments ÷ Average Total Investments) × 100",
        "numerator": "Income from Investments (Dividend, Interest from securities, Gain on sale)",
        "denominator": "Average Total Investments = (Opening Investments + Closing Investments) ÷ 2",
        "significance": (
            "Measures the return earned specifically on treasury, quoted, and unquoted investments.<br><br>"
            "<b>Audit Relevance:</b> If the entity holds no investments, Schedule III requires this ratio to be reported as 'Not meaningful' rather than 0.00%."
        ),
        "guidelines": (
            "• <b>Zero Investments:</b> Outputted as 'Not meaningful' with mandatory basis disclosure."
        )
    }
}


class RatioInfoDialog(QDialog):
    def __init__(self, ratio_key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statutory & Financial Guidance — Schedule III Ratio")
        self.setMinimumSize(620, 500)
        self.setModal(True)
        
        info = RATIO_GUIDANCE.get(ratio_key, {
            "name": ratio_key.replace("_", " ").title(),
            "clause": "Schedule III General Instructions",
            "formula": "Numerator ÷ Denominator",
            "numerator": "Per statutory definition",
            "denominator": "Per statutory definition",
            "significance": "Key statutory ratio evaluated under Schedule III.",
            "guidelines": "Examine year-on-year variances exceeding 25%."
        })
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)
        
        # Header banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0A2540, stop:1 #0066CC);
                border-radius: 8px;
                padding: 16px;
            }
        """)
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(16, 12, 16, 12)
        h_layout.setSpacing(4)
        
        title_lbl = QLabel(info["name"])
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        h_layout.addWidget(title_lbl)
        
        clause_lbl = QLabel(f"📜 {info['clause']}")
        clause_lbl.setStyleSheet("color: #BAE6FD; font-size: 12px;")
        h_layout.addWidget(clause_lbl)
        
        layout.addWidget(header_frame)
        
        # Content Browser
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
                font-size: 13px;
                color: #1E293B;
                line-height: 1.5;
            }
        """)
        
        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <div style="margin-bottom: 14px; padding: 10px; background-color: #F8FAFC; border-left: 4px solid #0066CC; border-radius: 4px;">
                <b style="color: #0A2540; font-size: 14px;">📐 Statutory Formula:</b><br>
                <span style="font-size: 14px; font-weight: bold; color: #0066CC;">{info['formula']}</span>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 12px;">
                <tr>
                    <td style="padding: 6px; font-weight: bold; color: #475569; width: 110px;">Numerator:</td>
                    <td style="padding: 6px; color: #0F172A;">{info['numerator']}</td>
                </tr>
                <tr style="background-color: #F8FAFC;">
                    <td style="padding: 6px; font-weight: bold; color: #475569;">Denominator:</td>
                    <td style="padding: 6px; color: #0F172A;">{info['denominator']}</td>
                </tr>
            </table>
            
            <div style="margin-bottom: 14px;">
                <b style="color: #0A2540; font-size: 13px;">🎯 Financial Significance & Audit Purpose:</b>
                <p style="margin-top: 6px; color: #334155;">{info['significance']}</p>
            </div>
            
            <div style="margin-bottom: 10px;">
                <b style="color: #0A2540; font-size: 13px;">📊 Interpretation & Variance Analysis:</b>
                <p style="margin-top: 6px; color: #334155;">{info['guidelines']}</p>
            </div>
        </div>
        """
        browser.setHtml(html_content)
        layout.addWidget(browser)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066CC;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0052A3;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
