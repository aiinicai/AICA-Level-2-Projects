import { useState } from 'react';
import { X } from 'lucide-react';
import { parseWorkbookFromArrayBuffer } from '../../lib/parseWorkbook';
import { useFinancials } from '../../context/FinancialsContext';

const MANUAL_METRICS = [
  { key: 'total_revenue', label: 'Revenue' },
  { key: 'pat', label: 'PAT' },
];

export default function PeerUploadPanel({ onClose }) {
  const { setPeer, peer } = useFinancials();
  const [tab, setTab] = useState('workbook');
  const [peerName, setPeerName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const [manualYears, setManualYears] = useState(['FY24', 'FY25']);
  const [manualValues, setManualValues] = useState({}); // { metricKey: { period: value } }

  async function handleWorkbookUpload(file) {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const buffer = await file.arrayBuffer();
      const parsed = await parseWorkbookFromArrayBuffer(buffer);
      setPeer({ name: peerName || parsed.company, financials: parsed, source: 'workbook' });
    } catch (err) {
      setError(err.message || 'Could not parse this file.');
    } finally {
      setLoading(false);
    }
  }

  function applyManual() {
    const balance_sheet = {};
    const profit_and_loss = { total_revenue: {}, pat: {} };
    for (const metric of MANUAL_METRICS) {
      profit_and_loss[metric.key] = {};
      for (const year of manualYears) {
        profit_and_loss[metric.key][year] = manualValues[metric.key]?.[year] ?? null;
      }
    }
    setPeer({
      name: peerName || 'Peer Company',
      source: 'manual',
      financials: {
        company: peerName || 'Peer Company',
        periods: { annual: manualYears, quarterly: [] },
        balance_sheet,
        profit_and_loss,
        quarterly: {},
        ratios: {},
        derived_metrics: {},
      },
    });
  }

  return (
    <div className="fixed inset-0 z-50 bg-ink/40 flex items-center justify-center px-4">
      <div className="bg-paper rounded-lg w-full max-w-lg p-5 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate hover:text-ink" aria-label="Close">
          <X size={18} />
        </button>
        <h2 className="font-heading text-lg font-semibold text-ink mb-1">Compare with a peer</h2>
        <p className="text-xs text-slate font-body mb-4">
          Peer data lives only in this browser session (not saved to disk) — it clears on refresh. This is a
          deliberate MVP choice to avoid stale comparisons, not an oversight.
        </p>

        {peer && (
          <div className="mb-4 flex items-center justify-between bg-verdigris-soft rounded-lg px-3 py-2 text-sm font-body">
            <span>
              Comparing against <strong>{peer.name}</strong>
            </span>
            <button onClick={() => setPeer(null)} className="text-clay text-xs underline">
              Remove
            </button>
          </div>
        )}

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setTab('workbook')}
            className={`px-3 py-1.5 rounded-lg text-sm font-body ${tab === 'workbook' ? 'bg-verdigris text-paper' : 'bg-stone text-slate'}`}
          >
            Upload workbook
          </button>
          <button
            onClick={() => setTab('manual')}
            className={`px-3 py-1.5 rounded-lg text-sm font-body ${tab === 'manual' ? 'bg-verdigris text-paper' : 'bg-stone text-slate'}`}
          >
            Manual / CSV entry
          </button>
          <button
            disabled
            title="Coming soon — live competitor data fetch is not built in this pass"
            className="px-3 py-1.5 rounded-lg text-sm font-body bg-stone text-mist cursor-not-allowed"
          >
            Fetch online (soon)
          </button>
        </div>

        <input
          value={peerName}
          onChange={(e) => setPeerName(e.target.value)}
          placeholder="Peer company name"
          className="w-full border border-line rounded-lg px-3 py-2 text-sm font-body mb-3 focus:outline-none focus:ring-2 focus:ring-verdigris"
        />

        {tab === 'workbook' && (
          <div>
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => handleWorkbookUpload(e.target.files?.[0])}
              className="text-sm font-body"
            />
            {loading && <p className="text-xs text-slate mt-2">Parsing…</p>}
            {error && <p className="text-xs text-clay mt-2">{error}</p>}
          </div>
        )}

        {tab === 'manual' && (
          <div>
            <table className="w-full text-sm font-mono-figures mb-3">
              <thead>
                <tr>
                  <th className="text-left font-body text-slate text-xs">Metric</th>
                  {manualYears.map((y) => (
                    <th key={y} className="text-left font-body text-slate text-xs px-1">
                      {y}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MANUAL_METRICS.map((m) => (
                  <tr key={m.key}>
                    <td className="font-body text-ink py-1">{m.label}</td>
                    {manualYears.map((y) => (
                      <td key={y} className="px-1">
                        <input
                          type="number"
                          className="w-20 border border-line rounded px-1.5 py-1 text-xs"
                          value={manualValues[m.key]?.[y] ?? ''}
                          onChange={(e) =>
                            setManualValues((prev) => ({
                              ...prev,
                              [m.key]: { ...prev[m.key], [y]: e.target.value === '' ? null : Number(e.target.value) },
                            }))
                          }
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={applyManual}
              className="bg-verdigris text-paper text-sm font-body px-3 py-1.5 rounded-lg hover:opacity-90"
            >
              Apply peer data
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
