import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('data/all_questions.json', 'r', encoding='utf-8'))
bad = [q for q in data if any('Answer' in str(v) for v in q.get('options', {}).values())]
print(f"Found {len(bad)} bad questions out of {len(data)}")
for q in bad[:15]:
    print(f"  Q: {q['question'][:60]}")
    print(f"  Opts: {q['options']}")
    print(f"  Source: {q.get('source','')}")
    print()
