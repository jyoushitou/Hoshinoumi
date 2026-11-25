<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface LogRow { time: string; level: string; text: string }
const logs = ref<LogRow[]>([])
const level = ref('ALL')
const query = ref('')
const loading = ref(false)
const error = ref('')

const visible = computed(() => logs.value.filter(row => (level.value === 'ALL' || row.level === level.value) && (!query.value.trim() || row.text.toLowerCase().includes(query.value.trim().toLowerCase()))))

function parseLog(line: string) {
  const raw = String(line || '').trimEnd()
  const match = raw.match(/^\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\]\s*\[([^\]]+)\]\s*(.*)$/)
  if (!match) return { time: '', level: 'INFO', text: raw }
  const body = match[4]
  const level = /(错误|失败|异常|ERROR|ERR)/i.test(body) ? 'ERROR' : /(警告|降级|WARN)/i.test(body) ? 'WARN' : 'INFO'
  return { time: `${match[1].slice(5)} ${match[2].slice(0, 5)}`, level, text: body }
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<{ logs: string[] }>('/api/logs?limit=200')
    logs.value = result.logs.map(parseLog)
  } catch { error.value = '无法读取运行日志，请确认后端可用' } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="mlogs">
    <header class="head"><div><h1>运行日志</h1><p>一行一条 · 按级别筛选</p></div><button type="button" class="refresh" :disabled="loading" @click="load">↻</button></header>
    <div class="filters"><button v-for="item in ['ALL','INFO','WARN','ERROR']" :key="item" type="button" :class="{ on: level === item }" @click="level = item">{{ item }}</button></div>
    <input v-model="query" class="search" placeholder="搜索日志…">
    <div v-if="error" class="empty">{{ error }}</div>
    <div v-else-if="loading" class="empty">加载中…</div>
    <div v-else-if="!visible.length" class="empty">没有匹配的日志</div>
    <div v-else class="list">
      <div v-for="(row, index) in visible" :key="index" class="row"><span class="lv" :class="row.level">{{ row.level }}</span><span class="time">{{ row.time }}</span><span class="text">{{ row.text }}</span></div>
    </div>
  </section>
</template>

<style scoped>
.mlogs{flex:1;min-height:0;overflow:auto;padding:18px 14px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}.head{display:flex;align-items:flex-end;gap:8px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;width:31px;height:31px;border:1px solid #dbe8ff;border-radius:9px;background:#fff;color:#2563eb;font:14px inherit;cursor:pointer}
.filters{display:flex;gap:6px;margin-bottom:8px}.filters button{flex:1;height:31px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;color:#607896;font:9px inherit;cursor:pointer}.filters button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
.search{width:100%;height:31px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;padding:0 9px;font:9.5px inherit;outline:0;box-sizing:border-box;margin-bottom:9px}
.list{display:grid;gap:5px}.row{display:grid;grid-template-columns:42px 58px minmax(0,1fr);align-items:center;gap:6px;background:#fff;border:1px solid #e3ebf7;border-radius:9px;padding:8px 9px}.lv{font:7px ui-monospace,monospace;text-align:center;border-radius:4px;padding:2px 0;color:#168b63;background:#edfbf4}.lv.WARN{color:#b7791f;background:#fff8e6}.lv.ERROR{color:#b23b52;background:#fff5f7}.time{font:7.5px ui-monospace,monospace;color:#9aabc0}.text{font:8.5px ui-monospace,monospace;color:#405872;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.empty{background:#fff;border:1px dashed #cfe0f7;border-radius:10px;padding:24px;text-align:center;color:#8a9bb0;font-size:9px}
@media(min-width:821px){.mlogs{padding:22px 24px}.list{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
