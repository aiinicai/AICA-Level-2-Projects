#!/usr/bin/env python3
"""
GST Blocked Credit Checker - command-line fallback
=====================================================
Same rules engine as app.py (src/rules.py), for a terminal-only quick check
or a bulk run without opening the Streamlit app.

Usage:
    python main.py check
        Interactive single-item check - describe an expense, answer any
        follow-up questions, get a verdict.

    python main.py bulk --input expenses.xlsx --output report.xlsx
        Runs the same engine over a whole Excel sheet (see
        sample_data/Sample_Expense_Ledger.xlsx for the expected columns,
        or run `python main.py template` to generate a blank one).

    python main.py template --output template.xlsx
        Writes a blank bulk-check template with example rows.

    python main.py invoice --input invoice.pdf
        Reads a photo/PDF invoice (AI if ANTHROPIC_API_KEY is set, else
        offline via PDF text layer / Tesseract OCR) and runs the same
        engine as `check`, prompting for any follow-up questions.

`check`, `bulk` and `invoice` all also raise an independent Reverse Charge
Mechanism (RCM) alert (src/rcm.py, Section 9(3)/9(4)) alongside the Section
17(5) verdict - a separate question about who is liable to pay the GST.
"""

import argparse
from pathlib import Path

import pandas as pd

from src.ai_explainer import explain
from src.bulk_check import make_template_bytes, run_bulk_check, to_excel_bytes
from src.invoice_reader import METHOD_LABELS, read_invoice
from src.rcm import match_rcm
from src.rules import ELIGIBLE, NEEDS_INPUT, evaluate, match_categories


def _ask_yn(question: str) -> str:
    while True:
        ans = input(f"  {question} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return "Y"
        if ans in ("n", "no"):
            return "N"
        print("  Please answer y or n.")


def _print_rcm_alert(desc: str) -> None:
    """Independent of the Section 17(5) verdict - see src/rcm.py."""
    for rc in match_rcm(desc):
        print(f"\n[RCM ALERT - Section {rc.section}] {rc.title}")
        print(f"  {rc.note}")
    print()


def cmd_check(args):
    desc = input("Describe the expense/purchase: ").strip()
    if not desc:
        print("Nothing entered.")
        return

    matches = match_categories(desc)
    _print_rcm_alert(desc)
    if not matches:
        print(
            "\nNo Section 17(5) block matched this description.\n"
            "-> ITC ELIGIBLE, subject to the general Section 16 conditions (business use, valid tax "
            "invoice, tax actually paid by supplier, return filed, etc.). Double-check manually if the "
            "description was brief."
        )
        return

    if len(matches) > 1:
        print("\nMore than one category matched:")
        for i, cat in enumerate(matches, 1):
            print(f"  {i}. {cat.clause} - {cat.title}")
        while True:
            try:
                choice = int(input(f"Pick the best fit [1-{len(matches)}]: ").strip())
                if 1 <= choice <= len(matches):
                    category = matches[choice - 1]
                    break
            except ValueError:
                pass
            print("  Invalid choice.")
    else:
        category = matches[0]
        print(f"\nMatched: {category.clause} - {category.title}")

    print(f"General rule: {category.general_rule}")
    if category.special_note:
        print(f"Note: {category.special_note}")

    answers = {}
    for cond in category.conditions:
        answers[cond.key] = _ask_yn(cond.question)
        result = evaluate(category, answers)
        if result["verdict"] != NEEDS_INPUT:
            break

    result = evaluate(category, answers)
    print(f"\n=== VERDICT: {result['verdict']} ===")
    print(f"Clause: {result['clause']}")
    print(f"Reasoning: {result['reasoning']}")

    if input("\nGenerate a plain-language explanation too? [y/n]: ").strip().lower() in ("y", "yes"):
        print("\n" + explain(desc, category.title, result["clause"], result["verdict"], result["reasoning"]))


def cmd_invoice(args):
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"File not found: {input_path}")

    result = read_invoice(input_path.read_bytes(), input_path.name)
    if result.error:
        raise SystemExit(result.error)

    print(f"Read via: {METHOD_LABELS.get(result.method, result.method)}\n")
    print("Extracted description:")
    print(result.text)
    print()

    desc = result.text
    matches = match_categories(desc)
    _print_rcm_alert(desc)
    if not matches:
        print(
            "No Section 17(5) block matched this description.\n"
            "-> ITC ELIGIBLE, subject to the general Section 16 conditions. Double-check manually - "
            "OCR/AI reading of a real invoice can occasionally miss the mark."
        )
        return

    if len(matches) > 1:
        print("More than one category matched:")
        for i, cat in enumerate(matches, 1):
            print(f"  {i}. {cat.clause} - {cat.title}")
        while True:
            try:
                choice = int(input(f"Pick the best fit [1-{len(matches)}]: ").strip())
                if 1 <= choice <= len(matches):
                    category = matches[choice - 1]
                    break
            except ValueError:
                pass
            print("  Invalid choice.")
    else:
        category = matches[0]
        print(f"Matched: {category.clause} - {category.title}")

    print(f"General rule: {category.general_rule}")
    if category.special_note:
        print(f"Note: {category.special_note}")

    answers = {}
    for cond in category.conditions:
        answers[cond.key] = _ask_yn(cond.question)
        result_eval = evaluate(category, answers)
        if result_eval["verdict"] != NEEDS_INPUT:
            break

    result_eval = evaluate(category, answers)
    print(f"\n=== VERDICT: {result_eval['verdict']} ===")
    print(f"Clause: {result_eval['clause']}")
    print(f"Reasoning: {result_eval['reasoning']}")

    if input("\nGenerate a plain-language explanation too? [y/n]: ").strip().lower() in ("y", "yes"):
        print("\n" + explain(desc, category.title, result_eval["clause"], result_eval["verdict"], result_eval["reasoning"]))


def cmd_bulk(args):
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"File not found: {input_path}")
    df = pd.read_excel(input_path)
    result_df = run_bulk_check(df)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(to_excel_bytes(result_df))
    print(f"Checked {len(result_df)} row(s). Report written to: {output_path}")
    counts = result_df["Verdict"].value_counts()
    for verdict, n in counts.items():
        print(f"  {verdict}: {n}")


def cmd_template(args):
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(make_template_bytes())
    print(f"Template written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="GST Blocked Credit Checker (Section 17(5), CGST Act)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Interactive single-item check")
    p_check.set_defaults(func=cmd_check)

    p_bulk = sub.add_parser("bulk", help="Check a whole Excel sheet of expenses")
    p_bulk.add_argument("--input", required=True)
    p_bulk.add_argument("--output", default="output/Blocked_Credit_Bulk_Report.xlsx")
    p_bulk.set_defaults(func=cmd_bulk)

    p_template = sub.add_parser("template", help="Write a blank bulk-check template")
    p_template.add_argument("--output", default="sample_data/Blocked_Credit_Bulk_Template.xlsx")
    p_template.set_defaults(func=cmd_template)

    p_invoice = sub.add_parser("invoice", help="Read an invoice photo/PDF and check it")
    p_invoice.add_argument("--input", required=True)
    p_invoice.set_defaults(func=cmd_invoice)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
