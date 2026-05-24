import psycopg2
try:
    # Try the pooler connection
    conn = psycopg2.connect('postgresql://postgres.iqgpxavpimxpcyrxizji:SHARAN%406382031836@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require')
    cur = conn.cursor()
    
    # Reset sequences to match max ID
    cur.execute("SELECT setval('quiz_results_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM quiz_results), false)")
    cur.execute("SELECT setval('quiz_answers_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM quiz_answers), false)")
    
    conn.commit()
    print('Sequences reset successfully!')
    cur.close()
    conn.close()
except Exception as e:
    print('Failed to reset sequences:', e)
