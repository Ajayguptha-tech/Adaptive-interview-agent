import React, { useState } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { AnimatedMetric } from '../common/AnimatedMetric';
import { EmptyState } from '../common/EmptyState';
import { ScrollReveal } from '../effects/ScrollReveal';
import { 
  Users, 
  Activity, 
  AlertCircle, 
  CheckCircle2, 
  ChevronRight, 
  Search, 
  Plus, 
  Radio, 
  FileCheck2, 
  ShieldAlert, 
  Server, 
  Sparkles,
  BarChart3,
  Layers
} from 'lucide-react';

export const DashboardOverview: React.FC = () => {
  const { 
    candidates, 
    selectedCandidate, 
    selectCandidate, 
    setActiveTab,
    isBackendConnected,
    isDemoMode,
    isInterviewActive,
    competencies,
    evidenceList,
    integrityEvents
  } = useInterview();

  const [searchTerm, setSearchTerm] = useState('');

  // Calculate live KPI metrics
  const activeCount = isInterviewActive ? 1 : candidates.filter(c => c.status === 'in_progress').length;
  const coveragePercent = competencies.length > 0 
    ? Math.round((competencies.filter(c => c.score !== null).length / competencies.length) * 100)
    : null;
  const unvalidatedCount = competencies.filter(c => c.classification === 'claimed_needs_validation').length;
  const reviewCount = integrityEvents.filter(e => e.recruiterStatus === 'pending_review' || e.recruiterStatus === 'requires_followup').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-100">Recruiter Workspace</h1>
            <StatusBadge variant={isBackendConnected ? 'emerald' : 'cyan'} size="sm">
              {isBackendConnected ? 'FastAPI Connected' : isDemoMode ? 'Demo Mode Active' : 'Waiting for Connection'}
            </StatusBadge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time candidate pipeline, adaptive session telemetry, and evidence verification matrix.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={() => setActiveTab('setup')}
          >
            <Plus className="w-3.5 h-3.5 text-cyan-400" />
            <span>Setup New Interview</span>
          </MagneticButton>

          <MagneticButton
            variant="primary"
            size="sm"
            onClick={() => setActiveTab('live')}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Enter Live Cockpit</span>
          </MagneticButton>
        </div>
      </div>

      {/* 4 Summary KPI Cards with Depth & Hover Tilt */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Active Interviews */}
        <InteractiveTiltCard glowColor="cyan" maxTilt={6} className="p-5">
          <AnimatedMetric
            label="Active Interviews"
            value={activeCount}
            color="cyan"
            subtext={isInterviewActive ? '1 live adaptive cockpit running' : 'Standby'}
            icon={<Activity className="w-4 h-4" />}
          />
        </InteractiveTiltCard>

        {/* KPI 2: Evidence Coverage */}
        <InteractiveTiltCard glowColor="violet" maxTilt={6} className="p-5">
          <AnimatedMetric
            label="Evidence Coverage"
            value={coveragePercent}
            unit="%"
            color="violet"
            subtext={`${evidenceList.length} verified quotes indexed`}
            icon={<BarChart3 className="w-4 h-4" />}
          />
        </InteractiveTiltCard>

        {/* KPI 3: Skills Needing Validation */}
        <InteractiveTiltCard glowColor="amber" maxTilt={6} className="p-5">
          <AnimatedMetric
            label="Unvalidated Claims"
            value={competencies.length > 0 ? unvalidatedCount : null}
            color="amber"
            subtext="Pre-interview CV claims"
            icon={<AlertCircle className="w-4 h-4" />}
          />
        </InteractiveTiltCard>

        {/* KPI 4: Human Review Items */}
        <InteractiveTiltCard glowColor="rose" maxTilt={6} className="p-5">
          <AnimatedMetric
            label="Human Review Items"
            value={integrityEvents.length > 0 ? reviewCount : 0}
            color="rose"
            subtext="Timeline sensory observations"
            icon={<ShieldAlert className="w-4 h-4" />}
          />
        </InteractiveTiltCard>
      </div>

      {/* Main Grid: Left Candidate Pipeline Roster vs Right Active Details Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Candidates Roster */}
        <div className="lg:col-span-7 space-y-6">
          <CursorGlowCard className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
              <div>
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span>Candidate Pipeline Roster</span>
                  <span className="text-xs font-mono font-normal text-slate-400">
                    ({candidates.length} synced)
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Select a candidate to inspect competency mappings and launch adaptive sessions.
                </p>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by name or role..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-full sm:w-56"
                />
              </div>
            </div>

            {/* Candidate List or Clean Empty State */}
            {candidates.length > 0 ? (
              <div className="divide-y divide-slate-800">
                {candidates.map((cand) => (
                  <div
                    key={cand.id}
                    onClick={() => selectCandidate(cand.id)}
                    className="p-3.5 rounded-xl hover:bg-slate-800/40 transition cursor-pointer flex items-center justify-between"
                  >
                    <div>
                      <div className="text-sm font-semibold text-slate-200">{cand.name}</div>
                      <div className="text-xs text-slate-400">{cand.role}</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No candidates synced yet"
                description="Connect your FastAPI backend service or configure candidate data in the setup screen to populate this pipeline."
                icon={<Users className="w-8 h-8 text-cyan-400" />}
                action={
                  <MagneticButton
                    variant="secondary"
                    size="sm"
                    onClick={() => setActiveTab('setup')}
                  >
                    Go to Interview Setup
                  </MagneticButton>
                }
              />
            )}
          </CursorGlowCard>
        </div>

        {/* Right Column: Candidate Detail & Competency Coverage Overview */}
        <div className="lg:col-span-5 space-y-6">
          <CursorGlowCard className="p-6">
            <h3 className="text-sm font-bold text-slate-100 mb-1">Active Candidate Focus</h3>
            <p className="text-xs text-slate-400 mb-4">Detailed profile and competency overview</p>

            {selectedCandidate ? (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                  <h4 className="text-sm font-bold text-slate-100">{selectedCandidate.name}</h4>
                  <div className="text-xs text-cyan-300 font-mono mt-0.5">{selectedCandidate.role}</div>
                </div>
              </div>
            ) : (
              <EmptyState
                title="No candidate selected"
                description="Select a candidate from the roster or upload a resume in the setup panel to view role alignment."
                showFastApiBadge={false}
                icon={<Sparkles className="w-7 h-7 text-violet-400" />}
              />
            )}
          </CursorGlowCard>

          {/* Real-time Competency Progress Container */}
          <CursorGlowCard className="p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-slate-100">Live Competency Coverage</h3>
              <StatusBadge variant="slate" size="sm">--% Verified</StatusBadge>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Competency score and confidence bounds are calculated during live interview speech extraction.
            </p>

            <EmptyState
              title="Interview data will appear here"
              description="As the candidate answers adaptive questions, structured evidence will populate real-time technical, behavioral, and role competencies."
              showFastApiBadge={false}
              icon={<Layers className="w-7 h-7 text-cyan-400" />}
            />
          </CursorGlowCard>
        </div>
      </div>
    </div>
  );
};
