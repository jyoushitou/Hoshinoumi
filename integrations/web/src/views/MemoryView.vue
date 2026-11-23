<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '@/api/client'
const tab = ref<'memory' | 'events' | 'profile' | 'relation'>('memory')
const stats = ref<{ total: number; targets: number; longterm: number } | null>(null)
interface MemoryItem { id: number; content: string; tags: string[]; source: string; longterm: boolean; created_at: string; target_id: string }
const items = ref<MemoryItem[]>([])
const loading = ref(false)
interface MemoryEvent { id: number; title: string; kind: string; created_at: string }
const events = ref<MemoryEvent[]>([])
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
onMounted(() => { void loadStats(); void loadItems(); void loadEvents() })
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
    <div v-if="tab === 'memory'" class="list">
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="!items.length" class="empty">暂无记忆</div>
      <article v-for="item in items" v-else :key="item.id" class="mem-card">
        <p>{{ item.content }}</p>
        <div class="mem-meta"><span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span><span class="source">{{ item.source }}</span><em v-if="item.longterm">长期</em><small>{{ item.created_at.slice(0, 10) }}</small></div>
      </article>
    </div>
    <div v-else-if="tab === 'events'" class="list">
      <div v-if="!events.length" class="empty">暂无事件</div>
      <div v-for="event in events" v-else :key="event.id" class="event-row"><span class="dot" /><div><b>{{ event.title }}</b><small>{{ event.kind }} · {{ event.created_at.slice(0, 10) }}</small></div></div>
    </div>
    <div v-else class="empty"><b>{{ tabs.find(t => t.key === tab)?.label }}</b><p>该分区在后续补丁接入。</p></div>
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
@media(min-width:821px){.memory{padding:22px 24px}.overview{max-width:520px}.empty{max-width:520px}}
.head,.tabs,.overview,.empty{animation:mem-in .28s cubic-bezier(.22,1,.36,1) both}.tabs{animation-delay:.03s}.overview{animation-delay:.06s}.empty{animation-delay:.09s}@keyframes mem-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.head,.tabs,.overview,.empty{animation:none}}
</style>
