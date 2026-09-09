"""
Shared declarative base for all FinSight ORM models.

Implementation note (not a schema/architecture change): Blueprint Section
C listed model files by domain (engagement.py, uploads.py, ...) but did
not name a base.py — SQLAlchemy 2.x declarative models need exactly one
shared Base class for Base.metadata to see every table, so this file is
a small, necessary addition to already-approved decisions (SQLAlchemy
2.x, one central DB — Blueprint Section 2/Ambiguity #1).
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
