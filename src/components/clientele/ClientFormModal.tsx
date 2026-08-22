import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Building2,
  Save,
  AlertCircle,
  CheckCircle2,
  Tag,
  CreditCard,
  Calendar,
  DollarSign,
  FileCheck,
  Upload,
  FileText,
  Trash2,
  Eye,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { Client, ClientDocument, ClientDocType } from '../../types';
import { StorageService, formatTIN, validateTIN } from '../../services/storage';

interface ClientFormModalProps {
  initialClient?: Client | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (client: Client) => void;
}

interface KYCDocDef {
  type: ClientDocType;
  title: string;
  description: string;
  isMandatory: boolean;
}

const KYC_DEFINITIONS: KYCDocDef[] = [
  {
    type: 'tin_certificate',
    title: 'TIN Certificate',
    description: 'Official TRA Taxpayer Identification Number Certificate',
    isMandatory: true,
  },
  {
    type: 'bank_account_letter',
    title: 'Bank Account Letter',
    description: 'Official bank reference letter / stamped bank statement header',
    isMandatory: true,
  },
  {
    type: 'shareholder_id',
    title: 'ID of Shareholder(s)',
    description: 'National ID (NIDA), Passport, or Voter ID of directors / shareholders',
    isMandatory: true,
  },
  {
    type: 'brela_search',
    title: 'BRELA Search Certificate',
    description: 'Current official company search certificate from BRELA ORS',
    isMandatory: true,
  },
  {
    type: 'business_license',
    title: 'Business License',
    description: 'Valid local municipal / Ministry trade business license',
    isMandatory: true,
  },
  {
    type: 'ewura_license',
    title: 'EWURA License',
    description: 'Energy and Water Utilities Regulatory Authority petroleum/trade permit',
    isMandatory: true,
  },
  {
    type: 'incorporation_certificate',
    title: 'Certificate of Incorporation',
    description: 'Official certificate of incorporation / registration certificate',
    isMandatory: true,
  },
  {
    type: 'ubo_certificate',
    title: 'UBO Declaration (Optional)',
    description: 'Ultimate Beneficial Ownership registration & declaration form',
    isMandatory: false,
  },
  {
    type: 'vrn_certificate',
    title: 'VAT Registration (VRN) Certificate (Optional)',
    description: 'TRA Value Added Tax registration certificate',
    isMandatory: false,
  },
  {
    type: 'other',
    title: 'Other Supporting Documents (Optional)',
    description: 'Audited financials, board resolutions, or supplier references',
    isMandatory: false,
  },
];

export const ClientFormModal: React.FC<ClientFormModalProps> = ({
  initialClient,
  isOpen,
  onClose,
  onSave,
}) => {
  const storage = StorageService.getInstance();
  const [name, setName] = useState(initialClient?.name || '');
  const [contactPerson, setContactPerson] = useState(initialClient?.contactPerson || '');
  const [mobile, setMobile] = useState(initialClient?.mobile || '+255 ');
  const [email, setEmail] = useState(initialClient?.email || '');
  const [address, setAddress] = useState(initialClient?.address || 'Dar es Salaam, Tanzania');
  const [tin, setTin] = useState(initialClient?.tin || '');
  const [licenseNo, setLicenseNo] = useState(initialClient?.licenseNo || '');
  const [isVatRegistered, setIsVatRegistered] = useState(initialClient?.isVatRegistered ?? true);
  const [vrn, setVrn] = useState(initialClient?.vrn || '');
  const [tagsStr, setTagsStr] = useState(initialClient?.tags?.join(', ') || 'Contractor, Road Builder');
  const [paymentTermsType, setPaymentTermsType] = useState<'prepaid' | 'credit'>(
    initialClient?.paymentTermsType || 'credit'
  );
  const [creditDays, setCreditDays] = useState<number>(initialClient?.creditDays || 30);
  const [creditLimit, setCreditLimit] = useState<number>(initialClient?.creditLimit || 150000000);
  const [tinError, setTinError] = useState<string | null>(null);

  // KYC Documents State
  const [kycDocs, setKycDocs] = useState<ClientDocument[]>([]);
  const [kycValidationError, setKycValidationError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<ClientDocument | null>(null);

  useEffect(() => {
    if (initialClient) {
      setName(initialClient.name);
      setContactPerson(initialClient.contactPerson);
      setMobile(initialClient.mobile);
      setEmail(initialClient.email);
      setAddress(initialClient.address);
      setTin(initialClient.tin === 'N/A' ? '' : initialClient.tin);
      setLicenseNo(initialClient.licenseNo);
      setIsVatRegistered(initialClient.isVatRegistered);
      setVrn(initialClient.vrn || '');
      setTagsStr(initialClient.tags?.join(', ') || '');
      setPaymentTermsType(initialClient.paymentTermsType);
      setCreditDays(initialClient.creditDays || 30);
      setCreditLimit(initialClient.creditLimit || 150000000);

      // Load existing KYC docs
      const existing = storage.getClientDocuments(initialClient.id);
      setKycDocs(existing);
    } else {
      setName('');
      setContactPerson('');
      setMobile('+255 ');
      setEmail('');
      setAddress('Dar es Salaam, Tanzania');
      setTin('');
      setLicenseNo('');
      setIsVatRegistered(true);
      setVrn('');
      setTagsStr('Contractor, Road Builder');
      setPaymentTermsType('credit');
      setCreditDays(30);
      setCreditLimit(150000000);
      setKycDocs([]);
    }
    setKycValidationError(null);
  }, [initialClient, isOpen]);

  if (!isOpen) return null;

  const handleTINChange = (val: string) => {
    const formatted = formatTIN(val);
    setTin(formatted);
    if (formatted.length > 0 && !validateTIN(formatted)) {
      setTinError('TRA TIN must contain exactly 9 numeric digits (XXX-XXX-XXX)');
    } else {
      setTinError(null);
    }
  };

  const handleFileUpload = (docDef: KYCDocDef, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      const newDoc: ClientDocument = {
        id: `doc_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        companyId: storage.getCurrentCompanyId(),
        clientId: initialClient?.id || 'temp_client',
        docType: docDef.type,
        title: docDef.title,
        fileName: file.name,
        fileSize: file.size,
        dataUrl: dataUrl || '',
        uploadedAt: new Date().toISOString(),
      };

      setKycDocs((prev) => {
        // Replace if docType already exists or append
        const filtered = prev.filter((d) => d.docType !== docDef.type);
        return [...filtered, newDoc];
      });
      setKycValidationError(null);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveDoc = (docType: ClientDocType) => {
    setKycDocs((prev) => prev.filter((d) => d.docType !== docType));
  };

  // Check which mandatory documents are missing
  const mandatoryDefinitions = KYC_DEFINITIONS.filter((d) => d.isMandatory);
  const uploadedTypes = new Set(kycDocs.map((d) => d.docType));
  const missingMandatory = mandatoryDefinitions.filter((d) => !uploadedTypes.has(d.type));
  const isKycComplete = missingMandatory.length === 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      alert('Company / Client name is required');
      return;
    }

    if (tin.trim() && !validateTIN(tin)) {
      setTinError('Please provide a valid 9-digit TRA TIN or leave empty');
      return;
    }

    // MANDATORY KYC VALIDATION ENFORCEMENT
    if (!isKycComplete) {
      const missingNames = missingMandatory.map((d) => d.title).join(', ');
      setKycValidationError(
        `Mandatory KYC Document Verification Incomplete: You must upload all 7 required regulatory documents before registering this client. Missing: ${missingNames}`
      );
      // Scroll to KYC section
      const kycElement = document.getElementById('kyc-document-section');
      if (kycElement) {
        kycElement.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    const tags = tagsStr
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const clientId = initialClient?.id || `cli_${Date.now()}`;

    const clientObj: Client = {
      id: clientId,
      companyId: initialClient?.companyId || storage.getCurrentCompanyId(),
      name: name.trim(),
      contactPerson: contactPerson.trim(),
      mobile: mobile.trim(),
      email: email.trim(),
      address: address.trim(),
      tin: tin.trim() || 'N/A',
      licenseNo: licenseNo.trim(),
      isVatRegistered,
      vrn: isVatRegistered ? vrn.trim() : undefined,
      tags,
      paymentTermsType,
      creditDays: paymentTermsType === 'credit' ? Number(creditDays) : undefined,
      creditLimit: paymentTermsType === 'credit' ? Number(creditLimit) : undefined,
      requirements: initialClient?.requirements,
      notes: initialClient?.notes,
      createdAt: initialClient?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Save KYC Documents linked to this client
    kycDocs.forEach((doc) => {
      storage.saveClientDocument({
        ...doc,
        clientId: clientId,
        companyId: storage.getCurrentCompanyId(),
      });
    });

    onSave(clientObj);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full overflow-hidden my-6 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <Building2 className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="font-semibold text-sm">
                {initialClient ? 'Edit Client Profile & KYC Compliance' : 'Register New Client (Mandatory KYC Verification)'}
              </h3>
              <p className="text-[11px] text-slate-400">
                Multi-tenant CRM with strict TRA, EWURA & BRELA statutory compliance
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body - Scrollable */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 text-xs overflow-y-auto flex-1">
          {/* Company Name */}
          <div className="space-y-1">
            <label className="font-bold text-slate-700">Company / Enterprise Legal Name *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Serengeti Infrastructure & Road Builders Ltd"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Contact Person */}
            <div className="space-y-1">
              <label className="font-bold text-slate-700">Primary Contact Person</label>
              <input
                type="text"
                value={contactPerson}
                onChange={(e) => setContactPerson(e.target.value)}
                placeholder="e.g. Eng. Josephat Mwakyusa"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Mobile */}
            <div className="space-y-1">
              <label className="font-bold text-slate-700">Phone / WhatsApp</label>
              <input
                type="text"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="+255 7XX XXX XXX"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Email */}
            <div className="space-y-1">
              <label className="font-bold text-slate-700">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="procurement@company.co.tz"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Business License / BRELA */}
            <div className="space-y-1">
              <label className="font-bold text-slate-700">BRELA / Business License #</label>
              <input
                type="text"
                value={licenseNo}
                onChange={(e) => setLicenseNo(e.target.value)}
                placeholder="e.g. BL-DAR-2023-9941"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Physical Address */}
          <div className="space-y-1">
            <label className="font-bold text-slate-700">Physical Business Address</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="e.g. Plot 42, Kurasini Industrial Area, Dar es Salaam"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* TRA TIN & VAT Registration */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="font-bold text-slate-800 flex items-center space-x-1">
                  <span>TRA 9-Digit TIN Number</span>
                </label>
                <input
                  type="text"
                  maxLength={11}
                  value={tin}
                  onChange={(e) => handleTINChange(e.target.value)}
                  placeholder="XXX-XXX-XXX"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono font-bold tracking-wider focus:ring-2 focus:ring-blue-500"
                />
                {tinError && <p className="text-[10px] text-rose-600 font-semibold">{tinError}</p>}
              </div>

              <div className="space-y-2 pt-1">
                <label className="flex items-center space-x-2 cursor-pointer font-bold text-slate-800">
                  <input
                    type="checkbox"
                    checked={isVatRegistered}
                    onChange={(e) => setIsVatRegistered(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-slate-300"
                  />
                  <span>VAT Registered (TRA VRN)</span>
                </label>

                {isVatRegistered && (
                  <input
                    type="text"
                    value={vrn}
                    onChange={(e) => setVrn(e.target.value)}
                    placeholder="VRN e.g. 40-008123-X"
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono"
                  />
                )}
              </div>
            </div>
          </div>

          {/* Payment Terms & Credit Limit Section */}
          <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-lg space-y-3">
            <span className="font-bold text-blue-900 uppercase tracking-wider text-[10px] flex items-center space-x-1.5">
              <CreditCard className="w-3.5 h-3.5 text-blue-700" />
              <span>Commercial Payment Terms & Credit Facility</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="font-bold text-slate-700 text-[11px]">Terms Type</label>
                <select
                  value={paymentTermsType}
                  onChange={(e) => setPaymentTermsType(e.target.value as 'prepaid' | 'credit')}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-semibold bg-white"
                >
                  <option value="credit">Credit Terms</option>
                  <option value="prepaid">Prepaid / Advance</option>
                </select>
              </div>

              {paymentTermsType === 'credit' ? (
                <>
                  <div className="space-y-1">
                    <label className="font-bold text-slate-700 text-[11px]">Credit Days</label>
                    <select
                      value={creditDays}
                      onChange={(e) => setCreditDays(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-semibold bg-white"
                    >
                      <option value={7}>7 Days</option>
                      <option value={14}>14 Days</option>
                      <option value={30}>30 Days (Standard)</option>
                      <option value={45}>45 Days</option>
                      <option value={60}>60 Days</option>
                      <option value={90}>90 Days</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="font-bold text-slate-700 text-[11px]">Approved Limit (TZS)</label>
                    <input
                      type="number"
                      value={creditLimit}
                      onChange={(e) => setCreditLimit(Number(e.target.value))}
                      placeholder="150000000"
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono font-semibold bg-white"
                    />
                  </div>
                </>
              ) : (
                <div className="sm:col-span-2 flex items-center text-slate-500 italic text-[11px] pt-4">
                  Advance wire transfer or cash required before dispatch.
                </div>
              )}
            </div>
          </div>

          {/* Tags */}
          <div className="space-y-1">
            <label className="font-bold text-slate-700 flex items-center space-x-1.5">
              <Tag className="w-3.5 h-3.5 text-slate-500" />
              <span>Client Categories / Tags (comma separated)</span>
            </label>
            <input
              type="text"
              value={tagsStr}
              onChange={(e) => setTagsStr(e.target.value)}
              placeholder="e.g. Contractor, Road Builder, Bitumen Buyer, TANROADS"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
            />
          </div>

          {/* MANDATORY KYC DOCUMENTS SECTION */}
          <div id="kyc-document-section" className="border-t-2 border-slate-200 pt-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Mandatory Regulatory KYC Verification Checklist</span>
                </h4>
                <p className="text-[11px] text-slate-500">
                  All 7 statutory documents marked with <span className="text-rose-600 font-bold">*</span> are strictly required to save a client.
                </p>
              </div>

              <div
                className={`px-3 py-1 rounded-full text-[11px] font-bold flex items-center space-x-1.5 shrink-0 ${
                  isKycComplete
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-rose-100 text-rose-800 border border-rose-300 animate-pulse'
                }`}
              >
                {isKycComplete ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>KYC Compliant ({kycDocs.filter(d => mandatoryDefinitions.some(m => m.type === d.docType)).length}/7 Verified)</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                    <span>{missingMandatory.length} Required Document(s) Missing</span>
                  </>
                )}
              </div>
            </div>

            {/* KYC Error Alert */}
            {kycValidationError && (
              <div className="p-3 bg-rose-50 border-2 border-rose-300 text-rose-900 rounded-lg text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Cannot Save Client Profile</p>
                  <p className="text-[11px] mt-0.5">{kycValidationError}</p>
                </div>
              </div>
            )}

            {/* Document Checklist Grid */}
            <div className="space-y-2">
              {KYC_DEFINITIONS.map((def) => {
                const uploaded = kycDocs.find((d) => d.docType === def.type);
                return (
                  <div
                    key={def.type}
                    className={`p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition ${
                      uploaded
                        ? 'bg-emerald-50/50 border-emerald-200'
                        : def.isMandatory
                        ? 'bg-rose-50/30 border-rose-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-start space-x-2.5 min-w-0">
                      <div className="mt-0.5 shrink-0">
                        {uploaded ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : def.isMandatory ? (
                          <div className="w-4 h-4 rounded-full border-2 border-rose-500 flex items-center justify-center text-[9px] font-bold text-rose-600">
                            !
                          </div>
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-slate-300" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-800 text-xs truncate">
                            {def.title} {def.isMandatory && <span className="text-rose-600">*</span>}
                          </span>
                          {uploaded ? (
                            <span className="px-1.5 py-0.2 bg-emerald-100 text-emerald-800 border border-emerald-300 text-[9px] font-bold rounded">
                              Uploaded
                            </span>
                          ) : def.isMandatory ? (
                            <span className="px-1.5 py-0.2 bg-rose-100 text-rose-800 border border-rose-200 text-[9px] font-bold rounded">
                              Mandatory
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 bg-slate-100 text-slate-600 text-[9px] rounded">
                              Optional
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500 truncate mt-0.5">{def.description}</p>
                        {uploaded && (
                          <p className="text-[10px] font-mono text-emerald-700 truncate mt-0.5">
                            File: {uploaded.fileName} ({(uploaded.fileSize / 1024).toFixed(1)} KB)
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
                      {uploaded ? (
                        <>
                          <button
                            type="button"
                            onClick={() => {
                              const w = window.open();
                              if (w) {
                                w.document.write(
                                  `<iframe src="${uploaded.dataUrl}" frameborder="0" style="border:0; top:0px; left:0px; bottom:0px; right:0px; width:100%; height:100%;" allowfullscreen></iframe>`
                                );
                              }
                            }}
                            className="p-1.5 text-blue-700 hover:bg-blue-50 border border-blue-200 rounded text-xs flex items-center space-x-1"
                            title="Preview file"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span className="text-[10px] font-medium">View</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRemoveDoc(def.type)}
                            className="p-1.5 text-rose-600 hover:bg-rose-50 border border-rose-200 rounded text-xs flex items-center space-x-1"
                            title="Remove file"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      ) : (
                        <label className="px-3 py-1.5 bg-white hover:bg-blue-50 border border-blue-300 text-blue-900 rounded-lg text-xs font-semibold cursor-pointer flex items-center space-x-1.5 transition">
                          <Upload className="w-3.5 h-3.5" />
                          <span>Attach File</span>
                          <input
                            type="file"
                            accept="application/pdf,image/png,image/jpeg"
                            onChange={(e) => handleFileUpload(def, e)}
                            className="hidden"
                          />
                        </label>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
            <div className="text-[11px] text-slate-500">
              {!isKycComplete && (
                <span className="text-rose-600 font-semibold flex items-center space-x-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Please attach all 7 mandatory documents to enable saving</span>
                </span>
              )}
            </div>

            <div className="flex items-center space-x-2 self-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className={`flex items-center space-x-1.5 px-5 py-2 rounded-lg font-bold shadow-xs transition ${
                  isKycComplete
                    ? 'bg-blue-900 hover:bg-blue-800 text-white cursor-pointer'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed hover:bg-slate-400 hover:text-white'
                }`}
                title={!isKycComplete ? 'Complete all 7 mandatory KYC uploads' : 'Save client'}
              >
                <Save className="w-4 h-4" />
                <span>Save Client Profile</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
