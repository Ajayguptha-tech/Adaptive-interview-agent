import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { StatusBadge, StatusVariant } from '../common/StatusBadge';

interface SectionHeadingProps {
  badge?: string;
  badgeVariant?: StatusVariant;
  title: string;
  subtitle?: string;
  align?: 'left' | 'center';
  className?: string;
}

export const SectionHeading: React.FC<SectionHeadingProps> = ({
  badge,
  badgeVariant = 'cyan',
  title,
  subtitle,
  align = 'center',
  className = '',
}) => {
  const shouldReduceMotion = useReducedMotion();

  const alignmentClass = align === 'center' ? 'text-center mx-auto' : 'text-left';

  if (shouldReduceMotion) {
    return (
      <div className={`max-w-2xl ${alignmentClass} ${className} space-y-3`}>
        {badge && <StatusBadge variant={badgeVariant} size="sm">{badge}</StatusBadge>}
        <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-100 tracking-tight">
          {title}
        </h2>
        {subtitle && <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{subtitle}</p>}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, filter: 'blur(8px)' }}
      whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={`max-w-2xl ${alignmentClass} ${className} space-y-3`}
    >
      {badge && (
        <div className={align === 'center' ? 'flex justify-center' : ''}>
          <StatusBadge variant={badgeVariant} size="sm">{badge}</StatusBadge>
        </div>
      )}
      <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-100 tracking-tight">
        {title}
      </h2>
      {subtitle && (
        <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{subtitle}</p>
      )}
    </motion.div>
  );
};
