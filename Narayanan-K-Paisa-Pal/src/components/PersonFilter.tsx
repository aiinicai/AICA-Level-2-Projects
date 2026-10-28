import React from 'react';
import { User, Users } from 'lucide-react';
import { AppRow } from '../types';
import { SYNTHETIC_PERSONS } from '../data/dummyDocuments';

interface Props {
  rows: AppRow[];
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
}

export const PersonFilter: React.FC<Props> = ({
  rows,
  selectedPerson,
  onSelectPerson,
}) => {
  // Count documents per holder
  const countsByHolder: Record<string, number> = {};
  rows.forEach((r) => {
    const h = (r.data?.holder || '').trim();
    if (h) {
      countsByHolder[h] = (countsByHolder[h] || 0) + 1;
    }
  });

  // Collect distinct holders in rows
  const activeHolders = Object.keys(countsByHolder).sort();

  if (activeHolders.length < 2) return null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap my-3 no-print">
      <span className="text-xs font-semibold text-[#6F7E92] dark:text-[#8594AA] flex items-center gap-1 mr-1">
        <Users className="w-3.5 h-3.5 text-[#0E7C86] dark:text-[#38bdf8]" />
        <span>Household Members ({activeHolders.length}):</span>
      </span>

      <button
        onClick={() => onSelectPerson('')}
        className={`px-3 py-1 text-xs font-medium rounded-full transition cursor-pointer ${
          selectedPerson === ''
            ? 'bg-[#0E7C86] text-white font-bold shadow-xs'
            : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA]'
        }`}
      >
        All Members ({rows.length})
      </button>

      {activeHolders.map((name) => {
        const count = countsByHolder[name] || 0;
        const isSelected = selectedPerson === name;
        return (
          <button
            key={name}
            onClick={() => onSelectPerson(name)}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full transition cursor-pointer ${
              isSelected
                ? 'bg-[#0E7C86] text-white font-bold shadow-xs'
                : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA] dark:hover:bg-[#283852]'
            }`}
          >
            <User className="w-3 h-3 opacity-70" />
            <span>{name}</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                isSelected
                  ? 'bg-white/20 text-white'
                  : 'bg-black/10 dark:bg-white/10 text-slate-600 dark:text-slate-300'
              }`}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
};
