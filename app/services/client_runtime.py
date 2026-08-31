import shutil
from pathlib import Path

from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import BASE_DIR
from app.core.database import Base, dispose_sqlite_engine, engine_for_sqlite
from app.core.schema import apply_sqlite_patches
from app.services.client_store import (
    add_client,
    client_db_path,
    client_uploads_path,
    is_testing,
    list_clients,
    migrate_legacy_client_storage,
)
from app.seed import apply_admin_login, apply_noida_login, seed_database


def prepare_client_database(client: dict, include_samples: bool = False, include_demo_branches: bool = False) -> Path:
    db_path = client_db_path(client)
    engine = engine_for_sqlite(db_path)
    Base.metadata.create_all(bind=engine)
    apply_sqlite_patches(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        seed_database(db=db, include_samples=include_samples, include_demo_branches=include_demo_branches)
        apply_admin_login(db)
        apply_noida_login(db)
    finally:
        db.close()
    return db_path


def reset_client_database(client: dict) -> Path:
    """Wipe a client's SQLite file and create empty books. Does not copy another client."""
    import gc
    import time

    db_path = client_db_path(client)
    dispose_sqlite_engine(db_path)
    extras = (db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm"))
    for attempt in range(8):
        gc.collect()
        try:
            for extra in extras:
                try:
                    extra.unlink()
                except FileNotFoundError:
                    pass
            if not db_path.exists():
                break
        except OSError:
            time.sleep(0.08 * (attempt + 1))
    if db_path.exists():
        return db_path
    return prepare_client_database(client, include_samples=False, include_demo_branches=False)


_BOOKS_TABLES = (
    "daily_sales",
    "cash_reconciliations",
    "card_qr_reconciliations",
    "settlement_batches",
    "import_batches",
    "bank_transactions",
    "attendance_marks",
    "branches",
)


def _books_fingerprint(db_path: Path):
    import sqlite3

    connection = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        counts = []
        for table in _BOOKS_TABLES:
            try:
                counts.append(int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]))
            except Exception:
                counts.append(None)
        return tuple(counts)
    finally:
        connection.close()


def isolate_cloned_client_databases() -> None:
    """If a later client was given a copy of earlier books, start it empty."""
    from app.core.database import dispose_all_sqlite_engines

    dispose_all_sqlite_engines()
    seen = []
    for client in list_clients():
        db_path = client_db_path(client)
        if not db_path.exists():
            continue
        try:
            fingerprint = _books_fingerprint(db_path)
        except OSError:
            continue
        has_books = any(count and count > 0 for count in fingerprint)
        if has_books and fingerprint in seen:
            reset_client_database(client)
            continue
        seen.append(fingerprint)


def bootstrap_clients() -> None:
    if is_testing():
        return
    migrate_legacy_client_storage()
    if list_clients():
        for client in list_clients():
            if not client_db_path(client).exists():
                prepare_client_database(client, include_samples=False, include_demo_branches=False)
        isolate_cloned_client_databases()
        return

    client = add_client("Default Client", slug="default")
    dest = client_db_path(client)
    legacy = BASE_DIR / "data" / "restaurant_reconcile.db"
    copied = False
    if legacy.exists() and legacy.resolve() != dest.resolve():
        shutil.copy2(legacy, dest)
        copied = True
        legacy_uploads = BASE_DIR / "uploads"
        if legacy_uploads.exists():
            shutil.copytree(legacy_uploads, client_uploads_path(client), dirs_exist_ok=True)
    prepare_client_database(
        client,
        include_samples=not copied,
        include_demo_branches=not copied,
    )
