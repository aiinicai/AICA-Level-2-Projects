import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getDashboard, DashboardData } from '../api';
import { formatRupeesUI, formatDateDdMmmYy } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import { useAuth } from '../contexts/AuthContext';
import StatusBadge from '../components/StatusBadge';

const Tile: React.FC<{ label: string; value: string; hint?: string; tone?: 'default' | 'warn' }> = ({
  label,
  value,
  hint,
  tone = 'default',
}) => (
  <div className="card">
    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</div>
    <div className={`mt-1.5 text-2xl font-semibold ${tone === 'warn' ? 'text-red-600' : 'text-gray-900'}`}>
      {value}
    </div>
    {hint && <div className="mt-1 text-xs text-gray-500">{hint}</div>}
  </div>
);

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then((res) => setData(res.data))
      .catch((err) => setError(errorMessage(err, 'Could not load the dashboard')));
  }, []);

  if (error) return <div className="card text-sm text-red-700">{error}</div>;
  if (!data) return <div className="text-sm text-gray-500">Loading…</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">
          Good day{user?.staffName ? `, ${user.staffName.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">{formatDateDdMmmYy(data.date)}</p>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Invoicing</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Tile label="Billed this month" value={`₹${formatRupeesUI(data.invoicing.billedThisMonth)}`} />
          <Tile label="Collected" value={`₹${formatRupeesUI(data.invoicing.collectedThisMonth)}`} hint="Against this month's bills" />
          <Tile
            label="Outstanding"
            value={`₹${formatRupeesUI(data.invoicing.outstanding)}`}
            hint={`${data.invoicing.openCount} open invoice${data.invoicing.openCount === 1 ? '' : 's'}`}
          />
          <Tile
            label="Overdue"
            value={`₹${formatRupeesUI(data.invoicing.overdue)}`}
            tone={data.invoicing.overdue > 0 ? 'warn' : 'default'}
            hint="Past the due date"
          />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Attendance today</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Tile label="Present" value={String(data.attendance.presentToday)} hint={`of ${data.attendance.activeStaff} staff`} />
          <Tile label="Not marked" value={String(data.attendance.absentToday)} />
          <Tile label="Hours logged" value={`${data.attendance.hoursToday}h`} hint="Completed shifts only" />
          <div className="card flex flex-col justify-center">
            <Link to="/attendance" className="btn-primary text-center">Punch in / out</Link>
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700">Recent invoices</h2>
          <Link to="/invoices" className="text-sm text-brand-600 hover:underline">View all</Link>
        </div>

        {data.recentInvoices.length === 0 ? (
          <div className="card text-sm text-gray-500">No invoices yet.</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Invoice</th>
                  <th className="table-header">Client</th>
                  <th className="table-header">Date</th>
                  <th className="table-header text-right">Total</th>
                  <th className="table-header">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.recentInvoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="table-cell font-medium whitespace-nowrap">{inv.invoiceNumber}</td>
                    <td className="table-cell">{inv.clientName}</td>
                    <td className="table-cell whitespace-nowrap">{formatDateDdMmmYy(inv.invoiceDate)}</td>
                    <td className="table-cell text-right whitespace-nowrap">₹{formatRupeesUI(inv.totalAmount)}</td>
                    <td className="table-cell"><StatusBadge status={inv.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Dashboard;
