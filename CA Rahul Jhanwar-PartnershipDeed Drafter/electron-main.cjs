const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const { execSync } = require('child_process');

app.commandLine.appendSwitch('allow-file-access-from-files');

const VENDOR_SECRET_SALT = 'DUMMY_SALT_KEY';
const MASTER_EMERGENCY_KEY = 'DUMMY_EMERGENCY_KEY';
const TRIAL_DURATION_SECONDS = 30 * 60; // 1800s (30 mins)

// Helper: Run shell command safely
function runCmd(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf8', timeout: 3500 }).trim();
  } catch {
    return '';
  }
}

// 1. Detect Real Hardware Fingerprint
let cachedHardwareId = null;
function getHardwareId() {
  if (cachedHardwareId) return cachedHardwareId;

  const parts = [];

  // (A) Windows MachineGuid from Registry (Permanent, unique per Windows installation)
  const regGuid = runCmd('reg query "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid');
  const matchGuid = regGuid.match(/MachineGuid\s+REG_SZ\s+([A-Fa-f0-9\-]+)/i);
  if (matchGuid) parts.push('GUID:' + matchGuid[1].trim());

  // (B) Motherboard UUID via PowerShell CIM
  const psUuid = runCmd('powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"');
  if (psUuid && !psUuid.includes('FFFFFFFF') && psUuid.length > 10) {
    parts.push('UUID:' + psUuid.trim());
  }

  // (C) Physical Network MAC Addresses
  try {
    const nets = os.networkInterfaces();
    const macs = [];
    for (const name of Object.keys(nets)) {
      for (const net of nets[name] || []) {
        if (net.mac && net.mac !== '00:00:00:00:00:00' && !net.internal) {
          macs.push(net.mac.toLowerCase());
        }
      }
    }
    if (macs.length > 0) {
      parts.push('MAC:' + macs.sort()[0]);
    }
  } catch {}

  // (D) Machine Host & Arch fallback
  parts.push('ARCH:' + os.arch());
  parts.push('HOST:' + os.hostname().toUpperCase());

  const raw = parts.join('||');
  const hash = crypto.createHash('sha256').update(raw).digest('hex').toUpperCase();

  cachedHardwareId = `PDD-HWID-${hash.slice(0, 4)}-${hash.slice(4, 8)}-${hash.slice(8, 12)}-${hash.slice(12, 16)}`;
  return cachedHardwareId;
}

// 2. Cryptographic Key Engine
function computeLicenseKey(hwId, salt = VENDOR_SECRET_SALT) {
  const cleanId = hwId.trim().toUpperCase();
  const hmac = crypto.createHmac('sha256', salt).update(cleanId).digest('hex').toUpperCase();
  return `PDD-ACTV-${hmac.slice(0, 4)}-${hmac.slice(4, 8)}-${hmac.slice(8, 12)}-${hmac.slice(12, 16)}`;
}

function isValidKey(key, hwId) {
  const cleanKey = (key || '').trim().toUpperCase();
  if (cleanKey === MASTER_EMERGENCY_KEY) return true;
  const expected = computeLicenseKey(hwId);
  return cleanKey === expected;
}

// 3. Persistent Hardware Store Management (ProgramData + LocalAppData + Windows Registry)
function getStorageLocations() {
  const pData = process.env.ALLUSERSPROFILE || 'C:\\ProgramData';
  const lApp = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
  return {
    programDataFile: path.join(pData, 'PDDrafter', '.hw_lic.sys'),
    localAppDataFile: path.join(lApp, 'PDDrafter', '.hw_state.dat')
  };
}

function computeStateSignature(state) {
  const payload = `${state.hwId}|${state.firstInstalled}|${state.accumulatedSeconds}|${state.isExpired}|${state.isActivated}|${state.licenseKey || ''}`;
  return crypto.createHmac('sha256', VENDOR_SECRET_SALT).update(payload).digest('hex');
}

function savePersistentState(state) {
  state.signature = computeStateSignature(state);
  const jsonStr = JSON.stringify(state);
  const { programDataFile, localAppDataFile } = getStorageLocations();

  try {
    const dir1 = path.dirname(programDataFile);
    if (!fs.existsSync(dir1)) fs.mkdirSync(dir1, { recursive: true });
    fs.writeFileSync(programDataFile, jsonStr, 'utf8');
  } catch (e) {
    console.warn('[Hardware License] ProgramData write error:', e.message);
  }

  try {
    const dir2 = path.dirname(localAppDataFile);
    if (!fs.existsSync(dir2)) fs.mkdirSync(dir2, { recursive: true });
    fs.writeFileSync(localAppDataFile, jsonStr, 'utf8');
  } catch (e) {
    console.warn('[Hardware License] LocalAppData write error:', e.message);
  }

  try {
    const b64 = Buffer.from(jsonStr).toString('base64');
    runCmd(`reg add "HKCU\\Software\\PDDrafter" /v "HwState" /t REG_SZ /d "${b64}" /f`);
  } catch (e) {
    console.warn('[Hardware License] Registry backup error:', e.message);
  }
}

function loadPersistentState(hwId) {
  const { programDataFile, localAppDataFile } = getStorageLocations();
  let candidateStr = null;

  // Check 1: ProgramData
  if (fs.existsSync(programDataFile)) {
    try { candidateStr = fs.readFileSync(programDataFile, 'utf8'); } catch {}
  }

  // Check 2: LocalAppData
  if (!candidateStr && fs.existsSync(localAppDataFile)) {
    try { candidateStr = fs.readFileSync(localAppDataFile, 'utf8'); } catch {}
  }

  // Check 3: Windows Registry
  if (!candidateStr) {
    try {
      const regOut = runCmd('reg query "HKCU\\Software\\PDDrafter" /v "HwState"');
      const match = regOut.match(/HwState\s+REG_SZ\s+([A-Za-z0-9+/=]+)/);
      if (match) {
        candidateStr = Buffer.from(match[1], 'base64').toString('utf8');
      }
    } catch {}
  }

  if (candidateStr) {
    try {
      const parsed = JSON.parse(candidateStr);
      const expectedSig = computeStateSignature(parsed);
      // Valid signature & matching hardware ID
      if (parsed.signature === expectedSig && parsed.hwId === hwId) {
        return parsed;
      }
    } catch (e) {
      console.warn('[Hardware License] State parse error:', e.message);
    }
  }

  return null;
}

// 4. In-Memory Active Hardware License State
let activeState = null;

function initializeHardwareLicense() {
  const hwId = getHardwareId();
  let state = loadPersistentState(hwId);

  if (!state) {
    // Brand new machine installation
    state = {
      hwId,
      firstInstalled: Date.now(),
      accumulatedSeconds: 0,
      isExpired: false,
      isActivated: false,
      licenseKey: '',
      lastTick: Date.now()
    };
    savePersistentState(state);
  } else {
    // If existing state has reached 1800s, enforce expired
    if (!state.isActivated && state.accumulatedSeconds >= TRIAL_DURATION_SECONDS) {
      state.isExpired = true;
    }
    state.lastTick = Date.now();
    savePersistentState(state);
  }

  activeState = state;
  return activeState;
}

// IPC Handlers
ipcMain.handle('get-hardware-state', async () => {
  if (!activeState) initializeHardwareLicense();
  const remaining = Math.max(0, TRIAL_DURATION_SECONDS - (activeState.accumulatedSeconds || 0));
  return {
    hwId: activeState.hwId,
    accumulatedSeconds: activeState.accumulatedSeconds || 0,
    remainingSeconds: remaining,
    totalTrialSeconds: TRIAL_DURATION_SECONDS,
    isExpired: activeState.isExpired || (!activeState.isActivated && remaining <= 0),
    isActivated: !!activeState.isActivated,
    licenseKey: activeState.licenseKey || '',
    firstInstalled: activeState.firstInstalled
  };
});

ipcMain.handle('tick-trial', async (event, secondsToAdd) => {
  if (!activeState) initializeHardwareLicense();
  if (activeState.isActivated) {
    return { isActivated: true, isExpired: false, remainingSeconds: TRIAL_DURATION_SECONDS };
  }

  const inc = typeof secondsToAdd === 'number' && secondsToAdd > 0 && secondsToAdd < 60 ? secondsToAdd : 5;
  activeState.accumulatedSeconds = (activeState.accumulatedSeconds || 0) + inc;
  activeState.lastTick = Date.now();

  if (activeState.accumulatedSeconds >= TRIAL_DURATION_SECONDS) {
    activeState.isExpired = true;
  }

  savePersistentState(activeState);

  const remaining = Math.max(0, TRIAL_DURATION_SECONDS - activeState.accumulatedSeconds);
  return {
    hwId: activeState.hwId,
    accumulatedSeconds: activeState.accumulatedSeconds,
    remainingSeconds: remaining,
    totalTrialSeconds: TRIAL_DURATION_SECONDS,
    isExpired: activeState.isExpired,
    isActivated: false
  };
});

ipcMain.handle('activate-key', async (event, keyInput) => {
  if (!activeState) initializeHardwareLicense();
  const key = (keyInput || '').trim().toUpperCase();

  if (isValidKey(key, activeState.hwId)) {
    activeState.isActivated = true;
    activeState.isExpired = false;
    activeState.licenseKey = key;
    activeState.activatedAt = new Date().toISOString();
    savePersistentState(activeState);
    return { success: true, message: 'Software activated successfully with lifetime access!' };
  } else {
    return { success: false, error: 'Invalid activation key for this computer hardware ID.' };
  }
});

let mainWindow = null;

function createWindow() {
  initializeHardwareLicense();

  mainWindow = new BrowserWindow({
    width: 1366,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    title: "Partnership Deed Drafter - Indian Legal Conveyancing Suite",
    icon: path.join(__dirname, 'public', 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
      sandbox: false,
      preload: path.join(__dirname, 'electron-preload.cjs')
    }
  });

  Menu.setApplicationMenu(null);

  let indexPath = path.join(__dirname, 'dist', 'index.html');
  if (!fs.existsSync(indexPath)) {
    indexPath = path.join(process.resourcesPath, 'app', 'dist', 'index.html');
  }

  mainWindow.loadFile(indexPath);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
