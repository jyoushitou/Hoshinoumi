<script setup lang="ts">
const chats = [
  { id: 'nao', name: '友利奈绪', last: '今天也一起加油吧', time: '21:04', unread: 2, avatar: '奈', color: '#dbeafe' },
  { id: 'seagroup', name: '星之海学园', last: '[图片] 晚上的教室', time: '20:41', unread: 0, avatar: '星', color: '#d1fae5' },
  { id: 'student', name: '学生会室', last: '明天放学后开个短会', time: '19:58', unread: 5, avatar: '学', color: '#ffedd5' },
  { id: 'photo', name: '摄影部', last: '周末去海边拍吗', time: '昨天', unread: 0, avatar: '摄', color: '#ede9fe' },
  { id: 'test', name: 'NapCat 测试群', last: '消息同步测试', time: '昨天', unread: 0, avatar: '测', color: '#fde8d7' },
]
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
      QQ 会话 <em>同步中</em>
    </div>
    <div class="convs">
      <RouterLink
        v-for="c in chats"
        :key="c.id"
        :to="'/chat'"
        class="conv"
        :class="{ on: c.id === 'nao' }"
      >
        <span
          class="avatar"
          :style="{ background: c.color }"
        >{{ c.avatar }}</span>
        <div class="body">
          <div class="nm">
            {{ c.name }}
          </div><div class="last">
            {{ c.last }}
          </div>
        </div>
        <span class="tm">{{ c.time }}</span>
        <span
          v-if="c.unread"
          class="unread"
        >{{ c.unread }}</span>
      </RouterLink>
    </div>
    <div class="conn">
      <div class="k">
        后端连接
      </div><div class="v">
        <span class="dot" /> 已连接 · schema 35
      </div><div class="meta">
        127.0.0.1:27004 · 42ms · owner
      </div>
    </div>
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
.conn{margin:10px 14px 14px;padding:11px 12px;border:1px solid #e3ebf7;border-radius:12px;background:#fff}.conn .k{font-size:9px;letter-spacing:.08em;color:#8a9bb0;margin-bottom:5px}.conn .v{font-size:11px;color:#1f9d6b;display:flex;align-items:center;gap:6px}.dot{width:6px;height:6px;border-radius:50%;background:#1f9d6b}.conn .meta{font-size:9.5px;color:#8a9bb0;margin-top:4px}
</style>
