import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface HistoryRow {
  id: string;
  clientNameSnapshot: string;
  generatedAt: string;
  templates: { template: { name: string } }[];
}

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    load();
  }, [dateFrom, dateTo]);

  async function load() {
    const r = await api.get('/history', { params: { dateFrom, dateTo } });
    setRows(r.data.data);
  }

  return (
    <div className="h-full overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-lg font-semibold">Generation History</h1>
        <a
          href={`/api/history/export?dateFrom=${dateFrom}&dateTo=${dateTo}`}
          className="text-sm px-3 py-1.5 border rounded-md"
        >
          Export to Excel
        </a>
      </div>

      <div className="flex gap-2 mb-4">
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded-md px-2 py-1.5 text-sm bg-transparent" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded-md px-2 py-1.5 text-sm bg-transparent" />
      </div>

      <table className="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="p-2 text-left">Date</th>
            <th className="p-2 text-left">Client</th>
            <th className="p-2 text-left">Templates</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-gray-100 dark:border-gray-800">
              <td className="p-2">{new Date(r.generatedAt).toLocaleString()}</td>
              <td className="p-2">{r.clientNameSnapshot}</td>
              <td className="p-2 text-xs italic text-gray-500">{r.templates.map((t) => t.template.name).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
