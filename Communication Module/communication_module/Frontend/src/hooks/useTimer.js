import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Countdown timer hook
 * @param {number} initialSeconds
 * @param {function} onComplete  called when timer reaches 0
 */
export function useTimer(initialSeconds, onComplete) {
  const [seconds, setSeconds] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const start = useCallback(() => {
    setSeconds(initialSeconds);
    setIsRunning(true);
  }, [initialSeconds]);

  const stop = useCallback(() => {
    setIsRunning(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback((newSeconds) => {
    stop();
    setSeconds(newSeconds ?? initialSeconds);
  }, [initialSeconds, stop]);

  useEffect(() => {
    if (!isRunning) return;

    intervalRef.current = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          setIsRunning(false);
          setTimeout(() => onCompleteRef.current?.(), 0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isRunning]);

  const progress = 1 - seconds / initialSeconds;
  const formattedTime = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

  return { seconds, isRunning, progress, formattedTime, start, stop, reset };
}
