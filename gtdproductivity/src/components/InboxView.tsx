import React, { useMemo } from 'react';
import { Item } from '../types/gtd';
import { Inbox, CheckCircle2, Play, Flag, Trash2, Search, X } from 'lucide-react';

interface InboxViewProps {
  inboxItems: Item[];
  searchQuery?: string;
  onClearSearch?: () => void;
  onStartClarify: () => void;
  onOpenCapture: () => void;
  onToggleFlag: (id: string) => void;
  onDelete: (id: string) => void;
}

export const InboxView: React.FC<InboxViewProps> = ({
  inboxItems,
  searchQuery = '',
  onClearSearch,
  onStartClarify,
  onOpenCapture,
  onToggleFlag,
  onDelete,
}) => {
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return inboxItems;
    const q = searchQuery.toLowerCase().trim();
    return inboxItems.filter(item =>
      item.title.toLowerCase().includes(q) ||
      (item.notes && item.notes.toLowerCase().includes(q))
    );
  }, [inboxItems, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Inbox className="w-5 h-5 text-rose-600" />
              Inbox
            </h2>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-rose-50 text-rose-800 border border-rose-200/80 rounded-full">
              {filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'}
              {searchQuery && ` of ${inboxItems.length}`}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Capture everything that has your attention. Clarify one item at a time to keep your mind clear.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onOpenCapture}
            className="px-3.5 py-2 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200/80 rounded-lg transition-colors cursor-pointer"
          >
            + Quick Capture (c)
          </button>
          <button
            onClick={onStartClarify}
            disabled={inboxItems.length === 0}
            className="px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 disabled:opacity-40 rounded-lg transition-all cursor-pointer flex items-center gap-2 shadow-sm shadow-blue-500/25 active:scale-98"
          >
            <Play className="w-3.5 h-3.5 fill-white" />
            <span>Process Inbox (Clarify)</span>
          </button>
        </div>
      </div>

      {/* Inbox List / Empty State */}
      {inboxItems.length === 0 ? (
        <div className="bg-gradient-to-br from-teal-50/40 via-white to-blue-50/30 border border-teal-200/80 rounded-xl p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center mx-auto shadow-2xs">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900">Inbox Zero Reached</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto leading-relaxed">
            All captured thoughts have been clarified into actions, projects, or reference material. Press <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-700 font-mono text-[11px]">c</kbd> or the button below to capture anything on your mind.
          </p>
          <div className="pt-2">
            <button
              onClick={onOpenCapture}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg text-xs font-semibold hover:bg-teal-700 transition-colors cursor-pointer shadow-xs shadow-teal-500/20"
            >
              Capture New Item
            </button>
          </div>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-2xs">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900">No matching inbox items</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            No items in your Inbox match keyword <span className="font-semibold text-slate-700">"{searchQuery}"</span>.
          </p>
          {onClearSearch && (
            <div className="pt-1">
              <button
                onClick={onClearSearch}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
                <span>Clear search filter</span>
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs divide-y divide-slate-100">
          {filteredItems.map((item, index) => (
            <div
              key={item.id}
              className="p-4 hover:bg-slate-50/70 transition-colors flex items-start justify-between gap-4 group"
            >
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <span className="text-xs font-mono text-slate-400 pt-0.5 w-6 select-none">
                  {index + 1}.
                </span>
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="text-sm font-semibold text-slate-900 break-words">
                    {item.title}
                  </div>
                  {item.notes && (
                    <div className="text-xs text-slate-500 line-clamp-2">
                      {item.notes}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-[11px] text-slate-400 pt-1">
                    <span>Captured {new Date(item.createdAt).toLocaleDateString()}</span>
                    {item.estimatedMinutes && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span className="font-mono tabular-nums">{item.estimatedMinutes} min</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Row Action Controls */}
              <div className="flex items-center gap-1 shrink-0 pt-0.5">
                <button
                  onClick={() => onToggleFlag(item.id)}
                  title="Toggle Flag"
                  className={`p-1.5 rounded-md transition-colors cursor-pointer ${
                    item.flagged ? 'text-amber-500 hover:text-amber-600' : 'text-slate-300 hover:text-slate-600'
                  }`}
                >
                  <Flag className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onDelete(item.id)}
                  title="Move to Trash"
                  className="p-1.5 text-slate-300 hover:text-rose-600 rounded-md transition-colors cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
