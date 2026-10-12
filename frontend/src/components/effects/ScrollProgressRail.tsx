import React, { useEffect, useState } from 'react';
import { motion, useScroll, useSpring } from 'framer-motion';

interface SectionMarker {
  id: string;
  label: string;
}

interface ScrollProgressRailProps {
  sections?: SectionMarker[];
}

export const ScrollProgressRail: React.FC<ScrollProgressRailProps> = ({
  sections = [
    { id: 'hero-section', label: 'Top' },
    { id: 'workflow-section', label: 'Workflow' },
    { id: 'modules-section', label: 'Pillars' },
    { id: 'ready-section', label: 'Launch' },
  ],
}) => {
  const { scrollYProgress } = useScroll();
  const scaleY = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 24,
    restDelta: 0.001,
  });

  const [activeSection, setActiveSection] = useState<string>(sections[0]?.id || '');

  useEffect(() => {
    const handleScroll = () => {
      const scrollPos = window.scrollY + window.innerHeight * 0.35;
      for (let i = sections.length - 1; i >= 0; i--) {
        const el = document.getElementById(sections[i].id);
        if (el && el.offsetTop <= scrollPos) {
          setActiveSection(sections[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [sections]);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="fixed right-4 top-1/2 -translate-y-1/2 z-40 hidden xl:flex flex-col items-center gap-6 pointer-events-auto select-none">
      {/* Background track line */}
      <div className="relative w-[2px] h-48 bg-slate-800/80 rounded-full overflow-hidden">
        {/* Animated Neon Fill Line */}
        <motion.div
          style={{ scaleY, originY: 0 }}
          className="absolute inset-0 w-full bg-gradient-to-b from-cyan-400 via-sky-300 to-violet-400 shadow-[0_0_12px_rgba(0,242,254,0.8)]"
        />
      </div>

      {/* Markers */}
      <div className="flex flex-col items-center gap-3">
        {sections.map((sec) => {
          const isActive = activeSection === sec.id;
          return (
            <button
              key={sec.id}
              onClick={() => scrollToSection(sec.id)}
              className="group relative flex items-center justify-end"
              title={`Scroll to ${sec.label}`}
            >
              {/* Tooltip Label */}
              <span className="absolute right-6 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300 bg-slate-900/90 border border-cyan-500/30 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-lg">
                {sec.label}
              </span>

              {/* Node Dot */}
              <div
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  isActive
                    ? 'w-2.5 h-2.5 bg-cyan-400 shadow-[0_0_10px_rgba(0,242,254,0.9)] scale-125'
                    : 'bg-slate-700 hover:bg-slate-500'
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
};
