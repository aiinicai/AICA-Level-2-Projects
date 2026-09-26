import os
import tempfile
from datetime import date
from pathlib import Path

# Keep the module-level ``app`` in app.main away from the real data folder.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="brmco-test-"))

import pytest  # noqa: E402

from app.accounting.models import VoucherKind  # noqa: E402
from app.config.settings import AppConfig, EnvSettings  # noqa: E402
from app.excel.generator import TemplateLists, build_template  # noqa: E402
from app.excel.samples import SAMPLE_ROWS  # noqa: E402
from app.excel.template_spec import spec_for  # noqa: E402
from app.tally.client import DEMO_MASTERS  # noqa: E402
from app.tally.masters import CachedMasters  # noqa: E402

TODAY = date(2026, 10, 15)


class NoHistory:
    def __init__(self, exact=None, fuzzy=None):
        self.exact = exact or {}
        self.fuzzy = fuzzy or {}

    def find_exact(self, company, keys):
        return {k: self.exact[k] for k in keys if k in self.exact}

    def find_fuzzy(self, company, keys):
        return {k: self.fuzzy[k] for k in keys if k in self.fuzzy}


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(company_name="Test Co", company_state="Maharashtra", financial_year="2026-27",
                     demo_mode=True)


@pytest.fixture
def masters() -> CachedMasters:
    return CachedMasters.from_records(DEMO_MASTERS)


def workbook(kind: VoucherKind, rows=None) -> bytes:
    return build_template(spec_for(kind), TemplateLists(), sample_rows=SAMPLE_ROWS[kind] if rows is None else rows)


@pytest.fixture
def env(tmp_path: Path) -> EnvSettings:
    return EnvSettings(_env_file=None, data_dir=tmp_path, demo_mode=True)


@pytest.fixture
def client(env):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(env)
    c = TestClient(app)
    r = c.put("/api/settings", json={"company_name": "Test Co", "company_state": "Maharashtra",
                                     "financial_year": "2026-27", "demo_mode": True})
    assert r.status_code == 200, r.text
    return c
