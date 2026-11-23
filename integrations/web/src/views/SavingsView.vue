<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface Account { account: string; balance_cents: number }
interface Entry { id?: number; account: string; kind: string; amount_cents: number; category?: string; note?: string; occurred_at?: string }
interface Savings { total_cents: number; accounts: Account[]; entries: Entry[] }
const data = ref<Savings | null>(null)
const loading = ref(false)
const error = ref('')
const amount = ref('')
const note = ref('')
const kind = ref<'expense' | 'income'>('expense')
const account = ref('银行卡')
const saving = ref(false)
const fmt = (cents: number) => `¥${(Number(cents || 0) / 100).toFixed(2)}`
const accounts = computed(() => data.value?.accounts || [])
const entries = computed(() => data.value?.entries || [])
async function load() {
  loading.value = true
  error.value = ''
  try { data.value = await http.get<Savings>('/api/savings') } catch (e) { error.value = e instanceof Error ? e.message : '存钱数据加载失败' } finally { loading.value = false }
}
async function addEntry() {
  const value = Number(amount.value)
  if (!Number.isFinite(value) || value <= 0) { error.value = '请输入有效金额'; return }
  saving.value = true
  error.value = ''
  try {
    await http.post('/api/savings/entries', { amount: value, kind: kind.value, account: account.value, note: note.value.trim() })
    amount.value = ''
    note.value = ''
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '记录失败' } finally { saving.value = false }
}
onMounted(() => { void load() })
</script>

<template>
  <section class="savings">
    <header class="head"><div><h1>存钱</h1><p>总余额 / 账户 / 流水</p></div><button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button></header>
    <div v-if="error" class="error">{{ error }}</div>
    <div class="hero"><small>总余额</small><b>{{ fmt(data?.total_cents || 0) }}</b><span>{{ accounts.length }} 个账户</span></div>
    <div class="accounts">
      <div v-for="item in accounts" :key="item.account" class="account"><b>{{ item.account }}</b><span>{{ fmt(item.balance_cents) }}</span></div>
    </div>
    <div class="form">
      <div class="seg"><button type="button" :class="{ on: kind === 'expense' }" @click="kind = 'expense'">支出</button><button type="button" :class="{ on: kind === 'income' }" @click="kind = 'income'">收入</button></div>
      <input v-model="amount" inputmode="decimal" placeholder="金额">
      <input v-model="note" placeholder="备注（可选）">
      <button class="primary" type="button" :disabled="saving" @click="addEntry">{{ saving ? '保存中…' : '记一笔' }}</button>
    </div>
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
.savings{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b}.head{display:flex;align-items:flex-end;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:10px inherit;padding:0 10px;cursor:pointer}
.hero{background:linear-gradient(135deg,#2563eb,#3b82f6);border-radius:14px;padding:15px;color:#fff;margin-bottom:9px}.hero small{display:block;font-size:8px;opacity:.7;letter-spacing:.12em}.hero b{display:block;font-size:26px;letter-spacing:-.03em;margin-top:3px}.hero span{font-size:8px;opacity:.72}
.accounts{display:flex;gap:6px;overflow:auto;margin-bottom:9px}.account{flex:none;min-width:104px;background:#fff;border:1px solid #e3ebf7;border-radius:10px;padding:8px 9px}.account b{display:block;font-size:8px;color:#8a9bb0}.account span{display:block;font-size:12px;color:#1e3a5f;margin-top:3px}
.form{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px;margin-bottom:9px}.seg{grid-column:1/-1;display:flex;gap:4px}.seg button{flex:1;height:25px;border:1px solid #e3ebf7;border-radius:6px;background:#f8fbff;color:#6b7c95;font:9px inherit}.seg button.on{background:#eef4ff;color:#2563eb;border-color:#c7dcff}.form input{min-width:0;height:29px;border:1px solid #e3ebf7;border-radius:7px;background:#f8fbff;padding:0 8px;font:9.5px inherit;outline:0}.form .primary{grid-column:1/-1;height:30px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9.5px inherit;font-weight:700}.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}
.entries{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:9px}.list-title{display:flex;justify-content:space-between;font-size:9px;color:#52708f;font-weight:700;padding:2px 2px 7px}.list-title span{font-weight:400;color:#9aabc0}.entry{display:flex;align-items:center;justify-content:space-between;padding:7px 2px;border-bottom:1px solid #f1f5fb}.entry:last-child{border-bottom:0}.entry b{display:block;font-size:9.5px;color:#314a65}.entry small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.entry em{font-style:normal;font-size:10px;color:#c0264a}.entry em.income{color:#1f9d6b}.empty{text-align:center;color:#9aabc0;font-size:9px;padding:16px}
@media(min-width:821px){.savings{padding:22px 24px;max-width:900px}.accounts{flex-wrap:wrap}.form{grid-template-columns:1fr 1fr 1fr}.form .seg{grid-column:1/-1}.form .primary{grid-column:1/-1}}
.hero,.accounts,.form,.entries{animation:sv-in .26s cubic-bezier(.22,1,.36,1) both}.accounts{animation-delay:.03s}.form{animation-delay:.06s}.entries{animation-delay:.09s}@keyframes sv-in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.hero,.accounts,.form,.entries{animation:none}}
</style>
