import React from 'react';
import { SkillClassification, QuestionDifficulty, IntegritySeverity, RecommendationOutcome } from '../../types';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: 'cyan' | 'violet' | 'mint' | 'amber' | 'rose' | 'slate';
  className?: string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ 
  children, 
  variant = 'cyan', 
  className = '', 
  size = 'md' 
}) => {
  const variantStyles = {
    cyan: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    violet: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
    mint: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    rose: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    slate: 'bg-slate-700/30 text-slate-300 border-slate-600/30',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-medium',
  };

  return (
    <span 
      className={`inline-flex items-center gap-1.5 rounded-full border tracking-wide font-mono ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};

export const SkillClassificationBadge: React.FC<{ classification: SkillClassification; size?: 'sm' | 'md' }> = ({ classification, size = 'sm' }) => {
  switch (classification) {
    case 'demonstrated':
      return <Badge variant="mint" size={size}>● Demonstrated</Badge>;
    case 'claimed_needs_validation':
      return <Badge variant="amber" size={size}>▲ Claimed — Needs Validation</Badge>;
    case 'not_assessed':
      return <Badge variant="slate" size={size}>○ Not Assessed</Badge>;
    case 'skill_gap':
      return <Badge variant="rose" size={size}>✕ Skill Gap</Badge>;
    default:
      return <Badge variant="slate" size={size}>{classification}</Badge>;
  }
};

export const DifficultyBadge: React.FC<{ difficulty: QuestionDifficulty }> = ({ difficulty }) => {
  switch (difficulty) {
    case 'foundational':
      return <Badge variant="mint" size="sm">Level: Foundational</Badge>;
    case 'intermediate':
      return <Badge variant="cyan" size="sm">Level: Intermediate</Badge>;
    case 'advanced':
      return <Badge variant="violet" size="sm">Level: Advanced Architectural</Badge>;
  }
};

export const SeverityBadge: React.FC<{ severity: IntegritySeverity }> = ({ severity }) => {
  switch (severity) {
    case 'advisory':
      return <Badge variant="slate" size="sm">Advisory</Badge>;
    case 'low':
      return <Badge variant="cyan" size="sm">Low Impact</Badge>;
    case 'medium':
      return <Badge variant="amber" size="sm">Medium Attention</Badge>;
    case 'high':
      return <Badge variant="rose" size="sm">High Priority Review</Badge>;
  }
};

export const OutcomeBadge: React.FC<{ outcome: RecommendationOutcome }> = ({ outcome }) => {
  switch (outcome) {
    case 'proceed_to_human_review':
      return <Badge variant="mint" size="md">Proceed to Human Review</Badge>;
    case 'request_follow_up':
      return <Badge variant="amber" size="md">Request Follow-up</Badge>;
    case 'insufficient_evidence':
      return <Badge variant="rose" size="md">Insufficient Evidence</Badge>;
  }
};
