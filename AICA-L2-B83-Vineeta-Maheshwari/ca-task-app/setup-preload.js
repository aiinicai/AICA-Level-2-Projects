'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('setupAPI', {
  submit: (choice) => ipcRenderer.invoke('setup-complete', choice),
});
