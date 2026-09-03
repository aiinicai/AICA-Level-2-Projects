import sqlite3
import logging
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

def init_db(config):
    """
    Initializes the SQLite database schema if it doesn't exist,
    and applies any necessary migrations linearly.
    """
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            
            # Create schema_version table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create processing_jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_jobs (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    display_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress_message TEXT
                )
            ''')
            
            # Check current version
            cursor.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row and row[0] is not None else 0
            
            if current_version == 0:
                logger.info("Applying initial schema migration (v1).")
                cursor.execute("INSERT INTO schema_version (version) VALUES (1)")
                current_version = 1
                
            if current_version == 1:
                logger.info("Applying schema migration (v2).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN source_filename TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN stored_filename TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN file_size INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN sha256 TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN page_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN pdf_type TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN encrypted BOOLEAN")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN error_code TEXT")
                cursor.execute("INSERT INTO schema_version (version) VALUES (2)")
                current_version = 2
                
            if current_version == 2:
                logger.info("Applying schema migration (v3).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN extractor_used TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN extraction_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN pages_processed INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN total_words INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN total_characters INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN table_candidate_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN extraction_started_at TIMESTAMP")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN extraction_completed_at TIMESTAMP")
                cursor.execute("INSERT INTO schema_version (version) VALUES (3)")
                current_version = 3
                
            if current_version == 3:
                logger.info("Applying schema migration (v4).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN bank_detected TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN bank_detection_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN normalization_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN transaction_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN normalization_warning_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN normalization_started_at TIMESTAMP")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN normalization_completed_at TIMESTAMP")
                cursor.execute("INSERT INTO schema_version (version) VALUES (4)")
                current_version = 4
                
            if current_version == 4:
                logger.info("Applying schema migration (v5).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN validation_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN validated_transaction_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN balance_mismatch_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN exception_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN statement_difference TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN validation_started_at TIMESTAMP")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN validation_completed_at TIMESTAMP")
                cursor.execute("INSERT INTO schema_version (version) VALUES (5)")
                current_version = 5

            if current_version == 5:
                logger.info("Applying schema migration (v6).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN profile_id TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN profile_revision INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN profile_match_score INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN profile_application_status TEXT")
                
                # Bank Profiles Index Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bank_profiles (
                        profile_id TEXT PRIMARY KEY,
                        profile_name TEXT NOT NULL,
                        bank_name TEXT NOT NULL,
                        profile_revision INTEGER NOT NULL,
                        active BOOLEAN DEFAULT 1,
                        last_used_at TIMESTAMP,
                        use_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute("INSERT INTO schema_version (version) VALUES (6)")
                current_version = 6
                
            if current_version == 6:
                logger.info("Applying schema migration (v7).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN review_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN review_revision INTEGER DEFAULT 1")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN correction_count INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN review_exception_count INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN last_reviewed_at TIMESTAMP")
                cursor.execute("INSERT INTO schema_version (version) VALUES (7)")
                current_version = 7
                
            if current_version == 7:
                logger.info("Applying schema migration (v8).")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS export_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        filename TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        review_revision INTEGER,
                        validation_status TEXT,
                        application_version TEXT
                    )
                ''')
                cursor.execute("INSERT INTO schema_version (version) VALUES (8)")
                current_version = 8

            if current_version == 8:
                logger.info("Applying schema migration (v9).")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_status TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_engine TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_engine_version TEXT")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_pages_requested INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_pages_completed INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_low_confidence_count INTEGER")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_started_at TIMESTAMP")
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN ocr_completed_at TIMESTAMP")
                cursor.execute("INSERT INTO schema_version (version) VALUES (9)")
                current_version = 9

            conn.commit()
        logger.info(f"Database schema version is {current_version}.")
    except sqlite3.Error as e:
        logger.error(f"Database migration failed: {e}")
        raise
