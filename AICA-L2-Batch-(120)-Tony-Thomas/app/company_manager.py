import os
import sys
import json
import datetime
from typing import Dict, Any, List, Optional

if getattr(sys, 'frozen', False):
    WORKSPACE_DIR = os.path.dirname(sys.executable)
else:
    WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGISTRY_FILE = os.path.join(WORKSPACE_DIR, "companies_registry.json")
COMPANIES_DIR = os.path.join(WORKSPACE_DIR, "companies_data")

os.makedirs(COMPANIES_DIR, exist_ok=True)

DEFAULT_COMPANIES = [
    {
        "id": "comp_1",
        "company_name": "Demo Retail Company",
        "legal_name": "Demo Retail Company LLC",
        "trn": "DEMO-TRN",
        "company_address": "Fictional Demo Address",
        "currency": "AED",
        "currency_symbol": "AED",
        "phone": "DEMO-PHONE",
        "email": "demo@example.com",
        "pin": "1234",
        "db_file": "erp_ledger.db",
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
]

def load_companies() -> List[Dict[str, Any]]:
    if not os.path.exists(REGISTRY_FILE):
        save_companies(DEFAULT_COMPANIES)
        return DEFAULT_COMPANIES
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                save_companies(DEFAULT_COMPANIES)
                return DEFAULT_COMPANIES
            return data
    except Exception:
        save_companies(DEFAULT_COMPANIES)
        return DEFAULT_COMPANIES

def save_companies(companies: List[Dict[str, Any]]) -> None:
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2)

def get_active_company() -> Dict[str, Any]:
    companies = load_companies()
    for c in companies:
        if c.get("is_active"):
            return c
    # Fallback to first
    companies[0]["is_active"] = True
    save_companies(companies)
    return companies[0]

def get_company_by_id(company_id: str) -> Optional[Dict[str, Any]]:
    companies = load_companies()
    for c in companies:
        if c.get("id") == company_id:
            return c
    return None

def verify_company_pin(company_id: str, pin: str) -> bool:
    comp = get_company_by_id(company_id)
    if not comp:
        return False
    return str(comp.get("pin", "")).strip() == str(pin).strip()

def set_active_company(company_id: str, pin: Optional[str] = None) -> Dict[str, Any]:
    companies = load_companies()
    target = None
    for c in companies:
        if c.get("id") == company_id:
            target = c
            break
    if not target:
        raise ValueError("Company not found")
    
    if pin is not None and not verify_company_pin(company_id, pin):
        raise ValueError("Invalid 4-digit PIN for this company")
    
    for c in companies:
        c["is_active"] = (c.get("id") == company_id)
    save_companies(companies)
    return target

def create_new_company(
    company_name: str,
    trn: str,
    pin: str,
    company_address: str = "Dubai, UAE",
    currency: str = "AED",
    currency_symbol: str = "AED",
    phone: str = "",
    email: str = ""
) -> Dict[str, Any]:
    pin_str = str(pin).strip()
    if len(pin_str) != 4 or not pin_str.isdigit():
        raise ValueError("Security PIN must be exactly 4 digits (e.g. 1234)")
    
    companies = load_companies()
    max_idx = 0
    for c in companies:
        cid = c.get("id", "")
        if cid.startswith("comp_"):
            try:
                num = int(cid.split("_")[1])
                if num > max_idx:
                    max_idx = num
            except (ValueError, IndexError):
                pass
    new_id = f"comp_{max_idx + 1}"
    db_file = os.path.join(COMPANIES_DIR, f"{new_id}.db")
    
    new_comp = {
        "id": new_id,
        "company_name": company_name.strip(),
        "legal_name": f"{company_name.strip()} LLC",
        "trn": trn.strip() or "TRN-PENDING",
        "company_address": company_address.strip() or "Dubai, UAE",
        "currency": currency.strip() or "AED",
        "currency_symbol": currency_symbol.strip() or "AED",
        "phone": phone.strip(),
        "email": email.strip(),
        "pin": pin_str,
        "db_file": db_file,
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    # Mark others as inactive
    for c in companies:
        c["is_active"] = False
    companies.append(new_comp)
    save_companies(companies)
    
    return new_comp

def update_company_profile(
    company_id: str,
    company_name: str,
    trn: str,
    company_address: str,
    currency: str,
    currency_symbol: str,
    phone: str = "",
    email: str = "",
    new_pin: Optional[str] = None
) -> Dict[str, Any]:
    companies = load_companies()
    target = None
    for c in companies:
        if c.get("id") == company_id:
            target = c
            break
    if not target:
        raise ValueError("Company not found")
        
    target["company_name"] = company_name.strip()
    target["legal_name"] = f"{company_name.strip()} LLC"
    target["trn"] = trn.strip()
    target["company_address"] = company_address.strip()
    target["currency"] = currency.strip()
    target["currency_symbol"] = currency_symbol.strip()
    target["phone"] = phone.strip()
    target["email"] = email.strip()
    
    if new_pin:
        p_str = str(new_pin).strip()
        if len(p_str) != 4 or not p_str.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        target["pin"] = p_str
        
    save_companies(companies)
    return target

def delete_company(company_id: str, pin: str) -> Dict[str, Any]:
    pin_str = str(pin).strip()
    if len(pin_str) != 4 or not pin_str.isdigit():
        raise ValueError("Security PIN must be exactly 4 digits.")

    companies = load_companies()
    if len(companies) <= 1:
        raise ValueError("Cannot delete the only registered company. At least one company must remain active.")

    target = None
    target_idx = -1
    for i, c in enumerate(companies):
        if c.get("id") == company_id:
            target = c
            target_idx = i
            break

    if not target:
        raise ValueError("Company not found.")

    if not verify_company_pin(company_id, pin_str):
        raise ValueError("Invalid 4-digit security PIN for this company. Deletion aborted.")

    was_active = target.get("is_active", False)
    deleted_name = target.get("company_name", "Company")
    db_file = target.get("db_file")

    # Remove company
    companies.pop(target_idx)

    # If deleted company was active, switch to first remaining company
    if was_active and len(companies) > 0:
        companies[0]["is_active"] = True

    save_companies(companies)

    # Clean up sqlite db file if it exists
    if db_file and os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Company '{deleted_name}' was successfully deleted.",
        "active_company_id": companies[0]["id"] if was_active and len(companies) > 0 else None
    }

