import { computed, ref, watch } from 'vue'

const HIDDEN_KEY = 'hoshinoumi.ui.hiddenPages'
const MOTION_KEY = 'hoshinoumi.ui.motion'
const NAV_HIDDEN_KEY = 'hoshinoumi.mobile.navHidden'
const NAV_BALL_KEY = 'hoshinoumi.mobile.navBall'

function readHidden(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(HIDDEN_KEY) || '[]')
    return Array.isArray(raw) ? raw.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
}

const hiddenPages = ref<string[]>(readHidden())
const motion = ref(localStorage.getItem(MOTION_KEY) !== 'off')
const navHidden = ref(localStorage.getItem(NAV_HIDDEN_KEY) === '1')
const navBall = ref(localStorage.getItem(NAV_BALL_KEY) === '1')

watch(hiddenPages, value => {
  try { localStorage.setItem(HIDDEN_KEY, JSON.stringify(value)) } catch { /* ignore */ }
}, { deep: true })

watch(motion, value => {
  try { localStorage.setItem(MOTION_KEY, value ? 'on' : 'off') } catch { /* ignore */ }
  document.documentElement.classList.toggle('motion-off', !value)
}, { immediate: true })

watch(navHidden, value => { try { localStorage.setItem(NAV_HIDDEN_KEY, value ? '1' : '0') } catch { /* ignore */ } })
watch(navBall, value => { try { localStorage.setItem(NAV_BALL_KEY, value ? '1' : '0') } catch { /* ignore */ } })

export function useUiSettings() {
  const hiddenCount = computed(() => hiddenPages.value.length)
  function isHidden(page: string) { return hiddenPages.value.includes(page) }
  function togglePage(page: string) {
    if (page === 'settings' || page === 'chat') return
    hiddenPages.value = isHidden(page) ? hiddenPages.value.filter(item => item !== page) : [...hiddenPages.value, page]
  }
  function resetPages() { hiddenPages.value = [] }
  return { hiddenPages, hiddenCount, isHidden, togglePage, resetPages, motion, navHidden, navBall }
}
