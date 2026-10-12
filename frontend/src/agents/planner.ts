import { 
  CandidateSetupInput, 
  InterviewPlan, 
  Competency, 
  EvaluationRubric, 
  InterviewQuestion,
  QuestionDifficulty
} from '../types';
import { apiRequest, isBackendConfigured } from '../api/apiClient';

/**
 * Agent 1: Interview Planner Agent
 * 
 * Analyzes candidate's resume, job description, interview settings, competencies,
 * skill gaps, and evaluation rubrics.
 */
export class InterviewPlannerAgent {
  /**
   * Generates a comprehensive interview plan from setup input.
   * If a backend is configured, calls the FastAPI service;
   * otherwise, executes the deterministic client-side planner algorithm (labelled DEMO).
   */
  static async generatePlan(input: CandidateSetupInput): Promise<{
    plan: InterviewPlan;
    source: 'backend' | 'demo';
  }> {
    if (isBackendConfigured()) {
      try {
        const remotePlan = await apiRequest<InterviewPlan>('/api/v1/planner/generate-plan', {
          method: 'POST',
          body: JSON.stringify(input),
        });
        if (remotePlan) {
          return { plan: remotePlan, source: 'backend' };
        }
      } catch (err) {
        console.warn('FastAPI planner failed, falling back to local planner agent:', err);
      }
    }

    // Client-side Planner Agent (Isolated deterministic DEMO implementation)
    const plan = this.generateLocalPlan(input);
    return { plan, source: 'demo' };
  }

  /**
   * Deterministic local analysis of resume and job description.
   */
  static generateLocalPlan(input: CandidateSetupInput): InterviewPlan {
    const resumeText = (input.resumeText || '').toLowerCase();
    const jdText = (input.jobDescription || '').toLowerCase();

    // Standard competency library for interview triangulation
    const potentialCompetencies = [
      {
        id: 'comp-react-arch',
        name: 'React Architecture & State Reconciliation',
        category: 'technical' as const,
        description: 'Deep understanding of React concurrent rendering, hooks lifecycle, memoization, and reconciliation trees.',
        keywords: ['react', 'fiber', 'hooks', 'virtual dom', 'redux', 'zustand', 'state management', 'context'],
      },
      {
        id: 'comp-ts-types',
        name: 'TypeScript Advanced Type Safety',
        category: 'technical' as const,
        description: 'Ability to architect strict typings, generics, conditional types, and discriminated unions.',
        keywords: ['typescript', 'generics', 'types', 'interfaces', 'union', 'type safety'],
      },
      {
        id: 'comp-web-perf',
        name: 'Client Performance & Web Vitals',
        category: 'technical' as const,
        description: 'Optimizing INP, LCP, CLS, bundle chunking, memory leak triage, and browser repaint lifecycles.',
        keywords: ['performance', 'web vitals', 'inp', 'lcp', 'lighthouse', 'optimization', 'profiling', 'lazy loading'],
      },
      {
        id: 'comp-a11y-wcag',
        name: 'Web Accessibility & WCAG 2.1 AA',
        category: 'role_specific' as const,
        description: 'Implementation of ARIA attributes, keyboard navigation traps, semantic DOM structure, and screen reader UX.',
        keywords: ['accessibility', 'a11y', 'wcag', 'aria', 'screen reader', 'keyboard navigation'],
      },
      {
        id: 'comp-system-design',
        name: 'Frontend Distributed Architecture',
        category: 'technical' as const,
        description: 'Micro-frontends, caching strategies, real-time WebSockets/WebRTC, and resilient offline capabilities.',
        keywords: ['architecture', 'micro-frontends', 'webrtc', 'websockets', 'system design', 'caching', 'service worker'],
      },
      {
        id: 'comp-incident-comms',
        name: 'Technical Communication & Incident Escalation',
        category: 'communication' as const,
        description: 'Synthesizing complex technical trade-offs to cross-functional stakeholders and post-mortem triage.',
        keywords: ['communication', 'mentorship', 'stakeholders', 'post-mortem', 'leadership', 'team'],
      },
    ];

    // Detect claims in resume
    const detectedClaims: string[] = [];
    potentialCompetencies.forEach(comp => {
      const match = comp.keywords.some(kw => resumeText.includes(kw));
      if (match) {
        detectedClaims.push(comp.name);
      }
    });

    // Detect requirements in JD
    const jdRequirements: string[] = [];
    potentialCompetencies.forEach(comp => {
      const match = comp.keywords.some(kw => jdText.includes(kw));
      if (match || jdText.length < 50) {
        jdRequirements.push(comp.name);
      }
    });

    // Detect pre-interview skill gaps (Required in JD but absent or unverified in resume)
    const preInterviewGaps: string[] = [];
    potentialCompetencies.forEach(comp => {
      const isRequired = jdRequirements.includes(comp.name);
      const isClaimed = detectedClaims.includes(comp.name);
      if (isRequired && !isClaimed) {
        preInterviewGaps.push(comp.name);
      }
    });

    // If candidate claims all or resume was short, designate at least one specialized gap for exploration
    if (preInterviewGaps.length === 0) {
      preInterviewGaps.push('Client Performance & Web Vitals');
    }

    // Build competencies list
    const competencies: Competency[] = potentialCompetencies.map(comp => {
      const isClaimed = detectedClaims.includes(comp.name);
      const isGap = preInterviewGaps.includes(comp.name);

      return {
        id: comp.id,
        name: comp.name,
        category: comp.category,
        description: comp.description,
        score: null,
        confidence: null,
        evidenceCount: 0,
        classification: isGap 
          ? 'not_assessed' 
          : isClaimed 
            ? 'claimed_needs_validation' 
            : 'not_assessed',
      };
    });

    // Build Evaluation Rubric
    const rubric: EvaluationRubric = {
      id: `rubric-${Date.now()}`,
      roleId: `role-${Date.now()}`,
      criteria: [
        {
          id: 'crit-react-core',
          competencyId: 'comp-react-arch',
          name: 'React Lifecycle & Concurrent Rendering',
          description: 'Depth of knowledge regarding React 18/19 concurrent rendering, batching, and suspense boundaries.',
          weight: 0.25,
          indicators: {
            inadequate: 'Confuses hooks execution timing; fails to explain reconciliation or renders loops.',
            proficient: 'Accurately describes fibers, concurrent transitions, memoization boundaries, and hook rules.',
            exceptional: 'Articulates internal scheduler priority queues, lane models, and custom hook abstraction ergonomics.',
          },
        },
        {
          id: 'crit-ts-safety',
          competencyId: 'comp-ts-types',
          name: 'Strict Type System Design',
          description: 'Leveraging TypeScript to eliminate runtime bugs through compile-time guarantees.',
          weight: 0.20,
          indicators: {
            inadequate: 'Over-relies on `any`, fails to grasp generic bounds or type narrowing.',
            proficient: 'Applies generics, utility types, discriminating unions, and unknown narrowing cleanly.',
            exceptional: 'Architects template literal types, distributive conditional types, and branded runtime validators.',
          },
        },
        {
          id: 'crit-perf-vitals',
          competencyId: 'comp-web-perf',
          name: 'Core Web Vitals & Runtime Profiling',
          description: 'Diagnosing and resolving frame drops, high INP latencies, and bloated bundle execution.',
          weight: 0.20,
          indicators: {
            inadequate: 'Cannot explain INP or causes of main thread blocking.',
            proficient: 'Identifies long tasks, applies code splitting, yields to main thread, and monitors CWV.',
            exceptional: 'Demonstrates Chrome DevTools Performance CPU flamegraph profiling, memory allocation instrumentation, and Worker thread offloading.',
          },
        },
        {
          id: 'crit-a11y-standards',
          competencyId: 'comp-a11y-wcag',
          name: 'Accessibility & Keyboard Traps',
          description: 'Designing inclusive user interfaces adhering to WCAG 2.1 AA specifications.',
          weight: 0.15,
          indicators: {
            inadequate: 'Treats accessibility as an afterthought; ignores semantic HTML and keyboard tab stops.',
            proficient: 'Implements focus containment, aria-live announcements, and semantic dialog roles.',
            exceptional: 'Performs manual screen reader audits, handles complex roving tabindexes, and designs robust high-contrast states.',
          },
        },
        {
          id: 'crit-comms-escalation',
          competencyId: 'comp-incident-comms',
          name: 'Engineering Articulation & Trade-offs',
          description: 'Clarity of thought, structural communication, and reasoning under technical constraints.',
          weight: 0.20,
          indicators: {
            inadequate: 'Rambles without answering the core prompt; does not acknowledge trade-offs.',
            proficient: 'Answers structured with context, action, result, and explicit architectural trade-offs.',
            exceptional: 'Mentors the interviewer through multi-variable engineering trade-offs with calm precision.',
          },
        },
      ],
    };

    // Build initial planned questions
    const initialQuestions: InterviewQuestion[] = [
      {
        id: 'q-101',
        order: 1,
        text: 'How do you design a high-frequency live telemetry dashboard in React without causing main thread jank or frame drops during rapid state updates?',
        category: 'technical',
        targetCompetencies: ['comp-react-arch', 'comp-web-perf'],
        difficulty: (input.experienceLevel.includes('Senior') || input.experienceLevel.includes('Staff')) 
          ? 'advanced' 
          : 'intermediate',
        whyThisQuestion: {
          contextAnalysis: 'Validates candidate ability to isolate frequent re-renders and preserve responsive 60fps UI.',
          gapDetected: preInterviewGaps.includes('Client Performance & Web Vitals') 
            ? 'Candidate resume omitted specific Web Vitals or rendering budget benchmarks.'
            : 'Establishes baseline architectural depth.',
          difficultyReason: 'Calibrated to verify Senior/L5 architectural maturity on modern concurrent React.',
          timeBalanceReason: 'Foundational starter question allocating 5-7 minutes for deep explanation.',
        },
      },
      {
        id: 'q-102',
        order: 2,
        text: 'Walk me through how you implement strict TypeScript typings for polymorphic component props and dynamic API payloads without resorting to type assertions or "any".',
        category: 'technical',
        targetCompetencies: ['comp-ts-types'],
        difficulty: 'intermediate',
        whyThisQuestion: {
          contextAnalysis: 'Evaluates if type safety is treated as a first-class architectural boundary.',
          gapDetected: 'Verifies whether candidate claims in resume reflect practical generic programming expertise.',
          difficultyReason: 'Intermediate question assessing real-world TypeScript ergonomic patterns.',
          timeBalanceReason: 'Targeted technical verification intended for 4-5 minutes.',
        },
      },
      {
        id: 'q-103',
        order: 3,
        text: 'When building a complex modal dialog with nested interactive widgets, how do you ensure bulletproof keyboard focus trapping and ARIA compliance according to WCAG 2.1 AA?',
        category: 'role_specific',
        targetCompetencies: ['comp-a11y-wcag'],
        difficulty: 'intermediate',
        whyThisQuestion: {
          contextAnalysis: 'Tests attention to accessibility and inclusive UX engineering.',
          gapDetected: preInterviewGaps.includes('Web Accessibility & WCAG 2.1 AA')
            ? 'Critical accessibility requirement in JD with no verifiable claims in submitted resume.'
            : 'Standard compliance requirement for production enterprise interfaces.',
          difficultyReason: 'Focus trapping and aria-hidden management expose practical frontend depth.',
          timeBalanceReason: 'Allocates 4 minutes.',
        },
      },
    ];

    return {
      id: `plan-${Date.now()}`,
      candidateId: `cand-${Date.now()}`,
      roleId: `role-${Date.now()}`,
      roleTitle: input.roleTitle,
      department: input.department,
      seniority: input.experienceLevel,
      targetDurationMinutes: input.sessionDurationMinutes,
      competencies,
      rubric,
      initialQuestions,
      preInterviewSkillGaps: preInterviewGaps,
      resumeClaims: detectedClaims,
      createdAt: new Date().toISOString(),
    };
  }
}
