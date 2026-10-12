import React, { useState } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { 
  Briefcase, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  Sparkles, 
  Radio, 
  Clock, 
  Gauge, 
  Layers, 
  Server,
  ArrowRight,
  User,
  AlertTriangle,
  FileCheck2,
  RefreshCw,
  ShieldCheck,
  Award
} from 'lucide-react';

const SUGGESTED_ROLES = [
  'Senior Python Engineer',
  'Full-Stack Developer',
  'Backend Engineer',
  'Java Developer',
  'C++ Developer',
  'Data Analyst',
  'Data Engineer',
  'Machine Learning Engineer',
  'AI/ML Engineer',
  'SQL Database Specialist',
  'Frontend Developer',
  'General Software Engineer'
];

export const InterviewSetupScreen: React.FC = () => {
  const { 
    uploadResumeFile,
    startBackendSession,
    backendResumeData,
    backendEligibility,
    backendIntegrity,
    isBackendConnected,
    isDemoMode
  } = useInterview();

  // Step 1: Input state
  const [targetRole, setTargetRole] = useState('Senior Python Engineer');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Step 2: Config state
  const [interviewMode, setInterviewMode] = useState<'mock' | 'predefined'>('mock');
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [difficulty, setDifficulty] = useState<string>('adaptive');
  const [isStarting, setIsStarting] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setUploadError('File exceeds 10MB limit. Please upload a smaller document.');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleAnalyzeResume = async () => {
    if (!selectedFile) {
      setUploadError('Please select a resume file (.pdf, .docx, or .txt).');
      return;
    }
    if (!targetRole.trim()) {
      setUploadError('Please specify your target technical role.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      await uploadResumeFile(selectedFile, targetRole.trim());
    } catch (err: any) {
      setUploadError(err.message || 'Failed to analyze resume. Check backend connection.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartInterview = async () => {
    setIsStarting(true);
    try {
      await startBackendSession({
        mode: interviewMode,
        count: questionCount,
        difficulty
      });
    } catch (err: any) {
      setUploadError(err.message || 'Failed to start interview.');
      setIsStarting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-100">Adaptive Technical Assessment Setup</h1>
            <StatusBadge variant="cyan" size="sm">Resume-First Verification</StatusBadge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Upload candidate resume to extract claims, evaluate role eligibility, and configure adaptive technical agenda.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge variant={isBackendConnected ? 'emerald' : 'amber'} size="sm">
            {isBackendConnected ? 'FastAPI Connected' : 'Demo Mode Active'}
          </StatusBadge>
        </div>
      </div>

      {uploadError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* PHASE 1: RESUME UPLOAD & ROLE SPECIFICATION (If not yet uploaded) */}
      {!backendResumeData ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 space-y-6">
            <InteractiveTiltCard glowColor="cyan" maxTilt={4} className="p-6 space-y-6">
              <div className="border-b border-slate-800 pb-4">
                <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Step 1 • Profile Specification</span>
                <h2 className="text-lg font-bold text-slate-100 mt-1">Target Engineering Role</h2>
                <p className="text-xs text-slate-400 mt-0.5">Specify the target technical domain for calibrated competency benchmarking.</p>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-2">
                  Target Technical Role <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Python Engineer, Full-Stack Developer, ML Engineer"
                  className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-cyan-400 transition-colors"
                />
                
                {/* Role quick pills */}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {SUGGESTED_ROLES.slice(0, 6).map(r => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setTargetRole(r)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border transition-all ${
                        targetRole === r 
                          ? 'bg-[#c6ee2e] text-[#111210] border-[#c6ee2e] font-semibold' 
                          : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-600'
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              {/* Resume File Upload Drop Zone */}
              <div className="pt-2">
                <label className="block text-xs font-mono text-slate-300 mb-2">
                  Candidate Resume Document <span className="text-rose-400">*</span>
                </label>
                <div 
                  className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
                    selectedFile 
                      ? 'border-[#c6ee2e]/60 bg-[#c6ee2e]/5' 
                      : 'border-slate-700 hover:border-cyan-400/50 bg-slate-900/50'
                  }`}
                  onClick={() => document.getElementById('resume-file-input')?.click()}
                >
                  <input
                    id="resume-file-input"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="mx-auto w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-3">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  {selectedFile ? (
                    <div>
                      <div className="text-sm font-semibold text-slate-100 flex items-center justify-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#c6ee2e]" />
                        <span>{selectedFile.name}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        {(selectedFile.size / 1024).toFixed(1)} KB • Click to change file
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        Drop resume here or <span className="text-cyan-400 underline underline-offset-2">browse files</span>
                      </p>
                      <p className="text-xs text-slate-500 mt-1">Supports PDF, DOCX, and TXT • Max 10MB</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Submit Action */}
              <div className="pt-2">
                <MagneticButton
                  variant="primary"
                  size="lg"
                  className="w-full flex items-center justify-center gap-2"
                  disabled={!selectedFile || isUploading}
                  onClick={handleAnalyzeResume}
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-[#111210]" />
                      <span>Analyzing Claims & Assessing Eligibility...</span>
                    </>
                  ) : (
                    <>
                      <span>Analyze Resume & Check Role Eligibility</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </MagneticButton>
              </div>
            </InteractiveTiltCard>
          </div>

          {/* Right Explanatory Card */}
          <div className="lg:col-span-5 space-y-4">
            <CursorGlowCard glowColor="violet" className="p-6 space-y-4">
              <div className="flex items-center gap-2 text-violet-400">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100 text-sm">Automated Integrity & Eligibility</h3>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Our evidence-first intelligence engine verifies resume technical claims against industry benchmarks:
              </p>
              <ul className="text-xs text-slate-400 space-y-2.5">
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Role Prerequisite Match:</strong> Cross-checks candidate skills with required role competencies.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Claim Integrity Audit:</strong> Non-accusatory verification of timelines and skill depth claims.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Dynamic Agenda:</strong> Builds personalized rubrics to probe unvalidated competencies.</span>
                </li>
              </ul>
            </CursorGlowCard>
          </div>
        </div>
      ) : (
        /* PHASE 2 & 3: PROFILE VERIFIED, ELIGIBILITY & INTERVIEW CONFIGURATION */
        <div className="space-y-6">
          {/* Candidate Profile Summary Card */}
          <InteractiveTiltCard glowColor="mixed" maxTilt={3} className="p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#c6ee2e] text-[#111210] flex items-center justify-center font-bold text-lg">
                  {backendResumeData.candidate_name[0] || 'C'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-100">{backendResumeData.candidate_name}</h2>
                    <StatusBadge variant="emerald" size="sm">Profile Verified</StatusBadge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Target Role: <strong className="text-slate-200">{backendResumeData.target_role}</strong> • {backendResumeData.experience_years} Years Experience
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <StatusBadge variant="cyan" size="sm">ATS Match: {backendResumeData.ats_score}%</StatusBadge>
                <StatusBadge variant="violet" size="sm">{backendResumeData.routed_track.toUpperCase()} Track</StatusBadge>
              </div>
            </div>

            {/* Extracted Skills Chips */}
            <div className="mt-4">
              <span className="text-xs font-mono text-slate-400 block mb-2">Extracted Resume Competencies:</span>
              <div className="flex flex-wrap gap-1.5">
                {backendResumeData.extracted_skills.map((s) => (
                  <span key={s} className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </InteractiveTiltCard>

          {/* Role Eligibility & Integrity Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Role Eligibility Card */}
            <CursorGlowCard glowColor="cyan" className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-cyan-400" />
                  <h3 className="font-semibold text-slate-100 text-sm">Role Readiness Eligibility</h3>
                </div>
                {backendEligibility && (
                  <StatusBadge 
                    variant={backendEligibility.outcome === 'eligible' ? 'emerald' : backendEligibility.outcome === 'potentially_eligible' ? 'amber' : 'rose'} 
                    size="sm"
                  >
                    {backendEligibility.outcome === 'eligible' ? 'Eligible' : backendEligibility.outcome === 'potentially_eligible' ? 'Potentially Eligible' : 'Not Currently Eligible'}
                  </StatusBadge>
                )}
              </div>

              {backendEligibility ? (
                <div className="space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 block mb-1">Found Prerequisites:</span>
                    <div className="flex flex-wrap gap-1">
                      {backendEligibility.competencies_found.slice(0, 5).map(c => (
                        <span key={c} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                          ✓ {c}
                        </span>
                      ))}
                    </div>
                  </div>

                  {backendEligibility.missing_competencies.length > 0 && (
                    <div>
                      <span className="text-slate-400 block mb-1">Missing / Weak Skills:</span>
                      <div className="flex flex-wrap gap-1">
                        {backendEligibility.missing_competencies.slice(0, 4).map(m => (
                          <span key={m} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                            ⚠ {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {backendEligibility.reasons.length > 0 && (
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-slate-400 block mb-1">Assessment Findings:</span>
                      <ul className="space-y-1 text-slate-300 list-disc list-inside">
                        {backendEligibility.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-400">Assessing eligibility against role requirement profile...</p>
              )}
            </CursorGlowCard>

            {/* Resume Integrity Card */}
            <CursorGlowCard glowColor="violet" className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-violet-400" />
                  <h3 className="font-semibold text-slate-100 text-sm">Resume Integrity Audit</h3>
                </div>
                {backendIntegrity && (
                  <StatusBadge 
                    variant={backendIntegrity.outcome === 'no_inconsistencies' ? 'emerald' : 'amber'} 
                    size="sm"
                  >
                    {backendIntegrity.outcome === 'no_inconsistencies' ? 'No Inconsistencies' : 'Potential Inconsistencies'}
                  </StatusBadge>
                )}
              </div>

              {backendIntegrity ? (
                <div className="space-y-3 text-xs">
                  <p className="text-slate-300 leading-relaxed">
                    {backendIntegrity.summary}
                  </p>
                  
                  {backendIntegrity.positive_indicators.length > 0 && (
                    <div>
                      <span className="text-slate-400 block mb-1">Positive Integrity Indicators:</span>
                      <div className="space-y-1 text-emerald-300">
                        {backendIntegrity.positive_indicators.map((p, i) => (
                          <div key={i} className="flex items-center gap-1.5">
                            <span>✓</span>
                            <span>{p}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-400">Analyzing career progression and claim consistency...</p>
              )}
            </CursorGlowCard>
          </div>

          {/* Interview Configuration Card */}
          <InteractiveTiltCard glowColor="cyan" maxTilt={3} className="p-6 space-y-6">
            <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-100">Assessment Configuration</h3>
                <p className="text-xs text-slate-400">Configure interview mode and duration (enforcing 5–10 calibrated questions).</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Interview Mode */}
              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-300">Interview Mode</label>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => setInterviewMode('mock')}
                    className={`w-full p-3 rounded-xl border text-left transition-all ${
                      interviewMode === 'mock'
                        ? 'bg-[#c6ee2e]/10 border-[#c6ee2e] text-slate-100'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-semibold text-xs flex items-center gap-1.5">
                      <span>✨ Mock Interview</span>
                      {interviewMode === 'mock' && <CheckCircle2 className="w-3.5 h-3.5 text-[#c6ee2e]" />}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      Dynamic questions adapted live from candidate answers and skill gaps.
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setInterviewMode('predefined')}
                    className={`w-full p-3 rounded-xl border text-left transition-all ${
                      interviewMode === 'predefined'
                        ? 'bg-[#c6ee2e]/10 border-[#c6ee2e] text-slate-100'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-semibold text-xs flex items-center gap-1.5">
                      <span>📚 Trained Questions</span>
                      {interviewMode === 'predefined' && <CheckCircle2 className="w-3.5 h-3.5 text-[#c6ee2e]" />}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      Curated benchmark question bank targeted to verified resume claims.
                    </div>
                  </button>
                </div>
              </div>

              {/* Assessment Length: 5 - 10 questions */}
              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-300">Assessment Length</label>
                <div className="space-y-2">
                  {[
                    { count: 5, label: '5 Questions', sub: 'Standard assessment (Recommended)' },
                    { count: 8, label: '8 Questions', sub: 'In-depth competency evaluation' },
                    { count: 10, label: '10 Questions', sub: 'Comprehensive technical review' },
                  ].map((item) => (
                    <button
                      key={item.count}
                      type="button"
                      onClick={() => setQuestionCount(item.count)}
                      className={`w-full p-2.5 rounded-xl border text-left transition-all ${
                        questionCount === item.count
                          ? 'bg-[#c6ee2e]/10 border-[#c6ee2e] text-slate-100'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-semibold text-xs">{item.label}</div>
                      <div className="text-[10px] text-slate-500">{item.sub}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Difficulty Progression */}
              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-300">Difficulty Progression</label>
                <div className="space-y-2">
                  {[
                    { diff: 'adaptive', label: 'Adaptive (Recommended)', sub: 'Dynamically scales with answer performance' },
                    { diff: 'intermediate', label: 'Intermediate', sub: 'Core practical engineering questions' },
                    { diff: 'advanced', label: 'Advanced', sub: 'Deep systems, concurrency, and architecture' },
                  ].map((item) => (
                    <button
                      key={item.diff}
                      type="button"
                      onClick={() => setDifficulty(item.diff)}
                      className={`w-full p-2.5 rounded-xl border text-left transition-all ${
                        difficulty === item.diff
                          ? 'bg-[#c6ee2e]/10 border-[#c6ee2e] text-slate-100'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-semibold text-xs">{item.label}</div>
                      <div className="text-[10px] text-slate-500">{item.sub}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Launch Action */}
            <div className="pt-4 border-t border-slate-800 flex justify-end">
              <MagneticButton
                variant="primary"
                size="lg"
                className="flex items-center gap-2"
                disabled={isStarting}
                onClick={handleStartInterview}
              >
                {isStarting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-[#111210]" />
                    <span>Preparing Calibrated Agenda...</span>
                  </>
                ) : (
                  <>
                    <span>Start Technical Interview</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </MagneticButton>
            </div>
          </InteractiveTiltCard>
        </div>
      )}
    </div>
  );
};
