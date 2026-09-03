import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";
import { AnalyticsData } from "@/types";
import { BarChart3, TrendingUp, Bike, Package, Wrench, Clock, Users } from "lucide-react";

export function AnalyticsView() {
  const [filter, setFilter] = useState<"today" | "week" | "month" | "all" | "custom">("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (filter === "custom" && (!from || !to)) return;
    setLoading(true);
    const qs =
      filter === "custom"
        ? `filter=custom&from=${from}&to=${to}`
        : `filter=${filter}`;
    apiFetch(`/api/analytics?${qs}`)
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching analytics:", err);
        setLoading(false);
      });
  }, [filter, from, to]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Workshop Analytics & Insights</h2>
          <p className="text-sm text-slate-400">Performance metrics, top products, and mechanic workloads.</p>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-col gap-2 items-start sm:items-end">
          <div className="flex flex-wrap rounded-xl bg-slate-900 p-1 border border-slate-750">
            {(["today", "week", "month", "all", "custom"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg capitalize transition-all ${
                  filter === f ? "bg-amber-500 text-slate-950 shadow" : "text-slate-400 hover:text-white"
                }`}
              >
                {f === "all" ? "All Time" : f === "custom" ? "Custom Range" : f}
              </button>
            ))}
          </div>

          {filter === "custom" && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
                className="px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
              />
              <span className="text-xs text-slate-400">to</span>
              <input
                type="date"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                className="px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
              />
            </div>
          )}
        </div>
      </div>

      {filter === "custom" && (!from || !to) ? (
        <div className="text-center py-16 text-slate-500 text-sm">Select a start and end date to view analytics.</div>
      ) : loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">Loading analytics...</div>

      ) : !data ? (
        <div className="text-center py-16 text-slate-500 text-sm">No analytics data available.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Summary Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Repairs</span>
            <div className="text-3xl font-extrabold text-white">{data.totalRepairs}</div>
            <p className="text-xs text-slate-500">Repairs logged in selected time period</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Avg Completion Time</span>
            <div className="text-3xl font-extrabold text-amber-400">{data.avgCompletionTimeMinutes} mins</div>
            <p className="text-xs text-slate-500">Average duration from start to finish</p>
          </div>

          {/* Current Workload */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Wrench className="w-4 h-4 text-amber-400" /> Current Workload by Mechanic
            </h3>
            <div className="space-y-2">
              {data.currentWorkload.length === 0 ? (
                <p className="text-xs text-slate-500">No active repairs right now.</p>
              ) : (
                data.currentWorkload.map((w, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl">
                    <span className="text-slate-200 font-medium">{w.name}</span>
                    <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 font-bold rounded-full">{w.count} active</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Most Frequently Returning Bikes */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Bike className="w-4 h-4 text-amber-400" /> Most Returning Bikes
            </h3>
            <div className="space-y-2">
              {data.returningBikes.length === 0 ? (
                <p className="text-xs text-slate-500">No data available.</p>
              ) : (
                data.returningBikes.map((b, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl font-mono">
                    <span className="text-slate-200 font-bold">{b.reg}</span>
                    <span className="text-amber-400 font-semibold">{b.count} visits</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Most Frequently Used Products */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Package className="w-4 h-4 text-amber-400" /> Most Used Products
            </h3>
            <div className="space-y-2">
              {data.topProducts.length === 0 ? (
                <p className="text-xs text-slate-500">No data available.</p>
              ) : (
                data.topProducts.map((p, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl">
                    <span className="text-slate-200 font-medium">{p.name}</span>
                    <span className="font-bold text-amber-400">× {p.count}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Most Used Brands */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-amber-400" /> Top Brands (Heuristic)
            </h3>
            <div className="space-y-2">
              {data.topBrands.length === 0 ? (
                <p className="text-xs text-slate-500">No data available.</p>
              ) : (
                data.topBrands.map((b, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl">
                    <span className="text-slate-200 font-medium">{b.brand}</span>
                    <span className="font-bold text-amber-400">{b.count} units</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Repairs Handled by Each Mechanic */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-amber-400" /> Repairs by Mechanic
            </h3>
            <div className="space-y-2">
              {data.repairsByMechanic.length === 0 ? (
                <p className="text-xs text-slate-500">No data available.</p>
              ) : (
                data.repairsByMechanic.map((m, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl">
                    <span className="text-slate-200 font-medium">{m.name}</span>
                    <span className="font-bold text-amber-400">{m.count} repairs</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Most Common Bike Models */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Bike className="w-4 h-4 text-amber-400" /> Most Common Bike Models
            </h3>
            <div className="space-y-2">
              {data.topModels.length === 0 ? (
                <p className="text-xs text-slate-500">No data available.</p>
              ) : (
                data.topModels.map((m, i) => (
                  <div key={i} className="flex justify-between items-center text-xs bg-slate-850 px-3 py-2 rounded-xl">
                    <span className="text-slate-200 font-medium">{m.model}</span>
                    <span className="font-bold text-amber-400">{m.count} bikes</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
