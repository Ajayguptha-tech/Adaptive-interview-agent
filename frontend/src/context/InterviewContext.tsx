import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { 
  Candidate, 
  JobRole, 
  Interview, 
  InterviewQuestion, 
  Evidence, 
  IntegrityEvent, 
  Competency, 
  CandidateReport, 
  IntegrityStatus, 
  RecommendationOutcome, 
  InterviewPlan, 
  CandidateSetupInput, 
  EvaluationResult, 
  AgentLogEntry,
  BackendResumeUploadResponse,
  BackendRoleEligibility,
  BackendIntegrityReport,
  BackendQuestion,
  BackendAnswerResponse,
  BackendFinalReport
} from '../types';
import { isBackendConfigured } from '../api/apiClient';
import { InterviewService } from '../services/interviewService';
import { InterviewPlannerAgent } from '../agents/planner';
import { AdaptiveInterviewerAgent } from '../agents/interviewer';
import { AnswerEvaluationAgent } from '../agents/evaluator';
import { InterviewIntegrityAgent } from '../agents/integrity';
import { DecisionIntelligenceAgent } from '../agents/decision';

export type NavigationTab = 
  | 'landing' 
  | 'dashboard' 
  | 'setup' 
  | 'live' 
  | 'evidence' 
  | 'integrity' 
  | 'report';

interface InterviewContextType {
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  isBackendConnected: boolean;
  isDemoMode: boolean;
  setIsDemoMode: (demo: boolean) => void;
  
  // Data State
  candidates: Candidate[];
  selectedCandidate: Candidate | null;
  activeRole: JobRole | null;
  activeInterview: Interview | null;
  interviewPlan: InterviewPlan | null;
  planSource: 'backend' | 'demo' | null;
  currentQuestion: InterviewQuestion | null;
  questionHistory: InterviewQuestion[];
  evidenceList: Evidence[];
  integrityEvents: IntegrityEvent[];
  competencies: Competency[];
  candidateReport: CandidateReport | null;
  agentLogs: AgentLogEntry[];

  // Backend Live State
  backendResumeData: BackendResumeUploadResponse | null;
  backendSessionId: string | null;
  backendFinalReport: BackendFinalReport | null;
  backendQuestion: BackendQuestion | null;
  backendEligibility: BackendRoleEligibility | null;
  backendIntegrity: BackendIntegrityReport | null;

  // Session state
  isInterviewActive: boolean;
  isPaused: boolean;
  isEvaluating: boolean;
  timeRemainingSeconds: number | null;
  sessionDurationMinutes: number;
  lastEvaluation: EvaluationResult | null;
  lastBackendAnswer: BackendAnswerResponse | null;

  // Actions
  uploadResumeFile: (file: File, targetRole: string) => Promise<BackendResumeUploadResponse>;
  startBackendSession: (options: { mode: 'mock' | 'predefined'; count: number; difficulty?: string }) => Promise<void>;
  submitAnswerToBackend: (answerText: string, language?: string, autoAdvance?: boolean) => Promise<BackendAnswerResponse>;
  advanceToNextBackendQuestion: (nextQ?: BackendQuestion | null) => void;
  endBackendSession: () => Promise<BackendFinalReport | null>;
  downloadPdfReport: () => Promise<void>;
  
  selectCandidate: (candidateId: string | null) => void;
  generateInterviewPlan: (input: CandidateSetupInput) => Promise<InterviewPlan>;
  startInterview: (customPlan?: InterviewPlan) => void;
  pauseResumeInterview: () => void;
  endInterview: () => Promise<void>;
  retryCurrentQuestion: () => void;
  submitAnswer: (transcriptText: string, audioDuration?: number) => Promise<void>;
  flagObservation: (notes?: string) => void;
  updateIntegrityEventStatus: (id: string, status: IntegrityStatus, notes?: string) => void;
  updateReportOutcome: (outcome: RecommendationOutcome) => void;
  refreshData: () => Promise<void>;
  resetSession: () => void;
}

const InterviewContext = createContext<InterviewContextType | undefined>(undefined);

export const InterviewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<NavigationTab>('landing');
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(true);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  // Collections state
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [activeRole, setActiveRole] = useState<JobRole | null>(null);
  const [activeInterview, setActiveInterview] = useState<Interview | null>(null);
  const [interviewPlan, setInterviewPlan] = useState<InterviewPlan | null>(null);
  const [planSource, setPlanSource] = useState<'backend' | 'demo' | null>(null);
  
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion | null>(null);
  const [questionHistory, setQuestionHistory] = useState<InterviewQuestion[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [integrityEvents, setIntegrityEvents] = useState<IntegrityEvent[]>([]);
  const [competencies, setCompetencies] = useState<Competency[]>([]);
  const [candidateReport, setCandidateReport] = useState<CandidateReport | null>(null);
  const [agentLogs, setAgentLogs] = useState<AgentLogEntry[]>([]);

  // Backend Live State
  const [backendResumeData, setBackendResumeData] = useState<BackendResumeUploadResponse | null>(null);
  const [backendSessionId, setBackendSessionId] = useState<string | null>(null);
  const [backendFinalReport, setBackendFinalReport] = useState<BackendFinalReport | null>(null);
  const [backendQuestion, setBackendQuestion] = useState<BackendQuestion | null>(null);
  const [backendEligibility, setBackendEligibility] = useState<BackendRoleEligibility | null>(null);
  const [backendIntegrity, setBackendIntegrity] = useState<BackendIntegrityReport | null>(null);
  const [lastBackendAnswer, setLastBackendAnswer] = useState<BackendAnswerResponse | null>(null);

  // Session tracking
  const [isInterviewActive, setIsInterviewActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [timeRemainingSeconds, setTimeRemainingSeconds] = useState<number | null>(null);
  const [sessionDurationMinutes, setSessionDurationMinutes] = useState<number>(30);
  const [lastEvaluation, setLastEvaluation] = useState<EvaluationResult | null>(null);

  // Helpers to log agent actions
  const addAgentLog = useCallback((agent: AgentLogEntry['agent'], action: string, details: string, level: AgentLogEntry['level'] = 'info') => {
    const entry: AgentLogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 5)}`,
      agent,
      timestamp: new Date().toLocaleTimeString(),
      action,
      details,
      level,
    };
    setAgentLogs(prev => [entry, ...prev.slice(0, 30)]);
  }, []);

  // Check health and connectivity on mount
  useEffect(() => {
    InterviewService.getHealth().then(health => {
      if (health && health.api === 'running') {
        setIsBackendConnected(true);
        setIsDemoMode(false);
        addAgentLog('planner', 'FastAPI Connected', `LLM: ${health.models?.[0] || 'qwen2.5:7b'}, Speech & Rubrics Ready.`);
        InterviewService.getCandidates().then(cands => {
          if (cands && cands.length > 0) setCandidates(cands);
        }).catch(() => {});
      } else {
        setIsBackendConnected(false);
        setIsDemoMode(true);
      }
    }).catch(() => {
      setIsBackendConnected(false);
      setIsDemoMode(true);
    });
  }, [addAgentLog]);

  // Real-time ticking interview timer
  useEffect(() => {
    if (!isInterviewActive || isPaused || timeRemainingSeconds === null) return;

    if (timeRemainingSeconds <= 0) {
      endInterview();
      return;
    }

    const interval = setInterval(() => {
      setTimeRemainingSeconds(prev => {
        if (prev === null || prev <= 1) return 0;
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isInterviewActive, isPaused, timeRemainingSeconds]);

  // Sensory listener: Candidate window focus / tab blur
  useEffect(() => {
    if (!isInterviewActive || isPaused || !activeInterview) return;

    const handleBlur = () => {
      const elapsed = (sessionDurationMinutes * 60) - (timeRemainingSeconds || sessionDurationMinutes * 60);
      const ev = InterviewIntegrityAgent.createFocusLossEvent(activeInterview.id, Math.max(0, elapsed));
      setIntegrityEvents(prev => [ev, ...prev]);
      addAgentLog('integrity', 'Window Focus Shift', 'Candidate tab temporarily transitioned focus away from interview window.', 'warning');

      if (backendSessionId) {
        InterviewService.logIntegrityEvent(backendSessionId, {
          event_type: 'window_blur',
          severity: 'info',
          confidence: 85,
          title: 'Candidate Window Focus Transition',
          description: 'Candidate browser tab temporarily lost focus during active interview session.',
          timestamp_offset_seconds: Math.max(0, elapsed),
        });
      }
    };

    window.addEventListener('blur', handleBlur);
    return () => window.removeEventListener('blur', handleBlur);
  }, [isInterviewActive, isPaused, activeInterview, sessionDurationMinutes, timeRemainingSeconds, backendSessionId, addAgentLog]);

  /**
   * BACKEND ACTION 1: Upload real resume file and receive eligibility & integrity audit
   */
  const uploadResumeFile = async (file: File, targetRole: string): Promise<BackendResumeUploadResponse> => {
    addAgentLog('planner', 'Uploading Resume', `Uploading ${file.name} for target role: ${targetRole}`);
    try {
      const resp = await InterviewService.uploadResume(file, targetRole);
      setBackendResumeData(resp);
      setBackendEligibility(resp.role_eligibility || null);
      setBackendIntegrity(resp.integrity_report || null);

      const skillsList: string[] = resp.extracted_skills || (resp as any).skills || [];
      const expYears: number = resp.experience_years ?? (resp as any).total_experience_years ?? 0;
      const routedTrack: string = resp.routed_track || 'python';
      const candName: string = resp.candidate_name || 'Technical Candidate';

      // Create candidate entity
      const newCand: Candidate = {
        id: resp.resume_id,
        name: candName,
        role: resp.target_role || targetRole,
        experienceYears: expYears,
        status: 'scheduled',
        createdAt: new Date().toISOString(),
        resume: {
          id: resp.resume_id,
          candidateId: resp.resume_id,
          fileName: file.name,
          uploadedAt: new Date().toISOString(),
          extractedSkills: skillsList,
          experienceYears: expYears,
        },
      };

      const newRole: JobRole = {
        id: `role-${Date.now()}`,
        title: resp.target_role || targetRole,
        department: 'Engineering',
        level: 'Engineering Candidate',
        description: `Target role: ${resp.target_role || targetRole} (${routedTrack.toUpperCase()} Track)`,
        requiredCompetencies: skillsList,
        niceToHaveCompetencies: [],
      };

      // Set competencies from extracted skills
      const comps: Competency[] = skillsList.map((skill, idx) => ({
        id: `comp-${idx}`,
        name: skill,
        category: 'technical',
        evidenceCount: 0,
        classification: 'claimed_needs_validation',
      }));

      setSelectedCandidate(newCand);
      setActiveRole(newRole);
      setCompetencies(comps);
      setCandidates(prev => [newCand, ...prev.filter(c => c.id !== newCand.id)]);
      addAgentLog('planner', 'Resume Analysis Done', `Candidate: ${candName}, Track: ${routedTrack}, Skills: ${skillsList.length}`);

      return resp;
    } catch (err: any) {
      console.error('Resume upload error:', err);
      addAgentLog('planner', 'Upload Failed', err.message || 'Error uploading resume document', 'warning');
      throw err;
    }
  };

  /**
   * BACKEND ACTION 2: Prepare and start real interview session
   */
  const startBackendSession = async (options: { mode: 'mock' | 'predefined'; count: number; difficulty?: string }) => {
    if (!backendResumeData) {
      throw new Error('Please upload a resume first.');
    }

    addAgentLog('planner', 'Preparing Interview', `Mode: ${options.mode}, Questions: ${options.count}`);
    const prep = await InterviewService.prepareInterview({
      resume_id: backendResumeData.resume_id,
      target_role: backendResumeData.target_role,
      mode: options.mode,
      question_count: options.count,
      difficulty: options.difficulty || 'adaptive'
    });

    const startRes = await InterviewService.startInterview({
      resume_id: backendResumeData.resume_id,
      mode: options.mode,
      difficulty: options.difficulty || 'adaptive',
      target_questions: options.count,
      role: backendResumeData.target_role
    });

    setBackendSessionId(startRes.session_id);
    addAgentLog('interviewer', 'Starting Session', `Session ID: ${startRes.session_id.substring(0, 8)}... (${prep.track || 'technical'} track)`);
    setBackendQuestion(startRes.question);

    // Map to InterviewQuestion format for UI
    const mappedQ: InterviewQuestion = {
      id: startRes.question.question_id,
      order: startRes.question.question_number || 1,
      text: startRes.question.text,
      category: 'technical',
      targetCompetencies: [startRes.question.topic || 'Core Engineering'],
      difficulty: (startRes.question.difficulty as any) || 'intermediate',
      whyThisQuestion: {
        contextAnalysis: `Question #${startRes.question.question_number || 1} (${startRes.question.type})`,
      }
    };

    setCurrentQuestion(mappedQ);
    setQuestionHistory([mappedQ]);

    const newInterview: Interview = {
      id: startRes.session_id,
      candidateId: backendResumeData.resume_id,
      jobRoleId: backendResumeData.target_role,
      status: 'in_progress',
      startedAt: new Date().toISOString(),
      timeRemainingSeconds: options.count * 300,
    };
    setActiveInterview(newInterview);
    setIsInterviewActive(true);
    setIsPaused(false);
    setTimeRemainingSeconds(options.count * 300);
    setActiveTab('live');

    addAgentLog('interviewer', 'Question Delivered', `Q1: ${startRes.question.text.substring(0, 60)}...`);
  };

  /**
  /**
   * Advance to the next backend question explicitly after candidate feedback review
   */
  const advanceToNextBackendQuestion = (nextQ?: BackendQuestion | null) => {
    if (nextQ) {
      setBackendQuestion(nextQ);
      const mappedNext: InterviewQuestion = {
        id: nextQ.question_id,
        order: nextQ.question_number,
        text: nextQ.text,
        category: 'technical',
        targetCompetencies: [nextQ.topic || 'Engineering Competency'],
        difficulty: (nextQ.difficulty as any) || 'intermediate',
      };
      setCurrentQuestion(mappedNext);
      setQuestionHistory(prev => [...prev, mappedNext]);
      addAgentLog('interviewer', 'Next Question Loaded', `Q${nextQ.question_number}: ${nextQ.text.substring(0, 60)}...`);
    } else {
      addAgentLog('interviewer', 'Interview Concluded', 'All questions answered. Generating final report.');
      endBackendSession();
    }
  };

  /**
   * BACKEND ACTION 3: Submit answer to FastAPI backend
   */
  const submitAnswerToBackend = async (
    answerText: string, 
    language: string = 'python',
    autoAdvance: boolean = true
  ): Promise<BackendAnswerResponse> => {
    if (!backendSessionId) throw new Error('No active backend session');

    setIsEvaluating(true);
    addAgentLog('evaluator', 'Evaluating Answer', `Submitting answer to rubric evaluator...`);

    try {
      const resp = await InterviewService.submitAnswer(backendSessionId, answerText, language);
      setLastBackendAnswer(resp);

      addAgentLog(
        'evaluator',
        'Rubric Score Awarded',
        `Awarded ${resp.marks_awarded} / ${resp.max_marks} marks (${resp.percentage}%)`
      );

      // Add evidence item
      const ev: Evidence = {
        id: `ev-${Date.now()}`,
        interviewId: backendSessionId,
        timestamp: new Date().toLocaleTimeString(),
        quote: answerText.substring(0, 150),
        competencyId: currentQuestion?.targetCompetencies[0] || 'Technical',
        competencyName: currentQuestion?.targetCompetencies[0] || 'Technical',
        scoreImpact: resp.percentage >= 70 ? 10 : -5,
        confidenceImpact: 15,
        rationale: resp.feedback,
        signalStrength: resp.percentage >= 70 ? 'high' : 'medium',
      };
      setEvidenceList(prev => [ev, ...prev]);

      if (autoAdvance) {
        if (resp.next_question) {
          advanceToNextBackendQuestion(resp.next_question);
        } else if (resp.is_complete) {
          addAgentLog('interviewer', 'Interview Concluded', 'All questions answered. Generating final report.');
          await endBackendSession();
        }
      }

      return resp;
    } finally {
      setIsEvaluating(false);
    }
  };

  /**
   * BACKEND ACTION 4: Conclude session and fetch report
   */
  const endBackendSession = async (): Promise<BackendFinalReport | null> => {
    setIsInterviewActive(false);
    setIsPaused(false);

    if (!backendSessionId) {
      setActiveTab('report');
      return null;
    }

    addAgentLog('decision', 'Finalizing Interview', 'Calling backend report generator and scoring engine.');
    await InterviewService.endInterview(backendSessionId);
    const report = await InterviewService.getReport(backendSessionId);
    setBackendFinalReport(report);

    if (report) {
      // Map to CandidateReport for compatibility
      const mappedReport: CandidateReport = {
        id: report.session_id,
        candidateId: report.session_id,
        jobRoleId: selectedCandidate?.role || 'Engineer',
        interviewId: report.session_id,
        alignmentScore: report.normalized_score,
        overallConfidence: 92,
        evidencePointsTotal: report.questions.length,
        durationMinutes: 25,
        outcome: report.normalized_score >= 70 ? 'proceed_to_human_review' : 'request_follow_up',
        executiveSummary: `Technical assessment completed with normalized score of ${report.normalized_score}/100 (${report.grade}).`,
        verifiedStrengths: report.demonstrated_skills.map(s => ({ skill: s, score: 85, evidence: 'Demonstrated in answer evaluations' })),
        criticalGaps: report.weak_skills.map(w => ({ skill: w, gapType: 'Unaddressed / Low Score', notes: 'Identified during rubric evaluation' })),
        unvalidatedClaims: report.claimed_unvalidated_skills,
        suggestedFollowUpQuestions: report.recommendations,
      };
      setCandidateReport(mappedReport);
      addAgentLog('decision', 'Report Synthesized', `Normalized Score: ${report.normalized_score}/100. Grade: ${report.grade}`);
    }

    setActiveTab('report');
    return report;
  };

  /**
   * BACKEND ACTION 5: Download PDF Report
   */
  const downloadPdfReport = async () => {
    if (!backendSessionId) return;
    addAgentLog('decision', 'Downloading PDF', 'Retrieving server-side ReportLab PDF report...');
    await InterviewService.downloadPdfReport(backendSessionId, selectedCandidate?.name || 'Candidate');
  };

  // --- Fallback Local Agent Methods (for Demo Mode) ---
  const selectCandidate = (candidateId: string | null) => {
    if (!candidateId) {
      setSelectedCandidate(null);
      return;
    }
    const found = candidates.find(c => c.id === candidateId);
    setSelectedCandidate(found || null);
  };

  const generateInterviewPlan = async (input: CandidateSetupInput): Promise<InterviewPlan> => {
    addAgentLog('planner', 'Analyzing Requisition & Resume', `Ingesting claims for candidate: ${input.candidateName}`);
    const { plan, source } = await InterviewPlannerAgent.generatePlan(input);
    setInterviewPlan(plan);
    setPlanSource(source);
    setCompetencies(plan.competencies);
    setSessionDurationMinutes(input.sessionDurationMinutes);
    return plan;
  };

  const startInterview = async (customPlan?: InterviewPlan) => {
    if (backendResumeData) {
      await startBackendSession({ mode: 'mock', count: 5 });
      return;
    }
    setIsInterviewActive(true);
    setActiveTab('live');
  };

  const pauseResumeInterview = () => {
    setIsPaused(prev => !prev);
  };

  const retryCurrentQuestion = () => {
    addAgentLog('interviewer', 'Question Retried', 'Candidate retrying current response.');
  };

  const submitAnswer = async (transcriptText: string, audioDuration?: number) => {
    if (backendSessionId) {
      await submitAnswerToBackend(transcriptText);
      return;
    }
    throw new Error('No active backend interview session. Please upload a resume and start interview.');
  };

  const endInterview = async () => {
    if (backendSessionId) {
      await endBackendSession();
      return;
    }
    setIsInterviewActive(false);
    setActiveTab('report');
  };

  const flagObservation = (notes?: string) => {
    addAgentLog('integrity', 'Observation Flagged', notes || 'Observation noted.');
  };

  const updateIntegrityEventStatus = (id: string, status: IntegrityStatus, notes?: string) => {
    setIntegrityEvents(prev => prev.map(ev => ev.id === id ? { ...ev, recruiterStatus: status, recruiterNotes: notes } : ev));
    if (backendSessionId) {
      InterviewService.updateIntegrityEvent(backendSessionId, id, status, notes);
    }
  };

  const updateReportOutcome = (outcome: RecommendationOutcome) => {
    if (candidateReport) {
      setCandidateReport({ ...candidateReport, outcome });
    }
    if (backendSessionId) {
      InterviewService.updateReportOutcome(backendSessionId, outcome);
    }
  };

  const refreshData = async () => {
    try {
      const cands = await InterviewService.getCandidates();
      if (cands && cands.length > 0) {
        setCandidates(cands);
      }
    } catch (err) {
      console.warn('Failed to refresh recruiter pipeline candidates:', err);
    }
  };

  const resetSession = () => {
    setIsInterviewActive(false);
    setIsPaused(false);
    setIsEvaluating(false);
    setTimeRemainingSeconds(null);
    setCurrentQuestion(null);
    setQuestionHistory([]);
    setEvidenceList([]);
    setIntegrityEvents([]);
    setCompetencies([]);
    setCandidateReport(null);
    setBackendResumeData(null);
    setBackendSessionId(null);
    setBackendFinalReport(null);
    setBackendQuestion(null);
    setBackendEligibility(null);
    setBackendIntegrity(null);
    setLastBackendAnswer(null);
  };

  return (
    <InterviewContext.Provider
      value={{
        activeTab,
        setActiveTab,
        isBackendConnected,
        isDemoMode,
        setIsDemoMode,
        candidates,
        selectedCandidate,
        activeRole,
        activeInterview,
        interviewPlan,
        planSource,
        currentQuestion,
        questionHistory,
        evidenceList,
        integrityEvents,
        competencies,
        candidateReport,
        agentLogs,
        backendResumeData,
        backendSessionId,
        backendFinalReport,
        backendQuestion,
        backendEligibility,
        backendIntegrity,
        isInterviewActive,
        isPaused,
        isEvaluating,
        timeRemainingSeconds,
        sessionDurationMinutes,
        lastEvaluation,
        lastBackendAnswer,
        uploadResumeFile,
        startBackendSession,
        submitAnswerToBackend,
        advanceToNextBackendQuestion,
        endBackendSession,
        downloadPdfReport,
        selectCandidate,
        generateInterviewPlan,
        startInterview,
        pauseResumeInterview,
        endInterview,
        retryCurrentQuestion,
        submitAnswer,
        flagObservation,
        updateIntegrityEventStatus,
        updateReportOutcome,
        refreshData,
        resetSession,
      }}
    >
      {children}
    </InterviewContext.Provider>
  );
};

export const useInterview = () => {
  const context = useContext(InterviewContext);
  if (!context) {
    throw new Error('useInterview must be used within an InterviewProvider');
  }
  return context;
};
