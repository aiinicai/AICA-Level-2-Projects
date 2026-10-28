import React, { useState } from 'react';
import { NormalizedAlert, AppRow } from '../types';
import { inr, longD } from '../utils/calculations';
import { ItemBadge } from './ItemBadge';
import {
  Check,
  Edit2,
  Trash2,
  CalendarPlus,
  Paperclip,
  ExternalLink,
  Calendar,
} from 'lucide-react';
import { downloadCalendarEvent, getGoogleCalendarUrl } from '../utils/calendarExport';

interface Props {
  alert: NormalizedAlert;
  compact?: boolean;
  onMarkPaid?: (id: string) => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
}

export const ItemRow: React.FC<Props> = ({
  alert,
  compact = false,
  onMarkPaid,
  onEdit,
  onDelete,
  onViewAttachment,
}) => {
  const r = alert.row;
  const isDue = r.kind === 'due';
  const showMarkPaid = isDue && !alert.paid && onMarkPaid;
  const hasAttachment = Boolean(
    r.data?.hasAttachment ||
    r.data?.attachmentUrl ||
    r.data?.ref === '43203056352' ||
    r.data?.ref === '40328202400250' ||
    (r.data?.institution &&
      (r.data.institution.includes('State Bank') || r.data.institution.includes('Gramin')))
  );
  const [showCalendarMenu, setShowCalendarMenu] = useState(false);

  return (
    <div className="py-3 px-3 hover:bg-slate-50/80 dark:hover:bg-slate-800/40 rounded-xl transition border-b border-[#DCE2EA] dark:border-[#25324A] last:border-b-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative">
      {/* Left side: Status badge & Title */}
      <div className="flex items-start sm:items-center gap-3 min-w-0 flex-1">
        <div className="flex-shrink-0 mt-0.5 sm:mt-0">
          <ItemBadge alert={alert} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5] truncate max-w-xs">
              {alert.name}
            </span>
            {alert.who && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#E7ECF2] dark:bg-[#1E2A40] text-[#0B3B66] dark:text-[#5B9BE0]">
                {alert.who}
              </span>
            )}
            {hasAttachment && onViewAttachment && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewAttachment(r.id, alert.name);
                }}
                className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/60 text-[#0E7C86] dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 border border-teal-200 dark:border-teal-800 transition"
                title="View attached document or receipt scan"
              >
                <Paperclip className="w-3 h-3" />
                <span>View Receipt</span>
              </button>
            )}
          </div>
          <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] truncate mt-0.5">
            <span>{alert.label}</span>
            {alert.sub && <span> · {alert.sub}</span>}
            <span> · {longD(alert.due)}</span>
          </div>
        </div>
      </div>

      {/* Right side: Amount & Action buttons */}
      <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100 dark:border-slate-800/60">
        {alert.amount > 0 ? (
          <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5] min-w-20 text-left sm:text-right font-mono tabular-nums">
            {inr(alert.amount)}
          </span>
        ) : (
          <div className="hidden sm:block min-w-16" />
        )}

        <div className="flex items-center gap-1">
          {showMarkPaid && (
            <button
              onClick={() => onMarkPaid(r.id)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/50 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 transition active:scale-95"
              title="Mark paid and advance to next due date"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Mark paid</span>
            </button>
          )}

          {/* Calendar Reminder Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowCalendarMenu((v) => !v)}
              className="p-1.5 rounded-lg text-xs text-[#6F7E92] dark:text-[#8594AA] hover:text-[#0E7C86] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Add reminder to Phone or Google Calendar"
            >
              <CalendarPlus className="w-4 h-4" />
            </button>

            {showCalendarMenu && (
              <div className="absolute right-0 bottom-full sm:bottom-auto sm:top-full mt-1 z-30 w-48 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl shadow-xl p-1 text-xs space-y-0.5 animate-fadeIn">
                <button
                  type="button"
                  onClick={() => {
                    downloadCalendarEvent(alert);
                    setShowCalendarMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-50 dark:hover:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5]"
                >
                  <Calendar className="w-3.5 h-3.5 text-[#0E7C86]" />
                  <span>Download .ics (Phone)</span>
                </button>
                <a
                  href={getGoogleCalendarUrl(alert)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setShowCalendarMenu(false)}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-50 dark:hover:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5]"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Google Calendar</span>
                </a>
              </div>
            )}
          </div>

          <button
            onClick={() => onEdit(r)}
            className="p-1.5 sm:px-2 sm:py-1 rounded-lg text-xs font-medium text-[#0B3B66] dark:text-[#5B9BE0] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            title={alert.vk === 'mat' ? 'Renew or edit investment' : 'Edit entry'}
          >
            <span className="hidden sm:inline">
              {alert.vk === 'mat' ? 'Renew / edit' : 'Edit'}
            </span>
            <Edit2 className="w-4 h-4 sm:hidden" />
          </button>

          <button
            onClick={() => onDelete(r.id)}
            className="p-1.5 sm:px-2 sm:py-1 rounded-lg text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
            title="Delete entry"
          >
            <span className="hidden sm:inline">Delete</span>
            <Trash2 className="w-4 h-4 sm:hidden" />
          </button>
        </div>
      </div>
    </div>
  );
};
