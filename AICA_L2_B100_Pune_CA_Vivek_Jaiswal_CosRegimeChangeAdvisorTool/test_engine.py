"""
test_engine.py - Checks the engine against hand calculations.

Run:  python test_engine.py
Each expected figure below was worked out by hand (the working is in the
comments) so the report can show the engine reproduces a CA's own computation.
Add your own client cases in the same way.
"""
import pandas as pd

from engine import load, options, simulate

comp, proj = load("data/companies.csv", "data/projections.csv")
company = {r["entity"]: r for r in comp.to_dict("records")}
years = {e: proj[proj["entity"] == e].sort_values("year") for e in company}


def check(label, got, expected):
    status = "PASS" if got == expected else "FAIL"
    print(f"{status}  {label}: got {got:,}  expected {expected:,}")
    return status == "PASS"


results = []

# HoldCo, year 1, normal regime
# Income 8 cr; dividend deduction = min(5 cr received, 4 cr distributed) = 4 cr; total income 4 cr
# Normal: 4 cr x 25% x 1.07 surcharge x 1.04 cess = 1,11,28,000
# MAT: 9 cr x 15% x 1.07 x 1.04 = 1,50,22,800 -> MAT is higher, so tax = 1,50,22,800
# MAT credit: 4,00,00,000 b/f + (1,50,22,800 - 1,11,28,000) = 4,38,94,800
s = simulate(company["HoldCo (sample)"], years["HoldCo (sample)"], None)
results.append(check("HoldCo Y1 tax", s["Tax"][0], 15_022_800))
results.append(check("HoldCo Y1 MAT credit c/f", s["MAT credit c/f"][0], 43_894_800))

# HoldCo, year 2: total income 14 cr - 3 cr = 11 cr (surcharge 12%)
# Normal: 11 cr x 25% x 1.12 x 1.04 = 3,20,32,000; MAT: 11 cr x 15% x 1.12 x 1.04 = 1,92,19,200
# Credit used = min(4,38,94,800, 3,20,32,000 - 1,92,19,200 = 1,28,12,800) -> tax = 1,92,19,200
results.append(check("HoldCo Y2 tax", s["Tax"][1], 19_219_200))
results.append(check("HoldCo Y2 MAT credit c/f", s["MAT credit c/f"][1], 31_082_000))

# TradeCo, year 1: income 4 cr fully absorbed by 6 cr loss -> total income 0, loss c/f 2 cr
# MAT: 3 cr x 15% x 1.07 x 1.04 = 50,07,600
t = simulate(company["TradeCo (sample)"], years["TradeCo (sample)"], None)
results.append(check("TradeCo Y1 tax", t["Tax"][0], 5_007_600))
results.append(check("TradeCo Y1 loss c/f", t["Loss c/f"][0], 20_000_000))

# TradeCo switching in Y1: 2 cr of the 6 cr loss is blocked, so only 4 cr is set off -> total income 0
# Concessional tax on 0 = 0; Y2 income 4.5 cr, no loss left -> 4.5 cr x 22% x 1.10 x 1.04 = 1,13,25,600
t1 = simulate(company["TradeCo (sample)"], years["TradeCo (sample)"], 1)
results.append(check("TradeCo switch-Y1, Y1 tax", t1["Tax"][0], 0))
results.append(check("TradeCo switch-Y1, Y2 tax", t1["Tax"][1], 11_325_600))

# ManufCo, concessional from Y1: income 60 cr - 15 cr losses = 45 cr x 22% x 1.10 x 1.04 = 11,32,56,000
m1 = simulate(company["ManufCo (sample)"], years["ManufCo (sample)"], 1)
results.append(check("ManufCo switch-Y1, Y1 tax", m1["Tax"][0], 113_256_000))

# Optimiser sanity: the chosen option must have the lowest PV of all six
o = options(company["ManufCo (sample)"], years["ManufCo (sample)"], 10)
results.append(check("ManufCo best PV is the minimum", int(o["PV of tax"].iloc[0]), int(o["PV of tax"].min())))

print(f"\n{sum(results)} of {len(results)} checks passed")
