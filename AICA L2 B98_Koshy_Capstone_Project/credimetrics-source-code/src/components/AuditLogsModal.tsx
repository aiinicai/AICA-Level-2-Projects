import React from 'react';
import { X, History, Shield, Clock, UserCheck } from 'lucide-react';
import { AuditLog } from '../types/financial';

interface AuditLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: AuditLog[];
}

export const AuditLogsModal: React.FC<AuditLogsModalProps> = ({
  isOpen,
  onClose,
  logs
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden my-8">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-850">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-purple-600/20 text-purple-400 rounded-lg">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">System Audit Trail &amp; Access Log</h3>
              <p className="text-xs text-slate-400">Institutional tracking of financial assessments and downloads</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Logs list */}
        <div className="p-5 max-h-96 overflow-y-auto divide-y divide-slate-800">
          {logs.map(log => (
            <div key={log.id} className="py-3 flex items-start space-x-3 text-xs">
              <div className="mt-0.5 p-1.5 rounded-lg bg-slate-800 text-slate-400 shrink-0">
                <Clock className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-bold text-white">{log.action}</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                      {log.userRole}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono shrink-0">{log.timestamp}</span>
                </div>
                <p className="text-slate-300 text-[11px] mt-1 leading-relaxed">{log.details}</p>
                <div className="text-[10px] text-slate-400 mt-1">
                  Actor: <strong className="text-slate-300">{log.userName}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 bg-slate-850 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
