import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto bg-white border-t border-slate-200 px-4 sm:px-8 py-3.5 flex flex-col sm:flex-row justify-between items-center text-[11px] text-slate-500 gap-2">
      <div className="flex items-center gap-1.5 flex-wrap">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
        <span>
          <strong className="text-slate-800 font-bold">CA VerifyAI</strong> | Developed by{' '}
          <strong className="text-slate-800 font-bold">CA Rajesh Kumar Pattanaik</strong> | Bhubaneswar, Odisha |{' '}
          <span className="text-slate-600 font-medium">AICA Level 2 Capstone Project</span>
        </span>
      </div>
      <div className="text-slate-500 font-medium">
        <span className="italic">“Verify Before You Rely.”</span>
      </div>
    </footer>
  );
};
