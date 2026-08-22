import React, { useState, useRef } from 'react';
import {
  Building2,
  Upload,
  Trash2,
  Palette,
  Landmark,
  Save,
  CheckCircle2,
  Eye,
  FileText,
  Stamp,
  PenTool,
  Image as ImageIcon,
  Cpu,
  Lock,
  Globe
} from 'lucide-react';
import { CompanyProfile, ThemeConfig, OcrConfig, OcrProviderType } from '../../types';
import { StorageService, formatTIN } from '../../services/storage';
import { encryptSecret, maskSecret } from '../../services/crypto';

interface CompanyProfileSettingsProps {
  companyProfile: CompanyProfile;
  onProfileUpdated: (newProfile: CompanyProfile) => void;
}

export const CompanyProfileSettings: React.FC<CompanyProfileSettingsProps> = ({
  companyProfile,
  onProfileUpdated,
}) => {
  const currentUser = StorageService.getInstance().getCurrentUser();
  const isAdmin = currentUser.role === 'admin';

  const [profile, setProfile] = useState<CompanyProfile>(companyProfile);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string | undefined>(companyProfile.logoUrl);
  const [stampPreview, setStampPreview] = useState<string | undefined>(companyProfile.stampUrl);
  const [signaturePreview, setSignaturePreview] = useState<string | undefined>(companyProfile.signatureUrl);

  // Document AI / OCR Provider state
  const [ocrProvider, setOcrProvider] = useState<OcrProviderType>(
    companyProfile.ocrConfig?.provider || 'none'
  );
  const [ocrApiKeyInput, setOcrApiKeyInput] = useState<string>('');
  const [ocrBaseUrl, setOcrBaseUrl] = useState<string>(
    companyProfile.ocrConfig?.baseUrl || ''
  );
  const [savedMaskedKey, setSavedMaskedKey] = useState<string | undefined>(
    companyProfile.ocrConfig?.apiKeyMasked
  );

  const logoInputRef = useRef<HTMLInputElement>(null);
  const stampInputRef = useRef<HTMLInputElement>(null);
  const signatureInputRef = useRef<HTMLInputElement>(null);

  const fontOptions = [
    { label: 'Inter & Modern Sans (Default)', value: 'Inter, system-ui, -apple-system, sans-serif' },
    { label: 'Corporate Segoe / Arial', value: 'Segoe UI, Arial, sans-serif' },
    { label: 'Classic Helvetica Display', value: 'Helvetica Neue, Helvetica, Arial, sans-serif' },
    { label: 'Executive Serif (Merriweather)', value: 'Merriweather, Georgia, serif' },
  ];

  const handleTINChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatTIN(e.target.value);
    setProfile(prev => ({ ...prev, tin: formatted }));
  };

  const handleImageUpload = (
    e: React.ChangeEvent<HTMLInputElement>,
    type: 'logo' | 'stamp' | 'signature'
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const dataUrl = evt.target?.result as string;
      if (type === 'logo') {
        setLogoPreview(dataUrl);
        setProfile(prev => ({ ...prev, logoUrl: dataUrl }));
      } else if (type === 'stamp') {
        setStampPreview(dataUrl);
        setProfile(prev => ({ ...prev, stampUrl: dataUrl }));
      } else if (type === 'signature') {
        setSignaturePreview(dataUrl);
        setProfile(prev => ({ ...prev, signatureUrl: dataUrl }));
      }
    };
    reader.readAsDataURL(file);
  };

  const handleThemeColorChange = (key: keyof ThemeConfig, val: string) => {
    const updatedTheme = { ...profile.theme, [key]: val };
    setProfile(prev => ({ ...prev, theme: updatedTheme }));
    // Instantly preview theme change globally
    StorageService.getInstance().applyTheme(updatedTheme);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const storage = StorageService.getInstance();

    let updatedOcrConfig: OcrConfig = {
      provider: ocrProvider,
      baseUrl: ocrProvider === 'other' ? ocrBaseUrl.trim() : undefined,
      apiKeyMasked: profile.ocrConfig?.apiKeyMasked,
      apiKeyEncrypted: profile.ocrConfig?.apiKeyEncrypted,
    };

    if (ocrProvider === 'none') {
      updatedOcrConfig = {
        provider: 'none',
      };
      setSavedMaskedKey(undefined);
      setOcrApiKeyInput('');
    } else if (ocrApiKeyInput.trim()) {
      const encrypted = encryptSecret(ocrApiKeyInput.trim(), profile.id);
      const masked = maskSecret(ocrApiKeyInput.trim());
      updatedOcrConfig.apiKeyEncrypted = encrypted;
      updatedOcrConfig.apiKeyMasked = masked;
      setSavedMaskedKey(masked);
      setOcrApiKeyInput(''); // Clear raw key immediately after encrypting
    }

    const updatedProfile: CompanyProfile = {
      ...profile,
      ocrConfig: isAdmin ? updatedOcrConfig : profile.ocrConfig,
    };

    storage.updateCompanyProfile(updatedProfile);
    setProfile(updatedProfile);
    onProfileUpdated(updatedProfile);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div id="company-profile-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-blue-600" />
            <span>Company Profile & Global Brand Engine</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure legal entity details, official seal, signature, bank accounts, and custom brand theme colors.
          </p>
        </div>

        <button
          id="btn-save-profile"
          onClick={handleSave}
          className="flex items-center space-x-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-lg text-xs font-semibold shadow-xs transition shrink-0"
        >
          <Save className="w-4 h-4" />
          <span>Save Changes</span>
        </button>
      </div>

      {savedSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg flex items-center space-x-2 text-xs font-medium animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Company profile and branding theme updated successfully and applied globally.</span>
        </div>
      )}

      {/* Main Grid: Form Left, Live A4 Preview Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form: Legal, Bank, Media & Theme (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <form onSubmit={handleSave} className="space-y-6">
            {/* 1. Legal & Contact Details */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-blue-600" />
                <span>1. Legal Entity & Contact Information</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
                <div className="sm:col-span-2">
                  <label className="block text-slate-600 font-medium mb-1">Company Legal Name *</label>
                  <input
                    type="text"
                    required
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-semibold text-slate-800"
                    placeholder="e.g. Kilimanjaro Global Trading Ltd"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">
                    TRA TIN (9 Digits) *
                    <span className="text-[10px] text-blue-600 font-normal ml-1">(Auto-formatted)</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={profile.tin}
                    onChange={handleTINChange}
                    maxLength={11}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono font-medium text-slate-800"
                    placeholder="123-456-789"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">VAT Reg No. (VRN)</label>
                  <input
                    type="text"
                    value={profile.vrn || ''}
                    onChange={(e) => setProfile({ ...profile, vrn: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono text-slate-800"
                    placeholder="e.g. 40-019842-Z"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-slate-600 font-medium mb-1">Physical & Postal Address</label>
                  <textarea
                    rows={2}
                    value={profile.address}
                    onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 text-xs"
                    placeholder="Plot No, Street, Commercial Area, Dar es Salaam, Tanzania"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Official Telephone</label>
                  <input
                    type="text"
                    value={profile.phone}
                    onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
                    placeholder="+255 22 286 4500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Official Email</label>
                  <input
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
                    placeholder="operations@kilitrade.co.tz"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-slate-600 font-medium mb-1">Company Website URL</label>
                  <input
                    type="url"
                    value={profile.website}
                    onChange={(e) => setProfile({ ...profile, website: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
                    placeholder="https://www.kilitrade.co.tz"
                  />
                </div>
              </div>
            </div>

            {/* 2. Official Bank Details */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Landmark className="w-4 h-4 text-emerald-600" />
                <span>2. Bank Settlement Details (Auto-populates on Invoices)</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Bank Name</label>
                  <input
                    type="text"
                    value={profile.bankDetails.bankName}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        bankDetails: { ...profile.bankDetails, bankName: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-800"
                    placeholder="e.g. CRDB Bank Plc / NMB Bank"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Branch Name</label>
                  <input
                    type="text"
                    value={profile.bankDetails.branchName || ''}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        bankDetails: { ...profile.bankDetails, branchName: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-800"
                    placeholder="e.g. Tower Branch / Bandari Branch"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Account Name</label>
                  <input
                    type="text"
                    value={profile.bankDetails.accountName}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        bankDetails: { ...profile.bankDetails, accountName: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-800"
                    placeholder="Account Name"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Account Number</label>
                  <input
                    type="text"
                    value={profile.bankDetails.accountNumber}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        bankDetails: { ...profile.bankDetails, accountNumber: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 font-mono text-slate-800"
                    placeholder="e.g. 0150389281900"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-slate-600 font-medium mb-1">SWIFT / BIC Code</label>
                  <input
                    type="text"
                    value={profile.bankDetails.swiftCode}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        bankDetails: { ...profile.bankDetails, swiftCode: e.target.value },
                      })
                    }
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 font-mono text-slate-800"
                    placeholder="e.g. CORUTZTZ / NMBLTZTZ"
                  />
                </div>
              </div>
            </div>

            {/* 3. Media: Logo, Stamp/Seal, Signature */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <ImageIcon className="w-4 h-4 text-indigo-600" />
                <span>3. Logo, Official Stamp & Authorized Signature</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                {/* Logo Upload */}
                <div className="p-3 border border-slate-200 rounded-lg space-y-2 text-center bg-slate-50/50">
                  <div className="flex items-center justify-between text-slate-700 font-semibold text-[11px]">
                    <span className="flex items-center space-x-1">
                      <ImageIcon className="w-3.5 h-3.5 text-blue-500" />
                      <span>Company Logo</span>
                    </span>
                    {logoPreview && (
                      <button
                        type="button"
                        onClick={() => {
                          setLogoPreview(undefined);
                          setProfile({ ...profile, logoUrl: undefined });
                        }}
                        className="text-rose-500 hover:text-rose-700"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  <div className="h-20 flex items-center justify-center bg-white border border-dashed border-slate-300 rounded p-2 overflow-hidden">
                    {logoPreview ? (
                      <img src={logoPreview} alt="Logo" className="max-h-full max-w-full object-contain" />
                    ) : (
                      <span className="text-[10px] text-slate-400">PNG / SVG Transparent</span>
                    )}
                  </div>

                  <input
                    type="file"
                    ref={logoInputRef}
                    onChange={(e) => handleImageUpload(e, 'logo')}
                    accept="image/png,image/svg+xml,image/jpeg"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => logoInputRef.current?.click()}
                    className="w-full py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-[11px] font-medium transition"
                  >
                    Upload Logo
                  </button>
                </div>

                {/* Stamp Upload */}
                <div className="p-3 border border-slate-200 rounded-lg space-y-2 text-center bg-slate-50/50">
                  <div className="flex items-center justify-between text-slate-700 font-semibold text-[11px]">
                    <span className="flex items-center space-x-1">
                      <Stamp className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Official Stamp / Seal</span>
                    </span>
                    {stampPreview && (
                      <button
                        type="button"
                        onClick={() => {
                          setStampPreview(undefined);
                          setProfile({ ...profile, stampUrl: undefined });
                        }}
                        className="text-rose-500 hover:text-rose-700"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  <div className="h-20 flex items-center justify-center bg-white border border-dashed border-slate-300 rounded p-2 overflow-hidden">
                    {stampPreview ? (
                      <img src={stampPreview} alt="Stamp" className="max-h-full max-w-full object-contain" />
                    ) : (
                      <span className="text-[10px] text-slate-400">PNG Transparent Stamp</span>
                    )}
                  </div>

                  <input
                    type="file"
                    ref={stampInputRef}
                    onChange={(e) => handleImageUpload(e, 'stamp')}
                    accept="image/png,image/jpeg"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => stampInputRef.current?.click()}
                    className="w-full py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-[11px] font-medium transition"
                  >
                    Upload Stamp
                  </button>
                </div>

                {/* Signature Upload */}
                <div className="p-3 border border-slate-200 rounded-lg space-y-2 text-center bg-slate-50/50">
                  <div className="flex items-center justify-between text-slate-700 font-semibold text-[11px]">
                    <span className="flex items-center space-x-1">
                      <PenTool className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Authorized Signature</span>
                    </span>
                    {signaturePreview && (
                      <button
                        type="button"
                        onClick={() => {
                          setSignaturePreview(undefined);
                          setProfile({ ...profile, signatureUrl: undefined });
                        }}
                        className="text-rose-500 hover:text-rose-700"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  <div className="h-20 flex items-center justify-center bg-white border border-dashed border-slate-300 rounded p-2 overflow-hidden">
                    {signaturePreview ? (
                      <img src={signaturePreview} alt="Signature" className="max-h-full max-w-full object-contain" />
                    ) : (
                      <span className="text-[10px] text-slate-400">PNG Transparent Sign</span>
                    )}
                  </div>

                  <input
                    type="file"
                    ref={signatureInputRef}
                    onChange={(e) => handleImageUpload(e, 'signature')}
                    accept="image/png,image/jpeg"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => signatureInputRef.current?.click()}
                    className="w-full py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-[11px] font-medium transition"
                  >
                    Upload Signature
                  </button>
                </div>
              </div>
            </div>

            {/* 4. Theme & Brand Color Engine */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Palette className="w-4 h-4 text-amber-600" />
                <span>4. Theme Palette & Font Engine (Global CSS Variables)</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 text-xs">
                {/* Primary Color */}
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Primary Brand Color</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={profile.theme.primaryColor}
                      onChange={(e) => handleThemeColorChange('primaryColor', e.target.value)}
                      className="w-8 h-8 rounded border border-slate-300 cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={profile.theme.primaryColor}
                      onChange={(e) => handleThemeColorChange('primaryColor', e.target.value)}
                      className="w-full px-2 py-1.5 border border-slate-300 rounded font-mono text-slate-800 uppercase"
                      placeholder="#0F2C59"
                    />
                  </div>
                </div>

                {/* Secondary Color */}
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Secondary Accent</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={profile.theme.secondaryColor}
                      onChange={(e) => handleThemeColorChange('secondaryColor', e.target.value)}
                      className="w-8 h-8 rounded border border-slate-300 cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={profile.theme.secondaryColor}
                      onChange={(e) => handleThemeColorChange('secondaryColor', e.target.value)}
                      className="w-full px-2 py-1.5 border border-slate-300 rounded font-mono text-slate-800 uppercase"
                      placeholder="#1E40AF"
                    />
                  </div>
                </div>

                {/* Accent Color */}
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Highlight / Gold Accent</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={profile.theme.accentColor}
                      onChange={(e) => handleThemeColorChange('accentColor', e.target.value)}
                      className="w-8 h-8 rounded border border-slate-300 cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={profile.theme.accentColor}
                      onChange={(e) => handleThemeColorChange('accentColor', e.target.value)}
                      className="w-full px-2 py-1.5 border border-slate-300 rounded font-mono text-slate-800 uppercase"
                      placeholder="#D97706"
                    />
                  </div>
                </div>

                {/* Font Family */}
                <div className="sm:col-span-3">
                  <label className="block text-slate-600 font-medium mb-1">Brand Typography Family</label>
                  <select
                    value={profile.theme.fontFamily}
                    onChange={(e) => handleThemeColorChange('fontFamily', e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 text-slate-800"
                  >
                    {fontOptions.map(fo => (
                      <option key={fo.value} value={fo.value}>
                        {fo.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* 5. Document AI / OCR Provider (Admin Only) */}
            {isAdmin && (
              <div id="section-ocr-provider" className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                    <Cpu className="w-4 h-4 text-purple-600" />
                    <span>5. Document AI / OCR Provider</span>
                  </h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                    Admin Only
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
                  {/* Provider Dropdown */}
                  <div className="sm:col-span-2">
                    <label className="block text-slate-600 font-medium mb-1">Provider</label>
                    <select
                      id="ocr-provider-select"
                      value={ocrProvider}
                      onChange={(e) => setOcrProvider(e.target.value as OcrProviderType)}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 text-slate-800 font-medium"
                    >
                      <option value="none">None — local OCR only</option>
                      <option value="anthropic">Anthropic Claude API</option>
                      <option value="other">Other (custom)</option>
                    </select>
                  </div>

                  {/* API Key (Password style masked input) */}
                  {ocrProvider !== 'none' && (
                    <div className={ocrProvider === 'other' ? 'sm:col-span-1' : 'sm:col-span-2'}>
                      <label className="block text-slate-600 font-medium mb-1">
                        API Key
                        {savedMaskedKey && (
                          <span className="text-[10px] text-emerald-600 font-normal ml-2 font-mono">
                            (Saved: {savedMaskedKey})
                          </span>
                        )}
                      </label>
                      <input
                        id="ocr-api-key-input"
                        type="password"
                        value={ocrApiKeyInput}
                        onChange={(e) => setOcrApiKeyInput(e.target.value)}
                        placeholder={savedMaskedKey ? `Key configured (${savedMaskedKey}) — enter new key to replace` : 'Enter API Key (e.g. sk-ant-api03-...)'}
                        className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 text-slate-800 font-mono"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Key is stored encrypted in database and displayed masked after saving.
                      </p>
                    </div>
                  )}

                  {/* Base URL/Endpoint: text field, only shown/required when Provider = "Other" */}
                  {ocrProvider === 'other' && (
                    <div className="sm:col-span-1">
                      <label className="block text-slate-600 font-medium mb-1">
                        Base URL / Endpoint <span className="text-rose-500">*</span>
                      </label>
                      <input
                        id="ocr-base-url-input"
                        type="url"
                        required={ocrProvider === 'other'}
                        value={ocrBaseUrl}
                        onChange={(e) => setOcrBaseUrl(e.target.value)}
                        placeholder="https://api.custom-ocr.internal/v1"
                        className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 text-slate-800 font-mono"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Required endpoint for custom provider requests.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Right Side: Live A4 Document Preview Panel (5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
              <Eye className="w-4 h-4 text-blue-600" />
              <span>Live A4 Invoice & Voucher Preview</span>
            </h3>
            <span className="text-[10px] text-slate-400 uppercase font-mono">Real-time Render</span>
          </div>

          {/* Scaled A4 Sheet Simulation */}
          <div
            id="branding-live-preview-card"
            className="bg-white border border-slate-300 shadow-md rounded-lg p-6 space-y-4 text-slate-800 text-[11px] select-none transition-all"
            style={{ fontFamily: profile.theme.fontFamily }}
          >
            {/* Top Colored Bar */}
            <div
              className="h-2 w-full rounded-xs"
              style={{ backgroundColor: profile.theme.primaryColor }}
            />

            {/* Header: Logo & Company Name */}
            <div className="flex items-start justify-between border-b pb-3 gap-2" style={{ borderColor: profile.theme.accentColor }}>
              <div className="flex items-center space-x-3 min-w-0">
                {profile.logoUrl ? (
                  <img src={profile.logoUrl} alt="Logo" className="w-12 h-12 object-contain rounded" />
                ) : (
                  <div
                    className="w-10 h-10 rounded flex items-center justify-center text-white font-bold text-xs shrink-0"
                    style={{ backgroundColor: profile.theme.primaryColor }}
                  >
                    LOGO
                  </div>
                )}
                <div className="min-w-0">
                  <h4
                    className="font-bold text-xs truncate leading-tight uppercase"
                    style={{ color: profile.theme.primaryColor }}
                  >
                    {profile.name}
                  </h4>
                  <p className="text-[10px] text-slate-500 truncate">{profile.address}</p>
                  <p className="text-[10px] text-slate-500 font-mono">TIN: {profile.tin} | VRN: {profile.vrn || 'N/A'}</p>
                </div>
              </div>

              <div
                className="px-2.5 py-1 rounded text-white font-bold text-[10px] shrink-0"
                style={{ backgroundColor: profile.theme.primaryColor }}
              >
                TAX INVOICE
              </div>
            </div>

            {/* Sample Recipient & Document Meta */}
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div className="p-2 bg-slate-50 rounded border border-slate-200">
                <span className="font-bold block" style={{ color: profile.theme.secondaryColor }}>
                  BILL TO:
                </span>
                <p className="font-semibold text-slate-700">Serengeti Infrastructure Ltd</p>
                <p className="text-slate-500">TIN: 102-491-884</p>
              </div>

              <div className="p-2 bg-slate-50 rounded border border-slate-200 text-right">
                <p className="text-slate-500">
                  Invoice No: <span className="font-bold text-slate-800 font-mono">INV-2026-0001</span>
                </p>
                <p className="text-slate-500">Date: {new Date().toISOString().slice(0, 10)}</p>
                <p className="font-semibold text-slate-700">Currency: TZS</p>
              </div>
            </div>

            {/* Sample Table */}
            <div className="border border-slate-200 rounded overflow-hidden">
              <div
                className="px-2 py-1 text-white font-bold text-[10px] grid grid-cols-12 gap-1"
                style={{ backgroundColor: profile.theme.primaryColor }}
              >
                <span className="col-span-6">ITEM</span>
                <span className="col-span-2 text-center">QTY</span>
                <span className="col-span-2 text-right">RATE</span>
                <span className="col-span-2 text-right">TOTAL</span>
              </div>
              <div className="px-2 py-1 text-[10px] grid grid-cols-12 gap-1 border-b border-slate-100 bg-white">
                <span className="col-span-6 font-medium text-slate-800">Bitumen Grade 60/70 (Drums)</span>
                <span className="col-span-2 text-center text-slate-600">50</span>
                <span className="col-span-2 text-right font-mono">850,000</span>
                <span className="col-span-2 text-right font-bold text-slate-800 font-mono">42,500,000</span>
              </div>
              <div className="px-2 py-1 text-[10px] grid grid-cols-12 gap-1 bg-slate-50">
                <span className="col-span-6 font-medium text-slate-800">TMT Rebar 16mm (Grade 500)</span>
                <span className="col-span-2 text-center text-slate-600">20</span>
                <span className="col-span-2 text-right font-mono">1,450,000</span>
                <span className="col-span-2 text-right font-bold text-slate-800 font-mono">29,000,000</span>
              </div>
            </div>

            {/* Totals & Bank Details */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="text-[9px] text-slate-500 space-y-0.5">
                <span className="font-bold block" style={{ color: profile.theme.secondaryColor }}>
                  BANK SETTLEMENT:
                </span>
                <p>Bank: {profile.bankDetails.bankName || 'CRDB Bank'}</p>
                <p>A/C No: {profile.bankDetails.accountNumber || '0150389281900'}</p>
                <p>SWIFT: {profile.bankDetails.swiftCode || 'CORUTZTZ'}</p>
              </div>

              <div className="text-right space-y-1">
                <p className="text-[10px] text-slate-600">
                  Subtotal: <span className="font-mono font-medium">TZS 71,500,000</span>
                </p>
                <p className="text-[10px] text-slate-600">
                  VAT (18%): <span className="font-mono font-medium">TZS 12,870,000</span>
                </p>
                <div
                  className="p-1 rounded text-white font-bold text-[11px]"
                  style={{ backgroundColor: profile.theme.primaryColor }}
                >
                  GRAND TOTAL: TZS 84,370,000
                </div>
              </div>
            </div>

            {/* Stamp & Signature Footer Section */}
            <div className="pt-3 border-t border-slate-200 flex items-end justify-between">
              <div className="text-[8px] text-slate-400">
                Official computer generated document.
              </div>

              <div className="flex items-center space-x-3">
                {/* Stamp */}
                {profile.stampUrl ? (
                  <img src={profile.stampUrl} alt="Stamp Preview" className="w-12 h-12 object-contain opacity-90" />
                ) : (
                  <div className="w-10 h-10 rounded-full border border-dashed border-indigo-300 flex items-center justify-center text-[8px] text-indigo-400 text-center font-bold">
                    SEAL
                  </div>
                )}

                {/* Signature */}
                <div className="text-center">
                  {profile.signatureUrl ? (
                    <img src={profile.signatureUrl} alt="Signature Preview" className="h-7 object-contain mx-auto" />
                  ) : (
                    <div className="h-6 w-16 border-b border-slate-400 mb-0.5" />
                  )}
                  <span className="text-[8px] font-semibold text-slate-600 block">Authorized Signatory</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
