import React, { useState, useEffect } from 'react';
import { AppSettings, Purchase, RateRecord, RateCorrection, ImportBatch } from '../../types';
import {
  getSupabaseConfig,
  setSupabaseConfig,
  isSupabaseConfigured,
  isUserSuperUser,
  SUPERUSER_EMAIL,
} from '../../services/supabaseClient';
import {
  testSupabaseConnection,
} from '../../db/supabaseRepository';
import {
  syncLocalDataToSupabase,
  uploadRatesToSupabase,
} from '../../db/repository';
import {
  Settings,
  Download,
  Upload,
  Coins,
  Shield,
  Layers,
  Sparkles,
  HelpCircle,
  Database,
  Radio,
  Trash2,
  FolderOpen,
  CheckCircle2,
  FileCode,
  Smartphone,
  Server,
  Cloud,
  Lock,
  LogOut,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  LineChart,
} from 'lucide-react';

interface SettingsScreenProps {
  settings: AppSettings;
  onUpdateSettings: (settings: AppSettings) => void;
  onExportBackup: () => void;
  onRestoreBackup: (file: File) => void;
  onLoadDemoData: () => void;
  onClearAllPurchases: () => void;
  purchasesCount: number;
  ratesCount: number;
  currentUser?: { email?: string } | null;
  onOpenAuthModal?: () => void;
  onSignOut?: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  settings,
  onUpdateSettings,
  onExportBackup,
  onRestoreBackup,
  onLoadDemoData,
  onClearAllPurchases,
  purchasesCount,
  ratesCount,
  currentUser,
  onOpenAuthModal,
  onSignOut,
}) => {
  const [goldMarkdown, setGoldMarkdown] = useState(settings.goldMarkdownPct.toString());
  const [silverMarkdown, setSilverMarkdown] = useState(settings.silverMarkdownPct.toString());
  const [confirmTax, setConfirmTax] = useState(settings.confirmTaxTreatment);
  const [confirmSession, setConfirmSession] = useState(settings.confirmSession);
  const [isSavedNotice, setIsSavedNotice] = useState(false);

  // Supabase connection configuration state
  const currentSupabase = getSupabaseConfig();
  const [supabaseUrl, setSupabaseUrl] = useState(currentSupabase.url);
  const [supabaseAnonKey, setSupabaseAnonKey] = useState(currentSupabase.anonKey);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [isUploadingRates, setIsUploadingRates] = useState(false);
  const [ratesSyncResult, setRatesSyncResult] = useState<string | null>(null);
  const [showSqlSchema, setShowSqlSchema] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  const handleUploadRates = async () => {
    setIsUploadingRates(true);
    setRatesSyncResult(null);
    try {
      const res = await uploadRatesToSupabase();
      setRatesSyncResult(res.message);
    } catch (err: any) {
      setRatesSyncResult(`Rates upload failed: ${err.message}`);
    } finally {
      setIsUploadingRates(false);
    }
  };

  const isSuperUser = isUserSuperUser(currentUser);
  const isOtherUser = !!currentUser && !isSuperUser;
  const isCloudConnected = isSupabaseConfigured();

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    const gMd = parseFloat(goldMarkdown) || 0;
    const sMd = parseFloat(silverMarkdown) || 0;

    const updated: AppSettings = {
      ...settings,
      goldMarkdownPct: Math.max(0, Math.min(100, gMd)),
      silverMarkdownPct: Math.max(0, Math.min(100, sMd)),
      confirmTaxTreatment: confirmTax,
      confirmSession: confirmSession,
    };

    onUpdateSettings(updated);
    setIsSavedNotice(true);
    setTimeout(() => setIsSavedNotice(false), 3000);
  };

  const handleSaveSupabaseConfig = () => {
    setSupabaseConfig(supabaseUrl, supabaseAnonKey);
    if (supabaseUrl && supabaseAnonKey) {
      fetch('/api/save-env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: supabaseUrl, anonKey: supabaseAnonKey }),
      }).catch(console.warn);
    }
    setTestResult({
      success: true,
      message: 'Supabase configuration saved! Testing connection...',
    });
    handleTestConnection();
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testSupabaseConnection();
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSyncToSupabase = async () => {
    const config = getSupabaseConfig();
    if (!config.isConfigured && (!supabaseUrl.trim() || !supabaseAnonKey.trim())) {
      setSyncResult(
        '⚠️ Supabase Connection Required: Please enter your Supabase Project URL and Anon Key in the fields below and click "Save Credentials" first, then click Upload.'
      );
      const urlInput = document.getElementById('supabase-url-input');
      if (urlInput) {
        urlInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        urlInput.focus();
      }
      return;
    }

    // If user filled in the fields but didn't click save yet, auto-save first
    if (!config.isConfigured && supabaseUrl.trim() && supabaseAnonKey.trim()) {
      setSupabaseConfig(supabaseUrl.trim(), supabaseAnonKey.trim());
    }

    setIsSyncing(true);
    setSyncResult(null);
    try {
      const res = await syncLocalDataToSupabase();
      setSyncResult(res.message);
      if (res.success) {
        handleTestConnection();
      }
    } catch (err: any) {
      setSyncResult(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handlePurgeCacheAndReload = async () => {
    try {
      if ('caches' in window) {
        const keys = await caches.keys();
        for (const key of keys) {
          await caches.delete(key);
        }
      }
      if ('serviceWorker' in navigator) {
        const regs = await navigator.serviceWorker.getRegistrations();
        for (const reg of regs) {
          await reg.unregister();
        }
      }
    } catch (e) {
      console.warn('Cache purge error:', e);
    }
    window.location.reload();
  };

  const handleCopySql = () => {
    const sql = `-- =========================================================================
-- BULLION LEDGER - SUPABASE DATABASE SCHEMA & ROW LEVEL SECURITY (RLS)
-- Run this in your Supabase SQL Editor:
-- =========================================================================

-- 1. Purchases table
CREATE TABLE IF NOT EXISTS public.purchases (
    id TEXT PRIMARY KEY,
    purchase_date DATE NOT NULL,
    seller TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    form TEXT NOT NULL CHECK (form IN ('VEDHANI', 'COIN', 'BAR')),
    purity NUMERIC NOT NULL CHECK (purity > 0),
    weight_grams NUMERIC NOT NULL CHECK (weight_grams > 0),
    purchase_rate NUMERIC NOT NULL CHECK (purchase_rate > 0),
    taxes_paid NUMERIC NOT NULL DEFAULT 0,
    other_charges NUMERIC NOT NULL DEFAULT 0,
    notes TEXT,
    bullion_value NUMERIC NOT NULL,
    invested_amount NUMERIC NOT NULL,
    batch_id TEXT,
    is_demo BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Rates table (institutional benchmarks)
CREATE TABLE IF NOT EXISTS public.rates (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    purity NUMERIC NOT NULL,
    price_per_gram NUMERIC NOT NULL CHECK (price_per_gram > 0),
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    original_unit TEXT NOT NULL,
    original_price NUMERIC NOT NULL,
    session TEXT DEFAULT 'PM',
    gst_included BOOLEAN DEFAULT FALSE,
    notes TEXT,
    provenance TEXT NOT NULL,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. App Settings table
CREATE TABLE IF NOT EXISTS public.app_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    gold_markdown_pct NUMERIC NOT NULL DEFAULT 3.0,
    silver_markdown_pct NUMERIC NOT NULL DEFAULT 3.0,
    rate_provider_enabled BOOLEAN DEFAULT FALSE,
    rate_provider_name TEXT DEFAULT 'IBJA Official Benchmark (Free Daily PM Source)',
    confirm_tax_treatment TEXT DEFAULT 'UNCONFIRMED',
    confirm_session TEXT DEFAULT 'UNSPECIFIED',
    last_api_check TIMESTAMPTZ,
    last_successful_update TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO public.app_settings (id, gold_markdown_pct, silver_markdown_pct) VALUES ('default', 3.0, 3.0) ON CONFLICT (id) DO NOTHING;

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;

-- 5. Drop policies if re-running
DROP POLICY IF EXISTS "Public Read Purchases" ON public.purchases;
DROP POLICY IF EXISTS "Superuser Modify Purchases" ON public.purchases;
DROP POLICY IF EXISTS "Allow Initial Ledger Upload" ON public.purchases;

DROP POLICY IF EXISTS "Public Read Rates" ON public.rates;
DROP POLICY IF EXISTS "Superuser Modify Rates" ON public.rates;
DROP POLICY IF EXISTS "Allow Initial Rates Upload" ON public.rates;

DROP POLICY IF EXISTS "Public Read Settings" ON public.app_settings;
DROP POLICY IF EXISTS "Superuser Modify Settings" ON public.app_settings;
DROP POLICY IF EXISTS "Allow Initial Settings Upload" ON public.app_settings;

-- 6. Recreate Policies
CREATE POLICY "Public Read Purchases" ON public.purchases FOR SELECT TO public USING (true);
CREATE POLICY "Superuser Modify Purchases" ON public.purchases FOR ALL TO authenticated USING (auth.jwt() ->> 'email' = 'kosamgo@gmail.com') WITH CHECK (auth.jwt() ->> 'email' = 'kosamgo@gmail.com');
CREATE POLICY "Allow Initial Ledger Upload" ON public.purchases FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Public Read Rates" ON public.rates FOR SELECT TO public USING (true);
CREATE POLICY "Superuser Modify Rates" ON public.rates FOR ALL TO authenticated USING (auth.jwt() ->> 'email' = 'kosamgo@gmail.com') WITH CHECK (auth.jwt() ->> 'email' = 'kosamgo@gmail.com');
CREATE POLICY "Allow Initial Rates Upload" ON public.rates FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Public Read Settings" ON public.app_settings FOR SELECT TO public USING (true);
CREATE POLICY "Superuser Modify Settings" ON public.app_settings FOR ALL TO authenticated USING (auth.jwt() ->> 'email' = 'kosamgo@gmail.com') WITH CHECK (auth.jwt() ->> 'email' = 'kosamgo@gmail.com');
CREATE POLICY "Allow Initial Settings Upload" ON public.app_settings FOR ALL TO anon USING (true) WITH CHECK (true);`;

    navigator.clipboard.writeText(sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2500);
  };

  const handleFileRestore = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (
        confirm(
          'Restoring from a backup will merge and update your current purchases and settings. Proceed?'
        )
      ) {
        onRestoreBackup(file);
      }
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-stone-900 tracking-tight flex items-center gap-2">
          <span>Settings, Supabase Cloud & Valuation Assumptions</span>
        </h2>
        <p className="text-xs text-stone-500">
          Configure cloud database synchronization, Super User authentication, resale liquidity haircuts, and backups
        </p>
      </div>

      {isSavedNotice && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-lg text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Settings saved. Valuation calculations have been updated with your new markdown parameters.</span>
        </div>
      )}

      {/* Supabase Cloud Database & Access Control Panel */}
      <div className="bg-white rounded-xl p-5 border border-[#D4AF37]/50 shadow-xs space-y-4">
        <div className="border-b border-stone-100 pb-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-stone-900 flex items-center gap-2">
              <Cloud className="w-4 h-4 text-[#B88B2A]" />
              Supabase Cloud Database & Public Access Control
            </h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Multi-device persistent cloud storage with public read-only views and Google OAuth for Super User write access.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
                isCloudConnected
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isCloudConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              />
              {isCloudConnected ? 'Connected to Cloud' : 'Offline / Local Mode'}
            </span>
          </div>
        </div>

        {/* Access Role & Auth Card */}
        <div className="bg-[#FAF7F2] p-3.5 rounded-lg border border-[#D4AF37]/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500 block">
              Active Access Role
            </span>
            <div className="flex items-center gap-2">
              {isSuperUser ? (
                <>
                  <span className="font-bold text-stone-900 flex items-center gap-1.5 text-xs">
                    <span className="text-amber-600">👑</span> Super User: {SUPERUSER_EMAIL}
                  </span>
                  <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold">
                    Full Write Access
                  </span>
                </>
              ) : isOtherUser ? (
                <>
                  <span className="font-bold text-rose-700 text-xs flex items-center gap-1.5">
                    <span>⚠️</span> User: {currentUser.email}
                  </span>
                  <span className="text-[10px] bg-rose-100 text-rose-800 px-2 py-0.5 rounded font-semibold">
                    Restricted (Read-Only)
                  </span>
                </>
              ) : (
                <>
                  <span className="font-bold text-stone-700 text-xs flex items-center gap-1.5">
                    <span>👁️</span> Public Guest (External Viewer)
                  </span>
                  <span className="text-[10px] bg-stone-100 text-stone-600 px-2 py-0.5 rounded font-semibold">
                    Read-Only
                  </span>
                </>
              )}
            </div>
            <p className="text-[11px] text-stone-500">
              {isSuperUser
                ? `You are logged in as the designated portfolio owner (${SUPERUSER_EMAIL}) with full cloud write permissions.`
                : isOtherUser
                ? `Super User privileges are reserved exclusively for ${SUPERUSER_EMAIL}. Your current session has read-only access.`
                : `External users viewing your link see all stored transactions and live valuations without login. Super User (${SUPERUSER_EMAIL}) can sign in to make edits.`}
            </p>
          </div>

          <div>
            {currentUser ? (
              <button
                type="button"
                onClick={onSignOut}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-stone-700 bg-white hover:bg-stone-100 border border-stone-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5 text-stone-500" />
                <span>Sign Out</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onOpenAuthModal}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] rounded-lg shadow-2xs transition-colors cursor-pointer"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Super User Sign In</span>
              </button>
            )}
          </div>
        </div>

        {/* 1-Click Cloud Sync Hero Box - Prominently Displayed */}
        <div className="bg-gradient-to-r from-emerald-50 via-teal-50/60 to-amber-50/40 border-2 border-emerald-500/60 rounded-xl p-4 sm:p-5 shadow-xs space-y-3">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-emerald-950 flex items-center gap-1.5">
                  <Upload className="w-4 h-4 text-emerald-700" />
                  Cloud Database Migration: Sync to Supabase
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 uppercase tracking-wider">
                  Direct Migration
                </span>
              </div>
              <p className="text-xs text-stone-600 max-w-xl">
                Upload your local browser data (<strong>{purchasesCount} purchase lots</strong>) and institutional benchmark price archive (<strong>{ratesCount.toLocaleString('en-IN')} rates</strong>) directly to Supabase cloud PostgreSQL. Once uploaded, anyone with your link can view the portfolio from any device without logging in.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 shrink-0 w-full md:w-auto">
              <button
                type="button"
                id="push-to-supabase-main-btn"
                onClick={handleSyncToSupabase}
                disabled={isSyncing}
                className={`px-4 py-2.5 rounded-lg text-xs font-bold text-white shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  isCloudConnected
                    ? 'bg-emerald-600 hover:bg-emerald-700 hover:shadow-md'
                    : 'bg-[#B88B2A] hover:bg-[#8E6B1D]'
                }`}
                title="Upload local purchase transactions and valuation settings to Supabase"
              >
                <Upload className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Uploading Purchases...' : '1-Click Upload Purchases'}</span>
              </button>

              <button
                type="button"
                id="push-rates-to-supabase-main-btn"
                onClick={handleUploadRates}
                disabled={isUploadingRates}
                className={`px-4 py-2.5 rounded-lg text-xs font-bold text-white shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  isCloudConnected
                    ? 'bg-teal-700 hover:bg-teal-800 hover:shadow-md'
                    : 'bg-stone-700 hover:bg-stone-800'
                }`}
                title="Upload all 5,666 historical price records (Gold 995/999 & Silver 999) to Supabase cloud"
              >
                <LineChart className={`w-4 h-4 ${isUploadingRates ? 'animate-spin' : ''}`} />
                <span>{isUploadingRates ? 'Uploading 5,666 Rates...' : 'Push 5,666 Rates to Supabase'}</span>
              </button>
            </div>
          </div>

          {!isCloudConnected && (
            <div className="text-[11px] text-amber-800 bg-amber-50/90 border border-amber-200 px-3 py-1.5 rounded-md flex items-center gap-1.5">
              <span>💡 <strong>Quick Step:</strong> Enter your Supabase Project URL & Anon Key below, click <strong>Save Credentials</strong>, then click the buttons above to push your local ledger and rates.</span>
            </div>
          )}
        </div>

        {/* Supabase URL & Anon Key Settings */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <label className="block text-stone-700 font-semibold mb-1" htmlFor="supabase-url-input">
              Supabase Project URL
            </label>
            <input
              id="supabase-url-input"
              type="text"
              value={supabaseUrl}
              onChange={(e) => setSupabaseUrl(e.target.value)}
              placeholder="https://your-project-id.supabase.co"
              className="w-full px-3 py-1.5 border border-stone-300 rounded-lg font-mono text-xs focus:ring-1 focus:ring-[#B88B2A]"
            />
            <span className="text-[10px] text-stone-400 mt-0.5 block">
              Found in Supabase Console → Project Settings → API
            </span>
          </div>

          <div>
            <label className="block text-stone-700 font-semibold mb-1" htmlFor="supabase-anon-key-input">
              Supabase Anon Key (Public)
            </label>
            <input
              id="supabase-anon-key-input"
              type="password"
              value={supabaseAnonKey}
              onChange={(e) => setSupabaseAnonKey(e.target.value)}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6..."
              className="w-full px-3 py-1.5 border border-stone-300 rounded-lg font-mono text-xs focus:ring-1 focus:ring-[#B88B2A]"
            />
            <span className="text-[10px] text-stone-400 mt-0.5 block">
              Found in Supabase Console → Project Settings → API (anon public)
            </span>
          </div>
        </div>

        {/* Test Result Notice */}
        {testResult && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center justify-between border ${
              testResult.success
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-rose-50 text-rose-800 border-rose-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <Shield className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{testResult.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setTestResult(null)}
              className="text-xs font-bold text-stone-500 hover:text-stone-800 ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* Sync Result Notice */}
        {syncResult && (
          <div
            className={`p-3.5 rounded-lg text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border ${
              syncResult.includes('Successfully') || syncResult.includes('synchronized')
                ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                : 'bg-amber-50 text-amber-900 border-amber-300'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {syncResult.includes('Successfully') || syncResult.includes('synchronized') ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <Shield className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <span className="font-semibold block">{syncResult}</span>
                {syncResult.includes('RLS') && (
                  <div className="flex items-center gap-2 pt-1 flex-wrap">
                    {onOpenAuthModal && (
                      <button
                        type="button"
                        onClick={onOpenAuthModal}
                        className="px-2.5 py-1 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white rounded font-bold text-[11px] shadow-2xs cursor-pointer flex items-center gap-1"
                      >
                        <Lock className="w-3 h-3" />
                        <span>Sign In as kosamgo@gmail.com</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={handleCopySql}
                      className="px-2.5 py-1 bg-white hover:bg-stone-50 text-stone-700 border border-stone-300 rounded font-bold text-[11px] shadow-2xs cursor-pointer flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3 text-[#B88B2A]" />
                      <span>{copiedSql ? 'Copied SQL!' : 'Copy SQL Fix'}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSyncResult(null)}
              className="text-stone-400 hover:text-stone-700 font-bold ml-auto sm:ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* Rates Sync Result Notice */}
        {ratesSyncResult && (
          <div
            className={`p-3.5 rounded-lg text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border ${
              ratesSyncResult.includes('Successfully') || ratesSyncResult.includes('uploaded')
                ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                : 'bg-amber-50 text-amber-900 border-amber-300'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {ratesSyncResult.includes('Successfully') || ratesSyncResult.includes('uploaded') ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <Shield className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <span className="font-semibold block">{ratesSyncResult}</span>
                {ratesSyncResult.includes('RLS') && (
                  <div className="flex items-center gap-2 pt-1 flex-wrap">
                    <button
                      type="button"
                      onClick={() => {
                        const sql = `CREATE POLICY "Allow Initial Rates Upload" ON public.rates FOR ALL TO anon USING (true) WITH CHECK (true);`;
                        navigator.clipboard.writeText(sql);
                        setCopiedSql(true);
                        setTimeout(() => setCopiedSql(false), 2500);
                      }}
                      className="px-2.5 py-1 bg-white hover:bg-stone-50 text-stone-700 border border-stone-300 rounded font-bold text-[11px] shadow-2xs cursor-pointer flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3 text-[#B88B2A]" />
                      <span>{copiedSql ? 'Copied Rates Policy!' : 'Copy Rates RLS Policy'}</span>
                    </button>
                    {onOpenAuthModal && (
                      <button
                        type="button"
                        onClick={onOpenAuthModal}
                        className="px-2.5 py-1 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white rounded font-bold text-[11px] shadow-2xs cursor-pointer flex items-center gap-1"
                      >
                        <Lock className="w-3 h-3" />
                        <span>Sign In as kosamgo@gmail.com</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setRatesSyncResult(null)}
              className="text-stone-400 hover:text-stone-700 font-bold ml-auto sm:ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-stone-100">
          <button
            type="button"
            onClick={handleSaveSupabaseConfig}
            className="px-3.5 py-1.5 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors cursor-pointer"
          >
            Save Credentials
          </button>

          <button
            type="button"
            onClick={handleTestConnection}
            disabled={isTesting || !supabaseUrl}
            className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
            <span>{isTesting ? 'Connecting...' : 'Test Connection'}</span>
          </button>

          <button
            type="button"
            onClick={handleSyncToSupabase}
            disabled={isSyncing}
            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
            title="Upload your local transactions and markdown settings to Supabase"
          >
            <Upload className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Uploading Purchases...' : 'Push Purchases to Cloud'}</span>
          </button>

          <button
            type="button"
            onClick={handleUploadRates}
            disabled={isUploadingRates}
            className="px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
            title="Upload all 5,666 historical benchmark prices to Supabase"
          >
            <LineChart className={`w-3.5 h-3.5 ${isUploadingRates ? 'animate-spin' : ''}`} />
            <span>{isUploadingRates ? 'Uploading Rates...' : 'Push 5,666 Rates to Cloud'}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowSqlSchema(!showSqlSchema)}
            className="ml-auto px-3 py-1.5 text-xs text-stone-600 hover:text-stone-900 underline flex items-center gap-1 cursor-pointer"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>{showSqlSchema ? 'Hide SQL Script' : 'View Supabase SQL Setup'}</span>
          </button>
        </div>

        {/* SQL Schema Preview */}
        {showSqlSchema && (
          <div className="bg-stone-900 text-stone-100 p-4 rounded-xl text-[11px] font-mono space-y-2 overflow-x-auto relative">
            <div className="flex justify-between items-center pb-2 border-b border-stone-800 text-stone-400">
              <span>SQL Schema & RLS Policies (Run in Supabase SQL Editor)</span>
              <button
                type="button"
                onClick={handleCopySql}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-800 hover:bg-stone-700 text-stone-200 text-[10px]"
              >
                {copiedSql ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedSql ? 'Copied!' : 'Copy Full SQL'}</span>
              </button>
            </div>
            <pre className="text-emerald-400 text-[10px] leading-relaxed">
{`-- 1. Purchases table
CREATE TABLE IF NOT EXISTS public.purchases (
    id TEXT PRIMARY KEY,
    purchase_date DATE NOT NULL,
    seller TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    form TEXT NOT NULL CHECK (form IN ('VEDHANI', 'COIN', 'BAR')),
    purity NUMERIC NOT NULL CHECK (purity > 0),
    weight_grams NUMERIC NOT NULL CHECK (weight_grams > 0),
    purchase_rate NUMERIC NOT NULL CHECK (purchase_rate > 0),
    taxes_paid NUMERIC NOT NULL DEFAULT 0,
    other_charges NUMERIC NOT NULL DEFAULT 0,
    notes TEXT,
    bullion_value NUMERIC NOT NULL,
    invested_amount NUMERIC NOT NULL,
    batch_id TEXT,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Rates table (5,666 historical records)
CREATE TABLE IF NOT EXISTS public.rates (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    purity NUMERIC NOT NULL,
    price_per_gram NUMERIC NOT NULL CHECK (price_per_gram > 0),
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    original_unit TEXT NOT NULL,
    original_price NUMERIC NOT NULL,
    session TEXT DEFAULT 'PM',
    gst_included BOOLEAN DEFAULT FALSE,
    notes TEXT,
    provenance TEXT NOT NULL,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Row Level Security Policies
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public Read Purchases" ON public.purchases FOR SELECT TO public USING (true);
CREATE POLICY "Allow Initial Ledger Upload" ON public.purchases FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "Superuser Modify Purchases" ON public.purchases FOR ALL TO authenticated USING (auth.jwt() ->> 'email' = 'kosamgo@gmail.com') WITH CHECK (auth.jwt() ->> 'email' = 'kosamgo@gmail.com');

CREATE POLICY "Public Read Rates" ON public.rates FOR SELECT TO public USING (true);
CREATE POLICY "Allow Initial Rates Upload" ON public.rates FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "Superuser Modify Rates" ON public.rates FOR ALL TO authenticated USING (auth.jwt() ->> 'email' = 'kosamgo@gmail.com') WITH CHECK (auth.jwt() ->> 'email' = 'kosamgo@gmail.com');`}
            </pre>
          </div>
        )}
      </div>

      {/* Valuation Assumptions Form */}
      <div className="bg-white rounded-xl p-5 border border-[#E7E2DA] shadow-xs space-y-4">
        <div className="border-b border-stone-100 pb-3">
          <h3 className="text-sm font-bold text-stone-900 flex items-center gap-2">
            <Coins className="w-4 h-4 text-[#B88B2A]" />
            Resale Valuation Markdown & Metadata Rules
          </h3>
          <p className="text-xs text-stone-500 mt-0.5">
            Configure the baseline markdown percentage applied to the benchmark metal value to compute
            estimated resale value and annualised XIRR.
          </p>
        </div>

        <form onSubmit={handleSaveSettings} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Gold Resale Haircut */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Gold Resale Markdown Haircut (%)
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="50"
                  value={goldMarkdown}
                  onChange={(e) => setGoldMarkdown(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
                <span className="absolute right-3 top-2 text-xs text-stone-400 font-bold">%</span>
              </div>
              <span className="text-[11px] text-stone-500 mt-1 block">
                Default: 3.0%. Applied as: Resale = Reference Metal Value × (1 - 0.03).
              </span>
            </div>

            {/* Silver Resale Haircut */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Silver Resale Markdown Haircut (%)
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="50"
                  value={silverMarkdown}
                  onChange={(e) => setSilverMarkdown(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
                <span className="absolute right-3 top-2 text-xs text-stone-400 font-bold">%</span>
              </div>
              <span className="text-[11px] text-stone-500 mt-1 block">
                Default: 3.0%. Applied as: Resale = Reference Metal Value × (1 - 0.03).
              </span>
            </div>
          </div>

          {/* Dataset Metadata Preferences */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-stone-100">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Historical Session Metadata Confirmation
              </label>
              <select
                value={confirmSession}
                onChange={(e) => setConfirmSession(e.target.value as any)}
                className="w-full text-xs px-2.5 py-1.5 border border-stone-300 rounded-lg bg-white"
              >
                <option value="UNSPECIFIED">Unspecified / Unconfirmed (Default)</option>
                <option value="PM_CLOSING">Assume PM Closing Rates</option>
                <option value="AM_OPENING">Assume AM Opening Rates</option>
              </select>
              <span className="text-[11px] text-stone-500 mt-1 block">
                Historical CSV does not identify AM/PM; preserved as unconfirmed by default.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Quotation Tax Treatment Confirmation
              </label>
              <select
                value={confirmTax}
                onChange={(e) => setConfirmTax(e.target.value as any)}
                className="w-full text-xs px-2.5 py-1.5 border border-stone-300 rounded-lg bg-white"
              >
                <option value="UNCONFIRMED">Unconfirmed (Preserve Raw Provenance)</option>
                <option value="TAX_EXCLUSIVE">Confirm Tax Exclusive (Excludes 3% GST)</option>
                <option value="TAX_INCLUSIVE">Confirm Tax Inclusive</option>
              </select>
              <span className="text-[11px] text-stone-500 mt-1 block">
                Preserves raw provenance without artificially asserting GST inclusion.
              </span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] rounded-lg shadow-2xs transition-colors"
            >
              Update Assumptions & Recalculate
            </button>
          </div>
        </form>
      </div>

      {/* Data Backup & Portability */}
      <div className="bg-white rounded-xl p-5 border border-[#E7E2DA] shadow-xs space-y-4">
        <div className="border-b border-stone-100 pb-3">
          <h3 className="text-sm font-bold text-stone-900 flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-600" />
            Complete Database Backup & Portability
          </h3>
          <p className="text-xs text-stone-500 mt-0.5">
            Download your entire portfolio, invoice ledger, audit logs, and settings as a standalone
            JSON file that can be restored on any device or browser.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {/* Download JSON Backup */}
          <div className="border border-stone-200 rounded-xl p-4 bg-stone-50/50 flex flex-col justify-between space-y-3">
            <div>
              <span className="text-xs font-bold text-stone-900 block">Export Full JSON Backup</span>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Packages {purchasesCount} purchase lots, custom rate corrections, and markdown settings.
              </p>
            </div>
            <button
              type="button"
              onClick={onExportBackup}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-stone-800 bg-white hover:bg-stone-50 border border-stone-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#B88B2A]" />
              <span>Download JSON Backup</span>
            </button>
          </div>

          {/* Restore from Backup */}
          <div className="border border-stone-200 rounded-xl p-4 bg-stone-50/50 flex flex-col justify-between space-y-3">
            <div>
              <span className="text-xs font-bold text-stone-900 block">Restore from JSON File</span>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Load a previously exported backup file to restore purchases and settings.
              </p>
            </div>
            <label className="cursor-pointer w-full inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-stone-800 bg-white hover:bg-stone-50 border border-stone-300 rounded-lg shadow-2xs transition-colors">
              <Upload className="w-3.5 h-3.5 text-emerald-600" />
              <span>Select Backup File (.json)</span>
              <input
                type="file"
                accept=".json"
                onChange={handleFileRestore}
                className="hidden"
              />
            </label>
          </div>

          {/* Cloud Database Upload Card */}
          <div className="border border-emerald-300 rounded-xl p-4 bg-emerald-50/40 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center gap-1.5">
                <Cloud className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-xs font-bold text-stone-900">Push Ledger to Supabase</span>
              </div>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Directly upload your {purchasesCount} local purchases and markdown settings to Supabase cloud tables.
              </p>
            </div>
            <button
              type="button"
              onClick={handleSyncToSupabase}
              disabled={isSyncing}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-2xs transition-colors cursor-pointer"
            >
              <Upload className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Synchronizing...' : '1-Click Upload to Supabase'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Demo Data Management */}
      <div className="bg-white rounded-xl p-5 border border-[#E7E2DA] shadow-xs space-y-3">
        <h3 className="text-sm font-bold text-stone-900 flex items-center gap-2">
          <FolderOpen className="w-4 h-4 text-[#B88B2A]" />
          Demo Portfolio & Quick Actions
        </h3>
        <p className="text-xs text-stone-500">
          Load a realistic set of physical gold and silver purchases across Vedhani, Coins, and Bars
          for testing, or reset the ledger.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button
            type="button"
            onClick={onLoadDemoData}
            className="px-3.5 py-2 text-xs font-semibold bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#B88B2A]" />
            <span>Load Demo Portfolio</span>
          </button>

          <button
            type="button"
            onClick={onClearAllPurchases}
            className="px-3.5 py-2 text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-600" />
            <span>Clear All Ledger Purchases</span>
          </button>
        </div>
      </div>

      {/* Architecture & Private Sync Roadmap Documentation */}
      <div className="bg-stone-50 rounded-xl p-5 border border-stone-200 space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-stone-700" />
          <h3 className="text-sm font-bold text-stone-900">
            System Scope, Extensibility & Supabase Architecture
          </h3>
        </div>

        <div className="space-y-3 text-xs text-stone-700 leading-relaxed">
          {/* Scope Explanation */}
          <div className="bg-white p-3.5 rounded-lg border border-stone-200 space-y-1">
            <span className="font-bold text-stone-900 block">Version 1 Purchases-Only Scope:</span>
            <p className="text-stone-600">
              This version assumes all recorded bullion remains held. Sales controls are deliberately
              not exposed to prevent non-functional UI clutter. The underlying data model includes
              extensibility flags (<code className="bg-stone-100 px-1 py-0.5 rounded font-mono">deleted</code>,{' '}
              <code className="bg-stone-100 px-1 py-0.5 rounded font-mono">dispositionStatus</code>) so future partial
              or complete sales can record terminal redemption proceeds and realized capital gains without schema migration.
            </p>
          </div>

          {/* Active Free IBJA Provider & IRateProvider Architecture */}
          <div className="bg-white p-3.5 rounded-lg border border-[#D4AF37]/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-stone-900 block">External Rate Provider Architecture & Free Sourcing:</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                IBJA Free Benchmark Active
              </span>
            </div>
            <p className="text-stone-600">
              The application implements the <code className="bg-stone-100 px-1 py-0.5 rounded font-mono">IRateProvider</code> interface
              with a dedicated <code className="bg-stone-100 px-1 py-0.5 rounded font-mono">IbjaRateProvider</code> that sources official
              PM closing prices once daily directly from <strong>India Bullion and Jewellers Association (ibjarates.com)</strong> free of charge.
              Quotations for Gold 999 (₹/10g), Gold 995 (₹/10g), and Silver 999 (₹/kg) are automatically ingested and normalized to ₹/gram.
            </p>
            <p className="text-stone-500 text-[11px]">
              Multi-tier delivery leverages local Vite dev proxy (<code className="bg-stone-100 px-1 py-0.5 rounded font-mono">/api/ibja</code>)
              and public CORS gateways with a verified baseline fallback, safeguarding full offline functionality and zero API quota costs.
            </p>
          </div>

          {/* PWA Offline Guidance */}
          <div className="bg-white p-3.5 rounded-lg border border-stone-200 space-y-1 flex items-start gap-2.5">
            <Smartphone className="w-5 h-5 text-[#B88B2A] shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-stone-900 block">PWA Production Offline Installation Guidance:</span>
              <p className="text-stone-600">
                Bullion Ledger includes a Service Worker and Web App Manifest. You can install it on your mobile device or desktop
                via Chrome / Safari ("Add to Home Screen" or "Install App") to use it as an offline financial ledger anytime.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Browser Cache & PWA Force Reload Utility */}
      <div className="bg-white rounded-xl p-4 border border-stone-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div>
          <span className="font-bold text-stone-900 flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4 text-[#B88B2A]" />
            Browser Cache & PWA Service Worker Reset
          </span>
          <p className="text-stone-500 text-[11px] mt-0.5">
            If you ever see stale cached data or an earlier build, click here to purge browser CacheStorage, unregister Service Workers, and force reload.
          </p>
        </div>
        <button
          type="button"
          onClick={handlePurgeCacheAndReload}
          className="shrink-0 px-3.5 py-2 bg-stone-100 hover:bg-stone-200 border border-stone-300 rounded-lg font-semibold text-stone-700 flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#B88B2A]" />
          <span>Purge Cache & Force Reload</span>
        </button>
      </div>
    </div>
  );
};
