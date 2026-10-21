const { app, BrowserWindow, Menu, dialog, shell, clipboard } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');
const os = require('os');
const url = require('url');

let mainWindow = null;
let server = null;
let activePort = 3000;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.otf': 'font/otf',
  '.wasm': 'application/wasm',
};

function getLocalIpAddresses() {
  const interfaces = os.networkInterfaces();
  const addresses = [];
  for (const name of Object.keys(interfaces)) {
    for (const net of interfaces[name] || []) {
      if (net.family === 'IPv4' && !net.internal) {
        addresses.push(net.address);
      }
    }
  }
  return addresses;
}

function startStaticServer(initialPort = 3000) {
  return new Promise((resolve) => {
    const distPath = path.resolve(__dirname, '..', 'dist');

    const requestHandler = (req, res) => {
      // Enable CORS for LAN access
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');

      if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
      }

      const parsedUrl = url.parse(req.url);
      let pathname = decodeURIComponent(parsedUrl.pathname || '/');

      let safePath = path.normalize(path.join(distPath, pathname));
      if (!safePath.startsWith(distPath)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
      }

      fs.stat(safePath, (err, stats) => {
        if (!err && stats.isDirectory()) {
          safePath = path.join(safePath, 'index.html');
        }

        fs.readFile(safePath, (readErr, data) => {
          if (!readErr) {
            const ext = path.extname(safePath).toLowerCase();
            res.setHeader('Content-Type', MIME_TYPES[ext] || 'application/octet-stream');
            res.writeHead(200);
            res.end(data);
          } else {
            // SPA fallback: serve dist/index.html
            const indexPath = path.join(distPath, 'index.html');
            fs.readFile(indexPath, (indexErr, indexData) => {
              if (!indexErr) {
                res.setHeader('Content-Type', 'text/html; charset=utf-8');
                res.writeHead(200);
                res.end(indexData);
              } else {
                res.writeHead(404);
                res.end('Not Found');
              }
            });
          }
        });
      });
    };

    const tryListen = (port) => {
      const s = http.createServer(requestHandler);
      s.once('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          console.warn(`Port ${port} in use, trying ${port + 1}...`);
          tryListen(port + 1);
        } else {
          console.error('Server error:', err);
          resolve({ port: null, server: null });
        }
      });
      s.listen(port, '0.0.0.0', () => {
        console.log(`MediCore Connect HTTP server listening on http://0.0.0.0:${port}`);
        resolve({ port, server: s });
      });
    };

    tryListen(initialPort);
  });
}

async function createWindow() {
  const { port, server: s } = await startStaticServer(3000);
  activePort = port;
  server = s;

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 720,
    title: 'MediCore Connect — Meridian Healthcare ERP',
    backgroundColor: '#0f172a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    autoHideMenuBar: false,
  });

  const ipAddresses = getLocalIpAddresses();
  const localUrl = `http://localhost:${activePort}`;
  const lanUrls = ipAddresses.map((ip) => `http://${ip}:${activePort}`);

  // Custom menu with LAN sharing
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload App',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow && mainWindow.reload(),
        },
        {
          label: 'LAN Sharing Info...',
          accelerator: 'CmdOrCtrl+I',
          click: () => {
            const message = [
              `Localhost URL:`,
              `  ${localUrl}`,
              ``,
              `Share with others on the same LAN / Wi-Fi:`,
              ...(lanUrls.length > 0 ? lanUrls.map((u) => `  ${u}`) : ['  No active Wi-Fi/LAN interface found']),
              ``,
              `Status: Server active on port ${activePort}`,
            ].join('\n');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'LAN Sharing Information',
              message: 'MediCore Connect is accessible on your local network!',
              detail: message,
            });
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'togglefullscreen' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { role: 'resetZoom' },
        { type: 'separator' },
        { role: 'toggleDevTools' },
      ],
    },
    {
      label: 'LAN Sharing',
      submenu: [
        ...lanUrls.map((u) => ({
          label: `Open ${u} in Browser`,
          click: () => shell.openExternal(u),
        })),
        {
          label: 'Copy Primary LAN Address to Clipboard',
          click: () => {
            const targetUrl = lanUrls[0] || localUrl;
            clipboard.writeText(targetUrl);
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Copied!',
              message: `Copied to clipboard:\n${targetUrl}`,
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  if (activePort) {
    mainWindow.loadURL(localUrl);
  } else {
    mainWindow.loadFile(path.resolve(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (server) {
    try {
      server.close();
    } catch (_) {}
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
