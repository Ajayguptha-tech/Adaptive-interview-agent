import { 
  InterviewQuestion, 
  Competency, 
  EvaluationResult, 
  AdaptiveRoutingDecision,
  QuestionDifficulty
} from '../types';
import { apiRequest, isBackendConfigured } from '../api/apiClient';

/**
 * Agent 2: Adaptive Interviewer Agent
 * 
 * Dynamically selects relevant questions and follow-ups based on previous
 * answers, evaluation results, and remaining unassessed competencies.
 */
export class AdaptiveInterviewerAgent {
  /**
   * Determine the next question adaptively.
   */
  static async selectNextQuestion(params: {
    interviewId: string;
    competencies: Competency[];
    askedQuestions: InterviewQuestion[];
    lastEvaluation?: EvaluationResult;
    availableQuestionsQueue: InterviewQuestion[];
  }): Promise<{
    decision: AdaptiveRoutingDecision;
    source: 'backend' | 'demo';
  }> {
    if (isBackendConfigured()) {
      try {
        const remote = await apiRequest<AdaptiveRoutingDecision>(
          `/api/v1/interviewer/next-question`,
          {
            method: 'POST',
            body: JSON.stringify(params),
          }
        );
        if (remote) {
          return { decision: remote, source: 'backend' };
        }
      } catch (err) {
        console.warn('FastAPI adaptive interviewer failed, falling back to local engine:', err);
      }
    }

    const decision = this.selectLocalNextQuestion(params);
    return { decision, source: 'demo' };
  }

  /**
   * Client-side adaptive question selection engine.
   */
  static selectLocalNextQuestion(params: {
    competencies: Competency[];
    askedQuestions: InterviewQuestion[];
    lastEvaluation?: EvaluationResult;
    availableQuestionsQueue: InterviewQuestion[];
  }): AdaptiveRoutingDecision {
    const { competencies, askedQuestions, lastEvaluation, availableQuestionsQueue } = params;

    // Strategy 1: If last evaluation highlighted specific missing information, follow up immediately
    if (lastEvaluation && lastEvaluation.missingInformation.length > 0 && lastEvaluation.overallScore < 75) {
      const missingPoint = lastEvaluation.missingInformation[0];
      const targetComp = competencies.find(c => 
        lastEvaluation.unaddressedCompetencies.includes(c.id) || 
        c.score === null || 
        (c.score !== undefined && c.score < 70)
      ) || competencies[0];

      const followUpQuestion: InterviewQuestion = {
        id: `q-followup-${Date.now()}`,
        order: askedQuestions.length + 1,
        text: `You mentioned your approach earlier, but could you elaborate specifically on: "${missingPoint}"? How do you handle that constraint in high-stakes production?`,
        category: targetComp.category,
        targetCompetencies: [targetComp.id],
        difficulty: 'intermediate',
        whyThisQuestion: {
          contextAnalysis: `Triggered by Answer Evaluation Agent detecting unverified depth on "${missingPoint}".`,
          gapDetected: `Candidate response lacked concrete execution details for ${missingPoint}.`,
          difficultyReason: 'Calibrated at intermediate level to isolate practical hands-on experience.',
          timeBalanceReason: 'Brief targeted follow-up (2-3 minutes).',
        },
      };

      return {
        nextQuestion: followUpQuestion,
        targetCompetencyName: targetComp.name,
        reasoning: `Follow-up triggered because candidate provided general answer but missed key indicator: ${missingPoint}.`,
        triggerType: 'gap_followup',
      };
    }

    // Strategy 2: If candidate demonstrated exceptional competence on previous question (score >= 85),
    // escalate difficulty with an advanced edge-case question
    if (lastEvaluation && lastEvaluation.overallScore >= 85) {
      const advancedQuestion: InterviewQuestion = {
        id: `q-advanced-${Date.now()}`,
        order: askedQuestions.length + 1,
        text: `Given your strong explanation, how would you architect this across distributed multi-region clients where network latency is intermittent and state divergence must be resolved automatically?`,
        category: 'technical',
        targetCompetencies: lastEvaluation.demonstratedCompetencies.length > 0 
          ? lastEvaluation.demonstratedCompetencies 
          : [competencies[0]?.id || 'comp-react-arch'],
        difficulty: 'advanced',
        whyThisQuestion: {
          contextAnalysis: 'Candidate established high proficiency (Score >= 85%); escalating to stress-test architectural bounds.',
          gapDetected: 'Verifying whether candidate knowledge extends to Staff/Principal-level distributed resilience.',
          difficultyReason: 'Advanced scenario testing concurrency, conflict resolution, and degraded network recovery.',
          timeBalanceReason: 'Deep dive query allocating 5 minutes.',
        },
      };

      return {
        nextQuestion: advancedQuestion,
        targetCompetencyName: 'Advanced Distributed Architecture',
        reasoning: 'Candidate demonstrated exemplary mastery on initial inquiry; escalating difficulty to assess upper competency bound.',
        triggerType: 'depth_escalation',
      };
    }

    // Strategy 3: Find unassessed competencies to maximize coverage
    const unassessed = competencies.filter(c => c.score === null || c.evidenceCount === 0);
    if (unassessed.length > 0) {
      const targetComp = unassessed[0];

      // Check if we have a prepared question in the queue for this competency
      const queuedQuestion = availableQuestionsQueue.find(q => 
        q.targetCompetencies.includes(targetComp.id) &&
        !askedQuestions.some(asked => asked.id === q.id)
      );

      if (queuedQuestion) {
        return {
          nextQuestion: {
            ...queuedQuestion,
            order: askedQuestions.length + 1,
          },
          targetCompetencyName: targetComp.name,
          reasoning: `Routing to unassessed competency "${targetComp.name}" to broaden coverage.`,
          triggerType: 'breadth_exploration',
        };
      }

      // Synthesize a new dynamic inquiry for this competency
      const dynamicQuestion: InterviewQuestion = {
        id: `q-dyn-${Date.now()}`,
        order: askedQuestions.length + 1,
        text: `Let's discuss ${targetComp.name}. Can you describe a real-world scenario where you had to balance this against tight business delivery deadlines?`,
        category: targetComp.category,
        targetCompetencies: [targetComp.id],
        difficulty: 'intermediate',
        whyThisQuestion: {
          contextAnalysis: `Unassessed competency detected in session matrix: ${targetComp.name}.`,
          gapDetected: 'Zero verifiable transcript quotes exist for this required competency.',
          difficultyReason: 'Standard calibrated inquiry for baseline evidence gathering.',
          timeBalanceReason: 'Coverage expansion inquiry allocating 4 minutes.',
        },
      };

      return {
        nextQuestion: dynamicQuestion,
        targetCompetencyName: targetComp.name,
        reasoning: `Dynamically formulated question targeting zero-evidence competency: ${targetComp.name}.`,
        triggerType: 'breadth_exploration',
      };
    }

    // Strategy 4: Calibration wrap-up question
    const calibrationQuestion: InterviewQuestion = {
      id: `q-wrapup-${Date.now()}`,
      order: askedQuestions.length + 1,
      text: 'Looking back at a major project you led, what is one architectural decision you would make differently today, and what evidence or telemetry convinced you of that change?',
      category: 'behavioral',
      targetCompetencies: ['comp-incident-comms'],
      difficulty: 'intermediate',
      whyThisQuestion: {
        contextAnalysis: 'All core competencies have initial evidence points; running reflective synthesis calibration.',
        gapDetected: 'Verifying retrospective technical self-awareness and empirical decision making.',
        difficultyReason: 'Open-ended calibration assessing engineering humility and growth.',
        timeBalanceReason: 'Final question allocating remaining session time.',
      },
    };

    return {
      nextQuestion: calibrationQuestion,
      targetCompetencyName: 'Retrospective Engineering Judgment',
      reasoning: 'All primary competencies have baseline coverage. Closing session with reflective calibration.',
      triggerType: 'calibration',
    };
  }
}
