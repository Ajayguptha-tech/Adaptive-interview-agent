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
  private static consecutiveErrors: number = 0;
  private static readonly MAX_CONSECUTIVE_ERRORS: number = 3;
  private static hasStartedFired: boolean = false;

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
      options.onError?.('SpeechRecognition API is not supported in this browser. Microphone audio fallback will be used.');
      return false;
    }

    try {
      this.abort(); // Cleanly abort any existing recognition session

      this.committedHistory = '';
      this.currentSessionSegments = [];
      this.currentInterim = '';
      this.isExplicitStop = false;
      this.isListening = true;
      this.consecutiveErrors = 0;
      this.hasStartedFired = false;
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
   * Detaches all listeners and safely tears down an existing recognition instance
   */
  private static detachExistingRecognition(): void {
    if (this.recognition) {
      try {
        this.recognition.onstart = null;
        this.recognition.onresult = null;
        this.recognition.onerror = null;
        this.recognition.onend = null;
        this.recognition.abort();
      } catch {
        // Ignore abort errors
      }
      this.recognition = null;
    }
  }

  /**
   * Initializes and starts a fresh SpeechRecognition session
   */
  private static initSession(): boolean {
    if (!this.isListening || this.isExplicitStop) return false;

    const SpeechRecognitionConstructor = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionConstructor) return false;

    try {
      // Never call start() on an ended instance — cleanly teardown previous instance
      this.detachExistingRecognition();

      const rec = new SpeechRecognitionConstructor();
      rec.continuous = this.activeOptions?.continuous ?? true;
      rec.interimResults = true;
      rec.lang = this.activeOptions?.lang || 'en-US';

      rec.onstart = () => {
        STTService.isListening = true;
        STTService.consecutiveErrors = 0;
        if (!STTService.hasStartedFired) {
          STTService.hasStartedFired = true;
          STTService.activeOptions?.onStart?.();
        }
      };

      rec.onresult = (event: any) => {
        STTService.consecutiveErrors = 0;
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
        const errorKey = event?.error || 'speech_recognition_error';

        if (errorKey === 'not-allowed' || errorKey === 'service-not-allowed') {
          STTService.isListening = false;
          STTService.isExplicitStop = true;
          STTService.activeOptions?.onError?.('Microphone access denied. Please grant microphone permission in your browser.');
          return;
        }

        if (errorKey === 'audio-capture') {
          STTService.isListening = false;
          STTService.isExplicitStop = true;
          STTService.activeOptions?.onError?.('No microphone detected. Please connect an audio input device.');
          return;
        }

        if (errorKey === 'no-speech') {
          // Normal pause in speech; do not abort session, allow seamless bounded restart
          return;
        }

        if (errorKey === 'aborted') {
          // Normal during stop/abort, ignore
          return;
        }

        STTService.consecutiveErrors++;
        if (errorKey === 'network') {
          if (STTService.consecutiveErrors >= STTService.MAX_CONSECUTIVE_ERRORS) {
            STTService.isListening = false;
            STTService.isExplicitStop = true;
            STTService.activeOptions?.onError?.('Speech recognition network error. Your answer will be transcribed from audio upon finishing.');
          }
          return;
        }

        if (STTService.consecutiveErrors >= STTService.MAX_CONSECUTIVE_ERRORS) {
          STTService.isListening = false;
          STTService.isExplicitStop = true;
          STTService.activeOptions?.onError?.(`Speech recognition encountered repeated errors: ${errorKey}. Audio will be transcribed upon finishing.`);
        }
      };

      rec.onend = () => {
        // Flush any pending interim speech so words before pause are preserved
        if (STTService.currentInterim && STTService.currentInterim.trim()) {
          STTService.currentSessionSegments.push(STTService.currentInterim.trim());
          STTService.currentInterim = '';
        }

        const sessionFinal = STTService.currentSessionSegments.filter(Boolean).join(' ').trim();
        if (sessionFinal) {
          STTService.committedHistory = (
            (STTService.committedHistory ? `${STTService.committedHistory} ` : '') + sessionFinal
          ).trim();
        }
        STTService.currentSessionSegments = [];

        // If recognition closed unexpectedly or paused and candidate hasn't finished, restart safely
        if (
          STTService.isListening && 
          !STTService.isExplicitStop && 
          STTService.consecutiveErrors < STTService.MAX_CONSECUTIVE_ERRORS
        ) {
          STTService.activeOptions?.onTranscriptUpdate?.({
            finalText: STTService.committedHistory,
            interimText: '',
            fullText: STTService.committedHistory,
          });

          clearTimeout(STTService.restartTimer);
          STTService.restartTimer = setTimeout(() => {
            if (STTService.isListening && !STTService.isExplicitStop) {
              STTService.initSession();
            }
          }, 100);
          return;
        }

        STTService.isListening = false;
        STTService.detachExistingRecognition();
        STTService.activeOptions?.onEnd?.();
      };

      rec.start();
      this.recognition = rec;
      return true;
    } catch (err) {
      console.warn('STT session init error:', err);
      STTService.consecutiveErrors++;
      if (STTService.consecutiveErrors >= STTService.MAX_CONSECUTIVE_ERRORS) {
        STTService.isListening = false;
      }
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
    if (sessionFinal) {
      this.committedHistory = (
        (this.committedHistory ? `${this.committedHistory} ` : '') + sessionFinal
      ).trim();
    }
    this.currentSessionSegments = [];

    this.detachExistingRecognition();

    return this.committedHistory;
  }

  /**
   * Immediately aborts speech recognition without waiting for audio buffers
   */
  static abort(): void {
    this.isExplicitStop = true;
    this.isListening = false;
    clearTimeout(this.restartTimer);
    this.detachExistingRecognition();
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
    this.consecutiveErrors = 0;
    this.hasStartedFired = false;
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
