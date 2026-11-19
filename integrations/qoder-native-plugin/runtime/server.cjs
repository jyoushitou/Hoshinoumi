// Hoshinoumi MCP server for Qoder native plugins.
// stdio JSON-RPC; reads backend config from ~/.qoder-cn/hoshinoumi.json
// (or HOSHINOUMI_QODER_CONFIG / ~/.dsh/hoshinoumi.json fallback).
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const VERSION = '1.0.0'
const CONFIG_CANDIDATES = [
  process.env.HOSHINOUMI_QODER_CONFIG,
  path.join(os.homedir(), '.qoder-cn', 'hoshinoumi.json'),
  path.join(os.homedir(), '.dsh', 'hoshinoumi.json'),
].filter(Boolean)

function readConfig() {
  for (const file of CONFIG_CANDIDATES) {
    try {
      const raw = JSON.parse(fs.readFileSync(file, 'utf8'))
      if (!raw || typeof raw !== 'object') continue
      return {
        base_url: String(raw.base_url || raw.gateway || '').replace(/\/+$/, ''),
        token: String(raw.token || ''),
        target_id: String(raw.target_id || 'owner'),
        config_file: file,
      }
    } catch {}
  }
  return { base_url: '', token: '', target_id: 'owner', config_file: CONFIG_CANDIDATES[0] || '' }
}

async function backend(endpoint, method = 'GET', body = null) {
  const cfg = readConfig()
  if (!cfg.base_url) throw new Error(`未配置后端地址，请编辑 ${cfg.config_file || '~/.qoder-cn/hoshinoumi.json'}`)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30000)
  try {
    const headers = { 'content-type': 'application/json' }
    if (cfg.token) headers.authorization = `Bearer ${cfg.token}`
    const res = await fetch(cfg.base_url + endpoint, {
      method,
      headers,
      body: body == null ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
    const text = await res.text()
    let data
    try { data = text ? JSON.parse(text) : {} } catch { data = { raw: text } }
    if (!res.ok) throw new Error(`后端 HTTP ${res.status}: ${JSON.stringify(data).slice(0, 500)}`)
    return data
  } finally {
    clearTimeout(timer)
  }
}

const tools = [
  {
    name: 'hoshinoumi_chat',
    description: '给 Hoshinoumi 机器人 nao 发一条消息并取得回复。适合聊天、问状态、让 nao 做事。',
    inputSchema: {
      type: 'object',
      properties: {
        message: { type: 'string', description: '要发送的消息' },
        target_id: { type: 'string', description: '可选：会话目标 ID，默认主人' },
      },
      required: ['message'],
    },
  },
  {
    name: 'hoshinoumi_history',
    description: '读取和 nao 的最近聊天历史。',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: '条数，默认 20，最大 100' },
        target_id: { type: 'string', description: '可选：目标 ID' },
      },
    },
  },
  {
    name: 'hoshinoumi_status',
    description: '读取 Hoshinoumi 机器人运行状态、记忆/事件/日志计数。',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'hoshinoumi_memory',
    description: '读取记忆：目标列表或指定目标的记忆记录。',
    inputSchema: {
      type: 'object',
      properties: { target_id: { type: 'string', description: '可选：目标 ID' } },
    },
  },
  {
    name: 'hoshinoumi_savings',
    description: '读取存钱总余额、账户和最近流水。',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'hoshinoumi_add_saving',
    description: '手动记一笔存钱/支出/收入。可关联事件，或新建事件，并设置 AI 是否可见。',
    inputSchema: {
      type: 'object',
      properties: {
        account: { type: 'string', description: '账户，例如 银行卡' },
        kind: { type: 'string', enum: ['expense', 'income', 'saving'], description: '类型' },
        amount: { type: ['string', 'number'], description: '金额，例如 35.50' },
        date: { type: 'string', description: '日期 YYYY-MM-DD' },
        note: { type: 'string', description: '备注' },
        event_title: { type: 'string', description: '可选：新建事件标题' },
        event_id: { type: 'number', description: '可选：已有事件 ID' },
        ai_visible: { type: 'boolean', description: '是否让 AI 知道，默认 true' },
      },
      required: ['account', 'kind', 'amount'],
    },
  },
  {
    name: 'hoshinoumi_weekly_plan',
    description: '读取指定周的周计划表。',
    inputSchema: { type: 'object', properties: { week: { type: 'number', description: '周次，默认 1' } } },
  },
  {
    name: 'hoshinoumi_import_weekly',
    description: '导入教务系统课程表 HTML 到指定周。',
    inputSchema: {
      type: 'object',
      properties: {
        html: { type: 'string', description: '教务页面 HTML 内容' },
        week: { type: 'number', description: '周次' },
      },
      required: ['html', 'week'],
    },
  },
  {
    name: 'hoshinoumi_persona',
    description: '读取 personas/* 人设卡摘要。',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'hoshinoumi_relation',
    description: '读取机器人与指定用户的关系亲密度、档位和最近变化。',
    inputSchema: { type: 'object', properties: { target_id: { type: 'string', description: '目标用户 ID，默认主人' } } },
  },
  {
    name: 'hoshinoumi_balance',
    description: '读取 DeepSeek API 余额。',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'hoshinoumi_command',
    description: '执行 Hoshinoumi 的 !命令，例如 status、memory、cron。',
    inputSchema: {
      type: 'object',
      properties: { command: { type: 'string', description: '命令名，不带 !' }, args: { type: 'array', items: { type: 'string' } } },
      required: ['command'],
    },
  },
]

async function callTool(name, args = {}) {
  const cfg = readConfig()
  const tid = args.target_id || cfg.target_id || 'owner'
  switch (name) {
    case 'hoshinoumi_chat':
      return backend('/api/chat', 'POST', { message: String(args.message || ''), target_id: tid })
    case 'hoshinoumi_history': {
      const limit = Math.max(1, Math.min(Number(args.limit || 20), 100))
      return backend(`/internal/history?target_id=${encodeURIComponent(tid)}&limit=${limit}`)
    }
    case 'hoshinoumi_status':
      return backend('/api/status')
    case 'hoshinoumi_memory':
      return backend(args.target_id ? `/api/memory?target_id=${encodeURIComponent(args.target_id)}` : '/api/memory')
    case 'hoshinoumi_savings':
      return backend('/api/savings')
    case 'hoshinoumi_add_saving': {
      const body = {
        account: args.account,
        kind: args.kind,
        amount: args.amount,
        date: args.date || new Date().toISOString().slice(0, 10),
        note: args.note || '',
        event_title: args.event_title || '',
        event_id: args.event_id || null,
        ai_visible: args.ai_visible !== false,
      }
      return backend('/api/savings/entries', 'POST', body)
    }
    case 'hoshinoumi_weekly_plan':
      return backend(`/api/weekly-plan?week=${Math.max(1, Math.min(Number(args.week || 1), 60))}`)
    case 'hoshinoumi_import_weekly':
      return backend('/api/weekly-plan/import', 'POST', { html: String(args.html || ''), week: Number(args.week || 1) })
    case 'hoshinoumi_persona':
      return backend('/api/persona')
    case 'hoshinoumi_relation':
      return backend(args.target_id ? `/api/relation?target_id=${encodeURIComponent(args.target_id)}` : '/api/relation')
    case 'hoshinoumi_balance':
      return backend('/api/balance')
    case 'hoshinoumi_command':
      return backend('/api/command', 'POST', { command: String(args.command || ''), args: Array.isArray(args.args) ? args.args : [] })
    default:
      throw new Error('unknown tool: ' + name)
  }
}

function send(message) {
  process.stdout.write(JSON.stringify(message) + '\n')
}

function result(id, value) {
  send({ jsonrpc: '2.0', id, result: value })
}

function error(id, code, message) {
  send({ jsonrpc: '2.0', id, error: { code, message } })
}

let buffer = ''
function consume() {
  while (true) {
    const headerEnd = buffer.indexOf('\r\n\r\n')
    const lineEnd = buffer.indexOf('\n')
    let raw = ''
    if (buffer.startsWith('Content-Length:')) {
      if (headerEnd < 0) return
      const header = buffer.slice(0, headerEnd)
      const m = /Content-Length:\s*(\d+)/i.exec(header)
      if (!m) { buffer = buffer.slice(headerEnd + 4); continue }
      const len = Number(m[1])
      if (buffer.length < headerEnd + 4 + len) return
      raw = buffer.slice(headerEnd + 4, headerEnd + 4 + len)
      buffer = buffer.slice(headerEnd + 4 + len)
    } else {
      if (lineEnd < 0) return
      raw = buffer.slice(0, lineEnd).trim()
      buffer = buffer.slice(lineEnd + 1)
    }
    if (!raw) continue
    let msg
    try { msg = JSON.parse(raw) } catch { continue }
    handle(msg)
  }
}

async function handle(msg) {
  if (!msg || msg.jsonrpc !== '2.0') return
  const { id, method, params } = msg
  if (method === 'initialize') {
    return result(id, {
      protocolVersion: '2024-11-05',
      capabilities: { tools: {} },
      serverInfo: { name: 'hoshinoumi', version: VERSION },
    })
  }
  if (method === 'notifications/initialized' || method === 'initialized') return
  if (method === 'ping') return result(id, {})
  if (method === 'tools/list') return result(id, { tools })
  if (method === 'tools/call') {
    const name = params?.name
    const args = params?.arguments || {}
    try {
      const data = await callTool(name, args)
      return result(id, { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }], isError: false })
    } catch (e) {
      return result(id, { content: [{ type: 'text', text: 'Hoshinoumi 调用失败：' + (e instanceof Error ? e.message : String(e)) }], isError: true })
    }
  }
  if (id != null) error(id, -32601, 'Method not found: ' + method)
}

process.stdin.setEncoding('utf8')
process.stdin.on('data', (chunk) => { buffer += chunk; consume() })
process.stdin.on('error', () => {})
process.on('uncaughtException', (e) => {
  try { process.stderr.write('[hoshinoumi-mcp] ' + String(e?.stack || e) + '\n') } catch {}
})
