<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
const relationProgress = computed(() => {
  const tier = String(session.relation?.tier || '')
  const map: Record<string, number> = { '陌生': 12, '认识': 28, '熟': 45, '亲近': 65, '知己': 82, '搭档': 92 }
  return map[tier] ?? (tier ? 50 : 0)
})
</script>
<template>
  <aside class="context">
    <div v-if="session.persona" class="pcard">
      <div class="biga">{{ String(session.persona.name || '?').slice(0,1) }}</div>
      <div><div class="name">{{ session.persona.name || '未命名人设' }}</div><div class="tag">{{ session.relation?.tier ? '关系 · ' + session.relation.tier : '人设已加载' }}</div></div>
      <span class="state" :class="{ off: !session.connected }" />
    </div>
    <div v-else class="pcard empty-card">未获取到人设</div>
    <div class="sec">
      关系
    </div>
    <div v-if="session.relation" class="rel-head">
      <span>关系档位</span><b>{{ session.relation.tier || '未获取' }}</b>
    </div>
    <div v-if="session.relation" class="track"><i :style="{ width: relationProgress + '%' }"></i></div>
    <div v-else class="note">
      {{ session.error ? '未获取到关系数据：' + session.error : '暂无关系数据' }}
    </div>
    <div class="sec">
      她的状态
    </div>
    <div v-if="session.lifeState" class="life">
      <div class="row"><span>心情</span><b>{{ session.lifeState.emotion ?? session.lifeState.mood ?? '未知' }}</b></div>
      <div class="row"><span>精力</span><b>{{ session.lifeState.energy ?? '未知' }}</b></div>
      <div class="row"><span>孤独</span><b>{{ session.lifeState.lonely ?? '未知' }}</b></div>
      <div class="row"><span>正在</span><b>{{ session.presence?.activity && session.presence.activity !== 'unknown' ? session.presence.activity : '未上报' }}</b></div>
    </div>
    <div v-else class="note">
      {{ session.connected ? '未获取到 state / presence' : '未连接后端' }}
    </div>
    <div class="sec">
      快捷
    </div>
    <div class="quick">
      <div class="q"><b>存钱</b>{{ session.savings ? '¥' + (Number(session.savings.total_cents || 0) / 100).toFixed(2) : '未获取' }}</div>
      <div class="q"><b>记忆</b>{{ session.memoryTargets.length ? session.memoryTargets.length + ' 个会话' : '未获取' }}</div>
      <div class="q"><b>周计划</b>{{ session.weekly ? '第 ' + (session.weekly.week || session.week) + ' 周 · ' + ((session.weekly.courses as unknown[]) || []).length + ' 门课' : '未获取' }}</div>
      <div class="q"><b>人设</b>{{ session.persona?.name || '未获取' }}</div>
    </div>
  </aside>
</template>
<style scoped>
.context{border-left:1px solid var(--line);background:#f8fbff;padding:16px 15px;overflow:auto}
.pcard.empty-card{color:#8a9bb0;font-size:11px;justify-content:center}
.pcard{border:1px solid #e3ebf7;border-radius:14px;background:#fff;padding:13px;display:flex;gap:11px;align-items:center}.biga{width:44px;height:44px;border-radius:14px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:16px;font-weight:800}.name{font-size:13px;font-weight:650}.tag{font-size:9.5px;color:#6b7c95;margin-top:2px}.state{margin-left:auto;width:7px;height:7px;border-radius:50%;background:#1f9d6b}.state.off{background:#c0264a}
.sec{font-size:9px;letter-spacing:.13em;color:#8a9bb0;text-transform:uppercase;margin:17px 2px 8px}.rel-head{display:flex;align-items:center;justify-content:space-between;font-size:10px;color:#6b7c95;margin-bottom:5px}.rel-head b{font-size:11px;color:#2563eb}.rel-head em{font-style:normal;font-size:9px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 4px;margin-left:3px}
.track{height:4px;border-radius:4px;background:#e8effa;overflow:hidden}.track i{display:block;height:100%;background:#2563eb;border-radius:4px;transition:width .5s}.rel-meta{font-size:9px;color:#8a9bb0;margin-top:5px;display:flex;justify-content:space-between}.rel-meta span{color:#4b5f78}
.life{display:flex;flex-direction:column;gap:6px}.life .row{display:flex;justify-content:space-between;font-size:10px;color:#6b7c95}.life .row b{color:#1e3a5f;font-weight:500}.note{font-size:8.5px;color:#9aabbe;margin-top:5px}
.quick{display:grid;grid-template-columns:1fr 1fr;gap:7px}.quick .q{border:1px solid #e3ebf7;border-radius:9px;background:#fff;padding:8px;font-size:9.5px;color:#6b7c95}.quick .q b{display:block;color:#1e3a5f;font-size:10.5px;margin-bottom:1px}
</style>
