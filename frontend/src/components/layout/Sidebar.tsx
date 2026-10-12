import React from 'react';
import { useInterview, NavigationTab } from '../../context/InterviewContext';
import {
  Orbit, LayoutDashboard, FileText, Radio, GitCompare, ShieldAlert, FileCheck2, Home,
} from 'lucide-react';

export const NAV_ITEMS: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Workspace', icon: <LayoutDashboard className="w-[18px] h-[18px]" /> },
  { id: 'setup', label: 'Setup', icon: <FileText className="w-[18px] h-[18px]" /> },
  { id: 'live', label: 'Live Adaptive', icon: <Radio className="w-[18px] h-[18px]" /> },
  { id: 'evidence', label: 'Evidence Map', icon: <GitCompare className="w-[18px] h-[18px]" /> },
  { id: 'integrity', label: 'Integrity Timeline', icon: <ShieldAlert className="w-[18px] h-[18px]" /> },
  { id: 'report', label: 'Report Dossier', icon: <FileCheck2 className="w-[18px] h-[18px]" /> },
];

/** Charcoal desktop sidebar (lg+). Mobile uses the scroll row in Navbar. */
export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab, isInterviewActive, selectedCandidate } = useInterview();

  return (
    <aside className="hidden lg:flex fixed inset-y-0 left-0 z-40 w-64 flex-col bg-[#1b1c17] text-white p-4" aria-label="Primary">
      <button onClick={() => setActiveTab('landing')} className="flex items-center gap-3 px-2 py-3 text-left" aria-label="Back to home page">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#c6ee2e]"><Orbit className="h-5 w-5 text-[#111210]" /></span>
        <span>
          <span className="block text-[15px] font-bold leading-tight">Adaptive Interview Intelligence</span>
        </span>
      </button>

      <nav className="mt-6 flex-1 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              aria-current={active ? 'page' : undefined}
              className={`w-full flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-medium transition-colors ${
                active ? 'bg-[#c6ee2e] text-[#111210]' : 'text-white/65 hover:bg-white/8 hover:text-white'
              }`}
            >
              {item.icon}
              <span className="flex-1 text-left">{item.label}</span>
              {item.id === 'live' && isInterviewActive && (
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="space-y-3">
        {selectedCandidate && (
          <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
            <div className="text-[10px] uppercase tracking-widest text-white/40">Active candidate</div>
            <div className="mt-1 text-sm font-semibold truncate">{selectedCandidate.name}</div>
          </div>
        )}
        <button onClick={() => setActiveTab('landing')} className="w-full flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm text-white/55 hover:text-white hover:bg-white/8 transition-colors">
          <Home className="w-[18px] h-[18px]" /> Home page
        </button>
      </div>
    </aside>
  );
};
