import { ref } from 'vue'
export interface Conversation {
  target_id: string
  name: string
  type?: string
  member_count?: number
  count?: number
  last_message?: string
  updated_at?: string
  unread?: number
  last_read_id?: number
}
export interface ChatMessage {
  id?: number | string
  role: string
  content: string
  created_at?: string
  pending?: boolean
  image_url?: string
  audio_url?: string
  kind?: string
  recalled?: boolean
  recall_notice?: string
  recalled_by?: string
}
export interface HistoryResponse {
  ok?: boolean
  data?: ChatMessage[]
  next_seq?: number
  has_more?: boolean
}
export interface Attachment {
  image?: string
  sticker?: string
  audio?: string
}
import { defineStore } from 'pinia'
import { http } from '@/api/client'
import { useAuthStore } from './auth'
function getIsoWeek(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const day = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - day)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
}
export const useSessionStore = defineStore('session', () => {
  const loading = ref(false)
  const connected = ref(false)
  const error = ref('')
  const status = ref<Record<string, unknown> | null>(null)
  const statusLatencyMs = ref<number | null>(null)
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const activeTarget = ref('')
  const conversationsError = ref('')
  const historyError = ref('')
  const unread = ref(0)
  const persona = ref<Record<string, unknown> | null>(null)
  const relation = ref<Record<string, unknown> | null>(null)
  const savings = ref<Record<string, unknown> | null>(null)
  const weekly = ref<Record<string, unknown> | null>(null)
  const memoryTargets = ref<unknown[]>([])
  const lifeState = ref<Record<string, unknown> | null>(null)
  const presence = ref<Record<string, unknown> | null>(null)
  const week = ref(getIsoWeek())
  const sending = ref(false)
  const sendError = ref('')
  const lastSeq = ref(0)
  const syncState = ref<'idle' | 'syncing' | 'online' | 'offline'>('idle')
  const syncError = ref('')
  const lastSyncAt = ref('')
  const syncGap = ref(false)
  let syncTimer: ReturnType<typeof setInterval> | null = null
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let syncInFlight = false
  let retryDelay = 5000
  async function loadConversations() {
    conversationsError.value = ''
    try {
      const r = await http.get<{ data?: Conversation[] }>('/api/conversations')
      conversations.value = Array.isArray(r.data) ? r.data : []
      unread.value = conversations.value.reduce((n, c) => n + Number(c.unread || 0), 0)
      if (!activeTarget.value && conversations.value.length) {
        await selectConversation(conversations.value[0].target_id)
      }
    } catch (e) {
      conversations.value = []
      conversationsError.value = e instanceof Error ? e.message : String(e)
    }
  }
  function seqOf(m: ChatMessage) {
    const n = Number(m.id)
    return Number.isFinite(n) ? n : 0
  }
  function appendUnique(rows: ChatMessage[]) {
    const seen = new Set(messages.value.map(m => String(m.id)))
    for (const m of rows) {
      if (m.id !== undefined && m.id !== null && seen.has(String(m.id))) continue
      messages.value.push(m)
    }
  }
  async function markRead(target: string) {
    if (!target) return
    const last = Math.max(0, ...messages.value.map(seqOf))
    if (!last) return
    try {
      await http.post('/api/read', { target_id: target, last_read_id: last })
      const conv = conversations.value.find(c => c.target_id === target)
      if (conv) { conv.unread = 0; conv.last_read_id = last }
      unread.value = conversations.value.reduce((n, c) => n + Number(c.unread || 0), 0)
    } catch { /* 未读上报失败不阻塞聊天 */ }
  }
  async function loadHistory(target: string) {
    if (!target) { messages.value = []; lastSeq.value = 0; return }
    historyError.value = ''
    try {
      const r = await http.get<HistoryResponse>('/api/history?target_id=' + encodeURIComponent(target) + '&limit=100')
      messages.value = Array.isArray(r.data) ? r.data : []
      lastSeq.value = typeof r.next_seq === 'number' ? r.next_seq : Math.max(0, ...messages.value.map(seqOf))
      syncState.value = 'online'; syncError.value = ''
      lastSyncAt.value = new Date().toLocaleTimeString()
    } catch (e) {
      messages.value = []
      historyError.value = e instanceof Error ? e.message : String(e)
      syncState.value = 'offline'; syncError.value = historyError.value
    }
  }
  async function selectConversation(target: string) {
    activeTarget.value = target
    await loadHistory(target)
    await markRead(target)
  }
  async function syncNow(force = false) {
    const auth = useAuthStore()
    if (!auth.loggedIn || !activeTarget.value || syncInFlight) return
    if (!force && typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    syncInFlight = true
    syncState.value = 'syncing'; syncError.value = ''
    try {
      let after = lastSeq.value
      let more = false
      for (let page = 0; page < 5; page++) {
        const r = await http.get<HistoryResponse>('/api/history?target_id=' + encodeURIComponent(activeTarget.value) + '&after_seq=' + after + '&limit=100')
        const rows = Array.isArray(r.data) ? r.data : []
        appendUnique(rows)
        if (typeof r.next_seq === 'number') after = Math.max(after, r.next_seq)
        more = Boolean(r.has_more)
        if (!more || rows.length === 0) break
      }
      lastSeq.value = after
      syncGap.value = more
      syncState.value = 'online'
      lastSyncAt.value = new Date().toLocaleTimeString()
      await refreshRecalls()
      await markRead(activeTarget.value)
      await loadConversations()
      retryDelay = 5000
      if (retryTimer) { clearTimeout(retryTimer); retryTimer = null }
    } catch (e) {
      syncState.value = 'offline'
      syncError.value = e instanceof Error ? e.message : String(e)
      if (retryTimer) clearTimeout(retryTimer)
      retryTimer = setTimeout(() => { retryTimer = null; void syncNow(true) }, retryDelay)
      retryDelay = Math.min(retryDelay * 2, 30000)
    } finally {
      syncInFlight = false
    }
  }
  function startSync() {
    if (syncTimer !== null) return
    syncTimer = setInterval(() => { void syncNow() }, 5000)
  }
  function stopSync() {
    if (syncTimer !== null) { clearInterval(syncTimer); syncTimer = null }
    if (retryTimer) { clearTimeout(retryTimer); retryTimer = null }
    syncState.value = 'idle'
  }

  async function sendMessage(content: string, attachment: Attachment = {}) {
    const text = content.trim()
    const { image, sticker, audio } = attachment
    if ((!text && !image && !sticker && !audio) || sending.value) return false
    if (!activeTarget.value) { sendError.value = '请先选择会话'; return false }
    const kind = sticker ? 'sticker' : audio ? 'voice' : image ? 'image' : ''
    const imageUrl = image || sticker
    const clientId = (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`)
    const localId = 'local-' + clientId
    const stamp = new Date().toISOString().slice(0, 19).replace('T', ' ')
    messages.value.push({ id: localId, role: 'user', content: text, image_url: imageUrl || undefined, audio_url: audio || undefined, kind, created_at: stamp, pending: true })
    sending.value = true; sendError.value = ''
    try {
      const r = await http.post<{ success?: boolean; reply?: string; segments?: string[]; error?: string; message?: string }>('/api/chat', {
        message: text,
        target_id: activeTarget.value,
        memory_target: activeTarget.value.startsWith('mode:') ? 'persona:nao' : activeTarget.value,
        client_message_id: clientId,
        ...(image ? { image } : {}),
        ...(sticker ? { sticker } : {}),
        ...(audio ? { audio } : {}),
      })
      if (!r.reply) throw new Error(r.message || r.error || '发送失败')
      messages.value = messages.value.filter(m => m.id !== localId)
      const target = activeTarget.value
      await loadHistory(target)
      if (!messages.value.length) {
        messages.value.push({ role: 'user', content: text, image_url: imageUrl || undefined, audio_url: audio || undefined, kind, created_at: stamp })
        const segments = Array.isArray(r.segments) && r.segments.length ? r.segments : [r.reply]
        for (const [index, segment] of segments.entries()) {
          messages.value.push({ role: 'assistant', content: segment, created_at: new Date(Date.now() + index * 1000).toISOString().slice(0, 19).replace('T', ' ') })
        }
        lastSeq.value = Math.max(lastSeq.value, ...messages.value.map(seqOf))
      }
      return true
    } catch (e) {
      messages.value = messages.value.filter(m => m.id !== localId)
      sendError.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      sending.value = false
    }
  }

  async function recallMessage(messageId: number | string) {
    try {
      await http.post(`/api/messages/${encodeURIComponent(String(messageId))}/recall`, { message_id: messageId })
      const m = messages.value.find(x => String(x.id) === String(messageId))
      if (m) { m.recalled = true; m.content = ''; m.image_url = undefined; m.audio_url = undefined; m.kind = undefined }
      await loadHistory(activeTarget.value)
      return true
    } catch (e) {
      sendError.value = e instanceof Error ? e.message : String(e)
      return false
    }
  }
  async function refreshRecalls() {
    if (!activeTarget.value) return
    try {
      const r = await http.get<HistoryResponse>('/api/history?target_id=' + encodeURIComponent(activeTarget.value) + '&limit=100')
      const rows = Array.isArray(r.data) ? r.data : []
      const map = new Map(rows.map(m => [String(m.id), m]))
      for (const m of messages.value) {
        const fresh = map.get(String(m.id))
        if (fresh?.recalled && !m.recalled) {
          m.recalled = true; m.content = ''; m.image_url = undefined; m.audio_url = undefined; m.kind = undefined
          m.recall_notice = fresh.recall_notice
        }
      }
    } catch { /* 静默，不能影响聊天 */ }
  }

  async function refresh() {
    const auth = useAuthStore()
    if (!auth.loggedIn) { connected.value = false; error.value = '未登录'; return }
    http.setToken(auth.token)
    loading.value = true; error.value = ''
    try {
      await http.get('/healthz')
      const t0 = performance.now()
      const s = await http.get<Record<string, unknown>>('/api/status')
      statusLatencyMs.value = Math.round(performance.now() - t0)
      status.value = s; connected.value = true
      try {
        const p = await http.get<{ data?: Array<Record<string, unknown>> }>('/api/persona')
        const list = Array.isArray(p.data) ? p.data : []
        persona.value = list.find(x => x.active) ?? list[0] ?? null
      } catch { persona.value = null }
      try {
        relation.value = await http.get<Record<string, unknown>>('/api/relation')
      } catch { relation.value = null }
      try {
        lifeState.value = (await http.get<{ data?: Record<string, unknown> }>('/api/state')).data ?? null
      } catch { lifeState.value = null }
      try {
        presence.value = await http.get<Record<string, unknown>>('/api/presence')
      } catch { presence.value = null }
      week.value = getIsoWeek()
      const [sav, mem, wk] = await Promise.allSettled([
        http.get<Record<string, unknown>>('/api/savings'),
        http.get<{ targets?: unknown[] }>('/api/memory'),
        http.get<Record<string, unknown>>('/api/weekly-plan?week=' + week.value),
      ])
      savings.value = sav.status === 'fulfilled' ? sav.value : null
      memoryTargets.value = mem.status === 'fulfilled' && Array.isArray(mem.value.targets) ? mem.value.targets : []
      weekly.value = wk.status === 'fulfilled' ? wk.value : null
      await loadConversations()
      startSync()
    } catch (e) {
      connected.value = false
      error.value = e instanceof Error ? e.message : String(e)
    } finally { loading.value = false }
  }
  return { loading, connected, error, status, statusLatencyMs, conversations, activeTarget, conversationsError, messages, historyError, unread, persona, relation, savings, weekly, memoryTargets, lifeState, presence, week, sending, sendError, lastSeq, syncState, syncError, lastSyncAt, syncGap, refresh, selectConversation, loadHistory, sendMessage, syncNow, startSync, stopSync, markRead, recallMessage, refreshRecalls }
})
