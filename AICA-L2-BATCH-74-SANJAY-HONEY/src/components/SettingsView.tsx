import React, { useState } from 'react';
import { Settings, ShieldCheck, Building, Save, RefreshCw, AlertCircle, Check, Key, LogOut, Mail, AlertTriangle } from 'lucide-react';
import { BriefingSource, BrandSettings } from '../types';
import { GmailConnectionState, connectGmailOAuth, disconnectGmail, getGmailAccessToken } from '../services/firebaseAuth';

interface SettingsViewProps {
  brandSettings: BrandSettings;
  onSaveBrandSettings: (settings: BrandSettings) => void;
  isLiveSystem?: boolean;
  briefingSource?: BriefingSource;
  isDemoMode?: boolean;
  onToggleDemoMode?: () => void;
  gmailState: GmailConnectionState;
  onGmailStateChange: (state: GmailConnectionState) => void;
  onLogAudit: (action: string, target: string, details: string) => void;
  briefingDate?: string;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  brandSettings,
  onSaveBrandSettings,
  isLiveSystem,
  briefingSource = 'DEMO',
  isDemoMode,
  onToggleDemoMode,
  gmailState,
  onGmailStateChange,
  onLogAudit,
  briefingDate = '7 August 2026',
}) => {
  const isLive = isLiveSystem !== undefined ? isLiveSystem : gmailState.isConnected;
  const [firmName, setFirmName] = useState(brandSettings.firmName);
  const [caName, setCaName] = useState(brandSettings.caName);
  const [membershipNo, setMembershipNo] = useState(brandSettings.membershipNo);
  const [contactEmail, setContactEmail] = useState(brandSettings.contactEmail);
  const [contactPhone, setContactPhone] = useState(brandSettings.contactPhone);
  const [firmAddress, setFirmAddress] = useState(brandSettings.firmAddress);
  const [disclaimer, setDisclaimer] = useState(brandSettings.disclaimer);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Test Connection state
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveBrandSettings({
      firmName,
      caName,
      membershipNo,
      contactEmail,
      contactPhone,
      firmAddress,
      disclaimer,
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleConnectGmail = async () => {
    try {
      setTestResult(null);
      const { state } = await connectGmailOAuth();
      onGmailStateChange(state);
      if (state.isConnected) {
        onLogAudit(
          'Gmail OAuth Connect',
          state.userEmail || 'Gmail Account',
          'Successfully authorized Google OAuth 2.0 and verified profile via Gmail API.'
        );
      } else {
        onLogAudit(
          'Gmail API Verification Failed',
          state.userEmail || 'Gmail Account',
          state.errorMessage || 'OAuth succeeded but profile check failed.'
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
        lastError: err.message || 'OAuth failure',
        lastTestTime: new Date().toLocaleString(),
      };
      onGmailStateChange(newState);
      onLogAudit('Gmail OAuth Failure', 'OAuth Popup', err.message || 'OAuth failed');
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      await disconnectGmail();
      onGmailStateChange({
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
    } catch (err: any) {
      console.error('Disconnect Error:', err);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    const token = getGmailAccessToken();

    try {
      const res = await fetch(`/api/gmail/search-briefing?date=${encodeURIComponent(briefingDate)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();

      if (data.connected && data.found) {
        setTestResult(`✅ Connection Verified! Found briefing: "${data.message.subject}" received on ${data.message.date}`);
        onLogAudit('Gmail API Test', 'Success', `Found briefing: ${data.message.subject}`);
      } else if (data.connected && !data.found) {
        setTestResult(`ℹ️ Gmail API Connected! Live search query succeeded. Status: ${data.message}`);
        onLogAudit('Gmail API Test', 'No Email Match', data.message);
      } else {
        setTestResult(`⚠️ ${data.message || 'Gmail not connected. Click "Connect Gmail" to authorize.'}`);
      }
    } catch (err: any) {
      setTestResult(`❌ Connection Error: ${err.message}`);
    } finally {
      setIsTesting(false);
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
    <div className="space-y-6 pb-12 max-w-4xl">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
          <Settings className="w-4 h-4" />
          <span>MODULE 11 — CA FIRM BRAND & SYSTEM CONFIGURATION</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">CA Firm Settings & Disclaimers</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure firm branding, membership registration, disclaimers and operating modes.
        </p>
      </div>

      {/* Mode Switcher Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">System Operating Mode</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Current Mode:{' '}
              {isLive ? (
                <strong className="text-emerald-700">
                  LIVE SYSTEM ({briefingSource === 'GMAIL' ? 'Gmail Briefing Ingested' : 'Gmail OAuth Connected'})
                </strong>
              ) : (
                <strong className="text-amber-700">DEMO MODE ACTIVE (Simulated Regulatory Data)</strong>
              )}
            </p>
          </div>

          <div>
            {isLive ? (
              <span className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                <Check className="w-3.5 h-3.5 mr-1" />
                Live Gmail Integration Active
              </span>
            ) : (
              <button
                onClick={handleConnectGmail}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
              >
                Connect Gmail for Live Mode
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Gmail OAuth Integration Status Box */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="flex items-start space-x-3">
            <div className="p-2.5 bg-teal-50 text-teal-700 rounded-xl shrink-0">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-slate-900">Gmail Daily Briefing Ingestion Status</h3>
                {getStatusBadge()}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Google OAuth 2.0 Read-Only Integration
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {gmailState.isConnected ? (
              <>
                <button
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                  <span>Test Gmail Connection</span>
                </button>
                <button
                  onClick={handleDisconnectGmail}
                  className="px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-xs rounded-xl transition-all flex items-center space-x-1 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Disconnect</span>
                </button>
              </>
            ) : (
              <button
                onClick={handleConnectGmail}
                className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center space-x-2 cursor-pointer"
              >
                <Key className="w-4 h-4" />
                <span>CONNECT GMAIL</span>
              </button>
            )}
          </div>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Connection Status
            </span>
            <span className="font-bold text-slate-800">
              {gmailState.isConnected ? 'Connected & Authorized' : gmailState.status}
            </span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Google Account Email
            </span>
            <span className="font-bold text-slate-800 truncate block">
              {gmailState.userEmail || (gmailState.isConnected ? 'OAuth Active' : 'Not Authenticated')}
            </span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Authorized OAuth Scope
            </span>
            <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px] font-mono text-teal-800 block truncate">
              https://www.googleapis.com/auth/gmail.readonly
            </code>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
            <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Last Successful Sync
            </span>
            <span className="font-mono text-slate-700 text-[11px]">
              {gmailState.lastSyncTime || 'No sync performed yet'}
            </span>
          </div>
        </div>

        {/* Diagnostic log output */}
        {testResult && (
          <div className="p-3 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs space-y-1">
            <p className="font-bold text-teal-400">GMAIL CONNECTION DIAGNOSTIC:</p>
            <p>{testResult}</p>
          </div>
        )}

        {gmailState.errorMessage && (
          <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-xl text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{gmailState.errorMessage}</span>
          </div>
        )}
      </div>

      {/* Firm Profile Settings Form */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
          <Building className="w-5 h-5 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900">CA Practice & Advisory Branding Profile</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">CA Firm Name *</label>
              <input
                type="text"
                required
                value={firmName}
                onChange={(e) => setFirmName(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Principal CA Name *</label>
              <input
                type="text"
                required
                value={caName}
                onChange={(e) => setCaName(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">ICAI Membership No *</label>
              <input
                type="text"
                required
                value={membershipNo}
                onChange={(e) => setMembershipNo(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Official Email</label>
              <input
                type="email"
                required
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Contact Phone</label>
              <input
                type="text"
                required
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
              />
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Firm Address</label>
            <input
              type="text"
              value={firmAddress}
              onChange={(e) => setFirmAddress(e.target.value)}
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Mandatory CA Statutory Disclaimer</label>
            <textarea
              rows={3}
              value={disclaimer}
              onChange={(e) => setDisclaimer(e.target.value)}
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs"
            />
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
            {savedSuccess && (
              <span className="flex items-center space-x-1.5 text-emerald-600 font-bold text-xs">
                <Check className="w-4 h-4" />
                <span>Settings Saved Successfully!</span>
              </span>
            )}
            <div className="ml-auto">
              <button
                type="submit"
                className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all cursor-pointer"
              >
                <Save className="w-4 h-4" />
                <span>SAVE BRAND SETTINGS</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
