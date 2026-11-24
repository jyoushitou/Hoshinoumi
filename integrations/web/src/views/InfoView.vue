<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

type Section = 'config' | 'backup' | 'plan' | 'account' | 'reading' | 'gateway'
const section = ref<Section>('config')
const status = ref<{ status?: string; master_qq?: string; schema?: number } | null>(null)
const error = ref('')
interface Backup { manifest?: { created_at?: string; counts?: Record<string, number>; checksums?: Record<string, string> }; db?: unknown }
const backup = ref<Backup | null>(null)
const backupBusy = ref(false)
async function exportBackup() {
  backupBusy.value = true
  try {
    const data = await http.get<Backup & { ok: boolean }>('/api/backup/export')
    backup.value = data
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'hoshinoumi-backup.json'; a.click(); URL.revokeObjectURL(a.href)
  } catch { error.value = '导出失败：无后端连接' } finally { backupBusy.value = false }
}
const sections: Array<{ key: Section; title: string; desc: string; icon: string }> = [
  { key: 'config', title: '配置', desc: '后端 / 存储 / 可见性', icon: '⚙' },
  { key: 'backup', title: '备份', desc: '实例导出 / 导入 / 回滚', icon: '⇩' },
  { key: 'plan', title: '计划', desc: '周计划 / 定时任务', icon: '▦' },
  { key: 'account', title: '账号', desc: '主人 / 成员 / 权限', icon: '◇' },
  { key: 'reading', title: '阅读', desc: '书架 / 当前阅读', icon: '◫' },
  { key: 'gateway', title: '网关', desc: '连接 / 路由 / 健康', icon: '⌘' },
]
const current = computed(() => sections.find(item => item.key === section.value)!)
async function load() {
  try { status.value = await http.get('/api/status'); error.value = '' } catch { status.value = null; error.value = '无后端连接' }
}
onMounted(load)
</script>

<template>
  <section class="info">
    <header class="head"><div><h1>信息</h1><p>运行 / 配置 / 备份 / 账号 / 阅读 / 网关</p></div><span class="conn" :class="{ off: !status }">{{ status ? '已连接' : '离线' }}</span></header>
    <div v-if="error" class="notice">{{ error }}</div>
    <div class="overview">
      <div><small>后端</small><b>{{ status?.status || '—' }}</b></div>
      <div><small>主人 QQ</small><b>{{ status?.master_qq || '—' }}</b></div>
      <div><small>schema</small><b>{{ status?.schema ?? '—' }}</b></div>
    </div>
    <div class="grid">
      <button v-for="item in sections" :key="item.key" type="button" class="entry" :class="{ on: section === item.key }" @click="section = item.key"><span class="icon">{{ item.icon }}</span><span><b>{{ item.title }}</b><small>{{ item.desc }}</small></span><em>›</em></button>
    </div>
    <div class="panel">
      <div class="panel-head"><b>{{ current.title }}</b><span>{{ current.desc }}</span></div>
      <div v-if="section === 'config'" class="rows"><div><span>后端地址</span><b>{{ (http as any).baseUrl || '当前站点' }}</b></div><div><span>可见性</span><b>主人全量 / 成员隔离</b></div><div><span>存储</span><b>本机实例</b></div></div>
      <div v-else-if="section === 'backup'" class="rows">
        <div><span>导出内容</span><b>manifest / DB / data / checksums</b></div>
        <div v-if="backup"><span>创建时间</span><b>{{ backup.manifest?.created_at }}</b></div>
        <div v-if="backup"><span>条目</span><b>记忆 {{ backup.manifest?.counts?.memories }} · 日记 {{ backup.manifest?.counts?.diary }}</b></div>
        <div v-if="backup"><span>data sha256</span><b>{{ backup.manifest?.checksums?.data?.slice(0, 16) }}…</b></div>
        <button type="button" class="primary" :disabled="backupBusy" @click="exportBackup">{{ backupBusy ? '导出中…' : '导出实例' }}</button>
      </div>
      <div v-else-if="section === 'plan'" class="rows"><div><span>周计划</span><b>ISO 年周</b></div><div><span>定时任务</span><b>3 个</b></div></div>
      <div v-else-if="section === 'account'" class="rows"><div><span>主人</span><b>{{ status?.master_qq || '—' }}</b></div><div><span>成员</span><b>按 target 隔离</b></div></div>
      <div v-else-if="section === 'reading'" class="rows"><div><span>当前阅读</span><b>《十日终焉》</b></div><div><span>进度</span><b>60%</b></div></div>
      <div v-else class="rows"><div><span>连接</span><b>{{ status ? '正常' : '离线' }}</b></div><div><span>路由</span><b>本机 / 局域网</b></div></div>
    </div>
  </section>
</template>

<style scoped>
.info{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.conn{margin-left:auto;font-size:8px;color:#1f9d6b;border:1px solid #cdeee0;background:#eefbf5;border-radius:10px;padding:3px 7px}.conn.off{color:#8a9bb0;border-color:#e3ebf7;background:#f8fbff}
.overview{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:10px}.overview div{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:9px}.overview small{display:block;font-size:7.5px;color:#9aabc0}.overview b{display:block;font-size:12px;color:#1e3a5f;margin-top:3px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:10px}.entry{display:flex;align-items:center;gap:7px;text-align:left;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:9px;cursor:pointer}.entry.on{background:#eef4ff;border-color:#c7dcff}.icon{width:26px;height:26px;border-radius:8px;background:#f4f8ff;display:grid;place-items:center;color:#52708f;flex:none}.entry b{display:block;font-size:9.5px;color:#314a65}.entry small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.entry em{margin-left:auto;font-style:normal;color:#9aabc0}
.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:11px}.panel-head{display:flex;align-items:baseline;gap:7px;margin-bottom:7px}.primary{width:100%;height:30px;margin-top:8px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;font-weight:700;cursor:pointer}.panel-head b{font-size:10px;color:#1e3a5f}.panel-head span{font-size:7.5px;color:#9aabc0}.rows div{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #f1f5fb}.rows div:last-child{border-bottom:0}.rows span{font-size:8.5px;color:#8a9bb0}.rows b{font-size:8.5px;color:#405872;font-weight:600;text-align:right;word-break:break-all}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
@media(min-width:821px){.info{padding:22px 24px;max-width:980px}.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.overview{max-width:620px}}
.head,.overview,.grid,.panel{animation:info-in .28s cubic-bezier(.22,1,.36,1) both}.overview{animation-delay:.03s}.grid{animation-delay:.06s}.panel{animation-delay:.09s}.entry{transition:background .18s,border-color .18s,transform .18s}.entry:hover{transform:translateY(-1px)}@keyframes info-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.head,.overview,.grid,.panel{animation:none}}
</style>
