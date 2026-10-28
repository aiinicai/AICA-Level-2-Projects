"""
Fixed Asset Register & Depreciation Calculator
Compliant with:
  1. Companies Act, 2013 (Schedule II) - Supports both SLM and WDV methods,
     pro-rata day-wise calculation, and 5% default residual value cap.
  2. Income Tax Act, 1961 (Section 32) - Supports WDV Block of Assets rates,
     automatic 180-day rule (>=180 days full rate, <180 days half rate in year
     of acquisition), and optional Additional Depreciation (20% / 10%).

Runs independently on any Windows system using only Python Standard Library
modules (tkinter, json, csv, datetime, math, os). Requires zero external pip
packages and works reliably across local drives, OneDrive, and network folders.
"""

import csv
from datetime import date, datetime, timedelta
import json
import math
import os
import sys
from typing import Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TKINTER = True
except ImportError:
    tk = None  # type: ignore
    filedialog = None  # type: ignore
    messagebox = None  # type: ignore
    ttk = None  # type: ignore
    HAS_TKINTER = False


# ---------------------------------------------------------------------------
# Standard Presets as per Schedule II (Companies Act, 2013) & Income Tax Act
# ---------------------------------------------------------------------------
ASSET_CATEGORIES: Dict[str, Dict[str, float]] = {
    "Buildings (Factory)": {
        "useful_life": 30.0,
        "residual_pct": 5.0,
        "it_rate": 10.0,
    },
    "Buildings (Office / Non-Factory)": {
        "useful_life": 60.0,
        "residual_pct": 5.0,
        "it_rate": 10.0,
    },
    "Plant & Machinery (General)": {
        "useful_life": 15.0,
        "residual_pct": 5.0,
        "it_rate": 15.0,
    },
    "Furniture & Fittings (General)": {
        "useful_life": 10.0,
        "residual_pct": 5.0,
        "it_rate": 10.0,
    },
    "Office Equipment": {
        "useful_life": 5.0,
        "residual_pct": 5.0,
        "it_rate": 15.0,
    },
    "Computers & Laptops (End-User)": {
        "useful_life": 3.0,
        "residual_pct": 5.0,
        "it_rate": 40.0,
    },
    "Servers & Networks": {
        "useful_life": 6.0,
        "residual_pct": 5.0,
        "it_rate": 40.0,
    },
    "Motor Cars (Non-Hire)": {
        "useful_life": 8.0,
        "residual_pct": 5.0,
        "it_rate": 15.0,
    },
    "Motor Buses / Lorries / Commercial": {
        "useful_life": 8.0,
        "residual_pct": 5.0,
        "it_rate": 30.0,
    },
    "Intangible Assets / Software": {
        "useful_life": 5.0,
        "residual_pct": 0.0,
        "it_rate": 25.0,
    },
    "Custom Category": {
        "useful_life": 10.0,
        "residual_pct": 5.0,
        "it_rate": 15.0,
    },
}


# ---------------------------------------------------------------------------
# Financial Year & Date Utilities
# ---------------------------------------------------------------------------
def get_fy_bounds(d: date) -> Tuple[int, date, date]:
    """
    Returns (fy_start_year, fy_start_date, fy_end_date) for an Indian Financial Year
    (April 1 to March 31).
    """
    if d.month >= 4:
        start_yr = d.year
    else:
        start_yr = d.year - 1
    return start_yr, date(start_yr, 4, 1), date(start_yr + 1, 3, 31)


def format_fy(start_yr: int) -> str:
    """Formats e.g. 2026 as 'FY 2026-27'."""
    return f"FY {start_yr}-{str(start_yr + 1)[-2:]}"


def parse_iso_date(date_str: str) -> date:
    """Parses YYYY-MM-DD or DD-MM-YYYY string into a date object."""
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD or DD-MM-YYYY.")


# ---------------------------------------------------------------------------
# Depreciation Calculation Engine (Companies Act 2013 & Income Tax Act 1961)
# ---------------------------------------------------------------------------
def calculate_depreciation_schedule(asset: Dict) -> List[Dict]:
    """
    Generates a year-by-year depreciation schedule from the Financial Year of
    acquisition up to the completion of useful life (and corresponding IT Act WDV).
    """
    cost = float(asset["cost"])
    put_to_use_date = parse_iso_date(asset.get("put_to_use_date") or asset["acq_date"])
    useful_life_years = float(asset["useful_life"])
    residual_val = float(asset["residual_value"])
    ca_method = asset.get("ca_method", "SLM").upper()
    it_rate = float(asset["it_rate"])
    add_dep_flag = bool(int(asset.get("it_additional_dep", 0)))

    if cost <= 0 or useful_life_years <= 0:
        return []

    depreciable_amount = max(0.0, cost - residual_val)
    annual_slm_dep = depreciable_amount / useful_life_years

    # Companies Act WDV annual rate: r = 1 - (Residual / Cost) ^ (1 / Useful_Life)
    if ca_method == "WDV":
        eff_residual = residual_val if residual_val > 0 else cost * 0.05
        if eff_residual >= cost:
            ca_wdv_rate = 0.0
        else:
            ca_wdv_rate = (1.0 - math.pow(eff_residual / cost, 1.0 / useful_life_years)) * 100.0
    else:
        ca_wdv_rate = (annual_slm_dep / cost) * 100.0 if cost > 0 else 0.0

    # Useful life end date from put_to_use_date
    try:
        whole_years = int(useful_life_years)
        rem_days = int(round((useful_life_years - whole_years) * 365.25))
        end_life_date = date(
            put_to_use_date.year + whole_years, put_to_use_date.month, put_to_use_date.day
        ) + timedelta(days=rem_days - 1)
    except ValueError:
        # Handle Feb 29 leap year edge case
        end_life_date = put_to_use_date + timedelta(days=int(round(useful_life_years * 365.25)) - 1)

    total_life_days = (end_life_date - put_to_use_date).days + 1
    start_fy_yr, _, _ = get_fy_bounds(put_to_use_date)
    max_fys = int(math.ceil(useful_life_years)) + 2

    ca_opening_wdv = cost
    ca_accum_dep = 0.0
    remaining_life_days = total_life_days

    it_opening_wdv = cost
    it_accum_dep = 0.0
    balance_half_add_dep_pending = False

    schedule: List[Dict] = []

    for idx in range(max_fys):
        fy_yr = start_fy_yr + idx
        fy_start = date(fy_yr, 4, 1)
        fy_end = date(fy_yr + 1, 3, 31)
        days_in_fy = (fy_end - fy_start).days + 1

        if remaining_life_days <= 0 and idx >= int(math.ceil(useful_life_years)):
            break

        # --- 1. COMPANIES ACT, 2013 CALCULATION ---
        if remaining_life_days > 0 and ca_opening_wdv > residual_val + 0.005:
            eff_start = max(put_to_use_date, fy_start)
            eff_end = min(end_life_date, fy_end)
            if eff_start <= eff_end:
                ca_days_used = (eff_end - eff_start).days + 1
            else:
                ca_days_used = 0

            if ca_days_used > 0:
                if ca_method == "SLM":
                    ca_dep = annual_slm_dep * (ca_days_used / days_in_fy)
                else:
                    ca_dep = ca_opening_wdv * (ca_wdv_rate / 100.0) * (ca_days_used / days_in_fy)

                max_allowable_ca_dep = max(0.0, ca_opening_wdv - residual_val)
                if (remaining_life_days - ca_days_used) <= 0:
                    ca_dep = max_allowable_ca_dep
                else:
                    ca_dep = min(ca_dep, max_allowable_ca_dep)

                ca_dep = round(ca_dep, 2)
                remaining_life_days -= ca_days_used
            else:
                ca_dep = 0.0
        else:
            ca_days_used = 0
            ca_dep = 0.0

        if ca_days_used == 0 and idx > 0 and remaining_life_days <= 0:
            break

        ca_accum_dep = round(ca_accum_dep + ca_dep, 2)
        ca_closing_wdv = round(max(residual_val if cost > residual_val else 0.0, cost - ca_accum_dep), 2)

        # --- 2. INCOME TAX ACT, 1961 CALCULATION ---
        it_days_used = 0
        it_rule_note = "Full Rate (100%)"
        if idx == 0:
            it_days_used = (fy_end - put_to_use_date).days + 1 if put_to_use_date <= fy_end else 0
            if it_days_used <= 0:
                eff_it_rate = 0.0
                eff_add_rate = 0.0
                it_rule_note = "Not Put to Use"
            elif it_days_used < 180:
                eff_it_rate = it_rate * 0.5
                eff_add_rate = 10.0 if add_dep_flag else 0.0
                balance_half_add_dep_pending = add_dep_flag
                it_rule_note = f"<180 Days ({it_days_used}d) - Half Rate"
            else:
                eff_it_rate = it_rate
                eff_add_rate = 20.0 if add_dep_flag else 0.0
                it_rule_note = f">=180 Days ({it_days_used}d) - Full Rate"

            it_normal_dep = round(it_opening_wdv * (eff_it_rate / 100.0), 2)
            it_add_dep = round(cost * (eff_add_rate / 100.0), 2)
        else:
            it_days_used = days_in_fy
            it_normal_dep = round(it_opening_wdv * (it_rate / 100.0), 2)
            if idx == 1 and balance_half_add_dep_pending:
                it_add_dep = round(cost * 0.10, 2)
                it_rule_note = "Full Rate + Bal 10% Add. Dep"
                balance_half_add_dep_pending = False
            else:
                it_add_dep = 0.0

        it_total_dep = min(it_opening_wdv, round(it_normal_dep + it_add_dep, 2))
        it_accum_dep = round(it_accum_dep + it_total_dep, 2)
        it_closing_wdv = round(max(0.0, it_opening_wdv - it_total_dep), 2)

        schedule.append({
            "year_no": idx + 1,
            "fy_start_yr": fy_yr,
            "fy_label": format_fy(fy_yr),
            "ca_days": ca_days_used,
            "ca_rate_pct": round(ca_wdv_rate, 2),
            "ca_opening_wdv": round(ca_opening_wdv, 2),
            "ca_depreciation": ca_dep,
            "ca_accum_dep": ca_accum_dep,
            "ca_closing_wdv": ca_closing_wdv,
            "it_days": it_days_used,
            "it_rule_note": it_rule_note,
            "it_opening_wdv": round(it_opening_wdv, 2),
            "it_normal_dep": it_normal_dep,
            "it_add_dep": it_add_dep,
            "it_total_dep": it_total_dep,
            "it_accum_dep": it_accum_dep,
            "it_closing_wdv": it_closing_wdv,
            "dep_diff": round(ca_dep - it_total_dep, 2),
        })

        ca_opening_wdv = ca_closing_wdv
        it_opening_wdv = it_closing_wdv

    return schedule


# ---------------------------------------------------------------------------
# Persistent Storage Layer (JSON-backed, works on local, OneDrive & network drives)
# ---------------------------------------------------------------------------
class DuplicateAssetCodeError(ValueError):
    """Raised when attempting to insert or update an asset with an existing asset_code."""


class AssetDatabase:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            db_path = os.path.join(base_dir, "fixed_assets_register.json")
        self.db_path = db_path
        self._data: Dict = {"next_id": 1, "assets": []}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict) and "assets" in loaded:
                        self._data = loaded
            except Exception:
                self._data = {"next_id": 1, "assets": []}
        else:
            self._data = {
                "next_id": 11,
                "assets": [
    {
        "id": 1,
        "asset_code": "FA-0001",
        "asset_name": "Industrial Factory Shed & Civil Works",
        "category": "Buildings (Factory)",
        "location": "Peenya Industrial Area - Block A",
        "vendor": "Shapoorji Industrial Constructions",
        "invoice_no": "SIC/22-23/014",
        "acq_date": "2022-05-15",
        "put_to_use_date": "2022-06-01",
        "cost": 4500000.0,
        "useful_life": 30.0,
        "residual_pct": 5.0,
        "residual_value": 225000.0,
        "ca_method": "SLM",
        "it_rate": 10.0,
        "it_additional_dep": 0,
        "remarks": "Factory building put to use >= 180 days in FY 2022-23"
    },
    {
        "id": 2,
        "asset_code": "FA-0002",
        "asset_name": "Corporate Office Floor Unit",
        "category": "Buildings (Office / Non-Factory)",
        "location": "Kochi InfoPark - Tower 2",
        "vendor": "Prestige Commercial Estates",
        "invoice_no": "PCE/22-23/089",
        "acq_date": "2022-09-01",
        "put_to_use_date": "2022-09-15",
        "cost": 8000000.0,
        "useful_life": 60.0,
        "residual_pct": 5.0,
        "residual_value": 400000.0,
        "ca_method": "SLM",
        "it_rate": 10.0,
        "it_additional_dep": 0,
        "remarks": "Admin office RCC structure (60 yrs Schedule II useful life)"
    },
    {
        "id": 3,
        "asset_code": "FA-0003",
        "asset_name": "5-Axis CNC Vertical Machining Center",
        "category": "Plant & Machinery (General)",
        "location": "Plant Shopfloor A",
        "vendor": "Bharat Machine Tools Ltd",
        "invoice_no": "BMT/23-24/108",
        "acq_date": "2023-05-10",
        "put_to_use_date": "2023-05-20",
        "cost": 1850000.0,
        "useful_life": 15.0,
        "residual_pct": 5.0,
        "residual_value": 92500.0,
        "ca_method": "SLM",
        "it_rate": 15.0,
        "it_additional_dep": 1,
        "remarks": "Put to use >= 180 days in FY 2023-24; 20% Add. Dep u/s 32(1)(iia)"
    },
    {
        "id": 4,
        "asset_code": "FA-0004",
        "asset_name": "Automated Laser Cutting & Bending Line",
        "category": "Plant & Machinery (General)",
        "location": "Plant Shopfloor B",
        "vendor": "Trumpf India Pvt Ltd",
        "invoice_no": "TIPL/23-24/412",
        "acq_date": "2023-11-10",
        "put_to_use_date": "2023-11-18",
        "cost": 1200000.0,
        "useful_life": 15.0,
        "residual_pct": 5.0,
        "residual_value": 60000.0,
        "ca_method": "WDV",
        "it_rate": 15.0,
        "it_additional_dep": 1,
        "remarks": "< 180 days in FY 2023-24 (Half rate + 10% Add. Dep in Yr 1, bal 10% in Yr 2)"
    },
    {
        "id": 5,
        "asset_code": "FA-0005",
        "asset_name": "Dell PowerEdge R750 Rack Server Cluster",
        "category": "Servers & Networks",
        "location": "Head Office Data Center",
        "vendor": "TechNova Enterprise Solutions",
        "invoice_no": "TN/24-25/119",
        "acq_date": "2024-04-08",
        "put_to_use_date": "2024-04-12",
        "cost": 640000.0,
        "useful_life": 6.0,
        "residual_pct": 5.0,
        "residual_value": 32000.0,
        "ca_method": "WDV",
        "it_rate": 40.0,
        "it_additional_dep": 0,
        "remarks": "Core production servers (6 yrs Schedule II; 40% IT Act Block)"
    },
    {
        "id": 6,
        "asset_code": "FA-0006",
        "asset_name": "Modular Workstations & Conference Tables",
        "category": "Furniture & Fittings (General)",
        "location": "Corporate Floor 3",
        "vendor": "Featherlite Office Systems",
        "invoice_no": "FL/24-25/204",
        "acq_date": "2024-08-01",
        "put_to_use_date": "2024-08-05",
        "cost": 420000.0,
        "useful_life": 10.0,
        "residual_pct": 5.0,
        "residual_value": 21000.0,
        "ca_method": "SLM",
        "it_rate": 10.0,
        "it_additional_dep": 0,
        "remarks": "50-seater modular office furniture & boardroom setup"
    },
    {
        "id": 7,
        "asset_code": "FA-0007",
        "asset_name": "Daikin VRV Central Air Conditioning System",
        "category": "Office Equipment",
        "location": "Corporate Floor 3",
        "vendor": "CoolAir HVAC Engineers",
        "invoice_no": "CA/24-25/551",
        "acq_date": "2024-12-02",
        "put_to_use_date": "2024-12-10",
        "cost": 360000.0,
        "useful_life": 5.0,
        "residual_pct": 5.0,
        "residual_value": 18000.0,
        "ca_method": "SLM",
        "it_rate": 15.0,
        "it_additional_dep": 0,
        "remarks": "Put to use < 180 days in FY 2024-25 (7.5% IT WDV in Year 1)"
    },
    {
        "id": 8,
        "asset_code": "FA-0008",
        "asset_name": "Executive Passenger SUV (Staff Transport)",
        "category": "Motor Cars (Non-Hire)",
        "location": "Head Office Fleet",
        "vendor": "TVS Sundaram Motors",
        "invoice_no": "TSM/25-26/077",
        "acq_date": "2025-06-12",
        "put_to_use_date": "2025-06-15",
        "cost": 1600000.0,
        "useful_life": 8.0,
        "residual_pct": 5.0,
        "residual_value": 80000.0,
        "ca_method": "WDV",
        "it_rate": 15.0,
        "it_additional_dep": 0,
        "remarks": "Company vehicle put to use >= 180 days in FY 2025-26"
    },
    {
        "id": 9,
        "asset_code": "FA-0009",
        "asset_name": "MacBook Pro & ThinkPad Developer Fleet (15 Units)",
        "category": "Computers & Laptops (End-User)",
        "location": "Engineering Wing",
        "vendor": "Croma Corporate Direct",
        "invoice_no": "CCD/25-26/903",
        "acq_date": "2025-10-20",
        "put_to_use_date": "2025-10-25",
        "cost": 1125000.0,
        "useful_life": 3.0,
        "residual_pct": 5.0,
        "residual_value": 56250.0,
        "ca_method": "SLM",
        "it_rate": 40.0,
        "it_additional_dep": 0,
        "remarks": "Put to use < 180 days in FY 2025-26 (20% effective IT WDV in Yr 1)"
    },
    {
        "id": 10,
        "asset_code": "FA-0010",
        "asset_name": "SAP Business One ERP License & Implementation",
        "category": "Intangible Assets / Software",
        "location": "Enterprise IT",
        "vendor": "SAP India Systems",
        "invoice_no": "SAP/26-27/019",
        "acq_date": "2026-04-10",
        "put_to_use_date": "2026-04-15",
        "cost": 750000.0,
        "useful_life": 5.0,
        "residual_pct": 0.0,
        "residual_value": 0.0,
        "ca_method": "SLM",
        "it_rate": 25.0,
        "it_additional_dep": 0,
        "remarks": "Perpetual ERP license amortized over 5 years; 25% IT Act intangible rate"
    }
]
            }
            self._save()

    def _save(self) -> None:
        tmp_path = f"{self.db_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp_path, self.db_path)

    def add_asset(self, data: Dict) -> int:
        code_upper = data["asset_code"].strip().upper()
        for existing in self._data["assets"]:
            if existing["asset_code"].strip().upper() == code_upper:
                raise DuplicateAssetCodeError(f"Asset code '{data['asset_code']}' already exists.")

        new_id = int(self._data.get("next_id", 1))
        record = dict(data)
        record["id"] = new_id
        record["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._data["assets"].append(record)
        self._data["next_id"] = new_id + 1
        self._save()
        return new_id

    def update_asset(self, asset_id: int, data: Dict) -> None:
        code_upper = data["asset_code"].strip().upper()
        for existing in self._data["assets"]:
            if existing["id"] != asset_id and existing["asset_code"].strip().upper() == code_upper:
                raise DuplicateAssetCodeError(f"Asset code '{data['asset_code']}' already exists.")

        for idx, existing in enumerate(self._data["assets"]):
            if existing["id"] == asset_id:
                updated = dict(existing)
                updated.update(data)
                updated["id"] = asset_id
                self._data["assets"][idx] = updated
                self._save()
                return

    def delete_asset(self, asset_id: int) -> None:
        self._data["assets"] = [a for a in self._data["assets"] if a["id"] != asset_id]
        self._save()

    def get_all_assets(self, search_query: str = "") -> List[Dict]:
        assets = list(self._data["assets"])
        assets.sort(key=lambda x: (x.get("acq_date", ""), x.get("id", 0)))
        q = search_query.strip().lower()
        if not q:
            return [dict(a) for a in assets]
        return [
            dict(a)
            for a in assets
            if q in a.get("asset_code", "").lower()
            or q in a.get("asset_name", "").lower()
            or q in a.get("category", "").lower()
            or q in a.get("location", "").lower()
        ]

    def get_asset_by_id(self, asset_id: int) -> Optional[Dict]:
        for a in self._data["assets"]:
            if a["id"] == asset_id:
                return dict(a)
        return None

    def next_asset_code(self) -> str:
        existing_codes = {a["asset_code"].strip().upper() for a in self._data["assets"]}
        cnt = len(existing_codes) + 1
        while True:
            candidate = f"FA-{cnt:04d}"
            if candidate not in existing_codes:
                return candidate
            cnt += 1


# ---------------------------------------------------------------------------
# Desktop GUI Application (Tkinter / ttk)
# ---------------------------------------------------------------------------
if HAS_TKINTER:
    class FixedAssetRegisterApp(tk.Tk):
        def __init__(self, db: AssetDatabase):
            super().__init__()
            self.db = db
            self.selected_asset_id: Optional[int] = None

            self.title(
                "Fixed Asset Register & Depreciation Calculator (Companies Act 2013 & Income Tax Act 1961)"
            )
            self.geometry("1360x820")
            self.minsize(1120, 700)

            # Configure High-DPI awareness on Windows if available
            if sys.platform.startswith("win"):
                try:
                    from ctypes import windll
                    windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    pass

            self._configure_styles()
            self._build_ui()
            self.refresh_asset_table()

        def _configure_styles(self) -> None:
            style = ttk.Style(self)
            if "clam" in style.theme_names():
                style.theme_use("clam")

            style.configure("TFrame", background="#F8FAFC")
            style.configure("Card.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
            style.configure(
                "Header.TLabel",
                background="#0F172A",
                foreground="#FFFFFF",
                font=("Segoe UI", 14, "bold"),
                padding=(12, 8),
            )
            style.configure(
                "SubHeader.TLabel",
                background="#0F172A",
                foreground="#94A3B8",
                font=("Segoe UI", 9),
            )
            style.configure(
                "Section.TLabelframe",
                background="#F8FAFC",
                font=("Segoe UI", 10, "bold"),
            )
            style.configure(
                "Section.TLabelframe.Label",
                background="#F8FAFC",
                foreground="#1E293B",
                font=("Segoe UI", 10, "bold"),
            )
            style.configure("TLabel", background="#F8FAFC", foreground="#1E293B", font=("Segoe UI", 9))
            style.configure("Bold.TLabel", background="#F8FAFC", foreground="#0F172A", font=("Segoe UI", 9, "bold"))
            style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 5))
            style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), foreground="#991B1B", padding=(10, 5))
            style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
            style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#E2E8F0", foreground="#0F172A")

        def _build_ui(self) -> None:
            self.configure(bg="#F8FAFC")

            # Top Banner
            banner = tk.Frame(self, bg="#0F172A", height=56)
            banner.pack(fill=tk.X, side=tk.TOP)
            lbl_title = tk.Label(
                banner,
                text="FIXED ASSET REGISTER & DEPRECIATION MANAGER",
                bg="#0F172A",
                fg="#FFFFFF",
                font=("Segoe UI", 13, "bold"),
                padx=16,
                pady=8,
            )
            lbl_title.pack(side=tk.LEFT)
            lbl_sub = tk.Label(
                banner,
                text="Companies Act, 2013 (Schedule II - SLM / WDV)  |  Income Tax Act, 1961 (Sec 32 WDV & 180-Day Rule)",
                bg="#0F172A",
                fg="#CBD5E1",
                font=("Segoe UI", 9),
                padx=16,
            )
            lbl_sub.pack(side=tk.RIGHT)

            # Main Notebook Tabs
            self.notebook = ttk.Notebook(self)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

            # Tab 1: Asset Master & Lifecycle Schedule
            self.tab_register = ttk.Frame(self.notebook)
            self.notebook.add(
                self.tab_register,
                text="  1. Asset Register & Lifecycle Depreciation (Acquisition to Useful Life)  ",
            )

            # Tab 2: Annual FY Summary Report
            self.tab_fy_summary = ttk.Frame(self.notebook)
            self.notebook.add(
                self.tab_fy_summary,
                text="  2. Financial Year-Wise Register Summary (All Assets)  ",
            )

            self._build_tab_register()
            self._build_tab_fy_summary()

        def _build_tab_register(self) -> None:
            left_frame = ttk.LabelFrame(
                self.tab_register, text="Asset Details (Add / Update / Delete)", style="Section.TLabelframe"
            )
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 6), pady=6)

            form_grid = ttk.Frame(left_frame)
            form_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

            self.var_code = tk.StringVar(value=self.db.next_asset_code())
            self.var_name = tk.StringVar()
            self.var_category = tk.StringVar(value="Plant & Machinery (General)")
            self.var_location = tk.StringVar()
            self.var_vendor = tk.StringVar()
            self.var_invoice = tk.StringVar()
            self.var_acq_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            self.var_put_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            self.var_cost = tk.StringVar(value="100000.00")
            self.var_useful_life = tk.StringVar(value="15.0")
            self.var_residual_pct = tk.StringVar(value="5.0")
            self.var_residual_val = tk.StringVar(value="5000.00")
            self.var_ca_method = tk.StringVar(value="SLM")
            self.var_it_rate = tk.StringVar(value="15.0")
            self.var_it_add_dep = tk.IntVar(value=0)
            self.var_remarks = tk.StringVar()

            row_idx = 0

            def add_field(label_text: str, widget: tk.Widget, r: int) -> None:
                lbl = ttk.Label(form_grid, text=label_text)
                lbl.grid(row=r, column=0, sticky=tk.W, pady=3, padx=(0, 8))
                widget.grid(row=r, column=1, sticky=tk.EW, pady=3)

            form_grid.columnconfigure(1, weight=1)

            add_field("Asset Code *:", ttk.Entry(form_grid, textvariable=self.var_code, width=26), row_idx)
            row_idx += 1

            add_field("Asset Name *:", ttk.Entry(form_grid, textvariable=self.var_name, width=26), row_idx)
            row_idx += 1

            cb_cat = ttk.Combobox(
                form_grid,
                textvariable=self.var_category,
                values=list(ASSET_CATEGORIES.keys()),
                state="readonly",
                width=24,
            )
            cb_cat.bind("<<ComboboxSelected>>", self._on_category_selected)
            add_field("Asset Category *:", cb_cat, row_idx)
            row_idx += 1

            add_field("Location / Dept:", ttk.Entry(form_grid, textvariable=self.var_location, width=26), row_idx)
            row_idx += 1

            add_field("Supplier / Vendor:", ttk.Entry(form_grid, textvariable=self.var_vendor, width=26), row_idx)
            row_idx += 1

            add_field("Invoice / Bill No.:", ttk.Entry(form_grid, textvariable=self.var_invoice, width=26), row_idx)
            row_idx += 1

            add_field(
                "Acquisition Date * (YYYY-MM-DD):",
                ttk.Entry(form_grid, textvariable=self.var_acq_date, width=26),
                row_idx,
            )
            row_idx += 1

            add_field(
                "Put-to-Use Date * (YYYY-MM-DD):",
                ttk.Entry(form_grid, textvariable=self.var_put_date, width=26),
                row_idx,
            )
            row_idx += 1

            ent_cost = ttk.Entry(form_grid, textvariable=self.var_cost, width=26)
            ent_cost.bind("<KeyRelease>", self._recalc_residual_from_pct)
            add_field("Total Acquisition Cost (Rs.) *:", ent_cost, row_idx)
            row_idx += 1

            ttk.Separator(form_grid, orient=tk.HORIZONTAL).grid(
                row=row_idx, column=0, columnspan=2, sticky=tk.EW, pady=6
            )
            row_idx += 1
            ttk.Label(form_grid, text="Companies Act, 2013 Parameters", style="Bold.TLabel").grid(
                row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
            )
            row_idx += 1

            cb_method = ttk.Combobox(
                form_grid,
                textvariable=self.var_ca_method,
                values=["SLM", "WDV"],
                state="readonly",
                width=24,
            )
            add_field("Depreciation Method *:", cb_method, row_idx)
            row_idx += 1

            add_field(
                "Useful Life (Years) *:",
                ttk.Entry(form_grid, textvariable=self.var_useful_life, width=26),
                row_idx,
            )
            row_idx += 1

            ent_res_pct = ttk.Entry(form_grid, textvariable=self.var_residual_pct, width=26)
            ent_res_pct.bind("<KeyRelease>", self._recalc_residual_from_pct)
            add_field("Residual Value (%) *:", ent_res_pct, row_idx)
            row_idx += 1

            add_field(
                "Residual Value (Rs.) *:",
                ttk.Entry(form_grid, textvariable=self.var_residual_val, width=26),
                row_idx,
            )
            row_idx += 1

            ttk.Separator(form_grid, orient=tk.HORIZONTAL).grid(
                row=row_idx, column=0, columnspan=2, sticky=tk.EW, pady=6
            )
            row_idx += 1
            ttk.Label(form_grid, text="Income Tax Act, 1961 Parameters", style="Bold.TLabel").grid(
                row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(0, 3)
            )
            row_idx += 1

            add_field(
                "IT Block WDV Rate (%) *:",
                ttk.Entry(form_grid, textvariable=self.var_it_rate, width=26),
                row_idx,
            )
            row_idx += 1

            chk_add_dep = ttk.Checkbutton(
                form_grid,
                text="Eligible for 20% Additional Dep. u/s 32(1)(iia)",
                variable=self.var_it_add_dep,
            )
            chk_add_dep.grid(row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=3)
            row_idx += 1

            add_field("Remarks / Notes:", ttk.Entry(form_grid, textvariable=self.var_remarks, width=26), row_idx)
            row_idx += 1

            btn_frame = ttk.Frame(left_frame)
            btn_frame.pack(fill=tk.X, padx=10, pady=(4, 8))

            btn_add = ttk.Button(
                btn_frame, text="Add New Asset", style="Primary.TButton", command=self.on_add_asset
            )
            btn_add.grid(row=0, column=0, sticky=tk.EW, padx=2, pady=3)

            btn_update = ttk.Button(
                btn_frame, text="Update Selected", style="Primary.TButton", command=self.on_update_asset
            )
            btn_update.grid(row=0, column=1, sticky=tk.EW, padx=2, pady=3)

            btn_delete = ttk.Button(
                btn_frame, text="Delete Selected Asset", style="Danger.TButton", command=self.on_delete_asset
            )
            btn_delete.grid(row=1, column=0, sticky=tk.EW, padx=2, pady=3)

            btn_clear = ttk.Button(
                btn_frame, text="Clear / Reset Form", command=self.clear_form
            )
            btn_clear.grid(row=1, column=1, sticky=tk.EW, padx=2, pady=3)

            btn_sample = ttk.Button(
                btn_frame, text="Load Sample Assets (Demo)", command=self.load_sample_assets
            )
            btn_sample.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=2, pady=3)

            btn_frame.columnconfigure(0, weight=1)
            btn_frame.columnconfigure(1, weight=1)

            right_paned = ttk.PanedWindow(self.tab_register, orient=tk.VERTICAL)
            right_paned.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6), pady=6)

            master_frame = ttk.LabelFrame(
                right_paned,
                text="Fixed Asset Master Register (Select any asset below to view its full lifecycle schedule)",
                style="Section.TLabelframe",
            )
            right_paned.add(master_frame, weight=1)

            search_bar = ttk.Frame(master_frame)
            search_bar.pack(fill=tk.X, padx=8, pady=4)
            ttk.Label(search_bar, text="Search Assets:").pack(side=tk.LEFT, padx=(0, 6))
            self.var_search = tk.StringVar()
            ent_search = ttk.Entry(search_bar, textvariable=self.var_search, width=32)
            ent_search.pack(side=tk.LEFT, padx=(0, 6))
            ent_search.bind("<KeyRelease>", lambda _e: self.refresh_asset_table())
            ttk.Button(
                search_bar, text="Export Asset Master (CSV)", command=self.export_master_csv
            ).pack(side=tk.RIGHT, padx=4)
            ttk.Button(
                search_bar,
                text="Export Selected Asset Schedule (CSV)",
                command=self.export_selected_schedule_csv,
            ).pack(side=tk.RIGHT, padx=4)

            cols_master = (
                "id",
                "asset_code",
                "asset_name",
                "category",
                "location",
                "acq_date",
                "put_to_use_date",
                "cost",
                "useful_life",
                "residual_value",
                "ca_method",
                "it_rate",
            )
            self.tree_master = ttk.Treeview(
                master_frame, columns=cols_master, show="headings", height=8, selectmode="browse"
            )
            headings_master = {
                "id": ("ID", 40, tk.CENTER),
                "asset_code": ("Code", 75, tk.CENTER),
                "asset_name": ("Asset Name", 170, tk.W),
                "category": ("Category", 150, tk.W),
                "location": ("Location", 90, tk.W),
                "acq_date": ("Acq. Date", 85, tk.CENTER),
                "put_to_use_date": ("Put to Use", 85, tk.CENTER),
                "cost": ("Original Cost", 95, tk.E),
                "useful_life": ("Life (Yrs)", 65, tk.CENTER),
                "residual_value": ("Residual Val", 85, tk.E),
                "ca_method": ("Co. Act Method", 95, tk.CENTER),
                "it_rate": ("IT Rate %", 70, tk.E),
            }
            for col, (text, width, anchor) in headings_master.items():
                self.tree_master.heading(col, text=text)
                self.tree_master.column(col, width=width, anchor=anchor)

            scroll_master_y = ttk.Scrollbar(master_frame, orient=tk.VERTICAL, command=self.tree_master.yview)
            self.tree_master.configure(yscrollcommand=scroll_master_y.set)
            self.tree_master.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 6))
            scroll_master_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 6))

            self.tree_master.bind("<<TreeviewSelect>>", self.on_asset_selected)

            sched_frame = ttk.LabelFrame(
                right_paned,
                text="Year-by-Year Depreciation Schedule (From Year of Acquisition till Useful Life)",
                style="Section.TLabelframe",
            )
            right_paned.add(sched_frame, weight=2)

            self.lbl_sched_banner = ttk.Label(
                sched_frame,
                text="Select an asset from the register above to inspect its full Companies Act & Income Tax Act depreciation schedule.",
                style="Bold.TLabel",
            )
            self.lbl_sched_banner.pack(fill=tk.X, padx=8, pady=4)

            cols_sched = (
                "year_no",
                "fy_label",
                "ca_days",
                "ca_opening_wdv",
                "ca_depreciation",
                "ca_accum_dep",
                "ca_closing_wdv",
                "it_rule_note",
                "it_opening_wdv",
                "it_normal_dep",
                "it_add_dep",
                "it_total_dep",
                "it_closing_wdv",
                "dep_diff",
            )
            self.tree_sched = ttk.Treeview(
                sched_frame, columns=cols_sched, show="headings", height=12
            )
            headings_sched = {
                "year_no": ("Yr #", 42, tk.CENTER),
                "fy_label": ("Financial Year", 85, tk.CENTER),
                "ca_days": ("CA Days", 60, tk.CENTER),
                "ca_opening_wdv": ("CA Opening WDV", 105, tk.E),
                "ca_depreciation": ("CA Depreciation", 105, tk.E),
                "ca_accum_dep": ("CA Accum. Dep.", 105, tk.E),
                "ca_closing_wdv": ("CA Closing WDV", 105, tk.E),
                "it_rule_note": ("IT Act Rule / Days", 145, tk.CENTER),
                "it_opening_wdv": ("IT Opening WDV", 105, tk.E),
                "it_normal_dep": ("IT Normal Dep.", 95, tk.E),
                "it_add_dep": ("IT Add. Dep.", 85, tk.E),
                "it_total_dep": ("IT Total Dep.", 95, tk.E),
                "it_closing_wdv": ("IT Closing WDV", 105, tk.E),
                "dep_diff": ("Diff (CA - IT)", 90, tk.E),
            }
            for col, (text, width, anchor) in headings_sched.items():
                self.tree_sched.heading(col, text=text)
                self.tree_sched.column(col, width=width, anchor=anchor)

            scroll_sched_y = ttk.Scrollbar(sched_frame, orient=tk.VERTICAL, command=self.tree_sched.yview)
            scroll_sched_x = ttk.Scrollbar(sched_frame, orient=tk.HORIZONTAL, command=self.tree_sched.xview)
            self.tree_sched.configure(yscrollcommand=scroll_sched_y.set, xscrollcommand=scroll_sched_x.set)

            self.tree_sched.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 0))
            scroll_sched_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8))
            scroll_sched_x.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 6))

        def _build_tab_fy_summary(self) -> None:
            top_bar = ttk.Frame(self.tab_fy_summary)
            top_bar.pack(fill=tk.X, padx=10, pady=8)

            ttk.Label(top_bar, text="Select Financial Year:", style="Bold.TLabel").pack(
                side=tk.LEFT, padx=(0, 8)
            )
            self.var_selected_fy = tk.StringVar()
            self.cb_fy = ttk.Combobox(
                top_bar, textvariable=self.var_selected_fy, state="readonly", width=18
            )
            self.cb_fy.pack(side=tk.LEFT, padx=(0, 12))
            self.cb_fy.bind("<<ComboboxSelected>>", lambda _e: self.refresh_fy_summary())

            ttk.Button(
                top_bar,
                text="Refresh FY Register",
                style="Primary.TButton",
                command=self.refresh_fy_summary,
            ).pack(side=tk.LEFT, padx=4)

            ttk.Button(
                top_bar,
                text="Export FY Register to CSV",
                command=self.export_fy_summary_csv,
            ).pack(side=tk.RIGHT, padx=4)

            self.lbl_fy_totals = ttk.Label(
                self.tab_fy_summary,
                text="Totals for Selected Financial Year will appear here.",
                style="Bold.TLabel",
            )
            self.lbl_fy_totals.pack(fill=tk.X, padx=12, pady=(0, 6))

            cols_fy = (
                "asset_code",
                "asset_name",
                "category",
                "put_to_use_date",
                "cost",
                "ca_method",
                "ca_opening_wdv",
                "ca_depreciation",
                "ca_closing_wdv",
                "it_rate",
                "it_rule_note",
                "it_opening_wdv",
                "it_total_dep",
                "it_closing_wdv",
            )
            self.tree_fy = ttk.Treeview(self.tab_fy_summary, columns=cols_fy, show="headings")
            headings_fy = {
                "asset_code": ("Code", 75, tk.CENTER),
                "asset_name": ("Asset Name", 160, tk.W),
                "category": ("Category", 145, tk.W),
                "put_to_use_date": ("Put to Use", 85, tk.CENTER),
                "cost": ("Original Cost", 95, tk.E),
                "ca_method": ("CA Method", 75, tk.CENTER),
                "ca_opening_wdv": ("CA Open WDV", 100, tk.E),
                "ca_depreciation": ("CA Dep. (Year)", 100, tk.E),
                "ca_closing_wdv": ("CA Close WDV", 100, tk.E),
                "it_rate": ("IT Rate %", 70, tk.E),
                "it_rule_note": ("IT Rule Applied", 140, tk.CENTER),
                "it_opening_wdv": ("IT Open WDV", 100, tk.E),
                "it_total_dep": ("IT Dep. (Year)", 100, tk.E),
                "it_closing_wdv": ("IT Close WDV", 100, tk.E),
            }
            for col, (text, width, anchor) in headings_fy.items():
                self.tree_fy.heading(col, text=text)
                self.tree_fy.column(col, width=width, anchor=anchor)

            scroll_fy_y = ttk.Scrollbar(self.tab_fy_summary, orient=tk.VERTICAL, command=self.tree_fy.yview)
            scroll_fy_x = ttk.Scrollbar(self.tab_fy_summary, orient=tk.HORIZONTAL, command=self.tree_fy.xview)
            self.tree_fy.configure(yscrollcommand=scroll_fy_y.set, xscrollcommand=scroll_fy_x.set)

            self.tree_fy.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 0))
            scroll_fy_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10))
            scroll_fy_x.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))

        def _on_category_selected(self, _event: Optional[object] = None) -> None:
            cat = self.var_category.get()
            if cat in ASSET_CATEGORIES:
                preset = ASSET_CATEGORIES[cat]
                self.var_useful_life.set(str(preset["useful_life"]))
                self.var_residual_pct.set(str(preset["residual_pct"]))
                self.var_it_rate.set(str(preset["it_rate"]))
                self._recalc_residual_from_pct()

        def _recalc_residual_from_pct(self, _event: Optional[object] = None) -> None:
            try:
                cost = float(self.var_cost.get())
                pct = float(self.var_residual_pct.get())
                res_val = round(cost * (pct / 100.0), 2)
                self.var_residual_val.set(f"{res_val:.2f}")
            except ValueError:
                pass

        def _validate_and_collect_form(self) -> Optional[Dict]:
            code = self.var_code.get().strip()
            name = self.var_name.get().strip()
            if not code or not name:
                messagebox.showerror("Validation Error", "Asset Code and Asset Name are required.")
                return None

            try:
                acq_d = parse_iso_date(self.var_acq_date.get())
                put_d = parse_iso_date(self.var_put_date.get())
            except ValueError as err:
                messagebox.showerror("Date Error", str(err))
                return None

            if put_d < acq_d:
                messagebox.showerror(
                    "Date Error", "Put-to-Use Date cannot be earlier than Acquisition Date."
                )
                return None

            try:
                cost = float(self.var_cost.get())
                useful_life = float(self.var_useful_life.get())
                residual_pct = float(self.var_residual_pct.get())
                residual_val = float(self.var_residual_val.get())
                it_rate = float(self.var_it_rate.get())
            except ValueError:
                messagebox.showerror(
                    "Numeric Error",
                    "Cost, Useful Life, Residual Value, and IT Rate must be valid numbers.",
                )
                return None

            if cost <= 0:
                messagebox.showerror("Validation Error", "Acquisition Cost must be greater than zero.")
                return None
            if useful_life <= 0 or useful_life > 100:
                messagebox.showerror(
                    "Validation Error", "Useful Life must be between 0.5 and 100 years."
                )
                return None
            if residual_val < 0 or residual_val >= cost:
                messagebox.showerror(
                    "Validation Error",
                    "Residual Value must be non-negative and less than Original Cost.",
                )
                return None
            if it_rate < 0 or it_rate > 100:
                messagebox.showerror("Validation Error", "Income Tax WDV Rate must be between 0% and 100%.")
                return None

            return {
                "asset_code": code,
                "asset_name": name,
                "category": self.var_category.get().strip(),
                "location": self.var_location.get().strip(),
                "vendor": self.var_vendor.get().strip(),
                "invoice_no": self.var_invoice.get().strip(),
                "acq_date": acq_d.strftime("%Y-%m-%d"),
                "put_to_use_date": put_d.strftime("%Y-%m-%d"),
                "cost": round(cost, 2),
                "useful_life": round(useful_life, 2),
                "residual_pct": round(residual_pct, 2),
                "residual_value": round(residual_val, 2),
                "ca_method": self.var_ca_method.get().strip().upper(),
                "it_rate": round(it_rate, 2),
                "it_additional_dep": int(self.var_it_add_dep.get()),
                "remarks": self.var_remarks.get().strip(),
            }

        def on_add_asset(self) -> None:
            data = self._validate_and_collect_form()
            if not data:
                return
            try:
                new_id = self.db.add_asset(data)
            except DuplicateAssetCodeError:
                messagebox.showerror(
                    "Duplicate Asset Code",
                    f"Asset Code '{data['asset_code']}' already exists. Please use a unique code.",
                )
                return

            self.refresh_asset_table(select_id=new_id)
            self.clear_form()
            messagebox.showinfo("Asset Added", f"Asset '{data['asset_name']}' added to register.")

        def on_update_asset(self) -> None:
            if self.selected_asset_id is None:
                messagebox.showwarning("No Selection", "Please select an asset from the register to update.")
                return
            data = self._validate_and_collect_form()
            if not data:
                return
            try:
                self.db.update_asset(self.selected_asset_id, data)
            except DuplicateAssetCodeError:
                messagebox.showerror(
                    "Duplicate Asset Code",
                    f"Asset Code '{data['asset_code']}' is already used by another asset.",
                )
                return

            current_id = self.selected_asset_id
            self.refresh_asset_table(select_id=current_id)
            messagebox.showinfo("Asset Updated", f"Asset '{data['asset_name']}' updated.")

        def on_delete_asset(self) -> None:
            if self.selected_asset_id is None:
                messagebox.showwarning("No Selection", "Please select an asset from the register to delete.")
                return
            asset = self.db.get_asset_by_id(self.selected_asset_id)
            if not asset:
                return
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to permanently delete asset '{asset['asset_code']} - {asset['asset_name']}'?",
            )
            if not confirm:
                return
            self.db.delete_asset(self.selected_asset_id)
            self.selected_asset_id = None
            self.clear_form()
            self.refresh_asset_table()
            for item in self.tree_sched.get_children():
                self.tree_sched.delete(item)
            self.lbl_sched_banner.config(
                text="Asset deleted. Select another asset to view its depreciation schedule."
            )

        def clear_form(self) -> None:
            self.selected_asset_id = None
            self.var_code.set(self.db.next_asset_code())
            self.var_name.set("")
            self.var_category.set("Plant & Machinery (General)")
            self.var_location.set("")
            self.var_vendor.set("")
            self.var_invoice.set("")
            today_str = date.today().strftime("%Y-%m-%d")
            self.var_acq_date.set(today_str)
            self.var_put_date.set(today_str)
            self.var_cost.set("100000.00")
            self._on_category_selected()
            self.var_ca_method.set("SLM")
            self.var_it_add_dep.set(0)
            self.var_remarks.set("")

        def load_sample_assets(self) -> None:
            samples = [
                {
                                "asset_code": "FA-0001",
                                "asset_name": "Industrial Factory Shed & Civil Works",
                                "category": "Buildings (Factory)",
                                "location": "Peenya Industrial Area - Block A",
                                "vendor": "Shapoorji Industrial Constructions",
                                "invoice_no": "SIC/22-23/014",
                                "acq_date": "2022-05-15",
                                "put_to_use_date": "2022-06-01",
                                "cost": 4500000.0,
                                "useful_life": 30.0,
                                "residual_pct": 5.0,
                                "residual_value": 225000.0,
                                "ca_method": "SLM",
                                "it_rate": 10.0,
                                "it_additional_dep": 0,
                                "remarks": "Factory building put to use >= 180 days in FY 2022-23"
                },
                {
                                "asset_code": "FA-0002",
                                "asset_name": "Corporate Office Floor Unit",
                                "category": "Buildings (Office / Non-Factory)",
                                "location": "Kochi InfoPark - Tower 2",
                                "vendor": "Prestige Commercial Estates",
                                "invoice_no": "PCE/22-23/089",
                                "acq_date": "2022-09-01",
                                "put_to_use_date": "2022-09-15",
                                "cost": 8000000.0,
                                "useful_life": 60.0,
                                "residual_pct": 5.0,
                                "residual_value": 400000.0,
                                "ca_method": "SLM",
                                "it_rate": 10.0,
                                "it_additional_dep": 0,
                                "remarks": "Admin office RCC structure (60 yrs Schedule II useful life)"
                },
                {
                                "asset_code": "FA-0003",
                                "asset_name": "5-Axis CNC Vertical Machining Center",
                                "category": "Plant & Machinery (General)",
                                "location": "Plant Shopfloor A",
                                "vendor": "Bharat Machine Tools Ltd",
                                "invoice_no": "BMT/23-24/108",
                                "acq_date": "2023-05-10",
                                "put_to_use_date": "2023-05-20",
                                "cost": 1850000.0,
                                "useful_life": 15.0,
                                "residual_pct": 5.0,
                                "residual_value": 92500.0,
                                "ca_method": "SLM",
                                "it_rate": 15.0,
                                "it_additional_dep": 1,
                                "remarks": "Put to use >= 180 days in FY 2023-24; 20% Add. Dep u/s 32(1)(iia)"
                },
                {
                                "asset_code": "FA-0004",
                                "asset_name": "Automated Laser Cutting & Bending Line",
                                "category": "Plant & Machinery (General)",
                                "location": "Plant Shopfloor B",
                                "vendor": "Trumpf India Pvt Ltd",
                                "invoice_no": "TIPL/23-24/412",
                                "acq_date": "2023-11-10",
                                "put_to_use_date": "2023-11-18",
                                "cost": 1200000.0,
                                "useful_life": 15.0,
                                "residual_pct": 5.0,
                                "residual_value": 60000.0,
                                "ca_method": "WDV",
                                "it_rate": 15.0,
                                "it_additional_dep": 1,
                                "remarks": "< 180 days in FY 2023-24 (Half rate + 10% Add. Dep in Yr 1, bal 10% in Yr 2)"
                },
                {
                                "asset_code": "FA-0005",
                                "asset_name": "Dell PowerEdge R750 Rack Server Cluster",
                                "category": "Servers & Networks",
                                "location": "Head Office Data Center",
                                "vendor": "TechNova Enterprise Solutions",
                                "invoice_no": "TN/24-25/119",
                                "acq_date": "2024-04-08",
                                "put_to_use_date": "2024-04-12",
                                "cost": 640000.0,
                                "useful_life": 6.0,
                                "residual_pct": 5.0,
                                "residual_value": 32000.0,
                                "ca_method": "WDV",
                                "it_rate": 40.0,
                                "it_additional_dep": 0,
                                "remarks": "Core production servers (6 yrs Schedule II; 40% IT Act Block)"
                },
                {
                                "asset_code": "FA-0006",
                                "asset_name": "Modular Workstations & Conference Tables",
                                "category": "Furniture & Fittings (General)",
                                "location": "Corporate Floor 3",
                                "vendor": "Featherlite Office Systems",
                                "invoice_no": "FL/24-25/204",
                                "acq_date": "2024-08-01",
                                "put_to_use_date": "2024-08-05",
                                "cost": 420000.0,
                                "useful_life": 10.0,
                                "residual_pct": 5.0,
                                "residual_value": 21000.0,
                                "ca_method": "SLM",
                                "it_rate": 10.0,
                                "it_additional_dep": 0,
                                "remarks": "50-seater modular office furniture & boardroom setup"
                },
                {
                                "asset_code": "FA-0007",
                                "asset_name": "Daikin VRV Central Air Conditioning System",
                                "category": "Office Equipment",
                                "location": "Corporate Floor 3",
                                "vendor": "CoolAir HVAC Engineers",
                                "invoice_no": "CA/24-25/551",
                                "acq_date": "2024-12-02",
                                "put_to_use_date": "2024-12-10",
                                "cost": 360000.0,
                                "useful_life": 5.0,
                                "residual_pct": 5.0,
                                "residual_value": 18000.0,
                                "ca_method": "SLM",
                                "it_rate": 15.0,
                                "it_additional_dep": 0,
                                "remarks": "Put to use < 180 days in FY 2024-25 (7.5% IT WDV in Year 1)"
                },
                {
                                "asset_code": "FA-0008",
                                "asset_name": "Executive Passenger SUV (Staff Transport)",
                                "category": "Motor Cars (Non-Hire)",
                                "location": "Head Office Fleet",
                                "vendor": "TVS Sundaram Motors",
                                "invoice_no": "TSM/25-26/077",
                                "acq_date": "2025-06-12",
                                "put_to_use_date": "2025-06-15",
                                "cost": 1600000.0,
                                "useful_life": 8.0,
                                "residual_pct": 5.0,
                                "residual_value": 80000.0,
                                "ca_method": "WDV",
                                "it_rate": 15.0,
                                "it_additional_dep": 0,
                                "remarks": "Company vehicle put to use >= 180 days in FY 2025-26"
                },
                {
                                "asset_code": "FA-0009",
                                "asset_name": "MacBook Pro & ThinkPad Developer Fleet (15 Units)",
                                "category": "Computers & Laptops (End-User)",
                                "location": "Engineering Wing",
                                "vendor": "Croma Corporate Direct",
                                "invoice_no": "CCD/25-26/903",
                                "acq_date": "2025-10-20",
                                "put_to_use_date": "2025-10-25",
                                "cost": 1125000.0,
                                "useful_life": 3.0,
                                "residual_pct": 5.0,
                                "residual_value": 56250.0,
                                "ca_method": "SLM",
                                "it_rate": 40.0,
                                "it_additional_dep": 0,
                                "remarks": "Put to use < 180 days in FY 2025-26 (20% effective IT WDV in Yr 1)"
                },
                {
                                "asset_code": "FA-0010",
                                "asset_name": "SAP Business One ERP License & Implementation",
                                "category": "Intangible Assets / Software",
                                "location": "Enterprise IT",
                                "vendor": "SAP India Systems",
                                "invoice_no": "SAP/26-27/019",
                                "acq_date": "2026-04-10",
                                "put_to_use_date": "2026-04-15",
                                "cost": 750000.0,
                                "useful_life": 5.0,
                                "residual_pct": 0.0,
                                "residual_value": 0.0,
                                "ca_method": "SLM",
                                "it_rate": 25.0,
                                "it_additional_dep": 0,
                                "remarks": "Perpetual ERP license amortized over 5 years; 25% IT Act intangible rate"
                }
]
            added = 0
            for s in samples:
                try:
                    self.db.add_asset(s)
                    added += 1
                except DuplicateAssetCodeError:
                    pass
            self.refresh_asset_table()
            self.clear_form()
            if added > 0:
                messagebox.showinfo("Sample Data Loaded", f"Loaded {added} sample fixed assets.")
            else:
                messagebox.showinfo("Sample Data", "Sample assets are already present in the register.")

        def refresh_asset_table(self, select_id: Optional[int] = None) -> None:
            for item in self.tree_master.get_children():
                self.tree_master.delete(item)

            assets = self.db.get_all_assets(self.var_search.get())
            selected_iid = None

            for a in assets:
                iid = str(a["id"])
                self.tree_master.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        a["id"],
                        a["asset_code"],
                        a["asset_name"],
                        a["category"],
                        a["location"],
                        a["acq_date"],
                        a["put_to_use_date"],
                        f"{a['cost']:,.2f}",
                        f"{a['useful_life']:.1f}",
                        f"{a['residual_value']:,.2f}",
                        a["ca_method"],
                        f"{a['it_rate']:.1f}%",
                    ),
                )
                if select_id is not None and a["id"] == select_id:
                    selected_iid = iid

            if selected_iid:
                self.tree_master.selection_set(selected_iid)
                self.tree_master.see(selected_iid)
                self.on_asset_selected()
            elif assets and self.selected_asset_id is None:
                first_iid = str(assets[0]["id"])
                self.tree_master.selection_set(first_iid)
                self.on_asset_selected()

            self._populate_fy_dropdown()
            self.refresh_fy_summary()

        def on_asset_selected(self, _event: Optional[object] = None) -> None:
            sel = self.tree_master.selection()
            if not sel:
                return
            asset_id = int(sel[0])
            asset = self.db.get_asset_by_id(asset_id)
            if not asset:
                return

            self.selected_asset_id = asset_id

            self.var_code.set(asset["asset_code"])
            self.var_name.set(asset["asset_name"])
            self.var_category.set(asset["category"])
            self.var_location.set(asset["location"])
            self.var_vendor.set(asset["vendor"])
            self.var_invoice.set(asset["invoice_no"])
            self.var_acq_date.set(asset["acq_date"])
            self.var_put_date.set(asset["put_to_use_date"])
            self.var_cost.set(f"{asset['cost']:.2f}")
            self.var_useful_life.set(f"{asset['useful_life']:.2f}")
            self.var_residual_pct.set(f"{asset['residual_pct']:.2f}")
            self.var_residual_val.set(f"{asset['residual_value']:.2f}")
            self.var_ca_method.set(asset["ca_method"])
            self.var_it_rate.set(f"{asset['it_rate']:.2f}")
            self.var_it_add_dep.set(int(asset["it_additional_dep"]))
            self.var_remarks.set(asset["remarks"])

            for item in self.tree_sched.get_children():
                self.tree_sched.delete(item)

            sched = calculate_depreciation_schedule(asset)
            eff_rate_str = f"{sched[0]['ca_rate_pct']:.2f}%" if sched else "N/A"
            self.lbl_sched_banner.config(
                text=(
                    f"Asset: {asset['asset_code']} - {asset['asset_name']}  |  "
                    f"Cost: Rs. {asset['cost']:,.2f}  |  Residual: Rs. {asset['residual_value']:,.2f}  |  "
                    f"Co. Act: {asset['ca_method']} ({asset['useful_life']:g} Yrs, Eff. Rate: {eff_rate_str})  |  "
                    f"IT Act WDV Rate: {asset['it_rate']:g}%"
                )
            )

            for row in sched:
                self.tree_sched.insert(
                    "",
                    tk.END,
                    values=(
                        row["year_no"],
                        row["fy_label"],
                        row["ca_days"],
                        f"{row['ca_opening_wdv']:,.2f}",
                        f"{row['ca_depreciation']:,.2f}",
                        f"{row['ca_accum_dep']:,.2f}",
                        f"{row['ca_closing_wdv']:,.2f}",
                        row["it_rule_note"],
                        f"{row['it_opening_wdv']:,.2f}",
                        f"{row['it_normal_dep']:,.2f}",
                        f"{row['it_add_dep']:,.2f}",
                        f"{row['it_total_dep']:,.2f}",
                        f"{row['it_closing_wdv']:,.2f}",
                        f"{row['dep_diff']:+,.2f}",
                    ),
                )

        def _populate_fy_dropdown(self) -> None:
            assets = self.db.get_all_assets()
            fy_years = set()
            for a in assets:
                for r in calculate_depreciation_schedule(a):
                    fy_years.add(r["fy_start_yr"])

            if not fy_years:
                cur_fy, _, _ = get_fy_bounds(date.today())
                fy_years.add(cur_fy)

            sorted_fys = sorted(fy_years)
            fy_labels = [format_fy(y) for y in sorted_fys]
            self.cb_fy["values"] = fy_labels
            if self.var_selected_fy.get() not in fy_labels:
                self.var_selected_fy.set(fy_labels[0])

        def refresh_fy_summary(self) -> None:
            for item in self.tree_fy.get_children():
                self.tree_fy.delete(item)

            target_fy = self.var_selected_fy.get()
            if not target_fy:
                return

            assets = self.db.get_all_assets()
            tot_cost = 0.0
            tot_ca_open = 0.0
            tot_ca_dep = 0.0
            tot_ca_close = 0.0
            tot_it_open = 0.0
            tot_it_dep = 0.0
            tot_it_close = 0.0

            for a in assets:
                sched = calculate_depreciation_schedule(a)
                for r in sched:
                    if r["fy_label"] == target_fy:
                        self.tree_fy.insert(
                            "",
                            tk.END,
                            values=(
                                a["asset_code"],
                                a["asset_name"],
                                a["category"],
                                a["put_to_use_date"],
                                f"{a['cost']:,.2f}",
                                a["ca_method"],
                                f"{r['ca_opening_wdv']:,.2f}",
                                f"{r['ca_depreciation']:,.2f}",
                                f"{r['ca_closing_wdv']:,.2f}",
                                f"{a['it_rate']:.1f}%",
                                r["it_rule_note"],
                                f"{r['it_opening_wdv']:,.2f}",
                                f"{r['it_total_dep']:,.2f}",
                                f"{r['it_closing_wdv']:,.2f}",
                            ),
                        )
                        tot_cost += a["cost"]
                        tot_ca_open += r["ca_opening_wdv"]
                        tot_ca_dep += r["ca_depreciation"]
                        tot_ca_close += r["ca_closing_wdv"]
                        tot_it_open += r["it_opening_wdv"]
                        tot_it_dep += r["it_total_dep"]
                        tot_it_close += r["it_closing_wdv"]
                        break

            self.lbl_fy_totals.config(
                text=(
                    f"{target_fy} Summary  |  Original Cost: Rs. {tot_cost:,.2f}  |  "
                    f"Co. Act Dep: Rs. {tot_ca_dep:,.2f} (Closing WDV: Rs. {tot_ca_close:,.2f})  |  "
                    f"IT Act Dep: Rs. {tot_it_dep:,.2f} (Closing WDV: Rs. {tot_it_close:,.2f})"
                )
            )

        def export_master_csv(self) -> None:
            assets = self.db.get_all_assets()
            if not assets:
                messagebox.showwarning("Empty Register", "No assets available to export.")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile="Fixed_Asset_Master_Register.csv",
                filetypes=[("CSV Files", "*.csv")],
            )
            if not path:
                return
            fieldnames = [
                "asset_code",
                "asset_name",
                "category",
                "location",
                "vendor",
                "invoice_no",
                "acq_date",
                "put_to_use_date",
                "cost",
                "useful_life",
                "residual_pct",
                "residual_value",
                "ca_method",
                "it_rate",
                "it_additional_dep",
                "remarks",
            ]
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(assets)
            messagebox.showinfo("Export Complete", f"Asset Master exported to:\n{path}")

        def export_selected_schedule_csv(self) -> None:
            if self.selected_asset_id is None:
                messagebox.showwarning("No Asset Selected", "Please select an asset first.")
                return
            asset = self.db.get_asset_by_id(self.selected_asset_id)
            if not asset:
                return
            sched = calculate_depreciation_schedule(asset)
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"Depreciation_Schedule_{asset['asset_code']}.csv",
                filetypes=[("CSV Files", "*.csv")],
            )
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Asset Code", asset["asset_code"], "Asset Name", asset["asset_name"]])
                writer.writerow(
                    [
                        "Category",
                        asset["category"],
                        "Acquisition Date",
                        asset["acq_date"],
                        "Put to Use Date",
                        asset["put_to_use_date"],
                    ]
                )
                writer.writerow(
                    [
                        "Original Cost",
                        asset["cost"],
                        "Useful Life (Yrs)",
                        asset["useful_life"],
                        "Residual Value",
                        asset["residual_value"],
                        "Co. Act Method",
                        asset["ca_method"],
                        "IT Act Rate %",
                        asset["it_rate"],
                    ]
                )
                writer.writerow([])
                writer.writerow(
                    [
                        "Year #",
                        "Financial Year",
                        "CA Days Used",
                        "CA Opening WDV",
                        "CA Depreciation",
                        "CA Accumulated Dep",
                        "CA Closing WDV",
                        "IT Act Rule",
                        "IT Opening WDV",
                        "IT Normal Dep",
                        "IT Additional Dep",
                        "IT Total Dep",
                        "IT Closing WDV",
                        "Timing Difference (CA - IT)",
                    ]
                )
                for r in sched:
                    writer.writerow(
                        [
                            r["year_no"],
                            r["fy_label"],
                            r["ca_days"],
                            r["ca_opening_wdv"],
                            r["ca_depreciation"],
                            r["ca_accum_dep"],
                            r["ca_closing_wdv"],
                            r["it_rule_note"],
                            r["it_opening_wdv"],
                            r["it_normal_dep"],
                            r["it_add_dep"],
                            r["it_total_dep"],
                            r["it_closing_wdv"],
                            r["dep_diff"],
                        ]
                    )
            messagebox.showinfo("Export Complete", f"Lifecycle Schedule exported to:\n{path}")

        def export_fy_summary_csv(self) -> None:
            target_fy = self.var_selected_fy.get()
            if not target_fy:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"Fixed_Asset_Register_{target_fy.replace(' ', '_')}.csv",
                filetypes=[("CSV Files", "*.csv")],
            )
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([f"Fixed Asset Register Summary - {target_fy}"])
                writer.writerow(
                    [
                        "Asset Code",
                        "Asset Name",
                        "Category",
                        "Put to Use Date",
                        "Original Cost",
                        "CA Method",
                        "CA Opening WDV",
                        "CA Depreciation",
                        "CA Closing WDV",
                        "IT Rate %",
                        "IT Rule Applied",
                        "IT Opening WDV",
                        "IT Depreciation",
                        "IT Closing WDV",
                    ]
                )
                for iid in self.tree_fy.get_children():
                    writer.writerow(self.tree_fy.item(iid)["values"])
            messagebox.showinfo("Export Complete", f"FY Summary exported to:\n{path}")


def main() -> None:
    db = AssetDatabase()
    if HAS_TKINTER:
        app = FixedAssetRegisterApp(db)
        app.mainloop()
    else:
        print(
            "Note: Tkinter GUI module is not installed in this Python environment.\n"
            "On standard Windows Python installations, Tkinter launches the desktop window automatically."
        )


if __name__ == "__main__":
    main()