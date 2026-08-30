"""
Shared infrastructure singletons.

Stage 2 scope: only the SQLAlchemy engine/session plumbing needed so the
rest of the app has a stable import target. No models are defined or
imported here yet — that is Stage 3 ("SQLite database") per the approved
roadmap. Deliberately using plain SQLAlchemy 2.x (engine + sessionmaker),
NOT Flask-SQLAlchemy, because the approved package list (Blueprint
Section L) specifies SQLAlchemy directly and Flask-SQLAlchemy was never
approved as a dependency.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker

engine = None
SessionLocal = None


def init_engine(db_uri: str):
    """Create the module-level engine/session factory. Called once from
    the app factory at startup. Idempotent-safe for the test suite,
    which calls create_app() repeatedly with an in-memory DB."""
    global engine, SessionLocal
    engine = create_engine(db_uri, future=True)

    if db_uri.startswith("sqlite"):
        # Stage 15 section 17: SQLite does not enforce declared FOREIGN
        # KEY constraints unless a connection explicitly turns it on —
        # every model in app/models/ already declares ForeignKey columns
        # and relationship cascades (Blueprint schema, Stage 3+), but
        # without this pragma SQLite would silently accept an orphaned
        # row if anything ever wrote outside the ORM's own cascade-aware
        # `.delete()` calls. Purely a per-connection runtime setting —
        # no schema, model, or migration change. Safe to enable: every
        # current delete in the codebase (accounting/audit/tax review
        # re-run cleanup, mapping re-confirm) already goes through
        # SQLAlchemy relationship cascades in the correct
        # child-before-parent order, confirmed during the Stage 15
        # security review. `@event.listens_for` (decorator form, not
        # `event.listen(...)`) deliberately — the sandbox's ORM
        # verification shim only provides the decorator form; using it
        # keeps this engine setup verifiable in-sandbox without changing
        # behavior against real SQLAlchemy, which supports both forms
        # identically.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))
    return engine
