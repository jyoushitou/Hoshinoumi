<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { http } from '@/api/client'
import HealthInitModal from '@/components/HealthInitModal.vue'

interface Meal { id?: number; name?: string; kcal?: number; time?: string }
interface Exercise { id?: number; kind?: string; minutes?: number; kcal?: number; time?: string }
interface Health {
  current_weight?: number
  target_weight?: number
  months?: number
  bmr?: number
  target_kcal?: number
  exercise_kcal?: number
  initialized?: boolean
  meals?: Meal[]
  exercises?: Exercise[]
}
interface HealthPayload { data?: Health; intake?: number; exercise?: number; remaining?: number }

const health = ref<Health | null>(null)
const intake = ref(0)
const exercise = ref(0)
const remaining = ref(0)
const loading = ref(false)
const healthError = ref('')
const initOpen = ref(false)
const form = ref({ name: '', kcal: '' })
const exerciseForm = ref({ kind: '走路', minutes: '' })
const recognizeBusy = ref(false)
const recognizeError = ref('')
const recognized = ref<{ name: string; kcal: number } | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)
const targetKcal = computed(() => Number(health.value?.target_kcal || 0))
const bmr = computed(() => Number(health.value?.bmr || 0))
const percent = computed(() => Math.max(0, Math.min(100, Math.round((intake.value / Math.max(1, targetKcal.value)) * 100))))
const shownIntake = ref(0)
const shownPercent = ref(0)
let raf = 0
function animateTo(value: number) {
  cancelAnimationFrame(raf)
  const from = shownIntake.value
  const start = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - start) / 420)
    const eased = 1 - Math.pow(1 - t, 3)
    shownIntake.value = Math.round(from + (value - from) * eased)
    shownPercent.value = Math.round((shownIntake.value / Math.max(1, targetKcal.value)) * 100)
    if (t < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}
watch(intake, value => animateTo(value), { immediate: true })

async function loadHealth() {
  loading.value = true
  healthError.value = ''
  try {
    const result = await http.get<HealthPayload>('/api/health/summary')
    health.value = result.data || null
    intake.value = Number(result.intake || 0)
    exercise.value = Number(result.exercise || 0)
    remaining.value = Number(result.remaining || 0)
    if (health.value && health.value.initialized === false) initOpen.value = true
  } catch (e) {
    health.value = null
    healthError.value = e instanceof Error ? e.message : '健康数据读取失败'
  } finally { loading.value = false }
}
async function finishInit() { initOpen.value = false; await loadHealth() }
async function addMeal() {
  const name = form.value.name.trim(); const kcal = Number(form.value.kcal)
  if (!name || !Number.isFinite(kcal) || kcal <= 0) return
  try {
    await http.post('/api/health/meals', { name, kcal: Math.round(kcal) })
    form.value = { name: '', kcal: '' }
    await loadHealth()
  } catch (e) { healthError.value = e instanceof Error ? e.message : '记录失败' }
}
async function removeMeal(id?: number) {
  if (!id) return
  try { await http.delete(`/api/health/meals/${id}`); await loadHealth() } catch (e) { healthError.value = e instanceof Error ? e.message : '删除失败' }
}
async function addExercise() {
  const minutes = Number(exerciseForm.value.minutes)
  if (!Number.isFinite(minutes) || minutes <= 0) return
  try {
    await http.post('/api/health/exercises', { kind: exerciseForm.value.kind, minutes })
    exerciseForm.value.minutes = ''
    await loadHealth()
  } catch (e) { healthError.value = e instanceof Error ? e.message : '运动记录失败' }
}
function applyRecognized() { if (!recognized.value) return; form.value = { name: recognized.value.name, kcal: String(recognized.value.kcal) }; recognized.value = null }
async function onPhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { recognizeError.value = '请选择图片文件'; return }
  if (file.size > 8 * 1024 * 1024) { recognizeError.value = '图片超过 8 MB'; return }
  recognizeBusy.value = true; recognizeError.value = ''; recognized.value = null
  try {
    const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || '').split(',')[1] || ''); reader.onerror = () => reject(new Error('read_failed')); reader.readAsDataURL(file) })
    const result = await http.post<{ food?: string; kcal?: number; message?: string }>('/api/health/recognize', { filename: file.name, data_base64: data })
    if (!result.food || !result.kcal) throw new Error(result.message || '没有识别出食物')
    recognized.value = { name: result.food, kcal: Math.round(Number(result.kcal)) }
  } catch (e) { recognizeError.value = e instanceof Error ? e.message : '识别失败，请重试或手动填写' } finally { recognizeBusy.value = false; if (photoInput.value) photoInput.value.value = '' }
}
onMounted(loadHealth)
</script>

<template>
  <section class="health">
    <header class="head">
      <div><h1>健康 / 热量</h1><p>基础代谢 · 目标 · 摄入 · 运动</p></div>
      <RouterLink to="/info" class="back">返回信息</RouterLink>
    </header>
    <div v-if="healthError" class="error">{{ healthError }}</div>
    <div v-if="!health && !loading" class="empty">暂无健康数据，请先初始化</div>
    <template v-else-if="health">
      <div class="hero">
        <div class="ring" :style="{ '--p': shownPercent + '%' }"><div class="ring-inner"><b>{{ shownIntake }}</b><small>kcal 摄入</small></div></div>
        <div class="hero-copy"><small>每日目标</small><b>{{ targetKcal }} kcal</b><span>基础代谢 {{ bmr }} kcal · 运动 {{ exercise }} kcal</span><span>当前 {{ health.current_weight ?? '—' }} kg → 目标 {{ health.target_weight ?? '—' }} kg · {{ health.months ?? '—' }} 个月</span></div>
        <div class="hero-stats"><div><small>已摄入</small><b>{{ shownIntake }}</b></div><div><small>剩余</small><b>{{ remaining }}</b></div><div><small>完成度</small><b>{{ shownPercent }}%</b></div></div>
      </div>
      <div class="grid">
        <div class="panel">
          <div class="panel-title">今日饮食 <span>{{ health.meals?.length || 0 }} 条</span></div>
          <div v-for="meal in health.meals" :key="meal.id" class="meal"><div><b>{{ meal.name }}</b><small>{{ meal.time }}</small></div><em>{{ meal.kcal }} kcal</em><button type="button" @click="removeMeal(meal.id)">×</button></div>
          <div v-if="!health.meals?.length" class="empty">今天还没有记录</div>
        </div>
        <div class="panel">
          <div class="panel-title">记一笔 <span>手动 / 识图</span></div>
          <label class="field">食物<input v-model="form.name" placeholder="例如：鸡胸饭"></label>
          <label class="field">热量 kcal<input v-model="form.kcal" inputmode="numeric" placeholder="例如：680"></label>
          <button class="primary" type="button" @click="addMeal">添加记录</button>
          <input ref="photoInput" class="photo-input" type="file" accept="image/*" @change="onPhoto"><button class="ghost" type="button" :disabled="recognizeBusy" @click="photoInput?.click()">{{ recognizeBusy ? '识别中…' : '拍照 / 选图识别' }}</button>
          <div v-if="recognized" class="recognized"><div><b>{{ recognized.name }}</b><small>{{ recognized.kcal }} kcal</small></div><button type="button" @click="applyRecognized">填入</button></div>
          <div v-if="recognizeError" class="error">{{ recognizeError }}</div>
          <p class="note">识图使用真实视觉模型；结果仅估算，可手动修正。</p>
        </div>
        <div class="panel">
          <div class="panel-title">运动 <span>{{ exercise }} kcal</span></div>
          <label class="field">类型<select v-model="exerciseForm.kind"><option v-for="kind in ['走路','跑步','骑行','力量','瑜伽','其他']" :key="kind" :value="kind">{{ kind }}</option></select></label>
          <label class="field">分钟<input v-model="exerciseForm.minutes" inputmode="numeric" placeholder="30"></label>
          <button class="primary" type="button" @click="addExercise">记录运动</button>
        </div>
      </div>
    </template>
    <HealthInitModal :open="initOpen" :current-weight="health?.current_weight ?? 52.4" :target-weight="health?.target_weight ?? 50" :months="health?.months ?? 3" @close="initOpen = false" @done="finishInit" />
  </section>
</template>

<style scoped>
.health{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.back{margin-left:auto;font-size:9px;color:#2563eb;text-decoration:none;border:1px solid #dbe8ff;border-radius:8px;background:#fff;padding:5px 9px}
.hero{display:flex;align-items:center;gap:16px;background:#fff;border:1px solid #e3ebf7;border-radius:14px;padding:16px;margin-bottom:10px;flex-wrap:wrap}.ring{width:104px;height:104px;border-radius:50%;background:conic-gradient(#2563eb var(--p),#e8effa 0);display:grid;place-items:center;flex:none}.ring-inner{width:78px;height:78px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}.ring-inner b{font-size:20px;color:#1e3a5f}.ring-inner small{font-size:7px;color:#8a9bb0;margin-top:2px}.hero-copy small{display:block;font-size:8px;color:#9aabc0}.hero-copy b{display:block;font-size:20px;color:#1d4ed8;margin:2px 0}.hero-copy span{display:block;font-size:8.5px;color:#7d8ca3;line-height:1.7}.hero-stats{margin-left:auto;display:grid;gap:5px;min-width:88px}.hero-stats div{display:flex;justify-content:space-between;gap:9px;font-size:8px;color:#8a9bb0}.hero-stats b{color:#314a65}
.grid{display:grid;grid-template-columns:1.4fr 1fr;gap:9px}.hero,.panel{animation:healthIn .3s cubic-bezier(.22,1,.36,1) both}.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px}.panel-title{display:flex;justify-content:space-between;font-size:10px;font-weight:700;color:#314a65;margin-bottom:8px}.panel-title span{font-weight:400;font-size:8px;color:#9aabc0}
.meal{display:flex;align-items:center;gap:7px;padding:8px 0;border-bottom:1px solid #f1f5fb}.meal:last-child{border-bottom:0}.meal b{display:block;font-size:9.5px;color:#314a65}.meal small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.meal em{font-style:normal;font-size:9px;color:#2563eb;margin-left:auto}.meal button{border:0;background:none;color:#b0bfd1;font:14px inherit;cursor:pointer;padding:0 2px}.empty{text-align:center;color:#9aabc0;font-size:9px;padding:18px}
.field{display:block;font-size:8.5px;color:#8a9bb0;margin-bottom:8px}.field input,.field select{display:block;width:100%;height:30px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;padding:0 8px;font:10px inherit;outline:0;margin-top:3px;box-sizing:border-box}.primary{width:100%;height:32px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:10px inherit;font-weight:700;cursor:pointer}.ghost{width:100%;height:30px;margin-top:6px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#8a9bb0;font:9px inherit}.photo-input{display:none}.recognized{display:flex;align-items:center;gap:6px;border:1px solid #dbe8ff;background:#f4f9ff;border-radius:8px;padding:6px 8px;margin-top:6px}.recognized b{font-size:9px;color:#314a65}.recognized small{display:block;font-size:7px;color:#8a9bb0;margin-top:1px}.recognized button{margin-left:auto;border:1px solid #dbe8ff;border-radius:5px;background:#fff;color:#2563eb;font:8px inherit;padding:2px 6px;cursor:pointer}.error{font-size:8px;color:#b91c1c;margin:6px 0}.note{font-size:7.5px;color:#9aabc0;line-height:1.6;margin:8px 0 0}
@keyframes healthIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.hero,.panel{animation:none}}@media(min-width:821px){.health{padding:22px 24px}.grid{grid-template-columns:1.4fr 1fr}}@media(max-width:820px){.health{padding:16px 14px 18px}.grid{grid-template-columns:1fr}.hero{gap:10px}.hero-stats{margin-left:0;width:100%;grid-template-columns:repeat(3,1fr)}.hero-stats div{flex-direction:column;gap:1px}}
</style>
