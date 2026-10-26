import React from 'react';
import {
  LayoutDashboard,
  CalendarClock,
  TrendingUp,
  FolderArchive,
  Settings,
  Sun,
  Moon,
  ShieldCheck,
  Share2,
  ExternalLink,
  Sparkles,
  Download,
  Zap,
} from 'lucide-react';
import { Kind } from '../types';
import { PWAInstallButton } from './PWAInstallButton';
import { usePWAInstall } from '../hooks/usePWAInstall';

export type TabType = 'home' | 'util' | 'due' | 'inv' | 'rec' | 'set';

interface Props {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  dueAttentionCount: number;
  utilityAttentionCount?: number;
  theme: 'system' | 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenShareTrial?: () => void;
  onOpenTrialDocuments?: () => void;
}

export const LogoSvg: React.FC<{ className?: string }> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
    <rect width="32" height="32" rx="9" fill="#0E7C86" />
    <circle cx="16" cy="16" r="9.5" fill="#fff" />
    <path
      d="M12 11.5h8M12 14.5h8M12.5 11.5c3.6 0 3.6 4.5 0 4.5H12l5.5 5"
      fill="none"
      stroke="#0E7C86"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="24.5" cy="7.5" r="3" fill="#F5B15A" />
  </svg>
);

export const Navigation: React.FC<Props> = ({
  currentTab,
  onSelectTab,
  dueAttentionCount,
  utilityAttentionCount = 0,
  theme,
  onToggleTheme,
  onOpenShareTrial,
  onOpenTrialDocuments,
}) => {
  const { isInIframe, openInNewTab } = usePWAInstall();

  const navItems: { id: TabType; label: string; icon: any; badge?: number }[] = [
    { id: 'home', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'util', label: 'Utilities', icon: Zap, badge: utilityAttentionCount },
    { id: 'due', label: 'Due dates', icon: CalendarClock, badge: dueAttentionCount },
    { id: 'inv', label: 'Investments', icon: TrendingUp },
    { id: 'rec', label: 'Records', icon: FolderArchive },
    { id: 'set', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Desktop Fixed Sidebar */}
      <aside
        id="sidebar"
        className="hidden md:flex flex-col w-60 bg-[#0F2A47] dark:bg-[#0A1626] text-[#C9D6E6] p-4 sticky top-0 h-screen z-30 select-none border-r border-[#1B406A]/40"
      >
        <div className="flex items-center gap-3 px-2 py-3 mb-6">
          <LogoSvg className="w-9 h-9 flex-shrink-0" />
          <div className="leading-tight">
            <h1 className="font-bold text-lg text-white tracking-tight">Paisa Pal</h1>
            <p className="text-[11px] text-[#9FB0C6] font-medium">Due Dates & Portfolio</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center justify-between w-full px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#1B406A] text-white shadow-xs font-semibold'
                    : 'text-[#C9D6E6] hover:bg-[#16263E] hover:text-white'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 ${isActive ? 'text-[#3CB7C2]' : 'text-[#8594AA]'}`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && item.badge > 0 ? (
                  <span className="bg-[#B42318] text-white text-[11px] font-bold px-2 py-0.5 rounded-full min-w-5 text-center">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="pt-4 border-t border-[#1B406A]/50 space-y-2.5">
          <div
            className="flex items-center justify-between w-full py-2 px-3 rounded-xl bg-teal-500/15 border border-teal-500/30 text-teal-200 text-xs font-medium"
            title="Demo Mode: Using synthetic test data in compliance with DPDP Act 2023. Real documents not required."
          >
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#3CB7C2]" />
              <span className="font-semibold">Demo Mode</span>
            </div>
            <span className="text-[10px] bg-teal-900/60 text-teal-300 px-1.5 py-0.5 rounded font-mono font-bold">DPDP Safe</span>
          </div>

          {isInIframe && (
            <button
              onClick={openInNewTab}
              className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#0E7C86] to-[#0B3B66] hover:brightness-110 text-white text-xs font-semibold transition shadow-sm"
              title="Open Paisa Pal directly in a full desktop browser window"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open in New Tab</span>
            </button>
          )}



          {onOpenShareTrial && (
            <button
              onClick={onOpenShareTrial}
              className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-xl bg-[#1B406A] hover:bg-[#234f82] text-white text-xs font-semibold transition shadow-xs"
              title="Send Paisa Pal direct link for trial on phone or desktop"
            >
              <Share2 className="w-3.5 h-3.5 text-[#3CB7C2]" />
              <span>Send for Trial</span>
            </button>
          )}

          <PWAInstallButton variant="nav" />

          <div className="flex items-center justify-between px-1 text-xs text-[#9FB0C6]">
            <button
              onClick={onToggleTheme}
              className="flex items-center gap-1.5 py-1 px-2 rounded-lg hover:bg-[#1B406A] transition text-xs"
              title="Toggle light / dark appearance"
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-amber-300" />
                  <span>Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-blue-200" />
                  <span>Dark</span>
                </>
              )}
            </button>
            <div className="flex items-center gap-1 opacity-80" title="All data stored in this browser on this computer">
              <ShieldCheck className="w-3.5 h-3.5 text-[#3CB7C2]" />
              <span>Offline & Private</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Top Header */}
      <header
        id="mobile-header"
        className="md:hidden flex items-center justify-between bg-[#0F2A47] dark:bg-[#0A1626] text-white px-4 py-3 sticky top-0 z-30 shadow-xs border-b border-[#1B406A]/40 safe-top"
      >
        <div className="flex items-center gap-2.5">
          <LogoSvg className="w-7 h-7" />
          <span className="font-bold text-base tracking-tight">Paisa Pal</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] bg-teal-500/20 text-teal-300 px-2 py-1 rounded-md font-semibold border border-teal-500/30">
            Demo Mode
          </span>
          {isInIframe && (
            <button
              onClick={openInNewTab}
              className="flex items-center gap-1 py-1.5 px-2 rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-medium transition"
              title="Open Standalone Tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="text-[11px] hidden sm:inline">New Tab</span>
            </button>
          )}
          {onOpenShareTrial && (
            <button
              onClick={onOpenShareTrial}
              className="flex items-center gap-1 py-1.5 px-2.5 rounded-lg bg-[#1B406A] hover:bg-[#234f82] text-white text-xs font-medium transition"
              title="Send for Trial"
            >
              <Share2 className="w-3.5 h-3.5 text-[#3CB7C2]" />
              <span className="text-[11px]">Trial</span>
            </button>
          )}
          <PWAInstallButton variant="compact" />
          <button
            onClick={onToggleTheme}
            className="p-1.5 rounded-lg text-[#C9D6E6] hover:bg-[#1B406A]"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-300" />
            ) : (
              <Moon className="w-4 h-4 text-blue-200" />
            )}
          </button>
        </div>
      </header>

      {/* Mobile Fixed Bottom Navigation */}
      <nav
        id="bottom-nav"
        className="md:hidden fixed bottom-0 left-0 right-0 bg-[#0F2A47] dark:bg-[#0A1626] border-t border-[#1B406A]/60 flex items-center justify-around px-2 py-1.5 z-40 safe-bottom shadow-lg"
        aria-label="Mobile Navigation"
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`flex flex-col items-center justify-center flex-1 py-1.5 px-1 min-h-[48px] relative transition-colors ${
                isActive ? 'text-[#3CB7C2] font-semibold' : 'text-[#9FB0C6] hover:text-white'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.2]' : 'stroke-[1.8]'}`} />
                {item.badge && item.badge > 0 ? (
                  <span className="absolute -top-1.5 -right-2 bg-[#B42318] text-white text-[9px] font-bold px-1.5 py-0.2 rounded-full min-w-4 text-center">
                    {item.badge}
                  </span>
                ) : null}
              </div>
              <span className="text-[10px] mt-1 tracking-tight truncate max-w-[64px]">
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>
    </>
  );
};
