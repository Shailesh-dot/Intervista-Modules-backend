import { useState } from 'react';
import Welcome from './components/Welcome';
import Speaking from './components/Speaking';
import Listening from './components/Listening';
import Results from './components/Results';
import './App.css';

function App() {
  const [phase, setPhase] = useState('welcome'); // welcome | speaking | listening | results
  const [speakingResults, setSpeakingResults] = useState([]);
  const [listeningResults, setListeningResults] = useState(null);
  const [interviewId, setInterviewId] = useState(null);

  const handleStart = () => {
    setPhase('speaking');
  };

  const handleSpeakingComplete = (results) => {
    setSpeakingResults(results || []);
    setPhase('listening');
  };

  const handleListeningComplete = (results) => {
    setListeningResults(results);
    setPhase('results');
  };

  const handleRestart = () => {
    setPhase('welcome');
    setSpeakingResults([]);
    setListeningResults(null);
    setInterviewId(null);
  };

  return (
    <div className="app">
      {phase === 'welcome' && <Welcome onStart={handleStart} />}
      {phase === 'speaking' && (
        <Speaking 
          interviewId={interviewId} 
          setInterviewId={setInterviewId} 
          onComplete={handleSpeakingComplete} 
        />
      )}
      {phase === 'listening' && (
        <Listening 
          interviewId={interviewId} 
          setInterviewId={setInterviewId} 
          onComplete={handleListeningComplete} 
        />
      )}
      {phase === 'results' && (
        <Results 
          speakingResults={speakingResults} 
          listeningResults={listeningResults} 
          onRestart={handleRestart} 
        />
      )}
    </div>
  );
}

export default App;
