<script setup lang="ts">
import RailNav from '@/components/RailNav.vue'
import ConversationList from '@/components/ConversationList.vue'
import ContextPanel from '@/components/ContextPanel.vue'
import { onBeforeUnmount, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
const auth = useAuthStore(); const session = useSessionStore()
function onFocus() { if (auth.loggedIn) void session.syncNow(true) }
function onVisibility() { if (document.visibilityState === 'visible' && auth.loggedIn) void session.syncNow() }
onMounted(() => {
  if (auth.loggedIn) { void session.refresh(); session.startSync() }
  else session.error = '未登录，请先填写 QQ 和 token'
  window.addEventListener('focus', onFocus)
  document.addEventListener('visibilitychange', onVisibility)
})
onBeforeUnmount(() => {
  window.removeEventListener('focus', onFocus)
  document.removeEventListener('visibilitychange', onVisibility)
  session.stopSync()
})
</script>
<template>
  <div class="shell">
    <RailNav />
    <ConversationList />
    <main class="main">
      <RouterView />
    </main>
    <ContextPanel />
  </div>
</template>
<style scoped>
.shell{display:grid;grid-template-columns:64px 292px minmax(0,1fr) 304px;height:100vh;height:100dvh;overflow:hidden;min-height:0}
.main{min-width:0;min-height:0;height:100%;display:flex;flex-direction:column;background:#fff;overflow:hidden}
@media(max-width:1180px){.shell{grid-template-columns:64px 270px minmax(0,1fr)}:deep(.context){display:none}}
@media(max-width:820px){.shell{grid-template-columns:54px minmax(0,1fr)}:deep(.side){display:none}}
</style>
