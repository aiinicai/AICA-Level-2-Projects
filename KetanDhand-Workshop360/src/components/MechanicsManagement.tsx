import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";
import { User } from "@/types";
import { Shield, CheckCircle, XCircle, Lock, UserX, UserCheck, Key, AlertCircle, UserPlus, Plus, X, Phone, Mail } from "lucide-react";

interface MechanicsManagementProps {
  currentUser: User;
}

export function MechanicsManagement({ currentUser }: MechanicsManagementProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetModalUserId, setResetModalUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  
  // Add Shopkeeper modal state
  const [showAddShopkeeperModal, setShowAddShopkeeperModal] = useState(false);
  const [shopName, setShopName] = useState("");
  const [shopPhone, setShopPhone] = useState("");
  const [shopEmail, setShopEmail] = useState("");
  const [shopPassword, setShopPassword] = useState("");
  const [shopConfirmPassword, setShopConfirmPassword] = useState("");

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const fetchUsers = async () => {
    try {
      const res = await apiFetch("/api/users");
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      console.error("Error fetching users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleStatusChange = async (userId: string, status: string) => {
    if (currentUser.role !== "owner") {
      setError("Only the Owner can approve or reject logins.");
      return;
    }
    setError("");
    setMessage("");
    try {
      const res = await apiFetch(`/api/users/${userId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("Failed to update user status");
      fetchUsers();
      setMessage("User status updated successfully.");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId: string, userName: string) => {
    if (currentUser.role !== "owner") {
      setError("Only the Owner can remove logins.");
      return;
    }
    if (!window.confirm(`Are you sure you want to completely remove login for ${userName}? This action cannot be undone.`)) return;
    setError("");
    setMessage("");
    try {
      const res = await apiFetch(`/api/users/${userId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to remove user");
      fetchUsers();
      setMessage("User login removed successfully.");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateShopkeeper = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    if (shopPassword !== shopConfirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const res = await apiFetch("/api/users/shopkeeper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: shopName,
          phone: shopPhone,
          email: shopEmail,
          password: shopPassword,
          confirmPassword: shopConfirmPassword,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create shopkeeper");
      
      setMessage("Shopkeeper created successfully. Pending approval status.");
      setShowAddShopkeeperModal(false);
      setShopName("");
      setShopPhone("");
      setShopEmail("");
      setShopPassword("");
      setShopConfirmPassword("");
      fetchUsers();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetModalUserId) return;
    setError("");
    setMessage("");
    try {
      const res = await apiFetch(`/api/users/${resetModalUserId}/password`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to reset password");
      setMessage("User password updated successfully.");
      setResetModalUserId(null);
      setNewPassword("");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const shopkeepers = users.filter((u) => u.role === "shopkeeper");
  const pendingShopkeepers = shopkeepers.filter((u) => u.status === "pending");

  const mechanics = users.filter((u) => u.role === "mechanic");
  const pendingMechanics = mechanics.filter((u) => u.status === "pending");
  const allStaff = users.filter((u) => u.role !== "owner");

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Users / Team Management</h2>
          <p className="text-sm text-slate-500">Manage shopkeepers, approve mechanics, and control system access.</p>
        </div>
        {currentUser.role === "owner" && (
          <button
            onClick={() => setShowAddShopkeeperModal(true)}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-sm shadow-md flex items-center gap-2 transition-all"
          >
            <UserPlus className="w-4 h-4" /> Add Shopkeeper
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {message && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* Pending Shopkeepers Approvals */}
      {pendingShopkeepers.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-6 space-y-4">
          <div className="flex items-center gap-2 text-amber-800 font-bold">
            <AlertCircle className="w-5 h-5 text-amber-600" /> Pending Shopkeepers ({pendingShopkeepers.length})
            {currentUser.role !== "owner" && <span className="text-xs font-normal text-slate-500">(Approval restricted to Owner)</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingShopkeepers.map((shop) => (
              <div key={shop.id} className="bg-white border border-slate-200 p-4 rounded-xl flex items-center justify-between gap-4 shadow-xs">
                <div>
                  <h4 className="font-bold text-slate-900 text-base">{shop.name}</h4>
                  <p className="text-xs text-slate-500">Phone: {shop.phone}</p>
                  {shop.email && <p className="text-xs text-slate-500">Email: {shop.email}</p>}
                </div>
                {currentUser.role === "owner" && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleStatusChange(shop.id, "approved")}
                      className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 shadow-xs"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button
                      onClick={() => handleStatusChange(shop.id, "rejected")}
                      className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 shadow-xs"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Mechanics Approvals */}
      {pendingMechanics.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-6 space-y-4">
          <div className="flex items-center gap-2 text-amber-800 font-bold">
            <AlertCircle className="w-5 h-5 text-amber-600" /> Pending Mechanic Approvals ({pendingMechanics.length})
            {currentUser.role !== "owner" && <span className="text-xs font-normal text-slate-500">(Approval restricted to Owner)</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingMechanics.map((mech) => (
              <div key={mech.id} className="bg-white border border-slate-200 p-4 rounded-xl flex items-center justify-between gap-4 shadow-xs">
                <div>
                  <h4 className="font-bold text-slate-900 text-base">{mech.name}</h4>
                  <p className="text-xs text-slate-500">Phone: {mech.phone}</p>
                  {mech.email && <p className="text-xs text-slate-500">Email: {mech.email}</p>}
                </div>
                {currentUser.role === "owner" && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleStatusChange(mech.id, "approved")}
                      className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 shadow-xs"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button
                      onClick={() => handleStatusChange(mech.id, "rejected")}
                      className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 shadow-xs"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Staff List */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900">All Workshop Team Members</h3>
          <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-semibold">
            Total Staff: {allStaff.length}
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {allStaff.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-sm">No other staff members found.</div>
          ) : (
            allStaff.map((member) => (
              <div key={member.id} className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors">
                <div>
                  <div className="flex items-center gap-3">
                    <h4 className="font-bold text-slate-900 text-base">{member.name}</h4>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                      member.role === "shopkeeper" ? "bg-purple-50 text-purple-700 border border-purple-200" : "bg-blue-50 text-blue-700 border border-blue-200"
                    }`}>
                      {member.role}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      member.status === "approved" ? "bg-emerald-50 text-emerald-700" :
                      member.status === "pending" ? "bg-amber-50 text-amber-700" :
                      member.status === "deactivated" ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-700"
                    }`}>
                      {member.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-4 flex-wrap">
                    <span>Phone: {member.phone}</span>
                    {member.email && <span>Email: {member.email}</span>}
                    <span>Joined: {new Date(member.createdAt).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {currentUser.role === "owner" && (
                    <>
                      {member.status === "approved" ? (
                        <button
                          onClick={() => handleStatusChange(member.id, "deactivated")}
                          className="px-3 py-1.5 bg-white hover:bg-red-50 hover:text-red-600 text-slate-700 rounded-xl text-xs font-semibold border border-slate-200 transition-colors flex items-center gap-1.5 shadow-xs"
                        >
                          <UserX className="w-3.5 h-3.5" /> Deactivate
                        </button>
                      ) : member.status === "deactivated" || member.status === "rejected" || member.status === "pending" ? (
                        <button
                          onClick={() => handleStatusChange(member.id, "approved")}
                          className="px-3 py-1.5 bg-white hover:bg-emerald-50 hover:text-emerald-600 text-slate-700 rounded-xl text-xs font-semibold border border-slate-200 transition-colors flex items-center gap-1.5 shadow-xs"
                        >
                          <UserCheck className="w-3.5 h-3.5" /> Approve / Activate
                        </button>
                      ) : null}

                      <button
                        onClick={() => setResetModalUserId(member.id)}
                        className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 rounded-xl text-xs font-semibold border border-amber-200 transition-colors flex items-center gap-1.5 shadow-xs"
                      >
                        <Key className="w-3.5 h-3.5" /> Reset Password
                      </button>

                      <button
                        onClick={() => handleDeleteUser(member.id, member.name)}
                        className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-xl text-xs font-semibold border border-red-200 transition-colors flex items-center gap-1.5 shadow-xs"
                      >
                        <UserX className="w-3.5 h-3.5" /> Remove Login
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add Shopkeeper Modal */}
      {showAddShopkeeperModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 max-w-md w-full p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Add New Shopkeeper</h3>
              <button onClick={() => setShowAddShopkeeperModal(false)} className="text-slate-400 hover:text-slate-700 p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Create a shopkeeper account. Shopkeepers have operational and billing access but cannot view analytics or manage user approvals.
            </p>
            <form onSubmit={handleCreateShopkeeper} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={shopName}
                  onChange={(e) => setShopName(e.target.value)}
                  placeholder="e.g. Anil Seth"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number *</label>
                <input
                  type="tel"
                  required
                  value={shopPhone}
                  onChange={(e) => setShopPhone(e.target.value)}
                  placeholder="e.g. 9876501234"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email (Optional)</label>
                <input
                  type="email"
                  value={shopEmail}
                  onChange={(e) => setShopEmail(e.target.value)}
                  placeholder="anil@sethautospares.com"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Password *</label>
                <input
                  type="password"
                  required
                  minLength={4}
                  value={shopPassword}
                  onChange={(e) => setShopPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm Password *</label>
                <input
                  type="password"
                  required
                  minLength={4}
                  value={shopConfirmPassword}
                  onChange={(e) => setShopConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddShopkeeperModal(false)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-bold shadow-md transition-all"
                >
                  Create Shopkeeper
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {resetModalUserId && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 max-w-md w-full p-6 rounded-2xl shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Reset User Password</h3>
            <p className="text-xs text-slate-500">
              Set a new password for the staff member. No OTP required. Existing passwords are never shown.
            </p>
            <form onSubmit={handlePasswordReset} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">New Password *</label>
                <input
                  type="password"
                  required
                  minLength={4}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setResetModalUserId(null)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl text-sm font-bold shadow-md transition-all"
                >
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
