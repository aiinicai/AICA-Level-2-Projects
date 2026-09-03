import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";
import { User, Repair } from "@/types";
import { Wrench, Shield, Users, History, BarChart3, LogOut, CheckCircle2, AlertCircle, Bike, Clock, FileText, ChevronRight, Search } from "lucide-react";
import { RepairManagement } from "./RepairManagement";
import { MechanicsManagement } from "./MechanicsManagement";
import { BikeHistory } from "./BikeHistory";
import { AnalyticsView } from "./AnalyticsView";

interface OwnerDashboardProps {
  currentUser: User;
  onLogout: () => void;
}

export function OwnerDashboard({ currentUser, onLogout }: OwnerDashboardProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "repairs" | "mechanics" | "history" | "analytics">("overview");
  const [repairs, setRepairs] = useState<Repair[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRepairForBilling, setSelectedRepairForBilling] = useState<Repair | null>(null);
  const [repairFilterStatus, setRepairFilterStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");


  const fetchData = async () => {
    try {
      const [repRes, userRes] = await Promise.all([
        apiFetch("/api/repairs"),
        apiFetch("/api/users"),
      ]);
      const repData = await repRes.json();
      const userData = await userRes.json();
      setRepairs(repData);
      setUsers(userData);
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 6000);
    return () => clearInterval(interval);
  }, []);

  const pendingApprovalsCount = users.filter(
    (u) => (u.role === "mechanic" || u.role === "shopkeeper") && u.status === "pending"
  ).length;
  const repairingCount = repairs.filter((r) => r.status === "repairing").length;
  const readyForBillingCount = repairs.filter((r) => r.status === "ready_for_billing").length;
  const completedCount = repairs.filter((r) => r.status === "completed").length;

  // Billing / labour totals
  const billTotal = (r: Repair) => {
    const itemsTotal = r.items.reduce((s, i) => s + i.quantity * i.rate, 0);
    const taxable = Math.max(0, itemsTotal + (r.labourCharges || 0) - (r.discount || 0));
    const tax = (taxable * (r.taxRate !== undefined ? r.taxRate : 0)) / 100;
    return Math.round(taxable + tax);
  };

  const todayStr = new Date().toDateString();
  const todaysCompletedRepairs = repairs.filter(
    (r) => r.status === "completed" && r.completionTime && new Date(r.completionTime).toDateString() === todayStr
  );
  const todaysBillingTotal = todaysCompletedRepairs.reduce((sum, r) => sum + billTotal(r), 0);
  const todaysLabourTotal = todaysCompletedRepairs.reduce((sum, r) => sum + (r.labourCharges || 0), 0);

  const rangeRepairs = repairs.filter((r) => {
    if (r.status !== "completed" || !r.completionTime) return false;
    if (!rangeFrom || !rangeTo) return false;
    const t = new Date(r.completionTime).getTime();
    return t >= new Date(`${rangeFrom}T00:00:00`).getTime() && t <= new Date(`${rangeTo}T23:59:59.999`).getTime();
  });
  const rangeBillingTotal = rangeRepairs.reduce((sum, r) => sum + billTotal(r), 0);
  const rangeLabourTotal = rangeRepairs.reduce((sum, r) => sum + (r.labourCharges || 0), 0);


  const filteredRepairs = repairs.filter((r) => {
    const matchesStatus = repairFilterStatus === "all" || r.status === repairFilterStatus;
    const matchesSearch =
      r.bikeRegistration.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.bikeModel.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.repairNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.mechanicName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-[#1E293B] flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-8 py-4 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 text-white rounded-xl flex items-center justify-center font-extrabold shadow-md shadow-blue-600/20">
            <Shield className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">
              Seth Auto Spares{" "}
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ml-2 ${
                currentUser.role === "owner" ? "bg-blue-50 text-blue-700" : "bg-purple-50 text-purple-700"
              }`}>
                {currentUser.role === "owner" ? "Owner / Admin" : "Shopkeeper"}
              </span>
            </h1>
            <p className="text-xs text-slate-500">Motorcycle Spare Parts & Workshop Management</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block text-right">
            <div className="text-sm font-bold text-slate-900">{currentUser.name}</div>
            <div className="text-xs text-slate-500">{currentUser.phone}</div>
          </div>
          <button
            onClick={onLogout}
            className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 rounded-xl transition-colors flex items-center gap-2 text-xs font-semibold border border-slate-200"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </header>

      {/* Navigation Tabs Bar */}
      <div className="bg-white border-b border-slate-200 px-4 sm:px-8 overflow-x-auto shadow-xs">
        <div className="flex space-x-2 py-2">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap ${
              activeTab === "overview" ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <BarChart3 className="w-4 h-4" /> Overview & Live
          </button>
          <button
            onClick={() => setActiveTab("repairs")}
            className={`px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap ${
              activeTab === "repairs" ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <FileText className="w-4 h-4" /> Repairs & Billing ({repairs.length})
          </button>
          {currentUser.role === "owner" && (
            <button
              onClick={() => setActiveTab("mechanics")}
              className={`px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap relative ${
                activeTab === "mechanics" ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <Users className="w-4 h-4" /> Users / Team
              {pendingApprovalsCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white font-bold text-[10px] w-5 h-5 rounded-full flex items-center justify-center">
                  {pendingApprovalsCount}
                </span>
              )}
            </button>
          )}
          <button
            onClick={() => setActiveTab("history")}
            className={`px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap ${
              activeTab === "history" ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <History className="w-4 h-4" /> Bike History
          </button>
          {currentUser.role === "owner" && (
            <button
              onClick={() => setActiveTab("analytics")}
              className={`px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap ${
                activeTab === "analytics" ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <BarChart3 className="w-4 h-4" /> Analytics
            </button>
          )}
        </div>
      </div>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto w-full p-4 sm:p-8 flex-1">
        {activeTab === "overview" && (
          <div className="space-y-8">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
              <div
                onClick={() => { setActiveTab("repairs"); setRepairFilterStatus("repairing"); }}
                className="bg-white border border-slate-200 p-5 rounded-2xl cursor-pointer hover:border-blue-500 transition-all space-y-2 shadow-sm"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase">Repairs in Progress</div>
                <div className="text-3xl font-extrabold text-blue-600">{repairingCount}</div>
                <div className="text-xs text-slate-400 flex items-center gap-1">Active workshop jobs <ChevronRight className="w-3 h-3" /></div>
              </div>

              <div
                onClick={() => { setActiveTab("repairs"); setRepairFilterStatus("ready_for_billing"); }}
                className="bg-white border border-slate-200 p-5 rounded-2xl cursor-pointer hover:border-amber-500 transition-all space-y-2 shadow-sm"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase">Ready for Billing</div>
                <div className="text-3xl font-extrabold text-amber-600">{readyForBillingCount}</div>
                <div className="text-xs text-slate-400 flex items-center gap-1">Finished by mechanics <ChevronRight className="w-3 h-3" /></div>
              </div>

              <div
                onClick={() => { setActiveTab("repairs"); setRepairFilterStatus("completed"); }}
                className="bg-white border border-slate-200 p-5 rounded-2xl cursor-pointer hover:border-emerald-500 transition-all space-y-2 shadow-sm"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase">Completed Repairs</div>
                <div className="text-3xl font-extrabold text-emerald-600">{completedCount}</div>
                <div className="text-xs text-slate-400 flex items-center gap-1">Finalised & billed <ChevronRight className="w-3 h-3" /></div>
              </div>

              <div className="bg-white border border-slate-200 p-5 rounded-2xl space-y-2 shadow-sm">
                <div className="text-xs font-semibold text-slate-500 uppercase">Today's Billing</div>
                <div className="text-3xl font-extrabold text-slate-900">₹{todaysBillingTotal.toLocaleString("en-IN")}</div>
                <div className="text-xs text-slate-400">Total collected today</div>
              </div>

              <div className="bg-white border border-slate-200 p-5 rounded-2xl space-y-2 shadow-sm">
                <div className="text-xs font-semibold text-slate-500 uppercase">Today's Labour Collection</div>
                <div className="text-3xl font-extrabold text-indigo-600">₹{todaysLabourTotal.toLocaleString("en-IN")}</div>
                <div className="text-xs text-slate-400">Labour charges collected today</div>
              </div>

              {currentUser.role === "owner" && (
                <div
                  onClick={() => setActiveTab("mechanics")}
                  className="bg-white border border-slate-200 p-5 rounded-2xl cursor-pointer hover:border-purple-500 transition-all space-y-2 shadow-sm"
                >
                  <div className="text-xs font-semibold text-slate-500 uppercase">Pending Approvals</div>
                  <div className="text-3xl font-extrabold text-purple-600">{pendingApprovalsCount}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-1">Staff waiting approval <ChevronRight className="w-3 h-3" /></div>
                </div>
              )}
            </div>

            {/* Custom range collections */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 space-y-4 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h3 className="text-base font-bold text-slate-900">Collections for a Custom Date Range</h3>
                <div className="flex items-center gap-2 flex-wrap">
                  <input
                    type="date"
                    value={rangeFrom}
                    onChange={(e) => setRangeFrom(e.target.value)}
                    className="px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  <span className="text-xs text-slate-500">to</span>
                  <input
                    type="date"
                    value={rangeTo}
                    onChange={(e) => setRangeTo(e.target.value)}
                    className="px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              {!rangeFrom || !rangeTo ? (
                <p className="text-sm text-slate-400">Pick a start and end date to see billing and labour collection for that period.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                    <div className="text-xs font-semibold text-slate-500 uppercase">Billing Collection</div>
                    <div className="text-2xl font-extrabold text-slate-900">₹{rangeBillingTotal.toLocaleString("en-IN")}</div>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                    <div className="text-xs font-semibold text-slate-500 uppercase">Labour Collection</div>
                    <div className="text-2xl font-extrabold text-indigo-600">₹{rangeLabourTotal.toLocaleString("en-IN")}</div>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                    <div className="text-xs font-semibold text-slate-500 uppercase">Repairs Billed</div>
                    <div className="text-2xl font-extrabold text-emerald-600">{rangeRepairs.length}</div>
                  </div>
                </div>
              )}
            </div>


            {/* Currently Working On (Live Activity) */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-blue-600" /> Currently Working On (Live Mechanics Feed)
                </h3>
                <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full font-medium">
                  Auto-refreshed in real-time
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {repairs.filter((r) => r.status === "repairing").length === 0 ? (
                  <div className="col-span-full text-center py-8 text-slate-400 text-sm">
                    No active repair jobs in progress right now.
                  </div>
                ) : (
                  repairs
                    .filter((r) => r.status === "repairing")
                    .map((job) => (
                      <div
                        key={job.id}
                        onClick={() => setSelectedRepairForBilling(job)}
                        className="bg-slate-50 border border-slate-200 p-4 rounded-xl cursor-pointer hover:border-blue-400 hover:shadow-md transition-all space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                            {job.repairNo}
                          </span>
                          <span className="text-xs font-semibold text-blue-600 animate-pulse flex items-center gap-1">
                            ● Repairing
                          </span>
                        </div>
                        <div>
                          <div className="font-bold text-slate-900 text-base">{job.mechanicName}</div>
                          <div className="text-sm font-semibold text-slate-700 mt-0.5">
                            {job.bikeModel} ({job.bikeRegistration})
                          </div>
                          {job.customerName && (
                            <div className="text-xs text-slate-500 mt-0.5">Customer: {job.customerName}</div>
                          )}
                        </div>
                        <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                          <span>Items added: {job.items.length}</span>
                          <span className="text-blue-600 font-semibold hover:underline">View details →</span>
                        </div>
                      </div>
                    ))
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "repairs" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Repairs & Billing Management</h2>
                <p className="text-sm text-slate-500">Review parts, set rates, edit quantities, and finalise customer bills.</p>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                <div className="relative flex-1 sm:w-64">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Search className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search reg no, model, ID..."
                    className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>

                <select
                  value={repairFilterStatus}
                  onChange={(e) => setRepairFilterStatus(e.target.value)}
                  className="px-3 py-2 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-600"
                >
                  <option value="all">All Statuses</option>
                  <option value="repairing">Repairing</option>
                  <option value="ready_for_billing">Ready for Billing</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>

            {/* Repairs Table */}
            <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 text-xs uppercase tracking-wider">
                      <th className="p-4">Repair No</th>
                      <th className="p-4">Bike & Reg No</th>
                      <th className="p-4">Mechanic</th>
                      <th className="p-4">Customer</th>
                      <th className="p-4">Status</th>
                      <th className="p-4 text-center">Items</th>
                      <th className="p-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredRepairs.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-slate-400">
                          No repairs match the filter.
                        </td>
                      </tr>
                    ) : (
                      filteredRepairs.map((rep) => (
                        <tr key={rep.id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="p-4 font-bold text-blue-600">{rep.repairNo}</td>
                          <td className="p-4">
                            <div className="font-bold text-slate-900">{rep.bikeRegistration}</div>
                            <div className="text-xs text-slate-500">{rep.bikeModel}</div>
                          </td>
                          <td className="p-4 text-slate-700">{rep.mechanicName}</td>
                          <td className="p-4 text-slate-700">{rep.customerName || "Walk-in"}</td>
                          <td className="p-4">
                            <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${
                              rep.status === "repairing" ? "bg-blue-50 text-blue-600" :
                              rep.status === "ready_for_billing" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
                            }`}>
                              {rep.status.replace(/_/g, " ").toUpperCase()}
                            </span>
                          </td>
                          <td className="p-4 text-center font-bold text-slate-700">{rep.items.length}</td>
                          <td className="p-4 text-right">
                            <button
                              onClick={() => setSelectedRepairForBilling(rep)}
                              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs transition-all shadow-sm"
                            >
                              {rep.status === "completed" ? "View / Audit" : "Review & Bill"}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === "mechanics" && currentUser.role === "owner" && (
          <MechanicsManagement currentUser={currentUser} />
        )}
        {activeTab === "history" && <BikeHistory />}
        {activeTab === "analytics" && currentUser.role === "owner" && <AnalyticsView />}
      </main>

      {/* Repair Management & Billing Modal */}
      {selectedRepairForBilling && (
        <RepairManagement
          repair={selectedRepairForBilling}
          currentUser={currentUser}
          onClose={() => {
            setSelectedRepairForBilling(null);
            fetchData();
          }}
          onRefresh={fetchData}
        />
      )}
    </div>
  );
}
