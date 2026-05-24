import './ProgressBar.css';

export default function ProgressBar({ current, total, label }) {
  return (
    <div className="progress-bar">
      <div className="progress-bar__header">
        <span className="progress-bar__label">{label}</span>
        <span className="progress-bar__count">
          {current} <span className="text-muted">of</span> {total}
        </span>
      </div>
      <div className="progress-bar__track">
        <div
          className="progress-bar__fill"
          style={{ width: `${(current / total) * 100}%` }}
        />
      </div>
      <div className="progress-bar__dots">
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={`progress-bar__dot ${i < current ? 'progress-bar__dot--done' : ''} ${i === current ? 'progress-bar__dot--active' : ''}`}
          />
        ))}
      </div>
    </div>
  );
}
