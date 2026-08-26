// main.js — Electron desktop shell for the CA Task Delegation App.
//
// This app can run in one of two modes, chosen once on first launch and
// remembered afterwards:
//   - "host"   — starts the actual server (server.js) and opens a window
//                pointed at it. Use this on the one computer that will
//                hold the shared database.
//   - "client" — opens a window pointed at another computer's host copy
//                over the local network. Use this on every teammate's PC.
//
// The same installer/app works for both — the choice is just saved locally.
//
// Important: the server is started as a SEPARATE process using the
// computer's own installed Node.js (the same `node` command used to run
// this app the plain way), NOT required directly into Electron's process.
// Electron bundles its own, older copy of Node.js internally, which does
// not include the newer database feature (node:sqlite) this app depends
// on — running the server in-process would silently fail. Spawning the
// real system Node.js avoids that mismatch entirely.
'use strict';

const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
const { spawn } = require('node:child_process');

const CONFIG_PATH = path.join(app.getPath('userData'), 'launcher-config.json');
const HOST_PORT = 3000;

let mainWindow = null;
let setupWindow = null;
let serverProcess = null;

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (e) {
    return null;
  }
}

function saveConfig(cfg) {
  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
}

function buildMenu() {
  const template = [
    {
      label: 'App',
      submenu: [
        {
          label: 'Change Server Connection…',
          click: () => {
            if (mainWindow) { mainWindow.close(); mainWindow = null; }
            showSetupWindow();
          },
        },
        { type: 'separator' },
        { role: 'reload' },
        { role: 'toggledevtools' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createMainWindow(url) {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 980,
    minHeight: 640,
    title: 'CA Task Delegation App',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    backgroundColor: '#eff6ff',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  buildMenu();
  mainWindow.loadURL(url);

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    dialog.showErrorBox(
      'Could not connect',
      `Could not reach the app at ${url}.\n\n` +
      `If this is the "connect to another computer" mode, make sure that ` +
      `computer's copy of the app is running and that you're on the same ` +
      `Wi-Fi/network.\n\nDetails: ${errorDescription}`
    );
  });
}

// Polls the given local port until the server answers, or times out.
function waitForServer(port, timeoutMs) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    (function attempt() {
      const req = http.get({ host: '127.0.0.1', port, path: '/login.html', timeout: 1500 }, (res) => {
        res.resume();
        resolve();
      });
      req.on('error', () => {
        if (Date.now() > deadline) { reject(new Error('The app server did not start in time.')); return; }
        setTimeout(attempt, 300);
      });
      req.on('timeout', () => {
        req.destroy();
        if (Date.now() > deadline) { reject(new Error('The app server did not start in time.')); return; }
        setTimeout(attempt, 300);
      });
    })();
  });
}

// Starts server.js as a child process using the system's own Node.js
// (found on PATH, same as the "Requirements" section in the README) and
// resolves once it's actually answering requests. Rejects with a clear,
// human-readable message on failure.
async function launchHostMode() {
  // If a copy of the server is already running on our port (a previous
  // launch of this app, or someone started it the plain `node server.js`
  // way), just reuse it instead of spawning a duplicate that would fail
  // to bind the same port anyway.
  const alreadyRunning = await waitForServer(HOST_PORT, 700).then(() => true).catch(() => false);
  if (alreadyRunning) return HOST_PORT;
  return spawnHostServer();
}

function spawnHostServer() {
  return new Promise((resolve, reject) => {
    let settled = false;
    const settle = (fn, arg) => { if (!settled) { settled = true; fn(arg); } };

    const nodeCmd = process.platform === 'win32' ? 'node.exe' : 'node';
    try {
      serverProcess = spawn(nodeCmd, ['server.js'], {
        cwd: __dirname,
        env: Object.assign({}, process.env, { PORT: String(HOST_PORT) }),
        windowsHide: true,
      });
    } catch (err) {
      settle(reject, new Error(
        'Could not start Node.js on this computer. Please make sure Node.js ' +
        '(version 22.5 or newer) is installed from https://nodejs.org, then try again.'
      ));
      return;
    }

    serverProcess.stdout.on('data', (d) => process.stdout.write(String(d)));
    serverProcess.stderr.on('data', (d) => process.stderr.write(String(d)));

    serverProcess.on('error', (err) => {
      if (err && err.code === 'ENOENT') {
        settle(reject, new Error(
          'Node.js was not found on this computer. Please install it from ' +
          'https://nodejs.org (version 22.5 or newer), then try again.'
        ));
      } else {
        settle(reject, new Error(String((err && err.message) || err)));
      }
    });

    serverProcess.on('exit', (code) => {
      if (!settled) {
        settle(reject, new Error(`The app server stopped unexpectedly (exit code ${code}). Make sure no other copy of the app is already running.`));
      }
    });

    waitForServer(HOST_PORT, 20000).then(() => {
      settle(resolve, HOST_PORT);
    }).catch((err) => {
      settle(reject, err);
    });
  });
}

function launchClientMode(serverIp) {
  createMainWindow(`http://${serverIp}:${HOST_PORT}/login.html`);
}

function showSetupWindow() {
  setupWindow = new BrowserWindow({
    width: 520,
    height: 480,
    resizable: false,
    title: 'CA Task App — Setup',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    autoHideMenuBar: true,
    backgroundColor: '#eff6ff',
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'setup-preload.js'),
    },
  });
  setupWindow.setMenuBarVisibility(false);
  setupWindow.loadFile('setup.html');
}

ipcMain.handle('setup-complete', async (event, choice) => {
  try {
    if (choice.mode === 'host') {
      const port = await launchHostMode();
      createMainWindow(`http://localhost:${port}/login.html`);
    } else {
      launchClientMode(choice.serverIp.trim());
    }
    // Only save the choice and close the setup window once we know it worked —
    // otherwise a failed attempt would be remembered and repeat on every launch.
    if (choice.mode === 'host') {
      saveConfig({ mode: 'host' });
    } else {
      saveConfig({ mode: 'client', serverIp: choice.serverIp.trim() });
    }
    if (setupWindow) { setupWindow.close(); setupWindow = null; }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String((err && err.message) || err) };
  }
});

app.whenReady().then(async () => {
  const cfg = loadConfig();
  if (!cfg) {
    showSetupWindow();
    return;
  }
  buildMenu();
  try {
    if (cfg.mode === 'host') {
      const port = await launchHostMode();
      createMainWindow(`http://localhost:${port}/login.html`);
    } else {
      launchClientMode(cfg.serverIp);
    }
  } catch (err) {
    dialog.showErrorBox('Could not start the app', String((err && err.message) || err));
    showSetupWindow();
  }
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('before-quit', () => {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
});
