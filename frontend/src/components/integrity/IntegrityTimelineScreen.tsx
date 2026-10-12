import React, { useState } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { Modal } from '../common/Modal';
import { IntegrityEvent, IntegrityStatus } from '../../types';
import { InterviewIntegrityAgent } from '../../agents/integrity';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  Info, 
  FileEdit, 
  Radio, 
  Server,
  AlertCircle,
  Plus,
  Filter,
  CheckCircle2,
  HelpCircle
} from 'lucide-react';

export const IntegrityTimelineScreen: React.FC = () => {
  const { 
    integrityEvents, 
    updateIntegrityEventStatus, 
    flagObservation,
    setActiveTab, 
    timeRemainingSeconds,
    activeInterview
  } = useInterview();

  const [selectedEvent, setSelectedEvent] = useState<IntegrityEvent | null>(null);
  const [reviewStatus, setReviewStatus] = useState<IntegrityStatus>('verified_benign');
  const [recruiterNotes, setRecruiterNotes] = useState('');
  const [statusFilter, setStatusFilter] = useState<IntegrityStatus | 'all'>('all');

  const handleOpenReview = (event: IntegrityEvent) => {
    setSelectedEvent(event);
    setReviewStatus(event.recruiterStatus);
    setRecruiterNotes(event.recruiterNotes || '');
  };

  const handleSaveReview = () => {
    if (!selectedEvent) return;
    updateIntegrityEventStatus(selectedEvent.id, reviewStatus, recruiterNotes);
    setSelectedEvent(null);
  };

  const filteredEvents = integrityEvents.filter(e => {
    if (statusFilter === 'all') return true;
    return e.recruiterStatus === statusFilter;
  });

  const pendingCount = integrityEvents.filter(e => e.recruiterStatus === 'pending_review').length;
  const reviewedCount = integrityEvents.length - pendingCount;

  // Format session time
  const formatTimer = (sec: number | null) => {
    if (sec === null) return '00:00';
    const elapsed = Math.max(0, 2400 - sec);
    const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const s = (elapsed % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-100">Interview Integrity Intelligence</h1>
            <StatusBadge variant="violet" size="sm">Observation Timeline</StatusBadge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Chronological sensor telemetry recorded during the session. Non-accusatory observations designed for human recruiter review.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={() => setActiveTab('live')}
          >
            Live Interview
          </MagneticButton>
          <MagneticButton
            variant="primary"
            size="sm"
            onClick={() => setActiveTab('report')}
          >
            Candidate Report
          </MagneticButton>
        </div>
      </div>

      {/* Ethical Standards Callout */}
      <div className="p-4 rounded-2xl bg-cyan-950/20 border border-cyan-500/20 flex items-start gap-3">
        <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="text-xs font-bold text-cyan-300 font-mono uppercase tracking-wide">
            Ethical Observation Protocol:
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            All telemetry entries represent raw sensory observations (acoustic fluctuations, document focus transitions, deliberation latency), <strong>never unilateral allegations of cheating</strong>. Human recruiters review all observations in context.
          </p>
        </div>
      </div>

      {/* Telemetry Filter & Manual Flag Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          <span className="text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Triage Filter:
          </span>
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-3 py-1 rounded-lg transition ${
              statusFilter === 'all'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            All Events ({integrityEvents.length})
          </button>
          <button
            onClick={() => setStatusFilter('pending_review')}
            className={`px-3 py-1 rounded-lg transition ${
              statusFilter === 'pending_review'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Pending Review ({pendingCount})
          </button>
          <button
            onClick={() => setStatusFilter('verified_benign')}
            className={`px-3 py-1 rounded-lg transition ${
              statusFilter === 'verified_benign'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Verified Benign
          </button>
          <button
            onClick={() => setStatusFilter('requires_followup')}
            className={`px-3 py-1 rounded-lg transition ${
              statusFilter === 'requires_followup'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Requires Follow-up
          </button>
        </div>

        <button
          onClick={() => flagObservation('Evaluator logged contextual sensor check during session.')}
          className="text-xs font-mono px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-cyan-300 hover:border-cyan-500/50 flex items-center gap-1.5 transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Log Manual Observation Flag</span>
        </button>
      </div>

      {/* Chronological Timeline Container */}
      <InteractiveTiltCard glowColor="mixed" maxTilt={4} className="p-6">
        <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-100">Chronological Telemetry Stream</h3>
            <p className="text-xs text-slate-400">
              {reviewedCount} reviewed • {pendingCount} pending recruiter confirmation
            </p>
          </div>
          <StatusBadge variant="slate" size="sm">
            Session Elapsed: {formatTimer(timeRemainingSeconds)}
          </StatusBadge>
        </div>

        {filteredEvents.length > 0 ? (
          <div className="relative border-l-2 border-slate-800 ml-4 pl-6 space-y-6">
            {/* Animated neon line */}
            <div className="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400 via-violet-400 to-transparent" />

            {filteredEvents.map((event) => {
              const isPending = event.recruiterStatus === 'pending_review';
              const isBenign = event.recruiterStatus === 'verified_benign';
              const isFollowUp = event.recruiterStatus === 'requires_followup';

              return (
                <div key={event.id} className="relative group">
                  <div className={`absolute -left-[35px] top-1 w-6 h-6 rounded-full bg-white border-2 ${
                    isPending ? 'border-amber-400 text-amber-400' : isBenign ? 'border-emerald-400 text-emerald-400' : 'border-rose-400 text-rose-400'
                  } flex items-center justify-center shadow-glow-cyan`}>
                    <ShieldAlert className="w-3.5 h-3.5" />
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-400/40 transition-all space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-cyan-300 font-bold">T+{event.timestampFormatted}</span>
                      <span className="text-slate-400">{event.confidence}% Detection Confidence</span>
                    </div>
                    <h4 className="text-sm font-semibold text-slate-100">{event.title}</h4>
                    <p className="text-xs text-slate-300 leading-relaxed">{event.description}</p>
                    
                    {event.recruiterNotes && (
                      <div className="text-[11px] text-slate-400 bg-slate-950/80 p-2 rounded-lg border border-slate-800 font-mono">
                        <strong className="text-cyan-300">Recruiter Notes: </strong>{event.recruiterNotes}
                      </div>
                    )}

                    <div className="pt-2 flex items-center justify-between">
                      <StatusBadge 
                        variant={isBenign ? 'emerald' : isFollowUp ? 'rose' : 'amber'} 
                        size="sm"
                      >
                        {event.recruiterStatus.replace('_', ' ').toUpperCase()}
                      </StatusBadge>

                      <button
                        onClick={() => handleOpenReview(event)}
                        className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        <FileEdit className="w-3 h-3" />
                        <span>Review Observation</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No integrity observations for this filter"
            description="Observations regarding acoustic fluctuations, cognitive pauses, and window focus transitions will stream automatically as candidate participates in live interviews."
            icon={<ShieldCheck className="w-8 h-8 text-emerald-400" />}
          />
        )}
      </InteractiveTiltCard>

      {/* Recruiter Review Modal */}
      {selectedEvent && (
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title="Review Telemetry Observation"
          subtitle={`Event T+${selectedEvent.timestampFormatted}: ${selectedEvent.title}`}
        >
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300">
              <strong className="text-slate-400 block mb-1">Sensor Observation Log:</strong>
              {selectedEvent.description}
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1.5">
                Assign Human Review Status:
              </label>
              <select
                value={reviewStatus}
                onChange={(e) => setReviewStatus(e.target.value as IntegrityStatus)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="verified_benign">Verified Benign / Cognitive Deliberation</option>
                <option value="verified_technical">Verified Technical Glitch / Hardware Handover</option>
                <option value="requires_followup">Requires Panel Follow-up</option>
                <option value="pending_review">Pending Review</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1.5">
                Recruiter Notes & Context:
              </label>
              <textarea
                rows={3}
                value={recruiterNotes}
                onChange={(e) => setRecruiterNotes(e.target.value)}
                placeholder="Document your contextual assessment..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <MagneticButton
                variant="primary"
                size="sm"
                onClick={handleSaveReview}
              >
                Save Resolution
              </MagneticButton>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
