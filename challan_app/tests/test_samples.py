import os
from app import create_app, gst
from app.cli import bootstrap
from app.extensions import db
from app.models import Challan, Plant, User, Vendor

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def test_shipped_sample_files_import_cleanly(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "s.db").replace("\\", "/")})
    with app.app_context():
        bootstrap()
        u = User.query.filter_by(username="admin").one(); u.must_change_password = False
        db.session.add(Plant(code="PNQ1", company_name="Demo", address="Pune", state_code="27", pin="411001", gstin=gst.make_gstin("27", "AABCD1111A")))
        db.session.commit()
        c = app.test_client()
        with c.session_transaction() as s:
            s["uid"], s["_csrf"] = u.id, "t"
        for kind in ("vendors", "challans"):
            with open(os.path.join(SAMPLES, f"sample_{kind}.xlsx"), "rb") as f:
                r = c.post(f"/upload/{kind}", data={"file": (f, "x.xlsx"), "_csrf": "t"}, content_type="multipart/form-data")
            bid = r.headers["Location"].rsplit("/", 1)[1]
            page = c.get(f"/upload/batch/{bid}").data
            assert b"No errors" in page, page.decode()[:3000]
            c.post(f"/upload/batch/{bid}/commit", data={"_csrf": "t"})
        assert Vendor.query.count() == 5 and Challan.query.count() == 5
        assert Challan.query.filter_by(status="CANCELLED").count() == 1
        mrc2 = Challan.query.filter_by(number="MRC/25-26/0002").one()
        assert mrc2.return_status == "Partially Received" and len(mrc2.lines) == 2
        db.session.remove(); db.engine.dispose()
