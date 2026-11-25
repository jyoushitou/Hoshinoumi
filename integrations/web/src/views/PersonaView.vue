<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface PersonaFiles { prompt?: boolean; life?: boolean; supplement?: boolean; state?: boolean; voice?: boolean }
interface Persona {
  name: string
  active?: boolean
  files?: PersonaFiles
  prompt_excerpt?: string
  prompt?: string
  state?: { mood?: number; energy?: number; lonely?: number }
  voice?: { voice?: string } | string
}
const personas = ref<Persona[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const preview = ref<Persona | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const activeName = computed(() => personas.value.find(item => item.active)?.name || '—')

async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<{ data?: Persona[] }>('/api/persona')
    personas.value = Array.isArray(result.data) ? result.data : []
  } catch { error.value = '无法读取人设列表，请确认后端可用' } finally { loading.value = false }
}
function fileList(files?: PersonaFiles) { return Object.entries(files || {}).filter(([, enabled]) => enabled).map(([name]) => name) }
function voiceLabel(persona: Persona) { return typeof persona.voice === 'string' ? persona.voice : persona.voice?.voice || '—' }
function avatar(name: string) { return name.slice(0, 1).toUpperCase() }
async function activate(persona: Persona) {
  if (persona.active) return
  try {
    await http.post('/api/persona/activate', { name: persona.name })
    await load(); notice.value = `已激活 ${persona.name}`
  } catch { error.value = '激活失败，仅 owner 可操作' }
}
async function exportPersona(persona: Persona) {
  try {
    const result = await http.get<{ data?: Persona }>('/api/persona/export?name=' + encodeURIComponent(persona.name))
    const blob = new Blob([JSON.stringify(result.data || persona, null, 2)], { type: 'application/json' })
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${persona.name}.persona.json`; link.click(); URL.revokeObjectURL(link.href)
    notice.value = `已导出 ${persona.name}`
  } catch { error.value = '导出失败' }
}
async function importFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!/\.json$/i.test(file.name)) { error.value = '只支持 JSON 人设卡'; return }
  try {
    const data = JSON.parse(await file.text())
    if (!data?.name || !data?.prompt) { error.value = '人设卡需要 name 和 prompt'; return }
    await http.post('/api/persona/import', { data, overwrite: true })
    await load(); notice.value = `已导入 ${data.name}`
  } catch (e) { error.value = e instanceof Error ? e.message : '导入失败' } finally { if (fileInput.value) fileInput.value.value = '' }
}
onMounted(load)
</script>

<template>
  <section class="persona-page">
    <header class="head">
      <div><h1>人设</h1><p>导入 / 导出 / 激活 · 当前 {{ activeName }}</p></div>
      <label class="btn primary">导入 JSON<input ref="fileInput" type="file" accept=".json,application/json" @change="importFile"></label>
      <button class="btn" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </header>
    <div v-if="error" class="notice error">{{ error }}</div>
    <div v-if="notice" class="notice ok">{{ notice }}</div>
    <div v-if="loading && !personas.length" class="empty">加载中…</div>
    <div v-else-if="!personas.length && !error" class="empty">还没有人设卡</div>
    <div class="grid">
      <article v-for="persona in personas" :key="persona.name" class="card" :class="{ active: persona.active }">
        <div class="card-head">
          <span class="avatar">{{ avatar(persona.name) }}</span>
          <div class="title"><b>{{ persona.name }}</b><small>{{ persona.active ? '使用中' : '可切换' }}</small></div>
          <span v-if="persona.active" class="badge">当前</span>
        </div>
        <p class="excerpt">{{ persona.prompt_excerpt || '暂无摘要' }}</p>
        <div class="tags"><span v-for="file in fileList(persona.files)" :key="file">{{ file }}</span><span v-if="!fileList(persona.files).length">无文件</span></div>
        <div class="state">
          <span>mood <b>{{ persona.state?.mood ?? '—' }}</b></span>
          <span>energy <b>{{ persona.state?.energy ?? '—' }}</b></span>
          <span>voice <b>{{ voiceLabel(persona) }}</b></span>
        </div>
        <div class="actions">
          <button type="button" @click="preview = persona">预览</button>
          <button type="button" class="primary" :disabled="persona.active" @click="activate(persona)">{{ persona.active ? '已激活' : '激活' }}</button>
          <button type="button" @click="exportPersona(persona)">导出</button>
        </div>
      </article>
    </div>
    <div v-if="preview" class="mask" @click.self="preview = null">
      <div class="modal">
        <header><b>{{ preview.name }}</b><button type="button" @click="preview = null">×</button></header>
        <pre>{{ preview.prompt || preview.prompt_excerpt || '暂无 prompt' }}</pre>
      </div>
    </div>
  </section>
</template>

<style scoped>
.persona-page{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}.head{display:flex;align-items:flex-end;gap:8px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.head .btn{margin-left:0;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer}.head .btn.primary{margin-left:auto;background:#2563eb;border-color:#2563eb;color:#fff;display:inline-flex;align-items:center}.head .btn input{display:none}.notice{border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}.notice.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c}.notice.ok{border:1px solid #cdeee0;background:#eefbf5;color:#168b63}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px;display:flex;flex-direction:column;transition:border-color .18s,transform .18s,box-shadow .18s}.card:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.06)}.card.active{border-color:#93b7fa;background:linear-gradient(180deg,#f8fbff,#fff)}.card-head{display:flex;align-items:center;gap:8px}.avatar{width:30px;height:30px;border-radius:9px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700;flex:none}.title b{display:block;font-size:11px;color:#1e3a5f}.title small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.badge{margin-left:auto;font-size:7.5px;color:#168b63;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 5px}.excerpt{font-size:9.5px;line-height:1.65;color:#6b7c95;margin:8px 0;min-height:32px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.tags{display:flex;flex-wrap:wrap;gap:4px}.tags span{font-size:7.5px;color:#6b7c95;border:1px solid #e3ebf7;border-radius:4px;padding:1px 5px}.state{display:grid;gap:3px;margin-top:8px}.state span{font-size:7.5px;color:#9aabc0}.state b{color:#526982;font-weight:500}.actions{display:flex;gap:5px;margin-top:auto;padding-top:9px}.actions button{flex:1;height:28px;border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#607795;font:8px inherit;cursor:pointer}.actions button.primary{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:700}.actions button:disabled{opacity:.65;cursor:default}
.empty{border:1px dashed #cfe0f7;border-radius:12px;background:#f8fbff;padding:32px;text-align:center;color:#8a9bb0;font-size:10px}.mask{position:fixed;inset:0;z-index:80;background:#0f172a52;display:grid;place-items:center;padding:20px}.modal{width:min(560px,100%);background:#fff;border-radius:14px;padding:15px;box-shadow:0 24px 60px #0f264e3d}.modal header{display:flex;align-items:center;margin-bottom:9px}.modal header b{font-size:14px;color:#1e3a5f}.modal header button{margin-left:auto;border:0;background:none;font-size:18px;color:#8a9bb0;cursor:pointer}.modal pre{margin:0;max-height:52vh;overflow:auto;white-space:pre-wrap;background:#f8fbff;border:1px solid #e3ebf7;border-radius:9px;padding:10px;font:10px/1.7 ui-monospace,monospace;color:#405872}
@media(max-width:1180px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:820px){.persona-page{padding:16px 14px 20px}.head{flex-wrap:wrap}.head .btn.primary{margin-left:0}.grid{grid-template-columns:1fr}}
</style>
