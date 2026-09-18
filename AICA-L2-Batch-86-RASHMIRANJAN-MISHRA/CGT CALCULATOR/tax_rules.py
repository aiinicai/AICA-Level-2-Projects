"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Tax Rule Engine Module
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import json
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional, List
from database import get_db_connection, log_audit


class TaxRuleMaster:
    """Manages configurable tax rules loaded from SQLite."""

    def __init__(self, conn=None):
        self.rules: Dict[str, Any] = {}
        self.load_rules(conn=conn)

    def load_rules(self, conn=None) -> None:
        """Loads all tax rules from the database into memory."""
        owns_conn = False
        if conn is None:
            conn = get_db_connection()
            owns_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT rule_key, rule_name, rule_value, value_type, category, description FROM tax_rule_master")
            rows = cursor.fetchall()
            for row in rows:
                key = row["rule_key"]
                v_type = row["value_type"]
                raw_val = row["rule_value"]
                if v_type == "float":
                    val = float(raw_val)
                elif v_type == "int":
                    val = int(raw_val)
                elif v_type == "json":
                    val = json.loads(raw_val)
                else:
                    val = raw_val
                self.rules[key] = val
        finally:
            if owns_conn:
                conn.close()

    def get(self, key: str, default: Any = None) -> Any:
        return self.rules.get(key, default)

    def update_rule(self, key: str, value: Any, conn=None) -> None:
        """Updates a specific rule in the database and reloads cache."""
        owns_conn = False
        if conn is None:
            conn = get_db_connection()
            owns_conn = True

        try:
            val_str = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE tax_rule_master
                SET rule_value = ?, updated_at = datetime('now')
                WHERE rule_key = ?
                """,
                (val_str, key),
            )
            conn.commit()
            self.load_rules(conn=conn)
            log_audit(
                action="UPDATE_TAX_RULE",
                entity_type="TAX_RULE_MASTER",
                entity_id=key,
                details=f"Updated rule '{key}' to '{val_str}'",
                conn=conn,
            )
        finally:
            if owns_conn:
                conn.close()


def parse_date(d: Any) -> date:
    """Helper to convert date or date string into date object."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(d.strip(), fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Unable to parse date: '{d}'")


def calculate_holding_period(acq_date: Any, sale_date: Any) -> Tuple[int, float]:
    """
    Calculates holding period in days and approx months.
    Returns (days, months).
    """
    d1 = parse_date(acq_date)
    d2 = parse_date(sale_date)

    if d1 > d2:
        raise ValueError(f"Date of Acquisition ({d1.strftime('%d/%m/%Y')}) cannot be after Date of Sale ({d2.strftime('%d/%m/%Y')}).")

    days = (d2 - d1).days
    # Approximate months using calendar difference
    months = (d2.year - d1.year) * 12 + (d2.month - d1.month) + ((d2.day - d1.day) / 30.0)
    return days, max(0.0, months)


def determine_asset_classification(
    asset_type: str,
    acq_date: Any,
    sale_date: Any,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> Tuple[str, float, int]:
    """
    Determines whether the asset is Short-Term (STCA) or Long-Term (LTCA).
    Thresholds:
      - Land, Building, Land & Building: 24 months
      - Unlisted Shares: 24 months
      - Listed Shares / Securities: 12 months
      - Other: 24 or 36 months (default 24)
    Returns: (classification: 'LONG_TERM' | 'SHORT_TERM', holding_months, threshold_months)
    """
    rules = tax_rules or TaxRuleMaster()
    days, months = calculate_holding_period(acq_date, sale_date)

    asset_type_clean = asset_type.strip()

    if asset_type_clean in ["Land", "Building", "Land & Building"]:
        threshold = rules.get("holding_period_immovable_months", 24)
    elif "Unlisted" in asset_type_clean:
        threshold = rules.get("holding_period_unlisted_shares_months", 24)
    elif "Listed" in asset_type_clean or asset_type_clean in ["Shares", "Securities"]:
        threshold = rules.get("holding_period_listed_shares_months", 12)
    else:
        threshold = rules.get("holding_period_immovable_months", 24)

    classification = "LONG_TERM" if months > threshold else "SHORT_TERM"
    return classification, months, threshold


def check_20_indexation_eligibility(
    asset_type: str,
    assessee_type: str,
    residential_status: str,
    acq_date: Any,
    sale_date: Any,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> Tuple[bool, str]:
    """
    Determines statutory eligibility for the 20% with indexation comparison under
    the second proviso to Section 112(1)(a) inserted by Finance (No. 2) Act, 2024.

    Statutory Requirements:
      1. Transfer must take place on or after 23rd July 2024 (statutory cut-off date).
      2. Asset must be Land, Building, or Land & Building (immovable property).
      3. Asset must have been acquired BEFORE 23rd July 2024.
      4. Assessee must be a Resident Individual or Resident HUF.
      5. Asset must qualify as Long-Term Capital Asset.

    Returns: (is_eligible: bool, explanation: str)
    """
    rules = tax_rules or TaxRuleMaster()
    d_acq = parse_date(acq_date)
    d_sale = parse_date(sale_date)

    cut_off_str = rules.get("statutory_cut_off_date", "2024-07-23")
    cut_off_date = parse_date(cut_off_str)

    # 1. Holding period check
    classification, months, threshold = determine_asset_classification(asset_type, acq_date, sale_date, rules)
    if classification == "SHORT_TERM":
        return False, (
            f"Asset is Short-Term Capital Asset (holding period {months:.1f} months <= {threshold} months threshold). "
            f"Comparison between 12.5% and 20% LTCG rates is only available for Long-Term Capital Assets."
        )

    # 2. Transfer date check
    if d_sale < cut_off_date:
        return False, (
            f"Date of Sale ({d_sale.strftime('%d/%m/%Y')}) is prior to 23rd July 2024. "
            f"Prior to 23-07-2024, the applicable statutory rate was 20% with indexation; "
            f"the 12.5% unindexed regime was introduced by Finance (No. 2) Act, 2024 w.e.f. 23-07-2024."
        )

    # 3. Asset Type check
    eligible_assets = rules.get("eligible_grandfathering_assets", ["Land", "Building", "Land & Building"])
    if asset_type not in eligible_assets:
        return False, (
            f"Asset type '{asset_type}' is not eligible for indexation comparison. "
            f"As per Finance (No. 2) Act, 2024 amendments to Section 112, indexation benefit is only preserved "
            f"for Land, Building, or Land & Building. For financial assets (shares/securities/others), tax is 12.5% without indexation."
        )

    # 4. Acquisition Date check (Acquired before 23-07-2024)
    if d_acq >= cut_off_date:
        return False, (
            f"Asset was acquired on or after 23rd July 2024 ({d_acq.strftime('%d/%m/%Y')}). "
            f"As per the proviso to Section 112, the option to calculate tax at 20% with indexation is strictly available "
            f"only for immovable properties acquired prior to 23rd July 2024. For properties acquired on or after 23-07-2024, "
            f"the tax is mandatory at 12.5% without indexation."
        )

    # 5. Assessee Type & Residential Status check
    eligible_assessees = rules.get("eligible_grandfathering_assessees", ["Individual", "HUF"])
    if assessee_type not in eligible_assessees:
        return False, (
            f"Assessee category '{assessee_type}' is not eligible for transitional indexation relief. "
            f"The second proviso to Section 112(1) confers the 20% indexed comparison exclusively upon Individuals and HUFs."
        )

    if residential_status.strip().lower() != "resident":
        return False, (
            f"Residential status is '{residential_status}'. "
            f"Transitional grandfathering relief under Section 112 is available only to Resident Individuals and HUFs."
        )

    return True, "Eligible for 12.5% without indexation vs 20% with indexation statutory comparison."


def get_pre_2001_adopted_cost(
    acq_date: Any,
    actual_cost: float,
    fmv_2001: float = 0.0,
    sdv_2001: Optional[float] = None,
    asset_type: str = "Land & Building",
    tax_rules: Optional[TaxRuleMaster] = None,
) -> Tuple[float, str]:
    """
    Computes adopted cost of acquisition under Section 55(2)(b):
    For assets acquired prior to 01-04-2001:
      - Assessee has option to substitute Fair Market Value (FMV) as of 01-04-2001.
      - In case of land/building, FMV as of 01-04-2001 cannot exceed Stamp Duty Value (SDV) as of 01-04-2001.
      - Adopted Cost = max(Actual Cost, min(FMV, SDV if provided else FMV)).
    Returns: (adopted_cost, explanation)
    """
    rules = tax_rules or TaxRuleMaster()
    d_acq = parse_date(acq_date)
    cut_off_str = rules.get("pre_2001_cut_off_date", "2001-04-01")
    cut_off_date = parse_date(cut_off_str)

    if d_acq >= cut_off_date:
        return actual_cost, "Acquired on or after 01-04-2001. Actual cost of acquisition considered."

    # Asset acquired before 01-04-2001
    effective_fmv = fmv_2001
    if asset_type in ["Land", "Building", "Land & Building"] and sdv_2001 is not None and sdv_2001 > 0:
        if fmv_2001 > sdv_2001:
            effective_fmv = sdv_2001
            explanation = f"FMV as of 01-04-2001 (₹{fmv_2001:,.2f}) restricted to Stamp Duty Value (₹{sdv_2001:,.2f}) under Section 55(2)(b)."
        else:
            explanation = f"FMV as of 01-04-2001 (₹{fmv_2001:,.2f}) is within Stamp Duty Value."
    else:
        explanation = f"FMV as of 01-04-2001 (₹{fmv_2001:,.2f}) adopted."

    adopted_cost = max(actual_cost, effective_fmv)
    if adopted_cost > actual_cost:
        explanation += f" Higher of actual cost (₹{actual_cost:,.2f}) and 01-04-2001 value adopted: ₹{adopted_cost:,.2f}."
    else:
        explanation += f" Actual cost (₹{actual_cost:,.2f}) is higher than 01-04-2001 value and adopted."

    return adopted_cost, explanation


def calculate_surcharge_rate(
    total_taxable_gains: float,
    manual_surcharge_rate: Optional[float] = None,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> float:
    """
    Determines applicable surcharge rate for Section 112 LTCG.
    Under Income-tax Act, surcharge on Section 112 LTCG for individuals/HUFs is capped at 15%.
    """
    if manual_surcharge_rate is not None:
        return min(float(manual_surcharge_rate), 15.0)

    rules = tax_rules or TaxRuleMaster()
    cap = rules.get("surcharge_cap_ltcg_112", 15.0)
    slab1_limit = rules.get("surcharge_slab_1_limit", 5000000.0)
    slab1_rate = rules.get("surcharge_slab_1_rate", 10.0)
    slab2_limit = rules.get("surcharge_slab_2_limit", 10000000.0)
    slab2_rate = rules.get("surcharge_slab_2_rate", 15.0)

    if total_taxable_gains > slab2_limit:
        rate = slab2_rate
    elif total_taxable_gains > slab1_limit:
        rate = slab1_rate
    else:
        rate = 0.0

    return min(rate, cap)
