import datetime as dt
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from .database import Base

# Role levels, matching the plan exactly (highest to lowest access)
ROLE_CEO = "CEO"
ROLE_DEPT_ADMIN = "DEPT_ADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_EMPLOYEE = "EMPLOYEE"
ROLES = [ROLE_CEO, ROLE_DEPT_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE]
ROLE_RANK = {ROLE_CEO: 0, ROLE_DEPT_ADMIN: 1, ROLE_MANAGER: 2, ROLE_EMPLOYEE: 3}


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    users = relationship("User", back_populates="department")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    employee_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    must_change_password = Column(Boolean, default=True)
    role = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    designation = Column(String(150))
    date_of_joining = Column(Date)
    is_active = Column(Boolean, default=True)

    # Lifecycle / resignation fields
    employment_status = Column(String(20), default="ACTIVE")  # ACTIVE, ON_NOTICE, EXITED
    resignation_date = Column(Date, nullable=True)
    notice_period_days = Column(Integer, nullable=True)
    last_working_day = Column(Date, nullable=True)
    resignation_reason = Column(Text, nullable=True)
    exit_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    department = relationship("Department", back_populates="users")
    manager = relationship("User", remote_side=[id])


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # the assignee - person who owns/does the work
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = self-created (prompt bar / manual)
    event_type = Column(String(20), nullable=False)  # TASK, MEETING, PENDING_ACTION, REMINDER
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=True)  # HH:MM
    end_date = Column(Date, nullable=True)
    priority = Column(String(10), default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    status = Column(String(15), default="OPEN")  # OPEN, IN_PROGRESS, DONE, CANCELLED
    invitees = Column(Text, nullable=True)  # comma separated user ids
    raw_prompt_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class TaskComment(Base):
    """A reply thread on a task/pending-action - used both for plain updates
    and for a junior 'raising a query' back to whoever assigned the task."""
    __tablename__ = "task_comments"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_type = Column(String(10), default="COMMENT")  # COMMENT or QUERY
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    event = relationship("CalendarEvent")
    author = relationship("User")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(15), nullable=False)  # WFO, WFH, LEAVE, HOLIDAY, HALF_DAY, ABSENT
    raw_prompt_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User")


class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    default_annual_days = Column(Integer, default=12)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(15), default="PENDING")  # PENDING, APPROVED, REJECTED
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    raw_prompt_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    leave_type = relationship("LeaveType")
    approver = relationship("User", foreign_keys=[approver_id])


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    actor = relationship("User")


class BackupLog(Base):
    __tablename__ = "backup_log"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # null = company-wide
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
