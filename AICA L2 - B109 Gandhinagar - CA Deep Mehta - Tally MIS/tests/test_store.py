"""Phase 2 tests: the in-memory model loads correctly, is replaceable, and leaves nothing behind."""
import os
import tempfile
from pathlib import Path

import pytest

from app.model.store import Store
from app.sync import Runs, import_files

DATA = Path(__file__).parent / "data"  # fictional demo books (generated), never real data
MASTERS, APR, MAY = (str(DATA / n) for n in ("masters.xml", "daybook-2024-04.xml", "daybook-2024-05.xml"))


@pytest.fixture()
def loaded():
    store = Store()
    cid = store.ensure_company("Demo Trading Co (Sample Data)")
    runs = Runs()
    for f in (MASTERS, APR):
        run = import_files(store, runs.new(company_id=cid, mode="file"), cid, [f])
        assert run.status == "succeeded", run.error
    yield store, cid, runs
    store.wipe()


def test_loads_and_balances(loaded):
    store, cid, _ = loaded
    c = store.counts()
    assert c["ledgers"] == 87 and c["vouchers"] > 50 and c["voucher_lines"] > c["vouchers"]
    assert store.scalar("SELECT SUM(amount_paise) FROM voucher_lines") == 0          # double entry: debits = credits
    assert store.scalar("SELECT COUNT(*) FROM vouchers WHERE base_type = 'Unknown'") == 0
    assert store.scalar("SELECT COUNT(*) FROM ledgers WHERE group_id IS NULL AND group_name IS NOT NULL") == 0


def test_reloading_a_month_does_not_duplicate(loaded):
    store, cid, runs = loaded
    before = store.counts()
    run = import_files(store, runs.new(company_id=cid, mode="file"), cid, [APR], replace_range=True)
    assert run.status == "succeeded"
    after = store.counts()
    assert after["vouchers"] == before["vouchers"] and after["voucher_lines"] == before["voucher_lines"]
    assert after["ledgers"] == before["ledgers"]


def test_a_second_month_adds_to_the_first(loaded):
    store, cid, runs = loaded
    n = store.counts()["vouchers"]
    import_files(store, runs.new(company_id=cid, mode="file"), cid, [MAY])
    assert store.counts()["vouchers"] > n
    assert store.scalar("SELECT COUNT(DISTINCT SUBSTR(date,1,7)) FROM vouchers") == 2


def test_cancelled_import_writes_nothing():
    store = Store()
    cid = store.ensure_company("X")
    run = Runs().new(company_id=cid, mode="file")
    run.cancel.set()
    import_files(store, run, cid, [MASTERS])
    assert run.status == "cancelled" and store.counts()["ledgers"] == 0
    store.wipe()


def test_broken_file_leaves_existing_data_alone(loaded, tmp_path):
    store, cid, runs = loaded
    bad = tmp_path / "bad.xml"
    bad.write_text("<ENVELOPE><VOUCHER><DATE>20240401</DATE></ENVELOPE>")
    before = store.counts()
    run = import_files(store, runs.new(company_id=cid, mode="file"), cid, [str(bad)])
    assert run.status == "failed" and store.counts() == before


def test_wipe_removes_everything(loaded):
    store, _, _ = loaded
    assert store.counts()["vouchers"] > 0
    store.wipe()
    assert store.closed
    with pytest.raises(Exception):
        store.counts()
    store.reset()                      # a fresh, empty database can start again
    assert sum(store.counts().values()) == 0
    store.wipe()


def test_nothing_is_written_to_disk():
    watched = {Path.cwd(), Path(tempfile.gettempdir())}
    def snapshot():
        return {(p, e.name) for p in watched for e in os.scandir(p)}
    before = snapshot()
    store = Store()
    assert store.scalar("SELECT current_setting('temp_directory')") in ("", None)
    cid = store.ensure_company("Demo")
    for f in (MASTERS, APR, MAY):
        assert import_files(store, Runs().new(company_id=cid, mode="file"), cid, [f]).status == "succeeded"
    # the database itself is in memory, and SQL cannot be used to write a file
    assert store.rows("PRAGMA database_list")[0]["file"] in (None, "")
    with pytest.raises(Exception):
        store.execute(f"COPY (SELECT 1) TO '{(Path(tempfile.gettempdir()) / 'leak.csv').as_posix()}'")
    store.wipe()
    new = {n for _, n in snapshot() - before}
    leaked = {n for n in new if n.endswith((".wal", ".duckdb", ".tmp", ".csv", ".parquet")) or n.startswith((".tmp", "duckdb"))}
    assert not leaked, leaked
