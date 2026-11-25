<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import { useUiSettings } from '@/composables/useUiSettings'

const auth = useAuthStore()
const session = useSessionStore()
const { hiddenPages, hiddenCount, isHidden, togglePage, resetPages, motion } = useUiSettings()
const testing = ref(false)
const testResult = ref('')
const testOk = ref(false)
const testLatency = ref<number | null>(null)
const pages = [
  { key: 'home', label: '主页' }, { key: 'memory', label: '记忆' }, { key: 'relation', label: '关系' },
  { key: 'savings', label: '存钱' }, { key: 'weekly', label: '周计划' }, { key: 'info', label: '信息' },
  { key: 'persona', label: '人设' }, { key: 'commands', label: '命令' }, { key: 'cron', label: '定时任务' },
  { key: 'diary', label: '日记' }, { key: 'logs', label: '运行日志' },
]
const apiBase = computed(() => (http as unknown as { baseUrl?: string }).baseUrl || window.location.origin)
const maskedToken = computed(() => auth.token ? auth.token.slice(0, 4) + '••••' + auth.token.slice(-3) : '未设置')
async function testConnection() {
  testing.value = true; testResult.value = ''; testLatency.value = null
  const started = performance.now()
  try {
    await http.get('/healthz')
    testOk.value = true
    testLatency.value = Math.round(performance.now() - started)
    testResult.value = `连接成功 · ${testLatency.value}ms`
  } catch {
    testOk.value = false
    testResult.value = '连接失败，请检查后端地址和 token'
  } finally { testing.value = false }
}
function logout() { auth.logout(); window.location.href = '/chat' }
onMounted(() => { if (auth.loggedIn) void auth.validate() })
</script>

<template>
  <section class="settings-page">
    <header class="head"><div><h1>设置</h1><p>账号 / 后端连接 / 页面可见性 / 动画</p></div><span class="status" :class="{ off: !session.connected }">{{ session.connected ? '后端已连接' : '后端离线' }}</span></header>
    <div class="grid">
      <div class="panel account">
        <div class="panel-title">账号 <span>owner</span></div>
        <div class="account-row"><span class="avatar">J</span><div><b>{{ auth.qq || '未登录' }}</b><small>{{ auth.loggedIn ? '主人账号 · 已登录' : '未登录' }}</small></div><button type="button" @click="logout">退出</button></div>
        <div class="rows"><div><span>权限</span><b>主人 · 全量</b></div><div><span>schema</span><b>{{ session.status?.schema || '—' }}</b></div><div><span>后端版本</span><b>{{ session.status?.version || '—' }}</b></div></div>
      </div>
      <div class="panel backend">
        <div class="panel-title">后端连接 <span :class="{ 'is-ok': testOk, 'is-bad': testResult && !testOk }">{{ testResult ? (testOk ? '● 已连接' : '● 连接失败') : '当前站点' }}</span></div>
        <div class="rows"><div><span>API 地址</span><b class="mono">{{ apiBase }}</b></div><div><span>访问 token</span><b class="mono">{{ maskedToken }}</b></div><div><span>延迟</span><b>{{ session.statusLatencyMs != null ? session.statusLatencyMs + 'ms' : '—' }}</b></div></div>
        <button class="test" type="button" :disabled="testing" @click="testConnection">{{ testing ? '测试中…' : (testResult ? '重新测试' : '测试连接') }}</button>
        <div v-if="testResult" class="test-result" :class="{ ok: testOk }"><b>{{ testOk ? '✓ 连接成功' : '× 连接失败' }}</b><span>{{ testResult }}</span></div>
      </div>
      <div class="panel visibility">
        <div class="panel-title">页面可见性 <span>隐藏 {{ hiddenCount }} 个</span></div>
        <p class="desc">隐藏后左侧导航不再显示入口，设置页和聊天不可隐藏。</p>
        <div class="page-grid"><button v-for="page in pages" :key="page.key" type="button" class="page-toggle" :class="{ on: !isHidden(page.key) }" @click="togglePage(page.key)"><span>{{ page.label }}</span><em>{{ isHidden(page.key) ? '隐藏' : '显示' }}</em></button></div>
        <button class="reset" type="button" @click="resetPages">恢复全部显示</button>
      </div>
      <div class="panel motion">
        <div class="panel-title">外观 <span>本机偏好</span></div>
        <div class="setting-row"><div><b>页面动画</b><small>关闭后移除过渡与入场动画</small></div><button class="switch" :class="{ on: motion }" type="button" role="switch" :aria-checked="motion" @click="motion = !motion"><i></i></button></div>
        <div class="about"><RouterLink to="/info">查看运行信息</RouterLink><span>·</span><a href="https://github.com/jyoushitou/Hoshinoumi" target="_blank" rel="noopener">GitHub</a><span>·</span><a href="https://github.com/jyoushitou" target="_blank" rel="noopener">作者 jyoushitou</a></div>
        <div class="powered">POWERED BY JYOUSHITOU</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.settings-page{flex:1;min-height:0;overflow:auto;padding:22px 24px 26px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.status{margin-left:auto;font-size:8px;color:#168b63;border:1px solid #cdeee0;background:#eefbf5;border-radius:9px;padding:3px 7px}.status.off{color:#8a9bb0;border-color:#e3ebf7;background:#f8fbff}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start}.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px}.panel-title{display:flex;justify-content:space-between;font-size:10px;font-weight:700;color:#314a65;margin-bottom:9px}.panel-title span{font-weight:400;font-size:8px;color:#9aabc0}.account-row{display:flex;align-items:center;gap:9px;padding-bottom:9px;border-bottom:1px solid #f1f5fb}.avatar{width:34px;height:34px;border-radius:9px;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-size:13px;font-weight:700}.account-row b{display:block;font-size:11px;color:#1e3a5f}.account-row small{display:block;font-size:8px;color:#9aabc0;margin-top:2px}.account-row button{margin-left:auto;height:26px;border:1px solid #f0d7dd;border-radius:6px;background:#fff7f9;color:#b23b52;font:8px inherit;padding:0 8px;cursor:pointer}.rows{padding-top:6px}.rows div{display:flex;justify-content:space-between;gap:8px;padding:5px 0;font-size:8.5px;color:#8a9bb0}.rows b{color:#314a65;font-weight:500;text-align:right;word-break:break-all}.rows b.mono{font:8px ui-monospace,monospace}.test{width:100%;height:29px;margin-top:7px;border:1px solid #dbe8ff;border-radius:7px;background:#f4f9ff;color:#2563eb;font:9px inherit;cursor:pointer}.test:disabled{opacity:.55}.test-result{display:flex;align-items:center;gap:7px;margin-top:6px;border-radius:7px;padding:7px 9px;font-size:8.5px;line-height:1.5;border:1px solid #fecaca;border-left:3px solid #dc2626;background:#fff5f5;color:#b91c1c}.test-result b{font-size:9px;font-weight:700}.test-result span{color:#b91c1c;opacity:.85}.test-result.ok{border-color:#cdeee0;border-left-color:#168b63;background:#eefbf5;color:#168b63}.test-result.ok span{color:#168b63}.panel-title span.is-ok{color:#168b63;font-weight:700}.panel-title span.is-bad{color:#b91c1c;font-weight:700}
.desc{font-size:8px;color:#9aabc0;line-height:1.6;margin:0 0 8px}.page-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}.page-toggle{display:flex;justify-content:space-between;align-items:center;height:28px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;color:#9aabc0;font:8.5px inherit;padding:0 8px;cursor:pointer}.page-toggle.on{border-color:#dbe8ff;background:#fff;color:#405872}.page-toggle em{font-style:normal;font-size:7.5px;color:#9aabc0}.page-toggle.on em{color:#168b63}.reset{width:100%;height:27px;margin-top:7px;border:1px solid #e3ebf7;border-radius:7px;background:#fff;color:#6b7c95;font:8px inherit;cursor:pointer}
.setting-row{display:flex;align-items:center;gap:9px;padding:5px 0}.setting-row b{display:block;font-size:9.5px;color:#314a65}.setting-row small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.switch{position:relative;flex:none;width:38px;height:22px;margin-left:auto;border:0;border-radius:11px;background:#cbd5e1;cursor:pointer;transition:background .2s}.switch.on{background:#2563eb}.switch i{position:absolute;left:2px;top:2px;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(15,23,42,.18);transition:left .2s}.switch.on i{left:18px}
.about{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-top:12px;font-size:8px}.about a{color:#2563eb;text-decoration:none}.about span{color:#c7d3e3}.powered{text-align:center;margin-top:8px;font:7px ui-monospace,monospace;letter-spacing:.12em;color:#a8b5c7}
@media(max-width:1180px){.settings-page{padding:18px 18px 22px}.grid{grid-template-columns:1fr}}
</style>
