import React from 'react';
import { 
  PieChart, 
  DollarSign, 
  TrendingUp, 
  Layers, 
  ExternalLink,
  Award,
  ArrowRight,
  Calendar
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { LISTED_COMPANIES, getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

interface ValuationMultiplesViewProps {
  company: ListedCompany;
  onSelectCompany: (code: string) => void;
  companies?: ListedCompany[];
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const ValuationMultiplesView: React.FC<ValuationMultiplesViewProps> = ({ 
  company, 
  onSelectCompany,
  companies = LISTED_COMPANIES,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores'
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);
  const peers = companies.filter(c => c.sector === company.sector);
  const enterpriseValue = fin.marketCap + fin.debt;
  const evEbitdaRatio = fin.ebitda > 0 
    ? (enterpriseValue / (selectedPeriod === 'RunRate' || selectedPeriod === 'PY' ? fin.ebitda : fin.ebitda * 4)) 
    : 0;

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const peerChartData = peers.slice(0, 8).map(p => {
    const peerFin = getResolvedCompanyFinancials(p, selectedPeriod);
    return {
      name: p.shortName,
      peRatio: peerFin.peRatio,
      pbRatio: peerFin.pbRatio,
      code: p.bseCode
    };
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Valuation Multiples Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PieChart className="w-4 h-4 text-blue-600" />
              <span>Valuation Multiples & Market Pricing: {company.name}</span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              P/E, P/B, EV/EBITDA multiples and sector peer valuation comparison
            </p>
          </div>
        </div>

        {/* 4 Multiples Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Price-to-Earnings (P/E)</span>
            <div className="text-2xl font-bold text-blue-600">{fin.peRatio.toFixed(1)}x</div>
            <p className="text-[11px] text-slate-500 font-sans">
              EPS Based on {fin.periodLabel.split(' ')[0]} PAT
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Price-to-Book (P/B)</span>
            <div className="text-2xl font-bold text-slate-900">{fin.pbRatio.toFixed(1)}x</div>
            <p className="text-[11px] text-slate-500 font-sans">
              Net Worth: {formatVal(fin.netWorth)}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">EV / EBITDA Multiple</span>
            <div className="text-2xl font-bold text-emerald-600">{evEbitdaRatio.toFixed(1)}x</div>
            <p className="text-[11px] text-slate-500 font-sans">
              Enterprise Value: {formatVal(enterpriseValue)}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Dividend Yield %</span>
            <div className="text-2xl font-bold text-purple-600">{fin.dividendYield.toFixed(2)}%</div>
            <p className="text-[11px] text-slate-500 font-sans">
              Payout: Prudent capital return
            </p>
          </div>
        </div>
      </div>

      {/* Peer Comparison Chart & Leaderboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Peer P/E Comparison Bar Chart */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            Sector Peer P/E Multiples Comparison ({company.sector})
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={peerChartData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}x`} />
                <Tooltip
                  formatter={(value: any) => [`${Number(value).toFixed(1)}x P/E`]}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="peRatio" name="P/E Multiple" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Peer Leaderboard Table */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            {company.sector} Peers Valuation Leaderboard
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] bg-slate-50">
                  <th className="py-2.5 px-3">Enterprise</th>
                  <th className="py-2.5 px-3 text-right">Stock Price</th>
                  <th className="py-2.5 px-3 text-right">P/E</th>
                  <th className="py-2.5 px-3 text-right">P/B</th>
                  <th className="py-2.5 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {peers.map((p) => {
                  const pFin = getResolvedCompanyFinancials(p, selectedPeriod);
                  return (
                    <tr key={p.bseCode} className={`hover:bg-slate-50 transition-colors ${p.bseCode === company.bseCode ? 'bg-blue-50 font-bold' : ''}`}>
                      <td className="py-2.5 px-3 font-sans">
                        <div className="font-semibold text-slate-900">{p.shortName}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{p.nseCode}</div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                        {currency === 'USD' ? `$ ${(p.stockPrice / 83.5).toFixed(1)}` : `₹ ${p.stockPrice.toLocaleString('en-IN')}`}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-blue-600">
                        {pFin.peRatio.toFixed(1)}x
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-700">
                        {pFin.pbRatio.toFixed(1)}x
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <button
                          onClick={() => onSelectCompany(p.bseCode)}
                          className="px-2 py-1 bg-slate-100 hover:bg-blue-600 hover:text-white rounded text-[10px] text-slate-700 font-sans transition-colors"
                        >
                          Switch
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
