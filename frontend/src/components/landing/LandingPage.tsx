import React, { useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useInterview, NavigationTab } from '../../context/InterviewContext';
import { OrbitScene, sceneState } from '../3d/OrbitScene';
import {
  Orbit, ArrowUpRight, ClipboardList, Radio, GitCompare, ShieldCheck, FileCheck2,
  Mic, Volume2, Brain, MessagesSquare, Eye, UserCheck, ChevronRight, Server,
} from 'lucide-react';

const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

const AGENTS = [
  { icon: ClipboardList, name: 'Planner', text: 'Reads the resume claims and job description, finds skill gaps, and builds a weighted rubric.' },
  { icon: MessagesSquare, name: 'Interviewer', text: 'Picks the next question from earlier answers: probes gaps or raises the difficulty.' },
  { icon: Brain, name: 'Evaluator', text: 'Scores answers against the rubric, quotes the transcript, and reports confidence separately.' },
  { icon: Eye, name: 'Integrity', text: 'Logs neutral telemetry (tab focus, pauses, audio shifts) for a recruiter to review. No accusations.' },
  { icon: FileCheck2, name: 'Decision', text: 'Writes an explainable dossier: verified strengths, open gaps, follow-up questions.' },
];

const STEPS: { n: string; title: string; text: string; tab: NavigationTab }[] = [
  { n: '01', title: 'Set up', text: 'Add the candidate resume and job requirements.', tab: 'setup' },
  { n: '02', title: 'Plan', text: 'The Planner extracts competencies and a rubric.', tab: 'setup' },
  { n: '03', title: 'Interview', text: 'Questions adapt live; answers are spoken and transcribed.', tab: 'live' },
  { n: '04', title: 'Review evidence', text: 'Every score links to a verbatim quote.', tab: 'evidence' },
  { n: '05', title: 'Check integrity', text: 'Context signals are listed for human review.', tab: 'integrity' },
  { n: '06', title: 'Decide', text: 'A recruiter reads the dossier and makes the call.', tab: 'report' },
];

const FEATURES = [
  { icon: Radio, title: 'Adaptive questioning', text: 'Follow-ups and difficulty change with each answer instead of following a fixed script.' },
  { icon: GitCompare, title: 'Evidence map', text: 'Resume claims versus what the interview actually validated, competency by competency.' },
  { icon: Mic, title: 'Voice answers', text: 'Speech-to-text capture with a live microphone level meter, started by the candidate.' },
  { icon: Volume2, title: 'Spoken questions', text: 'Browser text-to-speech with pause and resume. It never plays unless you press play.' },
  { icon: ShieldCheck, title: 'Integrity timeline', text: 'Neutral, non-accusatory observations with a review status for each event.' },
  { icon: UserCheck, title: 'Human in the loop', text: 'No automatic hiring or rejection. The system supplies evidence, people decide.' },
];

const Reveal: React.FC<{ children: React.ReactNode; delay?: number; className?: string }> = ({ children, delay = 0, className }) => {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }} transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}>
      {children}
    </motion.div>
  );
};

/** Pointer-driven 3D tilt with perspective. Disabled under reduced motion. */
const Tilt: React.FC<{ children: React.ReactNode; className?: string; max?: number }> = ({ children, className = '', max = 8 }) => {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const move = (e: React.PointerEvent) => {
    if (reduce || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    ref.current.style.transform = `perspective(900px) rotateX(${-y * max}deg) rotateY(${x * max}deg) translateZ(6px)`;
  };
  const leave = () => { if (ref.current) ref.current.style.transform = ''; };
  return (
    <div ref={ref} onPointerMove={move} onPointerLeave={leave} className={`transition-transform duration-200 ease-out will-change-transform ${className}`}>
      {children}
    </div>
  );
};

export const LandingPage: React.FC = () => {
  const { setActiveTab } = useInterview();
  const launch = () => setActiveTab('dashboard');
  const [active, setActive] = useState(-1);
  const focus = (i: number) => { sceneState.focus = i; setActive(i); };

  const links = [['Home', 'top'], ['Features', 'features'], ['How it works', 'how'], ['About', 'about']] as const;

  return (
    <div id="top" className="relative min-h-screen text-[#111210]">
      {/* One fixed WebGL stage behind the whole page; it moves to whichever section declares data-stage */}
      <OrbitScene />

      <header className="sticky top-0 z-40 bg-[#f4f3ee]/80 backdrop-blur border-b border-black/5">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
          <button onClick={() => scrollTo('top')} className="flex min-w-0 items-center gap-2.5" aria-label="Adaptive Interview Intelligence home">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#1b1c17]"><Orbit className="h-5 w-5 text-[#c6ee2e]" /></span>
            <span className="text-sm sm:text-base lg:text-lg font-bold tracking-tight leading-tight sm:whitespace-nowrap text-left">Adaptive Interview Intelligence</span>
          </button>
          <nav className="hidden lg:flex items-center gap-1 text-sm font-medium text-[#44443d]">
            {links.map(([l, id]) => (
              <button key={id} onClick={() => scrollTo(id)} className="px-3 py-2 rounded-full hover:bg-black/5 transition-colors">{l}</button>
            ))}
          </nav>
          <button onClick={launch} className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[#1b1c17] px-3 sm:px-4 py-2 text-xs sm:text-sm font-semibold text-white hover:bg-black transition-colors">
            Launch Application <ArrowUpRight className="h-4 w-4 text-[#c6ee2e]" />
          </button>
        </div>
      </header>

      <main className="relative z-10">
        {/* Hero: 3D system on the right */}
        <section data-stage="right" className="mx-auto max-w-7xl px-4 sm:px-6 pt-14 pb-24 min-h-[calc(100vh-4rem)] grid lg:grid-cols-2 gap-8 items-center">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/90 border border-black/5 px-3 py-1 text-xs font-medium text-[#44443d]">
              <span className="h-2 w-2 rounded-full bg-[#c6ee2e] ring-2 ring-[#8fb80f]/40" /> Adaptive Interview Intelligence
            </span>
            <h1 className="mt-5 text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.02]">
              Interviews that follow the <span className="bg-[#c6ee2e] px-2 rounded-xl">evidence</span>, not the script.
            </h1>
            <p className="mt-5 text-lg text-[#5e5d56] max-w-xl">
              Adaptive Interview Intelligence plans a rubric from the resume and job spec, adapts questions as the candidate answers,
              and hands the recruiter a dossier where every claim points to a quote.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button onClick={launch} className="inline-flex items-center gap-2 rounded-full bg-[#c6ee2e] px-6 py-3 font-semibold text-[#111210] hover:bg-[#d2f34f] transition-colors shadow-glow-cyan">
                Launch Application <ArrowUpRight className="h-4 w-4" />
              </button>
              <button onClick={() => scrollTo('features')} className="inline-flex items-center gap-2 rounded-full border border-black/15 bg-white/90 px-6 py-3 font-semibold hover:border-black/40 transition-colors">
                Explore Features <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </Reveal>
          <div className="relative flex lg:min-h-[520px] items-end justify-end">
            <Tilt className="w-full max-w-xs" max={12}>
              <div className="rounded-3xl bg-white/90 backdrop-blur border border-black/5 p-5 shadow-[0_30px_60px_-30px_rgba(17,18,16,0.55)]" aria-hidden="true">
                <div className="text-xs font-mono text-[#7d7c74]">Evaluator · Question 4</div>
                <p className="mt-2 text-sm font-medium leading-snug">“I'd shard by tenant ID and replay from the log.”</p>
                <div className="mt-4 flex items-center gap-3 text-xs text-[#5e5d56]">
                  <span className="w-16">Confidence</span>
                  <span className="flex-1 h-2.5 rounded-full bg-[#efeee8]"><span className="block h-2.5 w-4/5 rounded-full bg-[#c6ee2e]" /></span>
                </div>
                <p className="mt-3 text-[11px] text-[#7d7c74]">Illustrative example</p>
              </div>
            </Tilt>
          </div>
        </section>

        {/* Features */}
        <section id="features" data-stage="center" className="mx-auto max-w-7xl px-4 sm:px-6 py-16 scroll-mt-20">
          <Reveal><h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight max-w-2xl">What it does today</h2></Reveal>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={i * 0.04}>
                <Tilt className="h-full">
                  <div className="h-full rounded-3xl bg-white/95 border border-black/5 p-6 hover:border-black/20 transition-colors">
                    <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#c6ee2e]"><f.icon className="h-5 w-5 text-[#111210]" /></span>
                    <h3 className="mt-4 font-bold text-lg">{f.title}</h3>
                    <p className="mt-1.5 text-sm text-[#5e5d56] leading-relaxed">{f.text}</p>
                  </div>
                </Tilt>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Agents: stage on the left, list on the right. Hovering a row lights that agent in 3D. */}
        <section data-stage="left" className="mx-auto max-w-7xl px-4 sm:px-6 py-16 min-h-screen grid lg:grid-cols-2 gap-8 items-center">
          <div className="hidden lg:block self-end pb-4">
            <p className="text-sm text-[#5e5d56] max-w-xs">Point at an agent to find it in the orbit. Lime pulses are evidence flowing back to the candidate profile.</p>
          </div>
          <div className="rounded-[2rem] bg-[#1b1c17]/95 backdrop-blur text-white p-6 sm:p-8">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Five agents, one workflow</h2>
            <ul className="mt-6 space-y-2" onMouseLeave={() => focus(-1)}>
              {AGENTS.map((a, i) => (
                <li key={a.name} tabIndex={0} onMouseEnter={() => focus(i)} onFocus={() => focus(i)} onBlur={() => focus(-1)}
                  className={`flex gap-4 rounded-2xl border p-4 transition-colors outline-none ${active === i ? 'bg-[#c6ee2e] border-[#c6ee2e] text-[#111210]' : 'bg-white/5 border-white/10'}`}>
                  <a.icon className={`h-5 w-5 mt-0.5 shrink-0 ${active === i ? 'text-[#111210]' : 'text-[#c6ee2e]'}`} />
                  <div>
                    <h3 className="font-bold">{a.name}</h3>
                    <p className={`mt-0.5 text-sm leading-relaxed ${active === i ? 'text-[#111210]/75' : 'text-white/65'}`}>{a.text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* How it works */}
        <section id="how" data-stage="center" className="mx-auto max-w-7xl px-4 sm:px-6 py-16 scroll-mt-20">
          <Reveal><h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">How it works</h2></Reveal>
          <ol className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {STEPS.map((s, i) => (
              <li key={s.n}>
                <Reveal delay={i * 0.04} className="h-full">
                  <Tilt className="h-full">
                    <button onClick={() => setActiveTab(s.tab)} className="group h-full w-full text-left rounded-3xl bg-white/95 border border-black/5 p-6 hover:border-black/30 transition-colors">
                      <span className="text-4xl font-extrabold text-[#c9c8bf] group-hover:text-[#8fb80f] transition-colors">{s.n}</span>
                      <h3 className="mt-2 font-bold text-lg">{s.title}</h3>
                      <p className="mt-1 text-sm text-[#5e5d56]">{s.text}</p>
                    </button>
                  </Tilt>
                </Reveal>
              </li>
            ))}
          </ol>
        </section>

        {/* About: stage on the right */}
        <section id="about" data-stage="right" className="mx-auto max-w-7xl px-4 sm:px-6 py-16 min-h-[80vh] grid lg:grid-cols-2 gap-4 items-center scroll-mt-20">
          <div className="space-y-4">
            <div className="rounded-3xl bg-white/95 border border-black/5 p-8">
              <UserCheck className="h-6 w-6" />
              <h3 className="mt-3 text-xl font-bold">Responsible by design</h3>
              <p className="mt-2 text-sm text-[#5e5d56] leading-relaxed">
                Adaptive Interview Intelligence is an evidence assistant. It never decides to hire or reject, and it never calls anything cheating.
                Scores, confidence and integrity notes are tied to excerpts a human can check.
              </p>
            </div>
            <div className="rounded-3xl bg-white/95 border border-black/5 p-8">
              <Server className="h-6 w-6" />
              <h3 className="mt-3 text-xl font-bold">Demo mode or your own backend</h3>
              <p className="mt-2 text-sm text-[#5e5d56] leading-relaxed">
                With no server configured, the full agent pipeline runs in your browser in a labelled demo mode.
                Set a FastAPI URL to route the same requests to your backend.
              </p>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section data-stage="center" className="mx-auto max-w-7xl px-4 sm:px-6 py-16">
          <div className="rounded-[2rem] bg-[#c6ee2e] p-10 sm:p-14 text-center">
            <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#111210]">Run your first adaptive interview.</h2>
            <button onClick={launch} className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#1b1c17] px-7 py-3.5 font-semibold text-white hover:bg-black transition-colors">
              Launch Application <ArrowUpRight className="h-4 w-4 text-[#c6ee2e]" />
            </button>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-black/10 bg-[#f4f3ee] py-8 px-4 sm:px-6">
        <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#5e5d56]">
          <div className="flex items-center gap-2 font-semibold text-[#111210]"><Orbit className="h-4 w-4" /> Adaptive Interview Intelligence</div>
          <div className="flex gap-4">
            {links.map(([l, id]) => <button key={id} onClick={() => scrollTo(id)} className="hover:text-black">{l}</button>)}
          </div>
          <div>Google Student Club Welcome Hackathon 2026 · Problem Statement 3</div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
