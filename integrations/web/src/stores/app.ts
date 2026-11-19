import { defineStore } from 'pinia'
import { ref } from 'vue'
import { http } from '@/api/client'
export const useAppStore = defineStore('app', () => {
  const connected = ref(false)
  const version = ref('')
  const error = ref('')
  async function checkHealth() {
    error.value = ''
    try {
      const r = await http.get<{ status?: string; version?: string }>('/healthz')
      connected.value = r.status === 'ok' || r.status === 'ready'
      version.value = r.version ?? ''
    } catch (e) {
      connected.value = false
      error.value = e instanceof Error ? e.message : String(e)
    }
  }
  return { connected, version, error, checkHealth }
})
