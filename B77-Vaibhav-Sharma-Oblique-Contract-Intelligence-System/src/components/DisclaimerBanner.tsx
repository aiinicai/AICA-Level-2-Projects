import React, { useState } from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 text-amber-900 px-4 py-2 text-xs">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <p className="text-slate-700">
            <span className="font-semibold text-amber-900">CA Professional Notice:</span> This application provides AI-assisted identification of potential accounting, tax, compliance, and audit considerations. It does not constitute legal, tax or accounting advice and does not replace professional judgment. Statutory provisions (Ind AS, Income Tax Act, CGST Act, MSMED Act, Companies Act) should be independently verified.
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-slate-400 hover:text-slate-600 ml-4 shrink-0"
          title="Dismiss notice"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
