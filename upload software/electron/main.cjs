const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const path = require("path");
const http = require("http");
const fs = require("fs");

// ─── Configuration ────────────────────────────────────────────────────────────
const SERVER_PORT = 3000;
const SERVER_URL = `http://127.0.0.1:${SERVER_PORT}`;
const MAX_WAIT_MS = 20000; // 20 seconds max to wait for server
const POLL_INTERVAL_MS = 200;

let mainWindow = null;

// ─── Load .env / config.env for GEMINI_API_KEY ────────────────────────────────
function loadEnv() {
  const locations = [
    path.join(process.resourcesPath || "", "config.env"),
    path.join(path.dirname(app.getPath("exe")), "config.env"),
    path.join(__dirname, "..", ".env"),
    path.join(__dirname, "..", "config.env"),
  ];

  for (const loc of locations) {
    if (fs.existsSync(loc)) {
      try {
        const lines = fs.readFileSync(loc, "utf8").split(/\r?\n/);
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith("#")) continue;
          const eqIdx = trimmed.indexOf("=");
          if (eqIdx > 0) {
            const key = trimmed.slice(0, eqIdx).trim();
            const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
            if (!process.env[key]) process.env[key] = val;
          }
        }
        console.log(`[Electron] Loaded env from: ${loc}`);
      } catch (e) {
        console.warn(`[Electron] Could not read env from ${loc}:`, e.message);
      }
      break;
    }
  }
}

// ─── Resolve the bundled server path ─────────────────────────────────────────
function getServerPath() {
  const candidates = [
    path.join(process.resourcesPath || "", "dist", "server.cjs"),
    path.join(process.resourcesPath || "", "app.asar.unpacked", "dist", "server.cjs"),
    path.join(process.resourcesPath || "", "app.asar", "dist", "server.cjs"),
    path.join(process.resourcesPath || "", "app", "dist", "server.cjs"),
    path.join(__dirname, "..", "dist", "server.cjs"),
    path.join(app.getAppPath(), "dist", "server.cjs"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// ─── Start Express Server (In-Process) ───────────────────────────────────────
function startServer() {
  const serverPath = getServerPath();
  if (!serverPath) {
    throw new Error(
      "Could not find dist/server.cjs. Please build the app first.\n\nRun: install-and-run.bat"
    );
  }

  console.log(`[Electron] Starting in-process server from: ${serverPath}`);

  const exeDir = path.dirname(app.getPath("exe"));
  const userDataDir = path.join(app.getPath("userData"), "data");
  const configEnvPath = path.join(exeDir, "config.env");

  process.env.NODE_ENV = "production";
  process.env.PORT = String(SERVER_PORT);
  process.env.ACCUSHEET_DATA_DIR = userDataDir;
  if (fs.existsSync(configEnvPath)) {
    process.env.ACCUSHEET_CONFIG_PATH = configEnvPath;
  }

  // Load and start the server in the Electron main process
  require(serverPath);
}

// ─── Poll until server responds ───────────────────────────────────────────────
function waitForServer(timeout = MAX_WAIT_MS) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function check() {
      const req = http.get(SERVER_URL, (res) => {
        resolve();
      });
      req.on("error", (err) => {
        if (Date.now() - start > timeout) {
          reject(new Error(`Server did not respond within ${timeout / 1000}s (${err.message})`));
        } else {
          setTimeout(check, POLL_INTERVAL_MS);
        }
      });
      req.setTimeout(1000, () => {
        req.destroy();
      });
    }
    check();
  });
}

// ─── Create the main window ───────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "AccuSheet Pro",
    backgroundColor: "#E4E3E0",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false,
  });

  mainWindow.loadURL(SERVER_URL);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Open DevTools in development mode
  if (process.env.NODE_ENV === "development") {
    mainWindow.webContents.openDevTools();
  }
}

// ─── App lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  loadEnv();

  // Show loading splash while server starts
  const splash = new BrowserWindow({
    width: 420,
    height: 260,
    frame: false,
    alwaysOnTop: true,
    transparent: false,
    resizable: false,
    backgroundColor: "#1a1d2e",
  });

  splash.loadURL(
    "data:text/html," +
      encodeURIComponent(`
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          background: #1a1d2e;
          color: #f5f5f5;
          font-family: 'Segoe UI', system-ui, sans-serif;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100vh;
          gap: 20px;
        }
        h1 { font-size: 22px; font-weight: 600; color: #f5a623; letter-spacing: 0.5px; }
        p  { font-size: 13px; color: #9ca3af; }
        .spinner {
          width: 36px; height: 36px;
          border: 3px solid #2d3150;
          border-top-color: #f5a623;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      </style>
    </head>
    <body>
      <div class="spinner"></div>
      <h1>AccuSheet Pro</h1>
      <p>Starting application, please wait…</p>
    </body>
    </html>
  `)
  );

  try {
    startServer();
    await waitForServer();

    createWindow();
    setTimeout(() => {
      if (!splash.isDestroyed()) splash.close();
    }, 500);
  } catch (err) {
    if (!splash.isDestroyed()) splash.close();
    dialog.showErrorBox("AccuSheet Pro — Startup Error", err.stack || err.message);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
