import React from 'react';
import { Search, X, Filter, RotateCcw, Calendar, DollarSign, Building2 } from 'lucide-react';
import { ActiveFilterChip } from '../core/useTableFilters';

interface TableFilterBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedBU: string;
  onBUChange: (bu: string) => void;
  buOptions: string[];
  selectedStatus?: string;
  onStatusChange?: (status: string) => void;
  statusOptions?: string[];
  selectedCounterparty?: string;
  onCounterpartyChange?: (party: string) => void;
  counterpartyOptions?: string[];
  counterpartyLabel?: string;
  dateFrom?: string;
  onDateFromChange?: (d: string) => void;
  dateTo?: string;
  onDateToChange?: (d: string) => void;
  activeFilterChips: ActiveFilterChip[];
  onClearAll: () => void;
  totalRecords: number;
  filteredRecords: number;
  showDateRange?: boolean;
}

export const TableFilterBar: React.FC<TableFilterBarProps> = ({
  searchQuery,
  onSearchChange,
  selectedBU,
  onBUChange,
  buOptions,
  selectedStatus,
  onStatusChange,
  statusOptions = [],
  selectedCounterparty,
  onCounterpartyChange,
  counterpartyOptions = [],
  counterpartyLabel = 'Counterparty',
  dateFrom = '',
  onDateFromChange,
  dateTo = '',
  onDateToChange,
  activeFilterChips,
  onClearAll,
  totalRecords,
  filteredRecords,
  showDateRange = true,
}) => {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3.5 mb-4 shadow-2xs space-y-3">
      {/* Primary Row: Search + Selectors + Record Count */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left Inputs */}
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
          {/* Free Text Search */}
          <div className="relative min-w-[200px] flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search by number, name, description..."
              className="w-full pl-8 pr-7 py-1.5 bg-gray-50/60 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83] focus:border-[#5B2C83] focus:bg-white transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2 top-2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* BU Selector */}
          <div className="flex items-center space-x-1">
            <select
              value={selectedBU}
              onChange={(e) => onBUChange(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-gray-300 rounded-lg text-xs focus:ring-1 focus:ring-[#5B2C83] text-gray-700 font-medium"
            >
              <option value="All">All Business Units</option>
              {buOptions.map((bu) => (
                <option key={bu} value={bu}>
                  {bu}
                </option>
              ))}
            </select>
          </div>

          {/* Status Selector */}
          {onStatusChange && (
            <div className="flex items-center space-x-1">
              <select
                value={selectedStatus || 'All'}
                onChange={(e) => onStatusChange(e.target.value === 'All' ? '' : e.target.value)}
                className="px-2.5 py-1.5 bg-white border border-gray-300 rounded-lg text-xs focus:ring-1 focus:ring-[#5B2C83] text-gray-700"
              >
                <option value="All">All Statuses</option>
                {statusOptions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Counterparty Selector */}
          {onCounterpartyChange && counterpartyOptions.length > 0 && (
            <div className="flex items-center space-x-1">
              <select
                value={selectedCounterparty || 'All'}
                onChange={(e) => onCounterpartyChange(e.target.value === 'All' ? '' : e.target.value)}
                className="px-2.5 py-1.5 bg-white border border-gray-300 rounded-lg text-xs focus:ring-1 focus:ring-[#5B2C83] text-gray-700 max-w-[160px] truncate"
              >
                <option value="All">All {counterpartyLabel}s</option>
                {counterpartyOptions.slice(0, 50).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Date Range Inputs */}
          {showDateRange && onDateFromChange && onDateToChange && (
            <div className="flex items-center space-x-1 bg-gray-50 border border-gray-200 rounded-lg px-2 py-0.5">
              <span className="text-[10px] text-gray-500 font-medium">Date:</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => onDateFromChange(e.target.value)}
                className="bg-transparent text-[11px] py-1 text-gray-700 focus:outline-none"
                title="Date From"
              />
              <span className="text-gray-400 text-xs">→</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => onDateToChange(e.target.value)}
                className="bg-transparent text-[11px] py-1 text-gray-700 focus:outline-none"
                title="Date To"
              />
            </div>
          )}
        </div>

        {/* Record count summary & clear */}
        <div className="flex items-center space-x-3 shrink-0">
          <span className="text-gray-500 text-xs">
            Showing <strong className="text-[#5B2C83]">{filteredRecords}</strong> of{' '}
            <strong className="text-gray-800">{totalRecords}</strong> records
          </span>

          {activeFilterChips.length > 0 && (
            <button
              onClick={onClearAll}
              className="text-xs text-rose-600 hover:text-rose-800 font-semibold flex items-center space-x-1 hover:underline cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Clear All</span>
            </button>
          )}
        </div>
      </div>

      {/* Active Filter Chips */}
      {activeFilterChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-gray-100 text-xs">
          <span className="text-gray-400 text-[11px] font-medium mr-1">Active Filters:</span>
          {activeFilterChips.map((chip) => (
            <span
              key={chip.id}
              className="inline-flex items-center space-x-1 bg-plum-50 border border-plum-200 text-[#5B2C83] px-2.5 py-0.5 rounded-full text-[11px] font-medium shadow-2xs"
            >
              <span>{chip.label}:</span>
              <strong className="font-semibold text-gray-900">{chip.displayValue}</strong>
              <button
                type="button"
                onClick={chip.onRemove}
                className="ml-1 text-plum-400 hover:text-rose-600 cursor-pointer"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
