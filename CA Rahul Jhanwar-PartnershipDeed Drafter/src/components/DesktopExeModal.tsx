import React, { useState } from 'react';
import { 
  X, 
  Monitor, 
  Terminal, 
  Download, 
  FolderDown, 
  CheckCircle2, 
  Copy, 
  FileCode, 
  Laptop, 
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  Cpu,
  KeyRound,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { downloadDesktopLauncherBat, downloadStandaloneHtml } from '../utils/deedEngine';
import { DeedFormData } from '../types';
import { usePWAInstall } from '../hooks/usePWAInstall';
import { 
  getOrCreateMachineId, 
  resetTrialTimer, 
  deactivateLicense, 
  generateLicenseKey,
  MASTER_EMERGENCY_KEY 
} from '../utils/licenseManager';

interface DesktopExeModalProps {
  isOpen: boolean;
  onClose: () => void;
  formData: DeedFormData;
}

export const DesktopExeModal: React.FC<DesktopExeModalProps> = ({
  isOpen,
  onClose,
  formData,
}) => {
  const [activeTab, setActiveTab] = useState<'pwa' | 'bat' | 'electron' | 'licensing' | 'portable'>('pwa');
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [testResetSuccess, setTestResetSuccess] = useState(false);
  const { isInstallable, isInstalled, install } = usePWAInstall();

  if (!isOpen) return null;

  const currentMachineId = getOrCreateMachineId();
  const sampleKey = generateLicenseKey(currentMachineId);

  const handleResetTrialForTesting = () => {
    resetTrialTimer();
    deactivateLicense();
    setTestResetSuccess(true);
    setTimeout(() => setTestResetSuccess(false), 3000);
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2500);
  };

  const electronPackageJsonSnippet = `{
  "name": "partnership-deed-desktop",
  "version": "1.0.0",
  "main": "electron-main.cjs",
  "scripts": {
    "start": "electron .",
    "build:exe": "electron-builder --win portable"
  },
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0"
  }
}`;

  const electronMainSnippet = `const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    title: "Partnership Deed Drafter",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Load production build or offline bundle
  win.loadFile('dist/index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-8">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 text-slate-900">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-700 flex items-center justify-center text-white shadow-sm">
              <Monitor className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Desktop Base Application & .EXE Setup</h2>
              <p className="text-xs text-slate-500">
                Run, install, or compile this legal drafting application as a standalone desktop executable
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('pwa')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'pwa'
                ? 'border-blue-700 text-blue-700 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Laptop className="w-4 h-4" />
            1. Desktop App (1-Click PWA)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('bat')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'bat'
                ? 'border-blue-700 text-blue-700 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Terminal className="w-4 h-4" />
            2. Windows Launcher (.BAT)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('electron')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'electron'
                ? 'border-blue-700 text-blue-700 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Cpu className="w-4 h-4" />
            2. Native Windows .EXE Build
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('licensing')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'licensing'
                ? 'border-indigo-700 text-indigo-700 bg-white shadow-xs font-bold'
                : 'border-transparent text-indigo-900 hover:text-indigo-950 font-bold bg-indigo-50/70'
            }`}
          >
            <KeyRound className="w-4 h-4 text-indigo-600" />
            3. 🔑 Selling & 30-Min Trial Lock
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('bat')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'bat'
                ? 'border-blue-700 text-blue-700 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Terminal className="w-4 h-4" />
            4. Windows Launcher (.BAT)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('portable')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition whitespace-nowrap ${
              activeTab === 'portable'
                ? 'border-blue-700 text-blue-700 bg-white shadow-xs'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileCode className="w-4 h-4" />
            5. Portable Offline Bundle
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          
          {/* TAB 1: PWA Direct Desktop Installation */}
          {activeTab === 'pwa' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                <h3 className="text-sm font-bold text-blue-900 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-700" />
                  Instant Desktop Installation (Zero Dependencies Required)
                </h3>
                <p className="text-xs text-blue-800 mt-1 leading-relaxed">
                  You can install this Partnership Deed Drafting software directly to your Windows, macOS, or Linux desktop. It runs in its own dedicated window without browser toolbars, creates a desktop icon, and works completely offline.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="font-bold text-slate-900 text-sm mb-2">Option A: 1-Click Install Button</div>
                  <p className="text-xs text-slate-600 mb-4">
                    If supported by your browser (Chrome, Edge, Brave, Opera), click the button below to pin this app to your Desktop and Taskbar.
                  </p>
                  {isInstalled ? (
                    <div className="flex items-center gap-2 text-emerald-700 text-xs font-semibold bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
                      <CheckCircle2 className="w-4 h-4" />
                      App is currently running in Desktop Standalone Mode!
                    </div>
                  ) : isInstallable ? (
                    <button
                      type="button"
                      onClick={install}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-xs transition"
                    >
                      <FolderDown className="w-4 h-4" />
                      Install to Desktop Now
                    </button>
                  ) : (
                    <div className="text-xs text-slate-500 bg-white p-3 rounded-lg border border-slate-200">
                      Browser install prompt is active. If the button is not clickable, use Option B on the right.
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="font-bold text-slate-900 text-sm mb-2">Option B: Manual Browser Shortcut</div>
                  <ol className="text-xs text-slate-700 space-y-2 list-decimal list-inside">
                    <li>In your browser (Google Chrome or Microsoft Edge), open the menu <b>(⋮ or ...)</b> in the top right.</li>
                    <li>Click <b>"Cast, save, and share"</b> or <b>"Apps"</b> / <b>"More Tools"</b>.</li>
                    <li>Select <b>"Install Partnership Deed Drafter..."</b> or <b>"Create shortcut... (check Open as window)"</b>.</li>
                    <li>Click <b>Install</b>. A desktop shortcut will appear on your desktop immediately!</li>
                  </ol>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Windows Desktop Launcher .BAT */}
          {activeTab === 'bat' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-blue-700" />
                  Windows Desktop Launcher (.BAT)
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  Download a pre-configured Windows batch launcher that boots the local Express/Vite server and opens a dedicated app window automatically.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs overflow-x-auto relative">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-slate-400">
                  <span>Launch_Partnership_Deed_Desktop.bat</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(`@echo off\ntitle Partnership Deed Desktop\ncall npm run build\nstart "Deed Server" /B node dist\\server.cjs\ntimeout /t 2 /nobreak >nul\nstart msedge --app="http://localhost:3000"`, 'bat')}
                    className="flex items-center gap-1 text-[11px] hover:text-white"
                  >
                    <Copy className="w-3 h-3" />
                    {copiedCode === 'bat' ? 'Copied!' : 'Copy Script'}
                  </button>
                </div>
                <pre className="text-emerald-400">
{`@echo off
title Partnership Deed Drafter Desktop Launcher
color 1F
echo Starting local application server...
start "Deed Server" /B node dist\\server.cjs
timeout /t 2 /nobreak >nul
echo Opening Standalone Desktop Window...
start msedge --app="http://localhost:3000" || start chrome --app="http://localhost:3000"`}
                </pre>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => downloadDesktopLauncherBat(formData.firmName || 'Partnership Deed Drafter')}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-xs transition"
                >
                  <Download className="w-4 h-4" />
                  Download Launch_Partnership_Deed_Desktop.bat
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: Electron .EXE Guide */}
          {activeTab === 'electron' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-700" />
                  Compiling into a Standalone Windows Executable (.EXE)
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  To package this application into a standalone <b>.exe</b> file (portable executable or installer for distribution to clients or staff), use Electron or Tauri:
                </p>
              </div>

              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-800">
                  Step 1: Install Electron & Builder
                </div>
                <div className="bg-slate-900 text-slate-200 p-3 rounded-lg text-xs font-mono flex justify-between items-center">
                  <span>npm install -D electron electron-builder</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard('npm install -D electron electron-builder', 'c1')}
                    className="text-slate-400 hover:text-white"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="text-xs font-bold text-slate-800">
                  Step 2: Create <code className="bg-slate-100 px-1 py-0.5 rounded text-blue-700">electron-main.cjs</code>
                </div>
                <div className="bg-slate-900 text-slate-200 p-3 rounded-lg text-xs font-mono relative">
                  <button
                    type="button"
                    onClick={() => copyToClipboard(electronMainSnippet, 'c2')}
                    className="absolute top-3 right-3 text-slate-400 hover:text-white flex items-center gap-1 text-[11px]"
                  >
                    <Copy className="w-3 h-3" />
                    {copiedCode === 'c2' ? 'Copied!' : 'Copy'}
                  </button>
                  <pre className="text-slate-300 max-h-40 overflow-y-auto">
                    {electronMainSnippet}
                  </pre>
                </div>

                <div className="text-xs font-bold text-slate-800">
                  Step 3: Build Windows .EXE Executable
                </div>
                <div className="bg-slate-900 text-slate-200 p-3 rounded-lg text-xs font-mono flex justify-between items-center">
                  <span>npx electron-builder --win --x64</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard('npx electron-builder --win --x64', 'c3')}
                    className="text-slate-400 hover:text-white"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  The compiled <b>Partnership_Deed_Setup.exe</b> or portable <b>.exe</b> will be generated in the <code className="bg-slate-100 px-1 rounded">dist/</code> directory ready for instant distribution.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: Selling & 30-Min Trial Lock System */}
          {activeTab === 'licensing' && (
            <div className="space-y-5">
              
              <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 text-indigo-950 space-y-2">
                <h3 className="text-sm font-bold flex items-center gap-2 text-indigo-900">
                  <KeyRound className="w-4 h-4 text-indigo-600" />
                  Commercial Selling & 30-Minute Trial Protection
                </h3>
                <p className="text-xs leading-relaxed text-indigo-900/90">
                  Jab bhi koi naya customer aapka software apne computer me chalayega, use <b>30 Minutes ka free trial</b> milega. 30 minutes khatam hote hi software <b>poori tarah lock</b> ho jayega. Usko unlock karne ke liye aapki di hui <b>Activation Key</b> lagegi!
                </p>
              </div>

              {/* Step by Step Workflow */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Client Ko Sell Karne Ka Complete Process:
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
                    <div className="font-bold text-blue-700">1. Client Installs & Tries</div>
                    <p className="text-slate-600 text-[11px]">
                      Client 30 mins tak deed draft aur test karega. 30 min baad lock screen par uska unique <b>Machine ID</b> dikhega.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
                    <div className="font-bold text-indigo-700">2. Aap Key Generate Karein</div>
                    <p className="text-slate-600 text-[11px]">
                      Client apna Machine ID aapko WhatsApp karega. Aap apne <b>License Generator</b> tool me daalkar 1-click me Key banayenge.
                    </p>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
                    <div className="font-bold text-emerald-700">3. Lifetime Access Unlock</div>
                    <p className="text-slate-600 text-[11px]">
                      Client key enter karega aur uska software lifetime ke liye activate ho jayega! Ye key kisi aur PC par kaam nahi karegi.
                    </p>
                  </div>
                </div>
              </div>

              {/* Open License Generator Button */}
              <div className="p-4 bg-slate-900 rounded-xl text-white flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <div className="font-bold text-sm flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    Aapka Admin License Key Generator Tool
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    File: <code className="text-emerald-400 font-mono">public/license-generator.html</code> (Offline chalta hai)
                  </div>
                </div>

                <a
                  href="/license-generator.html"
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-lg shadow-md transition flex items-center gap-1.5 shrink-0 cursor-pointer"
                >
                  <span>Open Key Generator</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {/* Current Machine ID & Key Preview */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                <div className="font-bold text-slate-800">Testing & Debug Info on This PC:</div>
                <div className="flex items-center justify-between text-slate-600">
                  <span>Is Computer Ka Machine ID:</span>
                  <code className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-300">
                    {currentMachineId}
                  </code>
                </div>
                <div className="flex items-center justify-between text-slate-600">
                  <span>Is PC Ki Matching Activation Key:</span>
                  <code className="font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {sampleKey}
                  </code>
                </div>
                <div className="flex items-center justify-between text-slate-600">
                  <span>Universal Master Emergency Key:</span>
                  <code className="font-mono font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    {MASTER_EMERGENCY_KEY}
                  </code>
                </div>

                <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                  <button
                    type="button"
                    onClick={handleResetTrialForTesting}
                    className="flex items-center gap-1.5 text-slate-600 hover:text-red-700 transition text-[11px] font-semibold cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Reset 30-Min Trial (For Testing Lock)</span>
                  </button>

                  {testResetSuccess && (
                    <span className="text-emerald-600 font-bold text-[11px]">
                      ✅ Trial Reset to 30 mins!
                    </span>
                  )}
                </div>
              </div>

            </div>
          )}

          {/* TAB 4: Portable Offline Bundle */}
          {activeTab === 'portable' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-blue-700" />
                  Single-File Portable HTML Legal Suite
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  Download the complete partnership deed document and offline drafter as a single independent file. Double-click to open in any web browser or Word on any desktop computer without needing internet connection.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-slate-900">
                      Standalone Legal Deed Package (.html)
                    </div>
                    <div className="text-xs text-slate-500">
                      Contains fully rendered deed with your current parameters and formatting
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => downloadStandaloneHtml(formData)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-xs transition"
                  >
                    <Download className="w-4 h-4" />
                    Download Portable File
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-200 text-xs">
          <span className="text-slate-500">
            Complies with Indian Partnership Act, 1932 & Income-tax Act, 2025
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-lg transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
