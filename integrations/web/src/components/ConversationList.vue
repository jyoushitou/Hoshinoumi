<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { http } from '@/api/client'
import EmptyState from '@/components/EmptyState.vue'
import NewGroupModal from '@/components/NewGroupModal.vue'
import { railHidden, sideHidden } from '@/composables/useLayoutState'
import QqAvatar from '@/components/QqAvatar.vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'
const session = useSessionStore()
const auth = useAuthStore()
const isOwner = useIsOwner()
const appVersion = __APP_VERSION__
const botQq = computed(() => String(session.status?.self_qq || ''))
const router = useRouter()
const tab = ref<'all' | 'private' | 'group' | 'mode'>('all')
const searchQuery = ref('')
const searchOpen = ref(false)
const newGroupOpen = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
const commands = ref<Array<{ name?: string; help?: string; group?: string }>>([])
interface ConvPref { muted?: boolean; hidden?: boolean; deleted_at?: string | null }
const prefs = ref<Record<string, ConvPref>>({})
const convMenu = ref<{ x: number; y: number; conv: any } | null>(null)
const adminModal = ref<any | null>(null)
const adminQq = ref('')
const admins = ref<string[]>([])
const recallNotice = ref('消息已撤回')
async function loadPrefs() {
  try { const r = await http.get<{ data?: Record<string, ConvPref> }>('/api/conversations/preferences'); prefs.value = r.data || {} } catch { prefs.value = {} }
}
function isGone(c: any) { const p = prefs.value[c.target_id]; return Boolean(p?.hidden || p?.deleted_at) }
function isMuted(c: any) { return Boolean(prefs.value[c.target_id]?.muted) }
function openMenu(event: MouseEvent, conv: any) {
  event.preventDefault(); event.stopPropagation()
  convMenu.value = { x: Math.min(event.clientX, window.innerWidth - 180), y: Math.min(event.clientY, window.innerHeight - 250), conv }
}
function closeMenu() { convMenu.value = null }
async function toggleMute(conv: any) {
  const next = !isMuted(conv)
  try { await http.patch('/api/conversations/' + encodeURIComponent(conv.target_id), { muted: next }); prefs.value[conv.target_id] = { ...(prefs.value[conv.target_id] || {}), muted: next } } catch { /* ignore */ }
  closeMenu()
}
async function hideConversation(conv: any) {
  try { await http.patch('/api/conversations/' + encodeURIComponent(conv.target_id), { hidden: true }); prefs.value[conv.target_id] = { ...(prefs.value[conv.target_id] || {}), hidden: true } } catch { /* ignore */ }
  closeMenu()
}
async function deleteConversation(conv: any) {
  const group = conv.type === 'group' || conv.type === 'mode'
  const dissolve = conv.type === 'group' && String(conv.target_id).startsWith('h_')
  const text = dissolve ? '你是群主，退出会解散该群。确定？' : group ? '退出这个群聊？' : '删除这个联系人会话？'
  if (!window.confirm(text)) return
  try { await http.delete('/api/conversations/' + encodeURIComponent(conv.target_id), { dissolve }); prefs.value[conv.target_id] = { ...(prefs.value[conv.target_id] || {}), hidden: true, deleted_at: 'now' } } catch { /* ignore */ }
  closeMenu()
}
async function openAdmins(conv: any) {
  adminModal.value = conv
  adminQq.value = ''; recallNotice.value = '消息已撤回'
  try {
    const [a, b] = await Promise.all([http.get<{ admins?: string[] }>('/api/groups/' + encodeURIComponent(conv.target_id) + '/admins'), http.get<{ recall_notice?: string }>('/api/groups/' + encodeURIComponent(conv.target_id) + '/settings')])
    admins.value = Array.isArray(a.admins) ? a.admins : []
    recallNotice.value = b.recall_notice || '消息已撤回'
  } catch { admins.value = [] }
  closeMenu()
}
async function addAdmin(remove = false) {
  if (!adminModal.value || !adminQq.value.trim()) return
  try { const r = await http.post<{ admins?: string[] }>('/api/groups/' + encodeURIComponent(adminModal.value.target_id) + '/admins', { qq: adminQq.value.trim(), action: remove ? 'remove' : 'add' }); admins.value = r.admins || admins.value; adminQq.value = '' } catch { /* ignore */ }
}
async function saveRecallNotice() {
  if (!adminModal.value) return
  try { await http.patch('/api/groups/' + encodeURIComponent(adminModal.value.target_id) + '/settings', { recall_notice: recallNotice.value }) } catch { /* ignore */ }
}
const modeConversations = computed<any[]>(() => isOwner.value ? [
  { target_id: 'mode:code', name: '代码模式', type: 'mode', last_message: '独立会话 · 记忆共享 · 30 分钟', updated_at: '', member_count: 0, unread: 0, count: 0 },
  { target_id: 'mode:agent', name: 'Agent 模式', type: 'mode', last_message: '工具调用 / 任务状态', updated_at: '', member_count: 0, unread: 0, count: 0 },
  { target_id: 'mode:shell', name: 'Shell 模式', type: 'mode', last_message: '危险命令审批 / 输出', updated_at: '', member_count: 0, unread: 0, count: 0 },
] : [])
const filteredConversations = computed(() => {
  const base = tab.value === 'mode' ? modeConversations.value : tab.value === 'all' ? [...modeConversations.value, ...session.conversations] : session.conversations.filter(c => c.type === tab.value)
  return base.filter(c => !isGone(c))
})
const q = computed(() => searchQuery.value.trim().toLowerCase())
const conversationResults = computed(() => !q.value ? [] : session.conversations.filter(c => String(c.name || c.target_id).toLowerCase().includes(q.value)))
const memoryResults = computed(() => !q.value ? [] : session.memoryTargets.filter((m: unknown) => JSON.stringify(m).toLowerCase().includes(q.value)))
const commandResults = computed(() => !q.value ? [] : commands.value.filter(c => String(c.name || '').toLowerCase().includes(q.value) || String(c.help || '').toLowerCase().includes(q.value) || String(c.group || '').toLowerCase().includes(q.value)))
function closeSearch() { searchOpen.value = false; searchQuery.value = '' }
async function onGroupCreated(id: string) {
  newGroupOpen.value = false
  await session.refresh()
  await session.selectConversation(id)
  closeSearch()
  router.push('/chat')
}
async function choose(target: string) { await session.selectConversation(target); closeSearch(); router.push('/chat') }
function gotoMemory() { closeSearch(); router.push('/memory') }
function gotoCommand() { closeSearch(); router.push('/commands') }
function logout() { auth.logout(); session.connected = false; session.error = '已退出登录'; closeSearch(); router.push('/chat') }
function onShortcut(e: KeyboardEvent) { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); searchOpen.value = true; searchInput.value?.focus() } }
onMounted(async () => {
  window.addEventListener('keydown', onShortcut)
  window.addEventListener('click', closeMenu)
  document.addEventListener('keydown', onEscapeMenu)
  void loadPrefs()
  try { const r = await http.get<{ data?: Array<{ name?: string; help?: string; group?: string }> }>('/api/commands'); commands.value = Array.isArray(r.data) ? r.data : [] } catch { commands.value = [] }
})
function onEscapeMenu(e: KeyboardEvent) { if (e.key === 'Escape') { closeMenu(); adminModal.value = null } }
onBeforeUnmount(() => { window.removeEventListener('keydown', onShortcut); window.removeEventListener('click', closeMenu); document.removeEventListener('keydown', onEscapeMenu) })
</script>
<template>
  <aside class="side">
    <button class="panel-hide" type="button" title="隐藏左侧栏" @click="sideHidden = true">‹</button>
    <div class="brand">
      <button v-if="railHidden" class="panel-expand" type="button" title="展开导航栏" @click="railHidden = false"><img src="@/assets/hoshinoumi.svg" alt="展开导航"></button>
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
      <button class="add-group" type="button" @click="newGroupOpen = true">＋ 群聊</button>
    </div>
    <div class="tabs">
      <button type="button" :class="{ on: tab === 'all' }" @click="tab = 'all'">全部</button>
      <button type="button" :class="{ on: tab === 'private' }" @click="tab = 'private'">私聊</button>
      <button type="button" :class="{ on: tab === 'group' }" @click="tab = 'group'">群聊</button><button type="button" :class="{ on: tab === 'mode' }" @click="tab = 'mode'">模式</button>
    </div>
    <div class="convs">
      <div v-if="session.loading" class="load">加载中…</div>
      <EmptyState v-else-if="session.conversationsError" :text="'未获取到 QQ 会话：' + session.conversationsError" />
      <EmptyState v-else-if="!filteredConversations.length" text="暂无 QQ 会话" />
      <template v-else>
        <div v-for="c in filteredConversations" :key="c.target_id" class="conv" :class="{ on: c.target_id === session.activeTarget, muted: isMuted(c) }" @click="choose(c.target_id)" @contextmenu="openMenu($event, c)">
          <QqAvatar class="avatar" :class="{ mode: c.type === 'mode' }" :group="c.type === 'group' ? c.target_id : ''" :qq="c.type === 'group' ? '' : botQq" :name="c.name || c.target_id" />
          <div class="body"><div class="nm">{{ c.name || c.target_id }}</div><div class="last"><template v-if="c.type === 'group'">群聊 · {{ c.member_count || 0 }} 人 · </template>{{ c.last_message || '暂无消息' }}</div></div>
          <span class="tm">{{ c.type === 'mode' ? 'MODE' : String(c.updated_at || '').slice(11, 16) }}</span>
          <span v-if="isMuted(c)" class="muted-mark" title="免打扰">⌾</span><span v-if="Number(c.unread || 0) > 0" class="unread">{{ Number(c.unread) > 99 ? '99+' : c.unread }}</span>
        </div>
      </template>
    </div>
    <div class="side-foot"><span class="dot" :class="{ off: !session.connected }"></span><span>{{ auth.qq || 'owner' }} · schema {{ session.status?.schema || '—' }}</span><span class="lat">{{ session.statusLatencyMs != null ? session.statusLatencyMs + 'ms' : (session.connected ? '在线' : '离线') }}</span><button type="button" class="logout" @click="logout">退出</button></div>
  </aside>
  <div v-if="convMenu" class="conv-menu" :style="{ left: convMenu.x + 'px', top: convMenu.y + 'px' }" @click.stop>
    <div class="mh">{{ convMenu.conv.name || convMenu.conv.target_id }}</div>
    <button type="button" @click="toggleMute(convMenu.conv)">{{ isMuted(convMenu.conv) ? '取消免打扰' : '免打扰' }}</button>
    <button type="button" @click="hideConversation(convMenu.conv)">隐藏会话</button>
    <button v-if="convMenu.conv.type === 'group'" type="button" @click="openAdmins(convMenu.conv)">管理员 / 撤回提示</button>
    <div class="sep" />
    <button type="button" class="danger" @click="deleteConversation(convMenu.conv)">{{ convMenu.conv.type === 'group' ? (String(convMenu.conv.target_id).startsWith('h_') ? '退出并解散群聊' : '退出群聊') : '删除联系人' }}</button>
  </div>
  <div v-if="adminModal" class="admin-mask" @click.self="adminModal = null">
    <div class="admin-modal">
      <header><b>群管理 · {{ adminModal.name || adminModal.target_id }}</b><button type="button" @click="adminModal = null">×</button></header>
      <div class="admin-row"><input v-model="adminQq" placeholder="QQ 号"><button type="button" @click="addAdmin(false)">设为管理员</button></div>
      <div class="admin-list"><span v-for="q in admins" :key="q">{{ q }} <button type="button" @click="adminQq = q; addAdmin(true)">移除</button></span><small v-if="!admins.length">暂无管理员</small></div>
      <label class="recall-field">撤回提示<input v-model="recallNotice" maxlength="200" placeholder="消息已撤回"><button type="button" @click="saveRecallNotice">保存</button></label>
      <p class="admin-hint">群主可设/撤管理员；管理员可撤回任意消息。当前为本地群管理数据。</p>
    </div>
  </div>
  <NewGroupModal :open="newGroupOpen" @close="newGroupOpen = false" @created="onGroupCreated" />
</template>
<style scoped>
.side{background:#f8fbff;border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0;position:relative}
.brand{padding:18px 42px 12px 18px;display:flex;align-items:center;gap:9px;font-size:12px;letter-spacing:.18em;color:#1e3a5f}.panel-expand{display:flex;width:26px;height:26px;border:0;border-radius:7px;background:transparent;cursor:pointer;align-items:center;justify-content:center;padding:0;flex:none}.panel-expand img{width:18px;height:18px;display:block}.panel-hide{position:absolute;right:10px;top:14px;width:22px;height:22px;border:0;border-radius:6px;background:transparent;color:#9aabc0;font:13px/1 inherit;cursor:pointer;z-index:5;padding:0;display:grid;place-items:center;transition:background .18s,color .18s}.panel-hide:hover{background:#eef4ff;color:#2563eb}.brand span{margin-left:auto;font-size:9px;color:#8a9bb0;border:1px solid #dbe8ff;background:#fff;border-radius:20px;padding:2px 7px;letter-spacing:0}
.searchbox{position:relative;margin:0 14px 12px}.search{height:34px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;display:flex;align-items:center;gap:7px;padding:0 10px;color:#8a9bb0;font-size:11px}.search input{flex:1;min-width:0;border:0;outline:0;background:none;color:#243b55;font:11px inherit}.search kbd{margin-left:auto;font:9px ui-monospace,monospace;border:1px solid #dbe8ff;border-radius:4px;padding:1px 4px}.search-panel{position:absolute;left:0;right:0;top:40px;z-index:12;background:#fff;border:1px solid #dbe8ff;border-radius:10px;box-shadow:0 12px 30px rgba(29,78,216,.14);padding:6px;max-height:320px;overflow:auto}.search-hint{padding:10px 8px;font-size:9.5px;color:#8a9bb0}.sr-sec{padding:6px 8px 3px;font-size:8px;letter-spacing:.12em;color:#9aabbe}.sr{display:block;width:100%;text-align:left;border:0;background:none;color:#243b55;font:10px inherit;padding:6px 8px;border-radius:6px;cursor:pointer}.sr:hover{background:#eef4ff}.sr small{display:block;color:#8a9bb0;font-size:8.5px;margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.slabel{font-size:9px;letter-spacing:.14em;color:#8a9bb0;text-transform:uppercase;padding:6px 18px;display:flex}.slabel em{margin-left:auto;font-style:normal;color:#1f9d6b;letter-spacing:0}.add-group{border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:6px;font:8.5px inherit;padding:2px 5px;margin-left:6px;cursor:pointer}
.tabs{display:flex;gap:4px;padding:0 14px 8px}.tabs button{flex:1;border:1px solid #e3ebf7;background:#fff;color:#8a9bb0;font:9.5px inherit;border-radius:7px;padding:4px 0;cursor:pointer}.tabs button.on{background:#eef4ff;border-color:#c7dcff;color:#1d4ed8}.convs{flex:1;overflow:auto;padding:0 8px;min-height:0}.conv{display:flex;gap:9px;padding:9px;border-radius:11px;position:relative;text-decoration:none;color:inherit;border:1px solid transparent;transition:background .18s,border-color .18s,transform .18s}.conv:hover{background:#eef4ff;border-color:#dbe8ff;transform:translateX(2px)}.conv.on{background:#e7f0ff;border-color:#c7dcff}
.avatar.mode{background:#f3efff;color:#6d4fd6;font-size:10px}.avatar{width:33px;height:33px;border-radius:10px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#1d4ed8;flex:none}
.body{min-width:0}.nm{font-size:12px;font-weight:600;color:#1e3a5f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.last{font-size:10.5px;color:#8a9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}.tm{font-size:9px;color:#8a9bb0;margin-left:auto;flex:none}.unread{position:absolute;right:8px;bottom:8px;min-width:15px;height:15px;border-radius:8px;background:#2563eb;color:#fff;font-size:9px;font-weight:700;display:grid;place-items:center}
.conn{margin:10px 14px 14px;padding:11px 12px;border:1px solid #e3ebf7;border-radius:12px;background:#fff}.conn .k{font-size:9px;letter-spacing:.08em;color:#8a9bb0;margin-bottom:5px;display:flex;align-items:center}.logout{margin-left:auto;border:1px solid #f0d7dd;background:#fff;color:#b23b52;border-radius:5px;padding:2px 6px;font:8.5px inherit;cursor:pointer}.logout:hover{background:#fff5f7}.conn .v{font-size:11px;color:#1f9d6b;display:flex;align-items:center;gap:6px}.dot{width:6px;height:6px;border-radius:50%;background:#1f9d6b}.dot.off{background:#c0264a}.load{padding:18px 12px;text-align:center;font-size:10px;color:#8a9bb0}.side-foot{height:33px;flex:none;margin-top:auto;border-top:1px solid #e3ebf7;display:flex;align-items:center;gap:5px;padding:0 14px;font-size:8.5px;color:#7d8fa6;background:#fbfdff}.side-foot .lat{margin-left:auto;font-family:ui-monospace,monospace;color:#93a4b8}.side-foot .dot{flex:none}.side-foot .logout{margin-left:2px}
.muted-mark{font-size:9px;color:#9aabc0;margin-left:auto}.conv-menu{position:fixed;z-index:70;width:168px;background:#fff;border:1px solid #dbe8ff;border-radius:10px;box-shadow:0 14px 34px rgba(15,35,70,.18);padding:5px}.conv-menu .mh{padding:5px 7px;font-size:8px;color:#9aabc0;border-bottom:1px solid #f1f5fb;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.conv-menu button{display:block;width:100%;text-align:left;border:0;background:none;border-radius:6px;padding:7px;font:9px inherit;color:#405872;cursor:pointer}.conv-menu button:hover{background:#eef4ff;color:#2563eb}.conv-menu button.danger{color:#b23b52}.conv-menu .sep{height:1px;background:#f1f5fb;margin:3px}.admin-mask{position:fixed;inset:0;z-index:80;background:#0f172a52;display:grid;place-items:center;padding:16px}.admin-modal{width:min(380px,100%);background:#fff;border-radius:13px;padding:14px;box-shadow:0 24px 60px #0f264e3d}.admin-modal header{display:flex;align-items:center}.admin-modal header b{font-size:12px;color:#1e3a5f}.admin-modal header button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:17px;cursor:pointer}.admin-row{display:flex;gap:5px;margin:9px 0}.admin-row input{flex:1;height:28px;border:1px solid #dbe8ff;border-radius:6px;font:9px inherit;padding:0 7px}.admin-row button,.admin-list button,.recall-field button{border:1px solid #dbe8ff;border-radius:6px;background:#f8fbff;color:#2563eb;font:8px inherit;padding:4px 7px;cursor:pointer}.admin-list{display:flex;flex-wrap:wrap;gap:4px;font-size:8px;color:#526982}.admin-list span{display:flex;align-items:center;gap:3px;border:1px solid #e3ebf7;border-radius:6px;padding:3px 5px}.recall-field{display:flex;gap:5px;align-items:center;margin-top:10px;font-size:8px;color:#8a9bb0}.recall-field input{flex:1;min-width:0;height:27px;border:1px solid #dbe8ff;border-radius:6px;font:9px inherit;padding:0 7px}.admin-hint{font-size:7px;color:#9aabc0;line-height:1.5;margin:9px 0 0}
</style>
