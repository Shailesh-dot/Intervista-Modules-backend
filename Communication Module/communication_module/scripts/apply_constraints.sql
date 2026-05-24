-- Standalone SQL to fix duplicate results and add constraints
-- Run this in the Supabase SQL Editor

-- 1. Remove duplicates from speaking_clip_results (keeps the oldest record)
DELETE FROM speaking_clip_results a USING (
  SELECT MIN(ctid) as ctid, session_id, question_index
  FROM speaking_clip_results 
  GROUP BY session_id, question_index HAVING COUNT(*) > 1
) b
WHERE a.session_id = b.session_id 
AND a.question_index = b.question_index 
AND a.ctid <> b.ctid;

-- 2. Add unique constraint to speaking_clip_results
-- This ensures the DB will REJECT duplicates if the code tries to insert them
ALTER TABLE speaking_clip_results 
ADD CONSTRAINT unique_speaking_session_question UNIQUE (session_id, question_index);


-- 3. Remove duplicates from listening_clip_results (keeps the oldest record)
DELETE FROM listening_clip_results a USING (
  SELECT MIN(ctid) as ctid, session_id, clip_id
  FROM listening_clip_results 
  GROUP BY session_id, clip_id HAVING COUNT(*) > 1
) b
WHERE a.session_id = b.session_id 
AND a.clip_id = b.clip_id 
AND a.ctid <> b.ctid;

-- 4. Add unique constraint to listening_clip_results
-- This ensures the DB will REJECT duplicates if the code tries to insert them
ALTER TABLE listening_clip_results 
ADD CONSTRAINT unique_listening_session_clip UNIQUE (session_id, clip_id);
