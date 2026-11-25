<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface CronTask { id: number; schedule_type: string; content: string; at_time: string; enabled: boolean; next_ts?: string | null }
const tasks = ref<CronTask[]>([])
const loading = ref(false)
const error = ref('')
const editing = ref<CronTask | null>(null)
const showForm = ref(false)
const form = ref({ content: '', schedule_type: 'daily', at_time: '08:00', enabled: true })
const enabledCount = computed(() => tasks.value.filter(t => t.enabled).length)
const scheduleLabel = (task: CronTask) => task.schedule_type === 'hourly' ? '每小时' : task.schedule_type === 'weekly' ? `每周 ${task.at_time}` : `每天 ${task.at_time}`
async function load() {
  loading.value = true; error.value = ''
  try { const result = await http.get<{ data?: CronTask[] }>('/api/cron'); tasks.value = Array.isArray(result.data) ? result.data : [] }
  catch { error.value = '无法读取定时任务' } finally { loading.value = false }
}
function openAdd() { editing.value = null; form.value = { content: '', schedule_type: 'daily', at_time: '08:00', enabled: true }; showForm.value = true }
function openEdit(task: CronTask) { editing.value = task; form.value = { content: task.content, schedule_type: task.schedule_type, at_time: task.at_time, enabled: task.enabled }; showForm.value = true }
async function save() {
  const content = form.value.content.trim()
  if (!content) { error.value = '请填写任务内容'; return }
  const payload = { content, schedule_type: form.value.schedule_type, at_time: form.value.at_time, enabled: form.value.enabled }
  try {
    if (editing.value) await http.post('/api/cron/' + editing.value.id, payload)
    else await http.post('/api/cron', payload)
    showForm.value = false; editing.value = null; await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '保存失败' }
}
async function toggle(task: CronTask) {
  const next = !task.enabled
  try { await http.post('/api/cron/' + task.id, { enabled: next }); task.enabled = next } catch { error.value = '启停失败' }
}
async function run(task: CronTask) {
  try { await http.post('/api/cron/' + task.id + '/run', {}); error.value = `已触发：${task.content}` } catch { error.value = '运行失败' }
}
async function remove(task: CronTask) {
  try { await http.request('/api/cron/' + task.id, { method: 'DELETE' }); await load() } catch { error.value = '删除失败' }
}
onMounted(load)
</script>

<template>
  <section class="cron-page">
    <header class="head"><div><h1>定时任务</h1><p>新增 / 编辑 / 启停 / 删除 · {{ tasks.length }} 个任务 · {{ enabledCount }} 个启用</p></div><button class="add" type="button" @click="openAdd">＋ 新增任务</button><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '读取中…' : '刷新' }}</button></header>
    <div v-if="error" class="notice" :class="{ ok: error.startsWith('已触发') }">{{ error }}</div>
    <div v-if="showForm" class="form">
      <div class="form-head"><b>{{ editing ? '编辑任务' : '新增任务' }}</b><button type="button" @click="showForm = false">×</button></div>
      <div class="form-grid">
        <label class="full">任务内容<input v-model="form.content" placeholder="例如：每日早报"></label>
        <label>类型<select v-model="form.schedule_type"><option value="daily">每天</option><option value="hourly">每小时</option><option value="weekly">每周</option></select></label>
        <label>时间<input v-model="form.at_time" :disabled="form.schedule_type === 'hourly'" placeholder="08:00"></label>
        <label class="check"><input v-model="form.enabled" type="checkbox"> 启用</label>
        <button type="button" class="save" @click="save">{{ editing ? '保存' : '创建' }}</button>
      </div>
    </div>
    <div v-if="!tasks.length && !loading" class="empty">还没有定时任务</div>
    <div class="grid">
      <article v-for="task in tasks" :key="task.id" class="card" :class="{ off: !task.enabled }">
        <div class="card-head"><span class="dot" :class="{ off: !task.enabled }"></span><b>{{ task.content }}</b><span class="state">{{ task.enabled ? '启用' : '停用' }}</span></div>
        <div class="meta"><span>{{ scheduleLabel(task) }}</span><span>下次 {{ task.next_ts || '待计算' }}</span></div>
        <div class="actions"><button type="button" @click="run(task)">立即运行</button><button type="button" @click="toggle(task)">{{ task.enabled ? '停用' : '启用' }}</button><button type="button" @click="openEdit(task)">编辑</button><button type="button" class="danger" @click="remove(task)">删除</button></div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.cron-page{flex:1;min-height:0;overflow:auto;padding:22px 24px 26px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:8px;margin-bottom:11px;flex-wrap:wrap}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.add,.refresh{margin-left:0;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer}.add{margin-left:auto;background:#2563eb;border-color:#2563eb;color:#fff}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:9px}.notice.ok{border-color:#cdeee0;background:#eefbf5;color:#168b63}
.form{border:1px solid #dbe8ff;border-radius:10px;background:#fff;padding:11px;margin-bottom:10px}.form-head{display:flex;align-items:center;margin-bottom:8px}.form-head b{font-size:10px;color:#314a65}.form-head button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:16px;cursor:pointer}.form-grid{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:7px;align-items:end}.form-grid label{font-size:8px;color:#8a9bb0}.form-grid label.full{grid-column:1/-1}.form-grid input,.form-grid select{display:block;width:100%;height:29px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;padding:0 8px;font:10px inherit;outline:0;box-sizing:border-box;margin-top:3px}.form-grid .check{display:flex;align-items:center;gap:4px;height:29px}.form-grid .check input{width:auto;height:auto;margin:0}.form-grid .save{height:29px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;padding:0 12px;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:11px 12px}.card.off{opacity:.78}.card-head{display:flex;align-items:center;gap:6px}.dot{width:7px;height:7px;border-radius:50%;background:#1f9d6b}.dot.off{background:#cbd5e1}.card-head b{font-size:11px;color:#314a65}.state{margin-left:auto;font-size:7.5px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 5px}.card.off .state{color:#8a9bb0;border-color:#e3ebf7;background:#f8fbff}.meta{display:flex;gap:8px;font-size:8px;color:#8a9bb0;margin:7px 0}.actions{display:flex;gap:4px;flex-wrap:wrap}.actions button{height:25px;border:1px solid #dbe8ff;border-radius:5px;background:#f8fbff;color:#2563eb;font:8px inherit;padding:0 7px;cursor:pointer}.actions button.danger{color:#b23b52;border-color:#f0d7dd;background:#fff7f9}.empty{border:1px dashed #cfe0f7;border-radius:10px;background:#fff;padding:20px;text-align:center;color:#9aabc0;font-size:9px}
@media(max-width:1180px){.cron-page{padding:18px 18px 22px}.grid{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr 1fr}.form-grid .full{grid-column:1/-1}}
</style>
