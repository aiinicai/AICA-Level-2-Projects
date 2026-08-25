from datetime import date

from app.models.branch import Branch
from app.models.daily_sales import DailySale
from app.models.payment_channel import PaymentChannel
from app.models.user import Role, User
from app.seed import seed_database
from app.services.permission_service import default_permissions, user_can


def _auth(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _cash_payload(branch_id, rec_date="2099-08-23"):
    return {
        "branch_id": branch_id,
        "rec_date": rec_date,
        "site_expenses_inv_rec": 100,
        "actual_closing_balance": 500,
    }


def test_admin_always_has_full_rights(db_session):
    seed_database(db=db_session)
    admin = db_session.query(User).filter(User.email == "admin").first()
    for module in ("daybook", "cash_rec", "card_qr", "aggregators", "attendance", "reports", "gst_report"):
        assert user_can(admin, module, "view")
        assert user_can(admin, module, "enter")
        assert user_can(admin, module, "edit_saved")


def test_viewer_cannot_enter_by_default(db_session):
    seed_database(db=db_session)
    viewer = db_session.query(User).filter(User.email == "viewer@restaurant.com").first()
    assert user_can(viewer, "cash_rec", "view")
    assert user_can(viewer, "cash_rec", "enter") is False
    assert user_can(viewer, "daybook", "edit_saved") is False


def test_branch_user_can_enter_but_not_edit_saved(db_session):
    seed_database(db=db_session)
    staff = db_session.query(User).filter(User.email == "noida").first()
    assert user_can(staff, "daybook", "enter")
    assert user_can(staff, "cash_rec", "enter")
    assert user_can(staff, "attendance", "enter")
    assert user_can(staff, "cash_rec", "edit_saved") is False
    assert user_can(staff, "card_qr", "enter") is False


def test_custom_permissions_override_role(db_session):
    seed_database(db=db_session)
    viewer = db_session.query(User).filter(User.email == "viewer@restaurant.com").first()
    perms = default_permissions("Viewer")
    perms["cash_rec"] = {"view": True, "enter": True, "edit_saved": False}
    viewer.permissions = perms
    db_session.commit()
    db_session.refresh(viewer)
    assert user_can(viewer, "cash_rec", "enter")
    assert user_can(viewer, "cash_rec", "edit_saved") is False
    assert user_can(viewer, "daybook", "enter") is False


def test_viewer_cannot_post_cash(client, db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).first()
    headers = _auth(client, "viewer@restaurant.com", "viewer123")
    response = client.post("/api/cash-rec", json=_cash_payload(branch.id), headers=headers)
    assert response.status_code == 403


def test_branch_user_cannot_edit_saved_cash(client, db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).first()
    headers = _auth(client, "noida", "noida")
    first = client.post("/api/cash-rec", json=_cash_payload(branch.id), headers=headers)
    assert first.status_code == 200
    second = client.post(
        "/api/cash-rec",
        json=_cash_payload(branch.id, rec_date="2099-08-23") | {"actual_closing_balance": 900},
        headers=headers,
    )
    assert second.status_code == 403
    assert "edit" in second.json()["detail"].lower() or "change" in second.json()["detail"].lower()

    admin = _auth(client, "admin", "admin")
    allowed = client.post(
        "/api/cash-rec",
        json=_cash_payload(branch.id) | {"actual_closing_balance": 900},
        headers=admin,
    )
    assert allowed.status_code == 200


def test_edit_saved_false_blocks_existing_daybook(client, db_session):
    seed_database(db=db_session)
    branch = db_session.query(Branch).first()
    channel = db_session.query(PaymentChannel).first()
    db_session.add(DailySale(
        branch_id=branch.id,
        sale_date=date(2099, 8, 23),
        payment_channel_id=channel.id,
        amount=100,
    ))
    db_session.commit()
    headers = _auth(client, "noida", "noida")
    response = client.post(
        "/api/imports/confirm-image-import",
        json={
            "branch_id": branch.id,
            "sale_date": "2099-08-23",
            "cash": 10,
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_non_admin_cannot_manage_users(client, db_session):
    seed_database(db=db_session)
    headers = _auth(client, "accounts@restaurant.com", "accounts123")
    listed = client.get("/api/users", headers=headers)
    assert listed.status_code == 403
    page = client.get("/users", headers=headers, follow_redirects=False)
    assert page.status_code in (302, 303, 307)


def test_admin_can_add_and_modify_user(client, db_session):
    seed_database(db=db_session)
    headers = _auth(client, "admin", "admin")
    role = db_session.query(Role).filter(Role.name == "Branch User").first()
    created = client.post(
        "/api/users",
        json={
            "full_name": "Kitchen Clerk",
            "email": "clerk@restaurant.com",
            "password": "clerk123",
            "role_id": role.id,
            "permissions": {
                "daybook": {"view": True, "enter": True, "edit_saved": False},
                "attendance": {"view": True, "enter": True, "edit_saved": False},
            },
        },
        headers=headers,
    )
    assert created.status_code == 200
    data = created.json()
    assert data["email"] == "clerk@restaurant.com"
    assert data["permissions"]["daybook"]["enter"] is True
    assert data["permissions"]["daybook"]["edit_saved"] is False
    assert data["permissions"]["cash_rec"]["enter"] is True

    updated = client.put(
        f"/api/users/{data['id']}",
        json={
            "full_name": "Kitchen Clerk",
            "email": "clerk@restaurant.com",
            "role_id": role.id,
            "permissions": {
                "daybook": {"view": True, "enter": True, "edit_saved": True},
            },
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["permissions"]["daybook"]["edit_saved"] is True


def test_admin_can_delete_user(client, db_session):
    seed_database(db=db_session)
    headers = _auth(client, "admin", "admin")
    role = db_session.query(Role).filter(Role.name == "Viewer").first()
    created = client.post(
        "/api/users",
        json={
            "full_name": "Temp Viewer",
            "email": "temp.viewer@restaurant.com",
            "password": "temp123",
            "role_id": role.id,
        },
        headers=headers,
    )
    assert created.status_code == 200
    user_id = created.json()["id"]

    deleted = client.delete(f"/api/users/{user_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted_id"] == user_id

    remaining = client.get("/api/users", headers=headers)
    emails = [row["email"] for row in remaining.json()]
    assert "temp.viewer@restaurant.com" not in emails


def test_admin_cannot_delete_own_login(client, db_session):
    seed_database(db=db_session)
    headers = _auth(client, "admin", "admin")
    admin = db_session.query(User).filter(User.email == "admin").first()
    response = client.delete(f"/api/users/{admin.id}", headers=headers)
    assert response.status_code == 400
    assert "own login" in response.json()["detail"].lower()


def test_second_admin_can_delete_first_but_not_themselves(client, db_session):
    seed_database(db=db_session)
    headers = _auth(client, "admin", "admin")
    admin_role = db_session.query(Role).filter(Role.name == "Administrator").first()
    created = client.post(
        "/api/users",
        json={
            "full_name": "Backup Admin",
            "email": "backup.admin@restaurant.com",
            "password": "backup123",
            "role_id": admin_role.id,
        },
        headers=headers,
    )
    assert created.status_code == 200
    backup_id = created.json()["id"]
    original = db_session.query(User).filter(User.email == "admin").first()

    backup_headers = _auth(client, "backup.admin@restaurant.com", "backup123")
    removed = client.delete(f"/api/users/{original.id}", headers=backup_headers)
    assert removed.status_code == 200
    last = client.delete(f"/api/users/{backup_id}", headers=backup_headers)
    assert last.status_code == 400
    assert "own login" in last.json()["detail"].lower()


def test_delete_user_keeps_audit_history(client, db_session):
    seed_database(db=db_session)
    from app.models.audit_log import AuditLog
    from app.services.audit_service import log_action

    headers = _auth(client, "admin", "admin")
    target = db_session.query(User).filter(User.email == "viewer@restaurant.com").first()
    log_action(db_session, "LOGIN", "User", entity_id=target.id, user=target)
    deleted = client.delete(f"/api/users/{target.id}", headers=headers)
    assert deleted.status_code == 200
    db_session.expire_all()
    leftover = db_session.query(AuditLog).filter(AuditLog.username == "Auditor Viewer").first()
    if leftover is None:
        leftover = db_session.query(AuditLog).filter(AuditLog.entity_id == str(target.id)).first()
    assert leftover is not None
    assert leftover.user_id is None


def test_non_admin_cannot_delete_user(client, db_session):
    seed_database(db=db_session)
    target = db_session.query(User).filter(User.email == "viewer@restaurant.com").first()
    headers = _auth(client, "accounts@restaurant.com", "accounts123")
    response = client.delete(f"/api/users/{target.id}", headers=headers)
    assert response.status_code == 403
