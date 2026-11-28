import pytest

from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.services.auth_service import AuthService
from ipt.services.company_service import CompanyService


@pytest.fixture
def db(tmp_path):
    d = Database.for_file(tmp_path / "test.db")
    d.create_schema()
    return d


@pytest.fixture
def admin(db):
    return AuthService(db).create_user("admin", "admin12345", "admin", "Admin")


@pytest.fixture
def companies(db, tmp_path):
    return CompanyService(db, tmp_path / "data")


@pytest.fixture
def services(db, admin, tmp_path):
    """Services with an active company (Rajasthan, GSTIN set) and FY 2025-26."""
    from ipt.services.company_service import CompanyInput
    from ipt.ui.services import Services
    from tests.pdfgen import gst
    s = Services.build(db, tmp_path / "data")
    s.ctx.user = admin
    c = s.companies.create_company(CompanyInput(name="ABC Enterprises", state_code="08",
                                                gstin=gst("08AAACA1111A1Z")), admin)
    fy = s.companies.create_fy(c.id, 2025, admin)
    s.ctx.company_id, s.ctx.fy_id = c.id, fy.id
    s.company_gstin = c.gstin
    return s


@pytest.fixture(scope="session", autouse=True)
def _qt_clean_exit():
    """Let background jobs finish and delete Qt widgets before Python shuts down (avoids a crash at exit)."""
    yield
    try:
        import gc

        from PySide6.QtCore import QThreadPool
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return
    QThreadPool.globalInstance().waitForDone(5000)
    app = QApplication.instance()
    if app is not None:
        for w in app.topLevelWidgets():
            w.deleteLater()
        app.processEvents()
    gc.collect()
