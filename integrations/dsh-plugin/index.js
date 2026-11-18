/**
 * hoshinoumi-dsh — host half.
 *
 * The plugin is intentionally thin:
 *   - stores the Hoshinoumi gateway/token locally
 *   - proxies chat/command to that gateway
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
      gateway: typeof raw.gateway === 'string' ? raw.gateway.replace(/\/+$/, '') : '',
      token: typeof raw.token === 'string' ? raw.token : '',
      target_id: typeof raw.target_id === 'string' && raw.target_id.trim() ? raw.target_id.trim() : 'owner',
    }
  } catch {
    return { gateway: '', token: '', target_id: 'owner' }
  }
}

function saveConfig(patch) {
  const current = readConfig()
  const next = {
    gateway: typeof patch.gateway === 'string' ? patch.gateway.trim().replace(/\/+$/, '') : current.gateway,
    token: typeof patch.token === 'string' ? patch.token.trim() : current.token,
    target_id: typeof patch.target_id === 'string' && patch.target_id.trim() ? patch.target_id.trim() : current.target_id,
  }
  if (next.gateway && !/^https?:\/\//i.test(next.gateway)) throw new Error('gateway must start with http:// or https://')
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

async function gatewayFetch(cfg, path, init = {}) {
  if (!cfg.gateway) throw new Error('gateway is not configured')
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 20000)
  try {
    const res = await fetch(`${cfg.gateway}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...authHeaders(cfg), ...(init.headers || {}) },
      signal: controller.signal,
    })
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
    return sendJson(res, 200, { ok: true, version: '35.2.4.0', config: CONFIG_FILE })
  }

  if (path === '/api/hoshinoumi/ui' && req.method === 'GET') {
    const html = readFileSync(UI_FILE, 'utf8')
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
    res.end(html)
    return
  }

  if (path === '/api/hoshinoumi/config' && req.method === 'GET') {
    const cfg = readConfig()
    return sendJson(res, 200, { configured: Boolean(cfg.gateway), gateway: cfg.gateway, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
  }

  if (path === '/api/hoshinoumi/config' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = saveConfig(body)
    return sendJson(res, 200, { ok: true, configured: Boolean(cfg.gateway), gateway: cfg.gateway, target_id: cfg.target_id, hasToken: Boolean(cfg.token) })
  }

  if (path === '/api/hoshinoumi/test' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = { ...readConfig(), ...(body.gateway ? { gateway: String(body.gateway).trim().replace(/\/+$/, '') } : {}), ...(typeof body.token === 'string' ? { token: body.token.trim() } : {}) }
    if (!cfg.gateway) throw new Error('请先填写网关地址')
    const started = Date.now()
    const health = await gatewayFetch(cfg, '/healthz', { method: 'GET' })
    const ready = health.status < 400 ? await gatewayFetch(cfg, '/readyz', { method: 'GET' }) : null
    return sendJson(res, 200, {
      ok: health.status < 400,
      status: health.status,
      latency_ms: Date.now() - started,
      health: health.data,
      ready: ready?.data ?? null,
    })
  }

  if (path === '/api/hoshinoumi/history' && req.method === 'GET') {
    const url = new URL(req.url || '/', 'http://127.0.0.1')
    const cfg = readConfig()
    if (!cfg.gateway) throw new Error('gateway is not configured')
    const target = url.searchParams.get('target_id') || cfg.target_id || 'owner'
    const limit = Math.max(1, Math.min(Number(url.searchParams.get('limit') || 30), 100))
    const out = await gatewayFetch(cfg, `/internal/history?target_id=${encodeURIComponent(target)}&limit=${limit}`, { method: 'GET' })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/chat' && req.method === 'POST') {
    const body = await readBody(req)
    const message = typeof body.message === 'string' ? body.message.trim() : ''
    if (!message) throw new Error('message is empty')
    const cfg = readConfig()
    const target_id = typeof body.target_id === 'string' && body.target_id.trim() ? body.target_id.trim() : cfg.target_id
    const out = await gatewayFetch(cfg, '/api/chat', { method: 'POST', body: JSON.stringify({ message, target_id }) })
    return sendJson(res, out.status, out.data)
  }

  if (path === '/api/hoshinoumi/command' && req.method === 'POST') {
    const body = await readBody(req)
    const cfg = readConfig()
    const out = await gatewayFetch(cfg, '/api/command', { method: 'POST', body: JSON.stringify({ command: String(body.command || ''), args: Array.isArray(body.args) ? body.args : [] }) })
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
