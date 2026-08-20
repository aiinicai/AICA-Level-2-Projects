import React, { useState } from 'react';
import {
  X,
  BookOpen,
  FileText,
  Files,
  Users,
  TrendingUp,
  Sliders,
  ShieldCheck,
  Package,
  CreditCard,
  UserCheck,
  CheckCircle2,
  Terminal,
  Building2,
  Key,
  Download,
  FileCheck,
  Compass
} from 'lucide-react';
import { UserRole } from '../../types';

interface GettingStartedModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GettingStartedModal: React.FC<GettingStartedModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'admin' | 'finance' | 'operations' | 'procurement' | 'client_portal' | 'system'>('admin');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <div>
              <h3 className="font-semibold text-base">Multi-Tenant Platform — Getting Started & Role Guides</h3>
              <p className="text-xs text-slate-400">Standard operating procedures, role permissions, and client portal manual</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2 shrink-0 overflow-x-auto">
          <button
            onClick={() => setActiveTab('admin')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'admin'
                ? 'border-purple-600 text-purple-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-purple-600" />
            <span>Admin Guide</span>
          </button>

          <button
            onClick={() => setActiveTab('finance')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'finance'
                ? 'border-amber-600 text-amber-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5 text-amber-600" />
            <span>Finance Guide</span>
          </button>

          <button
            onClick={() => setActiveTab('operations')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'operations'
                ? 'border-blue-600 text-blue-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            <span>Operations Guide</span>
          </button>

          <button
            onClick={() => setActiveTab('procurement')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'procurement'
                ? 'border-cyan-600 text-cyan-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Package className="w-3.5 h-3.5 text-cyan-600" />
            <span>Procurement Guide</span>
          </button>

          <button
            onClick={() => setActiveTab('client_portal')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'client_portal'
                ? 'border-emerald-600 text-emerald-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Client Portal (1-Page Guide)</span>
          </button>

          <button
            onClick={() => setActiveTab('system')}
            className={`px-3.5 py-2 text-xs font-bold rounded-t-lg border-b-2 transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'system'
                ? 'border-slate-800 text-slate-900 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Compass className="w-3.5 h-3.5 text-slate-600" />
            <span>System Architecture</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-700 text-xs leading-relaxed">
          {/* TAB 1: ADMIN GUIDE */}
          {activeTab === 'admin' && (
            <div className="space-y-4">
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-purple-950 font-bold text-sm">
                  <Sliders className="w-4 h-4 text-purple-700" />
                  <span>Administrator Role & Governance Overview</span>
                </div>
                <p className="text-purple-900 text-xs">
                  As the Company Admin, you hold full root permissions across your company tenant. Your primary responsibilities include tenant branding, inviting staff/clients via your unique <strong>Company Code</strong>, reviewing the pending sign-up queue, maintaining the product catalog & VAT rules, and auditing payment trends.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <Key className="w-4 h-4 text-purple-600" />
                    <span>1. Company Code & User Onboarding</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Distribute your unique <strong>Company Code</strong> (e.g. <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-purple-800">KILI-7890</code>) to staff and clients. When they submit a sign-up request, navigate to <strong>Pending Sign-ups</strong> to review, approve, or reject applicants with audit email notifications.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <Building2 className="w-4 h-4 text-purple-600" />
                    <span>2. Branding, Seals & Bank Accounts</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    In <strong>Company & Branding</strong>, upload high-resolution transparent PNG logos, official company seals, and authorized signatures. Configure your primary/secondary brand palette to automatically customize invoice headers and PDF exports.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <Package className="w-4 h-4 text-purple-600" />
                    <span>3. Product Master & VAT Taxation</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Open <strong>Manage Products</strong> to define your company's full goods and services catalog. Configure TRA VAT rules (Non-vatable 0%, Standard-rated 18%, or per-line optional toggle) and active inventory status.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <CreditCard className="w-4 h-4 text-purple-600" />
                    <span>4. Credit Limits & Payment Trends</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Monitor company-wide Days-to-Pay (vs. 21-day benchmark) and aging overdue debts in <strong>Payment Trends</strong>. Record settlements and audit customer credit limit utilization.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: FINANCE GUIDE */}
          {activeTab === 'finance' && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-amber-950 font-bold text-sm">
                  <CreditCard className="w-4 h-4 text-amber-700" />
                  <span>Finance Role Overview & Cash Flow Management</span>
                </div>
                <p className="text-amber-900 text-xs">
                  Finance users have <strong>full operational access</strong> across all business modules: Vouchers (all document types), Clientele CRM, Payment Trend analytics, PDF Toolkit, and Global Intelligence. The only screen reserved exclusively for Admins is Company Branding Settings.
                </p>
              </div>

              <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                <h4 className="font-bold text-slate-900 text-xs">Key Finance Workflows</h4>
                <ul className="space-y-2 pl-4 list-disc text-slate-600">
                  <li><strong>Multi-Currency Tax Invoices</strong>: Create and finalize Sales Invoices in TZS, USD, INR, CNY, ZAR, GBP, and EUR with automatic legal spelled-out amounts in words and recorded exchange rates.</li>
                  <li><strong>Payment Trend Analytics</strong>: Analyze Days-to-Pay metrics, flag accounts exceeding credit terms, and record customer payments directly against finalized vouchers.</li>
                  <li><strong>Client KYC & Credit Days</strong>: Audit customer credit applications, view uploaded TIN & bank certificates, and manage credit limit ceilings in Clientele.</li>
                  <li><strong>Proforma Validity Expiration</strong>: Manage 3 to 10-day validity periods on Proforma Invoices with automated expiration tracking.</li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 3: OPERATIONS GUIDE */}
          {activeTab === 'operations' && (
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-blue-950 font-bold text-sm">
                  <FileText className="w-4 h-4 text-blue-700" />
                  <span>Operations Role & Order Fulfillment</span>
                </div>
                <p className="text-blue-900 text-xs">
                  Operations staff handle customer-facing documentation, order fulfillment, and client relationship management. Operations has full access to create/manage Proforma Invoices, Sales Invoices, Local Purchase Orders (LPO), and Delivery Notes, plus full Clientele CRM access.
                </p>
              </div>

              <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                <h4 className="font-bold text-slate-900 text-xs">Key Operations Responsibilities</h4>
                <ul className="space-y-2 pl-4 list-disc text-slate-600">
                  <li><strong>Mandatory KYC Onboarding</strong>: Add new clients through the 7-document regulatory verification checklist (TIN, Bank Letter, Shareholder ID, BRELA, Business License, EWURA, Incorporation Certificate).</li>
                  <li><strong>Order Conversion</strong>: Convert finalized Proformas into Tax Invoices or Delivery Notes with one click, preserving line items and auto-generating consecutive numbering.</li>
                  <li><strong>Repeat Order Cadence</strong>: Monitor customer reorder cycles on the Home Dashboard and engage overdue accounts to prevent competitor volume leakage.</li>
                  <li><strong>AI Sales Gap Insights</strong>: Review Gemini-powered recommendations comparing client stated monthly demand against actual delivery tonnage.</li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 4: PROCUREMENT GUIDE */}
          {activeTab === 'procurement' && (
            <div className="space-y-4">
              <div className="p-4 bg-cyan-50 border border-cyan-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-cyan-950 font-bold text-sm">
                  <Package className="w-4 h-4 text-cyan-700" />
                  <span>Procurement Role — Purchase Orders & Sourcing</span>
                </div>
                <p className="text-cyan-900 text-xs">
                  Procurement users focus strictly on supplier purchasing and global commodity benchmarks. The Procurement role has access to <strong>Purchase Orders (PO) only</strong> within the voucher module, plus full access to the PDF Toolkit and Global Intelligence.
                </p>
              </div>

              <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                <h4 className="font-bold text-slate-900 text-xs">Key Procurement Capabilities</h4>
                <ul className="space-y-2 pl-4 list-disc text-slate-600">
                  <li><strong>Vendor Purchase Orders (PO)</strong>: Issue professional, TRA-compliant POs to refinery suppliers, equipment lessors, and transport hauliers.</li>
                  <li><strong>Inline Product Creation</strong>: Add new specialized materials or spare parts directly inside the voucher line item dropdown via "+ Add New Product".</li>
                  <li><strong>Global Market Tracking</strong>: Monitor live Brent crude prices, bulk Bitumen 60/70 CFR Dar es Salaam rates, USD/TZS exchange rates, and Dar Port corridor dwell times.</li>
                  <li><strong>PDF Toolkit</strong>: Full vector merge, document split, password decryption, and Word/Excel conversion of supplier quotes.</li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 5: CLIENT PORTAL GUIDE (1-PAGE MANUAL) */}
          {activeTab === 'client_portal' && (
            <div className="space-y-4">
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-emerald-950 font-bold text-sm">
                  <ShieldCheck className="w-4 h-4 text-emerald-700" />
                  <span>Client Portal — 1-Page User Manual</span>
                </div>
                <p className="text-emerald-900 text-xs">
                  Welcome to your secure customer account portal. As an approved client, your login is strictly scoped to your organization's own finalized tax invoices, delivery notes, and proformas, with full access to the self-service PDF Toolkit.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <FileCheck className="w-4 h-4 text-emerald-600" />
                    <span>1. Invoices & Order History</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    View, search, and download your finalized Tax Invoices, Delivery Notes, and active Proforma Invoices with high-resolution PDF generation, stamped seals, and authorized signatures.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <Files className="w-4 h-4 text-emerald-600" />
                    <span>2. Full PDF & Image Toolkit</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Every client receives unrestricted access to the PDF Toolkit. Merge shipping documents, split contracts, compress large scans, convert PDFs to Word/Excel spreadsheets, and decrypt password-protected files in your browser.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <Download className="w-4 h-4 text-emerald-600" />
                    <span>3. KYC Records & Compliance</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Review and download your registered compliance documents on file (TIN Certificate, BRELA Incorporation, Business License, EWURA Permit) for your own accounting audits.
                  </p>
                </div>

                <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                  <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>4. Data Privacy & Isolation</span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Your session is isolated under enterprise encryption. You only see records issued to your company ID with zero access to internal CRM or other client accounts.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: SYSTEM ARCHITECTURE */}
          {activeTab === 'system' && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-900 text-slate-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-white font-bold text-sm">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  <span>Cloud Multi-Tenant & Desktop Architecture</span>
                </div>
                <p className="text-slate-300 text-xs">
                  The platform operates on a multi-tenant data architecture where every database entity carries a strict <code className="bg-slate-800 px-1 py-0.5 rounded text-emerald-400 font-mono">companyId</code> scoped at the query layer.
                </p>
              </div>

              <div className="border border-slate-200 rounded-lg p-4 space-y-2 bg-white">
                <h4 className="font-bold text-slate-900 text-xs">Architecture Specifications</h4>
                <ul className="space-y-2 pl-4 list-disc text-slate-600">
                  <li><strong>Multi-Tenant Data Isolation</strong>: Enforced at the data query layer so no user or API can access records from another company tenant.</li>
                  <li><strong>AI Narrative Layer</strong>: Gemini 3.7 Flash integration with Google Search grounding for real-time market indicators and B2B sales strategy generation.</li>
                  <li><strong>PDF Engine</strong>: Client-side vector manipulation with real text/table tokenization for lossless document conversions.</li>
                  <li><strong>Electron Desktop Shell</strong>: Supports packaging as an installable Windows/macOS desktop application pointing to the centralized cloud backend.</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded text-xs font-semibold transition"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};
