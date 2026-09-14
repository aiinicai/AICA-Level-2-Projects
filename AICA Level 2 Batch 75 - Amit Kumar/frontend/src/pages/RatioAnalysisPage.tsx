import React, { useEffect, useState } from 'react';
import type { Client, RatioItem } from '../types';
import { fetchRatios } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { PieChart as PieIcon } from 'lucide-react';

interface RatioAnalysisProps {
  client: Client;
}

export const RatioAnalysisPage: React.FC<RatioAnalysisProps> = ({ client }) => {
  const [ratios, setRatios] = useState<RatioItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchRatios(client.id);
      setRatios(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client]);

  const chartData = ratios.map(r => ({
    name: r.name,
    CY: r.cy_value,
    PY: r.py_value,
  }));

  return (
    <div className="space-y-6">
      <div className="border-b border-ca-border pb-4">
        <h1 className="text-xl font-bold text-navy-900 uppercase tracking-tight">SCHEDULE III RATIO ANALYSIS & INTERPRETATION</h1>
        <p className="text-xs text-ca-muted mt-0.5">8 key financial metrics calculated as per Schedule III Division I mandates with variance commentary.</p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-ca-muted text-xs">Computing Schedule III ratios...</div>
      ) : (
        <>
          <div className="ca-card bg-white space-y-3">
            <h3 className="text-xs font-bold text-navy-900 uppercase flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-orange-600" />
              CY vs PY Ratio Comparison Visualizer
            </h3>
            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-15} textAnchor="end" />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ fontSize: '11px', borderRadius: '4px' }} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="CY" fill="#0F172A" name={`Current Year (${client.reporting_period})`} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="PY" fill="#EA580C" name={`Previous Year (${client.previous_year_period})`} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ratios.map((r) => (
              <div key={r.code} className="ca-card bg-white border border-ca-border space-y-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="bg-navy-900 text-white font-mono text-[10px] font-bold px-1.5 py-0.5 rounded">
                      {r.code}
                    </span>
                    <h3 className="text-xs font-bold text-navy-900 uppercase">{r.name}</h3>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    Mov: {r.movement}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 py-1 text-center font-mono">
                  <div className="bg-slate-50 p-2 rounded border border-slate-200">
                    <span className="text-[10px] text-ca-muted block font-sans">CY Value</span>
                    <span className="text-sm font-bold text-navy-900">{r.cy_value}</span>
                    <span className="text-[9px] text-ca-muted ml-0.5">{r.unit}</span>
                  </div>

                  <div className="bg-slate-50 p-2 rounded border border-slate-200">
                    <span className="text-[10px] text-ca-muted block font-sans">PY Value</span>
                    <span className="text-sm font-bold text-slate-700">{r.py_value}</span>
                    <span className="text-[9px] text-ca-muted ml-0.5">{r.unit}</span>
                  </div>

                  <div className="bg-slate-50 p-2 rounded border border-slate-200 flex flex-col justify-center">
                    <span className="text-[10px] text-ca-muted block font-sans">Formula</span>
                    <span className="text-[9px] text-slate-600 font-sans truncate">{r.formula}</span>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs space-y-0.5">
                  <span className="font-bold text-navy-900 text-[11px] block">Audit Interpretation:</span>
                  <p className="text-[11px] text-slate-700 leading-normal">{r.interpretation}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
