<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'
const tab = ref<'memory' | 'events' | 'profile' | 'relation'>('memory')
const stats = ref<{ total: number; targets: number; longterm: number } | null>(null)
interface MemoryItem { id: number; content: string; tags: string[]; source: string; longterm: boolean; created_at: string; target_id: string }
const items = ref<MemoryItem[]>([])
const loading = ref(false)
const query = ref('')
const longtermOnly = ref(false)
const filteredItems = computed(() => {
  const q = query.value.trim().toLowerCase()
  return items.value.filter(item => (!q || `${item.content} ${item.tags.join(' ')}`.toLowerCase().includes(q)) && (!longtermOnly.value || item.longterm))
})
async function toggleLongterm(item: MemoryItem) {
  try {
    await http.request(`/api/memory/items/${item.id}`, { method: 'PATCH', body: { longterm: !item.longterm } })
    item.longterm = !item.longterm
    await loadStats()
  } catch { /* keep state */ }
}
async function removeItem(item: MemoryItem) {
  if (!window.confirm('删除这条记忆？')) return
  try { await http.request(`/api/memory/items/${item.id}`, { method: 'DELETE' }); await loadItems(); await loadStats() } catch { /* keep state */ }
}
interface MemoryEvent { id: number; title: string; kind: string; created_at: string }
const events = ref<MemoryEvent[]>([])
const profile = ref<{ summary: string; keywords: string[] } | null>(null)
async function loadProfile() {
  try { profile.value = await http.get<{ summary: string; keywords: string[] }>('/api/memory/profile') } catch { profile.value = null }
}
async function loadEvents() {
  try { const r = await http.get<{ data?: MemoryEvent[] }>('/api/memory/events'); events.value = Array.isArray(r.data) ? r.data : [] } catch { events.value = [] }
}
async function loadItems() {
  loading.value = true
  try {
    const r = await http.get<{ data?: MemoryItem[] }>('/api/memory/items')
    items.value = Array.isArray(r.data) ? r.data : []
  } catch { items.value = [] } finally { loading.value = false }
}
async function loadStats() {
  try { stats.value = await http.get<{ total: number; targets: number; longterm: number }>('/api/memory/stats') } catch { stats.value = null }
}
onMounted(() => { void loadStats(); void loadItems(); void loadEvents(); void loadProfile() })
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
      <div class="stat"><b>{{ stats?.total ?? '—' }}</b><small>记忆条数</small></div>
      <div class="stat"><b>{{ stats?.targets ?? '—' }}</b><small>会话</small></div>
      <div class="stat"><b>{{ stats?.longterm ?? '—' }}</b><small>长期</small></div>
    </div>
    <div v-if="tab === 'memory'" class="memory-pane">
      <div class="filters">
        <input v-model="query" placeholder="搜索记忆 / 标签">
        <button type="button" :class="{ on: longtermOnly }" @click="longtermOnly = !longtermOnly">长期</button>
      </div>
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="!filteredItems.length" class="empty">暂无匹配记忆</div>
      <div v-else class="list">
        <article v-for="item in filteredItems" :key="item.id" class="mem-card">
          <p>{{ item.content }}</p>
          <div class="mem-meta"><span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span><span class="source">{{ item.source }}</span><em v-if="item.longterm">长期</em><small>{{ item.created_at.slice(0, 10) }}</small></div>
          <div class="actions"><button type="button" @click="toggleLongterm(item)">{{ item.longterm ? '取消长期' : '标长期' }}</button><button type="button" class="danger" @click="removeItem(item)">删除</button></div>
        </article>
      </div>
    </div>
    <div v-else-if="tab === 'events'" class="list">
      <div v-if="!events.length" class="empty">暂无事件</div>
      <div v-for="event in events" v-else :key="event.id" class="event-row"><span class="dot" /><div><b>{{ event.title }}</b><small>{{ event.kind }} · {{ event.created_at.slice(0, 10) }}</small></div></div>
    </div>
    <div v-else-if="tab === 'profile'" class="profile">
      <div v-if="!profile" class="empty">暂无画像</div>
      <template v-else><p class="summary">{{ profile.summary }}</p><div class="keywords"><span v-for="word in profile.keywords" :key="word">{{ word }}</span></div></template>
    </div>
    <div v-else class="empty"><b>关系</b><p>关系数据由关系页提供。</p><RouterLink to="/relation" class="link">打开关系页</RouterLink></div>
  </section>
</template>

<style scoped>
.memory{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b}
.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.sync{margin-left:auto;font-size:8px;color:#8a9bb0;border:1px solid #e3ebf7;background:#fff;border-radius:20px;padding:3px 7px}
.tabs{display:flex;gap:5px;margin-bottom:11px}.tabs button{flex:1;height:31px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;color:#7d8ca3;font:10px inherit;cursor:pointer}.tabs button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
.overview{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:11px}.stat{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:10px;text-align:center}.stat b{display:block;font-size:19px;color:#1e3a5f}.stat small{display:block;font-size:8px;color:#9aabc0;margin-top:2px}
.empty{background:#fff;border:1px dashed #cfe0f7;border-radius:12px;padding:26px;text-align:center;color:#8a9bb0}.empty b{color:#314a65;font-size:11px}.empty p{font-size:9px;margin:5px 0 0}
.list{display:grid;gap:7px}.mem-card{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:10px}.mem-card p{margin:0;font-size:10.5px;line-height:1.65;color:#314a65}.mem-meta{display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-top:7px}.tag{font-size:7px;color:#52708f;background:#f4f8ff;border:1px solid #e3ebf7;border-radius:5px;padding:1px 5px}.source{font-size:7px;color:#9aabc0}.mem-meta em{font-style:normal;font-size:7px;color:#1f9d6b;background:#eefbf5;border-radius:5px;padding:1px 5px}.mem-meta small{margin-left:auto;font-size:7px;color:#9aabc0}
.event-row{display:flex;gap:9px;align-items:flex-start;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:9px 10px}.event-row .dot{width:7px;height:7px;border-radius:50%;background:#2563eb;margin-top:3px;flex:none}.event-row b{display:block;font-size:10px;color:#314a65}.event-row small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}
.profile{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:11px}.summary{margin:0;font-size:10.5px;line-height:1.7;color:#526982}.keywords{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}.keywords span{font-size:8px;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:20px;padding:2px 7px}.link{display:inline-block;margin-top:8px;font-size:9px;color:#2563eb}
.memory-pane{display:grid;gap:7px}.filters{display:flex;gap:6px}.filters input{flex:1;min-width:0;height:30px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;padding:0 9px;font:9px inherit;outline:0}.filters button{height:30px;border:1px solid #e3ebf7;border-radius:8px;background:#fff;color:#6b7c95;font:8.5px inherit;padding:0 9px;cursor:pointer}.filters button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb}.actions{display:flex;gap:5px;justify-content:flex-end;margin-top:7px}.actions button{border:1px solid #e3ebf7;background:#f8fbff;color:#607795;border-radius:5px;font:7.5px inherit;padding:2px 6px;cursor:pointer}.actions button.danger{color:#b91c1c;border-color:#fecaca;background:#fff5f5}
@media(min-width:821px){.memory{padding:22px 24px}.overview{grid-template-columns:repeat(3,minmax(0,1fr));max-width:620px}.list{grid-template-columns:repeat(2,minmax(0,1fr))}.empty,.profile{max-width:620px}}
.head,.tabs,.overview,.empty{animation:mem-in .28s cubic-bezier(.22,1,.36,1) both}.tabs{animation-delay:.03s}.overview{animation-delay:.06s}.empty{animation-delay:.09s}@keyframes mem-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.head,.tabs,.overview,.empty{animation:none}}
</style>
