"""
AuditVault - Utilities
Indian Locale Formatting, Date Automation, Vault File System Management,
and Consolidation Engine.
"""

import os
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Union, Tuple, List, Dict

# Base Vault Storage Directory
BASE_VAULT_DIR = Path(__file__).resolve().parent / "AuditVault_Data"

def ensure_vault_directories():
    """Ensure baseline directories exist in the vault."""
    for sub in ["engagements", "consolidated", "engagement_letters", "idr", "rcm", "exports", "profile_pictures"]:
        (BASE_VAULT_DIR / sub).mkdir(parents=True, exist_ok=True)

ensure_vault_directories()


# =====================================================================
# 1. INDIAN DATE FORMATTING & PARSING
# =====================================================================

def format_indian_date(dt: Union[datetime, date, str, None]) -> str:
    """Format a date or datetime object into DD-MM-YYYY."""
    if dt is None:
        return ""
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%d-%m-%Y")
    
    # If already a string, normalize
    cleaned = str(dt).strip()
    parsed = parse_indian_date(cleaned)
    if parsed:
        return parsed.strftime("%d-%m-%Y")
    return cleaned


def parse_indian_date(input_str: Union[str, None]) -> Optional[date]:
    """
    Parse a date string in DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD,
    OR flexible 8-digit manual numeric entry (e.g. '04062026' -> 04-06-2026).
    """
    if not input_str:
        return None
    
    val = str(input_str).strip()
    
    # Support 8-digit manual numeric entry without separators: '04062026' -> '04-06-2026'
    if re.match(r"^\d{8}$", val):
        day = int(val[:2])
        month = int(val[2:4])
        year = int(val[4:])
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # Common separator formats
    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d %B %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def normalize_indian_date_input(input_str: str) -> str:
    """
    Auto-formats user text entry into DD-MM-YYYY format.
    E.g. typing '04062026' returns '04-06-2026'.
    """
    if not input_str:
        return ""
    cleaned = re.sub(r"[^\d]", "", input_str)
    if len(cleaned) == 8:
        # DDMMYYYY
        return f"{cleaned[:2]}-{cleaned[2:4]}-{cleaned[4:]}"
    return input_str


def current_indian_date_str() -> str:
    """Return today's date in DD-MM-YYYY."""
    return datetime.now().strftime("%d-%m-%Y")


def current_indian_timestamp_str() -> str:
    """Return current timestamp in DD-MM-YYYY HH:MM:SS."""
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def is_overdue(deadline_str: Union[str, None]) -> Tuple[bool, int]:
    """
    Check if a deadline in DD-MM-YYYY is past.
    Returns (is_overdue, days_difference).
    """
    if not deadline_str:
        return (False, 0)
    d = parse_indian_date(deadline_str)
    if not d:
        return (False, 0)
    today = date.today()
    diff = (today - d).days
    return (diff > 0, diff)


# =====================================================================
# 2. INDIAN NUMBERING & CURRENCY SYSTEM
# =====================================================================

def format_indian_number(number: Union[int, float, str, None]) -> str:
    """
    Formats a number using the Indian Numbering System (Lakhs, Crores).
    E.g. 1000000 -> "10,00,000"
         12345678 -> "1,23,45,678"
         5000 -> "5,000"
    """
    if number is None or number == "":
        return "0"
    
    try:
        if isinstance(number, str):
            # Clean existing commas, spaces, currency symbols
            number = float(re.sub(r"[^\d.-]", "", number))
    except (ValueError, TypeError):
        return str(number)

    is_negative = number < 0
    abs_num = abs(number)

    # Separate integer and decimal parts
    parts = f"{abs_num:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        # Last 3 digits (hundreds)
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining digits by 2s (thousands, lakhs, crores)
        pairs = []
        while len(remaining) > 2:
            pairs.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            pairs.insert(0, remaining)
        formatted_int = ",".join(pairs) + "," + last_three

    result = formatted_int
    if decimal_part != "00":
        result += f".{decimal_part}"
    
    return f"-{result}" if is_negative else result


def format_indian_currency(amount: Union[int, float, str, None]) -> str:
    """
    Format amount as Indian Rupee (₹).
    E.g. 1250000 -> "₹ 12,50,000"
    """
    formatted = format_indian_number(amount)
    return f"₹ {formatted}"


# =====================================================================
# 3. VAULT FILE SYSTEM ARCHITECTURE
# =====================================================================

def sanitize_folder_name(name: str) -> str:
    """Make string safe for folder/file names."""
    if not name:
        return "unnamed"
    return re.sub(r'[\\/*?:"<>|]', "_", str(name)).strip().replace(" ", "_")


def get_engagement_letter_dir(engagement_id: int) -> Path:
    """Path: /AuditVault_Data/engagement_letters/{engagement_id}/"""
    target = BASE_VAULT_DIR / "engagement_letters" / str(engagement_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_idr_storage_dir(engagement_id: int) -> Path:
    """Path: /AuditVault_Data/idr/{engagement_id}/"""
    target = BASE_VAULT_DIR / "idr" / str(engagement_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_rcm_storage_dir(engagement_id: int) -> Path:
    """Path: /AuditVault_Data/rcm/{engagement_id}/"""
    target = BASE_VAULT_DIR / "rcm" / str(engagement_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_line_item_storage_dir(engagement_id: int, client_name: str, line_item_id: str, date_str: Optional[str] = None) -> Path:
    """
    Folder structure auto-generated:
    /AuditVault_Data/engagements/{EngagementID}/{ClientName}/{LineItemID}/{DD-MM-YYYY}/
    A new dated sub-folder is auto-created each calendar day a file is modified.
    """
    safe_client = sanitize_folder_name(client_name)
    safe_line_item = sanitize_folder_name(line_item_id)
    version_date = date_str or current_indian_date_str()

    target = (
        BASE_VAULT_DIR
        / "engagements"
        / str(engagement_id)
        / safe_client
        / safe_line_item
        / version_date
    )
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_all_version_folders(engagement_id: int, client_name: str, line_item_id: str) -> List[Path]:
    """Retrieve all daily version subfolders for a line item, sorted reverse chronologically."""
    safe_client = sanitize_folder_name(client_name)
    safe_line_item = sanitize_folder_name(line_item_id)
    line_item_dir = BASE_VAULT_DIR / "engagements" / str(engagement_id) / safe_client / safe_line_item
    if not line_item_dir.exists():
        return []
    
    subdirs = [p for p in line_item_dir.iterdir() if p.is_dir()]
    # Sort by parsed date descending
    def sort_key(p: Path):
        d = parse_indian_date(p.name)
        return d if d else date.min

    return sorted(subdirs, key=sort_key, reverse=True)


def save_uploaded_file(uploaded_file, target_path: Path) -> int:
    """Save Streamlit UploadedFile to target path and return byte size."""
    with open(target_path, "wb") as f:
        file_bytes = uploaded_file.getbuffer()
        f.write(file_bytes)
        return len(file_bytes)


# =====================================================================
# 4. CONSOLIDATION AND ARCHIVAL ENGINE
# =====================================================================

def consolidate_engagement_files(
    engagement_id: int,
    client_name: str,
    engagement_code: str,
    delete_originals: bool = False
) -> Tuple[Path, Path, Dict[str, int]]:
    """
    STEP 7: Finalization and Consolidation
    Consolidates latest version of every file into:
    /AuditVault_Data/consolidated/{EngagementID}_{ClientName}/{LineItemID}/[final files]
    
    Creates a ZIP archive of the consolidated structure.
    Returns (consolidated_dir, zip_path, stats_dict).
    """
    safe_client = sanitize_folder_name(client_name)
    folder_name = f"{engagement_id}_{safe_client}"
    consolidated_base = BASE_VAULT_DIR / "consolidated" / folder_name
    
    # Clean prior consolidation if any
    if consolidated_base.exists():
        shutil.rmtree(consolidated_base)
    consolidated_base.mkdir(parents=True, exist_ok=True)

    engagement_dir = BASE_VAULT_DIR / "engagements" / str(engagement_id) / safe_client
    
    stats = {
        "line_items_processed": 0,
        "files_consolidated": 0,
        "total_bytes": 0
    }

    if engagement_dir.exists():
        # Iterate over each line item directory
        for line_item_dir in engagement_dir.iterdir():
            if not line_item_dir.is_dir():
                continue
            
            line_item_id = line_item_dir.name
            target_line_dir = consolidated_base / line_item_id
            target_line_dir.mkdir(parents=True, exist_ok=True)

            # Find all files across all version subfolders, keeping the latest version of each filename
            # Version folders sorted oldest to newest so newest overwrites
            version_subdirs = sorted(
                [p for p in line_item_dir.iterdir() if p.is_dir()],
                key=lambda p: parse_indian_date(p.name) or date.min
            )

            latest_files: Dict[str, Path] = {}
            for vdir in version_subdirs:
                for file_p in vdir.iterdir():
                    if file_p.is_file():
                        latest_files[file_p.name] = file_p

            for fname, src_file in latest_files.items():
                dest_file = target_line_dir / fname
                shutil.copy2(src_file, dest_file)
                stats["files_consolidated"] += 1
                stats["total_bytes"] += dest_file.stat().st_size

            stats["line_items_processed"] += 1

    # Include Engagement Letter if present
    eng_letter_dir = BASE_VAULT_DIR / "engagement_letters" / str(engagement_id)
    if eng_letter_dir.exists():
        for el_file in eng_letter_dir.iterdir():
            if el_file.is_file():
                el_dest_dir = consolidated_base / "00_Engagement_Letter"
                el_dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(el_file, el_dest_dir / el_file.name)

    # Build ZIP archive
    zip_filename = f"AuditVault_Consolidated_{engagement_code}_{safe_client}.zip"
    zip_path = BASE_VAULT_DIR / "exports" / zip_filename
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(consolidated_base):
            for file in files:
                file_full = Path(root) / file
                arcname = file_full.relative_to(consolidated_base)
                zipf.write(file_full, arcname)

    # Handle optional cleanup of original working files
    if delete_originals and engagement_dir.exists():
        shutil.rmtree(engagement_dir)

    return consolidated_base, zip_path, stats


# =====================================================================
# 5. IMMUTABLE AUDIT TRAIL LOGGING HELPER
# =====================================================================

def log_audit_action(
    session,
    action_type: str,
    target_entity: str,
    target_id: Union[str, int, None],
    description: str,
    user_id: int,
    acting_user_name: str,
    true_admin_id: Optional[int] = None,
    true_admin_name: Optional[str] = None,
    actor_role: Optional[str] = None,
    target_role: Optional[str] = None,
    target_name: Optional[str] = None,
    action_category: Optional[str] = None,
    rbac_rule_applied: Optional[str] = None,
    previous_state: Optional[dict] = None,
    new_state: Optional[dict] = None,
    extra_metadata: Optional[dict] = None,
    ip_address: str = "127.0.0.1"
):
    """
    Writes an append-only entry to the immutable Audit_Trail table
    and appends a replica entry to a local audit log file.
    """
    from models import AuditTrailEntry, User

    t_str = current_indian_timestamp_str()
    
    # If impersonating, enrich description
    display_desc = description
    if true_admin_id and true_admin_name:
        display_desc = f"[Admin '{true_admin_name}' acting as '{acting_user_name}'] {description}"

    if not actor_role:
        actor = session.get(User, user_id) if user_id else None
        actor_role = actor.role if actor else "System"

    inferred_category = action_category
    if not inferred_category:
        action_upper = action_type.upper()
        entity_upper = target_entity.upper()
        if "IMPERSONAT" in action_upper:
            inferred_category = "Admin Sessions"
        elif entity_upper == "USER" or "PASSWORD" in action_upper or "LOGIN" in action_upper:
            inferred_category = "Users"
        elif entity_upper == "TEAM" or "TEAM" in action_upper:
            inferred_category = "Teams"
        elif entity_upper == "CLIENT":
            inferred_category = "Clients"
        elif "ASSIGN" in action_upper or "ALLOCAT" in action_upper:
            inferred_category = "Allocations"
        else:
            inferred_category = "System"

    previous_json = json.dumps(previous_state, sort_keys=True, default=str) if previous_state is not None else None
    new_json = json.dumps(new_state, sort_keys=True, default=str) if new_state is not None else None
    metadata_json = json.dumps(extra_metadata, sort_keys=True, default=str) if extra_metadata is not None else None
    prior_entry = session.query(AuditTrailEntry).order_by(AuditTrailEntry.id.desc()).first()
    previous_hash = prior_entry.integrity_hash if prior_entry and prior_entry.integrity_hash else "GENESIS"

    entry = AuditTrailEntry(
        timestamp=datetime.utcnow(),
        timestamp_str=t_str,
        action_type=action_type,
        target_entity=target_entity,
        target_id=str(target_id) if target_id else "",
        description=display_desc,
        user_id=user_id,
        acting_user_name=acting_user_name,
        true_admin_id=true_admin_id,
        true_admin_name=true_admin_name,
        ip_address=ip_address,
        actor_role=actor_role,
        target_role=target_role,
        target_name=target_name,
        action_category=inferred_category,
        rbac_rule_applied=rbac_rule_applied,
        previous_state_json=previous_json,
        new_state_json=new_json,
        metadata_json=metadata_json,
        previous_hash=previous_hash,
    )
    session.add(entry)
    session.flush()
    integrity_payload = {
        "id": entry.id,
        "timestamp": entry.timestamp_str,
        "action": entry.action_type,
        "entity": entry.target_entity,
        "target_id": entry.target_id or "",
        "description": entry.description,
        "user_id": entry.user_id,
        "actor": entry.acting_user_name,
        "previous_hash": previous_hash,
    }
    entry.integrity_hash = hashlib.sha256(
        json.dumps(integrity_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    session.commit()

    # Immutable text log file replica
    log_file = BASE_VAULT_DIR / "audit_trail_immutable.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"[{t_str}] | {action_type} | {target_entity}:{target_id} | "
                f"User: {acting_user_name} | SHA256: {entry.integrity_hash} | {display_desc}\n"
            )
    except Exception:
        pass


def open_file_in_native_app(filepath: Union[str, Path]) -> bool:
    """
    Stretch goal: Open file in native OS application (e.g. MS Excel or Word).
    Uses os.startfile on Windows.
    """
    path_obj = Path(filepath)
    if not path_obj.exists():
        return False
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(path_obj))
            return True
        return False
    except Exception:
        return False
