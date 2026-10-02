from fastapi.testclient import TestClient

from app.config.settings import APPLICATION_NAME, APPLICATION_VERSION, Settings
from app.main import create_app
from app.repositories.memory import InMemoryRepository


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_health():
    r = make_client().get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["application"] == APPLICATION_NAME
    assert body["version"] == APPLICATION_VERSION


def test_version():
    r = make_client().get("/version")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == APPLICATION_VERSION
    assert body["api_version"] == "v1"
    assert "min_local_version" in body
    assert body["features"]["ai_invoice_extraction"] is False


def test_version_never_leaks_secrets():
    settings = Settings(_env_file=None, ai_api_key="sk-should-not-leak", mongodb_uri="mongodb://u:p@h/db")
    client = TestClient(create_app(settings))
    text = client.get("/version").text + client.get("/health").text
    assert "sk-should-not-leak" not in text
    assert "mongodb://" not in text


def test_future_modules_are_placeholders():
    client = make_client()
    for module in ("auth", "ai", "users", "clients", "settings"):
        r = client.get(f"/api/v1/{module}")
        assert r.status_code == 200
        assert r.json()["enabled"] is False


def test_in_memory_repository():
    repo = InMemoryRepository()
    repo.upsert("c1", {"name": "ABC Traders", "state": "Maharashtra"})
    assert repo.get("c1")["name"] == "ABC Traders"
    assert len(repo.list({"state": "Maharashtra"})) == 1
    assert repo.delete("c1") is True
    assert repo.get("c1") is None
