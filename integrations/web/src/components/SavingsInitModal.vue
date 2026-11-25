<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { http } from '@/api/client'

const props = defineProps<{ open: boolean; accounts: string[] }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'done'): void }>()
const values = ref<Record<string, string>>({})
const busy = ref(false)
const error = ref('')

watch(() => [props.open, props.accounts] as const, () => {
  if (!props.open) return
  const next: Record<string, string> = {}
  for (const name of props.accounts) next[name] = values.value[name] ?? ''
  values.value = next
}, { immediate: true })

const total = computed(() => props.accounts.reduce((sum, name) => {
  const n = Number(values.value[name])
  return sum + (Number.isFinite(n) ? n : 0)
}, 0))

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const balances: Record<string, number> = {}
    for (const name of props.accounts) {
      const n = Number(values.value[name] || 0)
      if (Number.isFinite(n) && n !== 0) balances[name] = n
    }
    await http.post('/api/savings/init', { balances })
    emit('done')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '初始化失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="open" class="init-mask">
    <div class="init-card">
      <div class="badge">SAVINGS · FIRST RUN</div>
      <h2>初始化存钱账户</h2>
      <p class="lead">第一次进入存钱页，填写各账户当前余额。没有余额填 0 即可。</p>

      <div class="rows">
        <label v-for="name in accounts" :key="name" class="row">
          <span>{{ name }}</span>
          <input v-model="values[name]" inputmode="decimal" placeholder="0.00" autofocus>
          <em>元</em>
        </label>
      </div>

      <div class="total"><span>初始总额</span><b>¥{{ total.toFixed(2) }}</b></div>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="actions">
        <button type="button" class="later" @click="emit('close')">稍后</button>
        <button type="button" class="primary" :disabled="busy" @click="submit">{{ busy ? '保存中…' : '保存并开始' }}</button>
      </div>
      <p class="hint">只作为期初余额记一笔，不伪造日常流水。</p>
    </div>
  </div>
</template>

<style scoped>
.init-mask{position:fixed;inset:0;z-index:70;background:rgba(15,23,42,.28);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:18px}
.init-card{width:100%;max-width:400px;background:#fff;border:1px solid #dbe8ff;border-radius:16px;padding:20px;box-shadow:0 22px 60px rgba(15,23,42,.2)}
.badge{display:inline-block;font-size:8px;letter-spacing:.13em;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:20px;padding:4px 8px}
h2{margin:9px 0 4px;font-size:20px;letter-spacing:-.03em;color:#17263b}
.lead{margin:0 0 13px;font-size:9.5px;line-height:1.6;color:#8a9bb0}
.rows{display:grid;gap:7px;margin-bottom:10px}
.row{display:flex;align-items:center;gap:8px;border:1px solid #e3ebf7;border-radius:9px;background:#f8fbff;padding:7px 9px}
.row span{width:64px;font-size:9.5px;color:#405872}.row input{flex:1;min-width:0;height:26px;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#243b55;font:10px inherit;padding:0 8px;outline:0}.row input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.row em{font-style:normal;font-size:8px;color:#9aabc0}
.total{display:flex;justify-content:space-between;align-items:center;padding:8px 2px;border-top:1px solid #eef3fb;font-size:9px;color:#8a9bb0}.total b{font-size:16px;color:#2563eb}
.error{font-size:9px;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:7px;padding:6px 8px;margin:7px 0}
.actions{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}.actions button{height:32px;border-radius:8px;font:10px inherit;padding:0 14px;cursor:pointer}.later{border:1px solid #e3ebf7;background:#fff;color:#7d8ca3}.primary{border:0;background:#2563eb;color:#fff;font-weight:700}.primary:disabled{opacity:.55}.hint{margin:8px 0 0;font-size:8px;color:#9aabbe;text-align:right}
</style>
