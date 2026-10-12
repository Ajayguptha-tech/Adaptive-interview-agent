import React from 'react';
import { Database, AlertCircle, Sparkles, Server } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  showFastApiBadge?: boolean;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
  showFastApiBadge = true,
  className = '',
}) => {
  return (
    <div
      className={`rounded-2xl bg-white/60 backdrop-blur-md border border-slate-800 p-8 sm:p-12 text-center flex flex-col items-center justify-center space-y-4 ${className}`}
    >
      <div className="relative p-4 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-violet-500/10 border border-cyan-500/25 shadow-glow-cyan text-cyan-400">
        {icon || <Database className="w-8 h-8 text-cyan-400" />}
      </div>

      <div className="space-y-1.5 max-w-md">
        <h3 className="text-base sm:text-lg font-bold text-slate-100">{title}</h3>
        <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>

      {showFastApiBadge && (
        <div className="pt-2">
          <StatusBadge variant="slate" size="sm" className="gap-1.5 text-slate-400">
            <Server className="w-3 h-3 text-cyan-400" />
            <span>Waiting for FastAPI connection (`VITE_API_BASE_URL`)</span>
          </StatusBadge>
        </div>
      )}

      {action && <div className="pt-2">{action}</div>}
    </div>
  );
};
