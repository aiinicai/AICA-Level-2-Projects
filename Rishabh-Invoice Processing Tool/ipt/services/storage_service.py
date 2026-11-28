"""Local document folder layout:

IPT_DATA/Companies/<Company>_<id>/FY_2026_27/{Invoices,GSTR2B,Purchase_Register,XML,Reports}
"""
from __future__ import annotations

import re
from pathlib import Path

FY_SUBFOLDERS = ("Invoices", "GSTR2B", "Purchase_Register", "XML", "Reports")


def safe_folder_name(name: str, company_id: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:60] or "Company"
    return f"{cleaned}_{company_id}"


def company_dir(data_root: Path, folder_name: str) -> Path:
    return data_root / "Companies" / folder_name


def fy_dir(data_root: Path, folder_name: str, fy_label: str) -> Path:
    return company_dir(data_root, folder_name) / f"FY_{fy_label.replace('-', '_')}"


def ensure_fy_folders(data_root: Path, folder_name: str, fy_label: str) -> Path:
    base = fy_dir(data_root, folder_name, fy_label)
    for sub in FY_SUBFOLDERS:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base
