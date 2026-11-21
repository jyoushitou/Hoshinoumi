const { contextBridge, ipcRenderer } = require('electron')

let config = {}
try {
  const arg = process.argv.find((a) => a.startsWith('--hoshinoumi-config='))
  if (arg) config = JSON.parse(decodeURIComponent(arg.split('=').slice(1).join('=')))
} catch {}
contextBridge.exposeInMainWorld('desktopShell', {
  config,
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  openMain: () => ipcRenderer.send('window:open-main'),
  closeMini: () => ipcRenderer.send('window:close-mini'),
  toggleMini: () => ipcRenderer.send('window:toggle-mini'),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setMiniEnabled: (enabled) => ipcRenderer.invoke('settings:set-mini', enabled),
  saveSettings: (next) => ipcRenderer.invoke('settings:save', next),
})
