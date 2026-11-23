<script setup lang="ts">
import { ref } from 'vue'
const tab = ref<'memory' | 'events' | 'profile' | 'relation'>('memory')
const tabs = [
  { key: 'memory', label: '记忆' },
  { key: 'events', label: '事件' },
  { key: 'profile', label: '画像' },
  { key: 'relation', label: '关系' },
] as const
</script>

<template>
  <section class="memory">
    <header class="head">
      <div><h1>记忆</h1><p>记忆本 / 事件 / 画像 / 关系</p></div>
      <span class="sync">只读预览</span>
    </header>
    <nav class="tabs">
      <button v-for="item in tabs" :key="item.key" type="button" :class="{ on: tab === item.key }" @click="tab = item.key">{{ item.label }}</button>
    </nav>
    <div class="overview">
      <div class="stat"><b>—</b><small>记忆条数</small></div>
      <div class="stat"><b>—</b><small>会话</small></div>
      <div class="stat"><b>—</b><small>长期</small></div>
    </div>
    <div class="empty">
      <b>记忆页框架已接入</b>
      <p>具体统计、列表、事件和画像在 v35.9.2.2–2.6 接入。</p>
    </div>
  </section>
</template>

<style scoped>
.memory{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b}
.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.sync{margin-left:auto;font-size:8px;color:#8a9bb0;border:1px solid #e3ebf7;background:#fff;border-radius:20px;padding:3px 7px}
.tabs{display:flex;gap:5px;margin-bottom:11px}.tabs button{flex:1;height:31px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;color:#7d8ca3;font:10px inherit;cursor:pointer}.tabs button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
.overview{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:11px}.stat{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:10px;text-align:center}.stat b{display:block;font-size:19px;color:#1e3a5f}.stat small{display:block;font-size:8px;color:#9aabc0;margin-top:2px}
.empty{background:#fff;border:1px dashed #cfe0f7;border-radius:12px;padding:26px;text-align:center;color:#8a9bb0}.empty b{color:#314a65;font-size:11px}.empty p{font-size:9px;margin:5px 0 0}
@media(min-width:821px){.memory{padding:22px 24px}.overview{max-width:520px}.empty{max-width:520px}}
</style>
