import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Lock,
  Save,
  Send,
  Trash2,
} from 'lucide-react';
import { formatShortDate, parseIsoDateLocal } from '../lib/dateUtils';
import {
  addDaysIso,
  buildApprovedLeaveMap,
  buildHolidayMap,
  canEmployeeEdit,
  eachDate,
  getDayInfo,
  openWindowStart,
  toIso,
  validateLines,
} from '../lib/timesheetUtils';
import type { Employee, Holiday, LeaveRequest } from '../types/leave';
import {
  TIMESHEET_LIMITS,
  type Project,
  type TimesheetEntry,
  type TimesheetLine,
  type TimesheetStatus,
} from '../types/timesheet';

interface TimesheetViewProps {
  employee: Employee;
  projects: Project[];
  holidays: Holiday[];
  myEntries: TimesheetEntry[];
  myRequests: LeaveRequest[];
  today: string;
  approverName: string;
  onSaveDay: (date: string, lines: TimesheetLine[]) => Promise<void>;
  onSubmitDays: (entries: TimesheetEntry[]) => Promise<void>;
}

const WEEKDAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const STATUS_STYLES: Record<TimesheetStatus, string> = {
  draft: 'bg-amber-50 text-amber-800 border-amber-200',
  submitted: 'bg-sky-50 text-sky-800 border-sky-200',
  approved: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  rejected: 'bg-red-50 text-red-800 border-red-200',
};

const STATUS_LABEL: Record<TimesheetStatus, string> = {
  draft: 'Draft',
  submitted: 'Submitted',
  approved: 'Approved',
  rejected: 'Rejected',
};

const mondayOf = (iso: string): string => {
  const dt = parseIsoDateLocal(iso) || new Date();
  const offset = (dt.getDay() + 6) % 7; // Mon = 0
  dt.setDate(dt.getDate() - offset);
  return toIso(dt);
};

const hoursText = (n: number): string => (Number.isInteger(n) ? String(n) : String(n));

const parseHours = (text: string): number | null => {
  const t = text.trim();
  if (t === '') return null; // empty
  const n = Number(t);
  if (Number.isNaN(n)) return NaN;
  if (n === 0) return null;
  return n;
};

export const TimesheetView: React.FC<TimesheetViewProps> = ({
  employee,
  projects,
  holidays,
  myEntries,
  myRequests,
  today,
  approverName,
  onSaveDay,
  onSubmitDays,
}) => {
  const [weekStart, setWeekStart] = useState<string>(mondayOf(today));
  const [rowCodes, setRowCodes] = useState<string[]>([]);
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [edits, setEdits] = useState<Record<string, Record<string, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());

  const holidayMap = useMemo(() => buildHolidayMap(holidays), [holidays]);
  const leaveMap = useMemo(() => buildApprovedLeaveMap(myRequests), [myRequests]);
  const entryByDate = useMemo(() => {
    const map = new Map<string, TimesheetEntry>();
    for (const e of myEntries) map.set(e.date, e);
    return map;
  }, [myEntries]);

  const activeProjects = useMemo(() => projects.filter((p) => p.active), [projects]);
  const projectByCode = useMemo(() => {
    const map = new Map<string, Project>();
    for (const p of projects) map.set(p.code, p);
    return map;
  }, [projects]);

  const weekDates = useMemo(() => eachDate(weekStart, addDaysIso(weekStart, 6)), [weekStart]);

  // ---- rows: chosen projects + any project that already has hours this week ----
  const rows = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    const push = (code: string) => {
      if (!code || seen.has(code) || removed.has(code)) return;
      seen.add(code);
      out.push(code);
    };
    rowCodes.forEach(push);
    for (const d of weekDates) {
      const entry = entryByDate.get(d);
      entry?.lines.forEach((l) => push(l.projectCode));
    }
    return out;
  }, [rowCodes, removed, weekDates, entryByDate]);

  const projectMeta = (code: string) => {
    const p = projectByCode.get(code);
    if (p) return { code, name: p.name, client: p.client, type: p.type, active: p.active };
    for (const e of myEntries) {
      const l = e.lines.find((x) => x.projectCode === code);
      if (l) return { code, name: l.projectName, client: l.clientName, type: l.type, active: false };
    }
    return { code, name: code, client: '', type: 'chargeable' as const, active: false };
  };

  const savedText = (date: string, code: string): string => {
    const line = entryByDate.get(date)?.lines.find((l) => l.projectCode === code);
    return line ? hoursText(line.hours) : '';
  };

  const cellText = (date: string, code: string): string => {
    const e = edits[date]?.[code];
    return e !== undefined ? e : savedText(date, code);
  };

  const dayInfoFor = (date: string) => getDayInfo(date, today, holidayMap, leaveMap);
  const permissionFor = (date: string) => canEmployeeEdit(entryByDate.get(date), dayInfoFor(date));

  /** Lines for a date as they would be saved, built from the grid. */
  const buildLines = (date: string): TimesheetLine[] => {
    const out: TimesheetLine[] = [];
    const codes = new Set<string>(rows);
    // include codes with edits even if row hidden/removed, so removals take effect
    Object.keys(edits[date] || {}).forEach((c) => codes.add(c));
    entryByDate.get(date)?.lines.forEach((l) => codes.add(l.projectCode));
    for (const code of codes) {
      const hours = parseHours(cellText(date, code));
      if (hours === null) continue;
      const meta = projectMeta(code);
      out.push({
        projectCode: code,
        projectName: meta.name,
        clientName: meta.client,
        type: meta.type,
        hours,
      });
    }
    return out;
  };

  const sameLines = (a: TimesheetLine[], b: TimesheetLine[]): boolean => {
    if (a.length !== b.length) return false;
    const m = new Map(b.map((l) => [l.projectCode, l.hours]));
    return a.every((l) => m.get(l.projectCode) === l.hours);
  };

  const dayLines = useMemo(() => {
    const map = new Map<string, TimesheetLine[]>();
    for (const d of weekDates) map.set(d, buildLines(d));
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekDates, rows, edits, entryByDate, projectByCode]);

  const dirtyDates = useMemo(
    () =>
      weekDates.filter((d) => {
        if (!permissionFor(d).editable) return false;
        return !sameLines(dayLines.get(d) || [], entryByDate.get(d)?.lines || []);
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [weekDates, dayLines, entryByDate, today, holidayMap, leaveMap]
  );

  // Drop local edits that now equal what is saved.
  useEffect(() => {
    setEdits((prev) => {
      let changed = false;
      const next: Record<string, Record<string, string>> = {};
      for (const [date, cells] of Object.entries(prev)) {
        const kept: Record<string, string> = {};
        for (const [code, text] of Object.entries(cells)) {
          if (text === savedText(date, code)) changed = true;
          else kept[code] = text;
        }
        if (Object.keys(kept).length > 0) next[date] = kept;
        else changed = true;
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myEntries]);

  // ---- submit panel (drafts with exactly 8h, saved) ----
  const submittable = useMemo(() => {
    const out: TimesheetEntry[] = [];
    for (const e of myEntries) {
      if (e.status !== 'draft') continue;
      if (!canEmployeeEdit(e, getDayInfo(e.date, today, holidayMap, leaveMap)).editable) continue;
      if (validateLines(e.lines).complete) out.push(e);
    }
    return out.sort((a, b) => a.date.localeCompare(b.date));
  }, [myEntries, today, holidayMap, leaveMap]);

  const incompleteDrafts = useMemo(
    () =>
      myEntries
        .filter((e) => e.status === 'draft' && !validateLines(e.lines).complete)
        .sort((a, b) => a.date.localeCompare(b.date)),
    [myEntries]
  );

  const pendingDays = useMemo(() => {
    const out: string[] = [];
    for (const d of eachDate(openWindowStart(today), today)) {
      if (getDayInfo(d, today, holidayMap, leaveMap).kind !== 'working') continue;
      const e = entryByDate.get(d);
      if (!e || e.status === 'draft' || e.status === 'rejected') out.push(d);
    }
    return out;
  }, [today, holidayMap, leaveMap, entryByDate]);

  useEffect(() => {
    setPicked(new Set(submittable.map((e) => e.id)));
  }, [submittable]);

  const weekNotes = weekDates
    .map((d) => entryByDate.get(d))
    .filter((e): e is TimesheetEntry => Boolean(e))
    .filter(
      (e) =>
        (e.status === 'rejected' && e.managerComment) || (e.reopenedBy && e.reopenReason)
    );

  // ---- handlers ----
  const setCell = (date: string, code: string, text: string) => {
    setNotice(null);
    setError(null);
    setEdits((prev) => ({ ...prev, [date]: { ...(prev[date] || {}), [code]: text } }));
  };

  const addProject = (code: string) => {
    if (!code) return;
    setRemoved((prev) => {
      const next = new Set(prev);
      next.delete(code);
      return next;
    });
    setRowCodes((prev) => (prev.includes(code) ? prev : [...prev, code]));
  };

  const rowHasLockedHours = (code: string) =>
    weekDates.some((d) => !permissionFor(d).editable && savedText(d, code) !== '');

  const removeRow = (code: string) => {
    setNotice(null);
    setError(null);
    setEdits((prev) => {
      const next = { ...prev };
      for (const d of weekDates) {
        if (!permissionFor(d).editable) continue;
        if (cellText(d, code) !== '') next[d] = { ...(next[d] || {}), [code]: '' };
      }
      return next;
    });
    setRowCodes((prev) => prev.filter((c) => c !== code));
    setRemoved((prev) => new Set(prev).add(code));
  };

  const handleSave = async () => {
    setError(null);
    setNotice(null);
    for (const d of dirtyDates) {
      const v = validateLines(dayLines.get(d) || []);
      if (v.error) {
        setError(`${formatShortDate(d)}: ${v.error}`);
        return;
      }
    }
    setBusy(true);
    try {
      let saved = 0;
      for (const d of dirtyDates) {
        await onSaveDay(d, dayLines.get(d) || []);
        saved += 1;
      }
      setNotice(`${saved} day(s) saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save.');
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async () => {
    const chosen = submittable.filter((e) => picked.has(e.id));
    if (chosen.length === 0) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await onSubmitDays(chosen);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit for approval.');
    } finally {
      setBusy(false);
    }
  };

  const weekLabel = `${formatShortDate(weekStart).replace(/, \d{4}$/, '')} – ${formatShortDate(
    addDaysIso(weekStart, 6)
  )}`;

  const addableProjects = activeProjects.filter((p) => !rows.includes(p.code));
  const colTone = (date: string): string => {
    const k = dayInfoFor(date).kind;
    if (k === 'weekend') return 'bg-slate-50';
    if (k === 'holiday') return 'bg-sky-50';
    if (k === 'leave') return 'bg-violet-50';
    const st = entryByDate.get(date)?.status;
    if (st === 'draft') return 'bg-amber-50';
    if (st === 'submitted') return 'bg-sky-50';
    if (st === 'approved') return 'bg-emerald-50';
    if (st === 'rejected') return 'bg-red-50';
    return 'bg-white';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">My Timesheet</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Mon-Fri, 8 hours a day. Entries open from{' '}
            <span className="font-medium text-slate-700">{formatShortDate(openWindowStart(today))}</span> to{' '}
            <span className="font-medium text-slate-700">{formatShortDate(today)}</span>. Approver:{' '}
            <span className="font-medium text-slate-700">{approverName}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setWeekStart(addDaysIso(weekStart, -7))}
            className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
            aria-label="Previous week"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-semibold text-slate-900 min-w-52 text-center">{weekLabel}</span>
          <button
            type="button"
            onClick={() => setWeekStart(addDaysIso(weekStart, 7))}
            className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
            aria-label="Next week"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setWeekStart(mondayOf(today))}
            className="px-3 py-2 text-xs font-medium bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
          >
            This week
          </button>
        </div>
      </div>

      {pendingDays.length > 0 && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-xs text-amber-900">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-amber-700" />
          <p>
            <span className="font-semibold">{pendingDays.length} working day(s)</span> in the open window are
            not yet submitted:{' '}
            {pendingDays.slice(-6).map((d) => formatShortDate(d).replace(/, \d{4}$/, '')).join(', ')}
            {pendingDays.length > 6 ? ' and earlier' : ''}.
          </p>
        </div>
      )}

      {/* Weekly grid */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-4 sm:px-5 py-3 border-b border-slate-200 bg-slate-50 text-xs text-slate-600">
          Pick each project <span className="font-semibold text-slate-800">once</span> on the left, then type
          hours for each day on the right. Every working day must add up to{' '}
          <span className="font-semibold text-slate-800">{TIMESHEET_LIMITS.dailyHours} h</span>.
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="sticky left-0 z-10 bg-white text-left px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500 min-w-64 w-72">
                  Project
                </th>
                {weekDates.map((d, i) => {
                  const info = dayInfoFor(d);
                  const entry = entryByDate.get(d);
                  const frozen =
                    info.kind === 'working' && !info.future && !info.inOpenWindow && !(entry && entry.reopenedBy);
                  return (
                    <th key={d} className={`px-1.5 py-2 text-center min-w-20 ${colTone(d)}`}>
                      <div className="text-[11px] font-medium text-slate-500">{WEEKDAY_SHORT[i]}</div>
                      <div
                        className={`font-mono tabular-nums text-sm font-semibold ${
                          d === today ? 'text-white bg-slate-900 rounded-md inline-block px-1.5' : 'text-slate-900'
                        }`}
                      >
                        {Number(d.slice(8, 10))}
                      </div>
                      <div className="text-[10px] leading-tight h-6 mt-0.5 text-slate-500 font-normal">
                        {info.kind === 'holiday' && <span className="text-sky-800">{info.label}</span>}
                        {info.kind === 'leave' && (
                          <span className="text-violet-800">{info.halfDayLeave ? 'Half-day ' : ''}Leave</span>
                        )}
                        {info.kind === 'weekend' && 'Off'}
                        {frozen && (
                          <span className="inline-flex items-center gap-0.5">
                            <Lock className="w-3 h-3" />
                            Frozen
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
                <th className="px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-500 min-w-16">
                  Week
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={weekDates.length + 2}
                    className="px-4 py-8 text-center text-sm text-slate-500"
                  >
                    No projects added yet. Use <span className="font-semibold text-slate-800">+ Add project</span>{' '}
                    below to pick your first one.
                  </td>
                </tr>
              )}
              {rows.map((code) => {
                const meta = projectMeta(code);
                const weekSum = weekDates.reduce((n, d) => {
                  const h = parseHours(cellText(d, code));
                  return n + (h !== null && Number.isFinite(h) ? h : 0);
                }, 0);
                const removable = !rowHasLockedHours(code);
                return (
                  <tr key={code} className="border-b border-slate-100">
                    <td className="sticky left-0 z-10 bg-white px-4 py-2 align-middle">
                      <div className="flex items-center gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-slate-900 truncate">
                            <span className="font-mono text-xs text-slate-500 mr-1.5">{meta.code}</span>
                            {meta.name}
                            {!meta.active && <span className="ml-1.5 text-[10px] text-slate-400">(inactive)</span>}
                          </p>
                          <p className="text-[11px] text-slate-500 truncate">
                            {meta.client || '—'} ·{' '}
                            <span className={meta.type === 'chargeable' ? 'text-emerald-700' : 'text-slate-500'}>
                              {meta.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable'}
                            </span>
                          </p>
                        </div>
                        {removable && (
                          <button
                            type="button"
                            onClick={() => removeRow(code)}
                            className="shrink-0 p-1 text-slate-400 hover:text-red-600 cursor-pointer"
                            aria-label={`Remove ${meta.code}`}
                            title="Remove this project from the grid"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                    {weekDates.map((d) => {
                      const editable = permissionFor(d).editable;
                      const text = cellText(d, code);
                      const dirty = edits[d]?.[code] !== undefined && edits[d][code] !== savedText(d, code);
                      const parsed = parseHours(text);
                      const bad =
                        parsed !== null &&
                        (!Number.isFinite(parsed) ||
                          parsed < 0 ||
                          parsed > TIMESHEET_LIMITS.dailyHours ||
                          Math.abs(parsed / TIMESHEET_LIMITS.hourStep - Math.round(parsed / TIMESHEET_LIMITS.hourStep)) >
                            1e-9);
                      return (
                        <td key={d} className={`px-1.5 py-1.5 text-center ${colTone(d)}`}>
                          {dayInfoFor(d).kind === 'working' && !dayInfoFor(d).future ? (
                            <input
                              type="number"
                              inputMode="decimal"
                              min={0}
                              max={TIMESHEET_LIMITS.dailyHours}
                              step={TIMESHEET_LIMITS.hourStep}
                              value={text}
                              disabled={!editable}
                              onChange={(e) => setCell(d, code, e.target.value)}
                              aria-label={`${meta.code} hours on ${d}`}
                              placeholder="–"
                              className={`w-16 px-1.5 py-1.5 text-sm text-center font-mono tabular-nums rounded-md border ${
                                bad
                                  ? 'border-red-400 bg-red-50'
                                  : dirty
                                    ? 'border-amber-400 bg-amber-50'
                                    : 'border-slate-200 bg-white'
                              } disabled:bg-transparent disabled:border-transparent disabled:text-slate-700`}
                            />
                          ) : (
                            <span className="text-slate-300">·</span>
                          )}
                        </td>
                      );
                    })}
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-sm font-semibold text-slate-800">
                      {weekSum || '–'}
                    </td>
                  </tr>
                );
              })}

              {/* Add project row */}
              <tr className="border-b border-slate-200">
                <td className="sticky left-0 z-10 bg-white px-4 py-2" colSpan={1}>
                  <select
                    value=""
                    onChange={(e) => addProject(e.target.value)}
                    className="w-full px-2.5 py-2 text-sm font-medium text-slate-800 bg-white border-2 border-dashed border-slate-300 rounded-lg hover:border-slate-500 cursor-pointer"
                    aria-label="Add project"
                  >
                    <option value="">+ Add project…</option>
                    <optgroup label="Chargeable">
                      {addableProjects
                        .filter((p) => p.type === 'chargeable')
                        .map((p) => (
                          <option key={p.id} value={p.code}>
                            {p.code} - {p.name}{p.client ? ` · ${p.client}` : ''}
                          </option>
                        ))}
                    </optgroup>
                    <optgroup label="Non-chargeable">
                      {addableProjects
                        .filter((p) => p.type === 'non_chargeable')
                        .map((p) => (
                          <option key={p.id} value={p.code}>
                            {p.code} - {p.name}{p.client ? ` · ${p.client}` : ''}
                          </option>
                        ))}
                    </optgroup>
                  </select>
                </td>
                <td colSpan={weekDates.length + 1} />
              </tr>

              {/* Totals */}
              <tr className="border-b border-slate-100">
                <td className="sticky left-0 z-10 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700">
                  Day total (needs {TIMESHEET_LIMITS.dailyHours} h)
                </td>
                {weekDates.map((d) => {
                  const info = dayInfoFor(d);
                  if (info.kind !== 'working' || info.future) {
                    return <td key={d} className={`px-1.5 py-2.5 text-center text-slate-300 ${colTone(d)}`}>·</td>;
                  }
                  const lines = dayLines.get(d) || [];
                  const total = lines.reduce((n, l) => n + (Number.isFinite(l.hours) ? l.hours : 0), 0);
                  const tone =
                    total > TIMESHEET_LIMITS.dailyHours
                      ? 'text-red-700'
                      : total === TIMESHEET_LIMITS.dailyHours
                        ? 'text-emerald-700'
                        : total > 0
                          ? 'text-amber-700'
                          : 'text-slate-400';
                  return (
                    <td key={d} className={`px-1.5 py-2.5 text-center ${colTone(d)}`}>
                      <span className={`font-mono tabular-nums text-sm font-semibold ${tone}`}>
                        {total} / {TIMESHEET_LIMITS.dailyHours}
                      </span>
                    </td>
                  );
                })}
                <td className="px-3 py-2.5 text-center font-mono tabular-nums text-sm font-semibold text-slate-900">
                  {weekDates.reduce((n, d) => {
                    const info = dayInfoFor(d);
                    if (info.kind !== 'working') return n;
                    return n + (dayLines.get(d) || []).reduce((m, l) => m + (Number.isFinite(l.hours) ? l.hours : 0), 0);
                  }, 0) || '–'}
                </td>
              </tr>

              {/* Status */}
              <tr>
                <td className="sticky left-0 z-10 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700">
                  Status
                </td>
                {weekDates.map((d) => {
                  const entry = entryByDate.get(d);
                  const info = dayInfoFor(d);
                  return (
                    <td key={d} className={`px-1.5 py-2.5 text-center ${colTone(d)}`}>
                      {info.kind === 'working' && entry ? (
                        <span
                          className={`inline-block px-1.5 py-0.5 text-[10px] font-medium border rounded-md ${STATUS_STYLES[entry.status]}`}
                        >
                          {STATUS_LABEL[entry.status]}
                        </span>
                      ) : (
                        <span className="text-slate-300">·</span>
                      )}
                    </td>
                  );
                })}
                <td />
              </tr>
            </tbody>
          </table>
        </div>

        <div className="px-4 sm:px-5 py-2.5 border-t border-slate-200 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-200" />Draft</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-sky-200" />Submitted</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-200" />Approved</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-red-200" />Rejected</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-violet-200" />Leave</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-sky-100 border border-sky-200" />Holiday</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-slate-100 border border-slate-200" />Weekly off</span>
          <span className="inline-flex items-center gap-1.5"><Lock className="w-3 h-3" />Frozen</span>
        </div>
        <div className="px-4 sm:px-5 py-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs">
            {error && <span className="text-red-700 font-medium">{error}</span>}
            {!error && notice && <span className="text-emerald-700 font-medium">{notice}</span>}
            {!error && !notice && dirtyDates.length > 0 && (
              <span className="text-amber-800 font-medium">
                {dirtyDates.length} day(s) with unsaved changes. Click Save to keep them.
              </span>
            )}
            {!error && !notice && dirtyDates.length === 0 && (
              <span className="text-slate-500">All changes saved. Frozen or locked days are greyed out.</span>
            )}
          </div>
          <button
            type="button"
            onClick={handleSave}
            disabled={busy || dirtyDates.length === 0}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
          >
            <Save className="w-4 h-4" />
            Save changes
          </button>
        </div>
      </div>

      {weekNotes.length > 0 && (
        <div className="space-y-2">
          {weekNotes.map((e) => (
            <div
              key={e.id}
              className={`text-xs rounded-lg px-3 py-2 border ${
                e.status === 'rejected'
                  ? 'text-red-800 bg-red-50 border-red-200'
                  : 'text-slate-700 bg-slate-50 border-slate-200'
              }`}
            >
              <span className="font-semibold">{formatShortDate(e.date)}</span>{' '}
              {e.status === 'rejected' ? (
                <>
                  rejected by {approverName}: {e.managerComment}
                </>
              ) : (
                <>reopened by HR: {e.reopenReason}</>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Submit */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">Submit for approval</h2>
        {submittable.length === 0 ? (
          <p className="text-xs text-slate-500">
            No saved day is ready yet. A day is ready when it has exactly {TIMESHEET_LIMITS.dailyHours} h saved.
          </p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-1.5">
            {submittable.map((e) => (
              <label key={e.id} className="flex items-center gap-2 text-sm text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={picked.has(e.id)}
                  onChange={(ev) =>
                    setPicked((prev) => {
                      const next = new Set(prev);
                      if (ev.target.checked) next.add(e.id);
                      else next.delete(e.id);
                      return next;
                    })
                  }
                />
                {formatShortDate(e.date)}
                <span className="ml-auto font-mono text-[11px] text-slate-500">
                  {e.lines.map((l) => `${l.projectCode} ${l.hours}h`).join(', ')}
                </span>
              </label>
            ))}
          </div>
        )}
        {incompleteDrafts.length > 0 && (
          <p className="text-xs text-amber-800">
            Incomplete drafts (need {TIMESHEET_LIMITS.dailyHours}h):{' '}
            {incompleteDrafts.map((e) => formatShortDate(e.date).replace(/, \d{4}$/, '')).join(', ')}
          </p>
        )}
        {dirtyDates.length > 0 && submittable.length > 0 && (
          <p className="text-xs text-amber-800">Save your changes first, then submit.</p>
        )}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={busy || picked.size === 0 || submittable.length === 0 || dirtyDates.length > 0}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 disabled:opacity-40 cursor-pointer"
        >
          <Send className="w-4 h-4" />
          Submit {picked.size} day{picked.size === 1 ? '' : 's'} to {approverName}
        </button>
      </div>
    </div>
  );
};
