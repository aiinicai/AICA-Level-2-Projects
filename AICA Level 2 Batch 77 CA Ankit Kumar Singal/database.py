"""
database.py — SQLAlchemy models + DB initialisation + CRUD helpers
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, inspect, text
)
from sqlalchemy.orm import DeclarativeBase, Session
import pandas as pd
from utils import parse_date, format_date

DB_PATH = "gst_notices.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Base(DeclarativeBase):
    pass


class Notice(Base):
    __tablename__ = "notices"

    id                        = Column(Integer, primary_key=True, autoincrement=True)
    client_name               = Column(String(255))
    gstin                     = Column(String(20))
    notice_number             = Column(String(255))
    notice_issue_date         = Column(String(20))   # stored as DD-MM-YYYY
    notice_section            = Column(String(255))
    act_type                  = Column(String(50))
    issuing_officer           = Column(String(255))
    officer_designation       = Column(String(255))
    due_date                  = Column(String(20))   # stored as DD-MM-YYYY
    notice_type               = Column(String(255))
    client_data_status        = Column(String(100), default="Pending")
    data_requested            = Column(Text)
    date_data_requested       = Column(String(20))
    date_data_received        = Column(String(20))
    assigned_team_member      = Column(String(255))
    response_filing_date      = Column(String(20))
    response_status           = Column(String(100), default="Pending")
    remarks                   = Column(Text)
    created_at                = Column(DateTime, default=datetime.utcnow)
    updated_at                = Column(DateTime, default=datetime.utcnow,
                                       onupdate=datetime.utcnow)


def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(ENGINE)


# ─────────────────────────────────────────────
# Read helpers
# ─────────────────────────────────────────────

def get_all_notices() -> pd.DataFrame:
    """Return all notices as a DataFrame."""
    with Session(ENGINE) as session:
        rows = session.query(Notice).order_by(Notice.id.desc()).all()
        if not rows:
            return _empty_dataframe()
        return pd.DataFrame([_notice_to_dict(r) for r in rows])


def get_existing_keys() -> set:
    """Return a set of (gstin_upper, notice_number_upper) tuples already in DB."""
    with Session(ENGINE) as session:
        rows = session.query(Notice.gstin, Notice.notice_number).all()
        return {(str(r.gstin).upper().strip(), str(r.notice_number).upper().strip())
                for r in rows}


# ─────────────────────────────────────────────
# Write helpers
# ─────────────────────────────────────────────

def bulk_insert(records: list[dict]) -> int:
    """Insert a list of record dicts.  Returns count inserted."""
    if not records:
        return 0
    with Session(ENGINE) as session:
        objs = [Notice(**_sanitise(r)) for r in records]
        session.bulk_save_objects(objs)
        session.commit()
    return len(records)


def bulk_upsert(records: list[dict]) -> tuple[int, int]:
    """
    Insert new records and update existing ones.
    Matches on (gstin, notice_number).
    Maintains all existing data for empty/blank Excel cells when updating.
    Returns (inserted_count, updated_count).
    """
    if not records:
        return 0, 0

    inserted = 0
    updated = 0

    with Session(ENGINE) as session:
        for rec in records:
            key_gstin  = str(rec.get("gstin", "")).upper().strip()
            key_notice = str(rec.get("notice_number", "")).upper().strip()

            existing = (
                session.query(Notice)
                .filter(
                    Notice.gstin.ilike(key_gstin),
                    Notice.notice_number.ilike(key_notice),
                )
                .first()
            )

            clean = _sanitise(rec)

            if existing:
                # Update non-empty fields; preserve existing DB data for empty Excel fields
                for field, val in clean.items():
                    if field not in ("id", "created_at") and val not in (None, ""):
                        setattr(existing, field, val)
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                # For new records, set default statuses if missing
                if not clean.get("client_data_status"):
                    clean["client_data_status"] = "Pending"
                if not clean.get("response_status"):
                    clean["response_status"] = "Pending"
                session.add(Notice(**clean))
                inserted += 1

        session.commit()

    return inserted, updated


def replace_all_records(records: list[dict]) -> int:
    """
    Delete all existing notices and insert new records.
    Returns count of records inserted.
    """
    with Session(ENGINE) as session:
        session.query(Notice).delete()
        if records:
            objs = [Notice(**_sanitise(r)) for r in records]
            session.bulk_save_objects(objs)
        session.commit()
    return len(records)



def update_notice_fields(notice_id: int, fields: dict) -> bool:
    """Update arbitrary fields on a single notice by id."""
    with Session(ENGINE) as session:
        obj = session.get(Notice, notice_id)
        if not obj:
            return False
        for k, v in fields.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        session.commit()
    return True


def delete_notice(notice_id: int) -> bool:
    """Delete a notice by id."""
    with Session(ENGINE) as session:
        obj = session.get(Notice, notice_id)
        if not obj:
            return False
        session.delete(obj)
        session.commit()
    return True


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _notice_to_dict(n: Notice) -> dict:
    return {
        "id":                     n.id,
        "client_name":            n.client_name or "",
        "gstin":                  n.gstin or "",
        "notice_number":          n.notice_number or "",
        "notice_issue_date":      n.notice_issue_date or "",
        "notice_section":         n.notice_section or "",
        "act_type":               n.act_type or "",
        "issuing_officer":        n.issuing_officer or "",
        "officer_designation":    n.officer_designation or "",
        "due_date":               n.due_date or "",
        "notice_type":            n.notice_type or "",
        "client_data_status":     n.client_data_status or "Pending",
        "data_requested":         n.data_requested or "",
        "date_data_requested":    n.date_data_requested or "",
        "date_data_received":     n.date_data_received or "",
        "assigned_team_member":   n.assigned_team_member or "",
        "response_filing_date":   n.response_filing_date or "",
        "response_status":        n.response_status or "Pending",
        "remarks":                n.remarks or "",
        "created_at":             n.created_at,
        "updated_at":             n.updated_at,
    }


def _sanitise(rec: dict) -> dict:
    """Keep only keys that are valid Notice columns."""
    valid = {c.name for c in Notice.__table__.columns
             if c.name not in ("id", "created_at", "updated_at")}
    return {k: v for k, v in rec.items() if k in valid}


def _empty_dataframe() -> pd.DataFrame:
    cols = [
        "id", "client_name", "gstin", "notice_number", "notice_issue_date",
        "notice_section", "act_type", "issuing_officer", "officer_designation",
        "due_date", "notice_type", "client_data_status", "data_requested",
        "date_data_requested", "date_data_received", "assigned_team_member",
        "response_filing_date", "response_status", "remarks",
        "created_at", "updated_at",
    ]
    return pd.DataFrame(columns=cols)
