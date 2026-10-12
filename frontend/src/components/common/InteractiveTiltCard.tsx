import React, { useRef, useState, useCallback, useEffect } from 'react';

interface InteractiveTiltCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;      // Maximum tilt angle in degrees, default 10
  perspective?: number;  // Perspective depth in px, default 1000
  glowColor?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'rose' | 'mixed';
  onClick?: () => void;
  as?: 'div' | 'section' | 'article';
}

export const InteractiveTiltCard: React.FC<InteractiveTiltCardProps> = ({
  children,
  className = '',
  maxTilt = 10,
  perspective = 1000,
  glowColor = 'mixed',
  onClick,
  as: Component = 'div',
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [cursorPos, setCursorPos] = useState({ x: 50, y: 50 });
  const [isHovered, setIsHovered] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const xPct = (x / rect.width) * 100;
    const yPct = (y / rect.height) * 100;

    // Calculate rotation: center is 0 deg
    const rotateY = ((x / rect.width) - 0.5) * (maxTilt * 2);
    const rotateX = -(((y / rect.height) - 0.5) * (maxTilt * 2));

    setTilt({ x: rotateX, y: rotateY });
    setCursorPos({ x: xPct, y: yPct });
  }, [maxTilt, prefersReducedMotion]);

  const handleMouseEnter = () => setIsHovered(true);

  const handleMouseLeave = () => {
    setIsHovered(false);
    setTilt({ x: 0, y: 0 });
  };

  const getGlowGradient = () => {
    switch (glowColor) {
      case 'cyan':
        return `radial-gradient(circle 320px at ${cursorPos.x}% ${cursorPos.y}%, rgba(0, 242, 254, 0.16), transparent 70%)`;
      case 'violet':
        return `radial-gradient(circle 320px at ${cursorPos.x}% ${cursorPos.y}%, rgba(139, 92, 246, 0.16), transparent 70%)`;
      case 'emerald':
        return `radial-gradient(circle 320px at ${cursorPos.x}% ${cursorPos.y}%, rgba(16, 185, 129, 0.16), transparent 70%)`;
      case 'amber':
        return `radial-gradient(circle 320px at ${cursorPos.x}% ${cursorPos.y}%, rgba(245, 158, 11, 0.16), transparent 70%)`;
      case 'rose':
        return `radial-gradient(circle 320px at ${cursorPos.x}% ${cursorPos.y}%, rgba(244, 63, 94, 0.16), transparent 70%)`;
      case 'mixed':
      default:
        return `radial-gradient(circle 360px at ${cursorPos.x}% ${cursorPos.y}%, rgba(0, 242, 254, 0.14), rgba(139, 92, 246, 0.08) 50%, transparent 75%)`;
    }
  };

  const transformStyle = prefersReducedMotion ? {} : {
    transform: isHovered
      ? `perspective(${perspective}px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) translateY(-4px) translateZ(10px)`
      : `perspective(${perspective}px) rotateX(0deg) rotateY(0deg) translateY(0px) translateZ(0px)`,
    transition: isHovered ? 'transform 0.1s ease-out' : 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
    transformStyle: 'preserve-3d' as const,
  };

  return (
    <Component
      ref={cardRef as any}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={transformStyle}
      className={`relative rounded-2xl bg-white/80 backdrop-blur-xl border border-cyan-500/15 p-6 shadow-xl transition-shadow duration-300 ${
        isHovered ? 'border-cyan-400/40 shadow-[0_20px_40px_-15px_rgba(0,242,254,0.18)]' : ''
      } ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {/* Dynamic Cursor Glow Layer */}
      {isHovered && !prefersReducedMotion && (
        <div
          className="absolute inset-0 rounded-2xl pointer-events-none transition-opacity duration-300 z-0"
          style={{ background: getGlowGradient() }}
        />
      )}

      {/* Subtle Neon Edge Rim */}
      <div 
        className={`absolute inset-0 rounded-2xl pointer-events-none border border-transparent transition-colors duration-300 z-10 ${
          isHovered ? 'border-cyan-400/25' : ''
        }`} 
      />

      {/* Internal Content (preserve 3D depth) */}
      <div className="relative z-20" style={{ transformStyle: 'preserve-3d' }}>
        {children}
      </div>
    </Component>
  );
};
