"""Command line:  python -m app.cli <command> [options]

  init-db                       create / upgrade tables and seed settings and scenarios
  show-settings                 print deployment and business settings
  list-tables                   print tables with row counts
  import FILE --source S        import one file (S = collections, vendor_pdc, other, ...)
  import-folder DIR             import every recognised file in a folder (category list first)
  batches                       list upload batches (the file-hash log)
  exceptions                    list open mapping exceptions with suggestions
  resolve ID --map NAME | --new [--name N --direction inflow|outflow --group G] | --ignore
  findings                      advisory duplicate / overlap checks on current data
  forecast [--as-of D] [--scenario S] [--risk on|off] [--delay-model] [--months N] [--snapshot]
                                print the lot grid (and optionally save today's snapshot)
  pdcs [--lot N]                list PDCs with their lot and hold status (the keys used below)
  hold KEY (--until D | --open) [--amount A] [--reason R]     put a PDC on hold / extend it
  release KEY                   release a held PDC
  override SOURCE KEY ACTION [--date D] [--lot-start D] [--amount A] [--reason R]
                                defer / redate / reduce / exclude / bill_discounted / risk_adjusted
  revoke ID                     revoke an override by id
  holds                         hold register with warnings
  create-admin USER [--name N]  create the first Admin (asks for a temporary password)
  create-user USER --role R     create a user (admin / preparer / viewer)
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db import get_engine, session_scope
from app.models import Base, Category, ImportBatch, MappingException

# file name -> source type (for import-folder); order = import order
FOLDER_RULES = [
    (r"categor", "category_list"),
    (r"bank_?balance", "bank_balances"),
    (r"facilit", "bank_facility"),
    (r"payment_?history", "payment_history"),
    (r"receivable|collections?(?!.*additional)", "collections"),
    (r"additional", "additional"),
    (r"pdc", "vendor_pdc"),
    (r"payment_?plan|allocation", "allocation"),
    (r"bd|bill_?discount|_lc", "bill_discount"),
    (r"other|recurring", "other"),
]


def detect_source(name: str) -> str | None:
    n = name.lower()
    if "additional" in n:
        return "additional"
    for pat, src in FOLDER_RULES:
        if re.search(pat, n):
            return src
    return None


def _print_report(rep) -> None:
    flag = {"accepted": "OK ", "exceptions": "MAP", "rejected": "ERR"}.get(rep.status, "   ")
    print(f"[{flag}] {rep.filename:<32} {rep.source_type:<16} status={rep.status:<10} rows={rep.rows_read:<4} "
          f"records={rep.records:<4} errors={len(rep.errors)} warnings={len(rep.warnings)} batch={rep.batch_id}")
    for i in rep.issues:
        if i.level == "info" and i.message == "Total row skipped.":
            print(f"        info: total row skipped (row {i.row})")
            continue
        where = f" row {i.row}" if i.row else ""
        col = f" [{i.column}]" if i.column else ""
        print(f"        {i.level}:{where}{col} {i.message}")
    for e in rep.exceptions:
        sug = f"suggest '{e['suggestion']}' ({e['score']:.0f})" if e["suggestion"] else "no good match"
        print(f"        exception #{e['id']}: '{e['text']}' ({e['rows']} rows, {e['amount']}) -> {sug}")


def _n(v) -> str:
    return f"{v:,.3f}" if v >= 0 else f"({-v:,.3f})"


def print_grid(fc) -> None:
    from app.advisory.commentary import summary_commentary
    from app.engine.forecast import LINE_LABELS
    cols = fc.columns
    w = 17
    print(f"Working capital forecast - {fc.settings.base_currency} - as of {fc.as_of:%d-%b-%Y} - "
          f"scenario {fc.scenario}" + (" (risk-adjusted collections excluded)" if fc.exclude_risk else ""))
    for lt in fc.lots:
        if lt.start in fc.locked:
            c = fc.locked[lt.start]
            print(f"  ACTUAL (locked) {lt.label}: closing {c['lines']['closing']} (snapshot of {c['snapshot_as_of']})")
    print(f"{'':<42}" + "".join(f"{c.label:>{w}}" for c in cols))
    print(f"{'':<42}" + "".join(f"{(fc.fc_lots[c.lots[0]].status.upper() if c.kind == 'lot' else ''):>{w}}"
                                for c in cols))

    def line(label, fn):
        print(f"{label[:41]:<42}" + "".join(f"{fn(c):>{w}}" for c in cols))

    line("A. " + LINE_LABELS["opening"], lambda c: _n(fc.line("opening", c)))
    for title, rows, total in (("B. Cash inflows", fc.inflow_rows, "inflows"),
                               ("C. Cash outflows", fc.outflow_rows, "outflows")):
        print(title)
        for r in rows:
            line(f"   {r.name}", lambda c, r=r: _n(fc.row(r, c)))
        line("   " + LINE_LABELS[total], lambda c, t=total: _n(fc.line(t, c)))
    for key in ("net", "closing", "facility", "fp_before", "gap_before"):
        line(LINE_LABELS[key], lambda c, k=key: _n(fc.line(k, c)))
    print("G. Cheque holds")
    for key in ("hold_out", "hold_in", "hold_net", "hold_cum", "closing_after", "fp_after", "shortfall_after"):
        line("   " + LINE_LABELS[key], lambda c, k=key: _n(fc.line(k, c)))
    line("   Are the holds sufficient?", lambda c: fc.status(c))
    print("H. Memo (not in totals)")
    for key in ("risk_excluded", "deferred_in", "holds_open"):
        line("   " + LINE_LABELS[key], lambda c, k=key: _n(fc.line(k, c)))
    t = fc.tieout
    print(f"\nERP bank total {_n(t['erp_total'])} = model opening {_n(t['model_opening'])}; "
          f"facility {_n(fc.facility_total)}")
    if t["previous"]:
        p = t["previous"]
        print(f"Forecast from {p['as_of']:%d-%b} expected {_n(p['expected'])} today; ERP {_n(t['erp_total'])}; "
              f"variance {_n(p['variance'])}")
    for wmsg in fc.warnings:
        print(f"warning: {wmsg}")
    print("\n" + summary_commentary(fc))


def main(argv: list[str] | None = None) -> None:
    from app.services.init_db import init_db
    from app.services.settings_service import get_business_settings

    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db"); sub.add_parser("show-settings"); sub.add_parser("list-tables")
    sub.add_parser("batches"); sub.add_parser("exceptions"); sub.add_parser("findings")
    pi = sub.add_parser("import"); pi.add_argument("file"); pi.add_argument("--source", required=True)
    pi.add_argument("--as-of", type=date.fromisoformat); pi.add_argument("--slot"); pi.add_argument("--sheet")
    pf = sub.add_parser("import-folder"); pf.add_argument("folder"); pf.add_argument("--as-of", type=date.fromisoformat)
    pr = sub.add_parser("resolve"); pr.add_argument("id", type=int)
    g = pr.add_mutually_exclusive_group(required=True)
    g.add_argument("--map", metavar="CATEGORY"); g.add_argument("--new", action="store_true")
    g.add_argument("--ignore", action="store_true")
    pr.add_argument("--name"); pr.add_argument("--direction", choices=["inflow", "outflow"])
    pr.add_argument("--group", default="Other")
    d = date.fromisoformat
    pfc = sub.add_parser("forecast"); pfc.add_argument("--as-of", type=d); pfc.add_argument("--scenario")
    pfc.add_argument("--risk", choices=["on", "off"]); pfc.add_argument("--delay-model", action="store_true")
    pfc.add_argument("--months", type=int); pfc.add_argument("--snapshot", action="store_true")
    pp = sub.add_parser("pdcs"); pp.add_argument("--lot", type=int); pp.add_argument("--as-of", type=d)
    ph = sub.add_parser("hold"); ph.add_argument("key")
    hg = ph.add_mutually_exclusive_group(required=True)
    hg.add_argument("--until", type=d); hg.add_argument("--open", action="store_true")
    ph.add_argument("--amount"); ph.add_argument("--reason", default="")
    prl = sub.add_parser("release"); prl.add_argument("key")
    po = sub.add_parser("override"); po.add_argument("source"); po.add_argument("key"); po.add_argument("action")
    po.add_argument("--date", type=d); po.add_argument("--lot-start", type=d); po.add_argument("--amount")
    po.add_argument("--reason", default="")
    prv = sub.add_parser("revoke"); prv.add_argument("id", type=int)
    sub.add_parser("holds")
    sub.add_parser("has-users")
    sub.add_parser("list-users")
    sub.add_parser("backup"); sub.add_parser("list-backups"); sub.add_parser("url")
    pvb = sub.add_parser("verify-backup"); pvb.add_argument("file")
    prb = sub.add_parser("restore-backup"); prb.add_argument("file")
    prb.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    pex = sub.add_parser("export"); pex.add_argument("--as-of", type=d); pex.add_argument("--scenario")
    prp = sub.add_parser("reset-password"); prp.add_argument("username")
    pca =sub.add_parser("create-user", aliases=["create-admin"])
    pca.add_argument("username"); pca.add_argument("--role", default=None,
                                                   choices=["admin", "preparer", "viewer", "approver"])
    pca.add_argument("--name", default="")
    args = p.parse_args(argv)
    if args.command == "create-admin" and args.role is None:
        args.role = "admin"
    if args.command in ("create-user", "create-admin"):
        args.command = "create-user"
        args.role = args.role or "viewer"

    s = get_settings()
    init_db(get_engine())

    if args.command == "init-db":
        print(f"Database ready: {s.database_path}")
    elif args.command == "show-settings":
        with session_scope() as db:
            b = get_business_settings(db)
        print(json.dumps({"database": str(s.database_path), "host": s.host, "port": s.port,
                          "https": s.https_enabled, "upload_max_mb": s.upload_max_mb,
                          "business": b.model_dump()}, indent=2))
    elif args.command == "list-tables":
        with session_scope() as db:
            for name, table in sorted(Base.metadata.tables.items()):
                print(f"{name:<26} {db.scalar(select(func.count()).select_from(table)):>6}")
    elif args.command == "import":
        from app.importers.pipeline import import_file
        path = Path(args.file)
        with session_scope() as db:
            rep = import_file(db, args.source, path.name, path.read_bytes(), as_of=args.as_of, slot=args.slot,
                              sheet=args.sheet)
            _print_report(rep)
    elif args.command == "import-folder":
        from app.importers.pipeline import import_file
        folder = Path(args.folder)
        files = [f for f in sorted(folder.iterdir()) if f.suffix.lower() in (".xlsx", ".csv")]
        order = [src for _, src in FOLDER_RULES]
        plan = sorted(((detect_source(f.name), f) for f in files), key=lambda x: order.index(x[0]) if x[0] else 99)
        for src, f in plan:
            if src is None:
                print(f"[---] {f.name:<32} not recognised, skipped")
                continue
            with session_scope() as db:
                _print_report(import_file(db, src, f.name, f.read_bytes(), as_of=args.as_of))
    elif args.command == "batches":
        with session_scope() as db:
            for b in db.scalars(select(ImportBatch).order_by(ImportBatch.id)):
                print(f"#{b.id:<4} {b.uploaded_at:%Y-%m-%d %H:%M} {b.source_type.value:<16} {b.slot:<24} "
                      f"{b.status.value:<11} rows={b.row_count:<4} sha256={b.sha256[:16]}  {b.original_filename}")
    elif args.command == "exceptions":
        from app.importers.pipeline import open_exceptions
        with session_scope() as db:
            rows = open_exceptions(db)
            if not rows:
                print("No open exceptions.")
            for e in rows:
                sug = db.get(Category, e.suggested_category_id).name if e.suggested_category_id else None
                print(f"#{e.id:<4} batch {e.batch_id:<4} '{e.raw_text}' -> "
                      + (f"suggest '{sug}' ({e.suggestion_score:.0f})" if sug else "no good match"))
    elif args.command == "resolve":
        from app.importers import exceptions as X
        with session_scope() as db:
            e = db.get(MappingException, args.id)
            if e is None:
                raise SystemExit(f"exception {args.id} not found")
            if args.map:
                cat = db.scalar(select(Category).where(func.lower(Category.name) == args.map.lower()))
                if cat is None:
                    raise SystemExit(f"category '{args.map}' not found")
                done = X.map_to_category(db, args.id, cat.id)
            elif args.new:
                if not args.direction:
                    raise SystemExit("--direction inflow|outflow is required with --new")
                done = X.add_new_category(db, args.id, name=args.name, direction=args.direction,
                                          summary_group=args.group)
            else:
                done = X.ignore(db, args.id)
            print(f"Resolved #{args.id}." + (f" Batch {e.batch_id} is now current." if done else ""))
    elif args.command == "findings":
        from app.advisory.overlaps import find_overlaps
        with session_scope() as db:
            fs = find_overlaps(db)
            if not fs:
                print("No findings.")
            for f in fs:
                print(f"[{f.rule}] {f.message}\n        -> {f.suggested_action}")
    elif args.command == "forecast":
        from app.engine.loader import run_forecast
        from app.services.settings_service import get_business_settings as gbs
        with session_scope() as db:
            st = gbs(db)
            if args.months:
                st = st.model_copy(update={"horizon_months": args.months})
            fc = run_forecast(db, as_of=args.as_of, scenario=args.scenario, settings=st,
                              exclude_risk=None if args.risk is None else args.risk == "on",
                              use_delay_model=True if args.delay_model else None)
            print_grid(fc)
            if args.snapshot:
                from app.services.snapshots import save_snapshot
                snap = save_snapshot(db, fc)
                print(f"\nSnapshot #{snap.id} saved for {snap.snapshot_date} ({fc.scenario}).")
    elif args.command == "pdcs":
        from app.engine.loader import run_forecast
        with session_scope() as db:
            fc = run_forecast(db, as_of=args.as_of)
            print(f"{'Key':<22}{'Vendor':<24}{'Cheque date':<13}{'Lot':<11}{'Amount':>14}  Action")
            for i in sorted((x for x in fc.items if x.source == "vendor_pdc" and x.status == "active"),
                            key=lambda x: (x.lot, x.eff_date)):
                if args.lot is not None and i.lot != args.lot - 1:
                    continue
                act = "Active"
                if i.hold:
                    h = i.hold
                    act = (f"HOLD {_n(h.amount)} until " + (f"{h.honour_date:%d-%b-%Y}" if h.honour_date
                                                             else "open-ended"))
                elif "deferred" in i.flags:
                    act = "Deferred"
                print(f"{i.key:<22}{i.item.counterparty[:23]:<24}{i.item.planned_date:%d-%b-%Y}  "
                      f"{fc.fc_lots[i.lot].label:<11}{_n(i.eff_amount):>14}  {act}")
    elif args.command in ("hold", "release", "override", "revoke"):
        from app.services import overrides as OV
        with session_scope() as db:
            try:
                if args.command == "hold":
                    o = OV.hold_cheque(db, args.key, honour_date=args.until, open_ended=args.open,
                                       amount=args.amount, reason=args.reason)
                    print(f"Override #{o.id}: {args.key} on hold "
                          + (f"until {o.new_date:%d-%b-%Y}" if o.new_date else "(open-ended)")
                          + (f", amount {_n(o.new_amount)}" if o.new_amount else ", full amount"))
                elif args.command == "release":
                    OV.release_hold(db, args.key)
                    print(f"{args.key} released: it is honoured on its own date.")
                elif args.command == "override":
                    o = OV.set_override(db, args.source, args.key, args.action, new_date=args.date,
                                        target_lot_start=args.lot_start, new_amount=args.amount,
                                        reason=args.reason)
                    print(f"Override #{o.id}: {args.action} on {args.source} {args.key}.")
                else:
                    OV.revoke(db, args.id)
                    print(f"Override #{args.id} revoked.")
            except OV.OverrideError as exc:
                raise SystemExit(f"Not saved: {exc}")
    elif args.command == "has-users":          # exit code 3 when no user exists yet (used by start_app.bat)
        from app.models import User
        with session_scope() as db:
            n = db.scalar(select(func.count()).select_from(User))
        print(f"{n} user(s) in {s.database_path}")
        raise SystemExit(0 if n else 3)
    elif args.command == "url":                   # used by start_app.bat to open the browser
        host = "localhost" if s.host in ("0.0.0.0", "::", "127.0.0.1") else s.host
        print(f"{'https' if s.https_enabled else 'http'}://{host}:{s.port}")
    elif args.command in ("backup", "list-backups", "verify-backup", "restore-backup"):
        from app.services import backup as B
        from app.services.audit import audit
        if getattr(args, "file", None) and not Path(args.file).exists() and (s.backups_dir / args.file).exists():
            args.file = str(s.backups_dir / args.file)          # a bare name from list-backups
        try:
            if args.command == "backup":
                path = B.create_backup(s, note="console")
                with session_scope() as db:
                    audit(db, "backup.create", "backup", path.name, after={"via": "console"})
                print(f"Backup written: {path}")
            elif args.command == "list-backups":
                for b in B.list_backups(s):
                    print(f"{b.path.name}  {b.created:%d-%b-%Y %H:%M}  {b.size / 1024:,.0f} KB")
            elif args.command == "verify-backup":
                m, files = B.open_backup(Path(args.file), s.backup_passphrase)
                print(f"OK: backup of {m['created']} (app {m['app_version']}), {len(files)} files, "
                      f"{m['users']} user(s), database integrity ok.")
            else:
                m, files = B.open_backup(Path(args.file), s.backup_passphrase)
                print(f"Backup of {m['created']}: {len(files)} files, {m['users']} user(s). It will REPLACE the "
                      f"current database and uploads in {s.instance_dir}.")
                print("Stop the app first (close its window). The current data is backed up before the restore.")
                if not args.yes and input("Type RESTORE to continue: ").strip() != "RESTORE":
                    raise SystemExit("Not restored.")
                from app.db import reset_engine
                reset_engine()
                safety = B.restore_backup(Path(args.file), s)
                with session_scope() as db:
                    audit(db, "backup.restore", "backup", Path(args.file).name, after={"safety_backup": safety.name})
                print(f"Restored. The data from before the restore is in {safety.name}. Start the app again.")
        except B.BackupError as exc:
            raise SystemExit(f"Backup error: {exc}")
    elif args.command == "export":
        from app.engine.loader import get_scenario, run_forecast
        from app.services.export_service import create_export
        with session_scope() as db:
            sc = get_scenario(db, args.scenario) if args.scenario else None
            fc = run_forecast(db, as_of=args.as_of, scenario=sc)
            log = create_export(db, fc, None)
            print(f"Export #{log.id}: {log.check_status.value}{' - released' if log.released else ' - BLOCKED'}")
            print(log.note)
            for diff in (log.differences or [])[:20]:
                print(f"  {diff['sheet']}!{diff['cell']} {diff['item']}: app {diff['app']} excel {diff['excel']}")
            if log.released:
                print(f"File: {s.exports_dir / log.filename}")
        if not log.released:
            raise SystemExit(4)
    elif args.command == "list-users":
        from app.models import User
        from app.services.auth import is_locked
        with session_scope() as db:
            for u in db.scalars(select(User).order_by(User.username)):
                flags = [f for f, on in (("inactive", not u.is_active), ("locked", is_locked(u)),
                                         ("must change password", u.must_change_password)) if on]
                print(f"{u.username:<20} {u.role.value:<10} {', '.join(flags)}")
    elif args.command == "reset-password":
        # Console recovery (e.g. forgotten Admin password). Whoever can run this on the server PC
        # already has the database file, so this gives no extra access. Audited as done from the console.
        from app.models import User
        from app.services.audit import audit
        from app.services.auth import hash_password, temporary_password
        with session_scope() as db:
            u = db.scalar(select(User).where(func.lower(User.username) == args.username.strip().lower()))
            if u is None:
                raise SystemExit(f"No user '{args.username}'. Run:  list-users")
            temp = temporary_password()
            u.password_hash, u.must_change_password = hash_password(temp), True
            u.failed_logins, u.locked_until, u.is_active = 0, None, True
            audit(db, "user.password_reset", "user", u.username, after={"via": "console", "reactivated": True})
            print(f"Password of '{u.username}' ({u.role.value}) reset. Account unlocked and active.")
            print(f"Temporary password:  {temp}")
            print("Sign in with it now; you will be asked to choose a new password. It is not shown again.")
    elif args.command == "create-user":
        import getpass
        from app.services.auth import AuthError, check_password_rules, create_user
        print("Password rules: at least 10 characters, letters with numbers or symbols, not the user name.")
        print("Nothing is shown while you type the password - that is normal. Press Enter when done.")
        for attempt in range(3):
            pw = getpass.getpass(f"Temporary password for {args.username.lower()} (hidden): ")
            try:
                check_password_rules(pw, args.username.lower())
            except AuthError as exc:
                print(f"  {exc} Try again.")
                continue
            if pw != getpass.getpass("Type it again (hidden): "):
                print("  The two entries do not match. Try again.")
                continue
            break
        else:
            raise SystemExit("Not created: no valid password after 3 tries.")
        with session_scope() as db:
            try:
                u = create_user(db, args.username, pw, args.role, args.name, must_change_password=True)
            except AuthError as exc:
                raise SystemExit(f"Not created: {exc}")
            print(f"User '{u.username}' created as {u.role.value}. Sign in with user name '{u.username}'; "
                  "you will be asked to choose your own password.")
    elif args.command == "holds":
        from app.engine.loader import run_forecast
        with session_scope() as db:
            fc = run_forecast(db)
            if not fc.holds:
                print("No cheques on hold.")
            for i in fc.holds:
                h = i.hold
                hon = f"{h.honour_date:%d-%b-%Y}" if h.honour_date else "open-ended"
                hl = fc.fc_lots[h.honour_lot].label if h.honour_lot is not None else "-"
                print(f"{i.item.counterparty[:22]:<23} chq {i.item.reference:<10} {i.item.planned_date:%d-%b} "
                      f"lot {fc.fc_lots[h.out_lot].label:<10} held {_n(h.amount):>12} -> {hon} (lot {hl}) "
                      f"days {h.days_held if h.days_held is not None else '-'} ext {h.times_extended} "
                      f"'{h.reason}' by {h.held_by or '-'}")
                for wmsg in h.warnings:
                    print(f"      ! {wmsg}")


if __name__ == "__main__":
    main()
