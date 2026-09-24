"""Normalise a source system's output into the common internal schema.

This is the piece that keeps the rest of the application source-agnostic. The
classification rules below encode a CA's reading of a Tally chart of accounts:
which groups are cash, which are statutory, and which expense group belongs to
which of the nine burn categories the CFO wants to see.

Anything that cannot be classified is reported back rather than silently
dropped into "Other" — an unmapped ledger is a data-quality finding, and the
sync result says so.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import (
    Account, BurnCategory, Bill, CostNature, Customer, Entity, Invoice,
    LedgerEntry, Vendor,
)

# --- group → classification -------------------------------------------------
ASSET_GROUPS = {"current assets", "fixed assets", "investments", "loans & advances (asset)",
                "cash-in-hand", "bank accounts", "bank od a/c", "deposits (asset)",
                "sundry debtors", "stock-in-hand", "misc. expenses (asset)"}
LIABILITY_GROUPS = {"current liabilities", "loans (liability)", "sundry creditors",
                    "duties & taxes", "provisions", "secured loans", "unsecured loans",
                    "bank od a/c", "suspense a/c"}
EQUITY_GROUPS = {"capital account", "reserves & surplus"}
INCOME_GROUPS = {"sales accounts", "direct incomes", "indirect incomes", "income (direct)",
                 "income (indirect)"}
EXPENSE_GROUPS = {"purchase accounts", "direct expenses", "indirect expenses",
                  "expenses (direct)", "expenses (indirect)"}

CASH_GROUPS = {"cash-in-hand", "bank accounts", "deposits (asset)"}
RECEIVABLE_GROUPS = {"sundry debtors"}
PAYABLE_GROUPS = {"sundry creditors"}
STATUTORY_GROUPS = {"duties & taxes"}
LOAN_GROUPS = {"loans (liability)", "secured loans", "unsecured loans", "bank od a/c"}

# --- ledger name keyword → burn category -----------------------------------
CATEGORY_KEYWORDS: list[tuple[tuple[str, ...], str, str]] = [
    (("salary", "salaries", "wages", "payroll", "bonus", "gratuity", "esop",
      "provident", " pf ", "esi", "staff", "employee", "recruit", "hr "),
     BurnCategory.PEOPLE, CostNature.FIXED),
    (("gst", "tds", "tcs", "income tax", "professional tax", "duty", "duties",
      "cess", "advance tax", "statutory"),
     BurnCategory.STATUTORY, CostNature.VARIABLE),
    (("aws", "azure", "gcp", "cloud", "hosting", "server", "software", "saas",
      "subscription", "licence", "license", "api", "data centre", "domain"),
     BurnCategory.TECH, CostNature.VARIABLE),
    (("contractor", "freelance", "sub-contract", "subcontract", "installation",
      "commissioning", "site", "hardware", "component", "sensor", "material",
      "cost of sales", "cogs", "delivery", "logistics", "freight"),
     BurnCategory.DELIVERY, CostNature.VARIABLE),
    (("rent", "lease", "electricity", "power", "water", "housekeep", "security",
      "maintenance", "repairs", "office", "facility", "utilities"),
     BurnCategory.FACILITIES, CostNature.FIXED),
    (("marketing", "advertis", "brand", "campaign", "event", "conference",
      "exhibition", "sponsor", "promotion", "digital"),
     BurnCategory.MARKETING, CostNature.DISCRETIONARY),
    (("legal", "audit", "consult", "professional", "secretarial", "advisory",
      "retainer", "valuation"),
     BurnCategory.PROFESSIONAL, CostNature.VARIABLE),
    (("interest", "bank charge", "processing fee", "finance cost", "loan",
      "facility fee", "commission on"),
     BurnCategory.FINANCE_COST, CostNature.FIXED),
    (("insurance", "travel", "conveyance", "telephone", "internet", "printing",
      "stationery", "postage", "misc", "sundry", "donation", "membership"),
     BurnCategory.OTHER, CostNature.VARIABLE),
]


def classify_group(parent: str | None) -> tuple[str, str, bool]:
    """(classification, sub_type, is_cash) from a Tally group name."""
    p = (parent or "").strip().lower()
    if p in CASH_GROUPS:
        return "asset", ("cash" if "cash" in p else "bank"), True
    if p in RECEIVABLE_GROUPS:
        return "asset", "receivable", False
    if p in PAYABLE_GROUPS:
        return "liability", "payable", False
    if p in STATUTORY_GROUPS:
        return "liability", "statutory", False
    if p in LOAN_GROUPS:
        return "liability", "loan", False
    if p in EQUITY_GROUPS:
        return "equity", "other", False
    if p in INCOME_GROUPS:
        return "income", "other", False
    if p in EXPENSE_GROUPS:
        return "expense", "other", False
    if p in ASSET_GROUPS:
        return "asset", "other", False
    if p in LIABILITY_GROUPS:
        return "liability", "other", False
    return "expense", "other", False        # safest default for a P&L ledger


def classify_category(name: str, parent: str | None) -> tuple[str | None, str | None, bool]:
    """(burn_category, cost_nature, matched). `matched` is False when nothing
    in the ledger name was recognisable — reported as a data-quality finding."""
    hay = f" {(name or '').lower()} {(parent or '').lower()} "
    for keywords, category, nature in CATEGORY_KEYWORDS:
        if any(k in hay for k in keywords):
            return category, nature, True
    return BurnCategory.OTHER, CostNature.VARIABLE, False


# ---------------------------------------------------------------------------
def normalise_ledgers(db: Session, entity: Entity, rows: Iterable[dict]) -> dict:
    """Upsert the chart of accounts. Returns counts and unmapped names."""
    from app.models import LedgerMapping

    created = updated = 0
    unmapped: list[str] = []
    awaiting: list[str] = []
    existing = {a.name: a for a in db.query(Account)
                .filter(Account.entity_id == entity.id).all()}
    # A person's confirmed decision beats the app's guess, every time.
    decided = {m.ledger_name: m for m in db.query(LedgerMapping)
               .filter(LedgerMapping.entity_id == entity.id,
                       LedgerMapping.confirmed.is_(True)).all()}
    known = {m.ledger_name for m in db.query(LedgerMapping.ledger_name)
             .filter(LedgerMapping.entity_id == entity.id).all()}

    for r in rows:
        name = r["name"]
        cls, sub, is_cash = classify_group(r.get("parent_group"))
        cat, nature, matched = (None, None, True)
        if cls == "expense":
            cat, nature, matched = classify_category(name, r.get("parent_group"))
        elif sub == "statutory":
            cat, nature = BurnCategory.STATUTORY, CostNature.VARIABLE

        m = decided.get(name)
        if not matched and m is None:
            # Unrecognised *and* nobody has ruled on it. Once a person has
            # confirmed a mapping it is not a finding any more, however
            # unrecognisable the name was to the classifier.
            unmapped.append(name)
        if m is not None:
            cls = m.classification or cls
            sub = m.sub_type or sub
            is_cash = m.is_cash
            cat = m.burn_category or cat
            nature = m.cost_nature or nature
        elif name not in known:
            # New ledger nobody has looked at yet. Not silently absorbed —
            # a ledger created since the last review is a data-quality finding.
            awaiting.append(name)

        a = existing.get(name)
        if a is None:
            a = Account(entity_id=entity.id, name=name)
            db.add(a)
            created += 1
        else:
            updated += 1
        a.external_id = r.get("external_id") or a.external_id
        a.parent_group = r.get("parent_group")
        a.classification = cls
        a.sub_type = sub
        a.is_cash = is_cash
        a.burn_category = cat
        a.cost_nature = nature
        a.opening_balance = r.get("opening_balance", 0.0)
        a.closing_balance = r.get("closing_balance", 0.0)

    db.flush()
    banks = _sync_bank_accounts(db, entity)
    return {"accounts_created": created, "accounts_updated": updated,
            "unmapped_ledgers": sorted(set(unmapped)),
            "new_ledgers_awaiting_review": sorted(set(awaiting)),
            "bank_accounts_created": banks["created"],
            "bank_accounts_updated": banks["updated"]}


def _sync_bank_accounts(db: Session, entity: Entity) -> dict:
    """Give every cash and bank ledger a bank-account record.

    Without this, connecting Tally produces burn but no cash, so runway comes
    out as zero — the tool would be reading half the position and stating the
    other half as fact.

    What Tally cannot tell us is which balances are *restricted*. A lien, an
    escrow or a pledge is an agreement, not a ledger attribute, so every
    account arrives unrestricted and someone has to say otherwise in the
    register. That is the honest default only because the application says out
    loud that it is assuming it — an unrestricted balance is treated as
    spendable, and treating a lien-marked deposit as spendable is how a company
    plans around money it cannot touch.
    """
    from app.models import BankAccount

    cash_accounts = (db.query(Account)
                     .filter(Account.entity_id == entity.id,
                             Account.is_cash.is_(True)).all())
    existing = {b.account_name: b for b in db.query(BankAccount)
                .filter(BankAccount.entity_id == entity.id).all()}

    created = updated = 0
    for acc in cash_accounts:
        bank = existing.get(acc.name)
        if bank is None:
            bank = BankAccount(entity_id=entity.id,
                               institution=acc.name.split(" - ")[0].strip(),
                               account_name=acc.name,
                               purpose="Deposit" if acc.sub_type == "deposit" else "Operating",
                               is_restricted=False,
                               source="tally", created_by="Tally sync")
            db.add(bank)
            created += 1
        else:
            updated += 1
        # The books figure comes from Tally. The bank figure is whatever the
        # statement says, and stays put — the difference between the two is the
        # reconciliation gap the confidence banner is built on, so overwriting
        # it here would erase the very thing the tool is meant to surface.
        bank.books_balance = acc.closing_balance
        if bank.balance in (None, 0.0) or bank.source == "tally":
            bank.balance = acc.closing_balance
        bank.as_on = entity.books_closed_upto
        bank.updated_by = "Tally sync"

    db.flush()
    return {"created": created, "updated": updated}


def normalise_vouchers(db: Session, entity: Entity, rows: Iterable[dict]) -> dict:
    """Turn voucher lines into cash-affecting ledger entries.

    Only the cash side of a voucher matters for this tool: for each voucher we
    take the movement on cash/bank ledgers as the cash amount, and attribute it
    to the contra ledger's category.
    """
    accounts = {a.name: a for a in db.query(Account)
                .filter(Account.entity_id == entity.id).all()}
    existing = {e.external_id for e in db.query(LedgerEntry.external_id)
                .filter(LedgerEntry.entity_id == entity.id,
                        LedgerEntry.external_id.isnot(None)).all()}

    # group lines back into vouchers
    by_voucher: dict[str, list[dict]] = {}
    for r in rows:
        key = f"{r.get('voucher_no')}|{r.get('txn_date')}|{r.get('voucher_type')}"
        by_voucher.setdefault(key, []).append(r)

    created = skipped = non_cash = 0
    for key, lines in by_voucher.items():
        cash_lines = [l for l in lines
                      if (accounts.get(l["ledger"]) and accounts[l["ledger"]].is_cash)]
        if not cash_lines:
            non_cash += 1
            continue
        cash_amount = sum(l["amount"] for l in cash_lines)
        contra = [l for l in lines if l not in cash_lines]
        # Attribute to the largest contra line — good enough, and the drill-down
        # still shows the whole voucher.
        main = max(contra, key=lambda l: abs(l["amount"])) if contra else lines[0]
        acc = accounts.get(main["ledger"])

        ext = main.get("external_id") or key
        if ext in existing:
            skipped += 1
            continue

        db.add(LedgerEntry(
            entity_id=entity.id,
            account_id=acc.id if acc else None,
            txn_date=main["txn_date"],
            voucher_type=main["voucher_type"],
            voucher_no=main["voucher_no"],
            party=main.get("party") or main["ledger"],
            narration=main.get("narration"),
            debit=max(cash_amount, 0.0),
            credit=max(-cash_amount, 0.0),
            cash_amount=cash_amount,
            burn_category=acc.burn_category if acc else None,
            cost_nature=acc.cost_nature if acc else None,
            external_id=ext,
            source="tally",
        ))
        created += 1

    db.flush()
    return {"entries_created": created, "entries_skipped_duplicate": skipped,
            "vouchers_without_cash_movement": non_cash}


def normalise_bills(db: Session, entity: Entity, rows: Iterable[dict],
                    as_on: date) -> dict:
    """Bills outstanding → open invoices and open bills."""
    customers = {c.name: c for c in db.query(Customer)
                 .filter(Customer.entity_id == entity.id).all()}
    vendors = {v.name: v for v in db.query(Vendor)
               .filter(Vendor.entity_id == entity.id).all()}
    inv_seen = {i.invoice_no: i for i in db.query(Invoice)
                .filter(Invoice.entity_id == entity.id).all()}
    bill_seen = {b.bill_no: b for b in db.query(Bill)
                 .filter(Bill.entity_id == entity.id).all()}

    inv_created = bill_created = updated = 0
    for r in rows:
        party = (r.get("party") or "").strip()
        ref = (r.get("bill_no") or "").strip()
        if not party or not ref or not r.get("amount"):
            continue
        bdate = r.get("bill_date") or as_on
        ddate = r.get("due_date") or bdate

        if r["kind"] == "receivable":
            c = customers.get(party)
            if c is None:
                c = Customer(entity_id=entity.id, name=party, source="tally",
                             created_by="Tally sync")
                db.add(c)
                db.flush()
                customers[party] = c
            inv = inv_seen.get(ref)
            if inv is None:
                inv = Invoice(entity_id=entity.id, customer_id=c.id, invoice_no=ref,
                              invoice_date=bdate, due_date=ddate,
                              amount=r["amount"], outstanding=r["amount"],
                              status="open", source="tally", created_by="Tally sync")
                db.add(inv)
                inv_created += 1
            else:
                inv.outstanding = r["amount"]
                inv.due_date = ddate
                updated += 1
        else:
            v = vendors.get(party)
            if v is None:
                v = Vendor(entity_id=entity.id, name=party, source="tally",
                           created_by="Tally sync")
                db.add(v)
                db.flush()
                vendors[party] = v
            b = bill_seen.get(ref)
            if b is None:
                b = Bill(entity_id=entity.id, vendor_id=v.id, bill_no=ref,
                         bill_date=bdate, due_date=ddate,
                         amount=r["amount"], outstanding=r["amount"],
                         status="unpaid", source="tally", created_by="Tally sync")
                db.add(b)
                bill_created += 1
            else:
                b.outstanding = r["amount"]
                b.due_date = ddate
                updated += 1

    db.flush()
    return {"invoices_created": inv_created, "bills_created": bill_created,
            "bills_updated": updated}
