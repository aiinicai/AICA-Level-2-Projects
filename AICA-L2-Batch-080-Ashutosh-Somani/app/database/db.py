import sqlite3
from contextlib import contextmanager
from pathlib import Path
import configparser

@contextmanager
def get_db_connection(config: configparser.ConfigParser):
    """
    Context manager for SQLite database connection.
    Yields a connection, commits if no exception, rollbacks on exception.
    """
    db_path = config.get('paths', 'database', fallback='database/bank_statement_converter.db')
    project_root = Path(__file__).resolve().parent.parent.parent
    full_path = project_root / db_path
    
    conn = sqlite3.connect(full_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
