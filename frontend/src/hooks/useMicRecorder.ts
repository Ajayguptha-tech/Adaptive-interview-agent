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
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const pcmChunksRef = useRef<Float32Array[]>([]);
  const pcmSampleCountRef = useRef<number>(0);

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
    if (scriptProcessorRef.current) {
      try {
        scriptProcessorRef.current.disconnect();
        scriptProcessorRef.current.onaudioprocess = null;
      } catch {
        // Ignore
      }
      scriptProcessorRef.current = null;
    }
    if (gainNodeRef.current) {
      try {
        gainNodeRef.current.disconnect();
      } catch {
        // Ignore
      }
      gainNodeRef.current = null;
    }
    if (analyserRef.current) {
      try {
        analyserRef.current.disconnect();
      } catch {
        // Ignore
      }
      analyserRef.current = null;
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

      // Raw PCM capture for 16-bit 16kHz WAV backend compatibility
      pcmChunksRef.current = [];
      pcmSampleCountRef.current = 0;
      if (typeof audioCtx.createScriptProcessor === 'function') {
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        scriptProcessorRef.current = processor;
        processor.onaudioprocess = (event: AudioProcessingEvent) => {
          const input = event.inputBuffer.getChannelData(0);
          const copy = new Float32Array(input.length);
          copy.set(input);
          pcmChunksRef.current.push(copy);
          pcmSampleCountRef.current += copy.length;
        };

        const silenceGain = audioCtx.createGain();
        silenceGain.gain.value = 0;
        gainNodeRef.current = silenceGain;

        source.connect(processor);
        processor.connect(silenceGain);
        silenceGain.connect(audioCtx.destination);
      }

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
      pcmChunksRef.current = [];
      pcmSampleCountRef.current = 0;

      // Start Web Audio Analyser and PCM buffer capture
      startAudioAnalysis(stream);

      // Initialize MediaRecorder fallback
      try {
        const options = { mimeType: 'audio/webm;codecs=opus' };
        let recorder: MediaRecorder;
        if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          recorder = new MediaRecorder(stream, options);
        } else if (typeof MediaRecorder !== 'undefined') {
          recorder = new MediaRecorder(stream);
        } else {
          recorder = null as any;
        }

        if (recorder) {
          recorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
              recordedChunksRef.current.push(event.data);
            }
          };
          recorder.start(250);
          mediaRecorderRef.current = recorder;
        }
      } catch (recErr) {
        console.warn('MediaRecorder init fallback:', recErr);
      }

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
      const finalizeBlob = () => {
        // If PCM samples were captured from Web Audio, encode directly into 16kHz 16-bit mono WAV
        if (pcmChunksRef.current.length > 0 && pcmSampleCountRef.current > 0) {
          const totalSamples = pcmSampleCountRef.current;
          const merged = new Float32Array(totalSamples);
          let offset = 0;
          for (const chunk of pcmChunksRef.current) {
            merged.set(chunk, offset);
            offset += chunk.length;
          }
          const sampleRate = audioContextRef.current?.sampleRate || 44100;
          cleanupAudio();
          setStatus('stopped');
          const wavBlob = encodeWAV(merged, sampleRate);
          resolve(wavBlob);
          return;
        }

        // Secondary fallback to MediaRecorder Blob
        if (recordedChunksRef.current.length > 0) {
          const audioBlob = new Blob(recordedChunksRef.current, { 
            type: mediaRecorderRef.current?.mimeType || 'audio/webm' 
          });
          cleanupAudio();
          setStatus('stopped');
          resolve(audioBlob);
          return;
        }

        cleanupAudio();
        setStatus('stopped');
        resolve(null);
      };

      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        finalizeBlob();
        return;
      }

      recorder.onstop = () => {
        finalizeBlob();
      };

      try {
        recorder.stop();
      } catch {
        finalizeBlob();
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

/**
 * Encodes Float32Array PCM samples into standard 16-bit 16kHz mono WAV Blob
 */
function encodeWAV(samples: Float32Array, sampleRate: number): Blob {
  const targetSampleRate = 16000;
  let downsampled: Float32Array;

  if (sampleRate === targetSampleRate) {
    downsampled = samples;
  } else {
    const ratio = sampleRate / targetSampleRate;
    const newLength = Math.max(1, Math.round(samples.length / ratio));
    downsampled = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
      const srcIdx = Math.min(Math.round(i * ratio), samples.length - 1);
      downsampled[i] = samples[srcIdx];
    }
  }

  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = targetSampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = downsampled.length * (bitsPerSample / 8);
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeAscii(view, 8, 'WAVE');

  // fmt subchunk
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
  view.setUint16(22, numChannels, true); // NumChannels (1 = Mono)
  view.setUint32(24, targetSampleRate, true); // SampleRate (16000)
  view.setUint32(28, byteRate, true); // ByteRate
  view.setUint16(32, blockAlign, true); // BlockAlign
  view.setUint16(34, bitsPerSample, true); // BitsPerSample

  // data subchunk
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // Write PCM audio samples (clamped 16-bit integers)
  let offset = 44;
  for (let i = 0; i < downsampled.length; i++) {
    const s = Math.max(-1, Math.min(1, downsampled[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    offset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

function writeAscii(view: DataView, offset: number, string: string): void {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

