<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileNav } from '@/composables/useMobileNav'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'
import { http } from '@/api/client'
import { useUiSettings } from '@/composables/useUiSettings'

const router = useRouter()
const auth = useAuthStore()
const isOwner = useIsOwner()
const apkVersion = ref('Web 预览')
const backendVersion = ref('—')
interface UpdateManifest { version?: string; versionCode?: number; size?: number; sha256?: string; notes?: string; url?: string; available?: boolean }
const latest = ref<UpdateManifest | null>(null)
const updateState = ref<'idle' | 'checking' | 'available' | 'downloading' | 'latest' | 'complete' | 'error'>('idle')
const downloadPercent = ref(0)
let downloadTimer: ReturnType<typeof setInterval> | null = null
const updateError = ref('')
const updateUrl = computed(() => latest.value?.url ? new URL(latest.value.url, location.origin).href : '')
const apkVersionOnly = computed(() => (apkVersion.value.match(/\d+\.\d+\.\d+\.\d+/) || [''])[0])
const consistency = computed(() => {
  if (!latest.value?.version) return '—'
  if (!apkVersionOnly.value) return '浏览器预览'
  return apkVersionOnly.value === latest.value.version ? '客户端与包一致' : '客户端待更新'
})
const { entries, quickKeys, toggleQuick, resetQuick } = useMobileNav()
const { navHidden, navBall, hiddenPages, togglePage } = useUiSettings()
const visibilityEntries = computed(() => entries.value.filter(entry => !['settings', 'chats'].includes(entry.key)))
const visibleEntries = computed(() => isOwner.value ? entries.value : entries.value.filter(entry => entry.key !== 'relation' && entry.key !== 'savings'))
const message = computed(() => `${quickKeys.value.length} / 5`)
const quickLabel = computed(() => quickKeys.value.map(key => entries.value.find(entry => entry.key === key)?.label).filter(Boolean).join(' / '))

onMounted(async () => {
  try {
    const bridge = (window as any).HoshinoumiConfig
    if (bridge?.getEnvironment) {
      const env = JSON.parse(bridge.getEnvironment())
      apkVersion.value = `${env.appVersion || '—'}${env.versionCode ? ` (${env.versionCode})` : ''}`
    }
  } catch { /* web preview */ }
  try {
    const status = await http.get<{ version?: string; schema?: number }>('/api/status')
    backendVersion.value = status.version || (status.schema ? `schema ${status.schema}` : '—')
  } catch { backendVersion.value = '未连接' }
})
function versionParts(value?: string) { return String(value || '').replace(/^v/i, '').split(/[.\-]/).map(part => Number(part) || 0) }
function isNewer(remote?: string, current?: string) {
  const a = versionParts(remote), b = versionParts(current)
  for (let i = 0; i < Math.max(a.length, b.length); i++) if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0)
  return false
}
async function checkUpdate() {
  updateState.value = 'checking'; updateError.value = ''
  try {
    const r = await http.get<{ data?: UpdateManifest }>('/api/app/update?platform=android')
    latest.value = r.data || null
    const bridge = (window as any).HoshinoumiConfig
    const current = bridge?.getEnvironment ? JSON.parse(bridge.getEnvironment()).appVersion : (backendVersion.value === '—' ? apkVersion.value : backendVersion.value)
    if (!latest.value?.available || !isNewer(latest.value.version, current)) { updateState.value = 'latest'; return }
    if (bridge?.downloadApk) {
      updateState.value = 'downloading'
      bridge.downloadApk(updateUrl.value)
      startProgress()
    } else {
      updateState.value = 'available'
    }
  } catch (e) { updateState.value = 'error'; updateError.value = e instanceof Error ? e.message : '检查更新失败' }
}
function stopProgress() { if (downloadTimer) { clearInterval(downloadTimer); downloadTimer = null } }
function startProgress() {
  stopProgress()
  downloadTimer = setInterval(() => {
    try {
      const bridge = (window as any).HoshinoumiConfig
      if (!bridge?.getDownloadStatus) return
      const state = JSON.parse(bridge.getDownloadStatus())
      const total = Number(state.total || 0), done = Number(state.downloaded || 0)
      if (total > 0) downloadPercent.value = Math.max(1, Math.min(99, Math.round(done / total * 100)))
      if (state.status === 'complete') { downloadPercent.value = 100; updateState.value = 'complete'; stopProgress() }
      else if (state.status === 'failed') { updateState.value = 'error'; updateError.value = '下载失败，可重新下载'; stopProgress() }
    } catch { /* bridge 不可用时只显示系统通知 */ }
  }, 900)
}
function retryDownload() { if (updateUrl.value) { updateState.value = 'downloading'; downloadPercent.value = 0; (window as any).HoshinoumiConfig?.downloadApk?.(updateUrl.value); startProgress() } }
onBeforeUnmount(stopProgress)
function toggle(key: string) { toggleQuick(key) }
function logout() { auth.logout() }
function openPermissions() { void router.push('/settings/permissions') }
function changeBackend() {
  const bridge = (window as any).HoshinoumiConfig
  if (bridge?.open) {
    bridge.open()
    return
  }
  // App 内桥异常时仍可回本地配置页；浏览器没有壳配置，保持只读
  if (/Android/i.test(navigator.userAgent) && location.protocol.startsWith('http')) {
    location.href = 'https://localhost/index.html?config=1'
    return
  }
  window.alert('浏览器版的后端地址由当前站点决定；请在 Hoshinoumi App 内修改。')
}
</script>

<template>
  <section class="mobile-settings">
    <div class="head"><h1>设置</h1><p>连接 / 快捷栏 / 账号</p></div>

    <div class="block">
      <div class="block-title">底部快捷栏 <span>{{ message }}</span></div>
      <p class="block-desc">1–5 个图标入口，收起时显示在底部。当前：{{ quickLabel }}</p>
      <div class="quick-grid">
        <button
          v-for="entry in visibleEntries"
          :key="entry.key"
          type="button"
          class="quick-item"
          :class="{ on: quickKeys.includes(entry.key) }"
          @click="toggle(entry.key)"
        >
          <b>{{ entry.icon }}</b><span>{{ entry.label }}</span><em v-if="quickKeys.includes(entry.key)">✓</em>
        </button>
      </div>
      <button class="reset" type="button" @click="resetQuick">恢复默认</button>
    </div>

    <div class="block">
      <div class="block-title">页面可见性 <span>隐藏 {{ hiddenPages.length }} 个</span></div>
      <div class="visibility-grid"><button v-for="entry in visibilityEntries" :key="entry.key" type="button" class="visibility-item" :class="{ on: !hiddenPages.includes(entry.key) }" @click="togglePage(entry.key)">{{ entry.label }}<em>{{ hiddenPages.includes(entry.key) ? '隐藏' : '显示' }}</em></button></div>
    </div>

    <div class="block">
      <div class="row"><span>底部导航</span><button class="nav-switch" :class="{ on: !navHidden }" type="button" role="switch" :aria-checked="!navHidden" @click="navHidden = !navHidden"><i /></button></div>
      <div class="row"><span>导航球</span><button class="nav-switch" :class="{ on: navBall }" type="button" role="switch" :aria-checked="navBall" @click="navBall = !navBall"><i /></button></div>
    </div>

    <div class="block">
      <div class="row"><span>后端连接</span><small>{{ auth.loggedIn ? '已登录' : '未登录' }}</small></div>
      <button class="row backend-row" type="button" @click="changeBackend"><span>后端地址</span><small>修改 ›</small></button>
      <button class="row backend-row" type="button" @click="openPermissions"><span>权限与后台</span><small>管理 ›</small></button>
      <div class="row"><span>账号</span><small>{{ auth.qq || '—' }}</small></div>
      <div class="row"><span>手机 APK</span><small>{{ apkVersion }}</small></div>
      <div class="row"><span>后端版本</span><small>{{ backendVersion }}</small></div>
      <div class="row"><span>版本一致性</span><small>{{ consistency }}</small></div>
      <button class="row backend-row" type="button" :disabled="updateState === 'checking' || updateState === 'downloading'" @click="checkUpdate"><span>检查更新</span><small>{{ updateState === 'checking' ? '检查中…' : updateState === 'downloading' ? '已提交下载' : '检查 ›' }}</small></button>
      <div v-if="updateState === 'latest'" class="update-note ok">已是最新版本</div>
      <div v-else-if="updateState === 'error'" class="update-note bad"><b>{{ updateError }}</b><button v-if="latest?.available" type="button" class="update-retry" @click="retryDownload">重新下载</button></div>
      <div v-else-if="latest && updateState === 'available'" class="update-note"><b>发现新版本 {{ latest.version }}</b><span>{{ latest.notes }}</span><a :href="updateUrl" :download="'hoshinoumi-' + latest.version + '.apk'">下载 APK</a></div>
      <div v-else-if="updateState === 'downloading'" class="update-note"><b>正在下载 {{ latest?.version }} · {{ downloadPercent }}%</b><span class="update-bar"><i :style="{ width: downloadPercent + '%' }" /></span><span>下载完成后由系统安装。</span></div>
      <div v-else-if="updateState === 'complete'" class="update-note ok"><b>下载完成</b><span>系统安装器已启动；若未弹出请到通知栏点击安装。</span></div>
    </div>

    <button class="logout" type="button" @click="logout">退出登录</button>
    <div class="about-card"><b>关于 Hoshinoumi</b><span>APK {{ apkVersion }} · 后端 {{ backendVersion }}</span><div class="about-links"><a href="https://github.com/jyoushitou/Hoshinoumi" target="_blank" rel="noopener">GitHub</a><a href="https://github.com/jyoushitou" target="_blank" rel="noopener">作者 jyoushitou</a></div><em>POWERED BY JYOUSHITOU</em></div>
  </section>
</template>

<style scoped>
.mobile-settings{padding:16px 14px 18px;background:#f7faff;min-height:100%}
.head h1{margin:0;font-size:24px;letter-spacing:-.03em;line-height:1.15}.head p{margin:4px 0 14px;color:#8a9bb0;font-size:10px}
.block{background:#fff;border:1px solid #e3ebf7;border-radius:13px;padding:12px;margin-bottom:10px}
.block-title{display:flex;justify-content:space-between;font-size:11px;font-weight:750;color:#314a65}.block-title span{font-size:9px;color:#8a9bb0;font-weight:400}
.block-desc{font-size:8.5px;color:#8a9bb0;line-height:1.6;margin:4px 0 9px}
.quick-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.quick-item{position:relative;height:45px;border:1px solid #e1ebf9;background:#f8fbff;border-radius:8px;color:#607896;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:8px;cursor:pointer}
.quick-item b{font-size:14px;font-weight:400;line-height:1}.quick-item em{position:absolute;right:4px;top:2px;font-style:normal;color:#2563eb;font-size:8px}
.quick-item.on{border-color:#93c5fd;background:#eef4ff;color:#2563eb;font-weight:700}
.reset{width:100%;margin-top:8px;height:30px;border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:8px;font:10px inherit;cursor:pointer}
.row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f0f5fd;font-size:10px;color:#3d5470}.row:last-child{border-bottom:0}.visibility-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.visibility-item{height:30px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;color:#8a9bb0;font:8px inherit;display:flex;align-items:center;justify-content:space-between;padding:0 7px;cursor:pointer}.visibility-item.on{background:#fff;color:#405872;border-color:#dbe8ff}.visibility-item em{font-style:normal;font-size:7px;color:#9aabc0}.visibility-item.on em{color:#168b63}.nav-switch{position:relative;width:38px;height:22px;border:0;border-radius:11px;background:#cbd5e1;cursor:pointer}.nav-switch.on{background:#2563eb}.nav-switch i{position:absolute;left:2px;top:2px;width:18px;height:18px;border-radius:50%;background:#fff;transition:left .2s}.nav-switch.on i{left:18px}.row small{font-size:9px;color:#9aabc0}.backend-row{width:100%;border:0;background:none;text-align:left;cursor:pointer}.backend-row small{color:#2563eb}
.about-card{margin-top:12px;padding:13px;border:1px solid #e3ebf7;border-radius:13px;background:#fff;text-align:center}.about-card b{display:block;font-size:10px;color:#314a65}.about-card span{display:block;font-size:8px;color:#9aabc0;margin-top:3px}.about-card em{display:block;font:7px ui-monospace,monospace;letter-spacing:.12em;color:#a8b5c7;font-style:normal;margin-top:7px}.about-links{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-top:8px}.about-links a{font-size:8px;text-decoration:none;border-radius:6px;padding:2px 7px;color:#2563eb;border:1px solid #dbe8ff;background:#f4f9ff}.about-links a:last-child{color:#607795;border-color:#e3ebf7;background:#fff}
.update-note{margin-top:7px;border:1px solid #dbe8ff;border-radius:8px;background:#f8fbff;padding:7px 8px;font-size:8px;color:#526982;line-height:1.5}.update-note.ok{color:#168b63;border-color:#cdeee0;background:#f0fdf7}.update-note.bad{color:#b91c1c;border-color:#fecaca;background:#fff5f5}.update-note b{display:block;font-size:9px;margin-bottom:2px}.update-note span{display:block;color:#8a9bb0}.update-note a{display:inline-block;margin-top:5px;color:#2563eb}.update-bar{display:block;height:4px;border-radius:4px;background:#e8effa;margin:4px 0;overflow:hidden}.update-bar i{display:block;height:100%;background:#2563eb}.update-retry{margin-top:5px;border:1px solid #fecaca;border-radius:5px;background:#fff;color:#b91c1c;font:8px inherit;padding:2px 7px;cursor:pointer}.logout{width:100%;height:36px;border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:9px;font:10px inherit;cursor:pointer}
</style>
