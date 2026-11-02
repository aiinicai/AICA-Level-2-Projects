"""Comprehensive Compliance & Technical Audit Engine for Financial Reporting Review.

Performs deep, rigorous multi-standard audits against:
- Ind AS Standards (Ind AS 1, 2, 7, 8, 12, 16, 19, 20, 21, 23, 24, 33, 36, 37, 38, 107, 108, 109, 115, 116)
- AS Standards (AS 1, 2, 3, 9, 10, 15, 18, 20, 22, 29)
- Schedule III (2021 Amendments: Ageing, Ratios, Title deeds, Struck-off, CWIP, Promoter shareholding, Bank returns)
- Companies Act, 2013 (Sections 129, 134, 135, 185, 186, 188, 197)
- CARO 2020 (Clauses 3(i) to 3(xxi))
- ICAI FRRB Precedents (Study on Compliance of Ind AS Framework)

Uses deterministic rule codes to guarantee 100% uniformity and repeatability across all review runs.
"""

import re
from typing import Dict, Any, List, Optional


class ComplianceEngine:
    """Deep-audit engine executing comprehensive FRRB compliance reviews across corporate filings."""

    @classmethod
    def run_review(
        cls,
        extracted_doc: Dict[str, Any],
        profile: Dict[str, Any],
        review_mode: str = "Option A"
    ) -> Dict[str, Any]:
        """Runs the complete suite of deep compliance procedures across all sections and pages."""
        full_text = extracted_doc.get("full_text", "")
        pages = extracted_doc.get("pages", [])
        sections = extracted_doc.get("sections", {})
        framework = profile.get("framework", "Indian Accounting Standards (Ind AS)")
        is_ind_as = "ind as" in framework.lower()
        division = profile.get("schedule_iii_division", "Division II")
        is_listed = profile.get("listing_status", "Unlisted").lower() == "listed"

        all_candidate_issues: List[Dict[str, Any]] = []

        # 1. Arithmetic & Primary Statement Equations
        all_candidate_issues.extend(cls._check_arithmetic(full_text, pages, review_mode))

        # 2. Schedule III Part I & II (2021 Amendments)
        all_candidate_issues.extend(cls._check_schedule_iii(full_text, pages, is_ind_as, division, review_mode))

        # 3. Ind AS / AS Accounting Standards
        all_candidate_issues.extend(cls._check_accounting_standards(full_text, pages, is_ind_as, is_listed, review_mode, profile))

        # 4. Companies Act, 2013 Statutory Provisions
        all_candidate_issues.extend(cls._check_companies_act(full_text, pages, review_mode))

        # 5. Statutory Auditor's Report & CARO 2020 Review
        all_candidate_issues.extend(cls._check_auditor_and_caro(full_text, pages, sections, is_listed, review_mode))

        # Deduplicate strictly by unique rule_code to guarantee uniformity
        unique_issues: List[Dict[str, Any]] = []
        seen_rule_codes = set()
        
        for idx, item in enumerate(all_candidate_issues, start=1):
            rule_code = item.get("rule_code", f"RULE-{idx}")
            if rule_code not in seen_rule_codes:
                seen_rule_codes.add(rule_code)
                item_copy = dict(item)
                item_copy["issue_id"] = f"FRR-{review_mode[-1]}-{len(unique_issues)+1:03d}"
                unique_issues.append(item_copy)

        high_risk_count = sum(1 for i in unique_issues if i.get("risk") == "High")
        med_risk_count = sum(1 for i in unique_issues if i.get("risk") == "Medium")
        low_risk_count = sum(1 for i in unique_issues if i.get("risk") == "Low")

        categories_count: Dict[str, int] = {}
        for i in unique_issues:
            cat = i.get("category", "General")
            categories_count[cat] = categories_count.get(cat, 0) + 1

        return {
            "review_mode": review_mode,
            "total_issues": len(unique_issues),
            "high_risk_count": high_risk_count,
            "med_risk_count": med_risk_count,
            "low_risk_count": low_risk_count,
            "categories_breakdown": categories_count,
            "issues": unique_issues,
        }

    # =========================================================================
    # 1. ARITHMETIC & CROSS-STATEMENT INTEGRITY CHECKS
    # =========================================================================
    @classmethod
    def _check_arithmetic(cls, text: str, pages: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        issues = []
        bs_page = cls._find_page_containing(pages, ["balance sheet", "statement of financial position"])
        page_str = f"Page {bs_page}" if bs_page else "Balance Sheet"

        # Balance Sheet Equation: Assets = Equity + Liabilities
        m_assets = re.search(r"total\s+assets[^\d]{0,60}?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        m_liab = re.search(r"total\s+equity\s+and\s+liabilities[^\d]{0,60}?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)

        if m_assets and m_liab:
            try:
                v_assets = float(m_assets.group(1).replace(",", ""))
                v_liab = float(m_liab.group(1).replace(",", ""))
                diff = abs(v_assets - v_liab)

                if diff > 0.01:
                    extract = f"Total Assets = {v_assets:,.2f} | Total Equity and Liabilities = {v_liab:,.2f}"
                    issues.append({
                        "rule_code": "ARITH-BS-EQUATION",
                        "category": "Arithmetic & Balance Sheet Integrity",
                        "ref": f"{page_str} / Primary Balance Sheet",
                        "description": f"Balance Sheet Equation Out of Balance: Difference of {diff:,.2f} detected.",
                        "current_disclosure": extract,
                        "suggested_correction": (
                            f"Reconcile Assets ({v_assets:,.2f}) and Liabilities & Equity ({v_liab:,.2f}). "
                            "Check for unposted journal entries or omission in current/non-current line items."
                        ),
                        "statutory_ref": "Section 129(1) of Companies Act, 2013 read with Schedule III (Part I)",
                        "action": "Immediate Pre-Finalisation Correction Required: Adjust trial balance line items before sign-off.",
                        "status": "Critical Correction" if mode == "Option A" else "Confirmed Discrepancy",
                        "risk": "High",
                        "highlight_cells": ["Total Assets", "Total Equity and Liabilities"]
                    })
            except ValueError:
                pass

        # Cash Flow Statement: Closing Cash vs Balance Sheet Note
        cfs_page = cls._find_page_containing(pages, ["statement of cash flows", "cash flow statement"])
        cfs_page_str = f"Page {cfs_page}" if cfs_page else "Cash Flow Statement"

        m_cfs_end = re.search(r"cash\s+and\s+cash\s+equivalents\s+at\s+(?:the\s+)?end[^\d\n\r]*?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        m_bs_cash = re.search(r"cash\s+and\s+cash\s+equivalents[^\d\n\r]*?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)

        if m_cfs_end and m_bs_cash:
            try:
                cfs_val = float(m_cfs_end.group(1).replace(",", ""))
                bs_cash_val = float(m_bs_cash.group(1).replace(",", ""))
                if abs(cfs_val - bs_cash_val) > 1.0:
                    extract = f"Cash Flow Closing Cash = {cfs_val:,.2f} vs Balance Sheet Cash Note = {bs_cash_val:,.2f}"
                    issues.append({
                        "rule_code": "ARITH-CFS-RECON",
                        "category": "Arithmetic & Statement Reconciliation",
                        "ref": f"{cfs_page_str} / Cash Flow vs Balance Sheet",
                        "description": "Closing Cash & Cash Equivalents in Cash Flow Statement does not tie to Balance Sheet line item.",
                        "current_disclosure": extract,
                        "suggested_correction": "Reconcile bank overdraft, book overdraft, or restricted deposits included in Cash & Cash Equivalents.",
                        "statutory_ref": "Ind AS 7, Paragraph 45 / AS 3, Paragraph 43",
                        "action": "Verify definition of Cash & Cash Equivalents and reconcile discrepancies.",
                        "status": "Action Required" if mode == "Option A" else "Reporting Inconsistency",
                        "risk": "Medium",
                        "highlight_cells": ["Closing Cash and Cash Equivalents"]
                    })
            except ValueError:
                pass

        return issues

    # =========================================================================
    # 2. SCHEDULE III (PART I, PART II & 2021 AMENDMENTS) CHECKS
    # =========================================================================
    @classmethod
    def _check_schedule_iii(
        cls,
        text: str,
        pages: List[Dict[str, Any]],
        is_ind_as: bool,
        division: str,
        mode: str
    ) -> List[Dict[str, Any]]:
        issues = []
        div_ref = f"Schedule III, {division}, Part I"

        # 1. Trade Payables Ageing Schedule
        has_tp_note = re.search(r"trade\s+payables\b", text, re.IGNORECASE)
        has_tp_ageing = bool(re.search(r"trade\s+payables?\s+ageing\s+schedule", text, re.IGNORECASE) or (
            re.search(r"less\s+than\s+1\s+year", text, re.IGNORECASE) and
            re.search(r"1\s*-\s*2\s+years?", text, re.IGNORECASE) and
            re.search(r"(?:msme\s+dues|others|unbilled\s+dues)", text, re.IGNORECASE)
        ))
        if has_tp_note and not has_tp_ageing:
            tp_page = cls._find_page_containing(pages, ["trade payables"])
            ref_str = f"Page {tp_page} / Note on Trade Payables" if tp_page else "Note on Trade Payables"
            issues.append({
                "rule_code": "SCH3-TP-AGEING",
                "category": "Schedule III - Mandatory Ageing Schedules",
                "ref": ref_str,
                "description": "Mandatory Trade Payables Ageing Schedule is missing from Notes to Accounts.",
                "current_disclosure": "Trade payables presented without statutory ageing breakdown (<1 yr, 1-2 yrs, 2-3 yrs, >3 yrs).",
                "suggested_correction": (
                    "Insert MCA mandatory ageing table: categorize into (i) MSME dues, (ii) Others, "
                    "(iii) Disputed dues - MSME, and (iv) Disputed dues - Others across the 4 age buckets, plus Unbilled dues."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(FA) / MCA Notification G.S.R. 207(E)",
                "action": "Draft and include mandatory Trade Payables ageing table.",
                "status": "Mandatory Disclosure Missing" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "High",
                "highlight_cells": ["Trade Payables Note - Ageing Schedule"]
            })

        # 2. Section 22 MSMED Act Disclosures
        has_msme_split = bool(re.search(r"(?:msmed\s+act|micro\s+and\s+small\s+enterprises|interest\s+due\s+thereon|principal\s+amount\s+remaining\s+unpaid)", text, re.IGNORECASE))
        if has_tp_note and not has_msme_split:
            tp_page = cls._find_page_containing(pages, ["trade payables"])
            ref_str = f"Page {tp_page} / Note on Trade Payables" if tp_page else "Note on Trade Payables"
            issues.append({
                "rule_code": "SCH3-MSMED-SEC22",
                "category": "Schedule III & MSMED Act Compliance",
                "ref": ref_str,
                "description": "Omission of MSMED Act, 2006 Section 22 disclosures in Trade Payables Note.",
                "current_disclosure": "No separate identification of dues to Micro and Small Enterprises or interest accrued thereon.",
                "suggested_correction": (
                    "Add Note on MSME dues disclosing: (a) Principal and interest remaining unpaid, (b) Interest paid under MSMED Act, "
                    "(c) Interest due and payable, and (d) Further interest accrued and remaining unpaid."
                ),
                "statutory_ref": "Section 22 of MSMED Act, 2006 read with Schedule III Part I",
                "action": "Obtain MSME status confirmations from vendors and disclose outstanding dues under Section 22.",
                "status": "Action Required" if mode == "Option A" else "Statutory Disclosure Omission",
                "risk": "High",
                "highlight_cells": ["Total Outstanding Dues to Micro and Small Enterprises"]
            })

        # 3. Trade Receivables Ageing Schedule
        has_tr_note = re.search(r"trade\s+receivables\b", text, re.IGNORECASE)
        has_tr_ageing = bool(re.search(r"trade\s+receivables?\s+ageing\s+schedule", text, re.IGNORECASE) or (
            re.search(r"less\s+than\s+6\s+months", text, re.IGNORECASE) and
            re.search(r"(?:undisputed|disputed|credit\s+impaired)", text, re.IGNORECASE)
        ))
        if has_tr_note and not has_tr_ageing:
            tr_page = cls._find_page_containing(pages, ["trade receivables"])
            ref_str = f"Page {tr_page} / Note on Trade Receivables" if tr_page else "Note on Trade Receivables"
            issues.append({
                "rule_code": "SCH3-TR-AGEING",
                "category": "Schedule III - Mandatory Ageing Schedules",
                "ref": ref_str,
                "description": "Mandatory Trade Receivables Ageing Schedule is missing.",
                "current_disclosure": "Trade receivables presented without Schedule III age brackets (<6 mos, 6 mos-1 yr, 1-2 yrs, 2-3 yrs, >3 yrs).",
                "suggested_correction": (
                    "Present Schedule III ageing table dividing receivables into Undisputed/Disputed and distinguishing "
                    "between Good, Significant Increase in Credit Risk, and Credit Impaired, along with Unbilled dues."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(L) / MCA Notification G.S.R. 207(E)",
                "action": "Incorporate Trade Receivables ageing schedule.",
                "status": "Mandatory Disclosure Missing" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "High",
                "highlight_cells": ["Trade Receivables Ageing Schedule"]
            })

        # 4. Capital Work-in-Progress (CWIP) Ageing & Completion Schedule
        has_cwip = re.search(r"capital\s+work[- ]in[- ]progress|cwip\b", text, re.IGNORECASE)
        has_cwip_ageing = bool(re.search(r"cwip\s+ageing\s+schedule|projects\s+in\s+progress|projects\s+temporarily\s+suspended", text, re.IGNORECASE))
        if has_cwip and not has_cwip_ageing:
            cwip_page = cls._find_page_containing(pages, ["capital work-in-progress", "cwip"])
            ref_str = f"Page {cwip_page} / CWIP Note" if cwip_page else "Note on Capital Work-in-Progress"
            issues.append({
                "rule_code": "SCH3-CWIP-AGEING",
                "category": "Schedule III - Capital Work-in-Progress",
                "ref": ref_str,
                "description": "Mandatory Capital Work-in-Progress (CWIP) Ageing Schedule is missing.",
                "current_disclosure": "CWIP presented as a lump-sum carrying value without age analysis (<1 yr, 1-2 yrs, 2-3 yrs, >3 yrs).",
                "suggested_correction": (
                    "Disclose CWIP ageing table categorized into: (a) Projects in progress and (b) Projects temporarily suspended, "
                    "across the 4 statutory age brackets, and disclose completion schedule for delayed projects."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(EA) / MCA Notification G.S.R. 207(E)",
                "action": "Provide CWIP ageing schedule and completion plan for ongoing capital projects.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "High",
                "highlight_cells": ["Capital Work-in-Progress Ageing Schedule"]
            })

        # 5. Promoter Shareholding Table
        has_share_cap = re.search(r"share\s+capital\b", text, re.IGNORECASE)
        has_promoter_table = bool(re.search(r"promoter(?:s|'s)?\s+shareholding", text, re.IGNORECASE) or re.search(r"shares\s+held\s+by\s+promoters", text, re.IGNORECASE))
        if has_share_cap and not has_promoter_table:
            sc_page = cls._find_page_containing(pages, ["share capital"])
            ref_str = f"Page {sc_page} / Note on Share Capital" if sc_page else "Note on Share Capital"
            issues.append({
                "rule_code": "SCH3-PROMOTER-TABLE",
                "category": "Schedule III - Share Capital Disclosures",
                "ref": ref_str,
                "description": "Mandatory Disclosure of Promoter Shareholding and % Change during the Year is missing.",
                "current_disclosure": "Note on Share Capital omits the specific Promoter Shareholding table.",
                "suggested_correction": (
                    "Insert table showing: (i) Promoter name, (ii) Number of shares held at year end, "
                    "(iii) % of total shares, and (iv) % Change during the year."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(J) / MCA Notification G.S.R. 207(E)",
                "action": "Include Promoter Shareholding table with % change during the year.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "Medium",
                "highlight_cells": ["Promoter Shareholding Disclosure"]
            })

        # 6. Mandatory Analytical Ratios & >25% Variance Explanations
        has_ratios = bool(re.search(r"(?:analytical\s+ratios|financial\s+ratios|ratio\s+analysis)", text, re.IGNORECASE))
        has_ratio_explanation = bool(re.search(r"(?:explanation\s+for\s+variance|reasons?\s+for\s+variance|variance\s+exceeding\s+25%)", text, re.IGNORECASE))
        if not has_ratios:
            issues.append({
                "rule_code": "SCH3-RATIOS-OMISSION",
                "category": "Schedule III - Financial Ratios",
                "ref": "Notes to Accounts - Key Financial Ratios",
                "description": "Complete omission of the 11 Mandatory Analytical Ratios required under amended Schedule III.",
                "current_disclosure": "No ratio disclosures found in notes to financial statements.",
                "suggested_correction": (
                    "Provide note disclosing all 11 mandatory ratios: Current Ratio, Debt-Equity Ratio, DSCR, Return on Equity, "
                    "Inventory Turnover, Trade Receivables Turnover, Trade Payables Turnover, Net Capital Turnover, "
                    "Net Profit Ratio, Return on Capital Employed, Return on Investment, with definitions and prior year comparatives."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(VA) / MCA Notification G.S.R. 207(E)",
                "action": "Compute and disclose the 11 mandatory ratios with prior period figures.",
                "status": "Mandatory Disclosure Missing" if mode == "Option A" else "Material Schedule III Omission",
                "risk": "High",
                "highlight_cells": ["Key Financial Ratios Note"]
            })
        elif not has_ratio_explanation:
            issues.append({
                "rule_code": "SCH3-RATIOS-VARIANCE",
                "category": "Schedule III - Financial Ratios",
                "ref": "Notes to Accounts - Key Financial Ratios",
                "description": "Ratios disclosed without mandatory explanations for variances exceeding 25%.",
                "current_disclosure": "Analytical ratios table present but lacks explanatory footnotes for significant year-on-year variations.",
                "suggested_correction": (
                    "Provide granular reasons explaining operational and market drivers for every ratio where variance "
                    "between current year and previous year is more than 25%."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(VA)",
                "action": "Add explanatory commentary for all ratio variances > 25%.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "Medium",
                "highlight_cells": ["Ratio Variance Explanations"]
            })

        # 7. Immovable Property Title Deeds Not Held in Name of Company
        has_title_deeds_mention = bool(re.search(r"title\s+deeds\s+of\s+immovable\s+propert(?:y|ies)", text, re.IGNORECASE))
        if not has_title_deeds_mention:
            issues.append({
                "rule_code": "SCH3-TITLE-DEEDS",
                "category": "Schedule III - Property & Title Deeds",
                "ref": "Notes to Accounts - Property, Plant and Equipment",
                "description": "Schedule III disclosure on Title Deeds of Immovable Property not held in company's name is missing.",
                "current_disclosure": "No statement or disclosure table regarding whether title deeds of immovable properties are held in company name.",
                "suggested_correction": (
                    "Add Schedule III confirmation confirming either that all title deeds of immovable properties are held "
                    "in the name of the company or disclose the specific details table if held in promoter/third party name."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(L)",
                "action": "Incorporate statutory confirmation regarding title deeds of immovable properties.",
                "status": "Disclosure Missing" if mode == "Option A" else "Technical Non-Compliance",
                "risk": "Medium",
                "highlight_cells": ["Title Deeds of Immovable Property Note"]
            })

        # 8. Transactions with Struck-Off Companies
        has_struck_off = bool(re.search(r"struck[- ]off\s+companies", text, re.IGNORECASE))
        if not has_struck_off:
            issues.append({
                "rule_code": "SCH3-STRUCK-OFF",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Omission of mandatory Schedule III disclosure on Relationships with Struck-off Companies.",
                "current_disclosure": "No statement provided regarding whether company has transactions with companies struck off under Section 248.",
                "suggested_correction": (
                    "Disclose details of transactions with struck-off companies (nature, balance, relationship) or incorporate "
                    "explicit negative confirmation that company has no transactions with struck-off companies."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(W) / Section 248 of Companies Act, 2013",
                "action": "Add regulatory note on transactions with struck-off companies.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "Medium",
                "highlight_cells": ["Struck-off Companies Note"]
            })

        # 9. Registration and Satisfaction of Charges with ROC
        has_charges = bool(re.search(r"charges?\s+(?:registered|satisfaction|creation|modification)\s+with\s+(?:the\s+)?roc", text, re.IGNORECASE) or re.search(r"registration\s+of\s+charges", text, re.IGNORECASE))
        has_borrowings = bool(re.search(r"borrowings\b", text, re.IGNORECASE))
        if has_borrowings and not has_charges:
            issues.append({
                "rule_code": "SCH3-ROC-CHARGES",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Borrowings / Additional Regulatory Information",
                "description": "Disclosure regarding Registration of Charges or Satisfaction with ROC is missing.",
                "current_disclosure": "Borrowings secured by assets are disclosed, but status of charge registration/satisfaction with ROC beyond statutory period is not disclosed.",
                "suggested_correction": (
                    "Disclose whether any charges or satisfactions are pending registration with ROC beyond statutory period, "
                    "and provide reasons for delay per Section 77/82."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(T)",
                "action": "Confirm status of ROC charge registration and satisfaction in Borrowings note.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Deficiency",
                "risk": "Medium",
                "highlight_cells": ["Registration of Charges Note"]
            })

        # 10. Rounding-off Verification
        has_turnover_large = bool(re.search(r"turnover|revenue\s+from\s+operations", text, re.IGNORECASE))
        has_rounding_unit = bool(re.search(r"\((?:in\s+₹\s*)?(?:lakhs?|crores?|millions?|thousands?)\)", text, re.IGNORECASE))
        if not has_rounding_unit and has_turnover_large:
            issues.append({
                "rule_code": "SCH3-ROUNDING-OFF",
                "category": "Schedule III - Presentation & Rounding Off",
                "ref": "Primary Statements Heading",
                "description": "Unit of measurement / Rounding-off denomination not clearly indicated in statement headers.",
                "current_disclosure": "Headings do not explicitly specify whether figures are rounded in ₹ Lakhs, ₹ Crores, etc.",
                "suggested_correction": (
                    "Specify mandatory rounding off denomination at top of each financial statement as mandated by Schedule III Clause 4."
                ),
                "statutory_ref": "Schedule III, General Instructions Clause 4",
                "action": "Add explicit denomination indicator (e.g. '₹ in Lakhs') in header.",
                "status": "Presentation Defect",
                "risk": "Low",
                "highlight_cells": ["Primary Statements Header"]
            })

        # 11. Wilful Defaulter Declaration
        has_wilful = bool(re.search(r"wilful\s+defaulter", text, re.IGNORECASE))
        if not has_wilful:
            issues.append({
                "rule_code": "SCH3-WILFUL-DEFAULTER",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Schedule III declaration on Wilful Defaulter status is not disclosed.",
                "current_disclosure": "No declaration whether company is declared a wilful defaulter by any bank or financial institution.",
                "suggested_correction": "Disclose whether the company is declared a wilful defaulter by any lender under Schedule III Clause 6(S).",
                "statutory_ref": f"{div_ref}, Clause 6(S)",
                "action": "Add statutory wilful defaulter confirmation.",
                "status": "Action Required",
                "risk": "High",
                "highlight_cells": ["Wilful Defaulter Note"]
            })

        # 12. Benami Property Proceedings
        has_benami = bool(re.search(r"benami\s+propert(?:y|ies)", text, re.IGNORECASE))
        if not has_benami:
            issues.append({
                "rule_code": "SCH3-BENAMI-PROPERTY",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Mandatory Schedule III disclosure on Benami Property proceedings is missing.",
                "current_disclosure": "No statement provided regarding proceedings under Benami Transactions (Prohibition) Act, 1988.",
                "suggested_correction": "Incorporate statutory confirmation regarding Benami property proceedings under Clause 6(R).",
                "statutory_ref": f"{div_ref}, Clause 6(R)",
                "action": "Add Benami property declaration.",
                "status": "Action Required",
                "risk": "Medium",
                "highlight_cells": ["Benami Property Note"]
            })

        # 13. Crypto Currency / Virtual Currency
        has_crypto = bool(re.search(r"crypto\s+currency|virtual\s+currency", text, re.IGNORECASE))
        if not has_crypto:
            issues.append({
                "rule_code": "SCH3-CRYPTO-CURRENCY",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Schedule III disclosure on Crypto or Virtual Currency transactions is missing.",
                "current_disclosure": "No statement confirming trading or investment in Crypto Currency during the financial year.",
                "suggested_correction": "Provide declaration whether company has traded or invested in Crypto Currency under Clause 6(Z).",
                "statutory_ref": f"{div_ref}, Clause 6(Z)",
                "action": "Include Crypto Currency declaration.",
                "status": "Action Required",
                "risk": "Low",
                "highlight_cells": ["Crypto Currency Note"]
            })

        # 14. Cash and Bank Balances: Earmarked Balances & Restrictions
        has_bank_bal = bool(re.search(r"bank\s+balances?\b|cash\s+and\s+cash\s+equivalents\b", text, re.IGNORECASE))
        has_earmarked = bool(re.search(r"earmarked\s+balances?|restricted\s+(?:bank\s+)?balances?|margin\s+money|unpaid\s+dividend", text, re.IGNORECASE))
        if has_bank_bal and not has_earmarked:
            issues.append({
                "rule_code": "SCH3-EARMARKED-BANK",
                "category": "Schedule III - Cash and Bank Balances",
                "ref": "Notes to Accounts - Cash and Bank Balances",
                "description": "Omission of disclosure regarding Earmarked Balances / Restricted Bank Deposits.",
                "current_disclosure": "Bank balances disclosed without separate disclosure of earmarked balances (e.g. unpaid dividend, margin money held against bank guarantees).",
                "suggested_correction": (
                    "Separately state: (a) Earmarked balances with banks (e.g. unpaid dividend), (b) Balances with banks to the extent held as margin money, "
                    "and (c) Bank deposits with more than 12 months maturity under Other Financial Assets."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(I) / Chapter 1 ICAI FRRB Study",
                "action": "Disclose earmarked balances and margin money deposits separately in Bank Balances note.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Deficiency",
                "risk": "Medium",
                "highlight_cells": ["Earmarked Bank Balances Note"]
            })

        # 15. Receivables from Related Parties / Directors
        has_tr = bool(re.search(r"trade\s+receivables\b", text, re.IGNORECASE))
        has_dir_debts = bool(re.search(r"receivables?\s+due\s+by\s+directors?|debts\s+due\s+by\s+directors?|officers\s+of\s+the\s+company", text, re.IGNORECASE))
        if has_tr and not has_dir_debts:
            issues.append({
                "rule_code": "SCH3-DIRECTOR-RECEIVABLES",
                "category": "Schedule III - Trade Receivables",
                "ref": "Notes to Accounts - Trade Receivables",
                "description": "Statutory disclosure on debts due by directors, officers, or related firms is missing.",
                "current_disclosure": "Trade receivables note does not disclose whether any debts are due by directors or other officers of the company.",
                "suggested_correction": (
                    "Disclose separately receivables due by directors or other officers of the company, either severally or jointly, "
                    "or firms/private companies in which any director is a partner/director, or provide negative confirmation."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(L) / ICAI FRRB Study Observation 30-31",
                "action": "Add statutory disclosure regarding receivables due by directors/officers.",
                "status": "Disclosure Missing",
                "risk": "Medium",
                "highlight_cells": ["Receivables Due by Directors Note"]
            })

        # 16. Borrowings Secured by Current Assets - Quarterly Bank Returns Reconciliation
        has_borrowings = bool(re.search(r"borrowings\b|working\s+capital\s+facilities|cash\s+credit", text, re.IGNORECASE))
        has_qtr_bank_returns = bool(re.search(r"quarterly\s+(?:statements?|returns?).*filed\s+with\s+banks?|statements\s+of\s+current\s+assets\s+filed\s+with\s+banks", text, re.IGNORECASE))
        if has_borrowings and not has_qtr_bank_returns:
            issues.append({
                "rule_code": "SCH3-BANK-RETURNS-RECON",
                "category": "Schedule III - Borrowings & Bank Reconciliations",
                "ref": "Notes to Accounts - Borrowings / Regulatory Information",
                "description": "Omission of Schedule III disclosure reconciling quarterly statements filed with banks with books of accounts.",
                "current_disclosure": "Company has working capital facilities/borrowings secured by current assets, but does not state whether quarterly returns filed with banks agree with books.",
                "suggested_correction": (
                    "Disclose whether quarterly returns/statements of current assets filed with banks/FIs agree with books of accounts. "
                    "If not, provide summary of reconciliation and reasons for material discrepancies per Schedule III Clause 6(L)."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(L) / MCA Notification G.S.R. 207(E)",
                "action": "Include quarterly bank returns reconciliation disclosure in Borrowings note.",
                "status": "Action Required" if mode == "Option A" else "Schedule III Non-Compliance",
                "risk": "High",
                "highlight_cells": ["Quarterly Bank Returns Note"]
            })

        # 17. Undisclosed Income Surrendered in Tax Assessments
        has_undisclosed_tax = bool(re.search(r"undisclosed\s+income|search\s+or\s+survey|surrendered\s+or\s+disclosed\s+as\s+income", text, re.IGNORECASE))
        if not has_undisclosed_tax:
            issues.append({
                "rule_code": "SCH3-UNDISCLOSED-INCOME",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Schedule III disclosure regarding Undisclosed Income surrendered in tax assessments is missing.",
                "current_disclosure": "No declaration stating whether transactions not recorded in books have been surrendered/disclosed in Income Tax assessments.",
                "suggested_correction": (
                    "Disclose particulars of any transactions not recorded in books surrendered or disclosed as income during the year "
                    "in tax assessments under Income Tax Act, 1961, or provide explicit negative confirmation."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(X) / MCA Notification G.S.R. 207(E)",
                "action": "Add statutory undisclosed income declaration.",
                "status": "Action Required",
                "risk": "Medium",
                "highlight_cells": ["Undisclosed Income Note"]
            })

        # 18. Loans/Advances to Promoters, Directors, KMPs and Related Parties
        has_loans_promoters = bool(re.search(r"loans\s+or\s+advances\s+to\s+promoters|loans\s+repayable\s+on\s+demand", text, re.IGNORECASE))
        has_any_loans = bool(re.search(r"loans\s+and\s+advances\b|loans\s+given", text, re.IGNORECASE))
        if has_any_loans and not has_loans_promoters:
            issues.append({
                "rule_code": "SCH3-LOANS-TO-PROMOTERS-KMPS",
                "category": "Schedule III - Loans & Advances Disclosures",
                "ref": "Notes to Accounts - Loans and Advances",
                "description": "Schedule III disclosure on Loans/Advances to Promoters, Directors, KMPs and Related Parties is missing.",
                "current_disclosure": "No specific disclosure table indicating loans/advances in nature of loans granted to promoters, directors, KMPs, whether repayable on demand or without terms.",
                "suggested_correction": (
                    "Disclose amount of loans or advances in nature of loans granted to promoters, directors, KMPs and related parties "
                    "that are repayable on demand or without specifying any terms or period of repayment, along with percentage to total loans."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(E) / MCA Notification G.S.R. 207(E)",
                "action": "Provide statutory loans to promoters/KMPs table or negative confirmation.",
                "status": "Action Required",
                "risk": "High",
                "highlight_cells": ["Loans to Promoters and KMPs Note"]
            })

        # 19. Intangible Assets Under Development Ageing Schedule
        has_intangible = bool(re.search(r"intangible\s+assets?\s+under\s+development|iaud\b", text, re.IGNORECASE))
        has_iaud_ageing = bool(re.search(r"iaud\s+ageing\s+schedule|intangible\s+assets?\s+under\s+development\s+ageing", text, re.IGNORECASE))
        if has_intangible and not has_iaud_ageing:
            issues.append({
                "rule_code": "SCH3-INTANGIBLE-CWIP",
                "category": "Schedule III - Intangible Assets",
                "ref": "Notes to Accounts - Intangible Assets",
                "description": "Mandatory Intangible Assets under Development Ageing Schedule is missing.",
                "current_disclosure": "Intangible assets under development presented without statutory ageing breakdown and completion plan.",
                "suggested_correction": (
                    "Present ageing schedule for Intangible assets under development categorized into Projects in progress and "
                    "Projects temporarily suspended across <1 yr, 1-2 yrs, 2-3 yrs, >3 yrs, and completion schedule for delayed projects."
                ),
                "statutory_ref": f"{div_ref}, General Instructions Clause 6(EB)",
                "action": "Incorporate Intangible Assets under Development ageing table.",
                "status": "Mandatory Disclosure Missing",
                "risk": "Medium",
                "highlight_cells": ["Intangible Assets Under Development Note"]
            })

        # 20. Compliance with Layers of Companies
        has_layers = bool(re.search(r"layers\s+of\s+companies|number\s+of\s+layers|clause\s+\(87\)\s+of\s+section\s+2", text, re.IGNORECASE))
        has_subsidiaries = bool(re.search(r"subsidiaries\b|subsidiary\s+compan(?:y|ies)", text, re.IGNORECASE))
        if has_subsidiaries and not has_layers:
            issues.append({
                "rule_code": "SCH3-LAYERING",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "description": "Schedule III declaration on Compliance with Number of Layers of Companies is missing.",
                "current_disclosure": "Company has subsidiaries but does not disclose compliance with number of layers prescribed under Section 2(87).",
                "suggested_correction": (
                    "Disclose confirmation whether the company has complied with the number of layers prescribed under clause (87) "
                    "of Section 2 of the Act read with Companies (Restriction on number of layers) Rules, 2017."
                ),
                "statutory_ref": f"{div_ref}, Clause 6(Y) / Section 2(87) of Companies Act, 2013",
                "action": "Add statutory declaration on compliance with layering of companies.",
                "status": "Action Required",
                "risk": "Medium",
                "highlight_cells": ["Layering of Companies Note"]
            })

        return issues

    # =========================================================================
    # 3. COMPREHENSIVE IND AS / AS ACCOUNTING STANDARDS CHECKS
    # =========================================================================
    @classmethod
    def _check_accounting_standards(
        cls,
        text: str,
        pages: List[Dict[str, Any]],
        is_ind_as: bool,
        is_listed: bool,
        mode: str,
        profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        issues = []

        if is_ind_as:
            # --- Ind AS 16: PPE Capitalisation & Useful Lives ---
            if re.search(r"standard\s+of\s+performance", text, re.IGNORECASE):
                p_num = cls._find_page_containing(pages, ["standard of performance"])
                issues.append({
                    "rule_code": "INDAS-16-PPE-POLICY",
                    "category": "Accounting Standards - PPE (Ind AS 16)",
                    "ref": f"Page {p_num} / Significant Accounting Policies - PPE" if p_num else "PPE Accounting Policy",
                    "description": "Non-compliant PPE capitalization policy: Reference to legacy 'standard of performance' criteria.",
                    "current_disclosure": (
                        "Accounting policy states subsequent expenditure added to PPE carrying value if it increases "
                        "standard of performance beyond previously assessed standard."
                    ),
                    "suggested_correction": (
                        "Replace policy with Ind AS 16.7 & 16.13 recognition criteria: Capitalize subsequent costs only when "
                        "probable that future economic benefits will flow to entity and cost can be reliably measured."
                    ),
                    "statutory_ref": "Ind AS 16, Paragraphs 7 and 13; ICAI FRRB Ind AS Study Observation 1",
                    "action": "Revise PPE accounting policy to conform strictly to Ind AS 16.",
                    "status": "Policy Revision Required" if mode == "Option A" else "FRRB Reporting Deficiency",
                    "risk": "Medium",
                    "highlight_cells": ["PPE Accounting Policy - Subsequent Expenditure"]
                })

            # Check Capital Advances classification
            has_cap_advances = bool(re.search(r"capital\s+advances\b", text, re.IGNORECASE))
            has_other_non_curr = bool(re.search(r"other\s+non[- ]current\s+assets\b", text, re.IGNORECASE))
            if has_cap_advances and not has_other_non_curr:
                issues.append({
                    "rule_code": "INDAS-16-CAP-ADV",
                    "category": "Accounting Standards - PPE (Ind AS 16 / Sched III)",
                    "ref": "Notes to Accounts - Capital Advances",
                    "description": "Capital Advances must be presented under 'Other Non-Current Assets', not within CWIP or Loans.",
                    "current_disclosure": "Capital advances appear under loans and advances or within CWIP note.",
                    "suggested_correction": "Reclassify capital advances to 'Other Non-Current Assets' per Schedule III Division II Part I.",
                    "statutory_ref": "Schedule III Division II Part I; Ind AS 16",
                    "action": "Ensure capital advances are properly segregated from CWIP and financial loans.",
                    "status": "Action Required",
                    "risk": "Medium",
                    "highlight_cells": ["Capital Advances Line Item"]
                })

            # --- Ind AS 116: Leases ---
            has_leases = bool(re.search(r"leases?\b", text, re.IGNORECASE))
            has_ind_as_116 = bool(re.search(r"right[- ]of[- ]use\s+assets?|rou\s+assets?|lease\s+liabilit(?:y|ies)", text, re.IGNORECASE))
            has_lease_maturity = bool(re.search(r"(?:maturity\s+analysis\s+of\s+lease|undiscounted\s+lease\s+payments|lease\s+commitments\s+maturity)", text, re.IGNORECASE))

            if has_leases and not has_ind_as_116:
                issues.append({
                    "rule_code": "INDAS-116-LEGACY-MODEL",
                    "category": "Accounting Standards - Leases (Ind AS 116)",
                    "ref": "Notes to Accounts - Leases",
                    "description": "Legacy Operating Lease classification observed under Ind AS framework.",
                    "current_disclosure": "Expenses classified as operating lease rentals without recognizing Right-of-Use (ROU) Asset or Lease Liability.",
                    "suggested_correction": (
                        "Apply Ind AS 116 single lessee accounting model: Recognize ROU Asset and corresponding Lease Liability on Balance Sheet, "
                        "unless meeting short-term or low-value exemptions."
                    ),
                    "statutory_ref": "Ind AS 116, Paragraphs 22, 26 and 47",
                    "action": "Recognize ROU assets and lease liabilities and disclose maturity analysis.",
                    "status": "Critical Standard Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Lease Disclosures & Balance Sheet Line Items"]
                })
            elif has_ind_as_116 and not has_lease_maturity:
                issues.append({
                    "rule_code": "INDAS-116-MATURITY-SCHEDULE",
                    "category": "Accounting Standards - Leases (Ind AS 116)",
                    "ref": "Notes to Accounts - Leases",
                    "description": "Omission of contractual undiscounted lease liabilities maturity analysis.",
                    "current_disclosure": "ROU asset and lease liability recognized, but undiscounted contractual lease cash flows maturity profile is omitted.",
                    "suggested_correction": (
                        "Present contractual undiscounted cash flows maturity analysis for lease liabilities across <1 yr, 1-5 yrs, and >5 yrs per Ind AS 116.58."
                    ),
                    "statutory_ref": "Ind AS 116, Paragraph 58 read with Ind AS 107, Paragraph 39",
                    "action": "Add contractual undiscounted lease maturity schedule.",
                    "status": "Action Required" if mode == "Option A" else "Disclosure Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Lease Liabilities Maturity Table"]
                })

            # --- Ind AS 115: Revenue from Contracts with Customers ---
            has_rev = bool(re.search(r"revenue\s+from\s+operations\b", text, re.IGNORECASE))
            has_rev_disagg = bool(re.search(r"disaggregat(?:ion|ed)\s+of\s+revenue", text, re.IGNORECASE) or (
                re.search(r"revenue\s+by\s+(?:geography|timing|product)", text, re.IGNORECASE)
            ))
            has_contract_balances = bool(re.search(r"contract\s+assets?|contract\s+liabilit(?:y|ies)|unearned\s+revenue", text, re.IGNORECASE))

            if has_rev and not has_rev_disagg:
                rev_page = cls._find_page_containing(pages, ["revenue from operations"])
                ref_str = f"Page {rev_page} / Note on Revenue" if rev_page else "Note on Revenue"
                issues.append({
                    "rule_code": "INDAS-115-DISAGGREGATION",
                    "category": "Accounting Standards - Revenue (Ind AS 115)",
                    "ref": ref_str,
                    "description": "Omission of Revenue Disaggregation disclosure under Ind AS 115.",
                    "current_disclosure": "Revenue presented in P&L without disaggregation showing nature, amount, timing and uncertainty.",
                    "suggested_correction": (
                        "Disaggregate revenue into categories depicting economic factors (e.g., product line, geography, "
                        "market type, point in time vs over time) per Ind AS 115.114-115."
                    ),
                    "statutory_ref": "Ind AS 115, Paragraphs 114 and 115",
                    "action": "Include revenue disaggregation schedule in Note on Revenue.",
                    "status": "Disclosure Missing" if mode == "Option A" else "Reporting Deficiency",
                    "risk": "High",
                    "highlight_cells": ["Revenue from Operations Note"]
                })

            if has_rev and not has_contract_balances:
                issues.append({
                    "rule_code": "INDAS-115-CONTRACT-BALANCES",
                    "category": "Accounting Standards - Revenue (Ind AS 115)",
                    "ref": "Notes to Accounts - Revenue",
                    "description": "Omission of Contract Balances (Contract Assets & Liabilities) reconciliation under Ind AS 115.",
                    "current_disclosure": "No separate disclosure or reconciliation of opening and closing contract assets and contract liabilities.",
                    "suggested_correction": (
                        "Disclose opening and closing balances of contract assets, contract liabilities, and revenue recognized "
                        "from opening contract liabilities under Ind AS 115.116."
                    ),
                    "statutory_ref": "Ind AS 115, Paragraph 116",
                    "action": "Provide contract asset and liability roll-forward in Revenue Note.",
                    "status": "Action Required" if mode == "Option A" else "Disclosure Omission",
                    "risk": "Medium",
                    "highlight_cells": ["Contract Balances Table"]
                })

            # --- Ind AS 19: Employee Benefits ---
            has_emp_benefits = bool(re.search(r"employee\s+benefits?|gratuity\b|defined\s+benefit", text, re.IGNORECASE))
            has_actuarial_sens = bool(re.search(r"sensitivity\s+analysis", text, re.IGNORECASE) and re.search(r"gratuity|defined\s+benefit", text, re.IGNORECASE))

            if has_emp_benefits and not has_actuarial_sens:
                issues.append({
                    "rule_code": "INDAS-19-SENSITIVITY",
                    "category": "Accounting Standards - Employee Benefits (Ind AS 19)",
                    "ref": "Notes to Accounts - Employee Benefits",
                    "description": "Omission of Sensitivity Analysis for Significant Actuarial Assumptions under Ind AS 19.",
                    "current_disclosure": "Defined benefit plan disclosed without sensitivity analysis showing impact of discount rate and salary escalation shifts.",
                    "suggested_correction": (
                        "Incorporate sensitivity analysis table showing impact on defined benefit obligation of a reasonable change "
                        "(e.g., ±1% or 100 bps) in discount rate and salary escalation rate per Ind AS 19.145."
                    ),
                    "statutory_ref": "Ind AS 19, Paragraph 145",
                    "action": "Include actuarial assumption sensitivity analysis in Employee Benefits Note.",
                    "status": "Mandatory Disclosure Missing" if mode == "Option A" else "Ind AS 19 Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Actuarial Sensitivity Analysis Note"]
                })

            # --- Ind AS 12: Income Taxes ---
            has_tax = bool(re.search(r"tax\s+expense|income\s+tax\b", text, re.IGNORECASE))
            has_tax_recon = bool(re.search(r"(?:reconciliation\s+of\s+effective\s+tax|tax\s+expense\s+reconciliation|applicable\s+tax\s+rate\s+and\s+effective\s+tax)", text, re.IGNORECASE))
            if has_tax and not has_tax_recon:
                issues.append({
                    "rule_code": "INDAS-12-TAX-RECON",
                    "category": "Accounting Standards - Income Taxes (Ind AS 12)",
                    "ref": "Notes to Accounts - Income Taxes",
                    "description": "Omission of Numerical Effective Tax Rate Reconciliation under Ind AS 12.",
                    "current_disclosure": "Tax expense presented in P&L without the numerical reconciliation between accounting profit multiplied by statutory tax rate and reported tax expense.",
                    "suggested_correction": (
                        "Provide numerical reconciliation between tax expense and accounting profit multiplied by applicable domestic tax rate "
                        "explaining major reconciling items per Ind AS 12.81(c)."
                    ),
                    "statutory_ref": "Ind AS 12, Paragraph 81(c)",
                    "action": "Include effective tax rate reconciliation table in Income Tax Note.",
                    "status": "Action Required" if mode == "Option A" else "Ind AS 12 Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Effective Tax Rate Reconciliation Table"]
                })

            # --- Ind AS 24: Related Party Disclosures ---
            has_rpt = bool(re.search(r"related\s+party\b", text, re.IGNORECASE))
            has_kmp_breakdown = bool(re.search(r"(?:short[- ]term\s+employee\s+benefits|post[- ]employment\s+benefits|termination\s+benefits)", text, re.IGNORECASE))
            if has_rpt and not has_kmp_breakdown:
                issues.append({
                    "rule_code": "INDAS-24-KMP-COMP",
                    "category": "Accounting Standards - Related Parties (Ind AS 24)",
                    "ref": "Notes to Accounts - Related Party Disclosures",
                    "description": "KMP Remuneration not classified into 5 statutory categories under Ind AS 24.17.",
                    "current_disclosure": "KMP remuneration disclosed in aggregate or single figure without breakdown.",
                    "suggested_correction": (
                        "Disclose KMP compensation broken down into: (a) Short-term employee benefits, (b) Post-employment benefits, "
                        "(c) Other long-term benefits, (d) Termination benefits, and (e) Share-based payments."
                    ),
                    "statutory_ref": "Ind AS 24, Paragraph 17",
                    "action": "Break down KMP compensation into the 5 statutory categories.",
                    "status": "Action Required" if mode == "Option A" else "Ind AS 24 Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["KMP Remuneration Breakdown Table"]
                })

            # --- Ind AS 107 & 109: Financial Instruments & Risk ---
            has_fin_instr = bool(re.search(r"financial\s+instruments\b|financial\s+risk", text, re.IGNORECASE))
            has_fv_hierarchy = bool(re.search(r"fair\s+value\s+hierarchy|level\s+1.*level\s+2", text, re.IGNORECASE))
            has_liquidity_risk = bool(re.search(r"liquidity\s+risk|contractual\s+maturit(?:y|ies)", text, re.IGNORECASE))

            if has_fin_instr and not has_fv_hierarchy:
                issues.append({
                    "rule_code": "INDAS-107-FV-HIERARCHY",
                    "category": "Accounting Standards - Financial Instruments (Ind AS 107)",
                    "ref": "Notes to Accounts - Financial Instruments",
                    "description": "Omission of Fair Value Hierarchy Disclosure (Level 1, 2, 3) under Ind AS 113 / Ind AS 107.",
                    "current_disclosure": "Financial instruments recognized without disclosing the fair value measurement level hierarchy.",
                    "suggested_correction": (
                        "Disclose the fair value hierarchy (Level 1 quoted, Level 2 observable inputs, Level 3 unobservable inputs) "
                        "for all financial assets and liabilities measured at fair value."
                    ),
                    "statutory_ref": "Ind AS 107, Paragraph 34 read with Ind AS 113, Paragraphs 91-93",
                    "action": "Add fair value hierarchy categorization table.",
                    "status": "Disclosure Missing" if mode == "Option A" else "Technical Deficiency",
                    "risk": "Medium",
                    "highlight_cells": ["Fair Value Hierarchy Table"]
                })

            if has_fin_instr and not has_liquidity_risk:
                issues.append({
                    "rule_code": "INDAS-107-LIQUIDITY-MATURITY",
                    "category": "Accounting Standards - Financial Instruments (Ind AS 107)",
                    "ref": "Notes to Accounts - Financial Risk Management",
                    "description": "Omission of Liquidity Risk Contractual Maturity Profile under Ind AS 107.39.",
                    "current_disclosure": "No maturity analysis provided for non-derivative and derivative financial liabilities showing remaining contractual undiscounted cash flows.",
                    "suggested_correction": (
                        "Include contractual undiscounted maturity table for all financial liabilities (borrowings, trade payables, other liabilities) "
                        "categorized into time bands (<1 yr, 1-2 yrs, 2-5 yrs, >5 yrs)."
                    ),
                    "statutory_ref": "Ind AS 107, Paragraph 39(a) and 39(b)",
                    "action": "Incorporate liquidity risk contractual maturity schedule.",
                    "status": "Action Required" if mode == "Option A" else "Ind AS 107 Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Liquidity Risk Maturity Table"]
                })

            # --- Ind AS 7: Financing Liabilities Roll-Forward (Net Debt) ---
            has_cfs = bool(re.search(r"statement\s+of\s+cash\s+flows|cash\s+flow\s+statement", text, re.IGNORECASE))
            has_debt_recon = bool(re.search(r"reconciliation\s+of\s+liabilities\s+arising\s+from\s+financing|net\s+debt\s+reconciliation", text, re.IGNORECASE))
            if has_cfs and not has_debt_recon:
                issues.append({
                    "rule_code": "INDAS-7-NET-DEBT-RECON",
                    "category": "Accounting Standards - Cash Flow (Ind AS 7)",
                    "ref": "Statement of Cash Flows / Accompanying Note",
                    "description": "Omission of mandatory reconciliation of liabilities arising from financing activities.",
                    "current_disclosure": "No reconciliation provided between opening and closing balances of borrowings and lease liabilities.",
                    "suggested_correction": (
                        "Incorporate Note disclosing changes in liabilities arising from financing activities, distinguishing "
                        "between cash flow changes and non-cash changes (such as forex movements, acquisitions, lease additions)."
                    ),
                    "statutory_ref": "Ind AS 7, Paragraphs 44A to 44E",
                    "action": "Add financing liabilities roll-forward table.",
                    "status": "Action Required" if mode == "Option A" else "Ind AS Disclosure Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Financing Liabilities Reconciliation Note"]
                })

            # --- Ind AS 108: Operating Segments (For Listed Entities) ---
            if is_listed:
                has_segments = bool(re.search(r"segment\s+reporting|operating\s+segments?\b", text, re.IGNORECASE))
                if not has_segments:
                    issues.append({
                        "rule_code": "INDAS-108-SEGMENTS",
                        "category": "Accounting Standards - Segment Reporting (Ind AS 108)",
                        "ref": "Notes to Accounts - Operating Segments",
                        "description": "Complete Omission of Operating Segment Disclosures under Ind AS 108 for Listed Company.",
                        "current_disclosure": "Listed company filing financial statements without disclosing operating segments identified by CODM.",
                        "suggested_correction": (
                            "Disclose segment revenue, segment results, segment assets, segment liabilities, and entity-wide disclosures "
                            "per Ind AS 108, or explain single-segment nature with product/geographic breakdown."
                        ),
                        "statutory_ref": "Ind AS 108, Paragraphs 20-24",
                        "action": "Draft and incorporate Ind AS 108 segment disclosures.",
                        "status": "Mandatory Standard Omission",
                        "risk": "High",
                        "highlight_cells": ["Segment Disclosures Note"]
                    })

            # --- Ind AS 8: Prior Period Errors & Retrospective Restatement ---
            if re.search(r"prior\s+period\s+(?:items?|expenses?|adjustments?|incomes?)\b", text, re.IGNORECASE):
                p_prior = cls._find_page_containing(pages, ["prior period"])
                ref_str = f"Page {p_prior} / Statement of Profit and Loss" if p_prior else "Statement of Profit and Loss"
                issues.append({
                    "rule_code": "INDAS-8-PRIOR-PERIOD",
                    "category": "Accounting Standards - Prior Period Errors (Ind AS 8)",
                    "ref": ref_str,
                    "description": "Recognition of Prior Period Items in Current Year Statement of Profit and Loss.",
                    "current_disclosure": "Financial statements reflect prior period items/expenses charged directly to current year P&L.",
                    "suggested_correction": (
                        "Under Ind AS 8.42, prior period errors shall be corrected retrospectively by restating comparative amounts "
                        "for the prior period(s) presented in the opening balance sheet. They cannot be recognized in current period P&L."
                    ),
                    "statutory_ref": "Ind AS 8, Paragraph 42; ICAI FRRB Ind AS Study Chapter 4 Observation 37",
                    "action": "Restate prior period comparatives retrospectively; remove prior period line item from current P&L.",
                    "status": "Critical Standard Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Prior Period Items Line Item"]
                })

            # --- Inventories Valuation Policy (Ind AS 2) ---
            has_inv = bool(re.search(r"inventories\b", text, re.IGNORECASE))
            has_inv_formula = bool(re.search(r"(?:first[- ]in[- ]first[- ]out|fifo|weighted\s+average|cost\s+formula)", text, re.IGNORECASE))
            if has_inv and not has_inv_formula:
                issues.append({
                    "rule_code": "INDAS-2-INVENTORY-FORMULA",
                    "category": "Accounting Standards - Inventories (Ind AS 2)",
                    "ref": "Significant Accounting Policies - Inventories",
                    "description": "Cost formula used for inventory valuation is not disclosed.",
                    "current_disclosure": "Accounting policy does not specify whether cost is determined on FIFO or Weighted Average cost formula.",
                    "suggested_correction": (
                        "Disclose the cost formulas used (e.g. Weighted Average or FIFO) and confirm inventories are measured "
                        "at lower of cost and net realizable value per Ind AS 2.36(a)."
                    ),
                    "statutory_ref": "Ind AS 2, Paragraph 36(a); ICAI FRRB Study Chapter 1 Observation 32",
                    "action": "Disclose specific cost formula in Inventories accounting policy.",
                    "status": "Policy Defect",
                    "risk": "Low",
                    "highlight_cells": ["Inventories Accounting Policy - Cost Formula"]
                })

        else:
            # =================================================================
            # ACCOUNTING STANDARDS (AS) FRAMEWORK DEEP COMPLIANCE AUDIT
            # =================================================================
            # --- AS 1: Disclosure of Accounting Policies ---
            has_policies = bool(re.search(r"significant\s+accounting\s+policies|accounting\s+policies\b", text, re.IGNORECASE))
            if not has_policies:
                issues.append({
                    "rule_code": "AS-1-POLICIES-OMISSION",
                    "category": "Accounting Standards - General (AS 1)",
                    "ref": "Notes to Accounts - Note 1",
                    "description": "Omission of Significant Accounting Policies summary as required under AS 1.",
                    "current_disclosure": "No consolidated statement of significant accounting policies found in financial statements.",
                    "suggested_correction": (
                        "Disclose all significant accounting policies in one place forming part of financial statements per AS 1.24, "
                        "covering fundamental accounting assumptions (Going Concern, Consistency, Accrual)."
                    ),
                    "statutory_ref": "AS 1, Paragraph 24",
                    "action": "Incorporate Note 1 summarizing all significant accounting policies.",
                    "status": "Mandatory Standard Omission",
                    "risk": "High",
                    "highlight_cells": ["Significant Accounting Policies Note"]
                })

            # --- AS 2: Valuation of Inventories ---
            has_inv = bool(re.search(r"inventories\b", text, re.IGNORECASE))
            has_inv_formula = bool(re.search(r"(?:first[- ]in[- ]first[- ]out|fifo|weighted\s+average|cost\s+formula)", text, re.IGNORECASE))
            if has_inv and not has_inv_formula:
                issues.append({
                    "rule_code": "AS-2-INVENTORY-FORMULA",
                    "category": "Accounting Standards - Inventories (AS 2)",
                    "ref": "Significant Accounting Policies - Inventories",
                    "description": "Cost formula used for inventory valuation is not disclosed under AS 2.",
                    "current_disclosure": "Accounting policy does not specify whether cost is determined on FIFO or Weighted Average cost formula.",
                    "suggested_correction": (
                        "Disclose the specific cost formulas used (FIFO or Weighted Average) and confirm inventories are measured "
                        "at lower of cost and net realizable value per AS 2 Paragraph 26."
                    ),
                    "statutory_ref": "AS 2, Paragraph 26; Schedule III Division I",
                    "action": "Disclose specific cost formula in Inventories accounting policy.",
                    "status": "Policy Defect",
                    "risk": "Low",
                    "highlight_cells": ["Inventories Accounting Policy - Cost Formula"]
                })

            # --- AS 10 (Revised): Property, Plant and Equipment ---
            has_ppe = bool(re.search(r"property,\s+plant\s+and\s+equipment|fixed\s+assets\b", text, re.IGNORECASE))
            has_comp_dep = bool(re.search(r"component\s+accounting|component\s+depreciation|major\s+inspection", text, re.IGNORECASE))
            if has_ppe and not has_comp_dep:
                issues.append({
                    "rule_code": "AS-10-PPE-COMPONENT",
                    "category": "Accounting Standards - Fixed Assets (AS 10)",
                    "ref": "Significant Accounting Policies - Fixed Assets",
                    "description": "Omission of Component Accounting policy under AS 10 (Revised) / Schedule II.",
                    "current_disclosure": "Depreciation accounting policy omits reference to component-level depreciation for significant asset parts.",
                    "suggested_correction": (
                        "Incorporate component depreciation accounting policy: each part of an item of PPE with a cost significant "
                        "in relation to total cost shall be depreciated separately per AS 10 (Revised) Paragraph 46 and Schedule II."
                    ),
                    "statutory_ref": "AS 10 (Revised), Paragraph 46; Schedule II to Companies Act, 2013",
                    "action": "Update PPE policy with component accounting provisions.",
                    "status": "Policy Revision Required",
                    "risk": "Medium",
                    "highlight_cells": ["PPE Accounting Policy - Component Depreciation"]
                })

            # --- AS 15: Employee Benefits Disclosures ---
            has_gratuity = bool(re.search(r"gratuity\b|employee\s+benefits?\b", text, re.IGNORECASE))
            has_actuarial_rates = bool(re.search(r"discount\s+rate|salary\s+escalation\s+rate|rate\s+of\s+increase\s+in\s+compensation", text, re.IGNORECASE))
            if has_gratuity and not has_actuarial_rates:
                issues.append({
                    "rule_code": "AS-15-ACTUARIAL-ASSUMPTIONS",
                    "category": "Accounting Standards - Employee Benefits (AS 15)",
                    "ref": "Notes to Accounts - Employee Benefits",
                    "description": "Principal Actuarial Assumptions (Discount Rate, Salary Escalation) not disclosed under AS 15.",
                    "current_disclosure": "Gratuity/leave obligations disclosed without disclosing principal actuarial assumptions used in valuation.",
                    "suggested_correction": (
                        "Disclose the principal actuarial assumptions adopted: (a) Discount rate, (b) Expected rate of return on plan assets, "
                        "(c) Expected rate of salary increase, and (d) Mortality rates per AS 15 Paragraph 120(l)."
                    ),
                    "statutory_ref": "AS 15, Paragraph 120(l)",
                    "action": "Include table of principal actuarial assumptions in Employee Benefits note.",
                    "status": "Mandatory Disclosure Missing",
                    "risk": "High",
                    "highlight_cells": ["Principal Actuarial Assumptions Table"]
                })

            # --- AS 18: Related Party Disclosures ---
            has_rpt = bool(re.search(r"related\s+party\b|related\s+parties\b", text, re.IGNORECASE))
            has_rpt_names = bool(re.search(r"name\s+of\s+related\s+party|enterprises\s+over\s+which|key\s+management\s+personnel", text, re.IGNORECASE))
            if has_rpt and not has_rpt_names:
                issues.append({
                    "rule_code": "AS-18-RPT-NAMES",
                    "category": "Accounting Standards - Related Parties (AS 18)",
                    "ref": "Notes to Accounts - Related Party Disclosures",
                    "description": "Omission of Name of Related Parties and Nature of Relationships under AS 18.",
                    "current_disclosure": "Transactions with related parties disclosed without clear classification into holding, subsidiaries, fellow subsidiaries, and KMP.",
                    "suggested_correction": (
                        "Disclose: (a) Name of related party and nature of related party relationship where control exists, "
                        "(b) Volume of transactions, and (c) Outstanding balances at year-end per AS 18 Paragraphs 21-23."
                    ),
                    "statutory_ref": "AS 18, Paragraphs 21 to 23",
                    "action": "Disclose complete relationship roster and transaction matrix in RPT note.",
                    "status": "Action Required",
                    "risk": "High",
                    "highlight_cells": ["Related Party List and Transactions"]
                })

            # --- AS 22: Taxes on Income - Virtual Certainty for DTA on Losses ---
            has_dta_losses = bool(re.search(r"deferred\s+tax\s+assets?.*(?:tax\s+losses|unabsorbed\s+depreciation)", text, re.IGNORECASE))
            has_virtual_cert = bool(re.search(r"virtual\s+certainty\s+supported\s+by\s+convincing\s+evidence", text, re.IGNORECASE))
            if has_dta_losses and not has_virtual_cert:
                issues.append({
                    "rule_code": "AS-22-VIRTUAL-CERTAINTY",
                    "category": "Accounting Standards - Taxes on Income (AS 22)",
                    "ref": "Notes to Accounts - Deferred Tax",
                    "description": "Deferred Tax Asset recognized on unabsorbed depreciation/tax losses without Virtual Certainty disclosure.",
                    "current_disclosure": "DTA recognized on tax losses without explicit disclosure of virtual certainty supported by convincing evidence.",
                    "suggested_correction": (
                        "Under AS 22 Paragraph 17, DTA can be recognized on unabsorbed depreciation or carry-forward of losses ONLY "
                        "to the extent that there is virtual certainty supported by convincing evidence that sufficient future taxable income will be available."
                    ),
                    "statutory_ref": "AS 22, Paragraph 17; ICAI FRRB Study Chapter 2 Observation 18",
                    "action": "Provide convincing evidence substantiating virtual certainty or reverse DTA on tax losses.",
                    "status": "Critical Standard Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Deferred Tax Asset on Tax Losses"]
                })

            # --- AS 29: Provisions Movement Table & Contingent Liabilities ---
            has_prov = bool(re.search(r"provisions\b", text, re.IGNORECASE))
            has_prov_movement = bool(re.search(r"(?:carrying\s+amount\s+at\s+beginning|additional\s+provisions\s+made|amounts\s+used|unused\s+amounts\s+reversed)", text, re.IGNORECASE))
            if has_prov and not has_prov_movement:
                issues.append({
                    "rule_code": "AS-29-PROVISIONS-MOVEMENT",
                    "category": "Accounting Standards - Provisions (AS 29)",
                    "ref": "Notes to Accounts - Provisions",
                    "description": "Omission of Movement Schedule for each class of Provision under AS 29.",
                    "current_disclosure": "Provisions presented as single balance without disclosure of opening balance, additions, utilization, and reversals.",
                    "suggested_correction": (
                        "Disclose for each class of provision: (a) Carrying amount at beginning and end of period, (b) Additional provisions made, "
                        "(c) Amounts used, and (d) Unused amounts reversed during the period per AS 29 Paragraph 66."
                    ),
                    "statutory_ref": "AS 29, Paragraph 66",
                    "action": "Incorporate provisions roll-forward movement table.",
                    "status": "Disclosure Missing",
                    "risk": "Medium",
                    "highlight_cells": ["Provisions Movement Table"]
                })

            # --- AS 20: Earnings Per Share ---
            has_pat = bool(re.search(r"profit\s+(?:after\s+tax|for\s+the\s+year)\b", text, re.IGNORECASE))
            has_eps = bool(re.search(r"earnings\s+per\s+share|basic\s+eps|diluted\s+eps", text, re.IGNORECASE))
            if has_pat and not has_eps:
                issues.append({
                    "rule_code": "AS-20-EPS-OMISSION",
                    "category": "Accounting Standards - Earnings Per Share (AS 20)",
                    "ref": "Statement of Profit and Loss",
                    "description": "Omission of Basic and Diluted Earnings Per Share on face of Statement of Profit and Loss.",
                    "current_disclosure": "Statement of Profit and Loss omits mandatory disclosure of Basic and Diluted EPS.",
                    "suggested_correction": (
                        "Present Basic and Diluted earnings per share on the face of the Statement of Profit and Loss for each class of equity "
                        "shares per AS 20 Paragraph 48."
                    ),
                    "statutory_ref": "AS 20, Paragraph 48; Schedule III Division I Part II",
                    "action": "Disclose Basic and Diluted EPS on face of P&L.",
                    "status": "Mandatory Standard Omission",
                    "risk": "High",
                    "highlight_cells": ["Earnings Per Share Line Item"]
                })

            # --- AS 9: Revenue Recognition Policy ---
            has_sales = bool(re.search(r"revenue\s+from\s+operations|sale\s+of\s+products|sale\s+of\s+goods|rendering\s+of\s+services", text, re.IGNORECASE))
            has_rev_policy = bool(re.search(r"significant\s+risks\s+and\s+rewards|performance\s+of\s+services|completed\s+service|proportionate\s+completion", text, re.IGNORECASE))
            if has_sales and not has_rev_policy:
                issues.append({
                    "rule_code": "AS-9-REVENUE-POLICY",
                    "category": "Accounting Standards - Revenue (AS 9)",
                    "ref": "Significant Accounting Policies - Revenue Recognition",
                    "description": "Inadequate Revenue Recognition accounting policy under AS 9.",
                    "current_disclosure": "Accounting policy does not state transfer of significant risks and rewards of ownership for sale of goods or method of service completion.",
                    "suggested_correction": (
                        "Explicitly specify policy: (i) Revenue from sale of goods is recognized when significant risks and rewards of ownership "
                        "are transferred to buyer, and (ii) Revenue from services is recognized on proportionate completion or completed service method per AS 9 Paragraph 11-13."
                    ),
                    "statutory_ref": "AS 9, Paragraphs 11 to 13",
                    "action": "Update Revenue Recognition policy to conform to AS 9 criteria.",
                    "status": "Policy Defect",
                    "risk": "Medium",
                    "highlight_cells": ["Revenue Recognition Policy"]
                })

            # --- AS 3: Cash Flow Statement ---
            has_cfs = bool(re.search(r"cash\s+flow\s+statement|statement\s+of\s+cash\s+flows?", text, re.IGNORECASE))
            is_small_pvt = bool(profile and profile.get("company_type") == "Private Company" and "small" in str(profile.get("company_type", "")).lower())
            if not has_cfs and not is_small_pvt:
                issues.append({
                    "rule_code": "AS-3-CFS-OMISSION",
                    "category": "Accounting Standards - Cash Flow (AS 3)",
                    "ref": "Financial Statements - Cash Flow Statement",
                    "description": "Cash Flow Statement is omitted from the financial statements.",
                    "current_disclosure": "No Cash Flow Statement included in the uploaded financial statements.",
                    "suggested_correction": (
                        "Prepare and present Cash Flow Statement reporting cash flows during the period classified by operating, "
                        "investing and financing activities per AS 3 and Section 2(40) of Companies Act, 2013."
                    ),
                    "statutory_ref": "AS 3; Section 2(40) of Companies Act, 2013",
                    "action": "Prepare and attach Cash Flow Statement.",
                    "status": "Mandatory Statement Missing",
                    "risk": "High",
                    "highlight_cells": ["Cash Flow Statement"]
                })

        return issues

    # =========================================================================
    # 4. COMPANIES ACT, 2013 COMPLIANCE CHECKS
    # =========================================================================
    @classmethod
    def _check_companies_act(cls, text: str, pages: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        issues = []

        # Section 135 CSR Disclosures
        has_csr = bool(re.search(r"corporate\s+social\s+responsibility|csr\s+expenditure", text, re.IGNORECASE))
        has_csr_details = bool(re.search(r"(?:amount\s+required\s+to\s+be\s+spent|amount\s+unspent|unspent\s+csr\s+account)", text, re.IGNORECASE))

        if has_csr and not has_csr_details:
            csr_page = cls._find_page_containing(pages, ["csr", "corporate social responsibility"])
            ref_str = f"Page {csr_page} / CSR Note" if csr_page else "Note on CSR Expenditure"
            issues.append({
                "rule_code": "COACT-135-CSR-DETAILS",
                "category": "Companies Act, 2013 - Section 135 (CSR)",
                "ref": ref_str,
                "description": "Incomplete CSR Disclosures under amended Section 135.",
                "current_disclosure": "CSR expenses disclosed without statutory breakdown of amount spent, unspent, and ongoing project status.",
                "suggested_correction": (
                    "Disclose: (a) Amount required to be spent vs actually spent, (b) Shortfall amount, (c) Total previous years shortfall, "
                    "(d) Transfer to specified fund under Schedule VII within 6 months or Unspent CSR Account within 30 days."
                ),
                "statutory_ref": "Section 135(5) & 135(6) of Companies Act, 2013 read with CSR Policy Rules, 2014",
                "action": "Update CSR disclosure table with mandatory statutory columns.",
                "status": "Action Required" if mode == "Option A" else "Statutory Non-Compliance",
                "risk": "High",
                "highlight_cells": ["CSR Disclosure Table"]
            })

        # Section 186 Loans & Guarantees Disclosures
        has_sec186 = bool(re.search(r"section\s+186\b|loans\s+and\s+investments\s+under\s+section\s+186", text, re.IGNORECASE))
        has_loans_given = bool(re.search(r"loans\s+(?:given|to\s+subsidiaries|to\s+related\s+parties)|corporate\s+guarantees?\s+given", text, re.IGNORECASE))
        if has_loans_given and not has_sec186:
            issues.append({
                "rule_code": "COACT-186-LOANS-PURPOSE",
                "category": "Companies Act, 2013 - Section 186 (Loans & Guarantees)",
                "ref": "Notes to Accounts - Loans / Guarantees",
                "description": "Section 186(4) statutory purpose disclosure is missing for loans and guarantees given.",
                "current_disclosure": "Loans or corporate guarantees provided to entities, but disclosure of purpose for which loan/guarantee is proposed to be utilized by recipient is omitted.",
                "suggested_correction": (
                    "Disclose full particulars of loans given, investments made, guarantee given or security provided and the purpose "
                    "for which the loan/guarantee is proposed to be utilized by the recipient per Section 186(4)."
                ),
                "statutory_ref": "Section 186(4) of Companies Act, 2013",
                "action": "Add Section 186(4) purpose disclosures in Note on Loans / Guarantees.",
                "status": "Statutory Omission",
                "risk": "High",
                "highlight_cells": ["Section 186 Purpose Disclosures"]
            })

        return issues

    # =========================================================================
    # 5. AUDITOR'S REPORT & CARO 2020 REVIEW
    # =========================================================================
    @classmethod
    def _check_auditor_and_caro(
        cls,
        text: str,
        pages: List[Dict[str, Any]],
        sections: Dict[str, Any],
        is_listed: bool,
        mode: str
    ) -> List[Dict[str, Any]]:
        issues = []

        audit_sec = sections.get("auditor_report", {})
        if audit_sec.get("detected"):
            report_text = audit_sec.get("extract", "")
            start_p = audit_sec.get("start_page", 1)

            # Modified Opinion check (Qualified / Adverse / Disclaimer)
            if re.search(r"qualified\s+opinion\b", report_text, re.IGNORECASE):
                issues.append({
                    "rule_code": "AUDIT-QUALIFIED-OPINION",
                    "category": "Auditor's Report Review",
                    "ref": f"Page {start_p} / Independent Auditor's Report",
                    "description": "Modified Audit Opinion: Auditor has issued a 'Qualified Opinion'.",
                    "current_disclosure": "Auditor's Report contains 'Basis for Qualified Opinion' paragraph.",
                    "suggested_correction": (
                        "Analyze management's response in Board's Report (Section 134(3)(f)) addressing auditor qualifications "
                        "and evaluate whether financial statements require adjustments."
                    ),
                    "statutory_ref": "SA 705 (Modifications to the Opinion); Section 143(2) and Section 134(3)(f) of Companies Act, 2013",
                    "action": "Audit Review: Prioritize investigation of basis for qualification.",
                    "status": "Auditor Qualification" if mode == "Option B" else "Critical Audit Warning",
                    "risk": "High",
                    "highlight_cells": ["Basis for Qualified Opinion"]
                })

            if re.search(r"adverse\s+opinion\b", report_text, re.IGNORECASE):
                issues.append({
                    "rule_code": "AUDIT-ADVERSE-OPINION",
                    "category": "Auditor's Report Review",
                    "ref": f"Page {start_p} / Independent Auditor's Report",
                    "description": "Adverse Audit Opinion: Auditor states financial statements do not give a true and fair view.",
                    "current_disclosure": "Auditor's Report contains 'Basis for Adverse Opinion' paragraph.",
                    "suggested_correction": "Immediate management review required. Identify pervasive financial statement misstatements.",
                    "statutory_ref": "SA 705 (Modifications to the Opinion); Section 143(2) of Companies Act, 2013",
                    "action": "Investigate root cause of pervasive audit misstatement.",
                    "status": "Adverse Opinion",
                    "risk": "High",
                    "highlight_cells": ["Basis for Adverse Opinion"]
                })

            # Key Audit Matters (KAM) check for Listed entities
            if is_listed:
                has_kam = bool(re.search(r"key\s+audit\s+matters|kam\b", report_text, re.IGNORECASE))
                if not has_kam:
                    issues.append({
                        "rule_code": "AUDIT-KAM-OMISSION",
                        "category": "Auditor's Report Review",
                        "ref": f"Page {start_p} / Independent Auditor's Report",
                        "description": "Omission of Key Audit Matters (KAM) section in Listed Company Auditor's Report.",
                        "current_disclosure": "Auditor's report for a listed entity does not communicate Key Audit Matters under SA 701.",
                        "suggested_correction": (
                            "Ensure statutory auditor includes compliant Key Audit Matters section describing matters of most significance "
                            "and how they were addressed in the audit."
                        ),
                        "statutory_ref": "SA 701 (Communicating Key Audit Matters in the Independent Auditor's Report); Section 143(2)",
                        "action": "Request auditor to include SA 701 Key Audit Matters.",
                        "status": "Auditor Reporting Defect",
                        "risk": "High",
                        "highlight_cells": ["Key Audit Matters Section"]
                    })

            # Emphasis of Matter check
            if re.search(r"emphasis\s+of\s+matter\b", report_text, re.IGNORECASE):
                issues.append({
                    "rule_code": "AUDIT-EMPHASIS-OF-MATTER",
                    "category": "Auditor's Report Review",
                    "ref": f"Page {start_p} / Independent Auditor's Report",
                    "description": "Auditor has drawn attention to an 'Emphasis of Matter' paragraph.",
                    "current_disclosure": "Emphasis of Matter paragraph drawing attention to note in financial statements.",
                    "suggested_correction": "Cross-verify whether the corresponding note in financial statements provides transparent and comprehensive disclosure.",
                    "statutory_ref": "SA 706 (Emphasis of Matter Paragraphs); Guidance Note on CARO 2020",
                    "action": "Cross-reference note disclosure with auditor's emphasis.",
                    "status": "Review Attention" if mode == "Option B" else "Disclosure Verification Required",
                    "risk": "Medium",
                    "highlight_cells": ["Emphasis of Matter Note Reference"]
                })

        # CARO 2020 Clause Review
        caro_sec = sections.get("caro_report", {})
        if caro_sec.get("detected") or re.search(r"caro", text, re.IGNORECASE):
            # Clause 3(ii)(b): Quarterly bank returns vs books
            has_quarterly_text = bool(re.search(r"quarterly\s+(?:statements?|returns?)", text, re.IGNORECASE))
            has_discrepancy_text = bool(re.search(r"(?:discrepanc(?:y|ies)|differences?|not\s+in\s+agreement|varianc(?:e|es))", text, re.IGNORECASE))
            if has_quarterly_text and has_discrepancy_text:
                issues.append({
                    "rule_code": "CARO-QTR-RECON",
                    "category": "CARO 2020 - Working Capital Reconciliations",
                    "ref": "CARO Annexure / Clause 3(ii)(b)",
                    "description": "Auditor has reported discrepancies between quarterly statements submitted to banks and books of accounts.",
                    "current_disclosure": "Remarks under CARO Clause 3(ii)(b) indicating material differences between quarterly returns and financial books.",
                    "suggested_correction": (
                        "Disclose full reconciliation table between quarterly returns submitted to banks and books of accounts "
                        "in Notes to Accounts as mandated by Schedule III Clause 6(L)."
                    ),
                    "statutory_ref": "Clause 3(ii)(b) of CARO, 2020 read with Schedule III Part I Clause 6(L)",
                    "action": "Ensure Schedule III note matches CARO Clause 3(ii)(b) observations.",
                    "status": "Material Red Flag" if mode == "Option B" else "Mandatory Schedule III Reconciliation Missing",
                    "risk": "High",
                    "highlight_cells": ["Quarterly Bank Statements Reconciliation Note"]
                })

            # Clause 3(vii)(a): Undisputed statutory dues > 6 months
            has_statutory_arrears = bool(re.search(r"(?:undisputed\s+statutory\s+dues.*outstanding\s+for\s+a\s+period\s+of\s+more\s+than\s+six\s+months|arrears\s+of\s+statutory\s+dues)", text, re.IGNORECASE))
            if has_statutory_arrears:
                issues.append({
                    "rule_code": "CARO-STATUTORY-ARREARS",
                    "category": "CARO 2020 - Statutory Dues",
                    "ref": "CARO Annexure / Clause 3(vii)(a)",
                    "description": "Undisputed statutory dues outstanding for more than six months reported by auditor.",
                    "current_disclosure": "Remarks under CARO Clause 3(vii)(a) noting statutory dues (PF, ESI, GST, Tax) unpaid for > 6 months.",
                    "suggested_correction": "Verify whether appropriate provisions and disclosures of overdue statutory dues are made in current liabilities.",
                    "statutory_ref": "Clause 3(vii)(a) of CARO, 2020; Section 143(11) of Companies Act, 2013",
                    "action": "Verify tax liabilities schedule and deposit arrears immediately.",
                    "status": "Statutory Non-Compliance",
                    "risk": "High",
                    "highlight_cells": ["Statutory Dues Overdue Schedule"]
                })

            # Clause 3(xvii): Cash Losses
            has_cash_losses = bool(re.search(r"incurred\s+cash\s+losses\b", text, re.IGNORECASE))
            if has_cash_losses:
                issues.append({
                    "rule_code": "CARO-CASH-LOSSES",
                    "category": "CARO 2020 - Financial Health",
                    "ref": "CARO Annexure / Clause 3(xvii)",
                    "description": "Auditor has reported Cash Losses in current and/or immediately preceding financial year.",
                    "current_disclosure": "Remarks under CARO Clause 3(xvii) indicating company has incurred cash losses.",
                    "suggested_correction": "Evaluate Going Concern assumptions under Ind AS 1.25 and SA 570 in light of reported cash losses.",
                    "statutory_ref": "Clause 3(xvii) of CARO, 2020; Ind AS 1 Paragraph 25",
                    "action": "Assess management's going concern assessment and cash flow forecasts.",
                    "status": "Financial Red Flag",
                    "risk": "High",
                    "highlight_cells": ["Cash Loss Disclosures & Going Concern Assessment"]
                })

            # Clause 3(ix): Defaults in Repayment of Borrowings
            has_borrowing_default = bool(re.search(r"defaulted\s+in\s+repayment\s+of\s+loans|default\s+in\s+repayment\s+of\s+borrowings|delay\s+in\s+repayment\s+of\s+term\s+loans", text, re.IGNORECASE))
            if has_borrowing_default:
                issues.append({
                    "rule_code": "CARO-LOAN-DEFAULTS",
                    "category": "CARO 2020 - Borrowings & Repayment Defaults",
                    "ref": "CARO Annexure / Clause 3(ix)(a)",
                    "description": "Auditor has reported default in repayment of loans or borrowings to lenders.",
                    "current_disclosure": "Remarks under CARO Clause 3(ix)(a) detailing defaults in repayment of principal or interest.",
                    "suggested_correction": (
                        "Cross-verify whether disclosure of lender-wise period and amount of default is provided in Borrowings Note "
                        "and evaluate classification of borrowing as current liability under Ind AS 1.74."
                    ),
                    "statutory_ref": "Clause 3(ix)(a) of CARO, 2020; Ind AS 1 Paragraph 74",
                    "action": "Ensure loan defaults are fully disclosed and classified as Current Liabilities.",
                    "status": "Critical Red Flag",
                    "risk": "High",
                    "highlight_cells": ["Borrowings Default Note Reference"]
                })

            # Clause 3(xix): Material Uncertainty on Capability of Meeting Liabilities (Going Concern)
            has_going_concern_caro = bool(re.search(r"material\s+uncertainty\s+exists.*meeting\s+its\s+liabilities|capability\s+of\s+the\s+company\s+of\s+meeting\s+its\s+liabilities", text, re.IGNORECASE))
            if has_going_concern_caro:
                issues.append({
                    "rule_code": "CARO-GOING-CONCERN",
                    "category": "CARO 2020 - Going Concern & Solvency",
                    "ref": "CARO Annexure / Clause 3(xix)",
                    "description": "Auditor has reported material uncertainty regarding capability to meet liabilities within 1 year.",
                    "current_disclosure": "Remarks under CARO Clause 3(xix) indicating doubt on company's capability to service liabilities falling due within one year.",
                    "suggested_correction": (
                        "Examine note on Going Concern and management's liquidity plan under Ind AS 1.25, Ind AS 107.39 and SA 570 (Revised)."
                    ),
                    "statutory_ref": "Clause 3(xix) of CARO, 2020; Ind AS 1 Paragraph 25; SA 570 (Revised)",
                    "action": "Conduct immediate solvency review and examine working capital management plans.",
                    "status": "High-Risk Red Flag",
                    "risk": "High",
                    "highlight_cells": ["Going Concern Note"]
                })

        return issues

    @classmethod
    def _find_page_containing(cls, pages: List[Dict[str, Any]], keywords: List[str]) -> Optional[int]:
        """Finds the first page number containing any of the keywords."""
        for p in pages:
            t = p["text"].lower()
            for kw in keywords:
                if kw in t:
                    return p["page_num"]
        return None
