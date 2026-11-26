<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '@/api/client'

const props = defineProps<{ token: string }>()
interface ShareInfo { id: string; name: string; mime?: string; size?: number; downloads?: number; max_downloads?: number; expires_at?: string }
const info = ref<ShareInfo | null>(null)
const error = ref('')
const busy = ref(false)
const progress = ref(0)
function sizeLabel(n?: number) { const v = Number(n || 0); if (v >= 1024 * 1024) return (v / 1024 / 1024).toFixed(1) + ' MB'; return Math.max(1, Math.round(v / 1024)) + ' KB' }
async function load() {
  try {
    const r = await http.get<{ data?: ShareInfo }>('/api/files/share/' + encodeURIComponent(props.token))
    info.value = r.data || null
  } catch (e) { error.value = e instanceof Error ? e.message : '分享不存在或已过期' }
}
async function download() {
  if (!info.value) return
  busy.value = true; progress.value = 0
  try {
    const chunks: Uint8Array[] = []
    let offset = 0, total = 0
    while (true) {
      const part = await http.get<{ data_base64?: string; length?: number; size?: number }>('/api/files/share/' + encodeURIComponent(props.token) + '/download?offset=' + offset + '&length=' + (4 * 1024 * 1024))
      const bin = atob(part.data_base64 || '')
      const data = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) data[i] = bin.charCodeAt(i)
      chunks.push(data); total += data.length; offset += data.length
      progress.value = Math.round(offset / Math.max(1, Number(part.size || total)) * 100)
      if (!part.length || offset >= Number(part.size || total)) break
    }
    const blob = new Blob(chunks as BlobPart[], { type: info.value.mime || 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = info.value.name; a.click(); URL.revokeObjectURL(url)
  } catch (e) { error.value = e instanceof Error ? e.message : '下载失败' } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <div class="share-page">
    <div class="card">
      <div class="brand">HOSHINOUMI · 文件分享</div>
      <div v-if="error" class="error">{{ error }}</div>
      <template v-else-if="info">
        <div class="icon">{{ (info.name || '?').slice(0, 1).toUpperCase() }}</div>
        <h1>{{ info.name }}</h1>
        <p>{{ sizeLabel(info.size) }} · {{ info.mime || 'file' }}</p>
        <p class="meta">只读分享 · 已下载 {{ info.downloads || 0 }}{{ info.max_downloads ? ' / ' + info.max_downloads : '' }}<template v-if="info.expires_at"> · 到期 {{ info.expires_at }}</template></p>
        <div v-if="busy" class="progress"><i :style="{ width: progress + '%' }" /><span>{{ progress }}%</span></div>
        <button type="button" :disabled="busy" @click="download">{{ busy ? '下载中…' : '下载文件' }}</button>
      </template>
      <div v-else class="loading">正在读取分享…</div>
    </div>
  </div>
</template>

<style scoped>
.share-page{min-height:100vh;display:grid;place-items:center;padding:20px;background:radial-gradient(700px 460px at 80% 0%,rgba(37,99,235,.12),transparent 60%),#f2f7fd;box-sizing:border-box;color:#17263b;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif}.card{width:min(420px,100%);background:#fff;border:1px solid #dbe8ff;border-radius:16px;padding:22px;box-shadow:0 24px 60px rgba(29,78,137,.14);text-align:center}.brand{font:8px ui-monospace,monospace;letter-spacing:.16em;color:#6f86a4;margin-bottom:18px}.icon{width:58px;height:70px;margin:0 auto 12px;border-radius:8px;background:linear-gradient(135deg,#dbeafe,#93c5fd);display:grid;place-items:center;font-size:22px;font-weight:800;color:#1e3a5f}h1{margin:0 0 5px;font-size:17px;letter-spacing:-.02em;word-break:break-all}p{margin:3px 0;font-size:9px;color:#8a9bb0}.meta{color:#526982;margin:8px 0 14px}button{width:100%;height:36px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:10px inherit;font-weight:700;cursor:pointer}button:disabled{opacity:.55}.progress{height:5px;border-radius:5px;background:#eef3fa;margin:0 0 12px;position:relative;overflow:hidden}.progress i{display:block;height:100%;background:#2563eb}.progress span{position:absolute;right:0;top:7px;font-size:7px;color:#9aabc0}.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:8px;font-size:9px}.loading{font-size:9px;color:#9aabc0;padding:20px}
</style>
