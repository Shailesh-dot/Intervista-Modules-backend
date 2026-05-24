from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

QUESTION = {
    "id": "ts_v6_sub", "title": "Add", "description": "Print a+b",
    "difficulty": "Easy",
    "visible_test_cases": [{"input": "3 5", "expected_output": "8"}],
    "hidden_test_cases":  [{"input": "10 20", "expected_output": "30"}],
    "boilerplates": {"python": {"template": "a,b=map(int,input().split());print(a+b)\n"}},
    "allowed_languages": ["python"],
}


def _admin_token():
    r = client.post("/auth/register", json={"email": "sadm@test.com", "password": "admin123", "role": "admin"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "sadm@test.com", "password": "admin123"})
    return r.json()["data"]["access_token"]


def _user_token():
    r = client.post("/auth/register", json={"email": "susr@test.com", "password": "user1234", "role": "user"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "susr@test.com", "password": "user1234"})
    return r.json()["data"]["access_token"]


def _ah(token):
    return {"Authorization": f"Bearer {token}"}


def _load():
    client.post("/admin/question", json=QUESTION, headers=_ah(_admin_token()))


def _make_result(stdout):
    return {"stdout": stdout, "stderr": "", "compile_output": "",
            "status": "Accepted", "status_id": 3, "time": "0.04", "memory": "1024"}


@patch("app.services.execution.evaluator.run_code")
def test_user_can_submit(mock_run):
    _load()
    call = {"n": 0}
    def side(*args, **kwargs):
        call["n"] += 1
        return _make_result("8\n" if call["n"] == 1 else "30\n")
    mock_run.side_effect = side

    token = _user_token()
    resp = client.post("/submit/", headers=_ah(token), json={
        "question_id": "ts_v6_sub", "language": "python",
        "source_code": "a,b=map(int,input().split());print(a+b)",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["verdict"] == "Accepted"
    # candidate_id should be the user's user_id from the token
    assert resp.json()["data"]["candidate_id"] != "anonymous"


def test_unauthenticated_cannot_submit():
    resp = client.post("/submit/", json={
        "question_id": "ts_v6_sub", "language": "python", "source_code": "x"
    })
    assert resp.status_code in (401, 403)


def test_user_cannot_view_all_submissions():
    resp = client.get("/submit/all", headers=_ah(_user_token()))
    assert resp.status_code == 403


def test_admin_can_view_all_submissions():
    resp = client.get("/submit/all", headers=_ah(_admin_token()))
    assert resp.status_code == 200


def test_user_cannot_view_others_submission():
    _load()
    # get another user's token
    r = client.post("/auth/register", json={"email": "other@test.com", "password": "other123", "role": "user"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "other@test.com", "password": "other123"})
    other_uid = r.json()["data"]["user_id"]

    # try to access their history with our token
    resp = client.get(f"/submit/candidate/{other_uid}", headers=_ah(_user_token()))
    assert resp.status_code == 403
