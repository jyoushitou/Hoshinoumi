// Hoshinoumi VS Code extension host.
// The webview talks to this host; the host is the only place that knows the
// backend token and performs HTTP requests, same split as other Hoshinoumi clients.
const vscode = require('vscode')
const fs = require('node:fs')
const path = require('node:path')

const CONFIG_KEY = 'hoshinoumi.config'
const DEFAULT_CONFIG = { base_url: '', token: '', target_id: 'owner' }
let panel = null

function envConfig() {
  const file = process.env.HOSHINOUMI_VSCODE_CONFIG
  if (file) {
    try {
      const raw = JSON.parse(fs.readFileSync(file, 'utf8'))
      if (raw && typeof raw === 'object') return raw
    } catch {}
  }
  return null
}

function readConfig(context) {
  const raw = envConfig() || context.globalState.get(CONFIG_KEY)
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_CONFIG }
  return {
    base_url: typeof raw.base_url === 'string' ? raw.base_url.replace(/\/+$/, '') : (typeof raw.gateway === 'string' ? raw.gateway.replace(/\/+$/, '') : ''),
    token: typeof raw.token === 'string' ? raw.token : '',
    target_id: typeof raw.target_id === 'string' && raw.target_id.trim() ? raw.target_id.trim() : 'owner',
  }
}

async function saveConfig(context, patch) {
  const current = readConfig(context)
  const next = {
    base_url: typeof patch.base_url === 'string' ? patch.base_url.trim().replace(/\/+$/, '') : current.base_url,
    token: typeof patch.token === 'string' ? patch.token.trim() : current.token,
    target_id: typeof patch.target_id === 'string' && patch.target_id.trim() ? patch.target_id.trim() : current.target_id,
  }
  if (next.base_url && !/^https?:\/\//i.test(next.base_url)) throw new Error('后端地址必须以 http:// 或 https:// 开头')
  await context.globalState.update(CONFIG_KEY, next)
  return next
}

async function backendFetch(cfg, endpoint, method = 'GET', body = null) {
  if (!cfg.base_url) throw new Error('后端地址未配置')
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 20000)
  try {
    const headers = { 'content-type': 'application/json' }
    if (cfg.token) headers.authorization = `Bearer ${cfg.token}`
    let res
    try {
      res = await fetch(cfg.base_url + endpoint, {
        method,
        headers,
        body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
        signal: controller.signal,
      })
    } catch (e) {
      throw new Error(`无法连接后端 ${cfg.base_url}：${e instanceof Error ? e.message : String(e)}`)
    }
    const text = await res.text()
    let data
    try { data = text ? JSON.parse(text) : {} } catch { data = { raw: text } }
    return { status: res.status, data }
  } finally {
    clearTimeout(timer)
  }
}

function mapPath(rawPath) {
  const [base, query] = rawPath.split('?')
  const suffix = base.replace('/api/hoshinoumi', '')
  const map = {
    '/health': '/healthz',
    '/chat': '/api/chat',
    '/history': '/api/history',
    '/command': '/api/command',
    '/status': '/api/status',
    '/logs': '/api/logs',
    '/memory': '/api/memory',
    '/persona': '/api/persona',
    '/persona/export': '/api/persona/export',
    '/persona/import': '/api/persona/import',
    '/persona/activate': '/api/persona/activate',
    '/savings': '/api/savings',
    '/savings/import': '/api/savings/import',
    '/savings/entries': '/api/savings/entries',
    '/savings/events': '/api/savings/events',
    '/weekly-plan': '/api/weekly-plan',
    '/weekly-plan/import': '/api/weekly-plan/import',
    '/balance': '/api/balance',
    '/relation': '/api/relation',
    '/cron': '/api/cron',
  }
  const endpoint = map[suffix]
  if (!endpoint) return null
  return endpoint + (query ? '?' + query : '')
}

async function handleRequest(context, msg, post) {
  const { id, path: rawPath, method = 'GET' } = msg
  const send = (status, data) => post({ type: 'hoshinoumi:response', id, status, data })
  try {
    if (rawPath === '/api/hoshinoumi/config') {
      if (method === 'POST') {
        const body = msg.body ? (typeof msg.body === 'string' ? JSON.parse(msg.body) : msg.body) : {}
        const cfg = await saveConfig(context, body)
        return send(200, { ok: true, configured: Boolean(cfg.base_url && cfg.token), base_url: cfg.base_url, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
      }
      const cfg = readConfig(context)
      return send(200, { configured: Boolean(cfg.base_url && cfg.token), base_url: cfg.base_url, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
    }

    if (rawPath === '/api/hoshinoumi/test') {
      const candidate = msg.body ? (typeof msg.body === 'string' ? JSON.parse(msg.body) : msg.body) : {}
      const cfg = {
        base_url: candidate.base_url || readConfig(context).base_url,
        token: candidate.token || readConfig(context).token,
        target_id: candidate.target_id || readConfig(context).target_id || 'owner',
      }
      const started = Date.now()
      const health = await backendFetch(cfg, '/healthz')
      const ready = await backendFetch(cfg, '/readyz')
      const ok = health.status === 200 && ready.status === 200
      return send(ok ? 200 : 502, {
        ok,
        status: ready.status,
        latency_ms: Date.now() - started,
        health: health.data,
        ready: ready.data,
        message: ok ? undefined : '后端健康检查未通过',
      })
    }

    const endpoint = mapPath(rawPath)
    if (!endpoint) return send(404, { ok: false, error: 'unknown_route', message: rawPath })
    const cfg = readConfig(context)
    let finalEndpoint = endpoint
    if (finalEndpoint.startsWith('/api/history') && !finalEndpoint.includes('target_id=')) {
      finalEndpoint += (finalEndpoint.includes('?') ? '&' : '?') + 'target_id=' + encodeURIComponent(cfg.target_id || 'owner')
    }
    const out = await backendFetch(cfg, finalEndpoint, method, msg.body)
    return send(out.status, out.data)
  } catch (e) {
    return send(502, { ok: false, error: 'proxy_failed', message: e instanceof Error ? e.message : String(e) })
  }
}

class SidebarProvider {
  constructor(context) { this.context = context }
  resolveWebviewView(view) {
    view.webview.options = { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, 'media')] }
    const file = path.join(this.context.extensionPath, 'media', 'sidebar.html')
    view.webview.html = fs.readFileSync(file, 'utf8')
    view.webview.onDidReceiveMessage((msg) => {
      if (!msg || typeof msg !== 'object') return
      if (msg.type === 'hoshinoumi:request') return handleRequest(this.context, msg, (data) => view.webview.postMessage(data))
      if (msg.type === 'hoshinoumi:close') return
    })
  }
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('hoshinoumi.open', () => vscode.commands.executeCommand('hoshinoumi.sidebar.focus')),
    vscode.commands.registerCommand('hoshinoumi.configure', () => vscode.commands.executeCommand('hoshinoumi.sidebar.focus')),
    vscode.window.registerWebviewViewProvider('hoshinoumi.sidebar', new SidebarProvider(context)),
  )
}

function deactivate() {
  if (panel) { panel.dispose(); panel = null }
}

module.exports = { activate, deactivate }
