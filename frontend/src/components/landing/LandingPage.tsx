import React, { useEffect, useId, useRef } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  BarChart3,
  Check,
  ClipboardCheck,
  FileSearch,
  FileText,
  ListChecks,
  MessageSquareText,
  Mic2,
  Sparkles,
  Upload,
} from 'lucide-react';
import IntelligenceVisual from './IntelligenceVisual';
import './landing.css';

interface LandingPageProps {
  onStartInterview: () => void;
}

const features = [
  {
    title: 'Resume Intelligence',
    description: 'Understand candidate skills, projects, and experience.',
    icon: FileSearch,
    accent: 'blue',
    number: '01',
  },
  {
    title: 'Dynamic Question Generation',
    description: 'Generate relevant and varied interview questions.',
    icon: MessageSquareText,
    accent: 'violet',
    number: '02',
  },
  {
    title: 'Voice-First Interviews',
    description: 'Practice using spoken answers and AI-powered speech interaction.',
    icon: AudioLines,
    accent: 'mint',
    number: '03',
  },
  {
    title: 'Performance Insights',
    description: 'Review answer evaluations and feedback.',
    icon: BarChart3,
    accent: 'cyan',
    number: '04',
  },
];

const steps = [
  {
    title: 'Upload Your Resume',
    description: 'Add your resume so practice starts with your skills, projects, and experience.',
    icon: Upload,
    accent: 'blue',
  },
  {
    title: 'Generate Personalized Questions',
    description: 'Explore relevant questions shaped around your background and goals.',
    icon: ListChecks,
    accent: 'violet',
  },
  {
    title: 'Practice Through Voice or Code',
    description: 'Respond naturally by voice or work through role-relevant coding prompts.',
    icon: Mic2,
    accent: 'mint',
  },
  {
    title: 'Review Your Results',
    description: 'Reflect on answer evaluations and use feedback to guide your next practice session.',
    icon: ClipboardCheck,
    accent: 'cyan',
  },
];

function LogoMark() {
  const gradientId = `logo-${useId().replace(/:/g, '')}`;

  return (
    <svg className="logo-mark" viewBox="0 0 48 48" aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="7" y1="5" x2="41" y2="43" gradientUnits="userSpaceOnUse">
          <stop stopColor="#58b7ef" />
          <stop offset=".52" stopColor="#6688e8" />
          <stop offset="1" stopColor="#9a7bd4" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="44" height="44" rx="15" fill={`url(#${gradientId})`} />
      <circle cx="24" cy="24" r="8.5" fill="none" stroke="white" strokeWidth="1.7" opacity=".9" />
      <ellipse
        cx="24"
        cy="24"
        rx="16"
        ry="6"
        fill="none"
        stroke="white"
        strokeWidth="1.5"
        transform="rotate(-35 24 24)"
        opacity=".8"
      />
      <circle cx="35.5" cy="14.5" r="2.5" fill="#d4fff0" />
    </svg>
  );
}

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="Adaptive Interview Intelligence, back to top">
      <LogoMark />
      <span className="brand-copy">
        <strong>Adaptive</strong>
        <span>Interview Intelligence</span>
      </span>
    </a>
  );
}

function SectionLabel({ children, centered = false }: { children: React.ReactNode; centered?: boolean }) {
  return (
    <div className={`section-label${centered ? ' section-label-centered' : ''}`}>
      <span className="label-spark" aria-hidden="true">
        <Sparkles size={13} strokeWidth={1.8} />
      </span>
      <span>{children}</span>
    </div>
  );
}

function FeatureCard({ feature, index }: { feature: typeof features[0]; index: number }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const Icon = feature.icon;

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const card = cardRef.current;
    if (!card) return;
    const bounds = card.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width;
    const y = (event.clientY - bounds.top) / bounds.height;

    card.style.setProperty('--rotate-x', `${(0.5 - y) * 5}deg`);
    card.style.setProperty('--rotate-y', `${(x - 0.5) * 5}deg`);
    card.style.setProperty('--pointer-x', `${x * 100}%`);
    card.style.setProperty('--pointer-y', `${y * 100}%`);
  };

  const resetTilt = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.setProperty('--rotate-x', '0deg');
    card.style.setProperty('--rotate-y', '0deg');
    card.style.setProperty('--pointer-x', '50%');
    card.style.setProperty('--pointer-y', '50%');
  };

  return (
    <div className="feature-card-reveal" data-reveal style={{ '--delay': `${index * 80}ms` } as React.CSSProperties}>
      <article
        ref={cardRef}
        className={`feature-card feature-${feature.accent}`}
        onPointerMove={handlePointerMove}
        onPointerLeave={resetTilt}
      >
        <span className="feature-number" aria-hidden="true">{feature.number}</span>
        <div className="feature-icon" aria-hidden="true">
          <Icon size={24} strokeWidth={1.7} />
        </div>
        <h3>{feature.title}</h3>
        <p>{feature.description}</p>
        <span className="feature-accent-line" aria-hidden="true" />
      </article>
    </div>
  );
}

export default function LandingPage({ onStartInterview }: LandingPageProps) {
  useEffect(() => {
    const revealItems = document.querySelectorAll('[data-reveal]');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reducedMotion || !('IntersectionObserver' in window)) {
      revealItems.forEach((item) => item.classList.add('is-visible'));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -48px' },
    );

    revealItems.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing-page-root">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <div className="nav-container">
          <Brand />
          <nav className="desktop-nav" aria-label="Primary navigation">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
          </nav>
          <button
            className="button button-header"
            onClick={onStartInterview}
            type="button"
          >
            Start practicing
            <ArrowUpRight size={16} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
      </header>

      <main id="main-content">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-ambient hero-ambient-one" aria-hidden="true" />
          <div className="hero-ambient hero-ambient-two" aria-hidden="true" />
          <div className="hero-container">
            <div className="hero-copy">
              <div className="hero-eyebrow" data-hero style={{ '--hero-delay': '80ms' } as React.CSSProperties}>
                <span className="eyebrow-dot" aria-hidden="true" />
                AI-POWERED INTERVIEW PLATFORM
              </div>
              <h1 id="hero-title" data-hero style={{ '--hero-delay': '160ms' } as React.CSSProperties}>
                Your Skills.<br />
                Your Story.<br />
                <span className="gradient-text">Your Next Opportunity.</span>
              </h1>
              <p className="hero-description" data-hero style={{ '--hero-delay': '240ms' } as React.CSSProperties}>
                Prepare smarter with AI-powered mock interviews personalized to your resume. Practice naturally,
                explore your strengths, and improve with every answer.
              </p>
              <div className="hero-actions" data-hero style={{ '--hero-delay': '320ms' } as React.CSSProperties}>
                <button
                  id="start-your-interview-btn"
                  className="button button-primary"
                  onClick={onStartInterview}
                  type="button"
                >
                  Start Your Interview
                  <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
                </button>
                <a className="button button-secondary" href="#features">
                  Explore Features
                  <ArrowUpRight size={17} strokeWidth={1.8} aria-hidden="true" />
                </a>
              </div>
              <ul className="hero-highlights" data-hero style={{ '--hero-delay': '400ms' } as React.CSSProperties} aria-label="Platform highlights">
                <li><Check size={14} strokeWidth={2.4} aria-hidden="true" />Resume-aware</li>
                <li><Check size={14} strokeWidth={2.4} aria-hidden="true" />Voice-first</li>
                <li><Check size={14} strokeWidth={2.4} aria-hidden="true" />Actionable feedback</li>
              </ul>
            </div>
            <div className="hero-visual" data-hero style={{ '--hero-delay': '220ms' } as React.CSSProperties}>
              <IntelligenceVisual />
            </div>
          </div>
        </section>

        <section className="section features-section" id="features" aria-labelledby="features-title">
          <div className="section-container">
            <div className="section-heading" data-reveal>
              <div>
                <SectionLabel>INTELLIGENCE AT EVERY STEP</SectionLabel>
                <h2 id="features-title">Practice that begins with <span className="soft-gradient-text">you.</span></h2>
              </div>
              <p>
                From your resume to your reflections, every part of the experience is designed to keep practice
                personal, natural, and focused.
              </p>
            </div>
            <div className="features-grid">
              {features.map((feature, index) => (
                <FeatureCard key={feature.title} feature={feature} index={index} />
              ))}
            </div>
          </div>
        </section>

        <section className="section how-section" id="how-it-works" aria-labelledby="how-title">
          <div className="how-orb how-orb-one" aria-hidden="true" />
          <div className="how-orb how-orb-two" aria-hidden="true" />
          <div className="section-container how-container">
            <div className="centered-heading" data-reveal>
              <SectionLabel centered>A SIMPLE, FOCUSED FLOW</SectionLabel>
              <h2 id="how-title">From resume to reflection.</h2>
              <p>Four clear steps to turn your experience into more thoughtful interview practice.</p>
            </div>
            <div className="steps-grid">
              <div className="steps-line" aria-hidden="true"><span /></div>
              {steps.map((step, index) => {
                const Icon = step.icon;
                return (
                  <article
                    className={`step-card step-${step.accent}`}
                    key={step.title}
                    data-reveal
                    style={{ '--delay': `${index * 100}ms` } as React.CSSProperties}
                  >
                    <div className="step-number-wrap">
                      <span className="step-number">{index + 1}</span>
                      <span className="step-number-ring" aria-hidden="true" />
                    </div>
                    <div className="step-title-row">
                      <span className="step-icon" aria-hidden="true"><Icon size={17} strokeWidth={1.8} /></span>
                      <h3>{step.title}</h3>
                    </div>
                    <p>{step.description}</p>
                  </article>
                );
              })}
            </div>
            <div className="how-note" data-reveal>
              <span className="note-icon" aria-hidden="true"><FileText size={17} strokeWidth={1.8} /></span>
              <span>One resume. A practice path shaped around you.</span>
            </div>
          </div>
        </section>

        <section className="cta-section" id="get-started" aria-labelledby="cta-title">
          <div className="cta-card" data-reveal>
            <div className="cta-grid" aria-hidden="true" />
            <div className="cta-glow cta-glow-one" aria-hidden="true" />
            <div className="cta-glow cta-glow-two" aria-hidden="true" />
            <div className="cta-orbit cta-orbit-one" aria-hidden="true" />
            <div className="cta-orbit cta-orbit-two" aria-hidden="true" />
            <div className="cta-content">
              <span className="cta-icon" aria-hidden="true"><Sparkles size={22} strokeWidth={1.6} /></span>
              <h2 id="cta-title">Your Next Interview Starts Here.</h2>
              <p>Turn your preparation into confidence.</p>
              <button
                className="button button-primary cta-button"
                onClick={onStartInterview}
                type="button"
              >
                Get Started
                <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-container">
          <Brand />
          <p>Thoughtful preparation. Clearer confidence.</p>
          <nav aria-label="Footer navigation">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#top">Back to top <ArrowUpRight size={13} aria-hidden="true" /></a>
          </nav>
        </div>
        <div className="footer-bottom">
          <span>&copy; {new Date().getFullYear()} Adaptive Interview Intelligence</span>
          <span>Personalized practice, designed around your story.</span>
        </div>
      </footer>
    </div>
  );
}
