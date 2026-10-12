import { 
  IntegrityEvent, 
  IntegritySeverity, 
  IntegrityStatus 
} from '../types';
import { apiRequest, isBackendConfigured } from '../api/apiClient';

/**
 * Agent 4: Interview Integrity Agent
 * 
 * Records objective, observable session events (acoustic anomalies, prolonged pauses,
 * window focus transitions) and queues them for human recruiter context review.
 * Strictly adheres to ethical guidelines: NEVER accuses candidate of cheating.
 */
export class InterviewIntegrityAgent {
  /**
   * Log a new telemetry observation event.
   */
  static async logEvent(params: {
    interviewId: string;
    timestampSeconds: number;
    type: IntegrityEvent['type'];
    title: string;
    description: string;
    severity?: IntegritySeverity;
    confidence?: number;
    notes?: string;
  }): Promise<{
    event: IntegrityEvent;
    source: 'backend' | 'demo';
  }> {
    const minutes = Math.floor(params.timestampSeconds / 60).toString().padStart(2, '0');
    const seconds = (params.timestampSeconds % 60).toString().padStart(2, '0');
    const timestampFormatted = `${minutes}:${seconds}`;

    const newEvent: IntegrityEvent = {
      id: `integ-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      interviewId: params.interviewId,
      timestampSeconds: params.timestampSeconds,
      timestampFormatted,
      type: params.type,
      title: params.title,
      description: params.description,
      severity: params.severity || 'low',
      confidence: params.confidence ?? 85,
      recruiterStatus: 'pending_review',
      recruiterNotes: params.notes,
    };

    if (isBackendConfigured()) {
      try {
        const remote = await apiRequest<IntegrityEvent>('/api/v1/integrity/events', {
          method: 'POST',
          body: JSON.stringify(newEvent),
        });
        if (remote) {
          return { event: remote, source: 'backend' };
        }
      } catch (err) {
        console.warn('FastAPI integrity logging failed, storing locally:', err);
      }
    }

    return { event: newEvent, source: 'demo' };
  }

  /**
   * Factory for creating browser focus loss observation.
   */
  static createFocusLossEvent(interviewId: string, timestampSeconds: number): IntegrityEvent {
    const minutes = Math.floor(timestampSeconds / 60).toString().padStart(2, '0');
    const seconds = (timestampSeconds % 60).toString().padStart(2, '0');
    return {
      id: `integ-focus-${Date.now()}`,
      interviewId,
      timestampSeconds,
      timestampFormatted: `${minutes}:${seconds}`,
      type: 'focus_loss',
      title: 'Window Focus Transition Detected',
      description: 'Candidate browser tab temporarily lost active window focus during question formulation.',
      severity: 'advisory',
      confidence: 95,
      recruiterStatus: 'pending_review',
      recruiterNotes: 'Automated telemetry observation; verify if candidate was referencing code documentation or system prompt.',
    };
  }

  /**
   * Factory for creating prolonged deliberation pause observation.
   */
  static createProlongedPauseEvent(interviewId: string, timestampSeconds: number, durationSeconds: number): IntegrityEvent {
    const minutes = Math.floor(timestampSeconds / 60).toString().padStart(2, '0');
    const seconds = (timestampSeconds % 60).toString().padStart(2, '0');
    return {
      id: `integ-pause-${Date.now()}`,
      interviewId,
      timestampSeconds,
      timestampFormatted: `${minutes}:${seconds}`,
      type: 'inactivity_window',
      title: `Extended Deliberation Window (${durationSeconds}s)`,
      description: `Candidate engaged in ${durationSeconds} seconds of silent cognitive formulation before answering.`,
      severity: 'advisory',
      confidence: 90,
      recruiterStatus: 'verified_benign',
      recruiterNotes: 'Typical cognitive deliberation for architectural problem solving.',
    };
  }

  /**
   * Factory for creating acoustic fluctuation event.
   */
  static createAcousticFluctuationEvent(interviewId: string, timestampSeconds: number, details: string): IntegrityEvent {
    const minutes = Math.floor(timestampSeconds / 60).toString().padStart(2, '0');
    const seconds = (timestampSeconds % 60).toString().padStart(2, '0');
    return {
      id: `integ-audio-${Date.now()}`,
      interviewId,
      timestampSeconds,
      timestampFormatted: `${minutes}:${seconds}`,
      type: 'audio_fluctuation',
      title: 'Acoustic Baseline Variance',
      description: `Ambient audio variance detected: ${details}`,
      severity: 'low',
      confidence: 80,
      recruiterStatus: 'pending_review',
      recruiterNotes: 'Verify microphone input sensitivity or background noise in environment.',
    };
  }
}
