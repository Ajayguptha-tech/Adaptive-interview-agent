/**
 * Adaptive Interview Intelligence Text-to-Speech (TTS) Service
 * 
 * Provides accessible, user-initiated audio playback for interviewer questions
 * via Web Speech API with support for custom backend voice streaming.
 */

export interface TTSOptions {
  rate?: number;
  pitch?: number;
  volume?: number;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}

export class TTSService {
  private static currentUtterance: SpeechSynthesisUtterance | null = null;

  /**
   * Check if SpeechSynthesis is supported by user's browser
   */
  static isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window;
  }

  /**
   * Synthesizes and plays spoken text.
   * User-initiated only; never invoked automatically without user consent.
   */
  static speak(text: string, options: TTSOptions = {}): boolean {
    if (!this.isSupported()) {
      options.onError?.('SpeechSynthesis API is not supported in this browser.');
      return false;
    }

    try {
      this.cancel(); // Stop any previous speech

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = options.rate ?? 1.0;
      utterance.pitch = options.pitch ?? 1.0;
      utterance.volume = options.volume ?? 1.0;

      // Select natural sounding voice if available
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => 
        (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('English') || v.lang.startsWith('en')) &&
        !v.name.includes('Compact')
      );
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        options.onStart?.();
      };

      utterance.onend = () => {
        this.currentUtterance = null;
        options.onEnd?.();
      };

      utterance.onerror = (e) => {
        this.currentUtterance = null;
        options.onError?.(e.error || 'TTS Playback Error');
      };

      this.currentUtterance = utterance;
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (err) {
      console.warn('TTS speak error:', err);
      options.onError?.(err instanceof Error ? err.message : 'Unknown TTS error');
      return false;
    }
  }

  /**
   * Stop/cancel ongoing speech
   */
  static cancel(): void {
    if (this.isSupported()) {
      window.speechSynthesis.cancel();
      this.currentUtterance = null;
    }
  }

  /**
   * Pause ongoing speech
   */
  static pause(): void {
    if (this.isSupported() && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
    }
  }

  /**
   * Resume paused speech
   */
  static resume(): void {
    if (this.isSupported() && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  }

  /**
   * Check if speech is currently active
   */
  static isSpeaking(): boolean {
    return this.isSupported() && window.speechSynthesis.speaking;
  }
}
