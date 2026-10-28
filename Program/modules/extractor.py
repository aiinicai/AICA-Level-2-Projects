"""
Local AI and NLP Information Extraction Engine for Ind AS 116
Extracts 20+ lease agreement terms with confidence scores, page citations, and review flags.
Works 100% offline via robust NLP heuristics, with optional local Ollama LLM integration.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, date
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import requests

@dataclass
class ExtractedField:
    key: str
    label: str
    value: Any
    confidence: float  # 0.0 to 1.0
    source_page: Union[int, str]
    source_snippet: str
    requires_review: bool
    review_notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class LeaseExtractor:
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "mistral"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model

    def is_ollama_available(self) -> bool:
        """Checks if a local Ollama daemon is reachable offline on localhost."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_ollama_models(self) -> List[str]:
        """Lists locally downloaded models in Ollama."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def extract_all_fields(
        self,
        pages_dict: Dict[int, str],
        use_llm: bool = False,
        selected_model: Optional[str] = None
    ) -> Dict[str, ExtractedField]:
        """
        Main extraction entry point.
        Extracts all standard Ind AS 116 contract fields.
        """
        # Always run high-precision local NLP rule extractor first
        extracted = self._extract_with_heuristics(pages_dict)

        # If LLM requested and available, enhance/refine ambiguous fields
        if use_llm and self.is_ollama_available():
            model = selected_model or self.default_model
            llm_results = self._extract_with_ollama(pages_dict, model)
            if llm_results:
                for k, v in llm_results.items():
                    if k in extracted and (extracted[k].requires_review or extracted[k].confidence < 0.70):
                        if v.value is not None:
                            extracted[k] = v

        return extracted

    def _extract_with_heuristics(self, pages_dict: Dict[int, str]) -> Dict[str, ExtractedField]:
        """
        Rule-based NLP and Regular Expression extraction tailored for lease contracts.
        Preserves exact page numbers for traceability.
        """
        fields: Dict[str, ExtractedField] = {}
        full_text = "\n".join([f"Page {p}:\n{txt}" for p, txt in pages_dict.items()])

        # 1. Lessor Name
        lessor_val, lessor_conf, lessor_pg, lessor_snip = self._find_party(pages_dict, r"(?:Lessor|Landlord|Licensor|Owner)")
        fields["lessor_name"] = ExtractedField(
            key="lessor_name",
            label="Lessor / Landlord Name",
            value=lessor_val or "Requires Review",
            confidence=lessor_conf,
            source_page=lessor_pg,
            source_snippet=lessor_snip,
            requires_review=lessor_conf < 0.75 or not lessor_val
        )

        # 2. Lessee Name
        lessee_val, lessee_conf, lessee_pg, lessee_snip = self._find_party(pages_dict, r"(?:Lessee|Tenant|Licensee|Occupant)")
        fields["lessee_name"] = ExtractedField(
            key="lessee_name",
            label="Lessee / Tenant Name",
            value=lessee_val or "Requires Review",
            confidence=lessee_conf,
            source_page=lessee_pg,
            source_snippet=lessee_snip,
            requires_review=lessee_conf < 0.75 or not lessee_val
        )

        # 3. Asset Description / Demised Premises
        asset_val, asset_conf, asset_pg, asset_snip = self._find_asset_description(pages_dict)
        fields["asset_description"] = ExtractedField(
            key="asset_description",
            label="Demised Premises / Asset Description",
            value=asset_val or "Commercial Leased Premises",
            confidence=asset_conf,
            source_page=asset_pg,
            source_snippet=asset_snip,
            requires_review=asset_conf < 0.70
        )

        # 4. Lease Commencement Date
        comm_val, comm_conf, comm_pg, comm_snip = self._find_date(
            pages_dict,
            [
                r"commence(?:ment)?\s*(?:date|from)?\s*[:\-]?\s*([0-9]{1,2}[th|st|nd|rd\s]*[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
                r"w\.?e\.?f\.?\s*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
                r"dated\s+(?:this\s+)?([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:day of\s+)?[A-Za-z]+,?\s+[0-9]{4})"
            ]
        )
        fields["commencement_date"] = ExtractedField(
            key="commencement_date",
            label="Lease Commencement Date",
            value=comm_val or "2024-04-01",
            confidence=comm_conf,
            source_page=comm_pg,
            source_snippet=comm_snip,
            requires_review=comm_conf < 0.75 or not comm_val
        )

        # 5. Possession / Handover Date
        poss_val, poss_conf, poss_pg, poss_snip = self._find_date(
            pages_dict,
            [
                r"possession\s*(?:date|handed over on)?\s*[:\-]?\s*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
                r"handover\s*(?:date|on)?\s*[:\-]?\s*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})"
            ]
        )
        fields["possession_date"] = ExtractedField(
            key="possession_date",
            label="Possession / Handover Date",
            value=poss_val or comm_val or "2024-04-01",
            confidence=poss_conf if poss_val else 0.50,
            source_page=poss_pg or comm_pg,
            source_snippet=poss_snip or "Presumed same as commencement date",
            requires_review=not poss_val
        )

        # 6. Lease Term (Months)
        term_val, term_conf, term_pg, term_snip = self._find_lease_term(pages_dict)
        fields["lease_term_months"] = ExtractedField(
            key="lease_term_months",
            label="Lease Term (Months)",
            value=term_val if term_val is not None else 60,
            confidence=term_conf,
            source_page=term_pg,
            source_snippet=term_snip,
            requires_review=term_conf < 0.75 or term_val is None
        )

        # 7. Fixed Rental Amount
        rent_val, rent_conf, rent_pg, rent_snip = self._find_rental_amount(pages_dict)
        fields["fixed_rental_amount"] = ExtractedField(
            key="fixed_rental_amount",
            label="Fixed Rental Amount per Period",
            value=rent_val if rent_val is not None else 100000.0,
            confidence=rent_conf,
            source_page=rent_pg,
            source_snippet=rent_snip,
            requires_review=rent_conf < 0.75 or rent_val is None
        )

        # 8. Payment Frequency
        freq_val, freq_conf, freq_pg, freq_snip = self._find_frequency(pages_dict)
        fields["payment_frequency"] = ExtractedField(
            key="payment_frequency",
            label="Payment Frequency",
            value=freq_val,
            confidence=freq_conf,
            source_page=freq_pg,
            source_snippet=freq_snip,
            requires_review=freq_conf < 0.70
        )

        # 9. Payment Timing (Advance / Arrears)
        timing_val, timing_conf, timing_pg, timing_snip = self._find_payment_timing(pages_dict)
        fields["payment_timing"] = ExtractedField(
            key="payment_timing",
            label="Payment Timing",
            value=timing_val,
            confidence=timing_conf,
            source_page=timing_pg,
            source_snippet=timing_snip,
            requires_review=timing_conf < 0.65
        )

        # 10. Due Date Convention
        due_val, due_conf, due_pg, due_snip = self._find_due_date_convention(pages_dict)
        fields["due_date_convention"] = ExtractedField(
            key="due_date_convention",
            label="Due Date Convention",
            value=due_val or "7th of each month",
            confidence=due_conf,
            source_page=due_pg,
            source_snippet=due_snip,
            requires_review=due_conf < 0.60
        )

        # 11. Rent-Free Period
        rf_val, rf_conf, rf_pg, rf_snip = self._find_rent_free_period(pages_dict)
        fields["rent_free_period_months"] = ExtractedField(
            key="rent_free_period_months",
            label="Rent-Free Period (Fit-out months)",
            value=rf_val if rf_val is not None else 0,
            confidence=rf_conf,
            source_page=rf_pg,
            source_snippet=rf_snip,
            requires_review=False
        )

        # 12. Escalation Clause & Percentage
        esc_val, esc_pct, esc_freq, esc_conf, esc_pg, esc_snip = self._find_escalation(pages_dict)
        fields["escalation_clause"] = ExtractedField(
            key="escalation_clause",
            label="Escalation Clause Present?",
            value=esc_val,
            confidence=esc_conf,
            source_page=esc_pg,
            source_snippet=esc_snip,
            requires_review=esc_conf < 0.70
        )
        fields["escalation_pct"] = ExtractedField(
            key="escalation_pct",
            label="Escalation Percentage (%)",
            value=esc_pct if esc_pct is not None else 5.0,
            confidence=esc_conf,
            source_page=esc_pg,
            source_snippet=esc_snip,
            requires_review=esc_conf < 0.70 and esc_val
        )
        fields["escalation_frequency_months"] = ExtractedField(
            key="escalation_frequency_months",
            label="Escalation Frequency (Months)",
            value=esc_freq if esc_freq is not None else 12,
            confidence=esc_conf,
            source_page=esc_pg,
            source_snippet=esc_snip,
            requires_review=False
        )

        # 13. Security Deposit
        sec_val, sec_conf, sec_pg, sec_snip = self._find_money(
            pages_dict,
            [r"security\s*deposit", r"interest[\-\s]*free\s*refundable\s*security\s*deposit", r"refundable\s*deposit"]
        )
        fields["security_deposit"] = ExtractedField(
            key="security_deposit",
            label="Security Deposit",
            value=sec_val if sec_val is not None else 0.0,
            confidence=sec_conf,
            source_page=sec_pg,
            source_snippet=sec_snip,
            requires_review=sec_conf < 0.65
        )

        # 14. Lease Incentive
        inc_val, inc_conf, inc_pg, inc_snip = self._find_money(
            pages_dict,
            [r"lease\s*incentive", r"tenant\s*improvement\s*allowance", r"fit[\-\s]*out\s*contribution", r"reimbursement\s*by\s*lessor"]
        )
        fields["lease_incentive"] = ExtractedField(
            key="lease_incentive",
            label="Lease Incentive Received",
            value=inc_val if inc_val is not None else 0.0,
            confidence=inc_conf,
            source_page=inc_pg,
            source_snippet=inc_snip,
            requires_review=False
        )

        # 15. Initial Direct Costs
        idc_val, idc_conf, idc_pg, idc_snip = self._find_money(
            pages_dict,
            [r"initial\s*direct\s*cost", r"brokerage\s*fee", r"stamp\s*duty\s*and\s*registration", r"legal\s*fee\s*borne\s*by\s*lessee"]
        )
        fields["initial_direct_costs"] = ExtractedField(
            key="initial_direct_costs",
            label="Initial Direct Costs Incurred",
            value=idc_val if idc_val is not None else 0.0,
            confidence=idc_conf,
            source_page=idc_pg,
            source_snippet=idc_snip,
            requires_review=False
        )

        # 16. Restoration Obligation / Dismantling Provision
        rest_val, rest_conf, rest_pg, rest_snip = self._find_money(
            pages_dict,
            [r"restoration\s*(?:cost|obligation)", r"dismantling\s*obligation", r"reinstatement\s*cost", r"restore\s*premises\s*to\s*original"]
        )
        fields["restoration_obligation"] = ExtractedField(
            key="restoration_obligation",
            label="Dismantling / Restoration Obligation",
            value=rest_val if rest_val is not None else 0.0,
            confidence=rest_conf,
            source_page=rest_pg,
            source_snippet=rest_snip,
            requires_review=False
        )

        # 17. Renewal / Extension Option
        ren_val, ren_cert, ren_conf, ren_pg, ren_snip = self._find_renewal_clause(pages_dict)
        fields["renewal_option"] = ExtractedField(
            key="renewal_option",
            label="Renewal / Extension Option",
            value=ren_val,
            confidence=ren_conf,
            source_page=ren_pg,
            source_snippet=ren_snip,
            requires_review=ren_conf < 0.65
        )
        fields["renewal_certain"] = ExtractedField(
            key="renewal_certain",
            label="Renewal Reasonably Certain to be Exercised?",
            value=ren_cert,
            confidence=0.60,
            source_page=ren_pg,
            source_snippet="Judgmental assessment required by Management under Ind AS 116 para 18",
            requires_review=True,
            review_notes="Confirm if entity has significant economic incentive or leasehold improvements to renew."
        )

        # 18. Termination Option
        term_opt_val, term_opt_conf, term_opt_pg, term_opt_snip = self._find_termination_clause(pages_dict)
        fields["termination_option"] = ExtractedField(
            key="termination_option",
            label="Termination Option & Notice Period",
            value=term_opt_val,
            confidence=term_opt_conf,
            source_page=term_opt_pg,
            source_snippet=term_opt_snip,
            requires_review=term_opt_conf < 0.65
        )

        # 19. Purchase Option
        pur_val, pur_price, pur_cert, pur_conf, pur_pg, pur_snip = self._find_purchase_option(pages_dict)
        fields["purchase_option"] = ExtractedField(
            key="purchase_option",
            label="Purchase Option Available?",
            value=pur_val,
            confidence=pur_conf,
            source_page=pur_pg,
            source_snippet=pur_snip,
            requires_review=pur_val
        )
        fields["purchase_option_price"] = ExtractedField(
            key="purchase_option_price",
            label="Purchase Option Strike Price",
            value=pur_price if pur_price is not None else 0.0,
            confidence=pur_conf,
            source_page=pur_pg,
            source_snippet=pur_snip,
            requires_review=pur_val
        )
        fields["purchase_certain"] = ExtractedField(
            key="purchase_certain",
            label="Purchase Option Reasonably Certain?",
            value=pur_cert,
            confidence=0.60,
            source_page=pur_pg,
            source_snippet="Under Ind AS 116, exercise price is included in liability only if exercise is reasonably certain.",
            requires_review=pur_val
        )

        # 20. Variable Lease Payments
        var_val, var_conf, var_pg, var_snip = self._find_variable_payments(pages_dict)
        fields["variable_lease_payments"] = ExtractedField(
            key="variable_lease_payments",
            label="Variable Lease Payments Clause",
            value=var_val,
            confidence=var_conf,
            source_page=var_pg,
            source_snippet=var_snip,
            requires_review=bool(var_val and var_val != "None detected")
        )

        # 21. Non-Lease Components (CAM, Maintenance, Insurance)
        cam_val, cam_conf, cam_pg, cam_snip = self._find_non_lease_components(pages_dict)
        fields["non_lease_components"] = ExtractedField(
            key="non_lease_components",
            label="Non-Lease Components (CAM/Maintenance)",
            value=cam_val if cam_val is not None else 0.0,
            confidence=cam_conf,
            source_page=cam_pg,
            source_snippet=cam_snip,
            requires_review=cam_conf < 0.65
        )

        # 22. Discount Rate (Incremental Borrowing Rate)
        disc_val, disc_conf, disc_pg, disc_snip = self._find_discount_rate(pages_dict)
        fields["discount_rate"] = ExtractedField(
            key="discount_rate",
            label="Discount Rate / IBR (% p.a.)",
            value=disc_val if disc_val is not None else 8.50,
            confidence=disc_conf,
            source_page=disc_pg,
            source_snippet=disc_snip,
            requires_review=disc_conf < 0.70
        )

        # 23. Residual Value Guarantee
        fields["residual_value_guarantee"] = ExtractedField(
            key="residual_value_guarantee",
            label="Residual Value Guarantee",
            value=0.0,
            confidence=0.85,
            source_page="General",
            source_snippet="Typically Nil in real estate leases unless specifically contracted.",
            requires_review=False
        )

        # 24. Restrictions and Covenants
        cov_val, cov_conf, cov_pg, cov_snip = self._find_covenants(pages_dict)
        fields["restrictions_covenants"] = ExtractedField(
            key="restrictions_covenants",
            label="Restrictions and Operational Covenants",
            value=cov_val,
            confidence=cov_conf,
            source_page=cov_pg,
            source_snippet=cov_snip,
            requires_review=False
        )

        # 25. Indemnity & Other Clauses
        indem_val, indem_conf, indem_pg, indem_snip = self._find_indemnity(pages_dict)
        fields["indemnity_clauses"] = ExtractedField(
            key="indemnity_clauses",
            label="Indemnity & Dispute Resolution",
            value=indem_val,
            confidence=indem_conf,
            source_page=indem_pg,
            source_snippet=indem_snip,
            requires_review=False
        )

        return fields

    # ----------------- NLP Helper Regex Functions -----------------

    def _find_party(self, pages: Dict[int, str], party_pattern: str) -> Tuple[Optional[str], float, Union[int, str], str]:
        """Identifies Party name (Lessor/Lessee) from recitals, preamble, or signatures."""
        is_lessor = bool(re.search(r'lessor|landlord|licensor', party_pattern, re.IGNORECASE))
        
        for p_num, text in pages.items():
            # Pattern A: Standard recital format: between [Name] (hereinafter Lessor) and [Name] (hereinafter Lessee)
            if is_lessor:
                m1 = re.search(r'(?:between|by\s+and\s+between)\s*[:\-]?\s*([A-Za-z0-9\.\s\,\&\-\(\)]{4,80}?(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|Ltd\.?|LLP|Inc\.?|Corporation))', text, re.IGNORECASE)
                if m1:
                    name = m1.group(1).strip().strip("(),;:- \n")
                    snip = text[max(0, m1.start()): min(len(text), m1.end() + 25)]
                    return name, 0.94, p_num, snip.strip()
            else:
                m2 = re.search(r'\bAND\b\s*[:\-]?\s*([A-Za-z0-9\.\s\,\&\-\(\)]{4,80}?(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|Ltd\.?|LLP|Inc\.?|Corporation))', text, re.IGNORECASE)
                if m2:
                    name = m2.group(1).strip().strip("(),;:- \n")
                    snip = text[max(0, m2.start()): min(len(text), m2.end() + 25)]
                    return name, 0.94, p_num, snip.strip()

            # Pattern B: Direct label e.g., "Lessor: XYZ Pvt Ltd" or "Lessee: ABC Ltd"
            match_lbl = re.search(rf'{party_pattern}\s*[:\-]\s*([A-Za-z0-9\.\s\,\&]{{4,60}})', text, re.IGNORECASE)
            if match_lbl:
                name = match_lbl.group(1).split("\n")[0].strip()
                name = re.sub(r'^(?:m/s\.|mr\.|ms\.)\s*', '', name, flags=re.IGNORECASE).strip().strip("(),;:- ")
                snippet = text[max(0, match_lbl.start() - 10): min(len(text), match_lbl.end() + 20)]
                return name, 0.88, p_num, snippet.strip()

            # Pattern C: Generic party recital
            m_gen = re.search(
                rf'([A-Za-z0-9\.\s\,\&\-]{{4,60}}?)\s*\(?\s*(?:hereinafter|herein\s+after)[^\.\n]{{0,40}}?{party_pattern}',
                text,
                re.IGNORECASE
            )
            if m_gen:
                raw_name = m_gen.group(1).strip()
                clean = re.sub(r'^(?:between|by\s+and\s+between|and|mr\.|ms\.|m/s\.)\s*', '', raw_name, flags=re.IGNORECASE).strip().strip("(),;:- ")
                if len(clean) > 3 and not re.search(r'^(day|date|agreement)', clean, re.IGNORECASE):
                    snip = text[max(0, m_gen.start() - 10): min(len(text), m_gen.end() + 20)]
                    return clean, 0.88, p_num, snip.strip()

        return None, 0.30, "Not Found", "Party clause not identified clearly in document"

    def _find_asset_description(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            match = re.search(
                r'(?:demised\s+premises|leased\s+premises|description\s+of\s+(?:the\s+)?premises|schedule\s+["\']?[a-z]?["\']?\s+premises|unit\s+no|office\s+no|plot\s+no|situated\s+at)\s*[:\-]?\s*([^\n\.\;]{10,140})',
                text,
                re.IGNORECASE
            )
            if match:
                desc = match.group(0).strip()
                return desc, 0.85, p_num, desc

        return "Commercial Office / Property Premises", 0.40, 1, "Default description inferred"

    def _find_date(self, pages: Dict[int, str], patterns: List[str]) -> Tuple[Optional[str], float, Union[int, str], str]:
        for p_num, text in pages.items():
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    raw_date = m.group(1).strip()
                    std_date = self._standardize_date(raw_date)
                    snip = text[max(0, m.start() - 20): min(len(text), m.end() + 20)]
                    return std_date, 0.90, p_num, snip.strip()
        return None, 0.30, 1, "Date not located"

    def _standardize_date(self, raw: str) -> str:
        """Converts diverse date strings to YYYY-MM-DD format."""
        clean = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', raw).strip()
        clean = re.sub(r'day\s+of\s+', '', clean, flags=re.IGNORECASE)
        for fmt in (
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d/%m/%y", "%d-%m-%y",
            "%Y-%m-%d", "%Y/%m/%d",
            "%d %B %Y", "%d %b %Y",
            "%B %d, %Y", "%b %d, %Y"
        ):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return clean

    def _find_lease_term(self, pages: Dict[int, str]) -> Tuple[Optional[int], float, Union[int, str], str]:
        for p_num, text in pages.items():
            # Pattern in months
            m_months = re.search(r'(?:period|term|duration)\s*(?:of)?\s*(?:the)?\s*lease\s*(?:shall\s+be)?\s*[:\-]?\s*([0-9]{1,3})\s*(?:months)', text, re.IGNORECASE)
            if m_months:
                val = int(m_months.group(1))
                snip = text[max(0, m_months.start() - 15): min(len(text), m_months.end() + 20)]
                return val, 0.92, p_num, snip.strip()

            # Pattern in years
            m_years = re.search(r'(?:period|term|duration)\s*(?:of)?\s*(?:the)?\s*lease\s*(?:shall\s+be)?\s*[:\-]?\s*([0-9]{1,2})\s*(?:years)', text, re.IGNORECASE)
            if m_years:
                val = int(m_years.group(1)) * 12
                snip = text[max(0, m_years.start() - 15): min(len(text), m_years.end() + 20)]
                return val, 0.90, p_num, snip.strip()

            # Word years (e.g., "five (5) years", "three years")
            m_word = re.search(r'(?:term\s+of|period\s+of)\s*(one|two|three|four|five|six|seven|eight|nine|ten)\s*\(?\s*([0-9]{1,2})?\s*\)?\s*years', text, re.IGNORECASE)
            if m_word:
                num = int(m_word.group(2)) if m_word.group(2) else self._word_to_num(m_word.group(1))
                if num:
                    val = num * 12
                    snip = text[max(0, m_word.start() - 10): min(len(text), m_word.end() + 20)]
                    return val, 0.88, p_num, snip.strip()

        return None, 0.35, "Not Found", "Lease duration not clearly detected"

    def _find_rental_amount(self, pages: Dict[int, str]) -> Tuple[Optional[float], float, Union[int, str], str]:
        patterns = [
            # Pattern 1: monthly rent / lease rent / fixed rent ... Rs. X
            r'(?:monthly\s+fixed\s+rent|monthly\s+rent|lease\s+rent|fixed\s+rent|license\s+fee|rent\s+payable)[^\.\n]{0,80}?(?:rs\.?|inr|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)',
            # Pattern 2: Rs. X per month / p.m. (excluding CAM or maintenance)
            r'(?:rs\.?|inr|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)\s*(?:\/\-)?\s*(?:per\s+month|\/-\s*per\s+month|p\.m\.|towards\s+rent|as\s+rent)',
            # Pattern 3: rent of Rs. X
            r'rent\s+(?:shall\s+be\s+)?(?:of\s+)?(?:rs\.?|inr|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)'
        ]
        for p_num, text in pages.items():
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    # Check if line or match snippet is CAM
                    start_context = max(0, m.start() - 30)
                    end_context = min(len(text), m.end() + 30)
                    context_snippet = text[start_context:end_context]
                    if re.search(r'\b(?:cam|maintenance|deposit|incentive)\b', context_snippet, re.IGNORECASE):
                        continue  # Skip CAM or deposit lines

                    raw_num = m.group(1).replace(",", "")
                    try:
                        val = float(raw_num)
                        if val > 0:
                            snip = text[max(0, m.start() - 15): min(len(text), m.end() + 25)]
                            return val, 0.92, p_num, snip.strip()
                    except ValueError:
                        continue
        return None, 0.30, "Not Found", "Rental amount could not be parsed"

    def _find_frequency(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            if re.search(r'quarterly|every\s+quarter|per\s+quarter', text, re.IGNORECASE):
                return "Quarterly", 0.85, p_num, "Quarterly payments indicated"
            if re.search(r'half[\-\s]yearly|semi[\-\s]annually', text, re.IGNORECASE):
                return "Half-Yearly", 0.85, p_num, "Half-yearly payments indicated"
            if re.search(r'annually|per\s+annum|every\s+year', text, re.IGNORECASE):
                return "Annual", 0.85, p_num, "Annual payments indicated"
            if re.search(r'monthly|per\s+month|p\.m\.', text, re.IGNORECASE):
                return "Monthly", 0.90, p_num, "Monthly payments indicated"
        return "Monthly", 0.70, 1, "Default standard monthly frequency assumed"

    def _find_payment_timing(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            if re.search(r'in\s+advance|advance\s+of\s+each\s+month|prior\s+to\s+the\s+commencement\s+of\s+each\s+month', text, re.IGNORECASE):
                return "In Advance", 0.85, p_num, "Payment in advance clause identified"
            if re.search(r'in\s+arrears|end\s+of\s+each\s+month|payable\s+on\s+or\s+before\s+the\s+expiry\s+of', text, re.IGNORECASE):
                return "In Arrears", 0.85, p_num, "Payment in arrears clause identified"
        # Standard commercial lease default is In Advance (due at beginning of month)
        return "In Advance", 0.65, 1, "Default commercial lease convention (In Advance)"

    def _find_due_date_convention(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:on\s+or\s+before\s+(?:the)?\s*([0-9]{1,2}(?:st|nd|rd|th)?)\s+day\s+of\s+(?:each|every)\s+month)', text, re.IGNORECASE)
            if m:
                day_str = m.group(1)
                snip = text[max(0, m.start() - 10): min(len(text), m.end() + 15)]
                return f"{day_str} day of each calendar month", 0.88, p_num, snip.strip()
        return "7th of each calendar month", 0.50, 1, "Standard default assumption"

    def _find_rent_free_period(self, pages: Dict[int, str]) -> Tuple[int, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:rent[\-\s]*free\s*(?:period)?|fit[\-\s]*out\s*period)\s*(?:of)?\s*([0-9]{1,2})\s*(?:months|days)', text, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                snip = text[max(0, m.start() - 10): min(len(text), m.end() + 20)]
                return val, 0.85, p_num, snip.strip()
        return 0, 0.70, 1, "No rent-free period stated (0 months)"

    def _find_escalation(self, pages: Dict[int, str]) -> Tuple[bool, Optional[float], int, float, Union[int, str], str]:
        patterns = [
            r'(?:escalat\w*|increas\w*|enhancement)[^\.\n]{0,60}?(?:by|of|at)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*%\s*(?:every|after|per)?\s*([0-9]{1,2})?\s*(years?|months?|annum)?',
            r'([0-9]{1,2}(?:\.[0-9]+)?)\s*%\s*(?:escalation|increase|enhancement)\s*(?:every|after|per)?\s*([0-9]{1,2})?\s*(years?|months?|annum)?'
        ]
        for p_num, text in pages.items():
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    try:
                        pct = float(m.group(1))
                        time_val = m.group(2)
                        time_unit = m.group(3) if len(m.groups()) >= 3 else None
                        freq_months = 12
                        if time_val:
                            if time_unit and "year" in time_unit.lower():
                                freq_months = int(time_val) * 12
                            elif time_unit and "annum" in time_unit.lower():
                                freq_months = 12
                            else:
                                freq_months = int(time_val)
                        elif time_unit and ("year" in time_unit.lower() or "annum" in time_unit.lower()):
                            freq_months = 12

                        snip = text[max(0, m.start() - 15): min(len(text), m.end() + 25)]
                        return True, pct, freq_months, 0.90, p_num, snip.strip()
                    except (ValueError, IndexError):
                        continue
        return False, 0.0, 12, 0.65, 1, "No explicit escalation clause found"

    def _find_money(self, pages: Dict[int, str], keywords: List[str]) -> Tuple[Optional[float], float, Union[int, str], str]:
        for p_num, text in pages.items():
            for kw in keywords:
                m = re.search(rf'{kw}\s*[:\-]?\s*(?:of)?\s*(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)', text, re.IGNORECASE)
                if m:
                    raw = m.group(1).replace(",", "")
                    try:
                        val = float(raw)
                        snip = text[max(0, m.start() - 10): min(len(text), m.end() + 20)]
                        return val, 0.84, p_num, snip.strip()
                    except ValueError:
                        continue
        return None, 0.30, "Not Found", "Item not stated or Nil"

    def _find_renewal_clause(self, pages: Dict[int, str]) -> Tuple[str, bool, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:option\s+to\s+renew|renewal\s+option|extend\s+the\s+lease)\s*([^\.\n]{10,120}\.)', text, re.IGNORECASE)
            if m:
                clause = m.group(0).strip()
                return clause, False, 0.82, p_num, clause
        return "No renewal option detected", False, 0.60, 1, "Contract appears non-renewable or subject to fresh mutual agreement"

    def _find_termination_clause(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:lock[\-\s]*in\s*period|early\s*termination|termination\s*(?:by\s+giving)?\s*([0-9]{1,2})\s*months?\s*notice)', text, re.IGNORECASE)
            if m:
                clause = m.group(0).strip()
                return clause, 0.80, p_num, clause
        return "Standard mutual termination with notice period", 0.50, 1, "Default notice clause inferred"

    def _find_purchase_option(self, pages: Dict[int, str]) -> Tuple[bool, Optional[float], bool, float, Union[int, str], str]:
        for p_num, text in pages.items():
            if re.search(r'option\s+to\s+purchase|buyout\s+option|purchase\s+the\s+demised\s+premises', text, re.IGNORECASE):
                # Search for price
                m_price = re.search(r'(?:purchase\s+price|consideration\s+of)\s*(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)', text, re.IGNORECASE)
                price = float(m_price.group(1).replace(",", "")) if m_price else None
                return True, price, False, 0.82, p_num, "Purchase option clause identified"
        return False, 0.0, False, 0.88, 1, "No purchase option present (standard lease)"

    def _find_variable_payments(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:revenue\s*share|turnover\s*rent|percentage\s*of\s*sales|cpi[\-\s]*linked)', text, re.IGNORECASE)
            if m:
                return m.group(0).strip(), 0.80, p_num, "Variable payment term detected"
        return "None detected (pure fixed rent)", 0.85, 1, "No turnover or sales-linked rent detected"

    def _find_non_lease_components(self, pages: Dict[int, str]) -> Tuple[Optional[float], float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:cam\s*charges?|common\s*area\s*maintenance|maintenance\s*charges?)\s*(?:of)?\s*(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)', text, re.IGNORECASE)
            if m:
                val = float(m.group(1).replace(",", ""))
                return val, 0.82, p_num, m.group(0).strip()
        return 0.0, 0.70, 1, "CAM not separately listed or bundled in base rent"

    def _find_discount_rate(self, pages: Dict[int, str]) -> Tuple[Optional[float], float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:discount\s*rate|incremental\s*borrowing\s*rate|ibr|interest\s*rate\s*implicit)\s*(?:is|of|at)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*%', text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                return val, 0.88, p_num, m.group(0).strip()
        return 8.50, 0.50, 1, "Standard 8.50% IBR proxy (Confirm entity's specific borrowing rate)"

    def _find_covenants(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:use\s+of\s+premises|permitted\s+use|negative\s+covenants|restrictions)\s*[:\-]?\s*([^\.\n]{15,120}\.)', text, re.IGNORECASE)
            if m:
                return m.group(0).strip(), 0.78, p_num, m.group(0).strip()
        return "Commercial office use only; subletting restricted without Lessor prior written consent.", 0.65, 1, "Standard commercial covenants inferred"

    def _find_indemnity(self, pages: Dict[int, str]) -> Tuple[str, float, Union[int, str], str]:
        for p_num, text in pages.items():
            m = re.search(r'(?:indemnity|indemnification|governing\s+law|arbitration)\s*[:\-]?\s*([^\.\n]{15,120}\.)', text, re.IGNORECASE)
            if m:
                return m.group(0).strip(), 0.78, p_num, m.group(0).strip()
        return "Lessee indemnifies Lessor against third party claims arising from negligence; governed by Indian Laws.", 0.65, 1, "Standard indemnity clause inferred"

    def _word_to_num(self, word: str) -> Optional[int]:
        mapping = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        return mapping.get(word.lower(), None)

    # ----------------- Optional Ollama Local Model Integration -----------------

    def _extract_with_ollama(self, pages_dict: Dict[int, str], model_name: str) -> Optional[Dict[str, ExtractedField]]:
        """Queries local Ollama instance for structured JSON extraction."""
        try:
            sample_text = "\n\n".join([f"--- Page {p} ---\n{txt[:1200]}" for p, txt in list(pages_dict.items())[:6]])
            prompt = (
                "You are an expert Ind AS 116 lease accounting auditor. "
                "Analyze the following lease agreement text and extract key terms in strict JSON format.\n"
                "Keys required:\n"
                "- lessor_name (str)\n"
                "- lessee_name (str)\n"
                "- asset_description (str)\n"
                "- commencement_date (YYYY-MM-DD or string)\n"
                "- lease_term_months (integer)\n"
                "- fixed_rental_amount (number)\n"
                "- payment_frequency (Monthly, Quarterly, Annual)\n"
                "- escalation_pct (number)\n"
                "- security_deposit (number)\n"
                "- renewal_option (str)\n\n"
                f"Agreement text:\n{sample_text}\n\n"
                "Respond ONLY with valid JSON."
            )
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            res = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            if res.status_code == 200:
                raw_json = res.json().get("response", "{}")
                data = json.loads(raw_json)
                results: Dict[str, ExtractedField] = {}
                for k, v in data.items():
                    results[k] = ExtractedField(
                        key=k,
                        label=k.replace("_", " ").title(),
                        value=v,
                        confidence=0.91,
                        source_page="Local LLM",
                        source_snippet=f"Extracted by {model_name}",
                        requires_review=False
                    )
                return results
        except Exception:
            pass
        return None
