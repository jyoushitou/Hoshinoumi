<script setup lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
const router = useRouter()
async function choose(target: string) { await session.selectConversation(target); router.push('/chat') }
</script>
<template>
  <aside class="side">
    <div class="brand">
      <b>HOSHINOUMI</b><span>WEB v35.5</span>
    </div>
    <div class="search">
      ⌕ 搜索会话 / 记忆 / 命令 <kbd>⌘K</kbd>
    </div>
    <div class="slabel">
      QQ 会话 <em>{{ session.connected ? '同步中' : '未同步' }}</em>
    </div>
    <div class="convs">
      <div v-if="session.loading" class="load">加载中…</div>
      <EmptyState v-else-if="session.conversationsError" :text="'未获取到 QQ 会话：' + session.conversationsError" />
      <EmptyState v-else-if="!session.conversations.length" text="暂无 QQ 会话" />
      <template v-else>
        <div v-for="c in session.conversations" :key="c.target_id" class="conv" :class="{ on: c.target_id === session.activeTarget }" @click="choose(c.target_id)">
          <span class="avatar">{{ String(c.name || c.target_id).slice(0, 1) }}</span>
          <div class="body"><div class="nm">{{ c.name || c.target_id }}</div><div class="last">{{ c.last_message || '暂无消息' }}</div></div>
          <span class="tm">{{ String(c.updated_at || '').slice(11, 16) }}</span>
        </div>
      </template>
    </div>
    <div class="conn"><div class="k">后端连接</div><div class="v"><span class="dot" :class="{ off: !session.connected }"></span> {{ session.connected ? '已连接' : '未连接' }}</div><div class="meta">{{ session.error || '等待后端数据' }}</div></div>
  </aside>
</template>
<style scoped>
.side{background:#f8fbff;border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.brand{padding:18px 18px 12px;display:flex;align-items:center;gap:9px;font-size:12px;letter-spacing:.18em;color:#1e3a5f}.brand span{margin-left:auto;font-size:9px;color:#8a9bb0;border:1px solid #dbe8ff;background:#fff;border-radius:20px;padding:2px 7px;letter-spacing:0}
.search{margin:0 14px 12px;height:34px;border:1px solid #e3ebf7;border-radius:10px;background:#fff;display:flex;align-items:center;gap:7px;padding:0 10px;color:#8a9bb0;font-size:11px}.search kbd{margin-left:auto;font:9px ui-monospace,monospace;border:1px solid #dbe8ff;border-radius:4px;padding:1px 4px}
.slabel{font-size:9px;letter-spacing:.14em;color:#8a9bb0;text-transform:uppercase;padding:6px 18px;display:flex}.slabel em{margin-left:auto;font-style:normal;color:#1f9d6b;letter-spacing:0}
.convs{overflow:auto;padding:0 8px;min-height:0}.conv{display:flex;gap:9px;padding:9px;border-radius:11px;position:relative;text-decoration:none;color:inherit;border:1px solid transparent;transition:background .18s,border-color .18s,transform .18s}.conv:hover{background:#eef4ff;border-color:#dbe8ff;transform:translateX(2px)}.conv.on{background:#e7f0ff;border-color:#c7dcff}
.avatar{width:33px;height:33px;border-radius:10px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#1d4ed8;flex:none}
.body{min-width:0}.nm{font-size:12px;font-weight:600;color:#1e3a5f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.last{font-size:10.5px;color:#8a9bb0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}.tm{font-size:9px;color:#8a9bb0;margin-left:auto;flex:none}.unread{position:absolute;right:8px;bottom:8px;min-width:15px;height:15px;border-radius:8px;background:#2563eb;color:#fff;font-size:9px;font-weight:700;display:grid;place-items:center}
.conn{margin:10px 14px 14px;padding:11px 12px;border:1px solid #e3ebf7;border-radius:12px;background:#fff}.conn .k{font-size:9px;letter-spacing:.08em;color:#8a9bb0;margin-bottom:5px}.conn .v{font-size:11px;color:#1f9d6b;display:flex;align-items:center;gap:6px}.dot{width:6px;height:6px;border-radius:50%;background:#1f9d6b}.dot.off{background:#c0264a}.load{padding:18px 12px;text-align:center;font-size:10px;color:#8a9bb0}.conn .meta{font-size:9.5px;color:#8a9bb0;margin-top:4px}
</style>
