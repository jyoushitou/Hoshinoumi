import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'

/**
 * owner 判定：登录 QQ 必须等于后端 /api/status 返回的 master_qq。
 * 未登录、未拿到 status、或 QQ 不一致时都按非 owner 处理。
 */
function tokenRole(token: string): string {
  try {
    const raw = token.split('.')[1]
    if (!raw) return ''
    const base64 = raw.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64 + '='.repeat((4 - base64.length % 4) % 4)))
    return String(payload?.role || '')
  } catch {
    return ''
  }
}

export function useIsOwner() {
  const auth = useAuthStore()
  const session = useSessionStore()
  return computed(() => {
    if (!auth.loggedIn) return false
    const role = tokenRole(auth.token)
    if (role === 'owner') return true
    if (role === 'user') return false
    const master = session.status?.master_qq
    if (master === undefined || master === null || master === '') return false
    return String(auth.qq).trim() === String(master).trim()
  })
}
