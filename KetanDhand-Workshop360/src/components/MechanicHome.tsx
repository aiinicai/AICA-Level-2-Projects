import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";
import { User, Repair } from "@/types";
import { Wrench, Plus, Bike, Clock, ArrowRight, CheckCircle2, ShieldAlert, LogOut } from "lucide-react";
import { RepairDetailModal } from "./RepairDetailModal";

interface MechanicHomeProps {
  currentUser: User;
  onLogout: () => void;
}

export function MechanicHome({ currentUser, onLogout }: MechanicHomeProps) {
  const [repairs, setRepairs] = useState<Repair[]>([]);
  const [loading, setLoading] = useState(true);
  const [showStartModal, setShowStartModal] = useState(false);
  const [selectedRepair, setSelectedRepair] = useState<Repair | null>(null);

  // New repair form state
  const [bikeRegistration, setBikeRegistration] = useState("");
  const [bikeModel, setBikeModel] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [startError, setStartError] = useState("");
  const [starting, setStarting] = useState(false);

  const fetchRepairs = async () => {
    try {
      const res = await apiFetch("/api/repairs");
      const data = await res.json();
      setRepairs(data);
    } catch (err) {
      console.error("Error fetching repairs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepairs();
    const interval = setInterval(fetchRepairs, 5000); // live polling
    return () => clearInterval(interval);
  }, []);

  const handleStartRepair = async (e: React.FormEvent) => {
    e.preventDefault();
    setStartError("");
    setStarting(true);
    try {
      const res = await apiFetch("/api/repairs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bikeRegistration,
          bikeModel,
          customerName,
          customerPhone,
          mechanicId: currentUser.id,
          mechanicName: currentUser.name,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to start repair");
      
      setBikeRegistration("");
      setBikeModel("");
      setCustomerName("");
      setCustomerPhone("");
      setShowStartModal(false);
      fetchRepairs();
      setSelectedRepair(data); // Open immediately
    } catch (err: any) {
      setStartError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const myRepairs = repairs.filter((r) => r.mechanicId === currentUser.id);
  const activeRepairs = myRepairs.filter((r) => r.status === "repairing");
  const finishedRepairs = myRepairs.filter((r) => r.status !== "repairing");

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-[#1E293B] pb-16 font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 px-4 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center font-bold">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-tight">{currentUser.name}</h1>
            <span className="text-xs text-blue-600 font-semibold">Mechanic Portal</span>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 rounded-xl transition-colors flex items-center gap-1.5 text-xs font-semibold border border-slate-200"
        >
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </header>

      {/* Main Content (Mobile-First) */}
      <main className="max-w-md mx-auto p-4 space-y-6">
        {/* BIG START NEW REPAIR BUTTON */}
        <button
          onClick={() => setShowStartModal(true)}
          className="w-full py-5 px-6 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-lg rounded-2xl shadow-md flex items-center justify-center gap-3 transition-all transform active:scale-95"
        >
          <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center">
            <Plus className="w-6 h-6 stroke-[3]" />
          </div>
          START NEW REPAIR
        </button>

        {/* MY ACTIVE REPAIRS SECTION */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-600 uppercase tracking-wider">
              My Active Repairs ({activeRepairs.length})
            </h2>
          </div>

          {loading ? (
            <div className="text-center py-12 text-slate-400 text-sm">Loading active repairs...</div>
          ) : activeRepairs.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 text-center space-y-2 shadow-sm">
              <Bike className="w-10 h-10 text-slate-400 mx-auto" />
              <p className="text-sm text-slate-700 font-medium">No active repairs right now.</p>
              <p className="text-xs text-slate-500">Tap &quot;Start New Repair&quot; above when a bike comes in.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeRepairs.map((repair) => (
                <div
                  key={repair.id}
                  onClick={() => setSelectedRepair(repair)}
                  className="bg-white border-2 border-blue-500 hover:border-blue-600 rounded-2xl p-4 shadow-sm cursor-pointer transition-all active:scale-[0.99] flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md">
                        {repair.repairNo}
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(repair.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                      <Bike className="w-5 h-5 text-amber-400" />
                      {repair.bikeRegistration}
                    </div>
                    <div className="text-sm text-slate-300 font-medium">{repair.bikeModel}</div>
                    <div className="text-xs text-slate-400 pt-1 flex items-center gap-2">
                      <span>Parts used: <strong className="text-white">{repair.items.length}</strong></span>
                      {repair.customerName && <span>• Customer: {repair.customerName}</span>}
                    </div>
                  </div>
                  <div className="w-10 h-10 bg-amber-500/10 text-amber-400 rounded-xl flex items-center justify-center shrink-0">
                    <ArrowRight className="w-5 h-5" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RECENTLY FINISHED REPAIRS (Read-Only) */}
        {finishedRepairs.length > 0 && (
          <div className="space-y-3 pt-4">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
              Completed / Ready for Billing ({finishedRepairs.length})
            </h2>
            <div className="space-y-2">
              {finishedRepairs.slice(0, 5).map((repair) => (
                <div
                  key={repair.id}
                  onClick={() => setSelectedRepair(repair)}
                  className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 cursor-pointer hover:border-slate-700 transition-colors flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-400">{repair.repairNo}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        repair.status === "ready_for_billing" ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/20 text-emerald-400"
                      }`}>
                        {repair.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="text-sm font-bold text-slate-200 mt-0.5">{repair.bikeModel} ({repair.bikeRegistration})</div>
                  </div>
                  <span className="text-xs text-slate-500">View</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* START NEW REPAIR MODAL */}
      {showStartModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex flex-col justify-end sm:justify-center p-0 sm:p-4">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-lg mx-auto sm:rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Bike className="w-5 h-5 text-amber-400" /> Start New Repair
              </h3>
              <button
                onClick={() => setShowStartModal(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            {startError && (
              <div className="bg-red-950/80 border border-red-800 text-red-200 p-3 rounded-xl text-sm">
                {startError}
              </div>
            )}

            <form onSubmit={handleStartRepair} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Bike Registration Number * (e.g. KA01AB1234)
                </label>
                <input
                  type="text"
                  required
                  value={bikeRegistration}
                  onChange={(e) => setBikeRegistration(e.target.value.toUpperCase())}
                  placeholder="KA01AB1234"
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-600 text-base uppercase font-mono tracking-wide focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Bike Name / Model * (e.g. Hero Splendor, Activa 6G)
                </label>
                <input
                  type="text"
                  required
                  value={bikeModel}
                  onChange={(e) => setBikeModel(e.target.value)}
                  placeholder="Hero Splendor Plus"
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-600 text-base focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Customer Name (Optional)
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Amit Sharma"
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-600 text-base focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Customer Phone (Optional)
                </label>
                <input
                  type="tel"
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value)}
                  placeholder="9811122233"
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-600 text-base focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowStartModal(false)}
                  className="flex-1 py-3.5 bg-slate-800 hover:bg-slate-750 text-white font-semibold rounded-xl text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={starting}
                  className="flex-1 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold rounded-xl text-base shadow-lg shadow-amber-500/20 transition-all"
                >
                  {starting ? "Starting..." : "Begin Repair"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Repair Detail / Add Items Modal */}
      {selectedRepair && (
        <RepairDetailModal
          repair={selectedRepair}
          currentUser={currentUser}
          onClose={() => {
            setSelectedRepair(null);
            fetchRepairs();
          }}
          onRefresh={fetchRepairs}
        />
      )}
    </div>
  );
}
