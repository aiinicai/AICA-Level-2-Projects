from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_sqlite_patches(engine: Engine) -> None:
    statements = (
        "ALTER TABLE ocr_audit_logs ADD COLUMN extraction_trace JSON",
        "ALTER TABLE users ADD COLUMN permissions JSON",
        "ALTER TABLE employees ADD COLUMN monthly_salary FLOAT",
    )
    with engine.connect() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass
