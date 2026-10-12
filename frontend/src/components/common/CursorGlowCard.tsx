import React, { useRef, useState, useCallback } from 'react';

interface CursorGlowCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: 'cyan' | 'violet' | 'amber' | 'rose' | 'emerald';
  onClick?: () => void;
  hoverLift?: boolean;
}

export const CursorGlowCard: React.FC<CursorGlowCardProps> = ({
  children,
  className = '',
  glowColor = 'cyan',
  onClick,
  hoverLift = true,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [cursorPos, setCursorPos] = useState({ x: 50, y: 50 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const xPct = ((e.clientX - rect.left) / rect.width) * 100;
    const yPct = ((e.clientY - rect.top) / rect.height) * 100;
    setCursorPos({ x: xPct, y: yPct });
  }, []);

  const glowStyles = {
    cyan: 'rgba(0, 242, 254, 0.15)',
    violet: 'rgba(139, 92, 246, 0.15)',
    amber: 'rgba(245, 158, 11, 0.15)',
    rose: 'rgba(244, 63, 94, 0.15)',
    emerald: 'rgba(16, 185, 129, 0.15)',
  };

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`relative rounded-2xl bg-white/75 backdrop-blur-md border border-cyan-500/15 p-5 transition-all duration-300 overflow-hidden ${
        hoverLift ? 'hover:-translate-y-1 hover:border-cyan-400/40 hover:shadow-2xl' : ''
      } ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {/* Cursor Glow */}
      {isHovered && (
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-200 z-0"
          style={{
            background: `radial-gradient(circle 280px at ${cursorPos.x}% ${cursorPos.y}%, ${glowStyles[glowColor]}, transparent 70%)`,
          }}
        />
      )}

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
};
