<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { http } from '@/api/client'

const props = defineProps<{ open: boolean; currentWeight?: number; targetWeight?: number; months?: number }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'done'): void }>()
const current = ref('52.4')
const target = ref('50')
const months = ref('3')
const busy = ref(false)
const error = ref('')

watch(() => props.open, (open) => {
  if (!open) return
  current.value = String(props.currentWeight ?? 52.4)
  target.value = String(props.targetWeight ?? 50)
  months.value = String(props.months ?? 3)
}, { immediate: true })

const bmr = computed(() => Math.round((Number(current.value) || 0) * 22))
const dailyTarget = computed(() => {
  const c = Number(current.value) || 0
  const t = Number(target.value) || 0
  const m = Number(months.value) || 1
  const b = Math.round(c * 22)
  return Math.max(800, Math.round(b - (c - t) * 7700 / Math.max(30, m * 30)))
})

async function submit() {
  const c = Number(current.value); const t = Number(target.value); const m = Number(months.value)
  if (!Number.isFinite(c) || !Number.isFinite(t) || !Number.isFinite(m) || c <= 0 || t <= 0 || m <= 0) {
    error.value = '请填写有效数值'; return
  }
  busy.value = true; error.value = ''
  try {
    await http.post('/api/health/init', { current_weight: c, target_weight: t, months: m })
    emit('done')
  } catch (e) { error.value = e instanceof Error ? e.message : '初始化失败' } finally { busy.value = false }
}
</script>

<template>
  <div v-if="open" class="health-mask">
    <div class="health-card">
      <div class="badge">HEALTH · FIRST RUN</div>
      <h2>初始化健康 / 热量</h2>
      <p class="lead">只填体重和目标。基础代谢、每日目标由体重和月数自动计算。</p>
      <div class="fields">
        <label><span>当前体重</span><input v-model="current" inputmode="decimal"><em>kg</em></label>
        <label><span>目标体重</span><input v-model="target" inputmode="decimal"><em>kg</em></label>
        <label><span>目标月数</span><input v-model="months" inputmode="numeric"><em>个月</em></label>
      </div>
      <div class="calc">
        <div><small>基础代谢 BMR</small><b>{{ bmr }} kcal</b></div>
        <div><small>每日目标摄入</small><b>{{ dailyTarget }} kcal</b></div>
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="actions">
        <button type="button" class="later" @click="emit('close')">稍后</button>
        <button type="button" class="primary" :disabled="busy" @click="submit">{{ busy ? '保存中…' : '保存' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.health-mask{position:fixed;inset:0;z-index:71;background:rgba(15,23,42,.28);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:18px}
.health-card{width:100%;max-width:380px;background:#fff;border:1px solid #dbe8ff;border-radius:16px;padding:20px;box-shadow:0 22px 60px rgba(15,23,42,.2)}
.badge{display:inline-block;font-size:8px;letter-spacing:.13em;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:20px;padding:4px 8px}
h2{margin:9px 0 4px;font-size:20px;letter-spacing:-.03em;color:#17263b}.lead{margin:0 0 13px;font-size:9.5px;line-height:1.6;color:#8a9bb0}
.fields{display:grid;gap:7px;margin-bottom:10px}.fields label{display:flex;align-items:center;gap:8px;border:1px solid #e3ebf7;border-radius:9px;background:#f8fbff;padding:7px 9px}.fields span{width:64px;font-size:9.5px;color:#405872}.fields input{flex:1;min-width:0;height:26px;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#243b55;font:10px inherit;padding:0 8px;outline:0}.fields em{font-style:normal;font-size:8px;color:#9aabc0}
.calc{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:9px}.calc div{background:#f0f7ff;border:1px solid #dbe8ff;border-radius:8px;padding:7px 8px}.calc small{display:block;font-size:7px;color:#8a9bb0}.calc b{display:block;font-size:11px;color:#1d4ed8;margin-top:2px}
.error{font-size:9px;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:7px;padding:6px 8px;margin:7px 0}
.actions{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}.actions button{height:32px;border-radius:8px;font:10px inherit;padding:0 14px;cursor:pointer}.later{border:1px solid #e3ebf7;background:#fff;color:#7d8ca3}.primary{border:0;background:#2563eb;color:#fff;font-weight:700}.primary:disabled{opacity:.55}
</style>
