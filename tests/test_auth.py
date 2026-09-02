import pytest
from app.seed import seed_database
from app.core.security import verify_password, get_password_hash

def test_password_hashing():
    pwd = "secretpassword123"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpwd", hashed) is False

def test_login_api(client, db_session):
    seed_database(db=db_session)
    response = client.post("/api/auth/login", json={"email": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin"
