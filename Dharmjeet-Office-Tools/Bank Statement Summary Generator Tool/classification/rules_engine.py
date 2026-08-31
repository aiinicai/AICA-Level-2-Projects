"""Rule-Based Transaction Classification Engine.
Classifies transactions into nature taxonomy and maintains an audit trail.
"""

import os
import yaml
import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from classification.profile_manager import load_client_profile

DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "classification_rules.yaml"
)

def load_classification_rules(rules_path: Optional[str] = None) -> Dict[str, Any]:
    """Load default classification rules from YAML."""
    path = rules_path or DEFAULT_RULES_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"receipts": [], "payments": []}
        except Exception as e:
            print(f"Error loading classification rules: {e}")
    return {"receipts": [], "payments": []}

def classify_single_transaction(
    row: pd.Series,
    rules: Dict[str, Any],
    client_profile: Optional[Dict[str, Any]] = None
) -> Tuple[str, float, str]:
    """
    Classify a single transaction row.
    Returns: (nature_category, confidence_score, audit_rule_tag)
    """
    is_credit = float(row.get("credit_amount", 0.0) or 0.0) > 0
    narration = str(row.get("description", "") or "").upper()
    party = str(row.get("counterparty_name", "") or "").strip()
    mode = str(row.get("mode", "") or "").upper()
    
    # 1. Check Client Profile Learned Party Mappings (Highest Priority)
    if client_profile and "party_mappings" in client_profile:
        mappings = client_profile["party_mappings"]
        if party and party in mappings:
            return mappings[party], 1.0, f"Client Profile Mapping for '{party}'"
        # Check case-insensitive
        for p_map, nat in mappings.items():
            if party and p_map.upper() == party.upper():
                return nat, 1.0, f"Client Profile Mapping for '{p_map}'"

    # Select rules set (Receipts vs Payments)
    rule_set = rules.get("receipts", []) if is_credit else rules.get("payments", [])
    
    # 2. Iterate through rules
    for rule in rule_set:
        category = rule.get("category", "")
        keywords = rule.get("keywords", [])
        rule_modes = [m.upper() for m in rule.get("modes", [])]
        
        # Check keyword matches in narration or party
        for kw in keywords:
            kw_upper = kw.upper()
            if kw_upper in narration or (party and kw_upper in party.upper()):
                # Bonus if mode also aligns
                if rule_modes and mode in rule_modes:
                    return category, 0.95, f"Rule: {category} [Keyword: '{kw}', Mode: {mode}]"
                return category, 0.85, f"Rule: {category} [Keyword: '{kw}']"
                
    # 3. Mode-specific fallbacks
    if is_credit:
        if mode == "INT":
            return "Interest Income", 0.90, "Mode Rule: INT"
        if mode in ("CASH", "CDM", "BNA"):
            return "Cash Deposit", 0.90, f"Mode Rule: {mode}"
        return "Unidentified Credit", 0.20, "Unclassified Credit Entry"
    else:
        if mode == "ATM":
            return "Cash Withdrawal", 0.90, "Mode Rule: ATM"
        if mode == "BANK_CHG":
            return "Bank Charges", 0.90, "Mode Rule: BANK_CHG"
        if mode == "CHQ":
            return "Cheque Issued (Unidentified)", 0.50, "Mode Rule: CHQ"
        if mode in ("CASH", "CDM"):
            return "Cash Withdrawal", 0.85, f"Mode Rule: {mode}"
        return "Unidentified Debit", 0.20, "Unclassified Debit Entry"

def classify_transactions(
    df: pd.DataFrame,
    client_name: Optional[str] = None,
    rules_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Classify all transactions in a normalized DataFrame.
    Adds 'nature', 'confidence_score', and 'audit_trail' columns.
    """
    if df is None or df.empty:
        return df

    rules = load_classification_rules(rules_path)
    client_profile = load_client_profile(client_name) if client_name else None

    natures = []
    confidences = []
    audit_trails = []

    for _, row in df.iterrows():
        nature, conf, audit = classify_single_transaction(row, rules, client_profile)
        natures.append(nature)
        confidences.append(conf)
        audit_trails.append(audit)

    df_classified = df.copy()
    df_classified["nature"] = natures
    df_classified["confidence_score"] = confidences
    df_classified["audit_trail"] = audit_trails

    return df_classified
