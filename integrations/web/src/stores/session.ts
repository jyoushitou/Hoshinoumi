import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/api/client'
import { useAuthStore } from './auth'
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
      // v35.5.2 只验证连接；会话/历史在 v35.5.3 接入
      conversations.value = []; messages.value = []
    } catch (e) {
      connected.value = false
      error.value = e instanceof Error ? e.message : String(e)
    } finally { loading.value = false }
  }
  return { loading, connected, error, status, conversations, messages, unread, persona, relation, refresh }
})
