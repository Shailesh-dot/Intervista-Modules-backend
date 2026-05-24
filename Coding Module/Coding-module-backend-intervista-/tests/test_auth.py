from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ADMIN = {"email": "admin@test.com", "password": "admin123", "role": "admin", "name": "Test Admin"}
USER  = {"email": "user@test.com",  "password": "user1234", "role": "user",  "name": "Test User"}


def _register(payload):
    return client.post("/auth/register", json=payload)

def _login(email, password):
    return client.post("/auth/login", json={"email": email, "password": password})

def _token(payload):
    r = _register(payload)
    if r.status_code == 409:
        r = _login(payload["email"], payload["password"])
    return r.json()["data"]["access_token"]


def test_register_admin():
    resp = _register({**ADMIN, "email": "reg_admin@test.com"})
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["role"] == "admin"
    assert "access_token" in d


def test_register_user():
    resp = _register({**USER, "email": "reg_user@test.com"})
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "user"


def test_register_duplicate_409():
    _register({**USER, "email": "dup@test.com"})
    resp = _register({**USER, "email": "dup@test.com"})
    assert resp.status_code == 409


def test_register_invalid_email_422():
    resp = _register({"email": "notanemail", "password": "pass123", "role": "user"})
    assert resp.status_code == 422


def test_register_short_password_422():
    resp = _register({"email": "short@test.com", "password": "abc", "role": "user"})
    assert resp.status_code == 422


def test_register_invalid_role_422():
    resp = _register({"email": "role@test.com", "password": "pass123", "role": "superuser"})
    assert resp.status_code == 422


def test_login_success():
    _register({**USER, "email": "login@test.com"})
    resp = _login("login@test.com", "user1234")
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert "access_token" in d
    assert d["role"] == "user"


def test_login_wrong_password_401():
    _register({**USER, "email": "wrongpw@test.com"})
    resp = _login("wrongpw@test.com", "wrongpass")
    assert resp.status_code == 401


def test_login_unknown_email_401():
    resp = _login("ghost@test.com", "anypass")
    assert resp.status_code == 401


def test_get_me():
    token = _token({**USER, "email": "me@test.com"})
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "me@test.com"


def test_get_me_no_token_403():
    resp = client.get("/auth/me")
    assert resp.status_code in (401, 403)


def test_admin_can_list_users():
    token = _token({**ADMIN, "email": "listadmin@test.com"})
    resp = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_user_cannot_list_users():
    token = _token({**USER, "email": "listnope@test.com"})
    resp = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
