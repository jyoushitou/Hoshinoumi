import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/api/client'
const TOKEN_KEY = 'hsh_web_token'
const QQ_KEY = 'hsh_web_qq'
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const qq = ref(localStorage.getItem(QQ_KEY) || '')
  const validated = ref(false)
  const authError = ref('')
  const loggedIn = computed(() => Boolean(token.value && qq.value))
  function setCredentials(nextToken: string, nextQQ: string) {
    token.value = nextToken.trim(); qq.value = nextQQ.trim()
    localStorage.setItem(TOKEN_KEY, token.value); localStorage.setItem(QQ_KEY, qq.value)
  }
  function logout() { token.value = ''; qq.value = ''; validated.value = true; authError.value = ''; localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(QQ_KEY) }
  async function validate() {
    if (!token.value || !qq.value) { validated.value = true; return }
    try {
      await http.get('/api/status', token.value)
      validated.value = true
      authError.value = ''
    } catch (e) {
      const status = (e as { status?: number }).status
      if (status === 401 || status === 403) {
        token.value = ''; qq.value = ''
        localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(QQ_KEY)
        authError.value = '登录已失效，请重新填写 QQ 和 token'
      } else {
        authError.value = '连接后端失败：' + (e instanceof Error ? e.message : String(e))
      }
      validated.value = true
    }
  }
  return { token, qq, validated, authError, loggedIn, setCredentials, logout, validate }
})
