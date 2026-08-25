from pathlib import Path

from app.services.client_backup import backup_client_zip, restore_client_from_zip
from app.services.client_runtime import prepare_client_database
from app.services.client_store import add_client, client_db_path, delete_client, list_clients, update_client


def test_create_backup_and_restore_client(tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    first = add_client("Alpha Kitchen")
    prepare_client_database(first, include_samples=False, include_demo_branches=False)
    assert client_db_path(first).exists()

    zip_path = tmp_path / "alpha.zip"
    backup_client_zip(first, zip_path)
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0

    restored = restore_client_from_zip(zip_path.open("rb"), "alpha.zip")
    prepare_client_database(restored, include_samples=False, include_demo_branches=False)
    assert restored["name"] == "Alpha Kitchen"
    assert restored["id"] != first["id"]
    assert client_db_path(restored).exists()
    assert len(list_clients()) == 2


def test_restore_rejects_plain_zip(tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    import zipfile
    junk = tmp_path / "junk.zip"
    with zipfile.ZipFile(junk, "w") as zf:
        zf.writestr("notes.txt", "not a backup")
    try:
        restore_client_from_zip(junk.open("rb"), "junk.zip")
        assert False, "should have rejected the zip"
    except ValueError as exc:
        assert "backup" in str(exc).lower()


def test_clients_api_create_backup_restore(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    from app.seed import seed_database
    seed_database(db_session)
    login = client.post("/api/auth/login", json={"email": "admin", "password": "admin"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get("/api/clients")
    assert listed.status_code == 200

    created = client.post(
        "/api/clients/create",
        json={"name": "Beta Foods", "address": "Noida", "gstin": "09AABCU9603R1ZM"},
        headers=headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "Beta Foods"
    assert Path(tmp_path, "Beta Foods", "restaurant_reconcile.db").exists()

    backup = client.get(f"/api/clients/{body['id']}/backup", headers=headers)
    assert backup.status_code == 200
    assert backup.headers["content-type"].startswith("application/zip")

    restore = client.post(
        "/api/clients/restore",
        headers=headers,
        files={"file": ("beta.zip", backup.content, "application/zip")},
    )
    assert restore.status_code == 200
    assert restore.json()["name"] == "Beta Foods"
    assert restore.json()["gstin"] == "09AABCU9603R1ZM"
    assert len(client.get("/api/clients").json()["clients"]) >= 2

    page = client.get("/clients", headers=headers)
    assert page.status_code == 200
    assert b"Client Database" in page.content or b"GSTIN" in page.content

    first = add_client("Keep Me")
    extra = add_client("Remove Me", address="Delhi", gstin="07AABCU9603R1Z1")
    saved = update_client(extra["id"], name="Remove Me Pvt", address="South Delhi", gstin="07AABCU9603R1Z1")
    assert saved["address"] == "South Delhi"
    deleted = delete_client(extra["id"])
    assert deleted["deleted_id"] == extra["id"]
    assert first["id"] in [item["id"] for item in list_clients()]


def test_client_folder_uses_client_name(tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    client = add_client("Cafe Mocha")
    folder = Path(tmp_path, "Cafe Mocha")
    assert folder.is_dir()
    assert (folder / "restaurant_reconcile.db").parent == folder
    saved = update_client(client["id"], name="Cafe Mocha Pvt")
    renamed = Path(tmp_path, "Cafe Mocha Pvt")
    assert saved["folder"] == "Cafe Mocha Pvt"
    assert renamed.is_dir()
    assert not folder.exists()


def test_clients_keep_separate_databases(tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    import shutil

    from sqlalchemy.orm import sessionmaker

    from app.core.database import dispose_sqlite_engine, engine_for_sqlite
    from app.models.branch import Branch
    from app.services.client_runtime import isolate_cloned_client_databases, prepare_client_database
    from app.services.client_store import add_client, client_db_path, delete_client

    kitchen_a = add_client("Kitchen A")
    kitchen_b = add_client("Kitchen B")
    prepare_client_database(kitchen_a, include_samples=False, include_demo_branches=False)
    prepare_client_database(kitchen_b, include_samples=False, include_demo_branches=False)
    path_a = client_db_path(kitchen_a)
    path_b = client_db_path(kitchen_b)
    assert path_a.resolve() != path_b.resolve()

    session_a = sessionmaker(autocommit=False, autoflush=False, bind=engine_for_sqlite(path_a))()
    session_a.add(Branch(
        code="ONLYA",
        name="Only A Branch",
        address="A",
        opening_cash_balance=1,
        is_base_kitchen=False,
        is_active=True,
    ))
    session_a.commit()
    session_a.close()

    session_b = sessionmaker(autocommit=False, autoflush=False, bind=engine_for_sqlite(path_b))()
    assert session_b.query(Branch).filter(Branch.code == "ONLYA").count() == 0
    session_b.close()

    dispose_sqlite_engine(path_b)
    shutil.copy2(path_a, path_b)
    isolate_cloned_client_databases()

    session_b = sessionmaker(autocommit=False, autoflush=False, bind=engine_for_sqlite(path_b))()
    assert session_b.query(Branch).filter(Branch.code == "ONLYA").count() == 0
    session_b.close()

    session_a = sessionmaker(autocommit=False, autoflush=False, bind=engine_for_sqlite(path_a))()
    assert session_a.query(Branch).filter(Branch.code == "ONLYA").count() == 1
    session_a.close()

    deleted = delete_client(kitchen_b["id"])
    assert deleted["deleted_id"] == kitchen_b["id"]
    assert path_a.exists()
    assert not path_b.exists()
