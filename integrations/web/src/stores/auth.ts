import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
const TOKEN_KEY = 'hsh_web_token'
const QQ_KEY = 'hsh_web_qq'
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const qq = ref(localStorage.getItem(QQ_KEY) || '')
  const guest = ref(false)
  const loggedIn = computed(() => Boolean(token.value && qq.value))
  function setCredentials(nextToken: string, nextQQ: string) {
    token.value = nextToken.trim(); qq.value = nextQQ.trim()
    localStorage.setItem(TOKEN_KEY, token.value); localStorage.setItem(QQ_KEY, qq.value)
  }
  function logout() { token.value = ''; qq.value = ''; localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(QQ_KEY) }
  function enterGuest() { guest.value = true }
  return { token, qq, guest, loggedIn, setCredentials, logout, enterGuest }
})
