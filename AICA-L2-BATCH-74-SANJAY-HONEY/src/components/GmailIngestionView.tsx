import React, { useState } from 'react';
import {
  Mail,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  Key,
  ShieldCheck,
  LogOut,
  ArrowRight,
  Database,
  Calendar,
  Layers,
  FileText,
  AlertTriangle,
  FileCheck,
  Bug,
} from 'lucide-react';
import {
  GmailConnectionState,
  connectGmailOAuth,
  disconnectGmail,
  getGmailAccessToken,
  setLastSyncTime,
  verifyGmailProfileAPI,
} from '../services/firebaseAuth';

import { BriefingSource, ActiveBriefingInfo, GmailSearchDiagnostics } from '../types';

interface GmailIngestionViewProps {
  gmailState: GmailConnectionState;
  onStateChange: (state: GmailConnectionState) => void;
  briefingDate: string;
  setBriefingDate: (date: string) => void;
  onImportBriefing: (text: string, subject: string, importMeta?: any) => void;
  isExtracting: boolean;
  extractionError: string | null;
  onSwitchToDemoMode: () => void;
  isLiveSystem?: boolean;
  briefingSource?: BriefingSource;
  isDemoMode?: boolean;
  activeBriefingInfo?: ActiveBriefingInfo;
  onLogAudit: (action: string, target: string, details: string) => void;
}

export const GmailIngestionView: React.FC<GmailIngestionViewProps> = ({
  gmailState,
  onStateChange,
  briefingDate,
  setBriefingDate,
  onImportBriefing,
  isExtracting,
  extractionError,
  onSwitchToDemoMode,
  isLiveSystem,
  briefingSource = 'DEMO',
  isDemoMode,
  activeBriefingInfo,
  onLogAudit,
}) => {
  const isLive = isLiveSystem !== undefined ? isLiveSystem : gmailState.isConnected;
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [searchStatus, setSearchStatus] = useState<string | null>(null);
  const [lastImportData, setLastImportData] = useState<any | null>(null);
  const [searchResultError, setSearchResultError] = useState<any | null>(null);
  const [diagnosticsData, setDiagnosticsData] = useState<GmailSearchDiagnostics | null>(null);

  // Handle Connect Gmail with strict API verification
  const handleConnect = async () => {
    try {
      setTestResult(null);
      const { state, accessToken } = await connectGmailOAuth();
      onStateChange(state);

      if (state.isConnected) {
        onLogAudit(
          'Gmail OAuth Connect Success',
          state.userEmail || 'Gmail Account',
          'Successfully authenticated via Google OAuth 2.0 with scope gmail.readonly and verified profile via Gmail API.'
        );
      } else {
        onLogAudit(
          'Gmail API Verification Failed',
          state.userEmail || 'Gmail Account',
          `OAuth completed but Gmail API profile check failed: ${state.errorMessage || 'Unknown error'}`
        );
      }
    } catch (err: any) {
      console.error('Connect Gmail Error:', err);
      const isPopupClosed = err?.code === 'auth/popup-closed-by-user';
      const newState: GmailConnectionState = {
        isConnected: false,
        userEmail: null,
        userName: null,
        status: isPopupClosed ? 'Not Connected' : 'Connection Error',
        lastSyncTime: gmailState.lastSyncTime,
        errorMessage: isPopupClosed
          ? 'Sign in popup was closed before completing OAuth.'
          : err.message || 'OAuth authentication failed.',
        firebaseAuthStatus: 'FAIL',
        googleUserReturned: 'FAIL',
        oauthCredentialReturned: 'FAIL',
        googleAccessTokenPresent: 'Missing',
        gmailReadonlyScopeRequested: 'YES',
        gmailApiProfileStatus: 'FAIL',
        connectedGmailAddress: null,
        lastError: err.message || 'OAuth popup error',
        lastTestTime: new Date().toLocaleString(),
      };
      onStateChange(newState);
      onLogAudit(
        'Gmail OAuth Failed',
        'Google OAuth',
        `OAuth connection attempt failed: ${err.message || 'Popup closed or blocked'}`
      );
    }
  };

  // Handle Disconnect Gmail
  const handleDisconnect = async () => {
    try {
      await disconnectGmail();
      onStateChange({
        isConnected: false,
        userEmail: null,
        userName: null,
        status: 'Not Connected',
        lastSyncTime: gmailState.lastSyncTime,
        firebaseAuthStatus: 'FAIL',
        googleUserReturned: 'FAIL',
        oauthCredentialReturned: 'FAIL',
        googleAccessTokenPresent: 'Missing',
        gmailReadonlyScopeRequested: 'YES',
        gmailApiProfileStatus: 'Not Executed',
        connectedGmailAddress: null,
        lastError: null,
        lastTestTime: new Date().toLocaleString(),
      });
      onLogAudit('Gmail Disconnect', 'OAuth Revoked', 'User disconnected Gmail OAuth session.');
    } catch (e: any) {
      console.error('Disconnect error:', e);
    }
  };

  // Handle Test Connection - Calls real Gmail Profile API endpoint
  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    const token = getGmailAccessToken();

    if (!token) {
      setTestResult('❌ Test Failed: No Bearer OAuth token found in session. Click Connect Gmail to authenticate.');
      setIsTesting(false);
      return;
    }

    try {
      const verifyRes = await fetch('/api/gmail/verify-profile', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const verifyData = await verifyRes.json();

      if (verifyRes.ok && verifyData.success) {
        setTestResult(
          `✅ Gmail Profile API Test PASSED! Authenticated account: ${verifyData.profile.emailAddress} (Messages Total: ${verifyData.profile.messagesTotal})`
        );
        onLogAudit('Gmail API Diagnostic', 'Profile Test Passed', `Email: ${verifyData.profile.emailAddress}`);
      } else {
        setTestResult(`❌ Gmail API Profile Test FAILED: ${verifyData.error || 'Failed'}`);
        onLogAudit('Gmail API Diagnostic', 'Profile Test Failed', verifyData.error || 'Failed');
      }
    } catch (err: any) {
      setTestResult(`❌ Connection Error: ${err.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  // Handle Search & Import
  const handleSearchAndImport = async () => {
    const token = getGmailAccessToken();
    if (!token || !gmailState.isConnected) {
      onStateChange({
        ...gmailState,
        status: 'Not Connected',
        errorMessage: 'Gmail token is missing or API profile unverified. Click Connect Gmail first.',
      });
      return;
    }

    setLastImportData(null);
    setSearchResultError(null);
    setDiagnosticsData(null);
    setSearchStatus(`Searching Gmail inbox for subject "Daily Professional Briefing – ${briefingDate}"...`);

    try {
      const res = await fetch(`/api/gmail/search-briefing?date=${encodeURIComponent(briefingDate)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();

      if (data.diagnostics) {
        setDiagnosticsData(data.diagnostics);
      }

      if (data.found && data.message?.bodyText && data.dateMatch === 'PASS') {
        const syncTime = new Date().toLocaleString();
        setLastSyncTime(syncTime);
        onStateChange({
          ...gmailState,
          status: 'Connected',
          lastSyncTime: syncTime,
        });

        setLastImportData(data);
        setSearchResultError(null);
        setSearchStatus(`Briefing imported successfully! Subject: ${data.message.subject}`);

        onImportBriefing(data.message.bodyText, data.message.subject, data);
        onLogAudit(
          'Gmail Import Success',
          data.message.subject,
          `Strict Target Date Match PASS. Target Date: ${data.requestedTargetDate || briefingDate}. Gmail Message ID: ${data.message.id}. Proceeding to AI extraction.`
        );
      } else {
        setLastImportData(null);
        setSearchResultError(data);
        setSearchStatus('NO MATCHING LIVE GMAIL BRIEFING FOUND');
        onLogAudit(
          'Gmail Search Empty',
          `Target Date: ${briefingDate}`,
          `Searched subject "Daily Professional Briefing – ${briefingDate}". NO MATCHING LIVE GMAIL BRIEFING FOUND.`
        );
      }
    } catch (err: any) {
      setSearchResultError({
        requestedTargetDate: briefingDate,
        expectedSubject: `Daily Professional Briefing – ${briefingDate}`,
        searchStatus: 'Gmail Search API Error',
        error: err.message,
      });
      setSearchStatus(`Gmail search failed: ${err.message}`);
    }
  };

  const getStatusBadge = () => {
    if (gmailState.isConnected) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
          Connected
        </span>
      );
    }
    if (gmailState.status === 'Authentication Expired') {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
          <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
          Authentication Expired
        </span>
      );
    }
    if (gmailState.status === 'Connection Error') {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
          <AlertCircle className="w-3.5 h-3.5 mr-1 text-rose-600" />
          Connection Error
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-300">
        <span className="w-2 h-2 rounded-full bg-slate-400 mr-1.5" />
        Not Connected
      </span>
    );
  };

  return (
    <div className="space-y-6 pb-12 max-w-5xl mx-auto">
      {/* Module Title */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
          <Mail className="w-4 h-4" />
          <span>MODULE 02 — LIVE GMAIL DAILY BRIEFING INGESTION (VERSION 2.1)</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Gmail Daily Briefing Ingestion</h1>
        <p className="text-xs text-slate-500 mt-1">
          Secure Google OAuth 2.0 connection to retrieve, extract facts, and process daily professional compliance emails.
        </p>
      </div>

      {/* Main Connection Status Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div className="flex items-start space-x-3">
            <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-teal-700 shrink-0">
              <Mail className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-900">Google OAuth 2.0 Gmail Connection</h2>
                {getStatusBadge()}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Minimum Scope: <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-[11px]">https://www.googleapis.com/auth/gmail.readonly</code>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {gmailState.isConnected ? (
              <>
                <button
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                  <span>Test Gmail API Profile</span>
                </button>

                <button
                  onClick={handleDisconnect}
                  className="px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-xs rounded-xl transition-all flex items-center space-x-1.5 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Disconnect</span>
                </button>
              </>
            ) : (
              <button
                onClick={handleConnect}
                className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center space-x-2 cursor-pointer"
              >
                <Key className="w-4 h-4" />
                <span>CONNECT GMAIL</span>
              </button>
            )}
          </div>
        </div>

        {/* Visible Diagnostic Metrics Panel */}
        <div className="bg-slate-900 text-slate-100 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-teal-400" />
              <span className="font-bold text-xs uppercase tracking-wider text-teal-300">
                GMAIL OAUTH & API DIAGNOSTIC MATRIX
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              Live Profile Verification ({gmailState.lastTestTime || 'Not Tested'})
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 text-xs">
            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                Firebase Auth
              </span>
              <span className={`font-bold text-xs ${gmailState.firebaseAuthStatus === 'PASS' ? 'text-emerald-400' : 'text-slate-400'}`}>
                {gmailState.firebaseAuthStatus || 'FAIL'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                Google User
              </span>
              <span className={`font-bold text-xs ${gmailState.googleUserReturned === 'PASS' ? 'text-emerald-400' : 'text-slate-400'}`}>
                {gmailState.googleUserReturned || 'FAIL'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                OAuth Credential
              </span>
              <span className={`font-bold text-xs ${gmailState.oauthCredentialReturned === 'PASS' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {gmailState.oauthCredentialReturned || 'FAIL'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                Access Token
              </span>
              <span className={`font-bold text-xs ${gmailState.googleAccessTokenPresent === 'PASS' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {gmailState.googleAccessTokenPresent === 'PASS' ? 'PASS' : 'Missing'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                gmail.readonly Scope
              </span>
              <span className={`font-bold text-xs ${gmailState.gmailReadonlyScopeRequested === 'YES' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {gmailState.gmailReadonlyScopeRequested || 'YES'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                /users/me/profile
              </span>
              <span className={`font-bold text-xs ${gmailState.gmailApiProfileStatus === 'PASS' ? 'text-emerald-400' : gmailState.gmailApiProfileStatus === 'FAIL' ? 'text-rose-400' : 'text-slate-400'}`}>
                {gmailState.gmailApiProfileStatus || 'Not Executed'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                Connected Address
              </span>
              <span className="font-bold text-xs text-white truncate block" title={gmailState.connectedGmailAddress || gmailState.userEmail || 'None'}>
                {gmailState.connectedGmailAddress || gmailState.userEmail || 'None'}
              </span>
            </div>

            <div className="p-2 bg-slate-800/80 border border-slate-700/60 rounded-xl">
              <span className="text-[9px] text-slate-400 font-semibold block uppercase">
                Current Status
              </span>
              <span className={`font-bold text-xs ${gmailState.isConnected ? 'text-emerald-400' : 'text-rose-400'}`}>
                {gmailState.isConnected ? 'Connected' : gmailState.status}
              </span>
            </div>
          </div>

          {(gmailState.lastError || gmailState.errorMessage) && (
            <div className="p-3 bg-rose-950/60 border border-rose-800/60 text-rose-200 rounded-xl text-xs font-mono space-y-1">
              <strong className="font-bold text-rose-300 block">Diagnostic Failure / Error Log:</strong>
              <p>{gmailState.lastError || gmailState.errorMessage}</p>
            </div>
          )}
        </div>

        {/* Account & Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Connected Account
            </span>
            <p className="font-bold text-slate-800 break-all">
              {gmailState.userEmail || (gmailState.isConnected ? 'OAuth Token Active' : 'Not Authenticated')}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              OAuth Security
            </span>
            <p className="font-semibold text-slate-700 flex items-center space-x-1">
              <ShieldCheck className="w-4 h-4 text-emerald-600 inline mr-1" />
              <span>Read-Only Access • No Passwords Stored</span>
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Last Successful Sync
            </span>
            <p className="font-mono text-slate-700">
              {gmailState.lastSyncTime || 'No recent sync in session'}
            </p>
          </div>
        </div>

        {/* Test Result Message Box */}
        {testResult && (
          <div className="p-3.5 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs space-y-1">
            <p className="font-bold text-teal-400">GMAIL API DIAGNOSTIC LOG:</p>
            <p>{testResult}</p>
          </div>
        )}

        {/* Error / Warning Alert */}
        {gmailState.errorMessage && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Authentication Alert</p>
              <p className="mt-0.5">{gmailState.errorMessage}</p>
            </div>
          </div>
        )}
      </div>

      {/* Live Email Search & Import Panel */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
          <Search className="w-5 h-5 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900">Live Gmail Search & Ingestion Engine</h2>
        </div>

        {/* Current Active Briefing Status Box */}
        {activeBriefingInfo && (
          <div className="bg-slate-900 text-slate-100 rounded-2xl p-4 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-teal-400" />
                <span className="font-bold text-xs uppercase tracking-wider text-teal-300">
                  CURRENT ACTIVE BRIEFING IN SYSTEM
                </span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeBriefingInfo.source === 'GMAIL'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              }`}>
                {activeBriefingInfo.source === 'GMAIL' ? 'LIVE GMAIL' : 'DEMO DATA'}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div>
                <span className="text-[10px] text-slate-400 block font-semibold uppercase">Briefing Target Date</span>
                <span className="font-bold text-white">{activeBriefingInfo.targetDate}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-semibold uppercase">Actual Subject</span>
                <span className="font-bold text-white truncate block" title={activeBriefingInfo.actualSubject}>
                  {activeBriefingInfo.actualSubject}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-semibold uppercase">Date Match Validation</span>
                <span className={`font-bold flex items-center space-x-1 ${
                  activeBriefingInfo.dateMatch === 'PASS'
                    ? 'text-emerald-400'
                    : activeBriefingInfo.dateMatch === 'DEMO'
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{activeBriefingInfo.dateMatch === 'PASS' ? 'PASS (Strict Target Date Match)' : activeBriefingInfo.dateMatch}</span>
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-semibold uppercase">Source Type</span>
                <span className="font-bold text-teal-300">
                  {activeBriefingInfo.source === 'GMAIL' ? 'Live Gmail OAuth API' : 'Demo Data Engine'}
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 mb-1">Briefing Target Date</label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={briefingDate}
                onChange={(e) => setBriefingDate(e.target.value)}
                placeholder="e.g. 7 August 2026 or 07/08/2026"
                className="flex-1 p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none font-bold text-slate-800"
              />
              <button
                onClick={() => setBriefingDate(new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }))}
                className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs cursor-pointer"
              >
                Today
              </button>
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Gmail Subject Query (Strict Target Date Pattern)</label>
            <input
              type="text"
              readOnly
              value={`Daily Professional Briefing – ${briefingDate}`}
              className="w-full p-2.5 bg-slate-100 border border-slate-200 text-slate-800 font-mono text-xs rounded-xl cursor-not-allowed font-bold"
            />
          </div>
        </div>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <div className="text-xs text-slate-500">
            {isLive ? (
              briefingSource === 'GMAIL' ? (
                <span className="text-emerald-700 font-bold flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5 inline text-emerald-600" />
                  <span>LIVE SYSTEM — Gmail Briefing Ingested ({gmailState.userEmail || 'OAuth Connected'})</span>
                </span>
              ) : (
                <span className="text-teal-700 font-bold flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5 inline text-teal-600" />
                  <span>LIVE SYSTEM — Gmail Connected ({gmailState.userEmail || 'OAuth Verified'}). Ready to Search & Import.</span>
                </span>
              )
            ) : (
              <span className="text-amber-700 font-bold flex items-center space-x-1">
                <AlertCircle className="w-3.5 h-3.5 inline" />
                <span>Currently in Demo Mode. Connect Gmail to switch to Live Mode.</span>
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <button
              onClick={onSwitchToDemoMode}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all cursor-pointer"
            >
              Load Demo Briefing
            </button>

            <button
              onClick={handleSearchAndImport}
              disabled={isExtracting}
              className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center space-x-2 cursor-pointer disabled:opacity-50"
            >
              {isExtracting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>SEARCHING & EXTRACTING...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>SEARCH & IMPORT BRIEFING</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Confirmation Panel: Live Gmail Briefing Imported */}
        {lastImportData && lastImportData.found && (
          <div className="p-5 bg-emerald-50 border border-emerald-200 rounded-2xl space-y-3">
            <div className="flex items-center space-x-2 text-emerald-900 font-bold text-sm">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>LIVE GMAIL BRIEFING IMPORTED</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-slate-700 bg-white p-4 rounded-xl border border-emerald-100 shadow-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Requested Target Date</span>
                <span className="font-bold text-slate-900">{lastImportData.requestedTargetDate || briefingDate}</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Actual Email Subject</span>
                <span className="font-bold text-slate-900 break-all">{lastImportData.message.subject}</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Email Received Date/Time</span>
                <span className="font-bold text-slate-900">{lastImportData.message.date}</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Gmail Message ID</span>
                <span className="font-mono text-slate-800 text-[11px] truncate block" title={lastImportData.message.id}>
                  {lastImportData.message.id}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Connected Account</span>
                <span className="font-bold text-slate-900">{gmailState.connectedGmailAddress || gmailState.userEmail || 'Connected Gmail'}</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Imported Date/Time</span>
                <span className="font-bold text-slate-900">{new Date().toLocaleString()}</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Source Provenance</span>
                <span className="font-bold text-emerald-700">LIVE GMAIL API</span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block">Date Consistency</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded font-bold text-[11px] bg-emerald-100 text-emerald-800 border border-emerald-300">
                  DATE MATCH: PASS
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error / Warning Panel: NO MATCHING LIVE GMAIL BRIEFING FOUND */}
        {searchResultError && (
          <div className="p-5 bg-rose-50 border border-rose-200 rounded-2xl space-y-3">
            <div className="flex items-center space-x-2 text-rose-900 font-bold text-sm">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <span>NO MATCHING LIVE GMAIL BRIEFING FOUND</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-rose-100 text-xs space-y-3 text-slate-700">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Requested Date</span>
                  <span className="font-bold text-slate-900">{searchResultError.requestedTargetDate || briefingDate}</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Expected Subject</span>
                  <span className="font-mono text-slate-800 text-[11px] block font-bold">
                    {searchResultError.expectedSubject || `Daily Professional Briefing – ${briefingDate}`}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Search Status</span>
                  <span className="font-bold text-rose-700">{searchResultError.searchStatus || 'No Matching Email Found'}</span>
                </div>
              </div>

              <p className="text-slate-600 pt-1 leading-relaxed">
                Connected to Gmail account <strong className="text-slate-900">{gmailState.userEmail || 'OAuth Account'}</strong>, but no email with expected subject <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-[11px] text-slate-800 font-bold">{searchResultError.expectedSubject || `Daily Professional Briefing – ${briefingDate}`}</code> was located in your inbox. No fallback email or demo data was automatically imported.
              </p>

              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleSearchAndImport}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl transition-all cursor-pointer shadow-xs flex items-center space-x-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry Search</span>
                </button>

                <button
                  onClick={onSwitchToDemoMode}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs rounded-xl transition-all cursor-pointer"
                >
                  Explicitly Load Demo Briefing
                </button>
              </div>
            </div>
          </div>
        )}

        {extractionError && !searchResultError && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs">
            <strong className="font-bold">Extraction Error:</strong> {extractionError}
          </div>
        )}

        {/* GMAIL SEARCH DIAGNOSTICS PANEL */}
        {diagnosticsData && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md space-y-4 text-slate-200 mt-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Bug className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-sm text-white tracking-wide uppercase">
                  GMAIL SEARCH DIAGNOSTICS
                </h3>
              </div>
              <span className="text-xs bg-slate-800 text-slate-300 px-2.5 py-1 rounded-full font-mono border border-slate-700 font-bold">
                {diagnosticsData.candidateMessagesFound} Candidate Messages Found
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Connected Account</span>
                <span className="font-bold text-teal-300 truncate block" title={diagnosticsData.connectedAccount}>
                  {diagnosticsData.connectedAccount}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Target Date</span>
                <span className="font-bold text-white">{diagnosticsData.targetDate}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Broad Gmail Query</span>
                <code className="font-mono text-amber-300 text-[11px] font-bold block">{diagnosticsData.broadGmailQuery}</code>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Candidate Messages Found</span>
                <span className="font-bold text-white">{diagnosticsData.candidateMessagesFound}</span>
              </div>
            </div>

            {diagnosticsData.candidates && diagnosticsData.candidates.length > 0 ? (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {diagnosticsData.candidates.map((cand, idx) => (
                  <div
                    key={cand.id || idx}
                    className={`p-3.5 rounded-xl border text-xs space-y-2 transition-all ${
                      cand.subjectMatch === 'PASS' && cand.dateMatch === 'PASS'
                        ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-100 shadow-sm'
                        : 'bg-slate-950/80 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between font-mono text-[11px] border-b border-slate-800/80 pb-1.5">
                      <span className="text-slate-400">
                        Candidate #<strong className="text-white">{idx + 1}</strong> | ID: <span className="text-teal-300 font-bold">{cand.id}</span>
                      </span>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          cand.subjectMatch === 'PASS' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}>
                          Subject Match: {cand.subjectMatch}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          cand.dateMatch === 'PASS' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}>
                          Date Match: {cand.dateMatch}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">Actual Subject</span>
                        <span className="font-bold text-white block break-words">{cand.subject}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">Email Date Header</span>
                        <span className="text-slate-300 block">{cand.dateHeader}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">Normalized Subject</span>
                        <code className="font-mono text-[11px] text-slate-300 block break-words bg-slate-900 p-1 rounded">{cand.normalizedSubject}</code>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">Extracted Briefing Date</span>
                        <span className="font-bold text-teal-300 block">{cand.extractedBriefingDate}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-400 text-center font-medium">
                No candidate messages were returned by Gmail broad query: <code className="font-mono text-amber-300">{diagnosticsData.broadGmailQuery}</code>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Technical Architecture & Step-by-Step Configuration Panel */}
      <div className="bg-slate-900 text-slate-200 rounded-2xl p-6 shadow-lg space-y-4 text-xs">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
          <ShieldCheck className="w-5 h-5 text-teal-400" />
          <h3 className="font-bold text-white text-sm">Version 2.1 Technical & Compliance Disclosure</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px] text-slate-300">
          <div className="space-y-2">
            <h4 className="font-bold text-teal-300">1. OAuth 2.0 Scope Minimization</h4>
            <p>
              This applet requests exclusively <code className="text-teal-200 font-mono">https://www.googleapis.com/auth/gmail.readonly</code>. It cannot compose, delete, or modify emails. Access tokens are held exclusively in memory and session storage, and cleared upon disconnect.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-teal-300">2. Real vs Simulated Policy</h4>
            <p>
              In accordance with system policy, Gmail connection is never faked. When authenticated via OAuth 2.0, requests execute against Google's Gmail API. If no OAuth token is supplied or if Gmail API profile check fails, the system explicitly reports "Not Connected" and offers Demo Mode as a fallback.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
