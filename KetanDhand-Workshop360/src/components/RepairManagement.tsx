import React, { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { Repair, User, RepairItem } from "@/types";
import { X, Plus, Trash2, Edit2, CheckCircle2, DollarSign, Calculator, FileText, ArrowLeft, History, Shield, AlertCircle, Download, Eye } from "lucide-react";
import jsPDF from "jspdf";

interface RepairManagementProps {
  repair: Repair;
  currentUser: User;
  onClose: () => void;
  onRefresh: () => void;
}

export function RepairManagement({ repair, currentUser, onClose, onRefresh }: RepairManagementProps) {
  const [items, setItems] = useState<RepairItem[]>(repair.items || []);
  const [labourCharges, setLabourCharges] = useState(repair.labourCharges || 0);
  const [discount, setDiscount] = useState(repair.discount || 0);
  const [taxRate, setTaxRate] = useState(repair.taxRate !== undefined && repair.taxRate !== 18 ? repair.taxRate : 0);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [loading, setLoading] = useState(false);

  // New item state for owner/shopkeeper
  const [newItemName, setNewItemName] = useState("");
  const [newItemQty, setNewItemQty] = useState(1);
  const [newItemRate, setNewItemRate] = useState(0);

  // Editing item
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editQty, setEditQty] = useState(1);
  const [editRate, setEditRate] = useState(0);

  // PDF Preview Modal state
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfDataUri, setPdfDataUri] = useState("");

  // Calculate totals
  const itemsTotal = items.reduce((sum, item) => sum + item.quantity * item.rate, 0);
  const taxableAmount = Math.max(0, itemsTotal + Number(labourCharges) - Number(discount));
  const taxAmount = (taxableAmount * Number(taxRate)) / 100;
  const grandTotal = Math.round(taxableAmount + taxAmount);

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim()) return;
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newItemName.trim(),
          quantity: Number(newItemQty),
          userName: currentUser.name,
          userRole: currentUser.role,
        }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error);
      
      const addedItem = updated.items[updated.items.length - 1];
      if (newItemRate > 0 && addedItem) {
        await handleUpdateItemRateAndQty(addedItem.id, addedItem.name, addedItem.quantity, newItemRate);
      } else {
        setItems(updated.items);
      }

      setNewItemName("");
      setNewItemQty(1);
      setNewItemRate(0);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdateItemRateAndQty = async (itemId: string, name: string, qty: number, rate: number) => {
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/items/${itemId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          quantity: qty,
          rate,
          userName: currentUser.name,
          userRole: currentUser.role,
        }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error);
      setItems(updated.items);
      setEditingItemId(null);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!window.confirm("Delete this item?")) return;
    try {
      const res = await apiFetch(
        `/api/repairs/${repair.id}/items/${itemId}?userName=${encodeURIComponent(currentUser.name)}&userRole=${currentUser.role}`,
        { method: "DELETE" }
      );
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error);
      setItems(updated.items);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSaveBilling = async () => {
    setError("");
    setSuccessMsg("");
    setLoading(true);
    try {
      const res = await apiFetch(`/api/repairs/${repair.id}/billing`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          labourCharges: Number(labourCharges),
          discount: Number(discount),
          taxRate: Number(taxRate),
          items,
          userName: currentUser.name,
        }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error);
      onRefresh();
      setSuccessMsg("Billing and corrections saved successfully!");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteAndFinalize = async () => {
    setError("");
    setSuccessMsg("");
    setLoading(true);
    try {
      // Save billing first
      const billRes = await apiFetch(`/api/repairs/${repair.id}/billing`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          labourCharges: Number(labourCharges),
          discount: Number(discount),
          taxRate: Number(taxRate),
          items,
          userName: currentUser.name,
        }),
      });
      const billData = await billRes.json();
      if (!billRes.ok) throw new Error(billData.error || "Failed to save billing");

      // Then mark complete
      const res = await apiFetch(`/api/repairs/${repair.id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userName: currentUser.name }),
      });
      const updated = await res.json();
      if (!res.ok) throw new Error(updated.error || "Failed to complete repair");

      onRefresh();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const generateCustomerPDF = (previewAfterGenerate = false) => {
    const doc = new jsPDF();
    let y = 20;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(16);
    doc.text("Seth Auto Spares - Item Bill", 20, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Repair No: ${repair.repairNo} | Date: ${new Date().toLocaleDateString()}`, 20, y);
    y += 6;
    doc.text(`Bike: ${repair.bikeModel} (${repair.bikeRegistration}) | Customer: ${repair.customerName || "Walk-in"}`, 20, y);
    y += 10;

    // Table header
    doc.setFont("helvetica", "bold");
    doc.text("Product / Item", 20, y);
    doc.text("Qty", 100, y);
    doc.text("Rate", 130, y);
    doc.text("Amount", 165, y);
    y += 4;
    doc.line(20, y, 190, y);
    y += 8;

    doc.setFont("helvetica", "normal");
    items.forEach((item) => {
      const amt = item.quantity * item.rate;
      doc.text(item.name, 20, y);
      doc.text(String(item.quantity), 100, y);
      doc.text(`₹${item.rate}`, 130, y);
      doc.text(`₹${amt}`, 165, y);
      y += 8;
    });

    doc.line(20, y, 190, y);
    y += 8;

    // Totals breakdown
    doc.setFont("helvetica", "normal");
    doc.text(`Items Total:`, 120, y);
    doc.text(`₹${itemsTotal}`, 165, y);
    y += 6;

    if (labourCharges > 0) {
      doc.text(`Labour Charges:`, 120, y);
      doc.text(`₹${labourCharges}`, 165, y);
      y += 6;
    }

    if (discount > 0) {
      doc.text(`Discount:`, 120, y);
      doc.text(`-₹${discount}`, 165, y);
      y += 6;
    }

    if (taxRate > 0) {
      const taxAmt = (taxableAmount * taxRate) / 100;
      doc.text(`Tax (${taxRate}% GST):`, 120, y);
      doc.text(`₹${taxAmt.toFixed(2)}`, 165, y);
      y += 6;
    }

    doc.setFont("helvetica", "bold");
    doc.text(`Grand Total:`, 120, y);
    doc.text(`₹${grandTotal}`, 165, y);

    if (previewAfterGenerate) {
      const dataUri = doc.output("datauristring");
      setPdfDataUri(dataUri);
      setShowPdfModal(true);
    } else {
      doc.save(`item-bill-${repair.repairNo.toLowerCase()}.pdf`);
    }
  };

  const handleDownloadPDFOnly = () => {
    generateCustomerPDF(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex flex-col justify-end sm:justify-center p-0 sm:p-4 font-sans">
      <div className="bg-white border border-slate-200 w-full max-w-4xl mx-auto sm:rounded-2xl flex flex-col max-h-[92vh] shadow-xl">
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
            <h2 className="text-xl font-bold text-slate-900 mt-1">
              Repair Review & Billing: {repair.bikeModel} ({repair.bikeRegistration})
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
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm">
            <div>
              <span className="text-slate-500 text-xs block">Mechanic</span>
              <span className="font-semibold text-slate-900">{repair.mechanicName}</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Customer</span>
              <span className="font-semibold text-slate-900">{repair.customerName || "Walk-in"}</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Start Time</span>
              <span className="font-semibold text-slate-900">{new Date(repair.startTime).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Phone</span>
              <span className="font-semibold text-slate-900">{repair.customerPhone || "N/A"}</span>
            </div>
          </div>

          {/* ITEMS & BILLING TABLE */}
          <div className="space-y-4">
            <h3 className="text-base font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Calculator className="w-5 h-5 text-blue-600" /> Parts / Products & Rates (Initially ₹0)
            </h3>

            {/* Add Item Form */}
            <form onSubmit={handleAddItem} className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
              <div className="sm:col-span-5">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Product Name</label>
                <input
                  type="text"
                  required
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  placeholder="e.g. Brake Pad"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Qty</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newItemQty}
                  onChange={(e) => setNewItemQty(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm font-semibold"
                />
              </div>
              <div className="sm:col-span-3">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Rate (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={newItemRate}
                  onChange={(e) => setNewItemRate(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm font-semibold"
                />
              </div>
              <div className="sm:col-span-2">
                <button
                  type="submit"
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 shadow-sm"
                >
                  <Plus className="w-4 h-4" /> Add Item
                </button>
              </div>
            </form>

            {/* Items Table */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <div className="overflow-x-auto -mx-px">
              <table className="w-full min-w-[640px] text-left border-collapse text-sm">

                <thead>
                  <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 text-xs uppercase">
                    <th className="p-3">Item Name</th>
                    <th className="p-3 text-center">Qty</th>
                    <th className="p-3 text-right">Rate (₹)</th>
                    <th className="p-3 text-right">Amount (₹)</th>
                    <th className="p-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-6 text-slate-400 text-sm">
                        No items added yet.
                      </td>
                    </tr>
                  ) : (
                    items.map((item) => {
                      const isEditing = editingItemId === item.id;
                      return (
                        <tr key={item.id} className="hover:bg-slate-50/50">
                          <td className="p-3">
                            {isEditing ? (
                              <input
                                type="text"
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                className="w-full px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-900 text-xs font-medium"
                              />
                            ) : (
                              <div>
                                <span className="font-bold text-slate-900">{item.name}</span>
                                <span className="block text-[10px] text-slate-400">Added by {item.addedByName} ({item.addedBy})</span>
                              </div>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            {isEditing ? (
                              <input
                                type="number"
                                min="1"
                                value={editQty}
                                onChange={(e) => setEditQty(Number(e.target.value))}
                                className="w-16 px-2 py-1 bg-white border border-slate-200 rounded text-slate-900 text-xs font-semibold text-center mx-auto"
                              />
                            ) : (
                              <span className="font-bold text-slate-800">{item.quantity}</span>
                            )}
                          </td>
                          <td className="p-3 text-right">
                            {isEditing ? (
                              <input
                                type="number"
                                min="0"
                                value={editRate}
                                onChange={(e) => setEditRate(Number(e.target.value))}
                                className="w-24 px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-900 text-xs font-semibold text-right ml-auto"
                              />
                            ) : (
                              <span className="font-semibold text-slate-900">₹{item.rate}</span>
                            )}
                          </td>
                          <td className="p-3 text-right font-extrabold text-blue-600">
                            ₹{item.quantity * item.rate}
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-2">
                              {isEditing ? (
                                <button
                                  onClick={() => handleUpdateItemRateAndQty(item.id, editName, editQty, editRate)}
                                  className="px-2.5 py-1 bg-emerald-600 text-white rounded text-xs font-bold"
                                >
                                  Save
                                </button>
                              ) : (
                                <button
                                  onClick={() => {
                                    setEditingItemId(item.id);
                                    setEditName(item.name);
                                    setEditQty(item.quantity);
                                    setEditRate(item.rate);
                                  }}
                                  className="p-1.5 text-slate-500 hover:text-blue-600 rounded"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => handleDeleteItem(item.id)}
                                className="p-1.5 text-slate-500 hover:text-red-600 rounded"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
              </div>
            </div>

          </div>

          {/* Labour, Discount, Tax */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Labour Charges (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={labourCharges}
                  onChange={(e) => setLabourCharges(Number(e.target.value))}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 font-semibold text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Discount (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={discount}
                  onChange={(e) => setDiscount(Number(e.target.value))}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 font-semibold text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">GST / Tax Rate (%)</label>
                <select
                  value={taxRate}
                  onChange={(e) => setTaxRate(Number(e.target.value))}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 font-semibold text-sm"
                >
                  <option value={0}>0% (No Tax)</option>
                  <option value={5}>5% GST</option>
                  <option value={12}>12% GST</option>
                  <option value={18}>18% GST</option>
                  <option value={28}>28% GST</option>
                </select>
              </div>
            </div>

            {/* Totals Breakdown */}
            <div className="pt-4 border-t border-slate-200 space-y-1.5 text-sm">
              <div className="flex justify-between text-slate-600">
                <span>Items Total:</span>
                <span className="font-semibold text-slate-900">₹{itemsTotal}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Labour:</span>
                <span className="font-semibold text-slate-900">₹{labourCharges}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Discount:</span>
                <span className="font-semibold text-red-600">- ₹{discount}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Tax ({taxRate}%):</span>
                <span className="font-semibold text-slate-900">₹{taxAmount.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-lg font-extrabold text-blue-600 pt-2 border-t border-slate-200">
                <span>Grand Total:</span>
                <span>₹{grandTotal}</span>
              </div>
            </div>
          </div>

          {/* AUDIT TRAIL */}
          <div className="space-y-2 pt-2">
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-4 h-4" /> Internal Audit Trail
            </h4>
            <div className="bg-slate-900 text-slate-200 p-3 rounded-xl border border-slate-800 space-y-2 max-h-40 overflow-y-auto text-xs font-mono">
              {repair.auditTrail && repair.auditTrail.map((log) => (
                <div key={log.id} className="border-b border-slate-800 pb-1.5 last:border-0">
                  <span className="text-amber-400">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{" "}
                  <strong className="text-white">{log.userName}</strong> ({log.userRole}): {log.details}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-6 border-t border-slate-200 bg-slate-50 sm:rounded-b-2xl flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSaveBilling}
              disabled={loading}
              className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-colors border border-slate-200 shadow-xs"
            >
              Save Changes
            </button>
            <button
              type="button"
              onClick={() => generateCustomerPDF(true)}
              className="px-4 py-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold text-xs transition-colors border border-blue-200 flex items-center gap-1.5 shadow-xs"
            >
              <Eye className="w-4 h-4" /> Preview Customer Bill PDF
            </button>
            <button
              type="button"
              onClick={handleDownloadPDFOnly}
              className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs transition-colors border border-slate-200 flex items-center gap-1.5 shadow-xs"
            >
              <Download className="w-4 h-4" /> Download PDF
            </button>
          </div>

          {repair.status !== "completed" && (
            <button
              type="button"
              onClick={handleCompleteAndFinalize}
              disabled={loading}
              className="py-3 px-6 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-md flex items-center justify-center gap-2 text-sm transition-all"
            >
              <CheckCircle2 className="w-4 h-4" /> Finalise Bill & Complete
            </button>
          )}
        </div>
      </div>

      {/* Customer PDF Preview Modal */}
      {showPdfModal && (
        <div className="fixed inset-0 z-[60] bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 max-w-2xl w-full p-6 rounded-2xl shadow-2xl space-y-4 flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Customer Item Bill PDF Preview</h3>
                <p className="text-xs text-slate-500">Contains ONLY Product/Item Name, Quantity, and Rate (as required).</p>
              </div>
              <button onClick={() => setShowPdfModal(false)} className="text-slate-400 hover:text-slate-700 p-1">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 bg-slate-100 rounded-xl overflow-hidden min-h-[350px] border border-slate-200">
              {pdfDataUri ? (
                <iframe src={pdfDataUri} className="w-full h-full min-h-[350px]" title="PDF Preview" />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400">Loading PDF Preview...</div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowPdfModal(false)}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const doc = new jsPDF();
                  let y = 25;
                  doc.setFont("helvetica", "bold");
                  doc.setFontSize(14);
                  doc.text("Item Bill", 20, y);
                  y += 10;
                  doc.setFontSize(10);
                  doc.text("Product / Item", 20, y);
                  doc.text("Qty", 110, y);
                  doc.text("Rate", 150, y);
                  y += 4;
                  doc.line(20, y, 190, y);
                  y += 8;
                  doc.setFont("helvetica", "normal");
                  items.forEach((item) => {
                    doc.text(item.name, 20, y);
                    doc.text(String(item.quantity), 110, y);
                    doc.text(`₹${item.rate}`, 150, y);
                    y += 8;
                  });
                  doc.line(20, y, 190, y);
                  doc.save(`item-bill-${repair.repairNo.toLowerCase()}.pdf`);
                }}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-sm shadow-md flex items-center gap-2"
              >
                <Download className="w-4 h-4" /> Download PDF File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
