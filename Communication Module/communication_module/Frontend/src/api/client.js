const API_BASE = 'https://eloise-frizzlier-unradically.ngrok-free.dev/api/v1';

/**
 * Fetch 3 speaking questions (1 static + 2 dynamic)
 */
export async function fetchSpeakingQuestions(interviewId = null) {
  let url = `${API_BASE}/speaking/questions`;
  if (interviewId) {
    url += `?interview_id=${encodeURIComponent(interviewId)}`;
  }
  const res = await fetch(url, {
    headers: { 'ngrok-skip-browser-warning': 'true' }
  });
  if (!res.ok) throw new Error('Failed to fetch speaking questions');
  return await res.json();
}

/**
 * Submit a speaking response for evaluation
 * @param {Blob} audioBlob  WAV audio blob
 * @param {string} question The question that was asked
 */
export async function submitSpeakingResponse(audioBlob, sessionId, questionIndex) {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.wav');
  form.append('session_id', sessionId);
  form.append('question_index', questionIndex.toString());

  const res = await fetch(`${API_BASE}/evaluate`, {
    method: 'POST',
    headers: { 'ngrok-skip-browser-warning': 'true' },
    body: form,
  });
  if (!res.ok) throw new Error('Speaking evaluation failed');
  return res.json();
}

/**
 * Submit all speaking responses for batch evaluation
 * @param {Array} recordings Array of { blob, question }
 */
export async function submitSpeakingAllResponses(sessionId, recordings) {
  const form = new FormData();
  form.append('session_id', sessionId);
  recordings.forEach((rec, index) => {
    form.append(`audio_${index + 1}`, rec.blob, `recording_${index + 1}.wav`);
  });

  const res = await fetch(`${API_BASE}/speaking/evaluate_all`, {
    method: 'POST',
    headers: { 'ngrok-skip-browser-warning': 'true' },
    body: form,
  });
  if (!res.ok) throw new Error('Batched speaking evaluation failed');
  return res.json();
}

/**
 * Fetch listening clips (4 clips with audio)
 */
export async function fetchListeningClips(interviewId = null) {
  let url = `${API_BASE}/listening/clips`;
  if (interviewId) {
    url += `?interview_id=${encodeURIComponent(interviewId)}`;
  }
  const res = await fetch(url, {
    headers: { 'ngrok-skip-browser-warning': 'true' }
  });
  if (!res.ok) throw new Error('Failed to fetch listening clips');
  const data = await res.json();
  return data; // Return full object { session_id, clips } instead of data.clips
}

/**
 * Submit a listening response
 * @param {Blob} audioBlob
 * @param {string} sessionId
 * @param {string} clipId
 * @param {number} questionIndex
 */
export async function submitListeningResponse(audioBlob, sessionId, clipId, questionIndex = 0) {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.wav');
  form.append('session_id', sessionId);
  form.append('clip_id', clipId);
  form.append('question_index', questionIndex.toString());

  const res = await fetch(`${API_BASE}/listening/respond`, {
    method: 'POST',
    headers: { 'ngrok-skip-browser-warning': 'true' },
    body: form,
  });
  if (!res.ok) throw new Error('Listening response submission failed');
  return res.json();
}

/**
 * Submit all listening responses at once
 * @param {string} sessionId
 * @param {Object} recordings Mapping of clip ID to blobs { "clip_1": blob, "clip_2": blob, etc }
 */
export async function submitListeningAllResponses(sessionId, recordings) {
  const form = new FormData();
  form.append('session_id', sessionId);
  
  // 4 QnA clips
  if (recordings['clip_1_q1']) form.append('clip_1_q1', recordings['clip_1_q1'], 'c1q1.wav');
  if (recordings['clip_2_q1']) form.append('clip_2_q1', recordings['clip_2_q1'], 'c2q1.wav');
  if (recordings['clip_3_q1']) form.append('clip_3_q1', recordings['clip_3_q1'], 'c3q1.wav');
  if (recordings['clip_4_q1']) form.append('clip_4_q1', recordings['clip_4_q1'], 'c4q1.wav');

  const res = await fetch(`${API_BASE}/listening/respond_all`, {
    method: 'POST',
    headers: { 'ngrok-skip-browser-warning': 'true' },
    body: form,
  });
  if (!res.ok) throw new Error('Batched listening response submission failed');
  return res.json();
}

/**
 * Aggregate listening results
 * @param {Array} clipResults
 */
export async function aggregateListeningResults(clipResults) {
  const res = await fetch(`${API_BASE}/listening/aggregate`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true' 
    },
    body: JSON.stringify(clipResults),
  });
  if (!res.ok) throw new Error('Listening aggregation failed');
  return res.json();
}

/**
 * Aggregate speaking results
 * @param {Array} clipResults
 */
export async function aggregateSpeakingResults(clipResults) {
  const res = await fetch(`${API_BASE}/speaking/aggregate`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true' 
    },
    body: JSON.stringify(clipResults),
  });
  if (!res.ok) throw new Error('Speaking aggregation failed');
  return res.json();
}

