const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronHardwareLicense', {
  getHardwareState: () => ipcRenderer.invoke('get-hardware-state'),
  tickTrial: (seconds) => ipcRenderer.invoke('tick-trial', seconds),
  activateKey: (key) => ipcRenderer.invoke('activate-key', key)
});
