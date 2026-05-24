import urllib.request
import json
from db import get_connection

# Get one question from the API
req = urllib.request.urlopen('http://localhost:5000/api/questions')
qs = json.loads(req.read())
q1 = qs[0]

print(f"Answering Q: {q1['id']} -> {q1['question'][:40]}...")

payload = json.dumps({
    'answers': [
        {'question_id': q1['id'], 'answer': 'A'}
    ]
}).encode('utf-8')

req = urllib.request.Request('http://localhost:5000/api/save', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
res = urllib.request.urlopen(req)
print('Save response:', json.loads(res.read()))

# Verify insertion in DB
conn = get_connection()
cur = conn.cursor()
cur.execute('SELECT question_id, SUBSTRING(question_text, 1, 40) || $$...$$, user_answer, is_correct FROM quiz_answers ORDER BY answered_at DESC LIMIT 1')
row = cur.fetchone()
print(f"DB verify: QID={row[0]} // TEXT_SNIPPET={row[1]} // ANS={row[2]} // CORRECT={row[3]}")
