<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import { useIsOwner } from '@/composables/useIsOwner'

interface ModeState {
  mode?: string
  label?: string
  modes?: Array<{ id: string; label: string; description: string; timeout?: number }>
  expires_in?: number | null
  agent_task?: string
  approval?: { command?: string; approved?: boolean; at?: string } | null
}
const router = useRouter()
const session = useSessionStore()
const isOwner = useIsOwner()
const state = ref<ModeState | null>(null)
const busy = ref(false)
const error = ref('')
const shellCommand = ref('')
const remaining = ref(0)
const toolsCount = ref<number | null>(null)
let timer: ReturnType<typeof setInterval> | null = null
const modes = computed(() => state.value?.modes || [])
const mode = computed(() => state.value?.mode || 'chat')
const codeLabel = computed(() => {
  if (mode.value !== 'code') return ''
  const m = Math.floor(remaining.value / 60), s = remaining.value % 60
  return `${m}:${String(s).padStart(2, '0')}`
})
async function loadAgentTools() {
  try { const r = await http.get<{ tools?: unknown[] }>('/api/tools'); toolsCount.value = Array.isArray(r.tools) ? r.tools.length : 0 } catch { toolsCount.value = null }
}
function targetFor(value: string) { return value === 'chat' ? 'persona:nao' : 'mode:' + value }
async function load() {
  if (!isOwner.value) return
  try {
    const r = await http.get<{ data?: ModeState }>('/api/chat/mode')
    state.value = r.data || null
    remaining.value = Number(r.data?.expires_in || 0)
    error.value = ''
  } catch (e) { error.value = e instanceof Error ? e.message : '模式读取失败' }
}
async function select(value: string) {
  if (busy.value || value === mode.value) return
  busy.value = true; error.value = ''
  try {
    const r = await http.post<{ data?: ModeState }>('/api/chat/mode', { mode: value })
    state.value = r.data || null
    remaining.value = Number(r.data?.expires_in || 0)
    await session.selectConversation(targetFor(value))
    await router.push('/chat')
  } catch (e) { error.value = e instanceof Error ? e.message : '模式切换失败' } finally { busy.value = false }
}
async function approve(approved: boolean) {
  if (!shellCommand.value.trim() && !state.value?.approval?.command) return
  try {
    const r = await http.post<{ data?: ModeState }>('/api/chat/mode/approve', { command: shellCommand.value.trim() || state.value?.approval?.command, approved })
    state.value = r.data || state.value
    if (!approved) shellCommand.value = ''
  } catch (e) { error.value = e instanceof Error ? e.message : '审批失败' }
}
function onModeEvent(event: Event) {
  const value = String((event as CustomEvent).detail || '')
  if (modes.value.some(item => item.id === value)) void select(value)
}
function startClock() {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (mode.value !== 'code') return
    remaining.value = Math.max(0, remaining.value - 1)
    if (remaining.value === 0) { void select('chat') }
  }, 1000)
}
watch(mode, value => { if (value === 'agent') void loadAgentTools() })
onMounted(() => { window.addEventListener('hoshinoumi:chat-mode', onModeEvent); void load().then(() => { if (mode.value === 'agent') void loadAgentTools() }); startClock() })
onBeforeUnmount(() => { if (timer) clearInterval(timer); window.removeEventListener('hoshinoumi:chat-mode', onModeEvent) })
</script>

<template>
  <div v-if="isOwner" class="mode-bar">
    <div class="mode-head"><span>模式</span><b>{{ state?.label || 'Chat' }}</b><em v-if="mode === 'code'">{{ codeLabel }}</em><span v-if="error" class="err">{{ error }}</span></div>
    <div class="mode-tabs"><button v-for="item in modes" :key="item.id" type="button" :class="{ on: item.id === mode }" :disabled="busy" :title="item.description" @click="select(item.id)">{{ item.label }}</button></div>
    <div v-if="mode === 'agent'" class="mode-note">Agent · 工具 {{ toolsCount ?? '—' }} 个 · {{ state?.agent_task || '等待任务' }}</div>
    <div v-if="mode === 'shell'" class="shell-box">
      <div class="shell-row"><input v-model="shellCommand" placeholder="输入危险命令，提交审批"><button type="button" class="approve" @click="approve(true)">批准</button><button type="button" @click="approve(false)">拒绝</button></div>
      <div v-if="state?.approval" class="approval" :class="{ ok: state.approval.approved }"><b>{{ state.approval.approved ? '已批准' : '已拒绝' }}</b><code>{{ state.approval.command }}</code><small>{{ state.approval.at }}</small></div>
      <div v-if="state?.approval" class="shell-output"><small>输出面板</small><pre>{{ state.approval.approved ? '审批通过。危险命令不会由 Web 自动执行。' : '已拒绝，命令未执行。' }}</pre></div>
      <div class="shell-hint">Shell 模式只记录审批与输出；未批准的命令不会执行。</div>
    </div>
  </div>
</template>

<style scoped>
.mode-bar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:4px 0 6px}.mode-head{display:flex;align-items:center;gap:5px;font-size:8px;color:#9aabc0}.mode-head b{font-size:9px;color:#405872}.mode-head em{font-style:normal;font-family:ui-monospace,monospace;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:5px;padding:1px 4px}.mode-head .err{color:#b91c1c;margin-left:4px}.mode-tabs{display:flex;gap:3px}.mode-tabs button{height:23px;border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#7d8ca3;font:8px inherit;padding:0 7px;cursor:pointer}.mode-tabs button.on{background:#eef4ff;border-color:#93b7fa;color:#1d4ed8;font-weight:700}.mode-tabs button:disabled{opacity:.5}.mode-note{font-size:8px;color:#6d4fd6;background:#f3efff;border:1px solid #e4dcff;border-radius:6px;padding:2px 6px}.shell-box{flex-basis:100%;display:flex;flex-wrap:wrap;gap:4px;align-items:center;border-top:1px dashed #f1d7a8;padding-top:5px}.shell-row{display:flex;gap:4px;flex:1;min-width:180px}.shell-row input{flex:1;height:24px;border:1px solid #f0d7dd;border-radius:6px;background:#fffafa;font:8px ui-monospace,monospace;padding:0 6px;outline:0}.shell-row button{height:24px;border:1px solid #fecaca;border-radius:6px;background:#fff5f5;color:#b91c1c;font:8px inherit;padding:0 8px;cursor:pointer}.shell-row button.approve{background:#f0fdf7;border-color:#b7e4cc;color:#168b63}.approval{display:flex;align-items:center;gap:5px;font-size:7.5px;color:#9a6700}.approval.ok{color:#168b63}.approval code{font:7px ui-monospace,monospace;color:#526982;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.approval small{color:#9aabc0}.shell-output{flex-basis:100%;background:#fff;border:1px solid #e3ebf7;border-radius:6px;padding:4px 6px}.shell-output small{font-size:7px;color:#9aabc0}.shell-output pre{margin:2px 0 0;font:7px/1.5 ui-monospace,monospace;color:#405872;white-space:pre-wrap}.shell-hint{font-size:7px;color:#9aabc0;flex-basis:100%}
@media(max-width:820px){.mode-bar{gap:4px}.mode-tabs button{height:25px;padding:0 6px}.mode-head{font-size:8px}.shell-row input{height:26px}}
</style>
