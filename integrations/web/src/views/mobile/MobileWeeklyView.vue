<template>
  <div class="week-page">
    <div class="head">
      <div><h1>周计划</h1><p>{{ weekLabel }} · {{ courses.length }} 个节次</p></div>
      <button type="button" class="add" aria-label="新增节次" @click="formOpen = !formOpen">{{ formOpen ? '×' : '＋' }}</button>
    </div>

    <div class="week-strip">
      <button v-for="(day, index) in days" :key="day" type="button" class="day" :class="{ on: activeDay === index }" @click="activeDay = index">
        <b>{{ day }}</b><small>{{ dayNumber(index) }}</small>
      </button>
    </div>

    <div v-if="formOpen" class="form">
      <input v-model="newName" placeholder="节次名称，例如：学生会例会">
      <div class="form-row">
        <select v-model.number="newStart"><option v-for="n in 11" :key="n" :value="n">第 {{ n }} 节</option></select>
        <span>到</span>
        <select v-model.number="newEnd"><option v-for="n in 11" :key="n" :value="n">第 {{ n }} 节</option></select>
        <button type="button" :disabled="saving || !newName.trim()" @click="addCourse">添加</button>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="loading" class="notice">正在读取周计划…</div>
    <div v-else-if="!dayCourses.length" class="notice">{{ formOpen ? '填写上面的名称后添加' : '这一天没有节次' }}</div>
    <div v-else class="list">
      <div v-for="(course, index) in dayCourses" :key="index" class="course">
        <span class="idx">{{ String(course.period_start).padStart(2, '0') }}<template v-if="course.period_end !== course.period_start">–{{ course.period_end }}</template></span>
        <div class="copy"><b>{{ course.name }}</b><small>{{ [course.teacher, course.location].filter(Boolean).join(' · ') || '未填写教师 / 地点' }}</small></div>
        <button type="button" class="del" :disabled="saving" @click="removeCourse(course)">删除</button>
      </div>
    </div>
    <div class="hint">增删都会先保存整周；失败不会假装成功。</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'
import { useSessionStore } from '@/stores/session'

interface Course {
  name: string
  teacher?: string
  location?: string
  weekday: number
  period_start: number
  period_end: number
  weeks_raw?: string
  weeks?: number[]
  source?: string
}
interface WeeklyResponse { ok?: boolean; week?: number; courses?: Course[]; error?: string; message?: string }

const session = useSessionStore()
const days = ['一', '二', '三', '四', '五', '六', '日']
const currentWeek = ref(Number(session.week) || 1)
const courses = ref<Course[]>([])
const activeDay = ref(0)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const formOpen = ref(false)
const newName = ref('')
const newStart = ref(1)
const newEnd = ref(1)
const weekLabel = computed(() => `第 ${currentWeek.value} 周`)
const dayCourses = computed(() => courses.value.filter(course => course.weekday === activeDay.value + 1).sort((a, b) => a.period_start - b.period_start))
const dayNumber = (index: number) => {
  const now = new Date()
  const monday = new Date(now); monday.setHours(0, 0, 0, 0)
  const offset = (monday.getDay() + 6) % 7
  monday.setDate(monday.getDate() - offset + index)
  return `${monday.getMonth() + 1}/${monday.getDate()}`
}

async function load() {
  loading.value = true; error.value = ''
  try {
    const r = await http.get<WeeklyResponse>('/api/weekly-plan?week=' + currentWeek.value)
    if (r.ok === false) throw new Error(r.message || r.error || '读取失败')
    courses.value = Array.isArray(r.courses) ? r.courses : []
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    courses.value = []
  } finally {
    loading.value = false
  }
}
async function persist(next: Course[], success: string) {
  saving.value = true; error.value = ''
  const previous = courses.value
  courses.value = next
  try {
    const r = await http.post<WeeklyResponse>('/api/weekly-plan', { week: currentWeek.value, courses: next })
    if (r.ok === false) throw new Error(r.message || r.error || '保存失败')
    await load()
  } catch (e) {
    courses.value = previous
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}
async function removeCourse(course: Course) {
  if (saving.value) return
  await persist(courses.value.filter(item => item !== course), '已删除')
}
async function addCourse() {
  const name = newName.value.trim()
  if (!name || saving.value) return
  const start = Math.min(newStart.value, newEnd.value)
  const end = Math.max(newStart.value, newEnd.value)
  const next = [...courses.value, { name, teacher: '', location: '', weekday: activeDay.value + 1, period_start: start, period_end: end, source: 'manual' }]
  await persist(next, '已添加')
  if (!error.value) { newName.value = ''; formOpen.value = false }
}
onMounted(load)
</script>

<style scoped>
.week-page{height:100%;min-height:0;overflow-y:auto;padding:0 14px calc(16px + env(safe-area-inset-bottom));background:#f7faff;color:#17263b;overscroll-behavior:contain}
.head{display:flex;align-items:flex-end;justify-content:space-between;padding:14px 2px 9px}h1{margin:0;font-size:24px;letter-spacing:-.03em}p{margin:3px 0 0;color:#8a9bb0;font-size:10px}.add{width:34px;height:34px;border:1px solid #e3ebf7;border-radius:11px;background:#fff;color:#52708f;font-size:19px}
.week-strip{display:flex;gap:6px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:none}.week-strip::-webkit-scrollbar{display:none}.day{flex:1;min-width:42px;border:1px solid #e3ebf7;border-radius:12px;background:#fff;padding:7px 4px;color:#71859d}.day b{display:block;font-size:10px}.day small{display:block;font-size:7px;margin-top:2px;color:#9aabc0}.day.on{background:#2563eb;border-color:#2563eb;color:#fff}.day.on small{color:#dbeafe}
.form{background:#fff;border:1px solid #dbe8ff;border-radius:13px;padding:9px;margin-bottom:9px}.form input{width:100%;border:1px solid #e3ebf7;border-radius:9px;padding:8px 9px;font:16px/1.4 inherit;outline:0;background:#fbfdff}.form-row{display:flex;align-items:center;gap:5px;margin-top:7px}.form-row select{flex:1;min-width:0;border:1px solid #e3ebf7;border-radius:8px;padding:7px 5px;font:11px inherit;color:#405873;background:#fbfdff}.form-row span{font-size:8px;color:#9aabc0}.form-row button{height:32px;padding:0 11px;border:0;border-radius:8px;background:#2563eb;color:#fff;font-size:10px}.form-row button:disabled{background:#cbd5e1}
.notice{border:1px dashed #d7e6ff;background:#f4f9ff;color:#7a8fa8;border-radius:11px;padding:18px 12px;font-size:10px;text-align:center}.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:9px;padding:9px;font-size:9.5px;line-height:1.6;margin-bottom:8px}
.course{display:flex;align-items:center;gap:9px;background:#fff;border:1px solid #eef3fb;border-radius:13px;padding:10px;margin-bottom:7px}.idx{width:28px;flex:none;font:8px ui-monospace,monospace;color:#8fa3bb;text-align:center}.copy{flex:1;min-width:0}.copy b{display:block;font-size:11px;color:#314a65}.copy small{display:block;font-size:8px;color:#9aabc0;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.del{flex:none;border:1px solid #fecaca;border-radius:7px;background:#fff7f7;color:#dc2626;font-size:8px;padding:4px 7px}.del:disabled{opacity:.5}.hint{font-size:8px;color:#9aabc0;line-height:1.6;margin-top:10px}
</style>
