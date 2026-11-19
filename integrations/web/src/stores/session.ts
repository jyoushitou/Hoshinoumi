import { ref } from 'vue'
export interface Conversation {
  target_id: string
  name: string
  type?: string
  count?: number
  last_message?: string
  updated_at?: string
}
export interface ChatMessage {
  id?: number
  role: string
  content: string
  created_at?: string
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
  async function loadConversations() {
    conversationsError.value = ''
    try {
      const r = await http.get<{ data?: Conversation[] }>('/api/conversations')
      conversations.value = Array.isArray(r.data) ? r.data : []
      if (!activeTarget.value && conversations.value.length) {
        await selectConversation(conversations.value[0].target_id)
      }
    } catch (e) {
      conversations.value = []
      conversationsError.value = e instanceof Error ? e.message : String(e)
    }
  }
  async function loadHistory(target: string) {
    if (!target) { messages.value = []; return }
    historyError.value = ''
    try {
      const r = await http.get<{ data?: ChatMessage[] }>('/api/history?target_id=' + encodeURIComponent(target) + '&limit=100')
      messages.value = Array.isArray(r.data) ? r.data : []
    } catch (e) {
      messages.value = []
      historyError.value = e instanceof Error ? e.message : String(e)
    }
  }
  async function selectConversation(target: string) {
    activeTarget.value = target
    await loadHistory(target)
  }

  async function refresh() {
    const auth = useAuthStore()
    if (!auth.loggedIn) { connected.value = false; error.value = '未登录'; return }
    http.setToken(auth.token)
    loading.value = true; error.value = ''
    try {
      await http.get('/healthz')
      const s = await http.get<Record<string, unknown>>('/api/status')
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
    } catch (e) {
      connected.value = false
      error.value = e instanceof Error ? e.message : String(e)
    } finally { loading.value = false }
  }
  return { loading, connected, error, status, conversations, activeTarget, conversationsError, messages, historyError, unread, persona, relation, savings, weekly, memoryTargets, lifeState, presence, week, refresh, selectConversation, loadHistory }
})
