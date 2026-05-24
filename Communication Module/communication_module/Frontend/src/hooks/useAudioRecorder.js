import { useState, useRef, useCallback } from 'react';

/**
 * Converts a Float32Array of audio samples to a WAV Blob.
 */
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  // RIFF header
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');

  // fmt chunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);          // chunk size
  view.setUint16(20, 1, true);           // PCM
  view.setUint16(22, 1, true);           // mono
  view.setUint32(24, sampleRate, true);   // sample rate
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);           // block align
  view.setUint16(34, 16, true);          // bits per sample

  // data chunk
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write PCM samples (float → int16)
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Audio recorder hook using MediaRecorder + AudioContext for WAV output.
 */
export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);

  const streamRef = useRef(null);
  const contextRef = useRef(null);
  const processorRef = useRef(null);
  const samplesRef = useRef([]);
  const timerRef = useRef(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });
      contextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      samplesRef.current = [];

      processor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0);
        samplesRef.current.push(new Float32Array(channelData));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      setRecordingTime(0);
      setAudioBlob(null);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Failed to start recording:', err);
      throw err;
    }
  }, []);

  const stopRecording = useCallback(() => {
    return new Promise((resolve) => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
      }

      if (contextRef.current) {
        contextRef.current.close();
        contextRef.current = null;
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      // Merge all captured chunks
      const allSamples = samplesRef.current;
      const totalLength = allSamples.reduce((sum, arr) => sum + arr.length, 0);
      const merged = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of allSamples) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }

      const wavBlob = encodeWAV(merged, 16000);
      setAudioBlob(wavBlob);
      setIsRecording(false);
      resolve(wavBlob);
    });
  }, []);

  const clearRecording = useCallback(() => {
    setAudioBlob(null);
    setRecordingTime(0);
  }, []);

  const formattedRecordingTime = `${Math.floor(recordingTime / 60)}:${String(recordingTime % 60).padStart(2, '0')}`;

  return {
    isRecording,
    recordingTime,
    formattedRecordingTime,
    audioBlob,
    startRecording,
    stopRecording,
    clearRecording,
  };
}
