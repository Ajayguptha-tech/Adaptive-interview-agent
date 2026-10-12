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
    session_id: string;
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
        difficulty: payload.difficulty || 'adaptive',
        target_questions: payload.target_questions || 5,
        role: payload.role || 'Software Engineer'
      }),
    });
    if (!res) throw new Error('Failed to start interview session.');
    return res;
  }

  /**
   * Submit candidate answer (verbal transcript or code solution) for rubric evaluation
   */
  static async submitAnswer(
    sessionId: string, 
    answerText: string, 
    language: string = 'python'
  ): Promise<BackendAnswerResponse> {
    const res = await apiRequest<BackendAnswerResponse>(`/api/interview/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({
        answer: answerText,
        language
      }),
    });
    if (!res) throw new Error('Failed to evaluate candidate answer.');
    return res;
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
    return [];
  }

  static async getCandidate(id: string): Promise<Candidate | null> {
    return null;
  }

  static async getJobRoles(): Promise<JobRole[]> {
    return [];
  }

  static async getEvidence(interviewId: string): Promise<Evidence[]> {
    return [];
  }

  static async getIntegrityEvents(interviewId: string): Promise<IntegrityEvent[]> {
    return [];
  }

  static async updateIntegrityEvent(
    eventId: string, 
    status: IntegrityStatus, 
    notes?: string
  ): Promise<boolean> {
    return true;
  }

  static async updateReportOutcome(
    reportId: string, 
    outcome: RecommendationOutcome, 
    notes?: string
  ): Promise<boolean> {
    return true;
  }
}
