<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'

const session = useSessionStore()
const auth = useAuthStore()
const pane = ref<'list' | 'chat'>('list')
const draft = ref('')
const listError = computed(() => auth.loggedIn ? (session.conversationsError || session.error) : '')

onMounted(() => {
  if (auth.loggedIn && !session.conversations.length) void session.refresh()
})

function timeOf(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function openConversation(targetId: string) {
  await session.selectConversation(targetId)
  pane.value = 'chat'
}

async function send() {
  const text = draft.value.trim()
  if (!text || session.sending) return
  draft.value = ''
  await session.sendMessage(text)
}
</script>

<template>
  <div class="mobile-chat">
    <template v-if="pane === 'list'">
      <div class="list-head">
        <div><h1>聊天</h1><p>QQ 会话 · {{ session.conversations.length }} 个</p></div>
        <span class="status-dot" :class="{ off: !session.connected }" />
      </div>
      <div class="search-box">⌕ 搜索会话</div>

      <div v-if="!auth.loggedIn" class="notice">游客模式：登录后可同步 QQ 会话。</div>
      <div v-else-if="listError" class="notice error">{{ listError }}</div>
      <div v-else-if="!session.conversations.length" class="notice">
        {{ session.loading ? '正在同步会话…' : '暂无会话。后端有 QQ 消息后会出现在这里。' }}
      </div>

      <button
        v-for="row in session.conversations"
        :key="row.target_id"
        class="conv"
        type="button"
        @click="openConversation(row.target_id)"
      >
        <span class="avatar">{{ (row.name || '?').slice(0, 1) }}</span>
        <span class="copy">
          <span class="name">{{ row.name || row.target_id }}</span>
          <span class="last">{{ row.last_message || '暂无消息' }}</span>
        </span>
        <span class="meta">
          <span class="time">{{ timeOf(row.updated_at) }}</span>
          <span v-if="row.unread" class="badge">{{ row.unread > 99 ? '99+' : row.unread }}</span>
        </span>
      </button>
    </template>

    <template v-else>
      <div class="chat-head">
        <button type="button" class="back" @click="pane = 'list'">‹</button>
        <div>
          <b>{{ session.conversations.find(row => row.target_id === session.activeTarget)?.name || '会话' }}</b>
          <small>{{ session.syncState === 'online' ? '已连接' : '未同步' }}</small>
        </div>
        <span class="chat-more">☰</span>
      </div>
      <div class="messages">
        <div v-if="session.historyError" class="notice error">{{ session.historyError }}</div>
        <div v-else-if="!session.messages.length" class="notice">暂无历史消息</div>
        <div v-for="(message, index) in session.messages" :key="message.id ?? index" class="bubble-row" :class="{ me: message.role === 'user' || message.role === 'me' }">
          <div class="bubble" :class="{ image: message.kind === 'image' }">{{ message.content || (message.kind === 'image' ? '[图片]' : '') }}</div>
        </div>
      </div>
      <div class="composer">
        <textarea v-model="draft" rows="1" placeholder="和奈绪说点什么…" @keydown.enter.exact.prevent="send" />
        <button type="button" :disabled="session.sending || !draft.trim()" @click="send">↑</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.mobile-chat{min-height:100%;display:flex;flex-direction:column;padding:0 14px 12px;background:#f7faff}
.list-head{display:flex;align-items:flex-end;justify-content:space-between;padding:16px 2px 10px}
h1{font-size:24px;line-height:1.15;margin:0;letter-spacing:-.03em}p{margin:3px 0 0;color:#8a9bb0;font-size:10px}
.status-dot{width:8px;height:8px;border-radius:50%;background:#1f9d6b;box-shadow:0 0 0 3px rgba(31,157,107,.1)}
.status-dot.off{background:#cbd5e1;box-shadow:none}
.search-box{height:36px;border:1px solid #e3ebf7;border-radius:11px;background:#fff;color:#9aabc0;display:flex;align-items:center;padding:0 11px;font-size:10px;margin-bottom:10px}
.notice{border:1px dashed #d7e6ff;background:#f4f9ff;color:#7a8fa8;border-radius:11px;padding:12px;font-size:10px;line-height:1.6;margin:6px 0}
.notice.error{border-color:#fecaca;background:#fff5f5;color:#b91c1c}
.conv{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:1px solid transparent;background:transparent;padding:10px 8px;border-radius:12px;cursor:pointer}
.conv:active{background:#fff;border-color:#e7efff}
.avatar{width:38px;height:38px;border-radius:12px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-weight:800;font-size:13px;flex:none}
.copy{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.name{font-size:12px;color:#253b56;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.last{font-size:9.5px;color:#8b9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none}
.time{font-size:8px;color:#a2b2c6}.badge{min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:#2563eb;color:#fff;font-size:8px;display:grid;place-items:center}
.chat-head{display:flex;align-items:center;gap:9px;padding:14px 0 10px;border-bottom:1px solid #e7effa}
.chat-head .back{width:28px;height:30px;border:0;background:none;color:#52708f;font-size:20px;cursor:pointer}
.chat-head b{display:block;font-size:13px;color:#213954}.chat-head small{display:block;color:#1f9d6b;font-size:8px;margin-top:1px}
.chat-more{margin-left:auto;color:#8093ab;font-size:15px}
.messages{flex:1;min-height:180px;overflow-y:auto;padding:12px 0}
.bubble-row{display:flex;margin-bottom:9px;justify-content:flex-start}.bubble-row.me{justify-content:flex-end}
.bubble{max-width:82%;padding:8px 10px;border-radius:12px 12px 12px 4px;background:#fff;border:1px solid #e3ebf7;color:#344b64;font-size:11px;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.bubble-row.me .bubble{background:#2563eb;border-color:#2563eb;color:#fff;border-radius:12px 12px 4px 12px}
.bubble.image{padding:6px;background:#eef4ff;color:#2563eb}
.composer{display:flex;gap:7px;align-items:flex-end;border-top:1px solid #e5edf9;padding-top:8px;background:#f7faff}
.composer textarea{flex:1;resize:none;max-height:90px;border:1px solid #e1ebf9;border-radius:10px;background:#fff;padding:8px 10px;font:11px/1.5 inherit;color:#344b64;outline:0}
.composer button{width:34px;height:34px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-size:15px;cursor:pointer}
.composer button:disabled{background:#cbd5e1;cursor:default}
</style>
