const { app, BrowserWindow } = require('electron');
const path = require('path');

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[CONSOLE ${level}] ${message} (${sourceId}:${line})`);
  });

  // Inject error logger as early as possible
  await win.webContents.executeJavaScriptInIsolatedWorld(999, [{
    code: `
      window.addEventListener('error', (e) => {
        console.error('WINDOW ERROR:', e.message, e.filename, e.lineno, e.colno, e.error ? e.error.stack : 'no stack');
      });
      window.addEventListener('unhandledrejection', (e) => {
        console.error('UNHANDLED REJECTION:', e.reason);
      });
    `
  }]);

  const distIndex = path.resolve(__dirname, 'dist', 'index.html');
  await win.loadFile(distIndex, { hash: '/general-accounting/journals' });

  // In page context:
  win.webContents.executeJavaScript(`
    window.onerror = function(msg, url, line, col, err) {
      console.log('EXACT ERROR STACK:', err ? err.stack : (msg + ' at ' + line + ':' + col));
    };
  `);

  setTimeout(async () => {
    app.quit();
  }, 4000);
});
