from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_Q = {
    "title": "Two Sum", "description": "Return indices.", "difficulty": "Easy",
    "visible_test_cases": [{"input": "4\n2 7 11 15\n9", "expected_output": "0 1"}],
    "hidden_test_cases": [{"input": "3\n3 2 4\n6", "expected_output": "1 2"}],
    "boilerplates": {"python": {"template": "# solve here\n"}},
    "allowed_languages": ["python"],
}


def _admin_token():
    r = client.post("/auth/register", json={"email": "adm@q.com", "password": "admin123", "role": "admin"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "adm@q.com", "password": "admin123"})
    return r.json()["data"]["access_token"]


def _user_token():
    r = client.post("/auth/register", json={"email": "usr@q.com", "password": "user1234", "role": "user"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "usr@q.com", "password": "user1234"})
    return r.json()["data"]["access_token"]


def _ah(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_question():
    resp = client.post("/admin/question", json={**BASE_Q, "id": "auth_q1"}, headers=_ah(_admin_token()))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == "auth_q1"


def test_user_cannot_create_question():
    resp = client.post("/admin/question", json={**BASE_Q, "id": "auth_q2"}, headers=_ah(_user_token()))
    assert resp.status_code == 403


def test_no_token_cannot_create_question():
    resp = client.post("/admin/question", json={**BASE_Q, "id": "auth_q3"})
    assert resp.status_code in (401, 403)


def test_admin_can_list_questions():
    resp = client.get("/admin/questions", headers=_ah(_admin_token()))
    assert resp.status_code == 200


def test_user_cannot_list_admin_questions():
    resp = client.get("/admin/questions", headers=_ah(_user_token()))
    assert resp.status_code == 403


def test_admin_can_delete_question():
    at = _admin_token()
    client.post("/admin/question", json={**BASE_Q, "id": "del_auth_q"}, headers=_ah(at))
    resp = client.delete("/admin/question/del_auth_q", headers=_ah(at))
    assert resp.status_code == 200
