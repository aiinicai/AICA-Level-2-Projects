from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ENTITY_FORM_OPTIONS, SMALL_COMPANY_THRESHOLD_HISTORY,
    CARO_PRIVATE_THRESHOLD_PUC_RESERVES, CARO_PRIVATE_THRESHOLD_BORROWINGS,
    CARO_PRIVATE_THRESHOLD_REVENUE, IFC_PRIVATE_TURNOVER_THRESHOLD,
    IFC_PRIVATE_BORROWINGS_THRESHOLD,
)

def _num(v) -> float:
    try:
        if v is None or str(v).strip() == "":
            return 0.0
        return float(str(v).replace(",", "").strip())
    except Exception:
        return 0.0

def _bool(v) -> bool:
    return str(v).strip().lower() in {"yes","true","1","y"}

def _date(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v
    s = str(v or "").strip()
    # Accept common Word/report date forms such as "31st March, 2026".
    import re
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)
    s = s.replace(",", "")
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%B %d, %Y","%d %B %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def assessment_date_from_year_ending(year_ending: str, report_date: str = "") -> str:
    d = _date(year_ending)
    if d:
        return d.strftime("%Y-%m-%d")
    d = _date(report_date)
    if d:
        return d.strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")

def small_company_thresholds(assessment_date: str) -> Tuple[float,float,str]:
    d = _date(assessment_date) or datetime.now()
    for start, end, puc, turnover, source in SMALL_COMPANY_THRESHOLD_HISTORY:
        sd = datetime.strptime(start, "%Y-%m-%d")
        ed = datetime.strptime(end, "%Y-%m-%d") if end else None
        if d >= sd and (ed is None or d <= ed):
            return puc, turnover, source
    return 10.0, 100.0, "MCA G.S.R. 880(E)"

@dataclass
class Facts:
    entity_form: str
    listed: bool = False
    in_process_listing: bool = False
    bank: bool = False
    financial_institution: bool = False
    insurance: bool = False
    section8: bool = False
    opc: bool = False
    holding: bool = False
    subsidiary: bool = False
    holding_subsidiary_of_non_msme: bool = False
    special_act: bool = False
    paid_up_capital: float = 0.0
    reserves_surplus: float = 0.0
    turnover_prior: float = 0.0
    revenue_current: float = 0.0
    borrowings_max: float = 0.0
    net_worth: float = 0.0
    indas_required: bool = False
    accounting_framework: str = "AS – Companies"
    noncompany_as_category: str = ""
    legacy_level: str = ""

    @property
    def private_company(self):
        return self.entity_form == "private_ltd"

    @property
    def public_company(self):
        return self.entity_form in {"public_ltd_unlisted","public_ltd_listed","producer_company","nidhi_company","government_company"}

def derive_small_company(f: Facts, assessment_date: str) -> Tuple[bool,str]:
    puc_limit, turnover_limit, source = small_company_thresholds(assessment_date)
    if not f.private_company and f.entity_form != "opc":
        # OPC is a private company in legal character for many Companies Act
        # provisions but is captured separately for transparent reporting.
        if f.entity_form != "opc":
            return False, "Small company is not applicable to this entity form."
    if f.listed or f.in_process_listing:
        return False, "Listed / in-process-of-listing condition prevents small-company classification."
    if f.holding or f.subsidiary:
        return False, "Holding/subsidiary companies are excluded from small-company definition."
    if f.section8 or f.special_act:
        return False, "Section 8 / special Act exclusion."
    ok = f.paid_up_capital <= puc_limit and f.turnover_prior <= turnover_limit
    if ok:
        return True, f"Paid-up capital ≤ ₹{puc_limit:g} crore and preceding-year turnover ≤ ₹{turnover_limit:g} crore; thresholds effective {source}."
    return False, f"Threshold not met: PUC ₹{f.paid_up_capital:g} crore / turnover ₹{f.turnover_prior:g} crore; limits ₹{puc_limit:g} crore / ₹{turnover_limit:g} crore."

def derive_noncompany_category(f: Facts, assessment_date: str) -> Tuple[str,str]:
    # Current ICAI scheme effective 1 April 2024: MSME vs Large.
    if f.entity_form in {"private_ltd","public_ltd_unlisted","public_ltd_listed","opc","section8","producer_company","nidhi_company","government_company","foreign_company","other_company"}:
        return "", "Not a non-company entity."
    if f.listed or f.in_process_listing or f.bank or f.financial_institution or f.insurance:
        return "Large", "Listed/listing, bank, financial institution or insurance entities are Large under current ICAI non-company AS criteria."
    if f.turnover_prior > 250 or f.borrowings_max > 50 or f.holding or f.subsidiary:
        return "Large", "Current ICAI criterion: turnover > ₹250 crore, borrowings > ₹50 crore, or holding/subsidiary of a non-MSME."
    return "MSME", "Current ICAI criterion: non-listed, non-bank/financial institution/insurance, turnover ≤ ₹250 crore, borrowings ≤ ₹50 crore and not holding/subsidiary of a non-MSME."

def legacy_level_2021(f: Facts) -> Tuple[str,str]:
    if f.listed or f.in_process_listing or f.bank or f.financial_institution or f.insurance or f.turnover_prior > 250 or f.borrowings_max > 50 or f.holding or f.subsidiary:
        return "Level I", "Legacy ICAI 2021 classification."
    if f.turnover_prior > 50 or f.borrowings_max > 10:
        return "Level II", "Legacy ICAI 2021 classification."
    if f.turnover_prior > 10 or f.borrowings_max > 2:
        return "Level III", "Legacy ICAI 2021 classification."
    return "Level IV", "Legacy ICAI 2021 classification."

def derive_corporate_smc(f: Facts) -> Tuple[str,str]:
    """
    SMC under Companies (Accounting Standards) Rules, 2021 is distinct from
    'small company' under section 2(85). This function is only a screening aid.
    """
    is_company = f.entity_form not in {"proprietorship","partnership","llp","trust","other_noncorporate"}
    if not is_company:
        return "N/A", "Not a company."
    if f.indas_required:
        return "N/A", "Ind AS applicability takes precedence; SMC classification under Companies AS Rules is not used."
    if f.listed or f.in_process_listing or f.bank or f.financial_institution or f.insurance:
        return "Non-SMC", "Listed/listing, banking, financial institution and insurance entities are outside the SMC definition."
    if f.turnover_prior <= 250 and f.borrowings_max <= 50 and not f.holding_subsidiary_of_non_msme:
        return "SMC", "System screening: turnover ≤ ₹250 crore, borrowings ≤ ₹50 crore and no holding/subsidiary-of-non-SMC condition identified."
    return "Non-SMC", "One or more SMC conditions are not met."

def derive_applicability(f: Facts, assessment_date: str, small_company: bool) -> List[Dict[str,Any]]:
    results = []

    def add(code, requirement, system, rationale, source, version="2026.08"):
        results.append({
            "RuleCode":code, "Requirement":requirement, "SystemResult":"Applicable" if system else "Not Applicable",
            "FinalResult":"Applicable" if system else "Not Applicable", "Override":"No",
            "Rationale":rationale, "Source":source, "RuleVersion":version
        })

    is_company = f.entity_form not in {"proprietorship","partnership","llp","trust","other_noncorporate"}
    is_private = f.private_company or f.entity_form == "opc"
    is_public = f.public_company or f.listed

    corporate_smc, corporate_smc_reason = derive_corporate_smc(f)
    add("AS_SMC","Small and Medium Sized Company (SMC) under Companies AS Rules, 2021",
        corporate_smc=="SMC", corporate_smc_reason,
        "Companies (Accounting Standards) Rules, 2021 – SMC definition")

    # CARO 2020
    caro = False
    if is_company:
        if f.bank or f.insurance or f.section8 or f.opc or small_company:
            caro = False
            reason = "CARO 2020 expressly excludes banking, insurance, Section 8, OPC and small companies."
        elif f.private_company and f.reserves_surplus + f.paid_up_capital <= CARO_PRIVATE_THRESHOLD_PUC_RESERVES and f.borrowings_max <= CARO_PRIVATE_THRESHOLD_BORROWINGS and f.revenue_current <= CARO_PRIVATE_THRESHOLD_REVENUE and not f.holding and not f.subsidiary:
            caro = False
            reason = "Specified private-company exemption: paid-up capital plus reserves/surplus ≤ ₹1 crore, borrowings ≤ ₹1 crore and revenue ≤ ₹10 crore; not holding/subsidiary of a public company."
        else:
            caro = True
            reason = "Company is not within the listed CARO 2020 exemptions; final applicability remains subject to the complete Order."
    else:
        caro = False
        reason = "CARO 2020 is a Companies Act order and is not applicable to non-company entities."
    add("CARO_2020","Companies (Auditor's Report) Order, 2020",caro,reason,"CARO 2020, paragraph 1")

    # IFC reporting under section 143(3)(i)
    if not is_company:
        ifc = False
        reason = "Section 143(3)(i) is a Companies Act reporting requirement and is not being applied to non-company entities by this engine."
    elif f.opc or small_company:
        ifc = False
        reason = "Private-company exemption covers OPC and small company."
    elif f.private_company and f.turnover_prior < IFC_PRIVATE_TURNOVER_THRESHOLD and f.borrowings_max < IFC_PRIVATE_BORROWINGS_THRESHOLD:
        ifc = False
        reason = "Private-company exemption: turnover < ₹50 crore and aggregate borrowings < ₹25 crore."
    else:
        ifc = True
        reason = "No private-company exemption identified; section 143(3)(i) reporting is recommended."
    add("IFC_143_3_I","Section 143(3)(i) – reporting on internal financial controls with reference to financial statements",ifc,reason,"Companies Act section 143(3)(i) + private-company exemption notification")

    # Current ICAI non-company AS scheme: AS 3, AS 17 and AS 24 are
    # not applicable to MSMEs in their entirety.
    is_noncompany = f.entity_form in {"proprietorship","partnership","trust","other_noncorporate","llp"}
    if is_noncompany and f.noncompany_as_category == "MSME":
        add("AS_3","AS 3 – Cash Flow Statements",False,
            "Current ICAI non-company AS scheme: AS 3 is not applicable to MSMEs in its entirety.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_17","AS 17 – Segment Reporting",False,
            "Current ICAI non-company AS scheme: AS 17 is not applicable to MSMEs in its entirety.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_24","AS 24 – Discontinuing Operations",False,
            "Current ICAI non-company AS scheme: AS 24 is not applicable to MSMEs in its entirety.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        cond_small = f.turnover_prior <= 50 and f.borrowings_max <= 10 and not f.holding_subsidiary_of_non_msme
        add("AS_18","AS 18 – Related Party Disclosures",not cond_small,
            "AS 18 is not applicable in entirety to qualifying MSMEs under the turnover / borrowing / holding-subsidiary criteria." if not cond_small else
            "System indicates the conditional AS 18 exemption is available.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_28","AS 28 – Impairment of Assets",not cond_small,
            "AS 28 is not applicable in entirety to qualifying MSMEs under the turnover / borrowing / holding-subsidiary criteria.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_15_RELAXATION","AS 15 – Employee Benefits: MSME relaxations",True,
            "MSMEs have specified relaxations from certain AS 15 requirements.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_19_RELAXATION","AS 19 – Leases: MSME disclosure relaxations",True,
            "MSMEs have specified disclosure relaxations under AS 19.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_22_RELAXATION","AS 22 – Income Taxes: MSME relaxation",True,
            "MSMEs have specified AS 22 relaxation provisions.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_29_RELAXATION","AS 29 – Provisions: MSME disclosure relaxations",True,
            "MSMEs have specified disclosure relaxations under AS 29.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        cashflow = False
        reason = "AS 3 is not applicable to current MSME non-company entities."
    elif is_noncompany:
        add("AS_3","AS 3 – Cash Flow Statements",True,
            "Large non-company entities comply in full with applicable Accounting Standards.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_17","AS 17 – Segment Reporting",True,
            "Large non-company entities comply in full with applicable Accounting Standards.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        add("AS_24","AS 24 – Discontinuing Operations",True,
            "Large non-company entities comply in full with applicable Accounting Standards.",
            "ICAI revised non-company AS criteria, effective 1 April 2024")
        cashflow = True
        reason = "Large non-company entity: AS 3 applies."
    else:
        cashflow = not (f.opc or small_company)
        reason = "Companies Act financial statement exemption applies to OPC/small company; otherwise cash flow statement is generally part of financial statements."
    add("CASH_FLOW","Cash Flow Statement / AS 3",cashflow,reason,"Companies Act section 2(40) / AS 3 applicability framework")
    # Schedule III
    schedule3 = is_company
    add("SCHEDULE_III","Schedule III presentation / disclosures",schedule3,
        "Schedule III applies to companies to the extent prescribed for their class; sector-specific Schedule III requirements may need further review.",
        "Companies Act section 129 / Schedule III")

    # Accounting framework
    if f.indas_required:
        af = "Ind AS"
    elif is_company:
        af = "Accounting Standards under Companies (Accounting Standards) Rules, 2021"
    elif f.entity_form == "llp":
        af = "LLP Accounting Standards / applicable ICAI framework – professional confirmation required"
    else:
        af = "ICAI Accounting Standards for non-company entities"
    add("ACCOUNTING_FRAMEWORK","Applicable accounting framework",True,
        f"System-selected framework: {af}. This is a classification aid and does not replace regulatory confirmation.",
        "Applicable Companies Act / ICAI accounting framework")

    return results

def build_facts(data: Dict[str,Any]) -> Facts:
    return Facts(
        entity_form=data.get("entity_form","private_ltd"),
        listed=_bool(data.get("listed")),
        in_process_listing=_bool(data.get("in_process_listing")),
        bank=_bool(data.get("bank")),
        financial_institution=_bool(data.get("financial_institution")),
        insurance=_bool(data.get("insurance")),
        section8=_bool(data.get("section8")),
        opc=_bool(data.get("opc")) or data.get("entity_form")=="opc",
        holding=_bool(data.get("holding")),
        subsidiary=_bool(data.get("subsidiary")),
        holding_subsidiary_of_non_msme=_bool(data.get("holding_subsidiary_of_non_msme")),
        special_act=_bool(data.get("special_act")),
        paid_up_capital=_num(data.get("paid_up_capital")),
        reserves_surplus=_num(data.get("reserves_surplus")),
        turnover_prior=_num(data.get("turnover_prior")),
        revenue_current=_num(data.get("revenue_current")),
        borrowings_max=_num(data.get("borrowings_max")),
        net_worth=_num(data.get("net_worth")),
        indas_required=_bool(data.get("indas_required")),
        accounting_framework=data.get("accounting_framework","AS – Companies"),
        noncompany_as_category=data.get("noncompany_as_category",""),
        legacy_level=data.get("legacy_level",""),
    )

def classify(data: Dict[str,Any]) -> Dict[str,Any]:
    f = build_facts(data)
    assessment_date = data.get("assessment_date") or assessment_date_from_year_ending(data.get("year_ending",""),data.get("report_date",""))
    small, small_reason = derive_small_company(f, assessment_date)
    current_nc, current_nc_reason = derive_noncompany_category(f, assessment_date)
    legacy, legacy_reason = legacy_level_2021(f)
    # Professional/manual inputs can be supplied separately.
    if data.get("professional_small_company") in {"yes","no"}:
        small = data["professional_small_company"] == "yes"
        small_reason = "Professional override applied."
    if data.get("professional_noncompany_category"):
        current_nc = data["professional_noncompany_category"]
        current_nc_reason = "Professional override applied."
    if data.get("professional_legacy_level"):
        legacy = data["professional_legacy_level"]
        legacy_reason = "Professional override applied."

    corporate_smc, corporate_smc_reason = derive_corporate_smc(f)
    results = derive_applicability(f, assessment_date, small)
    return {
        "facts":f, "assessment_date":assessment_date,
        "small_company":small, "small_company_reason":small_reason,
        "noncompany_category":current_nc, "noncompany_category_reason":current_nc_reason,
        "legacy_level":legacy, "legacy_level_reason":legacy_reason,
        "results":results,
        "thresholds":small_company_thresholds(assessment_date),
        "corporate_smc": corporate_smc,
        "corporate_smc_reason": corporate_smc_reason,
    }
