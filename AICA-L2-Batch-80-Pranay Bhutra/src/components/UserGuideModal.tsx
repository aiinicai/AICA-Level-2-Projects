import React, { useState } from 'react';
import {
  X,
  BookOpen,
  Package,
  Truck,
  Camera,
  CheckCircle2,
  Bell,
  BarChart3,
  Shield,
  Search,
  Layers,
  Sparkles,
  Smartphone,
  ChevronRight,
  HelpCircle,
  Clock,
  ArrowRight,
  FileSpreadsheet
} from 'lucide-react';
import { ThemeStyle } from '../types';
import { THEMES } from '../utils/theme';

interface UserGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme?: ThemeStyle;
}

export const UserGuideModal: React.FC<UserGuideModalProps> = ({
  isOpen,
  onClose,
  currentTheme = 'navy'
}) => {
  const [activeSection, setActiveSection] = useState<'overview' | 'inward' | 'outward' | 'tracking' | 'pod' | 'faq'>('overview');

  if (!isOpen) return null;

  const themeConfig = THEMES[currentTheme];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                How to Use ParcelDesk
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Interactive Guide
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Self-learning guide for reception, audit & tax staff, partners, and dispatch coordinators.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Layout: Sidebar navigation + Content */}
        <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
          {/* Navigation Tabs */}
          <div className="w-full md:w-56 p-3 border-b md:border-b-0 md:border-r border-slate-800 bg-slate-950/50 flex md:flex-col gap-1 overflow-x-auto md:overflow-x-visible shrink-0">
            <button
              onClick={() => setActiveSection('overview')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'overview'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Sparkles className="w-4 h-4 shrink-0" />
              <span>1. Quick Overview</span>
            </button>

            <button
              onClick={() => setActiveSection('inward')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'inward'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Package className="w-4 h-4 shrink-0" />
              <span>2. Logging Inward</span>
            </button>

            <button
              onClick={() => setActiveSection('outward')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'outward'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Truck className="w-4 h-4 shrink-0" />
              <span>3. Outward Dispatch</span>
            </button>

            <button
              onClick={() => setActiveSection('tracking')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'tracking'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Search className="w-4 h-4 shrink-0" />
              <span>4. Real-time Search</span>
            </button>

            <button
              onClick={() => setActiveSection('pod')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'pod'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>5. Proof of Delivery</span>
            </button>

            <button
              onClick={() => setActiveSection('faq')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-all ${
                activeSection === 'faq'
                  ? `${themeConfig.activeTab} text-white`
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <HelpCircle className="w-4 h-4 shrink-0" />
              <span>6. FAQs & Tips</span>
            </button>
          </div>

          {/* Guide Content Pane */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6 text-sm text-slate-300">
            {/* Section 1: Overview */}
            {activeSection === 'overview' && (
              <div className="space-y-5 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-base font-bold text-white mb-1">Welcome to ParcelDesk</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    ParcelDesk is an all-in-one digital logistics and chain-of-custody registry designed for professional firms. It eliminates lost courier packages, missing audit files, un-recovered delivery expenses, and manual paper registers.
                  </p>
                </div>

                {/* 3-Step Lifecycle Visual */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs mb-2">
                      <Package className="w-4 h-4" />
                      <span>1. INWARD INTAKE</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Front-desk receives the package, clicks photo with camera, logs AWB, assigns physical rack slot (e.g. <b>Rack A-02</b>), and staff receives instant notification.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="flex items-center gap-2 text-blue-400 font-semibold text-xs mb-2">
                      <Truck className="w-4 h-4" />
                      <span>2. OUTWARD DISPATCH</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Staff generates dispatch docket linked to Client Job code (e.g. <b>AUD-2026-INFY</b>) for 100% cost recovery and automated tracking email/WhatsApp to client.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="flex items-center gap-2 text-purple-400 font-semibold text-xs mb-2">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>3. DIGITAL POD & AUDIT</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Capture digital touchscreen signature or courier POD scan. Export CSV logs anytime for statutory audit compliance (Form 3CD tax audit).
                    </p>
                  </div>
                </div>

                {/* Role Switcher Note */}
                <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-start gap-3">
                  <Shield className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-0.5">Role-Based Access Control (RBAC):</span>
                    <span>
                      Use the persona switcher on the top-right navbar to test as <b>Front Desk</b> (Pooja Verma), <b>Senior Partner</b> (CA Rajesh Sharma), or <b>Staff</b> (Sneha Kulkarni, Aniket Deshmukh).
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Section 2: Logging Inward */}
            {activeSection === 'inward' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Package className="w-4 h-4 text-emerald-400" />
                  How to Log an Inward Courier / Parcel
                </h3>
                <p className="text-xs text-slate-400">
                  Follow these 4 simple steps whenever a delivery carrier or peon arrives at the reception:
                </p>

                <div className="space-y-3">
                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold shrink-0">1</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Click "Log Inward" button</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Click the top green <b>"Log Inward"</b> button or the <b>"+ Log Inward Package"</b> button on the Inward Register.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold shrink-0">2</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Capture Live Parcel Photo (With Date & Time Stamp)</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Click <b>"Capture Parcel Photo (Live Camera)"</b>. Point camera at the parcel box/docket label and click <b>"Capture Photo"</b>. The photo is stamped automatically with time, date, and intake location.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold shrink-0">3</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Select Carrier (Or type custom carrier with "Others")</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Choose carrier (Blue Dart, DTDC, Speed Post, etc.) or choose <b>"Others"</b> to type any custom carrier or local delivery person's name. Enter the AWB / Tracking Reference number.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold shrink-0">4</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Assign Intended Staff & Physical Holding Shelf</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Select which staff member the parcel is for, and specify the physical location (e.g. <b>Rack A-02</b>, <b>Vault 1</b>). Click <b>"Confirm & Allocate Inward"</b>. The staff will immediately be alerted.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Section 3: Outward Dispatch */}
            {activeSection === 'outward' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Truck className="w-4 h-4 text-blue-400" />
                  How to Create an Outward Dispatch Docket
                </h3>
                <p className="text-xs text-slate-400">
                  When sending documents, tax appeals, audited financial statements, or certificates to clients or government authorities:
                </p>

                <div className="space-y-3">
                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold shrink-0">1</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Click "New Outbound"</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Click the top blue <b>"New Outbound"</b> button.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold shrink-0">2</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Enter Client Job Code for 100% Billing Recovery</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Select the client and Job Code (e.g. <b>AUD-2026-INFY</b>) so the courier cost is tracked as a billable out-of-pocket disbursement.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold shrink-0">3</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Specify Recipient & Address Details</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Add destination address, city, recipient phone, and email for dispatch notifications.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold shrink-0">4</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">Carrier & Weight Details</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Select the carrier (or choose <b>"Others"</b>), enter the tracking AWB, package weight, and cost.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Section 4: Real-time Search */}
            {activeSection === 'tracking' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Search className="w-4 h-4 text-amber-400" />
                  Real-time Reference Search & Tracking
                </h3>
                <p className="text-xs text-slate-400">
                  Any authorized personnel can immediately find any parcel in under 2 seconds:
                </p>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                  <h4 className="text-xs font-bold text-white">How the Tracking Box works:</h4>
                  <ul className="text-xs text-slate-400 space-y-2 list-disc list-inside">
                    <li>
                      Enter any <b>Carrier AWB number</b> (e.g. <span className="font-mono text-blue-400">BD-847291039</span>) or internal reference (e.g. <span className="font-mono text-emerald-400">INW-2026-0842</span>).
                    </li>
                    <li>
                      You can also search by <b>Sender name, Recipient staff, Shelf Rack, or Client name</b>.
                    </li>
                    <li>
                      Click <b>"Track"</b> or press Enter. The complete live delivery timeline and chain of custody will expand instantly with options to update status or view proof of delivery.
                    </li>
                  </ul>
                </div>
              </div>
            )}

            {/* Section 5: Proof of Delivery */}
            {activeSection === 'pod' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Digital Signatures & Proof of Delivery (POD)
                </h3>
                <p className="text-xs text-slate-400">
                  Guarantee document custody with tamper-evident digital sign-offs:
                </p>

                <div className="space-y-3">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <h4 className="text-xs font-bold text-white mb-1">For Inward Documents:</h4>
                    <p className="text-xs text-slate-400">
                      When staff comes to the reception to pick up their parcel from the rack, click <b>"Handover Sign-off"</b> to record the staff's signature on any touchscreen device or mouse.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    <h4 className="text-xs font-bold text-white mb-1">For Outward Dispatches:</h4>
                    <p className="text-xs text-slate-400">
                      When courier delivery is confirmed, click <b>"Upload / View POD"</b> to attach the carrier acknowledgement or recipient signature stamp.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Section 6: FAQs & Tips */}
            {activeSection === 'faq' && (
              <div className="space-y-3 animate-in fade-in duration-150">
                <h3 className="text-base font-bold text-white mb-2">Frequently Asked Questions</h3>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <h4 className="text-xs font-bold text-slate-200">Q: Can I install ParcelDesk on my mobile phone or iPad?</h4>
                  <p className="text-xs text-slate-400">
                    <b>A: Yes!</b> ParcelDesk is a progressive web app (PWA). Click the <b>"PWA App"</b> button in the navbar to see installation steps for iOS and Android. It works offline and launches like a native app.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <h4 className="text-xs font-bold text-slate-200">Q: How do I export reports for our Tax Audit / Form 3CD?</h4>
                  <p className="text-xs text-slate-400">
                    <b>A:</b> Switch to the <b>"Cost & Audit Reports"</b> tab. Click <b>"Export Dispatch CSV"</b> or <b>"Export Inward CSV"</b> to download clean spreadsheet registers.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <h4 className="text-xs font-bold text-slate-200">Q: Can I customize the firm theme and app logo?</h4>
                  <p className="text-xs text-slate-400">
                    <b>A:</b> Click the <b>"Theme"</b> button in the top navbar. You can choose between Executive Navy, Modern Emerald, Corporate Sapphire, and Warm Amber, and pick your preferred PWA insignia.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-slate-950">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Smartphone className="w-4 h-4 text-blue-400" />
            <span>Works seamlessly on desktop, iPad & mobile</span>
          </div>
          <button
            onClick={onClose}
            className={`px-5 py-2 rounded-xl ${themeConfig.primaryBtn} text-xs font-semibold transition-all`}
          >
            Got It, Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};
