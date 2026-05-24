import './RecordButton.css';

export default function RecordButton({ isRecording, onStart, onStop, disabled }) {
  return (
    <button
      className={`record-btn ${isRecording ? 'record-btn--active' : ''}`}
      onClick={isRecording ? onStop : onStart}
      disabled={disabled}
      aria-label={isRecording ? 'Stop recording' : 'Start recording'}
      id="record-button"
    >
      <span className="record-btn__inner" />
      <span className="record-btn__label">
        {disabled ? 'Wait…' : isRecording ? 'Stop Recording' : 'Start Recording'}
      </span>
    </button>
  );
}
