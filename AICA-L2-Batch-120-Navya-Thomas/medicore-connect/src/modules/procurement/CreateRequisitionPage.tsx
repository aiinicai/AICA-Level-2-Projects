import React, { useState } from 'react';
import {
  ShoppingCart,
  Plus,
  Trash2,
  Save,
  Send,
  X,
  AlertCircle,
  CheckCircle2,
  Paperclip,
  ArrowLeft,
  Building2,
  Calendar,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { Requisition, RequisitionLine, ItemClass, TaxCode } from '../../core/types';
import { getActiveUser, checkMakerPermission } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { round2, formatAED } from '../../core/currency';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEPARTMENTS } from '../../data/chartOfAccounts';
import { DEMO_TODAY } from '../../core/dates';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';

interface CreateRequisitionPageProps {
  onNavigate: (route: string) => void;
  editRequisitionId?: string;
}

export const CreateRequisitionPage: React.FC<CreateRequisitionPageProps> = ({
  onNavigate,
  editRequisitionId,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const makerCheck = checkMakerPermission(currentUser, 'Procurement');

  const existing = editRequisitionId
    ? db.requisitions?.find((r) => r.id === editRequisitionId)
    : undefined;

  // Header State
  const [bu, setBu] = useState<string>(existing?.businessUnit || 'H01');
  const [department, setDepartment] = useState<string>(existing?.department || 'Clinical');
  const [requisitionType, setRequisitionType] = useState<'Goods' | 'Services' | 'Capital Asset'>(
    existing?.requisitionType || 'Goods'
  );
  const [priority, setPriority] = useState<'Normal' | 'Urgent'>(existing?.priority || 'Normal');
  const [deliveryLocation, setDeliveryLocation] = useState<string>(
    existing?.deliveryLocation || 'Main Hospital Store — Sub-inventory A'
  );
  const [requisitionDate, setRequisitionDate] = useState<string>(existing?.requisitionDate || DEMO_TODAY);
  const [needByDate, setNeedByDate] = useState<string>(
    existing?.needByDate || '2026-11-05'
  );
  const [justification, setJustification] = useState<string>(
    existing?.justification || existing?.description || ''
  );

  // Lines State
  const defaultLine: RequisitionLine = {
    lineNumber: 1,
    itemCode: db.items[0]?.code || 'MED-001',
    description: db.items[0]?.description || 'Paracetamol 500mg IV Infusion',
    itemClass: 'Pharmaceutical',
    uom: 'Vial',
    quantity: 100,
    estimatedUnitPrice: 14.5,
    estimatedAmount: 1450,
    department: 'Clinical',
    chargeAccount: '1200',
    isCapital: false,
    needByDate: '2026-11-05',
  };

  const [lines, setLines] = useState<RequisitionLine[]>(
    existing?.lines && existing.lines.length > 0 ? existing.lines : [defaultLine]
  );

  const [validationError, setValidationError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState<string | null>(null);

  // Calculate totals
  const subtotal = round2(
    lines.reduce((sum, l) => sum + (l.estimatedAmount || l.quantity * (l.estimatedUnitPrice || 0)), 0)
  );
  const estimatedTax = round2(subtotal * 0.05); // Standard 5%
  const grandTotal = round2(subtotal + estimatedTax);

  // Handlers
  const handleItemSelect = (index: number, itemCode: string) => {
    const item = db.items.find((i) => i.code === itemCode);
    if (!item) return;

    const newLines = [...lines];
    newLines[index] = {
      ...newLines[index],
      itemCode: item.code,
      description: item.description,
      itemClass: item.itemClass,
      uom: item.uom,
      estimatedUnitPrice: item.unitPrice,
      estimatedAmount: round2(newLines[index].quantity * item.unitPrice),
      chargeAccount:
        item.itemClass === 'Pharmaceutical'
          ? '1200'
          : item.itemClass === 'Consumable'
          ? '1210'
          : item.itemClass === 'Capital Asset'
          ? '1610'
          : '5010',
      isCapital: item.itemClass === 'Capital Asset',
      assetCategory: item.itemClass === 'Capital Asset' ? 'Medical Equipment' : undefined,
    };
    setLines(newLines);
  };

  const handleLineChange = (index: number, field: keyof RequisitionLine, value: any) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };

    if (field === 'quantity' || field === 'estimatedUnitPrice') {
      const q = field === 'quantity' ? Number(value) : newLines[index].quantity;
      const p = field === 'estimatedUnitPrice' ? Number(value) : (newLines[index].estimatedUnitPrice || 0);
      newLines[index].estimatedAmount = round2(q * p);
    }
    setLines(newLines);
  };

  const handleAddLine = () => {
    const nextNum = lines.length + 1;
    setLines([
      ...lines,
      {
        lineNumber: nextNum,
        itemCode: '',
        description: '',
        itemClass: requisitionType === 'Capital Asset' ? 'Capital Asset' : 'Pharmaceutical',
        uom: 'Each',
        quantity: 1,
        estimatedUnitPrice: 0,
        estimatedAmount: 0,
        department,
        chargeAccount: requisitionType === 'Capital Asset' ? '1610' : '1200',
        isCapital: requisitionType === 'Capital Asset',
        assetCategory: requisitionType === 'Capital Asset' ? 'Medical Equipment' : undefined,
        needByDate,
      },
    ]);
  };

  const handleRemoveLine = (index: number) => {
    if (lines.length <= 1) return;
    const newLines = lines.filter((_, i) => i !== index).map((l, i) => ({ ...l, lineNumber: i + 1 }));
    setLines(newLines);
  };

  const validate = (): boolean => {
    if (!makerCheck.allowed) {
      setValidationError(makerCheck.reason || 'You are not authorized as Procurement Maker.');
      return false;
    }
    if (!justification.trim()) {
      setValidationError('Business justification is required for all enterprise purchase requisitions.');
      return false;
    }
    if (lines.length === 0) {
      setValidationError('Requisition must contain at least one line item.');
      return false;
    }
    for (const l of lines) {
      if (!l.description.trim()) {
        setValidationError(`Line #${l.lineNumber} description is missing.`);
        return false;
      }
      if (l.quantity <= 0) {
        setValidationError(`Line #${l.lineNumber} quantity must be greater than zero.`);
        return false;
      }
      if ((l.estimatedUnitPrice || 0) < 0) {
        setValidationError(`Line #${l.lineNumber} estimated unit price cannot be negative.`);
        return false;
      }
      if (l.isCapital && !l.assetCategory) {
        setValidationError(`Line #${l.lineNumber} is marked as Capital Asset and requires an Asset Category.`);
        return false;
      }
    }
    setValidationError(null);
    return true;
  };

  const handleSave = (asDraft: boolean) => {
    if (!validate()) return;

    const reqNumber = existing?.number || getNextSequenceNumber('REQ');
    const status = asDraft ? 'Draft' : 'Pending Approval';

    const newReq: Requisition = {
      id: existing?.id || `REQ-${Date.now()}`,
      number: reqNumber,
      businessUnit: bu,
      department,
      requisitionType,
      priority,
      deliveryLocation,
      requisitionDate,
      needByDate,
      justification,
      description: justification,
      status,
      lines,
      subtotal,
      taxAmount: estimatedTax,
      totalAmount: grandTotal,
      createdBy: currentUser.userId,
      createdAt: existing?.createdAt || new Date().toISOString(),
      submittedAt: !asDraft ? new Date().toISOString() : undefined,
      requesterId: currentUser.userId,
      requesterName: currentUser.name,
      relatedPoNumbers: existing?.relatedPoNumbers || [],
    };

    updateDb((state) => {
      if (existing) {
        const idx = state.requisitions.findIndex((r) => r.id === existing.id);
        if (idx >= 0) state.requisitions[idx] = newReq;
      } else {
        if (!state.requisitions) state.requisitions = [];
        state.requisitions.unshift(newReq);
      }
    });

    addAuditLog({
      entityType: 'Requisition',
      entityId: newReq.id,
      action: asDraft ? 'CREATE' : 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `${asDraft ? 'Saved Draft' : 'Submitted for Approval'} Requisition ${newReq.number} (AED ${formatAED(grandTotal)})`,
    });

    setSavedSuccess(
      `Requisition ${newReq.number} ${asDraft ? 'saved as Draft' : 'submitted for Approval to Daniel Reed (CFO)'}.`
    );

    setTimeout(() => {
      onNavigate('#/procurement/requisitions');
    }, 1200);
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Module Access Banner */}
      <ModuleAccessBanner module="Procurement" onNavigate={onNavigate} />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onNavigate('#/procurement/requisitions')}
            className="p-2 rounded-lg bg-white border border-gray-200 text-gray-600 hover:text-[#5B2C83] hover:bg-plum-50 transition-colors cursor-pointer"
            title="Back to Requisitions"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-[#5B2C83] uppercase tracking-wider">
                Procurement Work Area
              </span>
              <span className="text-gray-300">&bull;</span>
              <span className="text-xs text-gray-500 font-mono">
                {existing?.number || 'New Requisition'}
              </span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              {existing ? `Edit Requisition ${existing.number}` : 'Create Purchase Requisition'}
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onNavigate('#/procurement/requisitions')}
            className="px-3 py-1.5 border border-gray-300 text-gray-700 hover:bg-gray-100 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={() => handleSave(true)}
            disabled={!makerCheck.allowed}
            className="px-3.5 py-1.5 border border-plum-300 bg-white text-[#5B2C83] hover:bg-plum-50 rounded-lg text-xs font-semibold shadow-2xs flex items-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save as Draft</span>
          </button>
          <button
            onClick={() => handleSave(false)}
            disabled={!makerCheck.allowed}
            className="px-4 py-1.5 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Submit for Approval</span>
          </button>
        </div>
      </div>

      {validationError && (
        <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {savedSuccess && (
        <div className="mb-5 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{savedSuccess}</span>
        </div>
      )}

      {/* Main Form Cards */}
      <div className="space-y-6">
        {/* Header Details Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83] mb-4">
            Requisition Header Information
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block text-gray-500 font-semibold mb-1">Business Unit *</label>
              <select
                value={bu}
                onChange={(e) => setBu(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] font-medium text-gray-800"
              >
                {BUSINESS_UNITS.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.code} — {b.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Department *</label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
              >
                {DEPARTMENTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Requisition Type *</label>
              <select
                value={requisitionType}
                onChange={(e) => setRequisitionType(e.target.value as any)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
              >
                <option value="Goods">Goods / Medical Supplies</option>
                <option value="Services">Services / Maintenance</option>
                <option value="Capital Asset">Capital Asset (Fixed Asset)</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as any)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
              >
                <option value="Normal">Normal</option>
                <option value="Urgent">Urgent (Clinical Escalation)</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Requisition Date</label>
              <input
                type="date"
                value={requisitionDate}
                onChange={(e) => setRequisitionDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Need-By Date</label>
              <input
                type="date"
                value={needByDate}
                onChange={(e) => setNeedByDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-gray-500 font-semibold mb-1">Delivery Location</label>
              <input
                type="text"
                value={deliveryLocation}
                onChange={(e) => setDeliveryLocation(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>
          </div>

          <div className="mt-4 text-xs">
            <label className="block text-gray-500 font-semibold mb-1">
              Business Justification * <span className="text-gray-400 font-normal">(Required for IFRS compliance)</span>
            </label>
            <textarea
              rows={2}
              required
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="State the clinical, operational, or replenishment justification for this procurement..."
              className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
            />
          </div>
        </div>

        {/* Lines Table Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83]">
                Requisition Line Items ({lines.length})
              </h2>
              <p className="text-[11px] text-gray-400">
                Item classification, quantities, estimated unit costs, and department distributions
              </p>
            </div>
            <button
              onClick={handleAddLine}
              className="px-3 py-1 bg-plum-50 border border-plum-300 text-[#5B2C83] hover:bg-plum-100 rounded-lg text-xs font-semibold flex items-center space-x-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Line</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF7FC] text-gray-700 uppercase font-semibold text-[10px] border-b border-gray-200">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Item / Description</th>
                  <th className="py-2.5 px-3">Class & UoM</th>
                  <th className="py-2.5 px-3 text-right">Qty</th>
                  <th className="py-2.5 px-3 text-right">Est. Unit Price</th>
                  <th className="py-2.5 px-3 text-right">Est. Amount (AED)</th>
                  <th className="py-2.5 px-3">Capital Asset?</th>
                  <th className="py-2.5 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lines.map((l, index) => (
                  <tr key={index} className="hover:bg-gray-50/50">
                    <td className="py-2.5 px-3 font-mono text-gray-400">{l.lineNumber}</td>

                    {/* Item & Description */}
                    <td className="py-2.5 px-3 min-w-[200px]">
                      <select
                        value={l.itemCode || ''}
                        onChange={(e) => handleItemSelect(index, e.target.value)}
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs mb-1 font-mono text-[#5B2C83]"
                      >
                        <option value="">-- Free text or Master Item --</option>
                        {db.items.slice(0, 80).map((it) => (
                          <option key={it.code} value={it.code}>
                            {it.code} - {it.description}
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        value={l.description}
                        onChange={(e) => handleLineChange(index, 'description', e.target.value)}
                        placeholder="Item line description..."
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs"
                      />
                    </td>

                    {/* Class & UOM */}
                    <td className="py-2.5 px-3 w-32">
                      <select
                        value={l.itemClass}
                        onChange={(e) => handleLineChange(index, 'itemClass', e.target.value as ItemClass)}
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs mb-1"
                      >
                        <option value="Pharmaceutical">Pharmaceutical</option>
                        <option value="Consumable">Consumable</option>
                        <option value="Implants & Surgical">Implants</option>
                        <option value="General">General Store</option>
                        <option value="Service">Service</option>
                        <option value="Capital Asset">Capital Asset</option>
                      </select>
                      <input
                        type="text"
                        value={l.uom || 'Each'}
                        onChange={(e) => handleLineChange(index, 'uom', e.target.value)}
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-600"
                        placeholder="UoM"
                      />
                    </td>

                    {/* Quantity */}
                    <td className="py-2.5 px-3 w-20 text-right">
                      <input
                        type="number"
                        min="1"
                        value={l.quantity}
                        onChange={(e) => handleLineChange(index, 'quantity', Number(e.target.value))}
                        className="w-20 px-2 py-1 text-right bg-white border border-gray-200 rounded text-xs font-mono"
                      />
                    </td>

                    {/* Estimated Unit Price */}
                    <td className="py-2.5 px-3 w-28 text-right">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={l.estimatedUnitPrice || ''}
                        onChange={(e) => handleLineChange(index, 'estimatedUnitPrice', Number(e.target.value))}
                        className="w-24 px-2 py-1 text-right bg-white border border-gray-200 rounded text-xs font-mono"
                      />
                    </td>

                    {/* Estimated Amount */}
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#5B2C83]">
                      {formatAED(l.estimatedAmount || 0)}
                    </td>

                    {/* Capital Asset Flag */}
                    <td className="py-2.5 px-3 w-36">
                      <label className="flex items-center space-x-1.5 cursor-pointer text-[11px] mb-1">
                        <input
                          type="checkbox"
                          checked={l.isCapital}
                          onChange={(e) => handleLineChange(index, 'isCapital', e.target.checked)}
                          className="rounded text-[#5B2C83]"
                        />
                        <span className="font-semibold text-gray-700">Capital</span>
                      </label>
                      {l.isCapital && (
                        <select
                          value={l.assetCategory || 'Medical Equipment'}
                          onChange={(e) => handleLineChange(index, 'assetCategory', e.target.value)}
                          className="w-full px-1.5 py-0.5 bg-white border border-plum-300 rounded text-[10px]"
                        >
                          <option value="Medical Equipment">Medical Equipment</option>
                          <option value="Buildings">Buildings</option>
                          <option value="IT Equipment">IT Equipment</option>
                          <option value="Furniture and Fixtures">Furniture</option>
                          <option value="Vehicles">Vehicles</option>
                        </select>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => handleRemoveLine(index)}
                        disabled={lines.length <= 1}
                        className="p-1 text-gray-400 hover:text-rose-600 disabled:opacity-30 cursor-pointer"
                        title="Remove line"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals Summary */}
          <div className="mt-6 flex justify-end">
            <div className="w-72 bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between text-gray-600">
                <span>Estimated Subtotal:</span>
                <span className="font-mono font-semibold">{formatAED(subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Estimated VAT (5%):</span>
                <span className="font-mono">{formatAED(estimatedTax)}</span>
              </div>
              <div className="pt-2 border-t border-gray-200 flex justify-between font-bold text-sm text-[#5B2C83]">
                <span>Total Commitment:</span>
                <span className="font-mono">{formatAED(grandTotal)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
