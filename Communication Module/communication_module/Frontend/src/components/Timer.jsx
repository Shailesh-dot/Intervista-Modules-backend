import { useMemo } from 'react';
import './Timer.css';

export default function Timer({ seconds, totalSeconds, label, variant = 'prep' }) {
  const progress = 1 - seconds / totalSeconds;
  const formattedTime = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

  // SVG circle dimensions
  const size = 140;
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - progress);

  const colorClass = variant === 'recording' ? 'timer--recording' : 'timer--prep';
  const isUrgent = variant === 'prep' && seconds <= 10 && seconds > 0;

  return (
    <div className={`timer ${colorClass} ${isUrgent ? 'timer--urgent' : ''}`}>
      <svg className="timer__svg" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <circle
          className="timer__track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress circle */}
        <circle
          className="timer__progress"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="timer__content">
        <span className="timer__time">{formattedTime}</span>
        {label && <span className="timer__label">{label}</span>}
      </div>
    </div>
  );
}
