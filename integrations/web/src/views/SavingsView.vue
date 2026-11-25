<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { http } from '@/api/client'
import { useIsOwner } from '@/composables/useIsOwner'
import SavingsInitModal from '@/components/SavingsInitModal.vue'

interface Account { account: string; balance_cents: number }
interface Entry { id?: number; account: string; kind: string; amount_cents: number; category?: string; note?: string; occurred_at?: string }
interface Savings { total_cents: number; accounts: Account[]; entries: Entry[] }
interface Overview { total_cents: number; frozen_cents: number; available_cents: number }
interface Goal { id: number; name: string; target_cents: number; saved_cents: number; deadline?: string }
interface Held { id: number; name: string; amount_cents?: number; code?: string; shares?: number; value_cents?: number; rate?: number; due?: string; matures_at?: string }
interface MonthRow { month: string; income_cents: number; expense_cents: number }
interface AuditRow { at: string; user: string; method: string; path: string; status: number }
interface Snapshot { id: number; taken_at: string; total_cents: number; note?: string; accounts?: Account[] }
interface ReconcileRow { account: string; snapshot_cents: number; current_cents: number; difference_cents: number }
interface Reconcile { snapshot: Snapshot | null; accounts: ReconcileRow[]; difference_cents: number }
interface Health { target?: number; burn?: number; weight?: number; meals?: Array<{ id?: number; name?: string; kcal?: number; time?: string }> }
interface HealthPayload { data?: Health; intake?: number; remaining?: number }
const isOwner = useIsOwner()
const initOpen = ref(false)
const initAccounts = ref<string[]>([])
const data = ref<Savings | null>(null)
const overview = ref<Overview | null>(null)
const goals = ref<Goal[]>([])
const frozen = ref<Held[]>([])
const fixed = ref<Held[]>([])
const funds = ref<Held[]>([])
const monthly = ref<MonthRow[]>([])
const audit = ref<AuditRow[]>([])
const snapshots = ref<Snapshot[]>([])
const reconcile = ref<Reconcile | null>(null)
const snapshotBusy = ref(false)
const health = ref<Health | null>(null)
const healthIntake = ref(0)
const healthRemaining = ref(0)
const healthOpen = ref(true)
const healthBusy = ref(false)
const mealName = ref('')
const mealKcal = ref('')
const loading = ref(false)
const error = ref('')
const amount = ref('')
const note = ref('')
const kind = ref<'expense' | 'income'>('expense')
const account = ref('银行卡')
const defaultAccounts = ['银行卡', '微信', '支付宝', '现金']
const saving = ref(false)
const dueBills = computed(() => frozen.value.filter((item: Held) => item.due).sort((a: Held, b: Held) => String(a.due).localeCompare(String(b.due))))
async function allocate(goal: Goal) {
  const raw = window.prompt(`向「${goal.name}」分配多少元？`)
  if (raw === null) return
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) { error.value = '分配金额无效'; return }
  try { await http.post(`/api/savings/goals/${goal.id}/allocate`, { amount: value }); await load() } catch (e) { error.value = e instanceof Error ? e.message : '分配失败' }
}
async function unfreeze(item: Held) {
  if (!window.confirm(`解冻「${item.name}」？`)) return
  try { await http.post(`/api/savings/frozen/${item.id}/unfreeze`, {}); await load() } catch (e) { error.value = e instanceof Error ? e.message : '解冻失败' }
}
const fmt = (cents: number) => `¥${(Number(cents || 0) / 100).toFixed(2)}`
const accounts = computed(() => data.value?.accounts || [])
const accountOptions = computed(() => accounts.value.length ? accounts.value.map(item => item.account) : defaultAccounts)
const entries = computed(() => data.value?.entries || [])
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [main, ov, gl, fz, fx, fd, mo, au] = await Promise.allSettled([
      http.get<Savings>('/api/savings'),
      http.get<Overview>('/api/savings/overview'),
      http.get<{ data?: Goal[] }>('/api/savings/goals'),
      http.get<{ data?: Held[] }>('/api/savings/frozen'),
      http.get<{ data?: Held[] }>('/api/savings/fixed'),
      http.get<{ data?: Held[] }>('/api/savings/funds'),
      http.get<{ data?: MonthRow[] }>('/api/savings/monthly'),
      http.get<{ data?: AuditRow[] }>('/api/finance/audit'),
    ])
    data.value = main.status === 'fulfilled' ? main.value : null
    overview.value = ov.status === 'fulfilled' ? ov.value : null
    goals.value = gl.status === 'fulfilled' ? gl.value.data || [] : []
    frozen.value = fz.status === 'fulfilled' ? fz.value.data || [] : []
    fixed.value = fx.status === 'fulfilled' ? fx.value.data || [] : []
    funds.value = fd.status === 'fulfilled' ? fd.value.data || [] : []
    monthly.value = mo.status === 'fulfilled' ? mo.value.data || [] : []
    audit.value = au.status === 'fulfilled' ? au.value.data || [] : []
  } catch (e) { error.value = e instanceof Error ? e.message : '存钱数据加载失败' } finally { loading.value = false }
}
async function addEntry() {
  const value = Number(amount.value)
  if (!Number.isFinite(value) || value <= 0) { error.value = '请输入有效金额'; return }
  if (value > 100000000) { error.value = '单笔金额过大'; return }
  if (note.value.length > 60) { error.value = '备注不能超过 60 字'; return }
  if (!accountOptions.value.includes(account.value)) { error.value = '账户不存在'; return }
  saving.value = true
  error.value = ''
  try {
    await http.post('/api/savings/entries', { amount: value, kind: kind.value, account: account.value, note: note.value.trim() })
    amount.value = ''
    note.value = ''
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '记录失败' } finally { saving.value = false }
}
function exportCsv() {
  const header = ['日期', '账户', '类型', '金额(元)', '备注']
  const lines = entries.value.map(entry => [String(entry.occurred_at || '').slice(0, 10), entry.account || '', entry.kind || '', (entry.amount_cents / 100).toFixed(2), entry.note || entry.category || ''])
  const csv = [header, ...lines].map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([new Uint8Array([0xef, 0xbb, 0xbf]), csv], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'hoshinoumi-savings.csv'; link.click(); URL.revokeObjectURL(link.href)
}
async function loadReconcile() {
  const [list, diff] = await Promise.allSettled([http.get<{ data?: Snapshot[] }>('/api/savings/snapshots'), http.get<Reconcile>('/api/savings/reconcile')])
  snapshots.value = list.status === 'fulfilled' ? list.value.data || [] : []
  reconcile.value = diff.status === 'fulfilled' ? diff.value : null
}
async function createSnapshot() {
  snapshotBusy.value = true; error.value = ''
  try { await http.post('/api/savings/snapshots', { note: '手动快照' }); await loadReconcile() } catch (e) { error.value = e instanceof Error ? e.message : '快照失败' } finally { snapshotBusy.value = false }
}
async function loadHealth() {
  try {
    const r = await http.get<HealthPayload>('/api/health/summary')
    health.value = r.data || null
    healthIntake.value = Number(r.intake || 0)
    healthRemaining.value = Number(r.remaining || 0)
  } catch { health.value = null }
}
async function addMeal() {
  const name = mealName.value.trim(); const kcal = Number(mealKcal.value)
  if (!name || !Number.isFinite(kcal) || kcal <= 0) return
  healthBusy.value = true
  try {
    await http.post('/api/health/meals', { name, kcal })
    mealName.value = ''; mealKcal.value = ''
    await loadHealth()
  } finally { healthBusy.value = false }
}
async function loadInit() {
  if (!isOwner.value) return
  try {
    const state = await http.get<{ initialized?: boolean; accounts?: string[] }>('/api/savings/init')
    initAccounts.value = Array.isArray(state.accounts) && state.accounts.length ? state.accounts : defaultAccounts
    initOpen.value = !state.initialized
  } catch { initOpen.value = false }
}
async function finishInit() {
  initOpen.value = false
  await load()
  await loadReconcile()
}
onMounted(() => { if (isOwner.value) { void load(); void loadReconcile(); void loadInit(); void loadHealth() } })
watch(isOwner, value => { if (value && !data.value) { void load(); void loadInit() } })
</script>

<template>
  <section class="savings" :class="{ locked: !isOwner }">
    <div v-if="!isOwner" class="owner-lock">财务数据仅主人可见</div>
    <header class="head"><div><h1>存钱</h1><p>总余额 / 账户 / 流水</p></div><div class="head-actions"><button class="refresh" type="button" :disabled="!entries.length" @click="exportCsv">导出 CSV</button><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></div></header>
    <div v-if="error" class="error">{{ error }}</div>
    <div class="hero"><small>总余额</small><b>{{ fmt(overview?.total_cents ?? data?.total_cents ?? 0) }}</b><span>可用 {{ fmt(overview?.available_cents ?? data?.total_cents ?? 0) }} · 冻结 {{ fmt(overview?.frozen_cents || 0) }} · {{ accounts.length }} 个账户</span></div>
    <div class="accounts">
      <div v-for="item in accounts" :key="item.account" class="account"><b>{{ item.account }}</b><span>{{ fmt(item.balance_cents) }}</span></div>
    </div>
    <div class="panel recon-panel">
      <div class="list-title">账户对账<span>{{ snapshots.length }} 个快照</span></div>
      <div class="recon-head"><span>最近快照：{{ snapshots[0]?.taken_at || '暂无' }}</span><span>总差异：<b :class="{ diff: reconcile?.difference_cents }">{{ fmt(reconcile?.difference_cents || 0) }}</b></span><button class="mini" type="button" :disabled="snapshotBusy" @click="createSnapshot">{{ snapshotBusy ? '快照中…' : '拍快照' }}</button></div>
      <div v-if="reconcile?.accounts?.length" class="recon-table"><div class="recon-row recon-th"><span>账户</span><span>快照</span><span>当前</span><span>差异</span></div><div v-for="row in reconcile.accounts" :key="row.account" class="recon-row"><b>{{ row.account }}</b><span>{{ fmt(row.snapshot_cents) }}</span><span>{{ fmt(row.current_cents) }}</span><em :class="{ diff: row.difference_cents }">{{ row.difference_cents > 0 ? '+' : '' }}{{ fmt(row.difference_cents) }}</em></div></div>
      <div v-else class="recon-empty">拍一张快照后，可对比各账户当前余额与快照差异。</div>
    </div>
    <div v-if="goals.length" class="panel"><div class="list-title">存钱目标<span>{{ goals.length }}</span></div><div v-for="goal in goals" :key="goal.id" class="goal"><div><b>{{ goal.name }}</b><small>{{ goal.deadline || '无期限' }}</small></div><em>{{ fmt(goal.saved_cents) }} / {{ fmt(goal.target_cents) }}</em><button type="button" @click="allocate(goal)">存入</button><i><span :style="{ width: Math.min(100, goal.saved_cents / Math.max(1, goal.target_cents) * 100) + '%' }" /></i></div></div>
    <div v-if="frozen.length || fixed.length || funds.length" class="panel"><div class="list-title">资金位置<span>{{ frozen.length + fixed.length + funds.length }}</span></div><div v-for="item in frozen" :key="'f'+item.id" class="entry"><div><b>{{ item.name }}</b><small>冻结 · 到期 {{ item.due || '—' }}</small></div><em>{{ fmt(item.amount_cents || 0) }}</em><button class="mini" type="button" @click="unfreeze(item)">解冻</button></div><div v-for="item in fixed" :key="'d'+item.id" class="entry"><div><b>{{ item.name }}</b><small>定期 {{ item.rate || 0 }}% · {{ item.matures_at || '' }}</small></div><em>{{ fmt(item.amount_cents || 0) }}</em></div><div v-for="item in funds" :key="'u'+item.code" class="entry"><div><b>{{ item.name }}</b><small>基金 {{ item.code }} · {{ item.shares || 0 }} 份</small></div><em>{{ fmt(item.value_cents || 0) }}</em></div></div>
    <div v-if="dueBills.length" class="bill-note">缴费提醒：{{ dueBills.map(x => x.name + ' ' + fmt(x.amount_cents || 0) + ' · ' + x.due).join('；') }}</div>
    <div class="form">
      <div class="seg"><button type="button" :class="{ on: kind === 'expense' }" @click="kind = 'expense'">支出</button><button type="button" :class="{ on: kind === 'income' }" @click="kind = 'income'">收入</button></div>
      <select v-model="account" class="account-select"><option v-for="name in accountOptions" :key="name" :value="name">{{ name }}</option></select>
      <input v-model="amount" inputmode="decimal" placeholder="金额">
      <input v-model="note" placeholder="备注（可选）">
      <button class="primary" type="button" :disabled="saving" @click="addEntry">{{ saving ? '保存中…' : '记一笔' }}</button>
    </div>
    <div v-if="monthly.length" class="panel"><div class="list-title">月流水<span>{{ monthly.length }} 个月</span></div><div class="chart"><div v-for="row in monthly" :key="row.month" class="bar-group"><div class="bars"><i class="in" :style="{ height: Math.max(4, row.income_cents / Math.max(1, ...monthly.map(m => Math.max(m.income_cents, m.expense_cents))) * 48) + 'px' }" /><i class="out" :style="{ height: Math.max(4, row.expense_cents / Math.max(1, ...monthly.map(m => Math.max(m.income_cents, m.expense_cents))) * 48) + 'px' }" /></div><small>{{ row.month.slice(5) }}</small></div></div><div class="legend"><span><i class="in" />收入</span><span><i class="out" />支出</span></div></div>
    <div class="panel"><div class="list-title">权限审计<span>{{ audit.length }}</span></div><div v-if="!audit.length" class="empty">暂无越权访问记录</div><div v-for="row in audit.slice(0, 5)" :key="row.at + row.path" class="entry"><div><b>{{ row.method }} {{ row.path }}</b><small>{{ row.user }} · {{ row.at }}</small></div><em class="danger-text">403</em></div></div>
    <div class="entries">
      <div class="list-title">流水<span>{{ entries.length }}</span></div>
      <div v-if="!entries.length" class="empty">暂无流水</div>
      <div v-for="(entry, index) in entries" :key="entry.id ?? index" class="entry">
        <div><b>{{ entry.note || entry.category || entry.kind }}</b><small>{{ entry.account }} · {{ String(entry.occurred_at || '').slice(0, 10) }}</small></div>
        <em :class="{ income: entry.amount_cents > 0 }">{{ entry.amount_cents > 0 ? '+' : '' }}{{ fmt(entry.amount_cents) }}</em>
      </div>
    </div>
    <div class="panel health-panel">
      <div class="list-title health-title">健康 / 热量
        <button type="button" class="health-toggle" @click="healthOpen = !healthOpen">{{ healthOpen ? '收起' : '展开' }}</button>
      </div>
      <div v-if="healthOpen" class="health-body">
        <div v-if="health" class="health-stats">
          <div><small>今日摄入</small><b>{{ healthIntake }} kcal</b></div>
          <div><small>目标</small><b>{{ health.target ?? 0 }} kcal</b></div>
          <div><small>运动</small><b>{{ health.burn ?? 0 }} kcal</b></div>
          <div><small>剩余</small><b>{{ healthRemaining }} kcal</b></div>
          <div><small>体重</small><b>{{ health.weight ?? '—' }} kg</b></div>
        </div>
        <div v-else class="empty">健康数据未配置</div>
        <div v-if="health?.meals?.length" class="health-meals">
          <div v-for="meal in health.meals" :key="meal.id" class="health-meal"><span>{{ meal.name }}</span><em>{{ meal.kcal }} kcal · {{ meal.time || '' }}</em></div>
        </div>
        <div class="health-form">
          <input v-model="mealName" placeholder="食物">
          <input v-model="mealKcal" inputmode="decimal" placeholder="热量 kcal">
          <button type="button" :disabled="healthBusy" @click="addMeal">{{ healthBusy ? '保存中…' : '记录' }}</button>
        </div>
      </div>
    </div>
    <SavingsInitModal :open="initOpen" :accounts="initAccounts" @close="initOpen = false" @done="finishInit" />
  </section>
</template>

<style scoped>
.savings.locked > *:not(.owner-lock):not(.head){display:none}.owner-lock{background:#fff;border:1px dashed #cfe0f7;border-radius:12px;padding:26px;text-align:center;color:#8a9bb0;font-size:10px}.savings{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b}.head{display:flex;align-items:flex-end;margin-bottom:12px}.head-actions{margin-left:auto;display:flex;gap:6px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:10px inherit;padding:0 10px;cursor:pointer}
.hero{background:linear-gradient(135deg,#2563eb,#3b82f6);border-radius:14px;padding:15px;color:#fff;margin-bottom:9px}.hero small{display:block;font-size:8px;opacity:.7;letter-spacing:.12em}.hero b{display:block;font-size:26px;letter-spacing:-.03em;margin-top:3px}.hero span{font-size:8px;opacity:.72}
.health-panel{margin-top:10px}.health-title{display:flex;align-items:center}.health-toggle{margin-left:auto;border:0;background:none;color:#2563eb;font:8px inherit;cursor:pointer}.health-stats{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin:8px 0}.health-stats div{background:#f8fbff;border:1px solid #e3ebf7;border-radius:8px;padding:7px}.health-stats small{display:block;font-size:7px;color:#9aabc0}.health-stats b{display:block;font-size:10px;color:#1e3a5f;margin-top:2px}.health-meals{display:grid;gap:4px;margin:6px 0}.health-meal{display:flex;justify-content:space-between;font-size:8px;color:#526982;padding:4px 0;border-bottom:1px solid #f1f5fb}.health-meal em{font-style:normal;color:#9aabc0}.health-form{display:flex;gap:6px;margin-top:7px}.health-form input{flex:1;min-width:0;height:28px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;font:9px inherit;padding:0 7px;outline:0}.health-form button{height:28px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:8px inherit;padding:0 10px;cursor:pointer}.account-select{height:32px;border:1px solid #dbe8ff;border-radius:8px;background:#f8fbff;color:#243b55;font:10px inherit;padding:0 7px;outline:0}.accounts{display:flex;gap:6px;overflow:auto;margin-bottom:9px}.account{flex:none;min-width:104px;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 9px}.account b{display:block;font-size:8px;color:#8a9bb0}.account span{display:block;font-size:12px;color:#1e3a5f;margin-top:3px}
.form{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px;margin-bottom:9px}.seg{grid-column:1/-1;display:flex;gap:4px}.seg button{flex:1;height:25px;border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#6b7c95;font:9px inherit}.seg button.on{background:#eef4ff;color:#2563eb;border-color:#c7dcff}.form input{min-width:0;height:29px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;padding:0 8px;font:9.5px inherit;outline:0}.form .primary{grid-column:1/-1;height:30px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9.5px inherit;font-weight:700}.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
.entries{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px}.list-title{display:flex;justify-content:space-between;font-size:9px;color:#52708f;font-weight:700;padding:2px 2px 7px}.list-title span{font-weight:400;color:#9aabc0}.entry{display:flex;align-items:center;justify-content:space-between;padding:7px 2px;border-bottom:1px solid #f1f5fb}.entry:last-child{border-bottom:0}.entry b{display:block;font-size:9.5px;color:#314a65}.entry small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.entry em{font-style:normal;font-size:10px;color:#c0264a}.entry em.income{color:#1f9d6b}.entry em.danger-text{color:#b91c1c;font-size:8px}.empty{text-align:center;color:#9aabc0;font-size:9px;padding:16px}
.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px;margin-bottom:9px}.goal{display:grid;grid-template-columns:1fr auto;gap:3px;padding:6px 2px}.goal b{font-size:9.5px;color:#314a65}.goal small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.goal em{font-style:normal;font-size:8.5px;color:#2563eb}.goal button{grid-row:1/3;grid-column:2;align-self:center;border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb;border-radius:5px;font:7.5px inherit;padding:2px 6px;cursor:pointer}.entry .mini{margin-left:7px;border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb;border-radius:5px;font:7.5px inherit;padding:2px 6px;cursor:pointer}.bill-note{border:1px solid #f2d491;background:#fff8e6;color:#8a5a00;border-radius:8px;padding:7px 9px;font-size:8px;line-height:1.6;margin-bottom:8px}.goal i{grid-column:1/-1;height:4px;border-radius:3px;background:#eef4ff;overflow:hidden}.goal i span{display:block;height:100%;background:#2563eb;border-radius:3px}
.chart{display:flex;align-items:flex-end;gap:10px;height:64px;padding:4px 2px}.bar-group,.bars{display:flex;flex-direction:column;align-items:center;gap:4px}.bars{flex-direction:row;align-items:flex-end;gap:2px;height:50px}.bars i{width:7px;border-radius:3px 3px 0 0;display:block}.bars .in{background:#34d399}.bars .out{background:#f87171}.bar-group small{font-size:7px;color:#9aabc0}.legend{display:flex;gap:9px;font-size:7px;color:#8a9bb0;padding:4px 2px}.legend i{display:inline-block;width:6px;height:6px;border-radius:2px;margin-right:3px}.legend .in{background:#34d399}.legend .out{background:#f87171}
.recon-panel .recon-head{display:flex;align-items:center;gap:10px;font-size:8px;color:#8a9bb0;flex-wrap:wrap}.recon-head span:nth-child(2){margin-left:auto}.recon-head b{color:#168b63}.recon-head b.diff{color:#b23b52}.recon-head .mini{height:25px;border:1px solid #dbe8ff;border-radius:6px;background:#f4f9ff;color:#2563eb;font:8px inherit;padding:0 8px;cursor:pointer}.recon-table{margin-top:8px}.recon-row{display:grid;grid-template-columns:1.2fr 1fr 1fr 1fr;gap:6px;padding:5px 0;border-bottom:1px solid #f1f5fb;font-size:8px;color:#405872}.recon-row:last-child{border-bottom:0}.recon-th{font-size:7px;color:#9aabc0}.recon-row em{font-style:normal;text-align:right;color:#168b63}.recon-row em.diff{color:#b23b52}.recon-row span:last-child,.recon-row em{text-align:right}.recon-empty{font-size:8px;color:#9aabc0;padding:8px 0 2px}@media(min-width:821px){.savings{padding:22px 24px;max-width:none;width:100%}.accounts{flex-wrap:wrap}.form{grid-template-columns:1fr 1fr 1fr}.form .seg{grid-column:1/-1}.form .primary{grid-column:1/-1}}
.hero,.accounts,.form,.entries{animation:sv-in .26s cubic-bezier(.22,1,.36,1) both}.accounts{animation-delay:.03s}.form{animation-delay:.06s}.entries{animation-delay:.09s}@keyframes sv-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.hero,.accounts,.form,.entries{animation:none}}
</style>
