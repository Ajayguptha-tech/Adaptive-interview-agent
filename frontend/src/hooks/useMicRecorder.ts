import { useState, useRef, useEffect, useCallback } from 'react';

export type MicRecorderStatus = 
  | 'idle' 
  | 'requesting' 
  | 'recording' 
  | 'paused' 
  | 'stopped' 
  | 'denied' 
  | 'unsupported';

export interface UseMicRecorderReturn {
  status: MicRecorderStatus;
  isRecording: boolean;
  audioLevel: number; // 0 - 100
  frequencyData: number[]; // 10-16 bar heights (0 - 100)
  durationSeconds: number;
  errorMessage: string | null;
  startRecording: () => Promise<boolean>;
  stopRecording: () => Promise<Blob | null>;
  pauseRecording: () => void;
  resumeRecording: () => void;
  resetRecording: () => void;
}

export function useMicRecorder(): UseMicRecorderReturn {
  const [status, setStatus] = useState<MicRecorderStatus>('idle');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [frequencyData, setFrequencyData] = useState<number[]>(new Array(12).fill(6));
  const [durationSeconds, setDurationSeconds] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  // Cleanup resources helper
  const cleanupAudio = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close();
      } catch {
        // Ignore
      }
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    setAudioLevel(0);
    setFrequencyData(new Array(12).fill(6));
  }, []);

  // Real-time audio frequency visualizer loop
  const startAudioAnalysis = useCallback((stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64; // Gives 32 frequency bins
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        // Compute average RMS/volume level
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const normalizedLevel = Math.min(100, Math.round((avg / 255) * 100));
        setAudioLevel(normalizedLevel);

        // Sample 12 frequency bars for UI waveform
        const bars: number[] = [];
        const step = Math.max(1, Math.floor(bufferLength / 12));
        for (let i = 0; i < 12; i++) {
          const val = dataArray[i * step] || 0;
          // Scale between 6% min height and 100% max height
          const barHeight = Math.max(6, Math.min(100, Math.round((val / 255) * 100)));
          bars.push(barHeight);
        }
        setFrequencyData(bars);

        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch (err) {
      console.warn('Web Audio analysis error:', err);
    }
  }, []);

  const startRecording = useCallback(async (): Promise<boolean> => {
    setErrorMessage(null);

    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus('unsupported');
      setErrorMessage('Microphone recording is not supported in this browser.');
      return false;
    }

    try {
      setStatus('requesting');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      mediaStreamRef.current = stream;
      recordedChunksRef.current = [];

      // Initialize MediaRecorder
      const options = { mimeType: 'audio/webm;codecs=opus' };
      let recorder: MediaRecorder;
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        recorder = new MediaRecorder(stream, options);
      } else {
        recorder = new MediaRecorder(stream);
      }

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };

      recorder.start(250); // Collect in 250ms chunks
      mediaRecorderRef.current = recorder;

      // Start Web Audio Analyser
      startAudioAnalysis(stream);

      // Start duration counter
      setDurationSeconds(0);
      timerIntervalRef.current = window.setInterval(() => {
        setDurationSeconds(prev => prev + 1);
      }, 1000);

      setStatus('recording');
      return true;
    } catch (err: any) {
      cleanupAudio();
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setStatus('denied');
        setErrorMessage('Microphone permission was denied. Please allow microphone access in your browser settings.');
      } else {
        setStatus('idle');
        setErrorMessage(err.message || 'Could not access microphone input device.');
      }
      return false;
    }
  }, [cleanupAudio, startAudioAnalysis]);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        cleanupAudio();
        setStatus('stopped');
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const audioBlob = new Blob(recordedChunksRef.current, { 
          type: recorder.mimeType || 'audio/webm' 
        });
        cleanupAudio();
        setStatus('stopped');
        resolve(audioBlob);
      };

      try {
        recorder.stop();
      } catch {
        cleanupAudio();
        setStatus('stopped');
        resolve(null);
      }
    });
  }, [cleanupAudio]);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      setStatus('paused');
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      timerIntervalRef.current = window.setInterval(() => {
        setDurationSeconds(prev => prev + 1);
      }, 1000);
      setStatus('recording');
    }
  }, []);

  const resetRecording = useCallback(() => {
    cleanupAudio();
    recordedChunksRef.current = [];
    setDurationSeconds(0);
    setAudioLevel(0);
    setFrequencyData(new Array(12).fill(6));
    setStatus('idle');
    setErrorMessage(null);
  }, [cleanupAudio]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  return {
    status,
    isRecording: status === 'recording',
    audioLevel,
    frequencyData,
    durationSeconds,
    errorMessage,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    resetRecording,
  };
}
