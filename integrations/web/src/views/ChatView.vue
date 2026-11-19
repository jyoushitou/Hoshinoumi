<script setup lang="ts">
import { computed, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
const draft = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const imagePreview = ref('')
const imageName = ref('')
const imageError = ref('')
const canSend = computed(() => (draft.value.trim().length > 0 || Boolean(imagePreview.value)) && !session.sending && Boolean(session.activeTarget))
async function send() {
  if (!canSend.value) return
  const content = draft.value
  const image = imagePreview.value
  const name = imageName.value
  draft.value = ''; imagePreview.value = ''; imageName.value = ''
  const ok = await session.sendMessage(content, image)
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
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void send()
  }
}
</script>
<template>
  <div class="chat">
    <div class="top">
      <div class="who">
        <span class="avatar">{{ String(session.persona?.name || '?').slice(0, 1) }}</span><div>
          <div class="nm">
            {{ session.persona?.name || '未获取到人设' }}
          </div><div class="sub">
            私聊 · 记忆同步 <span v-if="session.connected" class="pill">在线</span>
          </div>
        </div>
      </div><button class="tbtn">
        ⌕ 聊天内搜索
      </button><button class="tbtn">
        ⋯
      </button>
    </div>
    <div class="msgs">
      <div v-if="session.loading" class="state">加载中…</div>
      <EmptyState v-else-if="session.historyError" :text="'未获取到聊天记录：' + session.historyError" />
      <EmptyState v-else-if="!session.messages.length" text="暂无聊天记录" />
      <template v-else>
        <div v-for="(m, i) in session.messages" :key="m.id || i" class="msg" :class="{ me: m.role === 'user' }">
          <span v-if="m.role !== 'user'" class="avatar">{{ String(session.persona?.name || '?').slice(0, 1) }}</span>
          <div><img v-if="m.image_url" :src="m.image_url" class="msg-img" alt="图片"><div v-if="m.content" class="bubble">{{ m.content }}</div><div class="meta">{{ m.pending ? '发送中…' : String(m.created_at || '').slice(0, 16) }}</div></div>
          <span v-if="m.role === 'user'" class="avatar mea">你</span>
        </div>
      </template>
    </div>
    <div class="composer">
      <div class="tools">
        <button type="button" class="tool" @click="pickImage">＋ 图片</button><span>◌ 语音</span><span>◇ 表情</span><span>⌕ 搜图</span><span>✦ 记忆</span>
      </div>
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden @change="onFile">
      <div v-if="imagePreview" class="img-prev">
        <img :src="imagePreview" alt="预览">
        <span>{{ imageName }}</span>
        <button type="button" @click="clearImage">×</button>
      </div>
      <div v-if="imageError" class="img-err">{{ imageError }}</div><div class="inputbox">
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
.chat{display:flex;flex-direction:column;min-height:0;height:100%;flex:1;overflow:hidden}.top{height:66px;flex:none;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:8px;background:#fff}.who{display:flex;align-items:center;gap:11px;min-width:0}.avatar{width:33px;height:33px;border-radius:10px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:11px;font-weight:700;flex:none}.nm{font-size:14px;font-weight:650}.sub{font-size:10px;color:#7d8ca3;margin-top:2px}.pill{font-size:9px;color:#1d4ed8;border:1px solid #dbe8ff;background:#eef4ff;border-radius:20px;padding:2px 7px}.top .tbtn{margin-left:auto;height:30px;padding:0 10px;border-radius:9px;border:1px solid #e3ebf7;background:#fff;color:#5f7189;font-size:10.5px}.top .tbtn + .tbtn{margin-left:0}
.msgs{flex:1 1 0;overflow-y:auto;padding:20px 22px 16px;min-height:0}.state{padding:20px;text-align:center;font-size:10px;color:#8a9bb0}.day{text-align:center;font-size:9px;color:#93a3b8;margin:2px 0 18px}.day b{font-weight:500;color:#7d8ca3}.msg{display:flex;gap:9px;margin-bottom:14px;max-width:92%}.bubble{padding:9px 12px;border-radius:13px 13px 13px 4px;background:#eef4ff;border:1px solid #e3ebf7;font-size:12.5px;line-height:1.65;color:#243b55}.meta{font-size:9px;color:#93a3b8;margin:4px 2px 0}.msg.me{margin-left:auto;flex-direction:row-reverse}.msg.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:13px 13px 4px 13px}.msg.me .meta{text-align:right}.msg.me .mea{background:#2563eb;color:#fff}.memchip{display:inline-block;margin-top:6px;padding:5px 8px;border-radius:8px;border:1px solid #e4dcff;background:#f3efff;font-size:9.5px;color:#6d4fd6}
.composer{flex:0 0 auto;border-top:1px solid var(--line);padding:11px 18px 13px;background:#fff}.tools{display:flex;gap:6px;margin-bottom:7px}.tools span,.tools .tool{font-size:10px;color:#8a9bb0;padding:4px 8px;border-radius:7px;background:none;border:0;font-family:inherit}.tools .tool{cursor:pointer}.tools span:hover,.tools .tool:hover{background:#eef4ff;color:#1d4ed8}.inputbox{display:flex;align-items:flex-end;gap:9px;border:1px solid #dbe8ff;border-radius:12px;background:#f8fbff;padding:9px 10px}.inputbox:focus-within{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}textarea{flex:1;resize:none;border:0;outline:0;background:none;color:#243b55;font:12.5px/1.5 inherit;height:22px}.send{height:30px;padding:0 14px;border-radius:8px;background:#2563eb;color:#fff;font-size:11px;font-weight:700;border:0}.send:disabled{opacity:.45;cursor:not-allowed}.send-error{font-size:9.5px;color:#c0264a;margin-top:5px}.msg-img{max-width:230px;max-height:230px;border-radius:10px;display:block;margin-bottom:5px;border:1px solid #dbe8ff;object-fit:cover}.img-prev{display:flex;align-items:center;gap:8px;margin-bottom:7px;border:1px solid #dbe8ff;background:#f8fbff;border-radius:9px;padding:5px}.img-prev img{width:48px;height:48px;object-fit:cover;border-radius:6px}.img-prev span{font-size:9.5px;color:#6b7c95;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.img-prev button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:14px;cursor:pointer}.img-err{font-size:9.5px;color:#c0264a;margin-top:5px}.hint{display:flex;justify-content:space-between;font-size:9px;color:#9aabbe;margin-top:6px}
</style>
