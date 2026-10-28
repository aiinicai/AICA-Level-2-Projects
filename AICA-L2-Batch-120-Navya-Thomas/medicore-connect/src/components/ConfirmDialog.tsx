import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, XCircle, Undo2, Send } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (comment?: string) => void;
  title: string;
  message: string;
  type?: 'approve' | 'reject' | 'submit' | 'reverse' | 'danger';
  confirmLabel?: string;
  requireComment?: boolean;
  commentPlaceholder?: string;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  type = 'approve',
  confirmLabel = 'Confirm',
  requireComment = false,
  commentPlaceholder = 'Enter reason...',
}) => {
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (requireComment && !comment.trim()) {
      setError('A reason or justification is required to proceed.');
      return;
    }
    setError('');
    onConfirm(comment.trim());
    setComment('');
  };

  const getTheme = () => {
    switch (type) {
      case 'approve':
        return {
          icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />,
          btn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
        };
      case 'reject':
        return {
          icon: <XCircle className="w-6 h-6 text-rose-600" />,
          btn: 'bg-rose-600 hover:bg-rose-700 text-white',
        };
      case 'reverse':
        return {
          icon: <Undo2 className="w-6 h-6 text-amber-600" />,
          btn: 'bg-amber-600 hover:bg-amber-700 text-white',
        };
      case 'submit':
        return {
          icon: <Send className="w-6 h-6 text-[#5B2C83]" />,
          btn: 'bg-[#5B2C83] hover:bg-[#3F1D5C] text-white',
        };
      default:
        return {
          icon: <AlertCircle className="w-6 h-6 text-rose-600" />,
          btn: 'bg-rose-600 hover:bg-rose-700 text-white',
        };
    }
  };

  const theme = getTheme();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 max-w-md w-full p-6 z-10 animate-in zoom-in-95 duration-150">
        <div className="flex items-start space-x-3 mb-4">
          <div className="p-2 bg-gray-100 rounded-full shrink-0">{theme.icon}</div>
          <div>
            <h3 className="font-bold text-base text-gray-900">{title}</h3>
            <p className="text-xs text-gray-600 mt-1 leading-relaxed">{message}</p>
          </div>
        </div>

        {requireComment && (
          <div className="mb-4">
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Reason / Comments <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              placeholder={commentPlaceholder}
              value={comment}
              onChange={(e) => {
                setComment(e.target.value);
                if (error) setError('');
              }}
              className="w-full text-xs p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5B2C83] focus:border-[#5B2C83]"
            />
            {error && <p className="text-[11px] text-rose-600 font-medium mt-1">{error}</p>}
          </div>
        )}

        <div className="flex justify-end space-x-2 pt-2 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg border border-gray-300 text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition-colors ${theme.btn}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
