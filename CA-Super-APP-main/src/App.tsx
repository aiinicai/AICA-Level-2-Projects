import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/Navbar';
import { LoginModal } from './components/LoginModal';
import { ResetCredentialsModal } from './components/ResetCredentialsModal';
import { UdinManager } from './components/UdinManager';
import { TaskManagement } from './components/TaskManagement';
import { StatutoryCalendar } from './components/StatutoryCalendar';
import { GovernmentPortals } from './components/GovernmentPortals';
import { MsmeAssistant } from './components/MsmeAssistant';
import { AifAssistant } from './components/AifAssistant';
import { OfficeAutomationTools } from './components/OfficeAutomationTools';
import { SidebarUpcomingCalendar } from './components/SidebarUpcomingCalendar';
import { 
  Building2, 
  Calendar as CalendarIcon, 
  Globe2, 
  KeyRound, 
  FileSpreadsheet, 
  Sprout, 
  Wrench, 
  Settings2, 
  Sparkles, 
  CheckSquare, 
  ExternalLink,
  ShieldCheck,
  X,
  Flame,
  Layers,
  ChevronRight
} from 'lucide-react';

const AppContent: React.FC = () => {
  const { auth, tasks } = useApp();

  // Active modal state for the small tabs
  const [activeModalTab, setActiveModalTab] = useState<string | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isResetCredsOpen, setIsResetCredsOpen] = useState(false);

  const smallTabs = [
    {
      id: 'calendar',
      label: 'Statutory Calendar',
      sublabel: auth.role === 'admin' ? '15-Day Look' : '7-Day Look',
      desc: 'GST, TDS, ITR & Punjab Holidays',
      icon: CalendarIcon,
      color: 'from-amber-600 to-amber-700',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300'
    },
    {
      id: 'portals',
      label: 'Govt Portals',
      sublabel: 'ITR • GST • MSME',
      desc: 'Direct links to official portals',
      icon: Globe2,
      color: 'from-amber-700 to-yellow-800',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300'
    },
    {
      id: 'udin',
      label: 'UDIN ICAI Vault',
      sublabel: '2 Partners & Captcha',
      desc: 'Partner 1 & 2 credentials & login',
      icon: KeyRound,
      color: 'from-amber-600 to-amber-800',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300'
    },
    {
      id: 'msme',
      label: 'MSME Udyam AI',
      sublabel: 'Folder Extractor',
      desc: 'Extract KYC & download certificate',
      icon: FileSpreadsheet,
      color: 'from-yellow-600 to-amber-700',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300',
      aiBadge: true
    },
    {
      id: 'aif',
      label: 'AIF Agri Fund',
      sublabel: '3% Subvention DPR',
      desc: 'Interest subvention calculator',
      icon: Sprout,
      color: 'from-amber-700 to-amber-900',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300',
      aiBadge: true
    },
    {
      id: 'tools',
      label: 'Office PDF Tools',
      sublabel: 'Merge • Compress MB',
      desc: 'Client-side PDF & redaction suite',
      icon: Wrench,
      color: 'from-amber-800 to-yellow-700',
      textColor: 'text-amber-950',
      bgColor: 'bg-white hover:bg-amber-100/80 border border-amber-300'
    }
  ];

  if (!auth.role) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-100 via-yellow-50 to-amber-200/70">
        <LoginModal
          isOpen={true}
          isMandatoryLock={true}
          onClose={() => setIsLoginModalOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50/80 via-yellow-50/60 to-amber-100/40 flex flex-col selection:bg-amber-500 selection:text-white">
      {/* Top Header in Dark Yellow with Light Yellowish accents */}
      <Navbar
        onOpenResetCreds={() => setIsResetCredsOpen(true)}
        onOpenUdin={() => setActiveModalTab('udin')}
        onOpenAuthModal={() => setIsLoginModalOpen(true)}
        onSelectTab={(tabId) => setActiveModalTab(tabId)}
      />

      {/* Main Layout: Left Side Quick Launch + Right Side Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-2 sm:px-4 lg:px-8 py-3 sm:py-4">
        <div className="flex flex-row gap-2.5 sm:gap-4 items-start w-full">
          {/* LEFT SIDE: OFFICE QUICK LAUNCH TABS & 7-DAY CALENDAR BEHIND IT (Always on the Left) */}
          <aside className="w-16 sm:w-56 md:w-64 shrink-0 bg-amber-50/95 rounded-2xl p-2 sm:p-2.5 border border-amber-300 shadow-xs sticky top-16 z-20">
            <div className="flex items-center justify-between mb-2 px-0.5 sm:px-1 border-b border-amber-200/90 pb-1.5">
              <span className="text-[11px] font-black uppercase tracking-wider text-amber-950 flex items-center space-x-1.5">
                <Layers className="w-4 h-4 text-amber-700 shrink-0" />
                <span className="hidden sm:inline">Quick Launch</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] font-bold bg-amber-200/80 text-amber-950 px-1.5 py-0.2 rounded border border-amber-300">
                Tabs
              </span>
            </div>

            {/* Vertical Stack of Small Tabs Always on Left */}
            <div className="flex flex-col space-y-1.5">
              {smallTabs.map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveModalTab(tab.id)}
                    title={`${tab.label} (${tab.sublabel})`}
                    className={`p-1.5 sm:p-2 rounded-xl border text-left transition-all hover:shadow-xs hover:border-amber-500 active:scale-98 flex items-center space-x-2 group ${tab.bgColor}`}
                  >
                    <div className={`w-8 h-8 rounded-lg bg-gradient-to-tr ${tab.color} text-amber-50 flex items-center justify-center shrink-0 shadow-2xs group-hover:scale-105 transition-transform mx-auto sm:mx-0`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1 hidden sm:block">
                      <div className="flex items-center space-x-1">
                        <span className={`text-xs font-black truncate ${tab.textColor}`}>
                          {tab.label}
                        </span>
                        {tab.aiBadge && (
                          <span className="text-[8px] font-black bg-amber-600 text-amber-50 px-1 rounded-xs">
                            AI
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-amber-800/80 truncate font-semibold">
                        {tab.sublabel}
                      </div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-amber-500 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all hidden md:block" />
                  </button>
                );
              })}
            </div>

            {/* Quick Helper Note on Left Sidebar */}
            <div className="mt-2.5 pt-2 border-t border-amber-200/70 hidden sm:block text-[11px] text-amber-900/80 px-1">
              <div className="flex items-center space-x-1 font-bold text-amber-950 mb-0.5">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
                <span>One-Click Tabs</span>
              </div>
              <p className="text-[10px] text-amber-800/70 leading-relaxed">
                Click any tab to launch tool in focused popup while keeping To-Do list active.
              </p>
            </div>

            {/* 7-DAY UPCOMING CALENDAR BEHIND QUICK LAUNCH (For Both Admin & Staff) */}
            <SidebarUpcomingCalendar onOpenFullCalendar={() => setActiveModalTab('calendar')} />
          </aside>

          {/* RIGHT SIDE: TO-DO COMPLIANCE LIST */}
          <div className="flex-1 w-full min-w-0">
            <TaskManagement />
          </div>
        </div>
      </main>

      {/* Footer in Warm Light Yellow with Dark Yellow Accents */}
      <footer className="bg-amber-100/60 border-t border-amber-200/90 py-4 text-xs text-amber-900 mb-14 lg:mb-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <Building2 className="w-4 h-4 text-amber-700" />
            <span className="font-black text-amber-950">CA RISHU GARG &amp; ASSOCIATES</span>
            <span className="text-amber-800">• Chartered Accountants • Bishnandi Bazaar, Jaitu, Punjab</span>
          </div>

          <div className="flex items-center space-x-4">
            <button
              onClick={() => setActiveModalTab('udin')}
              className="text-amber-900 hover:text-amber-950 font-black flex items-center space-x-1"
            >
              <KeyRound className="w-3.5 h-3.5 text-amber-700" />
              <span>UDIN Portal Helper</span>
            </button>
            <span>•</span>
            <span className="text-amber-800">Admin &amp; Staff Recovery: <strong>rishugarg006@gmail.com</strong></span>
          </div>
        </div>
      </footer>

      {/* MODAL DIALOGS FOR EACH SMALL TAB */}

      {/* Tab 1: Full Statutory Calendar Modal */}
      {activeModalTab === 'calendar' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[92vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CalendarIcon className="w-5 h-5 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-base leading-tight">Statutory Compliance &amp; Punjab Calendar</h3>
                  <p className="text-xs text-amber-200">GST, Income Tax, Punjab Gazetted Holidays &amp; Gemini AI Sync</p>
                </div>
              </div>
              <button
                onClick={() => setActiveModalTab(null)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <StatutoryCalendar />
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Government Portals Modal */}
      {activeModalTab === 'portals' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[92vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Globe2 className="w-5 h-5 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-base leading-tight">Government Compliance Gateways</h3>
                  <p className="text-xs text-amber-200">Income Tax, GST, MSME, AIF, TRACES, MCA &amp; E-Way Bill</p>
                </div>
              </div>
              <button
                onClick={() => setActiveModalTab(null)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <GovernmentPortals />
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: UDIN ICAI Partner Vault Modal */}
      {activeModalTab === 'udin' && (
        <UdinManager
          isOpen={true}
          onClose={() => setActiveModalTab(null)}
        />
      )}

      {/* Tab 4: MSME Udyam AI Assistant Modal */}
      {activeModalTab === 'msme' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[92vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileSpreadsheet className="w-5 h-5 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-base leading-tight">MSME Udyam Application &amp; AI Extractor</h3>
                  <p className="text-xs text-amber-200">Fixed office presets + Gemini AI folder extractor + certificate download</p>
                </div>
              </div>
              <button
                onClick={() => setActiveModalTab(null)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <MsmeAssistant />
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: AIF Agri Infra Fund Assistant Modal */}
      {activeModalTab === 'aif' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[92vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sprout className="w-5 h-5 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-base leading-tight">Agriculture Infrastructure Fund (AIF) Assistant</h3>
                  <p className="text-xs text-amber-200">DPR analysis, 3% interest subvention schedule &amp; portal application</p>
                </div>
              </div>
              <button
                onClick={() => setActiveModalTab(null)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <AifAssistant />
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Office PDF & Automation Suite Modal */}
      {activeModalTab === 'tools' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden max-h-[92vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Wrench className="w-5 h-5 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-base leading-tight">CA Office PDF &amp; Automation Suite</h3>
                  <p className="text-xs text-amber-200">PDF Merge, target MB compression, Image-to-PDF, Page Organizer &amp; Redaction</p>
                </div>
              </div>
              <button
                onClick={() => setActiveModalTab(null)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <OfficeAutomationTools />
            </div>
          </div>
        </div>
      )}

      {/* Login & Credential Reset Modals */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />

      <ResetCredentialsModal
        isOpen={isResetCredsOpen}
        onClose={() => setIsResetCredsOpen(false)}
      />
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
