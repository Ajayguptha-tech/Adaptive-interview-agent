import React from 'react';
import { useInterview } from '../../context/InterviewContext';
import { NAV_ITEMS } from './Sidebar';
import { Orbit, Server, ServerOff } from 'lucide-react';

/** Top bar: connection / mode status (all pages) + mobile & tablet navigation row. */
export const Navbar: React.FC = () => {
  const { activeTab, setActiveTab, isBackendConnected, isDemoMode, setIsDemoMode, selectedCandidate } = useInterview();
  const current = NAV_ITEMS.find((n) => n.id === activeTab);

  return (
    <header className="sticky top-0 z-30 w-full bg-[#f4f3ee]/85 backdrop-blur border-b border-black/5">
      <div className="flex items-center justify-between gap-3 px-4 sm:px-6 h-16">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => setActiveTab('landing')} className="lg:hidden grid h-9 w-9 place-items-center rounded-xl bg-[#1b1c17]" aria-label="Back to home page">
            <Orbit className="h-5 w-5 text-[#c6ee2e]" />
          </button>
          <div className="min-w-0">
            <div className="text-base font-bold tracking-tight truncate">{current?.label ?? 'Adaptive Interview Intelligence'}</div>
            {selectedCandidate && <div className="hidden sm:block text-xs text-[#7d7c74] truncate">Active: {selectedCandidate.name}</div>}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isBackendConnected ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-xs font-medium text-emerald-700">
              <Server className="h-3.5 w-3.5" /> FastAPI connected
            </span>
          ) : (
            <button
              onClick={() => setIsDemoMode(!isDemoMode)}
              title="Toggle Demo Mode / Backend connection"
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                isDemoMode ? 'bg-[#c6ee2e] border-[#8fb80f]/40 text-[#111210] hover:bg-[#d2f34f]' : 'bg-amber-50 border-amber-200 text-amber-800 hover:bg-amber-100'
              }`}
            >
              {isDemoMode ? (<><span className="h-1.5 w-1.5 rounded-full bg-[#111210] animate-pulse" /> Demo mode (client AI agents)</>) : (<><ServerOff className="h-3.5 w-3.5" /> FastAPI backend standby</>)}
            </button>
          )}
        </div>
      </div>

      <nav className="lg:hidden flex items-center gap-2 overflow-x-auto no-scrollbar px-4 pb-3" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const active = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2 text-xs font-semibold transition-colors ${
                active ? 'bg-[#1b1c17] text-white' : 'bg-white border border-black/5 text-[#44443d] hover:border-black/30'
              }`}
            >
              {item.icon}<span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
};
