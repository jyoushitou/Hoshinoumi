<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'
const session = useSessionStore()
const auth = useAuthStore()
const isOwner = useIsOwner()
const modules = [
  { path: '/chat', icon: '◉', label: '聊天', desc: '会话 / 消息' },
  { path: '/memory', icon: '◈', label: '记忆', desc: '记忆本 / 事件' },
  { path: '/relation', icon: '♡', label: '关系', desc: '档位 / 变化' },
  { path: '/savings', icon: '¥', label: '存钱', desc: '账户 / 目标' },
  { path: '/weekly', icon: '▦', label: '周计划', desc: '节次 / 时间' },
  { path: '/info', icon: '≡', label: '信息', desc: '运行 / 配置' },
  { path: '/persona', icon: '◇', label: '人设', desc: '导入 / 激活' },
  { path: '/commands', icon: '⌘', label: '命令', desc: '浏览 / 执行' },
  { path: '/cron', icon: '◷', label: '定时任务', desc: '启停 / 运行' },
  { path: '/logs', icon: '≣', label: '运行日志', desc: '筛选 / 搜索' },
]
const visibleModules = computed(() => isOwner.value ? modules : modules.filter(item => item.path !== '/relation' && item.path !== '/savings'))
const hour = new Date().getHours()
const greeting = computed(() => hour < 6 ? '夜深了' : hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好')
</script>

<template>
  <section class="home">
    <header class="hero">
      <div><p>{{ greeting }} · {{ auth.qq || '主人' }}</p><h1>今天也慢慢来。</h1><span>{{ session.connected ? '后端已连接 · 记忆同步中' : '后端离线 · 部分功能不可用' }}</span></div>
      <div class="hero-stats"><div><small>schema</small><b>{{ session.status?.schema || '—' }}</b></div><div><small>延迟</small><b>{{ session.statusLatencyMs != null ? session.statusLatencyMs + 'ms' : '—' }}</b></div><div><small>未读</small><b>{{ session.unread }}</b></div></div>
    </header>
    <div class="section-title"><b>功能模块</b><span>{{ visibleModules.length }} 个入口</span></div>
    <div class="module-grid">
      <RouterLink v-for="item in visibleModules" :key="item.path" :to="item.path" class="module">
        <span class="icon">{{ item.icon }}</span>
        <div><b>{{ item.label }}</b><small>{{ item.desc }}</small></div>
        <em>›</em>
      </RouterLink>
    </div>
    <div class="tip"><b>提示</b><span>页面只走导航，不塞进 QQ 会话列表；数据全部来自后端。</span><RouterLink to="/info">查看运行信息</RouterLink></div>
  </section>
</template>

<style scoped>
.home{flex:1;min-height:0;overflow:auto;padding:24px 28px 28px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.hero{display:flex;align-items:flex-end;gap:12px;background:linear-gradient(135deg,#eff6ff,#fff);border:1px solid #dbe8ff;border-radius:14px;padding:18px 19px;margin-bottom:14px}.hero p{margin:0;font-size:9px;color:#8a9bb0;letter-spacing:.04em}.hero h1{margin:5px 0 4px;font-size:26px;letter-spacing:-.03em}.hero span{font-size:9px;color:#7d8ca3}.hero-stats{margin-left:auto;display:flex;gap:18px}.hero-stats small{display:block;font-size:7px;color:#9aabc0;letter-spacing:.08em}.hero-stats b{display:block;font-size:15px;color:#1d4ed8;margin-top:3px}.section-title{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px}.section-title b{font-size:11px;color:#314a65}.section-title span{font-size:8px;color:#9aabc0}.module-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.module{display:flex;align-items:center;gap:8px;text-decoration:none;background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:11px 10px;transition:border-color .18s,transform .18s,box-shadow .18s}.module:hover{border-color:#bcd4f7;transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.06)}.icon{width:29px;height:29px;border-radius:8px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:14px;flex:none}.module b{display:block;font-size:10px;color:#1e3a5f}.module small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.module em{margin-left:auto;font-style:normal;font-size:13px;color:#c7d3e3}.tip{display:flex;align-items:center;gap:8px;margin-top:14px;border:1px dashed #cfe0f7;border-radius:9px;background:#f8fbff;padding:9px 11px;font-size:8px;color:#8a9bb0;line-height:1.6}.tip b{color:#526982}.tip a{margin-left:auto;color:#2563eb;text-decoration:none;white-space:nowrap}
@media(max-width:1180px){.module-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:820px){.home{padding:16px 14px 20px}.hero{padding:14px}.hero h1{font-size:22px}.hero-stats{gap:10px}.module-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tip{flex-wrap:wrap}.tip a{margin-left:0}}
</style>
