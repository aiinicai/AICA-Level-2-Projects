import React, { useState, useEffect, useRef } from 'react';
import { Plus, Camera, PenTool, Sparkles } from 'lucide-react';

interface FABProps {
  onScanInvoice: () => void;
  onAddManual: () => void;
}

export const FAB: React.FC<FABProps> = ({ onScanInvoice, onAddManual }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="fixed bottom-6 right-6 z-40 flex flex-col items-end">
      {/* Speed Dial Options */}
      {isOpen && (
        <div className="flex flex-col items-end space-y-3 mb-3 animate-in fade-in slide-in-from-bottom-3 duration-200">
          {/* Option 1: Scan Invoice with AI */}
          <button
            onClick={() => {
              setIsOpen(false);
              onScanInvoice();
            }}
            className="flex items-center gap-3 bg-white dark:bg-slate-900 border border-emerald-300 dark:border-emerald-700/60 rounded-full pl-4 pr-2 py-1.5 shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 transition-all cursor-pointer group"
          >
            <div className="text-right">
              <span className="text-xs font-black text-slate-900 dark:text-white group-hover:text-emerald-600 transition block">
                Scan Invoice / Receipt
              </span>
              <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                AI Vision extraction
              </span>
            </div>
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-500 text-white flex items-center justify-center shadow-md shadow-emerald-500/30">
              <Camera className="w-5 h-5" />
            </div>
          </button>

          {/* Option 2: Add Manually */}
          <button
            onClick={() => {
              setIsOpen(false);
              onAddManual();
            }}
            className="flex items-center gap-3 bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800/60 rounded-full pl-4 pr-2 py-1.5 shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 transition-all cursor-pointer group"
          >
            <div className="text-right">
              <span className="text-xs font-black text-slate-900 dark:text-white group-hover:text-indigo-600 transition block">
                Add Manually
              </span>
              <span className="text-[10px] font-bold text-indigo-500 dark:text-indigo-400">
                Quick entry form
              </span>
            </div>
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/30">
              <PenTool className="w-4 h-4" />
            </div>
          </button>
        </div>
      )}

      {/* Main Floating Trigger Button with Radiant Multicolor Gradient */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Add transaction or scan receipt"
        className={`relative w-14 h-14 rounded-full flex items-center justify-center text-white shadow-xl hover:scale-105 active:scale-95 transition-all duration-300 cursor-pointer border-2 border-white/40 ${
          isOpen
            ? 'bg-slate-900 rotate-45 shadow-slate-900/40'
            : 'bg-gradient-to-tr from-emerald-600 via-teal-500 to-indigo-600 shadow-emerald-500/40 hover:shadow-indigo-500/50'
        }`}
      >
        <Plus className="w-6 h-6 transition-transform" />
      </button>
    </div>
  );
};
