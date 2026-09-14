#!/usr/bin/env python
"""
Database Restore Script for FS Builder Lite v0.2 (PostgreSQL)
Restores PostgreSQL database from a native SQL or universal JSON backup file.
"""
import os
import sys
import json
import datetime
import subprocess
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def find_latest_backup():
    if not os.path.exists(BACKUP_DIR):
        return None
    files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(('.json', '.sql'))]
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def restore_database(backup_file_path: str = None):
    print("=" * 60)
    print("      FS BUILDER LITE - POSTGRESQL DATABASE RESTORE UTILITY   ")
    print("=" * 60)

    if not backup_file_path:
        backup_file_path = find_latest_backup()

    if not backup_file_path or not os.path.exists(backup_file_path):
        print("[ERROR] No backup file specified or found in backups directory.")
        sys.exit(1)

    print(f"Restore File: {backup_file_path}")
    print(f"Target DB: {engine.url.render_as_string(hide_password=True)}")

    # Case 1: .sql file with psql
    if backup_file_path.endswith(".sql"):
        url_parts = engine.url
        env = os.environ.copy()
        if url_parts.password:
            env["PGPASSWORD"] = url_parts.password

        cmd = [
            "psql",
            "-h", url_parts.host or "localhost",
            "-p", str(url_parts.port or 5432),
            "-U", url_parts.username or "postgres",
            "-d", url_parts.database,
            "-f", backup_file_path
        ]
        try:
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode == 0:
                print("[SUCCESS] Native SQL restore completed successfully via psql.")
                return
            else:
                print(f"[ERROR] psql restore failed: {res.stderr}")
        except Exception as e:
            print(f"[ERROR] Could not execute psql tool: {e}")

    # Case 2: Universal JSON restore
    elif backup_file_path.endswith(".json"):
        with open(backup_file_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        data = backup_data.get("data", {})
        meta = backup_data.get("metadata", {})
        print(f"[INFO] Backup Created At: {meta.get('timestamp')}")

        # Ensure schema exists
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        model_map = {
            "clients": models.Client,
            "users": models.User,
            "engagements": models.Engagement,
            "audit_logs": models.AuditLog,
            "uploaded_files": models.UploadedFile,
            "generated_reports": models.GeneratedReport,
            "trial_balance_lines": models.TrialBalanceLine,
            "mapping_rules": models.MappingRule,
            "ar_ageing": models.ARAgeing,
            "ap_ageing": models.APAgeing,
            "cwip_ageing": models.CWIPAgeing,
            "related_parties": models.RelatedParty,
            "borrowings": models.Borrowing,
            "contingencies": models.Contingency,
            "notes": models.Note,
            "accounting_policies": models.AccountingPolicy,
            "cash_flow_adjustments": models.CashFlowAdjustment
        }

        total_restored = 0
        try:
            for table_name, model_cls in model_map.items():
                records = data.get(table_name, [])
                if not records:
                    continue

                print(f"  • Restoring '{table_name}': {len(records)} records...", end="")
                for rec in records:
                    # Convert ISO date strings back to datetime objects if needed
                    for k, v in rec.items():
                        if isinstance(v, str) and len(v) >= 19 and ("T" in v or "-" in v and ":" in v):
                            try:
                                rec[k] = datetime.datetime.fromisoformat(v)
                            except ValueError:
                                pass
                    
                    existing = db.query(model_cls).filter(model_cls.id == rec.get("id")).first() if "id" in rec else None
                    if not existing:
                        obj = model_cls(**rec)
                        db.add(obj)
                db.commit()
                total_restored += len(records)
                print(" DONE!")

            print("\n" + "=" * 60)
            print(f" SUCCESS: Restored {total_restored} total records to PostgreSQL!")
            print("=" * 60)
        except Exception as e:
            db.rollback()
            print(f"\n[ERROR] JSON Restore failed: {e}")
            sys.exit(1)
        finally:
            db.close()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    restore_database(target)
