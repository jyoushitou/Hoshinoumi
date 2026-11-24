<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface DiaryEntry { id: number; date: string; title?: string; content?: string; mood?: string; source?: string }
const entries = ref<DiaryEntry[]>([])
const selectedMonth = ref('')
const loading = ref(false)
const error = ref('')
const selected = ref<DiaryEntry | null>(null)
const emit = defineEmits<{ (e: 'detail-change', value: boolean): void }>()
function openDetail(item: DiaryEntry) { selected.value = item; emit('detail-change', true) }
function closeDetail() { selected.value = null; emit('detail-change', false) }
onBeforeUnmount(() => emit('detail-change', false))

const months = computed(() => [...new Set(entries.value.map(item => String(item.date || '').slice(0, 7)))].filter(Boolean).sort().reverse())
const visibleEntries = computed(() => entries.value.filter(item => String(item.date || '').startsWith(selectedMonth.value)).sort((a, b) => String(b.date).localeCompare(String(a.date))))
const preview = (text?: string) => {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  return value.length > 50 ? value.slice(0, 50) + '…' : value
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const r = await http.get<{ data?: DiaryEntry[] }>('/api/diary?all=1')
    entries.value = Array.isArray(r.data) ? r.data : []
    if (!months.value.includes(selectedMonth.value)) selectedMonth.value = months.value[0] || ''
  } catch (e) {
    entries.value = []
    error.value = '无后端连接'
  } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="diary">
    <template v-if="selected">
      <header class="head detail-head"><button type="button" class="back" @click="closeDetail">‹</button><div><h1>日记详情</h1><p>{{ selected.date }}</p></div></header>
      <article class="detail-card"><div class="detail-title">{{ selected.title || '无标题' }}</div><div class="detail-meta">{{ selected.mood || '平静' }} · {{ selected.source || '!diary' }}</div><p>{{ selected.content || '' }}</p></article>
    </template>
    <template v-else>
    <header class="head"><div><h1>日记</h1><p>按月查看 · 前 50 字概览</p></div><button type="button" class="refresh" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></header>
    <div class="stats"><div><b>{{ entries.length }}</b><small>全部日记</small></div><div><b>{{ months.length }}</b><small>月份</small></div><div><b>{{ entries[0]?.date || '—' }}</b><small>最近</small></div></div>
    <div v-if="error" class="notice">{{ error }}<button type="button" @click="load">重试</button></div>
    <div v-else-if="!months.length && !loading" class="notice">暂无日记</div>
    <template v-else>
      <div class="months"><button v-for="month in months" :key="month" type="button" :class="{ on: month === selectedMonth }" @click="selectedMonth = month">{{ month.replace('-', ' 年 ') }} 月</button></div>
      <div class="grid">
        <article v-for="item in visibleEntries" :key="item.id" class="card">
          <div class="card-head"><b>{{ item.title || '无标题' }}</b><span>{{ item.date }}</span></div>
          <p>{{ preview(item.content) }}</p>
          <div class="meta">{{ item.mood || '平静' }} · {{ item.source || '!diary' }}<button type="button" @click="openDetail(item)">查看</button></div>
        </article>
      </div>
    </template>
    </template>
  </section>
</template>

<style scoped>
.diary{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}
.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:10px inherit;padding:0 10px;cursor:pointer}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:10px}.stats div{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:10px;text-align:center}.stats b{display:block;font-size:17px;color:#1e3a5f}.stats small{display:block;font-size:8px;color:#9aabc0;margin-top:2px}
.months{display:flex;gap:7px;overflow:auto;margin-bottom:10px}.months button{flex:none;height:29px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;color:#526982;font:9px inherit;padding:0 10px;cursor:pointer}.months button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
.grid{display:grid;gap:8px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px 13px}.card-head{display:flex;align-items:center;gap:7px}.card-head b{font-size:12px;color:#1e3a5f}.card-head span{margin-left:auto;font-size:8px;color:#9aabc0}.card p{margin:8px 0 0;font-size:10.5px;line-height:1.75;color:#526982}.meta{display:flex;align-items:center;gap:6px;margin-top:9px;font-size:8px;color:#8a9bb0}.meta button{margin-left:auto;border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb;border-radius:6px;font:8px inherit;padding:3px 8px;cursor:pointer}
.detail-head .back{width:29px;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font-size:18px;line-height:1;cursor:pointer}.detail-card{background:#fff;border:1px solid #e3ebf7;border-radius:13px;padding:18px}.detail-title{font-size:18px;font-weight:700;color:#1e3a5f}.detail-meta{font-size:8px;color:#8a9bb0;margin-top:5px}.detail-card p{margin:16px 0 0;white-space:pre-wrap;font-size:11px;line-height:1.9;color:#405872}.notice button{margin-left:8px;border:1px solid #dbe8ff;border-radius:6px;background:#f4f9ff;color:#2563eb;font:8px inherit;padding:2px 7px;cursor:pointer}.notice{border:1px dashed #cfe0f7;border-radius:12px;background:#fff;padding:24px;text-align:center;color:#8a9bb0;font-size:10px}
@media(min-width:821px){.diary{padding:22px 24px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{max-width:620px}.card{min-height:150px}}
</style>
