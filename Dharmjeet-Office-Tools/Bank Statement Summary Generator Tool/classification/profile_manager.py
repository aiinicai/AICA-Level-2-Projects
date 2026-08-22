"""Client Profile and Memory Management.
Stores client-specific classification rules, party mappings, and custom thresholds.
"""

import os
import yaml
from typing import Dict, Any, List, Optional

CLIENT_PROFILES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "client_profiles"
)

def ensure_profiles_dir():
    os.makedirs(CLIENT_PROFILES_DIR, exist_ok=True)

def list_client_profiles() -> List[str]:
    """Return a list of all saved client profile names."""
    ensure_profiles_dir()
    profiles = []
    for f in os.listdir(CLIENT_PROFILES_DIR):
        if f.endswith(".yaml") or f.endswith(".yml"):
            profiles.append(os.path.splitext(f)[0])
    return sorted(profiles)

def load_client_profile(client_name: str) -> Dict[str, Any]:
    """Load a client's profile YAML or return default structure."""
    ensure_profiles_dir()
    safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_', '-')).strip()
    file_path = os.path.join(CLIENT_PROFILES_DIR, f"{safe_name}.yaml")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data or {}
        except Exception as e:
            print(f"Error loading client profile {client_name}: {e}")
            
    return {
        "client_name": client_name,
        "pan": "",
        "gstin": "",
        "declared_turnover": 0.0,
        "custom_thresholds": {},
        "party_mappings": {},  # {"Party Name": "Business Receipts/Sales"}
        "custom_rules": []
    }

def save_client_profile(profile_data: Dict[str, Any]) -> bool:
    """Save client profile data to YAML."""
    ensure_profiles_dir()
    client_name = profile_data.get("client_name", "Default_Client")
    safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_', '-')).strip()
    file_path = os.path.join(CLIENT_PROFILES_DIR, f"{safe_name}.yaml")
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Error saving client profile {client_name}: {e}")
        return False

def add_party_mapping(client_name: str, party_name: str, nature: str) -> bool:
    """Map a specific counterparty to a nature category for future runs."""
    profile = load_client_profile(client_name)
    if "party_mappings" not in profile:
        profile["party_mappings"] = {}
    profile["party_mappings"][party_name.strip()] = nature.strip()
    return save_client_profile(profile)
