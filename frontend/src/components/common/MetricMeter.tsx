import React from 'react';

interface MetricMeterProps {
  label: string;
  score?: number | null;       // 0 - 100, null if unassessed
  confidence?: number | null;  // 0 - 100, null if unassessed
  evidenceCount?: number;
  compact?: boolean;
}

export const MetricMeter: React.FC<MetricMeterProps> = ({
  label,
  score,
  confidence,
  evidenceCount,
  compact = false,
}) => {
  const isAssessed = score !== null && score !== undefined;
  const numScore = isAssessed ? score : 0;
  const numConf = confidence !== null && confidence !== undefined ? confidence : 0;

  const getScoreColor = (val: number) => {
    if (val >= 80) return 'from-cyan-400 to-blue-500';
    if (val >= 65) return 'from-violet-400 to-indigo-500';
    return 'from-amber-400 to-rose-500';
  };

  const getConfidenceBadgeColor = (val: number) => {
    if (val >= 80) return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10';
    if (val >= 60) return 'text-violet-400 border-violet-500/30 bg-violet-500/10';
    return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
  };

  return (
    <div className={`space-y-1.5 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-200">{label}</span>
          {evidenceCount !== undefined && evidenceCount > 0 && (
            <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50">
              {evidenceCount} ev
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 font-mono">
          <span className="text-slate-100 font-semibold">
            {isAssessed ? `${score}%` : '--%'}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${isAssessed ? getConfidenceBadgeColor(numConf) : 'text-slate-500 border-slate-800 bg-slate-900'}`}>
            {isAssessed ? `${confidence}% conf` : '--% conf'}
          </span>
        </div>
      </div>

      {/* Progress Bar Container */}
      <div className="relative w-full h-2 bg-slate-900/90 rounded-full overflow-hidden border border-slate-800">
        {/* Main Score Bar */}
        <div
          className={`h-full rounded-full ${isAssessed ? `bg-gradient-to-r ${getScoreColor(numScore)}` : 'bg-slate-800'} transition-all duration-500`}
          style={{ width: `${numScore}%` }}
        />
        {/* Confidence Overlay Indicator */}
        {isAssessed && (
          <div
            className="absolute top-0 bottom-0 bg-white/20 transition-all duration-500"
            style={{
              left: `${Math.max(0, numScore - (100 - numConf) * 0.15)}%`,
              width: `${Math.min(100, (100 - numConf) * 0.3)}%`,
            }}
          />
        )}
      </div>
    </div>
  );
};
