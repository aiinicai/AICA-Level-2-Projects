from datetime import datetime, date
from decimal import Decimal

from .extensions import db

REQUESTER, APPROVER, ADMIN = "requester", "approver", "admin"
ROLES = (REQUESTER, APPROVER, ADMIN)
MRC, MNRC = "MRC", "MNRC"
DRAFT, FINAL, CANCELLED = "DRAFT", "FINAL", "CANCELLED"


def now():
    return datetime.now().replace(microsecond=0)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=REQUESTER)
    active = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=now)

    @property
    def is_admin(self):
        return self.role == ADMIN

    @property
    def is_approver(self):
        return self.role in (APPROVER, ADMIN)


class Plant(db.Model):
    """A consignor location / GSTIN registration of our company."""
    __tablename__ = "plants"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(400), nullable=False)
    state_code = db.Column(db.String(2), nullable=False)
    pin = db.Column(db.String(6), nullable=False)
    gstin = db.Column(db.String(15), nullable=False)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    signatory = db.Column(db.String(100), default="Authorised Signatory")
    active = db.Column(db.Boolean, nullable=False, default=True)


class SeriesConfig(db.Model):
    """Numbering format per challan type. Number = prefix / FY / zero-padded sequence."""
    __tablename__ = "series_config"
    ctype = db.Column(db.String(10), primary_key=True)      # MRC / MNRC (stable code)
    prefix = db.Column(db.String(10), nullable=False)
    fy_style = db.Column(db.String(5), nullable=False, default="short")   # short=26-27, long=2026-27
    separator = db.Column(db.String(1), nullable=False, default="/")
    pad = db.Column(db.Integer, nullable=False, default=4)
    title = db.Column(db.String(60), nullable=False)
    returnable = db.Column(db.Boolean, nullable=False, default=False)


class Counter(db.Model):
    """One row per sequence ('VENDOR', 'MRC|2026-27', ...). Incremented inside the saving transaction,
    so a rolled-back save never burns a number and concurrent saves are serialised by the database."""
    __tablename__ = "counters"
    key = db.Column(db.String(40), primary_key=True)
    last_no = db.Column(db.Integer, nullable=False, default=0)


class Vendor(db.Model):
    __tablename__ = "vendors"
    id = db.Column(db.Integer, primary_key=True)
    vendor_no = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    name_norm = db.Column(db.String(150), index=True)
    address = db.Column(db.String(400), nullable=False)
    state_code = db.Column(db.String(2), nullable=False)
    pin = db.Column(db.String(6), nullable=False)
    gstin = db.Column(db.String(15), unique=True)           # NULL for unregistered
    pan = db.Column(db.String(10))
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    erp_code = db.Column(db.String(30))
    erp_code_updated_at = db.Column(db.DateTime)
    erp_code_updated_by = db.Column(db.String(50))
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


class Challan(db.Model):
    __tablename__ = "challans"
    id = db.Column(db.Integer, primary_key=True)
    ctype = db.Column(db.String(10), nullable=False, index=True)       # MRC / MNRC
    status = db.Column(db.String(10), nullable=False, default=DRAFT, index=True)
    number = db.Column(db.String(16), unique=True)                     # assigned on final save only
    fy = db.Column(db.String(7), index=True)
    seq_no = db.Column(db.Integer)
    challan_date = db.Column(db.Date, nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, index=True)
    place_of_supply = db.Column(db.String(2), nullable=False)
    interstate = db.Column(db.Boolean, nullable=False, default=False)
    purpose = db.Column(db.String(40), nullable=False)
    purpose_text = db.Column(db.String(200))
    reason = db.Column(db.Text, nullable=False)           # MRC: why manual; MNRC: business justification
    # returnable-only
    corrective_action = db.Column(db.Text)
    corrective_owner = db.Column(db.String(100))
    corrective_target_date = db.Column(db.Date)
    corrective_status = db.Column(db.String(10))          # Open / Done
    corrective_done_date = db.Column(db.Date)
    corrective_remarks = db.Column(db.String(300))
    expected_return_date = db.Column(db.Date)
    goods_category = db.Column(db.String(10))             # INPUTS / CAPITAL (job-work time limit)
    return_status = db.Column(db.String(20))              # Open / Partially Received / Closed
    # transport & reference
    transport_mode = db.Column(db.String(20))
    vehicle_no = db.Column(db.String(15))
    transporter_name = db.Column(db.String(100))
    transporter_id = db.Column(db.String(15))
    ref_doc_no = db.Column(db.String(60))
    ref_doc_date = db.Column(db.Date)
    remarks = db.Column(db.String(400))
    # e-way bill
    ewb_status = db.Column(db.String(10), nullable=False, default="Pending", index=True)
    ewb_no = db.Column(db.String(12))
    ewb_date = db.Column(db.Date)
    ewb_valid_upto = db.Column(db.Date)
    # totals
    taxable_total = db.Column(db.Numeric(14, 2), default=0)
    cgst_total = db.Column(db.Numeric(14, 2), default=0)
    sgst_total = db.Column(db.Numeric(14, 2), default=0)
    igst_total = db.Column(db.Numeric(14, 2), default=0)
    cess_total = db.Column(db.Numeric(14, 2), default=0)
    grand_total = db.Column(db.Numeric(14, 2), default=0)
    # snapshots taken at finalisation so later master edits never change an issued challan
    consignor_json = db.Column(db.Text)
    consignee_json = db.Column(db.Text)
    # print / lifecycle
    printed_at = db.Column(db.DateTime)
    print_count = db.Column(db.Integer, default=0)
    cancel_reason = db.Column(db.String(300))
    cancelled_by = db.Column(db.String(50))
    cancelled_at = db.Column(db.DateTime)
    is_historical = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=now)
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    finalized_by = db.Column(db.String(50))
    finalized_at = db.Column(db.DateTime)

    plant = db.relationship("Plant")
    vendor = db.relationship("Vendor")
    lines = db.relationship("ChallanLine", backref="challan", order_by="ChallanLine.line_no",
                            cascade="all, delete-orphan")
    receipts = db.relationship("Receipt", backref="challan", order_by="Receipt.received_date",
                               cascade="all, delete-orphan")

    @property
    def is_returnable(self):
        return self.ctype == MRC

    @property
    def display_no(self):
        return self.number or f"DRAFT-{self.id}"

    @property
    def total_qty(self):
        return sum((l.qty for l in self.lines), Decimal(0))

    @property
    def received_qty(self):
        return sum((l.qty_received or 0 for l in self.lines), Decimal(0))

    def corrective_state(self, today=None):
        today = today or date.today()
        if not self.is_returnable or self.status != FINAL:
            return None
        if self.corrective_status == "Done":
            return "Done"
        if self.corrective_target_date and self.corrective_target_date < today:
            return "Overdue"
        return "Open"

    def statutory_due(self):
        """Sec. 143 CGST Act: inputs 1 year, capital goods 3 years from the date of sending."""
        if not self.is_returnable or not self.challan_date:
            return None
        years = 3 if self.goods_category == "CAPITAL" else 1
        d = self.challan_date
        try:
            return d.replace(year=d.year + years)
        except ValueError:            # 29 Feb
            return d.replace(year=d.year + years, day=28)


class ChallanLine(db.Model):
    __tablename__ = "challan_lines"
    id = db.Column(db.Integer, primary_key=True)
    challan_id = db.Column(db.Integer, db.ForeignKey("challans.id"), nullable=False, index=True)
    line_no = db.Column(db.Integer, nullable=False)
    part_no = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.String(250), nullable=False)
    hsn = db.Column(db.String(8), nullable=False)
    qty = db.Column(db.Numeric(14, 3), nullable=False)
    uom = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    taxable_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    cess_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    cgst = db.Column(db.Numeric(14, 2), default=0)
    sgst = db.Column(db.Numeric(14, 2), default=0)
    igst = db.Column(db.Numeric(14, 2), default=0)
    cess = db.Column(db.Numeric(14, 2), default=0)
    qty_received = db.Column(db.Numeric(14, 3), nullable=False, default=0)

    @property
    def line_total(self):
        return (self.taxable_value or 0) + (self.cgst or 0) + (self.sgst or 0) + (self.igst or 0) + (self.cess or 0)


class Receipt(db.Model):
    """Goods received back against a returnable challan line (partial receipts allowed)."""
    __tablename__ = "receipts"
    id = db.Column(db.Integer, primary_key=True)
    challan_id = db.Column(db.Integer, db.ForeignKey("challans.id"), nullable=False, index=True)
    line_id = db.Column(db.Integer, db.ForeignKey("challan_lines.id"), nullable=False)
    received_date = db.Column(db.Date, nullable=False)
    qty = db.Column(db.Numeric(14, 3), nullable=False)
    doc_ref = db.Column(db.String(60), nullable=False)
    remarks = db.Column(db.String(200))
    created_by = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=now)
    line = db.relationship("ChallanLine")


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, default=now, index=True)
    username = db.Column(db.String(50))
    entity = db.Column(db.String(20), index=True)
    entity_id = db.Column(db.Integer)
    ref = db.Column(db.String(60))
    action = db.Column(db.String(30))
    details = db.Column(db.Text)


class UploadBatch(db.Model):
    """Parsed + validated Excel upload waiting for the user to confirm the commit."""
    __tablename__ = "upload_batches"
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), nullable=False)       # vendors / challans
    filename = db.Column(db.String(200))
    payload = db.Column(db.Text, nullable=False)          # JSON of parsed rows
    errors = db.Column(db.Text)                           # JSON list
    warnings = db.Column(db.Text)
    status = db.Column(db.String(12), default="PENDING")  # PENDING / COMMITTED / DISCARDED
    created_by = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=now)
