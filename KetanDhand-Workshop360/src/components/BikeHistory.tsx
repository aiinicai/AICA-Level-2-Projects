import React, { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { Repair } from "@/types";
import { Search, Bike, History, Calendar, User, Wrench, DollarSign } from "lucide-react";

export function BikeHistory() {
  const [searchReg, setSearchReg] = useState("");
  const [history, setHistory] = useState<Repair[] | null>(null);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchReg.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await apiFetch(`/api/bikes/${encodeURIComponent(searchReg.trim())}/history`);
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error("Error fetching bike history:", err);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Bike Repair History Lookup</h2>
        <p className="text-sm text-slate-400">Search by registration number to view complete maintenance history and past bills.</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-xl">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            required
            value={searchReg}
            onChange={(e) => setSearchReg(e.target.value.toUpperCase())}
            placeholder="Enter Registration No (e.g. KA01AB1234)"
            className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 uppercase font-mono text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-sm shadow transition-all"
        >
          {loading ? "Searching..." : "Search History"}
        </button>
      </form>

      {searched && history && (
        <div className="space-y-4 pt-2">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
            Found {history.length} repair records for <span className="text-amber-400 font-mono">{searchReg}</span>
          </h3>

          {history.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl text-center text-slate-400 text-sm">
              No previous repair history found for this registration number.
            </div>
          ) : (
            <div className="space-y-4">
              {history.map((rep) => {
                const itemsTotal = rep.items.reduce((s, i) => s + i.quantity * i.rate, 0);
                const taxable = Math.max(0, itemsTotal + (rep.labourCharges || 0) - (rep.discount || 0));
                const tax = (taxable * (rep.taxRate !== undefined ? rep.taxRate : 0)) / 100;
                const grandTotal = Math.round(taxable + tax);

                return (
                  <div key={rep.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-400 font-bold text-xs rounded-full">
                            {rep.repairNo}
                          </span>
                          <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
                            rep.status === "completed" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
                          }`}>
                            {rep.status.replace(/_/g, " ").toUpperCase()}
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-white mt-1">{rep.bikeModel}</h4>
                      </div>
                      <div className="text-right text-xs text-slate-400">
                        <div>Start: {new Date(rep.startTime).toLocaleDateString()}</div>
                        {rep.completionTime && <div>Completed: {new Date(rep.completionTime).toLocaleDateString()}</div>}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs text-slate-300">
                      <div>
                        <span className="text-slate-500 block">Mechanic</span>
                        <span className="font-medium text-white">{rep.mechanicName}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Customer</span>
                        <span className="font-medium text-white">{rep.customerName || "Walk-in"} ({rep.customerPhone || "N/A"})</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Total Bill Amount</span>
                        <span className="font-bold text-amber-400 text-sm">₹{grandTotal}</span>
                      </div>
                    </div>

                    {/* Items used */}
                    <div>
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Parts & Products Used</span>
                      <div className="space-y-1.5">
                        {rep.items.map((item) => (
                          <div key={item.id} className="bg-slate-850 px-3 py-2 rounded-xl flex items-center justify-between text-xs">
                            <span className="text-slate-200 font-medium">{item.name} × {item.quantity}</span>
                            <span className="text-slate-400">Rate: ₹{item.rate} | Amount: <strong className="text-amber-400">₹{item.quantity * item.rate}</strong></span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
