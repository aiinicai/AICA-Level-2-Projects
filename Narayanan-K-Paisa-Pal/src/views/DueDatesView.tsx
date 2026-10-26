import React, { useState } from 'react';
import {
  Plus,
  FileUp,
  Printer,
  Search,
  CalendarClock,
  List,
  CalendarDays,
  TrendingUp,
} from 'lucide-react';
import { AppRow, DueCategory, UserProfile } from '../types';
import { CATS, norm, normAll } from '../utils/calculations';
import { ItemRow } from '../components/ItemRow';
import { PersonFilter } from '../components/PersonFilter';
import { CalendarView } from '../components/CalendarView';
import { triggerPrint } from '../utils/exportImport';

interface Props {
  rows: AppRow[];
  profile: UserProfile;
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
  onAdd: (kind: 'due') => void;
  onUpload: (kind: 'due') => void;
  onOpenCashFlow?: () => void;
  onMarkPaid: (id: string) => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
}

export const DueDatesView: React.FC<Props> = ({
  rows,
  profile,
  selectedPerson,
  onSelectPerson,
  onAdd,
  onUpload,
  onOpenCashFlow,
  onMarkPaid,
  onEdit,
  onDelete,
  onViewAttachment,
}) => {
  const [selectedCat, setSelectedCat] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list');

  const dueRows = rows.filter((r) => r.kind === 'due');

  const visibleRows = dueRows.filter((r) => {
    if (selectedPerson && (r.data?.holder || '').trim() !== selectedPerson) return false;
    if (selectedCat !== 'all' && (r.data?.category || 'utility') !== selectedCat) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const name = (r.data?.name || '').toLowerCase();
      const provider = (r.data?.provider || '').toLowerCase();
      const ref = (r.data?.ref || '').toLowerCase();
      if (!name.includes(term) && !provider.includes(term) && !ref.includes(term)) {
        return false;
      }
    }
    return true;
  });

  // Category counts
  const catCounts: Record<string, number> = {};
  dueRows.forEach((r) => {
    const c = r.data?.category || 'utility';
    catCounts[c] = (catCounts[c] || 0) + 1;
  });

  const allAlerts = visibleRows.flatMap(normAll);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F1B2D] dark:text-[#E8EDF5]">
            Due Dates
          </h1>
          <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
            Bills, premiums, EMIs and recurring renewals
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap no-print">
          {/* View Toggle */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] text-xs">
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                viewMode === 'list'
                  ? 'bg-white dark:bg-[#131C2E] text-[#0F1B2D] dark:text-[#E8EDF5] shadow-xs font-semibold'
                  : 'text-[#6F7E92] dark:text-[#8594AA] hover:text-[#0F1B2D]'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>List</span>
            </button>
            <button
              onClick={() => setViewMode('calendar')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                viewMode === 'calendar'
                  ? 'bg-white dark:bg-[#131C2E] text-[#0F1B2D] dark:text-[#E8EDF5] shadow-xs font-semibold'
                  : 'text-[#6F7E92] dark:text-[#8594AA] hover:text-[#0F1B2D]'
              }`}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span>Monthly Calendar</span>
            </button>
          </div>

          <button
            onClick={triggerPrint}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-[#0E7C86] text-[#0F1B2D] dark:text-[#E8EDF5] transition"
            title="Print or Save as PDF"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Print / PDF</span>
          </button>

          {profile.showUpload !== false && (
            <button
              onClick={() => onUpload('due')}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-teal-400/50 bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 dark:hover:bg-teal-900 text-teal-800 dark:text-teal-200 transition shadow-2xs cursor-pointer"
            >
              <FileUp className="w-4 h-4 text-[#0E7C86] dark:text-[#38bdf8]" />
              <span>Add from file (auto-detect)</span>
            </button>
          )}

          {onOpenCashFlow && (
            <button
              onClick={onOpenCashFlow}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-indigo-500 text-indigo-700 dark:text-indigo-300 transition"
              title="View month-by-month cash outflows and inflows"
            >
              <TrendingUp className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Cash Flow</span>
            </button>
          )}

          <button
            onClick={() => onAdd('due')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add due date</span>
          </button>
        </div>
      </div>

      <PersonFilter
        rows={rows}
        selectedPerson={selectedPerson}
        onSelectPerson={onSelectPerson}
      />

      {/* Calendar View Mode */}
      {viewMode === 'calendar' ? (
        <CalendarView
          alerts={allAlerts}
          onMarkPaid={onMarkPaid}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ) : (
        /* List View Mode */
        <>
          {/* Category Chips & Search */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 no-print">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
              <button
                onClick={() => setSelectedCat('all')}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition whitespace-nowrap ${
                  selectedCat === 'all'
                    ? 'bg-[#0B3B66] text-white dark:bg-[#5B9BE0] dark:text-[#08121F]'
                    : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA]'
                }`}
              >
                All <span>({dueRows.length})</span>
              </button>

              {Object.entries(CATS).map(([k, label]) => {
                const count = catCounts[k] || 0;
                if (count === 0 && selectedCat !== k) return null;
                return (
                  <button
                    key={k}
                    onClick={() => setSelectedCat(k)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-full transition whitespace-nowrap ${
                      selectedCat === k
                        ? 'bg-[#0B3B66] text-white dark:bg-[#5B9BE0] dark:text-[#08121F]'
                        : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA]'
                    }`}
                  >
                    {label} <span className="opacity-75">({count})</span>
                  </button>
                );
              })}
            </div>

            <div className="relative w-full sm:w-64 flex-shrink-0">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#6F7E92] dark:text-[#8594AA]" />
              <input
                type="text"
                placeholder="Search due dates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl focus:outline-2 focus:outline-[#0E7C86]"
              />
            </div>
          </div>

          {/* Main List */}
          <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 sm:p-5 shadow-xs">
            <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A]">
              {visibleRows.length ? (
                visibleRows.map((r) => {
                  const alert = norm(r);
                  if (!alert) return null;
                  return (
                    <ItemRow
                      key={r.id}
                      alert={alert}
                      onMarkPaid={onMarkPaid}
                      onEdit={onEdit}
                      onDelete={onDelete}
                      onViewAttachment={onViewAttachment}
                    />
                  );
                })
              ) : (
                <div className="text-center py-12 text-[#6F7E92] dark:text-[#8594AA] space-y-2">
                  <CalendarClock className="w-10 h-10 mx-auto opacity-50 stroke-[1.5]" />
                  <p className="text-sm">
                    No due dates found. Press <strong>Add due date</strong> or import from a file.
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
