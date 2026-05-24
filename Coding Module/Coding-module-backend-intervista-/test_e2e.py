import requests
import time
import json

BASE_URL = "http://localhost:8000"
session = requests.Session()

print("1. Registering user (Testing Role Lockdown)...")
resp = session.post(f"{BASE_URL}/auth/register", json={
    "email": "hacker@gmail.com",
    "password": "password123",
    "name": "Hacker User",
    "role": "admin" # Trying to inject admin role
})
print("Reg status:", resp.status_code)

# Login
resp = session.post(f"{BASE_URL}/auth/login", json={
    "email": "hacker@gmail.com",
    "password": "password123"
})
token = resp.json()["data"]["access_token"]
role = resp.json()["data"]["role"]
print(f"Logged in. Assigned role: {role} (expected 'user' natively bypassing injection)")
headers = {"Authorization": f"Bearer {token}"}

print("\n2. Elevating user to Admin via DB bypass for testing...")
from app.db.session import db_session
from app.models.user import User
with db_session() as db:
    u = db.query(User).filter(User.email=="hacker@gmail.com").first()
    u.role = "admin"
    db.commit()

# Re-login to hit new tokens
resp = session.post(f"{BASE_URL}/auth/login", json={"email": "hacker@gmail.com", "password": "password123"})
admin_token = resp.json()["data"]["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

print("\n3. Creating Question via Admin routes...")
boilerplate_code = """def solve():
    import sys
    data = sys.stdin.read().split()
    if len(data) < 2: return
    print('true' if sorted(data[0]) == sorted(data[1]) else 'false')

if __name__ == '__main__':
    solve()"""

q_payload = {
  "id": "q_async_test",
  "title": "Valid Anagram Async",
  "description": "Anagram test",
  "difficulty": "Easy",
  "sample_test_cases": [
      {"input": "anagram\\nnagaram", "expected_output": "true"}
  ],
  "hidden_test_cases": [
      {"input": "rat\\ncar", "expected_output": "false"}
  ],
  "boilerplates": {
      "python": {
          "template": boilerplate_code
      }
  },
  "allowed_languages": ["python"]
}

resp = session.post(f"{BASE_URL}/admin/question", json=q_payload, headers=admin_headers)
if resp.status_code != 200:
    print("Create Q Failed:", resp.text)
else:
    print("Create Q status: 200 OK")

print("\n4. Fetching Public Question (Verifying zero leak of hidden test cases)...")
resp = session.get(f"{BASE_URL}/question/q_async_test")
data = resp.json()["data"]
keys = list(data.keys())
print(f"Keys exposed to public: {keys}")
assert "hidden_test_cases" not in keys, "SECURITY FLAW: Hidden TCs Leaked!"
print("Success: hidden_test_cases strictly stripped securely.")

print("\n5. Submitting code asynchronously...")
sub_payload = {
    "question_id": "q_async_test",
    "language": "python",
    "source_code": boilerplate_code
}
resp = session.post(f"{BASE_URL}/submit/", json=sub_payload, headers=headers)
print("Submit Initial Resp:", resp.json())
sub_id = resp.json()["data"]["submission_id"]

print("\n6. Polling asynchronous submission...")
for i in range(10):
    time.sleep(1.5)
    p_resp = session.get(f"{BASE_URL}/submit/{sub_id}/status", headers=headers)
    data = p_resp.json()["data"]
    print(f"Poll check {i+1}: job_status='{data['job_status']}' | verdict='{data['status']}'")
    if data["job_status"] == "completed":
        print("\n=== FINAL RESULTS ===")
        print("Verdict:", data["status"], "| Score:", data["score"])
        for tc in data["test_case_results"]:
            print(f"  TC {tc['test_case_id']} | hidden={tc.get('is_hidden', 'MASKED')} | expected={tc.get('expected_output', 'MASKED')} | status={tc['status']}")
        break

print("\nEnd-to-End Pipeline Successful!")
