import json

import pytest

from advtax import storage


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("ADVTAX_DATA_DIR", str(tmp_path))
    return storage.connect()


def test_database_is_created_in_the_data_folder(con, tmp_path):
    assert storage.db_path() == tmp_path / "advance_tax.db" and storage.db_path().exists()


def test_client_save_update_and_list(con):
    storage.save_client(con, "B Client", {"name": "B Client", "business_income": 1}, {"mode": "x"})
    storage.save_client(con, "a client", {"name": "a client"}, {})
    storage.save_client(con, "B Client", {"name": "B Client", "business_income": 2}, {"mode": "y"})
    assert [c["name"] for c in storage.list_clients(con)] == ["a client", "B Client"]
    rec = storage.get_client(con, "B Client")
    assert rec["inputs"]["business_income"] == 2 and rec["working"]["mode"] == "y"


def test_trial_balance_file_and_ledgers_round_trip(con):
    ledgers = [{"ledger": "Sales", "group": "Sales Accounts", "net": -5000.0, "type": "Income",
                "review": False, "one_off": False}]
    storage.save_trial_balance(con, "C", "tb.xlsx", b"\x00\x01binary", {"sheet": 0, "header_row": 5}, ledgers)
    tb = storage.get_trial_balance(con, "C")
    assert tb["data"] == b"\x00\x01binary" and tb["filename"] == "tb.xlsx"
    assert tb["ledgers"] == ledgers and tb["meta"]["header_row"] == 5
    storage.save_trial_balance(con, "C", "tb2.csv", b"new", {}, [])
    assert storage.get_trial_balance(con, "C")["filename"] == "tb2.csv"
    assert storage.counts(con)["trial_balances"] == 1


def test_every_save_adds_a_history_row_newest_first(con):
    first = storage.save_estimate(con, "C", "2026-09-10", {"a": 1}, {}, {"total_tax": 100}, "msg1", "why1")
    second = storage.save_estimate(con, "C", "2026-11-22", {"a": 2}, {}, {"total_tax": 200}, "msg2")
    storage.save_estimate(con, "Other", "2026-11-22", {}, {}, {})
    hist = storage.list_estimates(con, "C")
    assert [h["id"] for h in hist] == [second, first]
    assert hist[0]["summary"]["total_tax"] == 200 and hist[1]["message"] == "msg1"
    assert storage.get_estimate(con, first)["explanation"] == "why1"


def test_delete_removes_client_trial_balance_and_history(con):
    storage.save_client(con, "C", {"name": "C"}, {})
    storage.save_trial_balance(con, "C", "tb.xlsx", b"x", {}, [])
    storage.save_estimate(con, "C", "2026-11-22", {}, {}, {})
    storage.delete_client(con, "C")
    assert storage.counts(con) == {"clients": 0, "trial_balances": 0, "estimates": 0}


def test_choosing_another_folder_is_remembered(tmp_path, monkeypatch):
    monkeypatch.delenv("ADVTAX_DATA_DIR", raising=False)
    monkeypatch.setattr(storage, "SETTINGS_PATH", tmp_path / "settings.json")
    assert storage.data_dir() == storage.DEFAULT_DIR
    target = tmp_path / "Office Drive" / "AdvanceTax"
    assert storage.set_data_dir(str(target)) == target and target.is_dir()
    assert json.loads((tmp_path / "settings.json").read_text())["data_dir"] == str(target)
    assert storage.db_path() == target / "advance_tax.db"
    storage.save_client(storage.connect(), "Z", {"name": "Z"}, {})
    assert (target / "advance_tax.db").exists()
    storage.reset_data_dir()
    assert storage.data_dir() == storage.DEFAULT_DIR


def test_relative_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "SETTINGS_PATH", tmp_path / "settings.json")
    with pytest.raises(ValueError):
        storage.set_data_dir("some/relative/folder")
