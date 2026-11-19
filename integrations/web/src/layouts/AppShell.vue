<script setup lang="ts">
import RailNav from '@/components/RailNav.vue'
import ConversationList from '@/components/ConversationList.vue'
import ContextPanel from '@/components/ContextPanel.vue'
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
const auth = useAuthStore(); const session = useSessionStore()
onMounted(() => { if (auth.loggedIn) session.refresh(); else session.error = '未登录，请先填写 QQ 和 token' })
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
.shell{display:grid;grid-template-columns:64px 292px minmax(0,1fr) 304px;height:100vh;overflow:hidden}
.main{min-width:0;display:flex;flex-direction:column;background:#fff}
@media(max-width:1180px){.shell{grid-template-columns:64px 270px minmax(0,1fr)}:deep(.context){display:none}}
@media(max-width:820px){.shell{grid-template-columns:54px minmax(0,1fr)}:deep(.side){display:none}}
</style>
