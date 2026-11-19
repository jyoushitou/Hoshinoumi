<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useAppStore } from '@/stores/app'
const app = useAppStore()
onMounted(() => app.checkHealth())
</script>
<template>
  <div class="shell">
    <header class="top">
      <img
        src="./assets/hoshinoumi.svg"
        alt="Hoshinoumi"
      ><b>Hoshinoumi Web</b><span class="ver">v35.5.0</span><span class="state">{{ app.connected ? '已连接' : '未连接' }}</span>
    </header>
    <nav>
      <RouterLink to="/">
        主页
      </RouterLink><RouterLink to="/chat">
        聊天
      </RouterLink>
    </nav>
    <main><RouterView /></main>
  </div>
</template>
<style scoped>
.shell{max-width:960px;margin:0 auto;padding:28px}.top{display:flex;align-items:center;gap:10px}.top img{width:32px;height:32px}.ver{font-size:10px;color:var(--muted);border:1px solid var(--line);border-radius:20px;padding:2px 8px}.state{margin-left:auto;font-size:11px;color:var(--blue)}nav{display:flex;gap:14px;margin:18px 0}nav a{color:var(--muted);text-decoration:none;font-size:13px}nav a.router-link-active{color:var(--blue)}main{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px;min-height:360px}
</style>
