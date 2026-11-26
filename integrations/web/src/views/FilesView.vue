<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface FileItem { id: string; name: string; mime: string; size: number; sha256?: string; created_at?: string; downloads?: number; max_downloads?: number; share_token?: string; share_url?: string; share_expires_at?: string }
interface UploadState { name: string; progress: number; error: string; file: File; id?: string; offset: number }
const files = ref<FileItem[]>([])
const used = ref(0)
const quota = ref(2 * 1024 * 1024 * 1024)
const loading = ref(false)
const error = ref('')
const search = ref('')
const drop = ref(false)
const input = ref<HTMLInputElement | null>(null)
const uploads = ref<UploadState[]>([])
const sharing = ref<FileItem | null>(null)
const shareHours = ref('24')
const shareMax = ref('0')
const shareBusy = ref(false)
const shareResult = ref('')
const chunkSize = 4 * 1024 * 1024
const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? files.value.filter(f => f.name.toLowerCase().includes(q)) : files.value
})
const usage = computed(() => Math.min(100, Math.round((used.value / Math.max(1, quota.value)) * 100)))
function sizeLabel(n?: number) { const v = Number(n || 0); if (v >= 1024 * 1024 * 1024) return (v / 1024 / 1024 / 1024).toFixed(2) + ' GB'; if (v >= 1024 * 1024) return (v / 1024 / 1024).toFixed(1) + ' MB'; return Math.max(1, Math.round(v / 1024)) + ' KB' }
async function load() {
  loading.value = true; error.value = ''
  try {
    const r = await http.get<{ data?: FileItem[]; used?: number; quota?: number }>('/api/files')
    files.value = Array.isArray(r.data) ? r.data : []
    used.value = Number(r.used || 0); quota.value = Number(r.quota || quota.value)
  } catch (e) { error.value = e instanceof Error ? e.message : '文件列表读取失败' } finally { loading.value = false }
}
function choose() { input.value?.click() }
function copyShare() { if (shareResult.value) void navigator.clipboard?.writeText(shareResult.value) }
function onPick(event: Event) {
  const list = (event.target as HTMLInputElement).files
  if (list) void uploadFiles(Array.from(list))
  ;(event.target as HTMLInputElement).value = ''
}
function onDrop(event: DragEvent) {
  drop.value = false
  if (event.dataTransfer?.files?.length) void uploadFiles(Array.from(event.dataTransfer.files))
}
function encode(data: Uint8Array): string {
  let text = ''
  for (let i = 0; i < data.length; i += 0x8000) text += String.fromCharCode(...data.subarray(i, i + 0x8000))
  return btoa(text)
}
async function uploadOne(state: UploadState) {
  try {
    let id = state.id
    if (!id) {
      const init = await http.post<{ id?: string; chunk_size?: number }>('/api/files/init', { name: state.file.name, size: state.file.size, mime: state.file.type || 'application/octet-stream' })
      if (!init.id) throw new Error('init failed')
      id = init.id; state.id = id
    }
    const status = await http.get<{ offset?: number }>('/api/files/' + encodeURIComponent(id) + '/upload')
    let offset = Number(status.offset || 0)
    const size = chunkSize
    while (offset < state.file.size) {
      const buf = new Uint8Array(await state.file.slice(offset, offset + size).arrayBuffer())
      await http.put('/api/files/' + encodeURIComponent(id) + '/chunk', { offset, data_base64: encode(buf) })
      offset += buf.length
      state.offset = offset
      state.progress = Math.round(Math.min(1, offset / Math.max(1, state.file.size)) * 100)
    }
    await http.post('/api/files/' + encodeURIComponent(id) + '/complete', {})
    state.progress = 100; state.error = ''
    await load()
    setTimeout(() => { uploads.value = uploads.value.filter(item => item !== state) }, 800)
  } catch (e) { state.error = e instanceof Error ? e.message : '上传失败'; state.progress = Math.round(state.offset / Math.max(1, state.file.size) * 100); error.value = state.name + ' 上传失败，可重试' }
}
async function uploadFiles(list: File[]) {
  for (const file of list) {
    if (file.size > 30 * 1024 * 1024) { error.value = file.name + ' 超过 30 MB'; continue }
    const state: UploadState = { name: file.name, progress: 0, error: '', file, offset: 0 }
    uploads.value.push(state)
    await uploadOne(state)
  }
}
function retryUpload(state: UploadState) { state.error = ''; void uploadOne(state) }
async function download(item: FileItem) {
  try {
    const chunks: Uint8Array[] = []
    let offset = 0, total = 0
    while (true) {
      const part = await http.get<{ data_base64?: string; length?: number; size?: number }>('/api/files/' + encodeURIComponent(item.id) + '/download?offset=' + offset + '&length=' + chunkSize)
      const bytes = part.data_base64 || ''
      const bin = atob(bytes)
      const data = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) data[i] = bin.charCodeAt(i)
      chunks.push(data); total += data.length; offset += data.length
      if (!part.length || offset >= Number(part.size || total)) break
    }
    const blob = new Blob(chunks as BlobPart[], { type: item.mime || 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a'); link.href = url; link.download = item.name; link.click(); URL.revokeObjectURL(url)
  } catch (e) { error.value = e instanceof Error ? e.message : '下载失败' }
}
async function remove(item: FileItem) {
  if (!confirm('删除「' + item.name + '」？')) return
  try { await http.delete('/api/files/' + encodeURIComponent(item.id)); await load() } catch (e) { error.value = e instanceof Error ? e.message : '删除失败' }
}
async function createShare() {
  if (!sharing.value) return
  shareBusy.value = true
  shareResult.value = ''
  try {
    const r = await http.post<{ url?: string; token?: string }>('/api/files/' + encodeURIComponent(sharing.value.id) + '/share', { expires_hours: Number(shareHours.value), max_downloads: Number(shareMax.value) })
    const url = location.origin + '/files/share/' + (r.token || '')
    shareResult.value = url
    await navigator.clipboard?.writeText(url).catch(() => {})
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '分享失败' } finally { shareBusy.value = false }
}
onMounted(load)
</script>

<template>
  <section class="files">
    <header class="head"><div><h1>文件</h1><p>单层文件库 · 分片上传 · 分享链接</p></div><button class="primary" type="button" @click="choose">＋ 上传文件</button><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></header>
    <div v-if="error" class="notice">{{ error }}</div>
    <div class="quota"><div><small>空间用量</small><b>{{ sizeLabel(used) }} / {{ sizeLabel(quota) }}</b></div><div class="bar"><i :style="{ width: usage + '%' }" /></div><span>{{ usage }}%</span></div>
    <div class="drop" :class="{ on: drop }" @dragover.prevent="drop = true" @dragleave.prevent="drop = false" @drop.prevent="onDrop" @click="choose">
      <b>拖拽文件到这里</b><span>或点击选择 · 单文件 ≤ 30 MB · 分片 4 MB</span><input ref="input" type="file" multiple hidden @change="onPick">
    </div>
    <div v-for="up in uploads" :key="up.id || up.name" class="upload"><span>{{ up.name }}</span><i :style="{ width: up.progress + '%' }" /><em>{{ up.error || up.progress + '%' }}</em><button v-if="up.error" type="button" class="retry" @click="retryUpload(up)">重试</button></div>
    <div class="toolbar"><input v-model="search" placeholder="搜索文件"><span>{{ visible.length }} 个文件</span></div>
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!visible.length" class="empty">暂无文件，上传第一个吧。</div>
    <div v-else class="grid">
      <article v-for="item in visible" :key="item.id" class="card">
        <div class="icon">{{ (item.name || '?').slice(0, 1).toUpperCase() }}</div>
        <div class="meta"><b>{{ item.name }}</b><span>{{ sizeLabel(item.size) }} · {{ item.mime || 'file' }} · {{ String(item.created_at || '').slice(0, 16) }}</span><small v-if="item.share_token">分享中 · 下载 {{ item.downloads || 0 }}{{ item.max_downloads ? ' / ' + item.max_downloads : '' }}</small></div>
        <div class="acts"><button type="button" @click="download(item)">下载</button><button type="button" @click="sharing = item; shareResult = ''">分享</button><button type="button" class="danger" @click="remove(item)">删除</button></div>
      </article>
    </div>
    <div v-if="sharing" class="mask" @click.self="sharing = null">
      <div class="modal"><header><b>分享「{{ sharing.name }}」</b><button type="button" @click="sharing = null">×</button></header><label>有效期（小时）<input v-model="shareHours" inputmode="numeric"></label><label>最大下载次数（0 不限）<input v-model="shareMax" inputmode="numeric"></label><button class="primary wide" type="button" :disabled="shareBusy" @click="createShare">{{ shareBusy ? '生成中…' : '生成只读链接' }}</button><div v-if="shareResult" class="share-result"><input :value="shareResult" readonly><button type="button" @click="copyShare">复制</button></div><p class="hint">链接只读，可过期，可限下载次数。</p></div>
    </div>
  </section>
</template>

<style scoped>
.files{flex:1;min-height:0;overflow:auto;padding:22px 24px 28px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:7px;margin-bottom:10px;flex-wrap:wrap}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.primary,.refresh{margin-left:auto;height:29px;border:1px solid #2563eb;border-radius:8px;background:#2563eb;color:#fff;font:9px inherit;padding:0 10px;cursor:pointer}.refresh{margin-left:0;background:#fff;color:#2563eb;border-color:#dbe8ff}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
.quota{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 10px;margin-bottom:9px;font-size:8px;color:#8a9bb0}.quota>div:first-child{min-width:120px}.quota small{display:block;font-size:7px;color:#9aabc0}.quota b{display:block;font-size:10px;color:#314a65;margin-top:2px}.quota .bar{flex:1;height:5px;border-radius:5px;background:#eef3fa;overflow:hidden}.quota .bar i{display:block;height:100%;background:#2563eb}.quota>span{font-size:8px;color:#2563eb}
.drop{border:1px dashed #bcd4f7;border-radius:11px;background:#f8fbff;padding:16px;text-align:center;cursor:pointer;margin-bottom:8px;transition:.18s}.drop.on{border-color:#2563eb;background:#eef4ff}.drop b{display:block;font-size:10px;color:#526982}.drop span{display:block;font-size:8px;color:#9aabc0;margin-top:3px}.upload{display:flex;align-items:center;gap:7px;font-size:8px;color:#526982;background:#fff;border:1px solid #e3ebf7;border-radius:7px;padding:5px 8px;margin-bottom:4px;position:relative;overflow:hidden}.upload i{position:absolute;left:0;bottom:0;height:2px;background:#2563eb}.upload em{margin-left:auto;font-style:normal;color:#9aabc0}.upload .retry{margin-left:6px;border:1px solid #dbe8ff;border-radius:4px;background:#fff;color:#2563eb;font:7px inherit;padding:1px 5px;cursor:pointer}
.toolbar{display:flex;align-items:center;gap:8px;margin-bottom:8px}.toolbar input{flex:1;height:28px;border:1px solid #dbe8ff;border-radius:7px;background:#fff;font:9px inherit;padding:0 8px;outline:0}.toolbar span{font-size:8px;color:#9aabc0}
.grid{display:grid;grid-template-columns:1fr;gap:6px}.card{display:flex;align-items:center;gap:9px;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:9px}.icon{width:31px;height:31px;border-radius:8px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:12px;font-weight:700;flex:none}.meta{min-width:0;flex:1}.meta b{display:block;font-size:10px;color:#314a65;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta span{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.meta small{display:block;font-size:7px;color:#2563eb;margin-top:2px}.acts{display:flex;gap:4px;flex:none}.acts button{height:24px;border:1px solid #dbe8ff;border-radius:5px;background:#f8fbff;color:#2563eb;font:8px inherit;padding:0 7px;cursor:pointer}.acts button.danger{color:#b23b52;border-color:#f0d7dd;background:#fff}.empty{border:1px dashed #cfe0f7;border-radius:10px;background:#fff;padding:24px;text-align:center;color:#9aabc0;font-size:9px}
.mask{position:fixed;inset:0;z-index:80;background:#0f172a52;display:grid;place-items:center;padding:18px}.modal{width:min(400px,100%);background:#fff;border-radius:14px;padding:15px;box-shadow:0 24px 60px #0f264e3d}.modal header{display:flex;align-items:center;margin-bottom:8px}.modal header b{font-size:13px;color:#1e3a5f}.modal header button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:17px;cursor:pointer}.modal label{display:block;font-size:8.5px;color:#8a9bb0;margin-bottom:8px}.modal input{display:block;width:100%;height:29px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;font:9px inherit;padding:0 8px;margin-top:3px;box-sizing:border-box}.wide{width:100%;height:30px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;cursor:pointer}.share-result{display:flex;gap:5px;margin-top:8px}.share-result input{flex:1;font-size:8px}.share-result button{border:1px solid #dbe8ff;border-radius:6px;background:#f8fbff;color:#2563eb;font:8px inherit;padding:0 8px;cursor:pointer}.hint{font-size:7.5px;color:#9aabc0;margin:8px 0 0;line-height:1.5}
@media(max-width:820px){.files{padding:14px 12px 20px}.head h1{font-size:22px}.quota{flex-wrap:wrap}.quota>div:first-child{width:100%}.card{align-items:flex-start;flex-wrap:wrap}.acts{margin-left:40px}.acts button{height:27px;font-size:8.5px}}
</style>
