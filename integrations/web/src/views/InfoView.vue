<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

type Section = 'config' | 'backup' | 'plan' | 'account' | 'reading' | 'gateway'
const section = ref<Section>('config')
const status = ref<{ status?: string; master_qq?: string; schema?: number; version?: string; uptime_seconds?: number; napcat?: { connected?: boolean; port?: number; mode?: string }; db?: { engine?: string; tables?: number; size_mb?: number }; backup?: { last_at?: string; size_mb?: number; kept?: number; checksum?: string } } | null>(null)
const error = ref('')
interface BalanceInfo { currency?: string; total_balance?: string; granted_balance?: string; topped_up_balance?: string }
const balance = ref<{ is_available?: boolean; balance_infos?: BalanceInfo[]; fetched_at?: string } | null>(null)
const balanceError = ref('')
const balanceCurrency = computed(() => balance.value?.balance_infos?.[0]?.currency || 'CNY')
const balanceTotal = computed(() => balance.value?.balance_infos?.[0]?.total_balance || '—')
const balanceGranted = computed(() => balance.value?.balance_infos?.[0]?.granted_balance || '0.00')
const balanceTopped = computed(() => balance.value?.balance_infos?.[0]?.topped_up_balance || '0.00')
async function loadBalance() { try { balance.value = await http.get('/api/balance'); balanceError.value = '' } catch { balance.value = null; balanceError.value = 'API 余额不可用' } }
interface Backup { manifest?: { created_at?: string; counts?: Record<string, number>; checksums?: Record<string, string> }; db?: unknown }
const backup = ref<Backup | null>(null)
const exported = ref<unknown>(null)
const importText = ref('')
const importState = ref('')
const importBusy = ref(false)
const progress = ref(0)
const progressLabel = ref('')
interface Drill { entries: number; bytes: number; checksum: string; elapsed_ms: number }
const drill = ref<Drill | null>(null)
const drillStep = ref(Number(localStorage.getItem('hoshinoumi.drill.step') || 0))
const drillBusy = ref(false)
async function runDrill() {
  drillBusy.value = true
  try {
    for (const [step, label] of [[1, '生成大备份'], [2, '计算校验和'], [3, '恢复演练']] as const) {
      drillStep.value = step; localStorage.setItem('hoshinoumi.drill.step', String(step)); progressLabel.value = label; progress.value = step * 30
      await new Promise(resolve => setTimeout(resolve, 180))
    }
    drill.value = await http.post<Drill>('/api/backup/drill', { size: 2000 })
    progress.value = 100; progressLabel.value = '迁移演练完成'
  } catch { importState.value = '迁移演练失败：无后端连接' } finally { drillBusy.value = false }
}
const backupBusy = ref(false)
async function importBackup(dryRun: boolean) {
  let payload: unknown
  try { payload = JSON.parse(importText.value) } catch { importState.value = 'JSON 格式错误'; return }
  importBusy.value = true
  progress.value = 20; progressLabel.value = dryRun ? '校验 schema / checksums' : '校验并恢复'
  try {
    await http.post('/api/backup/import', { backup: payload, dry_run: dryRun })
    progress.value = 100; progressLabel.value = dryRun ? '校验通过' : '恢复完成'
    if (dryRun) importState.value = '校验通过，可以恢复'
    else { importState.value = '已恢复；可回滚'; await load() }
  } catch (e) { importState.value = e instanceof Error ? e.message : '导入失败' } finally { importBusy.value = false }
}
async function rollbackBackup() {
  importBusy.value = true
  try { await http.post('/api/backup/rollback', {}); importState.value = '已回滚到导入前'; await load() } catch (e) { importState.value = e instanceof Error ? e.message : '回滚失败' } finally { importBusy.value = false }
}
function onImportFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => { importText.value = String(reader.result || ''); importState.value = '已读取文件，先校验' }
  reader.readAsText(file)
}
async function exportBackup() {
  backupBusy.value = true
  progress.value = 20; progressLabel.value = '生成 manifest / DB / data'
  try {
    const data = await http.get<Backup & { ok: boolean }>('/api/backup/export')
    progress.value = 75; progressLabel.value = '计算 checksums'
    backup.value = data
    exported.value = data
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'hoshinoumi-backup.json'; a.click(); URL.revokeObjectURL(a.href)
    progress.value = 100; progressLabel.value = '导出完成'
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
const uptimeLabel = computed(() => { const seconds = Number(status.value?.uptime_seconds || 0); if (!seconds) return '—'; const days = Math.floor(seconds / 86400); const hours = Math.floor((seconds % 86400) / 3600); return days ? `${days} 天 ${hours} 小时` : `${hours} 小时` })
onMounted(() => { void load(); void loadBalance() })
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
    <div class="runtime-grid">
      <div class="runtime-card"><small>实例</small><b>{{ status?.version || '—' }}</b><span>schema {{ status?.schema ?? '—' }} · {{ uptimeLabel }}</span></div>
      <div class="runtime-card"><small>存储</small><b>{{ status?.db?.engine || '—' }}</b><span>{{ status?.db?.tables ?? '—' }} 张表 · {{ status?.db?.size_mb ?? '—' }} MB</span></div>
      <div class="runtime-card"><small>NapCat</small><b :class="status?.napcat?.connected ? 'on' : 'off'">{{ status?.napcat?.connected ? '已连接' : '未连接' }}</b><span>WS {{ status?.napcat?.port ?? '—' }} · {{ status?.napcat?.mode || '—' }}</span></div>
      <div class="runtime-card"><small>备份</small><b>{{ status?.backup?.last_at || '—' }}</b><span>{{ status?.backup?.size_mb ?? '—' }} MB · 保留 {{ status?.backup?.kept ?? '—' }} 份</span></div>
    </div>
    <div class="balance-card">
      <div><small>API 余额</small><b>{{ balanceCurrency }} {{ balanceTotal }}</b><span v-if="balance">赠送 {{ balanceGranted }} · 充值 {{ balanceTopped }}<template v-if="balance.fetched_at"> · {{ balance.fetched_at }}</template></span><span v-else class="muted">{{ balanceError || '读取中…' }}</span></div>
      <button type="button" :disabled="!balance" @click="loadBalance">刷新余额</button>
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
        <div v-if="progress" class="progress"><i :style="{ width: progress + '%' }" /><small>{{ progressLabel }} · {{ progress }}%</small></div>
        <div class="cli-note">CLI：<code>python scripts/backup.py export/validate/import/rollback</code></div>
        <div class="drill"><button type="button" class="primary" :disabled="drillBusy" @click="runDrill">{{ drillBusy ? '演练中…' : drillStep > 0 && drillStep < 3 ? '继续迁移演练' : '迁移演练（2000 条）' }}</button><div v-if="drill" class="drill-info">2000 条 · {{ (drill.bytes / 1024).toFixed(1) }} KB · {{ drill.elapsed_ms }}ms · {{ drill.checksum.slice(0, 12) }}…</div><div class="drill-note">断点记录：step {{ drillStep }}/3；重新打开页面可继续。</div></div>
        <button type="button" class="primary" :disabled="backupBusy" @click="exportBackup">{{ backupBusy ? '导出中…' : '导出实例' }}</button>
        <div class="import-box"><div class="import-title">导入备份（JSON）</div><label class="file-pick">选择备份文件<input type="file" accept=".json,application/json" @change="onImportFile"></label><textarea v-model="importText" placeholder="或粘贴导出的 JSON"></textarea><div class="import-actions"><button type="button" :disabled="importBusy || !importText.trim()" @click="importBackup(true)">校验</button><button type="button" class="danger" :disabled="importBusy || !importText.trim()" @click="importBackup(false)">恢复</button><button type="button" :disabled="importBusy" @click="rollbackBackup">回滚</button></div><div v-if="importState" class="import-state">{{ importState }}</div></div>
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
.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:11px}.panel-head{display:flex;align-items:baseline;gap:7px;margin-bottom:7px}.progress{display:block!important;padding:3px 0!important;border:0!important}.progress i{display:block;height:4px;border-radius:3px;background:#2563eb;transition:width .2s}.progress small{display:block;font-size:7.5px;color:#8a9bb0;margin-top:3px}.cli-note{font-size:7.5px;color:#8a9bb0;line-height:1.6}.cli-note code{font-family:ui-monospace,monospace;color:#526982}.drill{margin-top:9px;border-top:1px solid #f1f5fb;padding-top:8px}.drill .primary{height:34px;min-height:34px;max-height:34px;font-size:10px}.drill-info{font-size:7.5px;color:#405872;margin-top:5px;line-height:1.6}.drill-note{font-size:7px;color:#9aabc0;margin-top:2px}.import-box{display:grid!important;width:100%!important;max-width:none;justify-self:stretch;grid-template-columns:minmax(0,1fr);margin-top:9px;border-top:1px solid #f1f5fb;padding-top:9px;display:grid;gap:6px;min-width:0}.import-title{font-size:8px;color:#8a9bb0}.file-pick{display:block;text-align:center;border:1px solid #dbe8ff;border-radius:7px;background:#f4f9ff;color:#2563eb;font-size:9px;line-height:28px;height:28px;cursor:pointer}.file-pick input{display:none}.import-box textarea{width:100%;min-width:0;box-sizing:border-box;min-height:64px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;padding:6px;font:8px ui-monospace,monospace;resize:vertical}.import-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;min-width:0}.import-actions button{min-width:0;height:28px;border:1px solid #dbe8ff;border-radius:6px;background:#f4f9ff;color:#2563eb;font:9px inherit;line-height:1;white-space:nowrap;cursor:pointer;padding:0 2px}.import-actions button.danger{color:#b91c1c;border-color:#fecaca;background:#fff5f5}.import-state{font-size:8px;color:#6b7c95}.primary{width:100%;height:34px;min-height:34px;max-height:34px;margin-top:8px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;font-weight:700;cursor:pointer}.panel-head b{font-size:10px;color:#1e3a5f}.panel-head span{font-size:7.5px;color:#9aabc0}.rows>div{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #f1f5fb}.rows>div:last-child{border-bottom:0}.rows>div>span{font-size:8.5px;color:#8a9bb0}.rows>div>b{font-size:8.5px;color:#405872;font-weight:600;text-align:right;word-break:break-all}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
.runtime-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-bottom:10px}.runtime-card{background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:9px}.runtime-card small{display:block;font-size:7.5px;color:#9aabc0;letter-spacing:.06em}.runtime-card b{display:block;font-size:12px;color:#1e3a5f;margin-top:3px}.runtime-card b.on{color:#1f9d6b}.runtime-card b.off{color:#b23b52}.runtime-card span{display:block;font-size:7.5px;color:#8a9bb0;margin-top:3px;line-height:1.5}.balance-card{display:flex;align-items:center;gap:10px;background:linear-gradient(135deg,#eff6ff,#fff);border:1px solid #dbe8ff;border-radius:11px;padding:11px 12px;margin-bottom:10px}.balance-card small{display:block;font-size:7.5px;color:#7d8ca3;letter-spacing:.08em}.balance-card b{display:block;font-size:18px;color:#1d4ed8;margin-top:2px;letter-spacing:-.02em}.balance-card span{display:block;font-size:8px;color:#8a9bb0;margin-top:2px}.balance-card span.muted{color:#a2b2c6}.balance-card button{margin-left:auto;height:28px;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;font:9px inherit;padding:0 9px;cursor:pointer}.balance-card button:disabled{opacity:.55;cursor:not-allowed}@media(min-width:821px){.info{padding:22px 24px;max-width:none;width:100%}.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.overview{max-width:none}}
.head,.overview,.runtime-grid,.grid,.panel{animation:info-in .28s cubic-bezier(.22,1,.36,1) both}.overview{animation-delay:.03s}.runtime-grid{animation-delay:.05s}.grid{animation-delay:.07s}.panel{animation-delay:.09s}.runtime-card{animation:info-in .24s cubic-bezier(.22,1,.36,1) both}.runtime-card:nth-child(2){animation-delay:.03s}.runtime-card:nth-child(3){animation-delay:.06s}.runtime-card:nth-child(4){animation-delay:.09s}.entry{transition:background .18s,border-color .18s,transform .18s}.entry:hover{transform:translateY(-1px)}@keyframes info-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.head,.overview,.runtime-grid,.grid,.panel,.runtime-card{animation:none}}
</style>
