import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: 'cyan' | 'violet' | 'mint' | 'none';
  onClick?: () => void;
  hoverEffect?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  glow = 'none',
  onClick,
  hoverEffect = false,
}) => {
  const glowStyles = {
    none: '',
    cyan: 'border-cyan-500/30 shadow-[0_0_20px_-5px_rgba(0,242,254,0.18)]',
    violet: 'border-violet-500/30 shadow-[0_0_20px_-5px_rgba(139,92,246,0.18)]',
    mint: 'border-emerald-500/30 shadow-[0_0_20px_-5px_rgba(16,185,129,0.18)]',
  };

  return (
    <div
      onClick={onClick}
      className={`relative rounded-2xl bg-white/75 backdrop-blur-md border border-cyan-500/15 p-5 transition-all duration-200 ${
        glowStyles[glow]
      } ${
        hoverEffect ? 'hover:border-cyan-400/40 hover:-translate-y-0.5 hover:shadow-xl cursor-pointer' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
