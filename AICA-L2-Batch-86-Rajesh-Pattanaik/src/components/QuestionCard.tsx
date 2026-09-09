import React from 'react';
import { RotateCcw } from 'lucide-react';

interface QuestionCardProps {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({ value, onChange, disabled }) => {
  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-3.5 sm:p-4 flex flex-col justify-between transition-all">
      <div>
        <div className="flex items-center justify-between mb-1.5 flex-wrap gap-1">
          <label
            htmlFor="professional-question-input"
            className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5"
          >
            <span>① Professional Question / Case Facts</span>
          </label>
          {value && !disabled && (
            <button
              type="button"
              onClick={() => onChange('')}
              className="text-[10px] font-semibold text-slate-400 hover:text-slate-700 flex items-center gap-1 cursor-pointer transition-colors"
              title="Clear question"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>Clear</span>
            </button>
          )}
        </div>

        <textarea
          id="professional-question-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Enter the client case facts, transactions, turnover, entities, or statutory query..."
          rows={3}
          className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 focus:bg-white resize-y transition-all leading-relaxed"
        />
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 font-medium">
        <span>Specify sections, facts, turnover numbers, or assessment years.</span>
        <span>{value.length} chars</span>
      </div>
    </div>
  );
};
