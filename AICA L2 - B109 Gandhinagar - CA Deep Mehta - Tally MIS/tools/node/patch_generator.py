"""Patches a COPY of the Node project's demo generator so that it describes a healthy company over 4-5 years.
Usage: python patch_generator.py src/server/demo/generator_full.ts
Every replacement must match exactly once, so a change in the original generator is noticed instead of silently ignored.
"""
import re
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def sub(old, new, count=1):
    global s
    assert s.count(old) == count, f"expected {count} match(es) of: {old[:70]!r}, found {s.count(old)}"
    s = s.replace(old, new)


def sub_re(pattern, new):
    global s
    s, n = re.subn(pattern, new, s, count=1, flags=re.S)
    assert n == 1, f"no match for regex {pattern[:70]!r}"


# 1. no odd custom primary group / unclassifiable ledger (needs special group setup in Tally)
sub("      { name: 'Old Balances', parent: null, isRevenue: false, gp: false, debit: true },\n", "")
sub("L('Old Party Balance', 'Old Balances', 25000_00), ", "")
# 1b. Tally always has a "Cash" ledger; start it at nil so no opening balance depends on importing into it
sub("L('Cash', 'Cash-in-Hand', 150000_00)", "L('Cash', 'Cash-in-Hand', 0)")
# 2. never let stock go negative (the original deliberately did, once, for a test)
sub("if (qty > s.qty && !(it.name === 'Smart Plug WiFi' && mi === 3)) qty", "if (qty > s.qty) qty")
# 3. drop the test-only vouchers: sales order, cancelled invoice, optional journal (suspense journal stays)
a = s.index("    this.push({ date: d, type: 'Sales Order'")
b = s.index("    this.push({ date: addDays(d, 3), type: 'Journal'")
s = s[:a] + s[b:]

# 4. a profitable trading company: better selling prices, lighter overheads, steadier restocking
sub("(name === 'Inverter Battery 150Ah' ? 1 : 1.12)", "(name === 'Inverter Battery 150Ah' ? 1.08 : 1.30)")
sub("const nPurch = Math.round(perMonth * 0.22 * season);", "const nPurch = Math.round(perMonth * 0.30 * season);")
sub("const salary = Math.round((215000 + mi * 1500) * 100);", "const salary = Math.round((105000 + mi * 900) * 100);")
sub("pay('Rent', 95000_00,", "pay('Rent', 55000_00,")
sub("pay('Electricity Charges', Math.round((32000 + r() * 18000) * 100),", "pay('Electricity Charges', Math.round((19000 + r() * 11000) * 100),")
sub("(mi > 18 ? 1.8 : 1)", "1")
sub("pay('Freight Outward', Math.round((25000 + r() * 30000) * 100 * season),", "pay('Freight Outward', Math.round((12000 + r() * 16000) * 100 * season),")
sub("pay('Staff Welfare', Math.round((8000 + r() * 9000) * 100),", "pay('Staff Welfare', Math.round((5000 + r() * 5000) * 100),")
sub("pay('Office Expenses', Math.round((10000 + r() * 14000) * 100),", "pay('Office Expenses', Math.round((6000 + r() * 8000) * 100),")
sub("pay('Sales Commission', Math.round((20000 + r() * 25000) * 100),", "pay('Sales Commission', Math.round((12000 + r() * 14000) * 100),")
sub("pay('Interest on Cash Credit', Math.round((7500 + r() * 2500) * 100 * (1 + mi * 0.02)),", "pay('Interest on Cash Credit', Math.round((6500 + r() * 2000) * 100),")
sub("if (mo === 7) pay('Insurance', 145000_00,", "if (mo === 7) pay('Insurance', 95000_00,")
sub("{ ledger: 'Income Tax Expense', amount: 450000_00 }, { ledger: 'Provision for Income Tax', amount: -450000_00 }", "{ ledger: 'Income Tax Expense', amount: 300000_00 }, { ledger: 'Provision for Income Tax', amount: -300000_00 }")
sub("{ ledger: 'Provision for Income Tax', amount: 400000_00 }, { ledger: bank, amount: -400000_00 }", "{ ledger: 'Provision for Income Tax', amount: 300000_00 }, { ledger: bank, amount: -300000_00 }")

# 5. term loan: interest on the outstanding balance, EMI stops when the loan is repaid (the original kept paying)
sub("    const fyEnds = new Set<string>();\n", "    const fyEnds = new Set<string>();\n    let loanBal = 2400000_00;\n"
    "    const assets: Record<string, { bal: number; rate: number }> = { 'Plant & Machinery': { bal: 3200000_00, rate: 0.15 }, 'Furniture & Fixtures': { bal: 450000_00, rate: 0.10 }, 'Computers': { bal: 280000_00, rate: 0.40 } };\n")
sub_re(r"      const interest = Math\.round\(2400000_00.*?\{ ledger: bank, amount: -85000_00 \}\] \}\);\n",
       "      if (loanBal > 0) {\n"
       "        const interest = Math.round(loanBal * 0.105 / 12);\n"
       "        const emi = Math.min(85000_00, loanBal + interest);\n"
       "        this.push({ date: toIso(y, mo, 7), type: 'Journal', number: String(++jNo), narration: 'Interest on term loan', inventory: [], lines: [\n"
       "          { ledger: 'Interest on Term Loan', amount: interest }, { ledger: 'SBI Term Loan', amount: -interest }] });\n"
       "        this.push({ date: toIso(y, mo, 7), type: 'Payment', number: String(++payNo), narration: 'Term loan EMI', inventory: [], lines: [\n"
       "          { ledger: 'SBI Term Loan', amount: emi }, { ledger: bank, amount: -emi }] });\n"
       "        loanBal = loanBal + interest - emi;\n"
       "      }\n")

# 6. depreciation on the written-down value of each asset (never below nil); two new assets bought during the years
sub_re(r"      const dep: \[string, number\]\[\] = \[\['Plant & Machinery'.*?\n",
       "      if (mi === 24) { pay('Computers', 300000_00, 'New computers purchased', toIso(y, mo, 10)); assets['Computers'].bal += 300000_00; }\n"
       "      if (mi === 36) { pay('Plant & Machinery', 800000_00, 'New machine installed', toIso(y, mo, 10)); assets['Plant & Machinery'].bal += 800000_00; }\n"
       "      const dep: [string, number][] = Object.entries(assets).map(([n, a]) => [n, a.bal * a.rate / 12]);\n")
sub("      // GST settlement:", "      for (const [n, v] of dep) assets[n].bal -= Math.round(v);\n      // GST settlement:")

# 7. GST set-off uses the credit still unused from earlier months (the original only looked at the current month)
sub("const monthLines = this.vouchers.filter((v) => v.date >= m && v.date <= mEnd).flatMap((v) => v.lines);", "const monthLines = this.vouchers.filter((v) => v.date <= mEnd).flatMap((v) => v.lines);")

open(p, "w", encoding="utf-8").write(s)
print("patched", p)
