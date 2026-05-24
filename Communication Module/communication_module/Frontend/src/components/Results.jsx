import './Results.css';

export default function Results({ speakingResults, listeningResults, onRestart }) {
  // Simple scoring average for speaking
  const avgSpeaking = Array.isArray(speakingResults)
    ? speakingResults?.reduce((sum, res) => sum + (res.final_score_10 || 0), 0) / (speakingResults?.length || 1)
    : speakingResults?.final_score_10 || 0;
  const avgListening = listeningResults?.listening_score_10 || 0;
  const overall = Math.round((avgSpeaking + avgListening) / 2);

  const getPerformanceClass = (score) => {
    if (score >= 8) return 'performance--excellent';
    if (score >= 6) return 'performance--good';
    if (score >= 4) return 'performance--moderate';
    return 'performance--needs-improvement';
  };

  const getScoreWord = (score) => {
    if (score >= 8) return 'Excellent';
    if (score >= 6) return 'Good';
    if (score >= 4) return 'Moderate';
    return 'Needs Improvement';
  };

  const getWordColorClass = (score) => {
    if (score >= 8) return 'text-success';
    if (score >= 6) return 'text-primary';
    if (score >= 4) return 'text-warning';
    return 'text-danger'; 
  };

  // Speaking parameters
  const speakingParamsList = [
    { key: 'pronunciation', label: 'Pronunciation' },
    { key: 'fluency', label: 'Fluency' },
    { key: 'tone', label: 'Tone' },
    { key: 'grammar', label: 'Grammar' },
    { key: 'comprehension', label: 'Comprehension' }
  ];

  const speakingParamScores = speakingParamsList.map(param => {
    let score10 = 0;
    
    // Check new backend continuous scores (0-1 scale)
    if (speakingResults?._continuous_scores && speakingResults._continuous_scores[param.key] !== undefined) {
      score10 = Math.round(speakingResults._continuous_scores[param.key] * 10);
    } else if (Array.isArray(speakingResults)) {
      let totalScore = 0;
      let count = 0;
      speakingResults.forEach(res => {
        if (res._continuous_scores && res._continuous_scores[param.key] !== undefined) {
          totalScore += res._continuous_scores[param.key];
          count++;
        } else if (res.details && res.details[param.key] && res.details[param.key].score !== undefined) {
          totalScore += (res.details[param.key].score / 2); // old format baseline
          count++;
        }
      });
      score10 = count > 0 ? Math.round((totalScore / count) * 10) : 0;
    } else if (speakingResults?.details && speakingResults.details[param.key] && speakingResults.details[param.key].score !== undefined) {
      // old format fallback
      score10 = Math.round((speakingResults.details[param.key].score / 2) * 10);
    }
    
    return { ...param, score: score10 };
  });

  // Listening parameters
  const listeningParamsList = [
    { key: 'listening_accuracy', label: 'Accuracy' },
    { key: 'retention', label: 'Retention' },
    { key: 'comprehension', label: 'Comprehension' }
  ];

  const listeningParamScores = listeningParamsList.map(param => {
    let score10 = 0;
    if (listeningResults?.parameters && listeningResults.parameters[param.key]) {
      const p = listeningResults.parameters[param.key];
      // New format uses avg_score_01
      if (p.avg_score_01 !== undefined) {
        score10 = Math.round(p.avg_score_01 * 10);
      } else {
        // Old format fallback
        score10 = Math.round(((p.avg_score || 0) / 2) * 10);
      }
    }
    return { ...param, score: score10 };
  });

  return (
    <div className="page results-page">
      <div className="container animate-fade-in">
        <div className="results__header text-center">
          <h1 className="results__title">Assessment Summary</h1>
          <p className="results__subtitle">Great job completing both sections!</p>
        </div>

        {/* Overall Score Gauge */}
        <div className={`glass-card results__score-card ${getPerformanceClass(overall)}`}>
          <div className="results__gauge">
            <svg viewBox="0 0 100 100">
              <circle className="results__gauge-bg" cx="50" cy="50" r="45" />
              <circle 
                className="results__gauge-fill" 
                cx="50" cy="50" r="45" 
                strokeDasharray="283" 
                strokeDashoffset={283 - (283 * overall) / 10} 
              />
            </svg>
            <div className="results__gauge-content">
              <span className="results__gauge-score">{overall}</span>
              <span className="results__gauge-max">/ 10</span>
            </div>
          </div>
          <h2 className="results__verdict mt-3">
            {overall >= 8 ? 'Excellent Communication' : overall >= 6 ? 'Good Proficiency' : 'Developing Skills'}
          </h2>
        </div>

        {/* Section Breakdown */}
        <div className="results__grid stagger">
          <div className="glass-card results__section-results">
            <div className="flex items-center gap-1 mb-2">
              <span className="badge badge-primary">🎤 Speaking</span>
              <span className="results__section-score">{Math.round(avgSpeaking)} / 10</span>
            </div>
            
            <div className="results__parameters mt-4 mb-4">
              <h4>Parameter Scores</h4>
              <ul className="results__params-list">
                {speakingParamScores.map(p => (
                  <li key={p.key} className="results__param-item">
                    <span className="results__param-label">{p.label}</span>
                    <span className="results__param-value font-semibold flex items-center gap-2">
                      {p.score}/10 
                      <span className={`text-sm font-medium ${getWordColorClass(p.score)}`}>({getScoreWord(p.score)})</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="results__details">
              <h4>Strengths</h4>
              <ul>
                {(() => {
                  const sArr = Array.isArray(speakingResults) ? speakingResults?.[0]?.summary?.strengths : speakingResults?.summary?.strengths;
                  return sArr && sArr.length > 0 ? sArr.map((s, i) => <li key={i}>{s}</li>) : <li className="text-secondary">No strengths recorded.</li>;
                })()}
              </ul>
              <h4 className="mt-4 text-warning">Areas to Improve</h4>
              <ul>
                {(() => {
                  const iArr = Array.isArray(speakingResults) ? speakingResults?.[0]?.summary?.improvements : speakingResults?.summary?.improvements;
                  return iArr && iArr.length > 0 ? iArr.map((im, i) => <li key={i}>{im}</li>) : <li className="text-secondary">No improvements recorded.</li>;
                })()}
              </ul>
            </div>
          </div>

          <div className="glass-card results__section-results">
            <div className="flex items-center gap-1 mb-2">
              <span className="badge badge-accent">🎧 Listening</span>
              <span className="results__section-score">{Math.round(avgListening)} / 10</span>
            </div>
            
            <div className="results__parameters mt-4 mb-4">
              <h4>Parameter Scores</h4>
              <ul className="results__params-list">
                {listeningParamScores.map(p => (
                  <li key={p.key} className="results__param-item">
                    <span className="results__param-label">{p.label}</span>
                    <span className="results__param-value font-semibold flex items-center gap-2">
                      {p.score}/10 
                      <span className={`text-sm font-medium ${getWordColorClass(p.score)}`}>({getScoreWord(p.score)})</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="results__details">
              <p className="text-secondary mb-3">{listeningResults?.summary?.verdict || 'Well done on the listening tasks!'}</p>
              <h4 className="mt-2 text-accent">Summary</h4>
              <p className="results__summary-text">{listeningResults?.summary?.notes || listeningResults?.summary?.verdict || 'You showed consistent comprehension across repeat and Q&A tasks.'}</p>
            </div>
          </div>
        </div>

        <button 
          className="btn btn-primary btn-lg mt-4 mx-auto block" 
          onClick={onRestart}
          id="restart-assessment-btn"
        >
          Restart Assessment
        </button>
      </div>
    </div>
  );
}
