/**
 * Adaptive Interview Intelligence Speech-to-Text (STT) Service
 * 
 * Provides real-time streaming audio transcription using Web Speech API
 * with graceful fallback and error handling.
 */

// Declare browser SpeechRecognition global types
type SpeechRecognitionType = any;

export interface STTOptions {
  onInterimResult?: (text: string) => void;
  onFinalResult?: (text: string) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
  lang?: string;
  continuous?: boolean;
}

export class STTService {
  private static recognition: SpeechRecognitionType | null = null;
  private static isListening: boolean = false;

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
   * Start streaming speech recognition.
   */
  static start(options: STTOptions = {}): boolean {
    if (!this.isSupported()) {
      options.onError?.('SpeechRecognition API is not supported in this browser. Please use Chrome/Edge or manual text input.');
      return false;
    }

    try {
      this.stop(); // Stop any previous session

      const SpeechRecognitionConstructor = 
        (window as any).SpeechRecognition || 
        (window as any).webkitSpeechRecognition;

      const rec = new SpeechRecognitionConstructor();
      rec.continuous = options.continuous ?? true;
      rec.interimResults = true;
      rec.lang = options.lang || 'en-US';

      rec.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            finalTranscript += item[0].transcript;
          } else {
            interimTranscript += item[0].transcript;
          }
        }

        if (interimTranscript) {
          options.onInterimResult?.(interimTranscript);
        }
        if (finalTranscript) {
          options.onFinalResult?.(finalTranscript);
        }
      };

      rec.onerror = (event: any) => {
        let errorMsg = event.error || 'Speech recognition error';
        if (event.error === 'not-allowed') {
          errorMsg = 'Microphone access denied. Please enable microphone permissions in your browser.';
        } else if (event.error === 'no-speech') {
          errorMsg = 'No speech detected in audio stream.';
        } else if (event.error === 'network') {
          errorMsg = 'Network error during speech recognition.';
        }
        options.onError?.(errorMsg);
      };

      rec.onend = () => {
        this.isListening = false;
        options.onEnd?.();
      };

      rec.start();
      this.recognition = rec;
      this.isListening = true;
      return true;
    } catch (err) {
      console.warn('STT start error:', err);
      options.onError?.(err instanceof Error ? err.message : 'Failed to start speech recognition');
      return false;
    }
  }

  /**
   * Stop speech recognition
   */
  static stop(): void {
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore if already stopped
      }
      this.recognition = null;
    }
    this.isListening = false;
  }

  /**
   * Check if currently listening
   */
  static getIsListening(): boolean {
    return this.isListening;
  }
}
