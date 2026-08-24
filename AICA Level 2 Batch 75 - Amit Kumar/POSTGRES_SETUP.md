# FS Builder Lite v0.2 - PostgreSQL Migration & Setup Guide

This guide documents the enterprise PostgreSQL database architecture, connection pooling, migrations, backup/restore procedures, and health monitoring for **FS Builder Lite v0.2**.

---

## 1. Overview & Architecture

SQLite has been completely replaced with **PostgreSQL**. The database architecture includes:
- **Connection Pooling**: Managed via SQLAlchemy engine (`pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`).
- **Environment Configuration**: Controlled by the `DATABASE_URL` environment variable.
- **Index Optimization**: Explicit indexes on high-cardinality and frequently queried tables (`clients`, `engagements`, `users`, `audit_logs`, `notes`, `uploaded_files`, `generated_reports`).
- **Schema Management**: Database migration support via Alembic (`alembic upgrade head`).
- **Backup & Recovery**: Native `pg_dump`/`psql` scripts with universal JSON fallback.

---

## 2. Environment Configuration

Create or update `.env` in the `backend/` root directory:

```env
# PostgreSQL Connection URL format:
# postgresql://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL=postgresql://fsbuilder_user:password@localhost:5432/fsbuilder
```

---

## 3. PostgreSQL Server Setup

### Option A: Local PostgreSQL Installation (Windows / Linux / Mac)

Run the following SQL commands in `psql` or pgAdmin:

```sql
-- 1. Create Database User
CREATE USER fsbuilder_user WITH PASSWORD 'password';

-- 2. Create Database
CREATE DATABASE fsbuilder OWNER fsbuilder_user;

-- 3. Grant Permissions
GRANT ALL PRIVILEGES ON DATABASE fsbuilder TO fsbuilder_user;
```

### Option B: Docker Container

```bash
docker run --name fsbuilder-postgres \
  -e POSTGRES_USER=fsbuilder_user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=fsbuilder \
  -p 5432:5432 \
  -d postgres:16-alpine
```

---

## 4. Database Operations Scripts

All database tools are located in `backend/scripts/`:

| Script Name | Purpose | Usage Command |
|---|---|---|
| `scripts/init_db.py` | Initializes schema, creates tables, indexes & default rules | `python scripts/init_db.py` |
| `scripts/sqlite_to_postgres.py` | Migrates legacy SQLite `app.db` records to PostgreSQL | `python scripts/sqlite_to_postgres.py` |
| `scripts/backup_db.py` | Creates native SQL & universal JSON database backups | `python scripts/backup_db.py` |
| `scripts/restore_db.py` | Restores database from a SQL or JSON backup file | `python scripts/restore_db.py [path]` |

### Quick Start Workflow

```bash
# 1. Initialize PostgreSQL Schema & Default Rules
python scripts/init_db.py

# 2. (Optional) Migrate existing SQLite data into PostgreSQL
python scripts/sqlite_to_postgres.py

# 3. Perform Alembic Migration Check
alembic upgrade head

# 4. Create Database Backup
python scripts/backup_db.py

# 5. Restore Database Backup (if needed)
python scripts/restore_db.py backups/backup_20260813_223000.json
```

---

## 5. Database Health Check APIs

The API exposes endpoints to inspect database connection and connection pool metrics:

### `GET /api/health/db`

**Sample Response:**
```json
{
  "status": "healthy",
  "database": "PostgreSQL",
  "engine": "localhost:5432/fsbuilder",
  "pool_status": {
    "pool_size": 10,
    "checkedin": 10,
    "overflow": 0,
    "checkedout": 0
  }
}
```

### `GET /api/health`

**Sample Response:**
```json
{
  "status": "online",
  "app": "FS Builder Lite v0.2",
  "database": {
    "status": "healthy",
    "database": "PostgreSQL",
    "engine": "localhost:5432/fsbuilder",
    "pool_status": {
      "pool_size": 10,
      "checkedin": 10,
      "overflow": 0,
      "checkedout": 0
    }
  }
}
```

---

## 6. Table Indexes Reference

As required, explicit indexes have been created for optimal query performance:

| Table Name | Indexed Columns / Composite Indexes | Purpose |
|---|---|---|
| `clients` | `id`, `name`, `entity_type`, `created_at`, `(name, entity_type)` | Fast client lookups and filtering |
| `engagements` | `id`, `client_id`, `reporting_period`, `status`, `created_at`, `(client_id, reporting_period)` | Multi-period audit tracking |
| `users` | `id`, `username`, `email`, `role`, `is_active`, `(role, is_active)` | Authentication & RBAC performance |
| `audit_logs` | `id`, `user_id`, `client_id`, `action`, `timestamp`, `(client_id, action)` | Audit trail query acceleration |
| `notes` | `id`, `client_id`, `note_number`, `title`, `(client_id, note_number)` | Schedule III note fetching |
| `uploaded_files` | `id`, `client_id`, `file_type`, `uploaded_at`, `(client_id, file_type)` | File attachment lookups |
| `generated_reports` | `id`, `client_id`, `report_type`, `generated_at`, `(client_id, report_type)` | Report history tracking |
