import React from 'react';
import { 
  Users, 
  FileText, 
  Scale, 
  Settings2, 
  Check, 
  UserMinus, 
  UserPlus, 
  Building2, 
  MapPin, 
  Briefcase, 
  Calendar, 
  Sparkles,
  Percent,
  Plus,
  Trash2,
  AlertCircle,
  HelpCircle,
  ShieldCheck,
  CreditCard
} from 'lucide-react';
import { DeedFormData, SupplementaryConfig, Partner, CustomClause } from '../types';
import { DeedUploaderOCRCard } from './DeedUploaderOCRCard';
import { PartnerCard } from './PartnerCard';
import { DEFAULT_SUPPLEMENTARY_CONFIG } from '../utils/supplementaryAndDissolutionEngine';
import { calculateAge, formatPartnerNameWithPrefix } from '../utils/deedEngine';

interface SupplementaryDeedEditorProps {
  formData: DeedFormData;
  onUpdateFormData: (updates: Partial<DeedFormData> | ((prev: DeedFormData) => Partial<DeedFormData>)) => void;
}

export const SupplementaryDeedEditor: React.FC<SupplementaryDeedEditorProps> = ({
  formData,
  onUpdateFormData,
}) => {
  const supp = formData.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;

  const updateSupp = (updates: Partial<SupplementaryConfig>) => {
    onUpdateFormData((prev) => ({
      supplementaryConfig: {
        ...(prev.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG),
        ...updates,
      },
    }));
  };

  const handleDeedExtracted = (extracted: any, fileName: string) => {
    // Merge extracted data into formData and supplementaryConfig
    const updates: Partial<DeedFormData> = {
      uploadedDeedFileName: fileName,
      uploadedDeedExtractionStatus: 'extracted',
    };

    if (extracted.firmName) updates.firmName = extracted.firmName;
    if (extracted.firmAddress) updates.firmAddress = extracted.firmAddress;
    if (extracted.firmObjects) updates.firmObjects = extracted.firmObjects;
    if (extracted.interestRate) updates.interestRate = extracted.interestRate;

    const suppUpdates: SupplementaryConfig = { ...supp };
    if (extracted.originalDeedDate) suppUpdates.originalDeedDate = extracted.originalDeedDate;
    if (extracted.originalDeedCity) suppUpdates.originalDeedCity = extracted.originalDeedCity;
    if (extracted.registrationNumber) suppUpdates.originalRegistrationNumber = extracted.registrationNumber;

    if (Array.isArray(extracted.partners) && extracted.partners.length > 0) {
      updates.partners = extracted.partners.map((p: any, idx: number) => ({
        id: `extracted_p_${idx + 1}_${Date.now()}`,
        titlePrefix: p.titlePrefix || 'MR.',
        name: p.name || '',
        relationType: p.relationType || 'FATHER',
        parentName: p.parentName || '',
        pan: p.pan || '',
        aadhaar: p.aadhaar || '',
        dob: p.dob || '',
        age: p.age || '',
        address: p.address || '',
        profitShare: p.profitShare || '0',
        isWorking: p.isWorking !== undefined ? p.isWorking : true,
      }));
    }

    updates.supplementaryConfig = suppUpdates;
    onUpdateFormData(updates);
  };

  // Toggle Retiring Partner
  const toggleRetiringPartner = (partnerId: string) => {
    const current = supp.retiringPartnerIds || [];
    const updated = current.includes(partnerId)
      ? current.filter(id => id !== partnerId)
      : [...current, partnerId];
    updateSupp({ retiringPartnerIds: updated });
  };

  // Incoming Partners management
  const handleAddIncomingPartner = () => {
    const newIncoming: Partner = {
      id: `incoming_${Date.now()}`,
      titlePrefix: 'MR.',
      name: '',
      relationType: 'FATHER',
      parentName: '',
      pan: '',
      dob: '',
      age: '',
      address: '',
      profitShare: '0',
      isWorking: true,
    };
    updateSupp({
      incomingPartners: [...(supp.incomingPartners || []), newIncoming],
    });
  };

  const handleUpdateIncomingPartner = (index: number, field: keyof Partner, value: any) => {
    onUpdateFormData((prev) => {
      const currentSupp = prev.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
      const list = [...(currentSupp.incomingPartners || [])];
      if (field === 'dob' && value) {
        const age = calculateAge(value, currentSupp.effectiveDate || prev.execDate);
        list[index] = { ...list[index], dob: value, age };
      } else {
        list[index] = { ...list[index], [field]: value };
      }
      return {
        supplementaryConfig: {
          ...currentSupp,
          incomingPartners: list,
        },
      };
    });
  };

  const handleBatchUpdateIncomingPartner = (index: number, updates: Partial<Partner>) => {
    onUpdateFormData((prev) => {
      const currentSupp = prev.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
      const list = [...(currentSupp.incomingPartners || [])];
      let updatedPartner = { ...list[index], ...updates };
      if (updates.dob && !updates.age) {
        const age = calculateAge(updates.dob, currentSupp.effectiveDate || prev.execDate);
        updatedPartner.age = age;
      }
      list[index] = updatedPartner;
      return {
        supplementaryConfig: {
          ...currentSupp,
          incomingPartners: list,
        },
      };
    });
  };

  const handleRemoveIncomingPartner = (index: number) => {
    onUpdateFormData((prev) => {
      const currentSupp = prev.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
      const list = [...(currentSupp.incomingPartners || [])].filter((_, i) => i !== index);
      return {
        supplementaryConfig: {
          ...currentSupp,
          incomingPartners: list,
        },
      };
    });
  };

  // Revised Profit Share handler
  const handleRevisedProfitChange = (partnerId: string, value: string) => {
    updateSupp({
      revisedProfitShares: {
        ...(supp.revisedProfitShares || {}),
        [partnerId]: value,
      },
    });
  };

  // Active partners list: existing continuing + incoming
  const continuingPartners = (formData.partners || []).filter(
    p => !(supp.retiringPartnerIds || []).includes(p.id)
  );
  const incomingPartners = supp.incomingPartners || [];
  const allActivePartners = [...continuingPartners, ...incomingPartners];

  const totalRevisedProfit = allActivePartners.reduce((acc, p) => {
    const val = supp.revisedProfitShares?.[p.id];
    const num = parseFloat(val !== undefined && val !== '' ? val : (p.profitShare || '0')) || 0;
    return acc + num;
  }, 0);

  const isProfitTotalValid = Math.abs(totalRevisedProfit - 100) < 0.01;

  // Custom amended clause handler
  const handleAddCustomClause = () => {
    const newClause = {
      id: `cac_${Date.now()}`,
      clauseNumberOrTitle: `Clause ${supp.customAmendedClauses.length + 1}`,
      originalText: '',
      amendedText: '',
    };
    updateSupp({
      customAmendedClauses: [...(supp.customAmendedClauses || []), newClause],
    });
  };

  const handleUpdateCustomClause = (index: number, field: 'clauseNumberOrTitle' | 'amendedText', value: string) => {
    const list = [...(supp.customAmendedClauses || [])];
    list[index] = { ...list[index], [field]: value };
    updateSupp({ customAmendedClauses: list });
  };

  const handleRemoveCustomClause = (index: number) => {
    const list = (supp.customAmendedClauses || []).filter((_, i) => i !== index);
    updateSupp({ customAmendedClauses: list });
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      
      {/* 1. OCR UPLOADER FOR ORIGINAL & PRIOR DEEDS */}
      <DeedUploaderOCRCard
        onDeedExtracted={handleDeedExtracted}
        currentFileName={formData.uploadedDeedFileName}
        formatType="supplementary"
        priorDeeds={supp.priorDeeds || []}
        onUpdatePriorDeeds={(deeds) => updateSupp({ priorDeeds: deeds })}
      />

      {/* 2. PRINCIPAL DEED & EXECUTION PARTICULARS */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center font-bold text-sm">
            1
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Principal Deed Reference & Effective Date
            </h3>
            <p className="text-xs text-slate-500">
              Details of the original partnership deed being modified and the effective date of changes.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          
          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Principal Deed Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={supp.originalDeedDate || ''}
              onChange={(e) => updateSupp({ originalDeedDate: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500 bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Date when original deed was signed</span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Original Execution City / Place <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. AHMEDABAD, MUMBAI, JAIPUR"
              value={supp.originalDeedCity || formData.execCity || ''}
              onChange={(e) => {
                updateSupp({ originalDeedCity: e.target.value.toUpperCase() });
                onUpdateFormData({ execCity: e.target.value.toUpperCase() });
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500 uppercase bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">City where original deed was executed</span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              RoF / Sub-Registrar Reg. Number
            </label>
            <input
              type="text"
              placeholder="e.g. ROF/AHM/2023/12345 (optional)"
              value={supp.originalRegistrationNumber || ''}
              onChange={(e) => updateSupp({ originalRegistrationNumber: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500 uppercase bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Leave blank if firm is not registered</span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Effective Date of Modification <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={supp.effectiveDate || formData.execDate || ''}
              onChange={(e) => {
                updateSupp({ effectiveDate: e.target.value });
                onUpdateFormData({ execDate: e.target.value });
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500 bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Date from which changes take legal effect</span>
          </div>

          <div className="sm:col-span-2">
            <label className="block font-bold text-slate-700 mb-1">
              Current Firm Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. M/S. SHREE HARI ENTERPRISE"
              value={formData.firmName || ''}
              onChange={(e) => onUpdateFormData({ firmName: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold focus:ring-2 focus:ring-blue-500 uppercase bg-white text-blue-900"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Existing firm name under Principal Deed</span>
          </div>

        </div>
      </div>

      {/* 3. SELECT MODIFICATIONS SELECTOR (4 MAIN OPTIONS AS REQUESTED) */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="mb-4">
          <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">
            Select Modification Categories
          </span>
          <h3 className="font-bold text-base text-slate-900 mt-0.5">
            What changes are being made in this Supplementary Deed?
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Select one or more modification types below. The relevant fields will open automatically.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          
          {/* Option 1: Change in Partners */}
          <div
            onClick={() => updateSupp({ changePartners: !supp.changePartners })}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-start gap-3.5 select-none ${
              supp.changePartners 
                ? 'border-blue-600 bg-blue-50/60 shadow-xs' 
                : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
            }`}
          >
            <div className={`w-6 h-6 rounded-md flex items-center justify-center mt-0.5 shrink-0 transition ${
              supp.changePartners ? 'bg-blue-600 text-white' : 'border border-slate-300 bg-white'
            }`}>
              {supp.changePartners && <Check className="w-4 h-4 stroke-[3]" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-700" />
                <span className="font-bold text-sm text-slate-900">
                  1. Change in Partners
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Admission of new incoming partner, retirement / resignation of existing partner, and re-alignment of equity shares.
              </p>
              {supp.changePartners && (
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                  Active in drafting
                </span>
              )}
            </div>
          </div>

          {/* Option 2: Change in Clause */}
          <div
            onClick={() => updateSupp({ changeClauses: !supp.changeClauses })}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-start gap-3.5 select-none ${
              supp.changeClauses 
                ? 'border-blue-600 bg-blue-50/60 shadow-xs' 
                : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
            }`}
          >
            <div className={`w-6 h-6 rounded-md flex items-center justify-center mt-0.5 shrink-0 transition ${
              supp.changeClauses ? 'bg-blue-600 text-white' : 'border border-slate-300 bg-white'
            }`}>
              {supp.changeClauses && <Check className="w-4 h-4 stroke-[3]" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-700" />
                <span className="font-bold text-sm text-slate-900">
                  2. Change in Clauses
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Change of firm name, principal office address, expansion/amendment of business objects clause, or specific clause replacement.
              </p>
              {supp.changeClauses && (
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                  Active in drafting
                </span>
              )}
            </div>
          </div>

          {/* Option 3: Change in Remuneration */}
          <div
            onClick={() => updateSupp({ changeRemuneration: !supp.changeRemuneration })}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-start gap-3.5 select-none ${
              supp.changeRemuneration 
                ? 'border-blue-600 bg-blue-50/60 shadow-xs' 
                : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
            }`}
          >
            <div className={`w-6 h-6 rounded-md flex items-center justify-center mt-0.5 shrink-0 transition ${
              supp.changeRemuneration ? 'bg-blue-600 text-white' : 'border border-slate-300 bg-white'
            }`}>
              {supp.changeRemuneration && <Check className="w-4 h-4 stroke-[3]" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-blue-700" />
                <span className="font-bold text-sm text-slate-900">
                  3. Change in Remuneration
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Revise working partners' remuneration slabs under Income-tax Act 2025 Section 35(e) or alter interest on partner capital.
              </p>
              {supp.changeRemuneration && (
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                  Active in drafting
                </span>
              )}
            </div>
          </div>

          {/* Option 4: Any Other Condition */}
          <div
            onClick={() => updateSupp({ changeOtherConditions: !supp.changeOtherConditions })}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-start gap-3.5 select-none ${
              supp.changeOtherConditions 
                ? 'border-blue-600 bg-blue-50/60 shadow-xs' 
                : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
            }`}
          >
            <div className={`w-6 h-6 rounded-md flex items-center justify-center mt-0.5 shrink-0 transition ${
              supp.changeOtherConditions ? 'bg-blue-600 text-white' : 'border border-slate-300 bg-white'
            }`}>
              {supp.changeOtherConditions && <Check className="w-4 h-4 stroke-[3]" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-blue-700" />
                <span className="font-bold text-sm text-slate-900">
                  4. Any Other Condition
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Bank account operation mandate (joint/single), addition of dispute resolution covenants, or special governance terms.
              </p>
              {supp.changeOtherConditions && (
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                  Active in drafting
                </span>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* 4. DETAILS FOR OPTION 1: CHANGE IN PARTNERS */}
      {supp.changePartners && (
        <div className="bg-white border border-blue-200 rounded-2xl p-6 shadow-xs animate-in fade-in duration-200">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Option 1 Details: Change in Partners (Admission & Retirement)
              </h3>
            </div>
            <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-200">
              Indian Partnership Act 1932 Sec 31 & 32
            </span>
          </div>

          {/* SECTION A: RETIRING PARTNERS */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <UserMinus className="w-4 h-4 text-rose-600" />
              <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                Select Retiring Partner(s) (if any)
              </h4>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Check the partners who are retiring/resigning from the firm. They will be discharged and indemnified in the deed.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              {(formData.partners || []).map((p, idx) => {
                const isRetiring = (supp.retiringPartnerIds || []).includes(p.id);
                return (
                  <div
                    key={p.id}
                    onClick={() => toggleRetiringPartner(p.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                      isRetiring 
                        ? 'border-rose-400 bg-rose-50/60 shadow-2xs' 
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-xs text-slate-900">
                        {idx + 1}. {formatPartnerNameWithPrefix(p) || `Partner ${idx + 1}`}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        PAN: {p.pan || 'N/A'} | Current Share: {p.profitShare}%
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      isRetiring ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {isRetiring ? 'Retiring' : 'Continuing'}
                    </span>
                  </div>
                );
              })}
            </div>

            {(supp.retiringPartnerIds || []).length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-rose-50/40 p-4 rounded-xl border border-rose-200 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Retirement Effective Date
                  </label>
                  <input
                    type="date"
                    value={supp.retirementEffectiveDate || supp.effectiveDate || formData.execDate || ''}
                    onChange={(e) => updateSupp({ retirementEffectiveDate: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-rose-500 bg-white"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block font-bold text-slate-700 mb-1">
                    Retirement Settlement & Discharge Terms
                  </label>
                  <textarea
                    rows={2}
                    value={supp.retirementSettlementTerms}
                    onChange={(e) => updateSupp({ retirementSettlementTerms: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed focus:ring-2 focus:ring-rose-500 bg-white"
                  />
                </div>
              </div>
            )}
          </div>

          {/* SECTION B: INCOMING / NEW PARTNERS */}
          <div className="mb-6 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-emerald-600" />
                <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                  New Admitted / Incoming Partner(s)
                </h4>
              </div>
              <button
                type="button"
                onClick={handleAddIncomingPartner}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition shadow-2xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Incoming Partner</span>
              </button>
            </div>

            {(!supp.incomingPartners || supp.incomingPartners.length === 0) ? (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center text-xs text-slate-500">
                No incoming partners added yet. Click <b>"Add Incoming Partner"</b> above if a new partner is joining the firm.
              </div>
            ) : (
              <div className="space-y-4">
                {supp.incomingPartners.map((ip, idx) => (
                  <PartnerCard
                    key={ip.id}
                    partner={ip}
                    index={idx}
                    totalPartners={supp.incomingPartners.length}
                    titlePrefix="Incoming Partner"
                    badgeText="New Partner Admitted"
                    badgeTheme="emerald"
                    hideProfitShare={true}
                    onUpdate={(i, field, val) => handleUpdateIncomingPartner(i, field, val)}
                    onRemove={(i) => handleRemoveIncomingPartner(i)}
                    onDobChange={(i, dobVal) => handleUpdateIncomingPartner(i, 'dob', dobVal)}
                    onBatchUpdate={handleBatchUpdateIncomingPartner}
                  />
                ))}
              </div>
            )}
          </div>

          {/* SECTION C: REVISED PROFIT & LOSS SHARING RATIO */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Percent className="w-4 h-4 text-blue-600" />
                <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                  Revised Profit & Loss Sharing Table
                </h4>
              </div>
              <div className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                isProfitTotalValid 
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                  : 'bg-rose-100 text-rose-800 border border-rose-300'
              }`}>
                Total: {totalRevisedProfit.toFixed(2)}% {isProfitTotalValid ? '✓ Balanced' : '⚠️ Must sum to 100%'}
              </div>
            </div>

            <p className="text-xs text-slate-500 mb-3">
              Specify the revised profit/loss sharing percentage for all active continuing and incoming partners.
            </p>

            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700">
                  <tr>
                    <th className="p-2.5 text-center w-12">#</th>
                    <th className="p-2.5">Partner Name & Role</th>
                    <th className="p-2.5 text-right w-36">Revised Share (%)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {allActivePartners.map((p, idx) => {
                    const isIncoming = (supp.incomingPartners || []).some(ip => ip.id === p.id);
                    const val = supp.revisedProfitShares?.[p.id];
                    const shareValue = val !== undefined ? val : (p.profitShare || '0');
                    return (
                      <tr key={p.id} className="hover:bg-slate-50/80">
                        <td className="p-2.5 text-center font-bold text-slate-500">{idx + 1}</td>
                        <td className="p-2.5 font-semibold text-slate-800">
                          {formatPartnerNameWithPrefix(p) || `Partner ${idx + 1}`}
                          <span className={`ml-2 px-2 py-0.2 rounded text-[10px] ${
                            isIncoming ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-50 text-blue-700'
                          }`}>
                            {isIncoming ? 'Incoming' : 'Continuing'}
                          </span>
                        </td>
                        <td className="p-2.5 text-right">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={shareValue}
                            onChange={(e) => handleRevisedProfitChange(p.id, e.target.value)}
                            className="w-24 px-2.5 py-1 text-right font-bold text-slate-900 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* 5. DETAILS FOR OPTION 2: CHANGE IN CLAUSES */}
      {supp.changeClauses && (
        <div className="bg-white border border-blue-200 rounded-2xl p-6 shadow-xs animate-in fade-in duration-200 space-y-4">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Option 2 Details: Change in Clauses
              </h3>
            </div>
            <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-200">
              Clause Amendments
            </span>
          </div>

          {/* Change Firm Name */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-slate-700" />
                <span className="font-bold text-xs text-slate-800">Change Firm Name?</span>
              </div>
              <input
                type="checkbox"
                checked={supp.changeFirmName}
                onChange={(e) => updateSupp({ changeFirmName: e.target.checked })}
                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
              />
            </div>
            {supp.changeFirmName && (
              <div className="mt-3">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  New Firm Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. M/S. NEW HORIZON ENTERPRISES"
                  value={supp.newFirmName}
                  onChange={(e) => updateSupp({ newFirmName: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs uppercase font-bold text-blue-900 bg-white"
                />
              </div>
            )}
          </div>

          {/* Change Address */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-slate-700" />
                <span className="font-bold text-xs text-slate-800">Change Principal Place of Business (Address)?</span>
              </div>
              <input
                type="checkbox"
                checked={supp.changeAddress}
                onChange={(e) => updateSupp({ changeAddress: e.target.checked })}
                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
              />
            </div>
            {supp.changeAddress && (
              <div className="mt-3">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  New Principal Place of Business <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="Full amended office / factory address"
                  value={supp.newFirmAddress}
                  onChange={(e) => updateSupp({ newFirmAddress: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs uppercase bg-white"
                />
              </div>
            )}
          </div>

          {/* Change Objects */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-slate-700" />
                <span className="font-bold text-xs text-slate-800">Change / Add Nature of Business Objects?</span>
              </div>
              <input
                type="checkbox"
                checked={supp.changeObjects}
                onChange={(e) => updateSupp({ changeObjects: e.target.checked })}
                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
              />
            </div>
            {supp.changeObjects && (
              <div className="mt-3">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  New / Expanded Business Objects Clause <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Enter the amended objects clause or use AI assistant"
                  value={supp.newObjects}
                  onChange={(e) => updateSupp({ newObjects: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
                />
              </div>
            )}
          </div>

          {/* Custom Specific Clause Amendment */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-700">Specific Clause Replacements (Optional)</span>
              <button
                type="button"
                onClick={handleAddCustomClause}
                className="flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-900"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Clause Replacement</span>
              </button>
            </div>

            {supp.customAmendedClauses?.map((cac, idx) => (
              <div key={cac.id} className="p-3 mb-3 rounded-lg border border-slate-200 bg-white space-y-2">
                <div className="flex items-center justify-between">
                  <input
                    type="text"
                    placeholder="e.g. Clause 9 (Accounting Year) or Bank Accounts"
                    value={cac.clauseNumberOrTitle}
                    onChange={(e) => handleUpdateCustomClause(idx, 'clauseNumberOrTitle', e.target.value)}
                    className="font-bold text-xs text-slate-800 px-2 py-1 border border-slate-300 rounded"
                  />
                  <button
                    type="button"
                    onClick={() => handleRemoveCustomClause(idx)}
                    className="text-slate-400 hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <textarea
                  rows={2}
                  placeholder="Amended clause legal text..."
                  value={cac.amendedText}
                  onChange={(e) => handleUpdateCustomClause(idx, 'amendedText', e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs leading-relaxed"
                />
              </div>
            ))}
          </div>

        </div>
      )}

      {/* 6. DETAILS FOR OPTION 3: CHANGE IN REMUNERATION */}
      {supp.changeRemuneration && (
        <div className="bg-white border border-blue-200 rounded-2xl p-6 shadow-xs animate-in fade-in duration-200">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <Scale className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Option 3 Details: Change in Remuneration & Interest
              </h3>
            </div>
            <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-200">
              IT Act 2025 Sec 35(e)
            </span>
          </div>

          <div className="space-y-4 text-xs">
            
            <div className="p-3.5 rounded-xl bg-blue-50/50 border border-blue-200">
              <div className="font-bold text-slate-800 mb-1">
                Income-tax Act 2025 Section 35(e) Statutory Slab (Recommended)
              </div>
              <p className="text-slate-600 leading-relaxed text-[11px]">
                Under the revised IT Act 2025 provisions, working partners remuneration is allowable up to:
                <br />• First ₹6,00,000 book profit (or loss): <b>₹3,00,000 or 90%</b>, whichever is higher.
                <br />• Balance book profit: <b>60%</b>.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Distribution Among Working Partners
                </label>
                <select
                  value={supp.remunDistribution}
                  onChange={(e) => updateSupp({ remunDistribution: e.target.value as any })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold bg-white"
                >
                  <option value="ratio">In proportion to profit-sharing ratio (Standard)</option>
                  <option value="equal">Equally among all working partners</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Interest on Partner Capital Ceiling
                </label>
                <input
                  type="text"
                  placeholder="e.g. 12% per annum"
                  value={supp.revisedInterestRate || formData.interestRate || '12%'}
                  onChange={(e) => updateSupp({ revisedInterestRate: e.target.value, changeInterestRate: true })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold bg-white"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">Maximum 12% simple interest allowable under Income-tax Act</span>
              </div>
            </div>

            {/* Specific Monthly Salary per Partner */}
            <div className="pt-3 border-t border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="block font-bold text-slate-800">
                  Specific Fixed Monthly Salary per Working Partner (Optional, e.g. Rs. 50,000/month)
                </label>
                <span className="text-[10px] text-slate-500 font-medium">
                  Permanent / Agreed Drawings
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                If any working partner is entitled to draw a specific monthly salary, enter the amount below. This will be explicitly mentioned in the Supplementary Deed.
              </p>

              <div className="space-y-2 pt-1">
                {(formData.partners || []).filter(p => p.isWorking).map((p, pIdx) => {
                  const mSal = parseInt(p.salaryMonthly || '0', 10);
                  return (
                    <div key={p.id || pIdx} className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200 gap-2">
                      <span className="font-bold text-slate-800 text-xs">
                        {p.titlePrefix ? `${p.titlePrefix} ` : ''}{p.name || `Partner ${pIdx + 1}`}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500 font-semibold">Rs.</span>
                        <input
                          type="text"
                          placeholder="e.g. 50000"
                          value={p.salaryMonthly || ''}
                          onChange={(e) => {
                            const val = e.target.value.replace(/[^0-9]/g, '');
                            const updated = (formData.partners || []).map(item => {
                              if (item.id === p.id) {
                                return {
                                  ...item,
                                  salaryMonthly: val,
                                  salaryAnnual: val ? (parseInt(val, 10) * 12).toString() : ''
                                };
                              }
                              return item;
                            });
                            onUpdateFormData({ partners: updated });
                          }}
                          className="w-28 px-2.5 py-1.5 border border-slate-300 rounded-lg text-right font-bold text-xs bg-white text-slate-900 focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                        <span className="text-xs text-slate-500 font-medium">/ month</span>
                        {mSal > 0 && (
                          <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-1 rounded border border-emerald-200 shrink-0">
                            = Rs. {(mSal * 12).toLocaleString('en-IN')}/- p.a.
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

        </div>
      )}

      {/* 7. DETAILS FOR OPTION 4: ANY OTHER CONDITION */}
      {supp.changeOtherConditions && (
        <div className="bg-white border border-blue-200 rounded-2xl p-6 shadow-xs animate-in fade-in duration-200">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-sm">
                Option 4 Details: Any Other Condition / Special Covenants
              </h3>
            </div>
            <span className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-200">
              Custom Covenants
            </span>
          </div>

          <div className="space-y-4 text-xs">
            
            {/* Bank Accounts */}
            <div>
              <label className="block font-bold text-slate-700 mb-1">
                Bank Operation Mandate
              </label>
              <textarea
                rows={2}
                value={supp.newBankOperationTerms}
                onChange={(e) => updateSupp({ newBankOperationTerms: e.target.value, changeBankOperation: true })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
                placeholder="e.g. That the bank account(s) of the firm shall be operated jointly by Partner A and Partner B..."
              />
            </div>

            {/* Ratification Clause */}
            <div>
              <label className="block font-bold text-slate-700 mb-1">
                Ratification & Continuance Clause
              </label>
              <textarea
                rows={3}
                value={supp.ratificationClause}
                onChange={(e) => updateSupp({ ratificationClause: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white text-slate-700"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">
                Standard legal clause confirming all other original terms of the Principal Deed remain in full force.
              </span>
            </div>

          </div>

        </div>
      )}

    </div>
  );
};
