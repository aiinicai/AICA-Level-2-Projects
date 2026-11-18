#!/usr/bin/env python3
"""Bharat Stock Analyser command line.

Analyse a stock (fetches data, writes JSON, HTML and PDF, prints a Markdown digest):
    python analyse.py "tata steel"
    python analyse.py TATASTEEL --outdir ~/Desktop/reports
    python analyse.py 500470 --rf 6.4 --erp 7.5

Re-render an existing analysis with analyst commentary (no new download):
    python analyse.py --render ~/Documents/Bharat-Stock-Reports/TATASTEEL_20261101_analysis.json \
        --commentary commentary.json

Exit codes: 0 success, 2 stock not found, 3 data or render error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

# yfinance triggers pandas deprecation warnings that are noise for the user.
warnings.filterwarnings("ignore", module="yfinance")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bsa import data, pipeline  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Equity research report for an NSE or BSE listed stock.")
    ap.add_argument("stock", nargs="?", help="Company name, NSE symbol or 6-digit BSE code")
    ap.add_argument("--outdir", help=f"Output folder (default {pipeline.DEFAULT_OUTDIR})")
    ap.add_argument("--render", metavar="ANALYSIS_JSON", help="Re-render an existing *_analysis.json")
    ap.add_argument("--commentary", metavar="FILE", help="JSON file with analyst commentary to add to the report")
    ap.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    ap.add_argument("--no-exchange", action="store_true",
                    help="Do not read NSE and BSE filings (Yahoo Finance data only)")
    ap.add_argument("--rf", type=float, help="Risk-free rate in percent (default 6.5)")
    ap.add_argument("--erp", type=float, help="Equity risk premium in percent (default 7.0)")
    ap.add_argument("--tg", type=float, help="Terminal growth in percent (default 5.0)")
    ap.add_argument("--json", action="store_true", help="Print the full analysis JSON instead of the digest")
    args = ap.parse_args(argv)
    if args.no_exchange:
        os.environ["BSA_NO_EXCHANGE"] = "1"

    commentary = None
    if args.commentary:
        try:
            commentary = json.loads(Path(args.commentary).expanduser().read_text(encoding="utf-8"))
            commentary = pipeline.validate_commentary(commentary)
        except (OSError, ValueError) as exc:
            print(f"ERROR: commentary file problem: {exc}", file=sys.stderr)
            return 3

    try:
        if args.render:
            analysis = pipeline.rerender(args.render, commentary, make_pdf=not args.no_pdf)
        else:
            if not args.stock:
                ap.error("give a stock name, or --render with an analysis JSON")
            overrides = {k: v for k, v in (("risk_free", args.rf), ("equity_risk_premium", args.erp),
                                           ("terminal_growth", args.tg)) if v is not None}
            analysis = pipeline.run(args.stock, args.outdir, overrides, make_pdf=not args.no_pdf)
            if commentary is not None:
                analysis = pipeline.rerender(analysis["files"]["json"], commentary, make_pdf=not args.no_pdf)
    except data.ResolveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # report any other failure plainly to the caller
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(analysis, indent=1) if args.json else pipeline.digest(analysis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
