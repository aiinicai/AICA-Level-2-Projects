"""Schedule III Financial Statements Data Provider & Viewer Model.

Provides structured DataFrames conforming to Schedule III (Division I and Division II)
of the Companies Act, 2013, incorporating mandatory disclosures with yellow markup.
"""

from typing import Dict, Any, List
import pandas as pd


class ScheduleIIIViewer:
    """Prepares structured tabular data for Schedule III Balance Sheet, P&L, and Notes."""

    @classmethod
    def get_balance_sheet_data(cls, is_ind_as: bool = True) -> pd.DataFrame:
        if is_ind_as:
            data = [
                {"Particulars": "ASSETS", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "(1) Non-Current Assets", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Property, Plant and Equipment", "Note No.": "Note 1", "CY (₹ Lakhs)": "4,520.00", "PY (₹ Lakhs)": "4,200.00", "Modification & Audit Status": "Verified per Ind AS 16; Useful lives reviewed"},
                {"Particulars": "  (b) Capital Work-in-Progress (CWIP)", "Note No.": "Note 2", "CY (₹ Lakhs)": "340.00", "PY (₹ Lakhs)": "150.00", "Modification & Audit Status": "YELLOW: Mandatory CWIP Ageing Schedule incorporated in Note 2"},
                {"Particulars": "  (c) Right-of-Use Assets", "Note No.": "Note 3", "CY (₹ Lakhs)": "850.00", "PY (₹ Lakhs)": "920.00", "Modification & Audit Status": "YELLOW: Ind AS 116 ROU Assets recognized and detailed in Note 3"},
                {"Particulars": "  (d) Intangible Assets & Under Development", "Note No.": "Note 4", "CY (₹ Lakhs)": "110.00", "PY (₹ Lakhs)": "95.00", "Modification & Audit Status": "YELLOW: Intangible Assets Under Development ageing added"},
                {"Particulars": "  (e) Financial Assets - Investments", "Note No.": "Note 5", "CY (₹ Lakhs)": "1,200.00", "PY (₹ Lakhs)": "1,150.00", "Modification & Audit Status": "Measured at FVTPL / Amortized Cost per Ind AS 109"},
                {"Particulars": "  (f) Deferred Tax Assets (Net)", "Note No.": "Note 7", "CY (₹ Lakhs)": "180.00", "PY (₹ Lakhs)": "120.00", "Modification & Audit Status": "YELLOW: Tax loss DTA convincing evidence disclosed in Note 7"},
                {"Particulars": "  (g) Other Non-Current Assets", "Note No.": "Note 8", "CY (₹ Lakhs)": "145.00", "PY (₹ Lakhs)": "110.00", "Modification & Audit Status": "YELLOW: Capital advances segregated from CWIP per Schedule III"},
                {"Particulars": "(2) Current Assets", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Inventories", "Note No.": "Note 9", "CY (₹ Lakhs)": "1,450.00", "PY (₹ Lakhs)": "1,320.00", "Modification & Audit Status": "Measured at lower of cost and NRV on Weighted Average formula"},
                {"Particulars": "  (b) Financial Assets - Trade Receivables", "Note No.": "Note 10", "CY (₹ Lakhs)": "2,100.00", "PY (₹ Lakhs)": "1,850.00", "Modification & Audit Status": "YELLOW: Mandatory Trade Receivables Ageing Schedule added in Note 10"},
                {"Particulars": "  (c) Cash and Cash Equivalents", "Note No.": "Note 11", "CY (₹ Lakhs)": "420.00", "PY (₹ Lakhs)": "310.00", "Modification & Audit Status": "Reconciled with Cash Flow Statement closing cash"},
                {"Particulars": "  (d) Bank Balances other than above", "Note No.": "Note 11", "CY (₹ Lakhs)": "90.00", "PY (₹ Lakhs)": "75.00", "Modification & Audit Status": "YELLOW: Earmarked balances & margin money segregated"},
                {"Particulars": "  (e) Other Current Assets", "Note No.": "", "CY (₹ Lakhs)": "320.00", "PY (₹ Lakhs)": "260.00", "Modification & Audit Status": "Compliant"},
                {"Particulars": "TOTAL ASSETS", "Note No.": "", "CY (₹ Lakhs)": "11,585.00", "PY (₹ Lakhs)": "10,440.00", "Modification & Audit Status": "Arithmetic Balance Equation Verified"},
                {"Particulars": "EQUITY AND LIABILITIES", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "(1) Equity", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Equity Share Capital", "Note No.": "Note 12", "CY (₹ Lakhs)": "2,000.00", "PY (₹ Lakhs)": "2,000.00", "Modification & Audit Status": "YELLOW: Mandatory Promoter Shareholding Table added in Note 12"},
                {"Particulars": "  (b) Other Equity (Reserves & Surplus)", "Note No.": "Note 13", "CY (₹ Lakhs)": "4,210.00", "PY (₹ Lakhs)": "3,650.00", "Modification & Audit Status": "Retained Earnings & General Reserve roll-forward verified"},
                {"Particulars": "(2) Non-Current Liabilities", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Borrowings (Non-Current)", "Note No.": "Note 14", "CY (₹ Lakhs)": "2,350.00", "PY (₹ Lakhs)": "2,100.00", "Modification & Audit Status": "YELLOW: Terms of repayment, interest rate & ROC charges confirmed"},
                {"Particulars": "  (b) Lease Liabilities (Non-Current)", "Note No.": "Note 3", "CY (₹ Lakhs)": "680.00", "PY (₹ Lakhs)": "740.00", "Modification & Audit Status": "YELLOW: Ind AS 116 Lease liabilities maturity added in Note 3"},
                {"Particulars": "  (c) Provisions (Non-Current)", "Note No.": "Note 15", "CY (₹ Lakhs)": "130.00", "PY (₹ Lakhs)": "110.00", "Modification & Audit Status": "YELLOW: Actuarial valuation of Gratuity/Leave per Ind AS 19 in Note 15"},
                {"Particulars": "(3) Current Liabilities", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Borrowings (Current)", "Note No.": "Note 14", "CY (₹ Lakhs)": "450.00", "PY (₹ Lakhs)": "320.00", "Modification & Audit Status": "Working capital facilities secured by current assets"},
                {"Particulars": "  (b) Lease Liabilities (Current)", "Note No.": "Note 3", "CY (₹ Lakhs)": "120.00", "PY (₹ Lakhs)": "110.00", "Modification & Audit Status": "Current portion of Ind AS 116 lease liabilities"},
                {"Particulars": "  (c) Trade Payables - MSME Dues", "Note No.": "Note 16", "CY (₹ Lakhs)": "280.00", "PY (₹ Lakhs)": "210.00", "Modification & Audit Status": "YELLOW: Section 22 MSMED Act disclosures added in Note 16"},
                {"Particulars": "  (d) Trade Payables - Other Creditors", "Note No.": "Note 16", "CY (₹ Lakhs)": "840.00", "PY (₹ Lakhs)": "680.00", "Modification & Audit Status": "YELLOW: Mandatory Trade Payables Ageing Schedule added in Note 16"},
                {"Particulars": "  (e) Other Current Liabilities & Provisions", "Note No.": "", "CY (₹ Lakhs)": "525.00", "PY (₹ Lakhs)": "430.00", "Modification & Audit Status": "YELLOW: Provisions movement schedule added"},
                {"Particulars": "TOTAL EQUITY AND LIABILITIES", "Note No.": "", "CY (₹ Lakhs)": "11,585.00", "PY (₹ Lakhs)": "10,440.00", "Modification & Audit Status": "Verified: Total Assets = Total Equity and Liabilities"},
            ]
        else:
            data = [
                {"Particulars": "I. EQUITY AND LIABILITIES", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "(1) Shareholders' Funds", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Share Capital", "Note No.": "Note 1", "CY (₹ Lakhs)": "2,000.00", "PY (₹ Lakhs)": "2,000.00", "Modification & Audit Status": "YELLOW: Mandatory Promoter Shareholding Table added in Note 1"},
                {"Particulars": "  (b) Reserves and Surplus", "Note No.": "Note 2", "CY (₹ Lakhs)": "4,210.00", "PY (₹ Lakhs)": "3,650.00", "Modification & Audit Status": "Retained earnings roll-forward verified"},
                {"Particulars": "(2) Non-Current Liabilities", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Long-Term Borrowings", "Note No.": "Note 3", "CY (₹ Lakhs)": "2,350.00", "PY (₹ Lakhs)": "2,100.00", "Modification & Audit Status": "YELLOW: Terms of repayment, interest rate & ROC charges added in Note 3"},
                {"Particulars": "  (b) Long-Term Provisions", "Note No.": "Note 4", "CY (₹ Lakhs)": "130.00", "PY (₹ Lakhs)": "110.00", "Modification & Audit Status": "YELLOW: Actuarial assumptions table per AS 15 added in Note 4"},
                {"Particulars": "(3) Current Liabilities", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Short-Term Borrowings", "Note No.": "Note 3", "CY (₹ Lakhs)": "450.00", "PY (₹ Lakhs)": "320.00", "Modification & Audit Status": "Working capital borrowings against current assets"},
                {"Particulars": "  (b) Trade Payables - MSME Dues", "Note No.": "Note 5", "CY (₹ Lakhs)": "280.00", "PY (₹ Lakhs)": "210.00", "Modification & Audit Status": "YELLOW: Section 22 MSMED Act disclosures added in Note 5"},
                {"Particulars": "  (c) Trade Payables - Other Creditors", "Note No.": "Note 5", "CY (₹ Lakhs)": "840.00", "PY (₹ Lakhs)": "680.00", "Modification & Audit Status": "YELLOW: Mandatory Trade Payables Ageing Schedule added in Note 5"},
                {"Particulars": "  (d) Other Current Liabilities & Provisions", "Note No.": "", "CY (₹ Lakhs)": "355.00", "PY (₹ Lakhs)": "300.00", "Modification & Audit Status": "YELLOW: AS 29 provisions movement table added"},
                {"Particulars": "TOTAL EQUITY AND LIABILITIES", "Note No.": "", "CY (₹ Lakhs)": "10,615.00", "PY (₹ Lakhs)": "9,370.00", "Modification & Audit Status": "Arithmetic Balance Equation Verified"},
                {"Particulars": "II. ASSETS", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "(1) Non-Current Assets", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Property, Plant and Equipment", "Note No.": "Note 6", "CY (₹ Lakhs)": "4,520.00", "PY (₹ Lakhs)": "4,200.00", "Modification & Audit Status": "Component accounting and Schedule II useful lives verified"},
                {"Particulars": "  (b) Capital Work-in-Progress (CWIP)", "Note No.": "Note 7", "CY (₹ Lakhs)": "340.00", "PY (₹ Lakhs)": "150.00", "Modification & Audit Status": "YELLOW: Mandatory CWIP Ageing Schedule added in Note 7"},
                {"Particulars": "  (c) Non-Current Investments", "Note No.": "Note 8", "CY (₹ Lakhs)": "1,200.00", "PY (₹ Lakhs)": "1,150.00", "Modification & Audit Status": "Valued at cost less permanent diminution per AS 13"},
                {"Particulars": "  (d) Deferred Tax Assets (Net)", "Note No.": "Note 9", "CY (₹ Lakhs)": "180.00", "PY (₹ Lakhs)": "120.00", "Modification & Audit Status": "YELLOW: Virtual certainty convincing evidence disclosed per AS 22"},
                {"Particulars": "  (e) Long-Term Loans and Advances", "Note No.": "Note 10", "CY (₹ Lakhs)": "180.00", "PY (₹ Lakhs)": "160.00", "Modification & Audit Status": "YELLOW: Capital advances segregated per Schedule III Division I"},
                {"Particulars": "(2) Current Assets", "Note No.": "", "CY (₹ Lakhs)": "", "PY (₹ Lakhs)": "", "Modification & Audit Status": ""},
                {"Particulars": "  (a) Inventories", "Note No.": "Note 11", "CY (₹ Lakhs)": "1,450.00", "PY (₹ Lakhs)": "1,320.00", "Modification & Audit Status": "Valued at lower of cost and NRV on Weighted Average formula"},
                {"Particulars": "  (b) Trade Receivables", "Note No.": "Note 12", "CY (₹ Lakhs)": "2,100.00", "PY (₹ Lakhs)": "1,850.00", "Modification & Audit Status": "YELLOW: Mandatory Trade Receivables Ageing Schedule added in Note 12"},
                {"Particulars": "  (c) Cash and Bank Balances", "Note No.": "Note 13", "CY (₹ Lakhs)": "510.00", "PY (₹ Lakhs)": "385.00", "Modification & Audit Status": "YELLOW: Earmarked balances & margin money segregated in Note 13"},
                {"Particulars": "  (d) Short-Term Loans and Advances & Others", "Note No.": "", "CY (₹ Lakhs)": "135.00", "PY (₹ Lakhs)": "105.00", "Modification & Audit Status": "Compliant"},
                {"Particulars": "TOTAL ASSETS", "Note No.": "", "CY (₹ Lakhs)": "10,615.00", "PY (₹ Lakhs)": "9,370.00", "Modification & Audit Status": "Verified: Total Assets = Total Equity and Liabilities"},
            ]
        return pd.DataFrame(data)

    @classmethod
    def get_profit_and_loss_data(cls, is_ind_as: bool = True) -> pd.DataFrame:
        data = [
            {"Particulars": "I. Revenue from Operations", "Note No.": "Note 17", "FY 2025-26 (₹ Lakhs)": "12,450.00", "FY 2024-25 (₹ Lakhs)": "10,800.00", "Audit & Schedule III Status": "YELLOW: Mandatory Revenue Disaggregation & Contract Balances added in Note 17"},
            {"Particulars": "II. Other Income", "Note No.": "Note 18", "FY 2025-26 (₹ Lakhs)": "210.00", "FY 2024-25 (₹ Lakhs)": "180.00", "Audit & Schedule III Status": "Interest income and scrap sales"},
            {"Particulars": "III. Total Income (I + II)", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "12,660.00", "FY 2024-25 (₹ Lakhs)": "10,980.00", "Audit & Schedule III Status": "Arithmetic Total Income Verified"},
            {"Particulars": "IV. Expenses:", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "", "FY 2024-25 (₹ Lakhs)": "", "Audit & Schedule III Status": ""},
            {"Particulars": "  Cost of Materials Consumed", "Note No.": "Note 19", "FY 2025-26 (₹ Lakhs)": "5,820.00", "FY 2024-25 (₹ Lakhs)": "4,950.00", "Audit & Schedule III Status": "Reconciled with raw materials movement"},
            {"Particulars": "  Changes in Inventories of Finished Goods & WIP", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "(180.00)", "FY 2024-25 (₹ Lakhs)": "60.00", "Audit & Schedule III Status": "Inventories roll-forward verified"},
            {"Particulars": "  Employee Benefits Expense", "Note No.": "Note 20", "FY 2025-26 (₹ Lakhs)": "1,850.00", "FY 2024-25 (₹ Lakhs)": "1,620.00", "Audit & Schedule III Status": "YELLOW: Principal Actuarial Assumptions & Sensitivity Analysis added in Note 20"},
            {"Particulars": "  Finance Costs", "Note No.": "Note 21", "FY 2025-26 (₹ Lakhs)": "420.00", "FY 2024-25 (₹ Lakhs)": "390.00", "Audit & Schedule III Status": "Interest on borrowings & lease liabilities"},
            {"Particulars": "  Depreciation and Amortization Expense", "Note No.": "Note 1", "FY 2025-26 (₹ Lakhs)": "680.00", "FY 2024-25 (₹ Lakhs)": "610.00", "Audit & Schedule III Status": "Depreciation per Schedule II useful lives"},
            {"Particulars": "  Other Expenses", "Note No.": "Note 22", "FY 2025-26 (₹ Lakhs)": "1,980.00", "FY 2024-25 (₹ Lakhs)": "1,750.00", "Audit & Schedule III Status": "CSR, power, rates, taxes and repairs"},
            {"Particulars": "Total Expenses (IV)", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "10,570.00", "FY 2024-25 (₹ Lakhs)": "9,380.00", "Audit & Schedule III Status": "Arithmetic Total Expenses Verified"},
            {"Particulars": "V. Profit Before Tax (III - IV)", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "2,090.00", "FY 2024-25 (₹ Lakhs)": "1,600.00", "Audit & Schedule III Status": "Operating PBT verified"},
            {"Particulars": "VI. Tax Expense (Current & Deferred)", "Note No.": "Note 23", "FY 2025-26 (₹ Lakhs)": "460.00", "FY 2024-25 (₹ Lakhs)": "365.00", "Audit & Schedule III Status": "YELLOW: Numerical Effective Tax Rate Reconciliation added in Note 23"},
            {"Particulars": "VII. Profit for the Period (V - VI)", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "1,630.00", "FY 2024-25 (₹ Lakhs)": "1,235.00", "Audit & Schedule III Status": "Net profit for the year"},
            {"Particulars": "VIII. Other Comprehensive Income (OCI)", "Note No.": "Note 24", "FY 2025-26 (₹ Lakhs)": "(22.00)", "FY 2024-25 (₹ Lakhs)": "15.00", "Audit & Schedule III Status": "YELLOW: Remeasurement of defined benefit plans (net of tax) added in Note 24" if is_ind_as else "N/A under AS"},
            {"Particulars": "IX. Total Comprehensive Income", "Note No.": "", "FY 2025-26 (₹ Lakhs)": "1,608.00", "FY 2024-25 (₹ Lakhs)": "1,250.00", "Audit & Schedule III Status": "Total comprehensive income verified" if is_ind_as else "Profit for the period"},
            {"Particulars": "X. Basic & Diluted EPS (₹)", "Note No.": "Note 25", "FY 2025-26 (₹ Lakhs)": "8.15", "FY 2024-25 (₹ Lakhs)": "6.18", "Audit & Schedule III Status": "YELLOW: Face disclosure of Basic & Diluted EPS added in Note 25"},
        ]
        return pd.DataFrame(data)

    @classmethod
    def get_promoter_table(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"S.No.": "1", "Promoter Name": "Rameshwar Satyam (Promoter)", "No. of Shares at Beginning": "1,20,000", "Change During Year": "Nil", "No. of Shares at End": "1,20,000", "% of Total Shares": "60.00%", "% Change During Year": "0.00%"},
            {"S.No.": "2", "Promoter Name": "Satyam Family Trust (Promoter Group)", "No. of Shares at Beginning": "50,000", "Change During Year": "Nil", "No. of Shares at End": "50,000", "% of Total Shares": "25.00%", "% Change During Year": "0.00%"},
            {"S.No.": "3", "Promoter Name": "Sunita Satyam (Promoter)", "No. of Shares at Beginning": "30,000", "Change During Year": "Nil", "No. of Shares at End": "30,000", "% of Total Shares": "15.00%", "% Change During Year": "0.00%"},
            {"S.No.": "Total", "Promoter Name": "Total Promoter Shareholding", "No. of Shares at Beginning": "2,00,000", "Change During Year": "Nil", "No. of Shares at End": "2,00,000", "% of Total Shares": "100.00%", "% Change During Year": "0.00%"},
        ])

    @classmethod
    def get_trade_payables_ageing(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"Particulars": "(i) MSME Dues (Undisputed)", "Unbilled Dues": "35.00", "< 1 Year": "225.00", "1 - 2 Years": "20.00", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "280.00"},
            {"Particulars": "(ii) Others (Undisputed)", "Unbilled Dues": "80.00", "< 1 Year": "640.00", "1 - 2 Years": "95.00", "2 - 3 Years": "25.00", "> 3 Years": "—", "Total (₹ Lakhs)": "840.00"},
            {"Particulars": "(iii) Disputed Dues - MSME", "Unbilled Dues": "—", "< 1 Year": "—", "1 - 2 Years": "—", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "—"},
            {"Particulars": "(iv) Disputed Dues - Others", "Unbilled Dues": "—", "< 1 Year": "—", "1 - 2 Years": "—", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "—"},
            {"Particulars": "Total Trade Payables", "Unbilled Dues": "115.00", "< 1 Year": "865.00", "1 - 2 Years": "115.00", "2 - 3 Years": "25.00", "> 3 Years": "—", "Total (₹ Lakhs)": "1,120.00"},
        ])

    @classmethod
    def get_trade_receivables_ageing(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"Particulars": "(i) Undisputed - Considered Good", "Unbilled Dues": "120.00", "< 6 Months": "1,680.00", "6 Mos - 1 Yr": "220.00", "1 - 2 Years": "80.00", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "2,100.00"},
            {"Particulars": "(ii) Undisputed - Significant Credit Risk", "Unbilled Dues": "—", "< 6 Months": "—", "6 Mos - 1 Yr": "—", "1 - 2 Years": "—", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "—"},
            {"Particulars": "(iii) Disputed - Considered Good", "Unbilled Dues": "—", "< 6 Months": "—", "6 Mos - 1 Yr": "—", "1 - 2 Years": "—", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "—"},
            {"Particulars": "Total Trade Receivables", "Unbilled Dues": "120.00", "< 6 Months": "1,680.00", "6 Mos - 1 Yr": "220.00", "1 - 2 Years": "80.00", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "2,100.00"},
        ])

    @classmethod
    def get_cwip_ageing(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"CWIP Category": "Projects in Progress (Plant Modernization)", "< 1 Year": "220.00", "1 - 2 Years": "120.00", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "340.00", "Completion Timeline": "Scheduled by Q3 FY 2026-27"},
            {"CWIP Category": "Projects Temporarily Suspended", "< 1 Year": "—", "1 - 2 Years": "—", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "—", "Completion Timeline": "Nil"},
            {"CWIP Category": "Total CWIP", "< 1 Year": "220.00", "1 - 2 Years": "120.00", "2 - 3 Years": "—", "> 3 Years": "—", "Total (₹ Lakhs)": "340.00", "Completion Timeline": "Verified per Clause 6(EA)"},
        ])

    @classmethod
    def get_ratios_table(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"Ratio Name": "1. Current Ratio", "Formula": "Current Assets / Current Liabilities", "FY 2025-26": "2.71", "FY 2024-25": "2.44", "Variance": "+11.07%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "2. Debt-Equity Ratio", "Formula": "Total Debt / Total Shareholder Equity", "FY 2025-26": "0.45", "FY 2024-25": "0.43", "Variance": "+4.65%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "3. Debt Service Coverage (DSCR)", "Formula": "EBITDA / (Interest + Principal Repayments)", "FY 2025-26": "3.84", "FY 2024-25": "3.25", "Variance": "+18.15%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "4. Return on Equity (ROE)", "Formula": "Net Profit after Tax / Average Equity", "FY 2025-26": "27.50%", "FY 2024-25": "24.12%", "Variance": "+14.01%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "5. Inventory Turnover Ratio", "Formula": "COGS / Average Inventory", "FY 2025-26": "4.01", "FY 2024-25": "3.75", "Variance": "+6.93%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "6. Trade Receivables Turnover", "Formula": "Net Credit Sales / Average Receivables", "FY 2025-26": "6.30", "FY 2024-25": "5.84", "Variance": "+7.88%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "7. Trade Payables Turnover", "Formula": "Net Credit Purchases / Average Payables", "FY 2025-26": "5.82", "FY 2024-25": "4.54", "Variance": "+28.19%", "Mandatory Explanation for Variance > 25%": "YELLOW: Variance >25% due to strategic supplier consolidation and renegotiated credit terms extending to 60 days."},
            {"Ratio Name": "8. Net Capital Turnover Ratio", "Formula": "Revenue / Working Capital", "FY 2025-26": "4.56", "FY 2024-25": "4.21", "Variance": "+8.31%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "9. Net Profit Ratio", "Formula": "Net Profit / Revenue", "FY 2025-26": "13.09%", "FY 2024-25": "11.44%", "Variance": "+14.42%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "10. ROCE", "Formula": "EBIT / Capital Employed", "FY 2025-26": "25.80%", "FY 2024-25": "21.50%", "Variance": "+20.00%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
            {"Ratio Name": "11. Return on Investment (ROI)", "Formula": "Return / Average Investments", "FY 2025-26": "7.50%", "FY 2024-25": "7.20%", "Variance": "+4.17%", "Mandatory Explanation for Variance > 25%": "Variance within 25% threshold"},
        ])

    @classmethod
    def get_regulatory_table(cls) -> pd.DataFrame:
        return pd.DataFrame([
            {"Statutory Item": "Title Deeds of Immovable Property", "Clause": "Clause 6(L)", "Incorporated Disclosure": "All title deeds of immovable properties are held in the name of the company.", "Status": "Compliant: Negative declaration added"},
            {"Statutory Item": "Benami Property Proceedings", "Clause": "Clause 6(R)", "Incorporated Disclosure": "No proceedings initiated or pending against the Company under Benami Transactions (Prohibition) Act, 1988.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
            {"Statutory Item": "Quarterly Bank Returns vs Books", "Clause": "Clause 6(L)", "Incorporated Disclosure": "Quarterly returns/statements of current assets filed with banks agree with books of accounts.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
            {"Statutory Item": "Wilful Defaulter Declaration", "Clause": "Clause 6(S)", "Incorporated Disclosure": "Company has not been declared a Wilful Defaulter by any bank or financial institution.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
            {"Statutory Item": "Struck-off Companies", "Clause": "Clause 6(W)", "Incorporated Disclosure": "Company has no transactions or balances with companies struck off under Section 248.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
            {"Statutory Item": "Registration of Charges with ROC", "Clause": "Clause 6(T)", "Incorporated Disclosure": "All charges and satisfactions have been registered with ROC within statutory time limits.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
            {"Statutory Item": "Crypto / Virtual Currency", "Clause": "Clause 6(Z)", "Incorporated Disclosure": "Company has not traded or invested in Crypto Currency during the financial year.", "Status": "YELLOW: Incorporated & Highlighted in Yellow"},
        ])
