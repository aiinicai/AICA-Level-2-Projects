"""Command-line interface (same engine as the GUI). Examples:

  python -m ct_tool.cli analyse --tb tb.xlsx --currency AED --gl gl.xlsx --period-start 2025-01-01 --period-end 2025-12-31 --out outputs
  python -m ct_tool.cli analyse --tb tb_usd.xlsx --currency EUR --rate-pl 3.98 --rate-closing 4.05 --rate-equity 3.9 --rate-source "CBUAE ..." --out outputs
  python -m ct_tool.cli preview --tb tb.pdf
"""
from __future__ import annotations

import argparse
import json
import sys

from .extract import parse_gl, parse_tb
from .fx import default_settings
from .pipeline import run_analysis
from .project import Project
from .service import export_all


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cmd_preview(a):
    tb = parse_tb(a.tb, sheet=a.sheet, currency=a.currency or "")
    print(f"{tb.source_file} [{tb.sheet}] - {len(tb.accounts)} accounts, method {tb.extraction_method}; sign convention: {tb.sign_convention}")
    for w in tb.warnings:
        print("  WARNING:", w)
    for ac in tb.accounts[:60]:
        print(f"  {ac.code:>10}  {ac.name[:50]:<50} {ac.debit:>16,.2f} {ac.credit:>16,.2f}")
    return 0


def cmd_analyse(a):
    p = Project(name=a.name or "CLI project")
    p.tb = parse_tb(a.tb, sheet=a.sheet, currency=a.currency)
    if a.gl:
        p.gl = parse_gl(a.gl)
    if a.prior_tb:
        p.prior_tb = parse_tb(a.prior_tb, currency=a.currency)
    p.fx = default_settings(a.currency, a.period_start or "", a.period_end or "")
    if a.currency.upper() != "AED" and p.fx.method == "manual":
        missing = [k for k in ("rate_pl", "rate_closing", "rate_equity") if getattr(a, k) is None]
        if missing:
            print(f"ERROR: {a.currency} is not AED or a pegged currency. Supply --rate-pl --rate-closing --rate-equity (AED per 1 {a.currency}) "
                  f"and --rate-source. Missing: {', '.join(missing)}", file=sys.stderr)
            return 2
        p.fx.rates[a.currency.upper()] = {"pl": a.rate_pl, "closing": a.rate_closing, "equity": a.rate_equity}
        p.fx.rate_source = a.rate_source or ""
        p.fx.method_reason = a.method_reason or ""
        p.fx.translation_diff_approved = bool(a.approve_translation_difference)
    p.fx_confirmed = True
    if a.answers:
        p.answers = _load_json(a.answers)
    if a.decisions:
        p.decisions = _load_json(a.decisions)
    if a.settings_template:
        p.settings.template_path = a.settings_template
    if a.letterhead:
        p.settings.letterhead_path = a.letterhead
    p.log("CLI run", f"TB {a.tb}; GL {a.gl or '-'}; currency {a.currency}")
    an = run_analysis(p)
    res = export_all(an, a.out)
    c = an.comp
    print(f"Accounting profit AED {c.A:,.2f}; taxable income AED {c.E:,.2f}; tax payable AED {c.payable:,.2f} (CONFIRMED adjustments only; DRAFT)")
    print(f"{sum(1 for x in an.adjs if x.status == 'Proposed')} proposed adjustment(s) pending; {len(an.open_items)} open item(s); "
          f"{sum(1 for x in an.checks if x.status == 'FAIL')} failed check(s)")
    for k, v in res.items():
        print(f"  {k}: {v}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ct_tool", description="UAE Corporate Tax computation assistant (preliminary review tool)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("preview", help="Show what would be extracted from a trial balance")
    pv.add_argument("--tb", required=True)
    pv.add_argument("--sheet")
    pv.add_argument("--currency")
    pv.set_defaults(fn=cmd_preview)
    an = sub.add_parser("analyse", help="Run the analysis and write the deliverables")
    an.add_argument("--tb", required=True)
    an.add_argument("--sheet")
    an.add_argument("--gl")
    an.add_argument("--prior-tb", dest="prior_tb")
    an.add_argument("--currency", required=True, help="Currency of the TB, e.g. AED, USD, EUR (asked first - there is no default)")
    an.add_argument("--rate-pl", type=float, dest="rate_pl", help="AED per 1 unit, for P&L items")
    an.add_argument("--rate-closing", type=float, dest="rate_closing", help="AED per 1 unit, closing rate for the balance sheet")
    an.add_argument("--rate-equity", type=float, dest="rate_equity", help="AED per 1 unit, historical rate for equity")
    an.add_argument("--rate-source")
    an.add_argument("--method-reason")
    an.add_argument("--approve-translation-difference", action="store_true")
    an.add_argument("--period-start")
    an.add_argument("--period-end")
    an.add_argument("--answers", help="JSON file with questionnaire answers")
    an.add_argument("--decisions", help="JSON file with adjustment decisions")
    an.add_argument("--settings-template", help="Your own computation template (.xlsx); default is the bundled one")
    an.add_argument("--letterhead", help="Optional .docx letterhead for the Word report")
    an.add_argument("--name")
    an.add_argument("--out", required=True)
    an.set_defaults(fn=cmd_analyse)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
