"""Import pipeline: safety checks -> header detection -> row parsing -> categories -> batch.

Rules
* Any row error rejects the whole file: the current data stays as it was, so the forecast never
  silently misses an item. The report lists every problem with its row and column.
* Warnings (rounded amounts, exact duplicate rows, ignored columns...) do not block.
* Category text that cannot be matched creates a MappingException. The batch then waits in
  status EXCEPTIONS and becomes current only when every exception is resolved.
* Accepting a batch supersedes the previous accepted batch of the same slot. Overrides are keyed
  by (source_type, source_key), so they apply to the new rows automatically.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.advisory.matching import AUTO_COLUMN_MIN, best_match
from app.core.config import get_settings
from app.importers import parsing as P
from app.importers.readers import RawTable, UploadRejected, read_table, safe_filename, sha256_of
from app.importers.specs import BD_TYPES, FORECAST_SOURCES, SPECS, SourceSpec, normalise_header
from app.models import (BatchStatus, Category, CategoryAlias, Direction, ExceptionStatus, ImportBatch, LineItem,
                        MappingException, SourceDefaultCategory, SourceType, Treatment)
from app.services.audit import audit

TOTAL_WORDS = {"total", "grand total", "sub total", "subtotal", "totals", "net total"}
HEADER_SCAN_ROWS = 30
DEFAULT_SOURCE_KEYS = ("collections", "additional", "vendor_pdc", "allocation", "bill_discount_in",
                       "bill_discount_out", "other_in", "other_out")


# ------------------------------------------------------------------ report
@dataclass
class Issue:
    level: str                 # error | warning | info
    message: str
    row: int | None = None     # row number as seen in Excel
    column: str | None = None


@dataclass
class ImportReport:
    source_type: str
    filename: str
    slot: str = ""
    sheet: str = ""
    header_row: int | None = None
    columns: dict = field(default_factory=dict)        # header as in file -> column key
    category_headers: list = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    rows_read: int = 0
    records: int = 0                                   # line items / reference rows created or updated
    exceptions: list[dict] = field(default_factory=list)
    status: str = ""
    batch_id: int | None = None

    def add(self, level: str, message: str, row: int | None = None, column: str | None = None) -> None:
        self.issues.append(Issue(level, message, row, column))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["error_count"], d["warning_count"] = len(self.errors), len(self.warnings)
        return d


class _Abort(Exception):
    """Stop processing; the report already holds the error(s)."""


# ------------------------------------------------------------------ helpers
def _jsonable(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def _header_lookup(spec: SourceSpec) -> dict[str, str]:
    out = {}
    for c in spec.columns:
        for h in (c.label, *c.aliases):
            out[normalise_header(h)] = c.key
    return out


def detect_header(rows: list[list], spec: SourceSpec, rep: ImportReport):
    """Find the header row (it may sit below report title rows) and map its cells to column keys."""
    lookup = _header_lookup(spec)
    best_i, best_n = None, 0
    for i, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        n = sum(1 for v in row if normalise_header(v) in lookup)
        if n > best_n:
            best_i, best_n = i, n
    if best_i is None:
        rep.add("error", "No header row found. Expected headers such as: "
                + ", ".join(c.label for c in spec.columns if c.required) + ".")
        raise _Abort
    mapping: dict[int, str] = {}
    unknown: dict[int, str] = {}
    for j, v in enumerate(rows[best_i]):
        if P.is_blank(v):
            continue
        text = P.parse_str(v)
        n = normalise_header(text)
        key = lookup.get(n)
        if key is None:
            s = best_match(n, lookup, AUTO_COLUMN_MIN)
            if s is not None:
                key = s.target
                rep.add("warning", f"Header '{text}' read as '{spec.column(key).label}' (similarity {s.score:.0f}).",
                        column=text)
        if key is None:
            unknown[j] = text
        elif key in mapping.values():
            rep.add("error", f"Two columns map to '{spec.column(key).label}': check header '{text}'.", column=text)
        else:
            mapping[j] = key
    rep.header_row = best_i + 1
    rep.columns = {P.parse_str(rows[best_i][j]): k for j, k in mapping.items()}
    found = set(mapping.values())
    optional_wide = spec.source_type == "other"
    missing = [spec.column(k).label for k in spec.required_keys if k not in found
               and not (optional_wide and k == "description" and "date" in found)]
    if missing:
        rep.add("error", "Missing required column(s): " + ", ".join(missing) + ". Found: "
                + ", ".join(P.parse_str(v) for v in rows[best_i] if not P.is_blank(v)) + ".")
    if rep.errors:
        raise _Abort
    return best_i, mapping, unknown


def _is_total_row(row: list, key_idx: list[int]) -> bool:
    texts = [normalise_header(v) for v in row if isinstance(v, str) and v.strip()]
    keys_blank = all(P.is_blank(row[j]) if j < len(row) else True for j in key_idx)
    return keys_blank and any(t in TOTAL_WORDS for t in texts)


def parse_rows(rows, header_i, mapping, spec: SourceSpec, rep: ImportReport):
    """Yield (excel_row, parsed: dict, raw: dict, row_list) for each data row; errors go to the report."""
    headers = {j: P.parse_str(v) or f"Column {j + 1}" for j, v in enumerate(rows[header_i])}
    key_idx = [j for j, k in mapping.items() if k in spec.key_columns]
    for i in range(header_i + 1, len(rows)):
        row = rows[i]
        excel_row = i + 1
        if all(P.is_blank(v) for v in row):
            continue
        if _is_total_row(row, key_idx or list(mapping)[:1]):
            rep.add("info", "Total row skipped.", excel_row)
            continue
        rep.rows_read += 1
        raw = {headers.get(j, f"Column {j + 1}"): _jsonable(v) for j, v in enumerate(row) if not P.is_blank(v)}
        parsed: dict = {}
        ok = True
        for j, key in mapping.items():
            col = spec.column(key)
            v = row[j] if j < len(row) else None
            if P.is_blank(v):
                if col.required and not (spec.source_type == "other" and key in ("amount", "description")):
                    rep.add("error", f"{col.label} is missing.", excel_row, col.label)
                    ok = False
                continue
            try:
                if col.type == "amount":
                    amt, warn = P.parse_amount(v)
                    if warn:
                        rep.add("warning", warn, excel_row, col.label)
                    parsed[key] = amt
                else:
                    parsed[key] = P.PARSERS[col.type](v)
            except P.CellError as exc:
                rep.add("error", str(exc).capitalize() + ".", excel_row, col.label)
                ok = False
        if ok:
            yield excel_row, parsed, raw, row


def _hash_key(*parts) -> str:
    return "H-" + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12].upper()


class CategoryResolver:
    def __init__(self, db: Session):
        self.db = db
        self.by_text: dict[str, Category] = {}
        cats = list(db.scalars(select(Category).where(Category.is_active)))
        self.any_categories = bool(cats)
        for c in cats:
            self.by_text[normalise_header(c.name)] = c
        for a in db.scalars(select(CategoryAlias)):
            if a.category.is_active:
                self.by_text.setdefault(a.alias_normalised, a.category)
        self.defaults = {d.source_type: db.get(Category, d.category_id)
                         for d in db.scalars(select(SourceDefaultCategory))}

    def resolve(self, text: str) -> Category | None:
        return self.by_text.get(normalise_header(text))

    def suggest(self, text: str):
        s = best_match(text, {t: c.id for t, c in self.by_text.items()})
        return s


# ------------------------------------------------------------------ forecast sources
def _items_for_row(st: str, p: dict, extra_cats: list[tuple[str, object]]):
    """Return a list of item dicts (several for the WIDE 'other' layout)."""
    base = dict(counterparty="", project="", reference="", bank_name="", note="", risk=False, bd=False,
                linked_invoice="", category_text=p.get("category", ""), direction=None)
    if st == "collections":
        base.update(counterparty=p["customer"], project=p.get("project", ""), reference=p["invoice_no"],
                    planned=p["due_date"], amount=p["amount"], direction="inflow",
                    risk=p.get("risk_adjusted", False), bd=p.get("bill_discounted", False))
        return [base]
    if st == "additional":
        base.update(counterparty=p.get("customer", ""), project=p["project"], reference=p.get("reference", ""),
                    planned=p["expected_date"], amount=p["amount"], direction="inflow", note=p.get("note", ""))
        return [base]
    if st == "vendor_pdc":
        base.update(counterparty=p["vendor"], reference=p["cheque_no"], bank_name=p.get("bank", ""),
                    planned=p["cheque_date"], amount=p["amount"], direction="outflow", note=p["voucher_no"])
        return [base]
    if st == "allocation":
        base.update(counterparty=p["vendor"], reference=p["invoice"], planned=p["planned_date"],
                    amount=p["amount"], direction="outflow")
        return [base]
    if st == "bill_discount":
        base.update(counterparty=p["bank"], bank_name=p["bank"], reference=p["reference"],
                    planned=p["maturity_date"], amount=p["amount"], direction=BD_TYPES[p["bd_type"]],
                    note=p["bd_type"].capitalize() if p["bd_type"] != "lc maturity" else "LC maturity",
                    linked_invoice=p.get("invoice_no", ""))
        return [base]
    if st == "other":
        common = dict(base, reference=p.get("reference", ""), planned=p["date"], note=p.get("description", ""),
                      direction=p.get("direction"))
        if "amount" in p or not extra_cats:         # LONG layout
            return [dict(common, amount=p.get("amount"))]
        out = []                                     # WIDE layout: one item per category cell
        for header, cell in extra_cats:
            if P.is_blank(cell):
                continue
            amt, _ = P.parse_amount(cell)
            out.append(dict(common, amount=amt, category_text=header))
        return out
    raise ValueError(st)


def _natural_key(spec: SourceSpec, p: dict, item: dict, wide: bool) -> str | None:
    vals = [P.parse_str(p.get(k, "")) for k in spec.key_columns]
    if all(vals):
        key = "|".join(v.upper() for v in vals)
        return f"{key}|{normalise_header(item['category_text']).upper()}" if wide else key
    return None


def _import_forecast(db, spec, rows, header_i, mapping, unknown, rep, batch):
    st = spec.source_type
    res = CategoryResolver(db)
    if not res.any_categories:
        rep.add("error", "No categories yet. Upload the category list first.")
        raise _Abort
    wide = st == "other" and "amount" not in mapping.values()
    extra_idx = sorted(unknown) if wide else []
    if wide:
        if not extra_idx:
            rep.add("error", "No Amount column and no category columns found.")
            raise _Abort
        rep.category_headers = [unknown[j] for j in extra_idx]
    elif unknown:
        rep.add("warning", "Column(s) ignored: " + ", ".join(unknown.values()) + ".")

    seen: dict[str, tuple[int, tuple]] = {}
    hash_count: dict[str, int] = defaultdict(int)
    items: list[LineItem] = []
    unresolved: dict[str, list[LineItem]] = defaultdict(list)
    missing_default: set[str] = set()

    for excel_row, p, raw, row in parse_rows(rows, header_i, mapping, spec, rep):
        try:
            built = _items_for_row(st, p, [(unknown[j], row[j] if j < len(row) else None) for j in extra_idx])
        except P.CellError as exc:
            rep.add("error", str(exc).capitalize() + ".", excel_row)
            continue
        if not built:
            rep.add("info", "Row has no amounts.", excel_row)
        for it in built:
            if it["amount"] is None:
                rep.add("error", "Amount is missing.", excel_row, "Amount")
                continue
            if it["amount"] < 0:
                rep.add("error", f"Negative amount {it['amount']}: enter positive figures "
                                 "(direction comes from the source or the Type / Inflow-Outflow column).",
                        excel_row, "Amount")
                continue
            if it["amount"] == 0:
                rep.add("info", "Zero amount skipped.", excel_row)
                continue
            key = _natural_key(spec, p, it, wide)
            if key is None:
                base = _hash_key(st, it["planned"], it["amount"], it["counterparty"], it["note"],
                                 normalise_header(it["category_text"]))
                hash_count[base] += 1
                key = base if hash_count[base] == 1 else f"{base}-{hash_count[base]}"
            sig = (it["planned"], it["amount"], it["counterparty"], it["reference"], it["category_text"])
            if key in seen:
                first_row, first_sig = seen[key]
                if first_sig == sig:
                    rep.add("warning", f"Exact duplicate of row {first_row}; counted once.", excel_row)
                else:
                    rep.add("error", f"Same key '{key}' as row {first_row} but different details.", excel_row)
                continue
            seen[key] = (excel_row, sig)

            # ---- category and direction
            cat = None
            if it["category_text"]:
                cat = res.resolve(it["category_text"])
            else:
                dkey = {"bill_discount": f"bill_discount_{'in' if it['direction'] == 'inflow' else 'out'}",
                        "other": (f"other_{'in' if it['direction'] == 'inflow' else 'out'}"
                                  if it["direction"] else None)}.get(st, st)
                if dkey is None:
                    rep.add("error", "Give a Category or an Inflow/Outflow value.", excel_row)
                    continue
                cat = res.defaults.get(dkey)
                if cat is None:
                    missing_default.add(dkey)
                    continue
            provisional = False
            direction = it["direction"]
            if cat is not None:
                if direction is None:
                    direction = cat.direction.value
                elif direction != cat.direction.value:
                    msg = (f"'{cat.name}' is an {cat.direction.value} category but the row is an {direction}.")
                    if st == "other":
                        rep.add("warning", msg + " The row's own direction is used.", excel_row)
                    else:
                        rep.add("error", msg, excel_row)
                        continue
            elif direction is None:
                direction, provisional = "outflow", True   # fixed when the category is mapped

            li = LineItem(source_type=SourceType(st), source_key=key, row_number=excel_row,
                          category_id=cat.id if cat else None, category_text=it["category_text"],
                          direction=Direction(direction), direction_provisional=provisional,
                          counterparty=it["counterparty"], project=it["project"], reference=it["reference"],
                          bank_name=it["bank_name"], planned_date=it["planned"], amount=it["amount"],
                          risk_flag_imported=bool(it["risk"]), bill_discounted_imported=bool(it["bd"]),
                          linked_invoice=it["linked_invoice"], note=it["note"], raw=raw)
            items.append(li)
            if cat is None:
                unresolved[normalise_header(it["category_text"])].append(li)

    for dkey in sorted(missing_default):
        rep.add("error", f"The category list has no 'Default For Source' = {dkey}. Add it and upload the list again.")
    if rep.errors:
        raise _Abort
    if not items:
        rep.add("error", "No rows to import.")
        raise _Abort

    batch.items.extend(items)
    db.flush()
    for norm, its in unresolved.items():
        text = its[0].category_text
        s = res.suggest(text)
        exc = MappingException(batch_id=batch.id, raw_text=text, context="header" if wide else "category_column",
                               suggested_category_id=s.target if s else None, suggestion_score=s.score if s else None)
        db.add(exc)
        db.flush()
        rep.exceptions.append({"id": exc.id, "text": text, "rows": len(its),
                               "amount": f"{sum(i.amount for i in its):.3f}",
                               "suggestion": db.get(Category, s.target).name if s else None,
                               "score": s.score if s else None})
    rep.records = len(items)


# ------------------------------------------------------------------ reference sources
def _import_category_list(db, spec, rows, header_i, mapping, rep, user_id):
    seen_names, seen_defaults, seen_alias = {}, {}, {}
    parsed_rows = []
    for excel_row, p, raw, _row in parse_rows(rows, header_i, mapping, spec, rep):
        n = normalise_header(p["name"])
        if n in seen_names:
            rep.add("error", f"Category '{p['name']}' listed twice (first at row {seen_names[n]}).", excel_row)
            continue
        seen_names[n] = excel_row
        dfs = normalise_header(p.get("default_for_source", "")).replace(" ", "_")
        if dfs:
            if dfs not in DEFAULT_SOURCE_KEYS:
                rep.add("error", f"Default For Source '{p['default_for_source']}' is not one of: "
                                 + ", ".join(DEFAULT_SOURCE_KEYS) + ".", excel_row, "Default For Source")
                continue
            if dfs in seen_defaults:
                rep.add("error", f"Default For Source '{dfs}' already given at row {seen_defaults[dfs]}.", excel_row)
                continue
            seen_defaults[dfs] = excel_row
            need = "inflow" if dfs.endswith("_in") or dfs in ("collections", "additional") else "outflow"
            if p["direction"] != need:
                rep.add("error", f"'{p['name']}' is the default for {dfs}, which needs an {need} category.",
                        excel_row)
                continue
        aliases = [a.strip() for a in str(p.get("aliases", "")).split(";") if a.strip()]
        for a in aliases:
            an = normalise_header(a)
            if an in seen_alias and seen_alias[an] != n:
                rep.add("error", f"Alias '{a}' is used for two categories.", excel_row, "Aliases")
            seen_alias[an] = n
        parsed_rows.append((excel_row, p, dfs, aliases))
    for an, owner in seen_alias.items():
        if an in seen_names and an != owner:
            rep.add("error", f"Alias '{an}' is also the name of another category.")
    if rep.errors:
        raise _Abort
    existing = {normalise_header(c.name): c for c in db.scalars(select(Category))}
    created = updated = 0
    for _excel_row, p, dfs, aliases in parsed_rows:
        n = normalise_header(p["name"])
        values = dict(direction=Direction(p["direction"]), summary_group=p["summary_group"],
                      display_order=p["display_order"], default_treatment=Treatment(p["default_treatment"]),
                      is_active=True)
        cat = existing.get(n)
        if cat is None:
            cat = Category(name=p["name"], **values)
            db.add(cat); db.flush(); created += 1
            audit(db, "category.create", "category", cat.name, after={"name": cat.name, **values}, user_id=user_id)
        else:
            before = {k: getattr(cat, k) for k in values}
            for k, v in values.items():
                setattr(cat, k, v)
            if before != {k: getattr(cat, k) for k in values}:
                updated += 1
                audit(db, "category.update", "category", cat.name, before=before, after=values, user_id=user_id)
        for a in aliases:
            an = normalise_header(a)
            al = db.scalar(select(CategoryAlias).where(CategoryAlias.alias_normalised == an))
            if al is None:
                db.add(CategoryAlias(alias_normalised=an, alias_original=a, category_id=cat.id, created_by_id=user_id))
            elif al.category_id != cat.id:
                al.category_id = cat.id
        if dfs:
            sd = db.get(SourceDefaultCategory, dfs)
            if sd is None:
                db.add(SourceDefaultCategory(source_type=dfs, category_id=cat.id))
            else:
                sd.category_id = cat.id
    db.flush()
    rep.records = created + updated
    rep.add("info", f"{created} categories created, {updated} updated, "
                    f"{len(parsed_rows) - created - updated} unchanged.")


def _import_payment_history(db, spec, rows, header_i, mapping, rep):
    from app.models import CollectionHistory
    n = 0
    for excel_row, p, _raw, _row in parse_rows(rows, header_i, mapping, spec, rep):
        if p["paid_date"] < p["due_date"].replace(year=p["due_date"].year - 5):
            rep.add("error", "Paid date is implausibly early.", excel_row)
            continue
        h = db.scalar(select(CollectionHistory).where(CollectionHistory.invoice_no == p["invoice_no"]))
        vals = dict(customer=p["customer"], project=p.get("project", ""), invoice_date=p.get("invoice_date"),
                    due_date=p["due_date"], paid_date=p["paid_date"], amount=p["amount"])
        if h is None:
            db.add(CollectionHistory(invoice_no=p["invoice_no"], **vals))
        else:
            for k, v in vals.items():
                setattr(h, k, v)
        n += 1
    if rep.errors:
        raise _Abort
    rep.records = n


def _import_bank_balances(db, spec, rows, header_i, mapping, rep, user_id):
    from app.models import BankAccount, BankBalance
    from app.services.settings_service import get_business_settings
    b = get_business_settings(db)
    n = 0
    for excel_row, p, _raw, _row in parse_rows(rows, header_i, mapping, spec, rep):
        ccy = p["currency"].upper()
        if len(ccy) != 3 or not ccy.isalpha():
            rep.add("error", f"'{p['currency']}' is not a currency code.", excel_row, "Currency"); continue
        rate = p.get("fx_rate")
        if ccy == b.base_currency:
            if rate is not None and rate != 1:
                rep.add("error", f"{ccy} accounts must have rate 1.", excel_row, "Rate to OMR"); continue
            rate = Decimal(1)
        elif rate is None:
            rep.add("error", f"Enter the manual rate to {b.base_currency} for this {ccy} account.", excel_row,
                    "Rate to OMR"); continue
        acct = db.scalar(select(BankAccount).where(BankAccount.bank_name == p["bank"],
                                                   BankAccount.account_name == p["account"]))
        if acct is None:
            acct = BankAccount(bank_name=p["bank"], account_name=p["account"], currency=ccy)
            db.add(acct); db.flush()
        elif acct.currency != ccy:
            rep.add("error", f"Account is set up as {acct.currency}, file says {ccy}.", excel_row, "Currency"); continue
        bal = db.scalar(select(BankBalance).where(BankBalance.account_id == acct.id,
                                                  BankBalance.as_of_date == p["as_of_date"]))
        if bal is None:
            db.add(BankBalance(account_id=acct.id, as_of_date=p["as_of_date"], balance=p["balance"],
                               fx_rate_to_base=rate, entered_by_id=user_id))
        else:
            bal.balance, bal.fx_rate_to_base, bal.entered_by_id = p["balance"], rate, user_id
        n += 1
    db.flush()
    base_accounts = db.scalars(select(BankAccount).where(BankAccount.is_active,
                                                         BankAccount.currency == b.base_currency)).all()
    if len(base_accounts) > b.max_bank_accounts_base_currency:
        rep.add("error", f"{len(base_accounts)} active {b.base_currency} accounts; the limit is "
                         f"{b.max_bank_accounts_base_currency} (setting max_bank_accounts_base_currency).")
    if rep.errors:
        raise _Abort
    rep.records = n


def _import_bank_facility(db, spec, rows, header_i, mapping, rep, user_id):
    from app.models import BankFacility
    n = 0
    for excel_row, p, _raw, _row in parse_rows(rows, header_i, mapping, spec, rep):
        lim, used, avail = p.get("limit"), p.get("utilised"), p["available"]
        if lim is not None and used is not None and lim - used != avail:
            rep.add("warning", f"Limit - Utilised = {lim - used:.3f} but Available = {avail:.3f}; "
                               "Available is used.", excel_row)
        ftype = p.get("facility_type") or "Overdraft / working capital"
        f = db.scalar(select(BankFacility).where(BankFacility.bank_name == p["bank"],
                                                 BankFacility.facility_type == ftype,
                                                 BankFacility.as_of_date == p["as_of_date"]))
        vals = dict(limit_amount=lim, utilised_amount=used, available_amount=avail, entered_by_id=user_id)
        if f is None:
            db.add(BankFacility(bank_name=p["bank"], facility_type=ftype, as_of_date=p["as_of_date"], **vals))
        else:
            for k, v in vals.items():
                setattr(f, k, v)
        n += 1
    if rep.errors:
        raise _Abort
    rep.records = n


# ------------------------------------------------------------------ batch lifecycle
def make_current(db: Session, batch: ImportBatch, user_id: int | None = None) -> None:
    batch.status = BatchStatus.ACCEPTED
    for old in db.scalars(select(ImportBatch).where(ImportBatch.source_type == batch.source_type,
                                                    ImportBatch.slot == batch.slot,
                                                    ImportBatch.status == BatchStatus.ACCEPTED,
                                                    ImportBatch.id != batch.id)):
        old.status = BatchStatus.SUPERSEDED
        audit(db, "batch.supersede", "import_batch", old.id, after={"by": batch.id}, user_id=user_id)


def current_batches(db: Session, source_type: str | None = None) -> list[ImportBatch]:
    q = select(ImportBatch).where(ImportBatch.status == BatchStatus.ACCEPTED)
    if source_type:
        q = q.where(ImportBatch.source_type == SourceType(source_type))
    return list(db.scalars(q.order_by(ImportBatch.id)))


def import_file(db: Session, source_type: str, filename: str, content: bytes, *, user_id: int | None = None,
                as_of: date | None = None, slot: str | None = None, sheet: str | None = None) -> ImportReport:
    """Validate and import one uploaded file. Always records an ImportBatch (the file-hash log)."""
    settings = get_settings()
    if source_type not in SPECS:
        raise ValueError(f"unknown source type {source_type}")
    spec = SPECS[source_type]
    safe = safe_filename(filename)
    slot = (slot or (PurePath(safe).stem.lower() if source_type == "other" else source_type))[:80]
    rep = ImportReport(source_type=source_type, filename=safe, slot=slot)
    batch = ImportBatch(source_type=SourceType(source_type), slot=slot, original_filename=safe,
                        stored_filename="", sha256=sha256_of(content), size_bytes=len(content), as_of_date=as_of,
                        status=BatchStatus.UPLOADED, uploaded_by_id=user_id)
    db.add(batch)
    db.flush()
    rep.batch_id = batch.id

    same = db.scalar(select(ImportBatch).where(ImportBatch.sha256 == batch.sha256, ImportBatch.slot == slot,
                                               ImportBatch.status == BatchStatus.ACCEPTED,
                                               ImportBatch.id != batch.id))
    if same:
        rep.add("info", f"Identical to the current file (batch {same.id}, {same.uploaded_at:%d-%b %H:%M}). "
                        "Re-imported; your changes are kept.")
    sp = db.begin_nested()
    try:
        try:
            table: RawTable = read_table(safe, content, settings.upload_max_bytes, sheet)
        except UploadRejected as exc:
            rep.add("error", str(exc))
            raise _Abort from exc
        rep.sheet = table.sheet
        header_i, mapping, unknown = detect_header(table.rows, spec, rep)
        if source_type in FORECAST_SOURCES:
            _import_forecast(db, spec, table.rows, header_i, mapping, unknown, rep, batch)
        else:
            if unknown:
                rep.add("warning", "Column(s) ignored: " + ", ".join(unknown.values()) + ".")
            if source_type == "category_list":
                _import_category_list(db, spec, table.rows, header_i, mapping, rep, user_id)
            elif source_type == "payment_history":
                _import_payment_history(db, spec, table.rows, header_i, mapping, rep)
            elif source_type == "bank_balances":
                _import_bank_balances(db, spec, table.rows, header_i, mapping, rep, user_id)
            elif source_type == "bank_facility":
                _import_bank_facility(db, spec, table.rows, header_i, mapping, rep, user_id)
        sp.commit()
    except _Abort:
        sp.rollback()
        batch = db.get(ImportBatch, rep.batch_id)
        batch.status = BatchStatus.REJECTED
        rep.records, rep.exceptions = 0, []
    else:
        stored = f"{batch.id:06d}_{batch.sha256[:12]}_{safe}"
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        (settings.uploads_dir / stored).write_bytes(content)
        batch.stored_filename = stored
        if rep.exceptions:
            batch.status = BatchStatus.EXCEPTIONS
        else:
            make_current(db, batch, user_id)
    batch.row_count, batch.error_count = rep.rows_read, len(rep.errors)
    rep.status = batch.status.value
    batch.validation_report = rep.to_dict()
    audit(db, "import." + rep.status, "import_batch", batch.id,
          after={"source": source_type, "file": safe, "sha256": batch.sha256, "rows": rep.rows_read,
                 "records": rep.records, "errors": len(rep.errors), "warnings": len(rep.warnings),
                 "exceptions": len(rep.exceptions)}, user_id=user_id)
    db.flush()
    return rep


def open_exceptions(db: Session, batch_id: int | None = None) -> list[MappingException]:
    q = select(MappingException).where(MappingException.status == ExceptionStatus.OPEN)
    if batch_id:
        q = q.where(MappingException.batch_id == batch_id)
    return list(db.scalars(q.order_by(MappingException.id)))
