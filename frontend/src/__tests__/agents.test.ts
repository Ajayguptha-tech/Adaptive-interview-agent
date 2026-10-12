import { describe, it, expect } from 'vitest';
import { InterviewPlannerAgent } from '../agents/planner';
import { AdaptiveInterviewerAgent } from '../agents/interviewer';
import { AnswerEvaluationAgent } from '../agents/evaluator';
import { InterviewIntegrityAgent } from '../agents/integrity';
import { DecisionIntelligenceAgent } from '../agents/decision';
import { CandidateSetupInput, Competency, InterviewQuestion } from '../types';

describe('Adaptive Interview Intelligence 5 AI Agent Interfaces & Adaptive Engine', () => {
  const sampleInput: CandidateSetupInput = {
    candidateName: 'Alex Chen',
    candidateEmail: 'alex.chen@example.com',
    roleTitle: 'Senior Frontend Engineer',
    department: 'Core Product Engineering',
    experienceLevel: 'L5 / Senior',
    jobDescription: 'Senior Frontend Engineer needed with deep React, TypeScript, Core Web Vitals, and WCAG accessibility expertise.',
    resumeText: 'Alex Chen. 8 years with React and TypeScript. Built high-traffic web applications with Redux and Vite.',
    sessionDurationMinutes: 40,
    adaptiveSensitivity: 'high',
  };

  it('Agent 1 (Planner): generates structured plan with competencies, rubrics, and gap identification', () => {
    const plan = InterviewPlannerAgent.generateLocalPlan(sampleInput);

    expect(plan.id).toBeDefined();
    expect(plan.competencies.length).toBeGreaterThanOrEqual(4);
    expect(plan.rubric.criteria.length).toBeGreaterThanOrEqual(4);
    expect(plan.initialQuestions.length).toBeGreaterThanOrEqual(3);
    
    // Resume did not explicitly mention WCAG or Web Vitals in summary
    expect(plan.preInterviewSkillGaps.length).toBeGreaterThan(0);
    
    // Check rubric indicator structure
    const firstCrit = plan.rubric.criteria[0];
    expect(firstCrit.indicators.inadequate).toBeDefined();
    expect(firstCrit.indicators.proficient).toBeDefined();
    expect(firstCrit.indicators.exceptional).toBeDefined();
  });

  it('Agent 3 (Evaluator): extracts verbatim quotes and measures decoupled confidence against rubrics', () => {
    const plan = InterviewPlannerAgent.generateLocalPlan(sampleInput);
    const question = plan.initialQuestions[0];
    const candidateAnswer = 
      'To prevent main thread jank during rapid state updates, I isolate high-frequency telemetry state using fine-grained subscriptions outside the React component tree. For heavy rendering surfaces, I use React Concurrent transitions via startTransition to yield execution priority to user interactions, ensuring our INP remains under 50ms.';

    const evalResult = AnswerEvaluationAgent.evaluateLocalAnswer({
      interviewId: 'int-test-1',
      question,
      transcriptText: candidateAnswer,
      rubric: plan.rubric,
      competencies: plan.competencies,
      sessionTimestampSeconds: 120,
    });

    expect(evalResult.overallScore).toBeGreaterThanOrEqual(75);
    expect(evalResult.confidenceScore).toBeGreaterThanOrEqual(70);
    expect(evalResult.extractedEvidence.length).toBeGreaterThan(0);

    // Citations should be non-empty quotes
    const firstEvidence = evalResult.extractedEvidence[0];
    expect(firstEvidence.quote.length).toBeGreaterThan(10);
    expect(firstEvidence.scoreImpact).toBeGreaterThan(0);
  });

  it('Agent 2 (Adaptive Interviewer): triggers gap follow-up when previous response is incomplete', () => {
    const plan = InterviewPlannerAgent.generateLocalPlan(sampleInput);
    const question = plan.initialQuestions[0];

    // Incomplete answer
    const evalResult = AnswerEvaluationAgent.evaluateLocalAnswer({
      interviewId: 'int-test-1',
      question,
      transcriptText: 'I just use useState and useEffect and hope it runs fast enough.',
      rubric: plan.rubric,
      competencies: plan.competencies,
      sessionTimestampSeconds: 120,
    });

    expect(evalResult.overallScore).toBeLessThan(70);
    expect(evalResult.missingInformation.length).toBeGreaterThan(0);

    // Test adaptive question selection
    const decision = AdaptiveInterviewerAgent.selectLocalNextQuestion({
      competencies: plan.competencies,
      askedQuestions: [question],
      lastEvaluation: evalResult,
      availableQuestionsQueue: plan.initialQuestions,
    });

    expect(decision.triggerType).toBe('gap_followup');
    expect(decision.nextQuestion.text).toContain(evalResult.missingInformation[0]);
  });

  it('Agent 2 (Adaptive Interviewer): escalates to advanced difficulty when answer scores >= 85', () => {
    const plan = InterviewPlannerAgent.generateLocalPlan(sampleInput);
    const question = plan.initialQuestions[0];

    const evalResult = AnswerEvaluationAgent.evaluateLocalAnswer({
      interviewId: 'int-test-1',
      question,
      transcriptText: 
        'I memoize expensive subtrees with useMemo and useCallback, leverage React 19 concurrent transitions and scheduler priority queues, benchmark with Chrome profiler to optimize INP under 40ms, and offload heavy computation to Web Workers.',
      rubric: plan.rubric,
      competencies: plan.competencies,
      sessionTimestampSeconds: 180,
    });

    expect(evalResult.overallScore).toBeGreaterThanOrEqual(85);

    const decision = AdaptiveInterviewerAgent.selectLocalNextQuestion({
      competencies: plan.competencies,
      askedQuestions: [question],
      lastEvaluation: evalResult,
      availableQuestionsQueue: plan.initialQuestions,
    });

    expect(decision.triggerType).toBe('depth_escalation');
    expect(decision.nextQuestion.difficulty).toBe('advanced');
  });

  it('Agent 4 (Integrity): generates objective non-accusatory telemetry observations', () => {
    const focusEvent = InterviewIntegrityAgent.createFocusLossEvent('int-test-1', 240);
    expect(focusEvent.type).toBe('focus_loss');
    expect(focusEvent.recruiterStatus).toBe('pending_review');
    expect(focusEvent.title).toContain('Window Focus Transition');
    // Does not accuse candidate of cheating
    expect(focusEvent.description).not.toContain('cheating');

    const pauseEvent = InterviewIntegrityAgent.createProlongedPauseEvent('int-test-1', 480, 25);
    expect(pauseEvent.type).toBe('inactivity_window');
    expect(pauseEvent.recruiterStatus).toBe('verified_benign');
  });

  it('Agent 5 (Decision): synthesizes evidence dossier without automated hiring decisions', () => {
    const plan = InterviewPlannerAgent.generateLocalPlan(sampleInput);
    const candidate = {
      id: 'cand-1',
      name: sampleInput.candidateName,
      role: sampleInput.roleTitle,
      status: 'completed' as const,
      createdAt: new Date().toISOString(),
    };
    const role = {
      id: 'role-1',
      title: sampleInput.roleTitle,
      department: sampleInput.department,
      level: sampleInput.experienceLevel,
      description: sampleInput.jobDescription,
      requiredCompetencies: ['React', 'TypeScript'],
      niceToHaveCompetencies: [],
    };
    const interview = {
      id: 'int-1',
      candidateId: candidate.id,
      jobRoleId: role.id,
      status: 'completed' as const,
      timeRemainingSeconds: 600,
    };

    const report = DecisionIntelligenceAgent.generateLocalReport({
      candidate,
      role,
      interview,
      plan,
      competencies: plan.competencies,
      evidenceList: [],
      integrityEvents: [],
    });

    expect(report.id).toBeDefined();
    // Ethical requirement: outcome must be null, never automatically hiring/rejecting
    expect(report.outcome).toBeNull();
    expect(report.suggestedFollowUpQuestions?.length).toBeGreaterThan(0);
    expect(report.recruiterSignoff).toBeDefined();
  });
});
