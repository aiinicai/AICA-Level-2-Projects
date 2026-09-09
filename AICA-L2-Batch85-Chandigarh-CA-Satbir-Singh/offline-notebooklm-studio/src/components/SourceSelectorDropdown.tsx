import React, { useState, useRef, useEffect } from 'react';
import { SourceItem } from '../types';
import { ChevronDown, Check, Search, CheckSquare, Square, FileText } from 'lucide-react';

interface Props {
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onChangeSelected: (selected: Set<string>) => void;
  buttonLabel?: string;
  className?: string;
}

export const SourceSelectorDropdown: React.FC<Props> = ({
  sources,
  selectedSourceIds,
  onChangeSelected,
  buttonLabel,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredSources = sources.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleToggle = (id: string) => {
    const next = new Set(selectedSourceIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    onChangeSelected(next);
  };

  const handleSelectAll = () => {
    const next = new Set(sources.map((s) => s.id));
    onChangeSelected(next);
  };

  const handleClearAll = () => {
    onChangeSelected(new Set());
  };

  const selectedCount = selectedSourceIds.size;
  const countText = buttonLabel || `${selectedCount} source${selectedCount !== 1 ? 's' : ''}`;

  return (
    <div className={`relative inline-block ${className}`} ref={dropdownRef}>
      {/* Trigger Button Matching Screenshot (e.g., "65 sources ▾") */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white hover:bg-gray-50 border border-gray-300 text-gray-800 text-sm font-medium transition shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
      >
        <span>{countText}</span>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Floating Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-72 sm:w-80 bg-white rounded-2xl border border-gray-200 shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
          {/* Header & Quick Controls */}
          <div className="p-3 border-b border-gray-100 bg-[#fafafa]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-800">
                Grounding Sources ({selectedCount}/{sources.length})
              </span>
              <div className="flex items-center gap-2 text-xs">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-blue-600 hover:text-blue-800 font-medium hover:underline"
                >
                  All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="text-gray-500 hover:text-gray-700 font-medium hover:underline"
                >
                  None
                </button>
              </div>
            </div>

            {/* Search filter input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter sources..."
                className="w-full pl-8 pr-2.5 py-1 text-xs bg-white rounded-lg border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 text-gray-800"
              />
            </div>
          </div>

          {/* Sources List with Checkboxes */}
          <div className="max-h-56 overflow-y-auto p-1.5 space-y-0.5">
            {filteredSources.length === 0 ? (
              <div className="p-4 text-center text-xs text-gray-400">
                No matching sources found.
              </div>
            ) : (
              filteredSources.map((src) => {
                const isSelected = selectedSourceIds.has(src.id);
                return (
                  <button
                    key={src.id}
                    type="button"
                    onClick={() => handleToggle(src.id)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left text-xs transition ${
                      isSelected
                        ? 'bg-blue-50/70 text-blue-900 font-medium'
                        : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="shrink-0">
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                    <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                    <span className="truncate flex-1 text-xs" title={src.name}>
                      {src.name}
                    </span>
                    <span className="text-[10px] text-gray-400 shrink-0 font-mono">
                      {(src.sizeBytes / 1024).toFixed(0)}KB
                    </span>
                  </button>
                );
              })
            )}
          </div>

          {/* Done footer */}
          <div className="p-2 border-t border-gray-100 bg-[#fbfbfb] text-right">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-3 py-1 bg-gray-900 hover:bg-black text-white text-xs font-medium rounded-lg transition"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
