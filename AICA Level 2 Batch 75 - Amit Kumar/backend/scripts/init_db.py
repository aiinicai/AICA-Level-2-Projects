#!/usr/bin/env python
"""
PostgreSQL Database Initialization Script for FS Builder Lite v0.2
Creates all tables, schema constraints, and indexes in PostgreSQL.
"""
import os
import sys

# Add parent directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal, check_db_health
import models
from services.mapping_engine import init_default_rules

def init_postgresql():
    print("=" * 60)
    print("      FS BUILDER LITE - POSTGRESQL DATABASE INITIALIZATION     ")
    print("=" * 60)
    
    print(f"Target Database URL: {engine.url.render_as_string(hide_password=True)}")
    
    # Check DB Connection
    health = check_db_health()
    if health.get("status") != "healthy":
        print(f"\n[ERROR] Cannot connect to PostgreSQL: {health.get('error')}")
        print("Please check your DATABASE_URL environment variable and ensure PostgreSQL server is running.")
        sys.exit(1)
        
    print("\n[1/3] Database Connection Verified Successfully.")
    
    # Create all tables and indexes
    print("[2/3] Creating tables and indexes...")
    models.Base.metadata.create_all(bind=engine)
    print("      Tables and indexes created successfully.")
    
    # Initialize default mapping rules
    print("[3/3] Seeding default Schedule III mapping rules...")
    db = SessionLocal()
    try:
        init_default_rules(db)
        print("      Default mapping rules seeded successfully.")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print(" SUCCESS: PostgreSQL Database Initialized Successfully! ")
    print("=" * 60)

if __name__ == "__main__":
    init_postgresql()
