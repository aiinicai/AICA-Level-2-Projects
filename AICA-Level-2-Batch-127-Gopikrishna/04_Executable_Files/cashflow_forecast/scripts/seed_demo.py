"""Load the synthetic day-1 data into an EMPTY instance and create three demo users.

    $env:CFF_INSTANCE_DIR = "$env:TEMP\\cff_demo"     # keep demos away from your real database
    python scripts/seed_demo.py

Random passwords are generated and written to <instance>/demo_users.txt (the instance folder is
git-ignored). Each demo user must choose a new password at first sign-in. Synthetic data only.
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import get_engine, session_scope  # noqa: E402
from app.importers import exceptions as X  # noqa: E402
from app.importers.pipeline import import_file, open_exceptions  # noqa: E402
from app.models import Category, LineItem, User  # noqa: E402
from app.services.auth import create_user  # noqa: E402
from app.services.init_db import init_db  # noqa: E402

DAY1 = ROOT / "synthetic_data" / "day1_2026-11-24"
FILES = [("category_list", "category_list.xlsx"), ("bank_balances", "bank_balances.csv"),
         ("bank_facility", "bank_facility.csv"), ("payment_history", "payment_history.xlsx"),
         ("collections", "erp_receivables.xlsx"), ("additional", "additional_collections.xlsx"),
         ("vendor_pdc", "erp_pdc_register.xlsx"), ("allocation", "erp_payment_plan.csv"),
         ("bill_discount", "bank_bd_lc.xlsx"), ("other", "other_recurring_long.xlsx"),
         ("other", "other_recurring_wide.xlsx")]


def main() -> None:
    s = get_settings()
    init_db(get_engine())
    with session_scope() as db:
        if db.scalar(select(func.count()).select_from(User)) or db.scalar(select(func.count()).select_from(LineItem)):
            raise SystemExit(f"{s.database_path} is not empty. Point CFF_INSTANCE_DIR at a new folder for the demo.")
        for src, name in FILES:
            rep = import_file(db, src, name, (DAY1 / name).read_bytes(), as_of=None)
            print(f"{name:<30} {rep.status}")
        for e in open_exceptions(db):
            if e.suggested_category_id:
                X.map_to_category(db, e.id, e.suggested_category_id)
            else:
                X.add_new_category(db, e.id, direction="outflow", summary_group="Overheads")
            print(f"exception '{e.raw_text}' resolved")
        lines = ["Demo users (synthetic data). Each must choose a new password at first sign-in.", ""]
        for user, role in (("demo.admin", "admin"), ("demo.preparer", "preparer"), ("demo.viewer", "viewer")):
            pw = "Demo-" + secrets.token_urlsafe(9)
            create_user(db, user, pw, role, full_name=f"Demo {role}", must_change_password=True)
            lines.append(f"{user:<15} {role:<9} {pw}")
        print(f"{db.scalar(select(func.count()).select_from(Category))} categories")
    out = s.instance_dir / "demo_users.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Demo users written to {out}")


if __name__ == "__main__":
    main()
