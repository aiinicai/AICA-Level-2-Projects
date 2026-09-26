import React, { useCallback, useEffect, useState } from 'react';
import { getPunches, recordPunch, getMonthlyAttendance, PunchDay, MonthlyAttendance } from '../api';
import { formatTime, formatDuration, formatDateDdMmmYy } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import StatusBadge from '../components/StatusBadge';

/**
 * Ask the browser where the phone is, and give up rather than block.
 *
 * Location is proof of where someone was when they punched, not a gate on
 * punching: indoors or with permission refused the coordinates simply come
 * back null and the punch is still recorded.
 */
const LOCATION_TIMEOUT_MS = 8000;

function currentPosition(): Promise<GeolocationPosition | null> {
  if (!('geolocation' in navigator)) return Promise.resolve(null);
  return new Promise((resolve) => {
    // Our own deadline as well as the API's. Some browsers — a locked-down
    // profile, an embedded webview, a permission prompt that is never shown —
    // call neither callback, and a punch button that hangs for ever is worse
    // than one that records without coordinates.
    let settled = false;
    const finish = (value: GeolocationPosition | null) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    setTimeout(() => finish(null), LOCATION_TIMEOUT_MS);
    navigator.geolocation.getCurrentPosition(
      (pos) => finish(pos),
      () => finish(null),
      { enableHighAccuracy: true, timeout: LOCATION_TIMEOUT_MS, maximumAge: 60_000 },
    );
  });
}

const Attendance: React.FC = () => {
  const [day, setDay] = useState<PunchDay | null>(null);
  const [month, setMonth] = useState<MonthlyAttendance | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  // The current month, read at call time rather than captured from a render —
  // a phone left open across midnight on the last of the month should roll
  // over rather than keep asking for the old one.
  const thisMonth = () => {
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
  };

  const load = useCallback(async () => {
    try {
      const [punchRes, monthRes] = await Promise.all([getPunches(), getMonthlyAttendance(thisMonth())]);
      setDay(punchRes.data);
      setMonth(monthRes.data);
      setError('');
    } catch (err) {
      setError(errorMessage(err, 'Could not load your attendance'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const punch = async () => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const position = await currentPosition();
      const res = await recordPunch({
        latitude: position?.coords.latitude ?? null,
        longitude: position?.coords.longitude ?? null,
        locationAccuracy: position?.coords.accuracy ?? null,
      });
      setDay(res.data);
      setNotice(`Checked ${res.data.direction === 'IN' ? 'in' : 'out'} at ${formatTime(new Date())}`);
      // The month totals move with the punch, so they are refetched rather
      // than left showing yesterday's figure.
      const monthRes = await getMonthlyAttendance(thisMonth());
      setMonth(monthRes.data);
    } catch (err) {
      // A 409 is the debounce refusing a double-tap; it carries the true state
      // of the day, so the screen is corrected rather than just apologising.
      const conflict = (err as { response?: { status?: number; data?: PunchDay } }).response;
      if (conflict?.status === 409 && conflict.data) setDay(conflict.data);
      setError(errorMessage(err, 'Could not record the punch'));
    } finally {
      setBusy(false);
    }
  };

  const goingIn = day?.nextDirection !== 'OUT';

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Attendance</h1>
        <p className="text-sm text-gray-500 mt-0.5">{formatDateDdMmmYy(day?.date ?? new Date())}</p>
      </div>

      <div className="card text-center py-8">
        <div className="text-sm text-gray-500">
          {day?.firstIn ? `First in at ${formatTime(day.firstIn)}` : 'Not checked in yet today'}
        </div>
        <div className="text-3xl font-semibold text-gray-900 mt-2 tabular-nums">
          {formatDuration(day?.workedMinutes)}
        </div>
        <div className="text-xs text-gray-500 mt-1">worked so far</div>

        <button
          onClick={punch}
          disabled={busy}
          className={`mt-6 w-full sm:w-64 mx-auto block text-white font-semibold rounded-xl py-4 text-lg transition-colors disabled:opacity-60 ${
            goingIn ? 'bg-green-600 hover:bg-green-700' : 'bg-brand-700 hover:bg-brand-800'
          }`}
        >
          {busy ? 'Recording…' : goingIn ? 'Check in' : 'Check out'}
        </button>

        {notice && <p className="text-sm text-green-700 mt-3">{notice}</p>}
        {error && <p role="alert" className="text-sm text-red-700 mt-3">{error}</p>}
      </div>

      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Today&rsquo;s punches</h2>
        {!day || day.punches.length === 0 ? (
          <div className="card text-sm text-gray-500">Nothing recorded yet.</div>
        ) : (
          <div className="space-y-1.5">
            {day.punches.map((p) => (
              <div key={p.id} className="card py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`badge ${p.direction === 'IN' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}>
                    {p.direction === 'IN' ? 'Check in' : 'Check out'}
                  </span>
                  <span className="text-sm font-medium tabular-nums">{formatTime(p.punchedAt)}</span>
                </div>
                {p.latitude && p.longitude && (
                  <span className="text-xs text-gray-400">
                    {Number(p.latitude).toFixed(4)}, {Number(p.longitude).toFixed(4)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {month && (
        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-gray-700">This month</h2>
            <span className="text-xs text-gray-500">
              {month.summary.daysPresent} days · {month.summary.workedHours}h
            </span>
          </div>

          {month.days.length === 0 ? (
            <div className="card text-sm text-gray-500">No days recorded this month.</div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Date</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">In</th>
                    <th className="table-header">Out</th>
                    <th className="table-header text-right">Worked</th>
                  </tr>
                </thead>
                <tbody>
                  {[...month.days].reverse().map((d) => (
                    <tr key={d.date}>
                      <td className="table-cell whitespace-nowrap">{formatDateDdMmmYy(d.date)}</td>
                      <td className="table-cell"><StatusBadge status={d.status} /></td>
                      <td className="table-cell tabular-nums">{formatTime(d.checkedInAt)}</td>
                      <td className="table-cell tabular-nums">{formatTime(d.checkOutAt)}</td>
                      <td className="table-cell text-right tabular-nums">{formatDuration(d.workedMinutes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
};

export default Attendance;
