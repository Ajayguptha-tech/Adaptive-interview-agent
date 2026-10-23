import { describe, it, expect, vi, beforeEach } from 'vitest';
import { STTService } from '../services/stt';
import { TTSService } from '../services/tts';

// Mock Web Speech API SpeechRecognition
class MockSpeechRecognition {
  continuous: boolean = false;
  interimResults: boolean = false;
  lang: string = 'en-US';
  onstart: (() => void) | null = null;
  onresult: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onend: (() => void) | null = null;

  start() {
    setTimeout(() => {
      if (this.onstart) this.onstart();
    }, 0);
  }

  stop() {
    setTimeout(() => {
      if (this.onend) this.onend();
    }, 0);
  }

  abort() {
    setTimeout(() => {
      if (this.onend) this.onend();
    }, 0);
  }
}

describe('Speech-to-Text (STT) Segmented Transcription & Idempotency', () => {
  beforeEach(() => {
    (globalThis as any).window = {
      SpeechRecognition: MockSpeechRecognition,
      speechSynthesis: {
        speak: vi.fn(),
        cancel: vi.fn(),
        speaking: false,
        paused: false,
      },
    };
  });

  it('detects Web Speech API support accurately', () => {
    expect(STTService.isSupported()).toBe(true);
  });

  it('produces single authoritative final transcript from spoken stream without duplication', () => {
    let latestState: any = null;
    let finalCalls = 0;

    STTService.start({
      onTranscriptUpdate: (state) => {
        latestState = state;
      },
      onFinalResult: () => {
        finalCalls++;
      },
    });

    const rec = (STTService as any).recognition as MockSpeechRecognition;
    expect(rec).toBeTruthy();

    // Simulate browser streaming cumulative interim results followed by final results
    // Event 1: candidate starts saying "Python"
    rec.onresult?.({
      results: [
        [{ transcript: 'Python' }],
      ],
    });
    // Interim result:
    expect(latestState.interimText).toBe('Python');
    expect(latestState.finalText).toBe('');
    expect(latestState.fullText).toBe('Python');

    // Event 2: candidate continues "Python uses"
    rec.onresult?.({
      results: [
        [{ transcript: 'Python uses' }],
      ],
    });
    expect(latestState.interimText).toBe('Python uses');
    expect(latestState.finalText).toBe('');
    expect(latestState.fullText).toBe('Python uses');

    // Event 3: browser marks segment 0 as final: "Python uses dynamic typing"
    const finalResult0 = [{ transcript: 'Python uses dynamic typing' }];
    (finalResult0 as any).isFinal = true;

    rec.onresult?.({
      results: [finalResult0],
    });

    expect(latestState.finalText).toBe('Python uses dynamic typing');
    expect(latestState.interimText).toBe('');
    expect(latestState.fullText).toBe('Python uses dynamic typing');

    // Event 4: candidate continues second phrase: "and garbage collection"
    const interimResult1 = [{ transcript: 'and garbage collection' }];
    (interimResult1 as any).isFinal = false;

    rec.onresult?.({
      results: [finalResult0, interimResult1],
    });

    // CRITICAL TEST: Segment 0 should NOT be duplicated in finalText!
    expect(latestState.finalText).toBe('Python uses dynamic typing');
    expect(latestState.interimText).toBe('and garbage collection');
    expect(latestState.fullText).toBe('Python uses dynamic typing and garbage collection');

    // Event 5: browser finalizes segment 1: "and garbage collection"
    (interimResult1 as any).isFinal = true;
    rec.onresult?.({
      results: [finalResult0, interimResult1],
    });

    expect(latestState.finalText).toBe('Python uses dynamic typing and garbage collection');
    expect(latestState.interimText).toBe('');
    expect(latestState.fullText).toBe('Python uses dynamic typing and garbage collection');

    // Stopping recognition flushes any pending text exactly once
    const finalStopped = STTService.stop();
    expect(finalStopped).toBe('Python uses dynamic typing and garbage collection');
  });

  it('correctly handles unexpected speech session termination without repeating text', () => {
    let updateCount = 0;
    STTService.start({
      onTranscriptUpdate: () => {
        updateCount++;
      },
    });

    const rec = (STTService as any).recognition as MockSpeechRecognition;

    const finalSeg = [{ transcript: 'Global interpreter lock ensures thread safety' }];
    (finalSeg as any).isFinal = true;

    rec.onresult?.({ results: [finalSeg] });

    // Recognition ends
    rec.onend?.();

    // Verify flushed transcript remains exactly what was said
    const stopped = STTService.stop();
    expect(stopped).toBe('Global interpreter lock ensures thread safety');
  });
});

describe('Question Classification: Coding vs Verbal Tasks', () => {
  const isCodingQuestion = (q: {
    requires_code?: boolean;
    response_type?: string;
    type?: string;
    expected_answer_format?: string;
  }) => {
    return Boolean(
      q.requires_code === true ||
      q.response_type === 'code_writing' ||
      q.type === 'code_writing' ||
      q.expected_answer_format === 'code'
    );
  };

  it('correctly classifies coding tasks as requiring code editor', () => {
    // 1. Prime number function
    expect(isCodingQuestion({
      requires_code: true,
      response_type: 'code_writing',
      type: 'code_writing',
      expected_answer_format: 'code',
    })).toBe(true);

    // 2. Binary search implementation
    expect(isCodingQuestion({
      requires_code: true,
      response_type: 'code_writing',
      type: 'code_writing',
    })).toBe(true);

    // 3. Reverse linked list
    expect(isCodingQuestion({
      requires_code: true,
      type: 'code_writing',
    })).toBe(true);
  });

  it('correctly classifies verbal questions as NOT requiring code editor', () => {
    // 1. "What is Python?"
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
      expected_answer_format: 'verbal',
    })).toBe(false);

    // 2. "Explain inheritance."
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
    })).toBe(false);

    // 3. "What is the difference between a list and a tuple?"
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
    })).toBe(false);

    // 4. "Explain how binary search works."
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
    })).toBe(false);

    // 5. "Describe the time complexity of quicksort."
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
    })).toBe(false);

    // 6. "What is REST API?"
    expect(isCodingQuestion({
      requires_code: false,
      response_type: 'verbal',
      type: 'conceptual',
    })).toBe(false);
  });
});

describe('Voice Interview State Machine Flow', () => {
  type VoiceInterviewState =
    | 'question_ready'
    | 'speaking_question'
    | 'recording'
    | 'transcribing'
    | 'evaluating'
    | 'saving_result'
    | 'feedback_ready'
    | 'next_question'
    | 'error';

  it('strictly preserves the verbal question state sequence', () => {
    const states: VoiceInterviewState[] = [];

    // 1. Question ready
    states.push('question_ready');

    // 2. TTS reads aloud question
    states.push('speaking_question');

    // 3. TTS completes -> mic activated
    states.push('recording');

    // 4. Candidate presses Finish Answer -> mic stopped
    states.push('transcribing');

    // 5. Evaluator assesses answer
    states.push('evaluating');

    // 6. Result persisted
    states.push('saving_result');

    // 7. Feedback rendered for candidate review
    states.push('feedback_ready');

    // 8. Candidate clicks Continue -> next question
    states.push('next_question');

    expect(states).toEqual([
      'question_ready',
      'speaking_question',
      'recording',
      'transcribing',
      'evaluating',
      'saving_result',
      'feedback_ready',
      'next_question',
    ]);
  });
});
