import { ref, watch } from 'vue'

function boolean(key: string, fallback = false) {
  try {
    const raw = localStorage.getItem(key)
    if (raw === '1') return true
    if (raw === '0') return false
  } catch { /* storage unavailable */ }
  return fallback
}

export const railHidden = ref(boolean('hoshinoumi.layout.railHidden'))
export const sideHidden = ref(boolean('hoshinoumi.layout.sideHidden'))
export const contextHidden = ref(boolean('hoshinoumi.layout.contextHidden'))
export const contextHandleTop = ref(Number(localStorage.getItem('hoshinoumi.rightHandleTop') || 52))

for (const [key, state] of [['hoshinoumi.layout.railHidden', railHidden], ['hoshinoumi.layout.sideHidden', sideHidden], ['hoshinoumi.layout.contextHidden', contextHidden]] as const) {
  watch(state, value => { try { localStorage.setItem(key, value ? '1' : '0') } catch { /* ignore */ } })
}
watch(contextHandleTop, value => {
  try { localStorage.setItem('hoshinoumi.rightHandleTop', String(value)) } catch { /* ignore */ }
})

export function setContextHandleTop(value: number) {
  const max = typeof window === 'undefined' ? 800 : Math.max(60, window.innerHeight - 64)
  contextHandleTop.value = Math.max(8, Math.min(max, Math.round(value)))
}
