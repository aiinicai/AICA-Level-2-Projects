import React from 'react';
import { 
  FileText, 
  Scale, 
  Landmark, 
  Percent, 
  AlertOctagon,
  CheckCircle2
} from 'lucide-react';
import { AuditModule } from '../types';

interface NavigationProps {
  activeModule: AuditModule;
  onSelectModule: (module: AuditModule) => void;
  moduleRisks?: Record<AuditModule, { count: number; level: 'compliant' | 'warning' | 'critical' }>;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeModule,
  onSelectModule,
  moduleRisks,
}) => {
  const modules = [
    {
      id: 'invoice' as AuditModule,
      step: '01',
      title: 'Invoice Review',
      subtitle: 'Arithmetic & Mandates',
      icon: FileText,
    },
    {
      id: 'gst' as AuditModule,
      step: '02',
      title: 'GST Compliance',
      subtitle: 'PoS & ITC Rules',
      icon: Scale,
    },
    {
      id: 'tds' as AuditModule,
      step: '03',
      title: 'TDS Analyser',
      subtitle: 'Sec 194C / 194J / 194H',
      icon: Percent,
    },
    {
      id: 'bank' as AuditModule,
      step: '04',
      title: 'Bank Statement',
      subtitle: 'SFT & Cash >₹50k',
      icon: Landmark,
    }
  ];

  return (
    <nav className="bg-white border-b border-slate-200 shadow-xs shrink-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2 sm:gap-6 md:gap-8 h-12 overflow-x-auto no-scrollbar">
          {modules.map((mod) => {
            const isActive = activeModule === mod.id;
            const riskInfo = moduleRisks?.[mod.id];
            const isCritical = riskInfo?.level === 'critical';
            const isCompliant = riskInfo?.level === 'compliant';
            const isWarning = riskInfo?.level === 'warning';

            return (
              <button
                key={mod.id}
                id={`nav-module-${mod.id}`}
                onClick={() => onSelectModule(mod.id)}
                className={`h-full border-b-2 px-1.5 sm:px-3 flex items-center gap-2 text-xs sm:text-sm whitespace-nowrap transition-all ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600 font-semibold'
                    : 'border-transparent text-slate-500 hover:text-slate-800 font-medium'
                }`}
              >
                <span className={`text-[11px] font-bold ${isActive ? 'text-indigo-600 opacity-90' : 'text-slate-400 opacity-70'}`}>
                  {mod.step}
                </span>
                <span>{mod.title}</span>

                {isCritical && (
                  <span className="flex items-center" title="Critical Issues / Blocked Credit Detected">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse shadow-xs" />
                  </span>
                )}
                {isWarning && (
                  <span className="flex items-center" title="Audit Review Required">
                    <span className="w-2 h-2 rounded-full bg-amber-500 shadow-xs" />
                  </span>
                )}
                {isCompliant && (
                  <span className="flex items-center" title="100% Compliant & Reconciled">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-200 shadow-xs" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

