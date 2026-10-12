import React, { useState } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { RecommendationOutcome } from '../../types';
import { 
  FileCheck2, 
  Download, 
  Printer, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  UserCheck, 
  Sparkles,
  Award,
  RefreshCw
} from 'lucide-react';

export const CandidateReportScreen: React.FC = () => {
  const {
    selectedCandidate,
    activeRole,
    candidateReport,
    backendFinalReport,
    backendSessionId,
    downloadPdfReport,
    updateReportOutcome,
    isBackendConnected
  } = useInterview();

  const [selectedOutcome, setSelectedOutcome] = useState<RecommendationOutcome | null>(
    candidateReport?.outcome || null
  );
  const [recruiterNotes, setRecruiterNotes] = useState(
    candidateReport?.recruiterSignoff?.recruiterNotes || ''
  );
  const [signoffSaved, setSignoffSaved] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const handleOutcomeSelect = (outcome: RecommendationOutcome) => {
    setSelectedOutcome(outcome);
    updateReportOutcome(outcome);
  };

  const handleSaveSignoff = () => {
    if (selectedOutcome) {
      updateReportOutcome(selectedOutcome);
      setSignoffSaved(true);
      setTimeout(() => setSignoffSaved(false), 2500);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = async () => {
    if (!backendSessionId) return;
    setIsDownloadingPdf(true);
    try {
      await downloadPdfReport();
    } catch (err) {
      console.error('PDF download error:', err);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const scoreNormalized = backendFinalReport?.normalized_score ?? candidateReport?.alignmentScore ?? 80;
  const grade = backendFinalReport?.grade ?? (scoreNormalized >= 90 ? 'A+' : scoreNormalized >= 80 ? 'A' : scoreNormalized >= 70 ? 'B' : 'C');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8 print:p-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 print:hidden">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-100">Candidate Intelligence Dossier</h1>
            <StatusBadge variant="cyan" size="sm">Evidence Synthesis</StatusBadge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic scoring, rubric-traceable question evaluations, verified competencies, and server-side PDF generation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {backendSessionId && (
            <MagneticButton
              variant="primary"
              size="sm"
              onClick={handleDownloadPDF}
              disabled={isDownloadingPdf}
            >
              {isDownloadingPdf ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#111210]" />
              ) : (
                <Download className="w-3.5 h-3.5 text-[#111210]" />
              )}
              <span>Download PDF Report</span>
            </MagneticButton>
          )}

          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={handlePrint}
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Dossier</span>
          </MagneticButton>
        </div>
      </div>

      <div className="space-y-6">
        {/* Main Dossier Overview Card */}
        <InteractiveTiltCard glowColor="mixed" maxTilt={3} className="p-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#c6ee2e] to-emerald-400 text-[#111210] flex items-center justify-center font-mono text-2xl font-bold shadow-lg">
                {selectedCandidate?.name ? selectedCandidate.name[0] : 'C'}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-slate-100">
                    {selectedCandidate?.name || 'Technical Candidate'}
                  </h2>
                  <StatusBadge variant="emerald" size="sm">
                    Grade: {grade}
                  </StatusBadge>
                </div>
                <div className="text-xs text-cyan-300 font-mono mt-0.5">
                  {activeRole?.title || selectedCandidate?.role || 'Senior Software Engineer'}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Questions Evaluated: <strong className="text-slate-200">{backendFinalReport?.questions.length || 5}</strong> • Scoring Scale: 100 Normalized
                </div>
              </div>
            </div>

            {/* Metric Badges */}
            <div className="flex items-center gap-4 bg-slate-900/80 p-3 rounded-2xl border border-slate-800">
              <div className="text-center px-4 border-r border-slate-800">
                <div className="text-xs font-mono text-slate-400">Normalized Score</div>
                <div className="text-2xl font-bold font-mono text-[#c6ee2e]">
                  {scoreNormalized} / 100
                </div>
              </div>
              <div className="text-center px-4">
                <div className="text-xs font-mono text-slate-400">Total Marks</div>
                <div className="text-2xl font-bold font-mono text-cyan-400">
                  {backendFinalReport?.total_score || 22.5} / {backendFinalReport?.max_possible || 25}
                </div>
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="pt-5 space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400">Executive Evaluation Synthesis:</h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-slate-800/80">
              Candidate achieved a normalized score of {scoreNormalized}/100 across evaluated competencies. All awarded marks are deterministically grounded in rubric criteria with evidence propagation.
            </p>
          </div>
        </InteractiveTiltCard>

        {/* Backend Question-by-Question Audit Accordion (If available) */}
        {backendFinalReport && backendFinalReport.questions.length > 0 && (
          <InteractiveTiltCard glowColor="cyan" maxTilt={2} className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Question-by-Question Evaluation Audit ({backendFinalReport.questions.length} Items)
                </h3>
              </div>
              <StatusBadge variant="cyan" size="sm">Deterministic Rubrics</StatusBadge>
            </div>

            <div className="space-y-4">
              {backendFinalReport.questions.map((q, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <span className="text-[11px] font-mono text-cyan-400 font-bold uppercase">
                        Q{q.question_number} • {q.difficulty.toUpperCase()} • {q.type}
                      </span>
                      <p className="text-xs sm:text-sm font-semibold text-slate-100 mt-1">
                        {q.text}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="px-2.5 py-1 rounded-lg bg-[#c6ee2e]/10 border border-[#c6ee2e]/30 text-[#c6ee2e] font-mono text-xs font-bold">
                        {q.score} / {q.max_marks} marks
                      </span>
                    </div>
                  </div>

                  {/* Candidate Answer */}
                  <div className="text-xs space-y-1 bg-slate-950 p-3 rounded-lg border border-slate-850">
                    <span className="text-slate-400 font-mono block">Candidate Response:</span>
                    <p className="text-slate-200 italic">"{q.candidate_answer}"</p>
                  </div>

                  {/* Feedback */}
                  <div className="text-xs text-slate-300">
                    <span className="text-cyan-400 font-mono">Examiner Feedback: </span>
                    {q.feedback}
                  </div>

                  {/* Mistakes / Misconceptions */}
                  {q.mistakes && q.mistakes.length > 0 && (
                    <div className="text-xs text-amber-300 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20">
                      <span className="font-mono font-bold block mb-1">Identified Misconceptions / Gaps:</span>
                      <ul className="list-disc list-inside space-y-0.5">
                        {q.mistakes.map((m, mIdx) => (
                          <li key={mIdx}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </InteractiveTiltCard>
        )}

        {/* Demonstrated Competencies vs Critical Skill Gaps */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Demonstrated Competencies */}
          <CursorGlowCard className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Demonstrated Competencies ({backendFinalReport?.demonstrated_skills.length || candidateReport?.verifiedStrengths?.length || 0})
                </h3>
              </div>
              <StatusBadge variant="emerald" size="sm">Evidence Validated</StatusBadge>
            </div>

            <div className="flex flex-wrap gap-2">
              {(backendFinalReport?.demonstrated_skills || candidateReport?.verifiedStrengths?.map(s => s.skill) || []).map((skill, idx) => (
                <span key={idx} className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-mono">
                  ✓ {skill}
                </span>
              ))}
            </div>
          </CursorGlowCard>

          {/* Critical Gaps & Weak Skills */}
          <CursorGlowCard className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Critical Skill Gaps ({backendFinalReport?.weak_skills.length || candidateReport?.criticalGaps?.length || 0})
                </h3>
              </div>
              <StatusBadge variant="amber" size="sm">Assessed Not Demonstrated</StatusBadge>
            </div>

            <div className="flex flex-wrap gap-2">
              {(backendFinalReport?.weak_skills || candidateReport?.criticalGaps?.map(g => g.skill) || []).map((skill, idx) => (
                <span key={idx} className="px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-mono">
                  ⚠ {skill}
                </span>
              ))}
            </div>
          </CursorGlowCard>
        </div>

        {/* Claimed Unvalidated & Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Claimed-But-Unvalidated */}
          <CursorGlowCard className="p-6 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <HelpCircle className="w-4 h-4 text-slate-400" />
              <h3 className="text-sm font-bold text-slate-100">
                Claimed Unvalidated Skills ({backendFinalReport?.claimed_unvalidated_skills.length || candidateReport?.unvalidatedClaims?.length || 0})
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Mentioned in candidate resume, but unassessed or unverified during active question rounds:
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {(backendFinalReport?.claimed_unvalidated_skills || candidateReport?.unvalidatedClaims || []).map((claim, idx) => (
                <span key={idx} className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-slate-300">
                  {claim}
                </span>
              ))}
            </div>
          </CursorGlowCard>

          {/* Actionable Learning Recommendations */}
          <CursorGlowCard className="p-6 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Sparkles className="w-4 h-4 text-violet-400" />
              <h3 className="text-sm font-bold text-slate-100">Actionable Learning Plan</h3>
            </div>
            <p className="text-xs text-slate-400">
              Personalized technical progression recommendations based on interview assessment:
            </p>
            <div className="space-y-2 pt-1">
              {(backendFinalReport?.recommendations || candidateReport?.suggestedFollowUpQuestions || []).map((rec, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                  <strong className="text-violet-400 font-mono">#{idx + 1}: </strong>{rec}
                </div>
              ))}
            </div>
          </CursorGlowCard>
        </div>

        {/* Human in the loop signoff */}
        <InteractiveTiltCard glowColor="violet" maxTilt={3} className="p-6">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-violet-400" />
              Recruiter Action Recommendation (Human-in-the-Loop)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              The AI assessment engine provides calibrated evidence; final hiring decisions strictly remain with the human committee:
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div
              onClick={() => handleOutcomeSelect('proceed_to_human_review')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                selectedOutcome === 'proceed_to_human_review'
                  ? 'bg-emerald-500/15 border-emerald-500/40 ring-1 ring-emerald-500'
                  : 'bg-slate-900 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="font-semibold text-xs text-emerald-400">Advance to Next Round</div>
              <div className="text-[11px] text-slate-400 mt-1">High evidence confidence; strong alignment with role requisites.</div>
            </div>

            <div
              onClick={() => handleOutcomeSelect('request_follow_up')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                selectedOutcome === 'request_follow_up'
                  ? 'bg-amber-500/15 border-amber-500/40 ring-1 ring-amber-500'
                  : 'bg-slate-900 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="font-semibold text-xs text-amber-400">Focused Technical Follow-Up</div>
              <div className="text-[11px] text-slate-400 mt-1">Probe identified skill gaps and unvalidated claims.</div>
            </div>

            <div
              onClick={() => handleOutcomeSelect('insufficient_evidence')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                selectedOutcome === 'insufficient_evidence'
                  ? 'bg-rose-500/15 border-rose-500/40 ring-1 ring-rose-500'
                  : 'bg-slate-900 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="font-semibold text-xs text-rose-400">Significant Competency Gaps</div>
              <div className="text-[11px] text-slate-400 mt-1">Substantial gaps against core prerequisite expectations.</div>
            </div>
          </div>
        </InteractiveTiltCard>
      </div>
    </div>
  );
};
