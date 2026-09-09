import React, { useCallback, useEffect, useState } from 'react';
import { getRegister, markAttendance, RegisterRow, AttendanceStatus } from '../api';
import { formatTime, formatDuration, formatDateDdMmmYy, todayInputValue } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';

const STATUSES: AttendanceStatus[] = ['PRESENT', 'HALF_DAY', 'WFH', 'ON_LEAVE', 'ABSENT'];

/** Everyone's attendance for one day, with a way to correct it by hand. */
const AttendanceRegister: React.FC = () => {
  const [date, setDate] = useState(todayInputValue());
  const [rows, setRows] = useState<RegisterRow[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [marking, setMarking] = useState<RegisterRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRegister(date);
      setRows(res.data.rows);
      setSummary(res.data.summary);
      setError('');
    } catch (err) {
      setError(errorMessage(err, 'Could not load the register'));
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = () => {
    const header = ['Staff', 'Designation', 'Status', 'In', 'Out', 'Worked (minutes)', 'Punches'];
    const body = rows.map((r) => [
      r.staffName,
      r.designation ?? '',
      r.status,
      r.checkedInAt ? formatTime(r.checkedInAt) : '',
      r.checkOutAt ? formatTime(r.checkOutAt) : '',
      String(r.workedMinutes),
      String(r.punchCount),
    ]);
    // Every field is quoted and inner quotes doubled — a designation with a
    // comma in it would otherwise split into two columns.
    const csv = [header, ...body]
      .map((line) => line.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(','))
      .join('\r\n');

    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-${date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Attendance register</h1>
          <p className="text-sm text-gray-500 mt-0.5">{formatDateDdMmmYy(date)}</p>
        </div>
        <div className="flex gap-2">
          <input
            className="input-field w-auto"
            type="date"
            value={date}
            max={todayInputValue()}
            onChange={(e) => setDate(e.target.value)}
          />
          <button className="btn-secondary" onClick={exportCsv} disabled={rows.length === 0}>
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Present', value: summary.present ?? 0 },
          { label: 'On leave', value: summary.onLeave ?? 0 },
          { label: 'Half day', value: summary.halfDay ?? 0 },
          { label: 'Not marked', value: summary.absent ?? 0 },
        ].map((tile) => (
          <div key={tile.label} className="card">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{tile.label}</div>
            <div className="mt-1 text-xl font-semibold">{tile.value}</div>
          </div>
        ))}
      </div>

      {error && <div className="card text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">Staff</th>
                <th className="table-header">Status</th>
                <th className="table-header">In</th>
                <th className="table-header">Out</th>
                <th className="table-header text-right">Worked</th>
                <th className="table-header text-right">Punches</th>
                <th className="table-header" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.staffId} className="hover:bg-gray-50">
                  <td className="table-cell">
                    <div className="font-medium">{r.staffName}</div>
                    {r.designation && <div className="text-xs text-gray-400">{r.designation}</div>}
                  </td>
                  <td className="table-cell"><StatusBadge status={r.status} /></td>
                  <td className="table-cell tabular-nums">{formatTime(r.checkedInAt)}</td>
                  <td className="table-cell tabular-nums">{formatTime(r.checkOutAt)}</td>
                  <td className="table-cell text-right tabular-nums">{formatDuration(r.workedMinutes)}</td>
                  <td className="table-cell text-right tabular-nums">{r.punchCount || '—'}</td>
                  <td className="table-cell text-right">
                    <button className="text-brand-600 hover:underline text-sm" onClick={() => setMarking(r)}>
                      Mark
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MarkModal
        row={marking}
        date={date}
        onClose={() => setMarking(null)}
        onSaved={() => {
          setMarking(null);
          load();
        }}
      />
    </div>
  );
};

const MarkModal: React.FC<{
  row: RegisterRow | null;
  date: string;
  onClose: () => void;
  onSaved: () => void;
}> = ({ row, date, onClose, onSaved }) => {
  const [status, setStatus] = useState<AttendanceStatus>('PRESENT');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (row) {
      setStatus(row.status);
      setNotes(row.notes ?? '');
      setError('');
    }
  }, [row]);

  const submit = async () => {
    if (!row) return;
    setBusy(true);
    try {
      await markAttendance({ staffId: row.staffId, date, status, notes });
      onSaved();
    } catch (err) {
      setError(errorMessage(err, 'Could not save'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={!!row} title={row ? `Mark ${row.staffName}` : ''} onClose={onClose}>
      {row && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{formatDateDdMmmYy(date)}</p>

          <div>
            <label className="label">Status</label>
            <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value as AttendanceStatus)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Note</label>
            <input className="input-field" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Casual leave, client site…" />
          </div>

          <p className="text-xs text-gray-500">
            Marking a day by hand does not change the punches already recorded against it.
          </p>

          {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

          <div className="flex gap-2 justify-end">
            <button className="btn-secondary" onClick={onClose} disabled={busy}>Cancel</button>
            <button className="btn-primary" onClick={submit} disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
          </div>
        </div>
      )}
    </Modal>
  );
};

export default AttendanceRegister;
