"""
Implements the Data Visibility Matrix (Section 2.3 of the project plan).
All checks happen here, server-side, so the frontend never decides what's visible.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models


def is_ceo(user: models.User) -> bool:
    return user.role == models.ROLE_CEO


def is_dept_admin(user: models.User) -> bool:
    return user.role == models.ROLE_DEPT_ADMIN


def is_manager(user: models.User) -> bool:
    return user.role == models.ROLE_MANAGER


def get_team_ids(db: Session, manager: models.User) -> set:
    """All direct + indirect reports of a manager/admin."""
    ids = set()
    frontier = [manager.id]
    while frontier:
        next_frontier = db.query(models.User.id).filter(models.User.manager_id.in_(frontier)).all()
        next_ids = [r[0] for r in next_frontier if r[0] not in ids]
        if not next_ids:
            break
        ids.update(next_ids)
        frontier = next_ids
    return ids


def is_direct_or_indirect_report(db: Session, viewer: models.User, target: models.User) -> bool:
    if target.manager_id is None:
        return False
    node = target
    seen = set()
    while node.manager_id and node.manager_id not in seen:
        seen.add(node.manager_id)
        if node.manager_id == viewer.id:
            return True
        node = db.query(models.User).get(node.manager_id)
        if node is None:
            break
    return False


def can_view_detail(db: Session, viewer: models.User, target: models.User) -> bool:
    """Can `viewer` see full details (not just free/busy) of `target`'s
    calendar / attendance / leave / task records?"""
    if viewer.id == target.id:
        return True
    if is_ceo(viewer):
        return True
    if is_dept_admin(viewer) and viewer.department_id == target.department_id:
        return True
    if is_manager(viewer) and is_direct_or_indirect_report(db, viewer, target):
        return True
    return False


def can_view_confidential(db: Session, viewer: models.User, target: models.User) -> bool:
    """Leave detail / notice period / resignation visibility - Manager+ only,
    and only within their own scope (never for peers/juniors of others)."""
    if viewer.id == target.id:
        return True
    if is_ceo(viewer):
        return True
    if is_dept_admin(viewer) and viewer.department_id == target.department_id:
        return True
    if is_manager(viewer) and is_direct_or_indirect_report(db, viewer, target):
        return True
    return False


def can_manage_user(viewer: models.User, target: models.User) -> bool:
    """Add/edit/deactivate/reset-password rights."""
    if is_ceo(viewer):
        return True
    if is_dept_admin(viewer) and viewer.department_id == target.department_id and target.role != models.ROLE_CEO:
        return True
    return False


def visible_users_scope(db: Session, viewer: models.User):
    """Returns a SQLAlchemy query of users whose full record `viewer` may browse/manage."""
    q = db.query(models.User)
    if is_ceo(viewer):
        return q
    if is_dept_admin(viewer):
        return q.filter(models.User.department_id == viewer.department_id)
    if is_manager(viewer):
        team_ids = get_team_ids(db, viewer) | {viewer.id}
        return q.filter(models.User.id.in_(team_ids))
    return q.filter(models.User.id == viewer.id)


def assignable_users(db: Session, assigner: models.User):
    """Who `assigner` is allowed to hand tasks to - their manage-scope, excluding themselves.
    Employees/juniors cannot assign tasks to anyone."""
    if assigner.role == models.ROLE_EMPLOYEE:
        return []
    return visible_users_scope(db, assigner).filter(models.User.id != assigner.id).all()


def can_assign_to(db: Session, assigner: models.User, assignee: models.User) -> bool:
    if assigner.id == assignee.id:
        return False
    return assignee.id in {u.id for u in assignable_users(db, assigner)}


def can_manage_task(db: Session, viewer: models.User, task_owner: models.User, assigned_by_id) -> bool:
    """Can `viewer` update status / comment on a task owned by `task_owner`?
    True for the assignee, the person who assigned it, or anyone in the assignee's manage-scope."""
    if viewer.id == task_owner.id:
        return True
    if assigned_by_id and viewer.id == assigned_by_id:
        return True
    return can_view_detail(db, viewer, task_owner)


def export_scope_users(db: Session, viewer: models.User):
    """Same scoping rule used for Excel export (Section 2.1.G): CEO=all,
    Dept Admin=own dept, Manager=own team, Employee=self only."""
    return visible_users_scope(db, viewer).all()
