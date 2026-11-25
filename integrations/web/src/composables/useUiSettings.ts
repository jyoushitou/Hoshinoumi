import { computed, ref, watch } from 'vue'

const HIDDEN_KEY = 'hoshinoumi.ui.hiddenPages'
const MOTION_KEY = 'hoshinoumi.ui.motion'

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

watch(hiddenPages, value => {
  try { localStorage.setItem(HIDDEN_KEY, JSON.stringify(value)) } catch { /* ignore */ }
}, { deep: true })

watch(motion, value => {
  try { localStorage.setItem(MOTION_KEY, value ? 'on' : 'off') } catch { /* ignore */ }
  document.documentElement.classList.toggle('motion-off', !value)
}, { immediate: true })

export function useUiSettings() {
  const hiddenCount = computed(() => hiddenPages.value.length)
  function isHidden(page: string) { return hiddenPages.value.includes(page) }
  function togglePage(page: string) {
    if (page === 'settings' || page === 'chat') return
    hiddenPages.value = isHidden(page) ? hiddenPages.value.filter(item => item !== page) : [...hiddenPages.value, page]
  }
  function resetPages() { hiddenPages.value = [] }
  return { hiddenPages, hiddenCount, isHidden, togglePage, resetPages, motion }
}
