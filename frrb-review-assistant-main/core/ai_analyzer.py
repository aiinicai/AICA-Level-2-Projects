"""AI-Augmented Disclosure Analysis Module.

Performs deep natural language analysis of financial statement extracts,
auditor commentary, and nuanced disclosure omissions.
Supports live Google Gemini API analysis and an exhaustive Offline CA Expert Analytical Engine
that scans all notes and primary statements across large multi-page corporate reports.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional
import requests
from core.knowledge_base import KnowledgeBase


class AIAnalyzer:
    """Performs AI and deep-heuristics disclosure evaluations across financial filings."""

    SYSTEM_PROMPT = """
You are a senior Technical Reviewer for the Financial Reporting Review Board (FRRB) of the Institute of Chartered Accountants of India (ICAI).
Your objective is to critically examine corporate financial statements, notes to accounts, and statutory auditor's reports.

GUIDELINES:
1. Identify reporting non-compliances, ambiguous disclosures, missing mandatory data, and red flags.
2. Maintain strict technical accuracy: Cite exact paragraphs of Ind AS / AS, Schedule III, Companies Act 2013, or CARO 2020.
3. NEVER invent or fabricate standard paragraphs or statutory numbers. If a citation cannot be verified with certainty, state "Reference Verification Required".
4. Distinguish between confirmed arithmetic discrepancies, disclosure deficiencies, and matters requiring professional judgement.
5. Provide precise, actionable suggested corrections suitable for a Chartered Accountant.

Return your response in valid JSON format with a top-level list of findings:
[
  {
    "category": "Assets / Liabilities / Equity / P&L / Cash Flow / Disclosures / Auditor Report",
    "ref": "Document note or page reference",
    "extract": "Supporting quote from text",
    "description": "Clear description of deficiency or red flag",
    "technical_ref": "Exact Standard paragraph or statutory provision",
    "suggested_correction": "Precise wording or action required",
    "risk": "High / Medium / Low",
    "nature": "Confirmed Discrepancy / Disclosure Deficiency / Professional Judgement Required"
  }
]
"""

    @classmethod
    def analyze_full_document(
        cls,
        doc: Dict[str, Any],
        profile: Dict[str, Any],
        review_mode: str,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyzes all sections and pages of the document using Gemini API or deep CA heuristics."""
        effective_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        pages = doc.get("pages", [])
        full_text = doc.get("full_text", "")

        # Always run deep offline CA expert analysis across all pages
        deep_offline_findings = cls._deep_document_heuristics(pages, full_text, profile, review_mode)

        if effective_key and effective_key.strip():
            try:
                # Extract key representative text extracts across all pages (up to 30k chars)
                representative_extracts = cls._build_representative_extracts(pages, full_text)
                gemini_findings = cls._call_gemini_api(representative_extracts, profile, review_mode, effective_key.strip())
                
                # Combine Gemini findings with deep heuristics
                all_findings = list(deep_offline_findings)
                seen_descs = {f.get("description", "")[:40] for f in all_findings}
                for gf in gemini_findings:
                    if gf.get("description", "")[:40] not in seen_descs:
                        all_findings.append(gf)
                        seen_descs.add(gf.get("description", "")[:40])

                return {
                    "source": "Google Gemini 1.5 + ICAI FRRB Deep Engine",
                    "findings": all_findings,
                    "is_live_ai": True,
                    "error": None
                }
            except Exception as e:
                return {
                    "source": f"Offline CA Expert Engine (Gemini fallback: {str(e)[:60]})",
                    "findings": deep_offline_findings,
                    "is_live_ai": False,
                    "error": str(e)
                }
        else:
            return {
                "source": "Offline CA Expert Analytical Engine (Zero API Key Mode)",
                "findings": deep_offline_findings,
                "is_live_ai": False,
                "error": None
            }

    @classmethod
    def analyze_disclosure_extracts(
        cls,
        text_extracts: str = "",
        profile: Dict[str, Any] = None,
        review_mode: str = "Option A",
        api_key: Optional[str] = None,
        doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compatibility wrapper for extract analysis."""
        dummy_doc = doc or {"pages": [], "full_text": text_extracts}
        return cls.analyze_full_document(dummy_doc, profile or {}, review_mode, api_key)

    @classmethod
    def _build_representative_extracts(cls, pages: List[Dict[str, Any]], full_text: str) -> str:
        """Extracts high-value disclosure extracts from across all pages of a 50-200 page filing."""
        if len(full_text) <= 25000:
            return full_text

        # For large documents, select pages with significant accounting policies, primary statements, notes & CARO
        selected_snippets = []
        for p in pages:
            t = p["text"]
            t_lower = t.lower()
            if any(k in t_lower for k in [
                "balance sheet", "profit and loss", "cash flow", "significant accounting policies",
                "property, plant", "leases", "revenue", "employee benefit", "income tax", "related party",
                "financial instruments", "auditor's report", "caro", "ratios", "share capital", "contingent"
            ]):
                selected_snippets.append(f"--- PAGE {p['page_num']} ---\n{t[:1200]}")

            if sum(len(s) for s in selected_snippets) > 24000:
                break

        return "\n\n".join(selected_snippets)

    @classmethod
    def _call_gemini_api(
        cls,
        text_extracts: str,
        profile: Dict[str, Any],
        review_mode: str,
        api_key: str
    ) -> List[Dict[str, Any]]:
        """Makes REST call to Gemini 1.5 Flash."""
        prompt_content = f"""
Entity Profile:
- Company Type: {profile.get('company_type')}
- Listing Status: {profile.get('listing_status')}
- Framework: {profile.get('framework')}
- Schedule III: {profile.get('schedule_iii_division')}
- Statement Type: {profile.get('statement_type')}
- Review Mode: {review_mode}

Authoritative requirement text (from the notified standards in the reviewer's knowledge base).
Cite ONLY paragraphs that appear here or that you are certain of; otherwise write "Reference Verification Required":
\"\"\"
{KnowledgeBase.retrieval_context(text_extracts, profile.get('framework', ''))}
\"\"\"

Financial Statements & Notes Extracts:
\"\"\"
{text_extracts[:20000]}
\"\"\"

Analyze the disclosures above against Ind AS / AS, Schedule III, and CARO 2020.
Write each observation as a reviewing Chartered Accountant would: what is presented, what the requirement is, and the exact disclosure / correction needed.
Do not report a matter that is already adequately disclosed in the extracts.
Output ONLY a valid JSON list of findings.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": cls.SYSTEM_PROMPT + "\n\n" + prompt_content}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text[:120]}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        text_out = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        parsed = json.loads(text_out)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "findings" in parsed:
            return parsed["findings"]
        return []

    @classmethod
    def _deep_document_heuristics(
        cls,
        pages: List[Dict[str, Any]],
        text: str,
        profile: Dict[str, Any],
        review_mode: str
    ) -> List[Dict[str, Any]]:
        """Deep NLP analyzer scanning every note and page across large corporate financial filings."""
        findings = []
        is_ind_as = "ind as" in profile.get("framework", "").lower()

        # Helper to find relevant page for specific topics
        def find_page(keywords: List[str]) -> Optional[int]:
            for p in pages:
                t_lower = p["text"].lower()
                if any(kw in t_lower for kw in keywords):
                    return p["page_num"]
            return None

        # 1. Customer Concentration (>10% revenue)
        if re.search(r"revenue\s+from\s+operations\b|sale\s+of\s+products|turnover\b", text, re.IGNORECASE):
            if not re.search(r"(?:single\s+external\s+customer|major\s+customer|10%\s+or\s+more\s+of\s+the\s+entity'?s\s+revenues|customer\s+concentration)", text, re.IGNORECASE):
                p_rev = find_page(["revenue from operations", "operating segments", "segment"])
                ref_str = f"Page {p_rev} / Note on Revenue / Segments" if p_rev else "Notes to Accounts - Revenue & Segments"
                tech_citation = "Ind AS 108, Paragraph 34" if is_ind_as else "AS 17; Guidance Note on Accrual & Material Disclosures"
                findings.append({
                    "rule_code": "INDAS-108-MAJOR-CUSTOMER" if is_ind_as else "AS-17-MAJOR-CUSTOMER",
                    "category": "Accounting Standards - Segment Reporting & Concentrations",
                    "ref": ref_str,
                    "extract": "Revenue disclosures omit entity-wide major customer concentration details.",
                    "description": "Omission of mandatory disclosure regarding reliance on major customers contributing ≥ 10% of revenue.",
                    "technical_ref": tech_citation,
                    "suggested_correction": (
                        "Disclose information on the extent of reliance on major customers: state whether revenues from any single external customer "
                        "amount to 10% or more of total revenue, along with total amount of revenue from each such customer."
                    ),
                    "risk": "Medium",
                    "nature": "Disclosure Deficiency"
                })

        # 2. Gratuity / Employee Benefits: Published Mortality Table Reference (IALM)
        if re.search(r"defined\s+benefit\s+obligations?|gratuity\b|employee\s+benefits?\b", text, re.IGNORECASE):
            if not re.search(r"indian\s+assured\s+lives\s+mortality|ialm", text, re.IGNORECASE):
                p_emp = find_page(["gratuity", "employee benefit"])
                ref_str = f"Page {p_emp} / Note on Employee Benefits" if p_emp else "Notes to Accounts - Employee Benefits"
                tech_citation = "Ind AS 19, Paragraph 142; ICAI Guidance Note on Employee Benefits" if is_ind_as else "AS 15, Paragraph 120(l)"
                findings.append({
                    "rule_code": "INDAS-19-MORTALITY" if is_ind_as else "AS-15-MORTALITY",
                    "category": "Accounting Standards - Employee Benefits",
                    "ref": ref_str,
                    "extract": "Actuarial valuation disclosures do not explicitly cite the standard mortality table reference (IALM).",
                    "description": "Actuarial assumptions disclosure lacks reference to published mortality table (e.g. Indian Assured Lives Mortality 2012-14 Urban).",
                    "technical_ref": tech_citation,
                    "suggested_correction": (
                        "Explicitly disclose the actuarial mortality table adopted (e.g., 'IALM 2012-14 Ultimate') "
                        "in the principal actuarial assumptions table."
                    ),
                    "risk": "Low",
                    "nature": "Presentation Matter"
                })

        # 3. Foreign Currency Exposure: Unhedged Exposures
        if re.search(r"foreign\s+currency|forex\b", text, re.IGNORECASE):
            if not re.search(r"unhedged\s+foreign\s+currency|derivative\s+contracts\s+outstanding|unhedged\s+forex", text, re.IGNORECASE):
                p_fx = find_page(["foreign currency", "financial risk management", "forex"])
                ref_str = f"Page {p_fx} / Note on Foreign Currency Exposure" if p_fx else "Notes to Accounts - Financial Risk"
                tech_citation = "Schedule III Division II Clause 6(T); Ind AS 107 Paragraph 34" if is_ind_as else "Schedule III Division I Clause 6(T); AS 11"
                findings.append({
                    "rule_code": "SCH3-FOREX-UNHEDGED",
                    "category": "Schedule III - Foreign Currency Disclosures",
                    "ref": ref_str,
                    "extract": "Foreign currency transactions mentioned without explicit statement of unhedged foreign currency exposures.",
                    "description": "Omission of specific disclosure regarding unhedged foreign currency exposures as on balance sheet date.",
                    "technical_ref": tech_citation,
                    "suggested_correction": (
                        "Disclose particulars of unhedged foreign currency exposures (currency, foreign amount, INR amount) as on balance sheet date, "
                        "or provide explicit negative statement confirming nil unhedged exposure."
                    ),
                    "risk": "Medium",
                    "nature": "Disclosure Deficiency"
                })

        # 4. Useful Lives of PPE Different from Schedule II Justification
        if re.search(r"useful\s+lives\b", text, re.IGNORECASE) and re.search(r"schedule\s+ii\b", text, re.IGNORECASE):
            if not re.search(r"independent\s+technical\s+evaluation|technical\s+advice|techno-economic", text, re.IGNORECASE) and re.search(r"different\s+from\s+schedule\s+ii|higher\s+than\s+schedule\s+ii|lower\s+than\s+schedule\s+ii", text, re.IGNORECASE):
                p_ppe = find_page(["property, plant", "depreciation", "fixed assets"])
                ref_str = f"Page {p_ppe} / PPE Note" if p_ppe else "Notes to Accounts - PPE"
                tech_citation = "Schedule II, Part B of Companies Act, 2013; Ind AS 16 Paragraph 51" if is_ind_as else "Schedule II, Part B of Companies Act, 2013; AS 10 (Revised)"
                findings.append({
                    "rule_code": "PPE-USEFUL-LIVES-JUSTIFICATION",
                    "category": "Accounting Standards - PPE & Depreciation",
                    "ref": ref_str,
                    "extract": "Useful lives of certain assets stated as differing from Schedule II without citing technical evaluation.",
                    "description": "Adoption of asset useful lives different from Schedule II to Companies Act 2013 without disclosing independent technical evaluation.",
                    "technical_ref": tech_citation,
                    "suggested_correction": (
                        "Disclose that the useful lives different from Schedule II have been determined based on an independent technical evaluation, "
                        "specifying justification for the adopted useful lives."
                    ),
                    "risk": "High",
                    "nature": "Technical Deficiency"
                })

        # 5. Contingent Liabilities Qualitative Disclosures
        if re.search(r"contingent\s+liabilit(?:y|ies)", text, re.IGNORECASE):
            if not re.search(r"(?:possibility\s+of\s+reimbursement|timing\s+of\s+outflow|uncertaint(?:y|ies)\s+relating\s+to)", text, re.IGNORECASE):
                p_cont = find_page(["contingent liabilities", "contingent claims"])
                ref_str = f"Page {p_cont} / Note on Contingent Liabilities" if p_cont else "Notes to Accounts - Contingent Liabilities"
                findings.append({
                    "rule_code": "CONTINGENT-LIAB-QUALITATIVE",
                    "category": "Accounting Standards - Provisions & Contingencies",
                    "ref": ref_str,
                    "extract": "Contingent liabilities disclosed as numerical claims without qualitative uncertainty or reimbursement disclosures.",
                    "description": "Lack of required qualitative description regarding timing of cash outflows and possibility of reimbursement.",
                    "technical_ref": "Ind AS 37, Paragraph 86 / AS 29, Paragraph 68",
                    "suggested_correction": (
                        "Disclose: (a) brief description of nature of obligation, (b) estimate of financial effect, "
                        "(c) indication of uncertainties relating to amount or timing of outflow, and (d) possibility of reimbursement."
                    ),
                    "risk": "Medium",
                    "nature": "Disclosure Deficiency"
                })

        # 6. Deferred Tax Asset on Unused Tax Losses: Convincing Evidence
        if re.search(r"deferred\s+tax\s+assets?", text, re.IGNORECASE) and re.search(r"tax\s+losses|unabsorbed\s+depreciation", text, re.IGNORECASE):
            if not re.search(r"convincing\s+evidence|virtual\s+certainty|reasonable\s+certainty", text, re.IGNORECASE):
                p_tax = find_page(["deferred tax", "income taxes"])
                ref_str = f"Page {p_tax} / Note on Deferred Tax" if p_tax else "Notes to Accounts - Deferred Tax"
                findings.append({
                    "rule_code": "TAX-DTA-CONVINCING-EVIDENCE",
                    "category": "Accounting Standards - Income Taxes",
                    "ref": ref_str,
                    "extract": "Deferred tax asset recognized on unabsorbed business losses / depreciation without convincing evidence disclosure.",
                    "description": "Absence of disclosure regarding convincing evidence of future taxable profits supporting DTA recognition on tax losses.",
                    "technical_ref": "Ind AS 12, Paragraph 35 / AS 22, Paragraph 17",
                    "suggested_correction": (
                        "Disclose the specific nature of convincing evidence (e.g. firm order book, projected profitable taxable operations) "
                        "substantiating reasonable expectation of sufficient future taxable profits."
                    ),
                    "risk": "High",
                    "nature": "Professional Judgement Required"
                })

        # 7. Schedule III: Benami Property Proceedings
        if not re.search(r"benami\s+propert(?:y|ies)|benami\s+transactions", text, re.IGNORECASE):
            findings.append({
                "rule_code": "SCH3-BENAMI-PROPERTY",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "extract": "No disclosure statement found regarding Benami Property proceedings.",
                "description": "Omission of mandatory Schedule III disclosure on Benami Property held under Benami Transactions (Prohibition) Act, 1988.",
                "technical_ref": "Schedule III (General Instructions, Part I, Clause 6(R)); Section 129",
                "suggested_correction": (
                    "Incorporate statutory disclosure confirming whether any proceedings have been initiated or are pending against the company "
                    "for holding any benami property under the Benami Transactions (Prohibition) Act, 1988 and rules made thereunder."
                ),
                "risk": "Medium",
                "nature": "Disclosure Deficiency"
            })

        # 8. Schedule III: Wilful Defaulter Declaration
        if not re.search(r"wilful\s+defaulter", text, re.IGNORECASE):
            findings.append({
                "rule_code": "SCH3-WILFUL-DEFAULTER",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information / Borrowings",
                "extract": "No disclosure statement found regarding Wilful Defaulter declaration.",
                "description": "Omission of mandatory Schedule III confirmation regarding declaration as Wilful Defaulter by any bank or financial institution.",
                "technical_ref": "Schedule III (General Instructions, Part I, Clause 6(S))",
                "suggested_correction": (
                    "Add explicit statutory confirmation in Borrowings / Additional Regulatory Information note stating whether the company "
                    "has been declared a wilful defaulter by any bank or financial institution or other lender."
                ),
                "risk": "High",
                "nature": "Disclosure Deficiency"
            })

        # 9. Schedule III: Crypto Currency or Virtual Currency
        if not re.search(r"crypto\s+currency|virtual\s+currency", text, re.IGNORECASE):
            findings.append({
                "rule_code": "SCH3-CRYPTO-CURRENCY",
                "category": "Schedule III - Regulatory Disclosures",
                "ref": "Notes to Accounts - Additional Regulatory Information",
                "extract": "No disclosure statement found regarding Crypto or Virtual Currency transactions.",
                "description": "Omission of mandatory Schedule III disclosure on Crypto Currency or Virtual Currency trading/investing.",
                "technical_ref": "Schedule III (General Instructions, Part I, Clause 6(Z))",
                "suggested_correction": (
                    "Incorporate statutory declaration confirming whether the company has traded or invested in Crypto currency or Virtual Currency "
                    "during the financial year, including details of profit/loss or advance/deposits from customers."
                ),
                "risk": "Low",
                "nature": "Disclosure Deficiency"
            })

        # 10. Schedule III: Borrowing Security & Quarterly Statements Filed with Banks
        if re.search(r"working\s+capital\s+facilities|cash\s+credit|working\s+capital\s+limits", text, re.IGNORECASE):
            if not re.search(r"quarterly\s+(?:statements?|returns?).*filed\s+with\s+banks?|reconciliation\s+of\s+quarterly\s+returns", text, re.IGNORECASE):
                p_borr = find_page(["borrowings", "working capital"])
                ref_str = f"Page {p_borr} / Borrowings Note" if p_borr else "Notes to Accounts - Borrowings"
                findings.append({
                    "rule_code": "SCH3-BANK-RETURNS-RECON",
                    "category": "Schedule III - Bank Reconciliations",
                    "ref": ref_str,
                    "extract": "Company has working capital facilities secured by current assets without quarterly bank statements reconciliation.",
                    "description": "Omission of Schedule III disclosure reconciling quarterly statements filed with banks with books of accounts.",
                    "technical_ref": "Schedule III (General Instructions, Part I, Clause 6(L)); CARO 2020 Clause 3(ii)(b)",
                    "suggested_correction": (
                        "Disclose summary reconciliation between quarterly returns/statements filed by the company with banks/FIs "
                        "and the books of accounts, explaining any material differences."
                    ),
                    "risk": "High",
                    "nature": "Action Required" if review_mode == "Option A" else "Material Red Flag"
                })

        # 11. Related Party Transactions: Arm's Length Substantiation
        if re.search(r"related\s+party\b|related\s+parties\b", text, re.IGNORECASE):
            if re.search(r"arm'?s\s+length\s+basis|at\s+arm'?s\s+length", text, re.IGNORECASE) and not re.search(r"transfer\s+pricing|comparable\s+uncontrolled|substantiat", text, re.IGNORECASE):
                p_rpt = find_page(["related party", "related parties"])
                ref_str = f"Page {p_rpt} / Note on Related Party Disclosures" if p_rpt else "Notes to Accounts - Related Parties"
                findings.append({
                    "rule_code": "RPT-ARMS-LENGTH-SUBSTANTIATION",
                    "category": "Accounting Standards & Companies Act - Related Parties",
                    "ref": ref_str,
                    "extract": "Statement made that related party transactions are at arm's length without substantiation.",
                    "description": "Ind AS 24.23 / Section 188 arm's length statement requires management substantiation through transfer pricing documentation.",
                    "technical_ref": "Ind AS 24, Paragraph 23 / AS 18; Section 188(1) of Companies Act, 2013",
                    "suggested_correction": (
                        "Ensure management maintains contemporaneous transfer pricing documentation to substantiate arm's length assertions "
                        "made in financial statements as required by Ind AS 24.23."
                    ),
                    "risk": "Medium",
                    "nature": "Professional Judgement Required"
                })

        # 12. Cash Flow Statement: Non-Cash Investing and Financing Transactions
        if re.search(r"cash\s+flow\s+statement|statement\s+of\s+cash\s+flows?", text, re.IGNORECASE):
            if not re.search(r"non[- ]cash\s+(?:investing|financing|transactions)|supplemental\s+cash\s+flow", text, re.IGNORECASE):
                p_cfs = find_page(["cash flow", "statement of cash flows"])
                ref_str = f"Page {p_cfs} / Cash Flow Statement" if p_cfs else "Cash Flow Statement"
                findings.append({
                    "rule_code": "CFS-NON-CASH-TRANSACTIONS",
                    "category": "Accounting Standards - Statement of Cash Flows",
                    "ref": ref_str,
                    "extract": "Cash Flow Statement lacks explicit disclosure of non-cash investing and financing transactions.",
                    "description": "Omission of disclosure regarding non-cash investing and financing transactions (e.g., acquisition of assets via lease liabilities, share-based payments).",
                    "technical_ref": "Ind AS 7, Paragraph 43 / AS 3, Paragraph 40",
                    "suggested_correction": (
                        "Disclose non-cash investing and financing transactions that do not require use of cash or cash equivalents "
                        "(e.g., ROU asset additions, conversion of debt to equity) in a separate note to Cash Flow Statement."
                    ),
                    "risk": "Low",
                    "nature": "Disclosure Deficiency"
                })

        return findings

        return findings
