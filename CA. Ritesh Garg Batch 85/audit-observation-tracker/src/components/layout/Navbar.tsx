import React from 'react';
import { 
  Building2, 
  Search, 
  PlusCircle, 
  FileSpreadsheet, 
  ShieldCheck, 
  Briefcase,
  AlertTriangle,
  LayoutDashboard,
  FileText,
  CheckSquare,
  Settings
} from 'lucide-react';
import { FirmProfile, Engagement, Observation } from '../../types/audit';
import { NavView } from './Sidebar';

interface NavbarProps {
  firmProfile: FirmProfile;
  engagements?: Engagement[];
  observations?: Observation[];
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  onOpenNewObservation: () => void;
  onOpenNewEngagement: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  firmProfile,
  engagements = [],
  observations = [],
  currentView,
  onNavigate,
  onOpenNewObservation,
  onOpenNewEngagement,
}) => {
  const obsList = observations || [];
  const openCriticalCount = obsList.filter(
    o => (o.severity === 'Critical' || o.severity === 'High') && o.status !== 'Closed' && o.status !== 'Rectified'
  ).length;

  return (
    <header id="main-header" className="bg-white border-b border-stone-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Brand & Firm Logo */}
          <div 
            className="flex items-center gap-3 shrink-0 cursor-pointer"
            onClick={() => onNavigate('dashboard')}
          >
            <div className="w-10 h-10 rounded-xl bg-[#5A5A40] flex items-center justify-center text-white shadow-xs">
              <ShieldCheck className="w-6 h-6 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-stone-800 text-base leading-tight tracking-tight">
                  AuditTracker
                </span>
                <span className="bg-[#F5F2ED] text-stone-700 text-[11px] px-2 py-0.5 rounded-full font-medium border border-[#DED9D0] hidden sm:inline-block">
                  CA FIRM & CO.
                </span>
              </div>
              <p className="text-xs text-stone-500 font-medium truncate max-w-[220px] sm:max-w-xs">
                {firmProfile?.firmName || 'R. K. Garg & Associates'} • FRN {firmProfile?.frn || '014285N'}
              </p>
            </div>
          </div>

          {/* Quick Nav Links for small screens where sidebar is hidden */}
          <div className="flex md:hidden items-center gap-1">
            <button
              onClick={() => onNavigate('dashboard')}
              className={`p-2 rounded-lg ${currentView === 'dashboard' ? 'bg-[#5A5A40] text-white' : 'text-stone-600 hover:bg-stone-100'}`}
              title="Dashboard"
            >
              <LayoutDashboard className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('engagements')}
              className={`p-2 rounded-lg ${currentView === 'engagements' ? 'bg-[#5A5A40] text-white' : 'text-stone-600 hover:bg-stone-100'}`}
              title="Engagements"
            >
              <Briefcase className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('observations')}
              className={`p-2 rounded-lg ${currentView === 'observations' ? 'bg-[#5A5A40] text-white' : 'text-stone-600 hover:bg-stone-100'}`}
              title="Observations"
            >
              <FileText className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('checklists')}
              className={`p-2 rounded-lg ${currentView === 'checklists' ? 'bg-[#5A5A40] text-white' : 'text-stone-600 hover:bg-stone-100'}`}
              title="Checklists"
            >
              <CheckSquare className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('reports')}
              className={`p-2 rounded-lg ${currentView === 'reports' ? 'bg-[#5A5A40] text-white' : 'text-stone-600 hover:bg-stone-100'}`}
              title="Reports"
            >
              <FileSpreadsheet className="w-4 h-4" />
            </button>
          </div>

          {/* Action Hub & Quick Stats */}
          <div className="flex items-center gap-2 shrink-0">
            {openCriticalCount > 0 && (
              <button
                id="header-critical-alert-btn"
                onClick={() => onNavigate('observations')}
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold hover:bg-rose-100 transition-colors"
                title={`${openCriticalCount} Critical/High Risk observations open`}
              >
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                <span>{openCriticalCount} High Risk Open</span>
              </button>
            )}

            <button
              id="header-new-engagement-btn"
              onClick={onOpenNewEngagement}
              className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-700 hover:bg-[#F5F2ED] text-xs font-semibold transition-colors"
            >
              <Briefcase className="w-3.5 h-3.5 text-stone-600" />
              <span>+ Engagement</span>
            </button>

            <button
              id="header-new-observation-btn"
              onClick={onOpenNewObservation}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-all"
            >
              <PlusCircle className="w-4 h-4 text-amber-300" />
              <span>+ New Observation</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
