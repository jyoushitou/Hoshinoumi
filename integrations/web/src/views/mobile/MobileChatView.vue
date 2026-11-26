<template>
  <div class="mc">
    <template v-if="pane === 'list'">
      <div class="head"><div><h1>聊天</h1><p>QQ 会话 · {{ session.conversations.length }} 个</p></div><button class="new-group" type="button" @click="newGroupOpen = true">＋</button><i class="dot" :class="{ off: !session.connected }" /></div>
      <button type="button" class="search" @click="openSearch"><span class="search-svg"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m16.5 16.5 4 4"></path></svg></span>搜索会话 / 记忆 / 命令</button>
      <div v-if="listError" class="notice error">{{ listError }}</div>
      <div v-else-if="!session.conversations.length" class="notice">{{ session.loading ? '正在同步会话…' : '暂无会话。后端有 QQ 消息后会出现在这里。' }}</div>
      <div v-for="row in visibleConversations" :key="row.target_id" class="swipe-wrap" @touchstart.passive="swipeStart($event, row)" @touchmove.passive="swipeMove" @touchend.passive="swipeEnd">
        <div class="swipe-actions"><button type="button" @click="toggleMute(row)">{{ prefs[row.target_id]?.muted ? '取消免打扰' : '免打扰' }}</button><button type="button" class="danger" @click="removeRow(row)">{{ row.type === 'group' ? '退出群聊' : '删除' }}</button></div>
        <button class="conv" type="button" :class="{ muted: prefs[row.target_id]?.muted }" :style="{ transform: swipeTarget === row.target_id ? 'translateX(' + swipeDx + 'px)' : '' }" @click="open(row.target_id)">
          <span class="avatar">{{ (row.name || '?').slice(0, 1) }}</span>
          <span class="copy"><b>{{ row.name || row.target_id }}</b><small>{{ row.last_message || '暂无消息' }}</small></span>
          <span class="meta"><small>{{ timeOf(row.updated_at) }}</small><em v-if="row.unread">{{ row.unread > 99 ? '99+' : row.unread }}</em></span>
        </button>
      </div>
    </template>

    <template v-else>
      <div class="chat-head">
        <button type="button" class="back" aria-label="返回" @click="pane = 'list'">‹</button>
        <div class="who"><b>{{ activeName }}</b><small>{{ activeGroup ? '群聊 · ' + (activeCount || 0) + ' 人' : '私聊' }} · {{ syncLabel }}</small></div>
        <button v-if="session.syncGap" type="button" class="gap" @click="session.syncNow(true)">继续同步</button>
      </div>
      <div ref="messageList" class="messages">
        <div v-if="session.historyError" class="notice error">{{ session.historyError }}</div>
        <div v-else-if="!session.messages.length" class="notice">{{ session.loading ? '正在加载…' : '暂无历史消息' }}</div>
        <div v-for="(m, i) in session.messages" :key="m.id ?? i" class="row" :class="{ me: m.role === 'user' || m.role === 'me' }" :data-message-index="i">
          <span v-if="m.role !== 'user' && m.role !== 'me'" class="mini">{{ activeName.slice(0, 1) }}</span>
          <div class="box">
            <div v-if="m.recalled" class="recalled">消息已撤回</div>
            <template v-else>
              <div v-if="m.image_url" class="media-wrap"><img :src="m.image_url" class="msg-img" :class="{ sticker: m.kind === 'sticker' }" alt="图片"><a :href="m.image_url" :download="`hoshinoumi-image-${i}`" class="download">下载</a></div>
              <div v-if="m.audio_url" class="media-wrap"><audio :src="m.audio_url" controls class="msg-audio" /><a :href="m.audio_url" :download="`hoshinoumi-voice-${i}`" class="download">下载</a></div>
              <div v-if="m.content" class="bubble">{{ m.content }}</div>
            </template>
            <small class="stamp">{{ m.pending ? '发送中…' : String(m.created_at || '').slice(11, 16) }}</small>
          </div>
          <span v-if="m.role === 'user' || m.role === 'me'" class="mini mea">你</span>
        </div>
      </div>
      <div v-if="mediaError" class="media-error">{{ mediaError }}</div>
      <div v-if="imagePreview" class="preview"><img :src="imagePreview" alt="预览"><span>{{ imageName }}</span><button type="button" @click="clearImage">×</button></div>
      <div v-if="stickerOpen" class="stickers"><button v-for="sticker in stickerCatalog" :key="sticker.id" type="button" @click="sendSticker(sticker)"><img :src="sticker.url" :alt="sticker.name" loading="lazy"></button><span v-if="stickerLoading" class="sticker-tip">加载中…</span><span v-else-if="stickerError" class="sticker-tip">{{ stickerError }}</span><span v-else-if="!stickerCatalog.length" class="sticker-tip">暂无表情</span></div>
      <ChatModeBar />
      <div class="composer">
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden @change="onFile">
        <button type="button" class="tool" aria-label="图片" @click="pickImage">＋</button>
        <button type="button" class="tool" :class="{ rec: recording }" aria-label="语音" @click="toggleVoice">{{ recording ? '■' : '🎙' }}</button>
        <button type="button" class="tool" aria-label="表情" @click="toggleStickerPanel">☺</button>
        <textarea ref="textarea" v-model="draft" rows="1" placeholder="和奈绪说点什么…" enterkeyhint="send" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" @keydown="onKeydown" @input="autosize" @focus="scrollBottom" />
        <button type="button" class="send" :disabled="!canSend" @click="send">{{ session.sending ? '…' : '↑' }}</button>
      </div>
      <div v-if="session.sendError" class="media-error">{{ session.sendError }}</div>
    </template>

    <div v-if="searchOpen" class="search-overlay">
      <div class="search-head">
        <input ref="searchInput" v-model="searchQuery" type="search" placeholder="搜索会话 / 记忆 / 命令" @keydown.esc="closeSearch">
        <button type="button" @click="closeSearch">取消</button>
      </div>
      <div class="search-body">
        <div v-if="!searchQuery.trim()" class="search-empty">输入关键词搜索会话和当前聊天记录</div>
        <div v-else-if="!searchResults.length" class="search-empty">没有匹配结果</div>
        <button v-for="hit in searchResults" :key="hit.key" type="button" class="search-hit" @click="openSearchResult(hit)">
          <span class="hit-kind">{{ hit.kind === 'conv' ? '会话' : hit.kind === 'msg' ? '消息' : hit.kind === 'memory' ? '记忆' : '命令' }}</span>
          <span class="hit-copy"><b>{{ hit.title }}</b><small>{{ hit.text }}</small></span>
        </button>
        <div class="search-note">只搜索已加载的会话和消息，不伪造未同步内容。</div>
      </div>
    </div>
  </div>
  <NewGroupModal :open="newGroupOpen" @close="newGroupOpen = false" @created="onGroupCreated" />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const emit = defineEmits<{ (e: 'detail-change', value: boolean): void }>()
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import { http } from '@/api/client'
import NewGroupModal from '@/components/NewGroupModal.vue'
import { cleanupStickerCache, getStickerDataUrl, type StickerMeta } from '@/lib/stickerCache'

const session = useSessionStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const deepTarget = computed(() => String(route.query.target || ''))
const pane = ref<'list' | 'chat'>('list')
watch(pane, value => emit('detail-change', value === 'chat'), { immediate: true })
const draft = ref('')
const messageList = ref<HTMLElement | null>(null)
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const imagePreview = ref('')
const imageName = ref('')
const mediaError = ref('')
const stickerOpen = ref(false)
const newGroupOpen = ref(false)
const stickerCatalog = ref<StickerMeta[]>([])
const stickerLoading = ref(false)
const stickerError = ref('')
const recording = ref(false)
let recorder: MediaRecorder | null = null
let chunks: BlobPart[] = []
let stream: MediaStream | null = null
async function loadStickers() {
  if (stickerCatalog.value.length || stickerLoading.value) return
  stickerLoading.value = true
  stickerError.value = ''
  try {
    const r = await http.get<{ data?: StickerMeta[] }>('/api/stickers')
    stickerCatalog.value = Array.isArray(r.data) ? r.data : []
  } catch (e) {
    stickerError.value = e instanceof Error ? e.message : '表情加载失败'
  } finally {
    stickerLoading.value = false
  }
}
function toggleStickerPanel() {
  stickerOpen.value = !stickerOpen.value
  if (stickerOpen.value) void loadStickers()
}
const searchOpen = ref(false)
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
interface SearchHit { key: string; kind: 'conv' | 'msg' | 'memory' | 'command'; title: string; text: string; target?: string; index?: number }
const commands = ref<Array<{ name?: string; help?: string; group?: string }>>([])
const listError = computed(() => auth.loggedIn ? (session.conversationsError || session.error) : '')
interface ConvPref { muted?: boolean; hidden?: boolean; deleted_at?: string | null }
const prefs = ref<Record<string, ConvPref>>({})
const swipeTarget = ref('')
const swipeDx = ref(0)
let swipeStartX = 0, swipeStartY = 0, swipeAxis: '' | 'x' | 'y' = '', swipeOpen = false
const visibleConversations = computed(() => session.conversations.filter(row => { const p = prefs.value[row.target_id]; return !p?.hidden && !p?.deleted_at }))
async function loadPrefs() { try { const r = await http.get<{ data?: Record<string, ConvPref> }>('/api/conversations/preferences'); prefs.value = r.data || {} } catch { prefs.value = {} } }
function swipeStart(event: TouchEvent, row: any) {
  if (event.touches.length !== 1) return
  if (swipeTarget.value && swipeTarget.value !== row.target_id) { swipeTarget.value = ''; swipeDx.value = 0 }
  swipeStartX = event.touches[0].clientX; swipeStartY = event.touches[0].clientY
  swipeAxis = ''; swipeOpen = swipeTarget.value === row.target_id; swipeTarget.value = row.target_id
}
function swipeMove(event: TouchEvent) {
  if (!swipeTarget.value || event.touches.length !== 1) return
  const dx = event.touches[0].clientX - swipeStartX, dy = event.touches[0].clientY - swipeStartY
  if (!swipeAxis && (Math.abs(dx) > 8 || Math.abs(dy) > 8)) swipeAxis = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y'
  if (swipeAxis !== 'x') return
  swipeDx.value = Math.max(-92, Math.min(0, dx + (swipeOpen ? -92 : 0)))
}
function swipeEnd() { if (swipeAxis === 'x') swipeDx.value = swipeDx.value < -42 ? -92 : 0 }
function resetSwipe() { swipeTarget.value = ''; swipeDx.value = 0 }
async function toggleMute(row: any) {
  const next = !prefs.value[row.target_id]?.muted
  try { await http.patch('/api/conversations/' + encodeURIComponent(row.target_id), { muted: next }); prefs.value[row.target_id] = { ...(prefs.value[row.target_id] || {}), muted: next } } catch { /* ignore */ }
  resetSwipe()
}
async function removeRow(row: any) {
  const dissolve = row.type === 'group' && String(row.target_id).startsWith('h_')
  if (!window.confirm(dissolve ? '你是群主，退出会解散该群。确定？' : row.type === 'group' ? '退出这个群聊？' : '删除联系人？')) return
  try { await http.delete('/api/conversations/' + encodeURIComponent(row.target_id), { dissolve }); prefs.value[row.target_id] = { ...(prefs.value[row.target_id] || {}), hidden: true, deleted_at: 'now' } } catch { /* ignore */ }
  resetSwipe()
}
const active = computed(() => session.conversations.find(row => row.target_id === session.activeTarget) || null)
const activeName = computed(() => {
  if (session.activeTarget === 'mode:code') return '代码模式'
  if (session.activeTarget === 'mode:agent') return 'Agent 模式'
  if (session.activeTarget === 'mode:shell') return 'Shell 模式'
  return active.value?.name || String(session.persona?.name || '会话')
})
const activeGroup = computed(() => active.value?.type === 'group')
const activeCount = computed(() => Number(active.value?.member_count || 0))
const syncLabel = computed(() => session.syncState === 'syncing' ? '同步中' : session.syncState === 'offline' ? '同步中断' : session.syncState === 'online' ? '已同步' : '等待同步')
const canSend = computed(() => Boolean(draft.value.trim() || imagePreview.value) && !session.sending && Boolean(session.activeTarget))
const searchResults = computed<SearchHit[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return []
  const hits: SearchHit[] = []
  for (const conv of session.conversations) {
    const text = `${conv.name || ''} ${conv.last_message || ''}`.toLowerCase()
    if (text.includes(query)) hits.push({ key: 'conv-' + conv.target_id, kind: 'conv', title: conv.name || conv.target_id, text: conv.last_message || '暂无消息', target: conv.target_id })
  }
  session.messages.forEach((message, index) => {
    const content = String(message.content || '')
    if (content.toLowerCase().includes(query)) hits.push({ key: 'msg-' + index, kind: 'msg', title: activeName.value, text: content.slice(0, 80), target: session.activeTarget, index })
  })
  session.memoryTargets.forEach((memory, index) => {
    const raw = typeof memory === 'object' && memory ? JSON.stringify(memory) : String(memory)
    if (raw.toLowerCase().includes(query)) hits.push({ key: 'memory-' + index, kind: 'memory', title: String((memory as Record<string, unknown>)?.target_id || '记忆'), text: raw.slice(0, 80) })
  })
  commands.value.forEach((command, index) => {
    const raw = `${command.name || ''} ${command.help || ''} ${command.group || ''}`.toLowerCase()
    if (raw.includes(query)) hits.push({ key: 'command-' + index, kind: 'command', title: command.name || '命令', text: command.help || command.group || '' })
  })
  return hits.slice(0, 40)
})

let viewportHandler: (() => void) | null = null
onMounted(() => {
  void cleanupStickerCache()
  window.addEventListener('hoshinoumi:back-detail', onNativeBackDetail)
  if (auth.loggedIn && !session.conversations.length) void session.refresh()
  if (auth.loggedIn) void loadPrefs()
  if (deepTarget.value) void open(deepTarget.value)
  viewportHandler = () => { if (pane.value === 'chat') setTimeout(scrollBottom, 80) }
  window.visualViewport?.addEventListener('resize', viewportHandler)
})
function onNativeBackDetail() {
  if (pane.value === 'chat') {
    pane.value = 'list'
    imagePreview.value = ''
    imageName.value = ''
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('hoshinoumi:back-detail', onNativeBackDetail)
  emit('detail-change', false)
  if (recorder && recording.value) recorder.stop()
  stream?.getTracks().forEach(t => t.stop())
  if (viewportHandler) window.visualViewport?.removeEventListener('resize', viewportHandler)
})
watch(() => session.messages.length, scrollBottom)
watch(() => session.activeTarget, scrollBottom)
watch(() => session.conversations.length, async length => {
  if (length && deepTarget.value && session.activeTarget !== deepTarget.value) {
    await open(deepTarget.value)
  }
})

function timeOf(value?: string) { const d = value ? new Date(value) : null; return d && !Number.isNaN(d.getTime()) ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '' }
async function scrollBottom() { await nextTick(); const el = messageList.value; if (el) el.scrollTop = el.scrollHeight }
async function loadCommands() {
  if (commands.value.length) return
  try {
    const r = await http.get<{ data?: Array<{ name?: string; help?: string; group?: string }> }>('/api/commands')
    commands.value = Array.isArray(r.data) ? r.data : []
  } catch { commands.value = [] }
}
async function openSearch() {
  searchOpen.value = true
  searchQuery.value = ''
  await nextTick()
  searchInput.value?.focus()
  void loadCommands()
}
function closeSearch() { searchOpen.value = false; searchQuery.value = '' }
async function openSearchResult(hit: SearchHit) {
  searchOpen.value = false
  if (hit.kind === 'memory') { void router.push('/memory'); return }
  if (hit.kind === 'command') { void router.push('/commands'); return }
  if (hit.kind === 'conv') { await open(hit.target || ''); return }
  if (session.activeTarget !== hit.target) await open(hit.target || '')
  await nextTick()
  const el = document.querySelector(`[data-message-index="${hit.index ?? 0}"]`)
  el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  el?.classList.add('search-flash')
  setTimeout(() => el?.classList.remove('search-flash'), 1200)
}
async function onGroupCreated(id: string) {
  newGroupOpen.value = false
  await session.refresh()
  await open(id)
}
async function open(target: string) {
  if (!target) return
  pane.value = 'chat'
  imagePreview.value = ''; imageName.value = ''; mediaError.value = ''
  await scrollBottom()
  try { await session.selectConversation(target) }
  catch (e) { mediaError.value = e instanceof Error ? e.message : '加载会话失败' }
  finally { await scrollBottom() }
}
function autosize() { const el = textarea.value; if (!el) return; el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 96) + 'px' }
function onKeydown(e: KeyboardEvent) { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); void send() } }
async function send() {
  if (!canSend.value) return
  const content = draft.value, image = imagePreview.value, name = imageName.value
  const ok = await session.sendMessage(content, image ? { image } : {})
  if (!ok) { draft.value = content; imagePreview.value = image; imageName.value = name; return }
  draft.value = ''; imagePreview.value = ''; imageName.value = ''; mediaError.value = ''
  const el = textarea.value; if (el) el.style.height = 'auto'; el?.focus(); await scrollBottom()
}
function pickImage() { fileInput.value?.click() }
function clearImage() { imagePreview.value = ''; imageName.value = ''; mediaError.value = '' }
function onFile(e: Event) {
  const input = e.target as HTMLInputElement, file = input.files?.[0]; mediaError.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) { mediaError.value = '只能选择图片'; return }
  if (file.size > 4 * 1024 * 1024) { mediaError.value = '图片不能超过 4MB'; return }
  const reader = new FileReader(); reader.onload = () => { imagePreview.value = String(reader.result || ''); imageName.value = file.name }; reader.onerror = () => { mediaError.value = '图片读取失败' }; reader.readAsDataURL(file); input.value = ''
}
function toDataUrl(blob: Blob): Promise<string> { return new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result || '')); r.onerror = reject; r.readAsDataURL(blob) }) }
async function toggleVoice() {
  mediaError.value = ''
  if (recording.value && recorder) { recorder.stop(); return }
  if (!navigator.mediaDevices?.getUserMedia) { mediaError.value = '当前浏览器不支持录音'; return }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true }); chunks = []
    const r = new MediaRecorder(stream); recorder = r
    r.ondataavailable = e => { if (e.data.size) chunks.push(e.data) }
    r.onstop = async () => {
      recording.value = false; recorder = null; stream?.getTracks().forEach(t => t.stop()); stream = null
      const blob = new Blob(chunks, { type: r.mimeType || 'audio/webm' })
      if (!blob.size) { mediaError.value = '没有录到声音'; return }
      if (blob.size > 4 * 1024 * 1024) { mediaError.value = '语音不能超过 4MB'; return }
      const ok = await session.sendMessage('', { audio: await toDataUrl(blob) })
      if (!ok) mediaError.value = session.sendError || '语音发送失败'; await scrollBottom()
    }
    r.start(); recording.value = true
  } catch { mediaError.value = '无法使用麦克风，请检查权限' }
}
async function sendSticker(sticker: StickerMeta) {
  stickerError.value = ''
  try {
    const data = await getStickerDataUrl(sticker)
    stickerOpen.value = false
    const ok = await session.sendMessage('', { sticker: data })
    if (!ok) mediaError.value = session.sendError || '表情发送失败'
    await scrollBottom()
  } catch (e) {
    stickerError.value = e instanceof Error ? e.message : '表情发送失败'
  }
}
</script>

<style scoped>
.mc{height:100%;min-height:0;display:flex;flex-direction:column;padding:0 12px calc(8px + env(safe-area-inset-bottom));background:#f7faff;color:#17263b}
.mc:has(textarea:focus),.mc:focus-within{padding-bottom:6px!important}
.head{display:flex;align-items:flex-end;justify-content:space-between;padding:14px 2px 9px}.new-group{width:30px;height:30px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font-size:17px;margin-left:auto;margin-right:7px;line-height:1}h1{margin:0;font-size:24px;letter-spacing:-.03em}p{margin:3px 0 0;color:#8a9bb0;font-size:10px}.dot{width:8px;height:8px;border-radius:50%;background:#1f9d6b;box-shadow:0 0 0 3px rgba(31,157,107,.1)}.dot.off{background:#cbd5e1;box-shadow:none}
.search{height:36px;border:1px solid #e3ebf7;border-radius:11px;background:#fff;color:#9aabc0;display:flex;align-items:center;padding:0 11px;font-size:10px;margin-bottom:10px}
.notice{border:1px dashed #d7e6ff;background:#f4f9ff;color:#7a8fa8;border-radius:11px;padding:12px;font-size:10px;line-height:1.6;margin:6px 0}.notice.error{border-color:#fecaca;background:#fff5f5;color:#b91c1c}
.swipe-wrap{position:relative;overflow:hidden;border-radius:12px;margin-bottom:2px}.swipe-actions{position:absolute;right:0;top:0;bottom:0;display:flex;align-items:stretch}.swipe-actions button{width:78px;border:0;background:#eef4ff;color:#2563eb;font:9px inherit;cursor:pointer}.swipe-actions button.danger{background:#fff1f2;color:#b91c1c}.conv{position:relative;z-index:1;background:#f7faff;transition:transform .18s ease;display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:1px solid transparent;background:transparent;padding:10px 8px;border-radius:12px;cursor:pointer}.conv:active{background:#fff;border-color:#e7efff}.conv.muted{opacity:.7}.conv .meta em{background:#2563eb}.avatar{width:38px;height:38px;border-radius:12px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-weight:800;font-size:13px;flex:none}.copy{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}.copy b{font-size:12px;color:#253b56;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.copy small{font-size:9.5px;color:#8b9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none}.meta small{font-size:8px;color:#a2b2c6}.meta em{min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:#2563eb;color:#fff;font-size:8px;font-style:normal;display:grid;place-items:center}
.chat-head{display:flex;align-items:center;gap:9px;padding:10px 0 9px;border-bottom:1px solid #e7effa;flex:none}.back{width:30px;height:32px;border:0;background:none;color:#52708f;font-size:20px;flex:none}.who{flex:1;min-width:0}.who b{display:block;font-size:13px;color:#213954;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.who small{display:block;color:#1f9d6b;font-size:8px;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.gap{flex:none;font-size:8px;color:#8a5a00;border:1px solid #f2d491;background:#fff8e6;border-radius:7px;padding:4px 6px}
.messages{flex:1;min-height:180px;overflow-y:auto;padding:12px 0;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;scrollbar-width:none}.messages::-webkit-scrollbar{display:none}.row{display:flex;align-items:flex-end;gap:5px;margin-bottom:10px}.row.me{justify-content:flex-end}.box{max-width:82%;display:flex;flex-direction:column;align-items:flex-start}.row.me .box{align-items:flex-end}.mini{width:22px;height:22px;border-radius:7px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:8px;font-weight:800;flex:none}.mini.mea{background:#2563eb;color:#fff}
.bubble{padding:8px 11px;border-radius:12px 12px 12px 4px;background:#fff;border:1px solid #e3ebf7;color:#344b64;font-size:12px;line-height:1.65;white-space:pre-wrap;word-break:break-word}.row.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:12px 12px 4px 12px}.recalled{font-size:9px;color:#93a3b8;border:1px dashed #dbe8ff;border-radius:8px;padding:5px 9px;background:#f8fbff}.stamp{font-size:7px;color:#a2b2c6;margin-top:3px}.row.me .stamp{text-align:right}.msg-img{max-width:180px;max-height:180px;border-radius:10px;display:block;margin-bottom:2px;object-fit:cover}.msg-img.sticker{width:96px;height:96px;object-fit:contain;background:transparent;border:0}.msg-audio{width:190px;max-width:100%;height:34px;display:block;margin-bottom:2px}
.media-error{flex:none;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:8px;font-size:9px;padding:6px 8px;margin:4px 0}.preview{display:flex;align-items:center;gap:7px;flex:none;border:1px solid #dbe8ff;background:#fff;border-radius:9px;padding:5px;margin-bottom:6px}.preview img{width:40px;height:40px;border-radius:6px;object-fit:cover}.preview span{flex:1;min-width:0;font-size:8px;color:#6b7c95;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.preview button{border:0;background:none;color:#8a9bb0;font-size:16px}
.stickers{display:flex;flex-wrap:wrap;gap:4px;flex:none;padding:6px;margin-bottom:6px;border:1px solid #dbe8ff;border-radius:10px;background:#fff}.stickers button{width:36px;height:36px;border:0;border-radius:7px;background:#f8fbff;padding:2px;overflow:hidden}.stickers button img{width:100%;height:100%;object-fit:contain;display:block}.sticker-tip{font-size:8px;color:#8a9bb0;padding:5px}
.composer{display:flex;gap:5px;align-items:flex-end;border-top:1px solid #e5edf9;padding:7px 0 0;background:#f7faff;flex:none}.tool{width:32px;height:34px;flex:none;border:1px solid #e5edf9;border-radius:9px;background:#fff;color:#607795;font-size:15px}.tool.rec{color:#c0264a;background:#ffecef;border-color:#fecaca}.composer textarea{flex:1;min-width:0;resize:none;max-height:96px;border:1px solid #e1ebf9;border-radius:11px;background:#fff;padding:8px 10px;font:16px/1.4 inherit;color:#344b64;outline:0}.composer textarea:focus{border-color:#93c5fd;box-shadow:0 0 0 3px rgba(37,99,235,.07)}.send{width:36px;height:36px;flex:none;border:0;border-radius:11px;background:#2563eb;color:#fff;font-size:17px}.send:disabled{background:#cbd5e1}
@media(max-height:560px){.messages{min-height:100px}.head{padding-top:8px}}

.search-svg{display:inline-flex;align-items:center;margin-right:2px}.search-svg svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round}.search{width:100%;height:36px;border:1px solid #e3ebf7;border-radius:11px;background:#fff;color:#9aabc0;display:flex;align-items:center;padding:0 11px;font-size:10px;margin-bottom:10px;text-align:left}
.media-wrap{display:flex;flex-direction:column;align-items:flex-start;gap:2px}.download{font-size:8px;color:#2563eb;text-decoration:none;border:1px solid #dbe8ff;background:#f4f9ff;border-radius:6px;padding:2px 6px}
.search-overlay{position:fixed;inset:0;z-index:80;background:#f7faff;display:flex;flex-direction:column;padding:calc(10px + env(safe-area-inset-top)) 12px calc(10px + env(safe-area-inset-bottom))}
.search-head{display:flex;gap:7px;align-items:center;flex:none}.search-head input{flex:1;min-width:0;height:40px;border:1px solid #dbe8ff;border-radius:11px;background:#fff;padding:0 12px;font-size:16px;outline:0}.search-head input:focus{border-color:#93c5fd;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.search-head button{flex:none;height:40px;border:1px solid #dbe8ff;border-radius:10px;background:#fff;color:#2563eb;font-size:11px;padding:0 11px}
.search-body{flex:1;min-height:0;overflow-y:auto;margin-top:10px;overscroll-behavior:contain}.search-empty{padding:26px 10px;text-align:center;color:#8fa3bb;font-size:10px;line-height:1.7}.search-hit{display:flex;width:100%;text-align:left;gap:8px;border:1px solid #eef3fb;border-radius:11px;background:#fff;padding:10px;margin-bottom:7px;align-items:flex-start}.hit-kind{flex:none;font-size:7px;color:#2563eb;background:#eef4ff;border-radius:5px;padding:3px 5px}.hit-copy{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}.hit-copy b{font-size:10px;color:#314a65;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hit-copy small{font-size:8px;color:#8fa3bb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.search-note{font-size:8px;color:#a2b2c6;text-align:center;padding:10px 0}
.search-flash .bubble{outline:2px solid #fbbf24;outline-offset:2px;transition:outline .2s}
@media (prefers-reduced-motion: no-preference){.row{animation:msg-in .16s ease-out both}.search-hit{animation:hit-in .14s ease-out both}}@keyframes msg-in{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}@keyframes hit-in{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:none}}

</style>
