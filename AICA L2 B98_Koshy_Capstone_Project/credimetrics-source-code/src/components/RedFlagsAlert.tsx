import React from 'react';
import { 
  AlertOctagon, 
  AlertTriangle, 
  Info, 
  ShieldAlert, 
  CheckCircle, 
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { RedFlag } from '../types/financial';

interface RedFlagsAlertProps {
  redFlags: RedFlag[];
}

export const RedFlagsAlert: React.FC<RedFlagsAlertProps> = ({ redFlags }) => {
  const [expanded, setExpanded] = React.useState(true);

  if (redFlags.length === 0) {
    return (
      <div className="bg-emerald-950/40 border border-emerald-800/60 rounded-xl p-4 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-emerald-300">No Critical Red Flags Detected</h4>
            <p className="text-slate-300 text-[11px] mt-0.5">
              Financial statements pass institutional screening rules (Current Ratio ≥ 1.0, Quick Ratio ≥ 0.8, Debt-Equity ≤ 3.0, ICR ≥ 1.5).
            </p>
          </div>
        </div>
        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          Clean Bill of Health
        </span>
      </div>
    );
  }

  const criticalCount = redFlags.filter(r => r.severity === 'Critical').length;
  const warningCount = redFlags.filter(r => r.severity === 'Warning').length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className={`p-2 rounded-xl ${criticalCount > 0 ? 'bg-rose-500/15 text-rose-400' : 'bg-amber-500/15 text-amber-400'}`}>
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-white">Red Flag Detection Engine</h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {redFlags.length} Risk Indicators
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated institutional warning alerts triggered by breaches of prudential thresholds.
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-semibold text-slate-400 hover:text-white px-2 py-1 rounded transition"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {expanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
          {redFlags.map(rf => {
            const isCritical = rf.severity === 'Critical';
            return (
              <div 
                key={rf.id}
                className={`p-3.5 rounded-xl border text-xs flex flex-col justify-between transition ${
                  isCritical 
                    ? 'bg-rose-950/30 border-rose-800/60 hover:border-rose-700' 
                    : 'bg-amber-950/20 border-amber-800/50 hover:border-amber-700'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center space-x-1.5">
                      {isCritical ? (
                        <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                      )}
                      <span className={`text-[10px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                        isCritical ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {rf.severity} • {rf.category}
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                      Rule: {rf.threshold}
                    </div>
                  </div>

                  <h4 className="text-xs font-bold text-slate-100">{rf.title}</h4>
                  <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">{rf.description}</p>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <div className="text-slate-400">
                    Actual: <span className="font-bold text-white font-mono">{rf.actualValue}</span>
                  </div>
                  <div className="text-cyan-300 text-[10px] font-medium flex items-center gap-1 text-right max-w-[65%] truncate" title={rf.recommendation}>
                    Action: {rf.recommendation}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
