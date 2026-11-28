"""Demo data: one plant, three users, a handful of vendors and challans. Everything goes through the real
services so numbering, tax and audit rules are exercised exactly like production."""
from datetime import date, timedelta
from decimal import Decimal

from werkzeug.security import generate_password_hash

from . import gst, services as sv
from .extensions import db
from .models import APPROVER, MNRC, MRC, REQUESTER, Challan, Plant, User

VENDORS = [
    ("Precision Calibration Labs Pvt Ltd", "Plot 12, MIDC Bhosari, Pune", "27", "411026", "AABCP1234C", "Mr. R. Kulkarni"),
    ("Sunrise Auto Components", "14 Industrial Estate, Peenya, Bengaluru", "29", "560058", "AAFCS5678D", "Ms. L. Rao"),
    ("Gujarat Rework Industries", "Survey 88, GIDC Vatva, Ahmedabad", "24", "382445", "AAECG4321K", "Mr. P. Shah"),
    ("Orion Technologies Ltd (Sister Co.)", "Tower B, Hinjewadi Phase 2, Pune", "27", "411057", "AAACO9876L", "IT Helpdesk"),
]


def load_demo():
    if Plant.query.first():
        return
    p = Plant(code="PNQ1", company_name="Demo Engineering Pvt Ltd", address="Gat 45, Chakan Industrial Area, Pune",
              state_code="27", pin="410501", gstin=gst.make_gstin("27", "AABCD1111A"), phone="020-5550100",
              email="accounts@demo-eng.example")
    db.session.add(p)
    for u, n, r in (("requester1", "Ravi Requester", REQUESTER), ("approver1", "Anita Approver", APPROVER)):
        db.session.add(User(username=u, full_name=n, role=r, password_hash=generate_password_hash("Demo@1234"),
                            must_change_password=False))
    db.session.commit()
    admin = User.query.filter_by(username="admin").first()
    req = User.query.filter_by(username="requester1").first()
    vs = []
    for i, (name, addr, st, pin, pan, contact) in enumerate(VENDORS):
        c, errs = sv.clean_vendor({"name": name, "address": addr, "state_code": st, "pin": pin,
                                   "gstin": gst.make_gstin(st, pan), "contact_person": contact})
        assert not errs, errs
        vs.append(sv.create_vendor(c, req))
    sv.set_erp_code(vs[1], "V10045", admin)          # already in ERP -> MRC blocked for requesters
    db.session.commit()

    today = date.today()

    def mk(ctype, vendor, user, days_ago, purpose, reason, lines, **extra):
        form = _Form({"plant_id": str(p.id), "challan_date": (today - timedelta(days=days_ago)).isoformat(),
                      "vendor_id": str(vendor.id), "purpose": purpose, "reason": reason, "transport_mode": "Road",
                      "vehicle_no": "MH12AB1234", **extra}, lines)
        h, ls, errs = sv.parse_challan_form(form, ctype, user)
        assert not errs, errs
        ch = Challan(ctype=ctype, status="DRAFT", created_by=user.username)
        sv.apply_challan(ch, h, ls)
        db.session.add(ch)
        db.session.flush()
        sv.finalize(ch, user)
        db.session.commit()
        return ch

    mrc = dict(corrective_action="Create vendor in ERP", corrective_owner="Purchase - Mr. Joshi",
               goods_category="CAPITAL")
    a = mk(MRC, vs[0], req, 40, "Calibration", "Calibrator not yet created in ERP",
           [("CMM-PRB-01", "Coordinate measuring probe", "9031", "1", "NOS", "45000", "18")],
           corrective_target_date=(today - timedelta(days=5)).isoformat(),
           expected_return_date=(today - timedelta(days=10)).isoformat(), **mrc)
    b = mk(MRC, vs[2], req, 10, "Rework", "New rework vendor, ERP onboarding in progress",
           [("BRK-221", "Brake bracket", "8708", "200", "NOS", "120", "18"),
            ("BRK-222", "Brake bracket LH", "8708", "100", "NOS", "125", "18")],
           corrective_target_date=(today + timedelta(days=20)).isoformat(),
           expected_return_date=(today + timedelta(days=20)).isoformat(), **{**mrc, "goods_category": "INPUTS"})
    c = mk(MNRC, vs[3], req, 3, "Return of sister-entity asset", "Laptop lent for audit period returned",
           [("LAP-8841", "Laptop (asset 8841)", "8471", "1", "NOS", "30000", "18")])
    d = mk(MNRC, vs[2], req, 2, "Return of customer material", "Customer material returned after rework",
           [("CUS-55", "Customer casting after rework", "7325", "50", "NOS", "300", "18")],
           ref_doc_no="CH-7781", ref_doc_date=(today - timedelta(days=30)).isoformat())
    sv.update_ewb(c, {"ewb_no": "341234567890", "ewb_date": (today - timedelta(days=3)).isoformat(),
                      "ewb_valid_upto": (today + timedelta(days=1)).isoformat()}, req)
    sv.record_receipt(b, _Form({"received_date": (today - timedelta(days=2)).isoformat(), "doc_ref": "GRN/26/118",
                                f"qty_{b.lines[0].id}": "120"}, []), req)
    db.session.commit()


class _Form(dict):
    """Minimal stand-in for request.form so demo data can reuse parse_challan_form."""
    def __init__(self, data, lines):
        super().__init__(data)
        self._lines = lines

    def getlist(self, key):
        keys = ["part_no", "description", "hsn", "qty", "uom", "rate", "tax_rate"]
        if key in keys:
            return [l[keys.index(key)] for l in self._lines]
        if key == "cess_rate":
            return ["0"] * len(self._lines)
        return []
