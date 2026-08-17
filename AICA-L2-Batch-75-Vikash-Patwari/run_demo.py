#!/usr/bin/env python3
"""
End-to-end demonstration run.

    python run_demo.py

This is the console version of the ICAI demo. Wire the same calls behind the
UI later; the numbers must not change when you do.
"""
from decimal import Decimal

from clock45.demo_data import build_demo_dataset
from clock45.engine import (
    run_assessment, action_list, exclusion_register, interest_only_register,
    ACC_INVOICE_DATE, ACC_POLICY_TEXT,
)
from clock45.normalise import cluster_vendors, BACKEND
from clock45.classify import (
    GATE_ACTIVITY, GATE_CLASS, GATE_REGISTRATION, GATE_TIMING,
)

GATE_LABEL = {
    GATE_CLASS: "Medium enterprise (not micro/small)",
    GATE_ACTIVITY: "Wholesale/retail trader (NIC 45/46/47)",
    GATE_REGISTRATION: "No Udyam registration on record",
    GATE_TIMING: "Registered after the date of supply",
}


def rs(x) -> str:
    """Indian digit grouping."""
    n = int(Decimal(x).quantize(Decimal("1")))
    s, neg = str(abs(n)), n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "Rs " + s


def rule(ch="-", n=78):
    print(ch * n)


def main():
    data = build_demo_dataset()
    print()
    rule("=")
    print("  THE 45-DAY CLOCK  ·  MSME Payable Exposure  ·  DEMONSTRATION DATA")
    rule("=")

    run = run_assessment(
        entity_name=data["entity_name"], fy=data["fy"],
        operator="CA <your name>", purchases=data["purchases"],
        payments=data["payments"], udyam=data["udyam"],
        acceptance_policy=ACC_INVOICE_DATE,
    )
    st, ct = run.statute, run.control_totals

    print(f"  Entity          : {run.entity_name}")
    print(f"  Tax year        : {run.fy}")
    print(f"  Governing law   : {st['act']}, Section {st['section']}  ->  {st['form']}")
    print(f"  Rule pack       : {run.rule_pack_version}   Run hash: {run.run_hash()}")
    print(f"  Matcher backend : {BACKEND}")
    print()

    rule()
    print("  CONTROL TOTALS")
    rule()
    print(f"  Ledger lines in year      : {ct['ledger_lines_in_year']:,}")
    print(f"  Ledger value              : {rs(ct['ledger_value'])}")
    print(f"  Value accounted for       : {rs(ct['value_accounted_for'])}")
    print(f"  Totals tie                : {'YES' if ct['ties'] else 'NO -- REFUSING TO CERTIFY'}")
    print(f"  Bank Rate at year end     : {ct['bank_rate_at_year_end_pct']}%")
    print(f"  MSMED s.16 rate           : {ct['msmed_rate_at_year_end_pct']}% p.a., monthly rests")
    print()

    rule("=")
    print("  YOU WILL LOSE")
    rule("=")
    print(f"  Disallowance u/s {st['section']:<8}  : {rs(run.disallowance_total)}")
    print(f"  Correctly NOT disallowed   : {rs(run.excluded_total)}")
    print(f"  s.16 interest exposure     : {rs(run.interest_total)}   (NOT deductible, s.23)")
    print(f"  Invoices affected          : "
          f"{sum(1 for f in run.findings if f.status == 'DISALLOWED'):,}")
    print()

    rule("=")
    print("  ...AND WHAT WAS FLAGGED INCORRECTLY")
    rule("=")
    reg = exclusion_register(run)
    by_gate: dict[str, list] = {}
    for r in reg:
        by_gate.setdefault(r["gate"], []).append(r)
    for gate, rows in sorted(by_gate.items(),
                             key=lambda kv: -sum(r["wrongly_disallowable"] for r in kv[1])):
        total = sum(r["wrongly_disallowable"] for r in rows)
        print(f"  {GATE_LABEL.get(gate, gate)}")
        print(f"      {len(rows)} vendors · {rs(total)} that another tool")
        print(f"      would have added back, and shouldn't have")
    print()
    traders = by_gate.get(GATE_ACTIVITY, [])
    if traders:
        print("  The trader exclusion, vendor by vendor:")
        for r in [t for t in traders if t["wrongly_disallowable"] > 0][:6]:
            print(f"      {r['vendor'][:34]:<34} {rs(r['wrongly_disallowable']):>14}")
        print(f"      {'':<34} {'':>14}")
        print(f"      Ministry of MSME OMs 02.07.2021 and 01.09.2021: trader")
        print(f"      benefits are restricted to Priority Sector Lending; the")
        print(f"      delayed-payment provisions are excluded. Not 'suppliers'")
        print(f"      for s.15 purposes.")
    print()

    rule("=")
    print("  THE 31 MARCH ACTION LIST   (top 10 by money saved)")
    rule("=")
    print(f"  {'Vendor':<32}{'Inv':>4}{'Pay by':>12}{'Pay now':>14}{'Interest':>12}")
    rule()
    for r in action_list(run, top_n=10):
        due = r["earliest_due"].strftime("%d-%b-%y") if r["earliest_due"] else "-"
        print(f"  {r['vendor'][:31]:<32}{r['invoices']:>4}{due:>12}"
              f"{rs(r['pay_now']):>14}{rs(r['interest_exposure']):>12}")
    print()

    io = interest_only_register(run)
    if io:
        rule("=")
        print("  PAID LATE, BUT WITHIN THE YEAR")
        print("  No disallowance -- but s.16 interest still accrues, and it is")
        print("  not deductible. Most tools miss this entirely.")
        rule("=")
        for r in io[:5]:
            print(f"  {r['vendor'][:34]:<36}{rs(r['value']):>14}{rs(r['interest']):>12}")
        print(f"  {'TOTAL non-deductible interest':<36}"
              f"{'':>14}{rs(sum(r['interest'] for r in io)):>12}")
        print()

    names = [p.vendor_name_as_written for p in data["purchases"]]
    clusters, review = cluster_vendors(names)
    multi = [c for c in clusters if len(c.members) > 1]
    rule("=")
    print("  VENDOR NAME NORMALISATION")
    rule("=")
    print(f"  Distinct ledger spellings  : {len(set(names)):,}")
    print(f"  Resolved vendors           : {len(clusters):,}")
    print(f"  Auto-merged clusters       : {len(multi)}")
    print(f"  Sent to human review       : {len(review)}")
    for c in multi[:3]:
        print(f"      {c.canonical}")
        for m in c.members:
            print(f"          <- {m}  ({c.scores.get(m, 0)})")
    print()

    rule("=")
    print("  ASSUMPTIONS AND WARNINGS  (printed in the working paper)")
    rule("=")
    print(f"  {ACC_POLICY_TEXT[run.acceptance_policy]}")
    for w in run.warnings:
        print(f"  ! {w}")
    print("  ! Computation aid, not professional advice. Every vendor")
    print("    classification requires human confirmation before sign-off.")
    print()
    rule("=")
    print("  This is a September conversation. Run it in January and 23 of")
    print("  these vendors get paid before 31 March -- and the disallowance")
    print("  never happens.")
    rule("=")
    print()


if __name__ == "__main__":
    main()
