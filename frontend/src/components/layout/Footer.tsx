import React from 'react';
import { ShieldCheck, Info, Sparkles } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-20 border-t border-slate-800/80 bg-[#f4f3ee]/90 py-10 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Responsible AI Disclaimer Banner */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 mt-0.5">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                Responsible AI & Human-in-the-Loop Standard
                <span className="text-[10px] font-mono bg-cyan-500/10 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/20">
                  Ethical Evaluation
                </span>
              </h4>
              <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
                Adaptive Interview Intelligence operates strictly as an <strong>evidence synthesis assistant</strong>. The system does not make unilateral hiring, rejection, or cheating determinations. All competency signals, confidence bounds, and integrity observations are transparently attributed to verifiable audio/transcript excerpts to support human recruiter decisions.
              </p>
            </div>
          </div>
          <div className="text-right whitespace-nowrap text-xs font-mono text-slate-500 hidden md:block">
            Built for Google Student Club<br />Welcome Hackathon 2026
          </div>
        </div>

        {/* Bottom Credits */}
        <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 pt-4 border-t border-slate-800/50 gap-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-semibold text-slate-300">Adaptive Interview Intelligence</span>
            <span>— Frontend Platform</span>
          </div>
          <div className="flex items-center gap-6 font-mono text-[11px]">
            <span>React + TypeScript</span>
            <span>Tailwind CSS</span>
            <span>3D Tilt & Parallax</span>
            <span>Framer Motion</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
