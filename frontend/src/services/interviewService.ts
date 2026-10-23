import { 
  Candidate, 
  JobRole, 
  Interview, 
  InterviewQuestion, 
  Evidence, 
  IntegrityEvent, 
  CandidateReport,
  IntegrityStatus,
  RecommendationOutcome,
  BackendResumeUploadResponse,
  BackendRoleEligibility,
  BackendAnswerResponse,
  BackendFinalReport,
  BackendQuestion
} from '../types';
import { apiRequest, apiUpload, apiDownloadBlob, isBackendConfigured } from '../api/apiClient';

export class InterviewService {
  /**
   * Check backend health and Ollama status
   */
  static async getHealth(): Promise<{ api: string; ollama: string; required_model_available: boolean; models: string[] } | null> {
    try {
      return await apiRequest('/api/health');
    } catch {
      return null;
    }
  }

  /**
   * Check speech synthesis and recognition device status
   */
  static async getSpeechStatus(): Promise<any | null> {
    try {
      return await apiRequest('/api/speech/status');
    } catch {
      return null;
    }
  }

  /**
   * Upload resume document (.pdf, .docx, .txt) and specify target technical role
   */
  static async uploadResume(file: File, targetRole: string): Promise<BackendResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_role', targetRole);
    return await apiUpload<BackendResumeUploadResponse>('/api/resume/upload', formData);
  }

  /**
   * Fetch 12-role eligibility and prerequisite audit for uploaded resume
   */
  static async getEligibility(resumeId: string): Promise<BackendRoleEligibility | null> {
    try {
      return await apiRequest<BackendRoleEligibility>(`/api/resume/${resumeId}/eligibility`);
    } catch {
      return null;
    }
  }

  /**
   * Prepare interview agenda and rubrics from parsed resume
   */
  static async prepareInterview(payload: {
    resume_id: string;
    target_role: string;
    mode?: 'mock' | 'predefined';
    question_count?: number;
    difficulty?: string;
  }): Promise<{
    status: string;
    session_id: string;
    track: string;
    display_title: string;
    questions_prepared: number;
    topics: string[];
    mode: string;
    first_topic?: string;
  }> {
    const res = await apiRequest<any>('/api/interview/prepare', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: payload.resume_id,
        target_role: payload.target_role,
        mode: payload.mode || 'mock',
        question_count: payload.question_count || 5,
        difficulty: payload.difficulty || 'adaptive'
      }),
    });
    if (!res) throw new Error('Failed to prepare interview with backend.');
    return res;
  }

  /**
   * Start technical interview session
   */
  static async startInterview(payload: {
    resume_id: string;
    session_id?: string;
    mode: 'mock' | 'predefined';
    difficulty?: string;
    target_questions?: number;
    role?: string;
  }): Promise<{
    session_id: string;
    status: string;
    question: BackendQuestion;
  }> {
    const res = await apiRequest<any>('/api/interview/start', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: payload.resume_id,
        session_id: payload.session_id,
        mode: payload.mode,
        dynamic_questions: payload.mode !== 'predefined',
        difficulty: payload.difficulty || 'adaptive',
        target_questions: payload.target_questions || 5,
        max_questions: payload.target_questions || 5,
        role: payload.role || 'Software Engineer'
      }),
    });
    if (!res) throw new Error('Failed to start interview session.');

    if (typeof sessionStorage !== 'undefined') {
      if (res.session_token) sessionStorage.setItem('interview_session_token', res.session_token);
      if (res.candidate_id) sessionStorage.setItem('interview_candidate_id', res.candidate_id);
    }

    const rawQD = res.question_details || {};
    const requiresCode = Boolean(
      res.requires_code ?? rawQD.requires_code ?? (res.question_type === 'code_writing' || rawQD.question_type === 'code_writing' || res.question_type === 'debugging' || rawQD.question_type === 'debugging')
    );
    const questionObj: BackendQuestion = {
      question_id: rawQD.question_id || rawQD.id || res.question_id || 'q-1',
      question_number: rawQD.question_number || res.question_number || 1,
      text: rawQD.text || res.text || res.question || '',
      type: rawQD.question_type || res.question_type || 'conceptual',
      difficulty: rawQD.difficulty || res.difficulty || 'intermediate',
      max_marks: rawQD.max_marks || res.max_marks || 5,
      code_snippet: rawQD.code_snippet || res.code_snippet || undefined,
      expected_answer_format: requiresCode ? 'code' : 'verbal',
      requires_code: requiresCode,
      starter_code: rawQD.starter_code || res.starter_code || undefined,
      language: rawQD.language || res.language || 'python',
      topic: rawQD.topic || res.topic || 'Engineering Competency',
    };

    return {
      session_id: res.session_id,
      status: res.status,
      question: questionObj,
    };
  }

  /**
   * Submit candidate answer (verbal transcript or code solution) for rubric evaluation
   */
  static async submitAnswer(
    sessionId: string, 
    answerText: string, 
    language: string = 'python'
  ): Promise<BackendAnswerResponse> {
    const res = await apiRequest<any>(`/api/interview/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({
        answer: answerText,
        language
      }),
    });
    if (!res) throw new Error('Failed to evaluate candidate answer.');

    let nextQuestionObj: BackendQuestion | null = null;
    if (res.next_question_details) {
      const nq = res.next_question_details;
      const nqRequiresCode = Boolean(
        nq.requires_code ?? (nq.question_type === 'code_writing' || nq.question_type === 'debugging')
      );
      nextQuestionObj = {
        question_id: nq.id || nq.question_id || `q-${res.question_number + 1}`,
        question_number: res.question_number + 1,
        text: nq.text || res.next_question || '',
        type: nq.question_type || 'conceptual',
        difficulty: nq.difficulty || 'intermediate',
        max_marks: nq.max_marks || 5,
        code_snippet: nq.code_snippet || undefined,
        expected_answer_format: nqRequiresCode ? 'code' : 'verbal',
        requires_code: nqRequiresCode,
        starter_code: nq.starter_code || undefined,
        language: nq.language || 'python',
        topic: nq.topic || res.next_competency || 'Engineering Competency',
      };
    } else if (res.next_question && typeof res.next_question === 'string' && res.next_question.trim().length > 0) {
      nextQuestionObj = {
        question_id: `q-${res.question_number + 1}`,
        question_number: res.question_number + 1,
        text: res.next_question,
        type: 'conceptual',
        difficulty: 'intermediate',
        max_marks: 5,
        expected_answer_format: 'verbal',
        topic: res.next_competency || 'Engineering Competency',
      };
    }

    const marksAwarded = res.marks_awarded ?? (res.evaluation ? res.evaluation.awarded_marks : 0);
    const maxMarks = res.max_marks ?? (res.evaluation ? res.evaluation.max_marks : 5);
    const pct = res.percentage ?? (res.evaluation ? res.evaluation.percentage : 0);
    const feedbackText = res.feedback ?? (res.evaluation ? res.evaluation.summary : 'Answer evaluated.');

    return {
      marks_awarded: marksAwarded,
      max_marks: maxMarks,
      percentage: pct,
      rubric_breakdown: (res.evaluation && res.evaluation.criteria) ? res.evaluation.criteria.map((c: any) => ({
        criterion: c.criterion_id || 'Rubric criterion',
        marks_awarded: c.awarded_marks,
        max_marks: c.max_marks,
        reason: c.explanation || c.evidence || '',
      })) : [],
      feedback: feedbackText,
      misconceptions: res.misconceptions || (res.evaluation ? res.evaluation.missing_knowledge : []) || [],
      next_question: nextQuestionObj,
      is_complete: Boolean(res.is_complete),
    };
  }

  /**
   * Conclude interview session early or at completion
   */
  static async endInterview(sessionId: string): Promise<any> {
    return await apiRequest(`/api/interview/${sessionId}/end`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  /**
   * Fetch complete performance, rubrics, and skill-gap intelligence report
   */
  static async getReport(sessionId: string): Promise<BackendFinalReport | null> {
    try {
      return await apiRequest<BackendFinalReport>(`/api/interview/${sessionId}/report`);
    } catch (err) {
      console.warn('Failed to fetch interview report:', err);
      return null;
    }
  }

  /**
   * Download server-side generated ReportLab PDF
   */
  static async downloadPdfReport(sessionId: string, candidateName: string = 'Candidate'): Promise<void> {
    const filename = `Interview_Report_${sessionId.substring(0, 8)}_${candidateName.replace(/\s+/g, '_')}.pdf`;
    await apiDownloadBlob(`/api/interview/${sessionId}/pdf`, filename);
  }

  /**
   * Speak text via backend TTS endpoint
   */
  static async speak(text: string): Promise<boolean> {
    try {
      await apiRequest('/api/speech/speak', {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      return true;
    } catch {
      return false;
    }
  }

  // --- Historical / Recruiter helpers (for dashboard overview) ---
  static async getCandidates(): Promise<Candidate[]> {
    try {
      const res = await apiRequest<{ count: number; candidates: any[] }>('/api/recruiter/candidates');
      if (!res || !res.candidates) return [];
      return res.candidates.map((c) => ({
        id: c.session_id,
        name: c.candidate_name || 'Candidate',
        role: c.target_role || 'Engineering Candidate',
        status: (c.normalized_score > 0 ? 'completed' : 'in_progress') as any,
        experienceYears: 3,
        createdAt: c.created_at || new Date().toISOString(),
        resume: {
          id: c.candidate_id || c.session_id,
          candidateId: c.candidate_id || c.session_id,
          uploadedAt: c.created_at || new Date().toISOString(),
          extractedSkills: c.demonstrated_competencies || [],
        },
      }));
    } catch (err) {
      console.warn('Failed to fetch candidates from recruiter endpoint:', err);
      return [];
    }
  }

  static async getCandidate(id: string): Promise<Candidate | null> {
    try {
      const res = await apiRequest<{ decision: any; report: any }>(`/api/recruiter/candidate/${id}`);
      if (!res || !res.decision) return null;
      const c = res.decision;
      return {
        id: c.session_id,
        name: c.candidate_name,
        role: c.target_role,
        status: 'completed',
        experienceYears: 3,
        createdAt: c.created_at,
        resume: {
          id: c.candidate_id,
          candidateId: c.candidate_id,
          uploadedAt: c.created_at,
          extractedSkills: c.demonstrated_competencies || [],
        },
      };
    } catch {
      return null;
    }
  }

  static async getJobRoles(): Promise<JobRole[]> {
    return [
      {
        id: 'python-engineer',
        title: 'Python Backend Engineer',
        department: 'Engineering',
        level: 'Mid - Senior',
        description: 'High-throughput async APIs, FastAPI/Django, PostgreSQL, and distributed caching.',
        requiredCompetencies: ['Python', 'FastAPI', 'PostgreSQL', 'AsyncIO', 'Data Structures'],
        niceToHaveCompetencies: ['Redis', 'Docker', 'System Design'],
      },
      {
        id: 'fullstack-engineer',
        title: 'Full-Stack Software Engineer',
        department: 'Engineering',
        level: 'Mid - Senior',
        description: 'End-to-end fullstack development across modern React and robust backend microservices.',
        requiredCompetencies: ['JavaScript', 'React', 'Node.js', 'REST APIs', 'SQL'],
        niceToHaveCompetencies: ['TypeScript', 'GraphQL', 'TailwindCSS'],
      },
    ];
  }

  static async getEvidence(interviewId: string): Promise<Evidence[]> {
    return [];
  }

  static async getIntegrityEvents(sessionId: string): Promise<IntegrityEvent[]> {
    try {
      const res = await apiRequest<{ count: number; events: any[] }>(`/api/interview/${sessionId}/integrity_events`);
      if (!res || !res.events) return [];
      return res.events.map((e) => {
        const sec = Math.round(e.timestamp_offset_seconds || 0);
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        return {
          id: e.id,
          interviewId: e.session_id,
          timestampSeconds: sec,
          timestampFormatted: `${m}:${s}`,
          type: (e.event_type === 'window_blur' ? 'focus_loss' : e.event_type) as any,
          title: e.title,
          description: e.description,
          severity: (e.severity || 'low') as any,
          confidence: e.confidence || 85,
          recruiterStatus: e.recruiter_status || 'pending_review',
          recruiterNotes: e.recruiter_notes || undefined,
        };
      });
    } catch {
      return [];
    }
  }

  static async logIntegrityEvent(
    sessionId: string,
    eventData: {
      event_type: string;
      severity?: string;
      confidence?: number;
      title?: string;
      description?: string;
      timestamp_offset_seconds?: number;
    }
  ): Promise<boolean> {
    try {
      await apiRequest(`/api/interview/${sessionId}/integrity_event`, {
        method: 'POST',
        body: JSON.stringify(eventData),
      });
      return true;
    } catch {
      return false;
    }
  }

  static async updateIntegrityEvent(
    sessionId: string,
    eventId: string, 
    status: IntegrityStatus, 
    notes?: string
  ): Promise<boolean> {
    try {
      await apiRequest(`/api/interview/${sessionId}/integrity_event/${eventId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status, notes }),
      });
      return true;
    } catch {
      return false;
    }
  }

  static async updateReportOutcome(
    sessionId: string, 
    outcome: RecommendationOutcome, 
    notes?: string
  ): Promise<boolean> {
    try {
      await apiRequest(`/api/recruiter/decision/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({ outcome, notes }),
      });
      return true;
    } catch {
      return false;
    }
  }

  static async compareCandidates(sessionIds: string[]): Promise<any> {
    return await apiRequest('/api/recruiter/compare', {
      method: 'POST',
      body: JSON.stringify({ session_ids: sessionIds }),
    });
  }
}

