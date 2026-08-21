"""First-run setup for a packaged installation.

A colleague who opens the .exe has no database, no schema and no firm record.
This creates all three, once, and is safe to call on every start.

**It does not create demo data.** `scripts/seed.py` makes a sample client with
invented figures, which is right for development and wrong here: a tool for real
audits must not open with a fictional company in the client register, where it
could be mistaken for a real file or rolled forward by accident.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, select

from alembic import command
from app.config import PROJECT_ROOT, get_settings
from app.db import SessionLocal, engine
from app.models.masters import Firm

logger = logging.getLogger("auditcraft")

# What a firm sees before it has entered its own details. Deliberately obvious
# placeholders rather than something plausible: a letterhead reading
# "Your Firm Name" is unmistakably unset, and one reading "ABC & Co" is not.
PLACEHOLDER_FIRM_NAME = "Your Firm Name"
PLACEHOLDER_FRN = "000000W"

# A new installation starts with the ICAI Chartered Accountant mark, which the
# firm's team asked for. Changeable at Admin -> Firm & Partners, including to
# "No logo": the mark is ICAI's and its use is governed by ICAI's guidelines
# for members, so a firm must be able to decide otherwise.
DEFAULT_LOGO_PATH = "/static/Firm_logo.png"


def _alembic_config() -> Config:
    """Alembic pointed at the bundled migration scripts.

    `script_location` is set explicitly because `alembic.ini` records a relative
    path, and the working directory of a double-clicked .exe is wherever the
    user happened to be -- often not the application at all.
    """
    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", str(engine.url))
    return config


def ensure_schema() -> None:
    """Bring the database up to the current migration head.

    On a new installation this runs the whole chain from empty, which is the
    same path the development database took -- rather than
    `Base.metadata.create_all`, which would produce an unversioned database that
    the next release could not migrate.
    """
    tables = inspect(engine).get_table_names()
    if "alembic_version" not in tables and tables:
        # Tables but no version row: a database created outside alembic. Left
        # alone rather than stamped, because guessing which revision it matches
        # is how a migration silently skips a column.
        logger.warning("database has tables but no alembic version; leaving it alone")
        return
    command.upgrade(_alembic_config(), "head")


def ensure_firm() -> None:
    """One firm record, so every screen has something to render.

    Without it the dashboard, the master answer sheet and the letterhead all
    have nothing to read, and two of them return 404. The details are
    placeholders the user replaces at Admin -> Firm & Partners.
    """
    with SessionLocal() as session:
        if session.scalar(select(Firm)) is not None:
            return
        session.add(
            Firm(
                firm_name=PLACEHOLDER_FIRM_NAME,
                frn=PLACEHOLDER_FRN,
                logo_path=DEFAULT_LOGO_PATH,
            )
        )
        session.commit()
        logger.info("created the placeholder firm record")


# The field catalogue is synced by the application's own startup
# (`app.main._sync_catalogue`), so it happens however the application is
# launched — from source with `run.py`, from the packaged .exe, or under a test
# client. Doing it here as well would be a second place for it to drift.


def first_run(data_dir: Path | None = None) -> None:
    """Everything a fresh installation needs, in order."""
    settings = get_settings()
    settings.ensure_directories()
    (data_dir or settings.data_path).mkdir(parents=True, exist_ok=True)
    ensure_schema()
    ensure_firm()
