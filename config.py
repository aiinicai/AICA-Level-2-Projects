"""
Configuration and Form Mapping Layer for TDS & TCS Certificate PDF Auto-Renamer.
Supports certificates under:
- Income-tax Act, 1961 (Form 16, 16A, 16B, 16C, 16D, 16E, 27D)
- Income-tax Act, 2025 (Form 130, 131, 132, 133)
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

# ==============================================================================
# 1. GOVERNING ACT DEFINITIONS
# ==============================================================================
ACT_1961 = "Income-tax Act, 1961"
ACT_2025 = "Income-tax Act, 2025"

CATEGORY_TDS = "TDS Certificate"
CATEGORY_TCS = "TCS Certificate"

# ==============================================================================
# 2. CONFIGURABLE FORM REGISTRY & MAPPING LAYER
# ==============================================================================
FORM_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # Income-tax Act, 1961 Forms
    # --------------------------------------------------------------------------
    "16": {
        "form_name": "Form 16",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "Certificate for Tax Deducted at Source on Salary (Section 203)",
        "target_party_label": "Employee",
        "section_ref": "203",
        "rule_ref": "Rule 31(1)(a)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16\b(?!A|B|C|D|E)",
            r"FORM\s*16\b(?!A|B|C|D|E)",
            r"Certificate\s+under\s+section\s+203.*?salary",
            r"rule\s+31\s*\(\s*1\s*\)\s*\(\s*a\s*\)",
        ]
    },
    "16A": {
        "form_name": "Form 16A",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "Certificate for Tax Deducted at Source on Payments other than Salary (Section 203)",
        "target_party_label": "Deductee",
        "section_ref": "203",
        "rule_ref": "Rule 31(1)(b)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16A\b",
            r"FORM\s*[-_]?\s*16A\b",
            r"Certificate\s+under\s+section\s+203.*?payments\s+other\s+than\s+salary",
            r"rule\s+31\s*\(\s*1\s*\)\s*\(\s*b\s*\)",
        ]
    },
    "16B": {
        "form_name": "Form 16B",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Sale of Immovable Property (Section 194-IA)",
        "target_party_label": "Transferor (Seller / Deductee)",
        "section_ref": "194-IA",
        "rule_ref": "Rule 31(1)(c)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16B\b",
            r"FORM\s*[-_]?\s*16B\b",
            r"section\s+194\s*[-]?\s*IA\b",
            r"rule\s+31\s*\(\s*1\s*\)\s*\(\s*c\s*\)",
        ]
    },
    "16C": {
        "form_name": "Form 16C",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Rent paid by Individuals/HUF (Section 194-IB)",
        "target_party_label": "Payee (Landlord / Deductee)",
        "section_ref": "194-IB",
        "rule_ref": "Rule 31(1)(d)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16C\b",
            r"FORM\s*[-_]?\s*16C\b",
            r"section\s+194\s*[-]?\s*IB\b",
            r"rule\s+31\s*\(\s*1\s*\)\s*\(\s*d\s*\)",
        ]
    },
    "16D": {
        "form_name": "Form 16D",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Payments by certain Individuals/HUF (Section 194M)",
        "target_party_label": "Payee (Contractor/Professional)",
        "section_ref": "194M",
        "rule_ref": "Rule 31(1)(e)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16D\b",
            r"FORM\s*[-_]?\s*16D\b",
            r"section\s+194\s*M\b",
            r"rule\s+31\s*\(\s*1\s*\)\s*\(\s*e\s*\)",
        ]
    },
    "16E": {
        "form_name": "Form 16E",
        "act": ACT_1961,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Transfer of Virtual Digital Assets (Section 194S)",
        "target_party_label": "Transferor (Seller of VDA)",
        "section_ref": "194S",
        "rule_ref": "Rule 31(1)(f)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*16E\b",
            r"FORM\s*[-_]?\s*16E\b",
            r"section\s+194\s*S\b",
            r"Virtual\s+Digital\s+Assets?",
        ]
    },
    "27D": {
        "form_name": "Form 27D",
        "act": ACT_1961,
        "category": CATEGORY_TCS,
        "description": "Certificate for Tax Collected at Source (Section 206C)",
        "target_party_label": "Collectee (Buyer)",
        "section_ref": "206C",
        "rule_ref": "Rule 37D",
        "detection_regex": [
            r"FORM\s+NO\.?\s*27D\b",
            r"FORM\s*[-_]?\s*27D\b",
            r"Certificate\s+under\s+section\s+206C",
            r"rule\s+37\s*D\b",
            r"Tax\s+Collected\s+at\s+Source",
        ]
    },

    # --------------------------------------------------------------------------
    # Income-tax Act, 2025 Forms
    # --------------------------------------------------------------------------
    "130": {
        "form_name": "Form 130",
        "act": ACT_2025,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Salary under Income-tax Act, 2025 (Corresponds to Form 16)",
        "target_party_label": "Employee",
        "section_ref": "395(1)",
        "rule_ref": "Rule 215",
        "detection_regex": [
            r"FORM\s+NO\.?\s*130\b",
            r"FORM\s*[-_]?\s*130\b",
            r"Form\s+130\b",
            r"section\s+395\s*\(\s*1\s*\)",
            r"section\s+392\b",
        ]
    },
    "131": {
        "form_name": "Form 131",
        "act": ACT_2025,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Non-Salary payments under Income-tax Act, 2025 (Corresponds to Form 16A)",
        "target_party_label": "Deductee",
        "section_ref": "395(4)",
        "rule_ref": "Rule 215(1)",
        "detection_regex": [
            r"FORM\s+NO\.?\s*131\b",
            r"FORM\s*[-_]?\s*131\b",
            r"Form\s+131\b",
            r"section\s+395\s*\(\s*4\s*\)",
            r"rule\s+215\s*\(\s*1\s*\)",
            r"section\s+397\s*\(\s*3\s*\)\s*\(\s*b\s*\)",
        ]
    },
    "132": {
        "form_name": "Form 132",
        "act": ACT_2025,
        "category": CATEGORY_TDS,
        "description": "TDS Certificate on Immovable Property / Specified Transactions under Income-tax Act, 2025 (Corresponds to Form 16B/16C/16D)",
        "target_party_label": "Payee / Transferor",
        "section_ref": "395",
        "rule_ref": "Rule 215",
        "detection_regex": [
            r"FORM\s+NO\.?\s*132\b",
            r"FORM\s*[-_]?\s*132\b",
            r"Form\s+132\b",
        ]
    },
    "133": {
        "form_name": "Form 133",
        "act": ACT_2025,
        "category": CATEGORY_TCS,
        "description": "TCS Certificate under Income-tax Act, 2025 (Corresponds to Form 27D)",
        "target_party_label": "Collectee",
        "section_ref": "398",
        "rule_ref": "Rule 217",
        "detection_regex": [
            r"FORM\s+NO\.?\s*133\b",
            r"FORM\s*[-_]?\s*133\b",
            r"Form\s+133\b",
            r"section\s+398\b",
            r"rule\s+217\b",
        ]
    }
}

# ==============================================================================
# 3. RENAMING TEMPLATES
# ==============================================================================
NAMING_TEMPLATES = [
    {
        "id": "name_only",
        "name": "Deductee Name only (Default)",
        "template": "{DeducteeName}",
        "example": "RAJESH KUMAR SHARMA.pdf"
    },
    {
        "id": "name_form_fy_q",
        "name": "Deductee Name + Form + Quarter + FY",
        "template": "{DeducteeName}_{FormType}_{Quarter}_{FinancialYear}",
        "example": "RAJESH KUMAR SHARMA_Form 16A_Q2_2024-25.pdf"
    },
    {
        "id": "name_pan_form",
        "name": "Deductee Name + PAN + Form",
        "template": "{DeducteeName}_{PAN}_{FormType}",
        "example": "RAJESH KUMAR SHARMA_ABCDE1234F_Form 16A.pdf"
    },
    {
        "id": "name_pan_q_fy",
        "name": "Deductee Name + PAN + Quarter + FY",
        "template": "{DeducteeName}_{PAN}_{Quarter}_{FinancialYear}",
        "example": "RAJESH KUMAR SHARMA_ABCDE1234F_Q2_2024-25.pdf"
    },
    {
        "id": "form_name_q_fy",
        "name": "Form + Deductee Name + Quarter + FY",
        "template": "{FormType}_{DeducteeName}_{Quarter}_{FinancialYear}",
        "example": "Form 16A_RAJESH KUMAR SHARMA_Q2_2024-25.pdf"
    },
    {
        "id": "name_certno",
        "name": "Deductee Name + Certificate No",
        "template": "{DeducteeName}_{CertificateNo}",
        "example": "RAJESH KUMAR SHARMA_TR123456789.pdf"
    }
]

# ==============================================================================
# 4. DUPLICATE & COLLISION POLICIES
# ==============================================================================
COLLISION_AUTO_INCREMENT = "auto_increment"      # append (1), (2), etc.
COLLISION_DISAMBIGUATE = "disambiguate"          # append _{Quarter}_{PAN}
COLLISION_SKIP = "skip"                          # skip renaming on collision
COLLISION_OVERWRITE = "overwrite"                # overwrite existing (not recommended)

# ==============================================================================
# 5. EXECUTION MODES
# ==============================================================================
MODE_RENAME_IN_PLACE = "rename_in_place"
MODE_COPY_TO_FOLDER = "copy_to_folder"
MODE_MOVE_TO_FOLDER = "move_to_folder"

# ==============================================================================
# 6. APPLICATION SETTINGS DATACLASS & PERSISTENCE
# ==============================================================================
@dataclass
class AppConfig:
    naming_template: str = "{DeducteeName}"
    collision_policy: str = COLLISION_AUTO_INCREMENT
    execution_mode: str = MODE_RENAME_IN_PLACE
    output_folder: str = ""
    include_subfolders: bool = False
    enable_ocr_fallback: bool = True
    tesseract_path: str = ""
    sanitize_uppercase: bool = True
    max_filename_length: int = 120
    custom_replacements: Dict[str, str] = None

    def __post_init__(self):
        if self.custom_replacements is None:
            self.custom_replacements = {}

    @classmethod
    def get_config_file_path(cls) -> Path:
        app_dir = Path.home() / ".tds_renamer"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "settings.json"

    @classmethod
    def load(cls) -> "AppConfig":
        config_path = cls.get_config_file_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception:
                pass
        return cls()

    def save(self):
        config_path = self.get_config_file_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
