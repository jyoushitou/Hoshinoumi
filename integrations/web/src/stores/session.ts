import { ref } from 'vue'
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
  const conversations = ref<unknown[]>([])
  const messages = ref<unknown[]>([])
  const unread = ref(0)
  const persona = ref<Record<string, unknown> | null>(null)
  const relation = ref<Record<string, unknown> | null>(null)
  const savings = ref<Record<string, unknown> | null>(null)
  const weekly = ref<Record<string, unknown> | null>(null)
  const memoryTargets = ref<unknown[]>([])
  const week = ref(getIsoWeek())
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
      week.value = getIsoWeek()
      const [sav, mem, wk] = await Promise.allSettled([
        http.get<Record<string, unknown>>('/api/savings'),
        http.get<{ targets?: unknown[] }>('/api/memory'),
        http.get<Record<string, unknown>>('/api/weekly-plan?week=' + week.value),
      ])
      savings.value = sav.status === 'fulfilled' ? sav.value : null
      memoryTargets.value = mem.status === 'fulfilled' && Array.isArray(mem.value.targets) ? mem.value.targets : []
      weekly.value = wk.status === 'fulfilled' ? wk.value : null
      // v35.5.2 只验证连接；会话/历史在 v35.5.3 接入
      conversations.value = []; messages.value = []
    } catch (e) {
      connected.value = false
      error.value = e instanceof Error ? e.message : String(e)
    } finally { loading.value = false }
  }
  return { loading, connected, error, status, conversations, messages, unread, persona, relation, savings, weekly, memoryTargets, week, refresh }
})
