<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface LogRow { time: string; level: 'INFO' | 'WARN' | 'ERROR'; text: string; raw: string }
const rows = ref<LogRow[]>([])
const level = ref('ALL')
const query = ref('')
const loading = ref(false)
const error = ref('')
const levels = ['ALL', 'INFO', 'WARN', 'ERROR']
const visible = computed(() => rows.value.filter(row => (level.value === 'ALL' || row.level === level.value) && (!query.value.trim() || row.raw.toLowerCase().includes(query.value.trim().toLowerCase()))))
const counts = computed(() => ({ INFO: rows.value.filter(r => r.level === 'INFO').length, WARN: rows.value.filter(r => r.level === 'WARN').length, ERROR: rows.value.filter(r => r.level === 'ERROR').length }))
function parse(line: string): LogRow {
  const raw = String(line || '').trimEnd()
  const bracket = raw.match(/^\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\]\s*(.*)$/)
  if (bracket) {
    const body = bracket[3]
    const level: LogRow['level'] = /(错误|失败|异常|ERROR|ERR)/i.test(body) ? 'ERROR' : /(警告|降级|WARN)/i.test(body) ? 'WARN' : 'INFO'
    return { time: `${bracket[1]} ${bracket[2]}`, level, text: body.replace(/^\[[^\]]+\]\s*/, ''), raw }
  }
  const match = raw.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(INFO|WARN|ERROR|ERR)\s+(.*)$/)
  if (!match) return { time: '', level: 'INFO', text: raw, raw }
  return { time: `${match[1]} ${match[2]}`, level: (match[3] === 'ERR' ? 'ERROR' : match[3]) as LogRow['level'], text: match[4], raw }
}
async function load() {
  loading.value = true; error.value = ''
  try { const result = await http.get<{ logs?: string[] | string }>('/api/logs?limit=200'); const raw = result.logs; const lines = Array.isArray(raw) ? raw : String(raw || '').split(/\r?\n/).filter(Boolean); rows.value = lines.map(parse) }
  catch { error.value = '无法读取运行日志' } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="logs-page">
    <header class="head"><div><h1>运行日志</h1><p>一行一条 · 筛选 / 搜索 · 最近 {{ rows.length }} 条</p></div><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '读取中…' : '刷新' }}</button></header>
    <div v-if="error" class="notice">{{ error }}</div>
    <div class="overview"><div><small>INFO</small><b>{{ counts.INFO }}</b></div><div><small>WARN</small><b class="warn">{{ counts.WARN }}</b></div><div><small>ERROR</small><b class="error">{{ counts.ERROR }}</b></div><div><small>显示</small><b>{{ visible.length }}</b></div></div>
    <div class="toolbar"><div class="filters"><button v-for="item in levels" :key="item" type="button" :class="{ on: level === item }" @click="level = item">{{ item }}</button></div><input v-model="query" class="search" placeholder="搜索日志…"></div>
    <div v-if="loading && !rows.length" class="empty">正在读取日志…</div>
    <div v-else-if="!visible.length" class="empty">没有匹配的日志</div>
    <div v-else class="table">
      <div class="table-head"><span>时间</span><span>级别</span><span>内容</span></div>
      <div v-for="(row, index) in visible" :key="index" class="row"><span class="time">{{ row.time || '—' }}</span><span class="lv" :class="row.level">{{ row.level }}</span><code>{{ row.text }}</code></div>
    </div>
  </section>
</template>

<style scoped>
.logs-page{flex:1;min-height:0;overflow:auto;padding:22px 24px 26px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:8px;margin-bottom:11px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:9px}
.overview{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-bottom:9px}.overview div{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 10px}.overview small{display:block;font-size:7px;color:#9aabc0;letter-spacing:.08em}.overview b{display:block;font-size:15px;color:#1e3a5f;margin-top:2px}.overview b.warn{color:#b7791f}.overview b.error{color:#b23b52}
.toolbar{display:flex;align-items:center;gap:7px;margin-bottom:8px}.filters{display:flex;gap:4px}.filters button{height:27px;border:1px solid #e3ebf7;border-radius:7px;background:#fff;color:#607795;font:8.5px inherit;padding:0 9px;cursor:pointer}.filters button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}.search{flex:1;min-width:0;max-width:300px;height:27px;border:1px solid #e3ebf7;border-radius:7px;background:#fff;padding:0 9px;font:9px inherit;outline:0}
.table{background:#fff;border:1px solid #e3ebf7;border-radius:11px;overflow:hidden}.table-head,.row{display:grid;grid-template-columns:142px 64px minmax(0,1fr);gap:8px;align-items:center}.table-head{background:#f8fbff;border-bottom:1px solid #e3ebf7;padding:7px 10px;font-size:7.5px;color:#9aabc0;letter-spacing:.06em}.row{padding:7px 10px;border-bottom:1px solid #f1f5fb}.row:last-child{border-bottom:0}.time{font:7.5px ui-monospace,monospace;color:#9aabc0}.lv{font:7px ui-monospace,monospace;text-align:center;border-radius:4px;padding:2px 0;color:#168b63;background:#edfbf4}.lv.WARN{color:#b7791f;background:#fff8e6}.lv.ERROR{color:#b23b52;background:#fff5f7}.row code{font:8.5px ui-monospace,monospace;color:#405872;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.empty{border:1px dashed #cfe0f7;border-radius:10px;background:#fff;padding:24px;text-align:center;color:#9aabc0;font-size:9px}
@media(max-width:820px){.logs-page{padding:16px 14px 20px}.overview{grid-template-columns:repeat(2,minmax(0,1fr))}.table-head,.row{grid-template-columns:110px 56px minmax(0,1fr)}}
</style>
