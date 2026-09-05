#!/usr/bin/env python
"""
Database Backup Script for FS Builder Lite v0.2 (PostgreSQL)
Supports native pg_dump as well as pure Python JSON/SQL dump fallback.
"""
import os
import sys
import json
import datetime
import subprocess
from sqlalchemy import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal, DATABASE_URL
import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 60)
    print("      FS BUILDER LITE - POSTGRESQL DATABASE BACKUP UTILITY    ")
    print("=" * 60)
    print(f"Timestamp: {timestamp}")

    # Attempt 1: Native pg_dump tool
    url_parts = engine.url
    sql_backup_path = os.path.join(BACKUP_DIR, f"pg_backup_{timestamp}.sql")
    json_backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")

    pg_dump_success = False
    try:
        env = os.environ.copy()
        if url_parts.password:
            env["PGPASSWORD"] = url_parts.password

        cmd = [
            "pg_dump",
            "-h", url_parts.host or "localhost",
            "-p", str(url_parts.port or 5432),
            "-U", url_parts.username or "postgres",
            "-d", url_parts.database,
            "-F", "p",  # plain text SQL
            "-f", sql_backup_path
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            pg_dump_success = True
            print(f"[SUCCESS] Native pg_dump created successfully: {sql_backup_path}")
        else:
            print(f"[INFO] pg_dump CLI not available or returned error: {result.stderr.strip()}")
    except Exception as e:
        print(f"[INFO] pg_dump attempt skipped: {e}")

    # Backup via Python Object Serialization (Universal Fallback)
    print("[INFO] Generating universal JSON database dump...")
    db = SessionLocal()
    backup_payload = {
        "metadata": {
            "timestamp": timestamp,
            "database_type": "PostgreSQL",
            "version": "0.2.0",
            "database_name": url_parts.database
        },
        "data": {}
    }

    model_classes = [
        models.Client,
        models.User,
        models.Engagement,
        models.AuditLog,
        models.UploadedFile,
        models.GeneratedReport,
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

    total_records = 0
    try:
        for model in model_classes:
            table_name = model.__tablename__
            rows = db.query(model).all()
            table_records = []
            for row in rows:
                row_data = {}
                for col in inspect(row).mapper.column_attrs:
                    val = getattr(row, col.name)
                    if isinstance(val, (datetime.datetime, datetime.date)):
                        val = val.isoformat()
                    row_data[col.name] = val
                table_records.append(row_data)
            
            backup_payload["data"][table_name] = table_records
            total_records += len(table_records)

        with open(json_backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, indent=2)

        print(f"[SUCCESS] Universal JSON Backup created: {json_backup_path} ({total_records} records)")
        
        print("\n" + "=" * 60)
        print(" BACKUP COMPLETE ")
        print("=" * 60)
        return json_backup_path
    except Exception as e:
        print(f"\n[ERROR] Backup failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_backup()
