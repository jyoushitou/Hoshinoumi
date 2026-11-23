<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { http } from '@/api/client'
import { useIsOwner } from '@/composables/useIsOwner'

interface Account { account: string; balance_cents: number }
interface Entry { id?: number; account: string; kind: string; amount_cents: number; category?: string; note?: string; occurred_at?: string }
interface Savings { total_cents: number; accounts: Account[]; entries: Entry[] }
interface Overview { total_cents: number; frozen_cents: number; available_cents: number }
interface Goal { id: number; name: string; target_cents: number; saved_cents: number; deadline?: string }
interface Held { id: number; name: string; amount_cents?: number; code?: string; shares?: number; value_cents?: number; rate?: number; due?: string; matures_at?: string }
interface MonthRow { month: string; income_cents: number; expense_cents: number }
interface AuditRow { at: string; user: string; method: string; path: string; status: number }
const isOwner = useIsOwner()
const data = ref<Savings | null>(null)
const overview = ref<Overview | null>(null)
const goals = ref<Goal[]>([])
const frozen = ref<Held[]>([])
const fixed = ref<Held[]>([])
const funds = ref<Held[]>([])
const monthly = ref<MonthRow[]>([])
const audit = ref<AuditRow[]>([])
const loading = ref(false)
const error = ref('')
const amount = ref('')
const note = ref('')
const kind = ref<'expense' | 'income'>('expense')
const account = ref('银行卡')
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
  if (!accounts.value.some(item => item.account === account.value)) { error.value = '账户不存在'; return }
  saving.value = true
  error.value = ''
  try {
    await http.post('/api/savings/entries', { amount: value, kind: kind.value, account: account.value, note: note.value.trim() })
    amount.value = ''
    note.value = ''
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '记录失败' } finally { saving.value = false }
}
onMounted(() => { if (isOwner.value) void load() })
watch(isOwner, value => { if (value && !data.value) void load() })
</script>

<template>
  <section class="savings" :class="{ locked: !isOwner }">
    <div v-if="!isOwner" class="owner-lock">财务数据仅主人可见</div>
    <header class="head"><div><h1>存钱</h1><p>总余额 / 账户 / 流水</p></div><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></header>
    <div v-if="error" class="error">{{ error }}</div>
    <div class="hero"><small>总余额</small><b>{{ fmt(overview?.total_cents ?? data?.total_cents ?? 0) }}</b><span>可用 {{ fmt(overview?.available_cents ?? data?.total_cents ?? 0) }} · 冻结 {{ fmt(overview?.frozen_cents || 0) }} · {{ accounts.length }} 个账户</span></div>
    <div class="accounts">
      <div v-for="item in accounts" :key="item.account" class="account"><b>{{ item.account }}</b><span>{{ fmt(item.balance_cents) }}</span></div>
    </div>
    <div v-if="goals.length" class="panel"><div class="list-title">存钱目标<span>{{ goals.length }}</span></div><div v-for="goal in goals" :key="goal.id" class="goal"><div><b>{{ goal.name }}</b><small>{{ goal.deadline || '无期限' }}</small></div><em>{{ fmt(goal.saved_cents) }} / {{ fmt(goal.target_cents) }}</em><button type="button" @click="allocate(goal)">存入</button><i><span :style="{ width: Math.min(100, goal.saved_cents / Math.max(1, goal.target_cents) * 100) + '%' }" /></i></div></div>
    <div v-if="frozen.length || fixed.length || funds.length" class="panel"><div class="list-title">资金位置<span>{{ frozen.length + fixed.length + funds.length }}</span></div><div v-for="item in frozen" :key="'f'+item.id" class="entry"><div><b>{{ item.name }}</b><small>冻结 · 到期 {{ item.due || '—' }}</small></div><em>{{ fmt(item.amount_cents || 0) }}</em><button class="mini" type="button" @click="unfreeze(item)">解冻</button></div><div v-for="item in fixed" :key="'d'+item.id" class="entry"><div><b>{{ item.name }}</b><small>定期 {{ item.rate || 0 }}% · {{ item.matures_at || '' }}</small></div><em>{{ fmt(item.amount_cents || 0) }}</em></div><div v-for="item in funds" :key="'u'+item.code" class="entry"><div><b>{{ item.name }}</b><small>基金 {{ item.code }} · {{ item.shares || 0 }} 份</small></div><em>{{ fmt(item.value_cents || 0) }}</em></div></div>
    <div v-if="dueBills.length" class="bill-note">缴费提醒：{{ dueBills.map(x => x.name + ' ' + fmt(x.amount_cents || 0) + ' · ' + x.due).join('；') }}</div>
    <div class="form">
      <div class="seg"><button type="button" :class="{ on: kind === 'expense' }" @click="kind = 'expense'">支出</button><button type="button" :class="{ on: kind === 'income' }" @click="kind = 'income'">收入</button></div>
      <input v-model="amount" inputmode="decimal" placeholder="金额">
      <input v-model="note" placeholder="备注（可选）">
      <button class="primary" type="button" :disabled="saving" @click="addEntry">{{ saving ? '保存中…' : '记一笔' }}</button>
    </div>
    <div v-if="monthly.length" class="panel"><div class="list-title">月流水<span>{{ monthly.length }} 个月</span></div><div class="chart"><div v-for="row in monthly" :key="row.month" class="bar-group"><div class="bars"><i class="in" :style="{ height: Math.max(4, row.income_cents / Math.max(1, ...monthly.map(m => Math.max(m.income_cents, m.expense_cents))) * 48) + 'px' }" /><i class="out" :style="{ height: Math.max(4, row.expense_cents / Math.max(1, ...monthly.map(m => Math.max(m.income_cents, m.expense_cents))) * 48) + 'px' }" /></div><small>{{ row.month.slice(5) }}</small></div></div><div class="legend"><span><i class="in" />收入</span><span><i class="out" />支出</span></div></div>
    <div class="panel"><div class="list-title">403 审计<span>{{ audit.length }}</span></div><div v-if="!audit.length" class="empty">暂无越权访问</div><div v-for="row in audit.slice(0, 5)" :key="row.at + row.path" class="entry"><div><b>{{ row.method }} {{ row.path }}</b><small>{{ row.user }} · {{ row.at }}</small></div><em class="danger-text">403</em></div></div>
    <div class="entries">
      <div class="list-title">流水<span>{{ entries.length }}</span></div>
      <div v-if="!entries.length" class="empty">暂无流水</div>
      <div v-for="(entry, index) in entries" :key="entry.id ?? index" class="entry">
        <div><b>{{ entry.note || entry.category || entry.kind }}</b><small>{{ entry.account }} · {{ String(entry.occurred_at || '').slice(0, 10) }}</small></div>
        <em :class="{ income: entry.amount_cents > 0 }">{{ entry.amount_cents > 0 ? '+' : '' }}{{ fmt(entry.amount_cents) }}</em>
      </div>
    </div>
  </section>
</template>

<style scoped>
.savings.locked > *:not(.owner-lock):not(.head){display:none}.owner-lock{background:#fff;border:1px dashed #cfe0f7;border-radius:12px;padding:26px;text-align:center;color:#8a9bb0;font-size:10px}.savings{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b}.head{display:flex;align-items:flex-end;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:10px inherit;padding:0 10px;cursor:pointer}
.hero{background:linear-gradient(135deg,#2563eb,#3b82f6);border-radius:14px;padding:15px;color:#fff;margin-bottom:9px}.hero small{display:block;font-size:8px;opacity:.7;letter-spacing:.12em}.hero b{display:block;font-size:26px;letter-spacing:-.03em;margin-top:3px}.hero span{font-size:8px;opacity:.72}
.accounts{display:flex;gap:6px;overflow:auto;margin-bottom:9px}.account{flex:none;min-width:104px;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 9px}.account b{display:block;font-size:8px;color:#8a9bb0}.account span{display:block;font-size:12px;color:#1e3a5f;margin-top:3px}
.form{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px;margin-bottom:9px}.seg{grid-column:1/-1;display:flex;gap:4px}.seg button{flex:1;height:25px;border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#6b7c95;font:9px inherit}.seg button.on{background:#eef4ff;color:#2563eb;border-color:#c7dcff}.form input{min-width:0;height:29px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;padding:0 8px;font:9.5px inherit;outline:0}.form .primary{grid-column:1/-1;height:30px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9.5px inherit;font-weight:700}.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
.entries{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px}.list-title{display:flex;justify-content:space-between;font-size:9px;color:#52708f;font-weight:700;padding:2px 2px 7px}.list-title span{font-weight:400;color:#9aabc0}.entry{display:flex;align-items:center;justify-content:space-between;padding:7px 2px;border-bottom:1px solid #f1f5fb}.entry:last-child{border-bottom:0}.entry b{display:block;font-size:9.5px;color:#314a65}.entry small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.entry em{font-style:normal;font-size:10px;color:#c0264a}.entry em.income{color:#1f9d6b}.entry em.danger-text{color:#b91c1c;font-size:8px}.empty{text-align:center;color:#9aabc0;font-size:9px;padding:16px}
.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px;margin-bottom:9px}.goal{display:grid;grid-template-columns:1fr auto;gap:3px;padding:6px 2px}.goal b{font-size:9.5px;color:#314a65}.goal small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.goal em{font-style:normal;font-size:8.5px;color:#2563eb}.goal button{grid-row:1/3;grid-column:2;align-self:center;border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb;border-radius:5px;font:7.5px inherit;padding:2px 6px;cursor:pointer}.entry .mini{margin-left:7px;border:1px solid #dbe8ff;background:#f4f9ff;color:#2563eb;border-radius:5px;font:7.5px inherit;padding:2px 6px;cursor:pointer}.bill-note{border:1px solid #f2d491;background:#fff8e6;color:#8a5a00;border-radius:8px;padding:7px 9px;font-size:8px;line-height:1.6;margin-bottom:8px}.goal i{grid-column:1/-1;height:4px;border-radius:3px;background:#eef4ff;overflow:hidden}.goal i span{display:block;height:100%;background:#2563eb;border-radius:3px}
.chart{display:flex;align-items:flex-end;gap:10px;height:64px;padding:4px 2px}.bar-group,.bars{display:flex;flex-direction:column;align-items:center;gap:4px}.bars{flex-direction:row;align-items:flex-end;gap:2px;height:50px}.bars i{width:7px;border-radius:3px 3px 0 0;display:block}.bars .in{background:#34d399}.bars .out{background:#f87171}.bar-group small{font-size:7px;color:#9aabc0}.legend{display:flex;gap:9px;font-size:7px;color:#8a9bb0;padding:4px 2px}.legend i{display:inline-block;width:6px;height:6px;border-radius:2px;margin-right:3px}.legend .in{background:#34d399}.legend .out{background:#f87171}
@media(min-width:821px){.savings{padding:22px 24px;max-width:900px}.accounts{flex-wrap:wrap}.form{grid-template-columns:1fr 1fr 1fr}.form .seg{grid-column:1/-1}.form .primary{grid-column:1/-1}}
.hero,.accounts,.form,.entries{animation:sv-in .26s cubic-bezier(.22,1,.36,1) both}.accounts{animation-delay:.03s}.form{animation-delay:.06s}.entries{animation-delay:.09s}@keyframes sv-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.hero,.accounts,.form,.entries{animation:none}}
</style>
