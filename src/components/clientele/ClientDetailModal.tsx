import React, { useState, useRef } from 'react';
import {
  X,
  Building2,
  Phone,
  Mail,
  MapPin,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Plus,
  Upload,
  Download,
  Trash2,
  ExternalLink,
  Calendar,
  FileCheck,
  Tag,
  CreditCard,
  Sparkles,
  Layers,
  RefreshCw
} from 'lucide-react';
import {
  Client,
  Voucher,
  ClientDocument,
  ClientRequirement,
  ClientDocType,
  DemandGapAnalysis
} from '../../types';
import { StorageService } from '../../services/storage';

interface ClientDetailModalProps {
  client: Client | null;
  vouchers: Voucher[];
  isOpen: boolean;
  onClose: () => void;
  onDuplicateSale: (voucher: Voucher) => void;
  onCreateNewSale: (client: Client) => void;
  onPreviewVoucher: (voucher: Voucher) => void;
}

export const ClientDetailModal: React.FC<ClientDetailModalProps> = ({
  client,
  vouchers,
  isOpen,
  onClose,
  onDuplicateSale,
  onCreateNewSale,
  onPreviewVoucher,
}) => {
  const [activeTab, setActiveTab] = useState<'timeline' | 'requirements' | 'kyc_docs'>('timeline');
  const [uploadDocName, setUploadDocName] = useState('');
  const [uploadDocType, setUploadDocType] = useState<ClientDocType>('tin_certificate');
  const [customDocTypeTitle, setCustomDocTypeTitle] = useState('');

  // Requirement form state
  const [showReqForm, setShowReqForm] = useState(false);
  const [reqProduct, setReqProduct] = useState('Bitumen Grade 60/70 (Steel Drums 200L / Bulk MT)');
  const [reqQty, setReqQty] = useState<number>(500);
  const [reqUnit, setReqUnit] = useState<'MT' | 'Liters' | 'Drums' | 'Bags' | 'Trips' | 'Units'>('MT');
  const [reqPeriod, setReqPeriod] = useState<'monthly' | 'quarterly' | 'annual'>('monthly');
  const [reqNotes, setReqNotes] = useState('');

  const [aiNoteGenerating, setAiNoteGenerating] = useState(false);
  const [dynamicAiNote, setDynamicAiNote] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen || !client) return null;

  const storage = StorageService.getInstance();
  const crmAnalytics = storage.getCRMAnalytics().find((a) => a.client.id === client.id);
  const clientVouchers = vouchers
    .filter((v) => v.clientId === client.id)
    .sort((a, b) => new Date(b.docDate).getTime() - new Date(a.docDate).getTime());

  const clientDocuments = storage.getClientDocuments(client.id);
  const clientRequirements = storage.getClientRequirements(client.id);
  const demandGaps = storage.getDemandGapAnalysis().filter((g) => g.client.id === client.id);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const dataUrl = evt.target?.result as string;
      const title = uploadDocName.trim() || customDocTypeTitle.trim() || file.name;

      storage.addClientDocument({
        id: `doc_${Date.now()}`,
        companyId: client.companyId || storage.getCurrentCompanyId(),
        clientId: client.id,
        docType: uploadDocType,
        title,
        fileName: file.name,
        fileSize: file.size,
        dataUrl,
        uploadedAt: new Date().toISOString(),
      });

      setUploadDocName('');
      setCustomDocTypeTitle('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    };
    reader.readAsDataURL(file);
  };

  const handleDeleteDoc = (docId: string) => {
    if (window.confirm('Delete this attached KYC document?')) {
      storage.deleteClientDocument(docId);
    }
  };

  const handleSaveRequirement = (e: React.FormEvent) => {
    e.preventDefault();
    storage.saveClientRequirement({
      id: `req_${Date.now()}`,
      companyId: client.companyId || storage.getCurrentCompanyId(),
      clientId: client.id,
      productName: reqProduct,
      expectedQuantity: Number(reqQty),
      unit: reqUnit,
      period: reqPeriod,
      notes: reqNotes.trim(),
    });
    setShowReqForm(false);
    setReqNotes('');
  };

  const handleDeleteRequirement = (reqId: string) => {
    if (window.confirm('Remove this product requirement target?')) {
      storage.deleteClientRequirement(reqId);
    }
  };

  const handleGenerateAiRecommendation = async (gap: DemandGapAnalysis) => {
    setAiNoteGenerating(true);
    try {
      const resp = await fetch('/api/intelligence/demand-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientName: client.name,
          productName: gap.requirement.productName,
          expectedQty: gap.requirement.expectedQuantity,
          actualSupplied: gap.actualQuantitySupplied,
          gapQty: gap.gapQuantity,
          fulfillmentPercent: gap.fulfillmentPercent,
          unit: gap.requirement.unit,
        }),
      });
      const data = await resp.json();
      if (data.advisory) {
        setDynamicAiNote(data.advisory);
      }
    } catch (err) {
      console.warn('AI analysis error', err);
    } finally {
      setAiNoteGenerating(false);
    }
  };

  const getDocTypeBadge = (type: ClientDocType) => {
    switch (type) {
      case 'tin_certificate':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-800 font-bold rounded text-[10px]">TIN Certificate</span>;
      case 'bank_account_letter':
        return <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 font-bold rounded text-[10px]">Bank Letter</span>;
      case 'shareholder_id':
        return <span className="px-2 py-0.5 bg-cyan-100 text-cyan-800 font-bold rounded text-[10px]">Shareholder ID</span>;
      case 'brela_search':
        return <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold rounded text-[10px]">BRELA Search</span>;
      case 'business_license':
        return <span className="px-2 py-0.5 bg-green-100 text-green-800 font-bold rounded text-[10px]">Business License</span>;
      case 'ewura_license':
        return <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-bold rounded text-[10px]">EWURA License</span>;
      case 'incorporation_certificate':
        return <span className="px-2 py-0.5 bg-purple-100 text-purple-800 font-bold rounded text-[10px]">Incorporation Cert</span>;
      case 'ubo_certificate':
        return <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-bold rounded text-[10px]">UBO Declaration</span>;
      case 'vrn_certificate':
        return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 font-bold rounded text-[10px]">VRN (VAT) Cert</span>;
      case 'tax_clearance':
        return <span className="px-2 py-0.5 bg-teal-100 text-teal-800 font-bold rounded text-[10px]">Tax Clearance (TCC)</span>;
      default:
        return <span className="px-2 py-0.5 bg-slate-100 text-slate-800 font-bold rounded text-[10px]">Other Document</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-blue-700 flex items-center justify-center font-bold text-white text-sm">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base leading-snug">{client.name}</h3>
              <p className="text-xs text-slate-400 font-mono">
                TIN: {client.tin} | {client.isVatRegistered ? `VRN: ${client.vrn || 'Registered'}` : 'Non-VAT'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Top Operational Metrics & Credit Terms */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs shrink-0">
          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Commercial Terms</span>
            <span className="font-bold text-slate-900 flex items-center space-x-1 capitalize">
              <CreditCard className="w-3.5 h-3.5 text-blue-600" />
              <span>{client.paymentTermsType === 'credit' ? `Credit (${client.creditDays || 30} Days)` : 'Prepaid / Cash'}</span>
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Approved Credit Limit</span>
            <span className="font-bold text-slate-900 font-mono">
              {client.creditLimit ? `TZS ${client.creditLimit.toLocaleString()}` : 'N/A'}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Lifetime Revenue</span>
            <span className="font-bold text-slate-900 font-mono">
              TZS {(crmAnalytics?.totalSpent || 0).toLocaleString()}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Order Cadence</span>
            <span className="font-bold text-slate-900">
              {crmAnalytics?.orderCount ? `${crmAnalytics.orderCount} Orders (avg ${crmAnalytics.averageDaysBetweenOrders || 0}d)` : 'New Client'}
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="px-6 border-b border-slate-200 flex items-center justify-between shrink-0 bg-white">
          <div className="flex space-x-6">
            <button
              onClick={() => setActiveTab('timeline')}
              className={`py-3 text-xs font-bold border-b-2 transition flex items-center space-x-1.5 ${
                activeTab === 'timeline'
                  ? 'border-blue-900 text-blue-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Invoices & Order History ({clientVouchers.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('requirements')}
              className={`py-3 text-xs font-bold border-b-2 transition flex items-center space-x-1.5 ${
                activeTab === 'requirements'
                  ? 'border-blue-900 text-blue-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>Expected Demand & AI Gap Analysis ({clientRequirements.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('kyc_docs')}
              className={`py-3 text-xs font-bold border-b-2 transition flex items-center space-x-1.5 ${
                activeTab === 'kyc_docs'
                  ? 'border-blue-900 text-blue-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <FileCheck className="w-4 h-4" />
              <span>KYC Documents ({clientDocuments.length})</span>
            </button>
          </div>

          <button
            onClick={() => onCreateNewSale(client)}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold shadow-xs transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Invoice</span>
          </button>
        </div>

        {/* Tab Content Area */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {/* TAB 1: Invoices & History */}
          {activeTab === 'timeline' && (
            <div className="space-y-3">
              {clientVouchers.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                  <p className="text-xs text-slate-600 font-medium">No sales or proforma records issued yet.</p>
                  <button
                    onClick={() => onCreateNewSale(client)}
                    className="px-3.5 py-1.5 bg-blue-900 text-white rounded text-xs font-semibold"
                  >
                    Issue First Invoice
                  </button>
                </div>
              ) : (
                clientVouchers.map((v) => (
                  <div
                    key={v.id}
                    className="p-3.5 bg-white border border-slate-200 rounded-lg shadow-2xs hover:border-slate-300 transition flex items-center justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold font-mono text-slate-900">{v.docNumber}</span>
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-800 font-bold rounded text-[10px]">
                          {v.type}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">Date: {v.docDate}</span>
                      </div>
                      <p className="text-slate-600 text-[11px]">
                        {v.items.length} items: {v.items.map((i) => i.itemName).join(', ')}
                      </p>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <span className="font-bold font-mono text-slate-900 text-sm block">
                          TZS {v.finalGrandTotal.toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          VAT: TZS {v.totalVat.toLocaleString()}
                        </span>
                      </div>

                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => onPreviewVoucher(v)}
                          className="p-1.5 text-slate-600 hover:text-blue-900 hover:bg-slate-100 rounded"
                          title="Preview Voucher"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onDuplicateSale(v)}
                          className="p-1.5 text-slate-600 hover:text-emerald-700 hover:bg-slate-100 rounded"
                          title="Repeat / Duplicate Sale"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 2: Expected Product Requirements & AI Demand Gap */}
          {activeTab === 'requirements' && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Expected Product Requirements & Contracted Volumes
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    Track recurring demand targets to detect supplier substitution and revenue leaks.
                  </p>
                </div>
                <button
                  onClick={() => setShowReqForm(!showReqForm)}
                  className="flex items-center space-x-1 px-3 py-1.5 bg-blue-50 text-blue-900 hover:bg-blue-100 rounded border border-blue-200 text-xs font-bold"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{showReqForm ? 'Cancel' : 'Add Target Requirement'}</span>
                </button>
              </div>

              {/* Requirement Add Form */}
              {showReqForm && (
                <form onSubmit={handleSaveRequirement} className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                  <h5 className="font-bold text-slate-800">Set Monthly / Periodic Requirement Target</h5>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2 space-y-1">
                      <label className="font-semibold text-slate-700">Product / Commodity Name</label>
                      <input
                        type="text"
                        required
                        value={reqProduct}
                        onChange={(e) => setReqProduct(e.target.value)}
                        placeholder="e.g. Bitumen Grade 60/70"
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Period</label>
                      <select
                        value={reqPeriod}
                        onChange={(e) => setReqPeriod(e.target.value as any)}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                      >
                        <option value="monthly">Monthly</option>
                        <option value="quarterly">Quarterly</option>
                        <option value="annual">Annual</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Expected Volume</label>
                      <input
                        type="number"
                        required
                        value={reqQty}
                        onChange={(e) => setReqQty(Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white font-mono font-bold"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Unit of Measure</label>
                      <select
                        value={reqUnit}
                        onChange={(e) => setReqUnit(e.target.value as any)}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                      >
                        <option value="MT">MT (Metric Ton)</option>
                        <option value="Liters">Liters</option>
                        <option value="Drums">Drums (200L)</option>
                        <option value="Trips">Trips</option>
                        <option value="Bags">Bags</option>
                        <option value="Units">Units</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Project / Notes</label>
                      <input
                        type="text"
                        value={reqNotes}
                        onChange={(e) => setReqNotes(e.target.value)}
                        placeholder="Contract scope or road section"
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      className="px-4 py-1.5 bg-blue-900 text-white rounded font-bold text-xs"
                    >
                      Save Requirement
                    </button>
                  </div>
                </form>
              )}

              {/* Demand Gap Cards */}
              <div className="space-y-3">
                {demandGaps.length === 0 ? (
                  <p className="text-xs text-slate-400 italic text-center py-4">
                    No product requirements configured yet. Click above to add stated demand.
                  </p>
                ) : (
                  demandGaps.map((gap) => (
                    <div
                      key={gap.requirement.id}
                      className="p-4 bg-white border border-slate-200 rounded-xl space-y-3 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <h5 className="font-bold text-slate-900 text-xs">{gap.requirement.productName}</h5>
                          <span className="text-[10px] text-slate-500 font-mono">
                            Target: {gap.requirement.expectedQuantity} {gap.requirement.unit} / {gap.requirement.period}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            gap.isUnderSupplied ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {gap.fulfillmentPercent}% Fulfilled
                          </span>
                          <button
                            onClick={() => handleDeleteRequirement(gap.requirement.id)}
                            className="text-slate-400 hover:text-rose-600 p-1"
                            title="Delete requirement"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            gap.fulfillmentPercent >= 75 ? 'bg-emerald-500' : 'bg-amber-500'
                          }`}
                          style={{ width: `${Math.min(100, gap.fulfillmentPercent)}%` }}
                        />
                      </div>

                      {/* AI Advisory Note */}
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-800 flex items-center space-x-1 text-[11px]">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                            <span>AI Demand Recommendation:</span>
                          </span>
                          <button
                            onClick={() => handleGenerateAiRecommendation(gap)}
                            disabled={aiNoteGenerating}
                            className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold"
                          >
                            {aiNoteGenerating ? 'Analyzing...' : 'Refresh AI Note'}
                          </button>
                        </div>
                        <p className="text-slate-600 text-xs leading-relaxed">
                          {dynamicAiNote || gap.aiSalesAdvisory}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: KYC Documents */}
          {activeTab === 'kyc_docs' && (
            <div className="space-y-5">
              {/* Document Upload Box */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <h4 className="font-bold text-slate-800 flex items-center space-x-1.5">
                  <Upload className="w-4 h-4 text-blue-600" />
                  <span>Upload Verified KYC Compliance Document</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Document Type</label>
                    <select
                      value={uploadDocType}
                      onChange={(e) => setUploadDocType(e.target.value as ClientDocType)}
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs"
                    >
                      <option value="tin_certificate">TIN Certificate</option>
                      <option value="brela_license">BRELA Certificate / Business License</option>
                      <option value="ubo_certificate">UBO (Ultimate Beneficial Ownership)</option>
                      <option value="vrn_certificate">VAT Registration Certificate (VRN)</option>
                      <option value="tax_clearance">Tax Clearance Certificate (TCC)</option>
                      <option value="other">Other Document</option>
                    </select>
                  </div>

                  <div className="space-y-1 sm:col-span-2">
                    <label className="font-semibold text-slate-700">Document Custom Title / Notes</label>
                    <input
                      type="text"
                      value={uploadDocName}
                      onChange={(e) => setUploadDocName(e.target.value)}
                      placeholder="e.g. BRELA Annual Return 2026 / CRB Class 1"
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-3 pt-1">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                    className="text-xs text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-900 file:text-white hover:file:bg-blue-800 cursor-pointer"
                  />
                  <span className="text-[11px] text-slate-400">PDF or Scanned Images up to 25MB</span>
                </div>
              </div>

              {/* Uploaded Documents List */}
              <div className="space-y-2.5">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Attached KYC & Regulatory Files ({clientDocuments.length})
                </h4>

                {clientDocuments.length === 0 ? (
                  <p className="text-xs text-slate-400 italic text-center py-4">
                    No KYC documents uploaded for this client yet.
                  </p>
                ) : (
                  clientDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between text-xs hover:border-slate-300 transition"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-slate-100 rounded text-slate-600">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="space-y-0.5">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-slate-900">{doc.title}</span>
                            {getDocTypeBadge(doc.docType)}
                          </div>
                          <p className="text-[10px] text-slate-400 font-mono">
                            {doc.fileName} • {(doc.fileSize / 1024).toFixed(0)} KB • Uploaded {new Date(doc.uploadedAt).toLocaleDateString()}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {doc.dataUrl && (
                          <a
                            href={doc.dataUrl}
                            download={doc.fileName}
                            className="p-1.5 text-blue-700 hover:bg-blue-50 rounded"
                            title="Download Document"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                        <button
                          onClick={() => handleDeleteDoc(doc.id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
