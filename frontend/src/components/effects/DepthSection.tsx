import React from 'react';

interface DepthSectionProps {
  children: React.ReactNode;
  id?: string;
  className?: string;
  perspective?: number;
}

export const DepthSection: React.FC<DepthSectionProps> = ({
  children,
  id,
  className = '',
  perspective = 1200,
}) => {
  return (
    <section
      id={id}
      style={{ perspective: `${perspective}px` }}
      className={`relative w-full ${className}`}
    >
      <div className="w-full" style={{ transformStyle: 'preserve-3d' }}>
        {children}
      </div>
    </section>
  );
};
