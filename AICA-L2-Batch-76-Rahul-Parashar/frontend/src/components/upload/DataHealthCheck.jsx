import { CheckCircle2, Circle, ArrowLeft } from 'lucide-react';
import { useFinancials } from '../../context/FinancialsContext';
import { FIELD_LABELS } from '../../lib/fieldDictionary';

const SECTION_LABELS = {
  balance_sheet: 'Balance Sheet',
  profit_and_loss: 'Profit & Loss',
  quarterly: 'Quarterly Results',
  ratios: 'Ratio Analysis',
};

const SECTION_ORDER = ['balance_sheet', 'profit_and_loss', 'quarterly', 'ratios'];

export default function DataHealthCheck() {
  const { financials, setDashboardReady, displayUnit, setDisplayUnit, resetFile } = useFinancials();

  if (!financials) return null;

  const grouped = {};
  for (const entry of financials.fieldReport) {
    if (!grouped[entry.section]) grouped[entry.section] = [];
    grouped[entry.section].push(entry);
  }

  const totalFound = financials.fieldReport.filter((f) => f.found).length;
  const totalFields = financials.fieldReport.length;

  return (
    <div className="min-h-screen bg-stone px-4 py-10 flex justify-center">
      <div className="w-full max-w-3xl">
        <button
          onClick={resetFile}
          className="flex items-center gap-1.5 text-sm text-slate hover:text-verdigris mb-6 font-body"
        >
          <ArrowLeft size={14} /> Upload a different file
        </button>

        <div className="bg-paper rounded-lg p-6 mb-6">
          <h1 className="font-heading text-xl font-semibold text-ink">Data Health Check</h1>
          <p className="text-slate text-sm mt-1 font-body">
            {financials.company} — {financials.basis} basis. Sourced from{' '}
            <span className="font-mono-figures">{financials.source_sheet.financials}</span>
            {financials.source_sheet.ratios ? (
              <>
                {' '}
                and <span className="font-mono-figures">{financials.source_sheet.ratios}</span>
              </>
            ) : null}
            . Detected periods:{' '}
            <span className="font-mono-figures">{financials.periods.annual.join(', ') || 'none'}</span>
            {financials.periods.quarterly.length > 0 && (
              <>
                {' '}
                (+ quarterly: <span className="font-mono-figures">{financials.periods.quarterly.join(', ')}</span>)
              </>
            )}
          </p>
          <p className="font-mono-figures text-sm text-verdigris mt-2">
            {totalFound} / {totalFields} fields found
          </p>

          <div className="mt-4 flex items-center gap-3">
            <label className="text-sm text-slate font-body" htmlFor="unit-select">
              Display unit
            </label>
            <select
              id="unit-select"
              value={displayUnit}
              onChange={(e) => setDisplayUnit(e.target.value)}
              className="border border-line rounded-lg px-2 py-1 text-sm font-mono-figures bg-paper focus:outline-none focus:ring-2 focus:ring-verdigris"
            >
              <option value="L">₹ Lakhs</option>
              <option value="Cr">₹ Crore</option>
            </select>
          </div>
        </div>

        <div className="space-y-4">
          {SECTION_ORDER.filter((s) => grouped[s]).map((section) => (
            <div key={section} className="bg-paper rounded-lg p-4">
              <h2 className="font-heading text-sm font-semibold text-ink mb-2">{SECTION_LABELS[section]}</h2>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
                {grouped[section].map((entry) => (
                  <li key={entry.key} className="flex items-center gap-2 text-sm py-0.5 border-b border-line/60">
                    {entry.found ? (
                      <CheckCircle2 size={14} className="text-verdigris shrink-0" />
                    ) : (
                      <Circle size={14} className="text-mist shrink-0" />
                    )}
                    <span className={entry.found ? 'text-ink font-body' : 'text-slate font-body'}>
                      {FIELD_LABELS[entry.key] || entry.key}
                    </span>
                    {!entry.found && <span className="text-mist text-xs ml-auto">Not found</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={() => setDashboardReady(true)}
            className="bg-verdigris text-paper font-body font-medium px-5 py-2.5 rounded-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-verdigris focus:ring-offset-2 focus:ring-offset-stone"
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
