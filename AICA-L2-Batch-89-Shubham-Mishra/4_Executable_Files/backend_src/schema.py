"""
Client Master schema contract, copied field-for-field from the existing L1 app
(CA_PracticeOS_Compliance.html: downloadClientTemplate() and mapClientImportRow()).
Agent 1 must produce rows that import cleanly via the app's "Upload Client Master"
feature, so this file is the single source of truth for field names and order.
"""
import re

CLIENT_MASTER_HEADERS = [
    "Client Name", "Entity Type", "PAN", "GSTIN", "CIN / LLPIN",
    "Contact Person", "Mobile", "Email", "Address", "State / UT",
    "SEZ Applicable",
]

ENTITY_TYPES = [
    "Individual", "Proprietorship", "Partnership", "LLP",
    "Private Limited Company", "Public Limited Company",
    "Trust", "Society", "Other",
]

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh",
    "Puducherry",
]

GSTIN_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "32": "Kerala",
    "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh",
}


def normalize_entity_type(raw: str) -> str:
    if not raw:
        return "Individual"
    raw_lower = raw.strip().lower()
    for option in ENTITY_TYPES:
        if option.lower() == raw_lower:
            return option
    aliases = {
        "pvt ltd": "Private Limited Company",
        "private limited": "Private Limited Company",
        "pvt. ltd.": "Private Limited Company",
        "public ltd": "Public Limited Company",
        "proprietor": "Proprietorship",
        "sole proprietorship": "Proprietorship",
        "huf": "Individual",
    }
    return aliases.get(raw_lower, "Other")


def validate_client_row(row: dict) -> dict:
    """Returns {field: [issue, ...]} for fields that fail validation. Empty dict = clean."""
    issues = {}
    if not row.get("name", "").strip():
        issues["name"] = ["Client Name is required"]
    if row.get("pan") and not PAN_RE.match(row["pan"]):
        issues["pan"] = [f"PAN '{row['pan']}' does not match the expected format AAAAA9999A"]
    if row.get("gstin") and not GSTIN_RE.match(row["gstin"]):
        issues["gstin"] = [f"GSTIN '{row['gstin']}' does not match the expected 15-character format"]
    if row.get("gstin") and row.get("pan") and len(row["gstin"]) == 15:
        if row["gstin"][2:12] != row["pan"]:
            issues.setdefault("gstin", []).append("GSTIN does not embed the extracted PAN")
    entity = row.get("entity", "")
    if entity not in ENTITY_TYPES:
        issues["entity"] = [f"Entity Type '{entity}' is not one of the app's allowed values"]
    return issues


def to_client_master_row(row: dict) -> list:
    """Order the fields exactly as CLIENT_MASTER_HEADERS expects, for CSV export."""
    return [
        row.get("name", ""),
        row.get("entity", ""),
        row.get("pan", ""),
        row.get("gstin", ""),
        row.get("cin", ""),
        row.get("contact", ""),
        row.get("mobile", ""),
        row.get("email", ""),
        row.get("address", ""),
        row.get("state", ""),
        "Yes" if row.get("sez") else "No",
    ]
