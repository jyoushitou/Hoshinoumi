<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'
import { useUiSettings } from '@/composables/useUiSettings'
const session = useSessionStore()
const auth = useAuthStore()
const isOwner = useIsOwner()
const { isHidden } = useUiSettings()
const baseNav = [
  { page: 'home', icon: '⌂', title: '主页' },
  { page: 'chat', icon: '◉', title: 'nao（聊天）' },
  { page: 'memory', icon: '◈', title: '记忆' },
  { page: 'relation', icon: '♡', title: '关系' },
  { page: 'savings', icon: '¥', title: '存钱' },
  { page: 'weekly', icon: '▦', title: '周计划表' },
  { page: 'info', icon: '≡', title: '信息' },
  { page: 'persona', icon: '◇', title: '人设' },
  { page: 'commands', icon: '⌘', title: '命令' },
  { page: 'cron', icon: '◷', title: '定时任务' },
  { page: 'diary', icon: '✎', title: '日记' },
  { page: 'logs', icon: '≣', title: '运行日志' },
]
const nav = computed(() => (isOwner.value ? baseNav : baseNav.filter(n => n.page !== 'relation' && n.page !== 'savings')).filter(n => !isHidden(n.page)))
</script>
<template>
  <aside class="rail">
    <div class="logo">
      <img
        src="@/assets/hoshinoumi.svg"
        alt="Hoshinoumi"
      >
    </div>
    <RouterLink
      v-for="n in nav"
      :key="n.page"
      :to="'/' + n.page"
      class="rnav"
      :title="n.title"
    >
      {{ n.icon }}<span v-if="n.page === 'chat' && session.unread > 0" class="badge">{{ session.unread }}</span>
    </RouterLink>
    <div class="spacer" />
    <RouterLink
      to="/settings"
      class="rail-status"
      :class="{ off: !session.connected || !auth.token }"
      :title="`${session.connected ? '后端已连接' : '后端离线'} · ${auth.token ? 'token 已配置' : '未配置 token'} · schema ${session.status?.schema || '—'}`"
      aria-label="连接状态"
    >
      <i />
    </RouterLink>
    <RouterLink
      to="/settings"
      class="rnav"
      title="设置"
    >
      ⚙
    </RouterLink>
  </aside>
</template>
<style scoped>
.rail{background:#fff;border-right:1px solid var(--line);display:flex;flex-direction:column;align-items:center;padding:14px 0;gap:8px;overflow:auto}
.logo{width:38px;height:38px;display:grid;place-items:center;margin-bottom:14px;border-radius:12px;background:#eef4ff;border:1px solid #dbe8ff}
.logo img{width:24px;height:24px}.rnav{width:40px;height:40px;border-radius:9px;display:grid;place-items:center;color:#7d8ca3;font-size:17px;position:relative;text-decoration:none;transition:background .18s,color .18s,transform .18s}
.rnav:hover{background:#eaf2ff;color:#1d4ed8;transform:translateY(-1px)}.rnav.router-link-active{background:#dbeafe;color:#1d4ed8}
.rnav.router-link-active:before{content:"";position:absolute;left:-12px;width:3px;height:18px;border-radius:3px;background:#2563eb}
.rnav .badge{position:absolute;top:3px;right:2px;min-width:14px;height:14px;border-radius:8px;background:#2563eb;color:#fff;font-size:9px;font-weight:700;display:grid;place-items:center;padding:0 3px}
.spacer{flex:1}.rail-status{width:22px;height:22px;display:grid;place-items:center;border-radius:7px;text-decoration:none;margin-bottom:2px}.rail-status i{width:7px;height:7px;border-radius:50%;background:#1f9d6b;box-shadow:0 0 0 3px #eefbf5}.rail-status.off i{background:#c0264a;box-shadow:0 0 0 3px #fff5f7}.rail-status:hover{background:#f4f9ff}
</style>
