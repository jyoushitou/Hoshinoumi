/**
 * hoshinoumi-dsh — host half.
 *
 * The plugin is intentionally thin:
 *   - stores the Hoshinoumi backend address/token locally
 *   - proxies chat/command to that backend
 *   - serves the full client UI at /api/hoshinoumi/ui
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, chmodSync } from 'node:fs'
import { join } from 'node:path'
import { homedir } from 'node:os'

export const name = 'hoshinoumi_dsh'
export const inject = ['webServer']

const UI_FILE = new URL('./ui.html', import.meta.url)
const CONFIG_DIR = join(process.env.DSH_HOME || join(homedir(), '.dsh'))
const CONFIG_FILE = join(CONFIG_DIR, 'hoshinoumi.json')

function readConfig() {
  try {
    const raw = JSON.parse(readFileSync(CONFIG_FILE, 'utf8'))
    return {
      base_url: typeof raw.base_url === 'string' ? raw.base_url.replace(/\/+$/, '') : (typeof raw.gateway === 'string' ? raw.gateway.replace(/\/+$/, '') : ''),
      token: typeof raw.token === 'string' ? raw.token : '',
      target_id: typeof raw.target_id === 'string' && raw.target_id.trim() ? raw.target_id.trim() : 'owner',
    }
  } catch {
    return { base_url: '', token: '', target_id: 'owner' }
  }
}

function saveConfig(patch) {
  const current = readConfig()
  const next = {
    base_url: typeof patch.base_url === 'string' ? patch.base_url.trim().replace(/\/+$/, '') : current.base_url,
    token: typeof patch.token === 'string' ? patch.token.trim() : current.token,
    target_id: typeof patch.target_id === 'string' && patch.target_id.trim() ? patch.target_id.trim() : current.target_id,
  }
  if (next.base_url && !/^https?:\/\//i.test(next.base_url)) throw new Error('后端地址必须以 http:// 或 https:// 开头')
  mkdirSync(CONFIG_DIR, { recursive: true })
  writeFileSync(CONFIG_FILE, JSON.stringify(next, null, 2) + '\n', 'utf8')
  try { chmodSync(CONFIG_FILE, 0o600) } catch {}
  return next
}

function sendJson(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
  res.end(JSON.stringify(data))
}

async function readBody(req) {
  let raw = ''
  for await (const chunk of req) raw += chunk
  if (!raw) return {}
  try { return JSON.parse(raw) } catch { throw new Error('invalid JSON body') }
}

function authHeaders(cfg) {
  return cfg.token ? { authorization: `Bearer ${cfg.token}` } : {}
}

async function backendFetch(cfg, path, init = {}) {
  if (!cfg.base_url) throw new Error('后端地址未配置')
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 20000)
  try {
    let res
    try {
      res = await fetch(`${cfg.base_url}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...authHeaders(cfg), ...(init.headers || {}) },
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

async function handleApi(req, res, path) {
  if (path === '/api/hoshinoumi/health' && req.method === 'GET') {
    return sendJson(res, 200, { ok: true, version: '35.2.24.7', config: CONFIG_FILE })
  }

  if (path === '/api/hoshinoumi/ui' && req.method === 'GET') {
    const html = readFileSync(UI_FILE, 'utf8')
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
    res.end(html)
    return
  }

  if (path === '/api/hoshinoumi/config' && req.method === 'GET') {
    const cfg = readConfig()
    return sendJson(res, 200, { configured: Boolean(cfg.base_url), base_url: cfg.base_url, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
  }

  if (path === '/api/hoshinoumi/config' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = saveConfig(body)
    return sendJson(res, 200, { ok: true, configured: Boolean(cfg.base_url), base_url: cfg.base_url, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
  }

  if (path === '/api/hoshinoumi/test' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = { ...readConfig(), ...(body.base_url ? { base_url: String(body.base_url).trim().replace(/\/+$/, '') } : {}), ...(typeof body.token === 'string' && body.token.trim() ? { token: body.token.trim() } : {}) }
    if (!cfg.base_url) throw new Error('请先填写后端地址')
    const started = Date.now()
    const health = await backendFetch(cfg, '/healthz', { method: 'GET' })
    const ready = health.status < 400 ? await backendFetch(cfg, '/readyz', { method: 'GET' }) : null
    return sendJson(res, 200, {
      ok: health.status < 400,
      status: health.status,
      latency_ms: Date.now() - started,
      health: health.data,
      ready: ready?.data ?? null,
    })
  }

  const proxyGet = async (targetPath) => {
    const cfg = readConfig()
    if (!cfg.base_url) throw new Error('后端地址未配置')
    const out = await backendFetch(cfg, targetPath, { method: 'GET' })
    return sendJson(res, out.status, out.data)
  }
  if (path === '/api/hoshinoumi/status' && req.method === 'GET') return proxyGet('/api/status')
  if (path === '/api/hoshinoumi/logs' && req.method === 'GET') {
    const u = new URL(req.url || '/', 'http://127.0.0.1')
    return proxyGet('/api/logs?limit=' + Math.max(1, Math.min(Number(u.searchParams.get('limit') || 20), 100)))
  }
  if (path === '/api/hoshinoumi/weekly-plan' && req.method === 'GET') {
    const u = new URL(req.url || '/', 'http://127.0.0.1')
    return proxyGet('/api/weekly-plan?week=' + encodeURIComponent(u.searchParams.get('week') || '1'))
  }
  if (path === '/api/hoshinoumi/weekly-plan' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/weekly-plan', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }
  if (path === '/api/hoshinoumi/weekly-plan/import' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/weekly-plan/import', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/balance' && req.method === 'GET') return proxyGet('/api/balance')
  if (path === '/api/hoshinoumi/savings' && req.method === 'GET') return proxyGet('/api/savings')
  if (path === '/api/hoshinoumi/savings/events' && req.method === 'GET') return proxyGet('/api/savings/events')
  if (path === '/api/hoshinoumi/savings/entries' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/savings/entries', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }
  if (path === '/api/hoshinoumi/savings/import' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/savings/import', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/persona' && req.method === 'GET') return proxyGet('/api/persona')
  if (path === '/api/hoshinoumi/persona/export' && req.method === 'GET') {
    const u = new URL(req.url || '/', 'http://127.0.0.1')
    return proxyGet('/api/persona/export?name=' + encodeURIComponent(u.searchParams.get('name') || ''))
  }
  if (path === '/api/hoshinoumi/persona/import' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/persona/import', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }
  if (path === '/api/hoshinoumi/persona/activate' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/persona/activate', { method: 'POST', body: JSON.stringify(body) })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/memory' && req.method === 'GET') {
    const u = new URL(req.url || '/', 'http://127.0.0.1')
    const t = u.searchParams.get('target_id')
    return proxyGet('/api/memory' + (t ? '?target_id=' + encodeURIComponent(t) : ''))
  }
  if (path === '/api/hoshinoumi/plan' && req.method === 'GET') return proxyGet('/api/plan')
  if (path === '/api/hoshinoumi/cron' && req.method === 'GET') return proxyGet('/internal/cron')

  if (path === '/api/hoshinoumi/history' && req.method === 'GET') {
    const url = new URL(req.url || '/', 'http://127.0.0.1')
    const cfg = readConfig()
    if (!cfg.base_url) throw new Error('后端地址未配置')
    const target = url.searchParams.get('target_id') || cfg.target_id || 'owner'
    const limit = Math.max(1, Math.min(Number(url.searchParams.get('limit') || 30), 100))
    const out = await backendFetch(cfg, `/internal/history?target_id=${encodeURIComponent(target)}&limit=${limit}`, { method: 'GET' })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/chat' && req.method === 'POST') {
    const body = await readBody(req)
    const message = typeof body.message === 'string' ? body.message.trim() : ''
    if (!message) throw new Error('message is empty')
    const cfg = readConfig()
    const target_id = typeof body.target_id === 'string' && body.target_id.trim() ? body.target_id.trim() : cfg.target_id
    const out = await backendFetch(cfg, '/api/chat', { method: 'POST', body: JSON.stringify({ message, target_id }) })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/command' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await backendFetch(cfg, '/api/command', { method: 'POST', body: JSON.stringify({ command: String(body.command || ''), args: Array.isArray(body.args) ? body.args : [] }) })
    return sendJson(res, out.status, out.data)
  }

  return sendJson(res, 404, { error: 'not_found', path })
}

export function apply(ctx) {
  const route = {
    kind: 'prefix',
    path: '/api/hoshinoumi',
    handler: async (req, res) => {
      try {
        const url = new URL(req.url || '/', 'http://127.0.0.1')
        await handleApi(req, res, url.pathname)
      } catch (e) {
        sendJson(res, 500, { error: 'hoshinoumi_error', message: e instanceof Error ? e.message : String(e) })
      }
    },
  }
  ctx.effect(() => ctx.webServer.register(route), 'hoshinoumi_dsh: api route')
  ctx.logger?.info?.(`[hoshinoumi-dsh] API ready; config: ${CONFIG_FILE}`)
}

export default { name, inject, apply }
