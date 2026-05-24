import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

const TIMER_SECS = 20 * 60
const DEFAULT_NUM_QUESTIONS = 15

function cleanQuestion(q = '') {
  return q.replace(/\*+/g, '').trim()
}

function fmtTime(secs) {
  const m = String(Math.floor(secs / 60)).padStart(2, '0')
  const s = String(secs % 60).padStart(2, '0')
  return `${m}:${s}`
}

// ── Topic Icons (mapped by keyword) ──────────────────────────
const TOPIC_ICONS = {
  'direction': '🧭', 'coding': '🔐', 'decoding': '🔐',
  'number': '🔢', 'series': '📊', 'blood': '👨‍👩‍👧',
  'order': '📋', 'ranking': '📋', 'syllogism': '🧩',
  'inequality': '⚖️', 'ratio': '📐', 'proportion': '📐',
  'profit': '💰', 'loss': '💰', 'discount': '💰',
  'average': '📈', 'time': '⏱️', 'work': '⏱️', 'pipe': '⏱️',
  'data': '📊', 'interpretation': '📊', 'probability': '🎲',
  'permutation': '🔄', 'combination': '🔄', 'sufficiency': '📝',
  'puzzle': '🧠', 'logical': '🧠', 'hcf': '🔣', 'lcm': '🔣',
  'percentage': '💯', 'mirror': '🪞', 'water': '💧',
  'shadow': '🌗', 'light': '🌗', 'figure': '🔷', 'missing': '❓',
  'pattern': '🔶', 'paper': '📄', 'folding': '📄', 'cutting': '📄',
  'cube': '🎯', 'dice': '🎯', 'embedded': '🔍',
  'calendar': '📅', 'clock': '🕐',
}

function getTopicIcon(displayName) {
  const lower = displayName.toLowerCase()
  for (const [keyword, icon] of Object.entries(TOPIC_ICONS)) {
    if (lower.includes(keyword)) return icon
  }
  return '📚'
}

// ── Root ──────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState('admin')
  const [quizConfig, setQuizConfig] = useState(null)

  const handleStartQuiz = (config) => {
    setQuizConfig(config)
    setScreen('loading')
  }

  return (
    <div className="app-shell">
      {screen === 'admin' && <AdminPanel onStartQuiz={handleStartQuiz} />}
      {screen === 'loading' && (
        <LoadingScreen
          config={quizConfig}
          onReady={(qs) => setScreen({ name: 'quiz', questions: qs })}
        />
      )}
      {screen.name === 'quiz' && (
        <QuizScreen
          questions={screen.questions}
          onDone={() => setScreen('submitted')}
        />
      )}
      {screen === 'submitted' && (
        <SubmittedScreen onRestart={() => setScreen('admin')} />
      )}
    </div>
  )
}

// ── Admin Panel ──────────────────────────────────────────────
function AdminPanel({ onStartQuiz }) {
  const [topics, setTopics] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [numQuestions, setNumQuestions] = useState(DEFAULT_NUM_QUESTIONS)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetch('/api/topics', {
      headers: { 'ngrok-skip-browser-warning': 'any' }
    })
      .then(r => {
        if (!r.ok) throw new Error(`Server error ${r.status}`)
        return r.json()
      })
      .then(data => {
        setTopics(data.topics || [])
        setLoading(false)
      })
      .catch(e => {
        setError(e.message)
        setLoading(false)
      })
  }, [])

  const toggleTopic = (key) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const selectAll = () => {
    if (selected.size === topics.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(topics.map(t => t.key)))
    }
  }

  const totalQuestions = topics
    .filter(t => selected.has(t.key))
    .reduce((sum, t) => sum + t.count, 0)

  const filteredTopics = topics.filter(t =>
    t.display.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleStart = () => {
    onStartQuiz({
      topics: Array.from(selected),
      numQuestions
    })
  }

  if (loading) return (
    <div className="screen center-screen fade-in">
      <div className="spinner" />
      <p className="loading-label">Loading topics…</p>
    </div>
  )

  if (error) return (
    <div className="screen center-screen fade-in">
      <div className="error-box">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Could not load topics</p>
        <p className="error-msg">{error}</p>
        <p className="error-hint">Make sure the Flask server is running on port 5000.</p>
      </div>
    </div>
  )

  return (
    <div className="screen admin-screen fade-up">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-header-top">
          <div className="admin-logo-group">
            <LogoMark size={42} />
            <div>
              <h1 className="admin-title">AptitudeIQ</h1>
              <span className="admin-badge">Admin Panel</span>
            </div>
          </div>
        </div>
        <p className="admin-subtitle">
          Select topics to customize your quiz, or start directly for a randomized experience across all {topics.length} topics.
        </p>
      </div>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <span className="stat-icon">📁</span>
          <div className="stat-info">
            <span className="stat-value">{topics.length}</span>
            <span className="stat-label">Total Topics</span>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon">✅</span>
          <div className="stat-info">
            <span className="stat-value">{selected.size}</span>
            <span className="stat-label">Selected</span>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon">📝</span>
          <div className="stat-info">
            <span className="stat-value">{selected.size > 0 ? totalQuestions : '∞'}</span>
            <span className="stat-label">Available Qs</span>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon">🎯</span>
          <div className="stat-info">
            <span className="stat-value">{numQuestions}</span>
            <span className="stat-label">Quiz Size</span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="admin-controls">
        <div className="search-wrap">
          <SearchIcon />
          <input
            type="text"
            className="search-input"
            placeholder="Search topics…"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button className="search-clear" onClick={() => setSearchTerm('')}>×</button>
          )}
        </div>
        <button className="btn-ghost btn-compact" onClick={selectAll}>
          {selected.size === topics.length ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      {/* Topics Grid */}
      <div className="topics-grid">
        {filteredTopics.map((topic, i) => (
          <button
            key={topic.key}
            className={`topic-card${selected.has(topic.key) ? ' active' : ''}`}
            onClick={() => toggleTopic(topic.key)}
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <div className="topic-card-header">
              <span className="topic-icon">{getTopicIcon(topic.display)}</span>
              <span className={`topic-check${selected.has(topic.key) ? ' visible' : ''}`}>
                <CheckIcon />
              </span>
            </div>
            <span className="topic-name">{topic.display}</span>
            <span className="topic-count">{topic.count} questions</span>
          </button>
        ))}
      </div>

      {filteredTopics.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">🔍</span>
          <p>No topics match "{searchTerm}"</p>
        </div>
      )}

      {/* Configuration Footer */}
      <div className="admin-footer">
        <div className="quiz-config">
          <label className="config-label">
            <span>Questions per quiz</span>
            <div className="stepper">
              <button
                className="stepper-btn"
                onClick={() => setNumQuestions(n => Math.max(5, n - 5))}
              >−</button>
              <span className="stepper-value">{numQuestions}</span>
              <button
                className="stepper-btn"
                onClick={() => setNumQuestions(n => Math.min(50, n + 5))}
              >+</button>
            </div>
          </label>
        </div>
        <div className="footer-actions">
          <div className="action-hint">
            {selected.size === 0
              ? '🔀 No topics selected — quiz will randomize from all topics'
              : `🎯 ${selected.size} topic${selected.size > 1 ? 's' : ''} selected · ${totalQuestions} questions available`
            }
          </div>
          <button className="btn-primary btn-launch" onClick={handleStart}>
            <RocketIcon />
            <span>Launch Quiz</span>
            <ArrowIcon />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Loading (fetches questions, then hands off) ───────────────
function LoadingScreen({ config, onReady }) {
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        let response
        if (config && config.topics && config.topics.length > 0) {
          // Fetch from selected topics
          response = await fetch('/api/questions/by-topics', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'any'
            },
            body: JSON.stringify({
              topics: config.topics,
              num_questions: config.numQuestions || DEFAULT_NUM_QUESTIONS
            })
          })
        } else {
          // Randomize from all topics
          response = await fetch('/api/questions/by-topics', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'any'
            },
            body: JSON.stringify({
              topics: [],
              num_questions: config?.numQuestions || DEFAULT_NUM_QUESTIONS
            })
          })
        }

        if (!response.ok) throw new Error(`Server error ${response.status}`)
        const data = await response.json()

        if (!Array.isArray(data) || data.length === 0)
          throw new Error('No questions returned from server')

        onReady(data)
      } catch (e) {
        setError(e.message)
      }
    }

    fetchQuestions()
  }, [])

  if (error) return (
    <div className="screen center-screen fade-in">
      <div className="error-box">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Could not load questions</p>
        <p className="error-msg">{error}</p>
        <p className="error-hint">Make sure the Flask server is running on port 5000.</p>
      </div>
    </div>
  )

  return (
    <div className="screen center-screen fade-in">
      <div className="spinner" />
      <p className="loading-label">Preparing your quiz…</p>
      <p className="loading-sub">
        {config?.topics?.length > 0
          ? `Fetching from ${config.topics.length} selected topic${config.topics.length > 1 ? 's' : ''}`
          : 'Randomizing from all topics'
        }
      </p>
    </div>
  )
}

// ── Quiz ──────────────────────────────────────────────────────
function QuizScreen({ questions, onDone }) {
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState(null)
  const [answers, setAnswers] = useState([])
  const [timeLeft, setTimeLeft] = useState(TIMER_SECS)
  const [animKey, setAnimKey] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const timerRef = useRef(null)
  const submitOnce = useRef(false)

  // Timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) { clearInterval(timerRef.current); return 0 }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current)
  }, [])

  // Auto-submit when time runs out
  useEffect(() => {
    if (timeLeft === 0) doSubmit(answers)
  }, [timeLeft])

  const doSubmit = useCallback(async (finalAnswers) => {
    if (submitOnce.current) return
    submitOnce.current = true
    clearInterval(timerRef.current)
    setSubmitting(true)
    try {
      await fetch('/api/save', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'any'
        },
        body: JSON.stringify({ answers: finalAnswers })
      })
    } catch (e) {
      console.error('Submit error:', e)
    }
    onDone()
  }, [onDone])

  const advance = useCallback((skip = false) => {
    const q = questions[current]
    if (!q || submitting) return

    const newAnswers = [
      ...answers,
      { question_id: q.id, answer: skip ? null : selected }
    ]
    setAnswers(newAnswers)

    if (current + 1 >= questions.length) {
      doSubmit(newAnswers)
    } else {
      setCurrent(c => c + 1)
      setSelected(null)
      setAnimKey(k => k + 1)
    }
  }, [questions, current, answers, selected, submitting, doSubmit])

  if (submitting) return (
    <div className="screen center-screen fade-in">
      <div className="spinner" />
      <p className="loading-label">Submitting your quiz…</p>
    </div>
  )

  const q = questions[current]
  const pct = (current / questions.length) * 100
  const answered = answers.filter(a => a.answer !== null).length
  const timerFrac = timeLeft / TIMER_SECS
  const timerWarn = timeLeft < TIMER_SECS * 0.2
  const CIRC = 150.8

  let opts = q.options || {}
  if (typeof opts === 'string') { try { opts = JSON.parse(opts) } catch { opts = {} } }

  return (
    <div className="screen quiz-screen">

      {/* Header */}
      <header className="quiz-header">
        <div className="qh-side">
          <span className="qh-label">Question</span>
          <span className="qh-count">
            <strong>{current + 1}</strong>
            <span className="qh-of">/{questions.length}</span>
          </span>
        </div>

        <div className="qh-center">
          <div className="timer-wrap">
            <svg width="60" height="60" viewBox="0 0 60 60">
              <circle cx="30" cy="30" r="24" fill="none"
                stroke="var(--surface3)" strokeWidth="4" />
              <circle cx="30" cy="30" r="24" fill="none"
                stroke={timerWarn ? 'var(--danger)' : 'var(--accent)'}
                strokeWidth="4" strokeLinecap="round"
                strokeDasharray={CIRC}
                strokeDashoffset={CIRC * (1 - timerFrac)}
                style={{
                  transform: 'rotate(-90deg)', transformOrigin: 'center',
                  transition: 'stroke-dashoffset 1s linear, stroke 0.4s'
                }} />
            </svg>
            <span className="timer-text" style={{ color: timerWarn ? 'var(--danger)' : 'var(--text)' }}>
              {fmtTime(timeLeft)}
            </span>
          </div>
        </div>

        <div className="qh-side qh-right">
          <span className="qh-label">Answered</span>
          <span className="qh-count">
            <strong style={{ color: 'var(--accent)' }}>{answered}</strong>
            <span className="qh-of">/{questions.length}</span>
          </span>
        </div>
      </header>

      {/* Category badge */}
      {q.category && (
        <div className="category-badge fade-in">
          <span>{getTopicIcon(q.category)}</span>
          <span>{q.category.replace(/_/g, ' ')}</span>
        </div>
      )}

      {/* Progress */}
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>

      {/* Question */}
      <div className="question-card fade-up" key={`q-${animKey}`}>
        <p className="q-text">{cleanQuestion(q.question)}</p>
      </div>

      {/* Options */}
      <div className="options-list">
        {['A', 'B', 'C', 'D', 'E'].map((key, i) => {
          const val = opts[key];
          if (val === undefined) return null;
          
          const displayVal = val.toString().trim() || `Option ${key}`
          const sel = selected === key
          return (
            <button
              key={`${animKey}-${key}`}
              className={`option-btn${sel ? ' selected' : ''} fade-up`}
              style={{ animationDelay: `${i * 55}ms` }}
              onClick={() => setSelected(key)}
            >
              <span className={`opt-key${sel ? ' sel' : ''}`}>{key}</span>
              <span className="opt-val">{displayVal}</span>
              {sel && <span className="opt-check"><CheckIcon /></span>}
            </button>
          )
        })}
      </div>

      {/* Footer */}
      <div className="quiz-footer">
        <button className="btn-ghost" onClick={() => advance(true)}>Skip</button>
        <button className="btn-primary" onClick={() => advance(false)}>
          {current + 1 >= questions.length ? 'Submit Quiz' : 'Next'}
          <ArrowIcon />
        </button>
      </div>

    </div>
  )
}

// ── Submitted ─────────────────────────────────────────────────
function SubmittedScreen({ onRestart }) {
  return (
    <div className="screen center-screen fade-up">
      <div className="submitted-icon">
        <svg width="38" height="38" viewBox="0 0 38 38" fill="none">
          <path d="M8 19l8 8 14-15"
            stroke="var(--success)" strokeWidth="3"
            strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <h2 className="submitted-title">Quiz Submitted!</h2>
      <p className="submitted-sub">Your answers have been saved and evaluated in the database.</p>
      <button className="btn-primary" onClick={onRestart}>
        Back to Admin Panel <ArrowIcon />
      </button>
    </div>
  )
}

// ── Icons ─────────────────────────────────────────────────────
function LogoMark({ size = 40 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <rect width="40" height="40" rx="12" fill="url(#lg1)" />
      <path d="M11 27L20 11l9 16" stroke="white" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14.5 21.5h11" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
      <defs>
        <linearGradient id="lg1" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#3d7eff" />
          <stop offset="100%" stopColor="#6c4fff" />
        </linearGradient>
      </defs>
    </svg>
  )
}
function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 7l3.5 3.5L12 3" stroke="currentColor" strokeWidth="2.2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" />
    </svg>
  )
}
function RocketIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11.95A22 22 0 0112 15z"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}