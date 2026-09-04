import React from 'react';
import { 
  Building2, 
  Calendar, 
  Users, 
  FileText, 
  Scale, 
  ShieldAlert, 
  Archive, 
  Newspaper, 
  Check, 
  CreditCard,
  AlertCircle
} from 'lucide-react';
import { DeedFormData, DissolutionConfig, Partner } from '../types';
import { DeedUploaderOCRCard } from './DeedUploaderOCRCard';
import { DEFAULT_DISSOLUTION_CONFIG } from '../utils/supplementaryAndDissolutionEngine';
import { formatPartnerNameWithPrefix } from '../utils/deedEngine';

interface DissolutionDeedEditorProps {
  formData: DeedFormData;
  onUpdateFormData: (updates: Partial<DeedFormData>) => void;
}

export const DissolutionDeedEditor: React.FC<DissolutionDeedEditorProps> = ({
  formData,
  onUpdateFormData,
}) => {
  const diss = formData.dissolutionConfig || DEFAULT_DISSOLUTION_CONFIG;

  const updateDiss = (updates: Partial<DissolutionConfig>) => {
    onUpdateFormData({
      dissolutionConfig: {
        ...diss,
        ...updates,
      },
    });
  };

  const handleDeedExtracted = (extracted: any, fileName: string) => {
    const updates: Partial<DeedFormData> = {
      uploadedDeedFileName: fileName,
      uploadedDeedExtractionStatus: 'extracted',
    };

    if (extracted.firmName) updates.firmName = extracted.firmName;
    if (extracted.firmAddress) updates.firmAddress = extracted.firmAddress;
    if (extracted.originalDeedCity || extracted.execCity) {
      updates.execCity = (extracted.originalDeedCity || extracted.execCity).toUpperCase();
    }

    const dissUpdates: DissolutionConfig = { ...diss };
    if (extracted.originalDeedDate) dissUpdates.originalDeedDate = extracted.originalDeedDate;
    if (extracted.originalDeedCity) dissUpdates.originalDeedCity = extracted.originalDeedCity;
    if (extracted.registrationNumber) dissUpdates.originalRegistrationNumber = extracted.registrationNumber;

    if (Array.isArray(extracted.partners) && extracted.partners.length > 0) {
      updates.partners = extracted.partners.map((p: any, idx: number) => ({
        id: `diss_partner_${idx + 1}_${Date.now()}`,
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
        isWorking: true,
      }));
      // Default custodian to first partner
      dissUpdates.custodianPartnerId = updates.partners[0].id;
      dissUpdates.custodianPartnerName = formatPartnerNameWithPrefix(updates.partners[0]);
    }

    updates.dissolutionConfig = dissUpdates;
    onUpdateFormData(updates);
  };

  const partners = formData.partners || [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      
      {/* 1. OCR UPLOADER FOR EXISTING & PRIOR DEEDS */}
      <DeedUploaderOCRCard
        onDeedExtracted={handleDeedExtracted}
        currentFileName={formData.uploadedDeedFileName}
        formatType="dissolution"
        priorDeeds={diss.priorDeeds || []}
        onUpdatePriorDeeds={(deeds) => updateDiss({ priorDeeds: deeds })}
      />

      {/* 2. DISSOLUTION PREAMBLE & DATES */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center justify-center font-bold text-sm">
            1
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Dissolution Execution Details & Partnership Reference
            </h3>
            <p className="text-xs text-slate-500">
              Details of the original deed being dissolved and the effective date of dissolution under Section 40 of Indian Partnership Act, 1932.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          
          <div className="sm:col-span-2">
            <label className="block font-bold text-slate-700 mb-1">
              Dissolving Firm Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. M/S. SHREE HARI ENTERPRISE"
              value={formData.firmName || ''}
              onChange={(e) => onUpdateFormData({ firmName: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold focus:ring-2 focus:ring-red-500 uppercase bg-white text-slate-900"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Effective Date of Dissolution <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={diss.dissolutionDate || formData.execDate || ''}
              onChange={(e) => {
                updateDiss({ dissolutionDate: e.target.value });
                onUpdateFormData({ execDate: e.target.value });
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold focus:ring-2 focus:ring-red-500 bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Date from which firm operations cease</span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Principal Partnership Deed Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={diss.originalDeedDate || ''}
              onChange={(e) => updateDiss({ originalDeedDate: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-red-500 bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Date when firm was originally established</span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Original Execution City / Place <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. AHMEDABAD"
              value={diss.originalDeedCity || formData.execCity || ''}
              onChange={(e) => {
                updateDiss({ originalDeedCity: e.target.value.toUpperCase() });
                onUpdateFormData({ execCity: e.target.value.toUpperCase() });
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-red-500 uppercase bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              RoF Registration / Diary Number
            </label>
            <input
              type="text"
              placeholder="e.g. ROF/AHM/2021/00912 (optional)"
              value={diss.originalRegistrationNumber || ''}
              onChange={(e) => updateDiss({ originalRegistrationNumber: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-red-500 uppercase bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Leave blank if unregistered firm</span>
          </div>

          <div className="sm:col-span-3">
            <label className="block font-bold text-slate-700 mb-1">
              Principal Place of Business (Office Address)
            </label>
            <input
              type="text"
              placeholder="Full address of the dissolving firm"
              value={formData.firmAddress || ''}
              onChange={(e) => onUpdateFormData({ firmAddress: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium uppercase bg-white"
            />
          </div>

        </div>
      </div>

      {/* 3. REASON FOR DISSOLUTION */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center justify-center font-bold text-sm">
            2
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Reason & Legal Basis of Dissolution
            </h3>
            <p className="text-xs text-slate-500">
              Select the commercial circumstance leading to dissolution of the firm.
            </p>
          </div>
        </div>

        <div className="space-y-3 text-xs">
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            
            <label className={`p-3 rounded-xl border-2 cursor-pointer transition flex items-start gap-2.5 ${
              diss.dissolutionReason === 'mutual_consent' 
                ? 'border-red-600 bg-red-50/50' 
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}>
              <input
                type="radio"
                name="diss_reason"
                checked={diss.dissolutionReason === 'mutual_consent'}
                onChange={() => updateDiss({ dissolutionReason: 'mutual_consent' })}
                className="mt-0.5 text-red-600 focus:ring-red-500"
              />
              <div>
                <span className="font-bold text-slate-900 block">Mutual Consent of All Partners (Standard)</span>
                <span className="text-[11px] text-slate-500 mt-0.5 block">
                  Dissolution under Section 40 of the Indian Partnership Act with mutual concurrence of all partners.
                </span>
              </div>
            </label>

            <label className={`p-3 rounded-xl border-2 cursor-pointer transition flex items-start gap-2.5 ${
              diss.dissolutionReason === 'completion_of_venture' 
                ? 'border-red-600 bg-red-50/50' 
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}>
              <input
                type="radio"
                name="diss_reason"
                checked={diss.dissolutionReason === 'completion_of_venture'}
                onChange={() => updateDiss({ dissolutionReason: 'completion_of_venture' })}
                className="mt-0.5 text-red-600 focus:ring-red-500"
              />
              <div>
                <span className="font-bold text-slate-900 block">Completion of Venture / Commercial Project</span>
                <span className="text-[11px] text-slate-500 mt-0.5 block">
                  The purpose or specific project for which the partnership was formed has been fulfilled.
                </span>
              </div>
            </label>

            <label className={`p-3 rounded-xl border-2 cursor-pointer transition flex items-start gap-2.5 ${
              diss.dissolutionReason === 'retirement_no_substitute' 
                ? 'border-red-600 bg-red-50/50' 
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}>
              <input
                type="radio"
                name="diss_reason"
                checked={diss.dissolutionReason === 'retirement_no_substitute'}
                onChange={() => updateDiss({ dissolutionReason: 'retirement_no_substitute' })}
                className="mt-0.5 text-red-600 focus:ring-red-500"
              />
              <div>
                <span className="font-bold text-slate-900 block">Retirement of Partner (Firm cannot continue)</span>
                <span className="text-[11px] text-slate-500 mt-0.5 block">
                  Retirement reduces partner count to one or remaining partners choose not to induct others.
                </span>
              </div>
            </label>

            <label className={`p-3 rounded-xl border-2 cursor-pointer transition flex items-start gap-2.5 ${
              diss.dissolutionReason === 'custom' 
                ? 'border-red-600 bg-red-50/50' 
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}>
              <input
                type="radio"
                name="diss_reason"
                checked={diss.dissolutionReason === 'custom'}
                onChange={() => updateDiss({ dissolutionReason: 'custom' })}
                className="mt-0.5 text-red-600 focus:ring-red-500"
              />
              <div>
                <span className="font-bold text-slate-900 block">Custom Reason</span>
                <span className="text-[11px] text-slate-500 mt-0.5 block">
                  Specify bespoke commercial or health reasons.
                </span>
              </div>
            </label>

          </div>

          {diss.dissolutionReason === 'custom' && (
            <div className="mt-2">
              <label className="block font-bold text-slate-700 mb-1">
                Custom Dissolution Reason Text
              </label>
              <textarea
                rows={2}
                value={diss.customReasonText}
                onChange={(e) => updateDiss({ customReasonText: e.target.value })}
                placeholder="Describe the reason for dissolution..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
              />
            </div>
          )}

        </div>
      </div>

      {/* 4. SETTLEMENT OF ACCOUNTS, ASSETS & LIABILITIES */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center justify-center font-bold text-sm">
            3
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Winding Up Terms: Assets Realization & Debt Discharge
            </h3>
            <p className="text-xs text-slate-500">
              Covenants governing settlement of statutory tax liabilities, creditors, and distribution of surplus capital.
            </p>
          </div>
        </div>

        <div className="space-y-4 text-xs">
          
          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Realization of Assets & Receivables
            </label>
            <textarea
              rows={2}
              value={diss.realizationOfAssets}
              onChange={(e) => updateDiss({ realizationOfAssets: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Discharge of Debts, Liabilities & Statutory Taxes (GST / Income Tax)
            </label>
            <textarea
              rows={2}
              value={diss.dischargeOfLiabilities}
              onChange={(e) => updateDiss({ dischargeOfLiabilities: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Distribution of Surplus Capital & Profit Balances
            </label>
            <textarea
              rows={2}
              value={diss.divisionOfSurplus}
              onChange={(e) => updateDiss({ divisionOfSurplus: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
            />
          </div>

        </div>
      </div>

      {/* 5. CUSTODY OF BOOKS & STATUTORY NOTICES */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center justify-center font-bold text-sm">
            4
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Custody of Books, RoF Notice & Bank Closure
            </h3>
            <p className="text-xs text-slate-500">
              Statutory preservation of books of accounts for 8 years and notification to authorities.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          
          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Custodian Partner for Books & Records <span className="text-red-500">*</span>
            </label>
            <select
              value={diss.custodianPartnerId || (partners[0]?.id || '')}
              onChange={(e) => {
                const selected = partners.find(p => p.id === e.target.value);
                updateDiss({ 
                  custodianPartnerId: e.target.value,
                  custodianPartnerName: selected ? formatPartnerNameWithPrefix(selected) : ''
                });
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold bg-white"
            >
              {partners.map((p, idx) => (
                <option key={p.id} value={p.id}>
                  {idx + 1}. {formatPartnerNameWithPrefix(p) || `Partner ${idx + 1}`}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-slate-400 mt-1 block">
              Partner responsible for keeping vouchers & tax records for 8 years
            </span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">
              Records Retention Period (Years)
            </label>
            <input
              type="number"
              min="8"
              max="15"
              value={diss.recordsRetentionYears || '8'}
              onChange={(e) => updateDiss({ recordsRetentionYears: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold bg-white"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">
              Statutory minimum is 8 years under Income-tax Act Section 44AA
            </span>
          </div>

          <div className="sm:col-span-2">
            <label className="block font-bold text-slate-700 mb-1">
              Public Notice Publication (Section 72 Indian Partnership Act)
            </label>
            <input
              type="text"
              value={diss.publicNoticeNewspapers || 'one English national daily and one vernacular daily newspaper'}
              onChange={(e) => updateDiss({ publicNoticeNewspapers: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block font-bold text-slate-700 mb-1">
              Bank Account Closure & Revocation of Mandate
            </label>
            <textarea
              rows={2}
              value={diss.bankAccountSettlement}
              onChange={(e) => updateDiss({ bankAccountSettlement: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block font-bold text-slate-700 mb-1">
              Mutual Indemnity and Full Release Covenant
            </label>
            <textarea
              rows={2}
              value={diss.mutualIndemnityTerms}
              onChange={(e) => updateDiss({ mutualIndemnityTerms: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs leading-relaxed bg-white"
            />
          </div>

        </div>
      </div>

    </div>
  );
};
