<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
const draft = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const imagePreview = ref('')
const imageName = ref('')
const imageError = ref('')
const recording = ref(false)
const recordError = ref('')
const stickerOpen = ref(false)
const searchOpen = ref(false)
const searchQuery = ref('')
const searchIndex = ref(0)
let mediaRecorder: MediaRecorder | null = null
let chunks: BlobPart[] = []
const canSend = computed(() => (draft.value.trim().length > 0 || Boolean(imagePreview.value)) && !session.sending && Boolean(session.activeTarget))
const searchHits = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return []
  return session.messages.map((m, i) => ({ m, i })).filter(x => (x.m.content || '').toLowerCase().includes(q))
})
const syncLabel = computed(() => session.syncState === 'syncing' ? '同步中…' : session.syncState === 'offline' ? '连接中断' : session.syncState === 'online' ? '已同步' : '等待同步')
async function send() {
  if (!canSend.value) return
  const content = draft.value
  const image = imagePreview.value
  const name = imageName.value
  draft.value = ''; imagePreview.value = ''; imageName.value = ''
  const ok = await session.sendMessage(content, image ? { image } : {})
  if (!ok) { draft.value = content; imagePreview.value = image; imageName.value = name }
  textarea.value?.focus()
}
function pickImage() { fileInput.value?.click() }
function clearImage() { imagePreview.value = ''; imageName.value = ''; imageError.value = '' }
function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  imageError.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) { imageError.value = '只能选图片文件'; return }
  if (file.size > 4 * 1024 * 1024) { imageError.value = '图片不能超过 4MB'; return }
  const reader = new FileReader()
  reader.onload = () => { imagePreview.value = String(reader.result || ''); imageName.value = file.name }
  reader.onerror = () => { imageError.value = '读取图片失败' }
  reader.readAsDataURL(file)
  input.value = ''
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
async function toggleVoice() {
  recordError.value = ''
  if (recording.value && mediaRecorder) { mediaRecorder.stop(); return }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    const rec = new MediaRecorder(stream)
    rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
    rec.onstop = async () => {
      recording.value = false
      mediaRecorder = null
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' })
      if (!blob.size) { recordError.value = '没有录到声音'; return }
      if (blob.size > 4 * 1024 * 1024) { recordError.value = '语音不能超过 4MB'; return }
      const data = await blobToDataUrl(blob)
      const ok = await session.sendMessage('', { audio: data })
      if (!ok) recordError.value = session.sendError || '语音发送失败'
    }
    rec.start()
    mediaRecorder = rec
    recording.value = true
  } catch {
    recordError.value = '无法使用麦克风，请检查权限'
  }
}
async function sendSticker(emoji: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 240; canvas.height = 240
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, 240, 240)
  ctx.font = '160px "Segoe UI Emoji", "Apple Color Emoji", sans-serif'
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText(emoji, 120, 132)
  const data = canvas.toDataURL('image/png')
  stickerOpen.value = false
  await session.sendMessage('', { sticker: data })
}
const stickers = ['😊', '😂', '🥺', '😳', '😭', '😡', '🤔', '😴', '❤️', '✨', '👍', '🎉']
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void send()
  }
}

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) searchIndex.value = 0
  else searchQuery.value = ''
}
function escapeHtml(text: string) {
  return text.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c))
}
function highlight(content: string) {
  const q = searchQuery.value.trim()
  const safe = escapeHtml(content || '')
  if (!q) return safe
  const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
  return safe.replace(re, m => '<mark>' + m + '</mark>')
}
async function goHit(i: number) {
  if (!searchHits.value.length) return
  searchIndex.value = (i + searchHits.value.length) % searchHits.value.length
  await nextTick()
  const nodes = document.querySelectorAll('.msg')
  nodes[searchHits.value[searchIndex.value].i]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}
function nextHit(dir = 1) { void goHit(searchIndex.value + dir) }
watch(() => session.activeTarget, () => { searchOpen.value = false; searchQuery.value = ''; searchIndex.value = 0 })
</script>
<template>
  <div class="chat">
    <div class="top">
      <div class="who">
        <span class="avatar">{{ String(session.persona?.name || '?').slice(0, 1) }}</span><div>
          <div class="nm">
            {{ session.persona?.name || '未获取到人设' }}
          </div><div class="sub">
            私聊 · 记忆同步 <span v-if="session.connected" class="pill">在线</span><span class="sync-pill" :class="session.syncState">{{ syncLabel }}</span>
          </div>
        </div>
      </div><button class="tbtn" @click="toggleSearch">
        ⌕ 聊天内搜索
      </button><button class="tbtn">
        ⋯
      </button>
    </div>
    <div v-if="searchOpen" class="searchbar">
      <input v-model="searchQuery" placeholder="搜索当前会话…" autofocus @keydown.enter.prevent="nextHit(1)" />
      <span>{{ searchHits.length ? (searchIndex + 1) + '/' + searchHits.length : '无结果' }}</span>
      <button type="button" @click="nextHit(-1)">↑</button>
      <button type="button" @click="nextHit(1)">↓</button>
      <button type="button" @click="toggleSearch">×</button>
    </div>
    <div class="msgs">
      <div v-if="session.loading" class="state">加载中…</div>
      <EmptyState v-else-if="session.historyError" :text="'未获取到聊天记录：' + session.historyError" />
      <EmptyState v-else-if="!session.messages.length" text="暂无聊天记录" />
      <template v-else>
        <div v-for="(m, i) in session.messages" :key="m.id || i" class="msg" :class="{ me: m.role === 'user', 'search-current': searchHits[searchIndex]?.i === i }">
          <span v-if="m.role !== 'user'" class="avatar">{{ String(session.persona?.name || '?').slice(0, 1) }}</span>
          <div><img v-if="m.image_url" :src="m.image_url" class="msg-img" :class="{ sticker: m.kind === 'sticker' }" alt="图片"><audio v-if="m.audio_url" :src="m.audio_url" controls class="msg-audio" /><div v-if="m.content && !((m.kind === 'voice' || m.kind === 'sticker') || (m.image_url && m.content === '[图片]'))" class="bubble" v-html="highlight(m.content)"></div><div class="meta">{{ m.pending ? '发送中…' : String(m.created_at || '').slice(0, 16) }}</div></div>
          <span v-if="m.role === 'user'" class="avatar mea">你</span>
        </div>
      </template>
    </div>
    <div class="composer">
      <div class="tools">
        <button type="button" class="tool" @click="pickImage">＋ 图片</button><button type="button" class="tool" :class="{ rec: recording }" @click="toggleVoice">{{ recording ? '■ 停止并发送' : '◌ 语音' }}</button><button type="button" class="tool" @click="stickerOpen = !stickerOpen">◇ 表情</button><span>⌕ 搜图</span><span>✦ 记忆</span>
      </div>
      <div v-if="stickerOpen" class="sticker-panel"><button v-for="e in stickers" :key="e" type="button" @click="sendSticker(e)">{{ e }}</button></div>
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden @change="onFile">
      <div v-if="imagePreview" class="img-prev">
        <img :src="imagePreview" alt="预览">
        <span>{{ imageName }}</span>
        <button type="button" @click="clearImage">×</button>
      </div>
      <div v-if="imageError" class="img-err">{{ imageError }}</div>
      <div v-if="recordError" class="img-err">{{ recordError }}</div><div class="inputbox">
        <textarea ref="textarea" v-model="draft" :disabled="!session.activeTarget" placeholder="说点什么…" @keydown="onKeydown" /><button class="send" :disabled="!canSend" @click="send">
          {{ session.sending ? '发送中…' : '发送' }}
        </button>
      </div>
      <div v-if="session.sendError" class="send-error">{{ session.sendError }}</div>
      <div class="hint">
        <span>Enter 发送 · Shift+Enter 换行</span><span>Web v35.5</span>
      </div>
    </div>
  </div>
</template>
<style scoped>
.chat{display:flex;flex-direction:column;min-height:0;height:100%;flex:1;overflow:hidden}.top{height:66px;flex:none;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:8px;background:#fff}.who{display:flex;align-items:center;gap:11px;min-width:0}.avatar{width:33px;height:33px;border-radius:10px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700;flex:none}.nm{font-size:14px;font-weight:650}.sub{font-size:10px;color:#7d8ca3;margin-top:2px}.sync-pill{font-size:9px;color:#8a9bb0;margin-left:5px}.sync-pill.online{color:#1f9d6b}.sync-pill.offline{color:#c0264a}.sync-pill.syncing{color:#2563eb}.pill{font-size:9px;color:#1d4ed8;border:1px solid #dbe8ff;background:#eef4ff;border-radius:20px;padding:2px 7px}.top .tbtn{margin-left:auto;height:30px;padding:0 10px;border-radius:9px;border:1px solid #e3ebf7;background:#fff;color:#5f7189;font-size:10.5px}.top .tbtn + .tbtn{margin-left:0}
.searchbar{display:flex;align-items:center;gap:6px;padding:7px 18px;border-bottom:1px solid var(--line);background:#f8fbff}.searchbar input{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#243b55;font:10.5px inherit;outline:0;padding:5px 8px}.searchbar span{font-size:9px;color:#8a9bb0;min-width:40px;text-align:right}.searchbar button{border:1px solid #dbe8ff;background:#fff;color:#5f7189;border-radius:6px;font-size:10px;padding:3px 7px;cursor:pointer}.searchbar button:hover{background:#eef4ff}.msg.search-current .bubble{outline:2px solid #93b7fa;outline-offset:2px}mark{background:#fff1a8;color:inherit;border-radius:2px;padding:0 1px}.msgs{flex:1 1 0;overflow-y:auto;padding:20px 22px 16px;min-height:0}.state{padding:20px;text-align:center;font-size:10px;color:#8a9bb0}.day{text-align:center;font-size:9px;color:#93a3b8;margin:2px 0 18px}.day b{font-weight:500;color:#7d8ca3}.msg{display:flex;gap:9px;margin-bottom:14px;max-width:92%}.bubble{padding:9px 12px;border-radius:13px 13px 13px 4px;background:#eef4ff;border:1px solid #e3ebf7;font-size:12.5px;line-height:1.65;color:#243b55}.meta{font-size:9px;color:#93a3b8;margin:4px 2px 0}.msg.me{margin-left:auto;flex-direction:row-reverse}.msg.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:13px 13px 4px 13px}.msg.me .meta{text-align:right}.msg.me .mea{background:#2563eb;color:#fff}.memchip{display:inline-block;margin-top:6px;padding:5px 8px;border-radius:8px;border:1px solid #e4dcff;background:#f3efff;font-size:9.5px;color:#6d4fd6}
.composer{flex:0 0 auto;border-top:1px solid var(--line);padding:11px 18px 13px;background:#fff}.tools{display:flex;gap:6px;margin-bottom:7px}.tools span,.tools .tool{font-size:10px;color:#8a9bb0;padding:4px 8px;border-radius:7px;background:none;border:0;font-family:inherit}.tools .tool{cursor:pointer}.tools span:hover,.tools .tool:hover{background:#eef4ff;color:#1d4ed8}.inputbox{display:flex;align-items:flex-end;gap:9px;border:1px solid #dbe8ff;border-radius:12px;background:#f8fbff;padding:9px 10px}.inputbox:focus-within{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}textarea{flex:1;resize:none;border:0;outline:0;background:none;color:#243b55;font:12.5px/1.5 inherit;height:22px}.send{height:30px;padding:0 14px;border-radius:8px;background:#2563eb;color:#fff;font-size:11px;font-weight:700;border:0}.send:disabled{opacity:.45;cursor:not-allowed}.send-error{font-size:9.5px;color:#c0264a;margin-top:5px}.msg-img{max-width:230px;max-height:230px;border-radius:10px;display:block;margin-bottom:5px;border:1px solid #dbe8ff;object-fit:cover}.msg-img.sticker{width:110px;height:110px;object-fit:contain;background:transparent;border:0}.msg-audio{width:230px;height:34px;display:block;margin-bottom:5px}.sticker-panel{display:flex;flex-wrap:wrap;gap:4px;padding:7px;margin-bottom:7px;border:1px solid #dbe8ff;border-radius:10px;background:#f8fbff;max-width:300px}.sticker-panel button{width:38px;height:38px;border:0;border-radius:7px;background:#fff;font-size:22px;cursor:pointer}.sticker-panel button:hover{background:#eef4ff}.tools .tool.rec{color:#c0264a;background:#ffecef}.img-prev{display:flex;align-items:center;gap:8px;margin-bottom:7px;border:1px solid #dbe8ff;background:#f8fbff;border-radius:9px;padding:5px}.img-prev img{width:48px;height:48px;object-fit:cover;border-radius:6px}.img-prev span{font-size:9.5px;color:#6b7c95;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.img-prev button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:14px;cursor:pointer}.img-err{font-size:9.5px;color:#c0264a;margin-top:5px}.hint{display:flex;justify-content:space-between;font-size:9px;color:#9aabbe;margin-top:6px}
</style>
