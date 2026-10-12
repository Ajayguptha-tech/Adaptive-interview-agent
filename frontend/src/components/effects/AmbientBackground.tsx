import React, { useEffect, useState } from 'react';
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion';

export const AmbientBackground: React.FC = () => {
  const shouldReduceMotion = useReducedMotion();
  const { scrollY } = useScroll();

  // Gentle scroll parallax offsets
  const y1 = useTransform(scrollY, [0, 2000], [0, 220]);
  const y2 = useTransform(scrollY, [0, 2000], [0, -180]);
  const y3 = useTransform(scrollY, [0, 2000], [0, 140]);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Dynamic Grid Overlay */}
      <div className="absolute inset-0 bg-grid-pattern opacity-60" />

      {/* Ambient Orb 1: Neon Cyan glow upper left */}
      <motion.div
        style={shouldReduceMotion ? {} : { y: y1 }}
        className="absolute -top-32 -left-32 w-[550px] h-[550px] rounded-full bg-gradient-to-tr from-cyan-500/12 to-sky-400/5 blur-[120px]"
      />

      {/* Ambient Orb 2: Electric Violet glow middle right */}
      <motion.div
        style={shouldReduceMotion ? {} : { y: y2 }}
        className="absolute top-1/3 -right-32 w-[600px] h-[600px] rounded-full bg-gradient-to-bl from-violet-600/12 to-indigo-500/5 blur-[140px]"
      />

      {/* Ambient Orb 3: Soft Mint / Emerald glow lower center */}
      <motion.div
        style={shouldReduceMotion ? {} : { y: y3 }}
        className="absolute bottom-10 left-1/3 w-[450px] h-[450px] rounded-full bg-gradient-to-r from-emerald-500/8 to-cyan-500/8 blur-[130px]"
      />

      {/* Animated Subtle Ambient Beam */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[1px] bg-gradient-to-r from-transparent via-cyan-400/25 to-transparent animate-pulse-slow" />
    </div>
  );
};
