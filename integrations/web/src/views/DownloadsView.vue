<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'
import { isNativeClient } from '@/lib/platform'

interface ClientItem { platform: string; name: string; version?: string; versionCode?: number; notes?: string; size?: number; sha256?: string; url?: string; available?: boolean }
const clients = ref<ClientItem[]>([])
const loading = ref(false)
const error = ref('')
const native = isNativeClient()
const copied = ref('')
const updatedAt = ref('')
const tabs = computed(() => Array.from(new Set(clients.value.map(item => item.platform))))
const active = ref('all')
const visible = computed(() => clients.value.filter(item => active.value === 'all' || item.platform === active.value).filter(item => !native || item.platform !== 'android'))
function platformLabel(platform: string) { return platform === 'android' ? 'Android' : platform === 'windows' ? 'Windows' : platform }
function icon(platform: string) { return platform === 'android' ? '▣' : platform === 'windows' ? '⊞' : '◫' }
function sizeLabel(size?: number) { const n = Number(size || 0); if (n >= 1024 * 1024 * 1024) return (n / 1024 / 1024 / 1024).toFixed(2) + ' GB'; if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'; return Math.max(1, Math.round(n / 1024)) + ' KB' }
function download(item: ClientItem) { if (item.url) location.href = item.url }
async function copyHash(hash?: string) {
  if (!hash) return
  try { await navigator.clipboard.writeText(hash); copied.value = hash; setTimeout(() => { copied.value = '' }, 1200) } catch { copied.value = '' }
}
async function load() {
  loading.value = true; error.value = ''
  try { const r = await http.get<{ data?: ClientItem[] }>('/api/clients'); clients.value = Array.isArray(r.data) ? r.data : []; updatedAt.value = new Date().toLocaleTimeString() }
  catch (e) { error.value = e instanceof Error ? e.message : '下载清单读取失败' } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="downloads">
    <header class="hero"><div class="mark">H</div><div><small>HOSHINOUMI · DOWNLOADS</small><h1>下载 Hoshinoumi</h1><p>Android 套壳 / Windows 便携包 · 版本、大小、SHA-256 均来自当前服务器</p></div></header>
    <div v-if="native" class="native-note"><b>当前为手机套壳端</b><span>APK 更新在「设置 → 检查更新」里完成；这里隐藏 Android 下载入口。</span></div>
    <div v-if="error" class="notice">{{ error }}</div>
    <div class="list-meta"><span>{{ clients.length }} 个平台包 · {{ updatedAt || '—' }}</span><button type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></div>
    <div class="tabs"><button type="button" :class="{ on: active === 'all' }" @click="active = 'all'">全部</button><button v-for="tab in tabs" :key="tab" type="button" :class="{ on: active === tab }" @click="active = tab">{{ platformLabel(tab) }}</button></div>
    <div v-if="loading" class="empty">正在读取下载清单…</div>
    <div v-else-if="!visible.length" class="empty"><b>暂无可用安装包</b><span>服务器没有对应平台的包，不显示伪造版本。</span></div>
    <div v-else class="grid">
      <article v-for="item in visible" :key="item.platform + item.version" class="card">
        <div class="card-head"><span class="icon">{{ icon(item.platform) }}</span><div><small>{{ platformLabel(item.platform) }}</small><b>{{ item.name }}</b><span>v{{ item.version || '—' }}<template v-if="item.versionCode"> · {{ item.versionCode }}</template></span></div><em>可用</em></div>
        <p>{{ item.notes || '官方安装包' }}</p>
        <dl><div><dt>大小</dt><dd>{{ sizeLabel(item.size) }}</dd></div><div><dt>更新</dt><dd>当前服务器</dd></div></dl>
        <div class="hash" @click="copyHash(item.sha256)"><small>SHA-256</small><code>{{ copied === item.sha256 ? '已复制' : (item.sha256 || '—') }}</code></div>
        <button type="button" @click="download(item)">下载 {{ platformLabel(item.platform) }} 版</button>
      </article>
    </div>
    <footer>安装包由服务器直接提供；下载走 Range，可断点续传。桌面便携包解压即用。</footer>
  </section>
</template>

<style scoped>
.downloads{flex:1;min-height:0;overflow:auto;padding:22px 24px 28px;background:radial-gradient(640px 300px at 85% 0%,rgba(37,99,235,.12),transparent 65%),#f7faff;color:#17263b;box-sizing:border-box;width:100%}.hero{display:flex;gap:13px;align-items:center;margin-bottom:14px}.mark{width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#60a5fa);color:#fff;display:grid;place-items:center;font-size:24px;font-weight:800;box-shadow:0 12px 26px rgba(37,99,235,.24);flex:none}.hero small{font:7px ui-monospace,monospace;letter-spacing:.16em;color:#7d90a9}.hero h1{margin:3px 0 2px;font-size:26px;letter-spacing:-.04em}.hero p{margin:0;font-size:9px;color:#8a9bb0}.native-note{display:flex;gap:6px;align-items:baseline;border:1px solid #dbe8ff;background:#eef4ff;border-radius:9px;padding:8px 9px;font-size:8.5px;color:#526982;margin-bottom:10px}.native-note b{font-size:9px;color:#1d4ed8}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:9px}
.list-meta{display:flex;align-items:center;font-size:8px;color:#9aabc0;margin-bottom:7px}.list-meta button{margin-left:auto;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#2563eb;font:8px inherit;padding:2px 7px;cursor:pointer}.tabs{display:flex;gap:5px;margin-bottom:10px}.tabs button{height:25px;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#607795;font:8px inherit;padding:0 9px;cursor:pointer}.tabs button.on{background:#2563eb;border-color:#2563eb;color:#fff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:14px;padding:13px;box-shadow:0 7px 20px rgba(24,58,110,.04)}.card-head{display:flex;align-items:flex-start;gap:9px}.icon{width:34px;height:34px;border-radius:9px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:16px;flex:none}.card-head div{min-width:0}.card-head small{display:block;font-size:7px;letter-spacing:.12em;color:#9aabc0}.card-head b{display:block;font-size:11px;color:#1e3a5f;margin:2px 0}.card-head span{display:block;font-size:8px;color:#8a9bb0}.card-head em{margin-left:auto;font-style:normal;font-size:7px;color:#168b63;border:1px solid #cdeee0;background:#f0fdf7;border-radius:8px;padding:2px 6px}.card p{font-size:8.5px;color:#7d90a9;margin:10px 0;min-height:24px;line-height:1.5}dl{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0 0 9px}dl div{border:1px solid #f0f5fd;border-radius:7px;padding:5px 7px}dt{font-size:7px;color:#9aabc0}dd{margin:2px 0 0;font-size:9px;color:#405872}.hash{border:1px dashed #dbe8ff;border-radius:7px;padding:5px 7px;margin-bottom:9px;cursor:pointer;overflow:hidden}.hash small{display:block;font-size:7px;color:#9aabc0}.hash code{display:block;font:7px ui-monospace,monospace;color:#405872;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.card>button{width:100%;height:31px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:9px inherit;font-weight:700;cursor:pointer}.empty{border:1px dashed #cfe0f7;border-radius:12px;background:#fff;padding:26px;text-align:center;color:#9aabc0;font-size:9px;line-height:1.8}.empty b{display:block;color:#526982;font-size:11px}footer{margin-top:15px;font-size:7.5px;color:#9aabc0;text-align:center}
@media(max-width:820px){.downloads{padding:16px 14px 20px}.hero h1{font-size:23px}.hero p{font-size:8px}.grid{grid-template-columns:1fr}.native-note{flex-direction:column}.tabs{overflow-x:auto}.card>button{height:35px}}
</style>
