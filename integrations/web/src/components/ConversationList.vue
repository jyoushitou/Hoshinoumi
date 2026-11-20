<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { http } from '@/api/client'
import EmptyState from '@/components/EmptyState.vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
const session = useSessionStore()
const auth = useAuthStore()
const appVersion = __APP_VERSION__
const router = useRouter()
const tab = ref<'all' | 'private' | 'group'>('all')
const searchQuery = ref('')
const searchOpen = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
const commands = ref<Array<{ name?: string; help?: string; group?: string }>>([])
const filteredConversations = computed(() => {
  if (tab.value === 'all') return session.conversations
  return session.conversations.filter(c => c.type === tab.value)
})
const q = computed(() => searchQuery.value.trim().toLowerCase())
const conversationResults = computed(() => !q.value ? [] : session.conversations.filter(c => String(c.name || c.target_id).toLowerCase().includes(q.value)))
const memoryResults = computed(() => !q.value ? [] : session.memoryTargets.filter((m: unknown) => JSON.stringify(m).toLowerCase().includes(q.value)))
const commandResults = computed(() => !q.value ? [] : commands.value.filter(c => String(c.name || '').toLowerCase().includes(q.value) || String(c.help || '').toLowerCase().includes(q.value) || String(c.group || '').toLowerCase().includes(q.value)))
function closeSearch() { searchOpen.value = false; searchQuery.value = '' }
async function choose(target: string) { await session.selectConversation(target); closeSearch(); router.push('/chat') }
function gotoMemory() { closeSearch(); router.push('/memory') }
function gotoCommand() { closeSearch(); router.push('/commands') }
function logout() { auth.logout(); session.connected = false; session.error = '已退出登录'; closeSearch(); router.push('/chat') }
function onShortcut(e: KeyboardEvent) { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); searchOpen.value = true; searchInput.value?.focus() } }
onMounted(async () => {
  window.addEventListener('keydown', onShortcut)
  try { const r = await http.get<{ data?: Array<{ name?: string; help?: string; group?: string }> }>('/api/commands'); commands.value = Array.isArray(r.data) ? r.data : [] } catch { commands.value = [] }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onShortcut))
</script>
<template>
  <aside class="side">
    <div class="brand">
      <b>HOSHINOUMI</b><span>WEB v{{ appVersion }}</span>
    </div>
    <div class="searchbox">
      <div class="search"><span>⌕</span><input ref="searchInput" v-model="searchQuery" placeholder="搜索会话 / 记忆 / 命令" @focus="searchOpen = true" @keydown.esc="closeSearch"><kbd>⌘K</kbd></div>
      <div v-if="searchOpen" class="search-panel">
        <div v-if="!q" class="search-hint">输入关键词搜索会话、记忆或命令</div>
        <template v-else>
          <div v-if="conversationResults.length" class="sr-sec">会话</div>
          <button v-for="c in conversationResults.slice(0, 5)" :key="'c'+c.target_id" type="button" class="sr" @click="choose(c.target_id)">◉ {{ c.name || c.target_id }}<small>{{ c.type === 'group' ? '群聊' : '私聊' }}</small></button>
          <div v-if="memoryResults.length" class="sr-sec">记忆</div>
          <button v-for="(m, i) in memoryResults.slice(0, 5)" :key="'m'+i" type="button" class="sr" @click="gotoMemory">◈ {{ (m as Record<string, unknown>).target_id || '记忆' }}<small>{{ (m as Record<string, unknown>).last_message || '' }}</small></button>
          <div v-if="commandResults.length" class="sr-sec">命令</div>
          <button v-for="cmd in commandResults.slice(0, 5)" :key="'x'+cmd.name" type="button" class="sr" @click="gotoCommand">{{ cmd.name }}<small>{{ cmd.help || cmd.group || '' }}</small></button>
          <div v-if="!conversationResults.length && !memoryResults.length && !commandResults.length" class="search-hint">没有匹配结果</div>
        </template>
      </div>
    </div>
    <div class="slabel">
      QQ 会话 <em>{{ session.connected ? '同步中' : '未同步' }}</em>
    </div>
    <div class="tabs">
      <button type="button" :class="{ on: tab === 'all' }" @click="tab = 'all'">全部</button>
      <button type="button" :class="{ on: tab === 'private' }" @click="tab = 'private'">私聊</button>
      <button type="button" :class="{ on: tab === 'group' }" @click="tab = 'group'">群聊</button>
    </div>
    <div class="convs">
      <div v-if="session.loading" class="load">加载中…</div>
      <EmptyState v-else-if="session.conversationsError" :text="'未获取到 QQ 会话：' + session.conversationsError" />
      <EmptyState v-else-if="!filteredConversations.length" text="暂无 QQ 会话" />
      <template v-else>
        <div v-for="c in filteredConversations" :key="c.target_id" class="conv" :class="{ on: c.target_id === session.activeTarget }" @click="choose(c.target_id)">
          <span class="avatar">{{ String(c.name || c.target_id).slice(0, 1) }}</span>
          <div class="body"><div class="nm">{{ c.name || c.target_id }}</div><div class="last"><template v-if="c.type === 'group'">群聊 · {{ c.member_count || 0 }} 人 · </template>{{ c.last_message || '暂无消息' }}</div></div>
          <span class="tm">{{ String(c.updated_at || '').slice(11, 16) }}</span>
          <span v-if="Number(c.unread || 0) > 0" class="unread">{{ Number(c.unread) > 99 ? '99+' : c.unread }}</span>
        </div>
      </template>
    </div>
    <div class="side-foot"><span class="dot" :class="{ off: !session.connected }"></span><span>{{ auth.qq || 'owner' }} · schema {{ session.status?.schema || '—' }}</span><span class="lat">{{ session.statusLatencyMs != null ? session.statusLatencyMs + 'ms' : (session.connected ? '在线' : '离线') }}</span><button type="button" class="logout" @click="logout">退出</button></div>
  </aside>
</template>
<style scoped>
.side{background:#f8fbff;border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.brand{padding:18px 18px 12px;display:flex;align-items:center;gap:9px;font-size:12px;letter-spacing:.18em;color:#1e3a5f}.brand span{margin-left:auto;font-size:9px;color:#8a9bb0;border:1px solid #dbe8ff;background:#fff;border-radius:20px;padding:2px 7px;letter-spacing:0}
.searchbox{position:relative;margin:0 14px 12px}.search{height:34px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;display:flex;align-items:center;gap:7px;padding:0 10px;color:#8a9bb0;font-size:11px}.search input{flex:1;min-width:0;border:0;outline:0;background:none;color:#243b55;font:11px inherit}.search kbd{margin-left:auto;font:9px ui-monospace,monospace;border:1px solid #dbe8ff;border-radius:4px;padding:1px 4px}.search-panel{position:absolute;left:0;right:0;top:40px;z-index:12;background:#fff;border:1px solid #dbe8ff;border-radius:10px;box-shadow:0 12px 30px rgba(29,78,216,.14);padding:6px;max-height:320px;overflow:auto}.search-hint{padding:10px 8px;font-size:9.5px;color:#8a9bb0}.sr-sec{padding:6px 8px 3px;font-size:8px;letter-spacing:.12em;color:#9aabbe}.sr{display:block;width:100%;text-align:left;border:0;background:none;color:#243b55;font:10px inherit;padding:6px 8px;border-radius:6px;cursor:pointer}.sr:hover{background:#eef4ff}.sr small{display:block;color:#8a9bb0;font-size:8.5px;margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.slabel{font-size:9px;letter-spacing:.14em;color:#8a9bb0;text-transform:uppercase;padding:6px 18px;display:flex}.slabel em{margin-left:auto;font-style:normal;color:#1f9d6b;letter-spacing:0}
.tabs{display:flex;gap:4px;padding:0 14px 8px}.tabs button{flex:1;border:1px solid #e3ebf7;background:#fff;color:#8a9bb0;font:9.5px inherit;border-radius:7px;padding:4px 0;cursor:pointer}.tabs button.on{background:#eef4ff;border-color:#c7dcff;color:#1d4ed8}.convs{flex:1;overflow:auto;padding:0 8px;min-height:0}.conv{display:flex;gap:9px;padding:9px;border-radius:11px;position:relative;text-decoration:none;color:inherit;border:1px solid transparent;transition:background .18s,border-color .18s,transform .18s}.conv:hover{background:#eef4ff;border-color:#dbe8ff;transform:translateX(2px)}.conv.on{background:#e7f0ff;border-color:#c7dcff}
.avatar{width:33px;height:33px;border-radius:10px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#1d4ed8;flex:none}
.body{min-width:0}.nm{font-size:12px;font-weight:600;color:#1e3a5f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.last{font-size:10.5px;color:#8a9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}.tm{font-size:9px;color:#8a9bb0;margin-left:auto;flex:none}.unread{position:absolute;right:8px;bottom:8px;min-width:15px;height:15px;border-radius:8px;background:#2563eb;color:#fff;font-size:9px;font-weight:700;display:grid;place-items:center}
.conn{margin:10px 14px 14px;padding:11px 12px;border:1px solid #e3ebf7;border-radius:12px;background:#fff}.conn .k{font-size:9px;letter-spacing:.08em;color:#8a9bb0;margin-bottom:5px;display:flex;align-items:center}.logout{margin-left:auto;border:1px solid #f0d7dd;background:#fff;color:#b23b52;border-radius:5px;padding:2px 6px;font:8.5px inherit;cursor:pointer}.logout:hover{background:#fff5f7}.conn .v{font-size:11px;color:#1f9d6b;display:flex;align-items:center;gap:6px}.dot{width:6px;height:6px;border-radius:50%;background:#1f9d6b}.dot.off{background:#c0264a}.load{padding:18px 12px;text-align:center;font-size:10px;color:#8a9bb0}.side-foot{height:33px;flex:none;margin-top:auto;border-top:1px solid #e3ebf7;display:flex;align-items:center;gap:5px;padding:0 14px;font-size:8.5px;color:#7d8fa6;background:#fbfdff}.side-foot .lat{margin-left:auto;font-family:ui-monospace,monospace;color:#93a4b8}.side-foot .dot{flex:none}.side-foot .logout{margin-left:2px}
</style>
