<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import MobileChatView from '@/views/mobile/MobileChatView.vue'
import MobilePageView from '@/views/mobile/MobilePageView.vue'
import MobileSettingsView from '@/views/mobile/MobileSettingsView.vue'
import MobileTabBar from '@/components/mobile/MobileTabBar.vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const auth = useAuthStore()
const session = useSessionStore()

const titles: Record<string, string> = {
  chat: '聊天', home: '主页', memory: '记忆', relation: '关系', savings: '存钱',
  weekly: '周计划', info: '信息', persona: '人设', commands: '命令', cron: '定时任务',
  logs: '运行日志', settings: '设置',
}
const pageView = computed(() => {
  if (route.name === 'chat') return MobileChatView
  if (route.name === 'settings') return MobileSettingsView
  return MobilePageView
})
const title = computed(() => titles[String(route.name)] ?? 'Hoshinoumi')

onMounted(() => {
  if (auth.loggedIn) { void session.refresh(); session.startSync() }
})
onBeforeUnmount(() => session.stopSync())
</script>

<template>
  <div class="mobile-shell">
    <header class="mobile-header">
      <span class="logo">✦</span>
      <span class="brand">HOSHINOUMI<small>{{ title }}</small></span>
      <span class="conn" :class="{ off: !session.connected }">{{ session.connected ? '在线' : '离线' }}</span>
    </header>
    <main class="mobile-main">
      <component :is="pageView" />
    </main>
    <MobileTabBar />
  </div>
</template>

<style scoped>
.mobile-shell{height:100vh;height:100dvh;display:flex;flex-direction:column;background:#f7faff;color:#17263b;overflow:hidden}
.mobile-header{flex:none;height:50px;display:flex;align-items:center;gap:9px;padding:0 14px;background:rgba(255,255,255,.92);border-bottom:1px solid #e5edf9}
.logo{width:28px;height:28px;border-radius:9px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:13px}
.brand{font-size:11px;font-weight:800;letter-spacing:.12em;line-height:1.1}
.brand small{display:block;font-size:7px;letter-spacing:.22em;color:#8a9bb0;font-weight:600;margin-top:2px}
.conn{margin-left:auto;font-size:8px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:10px;padding:3px 7px}
.conn.off{color:#8a9bb0;border-color:#e1e8f1;background:#f8fafc}
.mobile-main{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch}
</style>
