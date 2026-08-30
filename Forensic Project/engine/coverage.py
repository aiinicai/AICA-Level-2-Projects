"""
Coverage and Methods Registry evaluator for Red Flag Engine.
Reads `rules/methods_registry.yaml` to determine method readiness, execution feasibility,
and document why not-implemented methods are blocked.
"""
import os
from typing import Dict, List, Any, Optional
import yaml
import pandas as pd

def load_methods_registry(registry_path: str = "rules/methods_registry.yaml") -> List[Dict[str, Any]]:
    if not os.path.exists(registry_path):
        return []
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def evaluate_coverage(
    num_years: int,
    num_records: int,
    has_opening_balances: bool,
    params: Optional[Dict[str, Any]] = None,
    registry_path: str = "rules/methods_registry.yaml"
) -> Dict[str, Any]:
    """
    Evaluate which forensic methods can run given the current engagement inputs.
    """
    params = params or {}
    registry = load_methods_registry(registry_path)
    
    implemented_methods = []
    not_implemented_methods = []
    
    for m in registry:
        m_id = m.get("id")
        name = m.get("name")
        status = m.get("status")
        reqs = m.get("requires", [])
        min_y = m.get("min_years", 1)
        min_rec = m.get("min_records", 1)
        rules = m.get("rules", [])
        
        if status == "implemented":
            can_run = True
            reasons = []
            
            if num_years < min_y:
                can_run = False
                reasons.append(f"Requires {min_y} years (found {num_years})")
            if num_records < min_rec:
                can_run = False
                reasons.append(f"Requires {min_rec} records (found {num_records})")
            if "peer_ratios" in reqs and not params.get("peer_ratios"):
                can_run = False
                reasons.append("Missing peer_ratios parameter")
            if "related_parties" in reqs and not params.get("related_parties"):
                can_run = False
                reasons.append("Missing related_parties parameter")
            if m_id in ["M-08", "M-10"] and not has_opening_balances:
                can_run = False
                reasons.append("Missing opening balances for cash flow")
                
            implemented_methods.append({
                "id": m_id,
                "name": name,
                "status": "Available" if can_run else "Unavailable",
                "can_run": can_run,
                "reasons": ", ".join(reasons) if reasons else "Ready",
                "rules": ", ".join(rules) if rules else "N/A"
            })
        else:
            not_implemented_methods.append({
                "id": m_id,
                "name": name,
                "status": "Declared (Not Implemented)",
                "blocked_by": m.get("blocked_by", ""),
                "unlocked_by": m.get("unlocked_by", "")
            })
            
    return {
        "implemented": implemented_methods,
        "not_implemented": not_implemented_methods,
        "available_count": sum(1 for m in implemented_methods if m["can_run"]),
        "total_implemented": len(implemented_methods),
        "total_declared": len(not_implemented_methods)
    }
