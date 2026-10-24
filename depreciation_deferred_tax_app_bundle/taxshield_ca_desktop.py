#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TaxShield CA — Statutory Depreciation & Deferred Tax Desktop Suite (v3.0)
Companies Act, 2013 (Schedule II) | Income Tax Act, 1961 (Sec 32) | AS 22 / Ind AS 12
===============================================================================
Features in v3.0:
1. Dynamic Multi-Year WDV Roll-Forward & Roll-Back Engine (FY 2022-23 to FY 2034-35):
   - Selecting ANY Financial Year in the top bar (or clicking '<< Prev FY' / 'Next FY >>')
     automatically rolls every asset's Opening Book WDV, Opening Tax WDV, Current Year
     Depreciation, Closing WDV, and Opening/Closing Net DTL/(DTA) forward or backward!
   - Assets acquired in a future year relative to the selected FY are marked as
     'Future Addition (Not Yet Put to Use)' with ₹0 WDV/Depreciation for that earlier year.
   - Assets acquired in the selected FY apply exact day-wise pro-rata (Companies Act)
     and 180-day full/half rate + Sec 32(1)(iia) Additional Depreciation (Income Tax Act).
   - In subsequent FYs (e.g. FY 2026-27, 2027-28...), each asset's Closing WDV from the
     prior FY automatically becomes its Opening WDV for the selected FY.
2. Multi-Company Master Management (Add, Edit, Switch, Delete Companies).
3. Fixed Asset Register CRUD (Add, Edit, Delete, Clear, Reset Sample Data) backed by
   local SQLite database (`taxshield_ca_data.db`).

To compile into a standalone Windows .exe file:
    pip install pyinstaller
    pyinstaller --onefile --windowed --name "TaxShield_CA_Depreciation_Suite" taxshield_ca_desktop.py
===============================================================================
"""

import csv
import datetime
import json
import math
import os
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

DB_FILENAME = "taxshield_ca_data.db"

FY_LIST = [
    "2022-23", "2023-24", "2024-25", "2025-26", "2026-27",
    "2027-28", "2028-29", "2029-30", "2030-31", "2031-32",
    "2032-33", "2033-34", "2034-35"
]

IT_BLOCK_RATES = {
    "Plant & Machinery (15%)": 15.0,
    "Computers & Software (40%)": 40.0,
    "Energy Saving Devices (40%)": 40.0,
    "Building - Factory (10%)": 10.0,
    "Building - Office (10%)": 10.0,
    "Furniture & Fittings (10%)": 10.0,
    "Motor Cars (15%)": 15.0,
    "Commercial Vehicles (30%)": 30.0,
    "Intangible Assets (25%)": 25.0,
}

NESD_ELIGIBLE = {"Plant & Machinery (General)", "Energy Saving / Solar"}

TAX_REGIME_PRESETS = {
    "115BAA": 25.168,
    "115BAB": 17.160,
    "NORMAL_25": 27.820,
    "NORMAL_30": 34.944,
    "CUSTOM": 25.168,
}


def format_inr(val):
    try:
        num = float(val)
    except (TypeError, ValueError):
        num = 0.0
    is_neg = num < 0
    n = int(round(abs(num)))
    s = str(n)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3
    else:
        formatted = s
    return f"(₹{formatted})" if is_neg else f"₹{formatted}"


def get_fy_bounds(start_year):
    start_date = datetime.date(start_year, 4, 1)
    end_date = datetime.date(start_year + 1, 3, 31)
    total_days = (end_date - start_date).days + 1
    return start_date, end_date, total_days


def simulate_single_year_for_asset(asset, fy_start_year, op_book, op_tax, method):
    """Computes single-year depreciation for an asset in `fy_start_year` given its opening WDVs."""
    fy_start, fy_end, total_days_fy = get_fy_bounds(fy_start_year)
    c = float(asset["original_cost"])
    salvage_pct = float(asset["salvage_pct"])
    s = c * (salvage_pct / 100.0)
    n = max(1, int(asset["useful_life"]))
    disposal = float(asset.get("disposal_proceeds", 0.0))

    try:
        parts = [int(x) for x in asset["put_to_use_date"].split("-")]
        put_date = datetime.date(parts[0], parts[1], parts[2])
    except Exception:
        put_date = fy_start

    if put_date > fy_end:
        # Not yet acquired in this FY
        return {
            "status": "Future Addition",
            "is_active": False,
            "is_cy_add": False,
            "days_used": 0,
            "total_days_fy": total_days_fy,
            "op_book": 0.0,
            "book_depr": 0.0,
            "closing_book_wdv": 0.0,
            "op_tax": 0.0,
            "normal_it_depr": 0.0,
            "addl_it_depr": 0.0,
            "total_it_depr": 0.0,
            "closing_tax_wdv": 0.0,
            "co_base_rate": 0.0,
            "shift_factor": 1.0,
            "eff_co_rate": 0.0,
            "block_rate": IT_BLOCK_RATES.get(asset["it_block"], 15.0),
            "is_more_180": False,
            "applied_it_rate": 0.0,
            "addl_it_rate": 0.0,
        }

    is_cy_add = (fy_start <= put_date <= fy_end)
    days_used = (fy_end - put_date).days + 1 if is_cy_add else total_days_fy

    if method == "WDV":
        ratio = (s / c) if (c > 0 and s > 0) else 0.05
        co_base_rate = (1.0 - math.pow(ratio, 1.0 / n)) * 100.0
    else:
        co_base_rate = (100.0 - salvage_pct) / n

    shift_factor = 1.0
    if asset["co_category"] in NESD_ELIGIBLE:
        if int(asset["shifts"]) == 2:
            shift_factor = 1.5
        elif int(asset["shifts"]) == 3:
            shift_factor = 2.0

    eff_co_rate = co_base_rate * shift_factor
    pro_rata = days_used / float(total_days_fy)

    if method == "WDV":
        raw_book_depr = op_book * (eff_co_rate / 100.0) * pro_rata
    else:
        raw_book_depr = c * (eff_co_rate / 100.0) * pro_rata

    max_book_depr = max(0.0, op_book - disposal - s)
    book_depr = min(raw_book_depr, max_book_depr)
    closing_book_wdv = max(0.0, op_book - disposal - book_depr)

    block_rate = IT_BLOCK_RATES.get(asset["it_block"], 15.0)
    is_more_180 = (not is_cy_add) or (days_used >= 180)
    applied_it_rate = block_rate if is_more_180 else (block_rate / 2.0)

    net_tax_base = max(0.0, op_tax - disposal)
    normal_it_depr = net_tax_base * (applied_it_rate / 100.0)

    addl_it_rate = 0.0
    if is_cy_add and bool(asset["eligible_addl_depr"]) and days_used > 0:
        addl_it_rate = 20.0 if is_more_180 else 10.0

    addl_it_depr = net_tax_base * (addl_it_rate / 100.0)
    total_it_depr = min(net_tax_base, normal_it_depr + addl_it_depr)
    closing_tax_wdv = max(0.0, net_tax_base - total_it_depr)

    return {
        "status": "New in FY" if is_cy_add else "Opening Block",
        "is_active": True,
        "is_cy_add": is_cy_add,
        "days_used": days_used,
        "total_days_fy": total_days_fy,
        "op_book": op_book,
        "book_depr": book_depr,
        "closing_book_wdv": closing_book_wdv,
        "op_tax": op_tax,
        "normal_it_depr": normal_it_depr,
        "addl_it_depr": addl_it_depr,
        "total_it_depr": total_it_depr,
        "closing_tax_wdv": closing_tax_wdv,
        "co_base_rate": co_base_rate,
        "shift_factor": shift_factor,
        "eff_co_rate": eff_co_rate,
        "block_rate": block_rate,
        "is_more_180": is_more_180,
        "applied_it_rate": applied_it_rate,
        "addl_it_rate": addl_it_rate,
    }


def compute_asset_for_target_fy(asset, target_fy_start, method, base_fy_start=2025):
    """
    Dynamically rolls an asset's WDV from its acquisition date (or base FY 2025-26 anchor)
    to `target_fy_start` so changing Financial Year updates Opening WDV, CY Depr, and Closing WDV!
    """
    c = float(asset["original_cost"])
    base_op_book = float(asset["op_book_wdv"])
    base_op_tax = float(asset["op_tax_wdv"])

    try:
        parts = [int(x) for x in asset["put_to_use_date"].split("-")]
        put_date = datetime.date(parts[0], parts[1], parts[2])
    except Exception:
        put_date = datetime.date(base_fy_start, 4, 1)

    acq_fy_start = put_date.year if put_date.month >= 4 else (put_date.year - 1)

    # Case 1: Target FY is before the asset was even acquired
    if target_fy_start < acq_fy_start:
        return simulate_single_year_for_asset(asset, target_fy_start, 0.0, 0.0, method)

    # Determine starting simulation year and initial WDVs
    # If the user entered custom opening WDVs for an asset acquired before base_fy_start (2025)
    # and target_fy_start >= base_fy_start, we can start from base_fy_start using base_op_book/base_op_tax.
    # If target_fy_start < base_fy_start (e.g., 2024-25 or 2023-24), we simulate from acq_fy_start at Original Cost!
    if acq_fy_start >= base_fy_start:
        sim_start_yr = acq_fy_start
        curr_book = base_op_book if base_op_book > 0 else c
        curr_tax = base_op_tax if base_op_tax > 0 else c
    else:
        if target_fy_start >= base_fy_start:
            sim_start_yr = base_fy_start
            curr_book = base_op_book
            curr_tax = base_op_tax
        else:
            sim_start_yr = acq_fy_start
            curr_book = c
            curr_tax = c

    res = None
    for yr in range(sim_start_yr, target_fy_start + 1):
        res = simulate_single_year_for_asset(asset, yr, curr_book, curr_tax, method)
        curr_book = res["closing_book_wdv"]
        curr_tax = res["closing_tax_wdv"]

    return res


def compute_company_schedules(company, assets):
    """Computes Companies Act Schedule II, Income Tax Sec 32, and Deferred Tax for the active FY."""
    fy_str = company.get("fy", "2025-26")
    try:
        target_fy_start = int(fy_str.split("-")[0])
    except Exception:
        target_fy_start = 2025

    method = company.get("co_method", "WDV")
    tax_rate = float(company.get("effective_tax_rate", 25.168)) / 100.0

    computed_assets = []
    block_map = {}

    totals = {
        "original_cost": 0.0,
        "salvage_val": 0.0,
        "op_book_wdv": 0.0,
        "op_tax_wdv": 0.0,
        "book_depr": 0.0,
        "closing_book_wdv": 0.0,
        "normal_it_depr": 0.0,
        "addl_it_depr": 0.0,
        "total_it_depr": 0.0,
        "closing_tax_wdv": 0.0,
        "timing_diff_cy": 0.0,
        "cy_dtl_impact": 0.0,
        "temp_diff_closing": 0.0,
        "closing_net_dtl": 0.0,
        "opening_temp_diff": 0.0,
        "derived_opening_dtl": 0.0,
    }

    for a in assets:
        c = float(a["original_cost"])
        salvage_pct = float(a["salvage_pct"])
        s = c * (salvage_pct / 100.0)
        n = max(1, int(a["useful_life"]))
        disposal = float(a.get("disposal_proceeds", 0.0))

        sim = compute_asset_for_target_fy(a, target_fy_start, method, base_fy_start=2025)

        timing_diff_cy = sim["total_it_depr"] - sim["book_depr"]
        cy_dtl_impact = timing_diff_cy * tax_rate
        temp_diff_closing = sim["closing_book_wdv"] - sim["closing_tax_wdv"]
        closing_net_dtl = temp_diff_closing * tax_rate

        # Opening temporary difference (from existing opening assets in this FY)
        op_temp_diff = (sim["op_book"] - sim["op_tax"]) if (sim["is_active"] and not sim["is_cy_add"]) else 0.0

        comp_row = {
            **a,
            "c": c if sim["is_active"] else 0.0,
            "nominal_cost": c,
            "s": s if sim["is_active"] else 0.0,
            "n": n,
            "disposal": disposal,
            **sim,
            "timing_diff_cy": timing_diff_cy,
            "cy_dtl_impact": cy_dtl_impact,
            "temp_diff_closing": temp_diff_closing,
            "closing_net_dtl": closing_net_dtl,
        }
        computed_assets.append(comp_row)

        if sim["is_active"]:
            blk_name = a["it_block"]
            if blk_name not in block_map:
                block_map[blk_name] = {
                    "block_name": blk_name,
                    "rate_pct": sim["block_rate"],
                    "opening_wdv": 0.0,
                    "add_more_180": 0.0,
                    "add_less_180": 0.0,
                    "deductions": 0.0,
                    "normal_depr": 0.0,
                    "addl_depr": 0.0,
                    "total_depr": 0.0,
                    "closing_wdv": 0.0,
                }
            blk = block_map[blk_name]
            if sim["is_cy_add"]:
                if sim["is_more_180"]:
                    blk["add_more_180"] += sim["op_tax"]
                else:
                    blk["add_less_180"] += sim["op_tax"]
            else:
                blk["opening_wdv"] += sim["op_tax"]
            blk["deductions"] += disposal
            blk["normal_depr"] += sim["normal_it_depr"]
            blk["addl_depr"] += sim["addl_it_depr"]
            blk["total_depr"] += sim["total_it_depr"]
            blk["closing_wdv"] += sim["closing_tax_wdv"]

            totals["original_cost"] += c
            totals["salvage_val"] += s
            totals["op_book_wdv"] += sim["op_book"]
            totals["op_tax_wdv"] += sim["op_tax"]
            totals["book_depr"] += sim["book_depr"]
            totals["closing_book_wdv"] += sim["closing_book_wdv"]
            totals["normal_it_depr"] += sim["normal_it_depr"]
            totals["addl_it_depr"] += sim["addl_it_depr"]
            totals["total_it_depr"] += sim["total_it_depr"]
            totals["closing_tax_wdv"] += sim["closing_tax_wdv"]
            totals["timing_diff_cy"] += timing_diff_cy
            totals["cy_dtl_impact"] += cy_dtl_impact
            totals["temp_diff_closing"] += temp_diff_closing
            totals["closing_net_dtl"] += closing_net_dtl
            totals["opening_temp_diff"] += op_temp_diff

    totals["derived_opening_dtl"] = round(totals["opening_temp_diff"] * tax_rate)
    return computed_assets, list(block_map.values()), totals


class DatabaseManager:
    """Handles SQLite persistence for Company Master and Fixed Assets."""

    def __init__(self, db_path=DB_FILENAME):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                cin TEXT DEFAULT '',
                pan TEXT DEFAULT '',
                tan TEXT DEFAULT '',
                fy TEXT DEFAULT '2025-26',
                co_method TEXT DEFAULT 'WDV',
                tax_regime TEXT DEFAULT '115BAA',
                effective_tax_rate REAL DEFAULT 25.168,
                opening_dtl REAL DEFAULT 940276,
                address TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                asset_code TEXT NOT NULL,
                name TEXT NOT NULL,
                co_category TEXT NOT NULL,
                it_block TEXT NOT NULL,
                put_to_use_date TEXT NOT NULL,
                original_cost REAL NOT NULL,
                op_book_wdv REAL NOT NULL,
                op_tax_wdv REAL NOT NULL,
                useful_life INTEGER NOT NULL DEFAULT 15,
                salvage_pct REAL NOT NULL DEFAULT 5.0,
                shifts INTEGER NOT NULL DEFAULT 1,
                eligible_addl_depr INTEGER NOT NULL DEFAULT 1,
                disposal_proceeds REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()
        cur.execute("SELECT COUNT(*) AS cnt FROM companies")
        if cur.fetchone()["cnt"] == 0:
            self.seed_sample_data()

    def seed_sample_data(self):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO companies (code, name, cin, pan, tan, fy, co_method, tax_regime, effective_tax_rate, opening_dtl, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "CMP-001",
            "Apex Precision Engineering Pvt. Ltd.",
            "U28910KA2018PTC112345",
            "AABCA1234F",
            "BLRA98765E",
            "2025-26",
            "WDV",
            "115BAA",
            25.168,
            940276.0,
            "Plot 42, Peenya Industrial Area Phase II, Bengaluru / Kochi Operations"
        ))
        c1_id = cur.lastrowid

        sample_assets_c1 = [
            ("AST-001", "5-Axis CNC Machining Center (Haas VF-4)", "Plant & Machinery (General)", "Plant & Machinery (15%)", "2025-05-15", 8500000, 8500000, 8500000, 15, 5.0, 2, 1, 0),
            ("AST-002", "Robotic Laser Welding Line (Added Nov)", "Plant & Machinery (General)", "Plant & Machinery (15%)", "2025-11-20", 4200000, 4200000, 4200000, 15, 5.0, 1, 1, 0),
            ("AST-003", "Main Factory Building (Peenya Phase II)", "Building (Factory)", "Building - Factory (10%)", "2022-04-01", 25000000, 22625000, 18225000, 30, 5.0, 1, 0, 0),
            ("AST-004", "Enterprise ERP Servers & Rack Cluster", "Servers & Networks", "Computers & Software (40%)", "2025-06-10", 1800000, 1800000, 1800000, 6, 5.0, 1, 0, 0),
            ("AST-005", "Engineering Workstations & Laptops (25 Units)", "Computers & Laptops", "Computers & Software (40%)", "2025-10-25", 1500000, 1500000, 1500000, 3, 5.0, 1, 0, 0),
            ("AST-006", "Modular Office Furniture & Conference Fitout", "Furniture & Fittings", "Furniture & Fittings (10%)", "2023-04-01", 1200000, 910800, 972000, 10, 5.0, 1, 0, 0),
            ("AST-007", "Executive Passenger Vehicle (Toyota Hycross)", "Motor Vehicles (Car)", "Motor Cars (15%)", "2024-04-01", 2800000, 1925560, 2380000, 8, 5.0, 1, 0, 0),
            ("AST-008", "Rooftop Industrial Solar Power Plant (150 kWp)", "Energy Saving / Solar", "Energy Saving Devices (40%)", "2025-07-15", 6000000, 6000000, 6000000, 15, 5.0, 1, 1, 0),
        ]
        for row in sample_assets_c1:
            cur.execute("""
                INSERT INTO assets (company_id, asset_code, name, co_category, it_block, put_to_use_date,
                                    original_cost, op_book_wdv, op_tax_wdv, useful_life, salvage_pct, shifts, eligible_addl_depr, disposal_proceeds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c1_id, *row))

        cur.execute("""
            INSERT INTO companies (code, name, cin, pan, tan, fy, co_method, tax_regime, effective_tax_rate, opening_dtl, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "CMP-002",
            "Malabar Spice & Marine Exports Ltd.",
            "L15490KL2015PLC038912",
            "AACCM5678K",
            "CHNM12345B",
            "2025-26",
            "SLM",
            "NORMAL_25",
            27.820,
            417300.0,
            "Willingdon Island, Kochi, Kerala - 682003"
        ))
        c2_id = cur.lastrowid

        sample_assets_c2 = [
            ("AST-101", "Automated Cold Storage & Blast Freezer Unit", "Plant & Machinery (General)", "Plant & Machinery (15%)", "2023-04-01", 12000000, 9500000, 8000000, 15, 5.0, 3, 1, 0),
            ("AST-102", "Spice Cryogenic Grinding Line", "Plant & Machinery (General)", "Plant & Machinery (15%)", "2025-08-01", 5500000, 5500000, 5500000, 15, 5.0, 2, 1, 0),
            ("AST-103", "Quality Control Lab & Mass Spectrometer", "Office Equipment", "Plant & Machinery (15%)", "2025-11-10", 2400000, 2400000, 2400000, 5, 5.0, 1, 0, 0),
        ]
        for row in sample_assets_c2:
            cur.execute("""
                INSERT INTO assets (company_id, asset_code, name, co_category, it_block, put_to_use_date,
                                    original_cost, op_book_wdv, op_tax_wdv, useful_life, salvage_pct, shifts, eligible_addl_depr, disposal_proceeds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c2_id, *row))

        self.conn.commit()

    def get_companies(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM companies ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]

    def get_company(self, company_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_company_fy(self, company_id, new_fy, new_op_dtl):
        cur = self.conn.cursor()
        cur.execute("UPDATE companies SET fy = ?, opening_dtl = ? WHERE id = ?", (new_fy, float(new_op_dtl), company_id))
        self.conn.commit()

    def save_company(self, data, company_id=None):
        cur = self.conn.cursor()
        if company_id:
            cur.execute("""
                UPDATE companies
                SET code=?, name=?, cin=?, pan=?, tan=?, fy=?, co_method=?, tax_regime=?, effective_tax_rate=?, opening_dtl=?, address=?
                WHERE id=?
            """, (
                data["code"], data["name"], data["cin"], data["pan"], data["tan"],
                data["fy"], data["co_method"], data["tax_regime"], float(data["effective_tax_rate"]),
                float(data["opening_dtl"]), data["address"], company_id
            ))
            self.conn.commit()
            return company_id
        else:
            cur.execute("""
                INSERT INTO companies (code, name, cin, pan, tan, fy, co_method, tax_regime, effective_tax_rate, opening_dtl, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["code"], data["name"], data["cin"], data["pan"], data["tan"],
                data["fy"], data["co_method"], data["tax_regime"], float(data["effective_tax_rate"]),
                float(data["opening_dtl"]), data["address"]
            ))
            self.conn.commit()
            return cur.lastrowid

    def delete_company(self, company_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM assets WHERE company_id = ?", (company_id,))
        cur.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        self.conn.commit()

    def get_assets(self, company_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM assets WHERE company_id = ? ORDER BY id ASC", (company_id,))
        return [dict(r) for r in cur.fetchall()]

    def save_asset(self, company_id, data, asset_id=None):
        cur = self.conn.cursor()
        if asset_id:
            cur.execute("""
                UPDATE assets
                SET asset_code=?, name=?, co_category=?, it_block=?, put_to_use_date=?,
                    original_cost=?, op_book_wdv=?, op_tax_wdv=?, useful_life=?, salvage_pct=?,
                    shifts=?, eligible_addl_depr=?, disposal_proceeds=?
                WHERE id=? AND company_id=?
            """, (
                data["asset_code"], data["name"], data["co_category"], data["it_block"], data["put_to_use_date"],
                float(data["original_cost"]), float(data["op_book_wdv"]), float(data["op_tax_wdv"]),
                int(data["useful_life"]), float(data["salvage_pct"]), int(data["shifts"]),
                1 if data["eligible_addl_depr"] else 0, float(data.get("disposal_proceeds", 0.0)),
                asset_id, company_id
            ))
        else:
            cur.execute("""
                INSERT INTO assets (company_id, asset_code, name, co_category, it_block, put_to_use_date,
                                    original_cost, op_book_wdv, op_tax_wdv, useful_life, salvage_pct, shifts, eligible_addl_depr, disposal_proceeds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, data["asset_code"], data["name"], data["co_category"], data["it_block"], data["put_to_use_date"],
                float(data["original_cost"]), float(data["op_book_wdv"]), float(data["op_tax_wdv"]),
                int(data["useful_life"]), float(data["salvage_pct"]), int(data["shifts"]),
                1 if data["eligible_addl_depr"] else 0, float(data.get("disposal_proceeds", 0.0))
            ))
        self.conn.commit()

    def delete_asset(self, asset_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        self.conn.commit()


class TaxShieldDesktopApp(tk.Tk):
    """Main Tkinter Desktop Application Window with Dynamic Multi-Year WDV Roll-Forward."""

    def __init__(self):
        super().__init__()
        self.title("TaxShield CA v3.0 — Multi-Company & Multi-Year WDV Roll-Forward Suite")
        self.geometry("1380x840")
        self.minsize(1120, 700)
        self.configure(bg="#f1f5f9")

        self.db = DatabaseManager()
        companies = self.db.get_companies()
        self.active_company_id = companies[0]["id"] if companies else None

        self._setup_styles()
        self._build_header()
        self._build_kpi_bar()
        self._build_notebook()
        self.refresh_all()

    def _setup_styles(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26, background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[14, 6])

    def _build_header(self):
        hdr = tk.Frame(self, bg="#0f172a", padx=16, pady=10)
        hdr.pack(fill=tk.X)

        left = tk.Frame(hdr, bg="#0f172a")
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="TaxShield CA — Multi-Year WDV Roll-Forward & Deferred Tax Suite",
            font=("Segoe UI", 13, "bold"),
            bg="#0f172a",
            fg="#ffffff"
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Change Financial Year to dynamically roll forward/backward Opening WDV, CY Depreciation, Closing WDV & DTL/DTA",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8"
        ).pack(anchor="w")

        right = tk.Frame(hdr, bg="#0f172a")
        right.pack(side=tk.RIGHT)

        tk.Label(right, text="Company:", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#cbd5e1").pack(side=tk.LEFT, padx=(0, 4))
        self.company_combo = ttk.Combobox(right, state="readonly", width=30, font=("Segoe UI", 9, "bold"))
        self.company_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.company_combo.bind("<<ComboboxSelected>>", self._on_company_switch)

        tk.Button(right, text="<< Prev FY", command=lambda: self._step_fy(-1), bg="#334155", fg="#ffffff", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, pady=4).pack(side=tk.LEFT, padx=2)
        self.fy_combo = ttk.Combobox(right, values=FY_LIST, state="readonly", width=10, font=("Segoe UI", 9, "bold"))
        self.fy_combo.pack(side=tk.LEFT, padx=2)
        self.fy_combo.bind("<<ComboboxSelected>>", self._on_fy_change)
        tk.Button(right, text="Next FY >>", command=lambda: self._step_fy(1), bg="#334155", fg="#ffffff", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, pady=4).pack(side=tk.LEFT, padx=(2, 8))

        tk.Button(
            right, text="Save Data", command=self._manual_save_feedback,
            bg="#059669", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            right, text="Export CSV", command=self._export_csv,
            bg="#1e293b", fg="#e2e8f0", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            right, text="Backup JSON", command=self._export_json,
            bg="#1e293b", fg="#e2e8f0", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=3)

    def _build_kpi_bar(self):
        bar = tk.Frame(self, bg="#f1f5f9", padx=16, pady=8)
        bar.pack(fill=tk.X)

        self.kpi_labels = {}
        cards = [
            ("book_depr", "Book Depreciation (Co. Act)", "#1d4ed8"),
            ("tax_depr", "Tax Depreciation (IT Act Sec 32)", "#b45309"),
            ("timing_diff", "CY Timing Difference (AS 22)", "#6d28d9"),
            ("closing_dtl", "Closing Net DTL / (DTA) (Ind AS 12)", "#047857"),
        ]
        for idx, (key, title, color) in enumerate(cards):
            frame = tk.Frame(bar, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=8)
            frame.grid(row=0, column=idx, sticky="nsew", padx=5)
            bar.grid_columnconfigure(idx, weight=1)
            tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#64748b").pack(anchor="w")
            val_lbl = tk.Label(frame, text="₹0", font=("Consolas", 15, "bold"), bg="#ffffff", fg=color)
            val_lbl.pack(anchor="w", pady=(2, 0))
            sub_lbl = tk.Label(frame, text="", font=("Segoe UI", 8), bg="#ffffff", fg="#475569")
            sub_lbl.pack(anchor="w")
            self.kpi_labels[key] = (val_lbl, sub_lbl)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.tab_company = tk.Frame(self.notebook, bg="#ffffff")
        self.tab_assets = tk.Frame(self.notebook, bg="#ffffff")
        self.tab_co_act = tk.Frame(self.notebook, bg="#ffffff")
        self.tab_it_act = tk.Frame(self.notebook, bg="#ffffff")
        self.tab_def_tax = tk.Frame(self.notebook, bg="#ffffff")

        self.notebook.add(self.tab_company, text=" 0. Company Master ")
        self.notebook.add(self.tab_assets, text=" 1. Fixed Asset Register (Dynamic FY WDV) ")
        self.notebook.add(self.tab_co_act, text=" 2. Companies Act (Sch II) ")
        self.notebook.add(self.tab_it_act, text=" 3. Income Tax Act (Sec 32) ")
        self.notebook.add(self.tab_def_tax, text=" 4. Deferred Tax & JVs ")

        self._init_company_tab()
        self._init_assets_tab()
        self._init_co_act_tab()
        self._init_it_act_tab()
        self._init_def_tax_tab()

    def _init_company_tab(self):
        top = tk.Frame(self.tab_company, bg="#ffffff", padx=14, pady=10)
        top.pack(fill=tk.X)
        tk.Label(top, text="Company Master Register — Add, Edit, Switch or Delete Companies", font=("Segoe UI", 11, "bold"), bg="#ffffff").pack(side=tk.LEFT)
        tk.Button(top, text="+ Add New Company", command=self._open_add_company_dialog, bg="#0f172a", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Edit Selected Company", command=self._open_edit_company_dialog, bg="#e2e8f0", fg="#0f172a", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Delete Selected Company", command=self._delete_selected_company, bg="#fee2e2", fg="#991b1b", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)

        cols = ("code", "name", "cin", "pan", "fy", "co_method", "tax_regime", "effective_tax_rate", "opening_dtl")
        self.tree_companies = ttk.Treeview(self.tab_company, columns=cols, show="headings", height=16)
        headers = {
            "code": ("Code", 90),
            "name": ("Company Name", 260),
            "cin": ("CIN", 170),
            "pan": ("PAN", 100),
            "fy": ("Selected FY", 100),
            "co_method": ("Co. Act Method", 110),
            "tax_regime": ("Tax Regime", 110),
            "effective_tax_rate": ("Eff. Tax Rate %", 110),
            "opening_dtl": ("Opening Net DTL (₹)", 140),
        }
        for col, (text, width) in headers.items():
            self.tree_companies.heading(col, text=text)
            self.tree_companies.column(col, width=width, anchor="w" if col in ("code", "name", "cin", "pan") else "center")
        self.tree_companies.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))
        self.tree_companies.bind("<Double-1>", lambda e: self._open_edit_company_dialog())

    def _init_assets_tab(self):
        top = tk.Frame(self.tab_assets, bg="#ffffff", padx=14, pady=10)
        top.pack(fill=tk.X)
        self.lbl_asset_tab_title = tk.Label(top, text="Fixed Asset Register — WDV Rolled Forward to Selected FY", font=("Segoe UI", 11, "bold"), bg="#ffffff")
        self.lbl_asset_tab_title.pack(side=tk.LEFT)
        tk.Button(top, text="+ Add Fixed Asset", command=self._open_add_asset_dialog, bg="#0f172a", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Edit Selected Asset", command=self._open_edit_asset_dialog, bg="#e2e8f0", fg="#0f172a", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Delete Selected Asset", command=self._delete_selected_asset, bg="#fee2e2", fg="#991b1b", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.RIGHT, padx=4)

        cols = ("asset_code", "name", "status", "put_to_use_date", "original_cost", "op_book_wdv", "book_depr", "cl_book_wdv", "op_tax_wdv", "tax_depr", "cl_tax_wdv")
        self.tree_assets = ttk.Treeview(self.tab_assets, columns=cols, show="headings", height=18)
        headers = {
            "asset_code": ("ID", 70),
            "name": ("Asset Description", 220),
            "status": ("FY Status", 110),
            "put_to_use_date": ("Put to Use", 90),
            "original_cost": ("Original Cost", 110),
            "op_book_wdv": ("FY Op. Book WDV", 115),
            "book_depr": ("FY Book Depr", 110),
            "cl_book_wdv": ("FY Cl. Book WDV", 115),
            "op_tax_wdv": ("FY Op. Tax WDV", 115),
            "tax_depr": ("FY Tax Depr", 110),
            "cl_tax_wdv": ("FY Cl. Tax WDV", 115),
        }
        for col, (text, width) in headers.items():
            self.tree_assets.heading(col, text=text)
            self.tree_assets.column(col, width=width, anchor="w" if col in ("asset_code", "name", "status", "put_to_use_date") else "e")
        self.tree_assets.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))
        self.tree_assets.bind("<Double-1>", lambda e: self._open_edit_asset_dialog())

    def _init_co_act_tab(self):
        cols = ("asset_code", "name", "c", "s", "op_book", "n", "co_base_rate", "shift_factor", "days_used", "book_depr", "closing_book_wdv")
        self.tree_co = ttk.Treeview(self.tab_co_act, columns=cols, show="headings", height=20)
        headers = {
            "asset_code": ("ID", 75),
            "name": ("Asset Name", 230),
            "c": ("Original Cost", 115),
            "s": ("5% Residual", 100),
            "op_book": ("FY Op. Book WDV", 120),
            "n": ("Life", 60),
            "co_base_rate": ("Base Rate %", 90),
            "shift_factor": ("Shift Mult.", 85),
            "days_used": ("Days Used", 85),
            "book_depr": ("FY Book Depr", 120),
            "closing_book_wdv": ("FY Cl. Book WDV", 120),
        }
        for col, (text, width) in headers.items():
            self.tree_co.heading(col, text=text)
            self.tree_co.column(col, width=width, anchor="w" if col in ("asset_code", "name") else "e")
        self.tree_co.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

    def _init_it_act_tab(self):
        cols = ("block_name", "rate_pct", "opening_wdv", "add_more_180", "add_less_180", "deductions", "normal_depr", "addl_depr", "total_depr", "closing_wdv")
        self.tree_it = ttk.Treeview(self.tab_it_act, columns=cols, show="headings", height=18)
        headers = {
            "block_name": ("Block of Assets (Sec 32)", 210),
            "rate_pct": ("Rate %", 70),
            "opening_wdv": ("FY Op. WDV", 120),
            "add_more_180": ("Add >=180d", 120),
            "add_less_180": ("Add <180d", 120),
            "deductions": ("Deductions", 100),
            "normal_depr": ("Normal Depr", 120),
            "addl_depr": ("Addl. Depr", 120),
            "total_depr": ("Total IT Depr", 125),
            "closing_wdv": ("FY Cl. WDV", 125),
        }
        for col, (text, width) in headers.items():
            self.tree_it.heading(col, text=text)
            self.tree_it.column(col, width=width, anchor="w" if col == "block_name" else "e")
        self.tree_it.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

    def _init_def_tax_tab(self):
        self.txt_def_tax = tk.Text(self.tab_def_tax, font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", padx=16, pady=14)
        self.txt_def_tax.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

    def _step_fy(self, delta):
        active_comp = self.db.get_company(self.active_company_id)
        if not active_comp:
            return
        curr_fy = active_comp["fy"]
        idx = FY_LIST.index(curr_fy) if curr_fy in FY_LIST else 3
        new_idx = max(0, min(len(FY_LIST) - 1, idx + delta))
        self.fy_combo.current(new_idx)
        self._on_fy_change()

    def _on_fy_change(self, _event=None):
        new_fy = self.fy_combo.get()
        active_comp = self.db.get_company(self.active_company_id)
        if not active_comp:
            return
        active_comp["fy"] = new_fy
        assets = self.db.get_assets(self.active_company_id)
        _, _, totals = compute_company_schedules(active_comp, assets)
        self.db.update_company_fy(self.active_company_id, new_fy, totals["derived_opening_dtl"])
        self.refresh_all()

    def refresh_all(self):
        companies = self.db.get_companies()
        if not companies:
            self.db.seed_sample_data()
            companies = self.db.get_companies()

        if not any(c["id"] == self.active_company_id for c in companies):
            self.active_company_id = companies[0]["id"]

        active_comp = self.db.get_company(self.active_company_id)
        assets = self.db.get_assets(self.active_company_id)
        comp_assets, it_blocks, totals = compute_company_schedules(active_comp, assets)

        combo_vals = [f"{c['code']} — {c['name']} ({c['fy']})" for c in companies]
        self.company_combo["values"] = combo_vals
        active_idx = next((i for i, c in enumerate(companies) if c["id"] == self.active_company_id), 0)
        self.company_combo.current(active_idx)

        if active_comp["fy"] in FY_LIST:
            self.fy_combo.current(FY_LIST.index(active_comp["fy"]))
        else:
            self.fy_combo.set(active_comp["fy"])

        self.lbl_asset_tab_title.config(
            text=f"Fixed Asset Register — {active_comp['name']} | WDV Rolled Forward to FY {active_comp['fy']}"
        )

        # Populate Company Tree
        self.tree_companies.delete(*self.tree_companies.get_children())
        for c in companies:
            self.tree_companies.insert("", tk.END, iid=str(c["id"]), values=(
                c["code"], c["name"], c["cin"], c["pan"], c["fy"],
                c["co_method"], c["tax_regime"], f"{float(c['effective_tax_rate']):.3f}%",
                format_inr(c["opening_dtl"])
            ))

        # Update KPI Cards
        self.kpi_labels["book_depr"][0].config(text=format_inr(totals["book_depr"]))
        self.kpi_labels["book_depr"][1].config(text=f"FY {active_comp['fy']} Op WDV: {format_inr(totals['op_book_wdv'])} -> Cl WDV: {format_inr(totals['closing_book_wdv'])}")

        self.kpi_labels["tax_depr"][0].config(text=format_inr(totals["total_it_depr"]))
        self.kpi_labels["tax_depr"][1].config(text=f"FY {active_comp['fy']} Op WDV: {format_inr(totals['op_tax_wdv'])} -> Cl WDV: {format_inr(totals['closing_tax_wdv'])}")

        self.kpi_labels["timing_diff"][0].config(text=format_inr(totals["timing_diff_cy"]))
        self.kpi_labels["timing_diff"][1].config(text=f"FY {active_comp['fy']} P&L Deferred Tax: {format_inr(totals['cy_dtl_impact'])}")

        self.kpi_labels["closing_dtl"][0].config(text=format_inr(totals["closing_net_dtl"]))
        self.kpi_labels["closing_dtl"][1].config(text=f"Op DTL: {format_inr(totals['derived_opening_dtl'])} | Temp Diff: {format_inr(totals['temp_diff_closing'])}")

        # Populate Asset Register Tree
        self.tree_assets.delete(*self.tree_assets.get_children())
        for a in comp_assets:
            self.tree_assets.insert("", tk.END, iid=str(a["id"]), values=(
                a["asset_code"], a["name"], a["status"], a["put_to_use_date"],
                format_inr(a["nominal_cost"]), format_inr(a["op_book"]), format_inr(a["book_depr"]),
                format_inr(a["closing_book_wdv"]), format_inr(a["op_tax"]), format_inr(a["total_it_depr"]),
                format_inr(a["closing_tax_wdv"])
            ))

        # Populate Co Act Tree
        self.tree_co.delete(*self.tree_co.get_children())
        for a in comp_assets:
            self.tree_co.insert("", tk.END, values=(
                a["asset_code"], a["name"], format_inr(a["c"]), format_inr(a["s"]),
                format_inr(a["op_book"]), f"{a['n']}y", f"{a['co_base_rate']:.2f}%",
                f"{a['shift_factor']:.1f}x", f"{a['days_used']}/{a['total_days_fy']}",
                format_inr(a["book_depr"]), format_inr(a["closing_book_wdv"])
            ))

        # Populate IT Act Tree
        self.tree_it.delete(*self.tree_it.get_children())
        for b in it_blocks:
            self.tree_it.insert("", tk.END, values=(
                b["block_name"], f"{b['rate_pct']:.0f}%", format_inr(b["opening_wdv"]),
                format_inr(b["add_more_180"]), format_inr(b["add_less_180"]),
                format_inr(b["deductions"]), format_inr(b["normal_depr"]),
                format_inr(b["addl_depr"]), format_inr(b["total_depr"]),
                format_inr(b["closing_wdv"])
            ))

        # Populate Deferred Tax & JV Summary
        self.txt_def_tax.delete("1.0", tk.END)
        rate_pct = float(active_comp["effective_tax_rate"])
        op_dtl = float(totals["derived_opening_dtl"])
        summary_lines = [
            f"==========================================================================================",
            f" DEFERRED TAX & JOURNAL VOUCHER REPORT — {active_comp['name']} (FY {active_comp['fy']})",
            f" CIN: {active_comp['cin']} | PAN: {active_comp['pan']} | Method: {active_comp['co_method']} | Tax Rate: {rate_pct:.3f}%",
            f"==========================================================================================",
            f"",
            f"A. AS 22 — INCOME STATEMENT (TIMING DIFFERENCE) APPROACH (FY {active_comp['fy']}):",
            f"   1. Total Tax Depreciation as per Income Tax Act (Sec 32)   : {format_inr(totals['total_it_depr']):>18}",
            f"   2. Less: Book Depreciation as per Companies Act (Sch II)   : {format_inr(totals['book_depr']):>18}",
            f"   3. Current Year Timing Difference (1 - 2)                  : {format_inr(totals['timing_diff_cy']):>18}",
            f"   4. Deferred Tax Charge / (Credit) for the Year (@ {rate_pct:.3f}%) : {format_inr(totals['cy_dtl_impact']):>18}",
            f"",
            f"B. IND AS 12 — BALANCE SHEET (TEMPORARY DIFFERENCE) APPROACH (FY {active_comp['fy']}):",
            f"   1. Closing Carrying Amount (Book WDV)                      : {format_inr(totals['closing_book_wdv']):>18}",
            f"   2. Less: Closing Tax Base (Income Tax Block WDV)           : {format_inr(totals['closing_tax_wdv']):>18}",
            f"   3. Closing Temporary Difference (CA - TB)                  : {format_inr(totals['temp_diff_closing']):>18}",
            f"   4. Closing Net DTL / (DTA) Required on Balance Sheet       : {format_inr(totals['closing_net_dtl']):>18}",
            f"   5. Less: Rolled-Forward Opening Net DTL / (DTA) Balance    : {format_inr(op_dtl):>18}",
            f"   6. Net Deferred Tax Expense / (Income) in P&L              : {format_inr(totals['closing_net_dtl'] - op_dtl):>18}",
            f"",
            f"C. STATUTORY ACCOUNTING JOURNAL ENTRIES (31-Mar-{active_comp['fy'].split('-')[0][:2]}{active_comp['fy'].split('-')[1]}):",
            f"   [JV #1] Depreciation & Amortisation Expense A/c (P&L) ... Dr.   {format_inr(totals['book_depr'])}",
            f"               To Accumulated Depreciation / PPE Block A/c (Cr.)       {format_inr(totals['book_depr'])}",
            f"",
            f"   [JV #2] {'Deferred Tax Expense A/c (P&L) ... Dr.' if totals['cy_dtl_impact'] >= 0 else 'Deferred Tax Asset / DTL Reversal A/c ... Dr.'}          {format_inr(abs(totals['cy_dtl_impact']))}",
            f"               To {'Deferred Tax Liability (DTL) A/c (B/S Cr.)' if totals['cy_dtl_impact'] >= 0 else 'Deferred Tax Income / Credit A/c (P&L Cr.)'}      {format_inr(abs(totals['cy_dtl_impact']))}",
        ]
        self.txt_def_tax.insert(tk.END, "\n".join(summary_lines))

    def _on_company_switch(self, _event=None):
        companies = self.db.get_companies()
        idx = self.company_combo.current()
        if 0 <= idx < len(companies):
            self.active_company_id = companies[idx]["id"]
            self.refresh_all()

    def _manual_save_feedback(self):
        self.db.conn.commit()
        messagebox.showinfo("Data Saved", f"All Company Master records and Fixed Assets are saved in '{DB_FILENAME}'.")

    def _open_add_company_dialog(self):
        self._company_dialog(None)

    def _open_edit_company_dialog(self):
        sel = self.tree_companies.selection()
        comp_id = int(sel[0]) if sel else self.active_company_id
        comp = self.db.get_company(comp_id)
        if comp:
            self._company_dialog(comp)

    def _company_dialog(self, comp=None):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Company Master" if comp else "Add New Company Master")
        dlg.geometry("480x500")
        dlg.grab_set()

        fields = [
            ("Company Code:", "code", comp["code"] if comp else f"CMP-00{len(self.db.get_companies()) + 1}"),
            ("Company Name:", "name", comp["name"] if comp else ""),
            ("CIN:", "cin", comp["cin"] if comp else "U28910KA2020PTC100001"),
            ("PAN:", "pan", comp["pan"] if comp else "AABCA0000A"),
            ("TAN:", "tan", comp["tan"] if comp else "BLRA00000A"),
            ("Financial Year (e.g. 2025-26):", "fy", comp["fy"] if comp else "2025-26"),
            ("Companies Act Method (WDV/SLM):", "co_method", comp["co_method"] if comp else "WDV"),
            ("Tax Regime (115BAA/115BAB/NORMAL_25):", "tax_regime", comp["tax_regime"] if comp else "115BAA"),
            ("Effective Tax Rate (%):","effective_tax_rate", str(comp["effective_tax_rate"]) if comp else "25.168"),
            ("Opening Net DTL/(DTA) (₹):", "opening_dtl", str(comp["opening_dtl"]) if comp else "0"),
            ("Registered Address:", "address", comp["address"] if comp else ""),
        ]
        entries = {}
        frm = tk.Frame(dlg, padx=16, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)
        for row_idx, (lbl, key, default_val) in enumerate(fields):
            tk.Label(frm, text=lbl, font=("Segoe UI", 9, "bold")).grid(row=row_idx, column=0, sticky="w", pady=4)
            ent = tk.Entry(frm, width=34, font=("Segoe UI", 9))
            ent.insert(0, default_val)
            ent.grid(row=row_idx, column=1, sticky="ew", pady=4, padx=(8, 0))
            entries[key] = ent

        def save():
            data = {k: e.get().strip() for k, e in entries.items()}
            if not data["code"] or not data["name"]:
                messagebox.showerror("Validation", "Company Code and Company Name are required.")
                return
            new_id = self.db.save_company(data, comp["id"] if comp else None)
            self.active_company_id = new_id
            dlg.destroy()
            self.refresh_all()

        tk.Button(frm, text="Save Company Master", command=save, bg="#0f172a", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=14, pady=6).grid(row=len(fields), column=0, columnspan=2, pady=14)

    def _delete_selected_company(self):
        companies = self.db.get_companies()
        if len(companies) <= 1:
            messagebox.showwarning("Cannot Delete", "At least one company must remain in the Company Master.")
            return
        sel = self.tree_companies.selection()
        comp_id = int(sel[0]) if sel else self.active_company_id
        comp = self.db.get_company(comp_id)
        if comp and messagebox.askyesno("Confirm Delete", f"Delete company '{comp['name']}' and all its fixed assets?"):
            self.db.delete_company(comp_id)
            self.refresh_all()

    def _open_add_asset_dialog(self):
        self._asset_dialog(None)

    def _open_edit_asset_dialog(self):
        sel = self.tree_assets.selection()
        if not sel:
            messagebox.showinfo("Select Asset", "Please select an asset row in Tab 1 first.")
            return
        asset_id = int(sel[0])
        assets = self.db.get_assets(self.active_company_id)
        asset = next((a for a in assets if a["id"] == asset_id), None)
        if asset:
            self._asset_dialog(asset)

    def _asset_dialog(self, asset=None):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Fixed Asset" if asset else "Add New Fixed Asset")
        dlg.geometry("500x520")
        dlg.grab_set()

        existing_count = len(self.db.get_assets(self.active_company_id))
        fields = [
            ("Asset Tag / Code:", "asset_code", asset["asset_code"] if asset else f"AST-00{existing_count + 1}"),
            ("Asset Description:", "name", asset["name"] if asset else ""),
            ("Co. Act Category:", "co_category", asset["co_category"] if asset else "Plant & Machinery (General)"),
            ("Income Tax Block:", "it_block", asset["it_block"] if asset else "Plant & Machinery (15%)"),
            ("Put to Use Date (YYYY-MM-DD):", "put_to_use_date", asset["put_to_use_date"] if asset else "2025-07-01"),
            ("Original Cost (₹):", "original_cost", str(asset["original_cost"]) if asset else "1000000"),
            ("Base Opening Book WDV (₹):", "op_book_wdv", str(asset["op_book_wdv"]) if asset else "1000000"),
            ("Base Opening Tax WDV (₹):", "op_tax_wdv", str(asset["op_tax_wdv"]) if asset else "1000000"),
            ("Useful Life (Years):", "useful_life", str(asset["useful_life"]) if asset else "15"),
            ("Residual Value (%):", "salvage_pct", str(asset["salvage_pct"]) if asset else "5.0"),
            ("Shifts Worked (1 / 2 / 3):", "shifts", str(asset["shifts"]) if asset else "1"),
            ("Eligible Addl Depr (Yes/No):", "eligible_addl_depr", "Yes" if (asset and asset["eligible_addl_depr"]) or not asset else "No"),
            ("Disposal Proceeds (₹):", "disposal_proceeds", str(asset.get("disposal_proceeds", 0.0)) if asset else "0"),
        ]
        entries = {}
        frm = tk.Frame(dlg, padx=16, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)
        for idx, (lbl, key, val) in enumerate(fields):
            tk.Label(frm, text=lbl, font=("Segoe UI", 9, "bold")).grid(row=idx, column=0, sticky="w", pady=3)
            ent = tk.Entry(frm, width=32, font=("Segoe UI", 9))
            ent.insert(0, val)
            ent.grid(row=idx, column=1, sticky="ew", pady=3, padx=(8, 0))
            entries[key] = ent

        def save():
            data = {k: e.get().strip() for k, e in entries.items()}
            data["eligible_addl_depr"] = data["eligible_addl_depr"].lower() in ("yes", "true", "1", "y")
            self.db.save_asset(self.active_company_id, data, asset["id"] if asset else None)
            dlg.destroy()
            self.refresh_all()

        tk.Button(frm, text="Save Fixed Asset", command=save, bg="#0f172a", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=14, pady=6).grid(row=len(fields), column=0, columnspan=2, pady=14)

    def _delete_selected_asset(self):
        sel = self.tree_assets.selection()
        if not sel:
            messagebox.showinfo("Select Asset", "Please select a fixed asset row to delete.")
            return
        asset_id = int(sel[0])
        if messagebox.askyesno("Confirm Delete", "Delete the selected fixed asset?"):
            self.db.delete_asset(asset_id)
            self.refresh_all()

    def _export_csv(self):
        comp = self.db.get_company(self.active_company_id)
        assets = self.db.get_assets(self.active_company_id)
        comp_assets, _, _ = compute_company_schedules(comp, assets)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"{comp['code']}_Depreciation_Schedule_{comp['fy']}.csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Company Code", "Company Name", "Financial Year", "Asset Code", "Asset Name", "FY Status",
                "Co Act Category", "IT Block", "Put to Use Date", "Original Cost",
                "FY Op Book WDV", "FY Book Depr", "FY Closing Book WDV",
                "FY Op Tax WDV", "FY Normal IT Depr", "FY Addl IT Depr", "FY Total IT Depr", "FY Closing Tax WDV",
                "FY Timing Diff", "FY DTL Impact", "FY Closing Temp Diff", "FY Closing Net DTL"
            ])
            for a in comp_assets:
                writer.writerow([
                    comp["code"], comp["name"], comp["fy"], a["asset_code"], a["name"], a["status"],
                    a["co_category"], a["it_block"], a["put_to_use_date"], round(a["nominal_cost"]),
                    round(a["op_book"]), round(a["book_depr"]), round(a["closing_book_wdv"]),
                    round(a["op_tax"]), round(a["normal_it_depr"]), round(a["addl_it_depr"]), round(a["total_it_depr"]), round(a["closing_tax_wdv"]),
                    round(a["timing_diff_cy"]), round(a["cy_dtl_impact"]), round(a["temp_diff_closing"]), round(a["closing_net_dtl"])
                ])
        messagebox.showinfo("Export Complete", f"Saved CSV schedule for FY {comp['fy']} to:\n{path}")

    def _export_json(self):
        companies = self.db.get_companies()
        payload = {"companies": []}
        for c in companies:
            c_copy = dict(c)
            c_copy["assets"] = self.db.get_assets(c["id"])
            payload["companies"].append(c_copy)
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="taxshield_ca_full_backup.json",
            filetypes=[("JSON Database Backup", "*.json")]
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        messagebox.showinfo("Backup Complete", f"Saved full multi-company JSON backup to:\n{path}")


if __name__ == "__main__":
    app = TaxShieldDesktopApp()
    app.mainloop()
