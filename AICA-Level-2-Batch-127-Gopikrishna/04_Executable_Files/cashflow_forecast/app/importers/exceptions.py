"""Resolve mapping exceptions: map to an existing category, add a new category, or ignore.

Mapping (or adding) also stores a CategoryAlias, so the same header is recognised on the next
upload without asking again. When a batch has no open exceptions left it becomes current.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.importers.pipeline import make_current
from app.importers.specs import normalise_header
from app.models import (BatchStatus, Category, CategoryAlias, Direction, ExceptionStatus, ImportBatch, LineItem,
                        MappingException, Treatment)
from app.models.base import utcnow
from app.services.audit import audit


class ResolveError(ValueError):
    pass


def _open(db: Session, exc_id: int) -> MappingException:
    exc = db.get(MappingException, exc_id)
    if exc is None:
        raise ResolveError(f"exception {exc_id} not found")
    if exc.status != ExceptionStatus.OPEN:
        raise ResolveError(f"exception {exc_id} is already {exc.status.value}")
    return exc


def _items(db: Session, exc: MappingException) -> list[LineItem]:
    norm = normalise_header(exc.raw_text)
    return [li for li in db.scalars(select(LineItem).where(LineItem.batch_id == exc.batch_id,
                                                          LineItem.category_id.is_(None)))
            if normalise_header(li.category_text) == norm]


def _finish(db: Session, exc: MappingException, status: ExceptionStatus, cat_id: int | None, user_id) -> bool:
    exc.status, exc.resolved_category_id = status, cat_id
    exc.resolved_by_id, exc.resolved_at = user_id, utcnow()
    db.flush()
    remaining = db.scalar(select(func.count()).select_from(MappingException).where(
        MappingException.batch_id == exc.batch_id, MappingException.status == ExceptionStatus.OPEN))
    batch = db.get(ImportBatch, exc.batch_id)
    if remaining == 0 and batch.status == BatchStatus.EXCEPTIONS:
        make_current(db, batch, user_id)
        audit(db, "import.accepted", "import_batch", batch.id, after={"after_exceptions": True}, user_id=user_id)
        return True
    return False


def map_to_category(db: Session, exc_id: int, category_id: int, user_id: int | None = None,
                    remember: bool = True) -> bool:
    """Returns True when this made the batch current."""
    exc = _open(db, exc_id)
    cat = db.get(Category, category_id)
    if cat is None or not cat.is_active:
        raise ResolveError("category not found or inactive")
    items = _items(db, exc)
    batch = db.get(ImportBatch, exc.batch_id)
    for li in items:
        if not li.direction_provisional and li.direction != cat.direction and batch.source_type.value != "other":
            raise ResolveError(f"'{cat.name}' is an {cat.direction.value} category; these rows are "
                               f"{li.direction.value}s")
    for li in items:
        li.category_id = cat.id
        if li.direction_provisional:
            li.direction, li.direction_provisional = cat.direction, False
    norm = normalise_header(exc.raw_text)
    if remember and norm != normalise_header(cat.name):
        al = db.scalar(select(CategoryAlias).where(CategoryAlias.alias_normalised == norm))
        if al is None:
            db.add(CategoryAlias(alias_normalised=norm, alias_original=exc.raw_text, category_id=cat.id,
                                 created_by_id=user_id))
        else:
            al.category_id = cat.id
    audit(db, "exception.map", "mapping_exception", exc.id,
          after={"text": exc.raw_text, "category": cat.name, "rows": len(items), "remembered": remember},
          user_id=user_id)
    return _finish(db, exc, ExceptionStatus.MAPPED, cat.id, user_id)


def add_new_category(db: Session, exc_id: int, *, name: str | None = None, direction: str, summary_group: str,
                     display_order: int | None = None, treatment: str = "fixed",
                     user_id: int | None = None) -> bool:
    exc = _open(db, exc_id)
    name = (name or exc.raw_text).strip()
    if not name:
        raise ResolveError("name is required")
    if db.scalar(select(Category).where(func.lower(Category.name) == name.lower())):
        raise ResolveError(f"category '{name}' already exists; map to it instead")
    if display_order is None:
        same = db.scalar(select(func.max(Category.display_order)).where(Category.direction == Direction(direction)))
        display_order = (same or 0) + 5
    cat = Category(name=name, direction=Direction(direction), summary_group=summary_group.strip() or "Other",
                   display_order=display_order, default_treatment=Treatment(treatment))
    db.add(cat)
    db.flush()
    audit(db, "category.create", "category", cat.name,
          after={"from_exception": exc.id, "direction": direction, "group": cat.summary_group,
                 "order": display_order}, user_id=user_id)
    became_current = map_to_category(db, exc.id, cat.id, user_id)
    exc.status = ExceptionStatus.NEW_CATEGORY   # closed by the mapping; record that it was a new category
    db.flush()
    return became_current


def ignore(db: Session, exc_id: int, user_id: int | None = None, reason: str = "") -> bool:
    """The rows stay stored (as imported) but without a category, so the forecast leaves them out."""
    exc = _open(db, exc_id)
    n = len(_items(db, exc))
    audit(db, "exception.ignore", "mapping_exception", exc.id,
          after={"text": exc.raw_text, "rows_left_out": n, "reason": reason}, user_id=user_id)
    return _finish(db, exc, ExceptionStatus.IGNORED, None, user_id)
