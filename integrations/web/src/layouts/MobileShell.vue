<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MobileChatView from '@/views/mobile/MobileChatView.vue'
import MobilePageView from '@/views/mobile/MobilePageView.vue'
import MobileSettingsView from '@/views/mobile/MobileSettingsView.vue'
import MobilePermissionsView from '@/views/mobile/MobilePermissionsView.vue'
import MobileWeeklyView from '@/views/mobile/MobileWeeklyView.vue'
import MobileTabBar from '@/components/mobile/MobileTabBar.vue'
import MobileReminderPopup from '@/components/mobile/MobileReminderPopup.vue'
import { useAuthStore } from '@/stores/auth'
import { mobileEntries } from '@/composables/useMobileNav'
import { useSessionStore } from '@/stores/session'
import { useIsOwner } from '@/composables/useIsOwner'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const session = useSessionStore()
const isOwner = useIsOwner()
const viewportHeight = ref(0)
const chatDetail = ref(false)
const keyboardOpen = ref(false)
let visualViewport: VisualViewport | null = null
const shellStyle = computed(() => viewportHeight.value > 0 ? { height: viewportHeight.value + 'px' } : {})
function syncViewport() {
  const height = visualViewport?.height ?? window.innerHeight
  const safe = Math.max(320, Math.round(Number(height) || 0))
  viewportHeight.value = safe
  if (typeof document !== 'undefined') document.documentElement.style.setProperty('--app-height', safe + 'px')
  if (visualViewport && visualViewport.offsetTop > 0) window.scrollTo(0, 0)
}
function syncViewportSoon() {
  window.setTimeout(syncViewport, 50)
  window.setTimeout(syncViewport, 320)
}

const titles: Record<string, string> = {
  chat: '聊天', home: '主页', memory: '记忆', relation: '关系', savings: '存钱',
  weekly: '周计划', info: '信息', persona: '人设', commands: '命令', cron: '定时任务',
  logs: '运行日志', settings: '设置',
}
const pageTransition = ref('page-left')
const pageOrder = mobileEntries.map(entry => entry.path)
const pageView = computed(() => {
  if (route.name === 'relation' && !isOwner.value) return MobileChatView
  if (route.name === 'chat') return MobileChatView
  if (route.name === 'settings') return MobileSettingsView
  if (route.name === 'permissions') return MobilePermissionsView
  if (route.name === 'weekly') return MobileWeeklyView
  return MobilePageView
})
const title = computed(() => titles[String(route.name)] ?? 'Hoshinoumi')
watch(() => route.name, () => { chatDetail.value = false })
watch(() => route.path, (to, from) => {
  const a = pageOrder.indexOf(from)
  const b = pageOrder.indexOf(to)
  pageTransition.value = b >= 0 && a >= 0 && b < a ? 'page-right' : 'page-left'
})

watchEffect(() => {
  if (route.name !== 'relation') return
  if (!auth.loggedIn) { void router.replace('/chat'); return }
  if (session.status && !isOwner.value) void router.replace('/chat')
})

onMounted(() => {
  visualViewport = window.visualViewport
  syncViewport()
  visualViewport?.addEventListener('resize', syncViewport)
  visualViewport?.addEventListener('scroll', syncViewport)
  window.addEventListener('resize', syncViewport)
  window.addEventListener('focusin', syncViewportSoon)
  window.addEventListener('focusout', syncViewportSoon)
  const keyboard = (window as any).Capacitor?.Plugins?.Keyboard
  keyboard?.addListener?.('keyboardWillShow', () => { keyboardOpen.value = true })
  keyboard?.addListener?.('keyboardWillHide', () => { keyboardOpen.value = false })
  if (auth.loggedIn) { void session.refresh(); session.startSync() }
})
onBeforeUnmount(() => {
  visualViewport?.removeEventListener('resize', syncViewport)
  visualViewport?.removeEventListener('scroll', syncViewport)
  window.removeEventListener('resize', syncViewport)
  window.removeEventListener('focusin', syncViewportSoon)
  window.removeEventListener('focusout', syncViewportSoon)
  session.stopSync()
})
</script>

<template>
  <div class="mobile-shell" :class="{ 'keyboard-open': keyboardOpen }" :style="shellStyle">
    <header class="mobile-header">
      <span class="logo">✦</span>
      <span class="brand">HOSHINOUMI<small>{{ title }}</small></span>
      <span class="conn" :class="{ off: !session.connected }">{{ session.connected ? '在线' : '离线' }}</span>
    </header>
    <main class="mobile-main">
      <Transition :name="pageTransition" mode="out-in">
        <component :is="pageView" :key="route.path" @detail-change="chatDetail = $event" />
      </Transition>
    </main>
    <MobileReminderPopup />
    <MobileTabBar v-if="!chatDetail && !keyboardOpen" />
  </div>
</template>

<style scoped>
.mobile-shell{position:fixed;top:0;left:0;right:0;width:100%;height:100vh;height:100dvh;height:var(--app-height,100dvh);display:flex;flex-direction:column;background:#f7faff;color:#17263b;overflow:hidden}
.mobile-header{flex:none;height:calc(50px + env(safe-area-inset-top));display:flex;align-items:center;gap:9px;padding:env(safe-area-inset-top) 14px 0;background:rgba(255,255,255,.92);border-bottom:1px solid #e5edf9}
.logo{width:28px;height:28px;border-radius:9px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:13px}
.brand{font-size:11px;font-weight:800;letter-spacing:.12em;line-height:1.1}
.brand small{display:block;font-size:7px;letter-spacing:.22em;color:#8a9bb0;font-weight:600;margin-top:2px}
.conn{margin-left:auto;font-size:8px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:10px;padding:3px 7px}
.conn.off{color:#8a9bb0;border-color:#e1e8f1;background:#f8fafc}
.mobile-main{position:relative;flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;touch-action:pan-y}
.mobile-shell.keyboard-open :deep(.mc){padding-bottom:0}
.mobile-shell.keyboard-open :deep(.composer){padding-bottom:0}
.page-left-enter-active,.page-left-leave-active,.page-right-enter-active,.page-right-leave-active{transition:opacity .2s ease,transform .28s cubic-bezier(.22,1,.36,1)}
.page-left-enter-from{opacity:0;transform:translateX(18px)}
.page-left-leave-to{opacity:0;transform:translateX(-14px)}
.page-right-enter-from{opacity:0;transform:translateX(-18px)}
.page-right-leave-to{opacity:0;transform:translateX(14px)}
@media(prefers-reduced-motion:reduce){.page-left-enter-active,.page-left-leave-active,.page-right-enter-active,.page-right-leave-active{transition:none}}
</style>
