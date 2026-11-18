"""Turns Tally records into rows in the in-memory database (ported from importer.ts).

Usage:  imp = Importer(store, company_id, run_id, balances_as_of)
        for rec in records: imp.add(rec)      # maps and stages in plain Python memory (no database lock held)
        imp.commit()                            # one short transaction writes everything at once
So a failed or cancelled month never leaves half-written data behind.
Names are unique per company (like Tally); the importer keeps a name -> id map and re-uses an id when a master changes.
"""
from __future__ import annotations

from datetime import date, timedelta

from lxml import etree

from ..tally import mappers as M
from .schema import COLUMNS
from .store import Store, now_iso
from .voucher_types import default_effects, resolve_base_type

RESERVED_GROUPS = {
    "Capital Account", "Current Assets", "Current Liabilities", "Loans (Liability)", "Fixed Assets", "Investments",
    "Branch / Divisions", "Suspense A/c", "Misc. Expenses (ASSET)", "Sales Accounts", "Purchase Accounts",
    "Direct Expenses", "Direct Incomes", "Indirect Expenses", "Indirect Incomes", "Bank Accounts", "Bank OD A/c",
    "Cash-in-Hand", "Deposits (Asset)", "Duties & Taxes", "Loans & Advances (Asset)", "Provisions",
    "Reserves & Surplus", "Secured Loans", "Stock-in-Hand", "Sundry Creditors", "Sundry Debtors", "Unsecured Loans",
}


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def _b(v):
    return None if v is None else int(bool(v))


class Importer:
    def __init__(self, store: Store, company_id: int, run_id: int = 0, balances_as_of: str | None = None):
        self.store, self.cid, self.run_id = store, company_id, run_id
        self.balances_as_of = balances_as_of
        self.counts: dict[str, int] = {}
        self.warnings: list[str] = []
        self._warned: set[str] = set()
        self.voucher_range: dict[str, str] = {}
        self._reset_stage()

    # ------------------------------------------------------------------ staging
    def _reset_stage(self) -> None:
        self.master: dict[str, dict[str, dict]] = {}      # table -> name -> row dict (masters seen in this batch)
        self.implicit: dict[str, set[str]] = {}            # table -> names first created by a reference (not a master)
        self.new_ids: dict[str, dict[str, int]] = {}       # table -> name -> id assigned in this batch
        self.rows: dict[str, list[tuple]] = {}             # table -> new rows
        self.vouchers: list[M.Voucher] = []
        self.opening_ledgers: set[int] = set()
        self.closing_value_ledgers: set[int] = set()
        self.snapshot_keys: set[tuple[int, str]] = set()
        self.balance_keys: set[tuple[int, str]] = set()
        self.counts_stage: dict[str, int] = {}
        self.range_replace: tuple[str, str] | None = None
        self._implicit_done: set[tuple[str, str]] = set()

    def discard(self) -> None:
        self._reset_stage()

    def warn(self, msg: str) -> None:
        if len(self._warned) > 500 or msg in self._warned:
            return
        self._warned.add(msg)
        self.warnings.append(msg)

    def _inc(self, k: str, n: int = 1) -> None:
        self.counts_stage[k] = self.counts_stage.get(k, 0) + n

    def _row(self, table: str, **kw) -> tuple:
        return tuple(kw.get(c) for c in COLUMNS[table])

    def _stage(self, table: str, row: tuple) -> None:
        self.rows.setdefault(table, []).append(row)

    def _id(self, table: str, name: str, *, create_defaults: dict | None = None) -> int:
        """Existing id for a name (committed or staged); otherwise assign a new one and stage a bare row."""
        hit = self.store.name_map(table, self.cid).get(name) or self.new_ids.get(table, {}).get(name)
        if hit:
            return hit
        i = self.store.next_id(table)
        self.new_ids.setdefault(table, {})[name] = i
        self.implicit.setdefault(table, set()).add(name)
        return i

    def _upsert_master(self, table: str, name: str, row: dict) -> int:
        i = self._id(table, name)
        self.implicit.get(table, set()).discard(name)
        self.master.setdefault(table, {})[name] = {**row, "id": i, "company_id": self.cid, "name": name}
        return i

    # ------------------------------------------------------------------ record intake
    def add(self, el: etree._Element) -> None:
        tag = el.tag.upper()
        if tag == "GROUP":
            g = M.map_group(el)
            if not g["name"]:
                return
            self._upsert_master("ledger_groups", g["name"], dict(
                parent_name=g["parent"], is_revenue=_b(g["is_revenue"]), affects_gross_profit=_b(g["affects_gross_profit"]),
                is_deemed_positive=_b(g["is_deemed_positive"]), is_reserved=0, guid=g["guid"], alter_id=g["alter_id"]))
            self._inc("groups")
        elif tag == "LEDGER":
            self._ledger(M.map_ledger(el))
        elif tag == "VOUCHERTYPE":
            v = M.map_voucher_type(el)
            if v["name"]:
                self._upsert_master("voucher_types", v["name"], dict(parent=v["parent"], base_type="Unknown",
                                    affects_accounts=1, affects_inventory=0, is_known=0))
                self._inc("voucher_types")
        elif tag == "COSTCENTRE":
            c = M.map_cost_centre(el)
            if c["name"]:
                self._upsert_master("cost_centres", c["name"], dict(parent=c["parent"], category=c["category"], guid=c["guid"]))
                self._inc("cost_centres")
        elif tag == "STOCKGROUP":
            g = M.map_stock_group(el)
            if g["name"]:
                self._upsert_master("stock_groups", g["name"], dict(parent=g["parent"], guid=g["guid"]))
                self._inc("stock_groups")
        elif tag == "UNIT":
            u = M.map_unit(el)
            if u["name"]:
                self._upsert_master("units", u["name"], dict(is_simple=int(u["is_simple"]), base_unit=u["base_unit"],
                                    additional_unit=u["additional_unit"], conversion=u["conversion"], decimals=u["decimals"]))
                self._inc("units")
        elif tag == "GODOWN":
            g = M.map_godown(el)
            if g["name"]:
                self._upsert_master("godowns", g["name"], dict(parent=g["parent"]))
                self._inc("godowns")
        elif tag == "STOCKITEM":
            self._stock_item(M.map_stock_item(el))
        elif tag == "VOUCHER":
            v = M.map_voucher(el)
            if v is None:
                self._inc("vouchers_skipped_invalid")
                self.warn("Skipped a voucher without a valid DATE or VOUCHERTYPENAME")
                return
            for w in v.warnings:
                self.warn(w)
            self.voucher_range["min"] = min(v.date, self.voucher_range.get("min", v.date))
            self.voucher_range["max"] = max(v.date, self.voucher_range.get("max", v.date))
            self.vouchers.append(v)
        elif tag == "COMPANY":
            pass
        else:
            self._inc(f"ignored_{tag.lower()}")

    def _ledger(self, l: dict) -> None:
        if not l["name"]:
            return
        lid = self._upsert_master("ledgers", l["name"], dict(
            group_name=l["parent"], guid=l["guid"], master_id=l["master_id"], alter_id=l["alter_id"],
            opening_paise=l["opening_paise"], is_billwise=int(l["is_billwise"]), credit_period_days=l["credit_days"],
            credit_limit_paise=l["credit_limit_paise"], gstin=l["gstin"], state=l["state"], currency=l["currency"]))
        if l["has_closing_values"]:
            self.closing_value_ledgers.add(lid)
            for cv in l["closing_values"]:
                self._stage("ledger_closing_values", self._row("ledger_closing_values", company_id=self.cid, ledger_id=lid,
                            as_of=cv["date"], amount_paise=cv["amount_paise"]))
                self._inc("manual_closing_values")
        self.opening_ledgers.add(lid)  # opening bills come only from the ledger master: replace them wholesale
        for bill in l["opening_bills"]:
            d = bill.bill_date or "1900-01-01"
            due = bill.due_date or (add_days(bill.bill_date, bill.credit_days) if bill.credit_days is not None and bill.bill_date else None)
            if not bill.bill_date:
                self.warn(f'Opening bill "{bill.name}" of ledger "{l["name"]}" has no bill date; it cannot be aged accurately')
            self._stage("bill_allocations", self._row("bill_allocations", id=self.store.next_id("bill_allocations"), company_id=self.cid,
                        voucher_id=None, ledger_id=lid, bill_name=bill.name, bill_type=bill.bill_type, amount_paise=bill.amount_paise,
                        date=d, credit_days=bill.credit_days, due_date=due, is_opening=1))
            self._inc("opening_bills")
        if l["closing_paise"] is not None and self.balances_as_of:
            self.balance_keys.add((lid, self.balances_as_of))
            self._stage("source_balances", self._row("source_balances", company_id=self.cid, ledger_id=lid,
                        as_of=self.balances_as_of, closing_paise=l["closing_paise"], run_id=self.run_id))
            self._inc("source_balances")
        self._inc("ledgers")

    def _stock_item(self, s: dict) -> None:
        if not s["name"]:
            return
        valuation_only = s["base_unit"] is None and s["parent"] is None and s["guid"] is None
        if not valuation_only:  # a valuation-only record (Name + Closing*) must not wipe master fields
            self._upsert_master("stock_items", s["name"], dict(
                group_name=s["parent"], base_unit=s["base_unit"], guid=s["guid"], master_id=s["master_id"], alter_id=s["alter_id"],
                opening_qty_e4=s["opening_qty_e4"], opening_value_paise=s["opening_value_paise"],
                costing_method=s["costing_method"], hsn=s["hsn"]))
            self._inc("stock_items")
        iid = self._id("stock_items", s["name"])
        if s["closing_qty_e4"] is not None and s["closing_value_paise"] is not None and self.balances_as_of:
            self.snapshot_keys.add((iid, self.balances_as_of))
            self._stage("stock_snapshots", self._row("stock_snapshots", company_id=self.cid, stock_item_id=iid,
                        as_of=self.balances_as_of, qty_e4=s["closing_qty_e4"], value_paise=s["closing_value_paise"],
                        source="tally", run_id=self.run_id))
            self._inc("stock_snapshots")

    # ------------------------------------------------------------------ writing
    def replace_vouchers_in(self, frm: str, to: str) -> None:
        """Full-refresh semantics for this batch: vouchers in [from, to] that Tally no longer has are removed."""
        self.range_replace = (frm, to)

    def commit(self) -> None:
        st, cid = self.store, self.cid
        with st.transaction():
            # --- masters: replace changed rows (same id), insert new ones
            for table, by_name in self.master.items():
                committed = st.name_map(table, cid)
                st.delete_where_in(table, "id", [r["id"] for n, r in by_name.items() if n in committed])
                st.insert(table, [tuple(r.get(c) for c in COLUMNS[table]) for r in by_name.values()])
            # --- side tables that are replaced wholesale per ledger / item
            st.delete_where_in("bill_allocations", "ledger_id", sorted(self.opening_ledgers), "is_opening = 1 AND company_id = ?", [cid])
            st.delete_where_in("ledger_closing_values", "ledger_id", sorted(self.closing_value_ledgers), "company_id = ?", [cid])
            for table, keys, col in (("source_balances", self.balance_keys, "ledger_id"), ("stock_snapshots", self.snapshot_keys, "stock_item_id")):
                for as_of in {k[1] for k in keys}:
                    st.delete_where_in(table, col, [k[0] for k in keys if k[1] == as_of], "as_of = ? AND company_id = ?", [as_of, cid])
            for table in ("ledger_closing_values", "bill_allocations", "source_balances", "stock_snapshots"):
                st.insert(table, self.rows.get(table, []))
            self._write_vouchers()
        # publish new names only after the transaction succeeded
        for table, m in self.new_ids.items():
            st.name_map(table, cid).update(m)
        for k, v in self.counts_stage.items():
            self.counts[k] = self.counts.get(k, 0) + v
        st.bump(cid)
        self._reset_stage()

    def _write_vouchers(self) -> None:
        st, cid = self.store, self.cid
        vs = self.vouchers
        keys = [v.source_key for v in vs]
        # an existing voucher with the same key is replaced; in full-refresh mode so is every voucher in the range
        existing = st.ids_where_in("vouchers", "source_key", keys, "company_id = ?", [cid]) if keys else []
        old = set(existing)
        if self.range_replace:
            frm, to = self.range_replace
            old |= {r["id"] for r in st.rows("SELECT id FROM vouchers WHERE company_id = ? AND date BETWEEN ? AND ?", [cid, frm, to])}
        if old:
            gone = sorted(old)
            for t in ("voucher_lines", "inventory_lines", "bill_allocations", "cost_allocations"):
                st.delete_where_in(t, "voucher_id", gone)
            st.delete_where_in("vouchers", "id", gone)
            replaced = len(existing)
            self._inc("vouchers_updated", replaced)
            if len(old) > replaced:
                self._inc("vouchers_deleted", len(old) - replaced)
        self._inc("vouchers_created", len(vs) - len(existing))

        vrows, lrows, crow, brows, irows = [], [], [], [], []
        ledger_id = lambda n: self._id("ledgers", n)
        item_id = lambda n: self._id("stock_items", n)
        cc_id = lambda n: self._id("cost_centres", n)
        for v in vs:
            vid = st.next_id("vouchers")
            total = sum(l.amount_paise for l in v.lines)
            party_id = ledger_id(v.party_name) if v.party_name else None
            vrows.append(self._row("vouchers", id=vid, company_id=cid, source_key=v.source_key, guid=v.guid, master_id=v.master_id,
                         alter_id=v.alter_id, date=v.date, voucher_type=v.voucher_type, base_type="Unknown", number=v.number,
                         reference=v.reference, party_name=v.party_name, party_ledger_id=party_id, narration=v.narration,
                         is_cancelled=int(v.is_cancelled), is_optional=int(v.is_optional), is_postdated=int(v.is_postdated),
                         is_invoice=int(v.is_invoice), is_accounting=1, is_inventory=0, line_total_paise=total, run_id=self.run_id))
            for i, l in enumerate(v.lines):
                lid = ledger_id(l.ledger_name)
                lrows.append((st.next_id("voucher_lines"), vid, cid, i, lid, l.amount_paise))
                for ca in l.cost_allocations:
                    if ca["cost_centre"]:
                        crow.append((st.next_id("cost_allocations"), vid, cid, lid, cc_id(ca["cost_centre"]), ca["amount_paise"]))
                for b in l.bills:
                    due = b.due_date or (add_days(v.date, b.credit_days) if b.credit_days is not None else None)
                    brows.append(self._row("bill_allocations", id=st.next_id("bill_allocations"), company_id=cid, voucher_id=vid,
                                 ledger_id=lid, bill_name=b.name, bill_type=b.bill_type, amount_paise=b.amount_paise, date=v.date,
                                 credit_days=b.credit_days, due_date=due, is_opening=0))
            for i, il in enumerate(v.inventory):
                irows.append(self._row("inventory_lines", id=st.next_id("inventory_lines"), voucher_id=vid, company_id=cid, line_no=i,
                             stock_item_id=item_id(il.item_name), direction=il.direction, qty_e4=il.qty_e4, billed_qty_e4=il.billed_qty_e4,
                             unit=il.unit, value_paise=il.value_paise, godown=il.godown, batch=il.batch, mfg_date=il.mfg_date,
                             expiry_date=il.expiry_date, ledger_id=ledger_id(il.ledger_name) if il.ledger_name else None))
        # references created while mapping vouchers (unknown ledgers / items / cost centres) need their bare rows too
        self._flush_implicit()
        st.insert("vouchers", vrows)
        st.insert("voucher_lines", lrows)
        st.insert("cost_allocations", crow)
        st.insert("bill_allocations", brows)
        st.insert("inventory_lines", irows)

    def _flush_implicit(self) -> None:
        """Insert bare rows for names that vouchers referenced but no master record described."""
        cid, st = self.cid, self.store
        done = self._implicit_done
        for table, names in self.implicit.items():
            fresh = [n for n in names if (table, n) not in done]
            rows = []
            for n in fresh:
                base = {"id": self.new_ids[table][n], "company_id": cid, "name": n}
                if table == "ledgers":
                    base.update(opening_paise=0, is_billwise=0)
                elif table == "stock_items":
                    base.update(opening_qty_e4=0, opening_value_paise=0)
                rows.append(tuple(base.get(c) for c in COLUMNS[table]))
                done.add((table, n))
            st.insert(table, rows)

    # ------------------------------------------------------------------ finishing
    def finalize(self) -> None:
        finalize_company(self.store, self.cid)


def finalize_company(st: Store, cid: int) -> None:
    """Resolve group primaries, voucher-type semantics and per-voucher flags. Safe to call repeatedly."""
    with st.transaction():
        groups = st.rows("SELECT id, name, parent_name FROM ledger_groups WHERE company_id = ?", [cid])
        parent = {g["name"]: g["parent_name"] for g in groups}
        upd = []
        for g in groups:
            cur, seen = g["name"], set()
            while parent.get(cur) and cur not in seen:
                seen.add(cur)
                cur = parent[cur]
            upd.append((g["id"], cur, int(g["name"] in RESERVED_GROUPS)))
        with st.register("_gp", ["id", "primary_group", "is_reserved"], upd):
            st.execute("UPDATE ledger_groups SET primary_group = p.primary_group, is_reserved = p.is_reserved FROM _gp p WHERE ledger_groups.id = p.id")
        st.execute("UPDATE ledgers SET group_id = g.id FROM ledger_groups g WHERE g.company_id = ledgers.company_id "
                   "AND g.name = ledgers.group_name AND ledgers.company_id = ?", [cid])

        # voucher types referenced by vouchers but missing from masters
        have = {r["name"] for r in st.rows("SELECT name FROM voucher_types WHERE company_id = ?", [cid])}
        missing = [r["voucher_type"] for r in st.rows("SELECT DISTINCT voucher_type FROM vouchers WHERE company_id = ?", [cid])
                   if r["voucher_type"] not in have]
        vmap = st.name_map("voucher_types", cid)
        st.insert("voucher_types", [(vmap.setdefault(n, st.next_id("voucher_types")), cid, n, None, "Unknown", 1, 0, 0) for n in missing])

        vts = st.rows("SELECT id, name, parent FROM voucher_types WHERE company_id = ?", [cid])
        vparent = {v["name"]: v["parent"] for v in vts}
        rows = []
        for vt in vts:
            base, known = resolve_base_type(vt["name"], vparent)
            acc, inv = default_effects(base)
            rows.append((vt["id"], base, int(acc), int(inv), int(known)))
        with st.register("_vt", ["id", "base_type", "aa", "ai", "known"], rows):
            st.execute("UPDATE voucher_types SET base_type = t.base_type, affects_accounts = t.aa, affects_inventory = t.ai, is_known = t.known "
                       "FROM _vt t WHERE voucher_types.id = t.id")
        st.execute(
            "UPDATE vouchers SET base_type = vt.base_type, "
            "is_accounting = CASE WHEN vouchers.is_cancelled = 1 OR vouchers.is_optional = 1 THEN 0 ELSE vt.affects_accounts END, "
            "is_inventory = CASE WHEN vouchers.is_cancelled = 1 OR vouchers.is_optional = 1 THEN 0 ELSE vt.affects_inventory END "
            "FROM voucher_types vt WHERE vt.company_id = vouchers.company_id AND vt.name = vouchers.voucher_type AND vouchers.company_id = ?",
            [cid])
    st.bump(cid)
