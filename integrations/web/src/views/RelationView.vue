<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'
const session = useSessionStore()
const auth = useAuthStore()
const router = useRouter()
const isOwner = useIsOwner()
onMounted(() => {
  if (!auth.loggedIn) void router.replace('/chat')
  else if (session.status && !isOwner.value) void router.replace('/chat')
})
const tier = computed(() => String(session.relation?.tier || '未获取'))
const description = computed(() => String(session.relation?.description || '暂未获取到关系描述'))
const recent = computed(() => {
  const events = Array.isArray(session.relation?.events) ? session.relation.events as Array<Record<string, unknown>> : []
  return events[0]?.reason ? String(events[0].reason) : '暂无最近变化'
})
const progress = computed(() => {
  const map: Record<string, number> = { '陌生': 12, '认识': 28, '熟': 45, '亲近': 65, '知己': 82, '搭档': 92 }
  return map[tier.value] ?? (session.relation ? 50 : 0)
})
</script>
<template>
  <div v-if="isOwner" class="page">
    <div class="head"><div><h1>关系</h1><p>仅 owner 可见 · 不显示具体数值</p></div><RouterLink to="/chat" class="back">← 返回聊天</RouterLink></div>
    <div v-if="session.relation" class="grid">
      <section class="card wide"><div class="k">关系档位</div><div class="tier">{{ tier }}</div><div class="bar"><i :style="{ width: progress + '%' }" /></div><div class="note">{{ description }}</div></section>
      <section class="card"><div class="k">最近变化</div><div class="v">{{ recent }}</div><div class="note">不展示具体增减数值</div></section>
      <section class="card"><div class="k">可见范围</div><div class="v">仅 owner 全量</div><div class="note">普通用户只能查看自己的关系</div></section>
      <section class="card wide"><div class="k">关系事件</div><div v-if="Array.isArray(session.relation.events) && session.relation.events.length" class="events"><div v-for="(e, i) in (session.relation.events as Array<Record<string, unknown>>)" :key="i" class="event"><span>{{ e.reason || '关系变化' }}</span><small>{{ String(e.created_at || '').slice(0, 16) }}</small></div></div><div v-else class="note">暂无关系事件</div></section>
    </div>
    <div v-else class="empty">{{ session.error ? '未获取到关系数据：' + session.error : '未连接后端，暂无关系数据' }}</div>
  </div>
</template>
<style scoped>
.page{padding:22px 24px;overflow:auto;flex:1;background:#fff}.head{display:flex;align-items:center;gap:12px;margin-bottom:16px}.head h1{font-size:20px;margin:0;color:#17263b}.head p{font-size:10.5px;color:#6b7c95;margin:4px 0 0}.back{margin-left:auto;font-size:10px;color:#2563eb;border:1px solid #dbe8ff;border-radius:8px;padding:5px 9px;text-decoration:none;background:#fff}.grid{display:grid;grid-template-columns:1.6fr 1fr;gap:10px}.card{border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:14px}.wide{grid-column:span 2}.k{font-size:9px;letter-spacing:.12em;color:#8a9bb0;text-transform:uppercase}.tier{font-size:21px;font-weight:700;color:#2563eb;margin:7px 0 8px}.bar{height:5px;border-radius:5px;background:#e8effa;overflow:hidden}.bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#6ea4ff,#2563eb);transition:width .45s}.v{font-size:13px;color:#1e3a5f;margin:8px 0 4px}.note{font-size:9.5px;color:#8a9bb0;margin-top:6px;line-height:1.6}.events{display:grid;gap:0}.event{display:flex;justify-content:space-between;border-bottom:1px solid #f1f5fb;padding:7px 0;font-size:10px;color:#405872}.event:last-child{border-bottom:0}.event small{color:#8a9bb0}.empty{border:1px dashed #cfe0f7;border-radius:12px;background:#f8fbff;padding:32px;text-align:center;color:#6b7c95;font-size:11px}
</style>
