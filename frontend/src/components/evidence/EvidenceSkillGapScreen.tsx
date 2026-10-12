import React, { useState } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { SkillClassification, Competency } from '../../types';
import { 
  GitCompare, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  XCircle, 
  Quote, 
  Filter, 
  Search,
  Sparkles,
  ArrowRight,
  Layers,
  Activity,
  Check
} from 'lucide-react';

export const EvidenceSkillGapScreen: React.FC = () => {
  const { evidenceList, competencies, setActiveTab, selectedCandidate } = useInterview();

  const [selectedFilter, setSelectedFilter] = useState<SkillClassification | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Group competencies into 4 Quadrants
  const demonstrated = competencies.filter(c => c.classification === 'demonstrated' || (c.score !== null && (c.score || 0) >= 75));
  const needsValidation = competencies.filter(c => c.classification === 'claimed_needs_validation' || (c.score !== null && (c.score || 0) >= 60 && (c.score || 0) < 75));
  const notAssessed = competencies.filter(c => c.score === null || c.classification === 'not_assessed');
  const skillGaps = competencies.filter(c => c.classification === 'skill_gap' || (c.score !== null && (c.score || 0) < 60));

  // Filter competencies based on active selection and search
  const filteredCompetencies = competencies.filter(comp => {
    // Classification match
    if (selectedFilter !== 'all') {
      if (selectedFilter === 'demonstrated' && !demonstrated.some(d => d.id === comp.id)) return false;
      if (selectedFilter === 'claimed_needs_validation' && !needsValidation.some(d => d.id === comp.id)) return false;
      if (selectedFilter === 'not_assessed' && !notAssessed.some(d => d.id === comp.id)) return false;
      if (selectedFilter === 'skill_gap' && !skillGaps.some(d => d.id === comp.id)) return false;
    }

    // Search query match
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = comp.name.toLowerCase().includes(q);
      const matchCategory = comp.category.toLowerCase().includes(q);
      const matchEvidence = evidenceList.some(e => e.competencyId === comp.id && e.quote.toLowerCase().includes(q));
      if (!matchName && !matchCategory && !matchEvidence) return false;
    }

    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-100">Resume-to-Interview Skill Gap Intelligence</h1>
            <StatusBadge variant="cyan" size="sm">Evidence Matrix</StatusBadge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Reconciles candidate claims against verified speech quotations. Distinguishes observed facts from unassessed assumptions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={() => setActiveTab('live')}
          >
            Live Interview Cockpit
          </MagneticButton>
          <MagneticButton
            variant="primary"
            size="sm"
            onClick={() => setActiveTab('report')}
          >
            Review Report Dossier
          </MagneticButton>
        </div>
      </div>

      {/* 4 Quadrants Summary Counters with Hover Tilt */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Quadrant 1: Demonstrated */}
        <InteractiveTiltCard glowColor="emerald" maxTilt={6} className="p-5 cursor-pointer" onClick={() => setSelectedFilter('demonstrated')}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-emerald-400">Demonstrated</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-emerald-300">
            {demonstrated.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Substantiated with verbatim quotations</div>
        </InteractiveTiltCard>

        {/* Quadrant 2: Claimed - Needs Validation */}
        <InteractiveTiltCard glowColor="amber" maxTilt={6} className="p-5 cursor-pointer" onClick={() => setSelectedFilter('claimed_needs_validation')}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-amber-400">Claimed — Needs Validation</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-amber-300">
            {needsValidation.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Claimed in CV; requires deeper evidence</div>
        </InteractiveTiltCard>

        {/* Quadrant 3: Not Assessed */}
        <InteractiveTiltCard glowColor="mixed" maxTilt={6} className="p-5 cursor-pointer" onClick={() => setSelectedFilter('not_assessed')}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-300">Not Assessed</span>
            <HelpCircle className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-slate-200">
            {notAssessed.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Unaddressed in current interview queue</div>
        </InteractiveTiltCard>

        {/* Quadrant 4: Skill Gap */}
        <InteractiveTiltCard glowColor="rose" maxTilt={6} className="p-5 cursor-pointer" onClick={() => setSelectedFilter('skill_gap')}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-rose-400">Skill Gap</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-rose-300">
            {skillGaps.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Evaluated sub-threshold or missing claim</div>
        </InteractiveTiltCard>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          <button
            onClick={() => setSelectedFilter('all')}
            className={`px-3 py-1 rounded-lg text-xs font-mono transition ${
              selectedFilter === 'all'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            All Competencies ({competencies.length})
          </button>
          <button
            onClick={() => setSelectedFilter('demonstrated')}
            className={`px-3 py-1 rounded-lg text-xs font-mono transition ${
              selectedFilter === 'demonstrated'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Demonstrated ({demonstrated.length})
          </button>
          <button
            onClick={() => setSelectedFilter('claimed_needs_validation')}
            className={`px-3 py-1 rounded-lg text-xs font-mono transition ${
              selectedFilter === 'claimed_needs_validation'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Needs Validation ({needsValidation.length})
          </button>
          <button
            onClick={() => setSelectedFilter('not_assessed')}
            className={`px-3 py-1 rounded-lg text-xs font-mono transition ${
              selectedFilter === 'not_assessed'
                ? 'bg-slate-700/40 text-slate-200 border border-slate-600'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Not Assessed ({notAssessed.length})
          </button>
          <button
            onClick={() => setSelectedFilter('skill_gap')}
            className={`px-3 py-1 rounded-lg text-xs font-mono transition ${
              selectedFilter === 'skill_gap'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Skill Gaps ({skillGaps.length})
          </button>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search skill, category or quote..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-full sm:w-64 font-sans"
          />
        </div>
      </div>

      {/* Main Evidence Grid */}
      {filteredCompetencies.length > 0 ? (
        <div className="space-y-4">
          {filteredCompetencies.map((comp) => {
            const quotes = evidenceList.filter(e => e.competencyId === comp.id);
            const isAssessed = comp.score !== null;

            return (
              <CursorGlowCard key={comp.id} className="p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-100">{comp.name}</h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                        {comp.category}
                      </span>
                    </div>
                    {comp.description && (
                      <p className="text-xs text-slate-400 mt-1 max-w-2xl">{comp.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-4 bg-slate-900/80 px-4 py-2 rounded-xl border border-slate-800 text-xs font-mono shrink-0">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Score:</span>
                      <strong className={isAssessed ? 'text-cyan-400 text-sm' : 'text-slate-500 text-sm'}>
                        {isAssessed ? `${comp.score}/100` : '--'}
                      </strong>
                    </div>
                    <div className="border-l border-slate-800 pl-4">
                      <span className="text-slate-400 block text-[10px]">Confidence:</span>
                      <strong className={isAssessed ? 'text-violet-400 text-sm' : 'text-slate-500 text-sm'}>
                        {isAssessed ? `${comp.confidence}%` : '--'}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Evidence Citations */}
                <div>
                  <h4 className="text-xs font-mono text-slate-400 mb-2 flex items-center gap-1.5">
                    <Quote className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Verified Audio Citations ({quotes.length}):</span>
                  </h4>

                  {quotes.length > 0 ? (
                    <div className="space-y-2">
                      {quotes.map((q) => (
                        <div key={q.id} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1">
                          <div className="flex items-center justify-between text-[10px] font-mono">
                            <span className="text-cyan-400 font-bold">T+{q.timestamp}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-emerald-400">+{q.scoreImpact} Score</span>
                              <span className="text-violet-400">+{q.confidenceImpact}% Confidence</span>
                            </div>
                          </div>
                          <p className="text-slate-200 italic text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                            {q.quote}
                          </p>
                          <div className="text-[10px] text-slate-400 pt-0.5">
                            <strong className="text-slate-300">Rationale: </strong>{q.rationale}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-slate-900/30 border border-slate-800/60 text-xs text-slate-500 italic">
                      No verbatim audio citations extracted for this competency yet.
                    </div>
                  )}
                </div>
              </CursorGlowCard>
            );
          })}
        </div>
      ) : (
        <CursorGlowCard className="p-8">
          <EmptyState
            title="No evidence found for this filter"
            description="Start an active interview session to evaluate candidate speech and extract real verifiable quotes for this matrix."
            icon={<GitCompare className="w-8 h-8 text-cyan-400" />}
            action={
              <MagneticButton
                variant="secondary"
                size="sm"
                onClick={() => setActiveTab('live')}
              >
                Go to Live Interview
              </MagneticButton>
            }
          />
        </CursorGlowCard>
      )}
    </div>
  );
};
