import React, { useState, useEffect } from 'react';
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
  Layers,
  CheckSquare,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { PurchaseOrder, POLine, ItemClass, TaxCode, Requisition, RequisitionLine } from '../../core/types';
import { getActiveUser, checkMakerPermission } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { round2, formatAED } from '../../core/currency';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEPARTMENTS } from '../../data/chartOfAccounts';
import { DEMO_TODAY } from '../../core/dates';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';

interface CreatePurchaseOrderPageProps {
  onNavigate: (route: string) => void;
  sourceReqNumber?: string;
}

export const CreatePurchaseOrderPage: React.FC<CreatePurchaseOrderPageProps> = ({
  onNavigate,
  sourceReqNumber,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const makerCheck = checkMakerPermission(currentUser, 'Procurement');

  // Active suppliers only
  const activeSuppliers = db.suppliers.filter((s) => s.status === 'Active');

  // Header State
  const [bu, setBu] = useState<string>('H01');
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>(
    activeSuppliers[0]?.id || ''
  );
  const [supplierSite, setSupplierSite] = useState<string>('Primary Site');
  const [orderType, setOrderType] = useState<'Goods' | 'Services' | 'Capital'>('Goods');
  const [paymentTerms, setPaymentTerms] = useState<string>('Net 30');
  const [deliveryLocation, setDeliveryLocation] = useState<string>(
    'Meridian Central Medical Stores — Dock B'
  );
  const [poDate, setPoDate] = useState<string>(DEMO_TODAY);
  const [requiredDate, setRequiredDate] = useState<string>('2026-11-15');
  const [receiptMatching, setReceiptMatching] = useState<'Yes' | 'Optional' | 'No'>('Yes');
  const [notes, setNotes] = useState<string>('');

  // Requisition line picker modal
  const [isReqPickerOpen, setIsReqPickerOpen] = useState(false);

  // Default Line
  const defaultLine: POLine = {
    lineNumber: 1,
    itemCode: db.items[0]?.code || 'MED-001',
    description: db.items[0]?.description || 'Paracetamol 500mg IV Infusion',
    itemClass: 'Pharmaceutical',
    uom: 'Vial',
    quantity: 150,
    receivedQuantity: 0,
    invoicedQuantity: 0,
    unitPrice: 14.5,
    taxCode: 'STANDARD_5',
    lineAmount: 2175,
    account: '1200',
    department: 'Pharmacy',
    isCapital: false,
    needByDate: '2026-11-15',
  };

  const [lines, setLines] = useState<POLine[]>([defaultLine]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState<string | null>(null);

  // If sourceReqNumber provided, pre-fill from that requisition!
  useEffect(() => {
    if (sourceReqNumber) {
      const req = db.requisitions?.find((r) => r.number === sourceReqNumber);
      if (req) {
        setBu(req.businessUnit);
        if (req.requisitionType === 'Capital Asset') setOrderType('Capital');
        else if (req.requisitionType === 'Services') setOrderType('Services');
        else setOrderType('Goods');

        if (req.lines && req.lines.length > 0) {
          const poLines: POLine[] = req.lines.map((rl, i) => ({
            lineNumber: i + 1,
            itemCode: rl.itemCode,
            description: rl.description,
            itemClass: rl.itemClass || 'Pharmaceutical',
            uom: rl.uom || 'Each',
            quantity: rl.quantity,
            receivedQuantity: 0,
            invoicedQuantity: 0,
            unitPrice: rl.estimatedUnitPrice || 10,
            taxCode: 'STANDARD_5',
            lineAmount: round2(rl.quantity * (rl.estimatedUnitPrice || 10)),
            account: rl.chargeAccount || '1200',
            department: rl.department || req.department || 'Clinical',
            isCapital: rl.isCapital,
            assetCategory: rl.assetCategory,
            needByDate: rl.needByDate || req.needByDate,
            sourceRequisitionNumber: req.number,
            sourceRequisitionLineNumber: rl.lineNumber,
          }));
          setLines(poLines);
        }
        setNotes(`Generated from approved Purchase Requisition ${req.number}. Justification: ${req.justification}`);
      }
    }
  }, [sourceReqNumber, db.requisitions]);

  const supplier = activeSuppliers.find((s) => s.id === selectedSupplierId);

  // Totals
  const subtotal = round2(lines.reduce((acc, l) => acc + l.lineAmount, 0));
  const taxAmount = round2(
    lines.reduce((acc, l) => {
      const rate = l.taxCode === 'STANDARD_5' ? 0.05 : 0;
      return acc + l.lineAmount * rate;
    }, 0)
  );
  const grandTotal = round2(subtotal + taxAmount);

  // Line Handlers
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
      unitPrice: item.unitPrice,
      lineAmount: round2(newLines[index].quantity * item.unitPrice),
      account:
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

  const handleLineChange = (index: number, field: keyof POLine, value: any) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };

    if (field === 'quantity' || field === 'unitPrice') {
      const q = field === 'quantity' ? Number(value) : newLines[index].quantity;
      const p = field === 'unitPrice' ? Number(value) : newLines[index].unitPrice;
      newLines[index].lineAmount = round2(q * p);
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
        itemClass: orderType === 'Capital' ? 'Capital Asset' : 'Pharmaceutical',
        uom: 'Each',
        quantity: 1,
        receivedQuantity: 0,
        invoicedQuantity: 0,
        unitPrice: 0,
        taxCode: 'STANDARD_5',
        lineAmount: 0,
        account: orderType === 'Capital' ? '1610' : '1200',
        department: 'Clinical',
        isCapital: orderType === 'Capital',
        assetCategory: orderType === 'Capital' ? 'Medical Equipment' : undefined,
        needByDate: requiredDate,
      },
    ]);
  };

  const handleRemoveLine = (index: number) => {
    if (lines.length <= 1) return;
    setLines(lines.filter((_, i) => i !== index).map((l, i) => ({ ...l, lineNumber: i + 1 })));
  };

  // Convert/Import from approved requisitions picker
  const approvedReqs = (db.requisitions || []).filter(
    (r) => (r.status === 'Approved' || r.status === 'Partially Converted') && (r.businessUnit === bu || bu === 'All')
  );

  const handleImportReqLine = (req: Requisition, reqLine: RequisitionLine) => {
    const nextNum = lines.length + 1;
    const newLine: POLine = {
      lineNumber: nextNum,
      itemCode: reqLine.itemCode,
      description: reqLine.description,
      itemClass: reqLine.itemClass || 'Pharmaceutical',
      uom: reqLine.uom || 'Each',
      quantity: reqLine.quantity,
      receivedQuantity: 0,
      invoicedQuantity: 0,
      unitPrice: reqLine.estimatedUnitPrice || 10,
      taxCode: 'STANDARD_5',
      lineAmount: round2(reqLine.quantity * (reqLine.estimatedUnitPrice || 10)),
      account: reqLine.chargeAccount || '1200',
      department: reqLine.department || req.department || 'Clinical',
      isCapital: reqLine.isCapital,
      assetCategory: reqLine.assetCategory,
      needByDate: reqLine.needByDate || req.needByDate,
      sourceRequisitionNumber: req.number,
      sourceRequisitionLineNumber: reqLine.lineNumber,
    };

    setLines([...lines, newLine]);
    setIsReqPickerOpen(false);
  };

  const validate = (): boolean => {
    if (!makerCheck.allowed) {
      setValidationError(makerCheck.reason || 'Only Liam Carter can create Purchase Orders.');
      return false;
    }
    if (!selectedSupplierId) {
      setValidationError('Please select an approved Supplier.');
      return false;
    }
    if (lines.length === 0) {
      setValidationError('Purchase order must contain at least one line item.');
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
      if (l.unitPrice < 0) {
        setValidationError(`Line #${l.lineNumber} unit price cannot be negative.`);
        return false;
      }
      if (l.isCapital && !l.assetCategory) {
        setValidationError(`Line #${l.lineNumber} is marked as Capital and requires an Asset Category.`);
        return false;
      }
    }
    setValidationError(null);
    return true;
  };

  const handleSave = (asDraft: boolean) => {
    if (!validate()) return;

    const poNumber = getNextSequenceNumber('PO');
    const status = asDraft ? 'Draft' : 'Pending Approval';

    const sourceReqs = Array.from(
      new Set(lines.map((l) => l.sourceRequisitionNumber).filter(Boolean))
    ) as string[];

    const newPO: PurchaseOrder = {
      id: `PO-${Date.now()}`,
      number: poNumber,
      businessUnit: bu,
      supplierId: supplier?.id || selectedSupplierId,
      supplierName: supplier?.name || 'Selected Supplier',
      supplierSite,
      buyerId: currentUser.userId,
      buyerName: currentUser.name,
      poDate,
      date: poDate,
      orderType,
      currency: 'AED',
      paymentTerms: supplier?.paymentTerms || paymentTerms,
      deliveryLocation,
      requiredDate,
      receiptMatching,
      notes,
      status,
      lines,
      subtotal,
      taxAmount,
      totalAmount: grandTotal,
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
      submittedAt: !asDraft ? new Date().toISOString() : undefined,
      sourceRequisitionNumbers: sourceReqs,
    };

    updateDb((state) => {
      if (!state.purchaseOrders) state.purchaseOrders = [];
      state.purchaseOrders.unshift(newPO);

      // If lines reference requisitions, update requisition status to Converted or Partially Converted
      sourceReqs.forEach((reqNum) => {
        const req = state.requisitions?.find((r) => r.number === reqNum);
        if (req) {
          req.status = 'Converted to PO';
          if (!req.relatedPoNumbers) req.relatedPoNumbers = [];
          if (!req.relatedPoNumbers.includes(newPO.number)) req.relatedPoNumbers.push(newPO.number);
        }
      });
    });

    addAuditLog({
      entityType: 'PurchaseOrder',
      entityId: newPO.id,
      action: asDraft ? 'CREATE' : 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `${asDraft ? 'Created Draft' : 'Submitted for Approval'} Purchase Order ${newPO.number} for ${newPO.supplierName} (AED ${formatAED(grandTotal)})`,
    });

    setSavedSuccess(
      `Purchase Order ${newPO.number} ${asDraft ? 'saved as Draft' : 'submitted for Approval to Daniel Reed (CFO)'}.`
    );

    setTimeout(() => {
      onNavigate('#/procurement/orders');
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
            onClick={() => onNavigate('#/procurement/orders')}
            className="p-2 rounded-lg bg-white border border-gray-200 text-gray-600 hover:text-[#5B2C83] hover:bg-plum-50 transition-colors cursor-pointer"
            title="Back to Purchase Orders"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-[#5B2C83] uppercase tracking-wider">
                Procurement Operations
              </span>
              <span className="text-gray-300">&bull;</span>
              <span className="text-xs text-gray-500 font-mono">New PO</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Create Enterprise Purchase Order
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onNavigate('#/procurement/orders')}
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

      <div className="space-y-6">
        {/* Header Information Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83]">
              Purchase Order Header
            </h2>
            <button
              onClick={() => setIsReqPickerOpen(true)}
              className="px-3 py-1 bg-plum-50 border border-plum-300 text-[#5B2C83] hover:bg-plum-100 rounded-lg text-xs font-semibold flex items-center space-x-1.5 cursor-pointer shadow-2xs"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Add Lines from Approved Requisitions</span>
            </button>
          </div>

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
              <label className="block text-gray-500 font-semibold mb-1">Supplier / Vendor *</label>
              <select
                value={selectedSupplierId}
                onChange={(e) => {
                  setSelectedSupplierId(e.target.value);
                  const s = activeSuppliers.find((x) => x.id === e.target.value);
                  if (s) setPaymentTerms(s.paymentTerms);
                }}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] font-medium text-gray-800"
              >
                {activeSuppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Order Type *</label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as any)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
              >
                <option value="Goods">Goods / Stock Items</option>
                <option value="Services">Services / Non-Stock</option>
                <option value="Capital">Capital Asset (Fixed Asset)</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Payment Terms</label>
              <input
                type="text"
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">PO Date</label>
              <input
                type="date"
                value={poDate}
                onChange={(e) => setPoDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Required Delivery Date</label>
              <input
                type="date"
                value={requiredDate}
                onChange={(e) => setRequiredDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Receipt Matching</label>
              <select
                value={receiptMatching}
                onChange={(e) => setReceiptMatching(e.target.value as any)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-1 focus:ring-[#5B2C83] text-gray-800"
              >
                <option value="Yes">Yes (3-Way Match Required)</option>
                <option value="Optional">Optional (Direct Invoice Match)</option>
                <option value="No">No</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-500 font-semibold mb-1">Currency</label>
              <input
                type="text"
                disabled
                value="AED (United Arab Emirates Dirham)"
                className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
              />
            </div>

            <div className="md:col-span-4">
              <label className="block text-gray-500 font-semibold mb-1">Delivery Location & Instructions</label>
              <input
                type="text"
                value={deliveryLocation}
                onChange={(e) => setDeliveryLocation(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-800"
              />
            </div>
          </div>
        </div>

        {/* Lines Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83]">
                Purchase Order Lines ({lines.length})
              </h2>
              <p className="text-[11px] text-gray-400">
                Item pricing, GL distribution accounts, and tax codes
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
                  <th className="py-2.5 px-3">Class & Dept</th>
                  <th className="py-2.5 px-3 text-right">Qty</th>
                  <th className="py-2.5 px-3 text-right">Unit Price</th>
                  <th className="py-2.5 px-3">Tax</th>
                  <th className="py-2.5 px-3 text-right">Total (AED)</th>
                  <th className="py-2.5 px-3">Capital Asset?</th>
                  <th className="py-2.5 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lines.map((l, index) => (
                  <tr key={index} className="hover:bg-gray-50/50">
                    <td className="py-2.5 px-3 font-mono text-gray-400">
                      <div>{l.lineNumber}</div>
                      {l.sourceRequisitionNumber && (
                        <span className="text-[9px] text-[#5B2C83] block font-mono">
                          {l.sourceRequisitionNumber}
                        </span>
                      )}
                    </td>

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
                        placeholder="Line description..."
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs"
                      />
                    </td>

                    {/* Class & Department */}
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
                      <select
                        value={l.department}
                        onChange={(e) => handleLineChange(index, 'department', e.target.value)}
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-600"
                      >
                        {DEPARTMENTS.map((d) => (
                          <option key={d} value={d}>
                            {d}
                          </option>
                        ))}
                      </select>
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

                    {/* Unit Price */}
                    <td className="py-2.5 px-3 w-28 text-right">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={l.unitPrice || ''}
                        onChange={(e) => handleLineChange(index, 'unitPrice', Number(e.target.value))}
                        className="w-24 px-2 py-1 text-right bg-white border border-gray-200 rounded text-xs font-mono"
                      />
                    </td>

                    {/* Tax Code */}
                    <td className="py-2.5 px-3 w-28">
                      <select
                        value={l.taxCode}
                        onChange={(e) => handleLineChange(index, 'taxCode', e.target.value as TaxCode)}
                        className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs"
                      >
                        <option value="STANDARD_5">5% VAT</option>
                        <option value="ZERO_0">0% Zero-Rated</option>
                        <option value="EXEMPT">Exempt</option>
                        <option value="OUT_OF_SCOPE">Out of Scope</option>
                      </select>
                    </td>

                    {/* Line Amount */}
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#5B2C83]">
                      {formatAED(l.lineAmount)}
                    </td>

                    {/* Capital Asset */}
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

                    {/* Remove */}
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
                <span>Subtotal (Net of VAT):</span>
                <span className="font-mono font-semibold">{formatAED(subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Input VAT (Recoverable 1400):</span>
                <span className="font-mono">{formatAED(taxAmount)}</span>
              </div>
              <div className="pt-2 border-t border-gray-200 flex justify-between font-bold text-sm text-[#5B2C83]">
                <span>Total Commitment:</span>
                <span className="font-mono">{formatAED(grandTotal)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Requisition Picker Modal */}
      {isReqPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full p-5 shadow-2xl border border-gray-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <h3 className="font-bold text-sm text-gray-900">
                Add Lines from Approved Requisitions ({bu})
              </h3>
              <button onClick={() => setIsReqPickerOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 max-h-80 overflow-y-auto space-y-3">
              {approvedReqs.length === 0 ? (
                <p className="text-xs text-gray-500 py-6 text-center">
                  No approved unconverted requisitions found for Business Unit {bu}.
                </p>
              ) : (
                approvedReqs.map((req) => (
                  <div key={req.id} className="p-3 border border-gray-200 rounded-lg text-xs space-y-2">
                    <div className="flex items-center justify-between font-semibold text-gray-900">
                      <span>{req.number} &bull; {req.department}</span>
                      <span className="font-mono text-[#5B2C83]">{formatAED(req.totalAmount)}</span>
                    </div>
                    <p className="text-gray-500 text-[11px]">{req.justification || req.description}</p>
                    <div className="divide-y divide-gray-100 pt-1">
                      {req.lines.map((rl) => (
                        <div key={rl.lineNumber} className="py-1.5 flex items-center justify-between">
                          <div>
                            <span className="font-medium text-gray-800">{rl.description}</span>
                            <span className="text-[10px] text-gray-400 ml-2">
                              Qty: {rl.quantity} {rl.uom} &bull; Est. {formatAED(rl.estimatedUnitPrice || 0)}
                            </span>
                          </div>
                          <button
                            onClick={() => handleImportReqLine(req, rl)}
                            className="px-2.5 py-1 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded text-[11px] font-semibold cursor-pointer"
                          >
                            Add Line
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
