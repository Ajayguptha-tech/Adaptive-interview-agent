import React from 'react';
import { InterviewProvider, useInterview } from './context/InterviewContext';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { Sidebar } from './components/layout/Sidebar';
import { AmbientBackground } from './components/effects/AmbientBackground';
import { LandingPage } from './components/landing/LandingPage';
import { DashboardOverview } from './components/dashboard/DashboardOverview';
import { InterviewSetupScreen } from './components/setup/InterviewSetupScreen';
import { LiveInterviewScreen } from './components/live/LiveInterviewScreen';
import { EvidenceSkillGapScreen } from './components/evidence/EvidenceSkillGapScreen';
import { IntegrityTimelineScreen } from './components/integrity/IntegrityTimelineScreen';
import { CandidateReportScreen } from './components/report/CandidateReportScreen';

const MainContent: React.FC = () => {
  const { activeTab } = useInterview();

  return (
    <main className="flex-1 w-full relative z-10">
      {activeTab === 'dashboard' && <DashboardOverview />}
      {activeTab === 'setup' && <InterviewSetupScreen />}
      {activeTab === 'live' && <LiveInterviewScreen />}
      {activeTab === 'evidence' && <EvidenceSkillGapScreen />}
      {activeTab === 'integrity' && <IntegrityTimelineScreen />}
      {activeTab === 'report' && <CandidateReportScreen />}
    </main>
  );
};

const Shell: React.FC = () => {
  const { activeTab } = useInterview();

  // Landing page is a full-bleed introduction with its own navigation.
  if (activeTab === 'landing') {
    return (
      <div className="min-h-screen bg-[#f4f3ee] text-[#111210]">
        <LandingPage />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f4f3ee] text-[#111210] relative selection:bg-lime-300 selection:text-black">
      <AmbientBackground />
      <Sidebar />
      <div className="lg:pl-64 min-h-screen flex flex-col relative z-10">
        <Navbar />
        <MainContent />
        <Footer />
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <InterviewProvider>
      <Shell />
    </InterviewProvider>
  );
};

export default App;
