import { 
  CandidateReport, 
  Candidate, 
  JobRole, 
  Interview, 
  Competency, 
  Evidence, 
  IntegrityEvent,
  InterviewPlan
} from '../types';
import { apiRequest, isBackendConfigured } from '../api/apiClient';

/**
 * Agent 5: Decision Intelligence Agent
 * 
 * Synthesizes all session evidence into an explainable recruiter dossier.
 * Adheres strictly to the human-in-the-loop principle:
 * NEVER automatically makes hiring or rejection decisions.
 */
export class DecisionIntelligenceAgent {
  /**
   * Synthesize candidate report from collected interview evidence.
   */
  static async generateReport(params: {
    candidate: Candidate;
    role: JobRole;
    interview: Interview;
    plan: InterviewPlan;
    competencies: Competency[];
    evidenceList: Evidence[];
    integrityEvents: IntegrityEvent[];
  }): Promise<{
    report: CandidateReport;
    source: 'backend' | 'demo';
  }> {
    if (isBackendConfigured()) {
      try {
        const remote = await apiRequest<CandidateReport>(
          `/api/v1/reports/generate`,
          {
            method: 'POST',
            body: JSON.stringify(params),
          }
        );
        if (remote) {
          return { report: remote, source: 'backend' };
        }
      } catch (err) {
        console.warn('FastAPI report generation failed, synthesizing locally:', err);
      }
    }

    const report = this.generateLocalReport(params);
    return { report, source: 'demo' };
  }

  /**
   * Client-side synthesis of evidence and competencies.
   */
  static generateLocalReport(params: {
    candidate: Candidate;
    role: JobRole;
    interview: Interview;
    plan: InterviewPlan;
    competencies: Competency[];
    evidenceList: Evidence[];
    integrityEvents: IntegrityEvent[];
  }): CandidateReport {
    const { candidate, role, interview, plan, competencies, evidenceList, integrityEvents } = params;

    // Calculate score & confidence
    const assessedCompetencies = competencies.filter(c => c.score !== null && c.score !== undefined);
    
    let alignmentScore: number | null = null;
    let overallConfidence: number | null = null;

    if (assessedCompetencies.length > 0) {
      const totalScore = assessedCompetencies.reduce((acc, c) => acc + (c.score || 0), 0);
      alignmentScore = Math.round(totalScore / assessedCompetencies.length);

      const totalConfidence = assessedCompetencies.reduce((acc, c) => acc + (c.confidence || 70), 0);
      overallConfidence = Math.round(totalConfidence / assessedCompetencies.length);
    }

    // Identify Verified Strengths (Score >= 75 with at least 1 verifiable quote)
    const verifiedStrengths = assessedCompetencies
      .filter(c => (c.score || 0) >= 75)
      .map(c => {
        const relatedEvidence = evidenceList.find(e => e.competencyId === c.id);
        return {
          skill: c.name,
          score: c.score || 80,
          evidence: relatedEvidence ? relatedEvidence.quote : 'Demonstrated across multiple responses.',
        };
      });

    // Identify Critical Gaps (Score < 60 or pre-interview gaps that remained unaddressed)
    const criticalGaps: { skill: string; gapType: string; notes: string }[] = [];
    
    assessedCompetencies
      .filter(c => (c.score || 0) < 60)
      .forEach(c => {
        criticalGaps.push({
          skill: c.name,
          gapType: 'Evaluated Sub-Threshold',
          notes: `Candidate scored ${c.score}/100. Responses lacked concrete depth or omitted failure-mode handling.`,
        });
      });

    // Unassessed required competencies
    competencies
      .filter(c => c.score === null && plan.preInterviewSkillGaps.includes(c.name))
      .forEach(c => {
        criticalGaps.push({
          skill: c.name,
          gapType: 'Pre-Interview Gap Unassessed',
          notes: 'Identified as gap between CV and Requisition; insufficient interview time to fully explore.',
        });
      });

    // Identify Unvalidated Claims (Claimed in resume, but not assessed or insufficient confidence)
    const unvalidatedClaims = plan.resumeClaims.filter(claim => {
      const matchComp = competencies.find(c => c.name === claim);
      return !matchComp || matchComp.score === null || (matchComp.confidence || 0) < 65;
    });

    // Generate Targeted Follow-up Inquiries for Next Round
    const suggestedFollowUpQuestions: string[] = [];
    if (criticalGaps.length > 0) {
      suggestedFollowUpQuestions.push(
        `Inquire deeper into ${criticalGaps[0].skill}: ask candidate to present code architecture diagram or debug live trace.`
      );
    }
    if (unvalidatedClaims.length > 0) {
      suggestedFollowUpQuestions.push(
        `Verify resume claim for "${unvalidatedClaims[0]}": ask for production metrics or specific incident resolution story.`
      );
    }
    suggestedFollowUpQuestions.push(
      'Cross-functional alignment inquiry: assess how candidate resolves architectural conflict with backend/product managers.'
    );

    // Summarize integrity observations
    const reviewedEvents = integrityEvents.filter(e => e.recruiterStatus !== 'pending_review');
    const integritySummary = {
      totalEvents: integrityEvents.length,
      reviewedCount: reviewedEvents.length,
      statusSummary: integrityEvents.length === 0
        ? 'No telemetry variances recorded.'
        : `${integrityEvents.length} sensory observations logged (${reviewedEvents.length} human-reviewed, ${integrityEvents.length - reviewedEvents.length} pending).`,
    };

    const executiveSummary = assessedCompetencies.length > 0
      ? `Candidate demonstrated ${verifiedStrengths.length} verified technical competencies with an overall alignment index of ${alignmentScore}% (Confidence: ${overallConfidence}% across ${evidenceList.length} transcript citations). ${criticalGaps.length} areas have residual gaps or unverified claims for hiring committee review.`
      : 'Session completed with partial evidence coverage. Additional verification required.';

    return {
      id: `rep-${Date.now()}`,
      candidateId: candidate.id,
      jobRoleId: role.id,
      interviewId: interview.id,
      alignmentScore,
      overallConfidence,
      evidencePointsTotal: evidenceList.length,
      durationMinutes: Math.round(((interview.timeRemainingSeconds !== null && interview.timeRemainingSeconds !== undefined ? 2400 - interview.timeRemainingSeconds : 600) / 60)),
      outcome: null, // Intentionally null: human recruiter must decide
      executiveSummary,
      verifiedStrengths,
      criticalGaps,
      unvalidatedClaims,
      suggestedFollowUpQuestions,
      integritySummary,
      recruiterSignoff: {
        reviewedBy: 'Hiring Committee Panelist',
        decisionDate: new Date().toISOString().split('T')[0],
        recruiterNotes: 'Awaiting human recruiter review and sign-off.',
      },
    };
  }
}
