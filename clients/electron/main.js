const { app, BrowserWindow, shell, ipcMain } = require('electron')
const path = require('path')

const FRONTEND = path.join(__dirname, '../../integrations/web/dist/index.html')

app.commandLine.appendSwitch('no-sandbox')
app.disableHardwareAcceleration()
let win = null

function createWindow() {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1180,
    minHeight: 760,
    center: true,
    show: false,
    backgroundColor: '#ffffff',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  win.loadFile(FRONTEND)
  win.once('ready-to-show', () => win.show())
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url)
    return { action: 'deny' }
  })
  win.webContents.on('did-fail-load', (_e, code, desc, url) => {
    console.error('load failed', code, desc, url)
  })
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (win) { if (win.isMinimized()) win.restore(); win.focus() }
  })
  app.whenReady().then(() => {
    ipcMain.on('window:minimize', () => win?.minimize())
    ipcMain.on('window:maximize', () => win?.isMaximized() ? win.unmaximize() : win?.maximize())
    ipcMain.on('window:close', () => win?.close())
    createWindow()
  })
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
}
