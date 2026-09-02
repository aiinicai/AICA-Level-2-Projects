import React, { useState } from 'react';
import { 
  BookOpen, 
  Search, 
  Sparkles, 
  ShieldCheck, 
  Layers, 
  QrCode, 
  AlertTriangle, 
  Workflow, 
  FileText, 
  ClipboardCheck, 
  ArrowRight, 
  CheckCircle2, 
  HelpCircle, 
  UserCheck, 
  Scale, 
  Printer, 
  Sparkle,
  Compass,
  ChevronRight,
  ExternalLink,
  Info
} from 'lucide-react';
import { NavTab } from './Navbar';

interface UserManualProps {
  onNavigateTab: (tab: NavTab) => void;
  onOpenDemoSpotlight: () => void;
}

export const UserManual: React.FC<UserManualProps> = ({
  onNavigateTab,
  onOpenDemoSpotlight
}) => {
  const [activeSection, setActiveSection] = useState<'quickstart' | 'modules' | 'roles' | 'statutory' | 'faq'>('quickstart');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const sections = [
    { id: 'quickstart', label: '1. Quick Start & Workflow Tour', icon: Compass },
    { id: 'modules', label: '2. Module-by-Module User Guide', icon: Layers },
    { id: 'roles', label: '3. Role-Based Operating Playbooks', icon: UserCheck },
    { id: 'statutory', label: '4. Statutory & Accounting Guidelines', icon: Scale },
    { id: 'faq', label: '5. FAQ & Troubleshooting', icon: HelpCircle }
  ] as const;

  const faqs = [
    {
      q: 'What is the Asset Reliability Score and how is it calculated?',
      a: 'The Asset Reliability Score is a real-time index (0 to 100) that measures the balance-sheet audit readiness and physical integrity of the enterprise asset register. It evaluates 5 core dimensions: (1) Physical Verification Recency & Coverage (25%), (2) Source Document & 3-Way Match Completeness (20%), (3) General Ledger vs Fixed Asset Subledger Reconciliation (20%), (4) Statutory & Ind AS Policy Compliance (20%), and (5) Open Anomaly & Exception Resolution Velocity (15%).'
    },
    {
      q: 'How does AI Capitalisation Review handle Ind AS 16 componentisation?',
      a: 'Under Ind AS 16 (Para 43), each part of an item of Property, Plant, and Equipment with a cost that is significant in relation to total cost must be depreciated separately. AssetTrust AI analyzes the technical invoice line items, OEM manuals, and purchase orders to automatically break large equipment (e.g., a ₹48.5L CNC Machine) into distinct sub-components with independent useful lives (e.g., Cast Iron Frame: 15 yrs, Spindle: 6 yrs, CNC Controller: 6 yrs), ensuring 100% statutory compliance upon Controller approval.'
    },
    {
      q: 'What is the CARO 2020 Clause 3(i)(b) 10% discrepancy rule and how is it tracked?',
      a: 'Under Clause 3(i)(b) of the Companies (Auditor\'s Report) Order (CARO) 2020, management must physically verify fixed assets at reasonable intervals. If material discrepancies of 10% or more in the aggregate value of any class of assets are noticed during physical verification, they must be properly dealt with in the books of account. AssetTrust AI automatically calculates variance percentages across asset categories and flags any category nearing or exceeding 10% directly in the Risk Radar.'
    },
    {
      q: 'How do field auditors perform physical verification with mobile or terminal QR scanning?',
      a: 'In the "Verification Ops" module, field auditors can use any camera or barcode terminal to scan asset QR codes or enter Asset IDs. The system captures the machine serial number, plant location, operator custodian, and live GPS coordinates. If an asset is scanned at an unauthorized plant (e.g., tagged to Pune but scanned in Manesar), the system immediately records a "Location Drift" variance and opens an investigation ticket in the Exception Workflow.'
    },
    {
      q: 'How are tax depreciation (Income Tax Act Sec 32) and book depreciation (Sch II) synchronized?',
      a: 'AssetTrust AI maintains dual depreciation schedules for every asset: (1) Book Depreciation based on Straight Line Method (SLM) / Useful Life under Companies Act 2013 Schedule II and Ind AS 16, and (2) Tax Depreciation based on the Written Down Value (WDV) Block of Assets system under Income Tax Act Section 32 (e.g. 15% for Plant & Machinery, 40% for Computers). You can inspect this dual schedule in any asset\'s 360° dossier.'
    },
    {
      q: 'How do I approve and push a Capex procurement item into the live Fixed Asset Register?',
      a: 'Navigate to "AI Capex Review", select any inbound item from the Capex Queue, review the AI\'s classification, component split, and GST ITC eligibility assessment. Select an approver (e.g., Plant Controller or CFO), input an optional approval remark, and click "Approve & Capitalise to Subledger". The item is instantly minted as a verified asset in the Fixed Asset Register with full sub-components and audit trails.'
    }
  ];

  const filteredFaqs = faqs.filter(
    (f) => f.q.toLowerCase().includes(searchQuery.toLowerCase()) || f.a.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 pb-16">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <BookOpen className="w-4 h-4 text-blue-600" />
            <span>Platform Documentation & User Manual</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            AssetTrust AI — User Guidance & Operating Manual
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-3xl leading-relaxed">
            Comprehensive guide to navigating the Fixed Asset Governance Control Tower, AI Capitalisation Review, QR Physical Verification, Anomaly Risk Radar, and CARO 2020 Statutory Audit Assurance.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => window.print()}
            className="px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold flex items-center space-x-1.5 transition-colors border border-slate-200 shadow-2xs"
          >
            <Printer className="w-4 h-4" />
            <span>Print Manual</span>
          </button>
          
          <button
            onClick={onOpenDemoSpotlight}
            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-xs"
          >
            <Sparkle className="w-4 h-4 text-blue-200" />
            <span>Interactive Case Demo</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs & Search */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2 overflow-x-auto scrollbar-none w-full sm:w-auto">
            {sections.map((sec) => {
              const Icon = sec.icon;
              const isActive = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveSection(sec.id)}
                  className={`px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap flex items-center space-x-2 transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-slate-200'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{sec.label}</span>
                </button>
              );
            })}
          </div>

          <div className="relative w-full sm:w-64 shrink-0">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search guidance, rules, terms..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* SECTION 1: QUICK START & WORKFLOW TOUR */}
      {activeSection === 'quickstart' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Visual End-to-End Governance Flow */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
              <Compass className="w-4 h-4 text-blue-600" />
              <span>Core Architecture & Asset Lifecycle</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900">
              How AssetTrust AI Governs Fixed Assets from Inception to Audit
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">
              AssetTrust AI replaces disjointed spreadsheets and ERP blindspots with an autonomous, continuous internal controls engine that operates across 5 integrated lifecycle stages:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2">
              {[
                {
                  step: '01',
                  title: 'Inbound Procurement',
                  desc: 'PO, GRN, and Tax Invoice matching with GST Section 17(5) ITC validation.',
                  tab: 'capex-review' as NavTab,
                  tabName: 'AI Capex Review'
                },
                {
                  step: '02',
                  title: 'Ind AS 16 Split',
                  desc: 'AI recommends useful life, component split under Para 43, and Sch II life.',
                  tab: 'capex-review' as NavTab,
                  tabName: 'Capitalise Asset'
                },
                {
                  step: '03',
                  title: 'Subledger & QR Tag',
                  desc: 'Unique QR matrix assigned; registered in subledger with dual depreciation.',
                  tab: 'register' as NavTab,
                  tabName: 'Asset Register'
                },
                {
                  step: '04',
                  title: 'Field Verification',
                  desc: 'Mobile QR scans & GPS checks continuously validate physical presence.',
                  tab: 'physical-verification' as NavTab,
                  tabName: 'Verification Ops'
                },
                {
                  step: '05',
                  title: 'Assurance & Audit',
                  desc: 'CARO 2020 Clause 3(i) monitoring, anomaly resolution, and Big-4 audit memos.',
                  tab: 'audit-readiness' as NavTab,
                  tabName: 'Audit Readiness'
                }
              ].map((item, idx) => (
                <div key={idx} className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col justify-between space-y-3 relative group hover:border-blue-400 transition-all shadow-2xs">
                  <div className="space-y-1.5">
                    <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 inline-block">
                      Phase {item.step}
                    </span>
                    <h3 className="text-xs font-bold text-slate-900">{item.title}</h3>
                    <p className="text-[11px] text-slate-500 leading-snug">{item.desc}</p>
                  </div>
                  <button
                    onClick={() => onNavigateTab(item.tab)}
                    className="w-full py-1.5 px-2 rounded-lg bg-white border border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-[11px] font-bold text-slate-700 flex items-center justify-center space-x-1 transition-colors shadow-2xs"
                  >
                    <span>Open {item.tabName}</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* 5-Minute Quick Start Guide */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <span>5-Minute Quick Start: Key Actions to Test Now</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Action 1: Review & Approve Inbound Capex</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Step 1
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Go to <strong className="text-slate-900">AI Capex Review</strong>. Click on <span className="font-mono text-blue-700">CAP-2024-001 (5-Axis CNC Machine)</span> or any pending invoice. Inspect the AI’s Ind AS 16 component split into 3 parts, select an approver, and click <em>"Approve & Capitalise to Subledger"</em> to witness real-time ingestion.
                </p>
                <button
                  onClick={() => onNavigateTab('capex-review')}
                  className="text-blue-600 hover:text-blue-800 font-bold flex items-center space-x-1 pt-1"
                >
                  <span>Go to AI Capex Review</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Action 2: Inspect Deep 360° Asset Dossier</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Step 2
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Open the <strong className="text-slate-900">Asset Register</strong> and click on any asset row (or the CNC Spotlight button in the top bar). Explore the 5 inspection tabs: Overview, Dual Depreciation (Books vs Tax), Sub-components, QR Verification, and Audit Evidence 3-Way Match.
                </p>
                <button
                  onClick={() => onNavigateTab('register')}
                  className="text-blue-600 hover:text-blue-800 font-bold flex items-center space-x-1 pt-1"
                >
                  <span>Go to Asset Register</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Action 3: Simulate Field QR Code Scanning</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Step 3
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Open <strong className="text-slate-900">Verification Ops</strong>. Use the terminal quick-scan buttons (e.g. <em>Scan CNC Machine</em> or <em>Scan Generator</em>). Experience how instant verification logs geolocation stamps, matches serial numbers, and updates CARO physical verification status.
                </p>
                <button
                  onClick={() => onNavigateTab('physical-verification')}
                  className="text-blue-600 hover:text-blue-800 font-bold flex items-center space-x-1 pt-1"
                >
                  <span>Go to Verification Ops</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Action 4: Generate Executive Audit Memorandum</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Step 4
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Navigate to <strong className="text-slate-900">Audit Readiness</strong> and click <em>"Generate Executive Audit Summary"</em>. The AI will synthesize a complete, Big-4 style statutory audit memo detailing CARO Clause 3(i) compliance, gross block reconciliation, and key control matters.
                </p>
                <button
                  onClick={() => onNavigateTab('audit-readiness')}
                  className="text-blue-600 hover:text-blue-800 font-bold flex items-center space-x-1 pt-1"
                >
                  <span>Go to Audit Readiness</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: MODULE-BY-MODULE USER GUIDE */}
      {activeSection === 'modules' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {[
            {
              id: 'control-tower',
              title: 'Module 1: Executive Control Tower & Reliability Score (0–100)',
              icon: ShieldCheck,
              tab: 'control-tower' as NavTab,
              summary: 'The central nerve center for CFOs and Finance Directors, offering holistic visibility into asset base valuation, statutory health, and plant risk distribution.',
              keyFeatures: [
                { title: 'Asset Reliability Score Gauge', text: 'Combines 5 core drivers: Physical Verification (25%), Document Completeness (20%), Subledger Reconciliation (20%), Policy Compliance (20%), and Anomaly Resolution (15%).' },
                { title: 'Gross Block & NBV Summary', text: 'Live financial totals displayed in ₹ Crores, ₹ Lakhs, or Full INR with instant currency toggle.' },
                { title: 'Multi-Plant Health Matrix', text: 'Tracks physical coverage and risk scores across 5 manufacturing hubs: Pune, Chennai, Manesar, Sanand, and Bengaluru HQ.' },
                { title: 'Risk Distribution & Urgent Action Radar', text: 'Direct access to high-severity findings requiring immediate Controller or Audit Committee intervention.' }
              ]
            },
            {
              id: 'register',
              title: 'Module 2: Fixed Asset Register & 360° Technical Dossier',
              icon: Layers,
              tab: 'register' as NavTab,
              summary: 'The primary digital subledger tracking every capital asset with complete provenance, technical specs, dual book depreciation, and component breakdowns.',
              keyFeatures: [
                { title: 'Multi-Dimensional Search & Filtering', text: 'Filter instantly by Plant location, Asset Category, Verification Status (Verified, Missing, Wrong Location), or Risk Level.' },
                { title: '360° Modal Dossier', text: 'Click any asset to inspect 5 dedicated sub-views: General Overview, Dual Depreciation (Books vs Tax), Sub-components under Ind AS 16, Physical QR Verification history, and 3-Way Match documents.' },
                { title: 'Spotlight Showcase', text: 'Inspect pre-configured benchmark assets like the ₹48.5L DMG Mori CNC Machine to see end-to-end governance in practice.' }
              ]
            },
            {
              id: 'capex-review',
              title: 'Module 3: AI Capitalisation Review & Policy Memo Engine',
              icon: Sparkles,
              tab: 'capex-review' as NavTab,
              summary: 'Evaluates pending procurement invoices against Ind AS 16, Schedule II, and GST regulations to automate capitalisation and componentisation decisions.',
              keyFeatures: [
                { title: 'Automated 3-Way Match Validation', text: 'Cross-verifies Purchase Order (PO), Goods Receipt Note (GRN), and Vendor Tax Invoice.' },
                { title: 'Ind AS 16 Componentisation Suggestion', text: 'Automatically recommends splitting complex assets into sub-components with distinct useful lives under Para 43.' },
                { title: 'GST ITC Eligibility Check', text: 'Flags blocked input tax credit under CGST Act Section 17(5) (e.g., civil works or motor vehicles) vs eligible machinery.' },
                { title: 'Human Controller Approval & Auto-Ingestion', text: 'Mandates human approval before pushing the asset directly into the active Fixed Asset Subledger.' }
              ]
            },
            {
              id: 'physical-verification',
              title: 'Module 4: Verification Ops & Field QR Scanner Terminal',
              icon: QrCode,
              tab: 'physical-verification' as NavTab,
              summary: 'Enables plant engineers and field auditors to scan QR matrix tags on the shop floor with real-time GPS telemetry and discrepancy logging.',
              keyFeatures: [
                { title: 'High-Contrast Shop-Floor Terminal', text: 'Optimized for mobile tablets and handheld barcode scanners with quick-scan presets.' },
                { title: 'Live Geolocation & Serial Number Match', text: 'Captures GPS coordinates and matches physical nameplates against digital register serials.' },
                { title: 'Variance Auto-Escalation', text: 'Automatically logs discrepancies (e.g. Location Drift, Suspected Ghost Asset, Missing Tag) and triggers Risk Radar alerts.' },
                { title: 'CARO 2020 Clause 3(i)(b) Cycle Tracker', text: 'Monitors ongoing annual physical count progress towards statutory 100% cycle completion.' }
              ]
            },
            {
              id: 'risk-radar',
              title: 'Module 5: Risk Radar & Deterministic Anomaly Engine',
              icon: AlertTriangle,
              tab: 'risk-radar' as NavTab,
              summary: 'Continuously scans the asset subledger for 7 major categories of financial and compliance risk.',
              keyFeatures: [
                { title: 'Ghost Asset Detection', text: 'Identifies active capitalised assets that were unverified during consecutive physical count cycles.' },
                { title: 'Duplicate Capitalisation Alerts', text: 'Detects identical serial numbers or invoice references across multiple subledger entries.' },
                { title: 'Ind AS 36 Impairment Flags', text: 'Monitors idle or damaged machinery for impairment triggers and recoverable amount re-assessment.' },
                { title: 'Financial Exposure Quantification', text: 'Calculates exact Net Book Value (NBV) at risk for each finding to assist materiality analysis.' }
              ]
            },
            {
              id: 'exceptions',
              title: 'Module 6: 6-Stage Exception Governance Kanban',
              icon: Workflow,
              tab: 'exceptions' as NavTab,
              summary: 'A structured workflow managing exceptions from detection to formal sign-off with an immutable audit trail.',
              keyFeatures: [
                { title: '6-Stage Kanban Board', text: 'Stages: Detected → Assigned → Under Investigation → Management Review → Approved Action → Closed / Written-off.' },
                { title: 'Interactive State Transitions', text: 'Move findings through the pipeline with approver identity, action notes, and resolution evidence.' },
                { title: 'Formal Write-off & Disposal Sign-Off', text: 'Executes approved board write-offs with automatic disposal entries in the subledger.' }
              ]
            },
            {
              id: 'policy',
              title: 'Module 7: Policy Compliance & CARO 2020 Repository',
              icon: FileText,
              tab: 'policy' as NavTab,
              summary: 'Interactive matrix mapping enterprise assets against Indian statutory frameworks and accounting standards.',
              keyFeatures: [
                { title: 'Comprehensive Framework Matrix', text: 'Covers Ind AS 16 (PPE), Companies Act 2013 Sch II, Ind AS 36 (Impairment), Income Tax Act Sec 32, and CARO 2020.' },
                { title: 'CARO 2020 Clause 3(i) Checklist', text: 'Tracks compliance with sub-clauses 3(i)(a) (PPE records), 3(i)(b) (Physical count), 3(i)(c) (Title deeds), and 3(i)(e) (Benami property).' }
              ]
            },
            {
              id: 'audit-readiness',
              title: 'Module 8: Audit Readiness & Executive Memo Generator',
              icon: ClipboardCheck,
              tab: 'audit-readiness' as NavTab,
              summary: 'Automates preparation for Big-4 statutory audits and internal audit committees.',
              keyFeatures: [
                { title: 'AI Audit Memo Synthesizer', text: 'Generates structured audit memoranda with executive summary, CARO observations, and Key Audit Matters.' },
                { title: 'Statutory Deliverables Checklist', text: 'Tracks readiness of Subledger vs GL reconciliation, Componentisation files, and Title deeds dossier.' },
                { title: 'Export Options', text: 'Copy formatted markdown or print directly to PDF for presentation to audit committees.' }
              ]
            },
            {
              id: 'data-studio',
              title: 'Module 9: Data Ingestion & Multi-Entity Studio (Excel, CSV, PDF & Manual)',
              icon: FileText,
              tab: 'data-studio' as NavTab,
              summary: 'Enables custom corporate creation and rapid data ingestion from spreadsheets, vendor invoices, purchase orders, or direct manual registration.',
              keyFeatures: [
                { title: 'Corporate Entity Switcher & Creator', text: 'Create unlimited company profiles with custom CIN, GSTIN, depreciation policies, and operating plant locations.' },
                { title: 'Excel & CSV Subledger Ingestion', text: 'Download official Fixed Asset Register (FAR) templates, validate column structures, and append or overwrite subledger data.' },
                { title: 'PDF & Vendor Invoice AI Vision Parser', text: 'Ingests PDF tax invoices and POs, extracting vendor, gross value, GST ITC breakdown, and Ind AS 16 component lives.' },
                { title: 'Manual Asset & Component Splitter', text: 'Register individual assets with instant dual depreciation preview and 70/30 component accounting split.' }
              ]
            }
          ].map((mod, idx) => {
            const Icon = mod.icon;
            return (
              <div key={idx} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{mod.title}</h3>
                      <p className="text-xs text-slate-500">{mod.summary}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => onNavigateTab(mod.tab)}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center space-x-1 self-start sm:self-auto transition-colors shadow-2xs"
                  >
                    <span>Launch Module</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  {mod.keyFeatures.map((feat, fIdx) => (
                    <div key={fIdx} className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl space-y-1">
                      <h4 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
                        <span>{feat.title}</span>
                      </h4>
                      <p className="text-[11px] text-slate-600 leading-relaxed pl-3">{feat.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* SECTION 3: ROLE-BASED OPERATING PLAYBOOKS */}
      {activeSection === 'roles' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-3">
            <h2 className="text-lg font-bold text-slate-900">
              Role-Based Operating Playbooks & Daily Cadence
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">
              AssetTrust AI supports tailored daily and monthly workflows for each stakeholder in the enterprise fixed asset governance lifecycle:
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Playbook 1: Chief Financial Officer */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 font-bold">
                  CFO
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Chief Financial Officer (CFO)</h3>
                  <span className="text-xs text-blue-600 font-semibold">Executive Assurance & CARO Sign-off</span>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="space-y-1">
                  <span className="font-bold text-slate-900 block">Cadence: Monthly & Quarterly Close</span>
                  <ul className="list-disc list-inside space-y-1.5 text-slate-600 pl-1">
                    <li><strong className="text-slate-800">Review Reliability Score:</strong> Monitor that aggregate score stays ≥ 80% (Clean / High Reliability threshold).</li>
                    <li><strong className="text-slate-800">Financial Exposure Check:</strong> Review total NBV at risk in the Control Tower across critical anomaly classes.</li>
                    <li><strong className="text-slate-800">CARO 2020 Sign-off:</strong> Review Clause 3(i) assurance metrics in the Audit Readiness Center before signing Board financial statements.</li>
                    <li><strong className="text-slate-800">Synthesize Audit Memo:</strong> Generate the executive AI memorandum for presentation to the statutory Audit Committee.</li>
                  </ul>
                </div>
                <button
                  onClick={() => onNavigateTab('control-tower')}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-xs transition-colors border border-slate-200 flex items-center justify-center space-x-1"
                >
                  <span>Open Executive Control Tower</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Playbook 2: Financial Controller */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold">
                  FC
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Financial Controller / Accounting Lead</h3>
                  <span className="text-xs text-emerald-600 font-semibold">Capitalisation & Subledger Integrity</span>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="space-y-1">
                  <span className="font-bold text-slate-900 block">Cadence: Daily / Weekly</span>
                  <ul className="list-disc list-inside space-y-1.5 text-slate-600 pl-1">
                    <li><strong className="text-slate-800">Clear Capex Ingestion Queue:</strong> Process inbound Capex items in <em className="text-blue-700">AI Capex Review</em>, validating Ind AS 16 component splits and GST ITC claims.</li>
                    <li><strong className="text-slate-800">Reconcile Dual Books:</strong> Verify that Book Depreciation (Sch II SLM) and Tax Depreciation (IT Act Sec 32 WDV) match General Ledger accounts.</li>
                    <li><strong className="text-slate-800">Exception Resolution:</strong> Advance findings in the <em className="text-blue-700">Exceptions Workflow</em> from "Investigating" to "Management Review".</li>
                    <li><strong className="text-slate-800">Authorize Disposals:</strong> Sign off on disposal and scrap adjustments with proper accounting treatment.</li>
                  </ul>
                </div>
                <button
                  onClick={() => onNavigateTab('capex-review')}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-xs transition-colors border border-slate-200 flex items-center justify-center space-x-1"
                >
                  <span>Open AI Capex Review</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Playbook 3: Statutory & Internal Auditor */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
                <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 font-bold">
                  AUD
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Internal & Statutory Auditor</h3>
                  <span className="text-xs text-amber-600 font-semibold">Testing, 3-Way Match & CARO Audit</span>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="space-y-1">
                  <span className="font-bold text-slate-900 block">Cadence: Interim & Year-End Audit Cycles</span>
                  <ul className="list-disc list-inside space-y-1.5 text-slate-600 pl-1">
                    <li><strong className="text-slate-800">Sample Subledger Entries:</strong> Filter Asset Register by high NBV and inspect 3-way match documents (PO, GRN, Tax Invoices).</li>
                    <li><strong className="text-slate-800">Review Physical Count Discrepancies:</strong> Verify whether aggregate variances in any asset class exceed the CARO 10% threshold.</li>
                    <li><strong className="text-slate-800">Audit Subledger-to-GL Tie-Out:</strong> Review mathematical reconciliation in the Audit Readiness pack.</li>
                    <li><strong className="text-slate-800">Verify Impairment Indicators:</strong> Inspect Ind AS 36 assessment sheets for idle or under-utilized plant lines.</li>
                  </ul>
                </div>
                <button
                  onClick={() => onNavigateTab('audit-readiness')}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-xs transition-colors border border-slate-200 flex items-center justify-center space-x-1"
                >
                  <span>Open Audit Readiness Center</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Playbook 4: Plant Controller & Shop Floor Lead */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
                <div className="w-10 h-10 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700 font-bold">
                  OPS
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Plant Custodian & Field Engineer</h3>
                  <span className="text-xs text-purple-600 font-semibold">QR Tagging & Field Count Ops</span>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="space-y-1">
                  <span className="font-bold text-slate-900 block">Cadence: Ongoing Physical Counts</span>
                  <ul className="list-disc list-inside space-y-1.5 text-slate-600 pl-1">
                    <li><strong className="text-slate-800">Scan QR Tags on Equipment:</strong> Use the Verification Ops terminal to scan assets during scheduled shop-floor rounds.</li>
                    <li><strong className="text-slate-800">Validate Physical Nameplates:</strong> Check OEM serial numbers against digital register records.</li>
                    <li><strong className="text-slate-800">Log Asset Transfers:</strong> Record inter-bay and inter-plant equipment transfers to prevent location drift exceptions.</li>
                    <li><strong className="text-slate-800">Report Damaged Tags:</strong> Request QR matrix re-tagging directly from the mobile interface.</li>
                  </ul>
                </div>
                <button
                  onClick={() => onNavigateTab('physical-verification')}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-xs transition-colors border border-slate-200 flex items-center justify-center space-x-1"
                >
                  <span>Open Verification Ops Terminal</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: STATUTORY & ACCOUNTING GUIDELINES */}
      {activeSection === 'statutory' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-3">
            <h2 className="text-lg font-bold text-slate-900">
              Statutory Accounting Standard & Regulatory Rulebook
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">
              Summary of regulatory standards hardcoded into AssetTrust AI's deterministic governance engine:
            </p>
          </div>

          <div className="space-y-4">
            {[
              {
                standard: 'Ind AS 16',
                title: 'Property, Plant & Equipment (PPE) — Paragraphs 7, 43, 44 & 51',
                keyMandate: 'Initial capitalisation criteria requires probable future economic benefits and reliable cost measurement. Para 43 mandates separate depreciation for each significant sub-component. Para 51 requires annual review of useful life and residual values.',
                appImplementation: 'AI Capex Review performs automated line-item componentisation splits and allocates distinct useful lives with full audit documentation.'
              },
              {
                standard: 'Companies Act 2013',
                title: 'Schedule II — Useful Lives for Depreciating Assets',
                keyMandate: 'Prescribes mandatory standard useful lives (e.g. General Plant & Machinery: 15 years, IT Equipment: 3–6 years, Buildings: 30–60 years). If a company uses a different useful life, technical justification must be disclosed in notes.',
                appImplementation: 'Every asset subledger record calculates Book Depreciation on Schedule II benchmark lives while flagging any variance in company-adopted life.'
              },
              {
                standard: 'CARO 2020',
                title: 'Clause 3(i) — Statutory Auditor Reporting Requirements on PPE',
                keyMandate: 'Auditors must specifically report on: (a) Maintenance of proper records, (b) Regular physical verification and treatment of discrepancies exceeding 10%, (c) Holding of title deeds for immovable property in company name, and (e) Benami property proceedings.',
                appImplementation: 'Automated CARO 2020 readiness scoring, title deed tracking, 10% discrepancy thresholds, and exportable audit packs.'
              },
              {
                standard: 'Income Tax Act 1961',
                title: 'Section 32 — Tax Depreciation & Block of Assets',
                keyMandate: 'Depreciation for tax purposes is computed on the Written Down Value (WDV) of asset blocks (e.g. Plant: 15%, Computers: 40%). Assets put to use for less than 180 days in the year receive 50% of the normal depreciation rate.',
                appImplementation: 'Dual-book depreciation engine calculates both Companies Act SLM and Income Tax Sec 32 WDV simultaneously for every asset.'
              },
              {
                standard: 'CGST Act 2017',
                title: 'Section 17(5) — Apportionment of Credit & Blocked Credits',
                keyMandate: 'Input Tax Credit (ITC) is blocked on capital goods used for construction of immovable property (other than plant & machinery) and certain motor vehicles.',
                appImplementation: 'AI Capex Review scans procurement descriptions and marks GST ITC as Eligible or Blocked before capitalisation.'
              },
              {
                standard: 'Ind AS 36',
                title: 'Impairment of Assets — Paragraphs 9 & 12',
                keyMandate: 'An entity must assess at the end of each reporting period whether there is any indication that an asset may be impaired (idle status, obsolescence, damage, or technological shifts).',
                appImplementation: 'The Risk Radar continuously flags idle, unutilized, or physically damaged assets as candidate impairment triggers.'
              }
            ].map((rule, idx) => (
              <div key={idx} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-2 border-b border-slate-100">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                      {rule.standard}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">{rule.title}</h3>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl space-y-1">
                    <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider block">
                      Statutory Rule & Mandate
                    </span>
                    <p className="text-slate-600 leading-relaxed">{rule.keyMandate}</p>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl space-y-1">
                    <span className="font-bold text-blue-800 text-[11px] uppercase tracking-wider block">
                      AssetTrust AI Implementation
                    </span>
                    <p className="text-slate-600 leading-relaxed">{rule.appImplementation}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 5: FAQ & TROUBLESHOOTING */}
      {activeSection === 'faq' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-3">
            <h2 className="text-lg font-bold text-slate-900">
              Frequently Asked Questions & Operational Troubleshooting
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">
              Quick answers to common questions about fixed asset governance, componentisation, CARO compliance, and platform operations.
            </p>
          </div>

          <div className="space-y-3">
            {filteredFaqs.map((faq, idx) => {
              const isOpen = expandedFaq === idx;
              return (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs transition-all"
                >
                  <button
                    onClick={() => setExpandedFaq(isOpen ? null : idx)}
                    className="w-full p-4 text-left flex items-center justify-between gap-3 hover:bg-slate-50/80 transition-colors"
                  >
                    <span className="text-xs font-bold text-slate-900 flex items-center space-x-2">
                      <HelpCircle className="w-4 h-4 text-blue-600 shrink-0" />
                      <span>{faq.q}</span>
                    </span>
                    <span className={`text-xs font-bold text-slate-400 transition-transform ${isOpen ? 'rotate-90' : ''}`}>
                      →
                    </span>
                  </button>

                  {isOpen && (
                    <div className="p-4 pt-0 text-xs text-slate-600 leading-relaxed border-t border-slate-100 bg-slate-50/50">
                      <p className="pt-2">{faq.a}</p>
                    </div>
                  )}
                </div>
              );
            })}

            {filteredFaqs.length === 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-500">
                No matching FAQ items found for "{searchQuery}". Try searching for terms like "CARO", "Componentisation", "Depreciation", or "QR".
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer Support Banner */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-blue-400 text-xs font-bold uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4" />
            <span>Need Custom Assistance or Statutory Guidance?</span>
          </div>
          <h3 className="text-base font-bold tracking-tight text-white">
            AssetTrust AI Continuous Assurance Support
          </h3>
          <p className="text-xs text-slate-400">
            For specific queries regarding Ind AS 16 componentisation splits or CARO 2020 reporting, contact your internal Audit Committee liaison.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={() => onNavigateTab('control-tower')}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs"
          >
            Back to Control Tower
          </button>
        </div>
      </div>
    </div>
  );
};
