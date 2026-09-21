"""Headless test of the automatic flow.  python tests/run_sample_test.py <invoice.xlsx> [output_dir]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pec.engine import Engine
from pec.gui.main_window import find_template
from pec.settings import load_app_settings, load_profile

inv_path = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else "Output"
eng = Engine(find_template(load_app_settings()))
prof = load_profile(None)
inv = eng.read_source(inv_path, prof)
opt = eng.auto_options(inv, load_app_settings())
sup, notes = eng.auto_supplier(inv)
opt.auto_notes += notes
res = eng.analyse(inv, opt, sup, prof)
for i in res.issues:
    print(i.text())
if res.issues.has_red:
    print("NOT GENERATED")
    sys.exit(1)
out = eng.generate(res, out_dir, sup)
print("Generated:", out["json"], out["nic"], out["report"], "problems:", out["problems"])
