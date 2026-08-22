import { useRef, useState } from 'react';
import { UploadCloud, FileSpreadsheet, AlertTriangle } from 'lucide-react';
import { parseWorkbookFromArrayBuffer } from '../../lib/parseWorkbook';
import { useFinancials } from '../../context/FinancialsContext';
import sampleWorkbookUrl from '../../../test-fixtures/sample.xlsx?url';

export default function UploadScreen() {
  const { setFinancials } = useFinancials();
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    const okType = /\.(xlsx|xls)$/i.test(file.name);
    if (!okType) {
      setError('Please upload an .xlsx or .xls file.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const buffer = await file.arrayBuffer();
      const result = await parseWorkbookFromArrayBuffer(buffer);
      setFinancials(result);
    } catch (err) {
      console.error(err);
      setError(err?.message || 'Could not parse this file.');
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadSample() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(sampleWorkbookUrl);
      if (!res.ok) throw new Error('Sample file not found.');
      const buffer = await res.arrayBuffer();
      const result = await parseWorkbookFromArrayBuffer(buffer);
      setFinancials(result);
    } catch (err) {
      console.error(err);
      setError('Could not load the demo file.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone px-4">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h1 className="font-heading text-2xl font-semibold text-ink">CFO Financial Dashboard</h1>
          <p className="text-slate mt-2 text-sm">
            Upload a Ratio-file workbook (sheets named "Financials_Standalone" / "Financials_Consol") to build a
            live, drillable dashboard from it — parsed entirely in your browser.
          </p>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`rounded-lg border-2 border-dashed p-12 text-center cursor-pointer transition-colors bg-paper
            ${dragActive ? 'border-verdigris bg-verdigris-soft' : 'border-mist'}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          {loading ? (
            <p className="font-body text-slate">Parsing workbook…</p>
          ) : (
            <>
              <UploadCloud className="mx-auto mb-3 text-verdigris" size={32} />
              <p className="font-body text-ink font-medium">Drop your Ratio.xlsx file here</p>
              <p className="font-body text-slate text-sm mt-1">or click to browse</p>
            </>
          )}
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg bg-clay-soft border border-clay/30 p-3 text-sm text-ink">
            <AlertTriangle className="text-clay shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-6 text-center">
          <button
            onClick={handleLoadSample}
            className="inline-flex items-center gap-1.5 text-sm text-slate hover:text-verdigris font-body"
          >
            <FileSpreadsheet size={14} />
            Load demo data (Endurance Technologies sample)
          </button>
        </div>
      </div>
    </div>
  );
}
