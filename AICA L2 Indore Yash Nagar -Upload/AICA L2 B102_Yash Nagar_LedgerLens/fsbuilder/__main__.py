"""python -m fsbuilder samples/rpi_trial_balance.csv --groups samples/rpi_groups.csv --from 2024-04-01 --to 2025-03-31 --company "..." --out out
Or live from TallyPrime:  python -m fsbuilder --tally --company "..." --from 2024-04-01 --to 2025-03-31 --out out
"""
import argparse
import json
from datetime import date

from dotenv import load_dotenv

from .mapping import map_ledgers
from .model import build_model
from .render import write_all
from .statements import balance_check, line_totals
from .tb import TallyError, fetch_from_tally, load_snapshot, normalise


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(prog="fsbuilder", description="Build Schedule III statements from a Tally trial balance")
    ap.add_argument("snapshot", nargs="?", help="trial balance CSV (omit with --tally)")
    ap.add_argument("--groups", help="groups CSV (name,parent,nature)")
    ap.add_argument("--tally", action="store_true", help="read live from TallyPrime's XML server")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--company", required=True)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    ap.add_argument("--overrides", help="JSON file: {ledger: {line, sub, reason}}")
    ap.add_argument("--out", default="out")
    ap.add_argument("--review", action="store_true",
                    help="also write the reviewer's report (casting, ratios, disclosure checklist)")
    ap.add_argument("--ai", action="store_true",
                    help="with --review: add Gemini-drafted explanations and observations (needs GEMINI_API_KEY; "
                         "sends figures and labels, never ledger or party names, to Google)")
    a = ap.parse_args()

    try:
        tb = (fetch_from_tally(a.company, a.start, a.end, a.host, a.port) if a.tally
              else load_snapshot(a.snapshot, a.groups, a.company, a.start, a.end))
    except TallyError as e:
        raise SystemExit(f"Error: {e}")
    tb = normalise(tb)
    overrides = json.load(open(a.overrides, encoding="utf-8")) if a.overrides else None
    mapped = map_ledgers(tb, overrides=overrides)
    unmapped = mapped[mapped["source"] == "unmapped"]["ledger"].tolist()
    if unmapped:
        print(f"Warning: {len(unmapped)} unmapped ledger(s), excluded from the statements: {', '.join(unmapped)}")
    chk = balance_check(line_totals(mapped))["closing"]
    model = build_model(tb, mapped)
    docx, xlsx = write_all(model, a.out)
    print(f"Balance sheet difference before rounding: {chk['difference']:.2f}")
    print(f"Wrote {docx}\nWrote {xlsx}\n{len(model.flags)} open items, {len(model.notes)} notes")
    if a.review:
        from .reviewer import run_review
        from .reviewer.llm import GeminiLLM, LLMError
        from .reviewer.report import write_review
        llm = None
        if a.ai:
            try:
                llm = GeminiLLM()
            except LLMError as e:
                print(f"AI review skipped: {e}")
        rev = run_review(model, mapped, llm)
        rdocx, rxlsx = write_review(rev, a.out)
        s = rev.summary
        print(f"Wrote {rdocx}\nWrote {rxlsx}")
        print(f"Tie-outs: {s['passed']}/{s['checks']} passed; {s['ratios_flagged']} ratio(s) moved more than 25%; "
              f"checklist {s['checklist']}")
        for e in rev.ai.errors:
            print(f"AI problem: {e}")


if __name__ == "__main__":
    main()
