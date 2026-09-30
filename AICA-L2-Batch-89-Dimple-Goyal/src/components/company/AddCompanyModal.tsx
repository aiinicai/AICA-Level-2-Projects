import React, { useState } from 'react';
import { Building2, X, Check, ShieldAlert, Sparkles, MapPin, Hash, FileText } from 'lucide-react';
import { Company } from '../../types';
import { isValidGSTIN, isValidPAN } from '../../utils/formatters';

interface AddCompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddCompany: (company: Omit<Company, 'id'>, seedStarterData: boolean) => void;
}

const INDIAN_STATES = [
  { code: '27', name: 'Maharashtra' },
  { code: '29', name: 'Karnataka' },
  { code: '07', name: 'Delhi' },
  { code: '24', name: 'Gujarat' },
  { code: '33', name: 'Tamil Nadu' },
  { code: '36', name: 'Telangana' },
  { code: '19', name: 'West Bengal' },
  { code: '09', name: 'Uttar Pradesh' },
  { code: '08', name: 'Rajasthan' },
  { code: '06', name: 'Haryana' },
  { code: '03', name: 'Punjab' },
  { code: '10', name: 'Bihar' },
  { code: '23', name: 'Madhya Pradesh' },
  { code: '32', name: 'Kerala' },
  { code: '21', name: 'Odisha' },
  { code: '30', name: 'Goa' },
  { code: '37', name: 'Andhra Pradesh' },
  { code: '05', name: 'Uttarakhand' },
  { code: '02', name: 'Himachal Pradesh' },
  { code: '01', name: 'Jammu and Kashmir' },
  { code: '18', name: 'Assam' },
  { code: '11', name: 'Sikkim' },
  { code: '12', name: 'Arunachal Pradesh' },
  { code: '17', name: 'Meghalaya' },
  { code: '14', name: 'Manipur' },
  { code: '15', name: 'Mizoram' },
  { code: '13', name: 'Nagaland' },
  { code: '16', name: 'Tripura' },
  { code: '22', name: 'Chhattisgarh' },
  { code: '20', name: 'Jharkhand' },
  { code: '04', name: 'Chandigarh' },
  { code: '31', name: 'Lakshadweep' },
  { code: '34', name: 'Puducherry' },
  { code: '35', name: 'Andaman & Nicobar Islands' },
  { code: '38', name: 'Ladakh' }
];

export const AddCompanyModal: React.FC<AddCompanyModalProps> = ({ isOpen, onClose, onAddCompany }) => {
  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [gstin, setGstin] = useState('');
  const [pan, setPan] = useState('');
  const [tan, setTan] = useState('');
  const [cin, setCin] = useState('');
  const [businessType, setBusinessType] = useState<Company['businessType']>('Private Limited');
  const [industry, setIndustry] = useState('Manufacturing & Trading');
  const [address, setAddress] = useState('');
  const [selectedState, setSelectedState] = useState(INDIAN_STATES[0]);
  const [financialYear, setFinancialYear] = useState('2026-27');
  const [booksStartDate, setBooksStartDate] = useState('2026-04-01');
  const [defaultPaymentTerms, setDefaultPaymentTerms] = useState(30);
  const [defaultTdsSection, setDefaultTdsSection] = useState('194C');
  const [defaultTdsRate, setDefaultTdsRate] = useState(2);
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [seedStarterData, setSeedStarterData] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  // Auto extract PAN and state from GSTIN if valid
  const handleGstinChange = (val: string) => {
    const upper = val.toUpperCase().trim();
    setGstin(upper);
    if (upper.length >= 2) {
      const code = upper.slice(0, 2);
      const matched = INDIAN_STATES.find(s => s.code === code);
      if (matched) {
        setSelectedState(matched);
      }
    }
    if (upper.length >= 12) {
      const panPart = upper.slice(2, 12);
      if (isValidPAN(panPart)) {
        setPan(panPart);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!name.trim()) {
      setErrorMsg('Company display name is required.');
      return;
    }
    if (!legalName.trim()) {
      setErrorMsg('Legal entity name is required.');
      return;
    }
    if (gstin && !isValidGSTIN(gstin)) {
      setErrorMsg('Please enter a valid 15-digit Indian GSTIN (e.g. 27AAACA1234B1Z2).');
      return;
    }
    if (pan && !isValidPAN(pan)) {
      setErrorMsg('Please enter a valid 10-character Indian PAN (e.g. AAACA1234B).');
      return;
    }

    onAddCompany(
      {
        name: name.trim(),
        legalName: legalName.trim(),
        pan: pan.toUpperCase().trim() || (gstin ? gstin.slice(2, 12) : 'AABCP9999K'),
        gstin: gstin.toUpperCase().trim() || `${selectedState.code}AABCP9999K1Z5`,
        tan: tan.toUpperCase().trim() || undefined,
        cin: cin.toUpperCase().trim() || undefined,
        businessType,
        industry: industry.trim(),
        address: address.trim() || `${selectedState.name}, India`,
        state: selectedState.name,
        stateCode: selectedState.code,
        financialYear,
        booksStartDate,
        currency: 'INR',
        defaultPaymentTerms,
        defaultTdsSection,
        defaultTdsRate,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined
      },
      seedStarterData
    );

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Add New Company / Entity</h3>
              <p className="text-xs text-slate-500">Configure corporate details for FY 2026-27 multi-company reconciliation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs font-semibold text-rose-800">
            <ShieldAlert className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-xs">
          {/* Company Names */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Company Display Name *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Apex Industrial Solutions Ltd"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Legal Registered Entity Name *</label>
              <input
                type="text"
                required
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                placeholder="e.g. Apex Industrial Solutions Limited"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
              />
            </div>
          </div>

          {/* Constitution & Industry */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Constitution / Entity Type *</label>
              <select
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value as any)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white font-medium"
              >
                <option value="Private Limited">Private Limited Company (Pvt Ltd)</option>
                <option value="LLP">Limited Liability Partnership (LLP)</option>
                <option value="Partnership">Partnership Firm</option>
                <option value="Sole Proprietorship">Sole Proprietorship</option>
                <option value="Public Limited">Public Limited Company</option>
              </select>
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Industry Sector</label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. IT & Software, Engineering, Pharmaceuticals"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
              />
            </div>
          </div>

          {/* GSTIN & PAN */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-bold text-slate-700">15-Digit GSTIN</label>
                {gstin && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isValidGSTIN(gstin) ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                    {isValidGSTIN(gstin) ? 'Valid GSTIN' : 'Invalid Format'}
                  </span>
                )}
              </div>
              <input
                type="text"
                maxLength={15}
                value={gstin}
                onChange={(e) => handleGstinChange(e.target.value)}
                placeholder="e.g. 27AAACA1234B1Z2"
                className="w-full px-3 py-2 font-mono uppercase tracking-wider border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Auto-extracts PAN and state code</span>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-bold text-slate-700">10-Digit Income Tax PAN</label>
                {pan && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isValidPAN(pan) ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                    {isValidPAN(pan) ? 'Valid PAN' : 'Invalid PAN'}
                  </span>
                )}
              </div>
              <input
                type="text"
                maxLength={10}
                value={pan}
                onChange={(e) => setPan(e.target.value.toUpperCase().trim())}
                placeholder="e.g. AAACA1234B"
                className="w-full px-3 py-2 font-mono uppercase tracking-wider border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white"
              />
            </div>
          </div>

          {/* State & TAN */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">State / Union Territory *</label>
              <select
                value={selectedState.code}
                onChange={(e) => {
                  const s = INDIAN_STATES.find(st => st.code === e.target.value);
                  if (s) setSelectedState(s);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white font-medium"
              >
                {INDIAN_STATES.map((st) => (
                  <option key={st.code} value={st.code}>
                    {st.code} - {st.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">TAN (Tax Deduction A/c)</label>
              <input
                type="text"
                maxLength={10}
                value={tan}
                onChange={(e) => setTan(e.target.value.toUpperCase().trim())}
                placeholder="e.g. MUMV12345A"
                className="w-full px-3 py-2 uppercase font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">CIN / Registration No.</label>
              <input
                type="text"
                value={cin}
                onChange={(e) => setCin(e.target.value.toUpperCase().trim())}
                placeholder="e.g. U72900MH2020PTC123456"
                className="w-full px-3 py-2 uppercase font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
          </div>

          {/* Registered Office Address */}
          <div>
            <label className="block font-bold text-slate-700 mb-1">Registered Office Address</label>
            <textarea
              rows={2}
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="e.g. 301, Commerce Center, Ring Road, Industrial Area"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          {/* Financial Year & Terms */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-emerald-50/50 p-3.5 rounded-xl border border-emerald-200">
            <div>
              <label className="block font-bold text-emerald-950 mb-1">Financial Year</label>
              <input
                type="text"
                value={financialYear}
                readOnly
                className="w-full px-3 py-2 bg-emerald-100/60 font-bold text-emerald-900 border border-emerald-300 rounded-lg cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block font-bold text-emerald-950 mb-1">Books Starting Date</label>
              <input
                type="date"
                value={booksStartDate}
                onChange={(e) => setBooksStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-white font-medium border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
            <div>
              <label className="block font-bold text-emerald-950 mb-1">Credit Terms (Days)</label>
              <input
                type="number"
                min={0}
                max={180}
                value={defaultPaymentTerms}
                onChange={(e) => setDefaultPaymentTerms(parseInt(e.target.value, 10) || 30)}
                className="w-full px-3 py-2 bg-white font-medium border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
          </div>

          {/* Default TDS Section & Contact */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Primary TDS Section</label>
              <select
                value={defaultTdsSection}
                onChange={(e) => {
                  setDefaultTdsSection(e.target.value);
                  if (e.target.value === '194C') setDefaultTdsRate(2);
                  if (e.target.value === '194J') setDefaultTdsRate(10);
                  if (e.target.value === '194Q') setDefaultTdsRate(0.1);
                  if (e.target.value === '194H') setDefaultTdsRate(2);
                  if (e.target.value === '194I') setDefaultTdsRate(10);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white font-medium"
              >
                <option value="194C">Section 194C (Contractors / Transport - 1% / 2%)</option>
                <option value="194J">Section 194J (Professional & Technical Services - 10%)</option>
                <option value="194J(a)">Section 194J(a) (Technical Services SLA - 2%)</option>
                <option value="194Q">Section 194Q (Purchase of Goods &gt; ₹50L - 0.1%)</option>
                <option value="194H">Section 194H (Commission & Brokerage - 2%)</option>
                <option value="194I">Section 194I (Rent on Land & Building - 10%)</option>
              </select>
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Contact Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. accounts@apexindustrial.in"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
          </div>

          {/* Starter Data Toggle */}
          <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
            <div className="pr-4">
              <span className="font-bold text-slate-900 block">Initialize with Starter Ledger?</span>
              <p className="text-[11px] text-slate-500">
                Automatically seeds initial customer accounts, starter invoices, and bank deposits so you can immediately run reconciliations.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={seedStarterData}
                onChange={(e) => setSeedStarterData(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors shadow-sm flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              <span>Create & Activate Company</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
