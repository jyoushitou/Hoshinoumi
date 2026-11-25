<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface PersonaFiles { prompt?: boolean; life?: boolean; supplement?: boolean; state?: boolean; voice?: boolean }
interface Persona {
  name: string
  display?: string
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
function avatar(name: string) { return (name || '?').slice(0, 1).toUpperCase() }
function displayTitle(persona: Persona) { return persona.display ? `${persona.display} · ${persona.name}` : persona.name }
async function activate(persona: Persona) {
  if (persona.active) return
  try {
    await http.post('/api/persona/activate', { name: persona.name })
    await load(); notice.value = `已激活 ${persona.name}`
  } catch { error.value = '激活失败，仅 owner 可操作' }
}
async function exportPersona(persona: Persona) {
  try {
    const token = localStorage.getItem('hsh_web_token') || ''
    const response = await fetch(`/api/persona/export?name=${encodeURIComponent(persona.name)}&format=package`, { headers: token ? { authorization: `Bearer ${token}` } : {} })
    if (!response.ok) throw new Error(await response.text())
    const blob = await response.blob()
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${persona.name}.hoshinoumi.persona`; link.click(); URL.revokeObjectURL(link.href)
    notice.value = `已导出 ${persona.name}.hoshinoumi.persona`
  } catch { error.value = '导出失败' }
}
async function importFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    if (/\.hoshinoumi\.persona$/i.test(file.name)) {
      const dataBase64 = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || '').split(',')[1] || ''); reader.onerror = () => reject(new Error('read_failed')); reader.readAsDataURL(file) })
      const packageName = file.name.replace(/\.hoshinoumi\.persona$/i, '')
      await http.post('/api/persona/import', { package_base64: dataBase64, name: packageName, overwrite: true })
      await load(); notice.value = `已导入 ${packageName}.hoshinoumi.persona`
    } else if (/\.json$/i.test(file.name)) {
      const data = JSON.parse(await file.text())
      if (!data?.name || !data?.prompt) { error.value = '人设卡需要 name 和 prompt'; return }
      await http.post('/api/persona/import', { data, overwrite: true })
      await load(); notice.value = `已导入 ${data.name}`
    } else {
      error.value = '只支持 .hoshinoumi.persona 或 .json'
    }
  } catch (e) { error.value = e instanceof Error ? e.message : '导入失败' } finally { if (fileInput.value) fileInput.value.value = '' }
}
onMounted(load)
</script>

<template>
  <section class="persona-page">
    <header class="head"><div><h1>人设</h1><p>v35.5 Web 演示 · MOCK 数据 · 导入 / 导出 / 激活</p></div></header>
    <div class="toolbar">
      <label class="btn">导入人设卡 JSON<input ref="fileInput" type="file" accept=".hoshinoumi.persona,.json,application/json" @change="importFile"></label>
      <span class="hint">只读预览 · 仅 owner 可激活/导入</span>
    </div>
    <div class="backend">数据源 <b>/api/persona</b> · schema 35 · 当前激活 {{ activeName }} · {{ personas.length }} 个</div>
    <div v-if="error" class="notice error">{{ error }}</div>
    <div v-if="notice" class="notice ok">{{ notice }}</div>
    <div v-if="loading && !personas.length" class="empty">加载中…</div>
    <div v-else-if="!personas.length && !error" class="empty">还没有人设卡</div>
    <div class="grid">
      <article v-for="persona in personas" :key="persona.name" class="card" :class="{ active: persona.active }">
        <div class="card-head">
          <span class="avatar">{{ avatar(persona.display || persona.name) }}</span>
          <div class="title"><b>{{ displayTitle(persona) }}</b></div>
          <span v-if="persona.active" class="badge">当前</span>
        </div>
        <p class="excerpt">{{ persona.prompt_excerpt || '暂无摘要' }}</p>
        <div class="tags"><span v-for="file in fileList(persona.files)" :key="file">{{ file }}</span><span v-if="!fileList(persona.files).length">无文件</span></div>
        <div class="actions">
          <button type="button" @click="preview = persona">预览</button>
          <button type="button" :disabled="persona.active" @click="activate(persona)">{{ persona.active ? '已激活' : '激活' }}</button>
          <button type="button" @click="exportPersona(persona)">导出</button>
        </div>
      </article>
    </div>
    <div v-if="preview" class="mask" @click.self="preview = null">
      <div class="modal">
        <header><b>{{ displayTitle(preview) }}</b><button type="button" @click="preview = null">×</button></header>
        <pre>{{ preview.prompt || preview.prompt_excerpt || '暂无 prompt' }}</pre>
      </div>
    </div>
  </section>
</template>

<style scoped>
.persona-page{flex:1;min-height:0;overflow:auto;padding:24px 30px 30px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head h1{margin:0;font-size:27px;letter-spacing:-.03em;line-height:1.15}.head p{margin:6px 0 0;font-size:11.5px;color:#8a9bb0}.toolbar{display:flex;align-items:center;gap:10px;margin:22px 0 10px}.btn{height:31px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:10.5px inherit;padding:0 11px;display:inline-flex;align-items:center;cursor:pointer}.btn input{display:none}.hint{margin-left:auto;font-size:10px;color:#8a9bb0}.backend{font-size:10px;color:#8a9bb0;margin-bottom:16px}.backend b{color:#526982;font-weight:500}
.notice{border-radius:8px;padding:8px 10px;font-size:10px;margin-bottom:10px}.notice.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c}.notice.ok{border:1px solid #cdeee0;background:#eefbf5;color:#168b63}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:13px;padding:16px 17px;display:flex;flex-direction:column;min-height:168px;transition:border-color .18s,box-shadow .18s}.card:hover{border-color:#bcd4f7;box-shadow:0 8px 20px rgba(37,99,235,.05)}.card.active{border-color:#93b7fa;background:linear-gradient(180deg,#f8fbff,#fff)}.card-head{display:flex;align-items:center;gap:10px}.avatar{width:36px;height:36px;border-radius:9px;background:#e0e7ff;color:#4338ca;display:grid;place-items:center;font-size:14px;font-weight:700;flex:none}.title b{display:block;font-size:15px;color:#1e3a5f;letter-spacing:-.01em}.badge{margin-left:auto;font-size:8.5px;color:#168b63;border:1px solid #cdeee0;background:#eefbf5;border-radius:5px;padding:2px 6px}.excerpt{font-size:12px;line-height:1.65;color:#6b7c95;margin:12px 0;min-height:38px}.tags{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px}.tags span{font-size:8.5px;color:#6b7c95;border:1px solid #e3ebf7;border-radius:5px;padding:2px 6px;background:#fbfdff}.actions{display:flex;gap:6px;margin-top:auto}.actions button{height:29px;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#2563eb;font:9.5px inherit;padding:0 10px;cursor:pointer}.actions button:disabled{color:#9aabc0;border-color:#e3ebf7;background:#f8fbff;cursor:default}
.empty{border:1px dashed #cfe0f7;border-radius:12px;background:#f8fbff;padding:32px;text-align:center;color:#8a9bb0;font-size:10px}.mask{position:fixed;inset:0;z-index:80;background:#0f172a52;display:grid;place-items:center;padding:20px}.modal{width:min(560px,100%);background:#fff;border-radius:14px;padding:15px;box-shadow:0 24px 60px #0f264e3d}.modal header{display:flex;align-items:center;margin-bottom:9px}.modal header b{font-size:14px;color:#1e3a5f}.modal header button{margin-left:auto;border:0;background:none;font-size:18px;color:#8a9bb0;cursor:pointer}.modal pre{margin:0;max-height:52vh;overflow:auto;white-space:pre-wrap;background:#f8fbff;border:1px solid #e3ebf7;border-radius:9px;padding:10px;font:10px/1.7 ui-monospace,monospace;color:#405872}
@media(max-width:820px){.persona-page{padding:18px 14px 22px}.toolbar{flex-wrap:wrap}.hint{margin-left:0;width:100%}.grid{grid-template-columns:1fr}.head h1{font-size:24px}}
</style>
