import React from 'react';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  glow?: 'cyan' | 'violet' | 'none';
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className = '',
  glow = 'none',
}) => {
  const glowStyles = {
    none: '',
    cyan: 'shadow-[0_0_25px_-5px_rgba(0,242,254,0.15)] border-cyan-500/25',
    violet: 'shadow-[0_0_25px_-5px_rgba(139,92,246,0.15)] border-violet-500/25',
  };

  return (
    <div
      className={`rounded-2xl bg-white/80 backdrop-blur-xl border border-cyan-500/15 p-5 shadow-2xl transition-all duration-300 ${
        glowStyles[glow]
      } ${className}`}
    >
      {children}
    </div>
  );
};
