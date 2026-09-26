"""Command-line tools (use the project's virtualenv python).

    python cli.py init-db                    # create .env (first run) and migrate the database
    python cli.py seed-demo [--password P]   # fictitious demo firm, users and entities
    python cli.py create-owner --username U --name "Full Name"
    python cli.py recompute [--as-of YYYY-MM-DD]
    python cli.py nightly [--catch-up]       # recompute + reminders + digest (Task Scheduler / cron)
    python cli.py package                    # clean copy for the ICAI GitHub upload (Desktop/AICA-Submission-Kit)
    python cli.py backup                     # online SQLite backup to instance/backups/
    python cli.py restore instance/backups/<file>.db
    python cli.py verify-audit
    python cli.py calendar alpha|all [--as-of D]   # engine only, no database
    python cli.py fee AOC4 theta 2024-10-30 2026-09-10 --period FY2023-24
    python cli.py rulepack
"""
from __future__ import annotations

import argparse
import secrets
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))   # works from any working directory

import demo_data  # noqa: E402
import engine  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # ₹ on the Windows console


# ================================================================ database
def migrate(url: str | None = None) -> None:
    from alembic import command
    from alembic.config import Config as AlembicConfig
    cfg = AlembicConfig(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    if url:
        cfg.attributes["url"] = url
    command.upgrade(cfg, "head")


def cmd_init_db(args) -> None:
    from app.config import Config, ENV_FILE, ensure_env_file
    if ensure_env_file():
        print(f"Created {ENV_FILE.name} with fresh SECRET_KEY and FERNET_KEY (keep it safe; never commit it).")
    url = Config().DATABASE_URL
    migrate(url)
    print(f"Database ready: {url}")


def _app(as_of: date | None = None):
    from app import create_app
    return create_app(SCHEDULER=False, **({"AS_OF": as_of} if as_of else {}))


def temp_password() -> str:
    from app.routes.admin import temp_password as tp
    return tp()


def cmd_create_owner(args) -> None:
    from app import audit
    from app.auth import hash_password, password_problems
    from app.models import User, db
    app = _app()
    with app.app_context():
        if db.session.query(User).filter_by(username=args.username.lower()).first():
            sys.exit(f"User {args.username} already exists.")
        pw = args.password or temp_password()
        if args.password and password_problems(pw, args.username):
            sys.exit("Password rejected: " + " ".join(password_problems(pw, args.username)))
        u = User(username=args.username.lower(), full_name=args.name, role="OWNER",
                 password_hash=hash_password(pw), must_change_password=True)
        db.session.add(u)
        db.session.flush()
        audit.record(db.session, audit.SYSTEM, "USER_CREATED", "user", u.id, after={"username": u.username,
                                                                                     "role": "OWNER", "via": "cli"})
        db.session.commit()
        print(f"Owner '{u.username}' created. Temporary password (shown once): {pw}")


def cmd_recompute(args) -> None:
    from app.models import db
    from app.services import recompute_all
    as_of = args.as_of or None
    app = _app(as_of)
    with app.app_context():
        from app.auth import today
        stats = recompute_all(today())
        print(f"Recomputed {stats['entities']} entities: {stats['inserted']} new, {stats['updated']} updated, "
              f"{stats['superseded']} superseded, {stats['restored']} restored.")


def cmd_nightly(args) -> None:
    """Same work as the in-process 01:00 job — for cron / Windows Task Scheduler."""
    from app.exports import nightly
    app = _app(args.as_of or None)
    with app.app_context():
        from app.auth import today
        print("Nightly run:", nightly(today(), catch_up=args.catch_up))


def cmd_package(args) -> None:
    """Build a clean copy of the project for the ICAI GitHub upload and check it (brief §15)."""
    import re
    import shutil
    dest_root = Path(args.dest).expanduser() if args.dest else Path.home() / "Desktop" / "AICA-Submission-Kit" / "upload"
    dest = dest_root / ROOT.name
    if dest.exists():
        shutil.rmtree(dest)
    skip_dirs = {".venv", "venv", "instance", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode", "htmlcov"}
    skip_files = {".env", ".coverage"}
    skip_ext = {".db", ".sqlite", ".sqlite3", ".pyc", ".log"}
    copied = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in skip_dirs for part in rel.parts) or not path.is_file():
            continue
        if path.name in skip_files or path.suffix.lower() in skip_ext:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(rel)
    problems = []
    if len(copied) >= 100:
        problems.append(f"{len(copied)} files — ICAI's web upload accepts fewer than 100 per upload")
    big = [str(r) for r in copied if (dest / r).stat().st_size > 25 * 1024 * 1024]
    if big:
        problems.append(f"files over 25 MB: {big}")
    if not (dest / "README.md").exists():
        problems.append("README.md is missing (required by the ICAI guide)")
    secret = re.compile(r"^(SECRET_KEY|FERNET_KEY)=\S{20,}", re.M)
    for r in copied:
        if (dest / r).suffix in {".py", ".md", ".txt", ".yaml", ".example", ".ini", ".bat", ".html", ".css"}:
            text = (dest / r).read_text(encoding="utf-8", errors="ignore")
            if secret.search(text) and r.name != ".env.example":
                problems.append(f"possible secret key in {r}")
    onetime = (dest / "rulepack" / "companies_onetime.yaml").read_text(encoding="utf-8")
    if "offset: {days: 180}" not in onetime:
        problems.append("rulepack/companies_onetime.yaml: INC20A is not 180 days — revert any demo edit first")
    print(f"Clean copy: {dest}")
    print(f"Files: {len(copied)}  (excluded: .venv, instance/ with your database and uploads, .env, caches)")
    if problems:
        print("\nFIX BEFORE UPLOADING:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("Checks passed: under 100 files, no .env / database / virtualenv / caches, README present, rule pack unedited.")
    print("\nNext: open your GitHub fork -> Add file -> Upload files -> drag THIS folder:\n  " + str(dest))

def sqlite_path(url: str) -> Path:
    if not url.startswith("sqlite:///"):
        sys.exit("backup/restore via this CLI supports SQLite only; use pg_dump / pg_restore for PostgreSQL.")
    return Path(url[len("sqlite:///"):])


def backup_sqlite(db_file: Path, dest_dir: Path) -> Path:
    """Online backup with SQLite's backup API: safe while the server is running."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"mca-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(2)}.db"
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(dest)
    try:
        with dst:
            src.backup(dst)
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
        triggers = {r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    finally:
        src.close()
        dst.close()
    if ok != "ok" or not {"audit_log_no_update", "audit_log_no_delete"} <= triggers:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Backup verification failed (integrity={ok}, triggers={sorted(triggers)})")
    return dest


def cmd_backup(args) -> None:
    from app.config import Config
    cfg = Config()
    dest = backup_sqlite(sqlite_path(cfg.DATABASE_URL), cfg.BACKUP_DIR)
    print(f"Backup written and verified (integrity ok, audit triggers present): {dest}")


def cmd_restore(args) -> None:
    from app.config import Config
    cfg = Config()
    target = sqlite_path(cfg.DATABASE_URL)
    src_file = Path(args.file)
    if not src_file.is_absolute():
        src_file = ROOT / src_file
    if not src_file.is_file():
        sys.exit(f"No such backup: {src_file}")
    if not args.yes:
        sys.exit("Restoring replaces the live database. Stop the server first, then re-run with --yes.")
    safety = backup_sqlite(target, cfg.BACKUP_DIR) if target.exists() else None
    src, dst = sqlite3.connect(src_file), sqlite3.connect(target)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()
    print(f"Restored {src_file.name}." + (f" The previous database was saved as {safety.name}." if safety else ""))


def cmd_verify_audit(args) -> None:
    from app.audit import verify_chain
    from app.models import db
    app = _app()
    with app.app_context():
        rep = verify_chain(db.session)
        print(rep.message)
        if not rep.ok:
            sys.exit(1)


# ================================================================== seed
def seed_demo(password: str | None = None, as_of: date | None = None, quiet: bool = False, app=None) -> dict[str, str]:
    """Create the fictitious demo firm. Returns {username: password}."""
    from app import audit
    from app.auth import encrypt, hash_password
    from app.models import (AnnualFacts, Entity, EntityPerson, Event, Filing, Obligation, PeriodFlag, Person,
                            User, db)
    from app.services import FACT_FIELDS, fee_for, sync_entity

    app = app or _app(as_of)
    creds: dict[str, str] = {}
    with app.app_context():
        from app.auth import today
        t = today()
        if db.session.query(Entity).count() or db.session.query(User).count():
            raise SystemExit("The database already has users or entities; seed-demo only runs on an empty database.")
        s = db.session
        users = {}
        for uname, full, role in [("owner", "Owner Demo", "OWNER"), ("partner", "Partner Demo", "PARTNER"),
                                  ("manager", "Manager Demo", "MANAGER"), ("article1", "Article Assistant One", "PREPARER"),
                                  ("viewer", "Viewer Demo", "VIEWER")]:
            pw = password or temp_password()
            creds[uname] = pw
            u = User(username=uname, full_name=full, role=role, password_hash=hash_password(pw), must_change_password=True)
            s.add(u)
            users[uname] = u
        s.flush()
        audit.record(s, audit.SYSTEM, "SEED_DEMO", "user", None, after={"users": list(creds)})
        from app.models import RegulatoryUpdate
        for number, issued, url, summary, links in [
            ("G.S.R. 943(E)", date(2025, 12, 31), "https://taxguru.in/company-law/mca-notifies-significant-amendment-director-kyc-framework-w-e-f31-03-2026.html",
             "Companies (Appointment and Qualification of Directors) Amendment Rules 2025: DIR-3 KYC once every three FYs, due 30 June; change filings within 30 days (w.e.f. 31-03-2026).",
             [("DIR3KYC_ANNUAL", "closed"), ("DIR3KYC_TRIENNIAL", "created"), ("DIR3KYC_CHANGE", "created")]),
            ("G.S.R. 880(E)", date(2025, 12, 1), "https://taxguru.in/company-law/small-company-definition-revised-capital-rs-10-cr-turnover-rs-100-cr-w-e-f-1-dec-2025.html",
             "Small company limits raised to paid-up ₹10 crore / turnover ₹100 crore (threshold row SMALL_COMPANY).", []),
            ("ROF Amendment Rules 2026", date(2026, 4, 21), "https://www.scconline.com/blog/post/2026/04/24/companies-registration-offices-fees-amendment-rules-2026-dir-3-kyc-fee-changes/",
             "DIR-3 KYC Web fee: nil on time, ₹5,000 late / reactivation, ₹500 per change filing (fee table FIXED_KYC).", []),
            ("General Circular 01/2026", date(2026, 2, 24), "https://x.com/MCA21India/status/2026661150923120877",
             "Companies Compliance Facilitation Scheme 2026: 10% of additional fee on annual filings and ADT-1; extended to 15-09-2026 by GC 03/2026 and GC 04/2026 (scheme CCFS_2026).", []),
            ("General Circular 02/2026", date(2026, 6, 19), "https://www.corplawupdates.in/updates/mca-dpt3-due-date-extended-31-july-2026",
             "DPT-3 for FY 2025-26 may be filed without additional fee up to 31-07-2026 (scheme EXT_DPT3_FY2526).", [])]:
            s.add(RegulatoryUpdate(number=number, issued_on=issued, url=url, summary=summary, created_by_id=users["owner"].id,
                                   linked_rules=[{"code": c, "relation": r} for c, r in links]))

        demo = demo_data.entities()
        pans = {"alpha": "AAECA1111A", "beta": "AAECB2222B", "gamma": "AAACG3333C", "delta": "AAACD4444D",
                "epsilon": "AAACE5555E", "zeta": "AAFFZ6666F", "eta": "AAFFE7777G", "theta": "AAACT8888H"}
        preparer = {"alpha": "article1", "beta": "article1", "theta": "article1", "zeta": "article1", "eta": "article1",
                    "gamma": "manager", "delta": "manager", "epsilon": "manager"}
        ents: dict[str, Entity] = {}
        for key, d in demo.items():
            ei = d["entity"]
            e = Entity(name=ei.name, entity_type=ei.entity_type, cin=d["cin"], pan_enc=encrypt(pans[key]),
                       incorporation_date=ei.incorporation_date, roc="RoC-Delhi",
                       registered_office="Fictitious address, New Delhi", nominal_capital=ei.nominal_capital,
                       paid_up_capital=ei.paid_up_capital, llp_contribution=ei.llp_contribution,
                       has_share_capital=ei.has_share_capital, single_director=ei.single_director,
                       llp_elect_longer_first_fy=ei.llp_elect_longer_first_fy, engagement_start=ei.engagement_start,
                       preparer_id=users[preparer[key]].id, rm_id=users["partner"].id,
                       notes="FICTITIOUS demo entity")
            s.add(e)
            s.flush()
            ents[key] = e
            for fy_key, f in d["facts"].items():
                s.add(AnnualFacts(entity_id=e.id, fy_key=fy_key, **{k: getattr(f, k) for k in FACT_FIELDS}))
            for period, flags in d["flags"].items():
                for name, value in flags.items():
                    s.add(PeriodFlag(entity_id=e.id, period_key=period, name=name, value=value))
            for ev in d["events"]:
                s.add(Event(entity_id=e.id, type=ev.type, event_date=ev.date, attrs=ev.attrs,
                            reference="Demo record", created_by_id=users["manager"].id))
        s.flush()

        people = [  # (din, name, allotted, last annual KYC FY, dsc expiry, [(entity, designation)])
            ("10000101", "Ravi Demo-Kumar", date(2026, 1, 15), None, date(2027, 1, 10), [("alpha", "Director")]),
            ("10000102", "Meera Sample", date(2026, 1, 15), None, date(2027, 1, 10), [("alpha", "Director")]),
            ("10000201", "Kiran Example", date(2019, 7, 1), "FY2024-25", date(2027, 5, 1), [("beta", "Director")]),
            ("10000301", "Anil Placeholder", date(2014, 5, 2), "FY2024-25", date(2026, 12, 31),
             [("gamma", "Managing Director"), ("delta", "Director"), ("epsilon", "Director")]),
            ("10000302", "Sunita Fictional", date(2016, 8, 1), "FY2024-25", t + timedelta(days=15), [("delta", "Director")]),
            ("10000601", "Zubin Testcase", date(2021, 5, 20), "FY2024-25", date(2027, 3, 3), [("zeta", "Designated Partner")]),
            ("10000701", "Esha Mockup", date(2025, 11, 1), None, date(2027, 11, 1), [("eta", "Designated Partner")]),
            ("10000801", "Tarun Dummy", date(2018, 4, 1), "FY2024-25", date(2026, 11, 20), [("theta", "Director")]),
        ]
        persons = {}
        for din, name, allot, last_kyc, dsc, links in people:
            p = Person(name=name, din=din, din_allotment_date=allot, last_annual_kyc_fy=last_kyc, dsc_expiry=dsc,
                       email=f"{din}@example.invalid", mobile="9000000000")
            s.add(p)
            s.flush()
            persons[din] = p
            for ent, desig in links:
                s.add(EntityPerson(entity_id=ents[ent].id, person_id=p.id, designation=desig,
                                   appointed_on=max(allot, ents[ent].incorporation_date)))
        s.add(Event(person_id=persons["10000101"].id, type="DIRECTOR_DETAIL_CHANGE", event_date=date(2026, 8, 5),
                    attrs={"changed": "mobile"}, reference="Demo record", created_by_id=users["manager"].id))
        s.flush()

        for e in ents.values():
            sync_entity(e, t)
        s.flush()

        # --- realistic history: past items filed, a few left pending on purpose
        partner = users["partner"]
        keep_pending = {f"{ents['delta'].id}:MGT7:FY2024-25", f"{ents['delta'].id}:DEMAT_9B:FY2022-23",   # partner decisions
                        f"{ents['theta'].id}:AOC4:FY2023-24", f"{ents['theta'].id}:MGT7:FY2023-24",
                        f"{ents['theta'].id}:AOC4:FY2024-25", f"{ents['theta'].id}:MGT7:FY2024-25",
                        f"{ents['theta'].id}:AGM:FY2023-24", f"{ents['theta'].id}:AGM:FY2024-25"}
        special = {f"{ents['alpha'].id}:INC20A:ONCE": date(2026, 7, 10),
                   f"{ents['alpha'].id}:DPT3:FY2025-26": date(2026, 7, 15),        # GC 02/2026 overlay
                   f"{ents['zeta'].id}:LLP_FORM11:FY2025-26": date(2026, 9, 20)}   # golden test 14
        n = 0
        for o in s.query(Obligation).all():
            if o.superseded_at or o.key in keep_pending:      # history incl. pre-engagement
                continue
            filed_on = special.get(o.key)
            if filed_on is None and o.due_date < t and o.person_id is None:
                filed_on = o.due_date
            if filed_on is None:
                continue
            fb = fee_for(o, filed_on)
            o.status, o.reviewer_id, o.ready_by_id = "FILED", partner.id, users["article1"].id
            n += 1
            s.add(Filing(obligation_id=o.id, srn=f"D{10000000 + o.id:08d}"[:9], filing_date=filed_on,
                         normal_fee_paid=fb.normal, additional_fee_paid=fb.additional - fb.scheme_relief,
                         delay_days=fb.delay_days, computed_fee_json={"total": fb.total, "explanation": fb.explanation,
                                                                      "verified": fb.verified},
                         fee_mismatch=False, created_by_id=partner.id))
        s.flush()
        for e in ents.values():            # re-judge history under the limits in force when it was filed
            sync_entity(e, t)
        # workflow examples
        beta_aoc4 = s.query(Obligation).filter_by(key=f"{ents['beta'].id}:AOC4_OPC:FY2025-26").one()
        beta_aoc4.status, beta_aoc4.ready_by_id = "READY_FOR_REVIEW", users["article1"].id
        kyc = s.query(Obligation).filter(Obligation.rule_code == "DIR3KYC_CHANGE").first()
        if kyc:
            kyc.status, kyc.assignee_id = "IN_PROGRESS", users["article1"].id
        audit.record(s, audit.SYSTEM, "SEED_DEMO", "obligation", None,
                     after={"filed_history": n, "note": "synthetic filing history for fictitious entities"})
        s.commit()
        if not quiet:
            print(f"Seeded {len(ents)} fictitious entities, {len(persons)} persons, {n} historical filings "
                  f"(as of {t:%d-%m-%Y}).")
    return creds


def cmd_seed_demo(args) -> None:
    if args.if_empty:
        from app.models import User, db
        app = _app()
        with app.app_context():
            if db.session.query(User).count():
                print("Users already exist — demo data not loaded.")
                return
        db.session.remove()
        db.engine.dispose()
    creds = seed_demo(args.password, args.as_of)
    print("\nDemo users (passwords shown ONCE — every user must change it at first sign-in):")
    for u, p in creds.items():
        print(f"  {u:<9} {p}")
    print("\nStart the app: double-click START_APP.bat (or: python run.py). The browser opens by itself.")


# ============================================================ engine only
def cmd_calendar(args) -> None:
    rp = engine.load()
    demo = demo_data.entities()
    names = list(demo) if args.entity == "all" else [args.entity]
    for n in names:
        if n not in demo:
            sys.exit(f"Unknown demo entity '{n}'. Choose from: {', '.join(demo)} or all")
        d = demo[n]
        print(f"\n== {d['entity'].name} ({d['entity'].entity_type}, incorporated "
              f"{d['entity'].incorporation_date:%d-%m-%Y}) — as of {args.as_of:%d-%m-%Y}")
        for s in engine.generate(d["entity"], d["facts"], d["events"], d["persons"], rp, args.as_of,
                                 period_flags=d["flags"]):
            if not args.history and s.due_date < date(args.as_of.year - 1, 4, 1):
                continue
            tags = [t for t, on in (("Provisional", s.provisional), ("Facts stale", s.facts_stale),
                                    ("Pre-engagement", s.pre_engagement), ("Interpretation", s.interpretation))
                    if on]
            if s.person_din:
                tags.insert(0, f"DIN {s.person_din}")
            if s.needs_decision:
                tags.append(f"Decision needed: {s.needs_decision}")
            status = "OVERDUE " if s.due_date < args.as_of else "        "
            print(f"  {s.due_date:%d-%m-%Y} {status}{s.form[:34]:<34} {s.period_key:<28} {', '.join(tags)}")


def cmd_fee(args) -> None:
    e = demo_data.entities()[args.entity]["entity"]
    f = engine.compute_fee(args.rule, e, args.due, args.filed, rulepack=engine.load(), period_key=args.period)
    print(f.explanation)


def cmd_rulepack(args) -> None:
    rp = engine.load()
    print(f"Rule pack version {rp.version} — {len(rp.rules)} rules, content hash {rp.content_hash[:12]}")
    print(f"Unverified rules: {sum(1 for r in rp.rules if not r.verified)} (a partner signs these off in the app)")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="cli.py", description="MCA Compliance Mapper — command-line tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create .env on first run and migrate the database")
    c = sub.add_parser("create-owner", help="create an Owner account")
    c.add_argument("--username", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--password")
    c = sub.add_parser("seed-demo", help="load the fictitious demo firm into an empty database")
    c.add_argument("--password", help="use this password for every demo user (still forced to change)")
    c.add_argument("--if-empty", action="store_true", help="do nothing if the database already has users")
    c.add_argument("--as-of", type=date.fromisoformat)
    c = sub.add_parser("recompute", help="regenerate obligations for all active entities")
    c.add_argument("--as-of", type=date.fromisoformat)
    c = sub.add_parser("nightly", help="recompute + reminders + e-mail digest (for Task Scheduler / cron)")
    c.add_argument("--as-of", type=date.fromisoformat)
    c.add_argument("--catch-up", action="store_true", help="send reminders for thresholds missed while offline")
    c = sub.add_parser("package", help="clean, checked copy of the project for the ICAI GitHub upload")
    c.add_argument("--dest", help="folder to create the copy in (default: Desktop\\AICA-Submission-Kit\\upload)")
    sub.add_parser("backup", help="online backup of the SQLite database")
    c = sub.add_parser("restore", help="restore a backup (server must be stopped)")
    c.add_argument("file")
    c.add_argument("--yes", action="store_true")
    sub.add_parser("verify-audit", help="recompute the audit hash chain")
    c = sub.add_parser("calendar", help="engine only: obligations for a demo entity")
    c.add_argument("entity")
    c.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    c.add_argument("--history", action="store_true")
    c = sub.add_parser("fee", help="engine only: fee if a form is filed on a date")
    for a in ("rule", "entity"):
        c.add_argument(a)
    c.add_argument("due", type=date.fromisoformat)
    c.add_argument("filed", type=date.fromisoformat)
    c.add_argument("--period")
    sub.add_parser("rulepack", help="validate and summarise the rule pack")
    args = p.parse_args(argv)
    try:
        engine.load()           # refuse to do anything on an invalid pack
    except engine.RulePackError as e:
        sys.exit(f"Rule pack is invalid — refusing to start:\n{e}")
    {"init-db": cmd_init_db, "create-owner": cmd_create_owner, "seed-demo": cmd_seed_demo,
         "recompute": cmd_recompute, "nightly": cmd_nightly, "package": cmd_package, "backup": cmd_backup, "restore": cmd_restore, "verify-audit": cmd_verify_audit,
     "calendar": cmd_calendar, "fee": cmd_fee, "rulepack": cmd_rulepack}[args.cmd](args)


if __name__ == "__main__":
    main()
