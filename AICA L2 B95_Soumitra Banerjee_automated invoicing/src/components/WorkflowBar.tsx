import React from 'react';
import { 
  Users, 
  FileSpreadsheet, 
  Calculator, 
  Mail, 
  CheckCircle2, 
  FileText, 
  History,
  ChevronRight
} from 'lucide-react';

interface WorkflowBarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const WorkflowBar: React.FC<WorkflowBarProps> = ({ currentTab, onSelectTab }) => {
  const steps = [
    { id: 'clients', label: '1. Clients Master', icon: Users },
    { id: 'delivery-logs', label: '2. Upload Delivery Log', icon: FileSpreadsheet },
    { id: 'billing', label: '3. Quarterly Billing', icon: Calculator },
    { id: 'billing', label: '4. Send Confirmation', icon: Mail },
    { id: 'confirmations', label: '5. Simulate Client Reply', icon: CheckCircle2 },
    { id: 'invoices', label: '6. Auto Invoice & Email', icon: FileText },
    { id: 'audit', label: '7. Audit Trail', icon: History },
  ];

  return (
    <div className="bg-white border-b border-slate-200 px-6 py-2.5 overflow-x-auto shadow-xs">
      <div className="flex items-center space-x-1 min-w-max text-xs">
        <span className="font-semibold text-slate-500 uppercase tracking-wider mr-2 text-[10px]">
          End-to-End Workflow:
        </span>
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isActive = currentTab === step.id;
          return (
            <React.Fragment key={idx}>
              <button
                onClick={() => onSelectTab(step.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{step.label}</span>
              </button>
              {idx < steps.length - 1 && (
                <ChevronRight className="w-3 h-3 text-slate-300" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
