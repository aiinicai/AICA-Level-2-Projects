"""Generate demo input files (vendor master, bills, payments) for trying the tracker.

Usage: python make_demo_data.py [output_dir]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

out = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_data")
out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)

vendors = pd.DataFrame([
    ["Sri Lakshmi Plastics", "Micro", "V001", "ABCDE1234F", "UDYAM-TN-02-0012345", "2021-04-01", 30],
    ["Kaveri Packaging", "Small", "V002", "BCDEF2345G", "UDYAM-TN-02-0023456", "2020-07-15", None],
    ["Metro Metals Pvt Ltd", "Medium", "V003", "CDEFG3456H", "UDYAM-KA-03-0034567", "2019-01-10", 45],
    ["Global Components Ltd", "Not MSME", "V004", "DEFGH4567J", None, None, 60],
    ["Anand Die Casting", "Micro", "V005", "EFGHJ5678K", "UDYAM-TN-02-0045678", "2022-09-01", 45],
    ["Surya Cartons", "Small", "V006", "FGHJK6789L", "UDYAM-MH-14-0056789", "2023-02-20", 60],
], columns=["Vendor Name", "MSME Category", "Vendor ID", "PAN", "Udyam Number", "Udyam Registration Date", "Agreed Credit Days"])
vendors.to_csv(out / "vendor_master.csv", index=False)

bills, pays = [], []
n = 0
for _, v in vendors.iterrows():
    for _ in range(int(rng.integers(8, 14))):
        n += 1
        bd = pd.Timestamp("2025-10-01") + pd.Timedelta(days=int(rng.integers(0, 380)))
        amt = float(rng.integers(20, 400) * 1000)
        no = f"INV-{n:04d}"
        bills.append([no, v["Vendor Name"], bd, amt, None if rng.random() < 0.6 else bd + pd.Timedelta(days=int(rng.integers(1, 5))),
                      "Components", rng.choice(["Chennai", "Pune", "Cochin", "Hyderabad"])])
        r = rng.random()
        if r < 0.55:      # paid, sometimes late
            pdate = bd + pd.Timedelta(days=int(rng.integers(10, 80)))
            if pdate <= pd.Timestamp("2026-10-15"):
                pays.append([v["Vendor Name"], pdate, amt, no, f"UTR{n:06d}", "TReDS" if rng.random() < 0.2 else "Other"])
        elif r < 0.7:     # part paid
            pdate = bd + pd.Timedelta(days=int(rng.integers(10, 50)))
            if pdate <= pd.Timestamp("2026-10-15"):
                pays.append([v["Vendor Name"], pdate, round(amt * 0.4, 2), no, f"UTR{n:06d}", "TReDS" if rng.random() < 0.2 else "Other"])
bills = pd.DataFrame(bills, columns=["Bill No", "Vendor Name", "Bill Date", "Bill Amount", "Acceptance Date", "Description", "Branch"])
bills = bills[bills["Bill Date"] <= "2026-10-15"]
bills.to_csv(out / "bills.csv", index=False, date_format="%d-%m-%Y")
pd.DataFrame(pays, columns=["Vendor Name", "Payment Date", "Amount Paid", "Bill No", "Reference", "Payment Mode"]).to_csv(
    out / "payments.csv", index=False, date_format="%d-%m-%Y")
print(f"Wrote demo files to {out.resolve()}")
