const { contextBridge, ipcRenderer } = require('electron')

let config = {}
try {
  const arg = process.argv.find((a) => a.startsWith('--hoshinoumi-config='))
  if (arg) config = JSON.parse(decodeURIComponent(arg.split('=').slice(1).join('=')))
} catch {}
const capabilities = {
  engine: 'chromium',
  chrome: process.versions.chrome,
  electron: process.versions.electron,
  node: process.versions.node,
  platform: process.platform,
  arch: process.arch,
}
contextBridge.exposeInMainWorld('desktopShell', {
  config,
  capabilities,
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  openMain: () => ipcRenderer.send('window:open-main'),
  closeMini: () => ipcRenderer.send('window:close-mini'),
  toggleMini: () => ipcRenderer.send('window:toggle-mini'),
  retry: () => ipcRenderer.send('fallback:retry'),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setMiniEnabled: (enabled) => ipcRenderer.invoke('settings:set-mini', enabled),
  saveSettings: (next) => ipcRenderer.invoke('settings:save', next),
})
