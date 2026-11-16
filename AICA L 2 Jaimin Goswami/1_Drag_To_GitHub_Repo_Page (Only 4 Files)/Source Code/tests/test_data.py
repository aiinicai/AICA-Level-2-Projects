import json
import pytest

from app.database.events import EventRepository
from app.database.store import Database
from app.services.ingestion import IngestionService
from app.services.validation import ValidationError,validate_event
from app.utils.time import display_time,local_date,normalize_time


def test_json_csv_import_and_persistence(db,record,tmp_path):
    service=IngestionService(db)
    path=tmp_path/"events.json"; path.write_text(json.dumps([record]),encoding="utf-8")
    assert service.import_file(path).inserted==1
    import pandas as pd
    pd.DataFrame([record]).to_csv(tmp_path/"events.csv",index=False)
    assert service.import_file(tmp_path/"events.csv").duplicates==1
    reopened=Database(db.path)
    assert len(EventRepository(reopened).search()[0])==1


@pytest.mark.parametrize("missing",[None,"","NaN","null","N/A"])
def test_missing_values_never_zero(record,missing):
    event=validate_event(dict(record,forecast=missing,actual=missing),"fixture")
    assert event.forecast is None and event.actual is None
    assert event.previous=="4.2"
    assert validate_event(dict(record,actual=0),"fixture").actual=="0"


def test_required_fields_and_live_provenance(record):
    with pytest.raises(ValidationError):validate_event(dict(record,title=""),"fixture")
    with pytest.raises(ValidationError):validate_event(dict(record,sample=False),"fixture")
    with pytest.raises(ValidationError):validate_event(dict(record,source_url="javascript:alert(1)"),"fixture")


def test_sample_flag_csv_false(record):
    event=validate_event(dict(record,sample="false",source_url="https://example.org/release"),"fixture")
    assert event.sample is False


def test_duplicate_revision_and_values(db,record):
    ingest=IngestionService(db)
    assert ingest.import_records([record],"fixture").inserted==1
    assert ingest.import_records([record],"fixture").duplicates==1
    changed=dict(record,actual="4.3",forecast="4.1",status="Published",published_at="2026-11-13T12:00:10Z")
    assert ingest.import_records([changed],"fixture").updated==1
    repo=EventRepository(db); event=repo.search()[0][0]
    assert (event["previous"],event["forecast"],event["actual"])==("4.2","4.1","4.3")
    revisions=repo.revisions(event["id"])
    assert len(revisions)==2
    assert json.loads(revisions[-1]["payload"])["actual"] is None
    assert len(db.rows("SELECT * FROM economic_observations"))==10


def test_import_errors_are_logged(db,record):
    result=IngestionService(db).import_records([record,dict(record,title="")],"fixture")
    assert result.inserted==1 and result.rejected==1
    assert db.rows("SELECT * FROM ingestion_errors")[0]["row_number"]==2


def test_date_only_and_milestones(db,record):
    row=dict(record,scheduled_at="2026-11-14",published_at="2026-11-12",effective_at="2026-12-01",deadline_at="2026-12-31")
    assert IngestionService(db).import_records([row],"fixture").inserted==1
    event=EventRepository(db).search()[0][0]
    assert event["scheduled_at"]=="2026-11-14"
    assert local_date(event["effective_at"],"America/New_York")=="2026-12-01"
    assert len(EventRepository(db).search(start="2026-12-01",end="2026-12-01",date_basis="effective_at")[0])==1


@pytest.mark.parametrize("value,zone,expected",[
 ("2026-01-15T08:30:00-05:00","Asia/Kolkata","19:00"),
 ("2026-07-15T08:30:00-04:00","Asia/Kolkata","18:00"),
 ("2026-01-15T13:30:00Z","Australia/Sydney","00:30"),
 ("2026-07-15T12:30:00Z","Australia/Sydney","22:30"),
 ("2026-01-15T13:30:00Z","Australia/Perth","21:30"),
 ("2026-07-15T12:30:00Z","Europe/London","13:30"),
])
def test_worldwide_timezone(value,zone,expected):
    assert expected in display_time(normalize_time(value),zone)


def test_dst_ambiguity_and_midnight(record):
    with pytest.raises(ValueError):normalize_time("2026-11-01T01:30:00","America/New_York")
    with pytest.raises(ValueError):normalize_time("2026-03-08T02:30:00","America/New_York")
    with pytest.raises(ValueError):normalize_time("2026-01-01T12:30:00")
    assert local_date("2026-01-15T13:30:00Z","Australia/Sydney")=="2026-01-16"


def test_estimated_date_is_not_confirmed(record):
    event=validate_event(dict(record,date_confirmed=False),"fixture")
    assert event.status=="Tentative"


def test_search_filters_literal_wildcards(db,record):
    IngestionService(db).import_records([record,dict(record,external_id="2",country="Japan",importance="High",title="Sample GDP 100%")],"fixture")
    repo=EventRepository(db)
    assert len(repo.search(filters={"country":"Japan","importance":"High"})[0])==1
    assert len(repo.search(query="100%")[0])==1
    assert len(repo.search(query="not found")[0])==0
    assert len(repo.search(filters={"sample":False})[0])==0


def test_cross_exchange_strong_duplicate_and_candidates(db,record):
    corp=dict(record,kind="Corporate",company="Sample Ltd",isin="SAMPLE123",symbol="SAMPLE",exchange="NSE",title="Quarterly results",category="Financial results",document_hash="a"*64)
    service=IngestionService(db)
    service.import_records([corp],"nse-test")
    result=service.import_records([dict(corp,external_id="bse-1",exchange="BSE")],"bse-test")
    assert result.duplicates==1
    repo=EventRepository(db); events=repo.search()[0]
    assert len(events)==1 and len(repo.sources(events[0]["id"]))==2
    distinct=dict(corp,external_id="different",document_hash="b"*64)
    assert service.import_records([distinct],"bse-test").inserted==1
    assert len(repo.search()[0])==2
    assert len(db.rows("SELECT * FROM duplicate_candidates"))==1


def test_history_separates_sample_and_source(db,record):
    service=IngestionService(db)
    service.import_records([dict(record,status="Published",actual="4.1")],"fixture")
    service.import_records([dict(record,status="Published",actual="9.9",sample=False,source_url="https://example.org/release")],"source")
    repo=EventRepository(db); sample=repo.search(filters={"sample":True})[0][0]
    assert len(repo.history(sample))==1
    assert repo.history(sample)[0]["value_text"]=="4.1"


def test_backup_integrity(db,record,tmp_path):
    IngestionService(db).import_records([record],"fixture")
    target=tmp_path/"backup.db"; db.backup(target)
    assert Database(target).rows("SELECT count(*) AS n FROM events")[0]["n"]==1
    assert db.rows("PRAGMA integrity_check")[0]["integrity_check"]=="ok"


def test_source_update_timestamp_alone_is_not_material(db,record):
    service=IngestionService(db)
    service.import_records([dict(record,source_updated_at="2026-11-13T09:00:00Z")],"fixture")
    assert service.import_records([dict(record,source_updated_at="2026-11-13T10:00:00Z")],"fixture").duplicates==1


def test_chart_units_are_not_silently_combined(db,record):
    service=IngestionService(db)
    service.import_records([dict(record,actual="4.3%",status="Published"),dict(record,external_id="index-level",actual="143",unit="index",status="Published")],"fixture")
    repo=EventRepository(db)
    event=next(e for e in repo.search()[0] if e["external_id"]=="fixture-1")
    history=repo.history(event)
    assert len(history)==1 and history[0]["value_decimal"]=="4.3"

