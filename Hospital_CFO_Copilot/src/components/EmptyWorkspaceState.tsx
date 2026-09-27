import React from 'react';
import { UploadCloud, FileSpreadsheet, ShieldAlert, ArrowRight } from 'lucide-react';

interface EmptyWorkspaceStateProps {
  title: string;
  description: string;
  badge?: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ComponentType<{ className?: string }>;
  suggestedDatasets?: string[];
}

export const EmptyWorkspaceState: React.FC<EmptyWorkspaceStateProps> = ({
  title,
  description,
  badge = 'Awaiting Ingestion',
  actionText = 'Upload Hospital Financial Extracts',
  onAction,
  icon: Icon = FileSpreadsheet,
  suggestedDatasets = [
    'Inpatient Encounters (UHID, Admission/Discharge)',
    'Clinical Services & Order Items',
    'Billing Register & Invoices',
    'TPA / Insurance Claims & Adjudications',
    'Receipts & Collection Register',
  ],
}) => {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 sm:p-12 text-center shadow-xs">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 border border-teal-200 shadow-2xs">
        <Icon className="h-8 w-8" />
      </div>

      <div className="mt-4">
        {badge && (
          <span className="inline-block rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-600 border border-slate-200">
            {badge}
          </span>
        )}
        <h2 className="mt-3 text-lg sm:text-xl font-bold tracking-tight text-slate-900">
          {title}
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-xs sm:text-sm text-slate-500 leading-relaxed">
          {description}
        </p>
      </div>

      {suggestedDatasets && suggestedDatasets.length > 0 && (
        <div className="mx-auto mt-6 max-w-lg rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-left">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Supported Heterogeneous Hospital Extracts
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-600">
            {suggestedDatasets.map((d, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-600 shrink-0" />
                <span className="truncate">{d}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {onAction && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={onAction}
            className="inline-flex items-center gap-2 rounded-xl bg-teal-700 px-5 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-xs hover:bg-teal-800 transition active:scale-98 cursor-pointer ring-1 ring-teal-600/30"
          >
            <UploadCloud className="h-4 w-4" />
            <span>{actionText}</span>
            <ArrowRight className="h-3.5 w-3.5 opacity-70" />
          </button>
        </div>
      )}
    </div>
  );
};
