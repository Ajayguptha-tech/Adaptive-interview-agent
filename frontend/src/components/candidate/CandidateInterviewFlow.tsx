import React, { useState, useRef, useEffect } from 'react';
import { useInterview } from '../../context/InterviewContext';
import { InterviewService } from '../../services/interviewService';
import { useMicRecorder } from '../../hooks/useMicRecorder';
import { STTService } from '../../services/stt';
import { TTSService } from '../../services/tts';
import { 
  FileText, 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Play, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  ArrowRight, 
  Download, 
  RotateCcw, 
  Award, 
  Sparkles, 
  Code2, 
  Briefcase, 
  Clock, 
  Check, 
  StopCircle,
  Send,
  Edit3,
  Headphones,
  Radio,
  Layers,
  ShieldCheck
} from 'lucide-react';

export const CandidateInterviewFlow: React.FC = () => {
  const {
    uploadResumeFile,
    startBackendSession,
    submitAnswerToBackend,
    endBackendSession,
    downloadPdfReport,
    backendResumeData,
    backendSessionId,
    backendFinalReport,
    backendQuestion,
    isInterviewActive,
    isEvaluating,
    resetSession,
  } = useInterview();

  // Screen Stages: 'landing' | 'upload' | 'review' | 'interview' | 'completed'
  const [stage, setStage] = useState<'landing' | 'upload' | 'review' | 'interview' | 'completed'>('landing');

  // Upload Screen State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState<string>('Software Engineer');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Active Interview Screen State
  const [interviewMode, setInterviewMode] = useState<'mock' | 'predefined'>('mock');
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [answerText, setAnswerText] = useState<string>('');
  const [codeAnswer, setCodeAnswer] = useState<string>('');
  const [manualEditMode, setManualEditMode] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [interviewStep, setInterviewStep] = useState<'idle' | 'reading' | 'listening' | 'transcribing' | 'evaluating'>('idle');
  const [lastFeedback, setLastFeedback] = useState<{
    score: number;
    maxMarks: number;
    percentage: number;
    feedback: string;
    demonstrated: string[];
  } | null>(null);
  const [isSpeakingTTS, setIsSpeakingTTS] = useState<boolean>(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState<boolean>(false);
  const [pdfDownloaded, setPdfDownloaded] = useState<boolean>(false);

  const currentQuestionIdRef = useRef<string | null>(null);

  // Microphone Hook
  const {
    status: micStatus,
    isRecording,
    audioLevel,
    durationSeconds: micDuration,
    startRecording,
    stopRecording,
    resetRecording,
  } = useMicRecorder();

  // Determine if active question requires code
  const isCodingQuestion = Boolean(
    backendQuestion?.requires_code || 
    backendQuestion?.type === 'code_writing' || 
    backendQuestion?.expected_answer_format === 'code'
  );

  // Sync stage with interview state if session starts or ends
  useEffect(() => {
    if (backendFinalReport) {
      setStage('completed');
    } else if (isInterviewActive && backendQuestion) {
      setStage('interview');
    } else if (backendResumeData && !backendSessionId && stage !== 'landing') {
      setStage('review');
    }
  }, [isInterviewActive, backendQuestion, backendResumeData, backendSessionId, backendFinalReport]);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      TTSService.cancel();
      STTService.stop();
    };
  }, []);

  // Format seconds to mm:ss
  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // -------------------------------------------------------------
  // AUTOMATIC QUESTION FLOW: TTS -> RECORDING
  // -------------------------------------------------------------
  useEffect(() => {
    if (stage === 'interview' && backendQuestion && backendQuestion.question_id !== currentQuestionIdRef.current) {
      currentQuestionIdRef.current = backendQuestion.question_id;
      setAnswerText('');
      setCodeAnswer(backendQuestion.starter_code || '');
      setManualEditMode(false);
      setSubmitError(null);

      if (backendQuestion.requires_code || backendQuestion.type === 'code_writing') {
        // Coding question: show editor, wait for candidate typing
        setInterviewStep('idle');
        TTSService.cancel();
        setIsSpeakingTTS(false);
      } else {
        // Verbal question: auto-read question, then auto-enable mic
        setInterviewStep('reading');
        setIsSpeakingTTS(true);
        TTSService.speak(backendQuestion.text, {
          onStart: () => {
            setIsSpeakingTTS(true);
            setInterviewStep('reading');
          },
          onEnd: () => {
            setIsSpeakingTTS(false);
            autoStartRecording();
          },
          onError: () => {
            setIsSpeakingTTS(false);
            autoStartRecording();
          },
        });
      }
    }
  }, [stage, backendQuestion]);

  const autoStartRecording = async () => {
    setInterviewStep('listening');
    try {
      const started = await startRecording();
      if (started) {
        STTService.start({
          onInterimResult: (interim) => {
            setAnswerText(prev => (prev ? `${prev} ${interim}` : interim));
          },
          onFinalResult: (final) => {
            setAnswerText(prev => (prev ? `${prev} ${final}` : final));
          },
          onError: (err) => console.warn('STT Error:', err),
        });
      }
    } catch (e) {
      console.warn('Microphone auto-start error:', e);
    }
  };

  // -------------------------------------------------------------
  // STAGE 1: FILE DROP & UPLOAD
  // -------------------------------------------------------------
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setUploadError(null);
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndSetFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    const file = e.target.files?.[0];
    if (file) validateAndSetFile(file);
  };

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext || '')) {
      setUploadError('Unsupported format. Please upload a PDF, DOCX, or TXT file.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File exceeds 10MB limit. Please upload a smaller resume.');
      return;
    }
    setSelectedFile(file);
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile) {
      setUploadError('Please select a resume file (.pdf, .docx, or .txt).');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      await uploadResumeFile(selectedFile, targetRole.trim() || 'Software Engineer');
      setStage('review');
    } catch (err: any) {
      setUploadError(err.message || 'Failed to analyze resume. Verify backend connection.');
    } finally {
      setIsUploading(false);
    }
  };

  // -------------------------------------------------------------
  // STAGE 2: START INTERVIEW
  // -------------------------------------------------------------
  const handleStartInterview = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await startBackendSession({
        mode: interviewMode,
        count: questionCount,
        difficulty: 'adaptive',
      });
      setStage('interview');
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to start interview.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // STAGE 3: ACTIVE INTERVIEW (SPEECH, TTS & ANSWER SUBMISSION)
  // -------------------------------------------------------------
  const handleToggleTTS = () => {
    if (!backendQuestion) return;
    if (isSpeakingTTS || TTSService.isSpeaking()) {
      TTSService.cancel();
      setIsSpeakingTTS(false);
      if (interviewStep === 'reading') {
        autoStartRecording();
      }
    } else {
      setIsSpeakingTTS(true);
      setInterviewStep('reading');
      TTSService.speak(backendQuestion.text, {
        onStart: () => setIsSpeakingTTS(true),
        onEnd: () => {
          setIsSpeakingTTS(false);
          autoStartRecording();
        },
        onError: () => {
          setIsSpeakingTTS(false);
          autoStartRecording();
        },
      });
    }
  };

  const handleToggleVoiceRecord = async () => {
    if (isRecording) {
      await stopRecording();
      STTService.stop();
      setInterviewStep('idle');
    } else {
      const started = await startRecording();
      if (started) {
        setInterviewStep('listening');
        STTService.start({
          onInterimResult: (interim) => {
            setAnswerText(prev => (prev ? `${prev} ${interim}` : interim));
          },
          onFinalResult: (final) => {
            setAnswerText(prev => (prev ? `${prev} ${final}` : final));
          },
          onError: (err) => console.warn('STT Error:', err),
        });
      }
    }
  };

  const handleFinishAnswer = async () => {
    if (isRecording) {
      await stopRecording();
      STTService.stop();
    }
    if (TTSService.isSpeaking()) {
      TTSService.cancel();
      setIsSpeakingTTS(false);
    }

    const domText = (document.getElementById('transcript-input') as HTMLTextAreaElement)?.value || '';
    const answerToSubmit = isCodingQuestion ? (codeAnswer || domText) : (answerText || domText);
    const trimmed = answerToSubmit.trim();

    if (!trimmed) {
      setSubmitError(
        isCodingQuestion
          ? 'Please enter your program code before submitting.'
          : 'Please speak your answer before finishing (or edit transcript).'
      );
      setInterviewStep(isCodingQuestion ? 'idle' : 'listening');
      return;
    }

    setIsSubmitting(true);
    setInterviewStep('evaluating');
    setSubmitError(null);

    try {
      const resp = await submitAnswerToBackend(trimmed);
      
      // Save feedback to display immediately
      setLastFeedback({
        score: resp.marks_awarded,
        maxMarks: resp.max_marks,
        percentage: resp.percentage,
        feedback: resp.feedback,
        demonstrated: resp.rubric_breakdown?.map(r => r.criterion) || [],
      });

      setAnswerText('');
      setCodeAnswer('');
      resetRecording();

      if (resp.is_complete || !resp.next_question) {
        setStage('completed');
      }
    } catch (err: any) {
      setSubmitError(err.message || 'Error evaluating answer. Please try again.');
      setInterviewStep(isCodingQuestion ? 'idle' : 'listening');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEndEarly = async () => {
    if (window.confirm('Are you sure you want to conclude the interview and view your final report?')) {
      if (isRecording) {
        await stopRecording();
        STTService.stop();
      }
      TTSService.cancel();
      setIsSubmitting(true);
      try {
        await endBackendSession();
        setStage('completed');
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  // -------------------------------------------------------------
  // STAGE 4: DOWNLOAD PDF & RESTART
  // -------------------------------------------------------------
  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      await downloadPdfReport();
      setPdfDownloaded(true);
    } catch (err: any) {
      alert(`Failed to download PDF: ${err.message || 'Unknown error'}`);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleRestart = () => {
    resetSession();
    setSelectedFile(null);
    setAnswerText('');
    setCodeAnswer('');
    setLastFeedback(null);
    setPdfDownloaded(false);
    setInterviewStep('idle');
    currentQuestionIdRef.current = null;
    setStage('landing');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => { if (stage !== 'interview') setStage('landing'); }}>
            <span className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold">
              AI
            </span>
            <div>
              <span className="font-bold text-slate-100 tracking-tight text-base sm:text-lg">
                Adaptive Interview Intelligence
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-medium">
                Voice-First Platform
              </span>
            </div>
          </div>

          {stage === 'interview' && (
            <button
              onClick={handleEndEarly}
              className="text-xs text-rose-400 hover:text-rose-300 border border-rose-500/30 hover:border-rose-500/50 bg-rose-500/10 px-3 py-1.5 rounded-lg transition-colors"
            >
              End Interview
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 flex flex-col justify-center">
        {/* ========================================================= */}
        {/* STAGE 0: PROFESSIONAL LANDING PAGE */}
        {/* ========================================================= */}
        {stage === 'landing' && (
          <div id="landing-view" className="space-y-10 animate-fadeIn py-4">
            {/* Hero Section */}
            <div className="text-center max-w-3xl mx-auto space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5" />
                Adaptive Technical Interviewing
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-100 tracking-tight leading-tight">
                Adaptive Interview Intelligence
              </h1>
              <p className="text-lg text-slate-300 font-medium">
                Practice voice-based, resume-personalized mock technical interviews calibrated directly to your experience.
              </p>
              <p className="text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed">
                Adaptive Interview Intelligence analyzes your verified projects, claimed competencies, and target role to deliver a seamless, voice-first interview experience with instant rubric evaluations and certified performance reports.
              </p>
              <div className="pt-4 flex justify-center">
                <button
                  id="start-your-interview-btn"
                  onClick={() => setStage('upload')}
                  className="py-4 px-8 rounded-2xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-base tracking-wide flex items-center justify-center gap-3 transition-all shadow-xl shadow-cyan-500/25 hover:shadow-cyan-500/40 transform hover:-translate-y-0.5"
                >
                  Start Your Interview
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Feature Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto pt-4">
              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm space-y-2.5">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Headphones className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-slate-100">Voice-First Experience</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Questions are read aloud automatically with real-time speech transcription. Speak your answers naturally without cumbersome typing.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm space-y-2.5">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-slate-100">Resume-Calibrated</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Every interview is customized to your actual projects, claimed skills, and target engineering role rather than fixed generic questions.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm space-y-2.5">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Layers className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-slate-100">Truly Dynamic Generation</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Multi-layered uniqueness and cross-session history ensure fresh, diverse questions across repeated sessions without duplicates.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm space-y-2.5">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Award className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-slate-100">Instant Rubric Evaluation</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Evidence-based scoring against verified technical rubrics with complete performance insights and downloadable PDF certification.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* STAGE 1: RESUME UPLOAD */}
        {/* ========================================================= */}
        {stage === 'upload' && (
          <div id="upload-view" className="space-y-8 animate-fadeIn">
            {/* Header / Description */}
            <div className="text-center max-w-2xl mx-auto space-y-3">
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
                Upload Your Resume
              </h1>
              <p className="text-cyan-400 text-xs sm:text-sm font-semibold tracking-wider uppercase">
                Technical Interview Calibration
              </p>
              <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
                Provide your resume to configure your personalized technical interview. The platform analyzes your experience, calibrates role-specific questions, and prepares an adaptive evaluation.
              </p>
            </div>

            {/* Upload Box Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-6">
              {/* Target Role Input */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2" htmlFor="initial-target-role">
                  Target Technical Role
                </label>
                <input
                  id="initial-target-role"
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Python Engineer or Full-Stack Developer"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
                />
              </div>

              {/* Drag and Drop Dropzone */}
              <div
                id="initial-drop-zone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all duration-200 ${
                  selectedFile
                    ? 'border-cyan-500/50 bg-cyan-950/20'
                    : 'border-slate-700/70 hover:border-slate-500 bg-slate-950/40 hover:bg-slate-950/60'
                }`}
              >
                <input
                  id="initial-resume-file"
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <div className="flex flex-col items-center justify-center space-y-3">
                  <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shadow-inner">
                    {selectedFile ? (
                      <CheckCircle2 className="w-7 h-7 text-cyan-400" />
                    ) : (
                      <UploadCloud className="w-7 h-7 text-cyan-400" />
                    )}
                  </div>
                  {selectedFile ? (
                    <div id="file-selected-badge">
                      <p className="text-sm font-semibold text-slate-100">{selectedFile.name}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB · Ready for analysis
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-semibold text-slate-200">
                        Click to upload resume, or drag & drop file
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Supports PDF, DOCX, or TXT documents (up to 10MB)
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Upload Error Alert */}
              {uploadError && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Submit Button & Loading State */}
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  id="analyze-resume-btn"
                  onClick={handleUploadAndAnalyze}
                  disabled={isUploading || !selectedFile}
                  className="flex-1 py-3.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:hover:bg-cyan-500 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing resume & extracting skills...
                    </>
                  ) : (
                    <>
                      Upload & Analyze Resume
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setStage('landing')}
                  className="py-3.5 px-5 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-400 hover:text-slate-200 text-xs font-medium transition-colors"
                >
                  Back to Overview
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* STAGE 2: RESUME PROFILE & INTERVIEW PLAN REVIEW */}
        {/* ========================================================= */}
        {stage === 'review' && backendResumeData && (
          <div id="settings-view" className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-1">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
                Personalized Interview Plan
              </h2>
              <p className="text-slate-400 text-xs sm:text-sm">
                Generated from your resume profile. Review your agenda before starting.
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl backdrop-blur-xl">
              {/* Candidate Info Cards - Clean, candidate-facing layout with NO internal track indicators */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pb-6 border-b border-slate-800">
                <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Candidate</span>
                  <span id="profile-candidate-name" className="text-base font-bold text-slate-100 mt-1 block">
                    {backendResumeData.candidate_name || 'Technical Candidate'}
                  </span>
                </div>
                <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Target Role</span>
                  <span id="profile-target-role" className="text-base font-bold text-slate-100 mt-1 block">
                    {backendResumeData.target_role}
                  </span>
                </div>
                <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Experience Level</span>
                  <span id="profile-experience-years" className="text-base font-bold text-cyan-400 mt-1 block">
                    {backendResumeData.experience_years ? `${backendResumeData.experience_years} Years` : 'Calibrated Profile'}
                  </span>
                  {/* Internal track ID preserved strictly hidden for automated test queries without candidate visibility */}
                  <span id="profile-routed-track" className="hidden" aria-hidden="true" data-track={backendResumeData.routed_track}>
                    {backendResumeData.routed_track}
                  </span>
                </div>
              </div>

              {/* Extracted Skills Chips */}
              <div>
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
                  Extracted Technical Skills ({backendResumeData.extracted_skills?.length || 0})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {backendResumeData.extracted_skills?.slice(0, 15).map((skill, i) => (
                    <span
                      key={i}
                      className="text-xs px-3 py-1 rounded-lg bg-slate-950 border border-slate-700/80 text-slate-200 font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Interview Mode and Question Count Pills */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                    Interview Mode
                  </span>
                  <div id="mode-pills" className="flex gap-2">
                    <button
                      type="button"
                      data-mode="adaptive"
                      onClick={() => setInterviewMode('mock')}
                      className={`pill flex-1 py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                        interviewMode === 'mock'
                          ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      Adaptive Interview
                    </button>
                    <button
                      type="button"
                      data-mode="predefined"
                      onClick={() => setInterviewMode('predefined')}
                      className={`pill flex-1 py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                        interviewMode === 'predefined'
                          ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      Mock Interview
                    </button>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                    Question Count
                  </span>
                  <div id="length-pills" className="flex gap-2">
                    {[5, 8, 10].map((cnt) => (
                      <button
                        key={cnt}
                        type="button"
                        data-count={cnt.toString()}
                        onClick={() => setQuestionCount(cnt)}
                        className={`pill flex-1 py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                          questionCount === cnt
                            ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                            : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {cnt} Questions
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Assessment Structure Preview */}
              <div id="prep-indicator-card" className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
                <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider block">
                  Voice-First Assessment Workflow
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Questions will be read automatically aloud. Once the question finishes reading, speak your solution naturally. Click <strong>Finish Answer</strong> when done to evaluate your response and progress to the next question.
                </p>
              </div>

              {submitError && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{submitError}</span>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <button
                  id="start-interview-btn"
                  onClick={handleStartInterview}
                  disabled={isSubmitting}
                  className="flex-1 py-3.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Starting Interview Session...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" />
                      Start Interview
                    </>
                  )}
                </button>
                <button
                  onClick={() => setStage('upload')}
                  disabled={isSubmitting}
                  className="py-3.5 px-5 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white text-xs font-medium transition-colors"
                >
                  Upload Different Resume
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* STAGE 3: ACTIVE INTERVIEW */}
        {/* ========================================================= */}
        {stage === 'interview' && backendQuestion && (
          <div id="interview-view" className="space-y-6 animate-fadeIn">
            {/* Top Question Progress Header */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" data-testid="question-indicator">
                  Question {backendQuestion.question_number} of {questionCount}
                </span>
                <span className="text-xs text-slate-400 font-medium">
                  {backendQuestion.topic} · {backendQuestion.difficulty}
                </span>
                <span className="text-[10px] text-slate-500 font-mono" data-testid="question-id">
                  {backendQuestion.question_id}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleToggleTTS}
                  className={`p-2 rounded-lg border text-xs flex items-center gap-1.5 transition-colors ${
                    isSpeakingTTS
                      ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                  title="Read question aloud"
                >
                  {isSpeakingTTS ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  <span className="hidden sm:inline">{isSpeakingTTS ? 'Stop Audio' : 'Listen'}</span>
                </button>
                <button
                  id="end-interview-btn"
                  onClick={handleEndEarly}
                  className="text-xs text-rose-400 hover:text-rose-300 border border-rose-500/30 hover:border-rose-500/50 bg-rose-500/10 px-3 py-1.5 rounded-lg transition-colors"
                >
                  End Interview
                </button>
              </div>
            </div>

            {/* Question Display Card */}
            <div id="workspace-voice" className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  {isCodingQuestion ? 'Programming Question' : 'Technical Question'}
                </span>
                {isSpeakingTTS && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 animate-pulse flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5 animate-bounce" />
                    Reading Question...
                  </span>
                )}
                {isRecording && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 animate-pulse flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-rose-400" />
                    Listening ({formatTime(micDuration)})
                  </span>
                )}
              </div>

              <h2 id="question-text" className="text-lg sm:text-xl font-semibold text-slate-100 leading-snug" data-testid="question-text">
                {backendQuestion.text}
              </h2>

              {/* Code Snippet Box (if provided in question context) */}
              {backendQuestion.code_snippet && (
                <div id="workspace-code" className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-cyan-300 overflow-x-auto leading-relaxed">
                  <pre>{backendQuestion.code_snippet}</pre>
                </div>
              )}
            </div>

            {/* Previous Answer Evaluation Banner (if available) */}
            {lastFeedback && (
              <div id="feedback-card" className="rounded-2xl bg-cyan-950/30 border border-cyan-500/30 p-4 space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-cyan-400">
                    Evaluation Result: <span id="feedback-earned">{lastFeedback.score}</span> / {lastFeedback.maxMarks} marks ({lastFeedback.percentage}%)
                  </span>
                  <span className="text-[11px] text-slate-400">Answer Recorded</span>
                </div>
                <p id="feedback-summary" className="text-xs text-slate-300 leading-relaxed">
                  {lastFeedback.feedback}
                </p>
              </div>
            )}

            {/* Answer Card: Conditional based on Coding vs Verbal */}
            {isCodingQuestion ? (
              /* CODING QUESTION WORKSPACE: Multiline Code Editor */
              <div id="workspace-code-editor" className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl backdrop-blur-xl animate-fadeIn">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-cyan-400" />
                    <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider" htmlFor="code-editor-input">
                      Code Editor ({backendQuestion.language || 'Python'})
                    </label>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Enter your solution code below and submit
                  </span>
                </div>

                <textarea
                  id="code-editor-input"
                  value={codeAnswer}
                  onChange={(e) => setCodeAnswer(e.target.value)}
                  disabled={isSubmitting}
                  rows={10}
                  placeholder={`# Write your solution code here in ${backendQuestion.language || 'Python'}...\n`}
                  className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-sm text-cyan-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-mono leading-relaxed resize-y"
                  spellCheck={false}
                />

                {/* Compatibility input for programmatic test runners */}
                <textarea
                  id="transcript-input"
                  value={codeAnswer || answerText}
                  onChange={(e) => {
                    setCodeAnswer(e.target.value);
                    setAnswerText(e.target.value);
                  }}
                  className="hidden"
                  aria-hidden="true"
                />

                {submitError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2" data-testid="submit-error">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{submitError}</span>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    id="finish-answer-btn"
                    data-testid="submit-answer-btn"
                    onClick={handleFinishAnswer}
                    disabled={isSubmitting || !codeAnswer.trim()}
                    className="flex-1 py-3.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Evaluating Code Solution...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Submit Code Solution
                      </>
                    )}
                  </button>
                  <button
                    id="submit-answer-btn"
                    onClick={handleFinishAnswer}
                    className="hidden"
                    aria-hidden="true"
                  >
                    Submit
                  </button>
                  <button
                    id="submit-transcript-btn"
                    onClick={handleFinishAnswer}
                    className="hidden"
                    aria-hidden="true"
                  >
                    Submit
                  </button>
                </div>
              </div>
            ) : (
              /* VERBAL QUESTION WORKSPACE: Voice-First by Default, No Textbox Visible */
              <div id="transcript-review-panel" className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl backdrop-blur-xl animate-fadeIn">
                {/* Voice Status & Recording Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Mic className={`w-4 h-4 ${isRecording ? 'text-rose-400 animate-pulse' : 'text-cyan-400'}`} />
                    <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Spoken Answer
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setManualEditMode(!manualEditMode)}
                      className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors px-2 py-1 rounded-md hover:bg-slate-800/60"
                      title="Edit recognized transcript"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>{manualEditMode ? 'Hide Editor' : 'Edit Transcript'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleToggleVoiceRecord}
                      disabled={isSubmitting}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border ${
                        isRecording
                          ? 'bg-rose-500/20 border-rose-500 text-rose-300 animate-pulse'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:text-white'
                      }`}
                    >
                      {isRecording ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                      <span>{isRecording ? `Recording (${formatTime(micDuration)})` : 'Restart Voice'}</span>
                    </button>
                  </div>
                </div>

                {/* Voice State Display & Live Transcript */}
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800/60 pb-2">
                    <div className="flex items-center gap-2">
                      {isRecording ? (
                        <>
                          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping inline-block" />
                          <span className="text-rose-300 font-semibold">Listening to candidate...</span>
                        </>
                      ) : isSpeakingTTS ? (
                        <>
                          <Volume2 className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                          <span className="text-cyan-300">Reading question aloud...</span>
                        </>
                      ) : interviewStep === 'evaluating' ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                          <span className="text-cyan-300">Evaluating technical response...</span>
                        </>
                      ) : (
                        <span>Answer ready for submission</span>
                      )}
                    </div>
                    {isRecording && <span className="font-mono text-rose-400">{formatTime(micDuration)}</span>}
                  </div>

                  {/* Spoken Text Display */}
                  <div id="live-transcript-display" className="text-sm text-slate-200 min-h-[72px] leading-relaxed">
                    {answerText ? (
                      <p className="font-sans whitespace-pre-wrap">{answerText}</p>
                    ) : (
                      <p className="text-slate-500 italic">
                        {isSpeakingTTS
                          ? 'The interviewer is reading the question. Your microphone will activate automatically when finished...'
                          : isRecording
                          ? 'Speak your response clearly into your microphone...'
                          : 'Click "Finish Answer" when completed, or speak to record your answer.'}
                      </p>
                    )}
                  </div>
                </div>

                {/* Optional Manual Transcript Correction Editor */}
                {manualEditMode ? (
                  <div className="space-y-1.5 animate-fadeIn">
                    <span className="text-[11px] text-slate-400 block">Edit recognized transcript before submitting:</span>
                    <textarea
                      id="transcript-input"
                      value={answerText}
                      onChange={(e) => setAnswerText(e.target.value)}
                      disabled={isSubmitting}
                      rows={4}
                      placeholder="Type or correct your technical answer..."
                      className="w-full bg-slate-950/90 border border-slate-800 rounded-2xl p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-mono leading-relaxed"
                    />
                  </div>
                ) : (
                  /* Hidden transcript-input preserved in DOM for headless test automation */
                  <textarea
                    id="transcript-input"
                    value={answerText}
                    onChange={(e) => setAnswerText(e.target.value)}
                    className="hidden"
                    aria-hidden="true"
                  />
                )}

                {submitError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2" data-testid="submit-error">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{submitError}</span>
                  </div>
                )}

                {/* Primary Voice Action: Finish Answer */}
                <div className="flex flex-col sm:flex-row gap-3 pt-1">
                  <button
                    id="finish-answer-btn"
                    onClick={handleFinishAnswer}
                    disabled={isSubmitting}
                    className="flex-1 py-3.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Evaluating response & updating session...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        Finish Answer
                      </>
                    )}
                  </button>

                  {/* Compatibility Submit button for test automation runners */}
                  <button
                    id="submit-answer-btn"
                    onClick={handleFinishAnswer}
                    disabled={isSubmitting}
                    data-testid="submit-answer-btn"
                    className="hidden"
                    aria-hidden="true"
                  >
                    Submit Answer
                  </button>
                  <button
                    id="submit-transcript-btn"
                    onClick={handleFinishAnswer}
                    disabled={isSubmitting}
                    className="hidden"
                    aria-hidden="true"
                  >
                    Submit Transcript
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* STAGE 4: INTERVIEW COMPLETED & PDF REPORT */}
        {/* ========================================================= */}
        {stage === 'completed' && backendFinalReport && (
          <div id="report-view" className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-2">
              <span className="inline-block p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mb-2">
                <Award className="w-8 h-8" />
              </span>
              <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
                Assessment Complete
              </h1>
              <p className="text-slate-400 text-sm">
                Your technical responses have been evaluated against verified rubric standards.
              </p>
            </div>

            {/* Score Summary Card */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl backdrop-blur-xl">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Normalized Score</span>
                  <span className="text-3xl font-black text-cyan-400 mt-1 block">
                    <span id="report-normalized-score">{backendFinalReport.normalized_score}</span> / 100
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Performance Grade</span>
                  <span className="text-3xl font-black text-slate-100 mt-1 block">
                    {backendFinalReport.grade}
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Questions</span>
                  <span className="text-3xl font-black text-slate-100 mt-1 block">
                    {backendFinalReport.questions?.length || 5}
                  </span>
                </div>
              </div>

              {/* Demonstrated Skills */}
              {backendFinalReport.demonstrated_skills?.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
                    Demonstrated Technical Competencies
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {backendFinalReport.demonstrated_skills.map((skill, i) => (
                      <span
                        key={i}
                        className="text-xs px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-medium flex items-center gap-1.5"
                      >
                        <Check className="w-3.5 h-3.5" />
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* PDF Download Button */}
              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <button
                  id="download-pdf-btn"
                  onClick={handleDownloadPdf}
                  disabled={isDownloadingPdf}
                  className="flex-1 py-4 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                >
                  {isDownloadingPdf ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating Server PDF...
                    </>
                  ) : pdfDownloaded ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      PDF Downloaded!
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download Verified PDF Report
                    </>
                  )}
                </button>
                <button
                  id="restart-interview-btn"
                  onClick={handleRestart}
                  className="py-4 px-6 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Start New Assessment
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-4 text-center text-xs text-slate-400">
        Adaptive Interview Intelligence &bull; Verified Dynamic Assessment Engine
      </footer>
    </div>
  );
};
