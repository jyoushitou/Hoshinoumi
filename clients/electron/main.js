const { app, BrowserWindow, shell, ipcMain, Tray, Menu, nativeImage, dialog } = require('electron')
const fs = require('fs')
const path = require('path')

const FRONTEND = path.join(__dirname, '../../integrations/web/dist/index.html')
const ICON = path.join(__dirname, 'assets/hoshinoumi.png')

app.setAppUserModelId('com.hoshinoumi.desktop')
app.commandLine.appendSwitch('no-sandbox')
app.disableHardwareAcceleration()
let win = null
let tray = null
let mini = null
let settingsWin = null
const SETTINGS_FILE = path.join(app.getPath('userData'), 'shell-settings.json')
let shellSettings = { miniWindow: false, apiBase: 'http://127.0.0.1:27005', apiPrefix: '', startRoute: '/chat', updateUrl: '' }
function loadSettings() { try { shellSettings = { miniWindow: false, apiBase: 'http://127.0.0.1:27005', apiPrefix: '', startRoute: '/chat', updateUrl: '', ...JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8')) } } catch {} }
function saveSettings() { try { fs.mkdirSync(path.dirname(SETTINGS_FILE), { recursive: true }); fs.writeFileSync(SETTINGS_FILE, JSON.stringify(shellSettings, null, 2)) } catch {} }
function logTray(msg) { try { fs.appendFileSync(path.join(__dirname, '.electron-data', 'shell.log'), msg + '\n') } catch {} }

function createWindow() {
  win = new BrowserWindow({
    icon: ICON,
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
      additionalArguments: ['--hoshinoumi-config=' + encodeURIComponent(JSON.stringify({ apiBase: shellSettings.apiBase, apiPrefix: shellSettings.apiPrefix, startRoute: shellSettings.startRoute }))],
    },
  })
  win.loadFile(FRONTEND, { hash: shellSettings.startRoute || '/chat' })
  win.once('ready-to-show', () => win.show())
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url)
    return { action: 'deny' }
  })
  win.webContents.on('did-fail-load', (_e, code, desc, url) => {
    logTray('load:fail ' + code + ' ' + desc + ' ' + url)
    if (!String(url).includes('fallback.html')) win.loadFile(path.join(__dirname, 'fallback.html'))
  })
  win.webContents.on('render-process-gone', (_e, details) => {
    logTray('renderer:gone ' + JSON.stringify(details))
    win.loadFile(path.join(__dirname, 'fallback.html'))
  })
}

function toggleMini() {
  if (!shellSettings.miniWindow) { logTray('mini:disabled'); return }
  if (mini) {
    if (mini.isVisible()) mini.hide()
    else { mini.show(); mini.focus() }
    return
  }
  mini = new BrowserWindow({
    icon: ICON,
    width: 360,
    height: 130,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    backgroundColor: '#f8fbff',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  if (win) win.hide()
  mini.loadFile(path.join(__dirname, 'mini.html'))
  mini.webContents.on('did-fail-load', (_e, code, desc) => logTray('mini:load-fail ' + code + ' ' + desc))
  mini.once('ready-to-show', () => { logTray('mini:ready'); mini.show() })
  setTimeout(() => { try { if (mini && !mini.isVisible()) { logTray('mini:fallback-show'); mini.show() } } catch {} }, 1200)
  mini.on('closed', () => { mini = null })
}

function refreshTrayMenu() {
  if (!tray) return
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: '打开主窗口', click: () => { if (win) { win.show(); win.focus() } } },
    { label: '迷你窗口', enabled: !!shellSettings.miniWindow, click: toggleMini },
    { label: '设置', click: openSettings },
    { label: '检查更新', click: checkUpdate },
    { type: 'separator' },
    { label: '退出', click: () => app.quit() },
  ]))
}
function applyMiniState() {
  refreshTrayMenu()
  try {
    if (shellSettings.miniWindow) globalShortcut.register('CommandOrControl+Shift+M', toggleMini)
    else { globalShortcut.unregister('CommandOrControl+Shift+M'); if (mini) mini.hide() }
  } catch {}
}
function openSettings() {
  if (settingsWin) { settingsWin.show(); settingsWin.focus(); return }
  settingsWin = new BrowserWindow({ width: 440, height: 390, resizable: false, autoHideMenuBar: true, title: 'Hoshinoumi 设置', webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true } })
  settingsWin.loadFile(path.join(__dirname, 'settings.html'))
  settingsWin.on('closed', () => { settingsWin = null })
}
async function checkUpdate() {
  const url = String(shellSettings.updateUrl || '').trim()
  if (!url) {
    await dialog.showMessageBox({ type: 'info', title: '检查更新', message: '未配置更新源', detail: '在设置中填写 updateUrl 后再检查更新。' })
    return
  }
  try {
    const res = await fetch(url, { headers: { accept: 'application/json' } })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const manifest = await res.json()
    const current = app.getVersion()
    if (!manifest.version) throw new Error('manifest.version 缺失')
    const available = manifest.version !== current
    await dialog.showMessageBox({
      type: 'info', title: '检查更新',
      message: available ? '发现新版本 ' + manifest.version : '已是最新版本',
      detail: available ? ('当前 ' + current + ' → ' + manifest.version + '\n' + (manifest.notes || '')) : ('当前 ' + current),
    })
  } catch (e) {
    await dialog.showMessageBox({ type: 'error', title: '检查更新失败', message: String(e) })
  }
}

function createTray() {
  try {
    logTray('tray:create start')
    const image = nativeImage.createFromPath(ICON).resize({ width: 16, height: 16 })
    if (image.isEmpty()) throw new Error('empty tray icon')
    tray = new Tray(image)
    tray.setToolTip('Hoshinoumi')
    refreshTrayMenu()
    tray.on('click', () => { if (win) { win.isVisible() ? win.hide() : win.show(); if (win.isVisible()) win.focus() } })
    logTray('tray:create ok')
  } catch (e) { logTray('tray:error ' + String(e)) }
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
    ipcMain.on('window:open-main', () => { if (win) { win.show(); win.focus() }; mini?.hide() })
    ipcMain.on('window:close-mini', () => mini?.hide())
    ipcMain.on('window:toggle-mini', toggleMini)
    ipcMain.on('fallback:retry', () => { if (win) win.loadFile(FRONTEND, { hash: shellSettings.startRoute || '/chat' }) })
    ipcMain.handle('settings:get', () => shellSettings)
    ipcMain.handle('settings:set-mini', (_e, enabled) => { shellSettings.miniWindow = Boolean(enabled); saveSettings(); applyMiniState(); return shellSettings })
    ipcMain.handle('settings:save', (_e, next) => { shellSettings = { ...shellSettings, ...next, miniWindow: !!next?.miniWindow }; saveSettings(); applyMiniState(); if (win) { win.loadFile(FRONTEND, { hash: shellSettings.startRoute || '/chat' }); win.show(); win.focus() } return shellSettings })
    loadSettings()
    createWindow()
    createTray()
    applyMiniState()
    if (process.argv.includes('--mini')) toggleMini()
    if (process.argv.includes('--settings')) openSettings()
  })
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
}
