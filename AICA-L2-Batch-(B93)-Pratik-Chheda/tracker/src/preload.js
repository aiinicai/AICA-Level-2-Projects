'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const call = (ch, arg) => ipcRenderer.invoke(ch, arg);
contextBridge.exposeInMainWorld('dfAPI', {
  loadStore: () => call('store:load'),
  saveStore: store => call('store:save', store),
  info: () => call('app:info'),
  audit: () => call('app:audit'),
  backupNow: () => call('app:backupNow'),
  openDataFolder: () => call('app:openDataFolder'),
  restore: () => call('app:restore'),
  saveFile: payload => call('file:save', payload),
  savePDF: payload => call('pdf:save', payload),
  gcalStatus: () => call('gcal:status'),
  gcalConnect: creds => call('gcal:connect', creds),
  gcalDisconnect: () => call('gcal:disconnect'),
  gcalSync: payload => call('gcal:sync', payload),
  googleFetch: req => call('google:fetch', req),
  automationGet: () => call('auto:get'),
  automationSet: s => call('auto:set', s),
  automationPost: req => call('auto:post', req)
});
