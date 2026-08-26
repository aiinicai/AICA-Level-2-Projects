import React, { useState, useMemo } from 'react';
import {
  BarChart3, Activity, AlertOctagon, CheckCircle2, AlertTriangle,
  Info, Filter, Download, X, Search, ChevronRight, PieChart
} from 'lucide-react';
import 'chart.js/auto';
import { Bar } from 'react-chartjs-2';
import { BenfordSuiteResponse, DigitTestResult, IngestionResult } from '../types';

interface BenfordWorkbenchViewProps {
  benfordData: BenfordSuiteResponse | null;
  ingestionResult: IngestionResult | null;
  isLoading: boolean;
  onProceedToForensics: () => void;
}

export const BenfordWorkbenchView: React.FC<BenfordWorkbenchViewProps> = ({
  benfordData,
  ingestionResult,
  isLoading,
  onProceedToForensics
}) => {
  const [selectedTest, setSelectedTest] = useState<'first_two_digits' | 'first_digit' | 'second_digit' | 'first_three_digits' | 'last_two_digits' | 'mantissa_arc'>('first_two_digits');
  const [selectedDigitFilter, setSelectedDigitFilter] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // 1. Top-Level Hooks (Unconditionally executed across all renders)
  const currentTestResult: DigitTestResult | null = useMemo(() => {
    if (!benfordData || !benfordData.success) return null;
    if (selectedTest === 'first_two_digits') return benfordData.first_two_digits || null;
    if (selectedTest === 'first_digit') return benfordData.first_digit || null;
    if (selectedTest === 'second_digit') return benfordData.second_digit || null;
    if (selectedTest === 'first_three_digits') return benfordData.first_three_digits || null;
    if (selectedTest === 'last_two_digits') return benfordData.last_two_digits || null;
    return null;
  }, [benfordData, selectedTest]);

  // 2. Chart Data Preparation
  const chartData = useMemo(() => {
    if (!currentTestResult || !currentTestResult.items) return null;

    const labels = currentTestResult.items.map(item => item.digit_label || String(item.digit));
    const observedPcts = currentTestResult.items.map(item => item.observed_pct);
    const expectedPcts = currentTestResult.items.map(item => item.expected_pct);

    // Color bars based on whether Z-score is a significant spike (> 1.96)
    const backgroundColors = currentTestResult.items.map(item => {
      if (selectedDigitFilter !== null && item.digit === selectedDigitFilter) {
        return '#F59E0B'; // Highlighted active filter
      }
      if (item.is_spike) {
        return item.is_significant_99 ? '#EF4444' : '#F87171'; // Red for significant spike
      }
      return '#0284C7'; // Standard Blue
    });

    return {
      labels,
      datasets: [
        {
          type: 'bar' as const,
          label: 'Observed Frequency (%)',
          data: observedPcts,
          backgroundColor: backgroundColors,
          borderRadius: 4,
          order: 2
        },
        {
          type: 'line' as const,
          label: 'Benford Theoretical Curve (%)',
          data: expectedPcts,
          borderColor: '#10B981',
          borderWidth: 2,
          pointRadius: currentTestResult.items.length > 50 ? 0 : 3,
          pointBackgroundColor: '#10B981',
          tension: 0.2,
          order: 1
        }
      ]
    };
  }, [currentTestResult, selectedDigitFilter]);

  // 3. Drilldown Row Indices
  const drilldownRowIndices = useMemo(() => {
    if (selectedDigitFilter === null || !currentTestResult || !currentTestResult.items) return null;
    const item = currentTestResult.items.find(it => it.digit === selectedDigitFilter);
    return item ? new Set(item.row_indices) : null;
  }, [selectedDigitFilter, currentTestResult]);

  const allRecords = useMemo(() => ingestionResult?.sample_records || [], [ingestionResult]);
  const displayRecords = useMemo(() => {
    let recs = allRecords;
    if (drilldownRowIndices !== null) {
      recs = recs.filter((_, idx) => drilldownRowIndices.has(idx));
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      recs = recs.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(term)));
    }
    return recs;
  }, [allRecords, drilldownRowIndices, searchTerm]);

  // Conditional Rendering AFTER all hooks have executed
  if (!benfordData || !benfordData.success) {
    return (
      <div className="forensic-card p-12 text-center max-w-2xl mx-auto my-8">
        <Activity className="w-12 h-12 text-brand-400 mx-auto mb-4 animate-pulse" />
        <h3 className="text-base font-bold text-white mb-1">
          {isLoading ? 'Computing Benford Statistical Distributions...' : 'Benford Analysis Pending'}
        </h3>
        <p className="text-xs text-slate-400">
          {benfordData?.error_message || 'Please ingest a financial dataset with an Amount column to generate Benford Law charts.'}
        </p>
      </div>
    );
  }

  const chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (_event: any, elements: any[]) => {
      if (elements && elements.length > 0 && currentTestResult && currentTestResult.items) {
        const elementIndex = elements[0].index;
        const item = currentTestResult.items[elementIndex];
        if (item) {
          const clickedDigit = item.digit;
          setSelectedDigitFilter(prev => prev === clickedDigit ? null : clickedDigit);
        }
      }
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#CBD5E1',
          font: { size: 11, family: 'Inter' }
        }
      },
      tooltip: {
        callbacks: {
          afterBody: (context: any) => {
            if (!currentTestResult || !currentTestResult.items) return '';
            const idx = context[0]?.dataIndex;
            const item = currentTestResult.items[idx];
            if (!item) return '';
            return [
              `Count: ${item.count} / Expected: ${item.expected_count}`,
              `Difference: ${item.difference > 0 ? '+' : ''}${(item.difference * 100).toFixed(2)}%`,
              `Z-Score: ${item.z_score} ${item.is_significant_95 ? '(Statistically Significant Spike)' : ''}`
            ];
          }
        }
      }
    },
    scales: {
      x: {
        grid: { color: '#1E293B' },
        ticks: { color: '#94A3B8', font: { size: 10 } }
      },
      y: {
        grid: { color: '#1E293B' },
        ticks: {
          color: '#94A3B8',
          callback: (value: any) => `${value}%`
        }
      }
    }
  };

  const summary = benfordData.overall_summary || {
    badge_color: '#3B82F6',
    conformity_rating: 'Evaluated',
    mad_f2d: 0.0
  };

  const mantissaData = benfordData.mantissa_arc || {
    mean_mantissa: 0.5,
    variance_mantissa: 0.0833,
    skewness: 0,
    kurtosis: 0,
    center_of_gravity_x: 0,
    center_of_gravity_y: 0,
    is_conforming: true,
    status: 'Conforming',
    histogram: []
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-4">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-brand-400" />
            Nigrini Benford's Law Forensic Analytics
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Analyzed {benfordData.valid_rows ? benfordData.valid_rows.toLocaleString() : 0} valid transactions &bull; Nigrini MAD Conformity &bull; Z-Score Spike Alerts
          </p>
        </div>

        <button
          onClick={onProceedToForensics}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2 self-start sm:self-auto"
        >
          <span>Run Advanced Forensic Tests</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Top KPI Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {/* 1. Overall Conformity Rating */}
        <div className="forensic-card p-4 border-l-4" style={{ borderLeftColor: summary.badge_color || '#3B82F6' }}>
          <span className="text-[11px] text-slate-400 block font-medium">Nigrini MAD Rating (F2D)</span>
          <div className="text-base font-bold text-white mt-1 flex items-center gap-2">
            <span style={{ color: summary.badge_color || '#3B82F6' }}>{summary.conformity_rating}</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400 mt-1 block">
            MAD = {summary.mad_f2d !== undefined ? summary.mad_f2d.toFixed(5) : '-'}
          </span>
        </div>

        {/* 2. Chi-Square Goodness-of-Fit */}
        <div className="forensic-card p-4 border-l-4 border-l-brand-500">
          <span className="text-[11px] text-slate-400 block font-medium">Chi-Square Test (χ²)</span>
          <div className="text-base font-bold text-white mt-1">
            {currentTestResult ? `χ² = ${currentTestResult.chi2_statistic}` : '-'}
          </div>
          <span className="text-[11px] font-mono text-slate-400 mt-1 block">
            p-value = {currentTestResult ? currentTestResult.chi2_p_value : '-'}
          </span>
        </div>

        {/* 3. Kolmogorov-Smirnov Distance */}
        <div className="forensic-card p-4 border-l-4 border-l-cyan-500">
          <span className="text-[11px] text-slate-400 block font-medium">Kolmogorov-Smirnov (K-S)</span>
          <div className="text-base font-bold text-white mt-1">
            {currentTestResult ? `D = ${currentTestResult.ks_statistic}` : '-'}
          </div>
          <span className="text-[11px] font-mono text-slate-400 mt-1 block">
            Crit = {currentTestResult ? currentTestResult.ks_critical_95 : '-'}
          </span>
        </div>

        {/* 4. Mantissa Arc Summary */}
        <div className="forensic-card p-4 border-l-4 border-l-purple-500">
          <span className="text-[11px] text-slate-400 block font-medium">Mantissa Arc Center</span>
          <div className="text-base font-bold text-white mt-1">
            Mean = {mantissaData.mean_mantissa}
          </div>
          <span className="text-[11px] font-mono text-slate-400 mt-1 block">
            Expected: 0.5000 (Var: {mantissaData.variance_mantissa})
          </span>
        </div>
      </div>

      {/* Benford Test Selector Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {[
          { id: 'first_two_digits', label: 'First-Two Digits (F2D) [Primary]', desc: '10 to 99' },
          { id: 'first_digit', label: 'First Digit (1D)', desc: '1 to 9' },
          { id: 'second_digit', label: 'Second Digit (2D)', desc: '0 to 9' },
          { id: 'first_three_digits', label: 'First-Three Digits (F3D)', desc: '100 to 999' },
          { id: 'last_two_digits', label: 'Last-Two Digits (Uniformity)', desc: '00 to 99' },
          { id: 'mantissa_arc', label: 'Mantissa Arc Test', desc: 'Fractional log' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setSelectedTest(t.id as any);
              setSelectedDigitFilter(null);
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all flex flex-col items-start ${
              selectedTest === t.id
                ? 'bg-brand-600 text-white shadow-lg shadow-brand-500/20'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <span>{t.label}</span>
            <span className="text-[10px] opacity-75 font-normal">{t.desc}</span>
          </button>
        ))}
      </div>

      {/* Main Chart Area */}
      {selectedTest !== 'mantissa_arc' && chartData && (
        <div className="forensic-card p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Observed vs. Expected Benford Distribution</span>
                {currentTestResult?.spike_digits && currentTestResult.spike_digits.length > 0 ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 font-bold">
                    {currentTestResult.spike_digits.length} Anomaly Spikes Detected (Red Bars)
                  </span>
                ) : null}
              </h3>
              <p className="text-xs text-slate-400">
                Click any bar on the chart to filter the underlying transaction ledger table below.
              </p>
            </div>

            {selectedDigitFilter !== null && (
              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 rounded-lg text-xs text-amber-300">
                <Filter className="w-3.5 h-3.5" />
                <span>Active Filter: Digit <b>{selectedDigitFilter}</b></span>
                <button
                  onClick={() => setSelectedDigitFilter(null)}
                  className="hover:text-white ml-1 p-0.5 rounded hover:bg-amber-500/20"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          <div className="h-80 w-full">
            <Bar data={chartData} options={chartOptions} />
          </div>
        </div>
      )}

      {/* Mantissa Arc View */}
      {selectedTest === 'mantissa_arc' && (
        <div className="forensic-card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">
                Mantissa Arc Distribution &amp; Center of Gravity Analysis
              </h3>
              <p className="text-xs text-slate-400">
                Evaluates fractional logarithm distribution. Non-uniformity indicates truncated or fabricated accounting populations.
              </p>
            </div>
            <span className={`text-xs px-3 py-1 rounded-full font-bold border ${
              mantissaData.is_conforming
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}>
              {mantissaData.status}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Mean Mantissa:</span>
                <span className="text-white font-mono font-bold">{mantissaData.mean_mantissa} (Expected 0.5000)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Mantissa Variance:</span>
                <span className="text-white font-mono font-bold">{mantissaData.variance_mantissa} (Expected 0.0833)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Skewness / Kurtosis:</span>
                <span className="text-white font-mono">{mantissaData.skewness} / {mantissaData.kurtosis}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Center of Gravity Vector (X, Y):</span>
                <span className="text-white font-mono">({mantissaData.center_of_gravity_x}, {mantissaData.center_of_gravity_y})</span>
              </div>
            </div>

            {/* Mantissa Bins Table */}
            <div className="overflow-x-auto border border-slate-800 rounded-xl">
              <table className="w-full text-xs text-left text-slate-300">
                <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase">
                  <tr>
                    <th className="px-3 py-2">Mantissa Bin</th>
                    <th className="px-3 py-2 text-right">Count</th>
                    <th className="px-3 py-2 text-right">Observed %</th>
                    <th className="px-3 py-2 text-right">Expected %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {(mantissaData.histogram || []).map((bin, i) => (
                    <tr key={i} className="hover:bg-slate-800/20">
                      <td className="px-3 py-1.5 text-slate-200">{bin.bin_label}</td>
                      <td className="px-3 py-1.5 text-right">{bin.count}</td>
                      <td className="px-3 py-1.5 text-right">{(bin.observed_prob * 100).toFixed(1)}%</td>
                      <td className="px-3 py-1.5 text-right text-emerald-400">10.0%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Drilldown Transaction Ledger Table */}
      <div className="forensic-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Transaction Evidence Room</span>
              {selectedDigitFilter !== null && (
                <span className="text-xs text-amber-400">
                  (Filtered by Digit: {selectedDigitFilter} - {displayRecords.length} records)
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              Interactive transaction inspector for drilldown verification.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search transactions..."
                className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 w-48 sm:w-64"
              />
            </div>
            {selectedDigitFilter !== null && (
              <button
                onClick={() => setSelectedDigitFilter(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" /> Clear Filter
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-72">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px] sticky top-0">
              <tr>
                <th className="px-3 py-2">#</th>
                {ingestionResult?.columns?.slice(0, 7).map((col) => (
                  <th key={col} className="px-3 py-2 whitespace-nowrap">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {displayRecords.slice(0, 50).map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30">
                  <td className="px-3 py-1.5 text-slate-500">{idx + 1}</td>
                  {ingestionResult?.columns?.slice(0, 7).map((col) => (
                    <td key={col} className="px-3 py-1.5 whitespace-nowrap text-slate-200">
                      {String(row[col] !== null && row[col] !== undefined ? row[col] : '-')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
