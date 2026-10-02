'use strict';
const { app, BrowserWindow, ipcMain, dialog, shell, Menu, safeStorage } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const DB = require('./db');
const GCal = require('./gcal');

let win = null, db = null, gcal = null;
const dataDir = () => app.getPath('userData');
const dbPath = () => path.join(dataDir(), 'dealflow-tracker.sqlite');
const backupDir = () => path.join(dataDir(), 'backups');

if (!app.requestSingleInstanceLock()) { app.quit(); }
app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });

function dailyBackup() {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  if (db.lastBackupDay(backupDir()) !== today) { try { db.backup(backupDir()); } catch (e) { console.error('backup failed', e); } }
}

function createWindow() {
  win = new BrowserWindow({
    width: 1440, height: 920, minWidth: 900, minHeight: 600,
    title: 'Sample Advisory Lead and Meeting Tracker',
    icon: path.join(__dirname, '..', 'app', 'icons', 'icon-512.png'),
    backgroundColor: '#F6F8FA',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: true }
  });
  win.loadFile(path.join(__dirname, '..', 'app', 'index.html'));
  // Google Calendar, Gmail and any other link open in the default browser
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:|^mailto:/.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith('file:')) { e.preventDefault(); shell.openExternal(url); } });
}

function buildMenu() {
  const mac = process.platform === 'darwin';
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(mac ? [{ role: 'appMenu' }] : []),
    { label: 'File', submenu: [
      { label: 'Back up database now', click: () => { const p = db.backup(backupDir()); dialog.showMessageBox(win, { message: 'Backup saved', detail: p }); } },
      { label: 'Open data folder', click: () => shell.openPath(dataDir()) },
      { type: 'separator' }, mac ? { role: 'close' } : { role: 'quit' } ] },
    { role: 'editMenu' },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }] },
    { role: 'windowMenu' },
    { label: 'Help', submenu: [{ label: 'www.example.com', click: () => shell.openExternal('https://www.example.com') }] }
  ]));
}

function registerIPC() {
  ipcMain.handle('store:load', () => db.loadStore());
  ipcMain.handle('store:save', (e, store) => db.saveStore(store, { actor: os.userInfo().username }));
  ipcMain.handle('app:info', () => ({ dbPath: dbPath(), backupDir: backupDir(), version: app.getVersion(), platform: process.platform }));
  ipcMain.handle('app:audit', () => db.audit(200));
  ipcMain.handle('app:backupNow', () => ({ path: db.backup(backupDir()) }));
  ipcMain.handle('app:openDataFolder', () => shell.openPath(dataDir()));
  ipcMain.handle('app:restore', async () => {
    const r = await dialog.showOpenDialog(win, { title: 'Restore a database backup', defaultPath: backupDir(), filters: [{ name: 'Tracker database', extensions: ['sqlite'] }], properties: ['openFile'] });
    if (r.canceled || !r.filePaths[0]) return { restored: false };
    const ok = await dialog.showMessageBox(win, { type: 'warning', buttons: ['Restore', 'Cancel'], defaultId: 1, message: 'Replace the current data with this backup?', detail: 'A backup of the current data is taken first.' });
    if (ok.response !== 0) return { restored: false };
    db.backup(backupDir());
    db.close();
    db = await DB.openFromBackup(dbPath(), r.filePaths[0]);
    gcal = GCal.create(db);
    const s = db.loadStore();
    return { restored: true, store: s.store, version: s.version };
  });
  ipcMain.handle('file:save', async (e, { name, data }) => {
    const ext = path.extname(name).slice(1);
    const r = await dialog.showSaveDialog(win, { defaultPath: path.join(app.getPath('documents'), name), filters: [{ name: ext.toUpperCase() + ' file', extensions: [ext] }] });
    if (r.canceled || !r.filePath) return { saved: false };
    fs.writeFileSync(r.filePath, Buffer.from(data));
    shell.showItemInFolder(r.filePath);
    return { saved: true, path: r.filePath };
  });
  ipcMain.handle('pdf:save', async (e, { html, name }) => {
    const r = await dialog.showSaveDialog(win, { defaultPath: path.join(app.getPath('documents'), name), filters: [{ name: 'PDF', extensions: ['pdf'] }] });
    if (r.canceled || !r.filePath) return { saved: false };
    const tmp = path.join(app.getPath('temp'), 'df_report_' + Date.now() + '.html');
    fs.writeFileSync(tmp, html);
    const pw = new BrowserWindow({ show: false, webPreferences: { sandbox: true } });
    try {
      await pw.loadFile(tmp);
      const pdf = await pw.webContents.printToPDF({ pageSize: 'A4', printBackground: true, preferCSSPageSize: true, margins: { marginType: 'none' } });
      fs.writeFileSync(r.filePath, pdf);
    } finally { pw.destroy(); fs.unlink(tmp, () => {}); }
    shell.openPath(r.filePath);
    return { saved: true, path: r.filePath };
  });
  ipcMain.handle('gcal:status', () => gcal.status());
  ipcMain.handle('gcal:connect', (e, creds) => gcal.connect(creds));
  ipcMain.handle('gcal:disconnect', () => gcal.disconnect());
  ipcMain.handle('gcal:sync', (e, payload) => gcal.sync(payload));
  ipcMain.handle('google:fetch', (e, req) => gcal.googleFetch(req));
  // n8n automation: settings live in the database; the shared secret is encrypted and never returned to the page.
  ipcMain.handle('auto:get', () => automationSettings());
  ipcMain.handle('auto:set', (e, s) => {
    ['baseUrl', 'headerName', 'people'].forEach(k => { if (s[k] !== undefined) db.setSetting('auto_' + k, typeof s[k] === 'string' ? s[k] : JSON.stringify(s[k])); });
    if (s.secret) db.setSetting('auto_secret', safeStorage.isEncryptionAvailable() ? 'enc:' + safeStorage.encryptString(s.secret).toString('base64') : 'raw:' + s.secret);
    db.flush();
    return automationSettings();
  });
  ipcMain.handle('auto:post', async (e, { path: p, body }) => {
    const s = automationSettings(), secret = automationSecret();
    if (!s.baseUrl || !secret) throw new Error('Set the n8n address and shared secret first (Settings, Automation)');
    const url = s.baseUrl.replace(/\/+$/, '') + '/webhook/' + String(p).replace(/[^a-z0-9-]/gi, '');
    if (!/^https:\/\//.test(url)) throw new Error('The n8n address must start with https://');
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', [s.headerName || 'X-Sample Advisory-Secret']: secret }, body: JSON.stringify(body) });
    const text = await r.text();
    if (!r.ok) throw new Error('n8n answered ' + r.status + (text ? ': ' + text.slice(0, 200) : ''));
    return { ok: true, status: r.status };
  });
}

function automationSettings() {
  let people = {};
  try { people = JSON.parse(db.getSetting('auto_people') || '{}'); } catch (e) {}
  return { baseUrl: db.getSetting('auto_baseUrl') || 'https://your-instance.app.n8n.cloud', headerName: db.getSetting('auto_headerName') || 'X-Sample Advisory-Secret', hasSecret: !!db.getSetting('auto_secret'), people };
}
function automationSecret() {
  const s = db.getSetting('auto_secret');
  if (!s) return '';
  return s.startsWith('enc:') ? safeStorage.decryptString(Buffer.from(s.slice(4), 'base64')) : s.slice(4);
}

app.whenReady().then(async () => {
  db = await DB.open(dbPath());
  gcal = GCal.create(db);
  dailyBackup();
  registerIPC();
  buildMenu();
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => { try { db && db.flush(); } catch (e) {} });
