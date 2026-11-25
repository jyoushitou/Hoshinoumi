<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref, watch } from 'vue'
import { cleanupStickerCache, getStickerDataUrl, type StickerMeta } from '@/lib/stickerCache'
import { http } from '@/api/client'
import EmptyState from '@/components/EmptyState.vue'
import QqAvatar from '@/components/QqAvatar.vue'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
const session = useSessionStore()
const auth = useAuthStore()
const botQq = computed(() => String(session.status?.self_qq || ''))
const draft = ref('')
const msgsEl = ref<HTMLElement | null>(null)
const bottomAnchor = ref<HTMLElement | null>(null)
const showJump = ref(false)
const stickBottom = ref(true)
function onMsgScroll() { const el = msgsEl.value; if (!el) return; const distance = el.scrollHeight - el.scrollTop - el.clientHeight; showJump.value = distance > 140; stickBottom.value = distance < 80 }
async function scrollToBottom(behavior: ScrollBehavior = 'auto') { await nextTick(); const el = msgsEl.value; if (!el) return; bottomAnchor.value?.scrollIntoView({ block: 'end', behavior }); el.scrollTo({ top: el.scrollHeight, behavior }); showJump.value = false; stickBottom.value = true }
function pinBottomSoon() {
  if (!stickBottom.value) return
  requestAnimationFrame(() => { bottomAnchor.value?.scrollIntoView({ block: 'end' }); const el = msgsEl.value; if (el) el.scrollTop = el.scrollHeight })
}
async function jumpToBottom() { await scrollToBottom('smooth') }
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const imagePreview = ref('')
const imageName = ref('')
const imageError = ref('')
const recording = ref(false)
const recordError = ref('')
const stickerOpen = ref(false)
const stickerCatalog = ref<StickerMeta[]>([])
const stickerLoading = ref(false)
const stickerError = ref('')
const toolOpen = ref(false)
const toolQuery = ref('')
const toolResult = ref('')
const toolBusy = ref(false)
const topicStatus = ref('')
const topicFollowup = ref('')
const topicBusy = ref(false)
const searchOpen = ref(false)
const searchQuery = ref('')
const searchIndex = ref(0)
const motion = ref(localStorage.getItem('hsh_motion') === '1')
let mediaRecorder: MediaRecorder | null = null
let chunks: BlobPart[] = []
const canSend = computed(() => (draft.value.trim().length > 0 || Boolean(imagePreview.value)) && !session.sending && Boolean(session.activeTarget))
const searchHits = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return []
  return session.messages.map((m, i) => ({ m, i })).filter(x => (x.m.content || '').toLowerCase().includes(q))
})
const activeConversation = computed(() => session.conversations.find(c => c.target_id === session.activeTarget) || null)
const syncLabel = computed(() => session.syncState === 'syncing' ? '同步中…' : session.syncState === 'offline' ? '连接中断' : session.syncState === 'online' ? '已同步' : '等待同步')
async function send() {
  if (!canSend.value) return
  const content = draft.value
  const image = imagePreview.value
  const name = imageName.value
  draft.value = ''; imagePreview.value = ''; imageName.value = ''
  const ok = await session.sendMessage(content, image ? { image } : {})
  if (ok) await scrollToBottom('smooth')
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
async function sendSticker(sticker: StickerMeta) {
  stickerError.value = ''
  try {
    const data = await getStickerDataUrl(sticker)
    stickerOpen.value = false
    await session.sendMessage('', { sticker: data })
  } catch (e) {
    stickerError.value = e instanceof Error ? e.message : '表情发送失败'
  }
}
onMounted(() => { void cleanupStickerCache(); void scrollToBottom('auto'); setTimeout(() => { void scrollToBottom('auto') }, 120); setTimeout(() => { void scrollToBottom('auto') }, 600) })
onUpdated(pinBottomSoon)
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void send()
  }
}

function toggleMotion() {
  motion.value = !motion.value
  localStorage.setItem('hsh_motion', motion.value ? '1' : '0')
}
function canRecall(m: { id?: number | string; role: string; created_at?: string; recalled?: boolean }) {
  if (m.role !== 'user' || m.recalled || typeof m.id !== 'number') return false
  const t = Date.parse(String(m.created_at || '').replace(' ', 'T'))
  return Number.isFinite(t) && Date.now() - t <= 120000
}
async function recall(m: { id?: number | string }) {
  if (m.id === undefined) return
  if (!window.confirm('撤回这条消息？')) return
  await session.recallMessage(m.id)
}
async function checkTopic() {
  if (!session.activeTarget || topicBusy.value) return
  topicBusy.value = true
  try {
    const r = await http.post<{ status?: string; followup?: string; message?: string }>('/api/topic', { target_id: session.activeTarget })
    topicStatus.value = r.status === 'closed' ? '话题可能已经结束' : '话题还在继续'
    topicFollowup.value = r.followup || ''
  } catch (e) {
    topicStatus.value = e instanceof Error ? e.message : String(e)
    topicFollowup.value = ''
  } finally { topicBusy.value = false }
}
function useFollowup() {
  if (!topicFollowup.value) return
  draft.value = topicFollowup.value
  topicStatus.value = ''
  textarea.value?.focus()
}
async function runImageSearch() {
  const arg = toolQuery.value.trim()
  if (!arg) { toolResult.value = '先输入关键词'; return }
  toolBusy.value = true; toolResult.value = ''
  try {
    const r = await http.post<{ ok?: boolean; result?: unknown; message?: string }>('/api/tools/search_images/call', { arg })
    toolResult.value = typeof r.result === 'string' ? r.result : JSON.stringify(r.result ?? r.message ?? '已执行')
  } catch (e) {
    toolResult.value = e instanceof Error ? e.message : String(e)
  } finally { toolBusy.value = false }
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
watch(() => session.messages.length, async (_next, prev) => {
  if (stickBottom.value || !prev) await scrollToBottom(prev ? 'smooth' : 'auto')
})
watch(() => session.activeTarget, async () => {
  searchOpen.value = false; searchQuery.value = ''; searchIndex.value = 0
  stickBottom.value = true
  await scrollToBottom('auto')
})
</script>
<template>
  <div class="chat" :class="{ motion }">
    <div class="top">
      <div class="who">
        <QqAvatar class="avatar" :group="activeConversation?.type === 'group' ? session.activeTarget : ''" :qq="activeConversation?.type === 'group' ? '' : botQq" :name="activeConversation?.name || String(session.persona?.name || '?')" /><div>
          <div class="nm">
            {{ activeConversation?.name || session.persona?.name || '未获取到人设' }}
          </div><div class="sub">
            <template v-if="activeConversation?.type === 'group'">群聊 · {{ activeConversation.member_count || 0 }} 人</template><template v-else>私聊 · 记忆同步</template> <span v-if="session.connected" class="pill">在线</span><span class="sync-pill" :class="session.syncState">{{ syncLabel }}</span>
          </div>
        </div>
      </div>
      <Transition name="search-expand">
        <div v-if="searchOpen" class="searchbar">
          <input v-model="searchQuery" placeholder="搜索当前会话…" autofocus @keydown.enter.prevent="nextHit(1)" />
          <span>{{ searchHits.length ? (searchIndex + 1) + '/' + searchHits.length : '无结果' }}</span>
          <button type="button" @click="nextHit(-1)">↑</button>
          <button type="button" @click="nextHit(1)">↓</button>
          <button type="button" @click="toggleSearch">×</button>
        </div>
      </Transition>
      <button v-if="!searchOpen" class="tbtn" @click="toggleSearch">
        ⌕ 聊天内搜索
      </button><button class="tbtn">
        ⋯
      </button>
    </div>
    <div v-if="session.syncGap" class="sync-gap">消息较多，还有未拉完的内容 <button type="button" @click="session.syncNow(true)">继续同步</button></div>
    <div ref="msgsEl" class="msgs" @scroll.passive="onMsgScroll">
      <div v-if="session.loading" class="state">加载中…</div>
      <EmptyState v-else-if="session.historyError" :text="'未获取到聊天记录：' + session.historyError" />
      <EmptyState v-else-if="!session.messages.length" text="暂无聊天记录" />
      <template v-else>
        <div v-for="(m, i) in session.messages" :key="m.id || i" class="msg" :class="{ me: m.role === 'user', 'search-current': searchHits[searchIndex]?.i === i }">
          <QqAvatar v-if="m.role !== 'user'" class="avatar" :qq="botQq" :name="String(session.persona?.name || '?')" />
          <div><div v-if="m.recalled" class="recalled">消息已撤回</div><template v-else><img v-if="m.image_url" :src="m.image_url" class="msg-img" :class="{ sticker: m.kind === 'sticker' }" alt="图片"><audio v-if="m.audio_url" :src="m.audio_url" controls class="msg-audio" /><div v-if="m.content && !((m.kind === 'voice' || m.kind === 'sticker') || (m.image_url && m.content === '[图片]'))" class="bubble" v-html="highlight(m.content)"></div></template><div class="meta"><span>{{ m.pending ? '发送中…' : String(m.created_at || '').slice(0, 16) }}</span><button v-if="canRecall(m)" type="button" class="recall-btn" @click="recall(m)">撤回</button></div></div>
          <QqAvatar v-if="m.role === 'user'" class="avatar mea" :qq="auth.qq" name="你" />
        </div>
      </template>
      <div ref="bottomAnchor" class="bottom-anchor" />
    </div>
    <Transition name="jump-fade"><button v-if="showJump" type="button" class="jump-bottom" @click="jumpToBottom">↓ 最新消息</button></Transition>
    <div class="composer">
      <div class="tools">
        <button type="button" class="tool" @click="pickImage">＋ 图片</button><button type="button" class="tool" :class="{ rec: recording }" @click="toggleVoice">{{ recording ? '■ 停止并发送' : '◌ 语音' }}</button><button type="button" class="tool" @click="toggleStickerPanel">◇ 表情</button><button type="button" class="tool" @click="toolOpen = !toolOpen">⌕ 搜图</button><button type="button" class="tool" :disabled="topicBusy" @click="checkTopic">{{ topicBusy ? '判断中…' : '✦ 话题' }}</button><span>✦ 记忆</span>
      </div>
      <div v-if="topicStatus" class="topic-banner">{{ topicStatus }}<button v-if="topicFollowup" type="button" @click="useFollowup">追问</button><button type="button" @click="topicStatus = ''">×</button></div>
      <div v-if="toolOpen" class="tool-panel"><input v-model="toolQuery" placeholder="搜图关键词" @keydown.enter.prevent="runImageSearch" /><button type="button" :disabled="toolBusy" @click="runImageSearch">{{ toolBusy ? '…' : '搜图' }}</button><div v-if="toolResult" class="tool-result">{{ toolResult }}</div></div>
      <div v-if="stickerOpen" class="sticker-panel"><button v-for="sticker in stickerCatalog" :key="sticker.id" type="button" @click="sendSticker(sticker)"><img :src="sticker.url" :alt="sticker.name" loading="lazy"></button><span v-if="stickerLoading" class="sticker-tip">加载中…</span><span v-else-if="stickerError" class="sticker-tip">{{ stickerError }}</span><span v-else-if="!stickerCatalog.length" class="sticker-tip">暂无表情</span></div>
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
        <span>Enter 发送 · Shift+Enter 换行</span><span class="hint-right"><button type="button" class="motion-toggle" @click="toggleMotion">动画 {{ motion ? '开' : '关' }}</button><span>Web v35.5</span></span>
      </div>
    </div>
  </div>
</template>
<style scoped>
.chat{display:flex;flex-direction:column;min-height:0;height:100%;flex:1;overflow:hidden;position:relative}.top{height:66px;flex:none;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:8px;background:#fff;overflow:hidden}.who{display:flex;align-items:center;gap:11px;min-width:0}.avatar{width:33px;height:33px;border-radius:10px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700;flex:none}.nm{font-size:14px;font-weight:650}.sub{font-size:10px;color:#7d8ca3;margin-top:2px}.sync-pill{font-size:9px;color:#8a9bb0;margin-left:5px}.sync-pill.online{color:#1f9d6b}.sync-pill.offline{color:#c0264a}.sync-pill.syncing{color:#2563eb}.pill{font-size:9px;color:#1d4ed8;border:1px solid #dbe8ff;background:#eef4ff;border-radius:20px;padding:2px 7px}.top .tbtn{margin-left:auto;height:30px;padding:0 10px;border-radius:9px;border:1px solid #e3ebf7;background:#fff;color:#5f7189;font-size:10.5px}.top .tbtn + .tbtn{margin-left:0}
.searchbar{display:flex;align-items:center;gap:6px;flex:1 1 auto;min-width:0;max-width:100%;padding:4px 8px;border:1px solid var(--line);border-radius:8px;background:#f8fbff;overflow:hidden;opacity:1;transition:max-width .28s ease,opacity .2s ease,padding .25s ease}.search-expand-enter-active,.search-expand-leave-active{transition:max-width .28s ease,opacity .2s ease,padding .25s ease}.search-expand-enter-from,.search-expand-leave-to{max-width:0;opacity:0;padding-left:0;padding-right:0;border-width:0}.searchbar input{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#243b55;font:10.5px inherit;outline:0;padding:5px 8px}.searchbar span{font-size:9px;color:#8a9bb0;min-width:40px;text-align:right}.searchbar button{border:1px solid #dbe8ff;background:#fff;color:#5f7189;border-radius:6px;font-size:10px;padding:3px 7px;cursor:pointer}.searchbar button:hover{background:#eef4ff}.msg.search-current .bubble{outline:2px solid #93b7fa;outline-offset:2px}mark{background:#fff1a8;color:inherit;border-radius:2px;padding:0 1px}.sync-gap{display:flex;align-items:center;gap:8px;padding:5px 18px;background:#fff8e6;border-bottom:1px solid #f2d491;color:#8a5a00;font-size:9.5px}.sync-gap button{border:1px solid #f2d491;background:#fff;color:#8a5a00;border-radius:5px;padding:2px 6px;font:9px inherit;cursor:pointer}.msgs{flex:1 1 0;overflow-y:auto;padding:20px 22px 16px;min-height:0}.bottom-anchor{height:1px}.state{padding:20px;text-align:center;font-size:10px;color:#8a9bb0}.day{text-align:center;font-size:9px;color:#93a3b8;margin:2px 0 18px}.day b{font-weight:500;color:#7d8ca3}.msg{display:flex;gap:9px;margin-bottom:14px;max-width:92%}.bubble{padding:9px 12px;border-radius:13px 13px 13px 4px;background:#eef4ff;border:1px solid #e3ebf7;font-size:12.5px;line-height:1.65;color:#243b55}.meta{font-size:9px;color:#93a3b8;margin:4px 2px 0;display:flex;gap:7px;align-items:center}.msg.me .meta{justify-content:flex-end}.recall-btn{border:0;background:none;color:#93a3b8;font:9px inherit;cursor:pointer;padding:0}.recall-btn:hover{color:#c0264a}.recalled{font-size:10px;color:#93a3b8;border:1px dashed #dbe8ff;border-radius:8px;padding:5px 9px;background:#f8fbff}.msg.me{margin-left:auto;justify-content:flex-end}.msg.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:13px 13px 4px 13px}.msg.me .meta{text-align:right}.msg.me .mea{background:#2563eb;color:#fff}.memchip{display:inline-block;margin-top:6px;padding:5px 8px;border-radius:8px;border:1px solid #e4dcff;background:#f3efff;font-size:9.5px;color:#6d4fd6}
.composer{flex:0 0 auto;border-top:1px solid var(--line);padding:11px 18px 13px;background:#fff}.jump-bottom{position:absolute;right:20px;bottom:110px;z-index:5;height:28px;border:1px solid #dbe8ff;border-radius:14px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer;box-shadow:0 4px 14px rgba(37,99,235,.12)}.jump-bottom:hover{background:#eef4ff}.jump-fade-enter-active,.jump-fade-leave-active{transition:opacity .18s,transform .18s}.jump-fade-enter-from,.jump-fade-leave-to{opacity:0;transform:translateY(4px)}.tools{display:flex;gap:6px;margin-bottom:7px}.tools span,.tools .tool{font-size:10px;color:#8a9bb0;padding:4px 8px;border-radius:7px;background:none;border:0;font-family:inherit}.tools .tool{cursor:pointer}.tools span:hover,.tools .tool:hover{background:#eef4ff;color:#1d4ed8}.inputbox{display:flex;align-items:center;gap:9px;border:1px solid #dbe8ff;border-radius:12px;background:#f8fbff;padding:9px 10px}.inputbox:focus-within{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}textarea{flex:1;resize:none;border:0;outline:0;background:none;color:#243b55;font:12.5px/1.5 inherit;height:30px;min-height:30px;line-height:30px;padding:0 2px;box-sizing:border-box}.send{height:30px;padding:0 14px;border-radius:8px;background:#2563eb;color:#fff;font-size:11px;font-weight:700;border:0}.send:disabled{opacity:.45;cursor:not-allowed}.send-error{font-size:9.5px;color:#c0264a;margin-top:5px}.msg-img{max-width:230px;max-height:230px;border-radius:10px;display:block;margin-bottom:5px;border:1px solid #dbe8ff;object-fit:cover}.msg-img.sticker{width:110px;height:110px;object-fit:contain;background:transparent;border:0}.msg-audio{width:230px;height:34px;display:block;margin-bottom:5px}.topic-banner{display:flex;align-items:center;gap:8px;margin-bottom:7px;padding:6px 9px;border:1px solid #e4dcff;border-radius:8px;background:#f3efff;color:#6d4fd6;font-size:9.5px}.topic-banner button{margin-left:auto;border:1px solid #d6c9ff;background:#fff;color:#6d4fd6;border-radius:5px;padding:2px 6px;font:9px inherit;cursor:pointer}.topic-banner button + button{margin-left:0}.tool-panel{display:flex;flex-wrap:wrap;gap:6px;padding:7px;margin-bottom:7px;border:1px solid #dbe8ff;border-radius:10px;background:#f8fbff;max-width:360px}.tool-panel input{flex:1;min-width:120px;border:1px solid #dbe8ff;border-radius:7px;padding:5px 8px;font:10px inherit;outline:0}.tool-panel button{border:0;border-radius:7px;background:#2563eb;color:#fff;font:10px inherit;padding:5px 10px;cursor:pointer}.tool-panel button:disabled{opacity:.5}.tool-result{width:100%;font-size:9.5px;color:#4b5f78;border-top:1px solid #e3ebf7;padding-top:5px;white-space:pre-wrap}.sticker-panel{display:flex;flex-wrap:wrap;gap:4px;padding:7px;margin-bottom:7px;border:1px solid #dbe8ff;border-radius:10px;background:#f8fbff;max-width:300px}.sticker-panel button{width:38px;height:38px;border:0;border-radius:7px;background:#fff;cursor:pointer;padding:2px;overflow:hidden}.sticker-panel button img{width:100%;height:100%;object-fit:contain;display:block}.sticker-tip{font-size:9px;color:#8a9bb0;padding:6px}.sticker-panel button:hover{background:#eef4ff}.tools .tool.rec{color:#c0264a;background:#ffecef}.img-prev{display:flex;align-items:center;gap:8px;margin-bottom:7px;border:1px solid #dbe8ff;background:#f8fbff;border-radius:9px;padding:5px}.img-prev img{width:48px;height:48px;object-fit:cover;border-radius:6px}.img-prev span{font-size:9.5px;color:#6b7c95;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.img-prev button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:14px;cursor:pointer}.img-err{font-size:9.5px;color:#c0264a;margin-top:5px}.hint{display:flex;justify-content:space-between;font-size:9px;color:#9aabbe;margin-top:6px}.hint-right{display:flex;gap:8px;align-items:center}.motion-toggle{border:0;background:none;color:#8a9bb0;font:9px inherit;cursor:pointer;padding:0}.motion-toggle:hover{color:#2563eb}.chat.motion .msg{animation:msg-in .18s ease-out both}.chat.motion .msg.me{animation-name:msg-in-me}.chat.motion .bubble{transition:background .15s ease}.chat.motion .msgs{scroll-behavior:smooth}@keyframes msg-in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}@keyframes msg-in-me{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.chat.motion .msg{animation:none}.chat.motion .msgs{scroll-behavior:auto}}
@media(max-width:820px){
  .top{height:58px;padding:0 12px;gap:6px}.top .tbtn{height:27px;padding:0 7px;font-size:9.5px}.top .tbtn:first-of-type{margin-left:auto}
  .searchbar{flex:1 1 auto;margin:0;padding:3px 6px}.msgs{padding:12px 10px 10px}.composer{padding:8px 10px 10px}
  .tools{overflow-x:auto;white-space:nowrap;padding-bottom:2px}.tools .tool,.tools span{flex:none}
  .msg{max-width:100%}.bubble{font-size:12px}.msg-img{max-width:190px;max-height:190px}
  .inputbox{padding:7px 8px}.hint{font-size:8.5px}.hint .motion-toggle{font-size:8.5px}
}
@media(max-width:520px){
  .top .tbtn:first-of-type{font-size:0}.top .tbtn:first-of-type:after{content:'⌕';font-size:15px}
  .sub{font-size:9px}.sync-pill{display:none}.composer{padding:6px 8px 8px}
  .bubble{font-size:11.5px;line-height:1.55}.meta{font-size:8px}
}
@media(min-width:821px) and (max-width:1180px){
  .top{padding:0 16px}.msgs{padding:16px 18px 14px}.composer{padding:10px 14px 12px}
  .bubble{font-size:12.2px}.msg{max-width:96%}.msg-img{max-width:210px;max-height:210px}
  .tools .tool,.tools span,.top .tbtn{min-height:32px;display:inline-flex;align-items:center}
  .send{min-height:34px;padding:0 16px}.inputbox{padding:8px 9px}
}
@media(min-width:821px) and (max-width:1180px) and (orientation:portrait){
  .top{height:60px}.msgs{padding:14px 16px 12px}.hint{font-size:8.5px}
}
</style>
