import React from 'react';
import {
  SlidersHorizontal,
  FileSpreadsheet,
  CheckSquare,
  TrendingUp,
  Scale,
  ListOrdered,
  CheckCircle,
  BarChart3,
  Calculator,
  FileText,
} from 'lucide-react';
import { ActiveTab, ReconciliationReport } from '../types/accounting';

interface WorkflowStepperProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  reconciliation: ReconciliationReport;
  schedulesCount: number;
}

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({
  activeTab,
  onTabChange,
  reconciliation,
  schedulesCount,
}) => {
  const steps: { id: ActiveTab; label: string; subLabel: string; icon: React.FC<any>; badge?: string | number }[] = [
    {
      id: 'control',
      label: '1. CONTROL SHEET',
      subLabel: 'Entity & BS Heads',
      icon: SlidersHorizontal,
    },
    {
      id: 'trial-balance',
      label: '2. TRIAL BALANCE',
      subLabel: 'Import & Raw TB',
      icon: FileSpreadsheet,
    },
    {
      id: 'classification',
      label: '3. CLASSIFICATION',
      subLabel: 'Mapping Studio',
      icon: CheckSquare,
      badge: (reconciliation?.unclassifiedLedgersCount ?? 0) > 0 ? reconciliation?.unclassifiedLedgersCount : undefined,
    },
    {
      id: 'depreciation',
      label: '4. DEPRECIATION',
      subLabel: 'Asset Schedule',
      icon: Calculator,
    },
    {
      id: 'profit-and-loss',
      label: '5. PROFIT & LOSS',
      subLabel: 'Trading & P&L',
      icon: TrendingUp,
    },
    {
      id: 'balance-sheet',
      label: '6. BALANCE SHEET',
      subLabel: 'Main Statement',
      icon: Scale,
    },
    {
      id: 'schedules',
      label: '7. SCHEDULES',
      subLabel: `${schedulesCount} Worksheets`,
      icon: ListOrdered,
    },
    {
      id: 'notes',
      label: '8. NOTES TO ACCOUNTS',
      subLabel: 'Standard Disclosures',
      icon: FileText,
    },
    {
      id: 'reconciliation',
      label: '9. RECONCILIATION',
      subLabel: 'Audit & Balances',
      icon: CheckCircle,
      badge: reconciliation?.isBalanceSheetBalanced ? '✓' : '!',
    },
  ];

  return (
    <nav className="bg-[#ECEAE5] border-b border-[#141414]/20 sticky top-14 z-30" aria-label="Workflow Tabs" id="workflow-tabs-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex overflow-x-auto no-scrollbar space-x-1 py-1.5">
          {steps.map(step => {
            const Icon = step.icon;
            const isActive = activeTab === step.id;

            return (
              <button
                key={step.id}
                onClick={() => onTabChange(step.id)}
                id={`tab-${step.id}`}
                className={`flex items-center space-x-2 px-3 py-1.5 text-left transition-all whitespace-nowrap shrink-0 border ${
                  isActive
                    ? 'bg-[#141414] text-[#E4E3E0] border-[#141414] font-bold shadow-xs'
                    : 'bg-[#F4F3F0] border-[#141414]/20 text-[#5E5E5E] hover:bg-[#E4E3E0] hover:text-[#141414]'
                }`}
              >
                <div
                  className={`w-5 h-5 flex items-center justify-center transition-colors ${
                    isActive ? 'bg-[#E4E3E0] text-[#141414]' : 'bg-[#E4E3E0] text-[#5E5E5E]'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-[11px] font-mono leading-tight">{step.label}</span>
                    {step.badge !== undefined && (
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-0.2 border ${
                          step.badge === '✓'
                            ? isActive
                              ? 'bg-[#1b2a1e] text-[#4ade80] border-[#4ade80]/40'
                              : 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                            : isActive
                            ? 'bg-[#2f1f14] text-[#fbbf24] border-[#fbbf24]/40'
                            : 'bg-[#fef3c7] text-[#92400e] border-[#fde68a]'
                        }`}
                      >
                        {step.badge}
                      </span>
                    )}
                  </div>
                  <span className={`text-[9.5px] font-mono font-normal leading-none ${isActive ? 'text-[#A3A29E]' : 'text-[#8E8C85]'}`}>
                    {step.subLabel}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};
