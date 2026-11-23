<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface CommandRow { name: string; help?: string; group?: string; owner?: boolean }
const commands = ref<CommandRow[]>([])
const query = ref('')
const loading = ref(false)
const error = ref('')
const running = ref('')
const output = ref('')
const outputError = ref('')
const updatedAt = ref('')
const commandInput = ref('')
const resultState = ref('选择上方命令运行')
const resultOutput = ref('点击任意命令，结果显示在这里。\n\n提示：最终版通过 POST /api/command 执行。')
const collapsed = ref<Set<string>>(new Set())
let groupsInitialized = false
const desktopLayout = typeof window !== 'undefined' && window.matchMedia('(min-width: 821px)').matches
function isCollapsed(group: string) {
  return !query.value.trim() && collapsed.value.has(group)
}
function toggleGroup(group: string) {
  const next = new Set(collapsed.value)
  if (next.has(group)) next.delete(group)
  else next.add(group)
  collapsed.value = next
}
let timer: ReturnType<typeof setInterval> | null = null

const groups = computed(() => {
  const q = query.value.trim().toLowerCase()
  const map = new Map<string, CommandRow[]>()
  for (const row of commands.value) {
    if (q && !`${row.name} ${row.help || ''} ${row.group || ''}`.toLowerCase().includes(q)) continue
    const key = row.group || '其他'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(row)
  }
  return [...map.entries()]
})
async function load() {
  loading.value = true
  error.value = ''
  try {
    const r = await http.get<{ data?: CommandRow[] }>('/api/commands')
    commands.value = Array.isArray(r.data) ? r.data : []
    if (!groupsInitialized) {
      if (!desktopLayout) collapsed.value = new Set(commands.value.map(row => row.group || '其他'))
      groupsInitialized = true
    }
    updatedAt.value = new Date().toLocaleTimeString()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '命令加载失败'
  } finally {
    loading.value = false
  }
}
function selectCommand(row: CommandRow) {
  commandInput.value = row.name + ' '
  resultState.value = '等待执行'
  resultOutput.value = '已选择 ' + row.name + '，按回车或点击执行。'
}
async function executeInput() {
  const value = commandInput.value.trim()
  if (!value) { resultState.value = '先输入命令'; return }
  const cmd = value.replace(/^!/, '').split(/\s+/)[0]
  resultState.value = '执行中…'
  resultOutput.value = ''
  try {
    const r = await http.post<{ result?: string; message?: string; success?: boolean }>('/api/command', { command: cmd })
    if (r.success === false) { resultState.value = '执行失败'; resultOutput.value = r.message || '执行失败' }
    else { resultState.value = '200 OK'; resultOutput.value = r.result || '(无输出)' }
  } catch (e) {
    resultState.value = '执行失败'
    resultOutput.value = e instanceof Error ? e.message : '执行失败'
  }
}
async function run(row: CommandRow) {
  const cmd = row.name.replace(/^!/, '')
  running.value = row.name
  output.value = ''
  outputError.value = ''
  try {
    const r = await http.post<{ result?: string; message?: string; success?: boolean }>('/api/command', { command: cmd })
    if (r.success === false) outputError.value = r.message || '执行失败'
    else output.value = r.result || '(无输出)'
  } catch (e) {
    outputError.value = e instanceof Error ? e.message : '执行失败'
  } finally {
    running.value = ''
  }
}
onMounted(() => {
  void load()
  timer = setInterval(() => void load(), 15000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <section class="commands">
    <header class="head">
      <div><h1>命令</h1><p>按分组浏览 / 搜索 / 直接执行</p></div>
      <button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </header>
    <template v-if="desktopLayout">
      <div class="runbar"><span class="prompt">&gt;</span><input v-model="commandInput" placeholder="输入命令，例如 !persona activate nao" @keydown.enter.prevent="executeInput"><button type="button" :disabled="!commandInput.trim()" @click="executeInput">执行</button></div>
      <div class="hint">无参命令直接执行；带参命令先填参数；二级命令点上方命令后按提示输入。</div>
      <div class="groups desktop">
        <section v-for="[group, rows] in groups" :key="group" class="group">
          <div class="group-title">{{ group }}<span>{{ rows.length }}</span></div>
          <div class="chips">
            <button v-for="row in rows" :key="row.name" type="button" class="chip" :class="{ owner: row.owner }" @click="selectCommand(row)">{{ row.name }}<em v-if="row.owner">owner</em></button>
          </div>
        </section>
        <div v-if="!groups.length && !loading" class="empty">没有匹配的命令</div>
      </div>
      <div class="result"><div class="result-head"><b>执行结果</b><span>{{ resultState }}</span></div><pre>{{ resultOutput }}</pre></div>
    </template>
    <template v-else>
      <div class="bar">
        <input v-model="query" placeholder="搜索命令 / 说明 / 分组">
        <span>{{ commands.length }} 个 · {{ updatedAt || '—' }}</span>
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="groups">
        <section v-for="[group, rows] in groups" :key="group" class="group">
          <div class="group-title" role="button" tabindex="0" @click="toggleGroup(group)" @keydown.enter="toggleGroup(group)">{{ group }}<span>{{ rows.length }} {{ isCollapsed(group) ? '▸' : '▾' }}</span></div>
          <button v-for="row in rows" v-show="!isCollapsed(group)" :key="row.name" type="button" class="cmd" :disabled="running === row.name" @click="run(row)">
            <b>{{ row.name }}</b><small>{{ row.help || '—' }}</small><em v-if="row.owner">OWNER</em>
          </button>
        </section>
        <div v-if="!groups.length && !loading" class="empty">没有匹配的命令</div>
      </div>
      <div v-if="output || outputError" class="output" :class="{ bad: outputError }">
        <b>{{ outputError ? '执行失败' : '输出' }}</b>
        <pre>{{ outputError || output }}</pre>
        <button type="button" @click="output = ''; outputError = ''">关闭</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.commands{position:relative;flex:1;min-height:0;overflow:auto;padding:20px 22px 26px;background:#f7faff;color:#17263b}
.head{display:flex;align-items:center;gap:12px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:8px;font:10px inherit;padding:0 10px;cursor:pointer}
.bar{display:flex;align-items:center;gap:8px;margin-bottom:12px}.bar input{flex:1;height:32px;border:1px solid #dbe8ff;border-radius:9px;background:#fff;padding:0 10px;font:10.5px inherit;outline:0}.bar span{font-size:9px;color:#9aabc0;white-space:nowrap}
.groups{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}.group{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:8px;animation:group-in .24s cubic-bezier(.22,1,.36,1) both}.group:nth-child(2){animation-delay:.04s}.group:nth-child(3){animation-delay:.08s}@keyframes group-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}.group-title{cursor:pointer;user-select:none;display:flex;justify-content:space-between;font-size:9px;font-weight:700;color:#52708f;padding:2px 4px 7px}.group-title span{font-weight:400;color:#9aabc0}
.cmd{display:grid;grid-template-columns:1fr auto;gap:2px 6px;width:100%;text-align:left;border:1px solid transparent;border-radius:8px;background:#f8fbff;padding:6px 8px;margin-bottom:4px;cursor:pointer;transition:background .18s,border-color .18s,transform .18s}.cmd:hover{border-color:#dbe8ff;background:#eef4ff;transform:translateY(-1px)}.cmd:disabled{opacity:.55}.cmd b{font-size:10px;color:#1e3a5f}.cmd small{grid-column:1;font-size:8px;color:#8a9bb0}.cmd em{grid-row:1/3;grid-column:2;align-self:center;font-style:normal;font-size:7px;color:#9a6b1f;background:#fff8e6;border:1px solid #f2d491;border-radius:5px;padding:1px 4px}
.error{margin:8px 0;padding:7px 9px;border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;font-size:9px}.empty{padding:24px;text-align:center;color:#9aabc0;font-size:10px}
.output{position:sticky;bottom:0;margin-top:12px;background:#0f172a;color:#dbeafe;border-radius:12px;padding:11px 12px;box-shadow:0 12px 30px rgba(15,23,42,.22)}.output.bad{background:#3b0d16;color:#fecdd3}.output b{font-size:9px;letter-spacing:.08em;opacity:.75}.output pre{margin:6px 0 0;white-space:pre-wrap;font:10px/1.6 ui-monospace,monospace}.output button{position:absolute;right:9px;top:8px;border:0;background:rgba(255,255,255,.12);color:inherit;border-radius:5px;font:8px inherit;padding:3px 6px;cursor:pointer}
.runbar{display:flex;align-items:center;gap:8px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;padding:7px 9px;margin-bottom:6px}.runbar .prompt{color:#8a9bb0;font:11px ui-monospace,monospace}.runbar input{flex:1;min-width:0;border:0;outline:0;background:none;color:#243b55;font:10.5px inherit}.runbar button{height:27px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;padding:0 12px;cursor:pointer}.runbar button:disabled{opacity:.45}.hint{font-size:8.5px;color:#93a3b8;margin-bottom:10px}.groups.desktop{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.chips{display:flex;flex-wrap:wrap;gap:5px}.chip{border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#4b5f78;font:9px ui-monospace,monospace;padding:4px 7px;cursor:pointer}.chip:hover{background:#eef4ff;color:#2563eb;border-color:#bcd4f7}.chip em{font-style:normal;color:#c0264a;font-size:7px;margin-left:3px}.result{margin-top:10px;border-top:1px solid #e3ebf7;padding-top:10px}.result-head{display:flex;align-items:center;margin-bottom:6px;font-size:10px;color:#6b7c95}.result-head b{color:#1e3a5f;font-size:10.5px}.result-head span{margin-left:auto;font-size:9px;color:#93a3b8}.result pre{margin:0;min-height:150px;border:1px solid #e3ebf7;border-radius:9px;background:#f8fbff;padding:9px 10px;color:#4b5f78;font:10px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow:auto}
@media(min-width:821px){.commands{padding:18px 20px}}

@media(max-width:820px){.commands{padding:12px 12px 20px}.head h1{font-size:22px}.groups{grid-template-columns:1fr}.output{position:fixed;left:10px;right:10px;bottom:calc(64px + env(safe-area-inset-bottom));z-index:20}}
@media(prefers-reduced-motion:reduce){.group{animation:none}.cmd{transition:none}}
</style>
