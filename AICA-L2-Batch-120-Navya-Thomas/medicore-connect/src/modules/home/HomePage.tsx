import React, { useState, useRef, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ShoppingCart,
  Boxes,
  FileSpreadsheet,
  Receipt,
  BookOpen,
  ArrowLeftRight,
  Landmark,
  Building2,
  BarChart3,
  Wrench,
  Clock,
  AlertCircle,
  FileCheck,
  CheckCircle2,
  Plus,
  ShieldCheck,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { getActiveUser } from '../../core/auth';
import { getDb, subscribeToDb } from '../../core/storage';
import { NAV_MODULES } from '../../components/Navigator';
import { formatAED } from '../../core/currency';

interface HomePageProps {
  onNavigate: (route: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const [currentUser, setCurrentUser] = useState(getActiveUser());
  const [activeTabId, setActiveTabId] = useState('payables');
  const [dbState, setDbState] = useState(getDb());
  const tabStripRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleUserChange = () => setCurrentUser(getActiveUser());
    window.addEventListener('medicore-user-changed', handleUserChange);
    const unsub = subscribeToDb(() => setDbState(getDb()));

    return () => {
      window.removeEventListener('medicore-user-changed', handleUserChange);
      unsub();
    };
  }, []);

  // Time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const scrollTabStrip = (direction: 'left' | 'right') => {
    if (tabStripRef.current) {
      const offset = direction === 'left' ? -250 : 250;
      tabStripRef.current.scrollBy({ left: offset, behavior: 'smooth' });
    }
  };

  // Find active module
  const currentModule = NAV_MODULES.find((m) => m.id === activeTabId) || NAV_MODULES[2];

  // Things to Finish Live Counts
  const pendingInvoices = dbState.apInvoices.filter((i) => i.status === 'Pending Approval').length;
  const pendingAR = dbState.arTransactions.filter((i) => i.status === 'Pending Approval').length;
  const incompleteFA = dbState.assetSourceLines.filter((l) => l.status === 'Incomplete' || l.status === 'Exception').length;
  const unreconciledBankLines = dbState.bankStatements.reduce(
    (acc, st) => acc + st.lines.filter((l) => !l.isReconciled).length,
    0
  );
  const pendingIC = dbState.icTransactions.filter((i) => i.status === 'Pending Approval').length;

  return (
    <div className="flex-1 flex flex-col bg-gray-50 overflow-y-auto">
      {/* Plum Gradient Hero Section */}
      <div className="relative bg-gradient-to-r from-[#3F1D5C] via-[#5B2C83] to-[#4a236c] text-white pt-8 pb-14 px-6 sm:px-10 shadow-md overflow-hidden">
        {/* Subtle patterned background decoration */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#EDE4F5_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
        <div className="absolute -right-10 -bottom-10 w-96 h-96 rounded-full bg-amber-400/10 blur-3xl pointer-events-none" />

        <div className="max-w-7xl mx-auto relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-amber-300 text-xs font-semibold uppercase tracking-widest mb-1.5">
              <Sparkles className="w-4 h-4" />
              <span>Meridian Healthcare Group — Financials & Supply Chain</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {getGreeting()}, {currentUser.name}
            </h1>
            <p className="text-plum-200 text-xs sm:text-sm mt-1 max-w-2xl">
              Connected across 5 Hospitals, 5 Clinics, and 5 Pharmacies. Review pending approvals, create transactions, and manage unified IFRS financials.
            </p>
          </div>

          {/* Quick Stats Pill */}
          <div className="bg-white/10 backdrop-blur-md rounded-xl p-3 border border-white/15 flex items-center space-x-4 self-start md:self-auto">
            <div>
              <span className="text-[10px] text-plum-200 block uppercase font-medium">Fiscal Period</span>
              <span className="font-bold text-white text-sm">Oct-26 (Open)</span>
            </div>
            <div className="h-8 w-px bg-white/20" />
            <div>
              <span className="text-[10px] text-plum-200 block uppercase font-medium">Approval Limit</span>
              <span className="font-bold text-amber-300 text-sm">
                {currentUser.approvalLimitAED ? `AED ${currentUser.approvalLimitAED.toLocaleString()}` : 'Unlimited'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Horizontally Scrollable Tab Strip (overhanging hero) */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-8 -mt-7 relative z-20">
        <div className="bg-white rounded-xl shadow-lg border border-gray-200/80 p-1 flex items-center">
          <button
            onClick={() => scrollTabStrip('left')}
            className="p-2 hover:bg-plum-50 rounded-lg text-gray-500 hover:text-[#5B2C83] shrink-0 transition-colors"
            title="Scroll left"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div
            ref={tabStripRef}
            className="flex-1 flex space-x-1 overflow-x-auto no-scrollbar scroll-smooth px-1 py-1"
          >
            {NAV_MODULES.map((mod) => {
              const isActive = activeTabId === mod.id;
              const IconComp = mod.icon;
              return (
                <button
                  key={mod.id}
                  onClick={() => setActiveTabId(mod.id)}
                  className={`px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center space-x-2 shrink-0 ${
                    isActive
                      ? 'bg-[#5B2C83] text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <IconComp className={`w-4 h-4 ${isActive ? 'text-amber-300' : 'text-gray-500'}`} />
                  <span>{mod.title}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => scrollTabStrip('right')}
            className="p-2 hover:bg-plum-50 rounded-lg text-gray-500 hover:text-[#5B2C83] shrink-0 transition-colors"
            title="Scroll right"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Module Content: Quick Actions & Apps */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: QUICK ACTIONS (35%) */}
          <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 shadow-xs p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
                <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  <span>Quick Actions</span>
                </h2>
                <span className="text-[11px] text-gray-400 font-medium">{currentModule.title}</span>
              </div>

              <div className="space-y-1.5">
                {currentModule.quickActions.map((qa, idx) => (
                  <button
                    key={idx}
                    onClick={() => onNavigate(qa.route)}
                    className="w-full text-left p-2.5 rounded-lg hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] transition-colors flex items-center justify-between group border border-transparent hover:border-plum-200"
                  >
                    <span className="text-xs font-semibold group-hover:translate-x-0.5 transition-transform">
                      {qa.title}
                    </span>
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-[#5B2C83] transition-colors" />
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-gray-100 text-[11px] text-gray-500 flex items-center justify-between">
              <span>Standard Oracle Fusion Layout</span>
              <button
                onClick={() => onNavigate(currentModule.apps[0]?.route || '#/')}
                className="text-[#5B2C83] font-semibold hover:underline"
              >
                Open Work Area &rarr;
              </button>
            </div>
          </div>

          {/* Right Panel: APPS Frosted Square Tiles (65%) */}
          <div className="lg:col-span-8 bg-white rounded-xl border border-gray-200 shadow-xs p-5">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                <span>Applications</span>
              </h2>
              <span className="text-[11px] text-gray-400">{currentModule.apps.length} apps available</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {currentModule.apps.map((app, idx) => {
                const IconComp = currentModule.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => onNavigate(app.route)}
                    className="p-4 rounded-xl border border-gray-200 bg-gradient-to-b from-white to-gray-50 hover:to-plum-50/70 hover:border-plum-300 transition-all duration-150 flex flex-col items-center text-center group shadow-xs hover:shadow-md cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-xl bg-plum-100 text-[#5B2C83] group-hover:bg-[#5B2C83] group-hover:text-white flex items-center justify-center mb-2.5 transition-colors shadow-inner">
                      <IconComp className="w-6 h-6" />
                    </div>
                    <span className="font-semibold text-xs text-gray-800 group-hover:text-[#5B2C83] line-clamp-2">
                      {app.title}
                    </span>
                    {app.description && (
                      <span className="text-[10px] text-gray-500 mt-1 line-clamp-2">
                        {app.description}
                      </span>
                    )}
                  </button>
                );
              })}

              {/* + Add App Tile */}
              <button
                onClick={() => onNavigate('#/tools/administration')}
                title="Add App to Favorites"
                className="p-4 rounded-xl border border-dashed border-gray-300 bg-gray-50/50 hover:bg-plum-50 hover:border-plum-300 transition-colors flex flex-col items-center justify-center text-gray-400 hover:text-[#5B2C83]"
              >
                <div className="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center mb-1">
                  <Plus className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-medium">Add App</span>
              </button>
            </div>
          </div>
        </div>

        {/* Things to Finish Section */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-gray-900 flex items-center space-x-2">
              <Clock className="w-5 h-5 text-amber-500" />
              <span>Things to Finish</span>
            </h2>
            <span className="text-xs text-gray-500">Live operational action queue</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {/* Card 1: Pending AP Invoices */}
            <div
              onClick={() => onNavigate('#/payables/invoices')}
              className="bg-white p-4 rounded-xl border border-gray-200 hover:border-plum-300 shadow-xs hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Payables Approvals
                </span>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">
                  {pendingInvoices} Pending
                </span>
              </div>
              <div className="text-xl font-bold text-gray-900 group-hover:text-[#5B2C83] mb-1">
                {pendingInvoices} Invoices
              </div>
              <p className="text-[11px] text-gray-500">
                Supplier invoices awaiting Checker approval and GL posting.
              </p>
              <div className="mt-3 text-[11px] font-semibold text-[#5B2C83] flex items-center space-x-1">
                <span>Review & Approve</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* Card 2: Fixed Assets Additions Queue */}
            <div
              onClick={() => onNavigate('#/fixed-assets/assets')}
              className="bg-white p-4 rounded-xl border border-gray-200 hover:border-plum-300 shadow-xs hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Asset Additions
                </span>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-plum-100 text-[#5B2C83]">
                  {incompleteFA} Lines
                </span>
              </div>
              <div className="text-xl font-bold text-gray-900 group-hover:text-[#5B2C83] mb-1">
                {incompleteFA} Source Lines
              </div>
              <p className="text-[11px] text-gray-500">
                Incomplete & exception capital lines from AP awaiting preparation.
              </p>
              <div className="mt-3 text-[11px] font-semibold text-[#5B2C83] flex items-center space-x-1">
                <span>Prepare & Capitalise</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* Card 3: Bank Reconciliation */}
            <div
              onClick={() => onNavigate('#/cash/bank-reconciliation')}
              className="bg-white p-4 rounded-xl border border-gray-200 hover:border-plum-300 shadow-xs hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Treasury Cash
                </span>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800">
                  {unreconciledBankLines} Unmatched
                </span>
              </div>
              <div className="text-xl font-bold text-gray-900 group-hover:text-[#5B2C83] mb-1">
                Bank Statements
              </div>
              <p className="text-[11px] text-gray-500">
                Auto-match bank statements against payments & receipts.
              </p>
              <div className="mt-3 text-[11px] font-semibold text-[#5B2C83] flex items-center space-x-1">
                <span>Match Transactions</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* Card 4: System Integrity Self-Check */}
            <div
              onClick={() => onNavigate('#/tools/integrity')}
              className="bg-white p-4 rounded-xl border border-gray-200 hover:border-emerald-300 shadow-xs hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Auditing & Controls
                </span>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800">
                  8 / 8 Passing
                </span>
              </div>
              <div className="text-xl font-bold text-emerald-700 group-hover:text-emerald-800 mb-1 flex items-center space-x-1.5">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <span>Integrity Check</span>
              </div>
              <p className="text-[11px] text-gray-500">
                Run automated self-audit of TB, subledger ties, and segregation of duties.
              </p>
              <div className="mt-3 text-[11px] font-semibold text-emerald-700 flex items-center space-x-1">
                <span>Run Full Self-Test</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
