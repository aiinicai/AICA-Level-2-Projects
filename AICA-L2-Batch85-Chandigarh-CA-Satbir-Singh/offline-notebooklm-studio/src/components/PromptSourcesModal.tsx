import React from 'react';
import { StudioNote } from '../types';
import { X, Clock, FileText, Sparkles, Copy, Check } from 'lucide-react';

interface Props {
  note: StudioNote | null;
  onClose: () => void;
}

export const PromptSourcesModal: React.FC<Props> = ({ note, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  if (!note) return null;

  const handleCopyPrompt = () => {
    if (note.promptUsed) {
      navigator.clipboard.writeText(note.promptUsed);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Prompt and Sources</h3>
              <p className="text-[11px] text-gray-500 truncate max-w-xs">{note.title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Prompt Section */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>Original Generation Prompt</span>
              </div>
              {note.promptUsed && (
                <button
                  onClick={handleCopyPrompt}
                  className="text-gray-500 hover:text-gray-900 text-[11px] flex items-center gap-1 transition"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              )}
            </div>
            <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 text-xs text-gray-800 font-sans leading-relaxed">
              {note.promptUsed || 'Manual note created by user or drafted directly in Output Studio.'}
            </div>
          </div>

          {/* Grounded Sources Section */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700">
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span>Grounded Sources ({note.sourceNames?.length || note.sourcesCount || 0})</span>
            </div>
            <div className="space-y-1.5">
              {note.sourceNames && note.sourceNames.length > 0 ? (
                note.sourceNames.map((srcName, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-800"
                  >
                    <span className="font-medium truncate">{srcName}</span>
                    <span className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-semibold">
                      Grounded
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500 italic p-2">Direct standalone note without external source references.</p>
              )}
            </div>
          </div>

          {/* Timestamp Info */}
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex justify-between text-[11px] text-gray-500">
            <span>Created: {new Date(note.createdAt).toLocaleString()}</span>
            <span>Type: <strong className="capitalize text-gray-700">{note.type.replace('_', ' ')}</strong></span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-100 bg-white flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
