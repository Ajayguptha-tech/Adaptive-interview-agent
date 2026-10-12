import React from 'react';

interface AnimatedMetricProps {
  label: string;
  value?: string | number | null;
  unit?: string;
  subtext?: string;
  color?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'rose' | 'slate';
  icon?: React.ReactNode;
}

export const AnimatedMetric: React.FC<AnimatedMetricProps> = ({
  label,
  value,
  unit,
  subtext,
  color = 'cyan',
  icon,
}) => {
  const displayVal = value !== undefined && value !== null ? value : '--';

  const colorStyles = {
    cyan: 'text-cyan-400 drop-shadow-[0_0_12px_rgba(0,242,254,0.4)]',
    violet: 'text-violet-400 drop-shadow-[0_0_12px_rgba(139,92,246,0.4)]',
    emerald: 'text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.4)]',
    amber: 'text-amber-400 drop-shadow-[0_0_12px_rgba(245,158,11,0.4)]',
    rose: 'text-rose-400 drop-shadow-[0_0_12px_rgba(244,63,94,0.4)]',
    slate: 'text-slate-400',
  };

  const iconBgStyles = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    violet: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    slate: 'bg-slate-800 text-slate-400 border-slate-700',
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">{label}</span>
        {icon && (
          <div className={`p-1.5 rounded-lg border ${iconBgStyles[color]}`}>
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className={`text-3xl font-extrabold font-mono tracking-tight ${colorStyles[color]}`}>
          {displayVal}
        </span>
        {unit && <span className="text-sm font-mono text-slate-400">{unit}</span>}
      </div>

      {subtext && (
        <p className="text-[11px] font-mono text-slate-400 tracking-tight leading-relaxed">
          {subtext}
        </p>
      )}
    </div>
  );
};
