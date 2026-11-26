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
export const contextHandleY = ref(Number(localStorage.getItem('hoshinoumi.layout.contextHandleY') || 46))

for (const [key, state] of [['hoshinoumi.layout.railHidden', railHidden], ['hoshinoumi.layout.sideHidden', sideHidden], ['hoshinoumi.layout.contextHidden', contextHidden]] as const) {
  watch(state, value => { try { localStorage.setItem(key, value ? '1' : '0') } catch { /* ignore */ } })
}
watch(contextHandleY, value => {
  try { localStorage.setItem('hoshinoumi.layout.contextHandleY', String(Math.max(8, Math.min(92, value)))) } catch { /* ignore */ }
})

export function setContextHandleY(value: number) {
  contextHandleY.value = Math.max(8, Math.min(92, value))
}
