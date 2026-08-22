import React, { useState, useEffect, useMemo } from 'react';
import {
  Save,
  CheckCircle2,
  X,
  Plus,
  Trash2,
  Copy,
  Eye,
  FileText,
  DollarSign,
  Calendar,
  Building2,
  Hash,
  Sparkles,
  Lock,
  Unlock,
  AlertCircle,
  Package,
  Fuel,
  Truck,
  Layers,
  HelpCircle,
  Clock,
  ShieldAlert
} from 'lucide-react';
import {
  Voucher,
  VoucherType,
  VoucherItem,
  VoucherStatus,
  Client,
  CompanyProfile,
  ItemMaster,
  VatRule
} from '../../types';
import { StorageService, formatTIN, validateTIN } from '../../services/storage';
import { convertNumberToWords } from '../../utils/numberToWords';

interface VoucherEditorProps {
  initialVoucher?: Voucher | null;
  clients: Client[];
  companyProfile: CompanyProfile;
  onSave: (voucher: Voucher) => void;
  onCancel: () => void;
  onPreview: (voucher: Voucher) => void;
}

export const VoucherEditor: React.FC<VoucherEditorProps> = ({
  initialVoucher,
  clients,
  companyProfile,
  onSave,
  onCancel,
  onPreview,
}) => {
  const storage = StorageService.getInstance();
  const currentUser = storage.getCurrentUser();
  const itemCatalog = storage.getItemCatalog();

  // Role constraints
  const isProcurement = currentUser.role === 'procurement';
  const isOperations = currentUser.role === 'operations';
  const isClientPortal = currentUser.role === 'client_portal';

  const defaultType: VoucherType = isProcurement ? 'LPO' : initialVoucher?.type || 'SALES';

  const [type, setType] = useState<VoucherType>(defaultType);
  const [docNumber, setDocNumber] = useState<string>(
    initialVoucher?.docNumber || storage.getNextDocNumber(defaultType)
  );
  const [isDocNumberCustom, setIsDocNumberCustom] = useState(false);
  const [docDate, setDocDate] = useState<string>(
    initialVoucher?.docDate || new Date().toISOString().slice(0, 10)
  );
  const [dueDate, setDueDate] = useState<string>(initialVoucher?.dueDate || '');
  const [requestedDeliveryDate, setRequestedDeliveryDate] = useState<string>(
    initialVoucher?.requestedDeliveryDate || ''
  );
  const [paymentTerms, setPaymentTerms] = useState<string>(
    initialVoucher?.paymentTerms || 'Net 30 Days via CRDB Bank'
  );

  // Proforma Validity (Max 10 Days)
  const [proformaValidityDays, setProformaValidityDays] = useState<3 | 5 | 7 | 10>(
    initialVoucher?.proformaValidityDays || 7
  );

  // Gate Pass specific fields (No VAT/pricing on this type)
  const [direction, setDirection] = useState<'inward' | 'outward'>(
    initialVoucher?.direction || 'outward'
  );
  const [vehicleRegistration, setVehicleRegistration] = useState<string>(
    initialVoucher?.vehicleRegistration || ''
  );
  const [driverName, setDriverName] = useState<string>(
    initialVoucher?.driverName || ''
  );
  const [driverLicenseNumber, setDriverLicenseNumber] = useState<string>(
    initialVoucher?.driverLicenseNumber || ''
  );
  const [goodsDescription, setGoodsDescription] = useState<string>(
    initialVoucher?.goodsDescription || ''
  );
  const [quantityUnit, setQuantityUnit] = useState<string>(
    initialVoucher?.quantityUnit || ''
  );
  const [linkedVoucherId, setLinkedVoucherId] = useState<string>(
    initialVoucher?.linkedVoucherId || ''
  );
  const [linkedVoucherNumber, setLinkedVoucherNumber] = useState<string>(
    initialVoucher?.linkedVoucherNumber || ''
  );
  const [authorizedBy, setAuthorizedBy] = useState<string>(
    initialVoucher?.authorizedBy || currentUser.name
  );
  const [gatePassTime, setGatePassTime] = useState<string>(
    initialVoucher?.gatePassTime || new Date().toTimeString().slice(0, 5)
  );

  // Client info
  const [selectedClientId, setSelectedClientId] = useState<string>(initialVoucher?.clientId || '');
  const [clientName, setClientName] = useState<string>(initialVoucher?.clientName || '');
  const [clientAddress, setClientAddress] = useState<string>(initialVoucher?.clientAddress || '');
  const [clientMobile, setClientMobile] = useState<string>(initialVoucher?.clientMobile || '');
  const [clientTin, setClientTin] = useState<string>(initialVoucher?.clientTin || '');

  // Currency & Rate
  const [currency, setCurrency] = useState<'TZS' | 'USD'>(initialVoucher?.currency || 'TZS');
  const [exchangeRate, setExchangeRate] = useState<number>(initialVoucher?.exchangeRate || 2615.50);

  // Line items
  const [items, setItems] = useState<VoucherItem[]>(
    initialVoucher?.items || [
      {
        id: 'item_1',
        itemName: 'Bitumen Grade 60/70 (Steel Drums 200L / Bulk MT)',
        description: 'First dispatch batch',
        quantity: 1,
        unit: 'MT',
        rate: 1180000,
        vatRule: 'optional',
        vatApplied: true,
        vatPercent: 18,
        amount: 1180000,
        vatAmount: 212400,
        lineTotal: 1392400,
      },
    ]
  );

  // Round Off & Status
  const [roundOffEnabled, setRoundOffEnabled] = useState<boolean>(initialVoucher?.roundOffEnabled || false);
  const [notes, setNotes] = useState<string>(initialVoucher?.notes || '');
  const [status, setStatus] = useState<VoucherStatus>(initialVoucher?.status || 'draft');
  const [tinError, setTinError] = useState<string | null>(null);

  // Update doc number automatically when document type changes on a new document
  useEffect(() => {
    if (!initialVoucher && !isDocNumberCustom) {
      setDocNumber(storage.getNextDocNumber(type));
    }
  }, [type, initialVoucher, isDocNumberCustom]);

  // Compute expiration date for Proforma
  const proformaExpiresOn = useMemo(() => {
    if (type !== 'PROFORMA') return undefined;
    const base = new Date(docDate || Date.now());
    base.setDate(base.getDate() + proformaValidityDays);
    return base.toISOString().slice(0, 10);
  }, [type, docDate, proformaValidityDays]);

  // Autocomplete client details when selected from dropdown
  const handleClientSelect = (clientId: string) => {
    setSelectedClientId(clientId);
    const client = clients.find((c) => c.id === clientId);
    if (client) {
      setClientName(client.name);
      setClientAddress(client.address);
      setClientMobile(client.mobile);
      setClientTin(client.tin);
      if (client.paymentTermsType === 'credit') {
        setPaymentTerms(`Credit ${client.creditDays || 30} Days (Limit: TZS ${(client.creditLimit || 0).toLocaleString()})`);
      } else {
        setPaymentTerms('Prepaid / Advance Wire Transfer');
      }
      setTinError(null);
    }
  };

  const handleTINChange = (val: string) => {
    const formatted = formatTIN(val);
    setClientTin(formatted);
    if (formatted.length > 0 && !validateTIN(formatted)) {
      setTinError('TRA TIN must be exactly 9 numeric digits');
    } else {
      setTinError(null);
    }
  };

  // Helper to select an item from Master Catalog
  const handleCatalogItemSelect = (index: number, itemId: string) => {
    const catalogItem = itemCatalog.find((i) => i.id === itemId);
    if (!catalogItem) return;

    const updated = [...items];
    const item = { ...updated[index] };

    item.itemName = catalogItem.name;
    item.unit = catalogItem.unit;
    item.rate = catalogItem.standardRate;
    item.vatRule = catalogItem.vatRule;

    if (catalogItem.vatRule === 'exempt') {
      item.vatPercent = 0;
      item.vatApplied = false;
    } else if (catalogItem.vatRule === 'standard') {
      item.vatPercent = 18;
      item.vatApplied = true;
    } else {
      item.vatPercent = 18;
      item.vatApplied = true;
    }

    const qty = Number(item.quantity) || 0;
    const rate = Number(item.rate) || 0;
    item.amount = qty * rate;
    item.vatAmount = item.vatApplied ? item.amount * (item.vatPercent / 100) : 0;
    item.lineTotal = item.amount + item.vatAmount;

    updated[index] = item;
    setItems(updated);
  };

  // Line item modifications with strict VAT rules
  const handleItemChange = (index: number, field: keyof VoucherItem, val: any) => {
    const updated = [...items];
    const item = { ...updated[index], [field]: val };

    if (field === 'vatApplied') {
      const applied = Boolean(val);
      item.vatApplied = applied;
      item.vatPercent = applied ? 18 : 0;
    }

    const qty = Number(item.quantity) || 0;
    const rate = Number(item.rate) || 0;
    const vatPct = item.vatApplied ? (Number(item.vatPercent) || 0) : 0;

    item.amount = qty * rate;
    item.vatAmount = item.amount * (vatPct / 100);
    item.lineTotal = item.amount + item.vatAmount;

    updated[index] = item;
    setItems(updated);
  };

  const addItemRow = () => {
    const newItem: VoucherItem = {
      id: `item_${Date.now()}`,
      itemName: '',
      description: '',
      quantity: 1,
      unit: 'MT',
      rate: 0,
      vatRule: 'optional',
      vatApplied: true,
      vatPercent: 18,
      amount: 0,
      vatAmount: 0,
      lineTotal: 0,
    };
    setItems([...items, newItem]);
  };

  const removeItemRow = (index: number) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== index));
  };

  const duplicateItemRow = (index: number) => {
    const target = items[index];
    const clone: VoucherItem = {
      ...target,
      id: `item_${Date.now()}`,
    };
    const next = [...items];
    next.splice(index + 1, 0, clone);
    setItems(next);
  };

  // Overall financial calculations
  const { subtotal, totalVat, grandTotal, roundOffAdjustment, finalGrandTotal, amountInWords } = useMemo(() => {
    let sub = 0;
    let vat = 0;

    items.forEach((item) => {
      sub += item.amount || 0;
      vat += item.vatAmount || 0;
    });

    const rawGrand = sub + vat;
    let adjustment = 0;
    let finalTotal = rawGrand;

    if (roundOffEnabled) {
      const rounded = Math.round(rawGrand);
      adjustment = Number((rounded - rawGrand).toFixed(2));
      finalTotal = rounded;
    }

    const spelledOut = convertNumberToWords(finalTotal, currency);

    return {
      subtotal: sub,
      totalVat: vat,
      grandTotal: rawGrand,
      roundOffAdjustment: adjustment,
      finalGrandTotal: finalTotal,
      amountInWords: spelledOut,
    };
  }, [items, roundOffEnabled, currency]);

  if (isClientPortal) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center space-y-4">
        <div className="w-12 h-12 bg-amber-100 text-amber-800 rounded-full flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Client Portal Access Restriction</h3>
        <p className="text-xs text-slate-500">
          Client portal accounts are restricted to downloading finalized tax invoices and proforma documents. Document creation and editing is reserved for internal corporate staff.
        </p>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-bold"
        >
          Return to My Invoices
        </button>
      </div>
    );
  }

  const availableLinkedVouchers = useMemo(() => {
    return storage.getVouchers().filter((v) => v.id !== initialVoucher?.id && v.type !== 'GATE_PASS');
  }, [storage, initialVoucher]);

  const handleSubmit = (targetStatus: VoucherStatus = 'draft') => {
    if (type === 'GATE_PASS') {
      if (!vehicleRegistration.trim()) {
        alert('Vehicle Registration Number is required for Gate Pass (e.g. T 482 DXK)');
        return;
      }
      if (!driverName.trim()) {
        alert('Driver Name is required for Gate Pass');
        return;
      }
      if (!goodsDescription.trim()) {
        alert('Goods Description / Cargo Manifest is required for Gate Pass');
        return;
      }

      const gpVoucher: Voucher = {
        id: initialVoucher?.id || `vouch_${Date.now()}`,
        companyId: storage.getCurrentCompanyId(),
        type: 'GATE_PASS',
        docNumber,
        docDate,
        gatePassTime,
        direction,
        vehicleRegistration: vehicleRegistration.trim(),
        driverName: driverName.trim(),
        driverLicenseNumber: driverLicenseNumber.trim() || 'N/A',
        goodsDescription: goodsDescription.trim(),
        quantityUnit: quantityUnit.trim() || '1 Unit',
        linkedVoucherId: linkedVoucherId || undefined,
        linkedVoucherNumber: linkedVoucherNumber || undefined,
        authorizedBy: authorizedBy.trim() || currentUser.name,
        clientId: selectedClientId || 'cli_gate',
        clientName: clientName.trim() || 'Gate Logistics / Transporter',
        clientAddress: clientAddress.trim() || 'Dar es Salaam Facility Gate',
        clientMobile: clientMobile.trim() || 'N/A',
        clientTin: clientTin.trim() || 'N/A',
        currency: 'TZS',
        items: [
          {
            id: 'gp_item_1',
            itemName: goodsDescription.trim(),
            description: `Movement: ${direction.toUpperCase()} | Vehicle: ${vehicleRegistration.trim()}`,
            quantity: 1,
            unit: quantityUnit.trim() || 'Cargo Unit',
            rate: 0,
            vatRule: 'exempt',
            vatApplied: false,
            vatPercent: 0,
            amount: 0,
            vatAmount: 0,
            lineTotal: 0,
          },
        ],
        subtotal: 0,
        totalVat: 0,
        grandTotal: 0,
        roundOffEnabled: false,
        roundOffAdjustment: 0,
        finalGrandTotal: 0,
        amountInWords: 'Gate Movement Clearance (Non-Financial)',
        notes: notes.trim(),
        status: targetStatus,
        createdAt: initialVoucher?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      onSave(gpVoucher);
      return;
    }

    if (!clientName.trim()) {
      alert('Client / Customer name is required');
      return;
    }
    if (items.length === 0 || !items[0].itemName.trim()) {
      alert('At least one valid line item is required');
      return;
    }
    if (clientTin.trim() && !validateTIN(clientTin)) {
      alert('TRA TIN must be exactly 9 numeric digits');
      return;
    }

    const voucher: Voucher = {
      id: initialVoucher?.id || `vouch_${Date.now()}`,
      companyId: storage.getCurrentCompanyId(),
      type,
      docNumber,
      docDate,
      dueDate,
      requestedDeliveryDate,
      paymentTerms,
      clientId: selectedClientId || 'cli_custom',
      clientName: clientName.trim(),
      clientAddress: clientAddress.trim(),
      clientMobile: clientMobile.trim(),
      clientTin: clientTin.trim() || 'N/A',
      currency,
      exchangeRate: currency === 'USD' ? exchangeRate : undefined,
      items,
      subtotal,
      totalVat,
      grandTotal,
      roundOffEnabled,
      roundOffAdjustment,
      finalGrandTotal,
      amountInWords,
      proformaValidityDays: type === 'PROFORMA' ? proformaValidityDays : undefined,
      expiresOn: proformaExpiresOn,
      notes: notes.trim(),
      status: targetStatus,
      createdAt: initialVoucher?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    onSave(voucher);
  };

  const typeConfig: Record<VoucherType, { label: string; bg: string; allowedRoles: string[] }> = {
    SALES: { label: 'Tax Invoice (INV)', bg: 'bg-emerald-600', allowedRoles: ['admin', 'finance', 'operations'] },
    PROFORMA: { label: 'Proforma Invoice (PI)', bg: 'bg-blue-600', allowedRoles: ['admin', 'finance', 'operations'] },
    DELIVERY: { label: 'Delivery Note (DN)', bg: 'bg-amber-600', allowedRoles: ['admin', 'finance', 'operations'] },
    GATE_PASS: { label: 'Gate Pass (GP)', bg: 'bg-teal-600', allowedRoles: ['admin', 'finance', 'operations'] },
    LPO: { label: 'Local Purchase Order (LPO)', bg: 'bg-purple-600', allowedRoles: ['admin', 'finance', 'procurement'] },
    PO: { label: 'Purchase Order (PO)', bg: 'bg-slate-700', allowedRoles: ['admin', 'finance', 'operations'] },
  };

  const visibleTypes: VoucherType[] = isProcurement
    ? ['LPO', 'PO']
    : isClientPortal
    ? ['SALES', 'PROFORMA', 'DELIVERY']
    : ['SALES', 'PROFORMA', 'DELIVERY', 'GATE_PASS', 'LPO', 'PO'];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 uppercase tracking-wider">
            {initialVoucher ? 'Edit Document' : 'Document Generator & Invoicing'}
          </span>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2 mt-1">
            <FileText className="w-5 h-5 text-blue-900" />
            <span>{typeConfig[type]?.label || type} — {docNumber}</span>
          </h2>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={() => handleSubmit('draft')}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded-lg text-xs font-semibold transition"
          >
            <Save className="w-4 h-4" />
            <span>Save as Draft</span>
          </button>

          <button
            type="button"
            onClick={() => handleSubmit('finalized')}
            className="flex items-center space-x-1.5 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Finalize Document</span>
          </button>
        </div>
      </div>

      {/* 1. Document Configuration & Type Selector */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            1. Document Type & Series
          </h3>
          {isProcurement && (
            <span className="text-[10px] font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
              Procurement Role: LPO Mode Active
            </span>
          )}
          {isOperations && (
            <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Operations Role: Outbound Invoicing, Delivery & Gate Pass
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
          {visibleTypes.map((t) => {
            const isSelected = type === t;
            const isAllowed = typeConfig[t].allowedRoles.includes(currentUser.role);

            return (
              <button
                key={t}
                type="button"
                disabled={!isAllowed}
                onClick={() => isAllowed && setType(t)}
                className={`py-2 px-3 rounded-lg text-xs font-semibold border text-center transition ${
                  isSelected
                    ? 'bg-blue-900 text-white border-blue-900 shadow-xs'
                    : isAllowed
                    ? 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    : 'opacity-40 bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                }`}
                title={!isAllowed ? `Role "${currentUser.role}" is not permitted to create ${typeConfig[t].label}` : ''}
              >
                {typeConfig[t].label}
              </button>
            );
          })}
        </div>

        {/* Proforma Validity Selector (Max 10 Days) */}
        {type === 'PROFORMA' && (
          <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-blue-700 shrink-0" />
              <div>
                <p className="font-bold text-blue-900">Proforma Validity Duration (Max 10 Days)</p>
                <p className="text-blue-700 text-[11px]">
                  Controls document lifespan. Valid until <span className="font-bold underline">{proformaExpiresOn}</span> ({proformaValidityDays} days from issue).
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <label className="font-semibold text-blue-900">Validity Period:</label>
              <select
                value={proformaValidityDays}
                onChange={(e) => setProformaValidityDays(Number(e.target.value) as any)}
                className="px-3 py-1.5 bg-white border border-blue-300 rounded-lg font-bold text-blue-900 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
              >
                <option value={3}>3 Days Validity</option>
                <option value={5}>5 Days Validity</option>
                <option value={7}>7 Days Validity (Standard)</option>
                <option value={10}>10 Days Validity (Maximum)</option>
              </select>
            </div>
          </div>
        )}

        {/* Gate Pass Header Parameters */}
        {type === 'GATE_PASS' ? (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3.5 pt-2 text-xs">
            {/* Gate Pass Number */}
            <div>
              <label className="block text-slate-600 font-medium mb-1 flex items-center justify-between">
                <span>Gate Pass Number *</span>
                <button
                  type="button"
                  onClick={() => setIsDocNumberCustom(!isDocNumberCustom)}
                  className="text-[10px] text-blue-600 hover:underline flex items-center space-x-0.5"
                >
                  {isDocNumberCustom ? <Lock className="w-2.5 h-2.5" /> : <Unlock className="w-2.5 h-2.5" />}
                  <span>{isDocNumberCustom ? 'Auto' : 'Edit'}</span>
                </button>
              </label>
              <input
                type="text"
                required
                readOnly={!isDocNumberCustom}
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg font-mono font-bold ${
                  isDocNumberCustom
                    ? 'border-blue-500 bg-blue-50/20 text-slate-900'
                    : 'border-slate-200 bg-slate-100 text-slate-700'
                }`}
              />
            </div>

            {/* Date */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">Gate Movement Date *</label>
              <input
                type="date"
                required
                value={docDate}
                onChange={(e) => setDocDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>

            {/* Time */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">Movement Time *</label>
              <input
                type="time"
                required
                value={gatePassTime}
                onChange={(e) => setGatePassTime(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-slate-800 font-mono"
              />
            </div>

            {/* Direction */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">Movement Direction *</label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as 'inward' | 'outward')}
                className={`w-full px-3 py-2 border rounded-lg font-bold ${
                  direction === 'outward'
                    ? 'bg-amber-50 text-amber-900 border-amber-300'
                    : 'bg-emerald-50 text-emerald-900 border-emerald-300'
                }`}
              >
                <option value="outward">OUTWARD (Leaving Yard / Dispatch)</option>
                <option value="inward">INWARD (Entering Yard / Receiving)</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3.5 pt-2 text-xs">
            {/* Doc Number */}
            <div>
              <label className="block text-slate-600 font-medium mb-1 flex items-center justify-between">
                <span>Document Number *</span>
                <button
                  type="button"
                  onClick={() => setIsDocNumberCustom(!isDocNumberCustom)}
                  className="text-[10px] text-blue-600 hover:underline flex items-center space-x-0.5"
                >
                  {isDocNumberCustom ? <Lock className="w-2.5 h-2.5" /> : <Unlock className="w-2.5 h-2.5" />}
                  <span>{isDocNumberCustom ? 'Auto' : 'Edit'}</span>
                </button>
              </label>
              <input
                type="text"
                required
                readOnly={!isDocNumberCustom}
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg font-mono font-bold ${
                  isDocNumberCustom
                    ? 'border-blue-500 bg-blue-50/20 text-slate-900'
                    : 'border-slate-200 bg-slate-100 text-slate-700'
                }`}
              />
            </div>

            {/* Doc Date */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">Issue Date *</label>
              <input
                type="date"
                required
                value={docDate}
                onChange={(e) => setDocDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>

            {/* Due Date or Validity */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">
                {type === 'PROFORMA' ? 'Validity Expiry Date' : 'Payment Due Date'}
              </label>
              <input
                type="date"
                value={type === 'PROFORMA' ? proformaExpiresOn : dueDate}
                readOnly={type === 'PROFORMA'}
                onChange={(e) => setDueDate(e.target.value)}
                className={`w-full px-3 py-2 border border-slate-200 rounded-lg ${
                  type === 'PROFORMA' ? 'bg-blue-50 text-blue-900 font-semibold' : 'text-slate-800'
                }`}
              />
            </div>

            {/* Currency */}
            <div>
              <label className="block text-slate-600 font-medium mb-1">Document Currency</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setCurrency('TZS')}
                  className={`py-2 text-center rounded-lg border font-bold ${
                    currency === 'TZS'
                      ? 'bg-blue-900 text-white border-blue-900'
                      : 'bg-slate-50 text-slate-700 border-slate-200'
                  }`}
                >
                  TZS (Shillings)
                </button>
                <button
                  type="button"
                  onClick={() => setCurrency('USD')}
                  className={`py-2 text-center rounded-lg border font-bold ${
                    currency === 'USD'
                      ? 'bg-blue-900 text-white border-blue-900'
                      : 'bg-slate-50 text-slate-700 border-slate-200'
                  }`}
                >
                  USD ($)
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Gate Pass Specific Form OR Standard Client CRM Info */}
      {type === 'GATE_PASS' ? (
        <>
          {/* Gate Logistics & Driver Transport Details */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Truck className="w-4 h-4 text-teal-600" />
                <span>2. Vehicle, Driver & Security Logistics</span>
              </h3>
              <span className="text-[11px] text-teal-700 font-medium bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                Gate Clearance Protocol
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 text-xs">
              {/* Vehicle Registration Number */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Vehicle Registration Number *
                </label>
                <input
                  type="text"
                  required
                  value={vehicleRegistration}
                  onChange={(e) => setVehicleRegistration(e.target.value)}
                  placeholder="e.g. T 482 DXK / Trailer T 193 CDE"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 uppercase"
                />
              </div>

              {/* Driver Full Name */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">Driver Full Name *</label>
                <input
                  type="text"
                  required
                  value={driverName}
                  onChange={(e) => setDriverName(e.target.value)}
                  placeholder="e.g. Daudi Kibona"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 font-medium"
                />
              </div>

              {/* Driver License / National ID */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Driver ID / License Number
                </label>
                <input
                  type="text"
                  value={driverLicenseNumber}
                  onChange={(e) => setDriverLicenseNumber(e.target.value)}
                  placeholder="e.g. DL-894021-TZ or NIDA"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-slate-800"
                />
              </div>

              {/* Optional: Link to Related PO / LPO / Sales Invoice */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Optional: Link to Related Voucher (PO/LPO/Invoice)
                </label>
                <select
                  value={linkedVoucherId}
                  onChange={(e) => {
                    const vid = e.target.value;
                    setLinkedVoucherId(vid);
                    const found = availableLinkedVouchers.find((v) => v.id === vid);
                    if (found) {
                      setLinkedVoucherNumber(found.docNumber);
                      if (found.clientName) setClientName(found.clientName);
                      if (found.items && found.items.length > 0) {
                        setGoodsDescription(found.items.map((it) => `${it.itemName} (${it.quantity} ${it.unit})`).join(', '));
                      }
                    } else {
                      setLinkedVoucherNumber('');
                    }
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 font-medium"
                >
                  <option value="">-- No Linked Voucher (Direct Movement) --</option>
                  {availableLinkedVouchers.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.docNumber} ({v.type}) — {v.clientName}
                    </option>
                  ))}
                </select>
              </div>

              {/* Customer / Transporter Entity Name */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Transporter / Customer Entity
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. Kilimanjaro Logistics Ltd"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900"
                />
              </div>

              {/* Authorized By */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Authorized By (Logged-in User) *
                </label>
                <input
                  type="text"
                  required
                  value={authorizedBy}
                  onChange={(e) => setAuthorizedBy(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-slate-800 font-semibold"
                />
              </div>
            </div>
          </div>

          {/* 3. Goods Manifest & Cargo Specification (No VAT / Pricing on Gate Pass) */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Package className="w-4 h-4 text-blue-600" />
                <span>3. Goods Description & Quantity Specification</span>
              </h3>
              <span className="text-[11px] text-slate-500">
                Non-Financial Cargo Manifest (No VAT / Pricing applied)
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 text-xs">
              <div className="sm:col-span-2">
                <label className="block text-slate-600 font-medium mb-1">
                  Goods / Cargo Description *
                </label>
                <textarea
                  rows={3}
                  required
                  value={goodsDescription}
                  onChange={(e) => setGoodsDescription(e.target.value)}
                  placeholder="e.g. Bitumen Grade 60/70 in Steel Drums 200L, Batch #B78-2026. Loaded from Yard Tank 4."
                  className="w-full p-3 border border-slate-300 rounded-lg text-slate-900 font-medium"
                />
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">
                    Quantity & Unit of Measure *
                  </label>
                  <input
                    type="text"
                    required
                    value={quantityUnit}
                    onChange={(e) => setQuantityUnit(e.target.value)}
                    placeholder="e.g. 80 Drums (16.0 MT)"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">
                    Security Seal / Inspection Remarks
                  </label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. Security seal #TRA-9482 verified intact."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800"
                  />
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* 2. Client / Counterparty Information */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                2. Client / Counterparty Information
              </h3>
              <span className="text-[11px] text-slate-500">
                Select an existing customer or enter details manually
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3.5 text-xs">
              {/* Quick Select Client */}
              <div className="sm:col-span-2">
                <label className="block text-slate-600 font-medium mb-1">
                  Select Client from CRM Master
                </label>
                <select
                  value={selectedClientId}
                  onChange={(e) => handleClientSelect(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-slate-800 font-medium"
                >
                  <option value="">-- Choose Client (Auto-fills TIN & Terms) --</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — TIN: {c.tin} ({c.paymentTermsType.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>

              {/* Client TIN */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Client TRA TIN (9 Digits) *
                </label>
                <input
                  type="text"
                  value={clientTin}
                  onChange={(e) => handleTINChange(e.target.value)}
                  placeholder="XXX-XXX-XXX"
                  className={`w-full px-3 py-2 border rounded-lg font-mono ${
                    tinError ? 'border-rose-400 bg-rose-50' : 'border-slate-200'
                  }`}
                />
                {tinError && <p className="text-[10px] text-rose-600 mt-1 font-medium">{tinError}</p>}
              </div>

              {/* Client Mobile */}
              <div>
                <label className="block text-slate-600 font-medium mb-1">Client Mobile / Phone</label>
                <input
                  type="text"
                  value={clientMobile}
                  onChange={(e) => setClientMobile(e.target.value)}
                  placeholder="+255 754 000 000"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              {/* Full Name */}
              <div className="sm:col-span-2">
                <label className="block text-slate-600 font-medium mb-1">Customer / Entity Name *</label>
                <input
                  type="text"
                  required
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. Serengeti Infrastructure & Paving Ltd"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg font-medium text-slate-900"
                />
              </div>

              {/* Physical Address */}
              <div className="sm:col-span-2">
                <label className="block text-slate-600 font-medium mb-1">Physical Address & P.O. Box</label>
                <input
                  type="text"
                  value={clientAddress}
                  onChange={(e) => setClientAddress(e.target.value)}
                  placeholder="Plot No, Street, City, Tanzania"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>
            </div>
          </div>

      {/* 3. Line Items & TRA VAT Rule Table */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              3. Items & TRA Tax Classification
            </h3>
            <p className="text-[11px] text-slate-500">
              Fuel excise 0% Non-Vatable rules and Bitumen optional VAT toggles are automatically enforced.
            </p>
          </div>
          <button
            type="button"
            onClick={addItemRow}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-50 text-blue-800 border border-blue-200 rounded-lg text-xs font-bold hover:bg-blue-100 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Item Row</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-3 w-8">#</th>
                <th className="py-2.5 px-3 min-w-[280px]">Item Description & Catalog</th>
                <th className="py-2.5 px-2 w-20 text-center">Unit</th>
                <th className="py-2.5 px-2 w-24 text-center">Qty</th>
                <th className="py-2.5 px-2 w-32 text-right">Rate ({currency})</th>
                <th className="py-2.5 px-2 w-28 text-center">TRA VAT Rule</th>
                <th className="py-2.5 px-3 w-32 text-right">Amount</th>
                <th className="py-2.5 px-3 w-32 text-right">Line Total</th>
                <th className="py-2.5 px-2 w-16 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item, idx) => {
                const isFuelExempt =
                  item.vatRule === 'exempt' ||
                  item.itemName.toLowerCase().includes('diesel') ||
                  item.itemName.toLowerCase().includes('petrol') ||
                  item.itemName.toLowerCase().includes('kerosene');

                return (
                  <tr key={item.id} className="hover:bg-slate-50/50">
                    <td className="py-2 px-3 text-slate-400 font-mono text-center">{idx + 1}</td>

                    {/* Catalog item picker + Name */}
                    <td className="py-2 px-3 space-y-1.5">
                      <select
                        onChange={(e) => handleCatalogItemSelect(idx, e.target.value)}
                        className="w-full px-2 py-1 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-700 font-medium"
                      >
                        <option value="">-- Quick Pick from Master Catalog --</option>
                        <optgroup label="Bitumen Products (18% Optional)">
                          {itemCatalog
                            .filter((c) => c.category === 'Bitumen')
                            .map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name} ({c.standardRate.toLocaleString()} TZS/{c.unit})
                              </option>
                            ))}
                        </optgroup>
                        <optgroup label="Fuels (0% Non-Vatable)">
                          {itemCatalog
                            .filter((c) => c.category === 'Fuel')
                            .map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name} ({c.standardRate.toLocaleString()} TZS/{c.unit})
                              </option>
                            ))}
                        </optgroup>
                        <optgroup label="Transport & Logistics (18% Standard)">
                          {itemCatalog
                            .filter((c) => c.category === 'Logistics & Transport')
                            .map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name} ({c.standardRate.toLocaleString()} TZS/{c.unit})
                              </option>
                            ))}
                        </optgroup>
                      </select>

                      <input
                        type="text"
                        required
                        value={item.itemName}
                        onChange={(e) => handleItemChange(idx, 'itemName', e.target.value)}
                        placeholder="Item name / specification"
                        className="w-full px-2.5 py-1 border border-slate-300 rounded font-medium text-slate-900"
                      />

                      <input
                        type="text"
                        value={item.description || ''}
                        onChange={(e) => handleItemChange(idx, 'description', e.target.value)}
                        placeholder="Optional batch number, trailer #, or dispatch notes"
                        className="w-full px-2 py-0.5 border border-slate-200 rounded text-[11px] text-slate-600"
                      />
                    </td>

                    {/* Unit */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.unit || 'MT'}
                        onChange={(e) => handleItemChange(idx, 'unit', e.target.value)}
                        placeholder="MT/L"
                        className="w-full px-2 py-1 border border-slate-300 rounded text-center font-mono text-slate-800"
                      />
                    </td>

                    {/* Quantity */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        min="1"
                        step="any"
                        required
                        value={item.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', Number(e.target.value))}
                        className="w-full px-2 py-1 border border-slate-300 rounded text-center font-mono font-bold text-slate-800"
                      />
                    </td>

                    {/* Rate */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        min="0"
                        step="any"
                        required
                        value={item.rate}
                        onChange={(e) => handleItemChange(idx, 'rate', Number(e.target.value))}
                        className="w-full px-2 py-1 border border-slate-300 rounded text-right font-mono text-slate-800"
                      />
                    </td>

                    {/* TRA VAT Rule Enforcement */}
                    <td className="py-2 px-2 text-center">
                      {isFuelExempt ? (
                        <div className="px-2 py-1 bg-amber-50 border border-amber-200 rounded text-[10px] font-bold text-amber-800">
                          0% Non-Vatable
                          <span className="block text-[8px] text-amber-600 font-normal">TRA Fuel Excise</span>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center space-x-1">
                          <button
                            type="button"
                            onClick={() => handleItemChange(idx, 'vatApplied', !item.vatApplied)}
                            className={`px-2 py-1 rounded text-[11px] font-bold transition border ${
                              item.vatApplied
                                ? 'bg-blue-50 text-blue-800 border-blue-300'
                                : 'bg-slate-100 text-slate-600 border-slate-200'
                            }`}
                          >
                            {item.vatApplied ? '18% VAT' : '0% Exempt'}
                          </button>
                        </div>
                      )}
                    </td>

                    {/* Amount (Pre-VAT) */}
                    <td className="py-2 px-3 text-right font-mono text-slate-700 whitespace-nowrap">
                      {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Line Total (Inc VAT) */}
                    <td className="py-2 px-3 text-right font-mono font-bold text-slate-900 whitespace-nowrap">
                      {item.lineTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Actions */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center space-x-1">
                        <button
                          type="button"
                          title="Duplicate row"
                          onClick={() => duplicateItemRow(idx)}
                          className="p-1 text-slate-400 hover:text-blue-600 rounded"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          title="Delete row"
                          onClick={() => removeItemRow(idx)}
                          disabled={items.length <= 1}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded disabled:opacity-30"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Financial Totals & Spelled Out Words */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Notes & Payment Instructions
          </h3>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={`e.g. Goods delivered in good order. Payment due within 30 days into ${companyProfile.bankDetails.bankName} A/C ${companyProfile.bankDetails.accountNumber}.`}
            className="w-full p-3 border border-slate-300 rounded-lg text-xs"
          />
        </div>

        <div className="lg:col-span-5 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3 text-xs">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">
            Tax & Financial Breakdown
          </h3>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-slate-600">
              <span>Taxable Subtotal (Excl. VAT):</span>
              <span className="font-mono font-semibold">
                {currency} {subtotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="flex items-center justify-between text-slate-600">
              <span>Total TRA VAT (18% Applicable):</span>
              <span className="font-mono font-semibold">
                {currency} {totalVat.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            {/* Round Off Toggle */}
            <div className="flex items-center justify-between py-2 border-y border-slate-100">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={roundOffEnabled}
                  onChange={(e) => setRoundOffEnabled(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-slate-300"
                />
                <span className="font-semibold text-slate-700">Apply Integer Round-off</span>
              </label>
              {roundOffEnabled && (
                <span className="font-mono text-[11px] text-slate-500">
                  Adj: {roundOffAdjustment > 0 ? `+${roundOffAdjustment}` : roundOffAdjustment}
                </span>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-200">
              <span className="font-bold text-sm text-slate-900">Grand Total Payable:</span>
              <span className="font-bold text-base font-mono text-blue-900">
                {currency} {finalGrandTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            {/* Spelled Out Amount in Words */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Amount in Words (Non-Editable / Auto-Spelled):
              </span>
              <p className="font-semibold text-slate-800 text-[11px] leading-relaxed italic">
                "{amountInWords}"
              </p>
            </div>
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  );
};
