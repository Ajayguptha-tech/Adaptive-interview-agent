/**
 * Adaptive Interview Intelligence Speech-to-Text (STT) Service
 * 
 * Provides resilient, real-time streaming speech transcription using Web Speech API
 * with index-based segment tracking, seamless silence-restart continuity,
 * and duplicate-prevention across pauses.
 */

// Declare browser SpeechRecognition global types
type SpeechRecognitionType = any;

export interface STTTranscriptState {
  finalText: string;
  interimText: string;
  fullText: string;
}

export interface STTOptions {
  onTranscriptUpdate?: (state: STTTranscriptState) => void;
  onInterimResult?: (text: string) => void;
  onFinalResult?: (text: string) => void;
  onStart?: () => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
  lang?: string;
  continuous?: boolean;
}

export class STTService {
  private static recognition: SpeechRecognitionType | null = null;
  private static isListening: boolean = false;
  private static isExplicitStop: boolean = false;
  private static committedHistory: string = '';
  private static currentSessionSegments: string[] = [];
  private static currentInterim: string = '';
  private static activeOptions: STTOptions | null = null;
  private static restartTimer: any = null;

  /**
   * Check if SpeechRecognition is supported by user's browser
   */
  static isSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return !!(
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition
    );
  }

  /**
   * Start streaming speech recognition for a new answer attempt.
   * Completely resets internal transcript buffers to prevent duplicate text.
   */
  static start(options: STTOptions = {}): boolean {
    if (!this.isSupported()) {
      options.onError?.('SpeechRecognition API is not supported in this browser. Please use Google Chrome, Microsoft Edge, or audio upload fallback.');
      return false;
    }

    try {
      this.abort(); // Cleanly abort any existing recognition session

      this.committedHistory = '';
      this.currentSessionSegments = [];
      this.currentInterim = '';
      this.isExplicitStop = false;
      this.isListening = true;
      this.activeOptions = options;

      return this.initSession();
    } catch (err) {
      console.warn('STT start error:', err);
      this.isListening = false;
      this.recognition = null;
      options.onError?.(err instanceof Error ? err.message : 'Failed to start speech recognition');
      return false;
    }
  }

  /**
   * Initializes and starts a single SpeechRecognition session
   */
  private static initSession(): boolean {
    if (!this.isListening || this.isExplicitStop) return false;

    const SpeechRecognitionConstructor = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionConstructor) return false;

    try {
      const rec = new SpeechRecognitionConstructor();
      rec.continuous = this.activeOptions?.continuous ?? true;
      rec.interimResults = true;
      rec.lang = this.activeOptions?.lang || 'en-US';

      rec.onstart = () => {
        STTService.isListening = true;
        STTService.activeOptions?.onStart?.();
      };

      rec.onresult = (event: any) => {
        let interimText = '';

        // Process SpeechRecognitionResultList index-by-index within current session
        for (let i = 0; i < event.results.length; ++i) {
          const resultItem = event.results[i];
          const segmentText = resultItem[0]?.transcript?.trim() || '';

          if (resultItem.isFinal) {
            // Commit final segment at its exact index — never duplicates previously committed segments
            if (segmentText) {
              STTService.currentSessionSegments[i] = segmentText;
            }
          } else {
            // Accumulate currently active uncommitted interim speech
            if (segmentText) {
              interimText = interimText ? `${interimText} ${segmentText}` : segmentText;
            }
          }
        }

        STTService.currentInterim = interimText;

        const sessionFinal = STTService.currentSessionSegments.filter(Boolean).join(' ').trim();
        const completeFinal = (
          (STTService.committedHistory ? `${STTService.committedHistory} ` : '') + sessionFinal
        ).trim();

        const fullTranscript = (
          completeFinal + (interimText ? (completeFinal ? ' ' : '') + interimText : '')
        ).trim();

        // Deliver authoritative, non-duplicated transcript states to callbacks
        STTService.activeOptions?.onTranscriptUpdate?.({
          finalText: completeFinal,
          interimText: interimText,
          fullText: fullTranscript,
        });

        if (STTService.activeOptions?.onFinalResult && completeFinal) {
          STTService.activeOptions.onFinalResult(completeFinal);
        }
        if (STTService.activeOptions?.onInterimResult) {
          STTService.activeOptions.onInterimResult(interimText);
        }
      };

      rec.onerror = (event: any) => {
        const errorKey = event.error || 'speech_recognition_error';
        let errorMsg = 'Speech recognition error';

        if (errorKey === 'not-allowed') {
          errorMsg = 'Microphone access denied. Please click "Enable Microphone" or grant permission in your browser.';
          STTService.isListening = false;
          STTService.activeOptions?.onError?.(errorMsg);
        } else if (errorKey === 'no-speech') {
          // Normal pause in speech; do not abort the session, allow onend to restart seamlessly
          return;
        } else if (errorKey === 'network') {
          errorMsg = 'Network error during cloud speech recognition. Audio will be transcribed via backend fallback.';
          STTService.activeOptions?.onError?.(errorMsg);
        } else if (errorKey === 'aborted') {
          // Normal during stop/abort, ignore
          return;
        } else {
          STTService.activeOptions?.onError?.(errorMsg);
        }
      };

      rec.onend = () => {
        // If recognition closed unexpectedly or paused and candidate hasn't finished, restart
        if (STTService.isListening && !STTService.isExplicitStop) {
          const sessionFinal = STTService.currentSessionSegments.filter(Boolean).join(' ').trim();
          if (sessionFinal) {
            STTService.committedHistory = (
              (STTService.committedHistory ? `${STTService.committedHistory} ` : '') + sessionFinal
            ).trim();
          }
          STTService.currentSessionSegments = [];
          STTService.currentInterim = '';

          clearTimeout(STTService.restartTimer);
          STTService.restartTimer = setTimeout(() => {
            if (STTService.isListening && !STTService.isExplicitStop) {
              STTService.initSession();
            }
          }, 120);
          return;
        }

        STTService.isListening = false;
        STTService.recognition = null;
        STTService.activeOptions?.onEnd?.();
      };

      rec.start();
      this.recognition = rec;
      return true;
    } catch (err) {
      console.warn('STT session init error:', err);
      return false;
    }
  }

  /**
   * Stops recognition, commits any pending interim words, and returns authoritative final transcript.
   */
  static stop(): string {
    this.isExplicitStop = true;
    this.isListening = false;
    clearTimeout(this.restartTimer);

    // Flush any pending interim text into final transcript so no words are dropped
    if (this.currentInterim && this.currentInterim.trim()) {
      this.currentSessionSegments.push(this.currentInterim.trim());
      this.currentInterim = '';
    }

    const sessionFinal = this.currentSessionSegments.filter(Boolean).join(' ').trim();
    const completeFinal = (
      (this.committedHistory ? `${this.committedHistory} ` : '') + sessionFinal
    ).trim();

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore if already inactive
      }
      this.recognition = null;
    }

    return completeFinal;
  }

  /**
   * Immediately aborts speech recognition without waiting for audio buffers
   */
  static abort(): void {
    this.isExplicitStop = true;
    this.isListening = false;
    clearTimeout(this.restartTimer);
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Ignore
      }
      this.recognition = null;
    }
    this.currentInterim = '';
  }

  /**
   * Resets all internal buffers for a fresh question attempt
   */
  static reset(): void {
    this.abort();
    this.committedHistory = '';
    this.currentSessionSegments = [];
    this.currentInterim = '';
    this.activeOptions = null;
  }

  /**
   * Returns authoritative accumulated final transcript text
   */
  static getFinalTranscript(): string {
    const sessionFinal = this.currentSessionSegments.filter(Boolean).join(' ').trim();
    return (
      (this.committedHistory ? `${this.committedHistory} ` : '') + sessionFinal
    ).trim();
  }

  /**
   * Check if currently listening
   */
  static getIsListening(): boolean {
    return this.isListening;
  }
}
