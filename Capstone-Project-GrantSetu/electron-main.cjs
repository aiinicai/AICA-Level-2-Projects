const { app, BrowserWindow } = require('electron');
const path = require('path');
const express = require('express');

let mainWindow;

function createWindow() {
  const server = express();
  server.use(express.static(path.join(__dirname, 'dist')));
  
  const listener = server.listen(0, '127.0.0.1', () => {
    const port = listener.address().port;

    mainWindow = new BrowserWindow({
      width: 1366,
      height: 850,
      minWidth: 1024,
      minHeight: 700,
      title: 'GrantSetu - Indian NGO Grant ERP',
      autoHideMenuBar: true,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true
      }
    });

    mainWindow.loadURL(`http://127.0.0.1:${port}`);

    mainWindow.on('closed', () => {
      mainWindow = null;
    });
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
