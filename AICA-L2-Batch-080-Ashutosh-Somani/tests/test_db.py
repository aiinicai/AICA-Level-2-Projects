from app.database.migrations import init_db
from app.database.db import get_db_connection

def test_db_initialization_idempotency(temp_config):
    # First init
    init_db(temp_config)
    
    # Verify tables created
    with get_db_connection(temp_config) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        assert 'schema_version' in tables
        # Check first init
        with get_db_connection(temp_config) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            version = cursor.fetchone()[0]
            assert version == 9
            
        # Run again
        init_db(temp_config)
        with get_db_connection(temp_config) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            version = cursor.fetchone()[0]
            assert version == 9
