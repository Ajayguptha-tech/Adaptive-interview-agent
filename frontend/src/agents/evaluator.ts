import { 
  InterviewQuestion, 
  EvaluationRubric, 
  Evidence, 
  EvaluationResult,
  Competency
} from '../types';
import { apiRequest, isBackendConfigured } from '../api/apiClient';

/**
 * Agent 3: Answer Evaluation Agent
 * 
 * Evaluates spoken candidate responses against structured rubrics, extracting
 * transcript quotations, scoring criteria, measuring decoupled confidence,
 * and identifying missing information.
 */
export class AnswerEvaluationAgent {
  /**
   * Evaluate a candidate response transcript against the interview rubric.
   */
  static async evaluateAnswer(params: {
    interviewId: string;
    question: InterviewQuestion;
    transcriptText: string;
    rubric: EvaluationRubric;
    competencies: Competency[];
    sessionTimestampSeconds: number;
  }): Promise<{
    result: EvaluationResult;
    source: 'backend' | 'demo';
  }> {
    if (isBackendConfigured()) {
      try {
        const remoteResult = await apiRequest<EvaluationResult>(
          `/api/v1/evaluator/evaluate-answer`,
          {
            method: 'POST',
            body: JSON.stringify(params),
          }
        );
        if (remoteResult) {
          return { result: remoteResult, source: 'backend' };
        }
      } catch (err) {
        console.warn('FastAPI evaluator failed, falling back to local evaluator agent:', err);
      }
    }

    const result = this.evaluateLocalAnswer(params);
    return { result, source: 'demo' };
  }

  /**
   * Client-side rubric-driven evaluation engine.
   * Extracts verbatim quotes and maps to rubric criteria with objective confidence.
   */
  static evaluateLocalAnswer(params: {
    interviewId: string;
    question: InterviewQuestion;
    transcriptText: string;
    rubric: EvaluationRubric;
    competencies: Competency[];
    sessionTimestampSeconds: number;
  }): EvaluationResult {
    const { interviewId, question, transcriptText, rubric, competencies, sessionTimestampSeconds } = params;
    const cleanText = transcriptText.trim();
    const minutes = Math.floor(sessionTimestampSeconds / 60).toString().padStart(2, '0');
    const seconds = (sessionTimestampSeconds % 60).toString().padStart(2, '0');
    const formattedTimestamp = `${minutes}:${seconds}`;

    // Target competency mapping
    const targetCompIds = question.targetCompetencies;
    const targetComp = competencies.find(c => targetCompIds.includes(c.id)) || competencies[0];
    const targetCompName = targetComp ? targetComp.name : 'Technical Execution';

    // Find applicable rubric criteria
    const relevantCriteria = rubric.criteria.filter(crit => 
      targetCompIds.includes(crit.competencyId)
    );

    // Sentence extraction for evidence quotes
    const sentences = cleanText
      .split(/(?<=[.?!])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 15);

    const extractedEvidence: Evidence[] = [];
    const missingInformation: string[] = [];
    const demonstratedCompetencies: string[] = [];
    const unaddressedCompetencies: string[] = [];

    // Analyze text depth and indicators
    const lowerText = cleanText.toLowerCase();

    // Specific domain keywords for validation
    const positiveKeywords = [
      'memo', 'usememo', 'usecallback', 'reconciliation', 'scheduler', 'transitions',
      'concurrent', 'starttransition', 'batching', 'virtualize', 'virtual', 'worker', 'debounce',
      'generics', 'infer', 'discriminating union', 'aria', 'focus trap', 'wcag', 'keyboard',
      'screen reader', 'lighthouse', 'inp', 'profiler', 'profiling', 'trade-off', 'benchmark',
      'latency', 'cache', 'measure', 'incident', 'production', 'telemetry', 'subscription'
    ];

    const matchedKeywords = positiveKeywords.filter(kw => lowerText.includes(kw));

    // Formulate quotes and score impacts
    if (sentences.length > 0) {
      // Pick the best 1 to 3 substantive sentences as verifiable quotations
      const substantiveSentences = sentences
        .sort((a, b) => b.length - a.length)
        .slice(0, Math.min(3, sentences.length));

      substantiveSentences.forEach((sentence, idx) => {
        const containsStrongSignal = positiveKeywords.some(kw => sentence.toLowerCase().includes(kw));
        const impactScore = containsStrongSignal ? 8 + idx * 2 : 4;
        const confidenceBoost = containsStrongSignal ? 14 : 8;

        extractedEvidence.push({
          id: `ev-${Date.now()}-${idx}`,
          interviewId,
          questionId: question.id,
          timestamp: formattedTimestamp,
          quote: `"${sentence}"`,
          competencyId: targetComp?.id || 'comp-general',
          competencyName: targetCompName,
          scoreImpact: impactScore,
          confidenceImpact: confidenceBoost,
          rationale: containsStrongSignal
            ? `Candidate articulated concrete engineering mechanism ("${matchedKeywords.slice(0, 2).join(', ')}") aligning with Proficient criteria.`
            : 'General experiential statement without deep telemetry or quantitative metrics.',
          signalStrength: containsStrongSignal ? 'high' : 'medium',
        });
      });
    }

    // Determine score & missing info
    let overallScore = 65; // Baseline
    let confidenceScore = 60;

    if (cleanText.length < 50 || matchedKeywords.length === 0) {
      // Incomplete, brief, or superficial response without technical mechanisms
      overallScore = matchedKeywords.length === 0 ? 50 : 40;
      confidenceScore = 50;
      missingInformation.push('Concrete technical mechanisms, architecture patterns, or code implementation details.');
      missingInformation.push('Explanation of failure modes, edge-case handling, or performance telemetry.');
      unaddressedCompetencies.push(targetComp?.id || 'comp-general');
    } else if (matchedKeywords.length >= 3) {
      // High technical depth
      overallScore = Math.min(95, 76 + matchedKeywords.length * 3);
      confidenceScore = Math.min(96, 70 + matchedKeywords.length * 4);
      demonstratedCompetencies.push(targetComp?.id || 'comp-general');
      if (!lowerText.includes('trade-off') && !lowerText.includes('downside')) {
        missingInformation.push('Explicit architectural trade-offs or memory/performance downsides of chosen approach.');
      }
    } else {
      // Proficient / moderate technical depth (1-2 strong mechanisms identified)
      overallScore = 75 + matchedKeywords.length * 2;
      confidenceScore = 70 + matchedKeywords.length * 3;
      demonstratedCompetencies.push(targetComp?.id || 'comp-general');
      missingInformation.push('Specific metrics, benchmarking methodology, or browser profiler observations.');
    }

    const rubricFeedback = overallScore >= 80
      ? `Strong demonstration of ${targetCompName}. Candidate substantiated claim with verifiable mechanisms (${matchedKeywords.join(', ') || 'clear concepts'}).`
      : `Acceptable baseline understanding of ${targetCompName}, but lacked discussion of: ${missingInformation.join('; ')}.`;

    return {
      questionId: question.id,
      transcriptText: cleanText,
      overallScore,
      confidenceScore,
      extractedEvidence,
      missingInformation,
      unaddressedCompetencies,
      demonstratedCompetencies,
      rubricFeedback,
      evaluatedAt: new Date().toISOString(),
    };
  }
}
