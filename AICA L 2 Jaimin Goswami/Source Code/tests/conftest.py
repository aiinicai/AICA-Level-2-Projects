from datetime import datetime,timezone
import pytest
from app.database.store import Database
from app.services.bootstrap import initialize


@pytest.fixture
def db(tmp_path):
    database=Database(tmp_path/"events.db")
    initialize(database)
    return database


@pytest.fixture
def record():
    return dict(external_id="fixture-1",kind="Economic",title="Sample CPI",category="Inflation",country="India",authority="Fixture authority",sample=True,status="Scheduled",scheduled_at="2026-11-13T12:00:00+00:00",indicator="CPI",series_key="TEST:IN:CPI",reporting_period="Oct 2026",previous="4.2",forecast=None,actual=None,unit="%",importance="Low")


@pytest.fixture
def clock():
    class Clock:
        now=datetime(2026,11,13,11,0,tzinfo=timezone.utc)
        def __call__(self):return self.now
    return Clock()

