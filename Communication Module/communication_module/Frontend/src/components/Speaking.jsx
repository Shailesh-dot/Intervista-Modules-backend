import { useState, useEffect, useCallback } from 'react';
import Timer from './Timer';
import RecordButton from './RecordButton';
import ProgressBar from './ProgressBar';
import { useTimer } from '../hooks/useTimer';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { fetchSpeakingQuestions, submitSpeakingAllResponses } from '../api/client';
import './Speaking.css';

const PREP_TIME = 60; // 1 minute

export default function Speaking({ interviewId, setInterviewId, onComplete }) {
  const [questions, setQuestions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [phase, setPhase] = useState('loading');       // loading | prep | record | submitting | done
  const [recordings, setRecordings] = useState([]);
  const [error, setError] = useState(null);

  const { isRecording, formattedRecordingTime, audioBlob, startRecording, stopRecording, clearRecording } = useAudioRecorder();

  const handlePrepEnd = useCallback(() => {
    setPhase('record');
  }, []);

  const timer = useTimer(PREP_TIME, handlePrepEnd);

  // ── Fetch dynamic questions on mount ─────────────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchSpeakingQuestions(interviewId);
        if (!cancelled) {
          setSessionId(data.session_id);
          setQuestions(data.questions);
          if (data.interview_id) {
            setInterviewId(data.interview_id);
          }
          setPhase('prep');
          timer.start();
        }
      } catch (e) {
        console.error(e);
        if (!cancelled) {
          setError('Failed to connect to the server to get questions. Please refresh or check your connection.');
          setPhase('review'); // Just show the error
        }
      }
    })();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Handle recording submission ──────────────────────────
  const handleStopAndSubmit = async () => {
    const blob = await stopRecording();
    setRecordings((prev) => [...prev, { blob, question: questions[currentIndex] }]);
    setPhase('review'); // Just move to review immediately
  };

  const handleNext = async () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex >= questions.length) {
      setPhase('submitting');
      try {
        // Evaluate all recordings locally stored against the active session
        const aggregated = await submitSpeakingAllResponses(sessionId, recordings);
        setPhase('done');
        setTimeout(() => onComplete(aggregated), 800);
      } catch (err) {
        console.error(err);
        setError('Failed to aggregate speaking results. Please try again.');
        setPhase('review');
      }
    } else {
      setCurrentIndex(nextIndex);
      clearRecording();
      setPhase('prep');
      timer.reset(PREP_TIME);
      timer.start();
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
          <div className="speaking__loader" />
          <p className="mt-2 text-secondary">Generating your questions…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page speaking-page">
      <div className="container animate-fade-in">
        {/* Header */}
        <div className="speaking__header">
          <span className="badge badge-primary">🎤 Speaking Assessment</span>
          <ProgressBar
            current={currentIndex + 1}
            total={questions.length}
            label="Question"
          />
        </div>

        {/* Question Card */}
        <div className="glass-card speaking__question-card animate-fade-in-up" key={currentIndex}>
          <span className="speaking__q-label">Question {currentIndex + 1}</span>
          <h2 className="speaking__question">{questions[currentIndex]}</h2>
        </div>

        {/* Timer & Recording Area */}
        <div className="speaking__action-area">
          {phase === 'prep' && (
            <div className="speaking__prep animate-fade-in">
              <Timer
                seconds={timer.seconds}
                totalSeconds={PREP_TIME}
                label="Preparation"
                variant="prep"
              />
              <button className="btn btn-outline btn-sm mt-2" onClick={handleSkipPrep}>
                Skip Preparation
              </button>
              <p className="speaking__hint">
                Take a moment to organize your thoughts. Recording will begin after the timer.
              </p>
            </div>
          )}

          {phase === 'record' && (
            <div className="speaking__record animate-fade-in">
              <div className="speaking__rec-indicator">
                <span className="speaking__rec-dot" />
                <span className="speaking__rec-time">{formattedRecordingTime}</span>
              </div>
              <RecordButton
                isRecording={isRecording}
                onStart={startRecording}
                onStop={handleStopAndSubmit}
                disabled={false}
              />
              <p className="speaking__hint">
                {isRecording
                  ? 'Speak clearly. Click stop when you\'re done.'
                  : 'Click the button to start recording your answer.'}
              </p>
            </div>
          )}

          {phase === 'submitting' && (
            <div className="speaking__submitting animate-fade-in text-center">
              <div className="speaking__loader" />
              <p className="mt-2 text-secondary">Evaluating complete session. This may take a moment…</p>
            </div>
          )}



          {phase === 'review' && (
            <div className="speaking__review animate-fade-in text-center">
              <div className="speaking__check-icon mb-2">✓</div>
              <p className="text-secondary mb-3">Response recorded and evaluated successfully.</p>
              <button className="btn btn-primary btn-lg" onClick={handleNext}>
                {currentIndex + 1 >= questions.length ? 'See Final Results' : 'Next Question'}
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-2">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="speaking__error animate-fade-in">
            <p>{error}</p>
            <button className="btn btn-sm btn-outline" onClick={() => setError(null)}>
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
