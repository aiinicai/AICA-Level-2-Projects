import React, { useState, useEffect, useRef } from 'react';
import { X, CornerDownLeft, Sparkles, Inbox } from 'lucide-react';

interface CaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (title: string, notes: string, dueDate?: string | null) => void;
}

export const CaptureModal: React.FC<CaptureModalProps> = ({ isOpen, onClose, onCapture }) => {
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [keepOpen, setKeepOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setTitle('');
      setNotes('');
      setDueDate('');
      setShowDatePicker(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    onCapture(title, notes, dueDate || null);
    setTitle('');
    setNotes('');
    setDueDate('');
    setShowDatePicker(false);

    if (!keepOpen) {
      onClose();
    } else {
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/40 backdrop-blur-xs"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className="w-full max-w-xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-gradient-to-r from-rose-50/60 via-slate-50/40 to-teal-50/50">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
            <Inbox className="w-4 h-4 text-rose-600" />
            <span>Quick Capture to Inbox</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">esc to cancel</span>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What's on your mind? (Any open loop or idea...)"
              className="w-full text-base font-medium text-slate-900 placeholder:text-slate-400 outline-none border-b-2 border-slate-200 focus:border-teal-600 pb-2 transition-colors"
            />
          </div>

          <div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional context, notes, or details..."
              rows={2}
              className="w-full text-xs text-slate-700 placeholder:text-slate-400 outline-none resize-none bg-slate-50/60 p-2.5 rounded-lg border border-slate-200 focus:border-teal-400 transition-colors"
            />
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            {showDatePicker ? (
              <div className="flex items-center gap-2 w-full">
                <span className="text-slate-500 font-medium">Due:</span>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="p-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md font-mono outline-none focus:border-teal-500"
                />
                <button
                  type="button"
                  onClick={() => { setDueDate(''); setShowDatePicker(false); }}
                  className="text-slate-400 hover:text-rose-600 text-xs underline cursor-pointer"
                >
                  Clear
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowDatePicker(true)}
                className="text-slate-500 hover:text-blue-700 text-xs font-mono flex items-center gap-1 cursor-pointer transition-colors"
              >
                + Add Hard Landscape Due Date
              </button>
            )}
          </div>

          {/* Footer Controls */}
          <div className="flex items-center justify-between pt-2">
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={keepOpen}
                onChange={(e) => setKeepOpen(e.target.checked)}
                className="rounded text-teal-600 focus:ring-teal-500 w-3.5 h-3.5 cursor-pointer"
              />
              Capture another immediately
            </label>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!title.trim()}
                className="px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 disabled:opacity-40 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-sm shadow-teal-600/30 active:scale-98"
              >
                <span>Save to Inbox</span>
                <CornerDownLeft className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
