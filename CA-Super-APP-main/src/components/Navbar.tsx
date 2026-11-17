import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Building2, 
  CheckSquare, 
  Calendar as CalendarIcon, 
  Globe2, 
  KeyRound, 
  FileSpreadsheet, 
  Sprout, 
  Wrench, 
  UserCheck, 
  Users, 
  LogOut, 
  Settings2,
  Menu,
  X,
  Sparkles
} from 'lucide-react';

interface NavbarProps {
  onOpenResetCreds: () => void;
  onOpenUdin: () => void;
  onOpenAuthModal: () => void;
  onSelectTab?: (tabId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenResetCreds, onOpenUdin, onOpenAuthModal, onSelectTab }) => {
  const { auth, logout } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'calendar', label: 'Calendar', icon: CalendarIcon, badge: auth.role === 'admin' ? '15-Day' : '7-Day' },
    { id: 'portals', label: 'Govt Portals', icon: Globe2 },
    { id: 'udin', label: 'UDIN ICAI', icon: KeyRound, highlight: true },
    { id: 'msme', label: 'MSME Dossier', icon: FileSpreadsheet, aiBadge: true },
    { id: 'aif', label: 'AIF Agri Fund', icon: Sprout, aiBadge: true },
    { id: 'tools', label: 'PDF Suite', icon: Wrench }
  ];

  const handleTabClick = (tabId: string) => {
    setMobileMenuOpen(false);
    if (tabId === 'udin') {
      onOpenUdin();
    } else if (onSelectTab) {
      onSelectTab(tabId);
    }
  };

  return (
    <>
      {/* Top Banner & Header (Dark Yellow with Light Yellowish accents) */}
      <header className="sticky top-0 z-40 bg-amber-50/95 backdrop-blur-md border-b border-amber-200/90 shadow-xs">
        {/* Top Info Strip in Dark Yellow Gradient */}
        <div className="bg-gradient-to-r from-amber-800 via-amber-700 to-yellow-800 text-amber-50 text-xs py-1 px-4 border-b border-amber-900/20">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-2 font-medium text-[11px] text-amber-100">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              <span>Chartered Accountants Office • Punjab Compliance &amp; Central Taxes Live</span>
            </div>
            <div className="hidden sm:flex items-center space-x-4 text-amber-100/90 font-medium text-[11px]">
              <span className="cursor-pointer hover:text-white hover:underline transition-colors" onClick={onOpenUdin}>
                UDIN Partner Portal (2 Partners)
              </span>
              <span>•</span>
              <span>Recovery Email: rishugarg006@gmail.com</span>
            </div>
          </div>
        </div>

        {/* Main Header Bar */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Logo and Firm Branding */}
            <div 
              className="flex items-center space-x-2.5 cursor-pointer group" 
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-700 to-yellow-700 flex items-center justify-center text-amber-50 shadow-xs group-hover:scale-105 transition-transform border border-amber-600/40">
                <Building2 className="w-5 h-5 text-amber-100" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="font-black text-amber-950 tracking-tight text-sm sm:text-base leading-tight">
                    RISHU GARG &amp; ASSOCIATES
                  </h1>
                  <span className="hidden md:inline-flex text-[9px] font-black bg-amber-100 text-amber-900 px-1.5 py-0.2 rounded border border-amber-300">
                    FCA • DISA
                  </span>
                </div>
                <p className="text-[10px] text-amber-800/80 font-medium">Chartered Accountants • Bishnandi Bazaar, Jaitu, Punjab</p>
              </div>
            </div>

            {/* Desktop Navigation Quick Buttons in Warm Amber */}
            <nav className="hidden lg:flex items-center space-x-1">
              {navItems.map(item => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleTabClick(item.id)}
                    className="relative flex items-center space-x-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-amber-900 hover:text-amber-950 hover:bg-amber-100/80 border border-transparent hover:border-amber-300/80 transition-all duration-150"
                  >
                    <Icon className="w-3.5 h-3.5 text-amber-700" />
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="text-[9px] font-bold bg-amber-100 text-amber-900 px-1 py-0.2 rounded border border-amber-300/80">
                        {item.badge}
                      </span>
                    )}
                    {item.aiBadge && (
                      <span className="flex items-center space-x-0.5 text-[8px] font-black bg-amber-700 text-amber-50 px-1 rounded">
                        <Sparkles className="w-2 h-2 text-amber-200" />
                        <span>AI</span>
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>

            {/* User Session & Role Controls in Warm Amber */}
            <div className="flex items-center space-x-2">
              {auth.role ? (
                <div className="flex items-center space-x-1.5">
                  <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border border-amber-300 bg-amber-100/70 text-xs font-bold text-amber-950 shadow-2xs">
                    {auth.role === 'admin' ? (
                      <UserCheck className="w-3.5 h-3.5 text-amber-700" />
                    ) : (
                      <Users className="w-3.5 h-3.5 text-amber-700" />
                    )}
                    <div className="text-left hidden sm:block">
                      <div className="leading-tight text-[11px] font-black text-amber-950">{auth.role === 'admin' ? 'ADMIN' : 'STAFF'}</div>
                    </div>
                  </div>

                  {auth.role === 'admin' && (
                    <button
                      onClick={onOpenResetCreds}
                      title="Reset Admin & Staff Passwords"
                      className="p-1.5 rounded-lg text-amber-800 hover:text-amber-950 hover:bg-amber-100/80 border border-amber-300 transition-colors"
                    >
                      <Settings2 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    onClick={logout}
                    title="Switch Login / Logout"
                    className="flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-bold text-amber-900 hover:bg-red-50 hover:text-red-700 border border-amber-300 transition-colors"
                  >
                    <LogOut className="w-3 h-3" />
                    <span className="hidden sm:inline text-[11px]">Switch</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={onOpenAuthModal}
                  className="px-3.5 py-1.5 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-amber-50 rounded-lg text-xs font-bold shadow-xs transition-all border border-amber-600/40"
                >
                  Sign In
                </button>
              )}

              {/* Mobile menu button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden p-1.5 rounded-lg text-amber-900 hover:bg-amber-100 border border-amber-300"
              >
                {mobileMenuOpen ? <X className="w-4 h-4 text-amber-900" /> : <Menu className="w-4 h-4 text-amber-900" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-amber-50 border-b border-amber-200 px-4 pt-2 pb-4 space-y-1 shadow-md">
            <div className="text-xs font-bold text-amber-900/70 uppercase tracking-wider px-2 py-1">
              Office Tabs
            </div>
            {navItems.map(item => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabClick(item.id)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold text-amber-950 hover:bg-amber-100/80 transition-colors"
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className="w-4 h-4 text-amber-700" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] text-amber-900 bg-amber-100 px-1.5 py-0.2 rounded font-bold border border-amber-300">{item.badge}</span>
                  )}
                </button>
              );
            })}

            {auth.role === 'admin' && (
              <div className="pt-2 border-t border-amber-200/80">
                <button
                  onClick={() => {
                    onOpenResetCreds();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-semibold text-amber-950 hover:bg-amber-100"
                >
                  <Settings2 className="w-4 h-4 text-amber-700" />
                  <span>Admin Credentials &amp; Passwords</span>
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Android Mobile Bottom Navigation Bar in Dark Yellow & Light Yellowish */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-amber-50/95 backdrop-blur-md border-t border-amber-200/90 px-2 py-1 shadow-lg text-amber-900 font-bold">
        <div className="grid grid-cols-5 gap-1">
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="flex flex-col items-center justify-center py-1 rounded-lg text-amber-900 font-bold hover:text-amber-950"
          >
            <CheckSquare className="w-4 h-4 text-amber-700" />
            <span className="text-[9px] mt-0.5">To-Do</span>
          </button>

          <button
            onClick={() => handleTabClick('calendar')}
            className="flex flex-col items-center justify-center py-1 rounded-lg text-amber-900 font-bold hover:text-amber-950"
          >
            <CalendarIcon className="w-4 h-4 text-amber-700" />
            <span className="text-[9px] mt-0.5">Calendar</span>
          </button>

          <button
            onClick={onOpenUdin}
            className="flex flex-col items-center justify-center py-1 rounded-lg text-amber-900 font-bold hover:text-amber-950"
          >
            <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-amber-700 to-yellow-700 text-amber-50 flex items-center justify-center shadow-2xs">
              <KeyRound className="w-3 h-3 text-amber-100" />
            </div>
            <span className="text-[9px] mt-0.5">UDIN</span>
          </button>

          <button
            onClick={() => handleTabClick('msme')}
            className="flex flex-col items-center justify-center py-1 rounded-lg text-amber-900 font-bold hover:text-amber-950"
          >
            <FileSpreadsheet className="w-4 h-4 text-amber-700" />
            <span className="text-[9px] mt-0.5">MSME</span>
          </button>

          <button
            onClick={() => handleTabClick('tools')}
            className="flex flex-col items-center justify-center py-1 rounded-lg text-amber-900 font-bold hover:text-amber-950"
          >
            <Wrench className="w-4 h-4 text-amber-700" />
            <span className="text-[9px] mt-0.5">PDF Tools</span>
          </button>
        </div>
      </nav>
    </>
  );
};
