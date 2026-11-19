from datetime import timedelta
import pytest

from app.notifications.engine import NotificationEngine
from app.services.ingestion import IngestionService


class Sink:
    def __init__(self):self.jobs=[]
    def send(self,job):self.jobs.append(job)


def setup(db,record,clock,filters=None,include_samples=True):
    engine=NotificationEngine(db,clock)
    engine.save_rule("Test rule",filters or {},[900,3600],["reminder","new","updated"],include_samples=include_samples)
    ingest=IngestionService(db,engine)
    ingest.import_records([record],"fixture")
    return engine,ingest


def test_reminders_offsets_and_duplicates(db,record,clock):
    engine,ingest=setup(db,record,clock)
    sink=Sink()
    assert engine.dispatch(sink)==1
    assert engine.dispatch(sink)==0
    ingest.import_records([record],"fixture")
    engine.reconcile()
    assert engine.dispatch(sink)==0
    clock.now+=timedelta(minutes=45)
    assert engine.dispatch(sink)==1
    assert len(sink.jobs)==2


@pytest.mark.parametrize("filters",[{"countries":["Japan"]},{"companies":["UNKNOWN"]},{"categories":["GDP"]},{"authorities":["Other"]},{"importance":["High"]},{"kinds":["Corporate"]}])
def test_notification_preferences(db,record,clock,filters):
    engine,_=setup(db,record,clock,filters)
    assert engine.dispatch(Sink())==0
    assert not engine.history()


def test_sample_opt_in(db,record,clock):
    engine,_=setup(db,record,clock,include_samples=False)
    assert not engine.history()


def test_unscheduled_new_and_update(db,record,clock):
    engine,_=setup(db,record,clock)
    published=dict(record,external_id="unscheduled",scheduled_at=None,published_at="2026-11-13T10:59:00Z",kind="Regulatory",status="Published")
    ingest=IngestionService(db,engine)
    ingest.import_records([published],"fixture",mode="live")
    ingest.import_records([published],"fixture",mode="live")
    jobs=[j for j in engine.history() if j["trigger"]=="new"]
    assert len(jobs)==1
    ingest.import_records([dict(published,title="Material correction")],"fixture",mode="live")
    assert len([j for j in engine.history() if j["trigger"]=="updated"])==1


def test_backfill_never_alerts(db,record,clock):
    engine,_=setup(db,record,clock)
    published=dict(record,external_id="old",scheduled_at=None,published_at="2025-01-01",status="Published")
    IngestionService(db,engine).import_records([published],"fixture",mode="backfill")
    assert not [j for j in engine.history() if j["trigger"]=="new"]


def test_reschedule_and_cancel(db,record,clock):
    engine,ingest=setup(db,record,clock)
    ingest.import_records([dict(record,scheduled_at="2026-11-13T14:00:00Z")],"fixture")
    assert len([j for j in engine.history() if j["state"]=="Cancelled"])==2
    assert len([j for j in engine.history() if j["state"]=="Pending"])==2
    ingest.import_records([dict(record,status="Cancelled",scheduled_at="2026-11-13T14:00:00Z")],"fixture")
    assert not [j for j in engine.history() if j["state"]=="Pending"]


def test_no_exact_reminder_date_only(db,record,clock):
    engine,_=setup(db,dict(record,scheduled_at="2026-11-14"),clock)
    assert not engine.history()


def test_restart_recovery_and_missed_reminders(db,record,clock):
    engine,_=setup(db,record,clock)
    job=engine.history()[0]
    db.execute("UPDATE notification_jobs SET state='Dispatching' WHERE id=?",(job["id"],))
    reopened=NotificationEngine(db,clock); reopened.recover()
    assert any(j["state"]=="Uncertain" for j in reopened.history())
    clock.now+=timedelta(hours=3)
    assert reopened.dispatch(Sink())==0
    assert any(j["state"]=="Expired" for j in reopened.history())


def test_multiple_matching_rules_one_alert(db,record,clock):
    engine,_=setup(db,record,clock)
    engine.save_rule("Overlap",{},[3600],["reminder"],include_samples=True)
    assert engine.dispatch(Sink())==1


def test_watchlist_matches_and_disabling_rule(db,record,clock):
    record=dict(record,kind="Corporate",company="Example",symbol="TEST")
    db.execute("INSERT INTO watchlist_members VALUES('default','TEST')")
    engine,_=setup(db,record,clock,{"watchlists":["default"]})
    assert len(engine.history())==2
    db.execute("UPDATE notification_rules SET enabled=0")
    engine.reconcile()
    assert engine.dispatch(Sink())==0


def test_delivery_failure_retained(db,record,clock):
    class FailingSink:
        def send(self,job):raise RuntimeError("Desktop unavailable")
    engine,_=setup(db,record,clock)
    engine.dispatch(FailingSink())
    assert any(j["state"]=="Failed" and "Desktop unavailable" in j["last_error"] for j in engine.history())
