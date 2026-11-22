<template>
  <div class="mc">
    <template v-if="pane === 'list'">
      <div class="head"><div><h1>聊天</h1><p>QQ 会话 · {{ session.conversations.length }} 个</p></div><i class="dot" :class="{ off: !session.connected }" /></div>
      <div class="search">搜索会话</div>
      <div v-if="!auth.loggedIn" class="notice">游客模式：登录后可同步 QQ 会话。</div>
      <div v-else-if="listError" class="notice error">{{ listError }}</div>
      <div v-else-if="!session.conversations.length" class="notice">{{ session.loading ? '正在同步会话…' : '暂无会话。后端有 QQ 消息后会出现在这里。' }}</div>
      <button v-for="row in session.conversations" :key="row.target_id" class="conv" type="button" @click="open(row.target_id)">
        <span class="avatar">{{ (row.name || '?').slice(0, 1) }}</span>
        <span class="copy"><b>{{ row.name || row.target_id }}</b><small>{{ row.last_message || '暂无消息' }}</small></span>
        <span class="meta"><small>{{ timeOf(row.updated_at) }}</small><em v-if="row.unread">{{ row.unread > 99 ? '99+' : row.unread }}</em></span>
      </button>
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
        <div v-for="(m, i) in session.messages" :key="m.id ?? i" class="row" :class="{ me: m.role === 'user' || m.role === 'me' }">
          <span v-if="m.role !== 'user' && m.role !== 'me'" class="mini">{{ activeName.slice(0, 1) }}</span>
          <div class="box">
            <div v-if="m.recalled" class="recalled">消息已撤回</div>
            <template v-else>
              <img v-if="m.image_url" :src="m.image_url" class="msg-img" :class="{ sticker: m.kind === 'sticker' }" alt="图片">
              <audio v-if="m.audio_url" :src="m.audio_url" controls class="msg-audio" />
              <div v-if="m.content" class="bubble">{{ m.content }}</div>
            </template>
            <small class="stamp">{{ m.pending ? '发送中…' : String(m.created_at || '').slice(11, 16) }}</small>
          </div>
          <span v-if="m.role === 'user' || m.role === 'me'" class="mini mea">你</span>
        </div>
      </div>
      <div v-if="mediaError" class="media-error">{{ mediaError }}</div>
      <div v-if="imagePreview" class="preview"><img :src="imagePreview" alt="预览"><span>{{ imageName }}</span><button type="button" @click="clearImage">×</button></div>
      <div v-if="stickerOpen" class="stickers"><button v-for="e in stickers" :key="e" type="button" @click="sendSticker(e)">{{ e }}</button></div>
      <div class="composer">
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden @change="onFile">
        <button type="button" class="tool" aria-label="图片" @click="pickImage">＋</button>
        <button type="button" class="tool" :class="{ rec: recording }" aria-label="语音" @click="toggleVoice">{{ recording ? '■' : '🎙' }}</button>
        <button type="button" class="tool" aria-label="表情" @click="stickerOpen = !stickerOpen">☺</button>
        <textarea ref="textarea" v-model="draft" rows="1" placeholder="和奈绪说点什么…" enterkeyhint="send" @keydown="onKeydown" @input="autosize" />
        <button type="button" class="send" :disabled="!canSend" @click="send">{{ session.sending ? '…' : '↑' }}</button>
      </div>
      <div v-if="session.sendError" class="media-error">{{ session.sendError }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'

const session = useSessionStore()
const auth = useAuthStore()
const pane = ref<'list' | 'chat'>('list')
const draft = ref('')
const messageList = ref<HTMLElement | null>(null)
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const imagePreview = ref('')
const imageName = ref('')
const mediaError = ref('')
const stickerOpen = ref(false)
const recording = ref(false)
let recorder: MediaRecorder | null = null
let chunks: BlobPart[] = []
let stream: MediaStream | null = null
const stickers = ['😊','😂','🥺','😳','😭','😡','🤔','😴','❤️','✨','👍','🎉']
const listError = computed(() => auth.loggedIn ? (session.conversationsError || session.error) : '')
const active = computed(() => session.conversations.find(row => row.target_id === session.activeTarget) || null)
const activeName = computed(() => active.value?.name || String(session.persona?.name || '会话'))
const activeGroup = computed(() => active.value?.type === 'group')
const activeCount = computed(() => Number(active.value?.member_count || 0))
const syncLabel = computed(() => session.syncState === 'syncing' ? '同步中' : session.syncState === 'offline' ? '同步中断' : session.syncState === 'online' ? '已同步' : '等待同步')
const canSend = computed(() => Boolean(draft.value.trim() || imagePreview.value) && !session.sending && Boolean(session.activeTarget))

onMounted(() => { if (auth.loggedIn && !session.conversations.length) void session.refresh() })
onBeforeUnmount(() => { if (recorder && recording.value) recorder.stop(); stream?.getTracks().forEach(t => t.stop()) })
watch(() => session.messages.length, scrollBottom)
watch(() => session.activeTarget, scrollBottom)

function timeOf(value?: string) { const d = value ? new Date(value) : null; return d && !Number.isNaN(d.getTime()) ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '' }
async function scrollBottom() { await nextTick(); const el = messageList.value; if (el) el.scrollTop = el.scrollHeight }
async function open(target: string) { await session.selectConversation(target); pane.value = 'chat'; imagePreview.value = ''; imageName.value = ''; mediaError.value = ''; await scrollBottom() }
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
async function sendSticker(e: string) {
  const c = document.createElement('canvas'); c.width = 240; c.height = 240; const x = c.getContext('2d'); if (!x) return
  x.clearRect(0, 0, 240, 240); x.font = '160px "Segoe UI Emoji","Apple Color Emoji",sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(e, 120, 132)
  stickerOpen.value = false
  const ok = await session.sendMessage('', { sticker: c.toDataURL('image/png') })
  if (!ok) mediaError.value = session.sendError || '表情发送失败'; await scrollBottom()
}
</script>

<style scoped>
.mc{height:100%;min-height:0;display:flex;flex-direction:column;padding:0 12px calc(8px + env(safe-area-inset-bottom));background:#f7faff;color:#17263b}
.head{display:flex;align-items:flex-end;justify-content:space-between;padding:14px 2px 9px}h1{margin:0;font-size:24px;letter-spacing:-.03em}p{margin:3px 0 0;color:#8a9bb0;font-size:10px}.dot{width:8px;height:8px;border-radius:50%;background:#1f9d6b;box-shadow:0 0 0 3px rgba(31,157,107,.1)}.dot.off{background:#cbd5e1;box-shadow:none}
.search{height:36px;border:1px solid #e3ebf7;border-radius:11px;background:#fff;color:#9aabc0;display:flex;align-items:center;padding:0 11px;font-size:10px;margin-bottom:10px}
.notice{border:1px dashed #d7e6ff;background:#f4f9ff;color:#7a8fa8;border-radius:11px;padding:12px;font-size:10px;line-height:1.6;margin:6px 0}.notice.error{border-color:#fecaca;background:#fff5f5;color:#b91c1c}
.conv{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:1px solid transparent;background:transparent;padding:10px 8px;border-radius:12px;cursor:pointer}.conv:active{background:#fff;border-color:#e7efff}.avatar{width:38px;height:38px;border-radius:12px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-weight:800;font-size:13px;flex:none}.copy{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}.copy b{font-size:12px;color:#253b56;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.copy small{font-size:9.5px;color:#8b9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none}.meta small{font-size:8px;color:#a2b2c6}.meta em{min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:#2563eb;color:#fff;font-size:8px;font-style:normal;display:grid;place-items:center}
.chat-head{display:flex;align-items:center;gap:9px;padding:10px 0 9px;border-bottom:1px solid #e7effa;flex:none}.back{width:30px;height:32px;border:0;background:none;color:#52708f;font-size:20px;flex:none}.who{flex:1;min-width:0}.who b{display:block;font-size:13px;color:#213954;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.who small{display:block;color:#1f9d6b;font-size:8px;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.gap{flex:none;font-size:8px;color:#8a5a00;border:1px solid #f2d491;background:#fff8e6;border-radius:7px;padding:4px 6px}
.messages{flex:1;min-height:180px;overflow-y:auto;padding:12px 0;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;scrollbar-width:none}.messages::-webkit-scrollbar{display:none}.row{display:flex;align-items:flex-end;gap:5px;margin-bottom:10px}.row.me{justify-content:flex-end}.box{max-width:82%;display:flex;flex-direction:column;align-items:flex-start}.row.me .box{align-items:flex-end}.mini{width:22px;height:22px;border-radius:7px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:8px;font-weight:800;flex:none}.mini.mea{background:#2563eb;color:#fff}
.bubble{padding:8px 11px;border-radius:12px 12px 12px 4px;background:#fff;border:1px solid #e3ebf7;color:#344b64;font-size:12px;line-height:1.65;white-space:pre-wrap;word-break:break-word}.row.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:12px 12px 4px 12px}.recalled{font-size:9px;color:#93a3b8;border:1px dashed #dbe8ff;border-radius:8px;padding:5px 9px;background:#f8fbff}.stamp{font-size:7px;color:#a2b2c6;margin-top:3px}.row.me .stamp{text-align:right}.msg-img{max-width:180px;max-height:180px;border-radius:10px;display:block;margin-bottom:2px;object-fit:cover}.msg-img.sticker{width:96px;height:96px;object-fit:contain;background:transparent;border:0}.msg-audio{width:190px;max-width:100%;height:34px;display:block;margin-bottom:2px}
.media-error{flex:none;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:8px;font-size:9px;padding:6px 8px;margin:4px 0}.preview{display:flex;align-items:center;gap:7px;flex:none;border:1px solid #dbe8ff;background:#fff;border-radius:9px;padding:5px;margin-bottom:6px}.preview img{width:40px;height:40px;border-radius:6px;object-fit:cover}.preview span{flex:1;min-width:0;font-size:8px;color:#6b7c95;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.preview button{border:0;background:none;color:#8a9bb0;font-size:16px}
.stickers{display:flex;flex-wrap:wrap;gap:4px;flex:none;padding:6px;margin-bottom:6px;border:1px solid #dbe8ff;border-radius:10px;background:#fff}.stickers button{width:36px;height:36px;border:0;border-radius:7px;background:#f8fbff;font-size:19px}
.composer{display:flex;gap:5px;align-items:flex-end;border-top:1px solid #e5edf9;padding:7px 0 0;background:#f7faff;flex:none}.tool{width:32px;height:34px;flex:none;border:1px solid #e5edf9;border-radius:9px;background:#fff;color:#607795;font-size:15px}.tool.rec{color:#c0264a;background:#ffecef;border-color:#fecaca}.composer textarea{flex:1;min-width:0;resize:none;max-height:96px;border:1px solid #e1ebf9;border-radius:11px;background:#fff;padding:8px 10px;font:16px/1.4 inherit;color:#344b64;outline:0}.composer textarea:focus{border-color:#93c5fd;box-shadow:0 0 0 3px rgba(37,99,235,.07)}.send{width:36px;height:36px;flex:none;border:0;border-radius:11px;background:#2563eb;color:#fff;font-size:17px}.send:disabled{background:#cbd5e1}
@media(max-height:560px){.messages{min-height:100px}.head{padding-top:8px}}
</style>
