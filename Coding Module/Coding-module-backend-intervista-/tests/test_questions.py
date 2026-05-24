from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE = {
    "id": "tq_v5_1",
    "title": "Add Numbers",
    "description": "Print a+b",
    "difficulty": "Easy",
    "visible_test_cases": [{"input": "3 5", "expected_output": "8"}],
    "hidden_test_cases":  [{"input": "10 20", "expected_output": "30"}],
    "boilerplates": {
        "python": {"template": "a, b = map(int, input().split())\nprint(a + b)\n"},
        "java":   {"template": "import java.util.*;\npublic class Main { ... }\n"},
    },
    "allowed_languages": ["python", "java"],
}


def _admin_token():
    r = client.post("/auth/register", json={"email": "sadm@test.com", "password": "admin123", "role": "admin"})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": "sadm@test.com", "password": "admin123"})
    return r.json()["data"]["access_token"]


def _ah(token):
    return {"Authorization": f"Bearer {token}"}


def _load():
    client.post("/admin/question", json=SAMPLE, headers=_ah(_admin_token()))


def test_get_question_hides_hidden_test_cases():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    hidden = data.get("hidden_test_cases")
    assert hidden is None or hidden == []


def test_get_question_shows_boilerplates():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}")
    data = resp.json()["data"]
    assert "boilerplates" in data
    assert "python" in data["boilerplates"]
    assert "java" in data["boilerplates"]


def test_get_question_shows_allowed_languages():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}")
    data = resp.json()["data"]
    assert "python" in data["allowed_languages"]
    assert "java" in data["allowed_languages"]


def test_boilerplate_endpoint_python():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}/boilerplate?language=python", headers=_ah(_admin_token()))
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["language"] == "python"
    assert d["language_id"] == 71
    assert "a, b = map(int, input().split())" in d["template"]


def test_boilerplate_endpoint_java():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}/boilerplate?language=java", headers=_ah(_admin_token()))
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["language"] == "java"
    assert d["language_id"] == 62


def test_boilerplate_fallback_unknown_language():
    _load()
    resp = client.get(f"/question/{SAMPLE['id']}/boilerplate?language=brainfuck", headers=_ah(_admin_token()))
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert "brainfuck" in d["template"]
    assert d["language_id"] is None


def test_languages_endpoint():
    resp = client.get("/question/languages")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "python" in data
    assert data["python"]["language_id"] == 71
    assert "display" in data["python"]
    assert "java" in data
    assert "cpp" in data


def test_missing_question_404():
    resp = client.get("/question/does_not_exist_xyz")
    assert resp.status_code == 404


def test_random_question():
    _load()
    resp = client.get("/question/random")
    assert resp.status_code == 200


def test_stats():
    _load()
    resp = client.get("/question/stats")
    d = resp.json()["data"]
    assert "total_questions" in d
    assert "by_difficulty" in d
