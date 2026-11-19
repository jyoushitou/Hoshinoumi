<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
</script>
<template>
  <aside class="context">
    <div class="pcard">
      <div class="biga">
        奈
      </div><div>
        <div class="name">
          友利奈绪
        </div><div class="tag">
          亲近 · 知己 · 搭档
        </div>
      </div><span class="state" />
    </div>
    <div class="sec">
      关系
    </div>
    <div v-if="session.error" class="note">
      未获取到关系数据：{{ session.error }}
    </div>
    <div v-else class="note">
      暂无关系数据
    </div>
    <div class="sec">
      她的状态
    </div>
    <div class="note">
      未获取到 state / presence
    </div>
    <div class="sec">
      快捷
    </div>
    <div class="quick">
      <div class="q">
        <b>存钱</b>本月流水
      </div><div class="q">
        <b>记忆</b>最近 7 天
      </div><div class="q">
        <b>周计划</b>第 12 周
      </div><div class="q">
        <b>人设</b>nao · 当前
      </div>
    </div>
  </aside>
</template>
<style scoped>
.context{border-left:1px solid var(--line);background:#f8fbff;padding:16px 15px;overflow:auto}
.pcard{border:1px solid #e3ebf7;border-radius:14px;background:#fff;padding:13px;display:flex;gap:11px;align-items:center}.biga{width:44px;height:44px;border-radius:14px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:16px;font-weight:800}.name{font-size:13px;font-weight:650}.tag{font-size:9.5px;color:#6b7c95;margin-top:2px}.state{margin-left:auto;width:7px;height:7px;border-radius:50%;background:#1f9d6b}
.sec{font-size:9px;letter-spacing:.13em;color:#8a9bb0;text-transform:uppercase;margin:17px 2px 8px}.rel-head{display:flex;align-items:center;justify-content:space-between;font-size:10px;color:#6b7c95;margin-bottom:5px}.rel-head b{font-size:11px;color:#2563eb}.rel-head em{font-style:normal;font-size:9px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:4px;padding:1px 4px;margin-left:3px}
.track{height:4px;border-radius:4px;background:#e8effa;overflow:hidden}.track i{display:block;height:100%;background:#2563eb;border-radius:4px}.rel-meta{font-size:9px;color:#8a9bb0;margin-top:5px;display:flex;justify-content:space-between}.rel-meta span{color:#4b5f78}
.life{display:flex;flex-direction:column;gap:6px}.life .row{display:flex;justify-content:space-between;font-size:10px;color:#6b7c95}.life .row b{color:#1e3a5f;font-weight:500}.note{font-size:8.5px;color:#9aabbe;margin-top:5px}
.quick{display:grid;grid-template-columns:1fr 1fr;gap:7px}.quick .q{border:1px solid #e3ebf7;border-radius:9px;background:#fff;padding:8px;font-size:9.5px;color:#6b7c95}.quick .q b{display:block;color:#1e3a5f;font-size:10.5px;margin-bottom:1px}
</style>
