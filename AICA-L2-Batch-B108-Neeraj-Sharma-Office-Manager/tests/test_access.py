from conftest import Web, admin_web
from audit_manager.models import Client, User, db


def test_first_run_setup_flow(app):
    w = Web(app)
    assert w.get("/", follow_redirects=False).headers["Location"].endswith("/setup")
    r = w.post("/setup", {"firm_name": "X", "name": "A", "email": "a@x.in", "password": "short", "password2": "short"})
    assert b"at least 8" in r.data
    r = w.post("/setup", {"firm_name": "X", "name": "A", "email": "a@x.in", "password": "longenough1", "password2": "different1"})
    assert b"do not match" in r.data
    r = w.post("/setup", {"firm_name": "X Co", "name": "A", "email": "a@x.in", "password": "longenough1", "password2": "longenough1"}, follow_redirects=True)
    assert b"Setup complete" in r.data
    assert w.get("/setup", follow_redirects=False).status_code == 302  # closed once a user exists
    w.login("a@x.in", "longenough1")
    assert b"Dashboard" in w.get("/").data


def test_login_wrong_password_and_throttle(world):
    w = Web(world["app"])
    for _ in range(5):
        r = w.login("admin@firm.in", "wrong-password")
        assert r.status_code == 200
    assert w.login("admin@firm.in", "Passw0rd!x").status_code == 429  # locked even with the right password


def test_csrf_required_on_post(world):
    w = Web(world["app"])
    w.login("admin@firm.in")
    r = w.c.post("/clients/new", data={"name": "No token Ltd"})
    assert r.status_code == 400
    with world["app"].app_context():
        assert Client.query.filter_by(name="No token Ltd").count() == 0


def test_login_required_and_open_redirect_blocked(world):
    w = Web(world["app"])
    assert w.get("/clients/", follow_redirects=False).status_code == 302
    r = w.post("/login?next=//evil.example", {"email": "admin@firm.in", "password": "Passw0rd!x"})
    assert "evil.example" not in r.headers["Location"]


def test_role_gates(world):
    gates = ["/billing/", "/reports/", "/staff/", "/settings/"]
    expected = {"emp1": [403, 403, 403, 403], "manager": [200, 200, 200, 403], "partner": [200, 200, 200, 200], "admin": [200, 200, 200, 200]}
    for who, codes in expected.items():
        w = Web(world["app"])
        w.login(f"{who}@firm.in")
        assert [w.get(g).status_code for g in gates] == codes, who


def test_employee_sees_only_assigned_or_shared_clients(world):
    app, ids = world["app"], world["ids"]
    w = Web(app)
    w.login("emp1@firm.in")
    page = w.get("/clients/").data
    assert b"Apex Precision" in page and b"Beta Traders" not in page and b"Charlie" not in page
    assert w.get(f"/clients/{ids['apex']}").status_code == 200
    assert w.get(f"/clients/{ids['beta']}").status_code == 403
    assert w.get(f"/clients/{ids['beta']}/edit").status_code == 403
    with app.app_context():  # share Beta with emp1
        c = db.session.get(Client, ids["beta"])
        c.staff.append(db.session.get(User, ids["emp1"]))
        db.session.commit()
    assert w.get(f"/clients/{ids['beta']}").status_code == 200


def test_client_validation_duplicates_and_archive(world):
    w = admin_web(world)
    r = w.post("/clients/new", {"name": "Bad PAN Ltd", "pan": "12345"})
    assert b"PAN must look like" in r.data
    r = w.post("/clients/new", {"name": "Dup", "pan": "AABCA1234F"})
    assert b"already exists" in r.data
    r = w.post("/clients/new", {"name": "Good Ltd", "pan": "ZZZPZ9999Z", "gstin": "03ZZZPZ9999Z1Z5", "is_itr_applicable": "1"}, follow_redirects=True)
    assert b"Good Ltd" in r.data
    with world["app"].app_context():
        good = Client.query.filter_by(name="Good Ltd").one()
        assert good.client_code.startswith("CL-") and good.is_gst_registered
        gid = good.id
    w.post(f"/clients/{gid}/archive")
    w.get("/clients/")  # first view consumes the "was archived" flash message
    assert b"Good Ltd" not in w.get("/clients/").data


def test_employee_new_client_is_assigned_to_them(world):
    w = Web(world["app"])
    w.login("emp2@firm.in")
    w.post("/clients/new", {"name": "Emp Client", "pan": "EEEPE1111E", "assigned_to_id": str(world["ids"]["admin"])})
    with world["app"].app_context():
        assert Client.query.filter_by(name="Emp Client").one().assigned_to_id == world["ids"]["emp2"]


def test_staff_management_rules(world):
    ids = world["ids"]
    m = Web(world["app"])
    m.login("manager@firm.in")
    assert m.post("/staff/add", {"name": "New Admin", "email": "na@firm.in", "password": "Passw0rd!x", "role": "super_admin"}).status_code == 403
    m.post("/staff/add", {"name": "New Emp", "email": "ne@firm.in", "password": "Passw0rd!x", "role": "employee"})
    r = m.post(f"/staff/{ids['manager']}/update", {"name": "Manager", "role": "manager", "active": "0"}, follow_redirects=True)
    assert b"cannot change your own role" in r.data
    assert m.post(f"/staff/{ids['partner']}/update", {"name": "P", "role": "employee", "active": "1"}).status_code == 403
    # switched-off accounts cannot sign in
    with world["app"].app_context():
        new_id = User.query.filter_by(email="ne@firm.in").one().id
    m.post(f"/staff/{new_id}/update", {"name": "New Emp", "role": "employee", "active": "0"})
    e = Web(world["app"])
    r = e.login("ne@firm.in")
    assert b"Wrong email or password" in r.data


def test_forms_carry_a_real_csrf_token_like_a_browser(app):
    """Submit the setup and login forms using only what the HTML page contains (no test shortcuts)."""
    import re

    c = app.test_client()

    def scrape(url):
        html = c.get(url, follow_redirects=True).get_data(as_text=True)
        m = re.search(r'name="_csrf" value="([^"]+)"', html)
        assert m, f"{url} has an empty or missing CSRF field"
        return m.group(1)

    r = c.post("/setup", data={"_csrf": scrape("/setup"), "firm_name": "F", "name": "N", "email": "n@x.in", "password": "longenough1", "password2": "longenough1"})
    assert r.status_code == 302
    r = c.post("/login", data={"_csrf": scrape("/login"), "email": "n@x.in", "password": "longenough1"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    for url in ("/clients/new", "/tasks/", "/billing/new", "/staff/", "/settings/", "/whatsapp/", "/whatsapp/templates", "/calendar/", "/gst"):
        html = c.get(url).get_data(as_text=True)
        assert 'name="_csrf" value=""' not in html, url
