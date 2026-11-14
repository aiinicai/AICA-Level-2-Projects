import React, { useState, useMemo } from 'react';
import { RateRecord, RateCorrection, MetalType } from '../../types';
import {
  formatINR,
  formatDisplayDate,
} from '../../utils/formatters';
import { parsePriceHistoryCSV } from '../../utils/csvParser';
import {
  ibjaRateService,
  buildIbjaRateRecords,
  IbjaRatesFetchResult,
} from '../../services/ibjaRateService';
import { uploadRatesToSupabase, isSupabaseConfigured } from '../../db/repository';
import {
  Search,
  Filter,
  AlertTriangle,
  Upload,
  Edit3,
  CheckCircle,
  ExternalLink,
  History,
  Info,
  Radio,
  Zap,
  RefreshCw,
  Check,
  Calendar,
  CloudUpload,
} from 'lucide-react';

interface PriceHistoryScreenProps {
  rates: RateRecord[];
  corrections: RateCorrection[];
  onImportSupplementalRates: (rates: RateRecord[]) => void;
  onSaveCorrection: (correction: RateCorrection) => void;
  onRatesUpdated?: (newRates: RateRecord[], marketDate: string) => void;
  isSuperUser?: boolean;
  onRequireAuth?: () => void;
}

export const PriceHistoryScreen: React.FC<PriceHistoryScreenProps> = ({
  rates,
  corrections,
  onImportSupplementalRates,
  onSaveCorrection,
  onRatesUpdated,
  isSuperUser = true,
  onRequireAuth,
}) => {
  const [search, setSearch] = useState('');
  const [metalFilter, setMetalFilter] = useState<'ALL' | MetalType>('ALL');
  const [purityFilter, setPurityFilter] = useState<'ALL' | string>('ALL');
  const [sourceFilter, setSourceFilter] = useState<'ALL' | string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Manual correction modal state
  const [correctingRate, setCorrectingRate] = useState<RateRecord | null>(null);
  const [newPricePerGram, setNewPricePerGram] = useState<string>('');
  const [correctionReason, setCorrectionReason] = useState<string>('');

  // Supplemental upload state
  const [isUploading, setIsUploading] = useState(false);

  // IBJA rate fetch & preview modal state
  const [isFetchingIbja, setIsFetchingIbja] = useState(false);
  const [ibjaFetchResult, setIbjaFetchResult] = useState<IbjaRatesFetchResult | null>(null);
  const [isIbjaModalOpen, setIsIbjaModalOpen] = useState(false);
  const [editDate, setEditDate] = useState('');
  const [editGold999, setEditGold999] = useState('');
  const [editGold995, setEditGold995] = useState('');
  const [editSilver999, setEditSilver999] = useState('');
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Supabase cloud rates push state
  const [isUploadingToCloud, setIsUploadingToCloud] = useState(false);
  const [cloudRatesNotice, setCloudRatesNotice] = useState<{ success: boolean; message: string } | null>(null);

  const handlePushRatesToCloud = async () => {
    setIsUploadingToCloud(true);
    setCloudRatesNotice(null);
    try {
      const res = await uploadRatesToSupabase();
      setCloudRatesNotice(res);
    } catch (err: any) {
      setCloudRatesNotice({ success: false, message: err.message || 'Rates upload failed' });
    } finally {
      setIsUploadingToCloud(false);
    }
  };

  // Coverage statistics
  const stats = useMemo(() => {
    let gold995 = 0;
    let gold999 = 0;
    let silver999 = 0;
    let nseCount = 0;
    let ibjaCount = 0;

    for (const r of rates) {
      if (r.metal === 'GOLD') {
        if (r.purity === 995) gold995++;
        if (r.purity === 999) gold999++;
      } else if (r.metal === 'SILVER') {
        if (r.purity === 999) silver999++;
      }

      if (r.sourceType === 'NSE') nseCount++;
      else if (r.sourceType === 'IBJA') ibjaCount++;
    }

    return {
      total: rates.length,
      gold995,
      gold999,
      silver999,
      nseCount,
      ibjaCount,
    };
  }, [rates]);

  // Filtered rates
  const filteredRates = useMemo(() => {
    return rates.filter((r) => {
      if (metalFilter !== 'ALL' && r.metal !== metalFilter) return false;
      if (purityFilter !== 'ALL' && r.purity.toString() !== purityFilter) return false;
      if (sourceFilter !== 'ALL' && r.sourceType !== sourceFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchDate = r.date.includes(q);
        const matchSource = r.source.toLowerCase().includes(q);
        if (!matchDate && !matchSource) return false;
      }
      return true;
    });
  }, [rates, metalFilter, purityFilter, sourceFilter, search]);

  const totalPages = Math.ceil(filteredRates.length / pageSize) || 1;
  const paginatedRates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredRates.slice(start, start + pageSize);
  }, [filteredRates, page, pageSize]);

  // Handle manual correction
  const handleOpenCorrection = (r: RateRecord) => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    setCorrectingRate(r);
    setNewPricePerGram(r.pricePerGram.toString());
    setCorrectionReason('');
  };

  const handleSubmitCorrection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!correctingRate) return;

    const newPrice = parseFloat(newPricePerGram);
    if (isNaN(newPrice) || newPrice <= 0) {
      alert('Please enter a valid positive price per gram.');
      return;
    }

    if (!correctionReason.trim()) {
      alert('Please provide an audit reason for modifying historical market data.');
      return;
    }

    const correction: RateCorrection = {
      id: `CORR-${Date.now()}`,
      rateId: correctingRate.id,
      date: correctingRate.date,
      metal: correctingRate.metal,
      purity: correctingRate.purity,
      originalPricePerGram: correctingRate.pricePerGram,
      correctedPricePerGram: newPrice,
      reason: correctionReason.trim(),
      correctedAt: new Date().toISOString(),
    };

    onSaveCorrection(correction);
    setCorrectingRate(null);
  };

  // Supplemental CSV file upload
  const handleSupplementalUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = parsePriceHistoryCSV(text);
        if (parsed.skippedRows.length > 0) {
          alert(`Warning during parse: ${parsed.skippedRows.length} rows encountered issues.`);
        }
        onImportSupplementalRates(parsed.normalizedRecords);
        alert(`Successfully imported and merged ${parsed.normalizedRecords.length} price observations.`);
      } catch (err: any) {
        alert(`Failed to parse CSV file: ${err.message}`);
      } finally {
        setIsUploading(false);
      }
    };
    reader.readAsText(file);
  };

  // IBJA Rates Live Trigger
  const handleTriggerIbjaFetch = async () => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    setIsFetchingIbja(true);
    setSuccessNotice(null);
    try {
      const result = await ibjaRateService.fetchLatestRates();
      setIbjaFetchResult(result);
      setEditDate(result.marketDate);
      setEditGold999(result.gold999Per10g.toString());
      setEditGold995(result.gold995Per10g.toString());
      setEditSilver999(result.silver999PerKg.toString());
      setIsIbjaModalOpen(true);
    } catch (err: any) {
      alert(`IBJA rates service notice: ${err.message || 'Unable to contact rate gateway'}`);
    } finally {
      setIsFetchingIbja(false);
    }
  };

  // Confirm IBJA Ingestion
  const handleConfirmIbjaRates = () => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    const g999 = parseFloat(editGold999);
    const g995 = parseFloat(editGold995);
    const s999 = parseFloat(editSilver999);

    if (isNaN(g999) || g999 <= 0 || isNaN(g995) || g995 <= 0 || isNaN(s999) || s999 <= 0) {
      alert('Please enter valid positive rate values for Gold and Silver.');
      return;
    }

    const records = buildIbjaRateRecords(
      editDate,
      g999,
      g995,
      s999,
      ibjaFetchResult?.sourceUrl || 'https://ibjarates.com/'
    );

    onImportSupplementalRates(records);
    if (onRatesUpdated) {
      onRatesUpdated(records, editDate);
    }

    setIsIbjaModalOpen(false);
    setSuccessNotice(
      `Successfully ingested official IBJA PM closing rates for ${editDate}: Gold 999 (₹${(g999 / 10).toFixed(2)}/g), Gold 995 (₹${(g995 / 10).toFixed(2)}/g), Silver 999 (₹${(s999 / 1000).toFixed(3)}/g).`
    );
  };

  return (
    <div className="space-y-5">
      {/* Public Read-Only Notice */}
      {!isSuperUser && (
        <div className="bg-amber-50/70 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-amber-700 font-bold">👁️</span>
            <span>
              <strong>Public Price Archive:</strong> Viewing 5,666+ historical and live closing benchmark rates in read-only mode.
              Super User login (<strong>kosamgo@gmail.com</strong>) is required to fetch and ingest today's IBJA closing rates or upload supplemental CSVs.
            </span>
          </div>
          {onRequireAuth && (
            <button
              type="button"
              onClick={onRequireAuth}
              className="px-3 py-1 text-xs font-semibold text-[#B88B2A] bg-white border border-[#D4AF37]/50 rounded-lg hover:bg-stone-50 shrink-0 shadow-2xs"
            >
              Super User Login
            </button>
          )}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-stone-900 tracking-tight flex items-center gap-2">
            <span>Historical Price Dataset</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
              {stats.total.toLocaleString('en-IN')} observations
            </span>
          </h2>
          <p className="text-xs text-stone-500">
            Real institutional bullion settlement rates: 01-Jan-2019 through present
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick IBJA Fetch button in header */}
          <button
            type="button"
            onClick={handleTriggerIbjaFetch}
            disabled={isFetchingIbja}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] disabled:opacity-60 rounded-lg shadow-2xs transition-colors cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{isFetchingIbja ? 'Querying...' : "Fetch Today's IBJA"}</span>
          </button>

          {/* Upload Supplemental CSV */}
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 rounded-lg shadow-2xs transition-colors">
            <Upload className="w-3.5 h-3.5 text-[#B88B2A]" />
            <span>{isUploading ? 'Importing...' : 'Supplemental CSV'}</span>
            <input
              type="file"
              accept=".csv"
              onChange={handleSupplementalUpload}
              className="hidden"
            />
          </label>

          {/* Push to Supabase Cloud */}
          {isSupabaseConfigured() && (
            <button
              type="button"
              onClick={handlePushRatesToCloud}
              disabled={isUploadingToCloud}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 disabled:opacity-60 rounded-lg shadow-2xs transition-colors cursor-pointer"
              title="Upload all 5,666 historical price records to Supabase"
            >
              <CloudUpload className={`w-3.5 h-3.5 ${isUploadingToCloud ? 'animate-spin' : ''}`} />
              <span>{isUploadingToCloud ? 'Pushing Rates...' : 'Push to Supabase'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Cloud Rates Push Notice */}
      {cloudRatesNotice && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between border ${
            cloudRatesNotice.success
              ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
              : 'bg-amber-50 text-amber-900 border-amber-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {cloudRatesNotice.success ? (
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span className="font-medium">{cloudRatesNotice.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setCloudRatesNotice(null)}
            className="text-stone-400 hover:text-stone-700 font-bold ml-2 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* IBJA Free Daily PM Rates Service Panel */}
      <div className="bg-white p-4 rounded-xl border border-[#D4AF37]/50 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#B88B2A]" />
              <h3 className="text-xs font-bold text-stone-900">
                IBJA Daily PM Closing Rates (Free Institutional Benchmark)
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active Free Service
              </span>
            </div>
            <p className="text-[11px] text-stone-600 max-w-2xl leading-relaxed">
              Directly sources official closing benchmark rates published once per trading day by the{' '}
              <strong>India Bullion and Jewellers Association (IBJA)</strong> for Gold 999 (₹/10g), Gold 995 (₹/10g), and Silver 999 (₹/kg).
              Rates are converted to ₹/gram with verified exchange session tags and zero API key requirement.
            </p>
          </div>

          <button
            type="button"
            onClick={handleTriggerIbjaFetch}
            disabled={isFetchingIbja}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] disabled:opacity-60 rounded-lg shadow-2xs transition-colors shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetchingIbja ? 'animate-spin' : ''}`} />
            <span>{isFetchingIbja ? 'Querying IBJA...' : "Fetch Today's IBJA Rates"}</span>
          </button>
        </div>

        {/* Success Notice if triggered */}
        {successNotice && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-2 rounded-lg text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successNotice}</span>
            </div>
            <button
              type="button"
              onClick={() => setSuccessNotice(null)}
              className="text-emerald-600 hover:text-emerald-900 font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
          <div className="bg-[#FAF7F2] p-2.5 rounded-lg border border-stone-200">
            <span className="text-[10px] text-stone-500 font-semibold block uppercase">Target Feed</span>
            <span className="font-bold text-stone-900 flex items-center gap-1 mt-0.5">
              ibjarates.com (Official)
              <a href="https://ibjarates.com" target="_blank" rel="noreferrer" className="text-stone-400 hover:text-stone-700">
                <ExternalLink className="w-3 h-3 inline" />
              </a>
            </span>
            <span className="text-[10px] text-stone-500">PM Closing Session (~17:00 IST)</span>
          </div>

          <div className="bg-[#FAF7F2] p-2.5 rounded-lg border border-stone-200">
            <span className="text-[10px] text-stone-500 font-semibold block uppercase">Normalization Standard</span>
            <span className="font-bold text-stone-900 mt-0.5 block">Standard ₹/gram Conversion</span>
            <span className="text-[10px] text-stone-500">Gold: ÷ 10 | Silver: ÷ 1,000</span>
          </div>

          <div className="bg-[#FAF7F2] p-2.5 rounded-lg border border-stone-200">
            <span className="text-[10px] text-stone-500 font-semibold block uppercase">Gateway & Resilience</span>
            <span className="font-bold text-emerald-700 mt-0.5 block">Vite Proxy + CORS Gateways</span>
            <span className="text-[10px] text-stone-500">Local proxy + AllOrigins + verified fallback</span>
          </div>
        </div>
      </div>

      {/* Dataset Provenance & Coverage Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-[#E7E2DA] shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
            Gold 999 (Pure)
          </span>
          <span className="text-lg font-bold text-stone-900 mt-1 block">
            {stats.gold999.toLocaleString('en-IN')} quotes
          </span>
          <span className="text-[10px] text-stone-500">2019-01-01 through present</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E7E2DA] shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
            Gold 995 (Standard)
          </span>
          <span className="text-lg font-bold text-stone-900 mt-1 block">
            {stats.gold995.toLocaleString('en-IN')} quotes
          </span>
          <span className="text-[10px] text-stone-500">2019-01-01 through present</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E7E2DA] shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
            Silver 999 (1 Kg)
          </span>
          <span className="text-lg font-bold text-stone-900 mt-1 block">
            {stats.silver999.toLocaleString('en-IN')} quotes
          </span>
          <span className="text-[10px] text-stone-500">2019-01-01 through present</span>
        </div>

        <div className="bg-[#FAF7F2] p-3.5 rounded-xl border border-[#D4AF37]/40 shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#B88B2A] block">
            Exchange Sources
          </span>
          <div className="text-xs font-semibold text-stone-800 mt-1 space-y-0.5">
            <div>NSE Spot: {stats.nseCount.toLocaleString('en-IN')} quotes</div>
            <div>IBJA Benchmark: {stats.ibjaCount.toLocaleString('en-IN')} quotes</div>
          </div>
          <span className="text-[10px] text-stone-500 block mt-1">
            Transition on 16-Jun-2026
          </span>
        </div>
      </div>

      {/* Provenance & Gap Notices */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {/* Source Transition Note */}
        <div className="bg-stone-50 p-3.5 rounded-xl border border-stone-200 text-xs text-stone-700 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-stone-900">
            <Info className="w-4 h-4 text-[#B88B2A]" />
            <span>Exchange Transition (16-Jun-2026)</span>
          </div>
          <p className="text-[11px] text-stone-600 leading-relaxed">
            Historical settlement rates originated from <strong>NSE Spot quotations</strong> through{' '}
            <strong>15-Jun-2026</strong>. Starting <strong>16-Jun-2026</strong>, institutional benchmark
            rates transition to <strong>IBJA closing rates</strong>. The valuation engine preserves both
            source provenance tags on every observation.
          </p>
        </div>

        {/* Silver Non-publication Gap Note */}
        <div className="bg-amber-50/60 p-3.5 rounded-xl border border-amber-200 text-xs text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Documented Gap: Silver on 03-Aug-2020</span>
          </div>
          <p className="text-[11px] text-amber-800 leading-relaxed">
            On <strong>03-Aug-2020</strong>, Gold 995 & 999 rates were published by NSE, but Silver had no
            observation. The engine detects this non-publication gap and automatically carries forward
            the preceding closing rate (31-Jul-2020: ₹63.871/g) while flagging the estimate.
          </p>
        </div>
      </div>

      {/* Corrections Log if any */}
      {corrections.length > 0 && (
        <div className="bg-stone-50 p-4 rounded-xl border border-stone-200 space-y-2">
          <h3 className="text-xs font-bold text-stone-900 flex items-center gap-1.5">
            <History className="w-4 h-4 text-[#B88B2A]" />
            Audited Manual Price Corrections ({corrections.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] text-left">
              <thead className="text-stone-600 border-b border-stone-200 font-semibold">
                <tr>
                  <th className="py-1.5 px-2">Date</th>
                  <th className="py-1.5 px-2">Metal</th>
                  <th className="py-1.5 px-2">Purity</th>
                  <th className="py-1.5 px-2">Original ₹/g</th>
                  <th className="py-1.5 px-2">Corrected ₹/g</th>
                  <th className="py-1.5 px-2">Reason</th>
                  <th className="py-1.5 px-2">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                {corrections.map((c) => (
                  <tr key={c.id}>
                    <td className="py-1.5 px-2 font-mono">{c.date}</td>
                    <td className="py-1.5 px-2">{c.metal}</td>
                    <td className="py-1.5 px-2">{c.purity}</td>
                    <td className="py-1.5 px-2 font-mono">₹{c.originalPricePerGram.toFixed(2)}</td>
                    <td className="py-1.5 px-2 font-mono font-bold text-[#B88B2A]">
                      ₹{c.correctedPricePerGram.toFixed(2)}
                    </td>
                    <td className="py-1.5 px-2 text-stone-700">{c.reason}</td>
                    <td className="py-1.5 px-2 text-stone-400 text-[10px]">
                      {new Date(c.correctedAt).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rates Table Filter Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-[#E7E2DA] shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search date (e.g. 2026-10-30) or source..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-[#FAF7F2] border border-stone-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Metal Filter */}
          <select
            value={metalFilter}
            onChange={(e) => {
              setMetalFilter(e.target.value as any);
              setPage(1);
            }}
            className="text-xs bg-[#FAF7F2] border border-stone-200 rounded-lg px-2.5 py-1.5 font-medium text-stone-700 focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Metals</option>
            <option value="GOLD">Gold Only</option>
            <option value="SILVER">Silver Only</option>
          </select>

          {/* Purity Filter */}
          <select
            value={purityFilter}
            onChange={(e) => {
              setPurityFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs bg-[#FAF7F2] border border-stone-200 rounded-lg px-2.5 py-1.5 font-medium text-stone-700 focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Purities</option>
            <option value="999">999 Fineness</option>
            <option value="995">995 Fineness</option>
          </select>

          {/* Source Filter */}
          <select
            value={sourceFilter}
            onChange={(e) => {
              setSourceFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs bg-[#FAF7F2] border border-stone-200 rounded-lg px-2.5 py-1.5 font-medium text-stone-700 focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Sources</option>
            <option value="NSE">NSE Spot</option>
            <option value="IBJA">IBJA Closing</option>
          </select>
        </div>
      </div>

      {/* Rates Table */}
      <div className="bg-white rounded-xl border border-[#E7E2DA] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#FAF7F2] text-stone-600 font-semibold border-b border-stone-200">
              <tr>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Metal</th>
                <th className="py-2.5 px-3">Fineness</th>
                <th className="py-2.5 px-3">Original Quotation</th>
                <th className="py-2.5 px-3 font-semibold text-stone-900">Normalised (₹/gram)</th>
                <th className="py-2.5 px-3">Session</th>
                <th className="py-2.5 px-3">Source & Provenance</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {paginatedRates.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-stone-400">
                    No price records found matching your query.
                  </td>
                </tr>
              ) : (
                paginatedRates.map((r) => (
                  <tr key={r.id} className="hover:bg-stone-50/60 transition-colors">
                    <td className="py-2 px-3 font-mono text-stone-800 font-medium">
                      {formatDisplayDate(r.date)}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                          r.metal === 'GOLD'
                            ? 'bg-[#FBF6E9] text-[#B88B2A]'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {r.metal}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono font-medium text-stone-800">{r.purity}</td>
                    <td className="py-2 px-3 text-stone-600">
                      ₹{r.originalPrice.toLocaleString('en-IN')} / {r.originalUnit}
                    </td>
                    <td className="py-2 px-3 font-mono font-bold text-[#1C1A18]">
                      ₹{r.pricePerGram.toFixed(3)}
                    </td>
                    <td className="py-2 px-3 text-stone-500 text-[11px] font-medium">
                      {r.session || 'PM'}
                    </td>
                    <td className="py-2 px-3 text-[11px]">
                      <div className="font-semibold text-stone-800 flex items-center gap-1">
                        <span>{r.sourceType}</span>
                        {r.notes && (
                          <span className="text-[10px] text-amber-600 font-normal">
                            ({r.notes})
                          </span>
                        )}
                      </div>
                      <div className="text-stone-400 truncate max-w-xs">{r.provenance}</div>
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleOpenCorrection(r)}
                        className="text-stone-400 hover:text-[#B88B2A] p-1 rounded hover:bg-stone-100 transition-colors"
                        title="Enter audited correction for this quotation"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-3 bg-[#FAF7F2] border-t border-stone-200 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-stone-600">
          <div>
            Showing {(page - 1) * pageSize + 1} to{' '}
            {Math.min(page * pageSize, filteredRates.length)} of {filteredRates.length} records
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-2.5 py-1 bg-white hover:bg-stone-50 border border-stone-200 rounded disabled:opacity-40 text-stone-700"
            >
              Previous
            </button>
            <span className="px-2 font-medium">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-2.5 py-1 bg-white hover:bg-stone-50 border border-stone-200 rounded disabled:opacity-40 text-stone-700"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* IBJA Rate Preview & Confirmation Modal */}
      {isIbjaModalOpen && ibjaFetchResult && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-3 sm:p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-stone-200 overflow-hidden flex flex-col">
            <div className="bg-[#FAF7F2] px-5 py-3.5 border-b border-stone-200 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-md bg-[#FBF6E9] border border-[#D4AF37]/40 flex items-center justify-center text-[#B88B2A]">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    IBJA PM Benchmark Preview
                  </h3>
                  <p className="text-[11px] text-stone-500">
                    Review and confirm official closing rates before adding to ledger
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsIbjaModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 text-sm font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* Provenance & Source Label */}
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Source Delivery:</span>
                  <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {ibjaFetchResult.sourceLabel}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Session:</span>
                  <span className="font-bold text-stone-800">
                    PM Closing (Official Benchmark)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Retrieved At:</span>
                  <span className="text-stone-700 font-mono text-[11px]">
                    {new Date(ibjaFetchResult.retrievedAt).toLocaleTimeString()} IST
                  </span>
                </div>
              </div>

              {/* Market Date Selector */}
              <div>
                <label className="block text-stone-700 font-bold mb-1 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-[#B88B2A]" />
                  Market Effective Date
                </label>
                <input
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className="w-full px-3 py-1.5 border border-stone-300 rounded-lg text-xs font-mono font-medium text-stone-900 focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
              </div>

              {/* 3 Rates Cards */}
              <div className="space-y-2.5">
                {/* Gold 999 */}
                <div className="bg-[#FAF7F2] p-3 rounded-lg border border-[#D4AF37]/30 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="font-bold text-stone-900 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#B88B2A]" />
                      Gold 999 (Pure)
                    </div>
                    <div className="text-[11px] text-stone-500">
                      Normalized:{' '}
                      <strong className="text-stone-900 font-mono">
                        ₹{(parseFloat(editGold999 || '0') / 10).toFixed(2)}/g
                      </strong>
                    </div>
                  </div>
                  <div className="w-36">
                    <label className="block text-[10px] text-stone-500 mb-0.5 font-medium">
                      Rate per 10g (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={editGold999}
                      onChange={(e) => setEditGold999(e.target.value)}
                      className="w-full px-2 py-1 bg-white border border-stone-300 rounded text-xs font-mono font-bold text-stone-900 focus:ring-1 focus:ring-[#B88B2A]"
                    />
                  </div>
                </div>

                {/* Gold 995 */}
                <div className="bg-[#FAF7F2] p-3 rounded-lg border border-[#D4AF37]/30 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="font-bold text-stone-900 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#B88B2A]" />
                      Gold 995 (Standard)
                    </div>
                    <div className="text-[11px] text-stone-500">
                      Normalized:{' '}
                      <strong className="text-stone-900 font-mono">
                        ₹{(parseFloat(editGold995 || '0') / 10).toFixed(2)}/g
                      </strong>
                    </div>
                  </div>
                  <div className="w-36">
                    <label className="block text-[10px] text-stone-500 mb-0.5 font-medium">
                      Rate per 10g (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={editGold995}
                      onChange={(e) => setEditGold995(e.target.value)}
                      className="w-full px-2 py-1 bg-white border border-stone-300 rounded text-xs font-mono font-bold text-stone-900 focus:ring-1 focus:ring-[#B88B2A]"
                    />
                  </div>
                </div>

                {/* Silver 999 */}
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="font-bold text-stone-900 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      Silver 999
                    </div>
                    <div className="text-[11px] text-stone-500">
                      Normalized:{' '}
                      <strong className="text-stone-900 font-mono">
                        ₹{(parseFloat(editSilver999 || '0') / 1000).toFixed(3)}/g
                      </strong>
                    </div>
                  </div>
                  <div className="w-36">
                    <label className="block text-[10px] text-stone-500 mb-0.5 font-medium">
                      Rate per 1 Kg (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={editSilver999}
                      onChange={(e) => setEditSilver999(e.target.value)}
                      className="w-full px-2 py-1 bg-white border border-stone-300 rounded text-xs font-mono font-bold text-stone-900 focus:ring-1 focus:ring-slate-500"
                    />
                  </div>
                </div>
              </div>

              <div className="text-[11px] text-stone-500 italic">
                * Confirming will save these 3 benchmark observations to local IndexedDB and recalculate
                your portfolio resale value and annualised XIRR.
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-3 border-t border-stone-200">
                <button
                  type="button"
                  onClick={() => setIsIbjaModalOpen(false)}
                  className="px-3.5 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmIbjaRates}
                  className="px-4 py-1.5 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white rounded-lg font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Confirm & Ingest Rates</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Correction Modal */}
      {correctingRate && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full border border-stone-200 overflow-hidden">
            <div className="bg-[#FAF7F2] px-4 py-3 border-b border-stone-200 flex justify-between items-center">
              <h3 className="text-sm font-bold text-stone-900 flex items-center gap-1.5">
                <Edit3 className="w-4 h-4 text-[#B88B2A]" />
                Audited Price Correction
              </h3>
              <button
                type="button"
                onClick={() => setCorrectingRate(null)}
                className="text-stone-400 hover:text-stone-700"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitCorrection} className="p-4 space-y-3.5 text-xs">
              <div className="bg-stone-50 p-2.5 rounded-lg border border-stone-200 space-y-1">
                <div className="flex justify-between">
                  <span className="text-stone-500">Date:</span>
                  <span className="font-mono font-bold text-stone-800">
                    {correctingRate.date}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-stone-500">Commodity:</span>
                  <span className="font-bold text-stone-800">
                    {correctingRate.metal} {correctingRate.purity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-stone-500">Current Rate:</span>
                  <span className="font-mono font-bold text-stone-800">
                    ₹{correctingRate.pricePerGram.toFixed(3)}/g
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">
                  Corrected Price per Gram (₹/g) *
                </label>
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={newPricePerGram}
                  onChange={(e) => setNewPricePerGram(e.target.value)}
                  className="w-full px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">
                  Correction Reason / Source Audit Note *
                </label>
                <textarea
                  rows={2}
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  className="w-full px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                  placeholder="e.g. Official IBJA gazette corrigendum published on exchange"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-stone-200">
                <button
                  type="button"
                  onClick={() => setCorrectingRate(null)}
                  className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-md font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white rounded-md font-semibold"
                >
                  Save Audited Correction
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
