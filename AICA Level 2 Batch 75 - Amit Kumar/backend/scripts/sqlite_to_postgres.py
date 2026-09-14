#!/usr/bin/env python
"""
SQLite to PostgreSQL Data Migration Tool for FS Builder Lite v0.2
Migrates all existing records from legacy SQLite app.db to PostgreSQL.
"""
import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DATABASE_URL, engine as pg_engine, Base
import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "app.db")

def migrate_data():
    print("=" * 60)
    print("      SQLITE TO POSTGRESQL DATA MIGRATION UTILITY     ")
    print("=" * 60)

    if not os.path.exists(SQLITE_DB_PATH):
        print(f"[INFO] Legacy SQLite database not found at {SQLITE_DB_PATH}.")
        print("Skipping data migration.")
        return

    print(f"Source SQLite DB: {SQLITE_DB_PATH}")
    print(f"Target PostgreSQL: {pg_engine.url.render_as_string(hide_password=True)}")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    sqlite_db = SqliteSession()
    pg_db = PgSession()

    try:
        # Create tables on Postgres
        models.Base.metadata.create_all(bind=pg_engine)

        model_classes = [
            models.Client,
            models.TrialBalanceLine,
            models.MappingRule,
            models.ARAgeing,
            models.APAgeing,
            models.CWIPAgeing,
            models.RelatedParty,
            models.Borrowing,
            models.Contingency,
            models.Note,
            models.AccountingPolicy,
            models.CashFlowAdjustment
        ]

        total_migrated = 0
        for model in model_classes:
            table_name = model.__tablename__
            rows = sqlite_db.query(model).all()
            if not rows:
                print(f"  • Table '{table_name}': 0 rows (Skipped)")
                continue

            print(f"  • Table '{table_name}': Migrating {len(rows)} rows...", end="")
            for row in rows:
                # Convert row attributes to dictionary, excluding SQLAlchemy state
                row_dict = {
                    col.name: getattr(row, col.name)
                    for col in inspect(row).mapper.column_attrs
                }
                # Check if already exists in target
                existing = pg_db.query(model).filter(model.id == row.id).first() if hasattr(model, 'id') else None
                if not existing:
                    new_obj = model(**row_dict)
                    pg_db.add(new_obj)
            
            pg_db.commit()
            total_migrated += len(rows)
            print(" DONE!")

        print("\n" + "=" * 60)
        print(f" SUCCESS: Migrated {total_migrated} total records to PostgreSQL!")
        print("=" * 60)

    except Exception as e:
        pg_db.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        sqlite_db.close()
        pg_db.close()

if __name__ == "__main__":
    migrate_data()
