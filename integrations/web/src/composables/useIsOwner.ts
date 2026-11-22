import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'

/**
 * owner 判定：登录 QQ 必须等于后端 /api/status 返回的 master_qq。
 * 未登录、未拿到 status、或 QQ 不一致时都按非 owner 处理。
 */
export function useIsOwner() {
  const auth = useAuthStore()
  const session = useSessionStore()
  return computed(() => {
    const master = session.status?.master_qq
    if (!auth.loggedIn || master === undefined || master === null || master === '') return false
    return String(auth.qq).trim() === String(master).trim()
  })
}
