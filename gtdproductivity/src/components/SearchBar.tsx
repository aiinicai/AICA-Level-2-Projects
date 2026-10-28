import React, { useRef, useEffect } from 'react';
import { Search, X, Layers, Inbox, PlayCircle } from 'lucide-react';

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  activeView: string;
  totalMatches: number;
  totalItems: number;
  viewMatchCounts?: {
    inbox: number;
    next_actions: number;
    projects: number;
  };
  onSelectView?: (view: 'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture') => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  query,
  onQueryChange,
  activeView,
  totalMatches,
  totalItems,
  viewMatchCounts,
  onSelectView,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Press '/' or 'Cmd+K' / 'Ctrl+K' to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        if (e.key === 'Escape' && document.activeElement === inputRef.current) {
          inputRef.current?.blur();
          onQueryChange('');
        }
        return;
      }

      if (e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key === 'k')) {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onQueryChange]);

  const viewLabel = activeView === 'next_actions' 
    ? 'Next Actions' 
    : activeView.charAt(0).toUpperCase() + activeView.slice(1);

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-3 sm:p-3.5 shadow-2xs transition-all focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-500/15">
      <div className="flex items-center gap-3">
        <div className="pl-1 text-slate-400 group-focus-within:text-teal-600 transition-colors shrink-0">
          <Search className="w-4 h-4 text-slate-400" />
        </div>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={`Search tasks, projects, notes, and contexts across all views... (Press / to search)`}
          className="w-full text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 outline-none bg-transparent"
        />

        {query ? (
          <div className="flex items-center gap-2 pr-1 shrink-0">
            <span className="text-[11px] font-mono font-semibold text-teal-800 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
              {totalMatches} in this view
            </span>
            <button
              onClick={() => {
                onQueryChange('');
                inputRef.current?.focus();
              }}
              title="Clear search (Esc)"
              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 pr-2 select-none text-[10px] font-mono text-slate-400 shrink-0">
            <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-600 shadow-2xs">
              /
            </kbd>
            <span>quick search</span>
          </div>
        )}
      </div>

      {query && (
        <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 px-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-slate-400">Filtering:</span>
            <span className="font-semibold text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded">
              "{query}"
            </span>
            <span aria-hidden="true" className="text-slate-300">·</span>
            <span>
              Showing {totalMatches} of {totalItems} items in <strong className="text-slate-700">{viewLabel}</strong>
            </span>
          </div>

          {viewMatchCounts && onSelectView && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] text-slate-400 hidden md:inline">Jump to view:</span>
              <button
                onClick={() => onSelectView('inbox')}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-all cursor-pointer ${
                  activeView === 'inbox'
                    ? 'bg-rose-100 text-rose-800 border border-rose-300 shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-rose-50 hover:text-rose-700 border border-transparent'
                }`}
              >
                <Inbox className="w-3 h-3 text-rose-500" />
                <span>Inbox ({viewMatchCounts.inbox})</span>
              </button>
              <button
                onClick={() => onSelectView('next_actions')}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-all cursor-pointer ${
                  activeView === 'next_actions'
                    ? 'bg-teal-100 text-teal-800 border border-teal-300 shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-teal-50 hover:text-teal-700 border border-transparent'
                }`}
              >
                <PlayCircle className="w-3 h-3 text-teal-600" />
                <span>Next Actions ({viewMatchCounts.next_actions})</span>
              </button>
              <button
                onClick={() => onSelectView('projects')}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-all cursor-pointer ${
                  activeView === 'projects'
                    ? 'bg-blue-100 text-blue-800 border border-blue-300 shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-blue-50 hover:text-blue-700 border border-transparent'
                }`}
              >
                <Layers className="w-3 h-3 text-blue-600" />
                <span>Projects ({viewMatchCounts.projects})</span>
              </button>
              <button
                onClick={() => onQueryChange('')}
                className="ml-1 text-teal-700 hover:text-teal-900 font-medium underline cursor-pointer"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
