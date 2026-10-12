import React, { useRef, useState, useCallback, useEffect } from 'react';

interface MagneticButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  title?: string;
}

export const MagneticButton: React.FC<MagneticButtonProps> = ({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  title,
}) => {
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || prefersReducedMotion || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Dampened attraction: move button slightly towards cursor
    const pullDistance = 8;
    const deltaX = ((e.clientX - centerX) / (rect.width / 2)) * pullDistance;
    const deltaY = ((e.clientY - centerY) / (rect.height / 2)) * pullDistance;

    setPos({ x: deltaX, y: deltaY });
  }, [disabled, prefersReducedMotion]);

  const handleMouseLeave = () => {
    setPos({ x: 0, y: 0 });
  };

  const variantStyles = {
    primary: 'bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 text-[#111210] font-bold shadow-[0_0_25px_-5px_rgba(0,242,254,0.45)] hover:shadow-[0_0_35px_-2px_rgba(0,242,254,0.6)] border border-cyan-300/40',
    secondary: 'bg-slate-900/80 hover:bg-slate-800 text-slate-200 font-medium border border-slate-700/80 hover:border-cyan-400/40 shadow-md hover:shadow-cyan-500/10',
    ghost: 'bg-transparent hover:bg-slate-800/60 text-slate-300 hover:text-white border border-transparent hover:border-slate-700',
    danger: 'bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 font-medium border border-rose-500/30 shadow-[0_0_20px_-5px_rgba(244,63,94,0.3)]',
  };

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5',
    md: 'text-xs sm:text-sm px-4 py-2.5 rounded-xl gap-2',
    lg: 'text-sm sm:text-base px-6 py-3.5 rounded-xl gap-2.5',
  };

  return (
    <button
      ref={btnRef}
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: disabled || prefersReducedMotion ? 'none' : `translate(${pos.x}px, ${pos.y}px)`,
        transition: pos.x === 0 && pos.y === 0 ? 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)' : 'transform 0.1s ease-out',
      }}
      className={`relative inline-flex items-center justify-center tracking-wide active:scale-[0.97] transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none select-none ${
        variantStyles[variant]
      } ${sizeStyles[size]} ${className}`}
    >
      {children}
    </button>
  );
};
