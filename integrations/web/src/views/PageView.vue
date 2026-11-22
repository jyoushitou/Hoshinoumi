<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const title = computed(() => (route.meta.title as string) || '页面')
const desc = computed(() => (route.meta.desc as string) || 'v35.5 Web 页面框架')
</script>
<template>
  <div class="page">
    <div class="head">
      <div><h1>{{ title }}</h1><p>{{ desc }}</p></div><RouterLink
        to="/chat"
        class="back"
      >
        ← 返回聊天
      </RouterLink>
    </div><div class="placeholder">
      <div class="ico">
        ◈
      </div><b>{{ title }}</b><p>页面框架已就绪，具体功能在对应次次版本实现。</p>
    </div>
    <p v-if="route.name === 'settings'" class="page-credit">POWERED BY JYOUSUITOU</p>
  </div>
</template>
<style scoped>
.page{padding:22px 24px;overflow:auto;flex:1}.page-credit{text-align:center;margin:26px 0 6px;font:8px ui-monospace,monospace;letter-spacing:.14em;color:#a8b5c7}.head{display:flex;align-items:center;gap:12px;margin-bottom:16px}.head h1{font-size:20px;margin:0;color:#17263b}.head p{font-size:10.5px;color:#6b7c95;margin:4px 0 0}.back{margin-left:auto;font-size:10px;color:#2563eb;border:1px solid #dbe8ff;border-radius:8px;padding:5px 9px;text-decoration:none;background:#fff}.placeholder{border:1px dashed #cfe0f7;border-radius:12px;background:#f8fbff;padding:32px;display:grid;place-items:center;text-align:center;color:#6b7c95}.ico{width:34px;height:34px;border-radius:10px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;margin-bottom:8px}.placeholder b{color:#1e3a5f}.placeholder p{font-size:10px;margin:5px 0 0}
</style>
