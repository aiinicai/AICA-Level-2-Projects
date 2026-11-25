"""Initialise the local database and seed the legal-reference registry."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from noticemate.core.config import get_settings  # noqa: E402
from noticemate.core.db import init_db  # noqa: E402
from noticemate.services.taxlaw import seed_registry  # noqa: E402

if __name__ == "__main__":
    res = init_db()
    n = seed_registry()
    if res and res.get("from") != res.get("to"):
        print(f"Database migrated from schema v{res['from']} to v{res['to']}.")
        if res.get("backup"):
            print(f"Pre-migration backup: {res['backup']}")
    print(f"Database ready at {get_settings().db_path} (schema v{res.get('to') if res else '?'}); "
          f"{n} new legal-registry seed entries (all REQUIRES_VERIFICATION).")
