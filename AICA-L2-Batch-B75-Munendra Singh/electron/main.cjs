const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1366,
    height: 850,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#E4E3E0',
    title: 'FinAudit AI — Ind AS Statutory Financial Statement Auditor & Consistency Verifier',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
      sandbox: false,
    },
  });

  const appPath = app.getAppPath();
  const candidates = [
    path.join(__dirname, '../dist/index.html'),
    path.join(appPath, 'dist/index.html'),
    path.join(__dirname, 'dist/index.html'),
  ];

  let loaded = false;
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      mainWindow.loadFile(candidate);
      loaded = true;
      break;
    }
  }

  if (!loaded) {
    // Fallback to local server
    const devUrl = 'http://localhost:3000';
    mainWindow.loadURL(devUrl).catch(() => {
      setTimeout(() => mainWindow.loadURL(devUrl), 1500);
    });
  }

  // Create Application Menu
  const menuTemplate = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Print / Save as PDF...',
          accelerator: 'CmdOrCtrl+P',
          click: () => {
            mainWindow.webContents.print();
          },
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => app.quit(),
        },
      ],
    },
    {
      label: 'Audit Tools',
      submenu: [
        {
          label: 'Reload Workspace',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow.reload(),
        },
        {
          label: 'Toggle Full Screen',
          accelerator: 'F11',
          click: () => mainWindow.setFullScreen(!mainWindow.isFullScreen()),
        },
        {
          label: 'Developer Tools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => mainWindow.webContents.toggleDevTools(),
        },
      ],
    },
    {
      label: 'Help & Standards',
      submenu: [
        {
          label: 'ICAI Accounting Standards Guidance',
          click: () => shell.openExternal('https://www.icai.org/post/indian-accounting-standards-indas'),
        },
        {
          label: 'MCA Schedule III Guidance',
          click: () => shell.openExternal('https://www.mca.gov.in/'),
        },
        { type: 'separator' },
        {
          label: 'About FinAudit Offline Engine',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'FinAudit AI Compliance Engine',
              message: 'FinAudit AI Ind AS & AS Disclosure Verifier',
              detail: 'Version 2.0.0 (Offline Edition)\n\nDesigned for Statutory Auditors, Quality Review Boards & Chartered Accountants.\n100% On-Device Deterministic Audit Processing.',
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
