import React, { useState, useEffect } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InteractiveTiltCard } from '../common/InteractiveTiltCard';
import { CursorGlowCard } from '../common/CursorGlowCard';
import { MagneticButton } from '../common/MagneticButton';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { Modal } from '../common/Modal';
import { useMicRecorder } from '../../hooks/useMicRecorder';
import { TTSService } from '../../services/tts';
import { STTService } from '../../services/stt';
import { 
  Video, 
  Mic, 
  MicOff,
  Pause, 
  Play, 
  RotateCcw, 
  Square,
  Volume2, 
  VolumeX,
  Flag, 
  Sparkles, 
  Clock, 
  Activity, 
  Quote, 
  TrendingUp, 
  Radio, 
  FileCheck2,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  RefreshCw,
  Send
} from 'lucide-react';

export const LiveInterviewScreen: React.FC = () => {
  const {
    isInterviewActive,
    isPaused,
    isEvaluating,
    timeRemainingSeconds,
    sessionDurationMinutes,
    currentQuestion,
    evidenceList,
    competencies,
    agentLogs,
    lastEvaluation,
    pauseResumeInterview,
    retryCurrentQuestion,
    endInterview,
    submitAnswer,
    flagObservation,
    setActiveTab,
    isBackendConnected,
    isDemoMode,
    selectedCandidate,
    activeRole
  } = useInterview();

  // Microphone Hook
  const {
    status: micStatus,
    isRecording,
    audioLevel,
    frequencyData,
    durationSeconds: micDuration,
    errorMessage: micError,
    startRecording,
    stopRecording,
    resetRecording
  } = useMicRecorder();

  // Speech & Transcript State
  const [transcriptText, setTranscriptText] = useState<string>('');
  const [isSpeakingTTS, setIsSpeakingTTS] = useState<boolean>(false);
  const [showQuestionRationale, setShowQuestionRationale] = useState<boolean>(true);
  const [flagModalOpen, setFlagModalOpen] = useState(false);
  const [flagNote, setFlagNote] = useState('');

  // Handle Pause/Resume: cancel ongoing audio speech if paused
  useEffect(() => {
    if (isPaused) {
      if (TTSService.isSpeaking()) {
        TTSService.pause();
      }
      if (isRecording) {
        stopRecording();
        STTService.stop();
      }
    } else {
      if (TTSService.isSpeaking()) {
        TTSService.resume();
      }
    }
  }, [isPaused, isRecording, stopRecording]);

  // Clean up speech on unmount
  useEffect(() => {
    return () => {
      TTSService.cancel();
      STTService.stop();
    };
  }, []);

  const formatTimer = (sec: number | null) => {
    if (sec === null) return '--:--';
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // TTS Handler: Read question aloud
  const handleToggleTTS = () => {
    if (!currentQuestion) return;

    if (isSpeakingTTS || TTSService.isSpeaking()) {
      TTSService.cancel();
      setIsSpeakingTTS(false);
    } else {
      setIsSpeakingTTS(true);
      TTSService.speak(currentQuestion.text, {
        onStart: () => setIsSpeakingTTS(true),
        onEnd: () => setIsSpeakingTTS(false),
        onError: () => setIsSpeakingTTS(false),
      });
    }
  };

  // User-Initiated Microphone Recording & Live STT
  const handleToggleRecording = async () => {
    if (isRecording) {
      // Stop recording
      await stopRecording();
      STTService.stop();
    } else {
      // User explicitly starts microphone
      setTranscriptText('');
      const started = await startRecording();
      if (started) {
        STTService.start({
          onTranscriptUpdate: (state) => {
            setTranscriptText(state.fullText);
          },
          onError: (err) => {
            console.warn('STT Error:', err);
          },
        });
      }
    }
  };

  // Submit Answer to AI Agent Evaluation Pipeline
  const handleSubmitAnswer = async () => {
    if (!transcriptText.trim()) return;

    if (isRecording) {
      await stopRecording();
      STTService.stop();
    }

    await submitAnswer(transcriptText, micDuration);
    setTranscriptText('');
    resetRecording();
  };

  // Retry Current Question
  const handleRetry = () => {
    if (isRecording) {
      stopRecording();
      STTService.stop();
    }
    TTSService.cancel();
    setIsSpeakingTTS(false);
    setTranscriptText('');
    resetRecording();
    retryCurrentQuestion();
  };

  const handleFlagSubmit = () => {
    flagObservation(flagNote || undefined);
    setFlagNote('');
    setFlagModalOpen(false);
  };

  // Demo sample answer helpers for rapid testing
  const loadExemplaryAnswer = () => {
    setTranscriptText(
      'To prevent main thread jank during rapid state updates, I isolate high-frequency telemetry state using fine-grained subscriptions with Zustand or Jotai outside the React component tree. For heavy rendering surfaces, I use React Concurrent transitions via startTransition to yield execution priority to user interactions, ensuring our INP remains under 50ms. Additionally, I employ virtualized lists using react-window to constrain DOM node count, and wrap expensive mathematical derivations in useMemo and web workers so the browser compositor thread never drops below 60fps.'
    );
  };

  const loadIncompleteAnswer = () => {
    setTranscriptText(
      'I usually just use standard React useState and useEffect to update the data. If it runs slow, I might try to add some memo or useCallback hooks here and there to see if performance gets better.'
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Top Session Telemetry HUD */}
      <div className="rounded-2xl bg-white/90 backdrop-blur-xl border border-cyan-500/20 p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        {/* Left: Stream Status & Candidate */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-cyan-400">
            <Radio className={`w-5 h-5 text-cyan-400 ${isInterviewActive && !isPaused ? 'animate-pulse' : ''}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-slate-100">Live Adaptive Cockpit</span>
              <StatusBadge 
                variant={isInterviewActive ? (isPaused ? 'amber' : 'live') : 'slate'} 
                size="sm" 
                dotPulse={isInterviewActive && !isPaused}
              >
                {isInterviewActive ? (isPaused ? 'Session Paused' : 'Session Active') : 'Standby / Ready'}
              </StatusBadge>
              {isDemoMode && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/25">
                  DEMO ENGINE
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400">
              Candidate: <strong className="text-slate-200">{selectedCandidate?.name || 'Alex Chen'}</strong> ({activeRole?.title || 'Senior Frontend Engineer'})
            </div>
          </div>
        </div>

        {/* Center: Live Timers & Metric Badges */}
        <div className="flex items-center gap-4 sm:gap-6 font-mono text-xs">
          <div className="flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400">Remaining:</span>
            <span className={`font-bold text-sm tracking-wider ${timeRemainingSeconds !== null && timeRemainingSeconds < 300 ? 'text-rose-400 animate-pulse' : 'text-slate-100'}`}>
              {formatTimer(timeRemainingSeconds)}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800">
            <Activity className="w-4 h-4 text-violet-400" />
            <span className="text-slate-400">Coverage:</span>
            <span className="font-bold text-violet-300 text-sm">
              {competencies.length > 0
                ? `${Math.round((competencies.filter(c => c.score !== null).length / competencies.length) * 100)}%`
                : '--%'}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-400">Evidence Quotes:</span>
            <span className="font-bold text-emerald-300 text-sm">{evidenceList.length}</span>
          </div>
        </div>

        {/* Right: Recruiter Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={pauseResumeInterview}
            disabled={!isInterviewActive}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? 'Resume' : 'Pause'}</span>
          </MagneticButton>

          <MagneticButton
            variant="secondary"
            size="sm"
            onClick={handleRetry}
            disabled={!isInterviewActive}
            title="Reset answer state for current question"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </MagneticButton>

          <MagneticButton
            variant="danger"
            size="sm"
            onClick={() => setFlagModalOpen(true)}
            disabled={!isInterviewActive}
          >
            <Flag className="w-3.5 h-3.5" />
            <span>Flag</span>
          </MagneticButton>

          <MagneticButton
            variant="primary"
            size="sm"
            onClick={endInterview}
          >
            <FileCheck2 className="w-3.5 h-3.5" />
            <span>End Session & Dossier</span>
          </MagneticButton>
        </div>
      </div>

      {/* Main Cockpit Grid: Video & Current Question (Left) vs Real-Time Evidence (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (7 cols): Stream Monitor, Question, Speech Input */}
        <div className="lg:col-span-7 space-y-6">
          {/* Candidate Stream Stage with Real Audio Waveform Analysis */}
          <InteractiveTiltCard glowColor="cyan" maxTilt={3} className="p-4">
            <div className="relative aspect-video rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between p-4 overflow-hidden shadow-inner">
              <div className="relative z-10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${isRecording ? 'bg-rose-500 animate-ping' : isInterviewActive ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                  <span className="text-[11px] font-mono text-slate-300 uppercase tracking-widest">
                    Candidate Media Stream
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400 text-xs font-mono">
                  <Video className="w-3.5 h-3.5 text-cyan-400" />
                  <span>WebRTC Audio/Video</span>
                </div>
              </div>

              {/* Center Stream Monitor */}
              <div className="relative z-10 flex flex-col items-center justify-center my-2 space-y-3">
                <div className="relative">
                  <div className={`w-20 h-20 rounded-2xl bg-slate-900 border-2 ${isRecording ? 'border-rose-500/80 shadow-[0_0_20px_rgba(244,63,94,0.4)]' : 'border-slate-800'} flex items-center justify-center text-slate-500 transition-all duration-300`}>
                    {isRecording ? (
                      <Mic className="w-8 h-8 text-rose-400 animate-pulse" />
                    ) : (
                      <Video className="w-8 h-8 text-slate-500" />
                    )}
                  </div>
                  {isRecording && (
                    <span className="absolute -top-1.5 -right-1.5 px-1.5 py-0.5 rounded-full bg-rose-600 text-white text-[9px] font-mono font-bold uppercase animate-pulse">
                      REC
                    </span>
                  )}
                </div>

                {/* Real Dynamic Audio Frequency Waveform Bars from Web Audio API AnalyserNode */}
                <div className="flex items-center gap-1.5 h-8 px-4 py-1 rounded-xl bg-slate-900/80 border border-slate-800/80">
                  {frequencyData.map((val, i) => (
                    <div
                      key={i}
                      className={`w-1.5 rounded-full transition-all duration-75 ${
                        isRecording 
                          ? val > 30 ? 'bg-gradient-to-t from-cyan-500 to-rose-400' : 'bg-cyan-400' 
                          : 'bg-slate-800'
                      }`}
                      style={{ height: `${Math.max(6, val * 0.28)}px` }}
                    />
                  ))}
                </div>

                <div className="text-[11px] font-mono text-slate-400 text-center">
                  {isRecording ? (
                    <span className="text-rose-300 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                      Capturing candidate audio ({micDuration}s) • Level: {audioLevel}%
                    </span>
                  ) : isInterviewActive ? (
                    'Microphone ready. Click "Record Answer" below to begin.'
                  ) : (
                    'Waiting for session start.'
                  )}
                </div>
              </div>

              {/* Feed Footer */}
              <div className="relative z-10 flex items-center justify-between text-[10px] font-mono text-slate-500 pt-2 border-t border-slate-900">
                <span>Microphone Status: <strong className="text-slate-400">{micStatus.toUpperCase()}</strong></span>
                <span>Audio Engine: Web Audio API AnalyserNode</span>
              </div>
            </div>

            {/* Mic Error Notice */}
            {micError && (
              <div className="mt-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{micError}</span>
              </div>
            )}
          </InteractiveTiltCard>

          {/* Current Adaptive Question Card */}
          {currentQuestion ? (
            <InteractiveTiltCard glowColor="violet" maxTilt={4} className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-violet-400" />
                  <h3 className="text-sm font-bold text-slate-100">
                    Adaptive Inquiry #{currentQuestion.order}
                  </h3>
                  <StatusBadge 
                    variant={currentQuestion.difficulty === 'advanced' ? 'rose' : currentQuestion.difficulty === 'intermediate' ? 'violet' : 'cyan'} 
                    size="sm"
                  >
                    {currentQuestion.difficulty.toUpperCase()}
                  </StatusBadge>
                </div>

                {/* TTS Speak Question Button */}
                <button
                  onClick={handleToggleTTS}
                  title="Read question aloud via Text-to-Speech"
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-mono border transition ${
                    isSpeakingTTS
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse'
                      : 'bg-slate-900 text-slate-300 border-slate-700 hover:text-cyan-300 hover:border-cyan-500/30'
                  }`}
                >
                  {isSpeakingTTS ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  <span>{isSpeakingTTS ? 'Stop Audio' : 'Speak Question (TTS)'}</span>
                </button>
              </div>

              {/* Question Text */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-violet-950/20 to-slate-900/80 border border-violet-500/20">
                <p className="text-sm sm:text-base font-semibold text-slate-100 leading-relaxed">
                  "{currentQuestion.text}"
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-400">
                  <span className="text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                    Category: {currentQuestion.category}
                  </span>
                  <span className="text-slate-400">Target Competencies: {currentQuestion.targetCompetencies.join(', ')}</span>
                </div>
              </div>

              {/* Explainability Accordion: Why This Question? */}
              {currentQuestion.whyThisQuestion && (
                <div className="rounded-xl bg-slate-900/60 border border-slate-800/80 overflow-hidden text-xs">
                  <button
                    onClick={() => setShowQuestionRationale(!showQuestionRationale)}
                    className="w-full p-2.5 flex items-center justify-between text-slate-300 font-mono text-[11px] hover:text-cyan-300"
                  >
                    <span className="flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                      Agent 2 Explainability: Why was this question generated?
                    </span>
                    {showQuestionRationale ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {showQuestionRationale && (
                    <div className="p-3 pt-0 border-t border-slate-800/50 space-y-2 text-[11px] text-slate-400">
                      <div>
                        <strong className="text-slate-300 font-mono">Context Analysis: </strong>
                        {currentQuestion.whyThisQuestion.contextAnalysis}
                      </div>
                      <div>
                        <strong className="text-amber-300 font-mono">Gap Detected: </strong>
                        {currentQuestion.whyThisQuestion.gapDetected}
                      </div>
                      <div>
                        <strong className="text-slate-300 font-mono">Difficulty Rationale: </strong>
                        {currentQuestion.whyThisQuestion.difficultyReason}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </InteractiveTiltCard>
          ) : (
            <EmptyState
              title="No active question"
              description="Launch the interview session to dispatch the initial question."
              icon={<Sparkles className="w-8 h-8 text-cyan-400" />}
              showFastApiBadge={false}
            />
          )}

          {/* Live Synchronized Candidate Transcript & Controls */}
          <CursorGlowCard className="p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Quote className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-slate-200">Candidate Response Speech Stream</h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={loadExemplaryAnswer}
                  className="text-[10px] font-mono text-cyan-400 hover:underline"
                  title="Load high-scoring sample answer to test evaluation"
                >
                  Load Strong Sample
                </button>
                <span className="text-slate-600">•</span>
                <button
                  onClick={loadIncompleteAnswer}
                  className="text-[10px] font-mono text-amber-400 hover:underline"
                  title="Load incomplete answer to test gap detection"
                >
                  Load Gap Sample
                </button>
              </div>
            </div>

            {/* Transcript Input / Display */}
            <div>
              <textarea
                rows={4}
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                placeholder="Click 'Record Answer' to speak into your microphone, or type/edit the candidate's transcript here..."
                className="w-full bg-slate-900/90 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 leading-relaxed font-sans"
              />
            </div>

            {/* Response Actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <button
                onClick={handleToggleRecording}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold transition shadow-lg ${
                  isRecording
                    ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-glow-rose animate-pulse'
                    : 'bg-slate-900 border border-slate-700 hover:border-cyan-400 text-slate-200 hover:text-cyan-300'
                }`}
              >
                {isRecording ? <Square className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5 text-cyan-400" />}
                <span>{isRecording ? 'Stop Recording' : 'Record Answer (Microphone)'}</span>
              </button>

              <MagneticButton
                variant="primary"
                size="sm"
                onClick={handleSubmitAnswer}
                disabled={!transcriptText.trim() || isEvaluating}
              >
                {isEvaluating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating against Rubrics...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit & Adapt Next Question</span>
                  </>
                )}
              </MagneticButton>
            </div>
          </CursorGlowCard>
        </div>

        {/* Right Column (5 cols): Real-Time Evidence & Competencies & Agent Activity */}
        <div className="lg:col-span-5 space-y-6">
          {/* Real-time Agent Activity Feed */}
          <CursorGlowCard className="p-4 space-y-2.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
              <div className="flex items-center gap-1.5 font-bold text-slate-200">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>5-Agent Orchestration HUD</span>
              </div>
              <span className="text-[10px] font-mono text-cyan-300">Live Telemetry</span>
            </div>

            <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
              {agentLogs.length > 0 ? (
                agentLogs.slice(0, 5).map((log) => (
                  <div key={log.id} className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-[10px] font-mono space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="text-cyan-400 font-bold uppercase">[{log.agent}] {log.action}</span>
                      <span className="text-slate-500">{log.timestamp}</span>
                    </div>
                    <p className="text-slate-300 text-[11px] font-sans truncate">{log.details}</p>
                  </div>
                ))
              ) : (
                <div className="text-[11px] text-slate-500 italic p-2 text-center">
                  Agent activity stream will populate as interview proceeds.
                </div>
              )}
            </div>
          </CursorGlowCard>

          {/* Extracted Evidence Feed */}
          <CursorGlowCard className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-100">Extracted Evidence Stream</h3>
              </div>
              <StatusBadge variant="cyan" size="sm">
                {evidenceList.length} Quotes Logged
              </StatusBadge>
            </div>

            {evidenceList.length > 0 ? (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {evidenceList.map((ev) => (
                  <div key={ev.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-500/30 transition text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-mono">
                      <span className="text-cyan-300 font-bold">T+{ev.timestamp}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-400 font-bold">+{ev.scoreImpact} Score</span>
                        <span className="text-violet-400">+{ev.confidenceImpact}% Conf</span>
                      </div>
                    </div>
                    <p className="text-slate-200 italic text-[11px] leading-relaxed bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                      {ev.quote}
                    </p>
                    <div className="text-[10px] text-slate-400">
                      Competency: <strong className="text-slate-300">{ev.competencyName}</strong>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No evidence collected yet"
                description="As the candidate answers, verbatim quotes, score impacts, and confidence bounds will be extracted and indexed automatically by Agent 3."
                showFastApiBadge={false}
                icon={<Quote className="w-6 h-6 text-cyan-400" />}
              />
            )}
          </CursorGlowCard>

          {/* Live Competency Ratings */}
          <CursorGlowCard className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100">Competency Signals</h3>
              <StatusBadge variant="violet" size="sm">Decoupled Confidence</StatusBadge>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {competencies.map((comp) => {
                const score = comp.score ?? 0;
                const hasScore = comp.score !== null;

                return (
                  <div key={comp.id} className="p-2.5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{comp.name}</span>
                      <div className="flex items-center gap-2 text-[10px] font-mono">
                        {hasScore ? (
                          <>
                            <span className="text-cyan-300 font-bold">{comp.score}/100</span>
                            <span className="text-violet-400">({comp.confidence}% Conf)</span>
                          </>
                        ) : (
                          <span className="text-slate-500 italic">Unassessed</span>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-400 to-violet-500 transition-all duration-500 rounded-full"
                        style={{ width: `${hasScore ? score : 0}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CursorGlowCard>
        </div>
      </div>

      {/* Flag Observation Modal */}
      <Modal
        isOpen={flagModalOpen}
        onClose={() => setFlagModalOpen(false)}
        title="Record Recruiter Telemetry Observation"
        subtitle="Neutral human-in-the-loop observation record"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            Log an objective observation regarding candidate audio clarity, technical pauses, or ambiguous answers for subsequent committee review.
          </p>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Observation Notes:</label>
            <textarea
              rows={3}
              value={flagNote}
              onChange={(e) => setFlagNote(e.target.value)}
              placeholder="e.g. Candidate experienced brief audio buffer delay while answering..."
              className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={() => setFlagModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <MagneticButton
              variant="danger"
              size="sm"
              onClick={handleFlagSubmit}
            >
              Save Observation Flag
            </MagneticButton>
          </div>
        </div>
      </Modal>
    </div>
  );
};
