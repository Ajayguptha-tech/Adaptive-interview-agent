import React from 'react';

export type StatusVariant = 
  | 'cyan' 
  | 'violet' 
  | 'emerald' 
  | 'amber' 
  | 'rose' 
  | 'slate'
  | 'live';

interface StatusBadgeProps {
  children: React.ReactNode;
  variant?: StatusVariant;
  size?: 'sm' | 'md';
  className?: string;
  dotPulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  children,
  variant = 'cyan',
  size = 'md',
  className = '',
  dotPulse = false,
}) => {
  const variantStyles = {
    cyan: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    violet: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    rose: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    slate: 'bg-slate-800/60 text-slate-400 border-slate-700/60',
    live: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.25)]',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border tracking-wide font-mono ${
        variantStyles[variant]
      } ${sizeStyles[size]} ${className}`}
    >
      {dotPulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
        </span>
      )}
      {children}
    </span>
  );
};
