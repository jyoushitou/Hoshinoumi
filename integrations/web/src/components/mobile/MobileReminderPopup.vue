<template>
  <div v-if="current" class="reminder-overlay">
    <div class="reminder-card">
      <div class="reminder-title">提醒</div>
      <div class="reminder-source">来自定时任务</div>
      <div class="reminder-content">{{ current.content }}</div>
      <div v-if="error" class="reminder-error">{{ error }}</div>
      <div class="reminder-actions">
        <button type="button" :disabled="busy" @click="ack('later')">稍后</button>
        <button type="button" class="primary" :disabled="busy" @click="ack('done')">知道了</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { http } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface Reminder { id: number; content: string; created_at?: string; source_id?: number; kind?: string }
const auth = useAuthStore()
const items = ref<Reminder[]>([])
const current = ref<Reminder | null>(null)
const busy = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | null = null

async function load() {
  if (!auth.loggedIn) return
  try {
    const r = await http.get<{ reminders?: Reminder[] }>('/api/reminders?limit=20')
    items.value = Array.isArray(r.reminders) ? r.reminders : []
    if (!current.value && items.value.length) current.value = items.value[0]
  } catch { /* 后端未迁移 / 未连接：保持静默，不伪造提醒 */ }
}
async function ack(action: 'later' | 'done') {
  const reminder = current.value
  if (!reminder || busy.value) return
  busy.value = true; error.value = ''
  try {
    const r = await http.post<{ ok?: boolean; error?: string }>(`/api/reminders/${reminder.id}/ack`, { action })
    if (r.ok === false) throw new Error(r.error || '确认失败')
    items.value = items.value.filter(item => item.id !== reminder.id)
    current.value = items.value[0] || null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
onMounted(() => {
  void load()
  timer = setInterval(() => { if (!current.value) void load() }, 20000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
watch(() => auth.loggedIn, logged => { if (logged) void load() })
</script>

<style scoped>
.reminder-overlay{position:fixed;inset:0;z-index:90;background:rgba(9,22,40,.32);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:20px}
.reminder-card{width:100%;max-width:330px;background:#fff;border-radius:20px;padding:16px;box-shadow:0 24px 60px rgba(15,38,78,.24)}
.reminder-title{font-size:15px;font-weight:750;color:#223b56}.reminder-source{font-size:8px;color:#9aabc0;margin:4px 0 10px}
.reminder-content{background:#f7faff;border-radius:12px;padding:11px;font-size:11px;line-height:1.65;color:#314a65;word-break:break-word;white-space:pre-wrap}
.reminder-error{color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:8px;padding:6px 8px;font-size:9px;margin-top:8px}
.reminder-actions{display:flex;gap:7px;margin-top:11px}.reminder-actions button{flex:1;height:38px;border:1px solid #dbe8ff;border-radius:9px;background:#fff;color:#2563eb;font-size:11px}.reminder-actions button.primary{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:700}.reminder-actions button:disabled{opacity:.55}
</style>
