import { useState, useEffect, useCallback } from 'react';
import Timer from './Timer';
import RecordButton from './RecordButton';
import ProgressBar from './ProgressBar';
import AudioPlayer from './AudioPlayer';
import { useTimer } from '../hooks/useTimer';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { fetchListeningClips, submitListeningAllResponses, aggregateListeningResults } from '../api/client';
import './Listening.css';

const PREP_TIME = 60;

export default function Listening({ interviewId, setInterviewId, onComplete }) {
  const [session, setSession] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [phase, setPhase] = useState('loading'); // loading | play | prep | record | submitting | done
  const [recordings, setRecordings] = useState({});
  const [error, setError] = useState(null);

  const { isRecording, formattedRecordingTime, stopRecording, startRecording, clearRecording } = useAudioRecorder();

  const handlePrepEnd = useCallback(() => {
    setPhase('record');
  }, []);

  const timer = useTimer(PREP_TIME, handlePrepEnd);

  // ── Fetch clips on mount ────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchListeningClips(interviewId);
        if (!cancelled) {
          setSession(data);
          if (data.interview_id) {
            setInterviewId(data.interview_id);
          }
          setPhase('play');
        }
      } catch (e) {
        console.error(e);
        setError('Failed to load listening clips.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const currentClip = session?.clips[currentIndex];

  const handleAudioEnded = () => {
    setPhase('prep');
    timer.start();
  };

  const handleStopAndSubmit = async () => {
    const blob = await stopRecording();
    
    let key = `${currentClip.clip_id}_q1`;
    
    setRecordings((prev) => ({ ...prev, [key]: blob }));
    setPhase('review');
  };

  const handleNext = async () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex >= session.clips.length) {
      setPhase('submitting');
      try {
        const { clip_results } = await submitListeningAllResponses(session.session_id, recordings);
        const finalAggregate = await aggregateListeningResults(clip_results);
        setPhase('done');
        setTimeout(() => onComplete(finalAggregate), 800);
      } catch (e) {
        console.error(e);
        setError('Failed to process listening session.');
        setPhase('review');
      }
    } else {
      setCurrentIndex(nextIndex);
      clearRecording();
      setPhase('play');
      timer.reset(PREP_TIME);
    }
  };

  const handleSkipPrep = () => {
    timer.stop();
    setPhase('record');
  };

  if (phase === 'loading') {
    return (
      <div className="page">
        <div className="container text-center animate-fade-in">
          <div className="listening__loader" />
          <p className="mt-2 text-secondary">Preparing listening assessment…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page listening-page">
      <div className="container animate-fade-in">
        <div className="listening__header">
          <span className="badge badge-accent">🎧 Listening Assessment</span>
          <ProgressBar
            current={currentIndex + 1}
            total={session?.clips.length || 0}
            label="Clip"
          />
        </div>

        <div className="glass-card listening__clip-card animate-fade-in-up">
          <div className="listening__type-info">
            <span className="badge badge-primary">{currentClip?.task_type} Task</span>
            <p className="text-secondary mt-1">
              Listen to the passage and answer the question that follows.
            </p>
          </div>

          <div className="listening__player-area mt-4">
            {currentClip?.audio_b64 && (
              <AudioPlayer 
                src={`data:audio/wav;base64,${currentClip.audio_b64}`} 
                onEnded={handleAudioEnded}
              />
            )}
          </div>

          {phase !== 'play' && (
            <div className="listening__question-box animate-fade-in mt-4">
              <span className="listening__q-label">Question:</span>
              <p className="listening__question">{currentClip.questions[0]}</p>
            </div>
          )}
        </div>

        <div className="listening__action-area">
          {phase === 'prep' && (
            <div className="listening__prep animate-fade-in">
              <Timer
                seconds={timer.seconds}
                totalSeconds={PREP_TIME}
                label="Preparation"
                variant="prep"
              />
              <button className="btn btn-outline btn-sm mt-2" onClick={handleSkipPrep}>
                Skip Preparation
              </button>
              <p className="listening__hint">
                Organize your response. Recording will start automatically.
              </p>
            </div>
          )}

          {phase === 'record' && (
            <div className="listening__record animate-fade-in">
              <div className="listening__rec-indicator">
                <span className="listening__rec-dot" />
                <span className="listening__rec-time">{formattedRecordingTime}</span>
              </div>
              <RecordButton
                isRecording={isRecording}
                onStart={startRecording}
                onStop={handleStopAndSubmit}
              />
              <p className="listening__hint">
                {isRecording ? 'Recording your answer...' : 'Click to start recording.'}
              </p>
            </div>
          )}

          {phase === 'review' && (
            <div className="listening__review animate-fade-in text-center">
              <div className="speaking__check-icon mb-2">✓</div>
              <p className="text-secondary mb-3">Clip response recorded successfully.</p>
              <button className="btn btn-primary btn-lg" onClick={handleNext}>
                {currentIndex + 1 >= session.clips.length ? 'See Final Assessment' : 'Next Clip'}
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-2">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}

          {phase === 'submitting' && (
            <div className="listening__submitting animate-fade-in text-center">
              <div className="listening__loader" />
              <p className="mt-2 text-secondary">
                Evaluating complete session. This may take a moment...
              </p>
            </div>
          )}
        </div>

        {error && (
          <div className="listening__error animate-fade-in">
            <p>{error}</p>
            <button className="btn btn-sm btn-outline" onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}
      </div>
    </div>
  );
}
