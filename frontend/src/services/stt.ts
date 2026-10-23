/**
 * Adaptive Interview Intelligence Speech-to-Text (STT) Service
 * 
 * Provides real-time streaming audio transcription using Web Speech API
 * with graceful fallback and error handling.
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
  private static finalSegments: string[] = [];
  private static currentInterim: string = '';
  private static activeOptions: STTOptions | null = null;

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
      options.onError?.('SpeechRecognition API is not supported in this browser. Please use Google Chrome, Microsoft Edge, or text entry.');
      return false;
    }

    try {
      this.abort(); // Cleanly abort any existing recognition session

      const SpeechRecognitionConstructor = 
        (window as any).SpeechRecognition || 
        (window as any).webkitSpeechRecognition;

      const rec = new SpeechRecognitionConstructor();
      rec.continuous = options.continuous ?? true;
      rec.interimResults = true;
      rec.lang = options.lang || 'en-US';

      this.finalSegments = [];
      this.currentInterim = '';
      this.isExplicitStop = false;
      this.activeOptions = options;

      rec.onstart = () => {
        STTService.isListening = true;
        options.onStart?.();
      };

      rec.onresult = (event: any) => {
        let interimText = '';

        // Process SpeechRecognitionResultList index-by-index
        for (let i = 0; i < event.results.length; ++i) {
          const resultItem = event.results[i];
          const segmentText = resultItem[0]?.transcript?.trim() || '';

          if (resultItem.isFinal) {
            // Commit final segment at its exact index — never duplicates previously committed segments
            if (segmentText) {
              STTService.finalSegments[i] = segmentText;
            }
          } else {
            // Accumulate currently active uncommitted interim speech
            if (segmentText) {
              interimText = interimText ? `${interimText} ${segmentText}` : segmentText;
            }
          }
        }

        STTService.currentInterim = interimText;

        const completeFinal = STTService.finalSegments.filter(Boolean).join(' ').trim();
        const fullTranscript = (
          completeFinal + (interimText ? (completeFinal ? ' ' : '') + interimText : '')
        ).trim();

        // Deliver authoritative, non-duplicated transcript states to callbacks
        options.onTranscriptUpdate?.({
          finalText: completeFinal,
          interimText: interimText,
          fullText: fullTranscript,
        });

        if (options.onFinalResult && completeFinal) {
          options.onFinalResult(completeFinal);
        }
        if (options.onInterimResult) {
          options.onInterimResult(interimText);
        }
      };

      rec.onerror = (event: any) => {
        const errorKey = event.error || 'speech_recognition_error';
        let errorMsg = 'Speech recognition error';

        if (errorKey === 'not-allowed') {
          errorMsg = 'Microphone access denied. Please click "Enable Microphone" or grant permission in your browser.';
          STTService.isListening = false;
        } else if (errorKey === 'no-speech') {
          errorMsg = 'No speech detected in audio stream.';
        } else if (errorKey === 'network') {
          errorMsg = 'Network error during speech recognition.';
        } else if (errorKey === 'aborted') {
          // Normal during stop/abort, ignore
          return;
        }

        options.onError?.(errorMsg);
      };

      rec.onend = () => {
        // If recognition closed unexpectedly and candidate hasn't finished, restart
        if (STTService.isListening && !STTService.isExplicitStop && STTService.recognition) {
          try {
            rec.start();
            return;
          } catch {
            // Fallthrough to teardown
          }
        }

        STTService.isListening = false;
        STTService.recognition = null;
        options.onEnd?.();
      };

      rec.start();
      this.recognition = rec;
      return true;
    } catch (err) {
      console.warn('STT start error:', err);
      this.isListening = false;
      this.recognition = null;
      options.onError?.(err instanceof Error ? err.message : 'Failed to start speech recognition');
      return false;
    }
  }

  /**
   * Stops recognition, commits any pending interim words, and returns authoritative final transcript.
   */
  static stop(): string {
    this.isExplicitStop = true;
    this.isListening = false;

    // Flush any pending interim text into final transcript so no words are dropped
    if (this.currentInterim && this.currentInterim.trim()) {
      this.finalSegments.push(this.currentInterim.trim());
      this.currentInterim = '';
    }

    const completeFinal = this.finalSegments.filter(Boolean).join(' ').trim();

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
    this.finalSegments = [];
    this.currentInterim = '';
    this.activeOptions = null;
  }

  /**
   * Returns authoritative accumulated final transcript text
   */
  static getFinalTranscript(): string {
    return this.finalSegments.filter(Boolean).join(' ').trim();
  }

  /**
   * Check if currently listening
   */
  static getIsListening(): boolean {
    return this.isListening;
  }
}
