<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface Plugin { id: string; name: string; slug: string; enabled: boolean; pending: boolean; permissions: string[]; version: string; description: string }
interface PluginError { id: string; plugin: string; message: string; at: string }
const plugins = ref<Plugin[]>([])
const errors = ref<PluginError[]>([])
const stats = ref({ installed: 0, pending: 0, errors: 0 })
const tab = ref<'installed' | 'pending' | 'permissions' | 'errors'>('installed')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const importing = ref(false)
const showImport = ref(false)
const importUrl = ref('')
const importFile = ref<HTMLInputElement | null>(null)
const activePlugins = computed(() => plugins.value.filter(p => !p.pending))
const pendingPlugins = computed(() => plugins.value.filter(p => p.pending))
const permissions = computed(() => {
  const map = new Map<string, string[]>()
  activePlugins.value.forEach(plugin => plugin.permissions.forEach(permission => map.set(permission, [...(map.get(permission) || []), plugin.name])))
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
})
const visible = computed(() => tab.value === 'pending' ? pendingPlugins.value : tab.value === 'installed' ? activePlugins.value : [])
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<{ data?: Plugin[]; stats?: typeof stats.value; errors?: PluginError[] }>('/api/plugins')
    plugins.value = Array.isArray(result.data) ? result.data : []
    errors.value = Array.isArray(result.errors) ? result.errors : []
    if (result.stats) stats.value = result.stats
  } catch (e) { error.value = e instanceof Error ? e.message : '插件读取失败' } finally { loading.value = false }
}
async function toggle(plugin: Plugin) {
  try { await http.post(`/api/plugins/${plugin.id}/toggle`, {}); await load(); notice.value = plugin.enabled ? `已停用 ${plugin.name}` : `已启用 ${plugin.name}` } catch { error.value = '启停失败，仅 owner 可操作' }
}
async function action(plugin: Plugin, kind: 'approve' | 'reject') {
  try { await http.post(`/api/plugins/${plugin.id}/${kind}`, {}); await load(); notice.value = kind === 'approve' ? `已批准 ${plugin.name}` : `已拒绝 ${plugin.name}` } catch { error.value = '审批失败' }
}
async function install(body: Record<string, unknown>) {
  importing.value = true; error.value = ''
  try { const result = await http.post<{ data?: Plugin }>('/api/plugins/import', body); await load(); notice.value = result.data?.pending ? `${result.data.name} 待审批` : `已安装 ${result.data?.name || '插件'}`; showImport.value = false; importUrl.value = '' } catch (e) { error.value = e instanceof Error ? e.message : '安装失败' } finally { importing.value = false }
}
async function importFromUrl() {
  const url = importUrl.value.trim()
  if (!/^https?:\/\//i.test(url)) { error.value = '请输入完整的 http(s) 插件网址'; return }
  if (/\.json(?:\?|$)/i.test(url)) {
    try { const manifest = await (await fetch(url)).json(); await install({ source: 'manifest', manifest }) } catch { error.value = '读取 manifest 失败' }
    return
  }
  await install({ source: 'url', url })
}
async function importFromFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!/\.(hoshinoumi|zip|json)$/i.test(file.name)) { error.value = '只支持 .hoshinoumi / .zip / .json'; return }
  if (file.size > 20 * 1024 * 1024) { error.value = '插件包超过 20 MB'; return }
  if (/\.json$/i.test(file.name)) {
    try { const manifest = JSON.parse(await file.text()); await install({ source: 'manifest', manifest }) } catch { error.value = 'manifest JSON 格式错误' }
    return
  }
  const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || '').split(',')[1] || ''); reader.onerror = () => reject(new Error('read_failed')); reader.readAsDataURL(file) })
  await install({ source: 'file', filename: file.name, data_base64: data })
}
function onFocus() { void load() }
onMounted(() => { void load(); window.addEventListener('focus', onFocus) })
onBeforeUnmount(() => window.removeEventListener('focus', onFocus))
</script>

<template>
  <section class="plugins-page">
    <header class="head"><div><h1>插件</h1><p>安装 / 审批 / 权限 / 错误 · 真实 API · 仅 owner</p></div><button class="add" type="button" @click="showImport = true">＋ 安装插件</button><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></header>
    <div v-if="error" class="notice error">{{ error }}</div>
    <div v-if="notice" class="notice ok">{{ notice }}</div>
    <div class="overview"><div><small>已安装</small><b>{{ stats.installed }}</b></div><div><small>待审批</small><b class="warn">{{ stats.pending }}</b></div><div><small>错误</small><b class="bad">{{ stats.errors }}</b></div></div>
    <div class="tabs"><button v-for="item in [{k:'installed',l:'已安装'},{k:'pending',l:'待审批'},{k:'permissions',l:'权限'},{k:'errors',l:'错误'}]" :key="item.k" type="button" :class="{ on: tab === item.k }" @click="tab = item.k as typeof tab">{{ item.l }}</button></div>
    <div v-if="tab === 'permissions'" class="permission-list"><div v-for="[permission, names] in permissions" :key="permission" class="permission"><b>{{ permission }}</b><span>{{ names.join(' / ') }}</span></div><div v-if="!permissions.length" class="empty">暂无权限记录</div></div>
    <div v-else-if="tab === 'errors'" class="permission-list"><div v-for="item in errors" :key="item.id" class="permission"><b>{{ item.plugin }}</b><span>{{ item.message }} · {{ item.at }}</span></div><div v-if="!errors.length" class="empty">暂无错误</div></div>
    <div v-else class="grid">
      <article v-for="plugin in visible" :key="plugin.id" class="card" :class="{ pending: plugin.pending }">
        <div class="card-head"><span class="icon">▣</span><div><b>{{ plugin.name }} · {{ plugin.slug }}</b><small>v{{ plugin.version }} · {{ plugin.description }}</small></div><span v-if="plugin.pending" class="state warn">待审批</span><span v-else class="state" :class="{ on: plugin.enabled }">{{ plugin.enabled ? '启用' : '停用' }}</span></div>
        <div class="tags"><span v-for="permission in plugin.permissions" :key="permission">{{ permission }}</span></div>
        <div class="actions">
          <template v-if="plugin.pending"><button type="button" class="primary" @click="action(plugin, 'approve')">批准</button><button type="button" class="danger" @click="action(plugin, 'reject')">拒绝</button></template>
          <button v-else class="switch" type="button" role="switch" :aria-checked="plugin.enabled" :class="{ on: plugin.enabled }" @click="toggle(plugin)"><i></i></button>
        </div>
      </article>
      <div v-if="!visible.length" class="empty">{{ tab === 'pending' ? '没有待审批插件' : '暂无已安装插件' }}</div>
    </div>
    <div v-if="showImport" class="mask" @click.self="showImport = false">
      <div class="modal">
        <header><b>安装插件</b><button type="button" @click="showImport = false">×</button></header>
        <p>支持 .hoshinoumi / .zip 插件包、plugin.json、插件网址。安装后写权限需 owner 审批。</p>
        <label class="field">插件网址<input v-model="importUrl" placeholder="https://example.com/plugin.hoshinoumi"></label>
        <button class="primary wide" type="button" :disabled="importing" @click="importFromUrl">从网址安装</button>
        <div class="or"><span>或</span></div>
        <input ref="importFile" class="file" type="file" accept=".hoshinoumi,.zip,.json" @change="importFromFile">
        <button class="wide ghost" type="button" :disabled="importing" @click="importFile?.click()">选择插件文件</button>
        <div class="hint">单包最大 20 MB；未知权限和路径穿越会被拒绝。</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.plugins-page{flex:1;min-height:0;overflow:auto;padding:22px 24px 26px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:7px;margin-bottom:10px;flex-wrap:wrap}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.add,.refresh{margin-left:0;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer}.add{margin-left:auto;background:#2563eb;border-color:#2563eb;color:#fff}.notice{border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}.notice.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c}.notice.ok{border:1px solid #cdeee0;background:#eefbf5;color:#168b63}
.overview{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-bottom:9px}.overview div{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 10px}.overview small{display:block;font-size:7px;color:#9aabc0}.overview b{display:block;font-size:16px;color:#1e3a5f;margin-top:2px}.overview b.warn{color:#b7791f}.overview b.bad{color:#b23b52}.tabs{display:flex;gap:4px;margin-bottom:9px}.tabs button{height:27px;border:1px solid #e3ebf7;border-radius:7px;background:#fff;color:#607795;font:8.5px inherit;padding:0 9px;cursor:pointer}.tabs button.on{background:#eef4ff;border-color:#c7dcff;color:#2563eb;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.card{background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:11px;display:flex;flex-direction:column}.card.pending{border-color:#f2d491;background:#fffdf7}.card-head{display:flex;align-items:flex-start;gap:7px}.icon{width:27px;height:27px;border-radius:8px;background:#eef4ff;color:#2563eb;display:grid;place-items:center;font-size:12px;flex:none}.card-head b{display:block;font-size:10px;color:#314a65}.card-head small{display:block;font-size:7.5px;color:#8a9bb0;margin-top:2px}.state{margin-left:auto;font-size:7px;color:#8a9bb0;border:1px solid #e3ebf7;border-radius:4px;padding:1px 5px;white-space:nowrap}.state.on{color:#168b63;border-color:#cdeee0;background:#eefbf5}.state.warn{color:#b7791f;border-color:#f2d491;background:#fff8e6}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:8px 0}.tags span{font-size:7px;color:#6b7c95;border:1px solid #e3ebf7;border-radius:4px;padding:1px 5px}.actions{display:flex;gap:5px;justify-content:flex-end;margin-top:auto}.actions button.primary,.actions button.danger{height:26px;border:0;border-radius:6px;background:#2563eb;color:#fff;font:8px inherit;padding:0 9px;cursor:pointer}.actions button.danger{background:#fff5f5;color:#b23b52;border:1px solid #fecaca}.switch{position:relative;width:38px;height:22px;border:0;border-radius:11px;background:#cbd5e1;cursor:pointer}.switch.on{background:#2563eb}.switch i{position:absolute;left:2px;top:2px;width:18px;height:18px;border-radius:50%;background:#fff;transition:left .2s}.switch.on i{left:18px}.permission-list{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:4px 11px}.permission{display:flex;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:1px solid #f1f5fb;font-size:8.5px}.permission:last-child{border-bottom:0}.permission b{color:#314a65}.permission span{color:#8a9bb0;text-align:right}.empty{border:1px dashed #cfe0f7;border-radius:10px;background:#fff;padding:20px;text-align:center;color:#9aabc0;font-size:9px;grid-column:1/-1}
.mask{position:fixed;inset:0;z-index:80;background:#0f172a52;display:grid;place-items:center;padding:20px}.modal{width:min(440px,100%);background:#fff;border-radius:14px;padding:15px;box-shadow:0 24px 60px #0f264e3d}.modal header{display:flex;align-items:center;margin-bottom:7px}.modal header b{font-size:13px;color:#1e3a5f}.modal header button{margin-left:auto;border:0;background:none;font-size:17px;color:#8a9bb0;cursor:pointer}.modal p{font-size:8.5px;color:#8a9bb0;line-height:1.6;margin:0 0 8px}.field{display:block;font-size:8px;color:#8a9bb0}.field input{display:block;width:100%;height:29px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;padding:0 8px;font:9px inherit;outline:0;box-sizing:border-box;margin-top:3px}.wide{width:100%;height:29px;border-radius:7px;font:9px inherit;cursor:pointer;margin-top:6px}.primary{height:29px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;cursor:pointer}.ghost{border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb}.file{display:none}.or{text-align:center;font-size:8px;color:#9aabc0;margin:5px 0}.hint{font-size:7.5px;color:#9aabc0;line-height:1.6;margin-top:7px}
@media(max-width:1180px){.plugins-page{padding:18px 18px 22px}.grid{grid-template-columns:1fr}}
.overview div{animation:pluginIn .26s cubic-bezier(.22,1,.36,1) both}.overview div:nth-child(2){animation-delay:.04s}.overview div:nth-child(3){animation-delay:.08s}.tabs{animation:pluginIn .24s cubic-bezier(.22,1,.36,1) both}.card{animation:pluginIn .28s cubic-bezier(.22,1,.36,1) both}.card:nth-child(2){animation-delay:.04s}.card:nth-child(3){animation-delay:.08s}.card:nth-child(4){animation-delay:.12s}.permission-list{animation:pluginIn .26s cubic-bezier(.22,1,.36,1) both}.permission:nth-child(2){animation-delay:.03s}.permission:nth-child(3){animation-delay:.06s}@keyframes pluginIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.overview div,.tabs,.card,.permission-list{animation:none}}
</style>
