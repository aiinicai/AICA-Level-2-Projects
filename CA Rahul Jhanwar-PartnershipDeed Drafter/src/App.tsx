import React, { useState, useEffect, useMemo } from 'react';
import { 
  Building2, 
  MapPin, 
  Calendar, 
  CreditCard, 
  FileText, 
  Plus, 
  Download, 
  Printer, 
  Eye, 
  CheckCircle2, 
  Users, 
  Scale, 
  ShieldCheck, 
  Sparkles, 
  FolderDown, 
  Laptop, 
  RotateCcw,
  BookOpen,
  Info,
  Layers,
  ArrowRight,
  ArrowLeft,
  Check,
  CheckCircle,
  FileCheck2,
  ChevronRight,
  Scissors
} from 'lucide-react';
import { DeedFormData, Partner, IndustryPreset, CustomClause, Witness } from './types';
import { 
  DEFAULT_INITIAL_DATA, 
  INDUSTRY_PRESETS, 
  calculateAge, 
  downloadWordDocument, 
  downloadStandaloneHtml,
  constructDeedBody,
  printDeedDocument,
  exportDeedToPDF
} from './utils/deedEngine';
import { Navbar } from './components/Navbar';
import { PartnerCard } from './components/PartnerCard';
import { BusinessObjectsAI } from './components/BusinessObjectsAI';
import { RemunerationSection } from './components/RemunerationSection';
import { CustomClausesEditor } from './components/CustomClausesEditor';
import { DeedPreview } from './components/DeedPreview';
import { DesktopExeModal } from './components/DesktopExeModal';
import { SupplementaryDeedEditor } from './components/SupplementaryDeedEditor';
import { DissolutionDeedEditor } from './components/DissolutionDeedEditor';
import { LicenseLockModal } from './components/LicenseLockModal';
import { getLicenseStatus, recordActiveUsage, LicenseStatus } from './utils/licenseManager';

const STORAGE_KEY = 'PARTNERSHIP_DEED_DRAFTER_DATA_V2';

export default function App() {
  const [formData, setFormData] = useState<DeedFormData>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to parse saved state:', e);
    }
    return DEFAULT_INITIAL_DATA;
  });

  const [activeStep, setActiveStep] = useState<number | 'all'>(1);
  const [activeView, setActiveView] = useState<'form' | 'preview' | 'split'>('split');
  const [isDesktopModalOpen, setIsDesktopModalOpen] = useState(false);
  const [lastSavedTime, setLastSavedTime] = useState<string | null>(null);
  const [saveToast, setSaveToast] = useState(false);

  // Commercial Licensing & 30-Minute Trial Engine
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus>(() => getLicenseStatus());
  const [isActivationModalOpen, setIsActivationModalOpen] = useState(false);

  useEffect(() => {
    // Record 5 seconds of active usage periodically
    const interval = setInterval(() => {
      const updated = recordActiveUsage(5);
      setLicenseStatus(updated);
    }, 5000);

    const handleLicenseChanged = () => {
      setLicenseStatus(getLicenseStatus());
    };
    window.addEventListener('PDD_LICENSE_CHANGED', handleLicenseChanged);

    return () => {
      clearInterval(interval);
      window.removeEventListener('PDD_LICENSE_CHANGED', handleLicenseChanged);
    };
  }, []);

  const isForcedLock = Boolean(licenseStatus.isExpired && !licenseStatus.isLicensed);

  // Auto recalculate partner ages whenever execution date changes
  const handleExecDateChange = (newDate: string) => {
    setFormData((prev) => {
      const updatedPartners = prev.partners.map((p) => {
        if (p.dob) {
          return { ...p, age: calculateAge(p.dob, newDate) };
        }
        return p;
      });
      return { ...prev, execDate: newDate, partners: updatedPartners };
    });
  };

  // Partner Handlers
  const handlePartnerUpdate = (index: number, field: keyof Partner, value: any) => {
    setFormData((prev) => {
      const partners = [...prev.partners];
      partners[index] = { ...partners[index], [field]: value };
      return { ...prev, partners };
    });
  };

  const handlePartnerBatchUpdate = (index: number, updates: Partial<Partner>) => {
    setFormData((prev) => {
      const partners = [...prev.partners];
      let updatedPartner = { ...partners[index], ...updates };
      if (updates.dob && !updates.age) {
        const age = calculateAge(updates.dob, prev.execDate);
        updatedPartner.age = age;
      }
      partners[index] = updatedPartner;
      return { ...prev, partners };
    });
  };

  const handlePartnerDobChange = (index: number, dobValue: string) => {
    setFormData((prev) => {
      const partners = [...prev.partners];
      const age = calculateAge(dobValue, prev.execDate);
      partners[index] = { ...partners[index], dob: dobValue, age };
      return { ...prev, partners };
    });
  };

  const handleAddPartner = () => {
    setFormData((prev) => ({
      ...prev,
      partners: [
        ...prev.partners,
        {
          id: `partner_${Date.now()}`,
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
        },
      ],
    }));
  };

  const handleRemovePartner = (index: number) => {
    if (formData.partners.length <= 2) return;
    setFormData((prev) => {
      const partners = prev.partners.filter((_, i) => i !== index);
      return { ...prev, partners };
    });
  };

  // Witness Handlers
  const handleWitnessUpdate = (index: number, field: keyof Witness, value: string) => {
    setFormData((prev) => {
      const witnesses = [...prev.witnesses];
      if (!witnesses[index]) {
        witnesses[index] = { id: `w_${index + 1}`, name: '', parentName: '', address: '' };
      }
      witnesses[index] = { ...witnesses[index], [field]: value };
      return { ...prev, witnesses };
    });
  };

  // Custom Clauses Handlers
  const handleAddCustomClause = (clause: CustomClause) => {
    setFormData((prev) => ({
      ...prev,
      customClauses: [...(prev.customClauses || []), clause],
    }));
  };

  const handleUpdateCustomClause = (id: string, field: keyof CustomClause, val: any) => {
    setFormData((prev) => ({
      ...prev,
      customClauses: (prev.customClauses || []).map((c) =>
        c.id === id ? { ...c, [field]: val } : c
      ),
    }));
  };

  const handleRemoveCustomClause = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      customClauses: (prev.customClauses || []).filter((c) => c.id !== id),
    }));
  };

  const handleUpdateFormData = (
    updates: Partial<DeedFormData> | ((prev: DeedFormData) => Partial<DeedFormData>)
  ) => {
    setFormData((prev) => {
      const resolved = typeof updates === 'function' ? updates(prev) : updates;
      return { ...prev, ...resolved };
    });
  };

  // Save Draft Manually
  const handleSaveDraft = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(formData));
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setLastSavedTime(now);
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 3000);
  };

  // Reset to Defaults
  const handleReset = () => {
    if (window.confirm('Clear all fields and reset the form to blank?')) {
      setFormData(DEFAULT_INITIAL_DATA);
      localStorage.removeItem(STORAGE_KEY);
      setLastSavedTime(null);
    }
  };

  // Preset Selection
  const handleSelectPreset = (preset: IndustryPreset) => {
    setFormData((prev) => ({
      ...prev,
      firmName: preset.firmName,
      rawBusinessIdea: preset.businessIdea,
      firmObjects: preset.firmObjects,
    }));
  };

  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);

  // Download / Print Handlers
  const handleDownloadWord = () => {
    if (isForcedLock) {
      setIsActivationModalOpen(true);
      return;
    }
    downloadWordDocument(formData);
  };

  const handleDownloadPDF = async () => {
    if (isForcedLock) {
      setIsActivationModalOpen(true);
      return;
    }
    setIsExportingPdf(true);
    try {
      await exportDeedToPDF(formData);
    } catch (e) {
      console.error('PDF export failed:', e);
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handlePrint = () => {
    if (isForcedLock) {
      setIsActivationModalOpen(true);
      return;
    }
    printDeedDocument(formData);
  };

  // Total profit validation
  const totalProfit = formData.partners.reduce(
    (sum, p) => sum + (parseFloat(p.profitShare) || 0),
    0
  );
  const isProfitValid = Math.abs(totalProfit - 100) < 0.01;

  // Completion calculation
  const completionPercentage = useMemo(() => {
    let score = 0;
    const totalChecks = 8;
    if (formData.execCity.trim()) score++;
    if (formData.execDate.trim()) score++;
    if (formData.commDate.trim()) score++;
    if (formData.firmName.trim()) score++;
    if (formData.firmAddress.trim()) score++;
    if (formData.firmObjects.trim()) score++;
    if (formData.partners.length >= 2 && formData.partners.every(p => p.name.trim() && p.dob.trim())) score++;
    if (isProfitValid) score++;
    return Math.round((score / totalChecks) * 100);
  }, [formData, isProfitValid]);

  const stepsList = [
    { id: 1, title: 'General & Firm Terms', subtitle: 'Date, Place & Firm Address' },
    { id: 2, title: 'Objects & AI Drafter', subtitle: 'Nature of Business Clause' },
    { id: 3, title: 'Remuneration & IT Act', subtitle: 'Sec 35(e) & Interest Ceiling' },
    { id: 4, title: 'Partners & Equity', subtitle: `${formData.partners.length} Partners & Shares` },
    { id: 5, title: 'Covenants & Clauses', subtitle: 'Non-Compete & Custom Terms' },
    { id: 6, title: 'Witnesses & Signatures', subtitle: 'Execution Table & Parties' },
  ];

  return (
    <div className="flex flex-col h-screen w-full bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden selection:bg-blue-600 selection:text-white">
      
      {/* App Navbar */}
      <Navbar
        onPreview={() => setActiveView(activeView === 'preview' ? 'form' : 'preview')}
        onDownloadWord={handleDownloadWord}
        onDownloadPDF={handleDownloadPDF}
        onPrint={handlePrint}
        isExportingPdf={isExportingPdf}
        onOpenDesktopModal={() => setIsDesktopModalOpen(true)}
        onSaveDraft={handleSaveDraft}
        onReset={handleReset}
        presets={INDUSTRY_PRESETS}
        onSelectPreset={handleSelectPreset}
        lastSavedTime={lastSavedTime}
        activeView={activeView}
        setActiveView={setActiveView}
        firmName={formData.firmName}
        deedType={formData.deedType || 'original'}
        onSelectDeedType={(type) => setFormData(prev => ({ ...prev, deedType: type }))}
        licenseStatus={licenseStatus}
        onOpenActivation={() => setIsActivationModalOpen(true)}
      />

      {/* Save Toast Notification */}
      {saveToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-xl flex items-center gap-2.5 text-xs font-semibold border border-slate-700 animate-in fade-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Draft state successfully saved to browser local storage.</span>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT: Navigation Sidebar (Steps) */}
        {(activeView === 'form' || activeView === 'split') && (
          <aside className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 select-none overflow-y-auto hidden md:flex">
            
            <div className="px-5 pt-5 pb-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Drafting Navigation
              </span>
            </div>

            {/* Step Selector List */}
            {formData.deedType === 'supplementary' ? (
              <div className="flex-1 px-4 py-3 space-y-4 text-xs">
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-indigo-900">
                  <span className="font-bold block text-indigo-950">Supplementary Deed Mode</span>
                  <p className="text-[11px] text-indigo-700 mt-1 leading-relaxed">
                    Upload scanned deed PDF to automatically OCR-extract all partners & clauses, then configure modifications.
                  </p>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Workflow Steps
                  </span>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">1</span>
                    <span>Upload & OCR Extract Deed</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">2</span>
                    <span>Original Deed Particulars</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">3</span>
                    <span>Select Modification Types</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">4</span>
                    <span>Configure Terms & Clauses</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">5</span>
                    <span>Preview & Download Word</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, deedType: 'original' }))}
                    className="w-full text-center py-2 text-slate-600 hover:text-blue-600 transition font-semibold text-xs border border-slate-200 rounded-lg hover:bg-slate-50"
                  >
                    ← Switch to Original Deed
                  </button>
                </div>
              </div>
            ) : formData.deedType === 'dissolution' ? (
              <div className="flex-1 px-4 py-3 space-y-4 text-xs">
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-900">
                  <span className="font-bold block text-red-950">Deed of Dissolution Mode</span>
                  <p className="text-[11px] text-red-700 mt-1 leading-relaxed">
                    Upload scanned deed PDF to extract firm partners, then draft dissolution covenants under Section 40 of Indian Partnership Act, 1932.
                  </p>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Workflow Steps
                  </span>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-[10px]">1</span>
                    <span>Upload & OCR Extract Deed</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-[10px]">2</span>
                    <span>Dissolution Date & Preamble</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-[10px]">3</span>
                    <span>Reason & Legal Basis</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-[10px]">4</span>
                    <span>Winding Up & Tax Liabilities</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-700 py-1 font-medium">
                    <span className="w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-[10px]">5</span>
                    <span>Custody of Books (8 Yrs)</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, deedType: 'original' }))}
                    className="w-full text-center py-2 text-slate-600 hover:text-blue-600 transition font-semibold text-xs border border-slate-200 rounded-lg hover:bg-slate-50"
                  >
                    ← Switch to Original Deed
                  </button>
                </div>
              </div>
            ) : (
              <nav className="flex-1 px-3 space-y-1">
                {stepsList.map((step) => {
                  const isActive = activeStep === step.id;
                  return (
                    <button
                      key={step.id}
                      type="button"
                      onClick={() => setActiveStep(step.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition text-xs ${
                        isActive 
                          ? 'bg-blue-50 text-blue-700 font-semibold' 
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
                      }`}
                    >
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 font-bold ${
                        isActive 
                          ? 'bg-blue-600 text-white' 
                          : 'border-2 border-slate-300 text-slate-500'
                      }`}>
                        {step.id}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate">{step.title}</div>
                        <div className="text-[10px] text-slate-400 truncate">{step.subtitle}</div>
                      </div>
                      {isActive && <ChevronRight className="w-3.5 h-3.5 text-blue-600 shrink-0" />}
                    </button>
                  );
                })}

                <div className="pt-2 border-t border-slate-100 my-2">
                  <button
                    type="button"
                    onClick={() => setActiveStep('all')}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition text-xs ${
                      activeStep === 'all' 
                        ? 'bg-blue-50 text-blue-700 font-semibold' 
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
                    }`}
                  >
                    <Layers className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>View All Sections</span>
                  </button>
                </div>
              </nav>
            )}

            {/* Sidebar Bottom Progress Widget */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 mt-auto">
              <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex justify-between items-center">
                  <span>Document Progress</span>
                  <span className="text-blue-700 font-mono font-bold">{completionPercentage}%</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mt-2">
                  <CheckCircle className="w-3 h-3 text-emerald-600 shrink-0" />
                  <span>IT Act 2025 Compliant</span>
                </div>
              </div>
            </div>

          </aside>
        )}

        {/* CENTER: Editor Form Content Section */}
        {(activeView === 'form' || activeView === 'split') && (
          <div id="editorContainer" className="flex-1 flex flex-col min-w-0 bg-[#F8FAFC] overflow-hidden">
            
            {/* Scrollable Form Body */}
            <div className="flex-1 p-6 sm:p-8 overflow-y-auto space-y-6">
              
              {/* Deed Format Switcher Header Banner */}
              <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Select Legal Format / डीड प्रारूप चुनें
                    </span>
                    <h2 className="text-sm sm:text-base font-bold text-slate-900">
                      {formData.deedType === 'supplementary'
                        ? 'Supplementary Deed of Partnership (संशोधन / सप्लीमेंट्री डीड)'
                        : formData.deedType === 'dissolution'
                        ? 'Deed of Dissolution of Partnership (फर्म समापन / डिसोल्यूशन डीड)'
                        : 'Original Partnership Deed (मूल पार्टनरशिप डीड - नई फर्म)'}
                    </h2>
                  </div>

                  {/* 3 Pill Tabs */}
                  <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-semibold shrink-0">
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, deedType: 'original' }))}
                      className={`px-3 py-1.5 rounded-lg transition ${
                        formData.deedType === 'original' || !formData.deedType
                          ? 'bg-white text-blue-700 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Original Deed
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, deedType: 'supplementary' }))}
                      className={`px-3 py-1.5 rounded-lg transition ${
                        formData.deedType === 'supplementary'
                          ? 'bg-white text-indigo-700 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Supplementary Deed
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, deedType: 'dissolution' }))}
                      className={`px-3 py-1.5 rounded-lg transition ${
                        formData.deedType === 'dissolution'
                          ? 'bg-white text-red-700 shadow-xs font-bold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Dissolution Deed
                    </button>
                  </div>
                </div>
              </div>

              {formData.deedType === 'supplementary' ? (
                <SupplementaryDeedEditor
                  formData={formData}
                  onUpdateFormData={handleUpdateFormData}
                />
              ) : formData.deedType === 'dissolution' ? (
                <DissolutionDeedEditor
                  formData={formData}
                  onUpdateFormData={handleUpdateFormData}
                />
              ) : (
                <>
                  {/* Step Header */}
                  {activeStep !== 'all' && (
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-1">
                    {stepsList.find(s => s.id === activeStep)?.title}
                  </h2>
                  <p className="text-sm text-slate-500 mb-6">
                    {activeStep === 1 && 'Configure the primary legal identifiers, place of deed execution, and principal head office address.'}
                    {activeStep === 2 && 'Draft exhaustive legal objects clause defining business activities under Indian Partnership Act, 1932.'}
                    {activeStep === 3 && 'Configure partner remuneration framework under Section 35(e) of Income-tax Act, 2025 and interest ceilings.'}
                    {activeStep === 4 && 'Add partner particulars, relationship titles, age calculation, and profit/loss distribution shares.'}
                    {activeStep === 5 && 'Enforce non-compete covenants, clientele data ownership, and append bespoke legal agreements.'}
                    {activeStep === 6 && 'Review witness signatures and execution acknowledgment for physical deed stamping.'}
                  </p>
                </div>
              )}

              {/* SECTION 1: Firm Execution Details */}
              {(activeStep === 1 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        1
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Firm & Execution Particulars
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Sec 4, Indian Partnership Act 1932
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                    
                    {/* Execution City */}
                    <div className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        Deed Execution City
                      </label>
                      <input
                        type="text"
                        value={formData.execCity}
                        onChange={(e) => setFormData({ ...formData, execCity: e.target.value.toUpperCase() })}
                        placeholder="SURAT"
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-medium uppercase text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                      />
                    </div>

                    {/* Execution Date */}
                    <div className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        Execution Date
                      </label>
                      <input
                        type="date"
                        value={formData.execDate}
                        onChange={(e) => handleExecDateChange(e.target.value)}
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-medium text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                      />
                    </div>

                    {/* Commencement Date */}
                    <div className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        Commencement Date
                      </label>
                      <input
                        type="date"
                        value={formData.commDate}
                        onChange={(e) => setFormData({ ...formData, commDate: e.target.value })}
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-medium text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                      />
                    </div>

                    {/* Firm Name */}
                    <div className="space-y-1 sm:col-span-2">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-slate-400" />
                        Firm Name & Style
                      </label>
                      <input
                        type="text"
                        value={formData.firmName}
                        onChange={(e) => setFormData({ ...formData, firmName: e.target.value.toUpperCase() })}
                        placeholder="M/S. BOUNCE & BEAUTY UNISEX SALON"
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-bold uppercase text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                      />
                    </div>

                    {/* Firm PAN / Status */}
                    <div className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <CreditCard className="w-3 h-3 text-slate-400" />
                        Firm PAN / Status
                      </label>
                      <input
                        type="text"
                        value={formData.firmPan}
                        onChange={(e) => setFormData({ ...formData, firmPan: e.target.value.toUpperCase() })}
                        placeholder="APPLIED FOR"
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-mono text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase"
                      />
                    </div>

                    {/* Principal Place of Business */}
                    <div className="space-y-1 sm:col-span-2 lg:col-span-3">
                      <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        Principal Place of Business (Registered Office Address)
                      </label>
                      <textarea
                        rows={2}
                        value={formData.firmAddress}
                        onChange={(e) => setFormData({ ...formData, firmAddress: e.target.value.toUpperCase() })}
                        placeholder="SHOP NO. 106 & 107, 1ST FLOOR, TIMES CORNER, V.I.P ROAD, SURAT - 395007 (GUJARAT)"
                        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 uppercase text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                      />
                    </div>

                    {/* Front Cover Page Config Block */}
                    <div className="sm:col-span-2 lg:col-span-3 bg-indigo-50/60 border border-indigo-100 rounded-xl p-4 mt-2">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <BookOpen className="w-4 h-4 text-indigo-600" />
                          <span className="font-bold text-xs text-indigo-950">
                            Partnership Deed Front Cover Page (Title Page)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleUpdateFormData({ includeCoverPage: formData.includeCoverPage === false ? true : false })}
                          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                            formData.includeCoverPage !== false ? 'bg-indigo-600' : 'bg-slate-300'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                              formData.includeCoverPage !== false ? 'translate-x-4' : 'translate-x-0'
                            }`}
                          />
                        </button>
                      </div>

                      <p className="text-[11px] text-indigo-900/80 mb-3">
                        Adds a front title page formatted with double border containing <b>PARTNERSHIP DEED OF {formData.firmName || 'M/S. [FIRM NAME]'}</b>, partner names, date & prepared by note before Clause 1.
                      </p>

                      {formData.includeCoverPage !== false && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                              Cover Page Title Heading
                            </label>
                            <input
                              type="text"
                              value={formData.coverPageTitle || 'PARTNERSHIP DEED'}
                              onChange={(e) => handleUpdateFormData({ coverPageTitle: e.target.value.toUpperCase() })}
                              placeholder="PARTNERSHIP DEED"
                              className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-900 uppercase focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                              Prepared / Drafted By Note
                            </label>
                            <input
                              type="text"
                              value={formData.coverPagePreparedBy || ''}
                              onChange={(e) => handleUpdateFormData({ coverPagePreparedBy: e.target.value.toUpperCase() })}
                              placeholder="ADVOCATE & LEGAL CONSULTANT / CA"
                              className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 uppercase focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                          </div>
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              )}

              {/* SECTION 2: AI Business Objects Drafter */}
              {(activeStep === 2 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        2
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Business Objects & Nature of Trade
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Clause #3 in Legal Deed
                    </span>
                  </div>

                  <BusinessObjectsAI
                    rawBusinessIdea={formData.rawBusinessIdea}
                    onUpdateRawIdea={(val) => setFormData({ ...formData, rawBusinessIdea: val })}
                    firmObjects={formData.firmObjects}
                    onUpdateFirmObjects={(val) => setFormData({ ...formData, firmObjects: val })}
                  />
                </div>
              )}

              {/* SECTION 3: Income Tax Remuneration Framework */}
              {(activeStep === 3 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        3
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Remuneration & Income-tax Act Framework
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Sec 35(e), IT Act 2025
                    </span>
                  </div>

                  <RemunerationSection
                    remunType={formData.remunType}
                    onUpdateRemunType={(val) => setFormData({ ...formData, remunType: val })}
                    remunDistribution={formData.remunDistribution}
                    onUpdateDistribution={(val) => setFormData({ ...formData, remunDistribution: val })}
                    interestRate={formData.interestRate}
                    onUpdateInterestRate={(val) => setFormData({ ...formData, interestRate: val })}
                    partners={formData.partners}
                    onUpdatePartnerSalary={(partnerId, salaryMonthly) => {
                      const updatedPartners = formData.partners.map((p) => {
                        if (p.id === partnerId) {
                          const annual = salaryMonthly ? (parseInt(salaryMonthly, 10) * 12).toString() : '';
                          return { ...p, salaryMonthly, salaryAnnual: annual };
                        }
                        return p;
                      });
                      setFormData({ ...formData, partners: updatedPartners });
                    }}
                  />
                </div>
              )}

              {/* SECTION 4: Partner Details */}
              {(activeStep === 4 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        4
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Partner Particulars & Profit Ratio ({formData.partners.length} Partners)
                      </h3>
                    </div>

                    <button
                      type="button"
                      onClick={handleAddPartner}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-xs transition"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Partner</span>
                    </button>
                  </div>

                  {/* Profit Share Allocation Bar */}
                  <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800">Total Profit Share Allocation:</span>
                      <span className={`font-mono font-bold px-2 py-0.5 rounded text-xs ${
                        isProfitValid 
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                          : 'bg-rose-100 text-rose-800 border border-rose-300'
                      }`}>
                        {totalProfit.toFixed(2)}% / 100%
                      </span>
                    </div>
                    {isProfitValid ? (
                      <span className="text-emerald-700 font-semibold text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Balanced
                      </span>
                    ) : (
                      <span className="text-rose-600 font-semibold text-[11px]">
                        Difference: {(100 - totalProfit).toFixed(2)}%
                      </span>
                    )}
                  </div>

                  {/* Partner Card List */}
                  <div className="space-y-4">
                    {formData.partners.map((partner, index) => (
                      <PartnerCard
                        key={partner.id}
                        partner={partner}
                        index={index}
                        totalPartners={formData.partners.length}
                        onUpdate={handlePartnerUpdate}
                        onRemove={handleRemovePartner}
                        onDobChange={handlePartnerDobChange}
                        onBatchUpdate={handlePartnerBatchUpdate}
                      />
                    ))}
                  </div>

                  <div className="flex justify-center pt-2">
                    <button
                      type="button"
                      onClick={handleAddPartner}
                      className="flex items-center gap-2 px-5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold border border-slate-300 transition"
                    >
                      <Plus className="w-4 h-4 text-blue-600" />
                      <span>+ Add Another Partner</span>
                    </button>
                  </div>
                </div>
              )}

              {/* SECTION 5: Special Covenants & Custom Clauses */}
              {(activeStep === 5 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        5
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Special Covenants & Custom Clauses
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Non-Compete & IP
                    </span>
                  </div>

                  <CustomClausesEditor
                    nonCompete={formData.nonCompete}
                    onToggleNonCompete={(val) => setFormData({ ...formData, nonCompete: val })}
                    clientOwnership={formData.clientOwnership}
                    onToggleClientOwnership={(val) => setFormData({ ...formData, clientOwnership: val })}
                    customClauses={formData.customClauses || []}
                    onAddClause={handleAddCustomClause}
                    onUpdateClause={handleUpdateCustomClause}
                    onRemoveClause={handleRemoveCustomClause}
                  />
                </div>
              )}

              {/* SECTION 6: Witnesses Details */}
              {(activeStep === 6 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        6
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Witness Particulars (Execution Page)
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Physical Signing
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    
                    {/* Witness 1 */}
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                      <div className="font-bold text-slate-800 text-xs uppercase">WITNESS #1</div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Full Name</label>
                        <input
                          type="text"
                          value={formData.witnesses[0]?.name || ''}
                          onChange={(e) => handleWitnessUpdate(0, 'name', e.target.value.toUpperCase())}
                          placeholder="WITNESS 1 FULL NAME"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Father's / Husband's Name</label>
                        <input
                          type="text"
                          value={formData.witnesses[0]?.parentName || ''}
                          onChange={(e) => handleWitnessUpdate(0, 'parentName', e.target.value.toUpperCase())}
                          placeholder="FATHER'S / HUSBAND'S NAME"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Full Address</label>
                        <textarea
                          rows={2}
                          value={formData.witnesses[0]?.address || ''}
                          onChange={(e) => handleWitnessUpdate(0, 'address', e.target.value.toUpperCase())}
                          placeholder="RESIDENTIAL ADDRESS OF WITNESS 1"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                    </div>

                    {/* Witness 2 */}
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                      <div className="font-bold text-slate-800 text-xs uppercase">WITNESS #2</div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Full Name</label>
                        <input
                          type="text"
                          value={formData.witnesses[1]?.name || ''}
                          onChange={(e) => handleWitnessUpdate(1, 'name', e.target.value.toUpperCase())}
                          placeholder="WITNESS 2 FULL NAME"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Father's / Husband's Name</label>
                        <input
                          type="text"
                          value={formData.witnesses[1]?.parentName || ''}
                          onChange={(e) => handleWitnessUpdate(1, 'parentName', e.target.value.toUpperCase())}
                          placeholder="FATHER'S / HUSBAND'S NAME"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1 uppercase">Full Address</label>
                        <textarea
                          rows={2}
                          value={formData.witnesses[1]?.address || ''}
                          onChange={(e) => handleWitnessUpdate(1, 'address', e.target.value.toUpperCase())}
                          placeholder="RESIDENTIAL ADDRESS OF WITNESS 2"
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                      </div>
                    </div>

                  </div>
                </div>
              )}

              {/* SECTION 6.5: Document Spacing & Page Break Controls */}
              {(activeStep === 6 || activeStep === 'all') && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center border border-blue-200">
                        <Scissors className="w-3.5 h-3.5 text-blue-600" />
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Page Breaks & Stamp Paper Layout
                      </h3>
                    </div>
                    <span className="text-[11px] text-blue-600 font-semibold">
                      {formData.signaturePageBreak === 'continuous' ? 'Continuous Flow (No blank gaps)' : 'New Page for Signatures'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {/* Signature Placement Choice */}
                    <div 
                      onClick={() => handleUpdateFormData({ signaturePageBreak: 'continuous' })}
                      className={`cursor-pointer p-3 rounded-lg border transition ${
                        formData.signaturePageBreak === 'continuous'
                          ? 'border-blue-600 bg-blue-50/50 text-blue-950 font-medium'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs">Continuous Flow (Recommended)</span>
                        <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                          formData.signaturePageBreak === 'continuous' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'
                        }`}>
                          {formData.signaturePageBreak === 'continuous' && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Signatures immediately follow the last clause with no blank gap.
                      </p>
                    </div>

                    <div 
                      onClick={() => handleUpdateFormData({ signaturePageBreak: 'newPage' })}
                      className={`cursor-pointer p-3 rounded-lg border transition ${
                        formData.signaturePageBreak === 'newPage'
                          ? 'border-blue-600 bg-blue-50/50 text-blue-950 font-medium'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs">Force New Page for Signatures</span>
                        <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                          formData.signaturePageBreak === 'newPage' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'
                        }`}>
                          {formData.signaturePageBreak === 'newPage' && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Starts execution block and partner photos on a dedicated new page.
                      </p>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500">
                    💡 <b>Tip:</b> Click <b>"Page Breaks"</b> in the top preview toolbar to pick specific clauses to break or tweak spacing density (Compact / Tight / Standard).
                  </p>
                </div>
              )}
              </>
              )}

            </div>

            {/* Bottom Action Footer Bar */}
            <div className="h-20 bg-white border-t border-slate-200 px-6 sm:px-8 flex items-center justify-between shrink-0">
              <button
                type="button"
                onClick={handleSaveDraft}
                className="px-5 py-2.5 border border-slate-300 text-slate-700 font-semibold rounded-lg hover:bg-slate-50 transition-colors text-xs flex items-center gap-2 shadow-2xs"
              >
                <span>Save Draft</span>
              </button>

              <div className="flex items-center gap-3">
                {formData.deedType && formData.deedType !== 'original' ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setActiveView('preview')}
                      className="px-6 py-2.5 bg-blue-700 text-white font-semibold rounded-lg hover:bg-blue-800 shadow-md shadow-blue-900/10 transition-all text-xs flex items-center gap-2"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Preview {formData.deedType === 'supplementary' ? 'Supplementary' : 'Dissolution'} Deed</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadWord}
                      className="px-5 py-2.5 bg-slate-900 text-white font-semibold rounded-lg hover:bg-slate-800 transition text-xs flex items-center gap-2 shadow-xs"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download Word (.doc)</span>
                    </button>
                  </>
                ) : (
                  <>
                    {activeStep !== 'all' && activeStep > 1 && (
                      <button
                        type="button"
                        onClick={() => setActiveStep(typeof activeStep === 'number' ? activeStep - 1 : 1)}
                        className="px-5 py-2.5 border border-slate-300 text-slate-700 font-semibold rounded-lg hover:bg-slate-50 transition-colors text-xs flex items-center gap-2 shadow-2xs"
                      >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        <span>Previous Step</span>
                      </button>
                    )}

                    {activeStep !== 'all' && activeStep < 6 && (
                      <button
                        type="button"
                        onClick={() => setActiveStep(typeof activeStep === 'number' ? activeStep + 1 : 2)}
                        className="px-6 py-2.5 bg-blue-700 text-white font-semibold rounded-lg hover:bg-blue-800 shadow-md shadow-blue-900/10 transition-all text-xs flex items-center gap-2"
                      >
                        <span>Continue to Next</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {(activeStep === 6 || activeStep === 'all') && (
                      <button
                        type="button"
                        onClick={() => setActiveView('preview')}
                        className="px-6 py-2.5 bg-blue-700 text-white font-semibold rounded-lg hover:bg-blue-800 shadow-md shadow-blue-900/10 transition-all text-xs flex items-center gap-2"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View Live Deed</span>
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>

          </div>
        )}

        {/* RIGHT: Live Deed Document Preview Panel */}
        {(activeView === 'preview' || activeView === 'split') && (
          <div className={activeView === 'split' ? 'w-[380px] lg:w-[440px] xl:w-[480px] bg-[#E2E8F0] border-l border-slate-300 flex flex-col shrink-0 overflow-hidden' : 'flex-1 bg-[#E2E8F0] flex flex-col overflow-hidden'}>
            <DeedPreview
              formData={formData}
              onDownloadWord={handleDownloadWord}
              onDownloadPDF={handleDownloadPDF}
              onPrint={handlePrint}
              onUpdateFormData={handleUpdateFormData}
              isExportingPdf={isExportingPdf}
            />
          </div>
        )}

      </div>

      {/* Desktop App & .EXE Modal */}
      <DesktopExeModal
        isOpen={isDesktopModalOpen}
        onClose={() => setIsDesktopModalOpen(false)}
        formData={formData}
      />

      {/* Commercial License Lock & Activation Modal */}
      <LicenseLockModal
        isOpen={isForcedLock || isActivationModalOpen}
        onClose={() => setIsActivationModalOpen(false)}
        status={licenseStatus}
        isForcedLock={isForcedLock}
      />

      {/* Hidden Printable Container for Window.print() */}
      <div 
        id="printableDeedArea" 
        className="hidden print:block text-black"
        dangerouslySetInnerHTML={{ __html: constructDeedBody(formData) }}
      />

    </div>
  );
}
