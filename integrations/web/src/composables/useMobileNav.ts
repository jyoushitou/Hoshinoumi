import { computed, ref } from 'vue'
import { isNativeClient } from '@/lib/platform'
import { useUiSettings } from '@/composables/useUiSettings'

export interface MobileEntry {
  key: string
  path: string
  icon: string
  label: string
}

export const mobileEntries: MobileEntry[] = [
  { key: 'home', path: '/home', icon: '⌂', label: '主页' },
  { key: 'chats', path: '/chat', icon: '◉', label: '聊天' },
  { key: 'memory', path: '/memory', icon: '◈', label: '记忆' },
  { key: 'relation', path: '/relation', icon: '♡', label: '关系' },
  { key: 'savings', path: '/savings', icon: '¥', label: '存钱' },
  { key: 'weekly', path: '/weekly', icon: '▦', label: '周计划' },
  { key: 'books', path: '/books', icon: '▤', label: '阅读' },
  { key: 'info', path: '/info', icon: '≡', label: '信息' },
  { key: 'persona', path: '/persona', icon: '◇', label: '人设' },
  { key: 'commands', path: '/commands', icon: '⌘', label: '命令' },
  { key: 'cron', path: '/cron', icon: '◷', label: '定时' },
  { key: 'diary', path: '/diary', icon: '✎', label: '日记' },
  { key: 'logs', path: '/logs', icon: '≣', label: '日志' },
  { key: 'settings', path: '/settings', icon: '⚙', label: '设置' },
]

const STORAGE_KEY = 'hoshinoumi.mobile.quick'
const DEFAULT_KEYS = ['chats', 'memory', 'relation', 'settings']
const MIN_QUICK = 1
const MAX_QUICK = 5

function loadQuick(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? (JSON.parse(raw) as unknown) : null
    if (Array.isArray(parsed)) {
      const valid = parsed.filter((key): key is string => typeof key === 'string' && mobileEntries.some(entry => entry.key === key))
      if (valid.length >= MIN_QUICK && valid.length <= MAX_QUICK) return valid
    }
  } catch { /* ignore malformed storage */ }
  return [...DEFAULT_KEYS]
}

const quickKeys = ref<string[]>(loadQuick())

function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(quickKeys.value)) } catch { /* storage unavailable */ }
}

export function useMobileNav() {
  const { hiddenPages } = useUiSettings()
  const visibleMobileEntries = computed(() => (isNativeClient() ? mobileEntries.filter(entry => entry.key !== 'logs') : mobileEntries).filter(entry => !hiddenPages.value.includes(entry.key)))
  const quickEntries = computed(() => visibleMobileEntries.value.filter(entry => quickKeys.value.includes(entry.key)))

  function toggleQuick(key: string) {
    const index = quickKeys.value.indexOf(key)
    if (index >= 0) {
      if (quickKeys.value.length <= MIN_QUICK) return { ok: false, message: '至少保留一个快捷入口' }
      quickKeys.value.splice(index, 1)
    } else {
      if (quickKeys.value.length >= MAX_QUICK) return { ok: false, message: '最多选择 5 个' }
      quickKeys.value.push(key)
    }
    persist()
    return { ok: true, message: '' }
  }

  function resetQuick() {
    quickKeys.value = [...DEFAULT_KEYS]
    persist()
  }

  return { entries: visibleMobileEntries, quickEntries, quickKeys, toggleQuick, resetQuick, min: MIN_QUICK, max: MAX_QUICK }
}
