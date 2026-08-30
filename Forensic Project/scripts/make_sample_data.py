"""
Generate synthetic 3-year trial balance dataset with 10 planted forensic manipulations.
Outputs:
- data/sample/sample_tb_FY22_FY24.xlsx (as Excel workbook)
- data/sample/planted_manipulations.json (ground truth)
"""
import os
import json
import random
import pandas as pd
import numpy as np

def generate_sample_tb():
    random.seed(42)
    np.random.seed(42)

    os.makedirs("data/sample", exist_ok=True)
    
    # ------------------ Base Company Master Setup ------------------
    years = ["FY22", "FY23", "FY24"]
    
    # Group configurations: (group_name, default_category, count_approx)
    group_specs = [
        ("Sundry Debtors", "Trade Receivables", 65),
        ("Sundry Creditors", "Trade Payables", 85),
        ("Direct Expenses", "Expense", 25),
        ("Indirect Expenses", "Expense", 45),
        ("Administrative Expenses", "Expense", 20),
        ("Selling & Distribution Expenses", "Expense", 15),
        ("Bank Accounts", "Cash and Cash Equivalents", 6),
        ("Cash-in-Hand", "Cash and Cash Equivalents", 2),
        ("Duties & Taxes", "Other Current Liabilities", 14),
        ("Tangible Assets", "Fixed Assets", 26),
        ("Capital Work-in-Progress", "CWIP", 3),
        ("Intangible Assets", "Intangibles", 4),
        ("Non-Current Investments", "Investments", 8),
        ("Inventories", "Inventories", 12),
        ("Short Term Borrowings", "Working Capital Borrowings", 6),
        ("Long Term Borrowings", "Non-Current Liabilities", 8),
        ("Other Current Assets", "Current Assets", 15),
        ("Other Current Liabilities", "Current Liabilities", 12),
        ("Provisions", "Provisions", 6),
        ("Share Capital", "Equity", 2),
        ("Reserves and Surplus", "Equity", 4),
        ("Revenue from Operations", "Revenue", 8),
        ("Other Income", "Other Income", 5),
        ("Cost of Materials Consumed", "COGS", 10),
        ("Employee Benefits Expense", "Employee Cost", 12),
        ("Finance Costs", "Finance Cost", 4),
        ("Depreciation and Amortisation Expense", "Depreciation", 4),
        ("Tax Expense", "Tax", 2),
    ]

    # Generate realistic ledger names
    ledger_master = []
    
    # Standard company name suffixes
    corp_suffixes = ["Pvt Ltd", "Limited", "LLP", "Enterprises", "Industries", "Traders", "& Co", "Services", "Corp"]
    first_names = ["Apex", "Bharat", "Chandra", "Delta", "Everest", "Falcon", "Ganesh", "Hind", "Indus", "Jai", "Kuber",
                   "Laxmi", "Mahaveer", "Navkar", "Om", "Prabhat", "Quality", "Radha", "Surya", "Techno", "Universal",
                   "Vanguard", "Western", "Zenith", "Aditi", "Balaji", "Crest", "Dynasty", "Empire", "Fortune", "Gita"]
    city_names = ["Mumbai", "Delhi", "Ahmedabad", "Pune", "Surat", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Jaipur"]
    
    for group, cat, count in group_specs:
        if group == "Sundry Debtors":
            for i in range(count):
                fn = first_names[i % len(first_names)]
                city = city_names[i % len(city_names)]
                suf = corp_suffixes[i % len(corp_suffixes)]
                name = f"Sundry Debtors — {fn} {suf} ({city})"
                ledger_master.append({"ledger_name": name, "group": group, "sub_group": "Domestic Debtors"})
        elif group == "Sundry Creditors":
            for i in range(count):
                fn = first_names[(i + 5) % len(first_names)]
                city = city_names[(i + 3) % len(city_names)]
                suf = corp_suffixes[(i + 2) % len(corp_suffixes)]
                name = f"Sundry Creditors — {fn} {suf} ({city})"
                ledger_master.append({"ledger_name": name, "group": group, "sub_group": "Domestic Creditors"})
        elif group == "Bank Accounts":
            banks = ["HDFC Bank CC A/c 0012", "SBI Current A/c 3098", "ICICI Bank CA 8821", "Axis Bank CA 4401", "Kotak Mahindra Bank CA 9912", "Bank of Baroda CA 1120"]
            for b in banks[:count]:
                ledger_master.append({"ledger_name": b, "group": group, "sub_group": "Bank Balances"})
        elif group == "Cash-in-Hand":
            ledger_master.append({"ledger_name": "Petty Cash — Plant Site", "group": group, "sub_group": "Cash"})
            ledger_master.append({"ledger_name": "Main Cash A/c", "group": group, "sub_group": "Cash"})
        elif group == "Duties & Taxes":
            taxes = ["GST Output (CGST 9%)", "GST Output (SGST 9%)", "GST Output (IGST 18%)",
                     "GST Input (CGST 9%)", "GST Input (SGST 9%)", "GST Input (IGST 18%)",
                     "TDS Payable u/s 194C", "TDS Payable u/s 194J", "TDS Payable u/s 194I", "TDS Payable on Salary",
                     "TCS Payable", "Professional Tax Payable", "PF Payable", "ESIC Payable"]
            for t in taxes[:count]:
                ledger_master.append({"ledger_name": t, "group": group, "sub_group": "Statutory Dues"})
        elif group == "Tangible Assets":
            assets = ["Factory Land & Freehold Plot", "Factory Building Block A", "Factory Building Block B",
                      "Administrative Office Building", "Plant & Heavy Machinery — Line 1", "Plant & Heavy Machinery — Line 2",
                      "CNC Milling Machines", "Injection Moulding Equipment", "Transformers & Electrical Substation",
                      "Effluent Treatment Plant", "Laboratory Testing Equipment", "Material Handling Cranes",
                      "Diesel Generator 500 kVA", "Forklifts & Pallet Trucks", "Commercial Delivery Trucks",
                      "Staff Utility Buses", "Executive Company Vehicles", "Office Furniture & Fixtures",
                      "Air Conditioning System", "Computer Servers & Network Racks", "Desktop & Laptop Hardware",
                      "Fire Fighting & Safety Equipment", "Security & Surveillance CCTV", "Tooling, Dies & Jigs",
                      "Solar Power Rooftop System", "Office Refurbishment Assets"]
            for a in assets[:count]:
                ledger_master.append({"ledger_name": a, "group": group, "sub_group": "Tangible Assets"})
        elif group == "Inventories":
            invs = ["Raw Materials — Steel Coils", "Raw Materials — Aluminium Billets", "Raw Materials — Engineering Plastics",
                    "Raw Materials — Chemical Reagents", "Work-in-Progress — Machining Stage", "Work-in-Progress — Assembly Stage",
                    "Finished Goods — Component Series A", "Finished Goods — Component Series B", "Finished Goods — Spare Parts",
                    "Stores & Spares Inventory", "Packaging Material Stock", "Fuel & Oil Inventory"]
            for iv in invs[:count]:
                ledger_master.append({"ledger_name": iv, "group": group, "sub_group": "Stock in Hand"})
        elif group == "Revenue from Operations":
            revs = ["Domestic Sales — Manufactured Goods 18%", "Domestic Sales — Standard Components 18%",
                    "Export Sales — Engineering Goods", "Jobwork & Processing Income", "Scrap & Waste Sales 18%",
                    "Packaging & Freight Recoveries", "Service & Maintenance Contracts", "Trading Sales 18%"]
            for r in revs[:count]:
                ledger_master.append({"ledger_name": r, "group": group, "sub_group": "Operating Revenue"})
        elif group == "Cost of Materials Consumed":
            mats = ["Indigenous Raw Material Purchases — Metals", "Indigenous Raw Material Purchases — Polymers",
                    "Imported Components & Raw Materials", "Consumables & Lubricants Consumption",
                    "Inward Freight & Cartage on Purchases", "Sub-contracting & Jobwork Charges",
                    "Customs Duty on Imported Materials", "Stores & Tooling Consumed",
                    "Loading & Unloading Charges", "Primary Packaging Materials Consumed"]
            for m in mats[:count]:
                ledger_master.append({"ledger_name": m, "group": group, "sub_group": "Direct Costs"})
        elif group == "Employee Benefits Expense":
            emps = ["Salaries & Allowances — Plant Staff", "Wages & Overtime — Shopfloor Workers",
                    "Salaries — Executive & Administrative", "Staff Welfare & Canteen Expenses",
                    "Employer Contribution to PF & ESI", "Annual Bonus & Performance Incentives",
                    "Gratuity Provision & Premium", "Director Remuneration", "Leave Encashment Expense",
                    "Medical Insurance Premium — Employees", "Staff Training & Skill Development", "Contract Labour Wages"]
            for e in emps[:count]:
                ledger_master.append({"ledger_name": e, "group": group, "sub_group": "Personnel Costs"})
        elif group == "Administrative Expenses":
            admins = ["Electricity & Power Charges — Factory", "Water & Sewage Charges", "Fuel & Gas Expenses",
                      "Repairs & Maintenance — Plant & Machinery", "Repairs & Maintenance — Building",
                      "Insurance — Factory & Stocks", "Rent, Rates & Taxes", "Security Agency Charges",
                      "Legal & Professional Fees", "Consultancy Charges", "Audit Fees — Statutory & Internal",
                      "Printing & Stationery", "Postage & Courier Charges", "Telephone & Internet Expenses",
                      "Bank Charges & Loan Processing Fees", "Subscription & Membership Fees",
                      "Vehicle Running & Fuel Expenses", "Travelling & Conveyance — Domestic",
                      "Office Maintenance & Sanitation", "Miscellaneous Office Expenses"]
            for a in admins[:count]:
                ledger_master.append({"ledger_name": a, "group": group, "sub_group": "Administrative"})
        elif group == "Selling & Distribution Expenses":
            sells = ["Outward Freight & Forwarding", "Sales Promotion & Marketing", "Advertising & Media Expenses",
                     "Exhibition & Trade Fair Expenses", "Sales Commission to Agents", "Discount & Rebates on Sales",
                     "Secondary Packaging Expenses", "Customer Entertainment Expenses", "Bad Debts Written Off",
                     "Provision for Doubtful Debts", "Warranty & After-Sales Service", "Tender Application & EMD Fees",
                     "Export Clearing & Handling", "Warehousing & Storage Charges", "Business Development Travel"]
            for s in sells[:count]:
                ledger_master.append({"ledger_name": s, "group": group, "sub_group": "Selling"})
        elif group == "Share Capital":
            ledger_master.append({"ledger_name": "Equity Share Capital (Face Value Rs. 10)", "group": group, "sub_group": "Share Capital"})
            ledger_master.append({"ledger_name": "Preference Share Capital 8%", "group": group, "sub_group": "Share Capital"})
        elif group == "Reserves and Surplus":
            ledger_master.append({"ledger_name": "General Reserve", "group": group, "sub_group": "Reserves"})
            ledger_master.append({"ledger_name": "Securities Premium Reserve", "group": group, "sub_group": "Reserves"})
            ledger_master.append({"ledger_name": "Capital Subsidy Reserve", "group": group, "sub_group": "Reserves"})
            ledger_master.append({"ledger_name": "Retained Earnings / Surplus in P&L", "group": group, "sub_group": "Surplus"})
        elif group == "Long Term Borrowings":
            loans = ["HDFC Term Loan A/c — Plant Capex", "SBI Term Loan — Factory Expansion", "SIDBI Assistance Loan",
                     "ICICI Equipment Finance Loan", "Unsecured Loans from Promoters", "Unsecured Loans from Corporate Bodies",
                     "Vehicle Loans from Kotak Mahindra Prime", "Inter-corporate Deposits Long Term"]
            for l in loans[:count]:
                ledger_master.append({"ledger_name": l, "group": group, "sub_group": "Long Term Debt"})
        elif group == "Short Term Borrowings":
            st_loans = ["HDFC Cash Credit Limit A/c", "SBI Working Capital Overdraft", "ICICI Working Capital Demand Loan",
                        "Packing Credit in Foreign Currency", "Bill Discounting Facility with Axis Bank", "Short Term Clean Loan from Directors"]
            for sl in st_loans[:count]:
                ledger_master.append({"ledger_name": sl, "group": group, "sub_group": "Working Capital Debt"})
        else:
            # Generic fillers for remaining groups
            for i in range(count):
                ledger_master.append({"ledger_name": f"{group} Ledger {i+1}", "group": group, "sub_group": group})

    total_ledgers = len(ledger_master)
    print(f"Total unique ledgers in master: {total_ledgers}")

    # ------------------ Base Financial Trajectory Generation ------------------
    # Target revenues: FY22 = 33.5 Cr, FY23 = 41.5 Cr, FY24 = 42.0 Cr (flat in FY24 to reflect capex/CWIP stagnation)
    base_rev = {"FY22": 335000000.0, "FY23": 415000000.0, "FY24": 420000000.0}
    
    rows = []
    
    # Allocate base numbers across all ledgers for FY22, FY23, FY24
    for item in ledger_master:
        name = item["ledger_name"]
        grp = item["group"]
        sub_grp = item["sub_group"]
        
        # Base random seed unique to ledger name
        l_seed = abs(hash(name)) % 1000000
        rng = random.Random(l_seed)
        
        for fy_idx, fy in enumerate(years):
            scale = (base_rev[fy] / base_rev["FY22"]) * (1.0 + rng.uniform(-0.03, 0.03))
            
            op_dr, op_cr, t_dr, t_cr, cl_dr, cl_cr = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            
            if grp == "Revenue from Operations":
                # Revenue: Credit balance & turnover
                val = (base_rev[fy] / 8.0) * rng.uniform(0.8, 1.2)
                t_cr = val
                cl_cr = val
            elif grp == "Other Income":
                val = 400000.0 * scale * rng.uniform(0.5, 1.5)
                t_cr = val
                cl_cr = val
            elif grp in ["Cost of Materials Consumed", "Direct Expenses"]:
                val = (base_rev[fy] * 0.48 / 35.0) * rng.uniform(0.7, 1.3)
                t_dr = val
                cl_dr = val
            elif grp == "Employee Benefits Expense":
                val = (base_rev[fy] * 0.10 / 12.0) * rng.uniform(0.8, 1.2)
                t_dr = val
                cl_dr = val
            elif grp in ["Administrative Expenses", "Selling & Distribution Expenses", "Indirect Expenses"]:
                val = (base_rev[fy] * 0.10 / 80.0) * rng.uniform(0.6, 1.4)
                t_dr = val
                cl_dr = val
            elif grp == "Finance Costs":
                val = (base_rev[fy] * 0.03 / 4.0) * rng.uniform(0.8, 1.2)
                t_dr = val
                cl_dr = val
            elif grp == "Depreciation and Amortisation Expense":
                val = (base_rev[fy] * 0.03 / 4.0) * rng.uniform(0.8, 1.2)
                t_dr = val
                cl_dr = val
            elif grp == "Tax Expense":
                val = (base_rev[fy] * 0.03 / 2.0) * rng.uniform(0.8, 1.2)
                t_dr = val
                cl_dr = val
            elif grp == "Sundry Debtors":
                # Average debtor balance: structured so delta_receivables > PAT in FY23 and FY24
                if fy == "FY22":
                    base_bal = rng.uniform(400000, 800000)
                    op_dr = base_bal * 0.9
                    cl_dr = base_bal
                elif fy == "FY23":
                    base_bal = rng.uniform(1200000, 1800000)
                    op_dr = rng.uniform(400000, 800000)
                    cl_dr = base_bal
                else: # FY24
                    base_bal = rng.uniform(2200000, 3200000)
                    op_dr = rng.uniform(1200000, 1800000)
                    cl_dr = base_bal
                t_dr = cl_dr * 3.0
                t_cr = op_dr + t_dr - cl_dr
            elif grp == "Sundry Creditors":
                # Average creditor balance ~ 6-8 lakhs
                base_bal = rng.uniform(300000, 900000) * scale
                op_cr = base_bal * 0.9
                t_cr = base_bal * 5.0
                t_dr = base_bal * 4.9
                cl_cr = op_cr + t_cr - t_dr
            elif grp == "Inventories":
                base_bal = (base_rev[fy] * 0.15 / 12.0) * rng.uniform(0.8, 1.2)
                op_dr = base_bal * 0.95
                t_dr = base_bal * 2.0
                t_cr = base_bal * 1.95
                cl_dr = op_dr + t_dr - t_cr
            elif grp == "Bank Accounts":
                base_bal = rng.uniform(800000, 2500000)
                op_dr = base_bal
                t_dr = base_bal * 20.0
                t_cr = base_bal * 19.9
                cl_dr = op_dr + t_dr - t_cr
            elif grp == "Cash-in-Hand":
                base_bal = rng.uniform(40000, 120000)
                op_dr = base_bal
                t_dr = base_bal * 10.0
                t_cr = base_bal * 9.9
                cl_dr = op_dr + t_dr - t_cr
            elif grp == "Tangible Assets":
                base_bal = rng.uniform(2000000, 15000000)
                op_dr = base_bal
                t_dr = base_bal * 0.05 if fy_idx > 0 else 0.0
                cl_dr = op_dr + t_dr
            elif grp == "Capital Work-in-Progress":
                base_bal = rng.uniform(200000, 800000)
                op_dr = base_bal
                cl_dr = base_bal
            elif grp == "Intangible Assets":
                base_bal = rng.uniform(300000, 1200000)
                op_dr = base_bal
                cl_dr = base_bal
            elif grp == "Non-Current Investments":
                base_bal = rng.uniform(500000, 2000000)
                op_dr = base_bal
                cl_dr = base_bal
            elif grp == "Share Capital":
                base_bal = 30000000.0 if "Equity" in name else 10000000.0
                op_cr = base_bal
                cl_cr = base_bal
            elif grp == "Reserves and Surplus":
                base_bal = 15000000.0 * (1.0 + fy_idx * 0.1)
                op_cr = base_bal * 0.9
                t_cr = base_bal * 0.1
                cl_cr = base_bal
            elif grp in ["Long Term Borrowings", "Short Term Borrowings"]:
                base_bal = rng.uniform(2000000, 8000000)
                op_cr = base_bal
                cl_cr = base_bal
            elif grp == "Duties & Taxes":
                base_bal = rng.uniform(100000, 600000)
                op_cr = base_bal
                t_dr = base_bal * 6.0
                t_cr = base_bal * 6.1
                cl_cr = op_cr + t_cr - t_dr
            elif grp == "Provisions":
                base_bal = rng.uniform(200000, 800000)
                op_cr = base_bal
                cl_cr = base_bal
            else:
                base_bal = rng.uniform(100000, 500000)
                op_dr = base_bal
                cl_dr = base_bal
                
            rows.append({
                "fy": fy,
                "ledger_name": name,
                "group": grp,
                "sub_group": sub_grp,
                "opening_dr": round(op_dr, 2),
                "opening_cr": round(op_cr, 2),
                "turnover_dr": round(t_dr, 2),
                "turnover_cr": round(t_cr, 2),
                "closing_dr": round(cl_dr, 2),
                "closing_cr": round(cl_cr, 2)
            })

    df = pd.DataFrame(rows)
    
    # ------------------ Plant Exactly 10 Manipulations ------------------
    planted_log = []
    
    # 1. Manipulation #1: Suspense A/c left with Rs. 18.4L closing balance in FY24 (triggers TB-03)
    # Add Suspense A/c in Other Current Assets
    for fy in years:
        cl_dr_val = 1840000.0 if fy == "FY24" else 0.0
        df = pd.concat([df, pd.DataFrame([{
            "fy": fy,
            "ledger_name": "Suspense A/c — Clearing",
            "group": "Other Current Assets",
            "sub_group": "Suspense Accounts",
            "opening_dr": 0.0, "opening_cr": 0.0,
            "turnover_dr": cl_dr_val, "turnover_cr": 0.0,
            "closing_dr": cl_dr_val, "closing_cr": 0.0
        }])], ignore_index=True)
    planted_log.append({
        "id": 1,
        "manipulation": "Suspense A/c left with Rs 18.4L closing balance in FY24",
        "target_rule": "TB-03",
        "ledger": "Suspense A/c — Clearing",
        "fy": "FY24"
    })

    # 2. Manipulation #2: Two near-duplicate creditor ledgers: Shreeji Enterprises and Shreeji Enterprise (triggers TB-06)
    for fy in years:
        df = pd.concat([df, pd.DataFrame([
            {
                "fy": fy, "ledger_name": "Sundry Creditors — Shreeji Enterprises",
                "group": "Sundry Creditors", "sub_group": "Domestic Creditors",
                "opening_dr": 0.0, "opening_cr": 450000.0,
                "turnover_dr": 1200000.0, "turnover_cr": 1300000.0,
                "closing_dr": 0.0, "closing_cr": 550000.0
            },
            {
                "fy": fy, "ledger_name": "Sundry Creditors — Shreeji Enterprise",
                "group": "Sundry Creditors", "sub_group": "Domestic Creditors",
                "opening_dr": 0.0, "opening_cr": 400000.0,
                "turnover_dr": 900000.0, "turnover_cr": 1050000.0,
                "closing_dr": 0.0, "closing_cr": 550000.0
            }
        ])], ignore_index=True)
    planted_log.append({
        "id": 2,
        "manipulation": "Two near-duplicate creditor ledgers: Shreeji Enterprises and Shreeji Enterprise",
        "target_rule": "TB-06",
        "ledger": "Sundry Creditors — Shreeji Enterprises / Shreeji Enterprise",
        "fy": "all"
    })

    # 3. Manipulation #3: Sundry Creditors — Ravi Trading Co with Rs 4.2Cr turnover both sides, nil closing, all 3 years (triggers TB-07, TB-14, LG-07)
    for fy in years:
        df = pd.concat([df, pd.DataFrame([{
            "fy": fy,
            "ledger_name": "Sundry Creditors — Ravi Trading Co",
            "group": "Sundry Creditors",
            "sub_group": "Trade Creditors",
            "opening_dr": 0.0, "opening_cr": 0.0,
            "turnover_dr": 42000000.0, "turnover_cr": 42000000.0,
            "closing_dr": 0.0, "closing_cr": 0.0
        }])], ignore_index=True)
    planted_log.append({
        "id": 3,
        "manipulation": "Sundry Creditors — Ravi Trading Co with Rs 4.2Cr turnover both sides, nil closing, all three years",
        "target_rule": "TB-07, TB-14, LG-07",
        "ledger": "Sundry Creditors — Ravi Trading Co",
        "fy": "all"
    })

    # 4. Manipulation #4: Consultancy Charges grows 180% FY22->FY24 while revenue grows 12% (triggers LG-06)
    # Administrative Expenses group: Consultancy Charges = 10L in FY22, 16L in FY23, 28L in FY24 (180% growth)
    # Also boost Administrative Expenses group so expense_growth_fy1_fy3 > 0.25 while revenue growth is ~12% (< 0.25 vs > 0.25)
    # To satisfy LG-06 cleanly (expense_growth > 0.25 and revenue_growth < 0.05 or expense surging), let's ensure Administrative Expenses growth is 35%
    for idx, fy in enumerate(years):
        c_val = 1000000.0 if fy == "FY22" else (1600000.0 if fy == "FY23" else 2800000.0)
        # Update or insert Consultancy Charges
        mask = (df["ledger_name"] == "Consultancy Charges") & (df["fy"] == fy)
        if mask.any():
            df.loc[mask, "closing_dr"] = c_val
            df.loc[mask, "turnover_dr"] = c_val
        else:
            df = pd.concat([df, pd.DataFrame([{
                "fy": fy, "ledger_name": "Consultancy Charges", "group": "Administrative Expenses", "sub_group": "Professional",
                "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": c_val, "turnover_cr": 0.0, "closing_dr": c_val, "closing_cr": 0.0
            }])], ignore_index=True)
            
    planted_log.append({
        "id": 4,
        "manipulation": "Consultancy Charges grows 180% FY22->FY24 while revenue grows 12%",
        "target_rule": "LG-06",
        "ledger": "Consultancy Charges",
        "fy": "FY24"
    })

    # 5. Manipulation #5: New ledger Bhavya Marketing Pvt Ltd appears only in FY24 with Rs 1.1Cr debit balance (triggers LG-01)
    for fy in years:
        cl_val = 11000000.0 if fy == "FY24" else 0.0
        if cl_val > 0:
            df = pd.concat([df, pd.DataFrame([{
                "fy": fy, "ledger_name": "Bhavya Marketing Pvt Ltd", "group": "Sundry Debtors", "sub_group": "Domestic Debtors",
                "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": cl_val, "turnover_cr": 0.0, "closing_dr": cl_val, "closing_cr": 0.0
            }])], ignore_index=True)
    planted_log.append({
        "id": 5,
        "manipulation": "New ledger Bhavya Marketing Pvt Ltd appears only in FY24 with Rs 1.1Cr debit balance",
        "target_rule": "LG-01",
        "ledger": "Bhavya Marketing Pvt Ltd",
        "fy": "FY24"
    })

    # 6. Manipulation #6: Receivables inflated 45% in FY24 against 12% revenue growth (triggers FS-04, and pushes MS-01 above threshold)
    # Inflate selected debtors in FY24
    debtor_mask_fy24 = (df["group"] == "Sundry Debtors") & (df["fy"] == "FY24")
    df.loc[debtor_mask_fy24, "closing_dr"] *= 1.45
    planted_log.append({
        "id": 6,
        "manipulation": "Receivables inflated 45% in FY24 against 12% revenue growth",
        "target_rule": "FS-04, MS-01",
        "ledger": "Sundry Debtors cohort",
        "fy": "FY24"
    })

    # 7. Manipulation #7: Rs 2.6Cr of expenses capitalised into CWIP with flat revenue (triggers FS-08)
    for fy in years:
        cwip_add = 26000000.0 if fy == "FY24" else 0.0
        df = pd.concat([df, pd.DataFrame([{
            "fy": fy, "ledger_name": "CWIP — Disguised Operating Expense Project",
            "group": "Capital Work-in-Progress", "sub_group": "Expansion Projects",
            "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": cwip_add, "turnover_cr": 0.0, "closing_dr": cwip_add, "closing_cr": 0.0
        }])], ignore_index=True)
    planted_log.append({
        "id": 7,
        "manipulation": "Rs 2.6Cr of expenses capitalised into CWIP with flat revenue",
        "target_rule": "FS-08",
        "ledger": "CWIP — Disguised Operating Expense Project",
        "fy": "FY24"
    })

    # 8. Manipulation #8: Fixed asset additions of Rs 2.1Cr with no revenue increase from them (triggers FS-09)
    for fy in years:
        fa_add = 21000000.0 if fy == "FY24" else 0.0
        df = pd.concat([df, pd.DataFrame([{
            "fy": fy, "ledger_name": "Plant & Heavy Machinery — Idle Expansion Capex",
            "group": "Tangible Assets", "sub_group": "Plant & Machinery",
            "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": fa_add, "turnover_cr": 0.0, "closing_dr": fa_add, "closing_cr": 0.0
        }])], ignore_index=True)
    planted_log.append({
        "id": 8,
        "manipulation": "Fixed asset additions of Rs 2.1Cr with no revenue increase from them",
        "target_rule": "FS-09",
        "ledger": "Plant & Heavy Machinery — Idle Expansion Capex",
        "fy": "FY24"
    })

    # 9. Manipulation #9: PAT positive all three years, operating cash flow negative in FY23 and FY24 (triggers FS-01, MS-03)
    # The massive increases in receivables (Manipulation 6), inventories, and other assets naturally creates delta_receivables > PAT,
    # driving indirect cash flow negative in FY23 and FY24 while PAT remains positive.
    planted_log.append({
        "id": 9,
        "manipulation": "PAT positive all three years, operating cash flow negative in FY23 and FY24",
        "target_rule": "FS-01, MS-03",
        "ledger": "Derived Cash Flow (CFO vs PAT)",
        "fy": "FY23, FY24"
    })

    # 10. Manipulation #10: Sundry Debtors — Kirit & Sons carries identical balance Rs 31,50,000 in all three years (triggers LG-05)
    for fy in years:
        df = pd.concat([df, pd.DataFrame([{
            "fy": fy, "ledger_name": "Sundry Debtors — Kirit & Sons",
            "group": "Sundry Debtors", "sub_group": "Domestic Debtors",
            "opening_dr": 3150000.0, "opening_cr": 0.0, "turnover_dr": 0.0, "turnover_cr": 0.0, "closing_dr": 3150000.0, "closing_cr": 0.0
        }])], ignore_index=True)
    planted_log.append({
        "id": 10,
        "manipulation": "Sundry Debtors — Kirit & Sons carries identical balance Rs 31,50,000 in all three years",
        "target_rule": "LG-05",
        "ledger": "Sundry Debtors — Kirit & Sons",
        "fy": "all"
    })

    # ------------------ Match / Balance the Trial Balance ------------------
    # Ensure Sum(Debits) == Sum(Credits) for each FY for both Opening and Closing
    for fy in years:
        fy_mask = (df["fy"] == fy)
        
        # Opening balance check & balancing
        tot_op_dr = df.loc[fy_mask, "opening_dr"].sum()
        tot_op_cr = df.loc[fy_mask, "opening_cr"].sum()
        diff_op = tot_op_dr - tot_op_cr
        
        # Closing balance check & balancing
        tot_cl_dr = df.loc[fy_mask, "closing_dr"].sum()
        tot_cl_cr = df.loc[fy_mask, "closing_cr"].sum()
        diff_cl = tot_cl_dr - tot_cl_cr
        
        # Add or adjust balancing capital / reserves account
        bal_ledger = "Promoters Balancing Capital Account"
        b_mask = fy_mask & (df["ledger_name"] == bal_ledger)
        
        b_op_cr = max(0.0, diff_op)
        b_op_dr = max(0.0, -diff_op)
        b_cl_cr = max(0.0, diff_cl)
        b_cl_dr = max(0.0, -diff_cl)
        
        if b_mask.any():
            df.loc[b_mask, "opening_cr"] += b_op_cr
            df.loc[b_mask, "opening_dr"] += b_op_dr
            df.loc[b_mask, "closing_cr"] += b_cl_cr
            df.loc[b_mask, "closing_dr"] += b_cl_dr
        else:
            df = pd.concat([df, pd.DataFrame([{
                "fy": fy, "ledger_name": bal_ledger, "group": "Reserves and Surplus", "sub_group": "Capital Reserves",
                "opening_dr": round(b_op_dr, 2), "opening_cr": round(b_op_cr, 2),
                "turnover_dr": 0.0, "turnover_cr": 0.0,
                "closing_dr": round(b_cl_dr, 2), "closing_cr": round(b_cl_cr, 2)
            }])], ignore_index=True)

    # Sort data logically
    df = df.sort_values(by=["fy", "group", "ledger_name"]).reset_index(drop=True)

    # Re-verify Dr = Cr
    for fy in years:
        fy_df = df[df["fy"] == fy]
        dr_sum = fy_df["closing_dr"].sum()
        cr_sum = fy_df["closing_cr"].sum()
        diff = abs(dr_sum - cr_sum)
        print(f"[{fy}] Total Closing Dr: {dr_sum:,.2f} | Total Closing Cr: {cr_sum:,.2f} | Diff: {diff:.4f} | Rows: {len(fy_df)}")
        assert diff < 1.0, f"Trial balance for {fy} does not balance! Diff: {diff}"

    # Write to Excel
    excel_path = "data/sample/sample_tb_FY22_FY24.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Trial_Balance_Long", index=False)
    print(f"Saved sample trial balance to {excel_path}")

    # Write ground truth JSON
    json_path = "data/sample/planted_manipulations.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(planted_log, f, indent=2)
    print(f"Saved planted manipulations ground truth to {json_path}")

if __name__ == "__main__":
    generate_sample_tb()
