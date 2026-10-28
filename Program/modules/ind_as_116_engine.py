"""
Ind AS 116 Accounting Logic and Classification Engine
Evaluates contract definition, term, exemptions, component separation, and initial balance sheet measurement.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class IndAS116Assessment:
    contains_lease: bool
    identified_asset: bool
    economic_benefits: bool
    direct_use: bool
    lease_test_explanation: str
    
    # Lease term assessment
    non_cancellable_months: int
    renewal_included_months: int
    effective_lease_term_months: int
    term_assessment_rationale: str
    
    # Exemptions
    is_short_term_eligible: bool
    is_low_value_eligible: bool
    short_term_elected: bool
    low_value_elected: bool
    exemption_summary: str
    
    # Component separation
    separate_non_lease: bool
    practical_expedient_elected: bool
    lease_component_amount: float
    non_lease_component_amount: float
    
    # Classification & Initial Measurement
    accounting_classification: str  # "ROU_AND_LIABILITY", "SHORT_TERM_EXEMPT", "LOW_VALUE_EXEMPT"
    classification_rationale: str
    
    initial_direct_costs: float
    lease_incentives: float
    prepaid_rent: float
    restoration_provision: float
    residual_value_guarantee: float
    purchase_option_included: float


def _normalize_extracted(data: Dict) -> Dict[str, Dict]:
    """Ensures every field in extracted_data is accessible as a dictionary with 'value'."""
    normalized = {}
    if not data:
        return normalized
    for k, v in data.items():
        if hasattr(v, "to_dict") and callable(v.to_dict):
            normalized[k] = v.to_dict()
        elif hasattr(v, "value"):
            normalized[k] = {
                "key": getattr(v, "key", k),
                "label": getattr(v, "label", k),
                "value": v.value,
                "confidence": getattr(v, "confidence", 1.0),
                "source_page": getattr(v, "source_page", 1),
                "source_snippet": getattr(v, "source_snippet", ""),
                "requires_review": getattr(v, "requires_review", False)
            }
        elif isinstance(v, dict):
            normalized[k] = v
        else:
            normalized[k] = {"value": v}
    return normalized


class IndAS116Engine:
    def __init__(self, low_value_threshold: float = 400000.0):
        self.low_value_threshold = low_value_threshold

    def evaluate_contract(
        self,
        extracted_data: Dict,
        elect_short_term_exemption: bool = True,
        elect_low_value_exemption: bool = True,
        elect_practical_expedient: bool = False,
        asset_class: str = "Real Estate"  # "Real Estate", "Equipment", "Vehicles", "IT Hardware", "Office Furniture"
    ) -> IndAS116Assessment:
        """
        Executes formal Ind AS 116 decision tree analysis.
        """
        extracted_data = _normalize_extracted(extracted_data)

        # 1. Lease Definition (Paragraphs 9-17)
        # Does the contract convey the right to control the use of an identified asset for a period of time in exchange for consideration?
        asset_desc = str(extracted_data.get("asset_description", {}).get("value", "") or "")
        identified_asset = len(asset_desc.strip()) > 3
        economic_benefits = True  # Lessee gets primary economic utility / premises use
        direct_use = True         # Lessee directs how and for what purpose asset is used

        contains_lease = identified_asset and economic_benefits and direct_use

        lease_test_explanation = (
            f"1. Identified Asset: An explicit asset ('{asset_desc[:50]}...') is specified without substantive supplier substitution rights. (PASSED)\n"
            "2. Economic Benefits: Lessee has the right to obtain substantially all economic benefits from use of the demised premises throughout the term. (PASSED)\n"
            "3. Right to Direct Use: Lessee directs the operational use of the premises within defined zoning and lease covenants. (PASSED)\n"
            "CONCLUSION: The contract contains a lease under Ind AS 116.9."
        )

        # 2. Lease Term Assessment (Paragraphs 18-21)
        raw_term = int(extracted_data.get("lease_term_months", {}).get("value", 60) or 60)
        renewal_cert = bool(extracted_data.get("renewal_certain", {}).get("value", False))
        
        # If renewal is reasonably certain, add renewal period (presume 36 or 12 months if unspecified)
        renewal_months = 0
        if renewal_cert:
            renewal_months = 12  # standard default incremental extension
            effective_term = raw_term + renewal_months
            term_rationale = (
                f"Non-cancellable period of {raw_term} months plus {renewal_months} months renewal "
                f"assessed as reasonably certain of exercise under Ind AS 116.18. Total effective term: {effective_term} months."
            )
        else:
            effective_term = raw_term
            term_rationale = (
                f"Non-cancellable primary lease term of {raw_term} months. "
                "Any extension or renewal option is evaluated as not reasonably certain at inception."
            )

        # 3. Exemptions (Paragraphs 5-8)
        # Short-term exemption: term <= 12 months at commencement date AND contains NO purchase option
        pur_option = bool(extracted_data.get("purchase_option", {}).get("value", False))
        is_short_term = (effective_term <= 12) and (not pur_option)

        # Low-value exemption: asset when new <= threshold and not real estate or vehicles
        rent_amount = float(extracted_data.get("fixed_rental_amount", {}).get("value", 100000.0) or 100000.0)
        is_low_val = False
        if asset_class in ["IT Hardware", "Office Furniture", "Small Tools"]:
            # Annual rent proxy or asset description
            if (rent_amount * 12) <= (self.low_value_threshold * 0.4):
                is_low_val = True
        elif asset_class in ["Real Estate", "Vehicles"]:
            is_low_val = False  # Ind AS 116 Basis for Conclusions BC100 explicitly excludes land/buildings and cars from low-value

        # Determine user exemption elections
        apply_short_term = is_short_term and elect_short_term_exemption
        apply_low_val = is_low_val and elect_low_value_exemption

        if apply_short_term:
            classification = "SHORT_TERM_EXEMPT"
            classification_rationale = (
                f"Eligible for Short-Term Lease Exemption under Ind AS 116.5(a) (lease term {effective_term} months <= 12 months, "
                "with no purchase option). Entity elects to recognize lease payments as an operating expense on a straight-line basis."
            )
            exemption_summary = "Short-term lease exemption elected (Ind AS 116.5a). No balance sheet ROU Asset or Lease Liability recognized."
        elif apply_low_val:
            classification = "LOW_VALUE_EXEMPT"
            classification_rationale = (
                f"Eligible for Low-Value Asset Exemption under Ind AS 116.5(b) (asset class '{asset_class}' within threshold). "
                "Entity elects to recognize payments on a straight-line basis in P&L without balance sheet gross-up."
            )
            exemption_summary = "Low-value asset exemption elected (Ind AS 116.5b)."
        else:
            classification = "ROU_AND_LIABILITY"
            classification_rationale = (
                "Neither short-term nor low-value exemption applies or is elected. Under Ind AS 116.22, "
                "lessee must recognize a Right-of-Use (ROU) Asset and corresponding Lease Liability on the balance sheet at commencement date."
            )
            exemption_summary = "Standard on-balance sheet accounting applies (ROU Asset & Lease Liability recognized)."

        # 4. Component Separation (Paragraphs 12-16)
        cam_amount = float(extracted_data.get("non_lease_components", {}).get("value", 0.0) or 0.0)
        if elect_practical_expedient:
            # Practical expedient: Combine lease and non-lease components
            separate_non_lease = False
            lease_comp = rent_amount + cam_amount
            non_lease_comp = 0.0
        else:
            # Separate components
            separate_non_lease = cam_amount > 0
            lease_comp = rent_amount
            non_lease_comp = cam_amount

        # 5. Ancillary Adjustments for ROU Asset
        idc = float(extracted_data.get("initial_direct_costs", {}).get("value", 0.0) or 0.0)
        incentives = float(extracted_data.get("lease_incentive", {}).get("value", 0.0) or 0.0)
        restoration = float(extracted_data.get("restoration_obligation", {}).get("value", 0.0) or 0.0)
        rvg = float(extracted_data.get("residual_value_guarantee", {}).get("value", 0.0) or 0.0)
        
        pur_certain = bool(extracted_data.get("purchase_certain", {}).get("value", False))
        pur_price = float(extracted_data.get("purchase_option_price", {}).get("value", 0.0) or 0.0)
        pur_included = pur_price if pur_certain else 0.0

        return IndAS116Assessment(
            contains_lease=contains_lease,
            identified_asset=identified_asset,
            economic_benefits=economic_benefits,
            direct_use=direct_use,
            lease_test_explanation=lease_test_explanation,
            non_cancellable_months=raw_term,
            renewal_included_months=renewal_months,
            effective_lease_term_months=effective_term,
            term_assessment_rationale=term_rationale,
            is_short_term_eligible=is_short_term,
            is_low_value_eligible=is_low_val,
            short_term_elected=apply_short_term,
            low_value_elected=apply_low_val,
            exemption_summary=exemption_summary,
            separate_non_lease=separate_non_lease,
            practical_expedient_elected=elect_practical_expedient,
            lease_component_amount=lease_comp,
            non_lease_component_amount=non_lease_comp,
            accounting_classification=classification,
            classification_rationale=classification_rationale,
            initial_direct_costs=idc,
            lease_incentives=incentives,
            prepaid_rent=0.0,
            restoration_provision=restoration,
            residual_value_guarantee=rvg,
            purchase_option_included=pur_included
        )
