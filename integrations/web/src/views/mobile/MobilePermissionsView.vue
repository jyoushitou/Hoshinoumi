<template>
  <section class="perm-page">
    <div class="head">
      <button class="back" type="button" aria-label="返回" @click="router.back()">‹</button>
      <div><h1>权限与后台</h1><p>ANDROID · 系统能力</p></div>
    </div>
    <div v-if="!native" class="notice">浏览器里只显示说明；权限开关需要安装 Hoshinoumi App。</div>
    <div class="group">
      <div class="group-title">应用权限</div>
      <div v-for="row in appPermissions" :key="row.key" class="row">
        <span class="ic">{{ row.icon }}</span>
        <div class="copy"><b>{{ row.label }}</b><small>{{ row.desc }}</small></div>
        <button class="switch" :class="{ on: status[row.key] }" type="button" :aria-label="row.label" :disabled="!native" @click="toggle(row.key)"></button>
      </div>
    </div>
    <div class="group">
      <div class="group-title">后台限制</div>
      <div class="row">
        <span class="ic">↻</span><div class="copy"><b>自启动</b><small>重启后保持连接</small></div>
        <button class="go" type="button" :disabled="!native" @click="open('autostart')">去设置</button>
      </div>
      <div class="row">
        <span class="ic">◔</span><div class="copy"><b>电池优化</b><small>后台不被清理</small></div>
        <button class="go" type="button" :disabled="!native" @click="open('battery')">去设置</button>
      </div>
      <div class="row">
        <span class="ic">▣</span><div class="copy"><b>应用详情</b><small>通知 / 权限 / 存储</small></div>
        <button class="go" type="button" :disabled="!native" @click="open('app')">去设置</button>
      </div>
    </div>
    <div class="group">
      <div class="group-title">消息推送</div>
      <div class="row">
        <span class="ic">⇪</span><div class="copy"><b>ntfy 测试</b><small>{{ push.registered ? '已注册 · ' + push.topic : '未开启' }}</small></div>
        <button v-if="!push.registered" class="go" type="button" :disabled="!native || pushBusy" @click="startPush">开启测试</button>
        <button v-else class="go" type="button" :disabled="!native" @click="stopPush">关闭</button>
      </div>
      <div class="push-note">Mock 注册后约 5 分钟推送一条测试消息；真机需把 ntfy 地址改成自托管 HTTPS。</div>
    </div>
    <div class="group">
      <div class="group-title">系统信息</div>
      <div class="row"><span class="ic">▣</span><div class="copy"><b>Android</b><small>{{ system }}</small></div><span class="state">系统</span></div>
    </div>
    <div class="foot">开关读取系统真实状态；不能直接关闭的权限会跳转系统设置。</div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

interface NativeBridge {
  getPermissionStatus?: () => string
  requestPermission?: (key: string) => void
  openAppSettings?: () => void
  openBatterySettings?: () => void
  openAutostartSettings?: () => void
  startPush?: (backend: string, token: string, server: string) => void
  stopPush?: () => void
  getPushState?: () => string
}
const router = useRouter()
const auth = useAuthStore()
const native = ref(false)
const status = ref<Record<string, boolean>>({ notifications: false, camera: false, microphone: false, photos: false })
const system = ref('—')
const push = ref<{ registered: boolean; topic: string; server: string }>({ registered: false, topic: '', server: '' })
const pushBusy = ref(false)
const appPermissions = [
  { key: 'notifications', icon: '◉', label: '通知', desc: '新消息 / 提醒' },
  { key: 'camera', icon: '▧', label: '相机', desc: '拍照发送' },
  { key: 'microphone', icon: '♩', label: '麦克风', desc: '语音消息' },
  { key: 'photos', icon: '▤', label: '照片与文件', desc: '发图 / 下载' },
]
function bridge(): NativeBridge | undefined { return (window as any).HoshinoumiConfig }
function refresh() {
  const b = bridge()
  if (!b?.getPermissionStatus) { native.value = false; return }
  native.value = true
  try {
    const value = JSON.parse(b.getPermissionStatus())
    status.value = {
      notifications: Boolean(value.notifications),
      camera: Boolean(value.camera),
      microphone: Boolean(value.microphone),
      photos: Boolean(value.photos),
    }
    system.value = `Android ${value.android ?? '—'} · API ${value.sdk ?? '—'}`
    refreshPush()
  } catch { /* keep last state */ }
}
function refreshPush() {
  const b = bridge()
  if (!b?.getPushState) return
  try {
    const value = JSON.parse(b.getPushState())
    push.value = { registered: Boolean(value.registered), topic: String(value.topic || ''), server: String(value.server || '') }
  } catch { /* ignore */ }
}
async function startPush() {
  const b = bridge()
  if (!b?.startPush) return
  pushBusy.value = true
  const ntfy = localStorage.getItem('hsh_ntfy_url') || `${window.location.protocol}//${window.location.hostname}:2586`
  b.startPush(window.location.origin, auth.token, ntfy)
  window.setTimeout(() => { refreshPush(); pushBusy.value = false }, 1200)
}
function stopPush() {
  bridge()?.stopPush?.()
  window.setTimeout(refreshPush, 500)
}
function toggle(key: string) {
  const b = bridge()
  if (!b?.requestPermission) return
  b.requestPermission(key)
  window.setTimeout(refresh, 600)
}
function open(kind: 'app' | 'battery' | 'autostart') {
  const b = bridge()
  if (!b) return
  if (kind === 'app') b.openAppSettings?.()
  else if (kind === 'battery') b.openBatterySettings?.()
  else b.openAutostartSettings?.()
}
onMounted(() => {
  refresh()
  window.addEventListener('focus', refresh)
})
</script>

<style scoped>
.perm-page{padding:14px 14px 22px;background:#f7faff;min-height:100%}
.head{display:flex;align-items:center;gap:8px;margin-bottom:12px}.back{width:30px;height:32px;border:0;background:none;color:#52708f;font-size:22px}.head h1{margin:0;font-size:22px;letter-spacing:-.03em}.head p{margin:2px 0 0;font-size:7px;letter-spacing:.16em;color:#9aabc0}
.notice{border:1px solid #dbe8ff;background:#f4f9ff;color:#71859d;border-radius:9px;padding:8px 9px;font-size:8px;line-height:1.6;margin-bottom:9px}
.group{background:#fff;border:1px solid #e3ebf7;border-radius:13px;padding:4px 11px;margin-bottom:9px}.group-title{font-size:8px;color:#8a9bb0;padding:7px 0 2px;letter-spacing:.08em}
.row{display:flex;align-items:center;gap:9px;padding:9px 0;border-bottom:1px solid #f1f5fb}.row:last-child{border-bottom:0}.ic{width:27px;height:27px;border-radius:8px;background:#f4f8ff;color:#52708f;display:grid;place-items:center;font-size:12px;flex:none}.copy{flex:1;min-width:0}.copy b{display:block;font-size:9.5px;color:#314a65}.copy small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}
.switch{position:relative;flex:none;width:32px;height:18px;border:0;border-radius:10px;background:#cbd5e1;cursor:pointer;transition:background .18s}.switch.on{background:#2563eb}.switch:after{content:"";position:absolute;width:14px;height:14px;border-radius:50%;background:#fff;top:2px;left:2px;transition:left .18s}.switch.on:after{left:16px}.switch:disabled,.go:disabled{opacity:.5;cursor:not-allowed}
.go{height:24px;border:1px solid #dbe8ff;border-radius:7px;background:#f4f9ff;color:#2563eb;font:8px inherit;padding:0 8px;flex:none}.state{font-size:7px;color:#8a9bb0;background:#f4f8ff;border-radius:5px;padding:2px 5px}.push-note{font-size:7px;line-height:1.7;color:#9aabc0;padding:4px 0 7px}.foot{text-align:center;color:#9aabc0;font-size:7px;line-height:1.7;padding:4px 0}
</style>
