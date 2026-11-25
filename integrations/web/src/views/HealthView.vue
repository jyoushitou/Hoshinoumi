<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { http } from '@/api/client'

interface Meal { id: number; name: string; kcal: number; time: string }
const target = ref(2000)
const burn = ref(320)
const weight = ref(52.4)
const meals = ref<Meal[]>([
  { id: 1, name: '早餐 · 三明治', kcal: 420, time: '08:10' },
  { id: 2, name: '午餐 · 鸡胸饭', kcal: 680, time: '12:20' },
  { id: 3, name: '加餐 · 酸奶', kcal: 160, time: '15:40' },
])
const intake = computed(() => meals.value.reduce((sum, meal) => sum + meal.kcal, 0))
const remaining = computed(() => target.value + burn.value - intake.value)
const percent = computed(() => Math.max(0, Math.min(100, Math.round((intake.value / Math.max(1, target.value)) * 100))))
const shownIntake = ref(0)
const shownPercent = ref(0)
let raf = 0
function animateTo(value: number) {
  cancelAnimationFrame(raf)
  const from = shownIntake.value
  const start = performance.now()
  const duration = 420
  const tick = (now: number) => {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    shownIntake.value = Math.round(from + (value - from) * eased)
    shownPercent.value = Math.round((shownIntake.value / Math.max(1, target.value)) * 100)
    if (t < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}
watch(intake, value => animateTo(value), { immediate: true })
const form = ref({ name: '', kcal: '' })
const recognizeBusy = ref(false)
const recognizeError = ref('')
const recognized = ref<{ name: string; kcal: number } | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)
function applyRecognized() { if (!recognized.value) return; form.value = { name: recognized.value.name, kcal: String(recognized.value.kcal) }; recognized.value = null }
async function onPhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { recognizeError.value = '请选择图片文件'; return }
  if (file.size > 8 * 1024 * 1024) { recognizeError.value = '图片超过 8 MB'; return }
  recognizeBusy.value = true; recognizeError.value = ''; recognized.value = null
  try {
    const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || '').split(',')[1] || ''); reader.onerror = () => reject(new Error('read_failed')); reader.readAsDataURL(file) })
    const result = await http.post<{ food?: string; kcal?: number; items?: Array<{ name?: string; kcal?: number }> }>('/api/health/recognize', { filename: file.name, data_base64: data })
    const item = result.items?.[0]
    const name = result.food || item?.name
    const kcal = Number(result.kcal || item?.kcal || 0)
    if (!name || !kcal) throw new Error('no_result')
    recognized.value = { name, kcal: Math.round(kcal) }
  } catch { recognizeError.value = '识别失败，请重试或手动填写' } finally { recognizeBusy.value = false; if (photoInput.value) photoInput.value.value = '' }
}
function addMeal() {
  const name = form.value.name.trim()
  const kcal = Number(form.value.kcal)
  if (!name || !Number.isFinite(kcal) || kcal <= 0) return
  meals.value.push({ id: Date.now(), name, kcal: Math.round(kcal), time: new Date().toTimeString().slice(0, 5) })
  form.value = { name: '', kcal: '' }
}
function removeMeal(id: number) { meals.value = meals.value.filter(meal => meal.id !== id) }
</script>

<template>
  <section class="health">
    <header class="head">
      <div><h1>健康 / 热量</h1><p>今日摄入 · 目标 · 运动 · 体重</p></div>
      <RouterLink to="/info" class="back">返回信息</RouterLink>
    </header>
    <div class="hero">
      <div class="ring" :style="{ '--p': shownPercent + '%' }"><div class="ring-inner"><b>{{ shownIntake }}</b><small>kcal 摄入</small></div></div>
      <div class="hero-copy"><small>今日目标</small><b>{{ target }} kcal</b><span>运动消耗 {{ burn }} kcal · 剩余 {{ remaining }} kcal</span><span>体重 {{ weight }} kg</span></div>
      <div class="hero-stats"><div><small>已摄入</small><b>{{ shownIntake }}</b></div><div><small>剩余</small><b>{{ remaining }}</b></div><div><small>完成度</small><b>{{ shownPercent }}%</b></div></div>
    </div>
    <div class="grid">
      <div class="panel">
        <div class="panel-title">今日饮食 <span>{{ meals.length }} 条</span></div>
        <div v-for="meal in meals" :key="meal.id" class="meal"><div><b>{{ meal.name }}</b><small>{{ meal.time }}</small></div><em>{{ meal.kcal }} kcal</em><button type="button" @click="removeMeal(meal.id)">×</button></div>
        <div v-if="!meals.length" class="empty">今天还没有记录</div>
      </div>
      <div class="panel">
        <div class="panel-title">记一笔 <span>手动 / 识图</span></div>
        <label class="field">食物<input v-model="form.name" placeholder="例如：鸡胸饭"></label>
        <label class="field">热量 kcal<input v-model="form.kcal" inputmode="numeric" placeholder="例如：680"></label>
        <button class="primary" type="button" @click="addMeal">添加记录</button>
        <input ref="photoInput" class="photo-input" type="file" accept="image/*" @change="onPhoto"><button class="ghost" type="button" :disabled="recognizeBusy" @click="photoInput?.click()">{{ recognizeBusy ? '识别中…' : '拍照 / 选图识别' }}</button>
        <div v-if="recognized" class="recognized"><div><b>{{ recognized.name }}</b><small>{{ recognized.kcal }} kcal</small></div><button type="button" @click="applyRecognized">填入</button></div>
        <div v-if="recognizeError" class="error">{{ recognizeError }}</div>
        <p class="note">热量为估算值；识图与健康 API 在 v35.9.6.6 / .7 接入。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.health{flex:1;min-height:0;overflow:auto;padding:18px 18px 24px;background:#f7faff;color:#17263b;box-sizing:border-box}.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.back{margin-left:auto;font-size:9px;color:#2563eb;text-decoration:none;border:1px solid #dbe8ff;border-radius:8px;background:#fff;padding:5px 9px}
.hero{display:flex;align-items:center;gap:16px;background:#fff;border:1px solid #e3ebf7;border-radius:14px;padding:16px;margin-bottom:10px;flex-wrap:wrap}.ring{width:104px;height:104px;border-radius:50%;background:conic-gradient(#2563eb var(--p),#e8effa 0);display:grid;place-items:center;flex:none}.ring-inner{width:78px;height:78px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}.ring-inner b{font-size:20px;color:#1e3a5f}.ring-inner small{font-size:7px;color:#8a9bb0;margin-top:2px}.hero-copy small{display:block;font-size:8px;color:#9aabc0}.hero-copy b{display:block;font-size:20px;color:#1d4ed8;margin:2px 0}.hero-copy span{display:block;font-size:8.5px;color:#7d8ca3;line-height:1.7}.hero-stats{margin-left:auto;display:grid;gap:5px;min-width:88px}.hero-stats div{display:flex;justify-content:space-between;gap:9px;font-size:8px;color:#8a9bb0}.hero-stats b{color:#314a65}
.grid{display:grid;grid-template-columns:1.4fr 1fr;gap:9px}.hero,.panel{animation:healthIn .3s cubic-bezier(.22,1,.36,1) both}.hero{animation-delay:.02s}.grid .panel:nth-child(2){animation-delay:.06s}.meal{animation:mealIn .25s ease both}.meal:nth-child(2){animation-delay:.03s}.meal:nth-child(3){animation-delay:.06s}.meal:nth-child(4){animation-delay:.09s}.ring{transition:background .45s ease}@keyframes healthIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}@keyframes mealIn{from{opacity:0;transform:translateX(-4px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){.hero,.panel,.meal,.ring{animation:none;transition:none}}.panel{background:#fff;border:1px solid #e3ebf7;border-radius:12px;padding:12px}.panel-title{display:flex;justify-content:space-between;font-size:10px;font-weight:700;color:#314a65;margin-bottom:8px}.panel-title span{font-weight:400;font-size:8px;color:#9aabc0}.meal{display:flex;align-items:center;gap:7px;padding:8px 0;border-bottom:1px solid #f1f5fb}.meal:last-child{border-bottom:0}.meal b{display:block;font-size:9.5px;color:#314a65}.meal small{display:block;font-size:7.5px;color:#9aabc0;margin-top:2px}.meal em{font-style:normal;font-size:9px;color:#2563eb;margin-left:auto}.meal button{border:0;background:none;color:#b0bfd1;font:14px inherit;cursor:pointer;padding:0 2px}.empty{text-align:center;color:#9aabc0;font-size:9px;padding:18px}
.field{display:block;font-size:8.5px;color:#8a9bb0;margin-bottom:8px}.field input{display:block;width:100%;height:30px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;padding:0 8px;font:10px inherit;outline:0;margin-top:3px;box-sizing:border-box}.primary{width:100%;height:32px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:10px inherit;font-weight:700;cursor:pointer}.ghost{width:100%;height:30px;margin-top:6px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#8a9bb0;font:9px inherit}.photo-input{display:none}.recognized{display:flex;align-items:center;gap:6px;border:1px solid #dbe8ff;background:#f4f9ff;border-radius:8px;padding:6px 8px;margin-top:6px}.recognized b{font-size:9px;color:#314a65}.recognized small{display:block;font-size:7px;color:#8a9bb0;margin-top:1px}.recognized button{margin-left:auto;border:1px solid #dbe8ff;border-radius:5px;background:#fff;color:#2563eb;font:8px inherit;padding:2px 6px;cursor:pointer}.error{font-size:8px;color:#b91c1c;margin-top:6px}.note{font-size:7.5px;color:#9aabc0;line-height:1.6;margin:8px 0 0}
@media(min-width:821px){.health{padding:22px 24px}.grid{grid-template-columns:1.4fr 1fr}}
@media(max-width:820px){.health{padding:16px 14px 18px}.grid{grid-template-columns:1fr}.hero{gap:10px}.hero-stats{margin-left:0;width:100%;grid-template-columns:repeat(3,1fr)}.hero-stats div{flex-direction:column;gap:1px}}
</style>
