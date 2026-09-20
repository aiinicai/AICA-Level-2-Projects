"""Cross-format regression: the same invoice in Excel, Word, PDF and PNG must give the same data.
   python tests/cross_format_test.py <file1> <file2> ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pec.engine import Engine
from pec.gui.main_window import find_template
from pec.settings import load_app_settings, load_profile

eng = Engine(find_template(load_app_settings()))
prof = load_profile(None)
rows = []
for f in sys.argv[1:]:
    try:
        inv = eng.read_sources(f, prof)[0]
        opt = eng.auto_options(inv, load_app_settings())
        sup, notes = eng.auto_supplier(inv)
        opt.auto_notes += notes
        res = eng.analyse(inv, opt, sup, prof)
        h = res.header
        rows.append((Path(f).name, opt.transaction_type, opt.supply_type, len(res.items),
                     h.get("colDocno"), h.get("colBLegalname"), h.get("colTotTaxval"),
                     h.get("colTinvoiceval"), res.issues.n("RED"), res.issues.n("AMBER")))
    except Exception as e:
        rows.append((Path(f).name, "read error", str(e)[:60], 0, "", "", "", "", "", ""))
head = ("file", "type", "supply", "items", "doc no", "buyer", "taxable", "total", "RED", "AMBER")
w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
for r in [head] + rows:
    print("  ".join(str(v).ljust(w[i]) for i, v in enumerate(r)))
same = {r[1:4] + r[6:8] for r in rows if r[1] != "read error"}
print("\nCross-format consistent:", "YES" if len(same) <= 1 else "NO - " + str(same))
