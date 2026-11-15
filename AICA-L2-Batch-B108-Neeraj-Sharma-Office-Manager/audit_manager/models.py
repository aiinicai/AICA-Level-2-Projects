from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _):
    """Foreign keys on and WAL mode so several staff can use the database at once."""
    try:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()
    except Exception:  # not SQLite
        pass


ROLES = {
    "super_admin": "Super Admin",
    "partner": "CA / Partner",
    "manager": "Manager",
    "employee": "Accountant / Employee",
}

client_staff = db.Table(
    "client_staff",
    db.Column("client_id", db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    phone = db.Column(db.String(30))
    employee_code = db.Column(db.String(30))
    designation = db.Column(db.String(100))
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def role_label(self) -> str:
        return ROLES.get(self.role, self.role)

    @property
    def is_admin_or_partner(self) -> bool:
        return self.role in ("super_admin", "partner")

    @property
    def is_manager_or_above(self) -> bool:
        return self.role in ("super_admin", "partner", "manager")


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_code = db.Column(db.String(30), unique=True, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(20), default="business")  # individual / business
    pan = db.Column(db.String(20), index=True)
    gstin = db.Column(db.String(20))
    tan = db.Column(db.String(20))
    email = db.Column(db.String(160))
    mobile = db.Column(db.String(30))
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(12))
    status = db.Column(db.String(20), default="active")  # active / onboarding / inactive
    is_gst_registered = db.Column(db.Boolean, default=False)
    is_itr_applicable = db.Column(db.Boolean, default=True)
    is_tds_applicable = db.Column(db.Boolean, default=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    notes = db.Column(db.Text)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    hourly_rate = db.Column(db.Float)  # this client's own rate per hour; empty = use the staff / default rate
    contact_person = db.Column(db.String(120))
    contact_designation = db.Column(db.String(80))

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    staff = db.relationship("User", secondary=client_staff, backref="shared_clients")

    def outstanding(self) -> float:
        return round(sum(i.balance for i in self.invoices if i.status != "paid"), 2)


class GstReturnType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)  # GSTR-1, GSTR-3B ...
    frequency = db.Column(db.String(12), nullable=False, default="monthly")  # monthly / quarterly / annual
    due_day = db.Column(db.Integer, default=20)  # day of the following month (monthly) or period end
    active = db.Column(db.Boolean, default=True)


class GstReturn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    return_type_id = db.Column(db.Integer, db.ForeignKey("gst_return_type.id"), nullable=False)
    period = db.Column(db.String(20), nullable=False)  # e.g. 2026-10 or 2026-Q2
    due_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="pending")
    filed_date = db.Column(db.Date)
    arn = db.Column(db.String(60))
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    notes = db.Column(db.Text)

    client = db.relationship("Client", backref=db.backref("gst_returns", cascade="all, delete-orphan"))
    return_type = db.relationship("GstReturnType")
    assigned_to = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("client_id", "return_type_id", "period", name="uq_gst_period"),)


class ItrFiling(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_year = db.Column(db.String(10), nullable=False)  # 2026-27
    form_type = db.Column(db.String(10), default="ITR-1")
    due_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="pending")
    filed_date = db.Column(db.Date)
    ack_number = db.Column(db.String(60))
    refund_amount = db.Column(db.Float, default=0)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    notes = db.Column(db.Text)
    verification_status = db.Column(db.String(20))  # None / e_verified / itrv_sent / itrv_received
    verification_date = db.Column(db.Date)

    client = db.relationship("Client", backref=db.backref("itr_filings", cascade="all, delete-orphan"))

    @property
    def verify_by(self):
        """A filed return must be verified within 30 days of filing; None once verified or when not yet filed."""
        from datetime import timedelta

        if self.status != "filed" or not self.filed_date or self.verification_status in ("e_verified", "itrv_received"):
            return None
        return self.filed_date + timedelta(days=30)
    assigned_to = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("client_id", "assessment_year", "form_type", name="uq_itr_ay"),)


class TdsReturn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = db.Column(db.String(10), nullable=False)  # 2026-27
    quarter = db.Column(db.String(4), nullable=False)  # Q1..Q4
    form_type = db.Column(db.String(10), default="26Q")  # 24Q / 26Q / 27Q / 27EQ
    due_date = db.Column(db.Date)
    tds_deducted = db.Column(db.Float, default=0)
    tds_deposited = db.Column(db.Float, default=0)
    challan_number = db.Column(db.String(60))
    ack_number = db.Column(db.String(60))  # token / acknowledgement (RRR) number of the filed statement
    status = db.Column(db.String(30), default="pending")
    filed_date = db.Column(db.Date)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))

    client = db.relationship("Client", backref=db.backref("tds_returns", cascade="all, delete-orphan"))
    assigned_to = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("client_id", "financial_year", "quarter", "form_type", name="uq_tds_q"),)


class ComplianceRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    compliance_type = db.Column(db.String(20), default="custom")
    frequency = db.Column(db.String(12), default="monthly")  # monthly / quarterly / yearly
    due_day = db.Column(db.Integer, default=1)
    due_month = db.Column(db.Integer)  # for yearly rules
    applies_to = db.Column(db.String(12), default="all")  # all / gst / itr / tds
    active = db.Column(db.Boolean, default=True)


class ComplianceDeadline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    compliance_type = db.Column(db.String(20), default="custom")
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    due_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), default="upcoming")  # upcoming / in_progress / completed
    priority = db.Column(db.String(10), default="medium")
    description = db.Column(db.Text)
    completed_at = db.Column(db.DateTime)

    client = db.relationship("Client", backref=db.backref("deadlines", cascade="all, delete-orphan"))
    assigned_to = db.relationship("User")

    @property
    def is_overdue(self) -> bool:
        return self.status != "completed" and self.due_date < date.today()


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="SET NULL"), index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    category = db.Column(db.String(30), default="general")
    priority = db.Column(db.String(10), default="medium")
    status = db.Column(db.String(20), default="todo")  # todo / in_progress / under_review / completed
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("Client")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    comments = db.relationship("TaskComment", backref="task", cascade="all, delete-orphan", order_by="TaskComment.id")

    @property
    def is_overdue(self) -> bool:
        return self.status != "completed" and self.due_date is not None and self.due_date < date.today()


class TaskComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False, index=True)
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date)
    tax_mode = db.Column(db.String(12), default="cgst_sgst")  # cgst_sgst / igst / exempt
    subtotal = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    taxable_amount = db.Column(db.Float, default=0)
    cgst_rate = db.Column(db.Float, default=0)
    cgst_amount = db.Column(db.Float, default=0)
    sgst_rate = db.Column(db.Float, default=0)
    sgst_amount = db.Column(db.Float, default=0)
    igst_rate = db.Column(db.Float, default=0)
    igst_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default="unpaid")  # unpaid / partially_paid / paid / overdue
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("Client", backref="invoices")
    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.id")
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan", order_by="Payment.payment_date")

    def sync_payments(self) -> None:
        paid = round(sum(p.amount for p in self.payments), 2)
        self.paid_amount = paid
        self.balance = max(0.0, round(self.total_amount - paid, 2))
        past_due = self.due_date is not None and self.due_date < date.today()
        if self.balance <= 0.01 and self.total_amount > 0:
            self.balance = 0.0
            self.status = "paid"
        elif paid > 0:
            self.status = "overdue" if past_due else "partially_paid"
        else:
            self.status = "overdue" if past_due else "unpaid"


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    sac_code = db.Column(db.String(12), default="998221")
    quantity = db.Column(db.Float, default=1)
    rate = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, default=0)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(20), default="bank")
    reference = db.Column(db.String(80))
    notes = db.Column(db.Text)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))


class FirmSetting(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key: str, default=None):
        row = db.session.get(FirmSetting, key)
        return row.value if row is not None and row.value is not None else default

    @staticmethod
    def put(key: str, value) -> None:
        row = db.session.get(FirmSetting, key)
        if row is None:
            db.session.add(FirmSetting(key=key, value=value))
        else:
            row.value = value

    @staticmethod
    def all() -> dict:
        return {r.key: r.value for r in FirmSetting.query.all()}


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    module = db.Column(db.String(30))
    description = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user = db.relationship("User")


class WhatsAppTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    category = db.Column(db.String(20), default="general")
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.Column(db.String(80))  # optional picture sent with this template


class WhatsAppMessage(db.Model):
    """A message prepared for sending. We cannot confirm delivery (click-to-chat), so the final state is 'opened'."""
    id = db.Column(db.Integer, primary_key=True)
    audience = db.Column(db.String(10), nullable=False)  # client / staff
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="SET NULL"), index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    recipient_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    body = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), default="manual")  # manual / bulk / reminder
    status = db.Column(db.String(10), default="queued", index=True)  # queued / opened / skipped
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    opened_at = db.Column(db.DateTime)
    channel = db.Column(db.String(10), default="whatsapp")  # whatsapp / email
    subject = db.Column(db.String(200))
    image = db.Column(db.String(80))  # picture to send with the message
    send_at = db.Column(db.DateTime)  # scheduled emails
    email = db.Column(db.String(160))

    client = db.relationship("Client")
    created_by = db.relationship("User", foreign_keys=[created_by_id])


class ServiceItem(db.Model):
    """Services master for invoices: pick a service and its SAC code and usual fee are filled in."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    sac_code = db.Column(db.String(12), default="998221")
    default_rate = db.Column(db.Float, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)


class DueDate(db.Model):
    """Due-date master: statutory and office dates, used in messages and reminders."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(20), default="other")
    period = db.Column(db.String(80))
    due_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.String(300))
    original_date = db.Column(db.Date)  # the date before the department extended it


class ClientCredential(db.Model):
    """A client's portal login (income tax, GST, TRACES ...). The password is stored encrypted."""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    portal = db.Column(db.String(60), nullable=False)
    username = db.Column(db.String(160))
    secret = db.Column(db.Text)
    notes = db.Column(db.String(300))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship("Client", backref=db.backref("credentials", cascade="all, delete-orphan", order_by="ClientCredential.portal"))


class TimeEntry(db.Model):
    """Time spent on a client, for hour-based billing."""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    work_date = db.Column(db.Date, nullable=False, default=date.today)
    hours = db.Column(db.Float, nullable=False, default=0)
    description = db.Column(db.String(300))
    rate = db.Column(db.Float, default=0)
    billable = db.Column(db.Boolean, default=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id", ondelete="SET NULL"))

    client = db.relationship("Client")
    user = db.relationship("User")
    invoice = db.relationship("Invoice")

    @property
    def value(self) -> float:
        return round((self.hours or 0) * (self.rate or 0), 2)


class Matter(db.Model):
    """A case or matter (for advocates): court, parties and the next hearing date."""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    case_number = db.Column(db.String(80))
    court = db.Column(db.String(160))
    opposite_party = db.Column(db.String(200))
    stage = db.Column(db.String(120))
    next_hearing = db.Column(db.Date, index=True)
    status = db.Column(db.String(12), default="open")  # open / closed
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    notes = db.Column(db.Text)

    client = db.relationship("Client")
    assigned_to = db.relationship("User")


class AutoLog(db.Model):
    """Remembers which automatic reminders have already gone out, so nobody is reminded twice."""
    key = db.Column(db.String(120), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
