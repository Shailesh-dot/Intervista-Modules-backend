import './Welcome.css';

export default function Welcome({ onStart }) {
  return (
    <div className="page welcome-page">
      <div className="container animate-fade-in">
        {/* Hero */}
        <div className="welcome__hero">
          <div className="welcome__icon-ring">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </div>
          <h1 className="welcome__title">
            Communication<br />
            <span className="welcome__title-accent">Assessment</span>
          </h1>
          <p className="welcome__subtitle">
            Evaluate your speaking and listening skills with our AI-powered assessment platform.
            Complete both sections for a comprehensive communication score.
          </p>
        </div>

        {/* Section Cards */}
        <div className="welcome__sections stagger">
          <div className="glass-card welcome__section-card animate-fade-in-up">
            <div className="welcome__section-icon welcome__section-icon--speaking">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              </svg>
            </div>
            <h3>Speaking Assessment</h3>
            <p className="text-secondary">
              Answer 3 interview-style questions. Each includes a 1-minute preparation time before recording.
            </p>
            <div className="welcome__meta">
              <span className="badge badge-primary">🎤 3 Questions</span>
              <span className="badge badge-primary">⏱ ~5 min</span>
            </div>
          </div>

          <div className="glass-card welcome__section-card animate-fade-in-up">
            <div className="welcome__section-icon welcome__section-icon--listening">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
                <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
              </svg>
            </div>
            <h3>Listening Assessment</h3>
            <p className="text-secondary">
              Listen to 4 audio clips — repeat what you hear or answer questions based on the clip.
            </p>
            <div className="welcome__meta">
              <span className="badge badge-accent">🎧 4 Clips</span>
              <span className="badge badge-accent">⏱ ~6 min</span>
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="glass-card welcome__instructions animate-fade-in-up">
          <h3>📋 Before You Begin</h3>
          <ul>
            <li>Ensure you are in a <strong>quiet environment</strong></li>
            <li>Use a <strong>headset with microphone</strong> for best results</li>
            <li>Allow <strong>microphone access</strong> when prompted</li>
            <li>Each question has a <strong>1-minute preparation</strong> period</li>
            <li>Speak <strong>clearly and naturally</strong> — there are no wrong answers</li>
          </ul>
        </div>

        {/* CTA */}
        <button
          className="btn btn-primary btn-lg welcome__cta animate-fade-in-up"
          onClick={onStart}
          id="start-assessment-btn"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          Begin Assessment
        </button>
      </div>
    </div>
  );
}
