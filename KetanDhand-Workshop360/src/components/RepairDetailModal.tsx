import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api-client";
import { Repair, User, RepairItem } from "@/types";
import { X, Plus, Trash2, Edit2, CheckCircle2, AlertTriangle, Clock, Bike, User as UserIcon, Phone, Check, ArrowLeft } from "lucide-react";

interface RepairDetailModalProps {
  repair: Repair;
  currentUser: User;
  onClose: () => void;
  onRefresh: () => void;
}

export function RepairDetailModal({ repair, currentUser, onClose, onRefresh }: RepairDetailModalProps) {
  const [items, setItems] = useState<RepairItem[]>(repair.items || []);
  const [itemName, setItemName] = useState("");
  const [itemQty, setItemQty] = useState(1);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showFinishConfirm, setShowFinishConfirm] = useState(false);

  // Editing specific item
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState(1);
  const [editName, setEditName] = useState("");

  const isMechanic = currentUser.role === "mechanic";
  const isReadOnly = isMechanic && repair.status !== "repairing";

  useEffect(() => {
    // Fetch suggestions
    apiFetch("/api/suggestions")
      .then((res) => res.json())
      .then((data) => setSuggestions(data))
      .catch((err) => console.error("Error fetching suggestions:", err));
  }, []);

  useEffect(() => {
    setItems(repair.items || []);
  }, [repair]);

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!itemName.trim()) return;
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: itemName.trim(),
          quantity: Number(itemQty),
          userName: currentUser.name,
          userRole: currentUser.role,
        }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error || "Failed to add item");
      setItems(updated.items);
      setItemName("");
      setItemQty(1);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateItem = async (itemId: string) => {
    setError("");
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/items/${itemId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          quantity: Number(editQty),
          userName: currentUser.name,
          userRole: currentUser.role,
        }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error || "Failed to update item");
      setItems(updated.items);
      setEditingItemId(null);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!window.confirm("Are you sure you want to remove this item?")) return;
    setError("");
    try {
      const res = await apiFetch(
        `/api/repairs/${repair.id}/items/${itemId}?userName=${encodeURIComponent(currentUser.name)}&userRole=${currentUser.role}`,
        { method: "DELETE" }
      );
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error || "Failed to delete item");
      setItems(updated.items);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleFinishRepair = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/finish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userName: currentUser.name }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error || "Failed to finish repair");
      onRefresh();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
      setShowFinishConfirm(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex flex-col justify-end sm:justify-center p-0 sm:p-4 font-sans">
      <div className="bg-white border border-slate-200 w-full max-w-2xl mx-auto sm:rounded-2xl flex flex-col max-h-[92vh] shadow-xl">
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50 sm:rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-blue-50 text-blue-600 font-bold text-xs rounded-full">
                {repair.repairNo}
              </span>
              <span className={`px-2.5 py-1 font-semibold text-xs rounded-full ${
                repair.status === "repairing" ? "bg-blue-50 text-blue-600" :
                repair.status === "ready_for_billing" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
              }`}>
                {repair.status.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 mt-1 flex items-center gap-2">
              <Bike className="w-5 h-5 text-blue-600" /> {repair.bikeModel} ({repair.bikeRegistration})
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 bg-white">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm">
              {error}
            </div>
          )}

          {/* Bike & Customer Metadata */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-sm">
            <div>
              <span className="text-slate-500 text-xs block">Mechanic</span>
              <span className="font-medium text-slate-900">{repair.mechanicName}</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Customer</span>
              <span className="font-medium text-slate-900">{repair.customerName || "Walk-in"}</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Phone</span>
              <span className="font-medium text-slate-900">{repair.customerPhone || "N/A"}</span>
            </div>
          </div>

          {/* ITEMS USED SECTION */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                Items Used <span className="text-xs bg-slate-100 px-2 py-0.5 rounded-full text-slate-700 font-normal">{items.length}</span>
              </h3>
              {isReadOnly && (
                <span className="text-xs text-amber-700 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200">
                  🔒 Read-Only (Finished by Mechanic)
                </span>
              )}
            </div>

            {/* Add Item Form (Only if not read-only) */}
            {!isReadOnly && (
              <form onSubmit={handleAddItem} className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3 mb-4">
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  + Add Part / Product
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      list="product-suggestions"
                      required
                      value={itemName}
                      onChange={(e) => setItemName(e.target.value)}
                      placeholder="Type product name (e.g. Brake Pad, Engine Oil)"
                      className="w-full px-3.5 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    />
                    <datalist id="product-suggestions">
                      {suggestions.map((s, i) => (
                        <option key={i} value={s} />
                      ))}
                    </datalist>
                  </div>
                  <div className="w-24">
                    <input
                      type="number"
                      min="1"
                      required
                      value={itemQty}
                      onChange={(e) => setItemQty(Number(e.target.value))}
                      placeholder="Qty"
                      className="w-full px-3 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-center text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-sm transition-all flex items-center justify-center gap-2 text-base"
                >
                  <Plus className="w-5 h-5 stroke-[3]" /> Add Item to Repair
                </button>
              </form>
            )}

            {/* Items List */}
            <div className="space-y-2.5">
              {items.length === 0 ? (
                <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-slate-500 text-sm">
                  No items added yet. Click &quot;Add Item&quot; above.
                </div>
              ) : (
                items.map((item) => (
                  <div
                    key={item.id}
                    className="bg-white border border-slate-200 p-3.5 rounded-xl flex items-center justify-between gap-3 shadow-2xs"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-slate-900 text-sm sm:text-base truncate">{item.name}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                        <span>Added by {item.addedByName}</span>
                        <span>•</span>
                        <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>

                    {editingItemId === item.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="1"
                          value={editQty}
                          onChange={(e) => setEditQty(Number(e.target.value))}
                          className="w-16 px-2 py-1 bg-white border border-slate-200 text-slate-900 rounded text-center text-sm"
                        />
                        <button
                          onClick={() => handleUpdateItem(item.id)}
                          className="p-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingItemId(null)}
                          className="p-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="px-3 py-1 bg-slate-50 border border-slate-200 font-bold text-blue-600 rounded-lg text-sm">
                          × {item.quantity}
                        </span>

                        {!isReadOnly && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => {
                                setEditingItemId(item.id);
                                setEditQty(item.quantity);
                                setEditName(item.name);
                              }}
                              className="p-2 text-slate-400 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors"
                              title="Edit Quantity"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteItem(item.id)}
                              className="p-2 text-slate-400 hover:text-red-600 hover:bg-slate-100 rounded-lg transition-colors"
                              title="Delete Item"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-6 border-t border-slate-200 bg-slate-50 sm:rounded-b-2xl flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-3 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-100 font-semibold text-sm transition-colors"
          >
            Close
          </button>

          {!isReadOnly && repair.status === "repairing" && (
            <button
              type="button"
              onClick={() => setShowFinishConfirm(true)}
              className="flex-1 py-3 px-6 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-sm flex items-center justify-center gap-2 text-base transition-all"
            >
              <CheckCircle2 className="w-5 h-5" /> FINISH REPAIR
            </button>
          )}
        </div>
      </div>

      {/* Finish Confirmation Modal */}
      {showFinishConfirm && (
        <div className="fixed inset-0 z-60 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 max-w-md w-full p-6 rounded-2xl shadow-xl space-y-4">
            <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 text-center">Finish Repair Confirmation</h3>
            <p className="text-slate-600 text-sm text-center leading-relaxed">
              &quot;After finishing, you will not be able to add, delete or edit items. The owner can make corrections if required.&quot;
            </p>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowFinishConfirm(false)}
                className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleFinishRepair}
                className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm shadow-sm transition-all"
              >
                Confirm & Finish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
