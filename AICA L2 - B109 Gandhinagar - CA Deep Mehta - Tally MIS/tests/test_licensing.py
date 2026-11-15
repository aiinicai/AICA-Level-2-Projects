"""Licensing: genuine keys work, forged / expired / wrong-PC keys do not, and evaluation mode limits real data."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import licensing as L
from app.api.server import AppState, create_app
from app.assistant.service import Assistant

H = {"X-Requested-With": "mis"}
SECRET = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")  # RFC 8032 test key
PUB = L.public_key_from_secret(SECRET).hex()
DATA = Path(__file__).parent / "data"


def test_ed25519_matches_the_rfc_test_vector():
    assert PUB == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    sig = L.sign(SECRET, b"")
    assert sig.hex() == ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46b"
                         "d25bf5f0595bbe24655141438e7a100b")
    assert L.verify(bytes.fromhex(PUB), b"", sig) and not L.verify(bytes.fromhex(PUB), b"x", sig)


def key(**kw):
    return L.make_key(SECRET, licensee="Test User", **kw)


def test_genuine_key_for_this_pc_is_accepted():
    lic = L.check_key(key(machine=L.machine_id()), public_hex=PUB)
    assert lic.licensed and lic.licensee == "Test User"


def test_any_pc_key_with_future_expiry_is_accepted():
    assert L.check_key(key(expires=(date.today() + timedelta(days=5)).isoformat()), public_hex=PUB).licensed


def test_expired_key_is_refused():
    lic = L.check_key(key(expires=(date.today() - timedelta(days=1)).isoformat()), public_hex=PUB)
    assert lic.status == "expired"


def test_key_for_another_pc_is_refused():
    assert L.check_key(key(machine="AAAA-BBBB-CCCC-DDDD"), public_hex=PUB).status == "wrong_machine"


def test_forged_or_edited_keys_are_refused():
    good = key()
    body, sig = good.split(".")
    assert L.check_key(good, public_hex="00" * 32).status == "invalid"  # signed by someone else
    other = L.make_key(bytes(range(32)), licensee="Thief")  # a different private key
    assert L.check_key(other, public_hex=PUB).status == "invalid"
    # change the licensee, keep the old signature
    forged = L.make_key(SECRET, licensee="Someone Else").split(".")[0] + "." + sig
    assert L.check_key(forged, public_hex=PUB).status == "invalid"
    assert L.check_key("not a key", public_hex=PUB).status == "invalid"


def test_manager_saves_and_removes_the_key(tmp_path):
    m = L.LicenceManager(tmp_path / "licence.key", public_hex=PUB)
    assert m.current.status == "evaluation"
    assert m.activate("junk").status == "invalid" and m.current.status == "evaluation"
    assert m.activate(key()).licensed and L.LicenceManager(tmp_path / "licence.key", public_hex=PUB).current.licensed  # survives restart
    assert m.remove().status == "evaluation"


def test_evaluation_limits(tmp_path):
    m = L.LicenceManager(tmp_path / "x.key", public_hex=PUB)
    assert m.check_sync(3, 1) is None and "3 months" in m.check_sync(4, 1)
    assert m.check_sync(1, 2) is not None  # a second real company
    assert m.check_import(1024, 1) is None and "3 MB" in m.check_import(4 * 1024 * 1024, 1)
    m.activate(key(companies=2))
    assert m.check_sync(60, 2) is None and m.check_sync(1, 3) is not None


@pytest.fixture()
def client(tmp_path):
    state = AppState(assistant=Assistant(persist=False), licence=L.LicenceManager(tmp_path / "licence.key", public_hex=PUB))
    with TestClient(create_app(state)) as c:
        c.state = state
        yield c
    state.store.wipe()


def upload(c, name, **params):
    return c.post("/api/import/xml", params={"filename": name, **params}, content=(DATA / name).read_bytes(),
                  headers={**H, "Content-Type": "application/xml"})


def test_api_status_activation_and_limits(client):
    s = client.get("/api/licence").json()
    assert s["status"] == "evaluation" and s["machineId"] == L.machine_id() and s["evaluationLimits"]["monthsPerSync"] == 3
    assert upload(client, "masters.xml", newCompany="First Co").status_code == 200
    assert upload(client, "masters.xml", newCompany="Second Co").status_code == 402  # evaluation: one real company
    assert client.post("/api/demo/load", headers=H).status_code == 200  # the demo company is never limited
    assert client.post("/api/licence", json={"key": "nope"}, headers=H).status_code == 400
    r = client.post("/api/licence", json={"key": key(companies=5)}, headers=H)
    assert r.status_code == 200 and r.json()["status"] == "licensed" and r.json()["licensee"] == "Test User"
    assert upload(client, "masters.xml", newCompany="Second Co").status_code == 200
    assert client.delete("/api/licence", headers=H).json()["status"] == "evaluation"
    assert client.post("/api/licence", json={"key": key()}).status_code == 403  # needs the app header


def test_tally_sync_is_limited_to_three_months_in_evaluation(client):
    months = ["2025-04-01", "2025-05-01", "2025-06-01", "2025-07-01"]
    r = client.post("/api/tally/sync", json={"company": "X", "port": 9000, "months": months}, headers=H)
    assert r.status_code == 402 and "3 months" in r.json()["error"]
